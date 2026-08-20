"""C31 Repositories 단위 테스트 — 인메모리 SQLite, 네트워크 비의존 (NFR-10)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from app.core.enums import AuditEventType
from app.storage.database import Database
from app.storage.migrations import run_migrations
from app.storage.models import (
    ExternalCacheRow,
    GenerationJobRow,
    ItineraryItemRow,
    PlaceRow,
    TripDayRow,
    TripRow,
)
from app.storage.repositories import (
    AuditLogRepository,
    CacheRepository,
    JobRepository,
    QuotaRepository,
    TripRepository,
)


@pytest.fixture()
def db() -> Database:
    database = Database(":memory:")
    run_migrations(database.engine)
    yield database
    database.dispose()


def _make_trip(trip_id: str = "trip-1", share_token: str | None = None) -> TripRow:
    return TripRow(
        trip_id=trip_id,
        title="부산 2박3일",
        destination="부산",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 3),
        share_token=share_token,
    )


# ---------------------------------------------------------------------------
# TripRepository
# ---------------------------------------------------------------------------
def test_trip_crud(db: Database) -> None:
    with db.session_scope() as session:
        TripRepository(session).add(_make_trip())

    with db.session_scope() as session:
        found = TripRepository(session).find("trip-1")
        assert found is not None
        assert found.destination == "부산"


def test_share_token_lookup_is_separate_path(db: Database) -> None:
    """BR-37 — 공유 토큰으로만 조회되는 경로. trip_id 와 독립이다 (BR-36)."""
    with db.session_scope() as session:
        TripRepository(session).add(_make_trip(share_token="tok-abc"))

    with db.session_scope() as session:
        repo = TripRepository(session)
        assert repo.find_by_share_token("tok-abc") is not None
        assert repo.find_by_share_token("trip-1") is None  # trip_id 로는 못 찾는다


def test_no_list_all_method_exists(db: Database) -> None:
    """BR-39 / SEC-08 — 전체 목록 조회 메서드가 존재하면 열거 취약점이 된다."""
    forbidden = {"list_all", "list", "all", "find_all", "search"}
    assert forbidden.isdisjoint(dir(TripRepository))


def test_hard_delete_cascades(db: Database) -> None:
    """BR-54 — 하드 삭제 시 하위 일자·항목이 함께 사라진다."""
    with db.session_scope() as session:
        session.add(
            PlaceRow(place_id="p1", name="장소", latitude=35.1, longitude=129.0)
        )
        trip = _make_trip()
        day = TripDayRow(day_id="d1", trip_id="trip-1", day_index=1, date=date(2026, 9, 1))
        day.items.append(
            ItineraryItemRow(item_id="i1", day_id="d1", place_id="p1", position=0, stay_minutes=60)
        )
        trip.days.append(day)
        session.add(trip)

    with db.session_scope() as session:
        assert TripRepository(session).delete("trip-1") is True

    with db.session_scope() as session:
        assert TripRepository(session).find("trip-1") is None
        assert session.get(TripDayRow, "d1") is None
        assert session.get(ItineraryItemRow, "i1") is None
        # 장소는 다른 여행에서 재사용될 수 있으므로 남는다.
        assert session.get(PlaceRow, "p1") is not None


def test_delete_missing_trip_returns_false(db: Database) -> None:
    with db.session_scope() as session:
        assert TripRepository(session).delete("none") is False


# ---------------------------------------------------------------------------
# CacheRepository
# ---------------------------------------------------------------------------
def test_cache_hit_and_expiry(db: Database) -> None:
    with db.session_scope() as session:
        CacheRepository(session).put("k1", "local_search", '{"a":1}', ttl_days=7)

    with db.session_scope() as session:
        assert CacheRepository(session).get("k1") == '{"a":1}'

    with db.session_scope() as session:
        row = session.get(ExternalCacheRow, "k1")
        row.expires_at = datetime.now(tz=UTC) - timedelta(days=1)

    with db.session_scope() as session:
        assert CacheRepository(session).get("k1") is None  # 만료


def test_cache_purge_respects_grace_period(db: Database) -> None:
    """BR-57 — 만료 직후가 아니라 유예 기간(7일) 경과분만 삭제한다."""
    with db.session_scope() as session:
        CacheRepository(session).put("recent", "blog", "x", ttl_days=0)
        CacheRepository(session).put("old", "blog", "y", ttl_days=0)
        session.get(ExternalCacheRow, "old").expires_at = datetime.now(tz=UTC) - timedelta(days=30)

    with db.session_scope() as session:
        assert CacheRepository(session).purge_expired(grace_days=7) == 1

    with db.session_scope() as session:
        assert session.get(ExternalCacheRow, "old") is None
        assert session.get(ExternalCacheRow, "recent") is not None


# ---------------------------------------------------------------------------
# JobRepository
# ---------------------------------------------------------------------------
def test_orphan_jobs_are_recovered(db: Database) -> None:
    """RP-4 — 비정상 종료로 running 에 남은 job 을 기동 시 failed 로 전환한다."""
    with db.session_scope() as session:
        JobRepository(session).insert(
            GenerationJobRow(job_id="j1", trip_id="trip-1", state="running")
        )
        JobRepository(session).insert(
            GenerationJobRow(job_id="j2", trip_id="trip-1", state="succeeded")
        )

    with db.session_scope() as session:
        assert JobRepository(session).recover_orphans('{"code":"INTERNAL_ERROR"}') == 1

    with db.session_scope() as session:
        assert JobRepository(session).find("j1").state == "failed"
        assert JobRepository(session).find("j2").state == "succeeded"


def test_completed_jobs_are_purged(db: Database) -> None:
    """BR-56 — 완료 후 24시간 경과분만 정리한다."""
    with db.session_scope() as session:
        repo = JobRepository(session)
        repo.insert(
            GenerationJobRow(
                job_id="old", trip_id="t", state="succeeded",
                completed_at=datetime.now(tz=UTC) - timedelta(hours=48),
            )
        )
        repo.insert(
            GenerationJobRow(
                job_id="new", trip_id="t", state="succeeded",
                completed_at=datetime.now(tz=UTC),
            )
        )

    with db.session_scope() as session:
        assert JobRepository(session).purge_completed(retention_hours=24) == 1

    with db.session_scope() as session:
        assert JobRepository(session).find("old") is None
        assert JobRepository(session).find("new") is not None


# ---------------------------------------------------------------------------
# QuotaRepository — SP-4 (전역 일일 상한은 영속화)
# ---------------------------------------------------------------------------
def test_quota_counter_persists_across_sessions(db: Database) -> None:
    """SP-4 — 재시작으로 비용 통제가 우회되면 안 된다."""
    with db.session_scope() as session:
        QuotaRepository(session).increment("NAVER_LOCAL", count=3)

    with db.session_scope() as session:
        assert QuotaRepository(session).peek("NAVER_LOCAL") == 3
        assert QuotaRepository(session).increment("NAVER_LOCAL") == 4


def test_quota_usage_today_reports_all_apis(db: Database) -> None:
    with db.session_scope() as session:
        repo = QuotaRepository(session)
        repo.increment("NAVER_LOCAL", count=2)
        repo.increment("ANTHROPIC", error=True)

    with db.session_scope() as session:
        usage = QuotaRepository(session).usage_today()
        assert usage["NAVER_LOCAL"]["call_count"] == 2
        assert usage["ANTHROPIC"]["error_count"] == 1


# ---------------------------------------------------------------------------
# AuditLogRepository
# ---------------------------------------------------------------------------
def test_audit_append_and_retention(db: Database) -> None:
    with db.session_scope() as session:
        repo = AuditLogRepository(session)
        repo.append(AuditEventType.TRIP_CREATED, subject_id="trip-1", detail={"days": 3})
        repo.append(AuditEventType.SHARE_TOKEN_ISSUED, subject_id="trip-1")

    with db.session_scope() as session:
        assert AuditLogRepository(session).count() == 2
        assert AuditLogRepository(session).purge_older_than(90) == 0
