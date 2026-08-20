"""C21 TripService — 여행 생명주기 관리.

근거:
    FR-4    생성·조회·수정·삭제
    FR-5    항목 추가·삭제·순서 변경·일자 이동
    FR-7    시각·체류시간·메모 편집
    FR-25   UUIDv4 식별자 + **읽기 전용 공유 토큰**
    BR-01~05  규모·형식 검증
    BR-36   공유 토큰은 암호학적 난수 32바이트(base64url 43자), trip_id 와 독립
    BR-37   공유 조회는 **읽기 전용 타입**을 반환
    BR-39   목록 조회 API 없음 (열거 방지)
    BR-54   하드 삭제 + 감사 로그
    ND-18   DB 접근은 DbExecutor 경유
"""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from app.core.enums import AuditEventType
from app.core.errors import NotFoundError, ValidationError
from app.core.logging_config import get_correlation_id, get_logger
from app.domain.models import ItineraryItem, TripSpec, UnresolvedCandidate
from app.storage.database import Database
from app.storage.db_executor import DbExecutor
from app.storage.mappers import (
    item_to_row,
    opening_hours_to_row,
    place_to_row,
    row_to_item,
    row_to_spec,
    spec_to_row,
    unresolved_to_row,
)
from app.storage.models import TripDayRow, TripRow
from app.storage.repositories import AuditLogRepository, TripRepository

logger = get_logger(__name__)

SHARE_TOKEN_BYTES = 32  # BR-36 -> base64url 43자


@dataclass(frozen=True, slots=True)
class TripView:
    """조회 결과. 편집 메서드를 갖지 않는다."""

    trip_id: str
    spec: TripSpec
    days: list[list[ItineraryItem]]
    unresolved: list[dict]
    share_token: str | None

    def to_dict(self, *, include_share_token: bool = True) -> dict:
        payload = {
            "trip_id": self.trip_id,
            **self.spec.to_dict(),
            "days": [
                {"day_index": index + 1, "items": [i.to_dict() for i in items]}
                for index, items in enumerate(self.days)
            ],
            "unresolved": self.unresolved,
        }
        if include_share_token:
            payload["share_token"] = self.share_token
        return payload


@dataclass(frozen=True, slots=True)
class ReadOnlyTripView:
    """BR-37 / DD-25 — 공유 링크 조회 전용.

    편집 연산이 정의되지 않은 별도 타입이라, 공유 경로에서 쓰기가
    **타입 수준에서** 불가능하다.
    """

    trip_id: str
    spec: TripSpec
    days: list[list[ItineraryItem]]

    def to_dict(self) -> dict:
        return {
            "trip_id": self.trip_id,
            **self.spec.to_dict(),
            "days": [
                {"day_index": index + 1, "items": [i.to_dict() for i in items]}
                for index, items in enumerate(self.days)
            ],
            "read_only": True,
        }


