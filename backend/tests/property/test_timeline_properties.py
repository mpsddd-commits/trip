"""C15 TimelineCalculator 속성 기반 테스트 — P-01 ~ P-05 (PBT-03 / PBT-R2)."""

from __future__ import annotations

from datetime import date, time

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain import timeline
from app.domain.matrix import DistanceMatrix
from app.domain.models import TravelMode, WarningType
from tests.property.generators import item_lists, travel_legs

pytestmark = pytest.mark.property

DAY = date(2026, 9, 1)
DAY_START = time(9, 0)
DAY_END = time(21, 0)


@st.composite
def _scenario(draw):
    items = draw(item_lists(min_size=1, max_size=10))
    mode = draw(st.sampled_from(list(TravelMode)))
    legs = []
    for i in range(len(items) - 1):
        for m in TravelMode:
            legs.append(draw(travel_legs(from_index=i, to_index=i + 1, mode=m)))
    return items, DistanceMatrix.from_legs(legs), mode


@given(_scenario())
def test_p01_p02_item_set_is_preserved(scenario) -> None:
    """P-01 개수 보존 / P-02 구성(id) 보존."""
    items, matrix, mode = scenario
    result = timeline.compute(
        items, matrix, day=DAY, day_start=DAY_START, day_end=DAY_END, default_mode=mode
    )
    assert len(result) == len(items)
    assert [i.item_id for i in result] == [i.item_id for i in items]


@given(_scenario())
def test_p03_times_are_monotonic_where_no_conflict(scenario) -> None:
    """P-03 (정밀화) 시각 단조 증가.

    ⚠️ Functional Design 은 무조건 성립하는 불변식으로 기술했으나,
    BR-31/BR-32(고정 시각을 밀지 않고 경고만 부착)와 함께 두면 성립하지 않는다.
    정확한 불변식은 "FIXED_TIME_CONFLICT 경고가 없는 구간에서만 단조 증가" 이다.
    """
    items, matrix, mode = scenario
    result = timeline.compute(
        items, matrix, day=DAY, day_start=DAY_START, day_end=DAY_END, default_mode=mode
    )

    for item in result:
        assert item.arrival_at is not None and item.departure_at is not None
        assert item.arrival_at <= item.departure_at

    for prev, nxt in zip(result, result[1:], strict=False):
        conflicted = any(w.type is WarningType.FIXED_TIME_CONFLICT for w in nxt.warnings)
        if not conflicted:
            assert prev.departure_at <= nxt.arrival_at


@given(_scenario())
def test_p04_fixed_time_is_never_moved(scenario) -> None:
    """P-04 고정 시각 항목의 도착 시각은 항상 fixed_time 과 일치 (BR-31)."""
    items, matrix, mode = scenario
    result = timeline.compute(
        items, matrix, day=DAY, day_start=DAY_START, day_end=DAY_END, default_mode=mode
    )
    for original, computed in zip(items, result, strict=True):
        if original.time_fixed and original.fixed_time is not None:
            local = computed.arrival_at.astimezone(timeline.KST)  # type: ignore[union-attr]
            assert local.time() == original.fixed_time


@given(_scenario())
def test_p05_durations_are_non_negative(scenario) -> None:
    """P-05 체류시간 >= 1분, 이동시간 >= 0."""
    items, matrix, mode = scenario
    result = timeline.compute(
        items, matrix, day=DAY, day_start=DAY_START, day_end=DAY_END, default_mode=mode
    )
    for item in result:
        assert item.stay_minutes >= 1
        assert (item.departure_at - item.arrival_at).total_seconds() >= 60  # type: ignore[operator]
    for leg in matrix.legs():
        assert leg.duration_sec >= 0
        assert leg.distance_m >= 0
