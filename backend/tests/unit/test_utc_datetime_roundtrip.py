"""DB 시각 왕복 회귀 테스트 (NFR-7).

🔴 이 파일이 지키는 것: **API 가 내보내는 시각 문자열에 타임존 오프셋이 붙어 있다.**

SQLite 는 타임존을 저장하지 않는다. `DateTime(timezone=True)` 로 선언해도
읽을 때 naive 로 돌아오고, 그 값의 `isoformat()` 은 오프셋이 없다.
브라우저의 `new Date("2026-09-10T00:00:00")` 은 이것을 **현지 시각**으로 해석하므로
KST 사용자에게 일정이 **9시간 어긋나** 보인다. 오류도 경고도 나지 않는다.

실제로 09:00 시작 일정이 화면에 00:00 으로 표시됐다.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from app.storage.database import Database
from app.storage.migrations import run_migrations
from app.storage.models import (
    ItineraryItemRow,
    PlaceRow,
    TripDayRow,
    TripRow,
    UtcDateTime,
)

KST = ZoneInfo("Asia/Seoul")


class TestTypeDecorator:
    def test_naive_result_gets_utc_attached(self) -> None:
        decorator = UtcDateTime()
        naive = datetime(2026, 9, 10, 0, 0, 0)
        restored = decorator.process_result_value(naive, None)
        assert restored is not None
        assert restored.tzinfo is not None
        assert restored.isoformat() == "2026-09-10T00:00:00+00:00"

    def test_aware_result_is_left_alone(self) -> None:
        decorator = UtcDateTime()
        aware = datetime(2026, 9, 10, 0, 0, tzinfo=UTC)
        assert decorator.process_result_value(aware, None) == aware

    def test_bind_converts_to_utc(self) -> None:
        # KST 09:00 은 UTC 00:00 으로 저장돼야 한다.
        decorator = UtcDateTime()
        kst = datetime.combine(date(2026, 9, 10), time(9, 0), tzinfo=KST)
        stored = decorator.process_bind_param(kst, None)
        assert stored is not None
        assert (stored.hour, stored.minute) == (0, 0)

    def test_none_passes_through(self) -> None:
        decorator = UtcDateTime()
        assert decorator.process_bind_param(None, None) is None
        assert decorator.process_result_value(None, None) is None


class TestEndToEndRoundtrip:
    """실제 세션에 저장했다 읽어 오프셋이 살아남는지 본다."""

    def test_arrival_time_keeps_offset_through_database(self, db: Database) -> None:
        kst_nine = datetime.combine(date(2026, 9, 10), time(9, 0), tzinfo=KST)

        with db.session_scope() as session:
            session.add(
                TripRow(
                    trip_id="trip-tz",
                    title="시간대 확인",
                    destination="제주",
                    start_date=date(2026, 9, 10),
                    end_date=date(2026, 9, 10),
                )
            )
            session.flush()
            session.add(
                TripDayRow(
                    day_id="day-tz",
                    trip_id="trip-tz",
                    day_index=1,
                    date=date(2026, 9, 10),
                )
            )
            session.add(
                PlaceRow(
                    place_id="place-tz",
                    name="성산일출봉",
                    latitude=33.4581,
                    longitude=126.9425,
                    category="ATTRACTION",
                    source="MOCK",
                )
            )
            session.flush()
            session.add(
                ItineraryItemRow(
                    item_id="item-tz",
                    day_id="day-tz",
                    place_id="place-tz",
                    position=0,
                    stay_minutes=60,
                    arrival_at=kst_nine.astimezone(UTC),
                )
            )

        with db.session_scope() as session:
            row = session.get(ItineraryItemRow, "item-tz")
            assert row is not None
            assert row.arrival_at is not None

            # 🔴 핵심 — 오프셋이 없으면 브라우저가 이 문자열을 현지 시각으로 읽는다.
            assert row.arrival_at.tzinfo is not None
            assert row.arrival_at.isoformat().endswith("+00:00")

            # KST 로 되돌리면 원래 09:00 이어야 한다.
            assert row.arrival_at.astimezone(KST).hour == 9


@pytest.fixture()
def db() -> Database:
    database = Database(":memory:")
    run_migrations(database.engine)
    yield database
    database.dispose()
