"""SEC-14 / BR-59 — 감사 로그가 **추가 전용**임을 구조적으로 검증한다.

이 테스트는 "코드가 지금 무엇을 하는가"가 아니라 **"설계 규칙이 코드에 남아 있는가"**
를 본다. 누군가 편의를 위해 수정·삭제 메서드를 추가하면 즉시 실패한다.
"""

from __future__ import annotations

import inspect

from app.core.enums import AuditEventType
from app.storage.database import Database
from app.storage.migrations import run_migrations
from app.storage.repositories import AuditLogRepository

# 개별 이벤트를 바꾸거나 지우는 이름들. purge_older_than 은 SEC-14 의
# 보존 정책 이행이므로 유일하게 허용되는 삭제 경로다.
FORBIDDEN_METHOD_NAMES = {
    "update",
    "modify",
    "edit",
    "delete",
    "remove",
    "delete_by_id",
    "clear",
    "truncate",
    "purge_all",
}


def test_repository_exposes_no_mutation_methods() -> None:
    public = {
        name
        for name, _ in inspect.getmembers(AuditLogRepository, predicate=inspect.isfunction)
        if not name.startswith("_")
    }
    assert FORBIDDEN_METHOD_NAMES.isdisjoint(public), (
        f"감사 로그에 수정·삭제 메서드가 추가되었습니다: {public & FORBIDDEN_METHOD_NAMES}"
    )
    assert public == {"append", "count", "recent", "purge_older_than"}


def test_purge_only_accepts_a_retention_cutoff() -> None:
    """유일한 삭제 경로는 보존 기간 기준 일괄 정리여야 한다.

    개별 이벤트를 지목할 수 있는 인자(event_id 등)를 받으면 안 된다.
    """
    signature = inspect.signature(AuditLogRepository.purge_older_than)
    params = [p for p in signature.parameters if p != "self"]
    assert params == ["days"]


def test_appended_events_are_immutable_in_practice() -> None:
    """추가 후 조회되는 값이 그대로 유지되는지 확인한다."""
    database = Database(":memory:")
    run_migrations(database.engine)
    try:
        with database.session_scope() as session:
            AuditLogRepository(session).append(
                AuditEventType.TRIP_DELETED, subject_id="trip-9", detail={"item_count": 7}
            )

        with database.session_scope() as session:
            events = AuditLogRepository(session).recent()
            assert len(events) == 1
            assert events[0].event_type == "TRIP_DELETED"
            assert events[0].subject_id == "trip-9"
            assert '"item_count": 7' in events[0].detail
    finally:
        database.dispose()
