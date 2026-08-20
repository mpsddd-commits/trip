"""C17 TravelTimeEstimator 속성 기반 테스트 — P-11 ~ P-16 (PBT-03 / PBT-R2)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.estimator import (
    DEFAULT_PARAMS,
    estimate,
    estimate_car_fallback,
    estimate_transit,
    estimate_walk,
    haversine_m,
)
from app.domain.models import TravelMode
from tests.property.generators import ANY_COORDINATE

pytestmark = pytest.mark.property

_MODES = st.sampled_from(list(TravelMode))


@given(ANY_COORDINATE, ANY_COORDINATE, _MODES)
def test_p11_results_are_non_negative(a, b, mode) -> None:
    """P-11 duration_sec >= 0, distance_m >= 0."""
    leg = estimate(mode, a, b, 0, 1)
    assert leg.duration_sec >= 0
    assert leg.distance_m >= 0


@given(ANY_COORDINATE)
def test_p12_self_distance_is_zero(a) -> None:
    """P-12 haversine(a, a) == 0."""
    assert haversine_m(a, a) == pytest.approx(0.0, abs=1e-6)


@given(ANY_COORDINATE, ANY_COORDINATE)
def test_p13_symmetry(a, b) -> None:
    """P-13 haversine(a, b) == haversine(b, a)."""
    assert haversine_m(a, b) == pytest.approx(haversine_m(b, a), rel=1e-9, abs=1e-6)


@given(ANY_COORDINATE, ANY_COORDINATE, ANY_COORDINATE)
def test_p14_triangle_inequality(a, b, c) -> None:
    """P-14 haversine(a, c) <= haversine(a, b) + haversine(b, c)."""
    direct = haversine_m(a, c)
    detour = haversine_m(a, b) + haversine_m(b, c)
    # 부동소수 오차 여유를 1mm 로 둔다.
    assert direct <= detour + 1e-3


@given(ANY_COORDINATE, ANY_COORDINATE)
def test_p15_transit_is_always_estimate(a, b) -> None:
    """P-15 대중교통 결과는 항상 is_estimate=True 이고 실경로가 없다 (BR-27, CON-1)."""
    leg = estimate_transit(a, b, 0, 1)
    assert leg.is_estimate is True
    assert leg.path == ()
    assert leg.mode is TravelMode.TRANSIT


@given(ANY_COORDINATE, ANY_COORDINATE)
def test_p16_minimum_durations(a, b) -> None:
    """P-16 최소 시간 보장 (BR-24 ~ BR-26)."""
    assert estimate_walk(a, b, 0, 1).duration_sec >= DEFAULT_PARAMS.walk_min_sec
    assert estimate_transit(a, b, 0, 1).duration_sec >= DEFAULT_PARAMS.transit_min_sec
    assert estimate_car_fallback(a, b, 0, 1).duration_sec >= DEFAULT_PARAMS.car_min_sec


@given(ANY_COORDINATE, ANY_COORDINATE, ANY_COORDINATE)
def test_monotonicity_with_distance(a, b, c) -> None:
    """보조 속성: 거리가 멀수록 도보 소요시간이 줄지 않는다 (최소시간 구간 제외)."""
    d_ab, d_ac = haversine_m(a, b), haversine_m(a, c)
    leg_ab = estimate_walk(a, b, 0, 1)
    leg_ac = estimate_walk(a, c, 0, 1)
    if d_ab <= d_ac:
        assert leg_ab.duration_sec <= leg_ac.duration_sec
