"""C17 TravelTimeEstimator — 외부 경로 API 없이 이동시간을 근사한다.

근거:
    CON-1   네이버는 대중교통·도보 경로 API 를 제공하지 않는다
    BR-24   도보: 하버사인 x 1.3 / 4.5km/h, 최소 3분
    BR-25   대중교통: 하버사인 x 1.4 / 20km/h + 600초 대기, 최소 10분
    BR-26   자동차 폴백: 하버사인 x 1.4 / 30km/h, 최소 5분
    BR-27   대중교통은 항상 is_estimate=True, path 없음
    P-11~P-16  비음수 / 자기거리 0 / 대칭성 / 삼각부등식 / 최소시간

DD-16: 설정값은 import 하지 않고 EstimatorParams 로 주입받는다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain.models import Coordinate, LegSource, TravelLeg, TravelMode

EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True, slots=True)
class EstimatorParams:
    """BR-24 ~ BR-26 의 설정값. 기본값은 설계 확정치와 일치한다."""

    walk_detour: float = 1.3
    walk_speed_kmh: float = 4.5
    walk_min_sec: int = 180
    transit_detour: float = 1.4
    transit_speed_kmh: float = 20.0
    transit_wait_sec: int = 600
    transit_min_sec: int = 600
    car_fallback_detour: float = 1.4
    car_fallback_speed_kmh: float = 30.0
    car_min_sec: int = 300


DEFAULT_PARAMS = EstimatorParams()


def haversine_m(a: Coordinate, b: Coordinate) -> float:
    """두 좌표 사이의 대권 거리(m).

    P-12 haversine(a, a) == 0 / P-13 대칭성 / P-14 삼각부등식을 만족한다.
    """
    lat1, lng1 = math.radians(a.lat), math.radians(a.lng)
    lat2, lng2 = math.radians(b.lat), math.radians(b.lng)
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    # 부동소수 오차로 h 가 1 을 미세하게 넘는 경우를 막는다.
    h = min(1.0, max(0.0, h))
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def _duration_sec(distance_m: float, speed_kmh: float, minimum_sec: int, extra_sec: int = 0) -> int:
    speed_ms = speed_kmh * 1000.0 / 3600.0
    seconds = int(round(distance_m / speed_ms)) + extra_sec
    return max(minimum_sec, seconds)


def estimate_walk(
    a: Coordinate,
    b: Coordinate,
    from_index: int,
    to_index: int,
    params: EstimatorParams = DEFAULT_PARAMS,
) -> TravelLeg:
    """도보 근사 (BR-24)."""
    distance = haversine_m(a, b) * params.walk_detour
    return TravelLeg(
        from_index=from_index,
        to_index=to_index,
        mode=TravelMode.WALK,
        duration_sec=_duration_sec(distance, params.walk_speed_kmh, params.walk_min_sec),
        distance_m=int(round(distance)),
        source=LegSource.HAVERSINE_WALK,
        is_estimate=True,
    )


def estimate_transit(
    a: Coordinate,
    b: Coordinate,
    from_index: int,
    to_index: int,
    params: EstimatorParams = DEFAULT_PARAMS,
) -> TravelLeg:
    """대중교통 근사 (BR-25).

    ⚠️ 네이버가 대중교통 경로 API 를 제공하지 않으므로 이 값은 추정치다.
    `is_estimate=True` 가 항상 부착되며 UI 는 배지를 표시해야 한다 (BR-27, FR-12).
    """
    distance = haversine_m(a, b) * params.transit_detour
    return TravelLeg(
        from_index=from_index,
        to_index=to_index,
        mode=TravelMode.TRANSIT,
        duration_sec=_duration_sec(
            distance, params.transit_speed_kmh, params.transit_min_sec, params.transit_wait_sec
        ),
        distance_m=int(round(distance)),
        source=LegSource.HAVERSINE_TRANSIT,
        is_estimate=True,
    )


def estimate_car_fallback(
    a: Coordinate,
    b: Coordinate,
    from_index: int,
    to_index: int,
    params: EstimatorParams = DEFAULT_PARAMS,
) -> TravelLeg:
    """Directions 호출 실패 시의 자동차 폴백 (BR-26, NFR-3)."""
    distance = haversine_m(a, b) * params.car_fallback_detour
    return TravelLeg(
        from_index=from_index,
        to_index=to_index,
        mode=TravelMode.CAR,
        duration_sec=_duration_sec(
            distance, params.car_fallback_speed_kmh, params.car_min_sec
        ),
        distance_m=int(round(distance)),
        source=LegSource.HAVERSINE_CAR_FALLBACK,
        is_estimate=True,
    )


def estimate(
    mode: TravelMode,
    a: Coordinate,
    b: Coordinate,
    from_index: int,
    to_index: int,
    params: EstimatorParams = DEFAULT_PARAMS,
) -> TravelLeg:
    """이동수단에 맞는 근사 함수를 고른다."""
    if mode is TravelMode.WALK:
        return estimate_walk(a, b, from_index, to_index, params)
    if mode is TravelMode.TRANSIT:
        return estimate_transit(a, b, from_index, to_index, params)
    return estimate_car_fallback(a, b, from_index, to_index, params)