class TripService:
    def __init__(
        self,
        database: Database,
        executor: DbExecutor,
        *,
        max_trip_days: int = 10,
        max_items_per_day: int = 15,
        max_items_per_trip: int = 100,
    ) -> None:
        self._db = database
        self._executor = executor
        self._max_trip_days = max_trip_days
        self._max_items_per_day = max_items_per_day
        self._max_items_per_trip = max_items_per_trip

    # ------------------------------------------------------------------
    # 검증 (BR-01 ~ BR-04)
    # ------------------------------------------------------------------
    def validate_spec(self, spec: TripSpec) -> None:
        if spec.end_date < spec.start_date:
            raise ValidationError("end_date < start_date")
        if spec.day_count > self._max_trip_days:
            raise ValidationError(f"trip length {spec.day_count} > {self._max_trip_days}")
        if spec.day_end_time <= spec.day_start_time:
            raise ValidationError("day_end_time <= day_start_time")
        if not (1 <= spec.party_size <= 20):
            raise ValidationError(f"party_size out of range: {spec.party_size}")
        if not (1 <= len(spec.title) <= 100):
            raise ValidationError("title length out of range")
        if not (1 <= len(spec.destination) <= 50):
            raise ValidationError("destination length out of range")
        if len(spec.style_tags) > 8:
            raise ValidationError("too many style tags")

    # ------------------------------------------------------------------
    async def create(self, spec: TripSpec) -> str:
        self.validate_spec(spec)
        trip_id = str(uuid.uuid4())  # SEC-08 — 추측 불가능한 식별자

        def _create() -> None:
            with self._db.session_scope() as session:
                row = spec_to_row(spec, trip_id)
                for index in range(spec.day_count):
                    row.days.append(
                        TripDayRow(
                            day_id=str(uuid.uuid4()),
                            trip_id=trip_id,
                            day_index=index + 1,
                            date=spec.start_date + timedelta(days=index),
                        )
                    )
                TripRepository(session).add(row)
                AuditLogRepository(session).append(
                    AuditEventType.TRIP_CREATED,
                    correlation_id=get_correlation_id(),
                    subject_id=trip_id,
                    detail={"day_count": spec.day_count, "destination": spec.destination},
                )

        await self._executor.run(_create)
        return trip_id

    async def get(self, trip_id: str) -> TripView:
        def _get() -> TripView:
            with self._db.session_scope() as session:
                row = TripRepository(session).find(trip_id)
                if row is None:
                    raise NotFoundError(f"trip not found: {trip_id}")
                return self._to_view(row)

        return await self._executor.run(_get)

    async def get_by_share_token(self, share_token: str) -> ReadOnlyTripView:
        """BR-37 — 공유 토큰 전용 경로. 편집 불가 타입을 반환한다."""

        def _get() -> ReadOnlyTripView:
            with self._db.session_scope() as session:
                row = TripRepository(session).find_by_share_token(share_token)
                if row is None:
                    raise NotFoundError("shared trip not found")
                view = self._to_view(row)
                return ReadOnlyTripView(trip_id=view.trip_id, spec=view.spec, days=view.days)

        return await self._executor.run(_get)

    async def delete(self, trip_id: str) -> None:
        """BR-54 — 하드 삭제 + 감사 로그."""

        def _delete() -> None:
            with self._db.session_scope() as session:
                repo = TripRepository(session)
                row = repo.find(trip_id)
                if row is None:
                    raise NotFoundError(f"trip not found: {trip_id}")
                item_count = sum(len(day.items) for day in row.days)
                repo.delete(trip_id)
                AuditLogRepository(session).append(
                    AuditEventType.TRIP_DELETED,
                    correlation_id=get_correlation_id(),
                    subject_id=trip_id,
                    detail={"item_count": item_count},
                )

        await self._executor.run(_delete)

    # ------------------------------------------------------------------
    # 공유 (FR-25)
    # ------------------------------------------------------------------
    async def issue_share_token(self, trip_id: str) -> str:
        token = secrets.token_urlsafe(SHARE_TOKEN_BYTES)  # BR-36

        def _issue() -> str:
            with self._db.session_scope() as session:
                row = TripRepository(session).find(trip_id)
                if row is None:
                    raise NotFoundError(f"trip not found: {trip_id}")
                row.share_token = token
                AuditLogRepository(session).append(
                    AuditEventType.SHARE_TOKEN_ISSUED,
                    correlation_id=get_correlation_id(),
                    subject_id=trip_id,
                )
                return token

        return await self._executor.run(_issue)

    async def revoke_share_token(self, trip_id: str) -> None:
        def _revoke() -> None:
            with self._db.session_scope() as session:
                row = TripRepository(session).find(trip_id)
                if row is None:
                    raise NotFoundError(f"trip not found: {trip_id}")
                row.share_token = None  # BR-38 — 기존 링크 즉시 무효화
                AuditLogRepository(session).append(
                    AuditEventType.SHARE_TOKEN_REVOKED,
                    correlation_id=get_correlation_id(),
                    subject_id=trip_id,
                )

        await self._executor.run(_revoke)

    # ------------------------------------------------------------------
    # 일정 저장 (WF-2 SAVING 단계)
    # ------------------------------------------------------------------
    async def replace_itinerary(
        self,
        trip_id: str,
        days: list[list[ItineraryItem]],
        unresolved: list[UnresolvedCandidate],
    ) -> None:
        """BR-53 — 원자적으로 교체한다. 실패 시 전체 롤백."""
        total = sum(len(items) for items in days)
        if total > self._max_items_per_trip:
            raise ValidationError(f"total items {total} > {self._max_items_per_trip}")
        for items in days:
            if len(items) > self._max_items_per_day:
                raise ValidationError(f"items per day {len(items)} > {self._max_items_per_day}")

        def _replace() -> None:
            with self._db.session_scope() as session:
                row = TripRepository(session).find(trip_id)
                if row is None:
                    raise NotFoundError(f"trip not found: {trip_id}")

                seen_places: set[str] = set()
                for day_row, items in zip(row.days, days, strict=False):
                    day_row.items.clear()
                    for position, item in enumerate(items):
                        if item.place.place_id not in seen_places:
                            session.merge(place_to_row(item.place))
                            # 🔴 영업시간은 **별도 테이블**이라 place_to_row 에 실리지 않는다.
                            #    이 병합을 빠뜨리면 PUT /opening-hours 가 200 을 돌려주고도
                            #    값이 저장되지 않아, 사용자가 입력한 영업시간이
                            #    다음 조회에서 조용히 사라진다 (FR-13 / BR-35 무력화).
                            #    Build and Test 에서 발견.
                            if item.place.opening_hours is not None:
                                session.merge(
                                    opening_hours_to_row(
                                        item.place.place_id, item.place.opening_hours
                                    )
                                )
                            seen_places.add(item.place.place_id)
                        item_row = item_to_row(item, day_row.day_id)
                        item_row.position = position
                        day_row.items.append(item_row)

                row.unresolved.clear()
                for candidate in unresolved:
                    row.unresolved.append(unresolved_to_row(trip_id, candidate))

                AuditLogRepository(session).append(
                    AuditEventType.TRIP_UPDATED,
                    correlation_id=get_correlation_id(),
                    subject_id=trip_id,
                    detail={"item_count": total, "unresolved_count": len(unresolved)},
                )

        await self._executor.run(_replace)

    # ------------------------------------------------------------------
    @staticmethod
    def _to_view(row: TripRow) -> TripView:
        days = [[row_to_item(item) for item in day.items] for day in row.days]
        unresolved = [
            {
                "raw_name": u.raw_name,
                "day_index": u.day_index,
                "category_hint": u.category_hint,
                "reason": u.reason,
                "failure_code": u.failure_code,
                "best_candidate_name": u.best_candidate_name,
                "best_match_score": u.best_match_score,
            }
            for u in row.unresolved
        ]
        return TripView(
            trip_id=row.trip_id,
            spec=row_to_spec(row),
            days=days,
            unresolved=unresolved,
            share_token=row.share_token,
        )
