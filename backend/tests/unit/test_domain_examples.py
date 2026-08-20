"""domain 계층 예제 기반 테스트 (PBT-10 — PBT 와 병행).

속성 테스트가 "일반 규칙"을 보는 반면, 여기서는 비즈니스적으로 중요한
구체 시나리오를 못박는다.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time

import pytest

from app.domain import ics, timeline
from app.domain.estimator import estimate_transit, estimate_walk
from app.domain.matrix import DistanceMatrix
from app.domain.models import (
    Coordinate,
    CoordinateOutOfRangeError,
    DayRule,
    ItineraryItem,
    LegSource,
    OpeningHours,
    OptimizeConstraints,
    Place,
    PlaceCandidate,
    PlaceCategory,
    PlaceSource,
    TravelLeg,
    TravelMode,
    WarningType,
)
from app.domain.optimizer import DETERMINISTIC_LIMITS, optimize

SEOUL = Coordinate(37.5665, 126.9780)
BUSAN = Coordinate(35.1796, 129.0756)
DAY = date(2026, 9, 1)  # 화요일


def _place(name: str = "장소", coord: Coordinate = SEOUL, hours: OpeningHours | None = None) -> Place:
    return Place(
        place_id=f"p-{name}",
        name=name,
        coordinate=coord,
        category=PlaceCategory.RESTAURANT,
        source=PlaceSource.MOCK,
        opening_hours=hours,
    )


def _item(idx: int, stay: int = 60, *, fixed: time | None = None, place: Place | None = None) -> ItineraryItem:
    return ItineraryItem(
        item_id=f"item-{idx}",
        place=place or _place(f"장소{idx}"),
        stay_minutes=stay,
        position=idx,
        time_fixed=fixed is not None,
        fixed_time=fixed,
    )


def _legs(n: int, seconds: int, mode: TravelMode = TravelMode.WALK) -> DistanceMatrix:
    legs = [
        TravelLeg(
            from_index=i,
            to_index=j,
            mode=mode,
            duration_sec=seconds,
            distance_m=seconds * 2,
            source=LegSource.HAVERSINE_WALK,
            is_estimate=True,
        )
        for i in range(n)
        for j in range(n)
        if i != j
    ]
    return DistanceMatrix.from_legs(legs)


# ---------------------------------------------------------------------------
# BR-15 좌표 범위
# ---------------------------------------------------------------------------
def test_coordinate_rejects_out_of_country_values() -> None:
    """BR-15 — 좌표계를 잘못 해석하면 값이 범위를 크게 벗어난다. 즉시 실패시킨다."""
    with pytest.raises(CoordinateOutOfRangeError):
        Coordinate(0.0, 0.0)
    with pytest.raises(CoordinateOutOfRangeError):
        # KATECH(TM128) 계열 좌표를 그대로 넣은 경우
        Coordinate(311111.0, 552222.0)


# ---------------------------------------------------------------------------
# BR-08 LLM 후보에는 사실 정보 필드가 없다
# ---------------------------------------------------------------------------
def test_place_candidate_has_no_factual_fields() -> None:
    """BR-08 — 주소·좌표·전화를 타입 수준에서 수용할 수 없다."""
    fields = set(PlaceCandidate.__dataclass_fields__)
    assert fields == {
        "raw_name",
        "category_hint",
        "suggested_stay_minutes",
        "reason",
        "preferred_time_slot",
    }
    for forbidden in ("coordinate", "lat", "lng", "address", "road_address", "phone", "opening_hours"):
        assert forbidden not in fields


# ---------------------------------------------------------------------------
# BR-31 / BR-32 고정 시각
# ---------------------------------------------------------------------------
def test_fixed_time_is_kept_and_conflict_is_warned() -> None:
    """BR-32 — 도착이 불가능해도 시각을 밀지 않고 경고만 붙인다."""
    items = [_item(0, stay=600), _item(1, stay=60, fixed=time(10, 0))]
    result = timeline.compute(
        items, _legs(2, 600), day=DAY, day_start=time(9, 0), day_end=time(23, 0),
        default_mode=TravelMode.WALK,
    )
    second = result[1]
    assert second.arrival_at.astimezone(timeline.KST).time() == time(10, 0)
    assert any(w.type is WarningType.FIXED_TIME_CONFLICT for w in second.warnings)


def test_no_conflict_warning_when_reachable() -> None:
    items = [_item(0, stay=30), _item(1, stay=60, fixed=time(14, 0))]
    result = timeline.compute(
        items, _legs(2, 300), day=DAY, day_start=time(9, 0), day_end=time(23, 0),
        default_mode=TravelMode.WALK,
    )
    assert not any(w.type is WarningType.FIXED_TIME_CONFLICT for w in result[1].warnings)


# ---------------------------------------------------------------------------
# BR-33 하루 종료 초과
# ---------------------------------------------------------------------------
def test_day_overflow_is_warned_but_not_moved() -> None:
    """BR-33 — 초과해도 다음 날로 옮기거나 삭제하지 않는다."""
    items = [_item(0, stay=720)]
    result = timeline.compute(
        items, _legs(1, 0), day=DAY, day_start=time(18, 0), day_end=time(21, 0),
        default_mode=TravelMode.WALK,
    )
    assert len(result) == 1
    assert any(w.type is WarningType.DAY_OVERFLOW for w in result[0].warnings)


# ---------------------------------------------------------------------------
# BR-35 영업시간 — 정보가 없으면 경고하지 않는다
# ---------------------------------------------------------------------------
def test_no_opening_hours_means_no_warning() -> None:
    """BR-35 — 네이버 지역검색이 영업시간을 주지 않으므로 미입력이 정상 상태다."""
    items = [_item(0)]
    result = timeline.compute(
        items, _legs(1, 0), day=DAY, day_start=time(3, 0), day_end=time(23, 0),
        default_mode=TravelMode.WALK,
    )
    assert not any(w.type is WarningType.OUTSIDE_OPENING_HOURS for w in result[0].warnings)


def test_opening_hours_warning_when_user_entered() -> None:
    hours = OpeningHours(weekday_rules=(DayRule(weekday=1, open=time(11, 0), close=time(21, 0)),))
    items = [_item(0, place=_place("식당", hours=hours))]
    result = timeline.compute(
        items, _legs(1, 0), day=DAY, day_start=time(9, 0), day_end=time(23, 0),
        default_mode=TravelMode.WALK,
    )
    assert any(w.type is WarningType.OUTSIDE_OPENING_HOURS for w in result[0].warnings)


def test_closed_day_is_warned() -> None:
    hours = OpeningHours(weekday_rules=(DayRule(weekday=1, closed=True),))
    items = [_item(0, place=_place("휴무", hours=hours))]
    result = timeline.compute(
        items, _legs(1, 0), day=DAY, day_start=time(12, 0), day_end=time(23, 0),
        default_mode=TravelMode.WALK,
    )
    warning = next(w for w in result[0].warnings if w.type is WarningType.OUTSIDE_OPENING_HOURS)
    assert "휴무" in warning.detail


def test_overnight_opening_hours() -> None:
    """자정을 넘기는 영업시간(18:00~02:00)에 20:00 도착은 영업 중이다."""
    hours = OpeningHours(weekday_rules=(DayRule(weekday=1, open=time(18, 0), close=time(2, 0)),))
    items = [_item(0, place=_place("포차", hours=hours))]
    result = timeline.compute(
        items, _legs(1, 0), day=DAY, day_start=time(20, 0), day_end=time(23, 59),
        default_mode=TravelMode.WALK,
    )
    assert not any(w.type is WarningType.OUTSIDE_OPENING_HOURS for w in result[0].warnings)


# ---------------------------------------------------------------------------
# BR-27 근사 이동시간 경고
# ---------------------------------------------------------------------------
def test_estimated_travel_time_is_flagged() -> None:
    items = [_item(0), _item(1)]
    result = timeline.compute(
        items, _legs(2, 900), day=DAY, day_start=time(9, 0), day_end=time(23, 0),
        default_mode=TravelMode.WALK,
    )
    assert any(w.type is WarningType.ESTIMATED_TRAVEL_TIME for w in result[0].warnings)


def test_transit_leg_cannot_have_path() -> None:
    """BR-27 — 대중교통 구간에 실경로를 넣으려는 시도는 거부된다."""
    with pytest.raises(ValueError):
        TravelLeg(
            from_index=0, to_index=1, mode=TravelMode.TRANSIT,
            duration_sec=600, distance_m=1000,
            source=LegSource.HAVERSINE_TRANSIT, is_estimate=True,
            path=(SEOUL, BUSAN),
        )


# ---------------------------------------------------------------------------
# BR-19 앵커 제약
# ---------------------------------------------------------------------------
def test_anchor_start_and_end_are_pinned() -> None:
    items = [_item(i) for i in range(6)]
    matrix = _legs(6, 300)
    constraints = OptimizeConstraints(anchor_start="item-0", anchor_end="item-5")
    result = optimize(items, matrix, TravelMode.WALK, constraints, limits=DETERMINISTIC_LIMITS)
    assert result[0].item_id == "item-0"
    assert result[5].item_id == "item-5"


def test_optimize_keeps_single_and_empty_lists() -> None:
    assert optimize([], _legs(0, 0), TravelMode.WALK, limits=DETERMINISTIC_LIMITS) == []
    single = [_item(0)]
    assert [i.item_id for i in optimize(single, _legs(1, 0), TravelMode.WALK, limits=DETERMINISTIC_LIMITS)] == ["item-0"]


# ---------------------------------------------------------------------------
# BR-24 / BR-25 최소 시간
# ---------------------------------------------------------------------------
def test_minimum_durations_for_close_points() -> None:
    near = Coordinate(37.5665, 126.9781)   # 약 12m
    assert estimate_walk(SEOUL, near, 0, 1).duration_sec == 180

    # 🔴 BR-25 는 `거리 ÷ 20km/h + 600초(대기)`, 최소 600초다.
    #    대기 600초가 **더해지므로** 거리가 0 이 아닌 한 결과는 항상 600 을 넘는다.
    #    12m -> 이동 2초 + 대기 600초 = 602초.
    #    (원래 이 테스트는 600 을 기대했다. 최소값이 지배할 것이라 가정했지만,
    #     대기 시간이 최소값 적용 **전에** 더해지므로 그렇지 않다.)
    assert estimate_transit(SEOUL, near, 0, 1).duration_sec == 602

    # 최소값이 실제로 바닥 역할을 하는 것은 거리가 0 일 때뿐이다.
    assert estimate_transit(SEOUL, SEOUL, 0, 1).duration_sec == 600


# ---------------------------------------------------------------------------
# BR-45 ICS 줄 접기
# ---------------------------------------------------------------------------
def test_ics_lines_respect_75_octet_limit() -> None:
    item = _item(0, place=_place("가" * 80))
    timed = item.with_times(
        datetime(2026, 9, 1, 1, 0, tzinfo=UTC), datetime(2026, 9, 1, 2, 0, tzinfo=UTC)
    )
    text = ics.build("긴 이름 테스트", [timed])
    for line in text.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


def test_ics_skips_items_without_times() -> None:
    text = ics.build("미계산", [_item(0)])
    assert "BEGIN:VEVENT" not in text
