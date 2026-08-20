"""C31 Repositories — 테이블별 영속화 접근.

근거:
    BR-37  공유 토큰 조회는 별도 경로 (trip_id 로는 조회 불가)
    BR-39  **여행 목록 조회 메서드를 제공하지 않는다** (열거 방지, SEC-08)
    BR-54  하드 삭제 + 연쇄 삭제
    BR-56  완료 job 24시간 뒤 정리
    BR-57  캐시 TTL 만료 + 7일 유예
    BR-59  감사 로그는 **추가 전용**, 90일 보존
    SEC-05 ORM 파라미터 바인딩만 사용

전 메서드는 **동기**이며, async 컨텍스트에서는 L4 DbExecutor 를 경유해 호출한다 (ND-18).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import ApiName, AuditEventType
from app.storage.models import (
    ApiUsageRow,
    AuditEventRow,
    ExternalCacheRow,
    GenerationJobRow,
    TripRow,
    utcnow,
)

KST = ZoneInfo("Asia/Seoul")


def kst_today() -> date:
    """BR-50 — 쿼터 일자는 KST 기준."""
    return datetime.now(tz=KST).date()


# ---------------------------------------------------------------------------
class TripRepository:
    """여행 애그리게이트 영속화.

    ⚠️ `list_all()` 같은 전체 목록 메서드를 **의도적으로 제공하지 않는다** (BR-39).
       계정이 없는 구성에서 목록 API 는 열거 취약점이 된다.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, trip: TripRow) -> TripRow:
        self.session.add(trip)
        self.session.flush()
        return trip

    def find(self, trip_id: str) -> TripRow | None:
        stmt = (
            select(TripRow)
            .where(TripRow.trip_id == trip_id)
            .options(selectinload(TripRow.days), selectinload(TripRow.unresolved))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def find_by_share_token(self, share_token: str) -> TripRow | None:
        """BR-37 — 공유 토큰 전용 조회 경로."""
        stmt = (
            select(TripRow)
            .where(TripRow.share_token == share_token)
            .options(selectinload(TripRow.days), selectinload(TripRow.unresolved))
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def delete(self, trip_id: str) -> bool:
        """BR-54 — 하드 삭제. ORM 연쇄로 하위 행을 함께 제거한다."""
        trip = self.session.get(TripRow, trip_id)
        if trip is None:
            return False
        self.session.delete(trip)
        self.session.flush()
        return True


# ---------------------------------------------------------------------------
def _as_utc(value: datetime) -> datetime:
    """SQLite 에서 읽은 naive datetime 에 UTC 를 붙인다.

    🔴 컬럼을 ``DateTime(timezone=True)`` 로 선언해도 **SQLite 는 타임존을 저장하지 않는다.**
       SQLAlchemy 가 돌려주는 값은 tzinfo 가 없는 naive datetime 이고,
       ``utcnow()`` 는 aware 이므로 그대로 비교하면
       ``TypeError: can't compare offset-naive and offset-aware datetimes`` 가 난다.

       Build and Test 에서 발견: 캐시를 **읽을 때마다** 예외가 나서 C12 캐시 데코레이터가
       통째로 동작하지 않았다 (NFR-4). 쓰기는 성공하므로 증상이 늦게 드러난다.

       저장하는 값은 항상 UTC 이므로(``put`` 이 ``utcnow()`` 기준) UTC 로 해석하면 된다.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


# ---------------------------------------------------------------------------
class CacheRepository:
    """C12 CachingClientDecorator 가 사용하는 TTL 캐시 저장소 (NFR-4)."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, cache_key: str) -> str | None:
        row = self.session.get(ExternalCacheRow, cache_key)
        if row is None:
            return None
        if _as_utc(row.expires_at) <= utcnow():
            return None  # 만료. 삭제는 정리 작업(BR-57)이 맡는다.
        return row.payload

    def put(self, cache_key: str, namespace: str, payload: str, ttl_days: int) -> None:
        expires = utcnow() + timedelta(days=ttl_days)
        row = self.session.get(ExternalCacheRow, cache_key)
        if row is None:
            self.session.add(
                ExternalCacheRow(
                    cache_key=cache_key,
                    namespace=namespace,
                    payload=payload,
                    expires_at=expires,
                )
            )
        else:
            row.payload = payload
            row.expires_at = expires
        self.session.flush()

    def purge_expired(self, grace_days: int) -> int:
        """BR-57 — TTL 만료 후 유예 기간이 지난 항목을 삭제한다."""
        cutoff = utcnow() - timedelta(days=grace_days)
        result = self.session.execute(
            delete(ExternalCacheRow).where(ExternalCacheRow.expires_at < cutoff)
        )
        return int(result.rowcount or 0)


# ---------------------------------------------------------------------------
class JobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def insert(self, job: GenerationJobRow) -> GenerationJobRow:
        self.session.add(job)
        self.session.flush()
        return job

    def find(self, job_id: str) -> GenerationJobRow | None:
        return self.session.get(GenerationJobRow, job_id)

    def update(self, job_id: str, **fields: object) -> GenerationJobRow | None:
        job = self.session.get(GenerationJobRow, job_id)
        if job is None:
            return None
        for key, value in fields.items():
            setattr(job, key, value)
        self.session.flush()
        return job

    def recover_orphans(self, problem_json: str) -> int:
        """RP-4 — 기동 시 `running` 으로 남은 job 을 `failed` 로 전환한다.

        프로세스가 비정상 종료되면 그 job 은 영원히 running 으로 남는다.
        """
        rows = (
            self.session.execute(
                select(GenerationJobRow).where(GenerationJobRow.state.in_(("running", "queued")))
            )
            .scalars()
            .all()
        )
        for row in rows:
            row.state = "failed"
            row.problem_json = problem_json
            row.completed_at = utcnow()
        self.session.flush()
        return len(rows)

    def purge_completed(self, retention_hours: int) -> int:
        """BR-56 — 완료 후 24시간 경과 job 정리."""
        cutoff = utcnow() - timedelta(hours=retention_hours)
        result = self.session.execute(
            delete(GenerationJobRow).where(
                GenerationJobRow.completed_at.is_not(None),
                GenerationJobRow.completed_at < cutoff,
            )
        )
        return int(result.rowcount or 0)


# ---------------------------------------------------------------------------
class QuotaRepository:
    """C29 QuotaService 의 저장 계층 (BR-50, SP-4).

    IP 단위 윈도와 달리 **일일 카운터는 영속화한다.** 재시작으로 비용 통제가
    우회되면 안 되기 때문이다.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def increment(self, api_name: str, *, count: int = 1, error: bool = False) -> int:
        today = kst_today()
        row = self.session.get(ApiUsageRow, (api_name, today))
        if row is None:
            row = ApiUsageRow(api_name=api_name, usage_date=today, call_count=0, error_count=0)
            self.session.add(row)
        row.call_count += count
        if error:
            row.error_count += 1
        self.session.flush()
        return row.call_count

    def peek(self, api_name: str) -> int:
        row = self.session.get(ApiUsageRow, (api_name, kst_today()))
        return row.call_count if row else 0

    def usage_today(self) -> dict[str, dict[str, int]]:
        today = kst_today()
        rows = (
            self.session.execute(select(ApiUsageRow).where(ApiUsageRow.usage_date == today))
            .scalars()
            .all()
        )
        return {
            row.api_name: {"call_count": row.call_count, "error_count": row.error_count}
            for row in rows
        }

    def purge_older_than(self, days: int) -> int:
        cutoff = kst_today() - timedelta(days=days)
        result = self.session.execute(delete(ApiUsageRow).where(ApiUsageRow.usage_date < cutoff))
        return int(result.rowcount or 0)


# ---------------------------------------------------------------------------
class AuditLogRepository:
    """SEC-14 / BR-59 — **추가 전용 감사 로그.**

    🔴 이 클래스에는 기존 이벤트를 **수정하거나 개별 삭제하는 메서드가 없다.**
       유일한 삭제 경로는 보존 기간(90일) 경과분을 일괄 정리하는
       `purge_older_than` 이며, 이는 SEC-14 의 보존 정책 이행이다.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def append(
        self,
        event_type: AuditEventType,
        *,
        correlation_id: str = "-",
        subject_id: str | None = None,
        detail: dict[str, object] | None = None,
    ) -> str:
        # SEC-03 — detail 에 인증 정보·좌표 원문·요청 본문 전체를 넣지 않는다.
        event_id = str(uuid.uuid4())
        self.session.add(
            AuditEventRow(
                event_id=event_id,
                occurred_at=utcnow(),
                event_type=event_type.value,
                correlation_id=correlation_id,
                subject_id=subject_id,
                detail=json.dumps(detail or {}, ensure_ascii=False, default=str),
            )
        )
        self.session.flush()
        return event_id

    def count(self) -> int:
        return int(self.session.execute(select(func.count(AuditEventRow.event_id))).scalar_one())

    def recent(self, limit: int = 100) -> list[AuditEventRow]:
        stmt = select(AuditEventRow).order_by(AuditEventRow.occurred_at.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def purge_older_than(self, days: int) -> int:
        """BR-59 — 보존 기간 경과분만 정리한다. 개별 이벤트 삭제 경로는 없다."""
        cutoff = datetime.now(tz=UTC) - timedelta(days=days)
        result = self.session.execute(
            delete(AuditEventRow).where(AuditEventRow.occurred_at < cutoff)
        )
        return int(result.rowcount or 0)
