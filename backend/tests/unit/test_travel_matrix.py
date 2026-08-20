"""C24 TravelMatrixService 테스트 — BR-26, BR-28, CON-1.

가장 중요한 검증: **Directions 호출 수가 O(n) 인가** (BR-28).
"""

from __future__ import annotations

import uuid

import pytest

from app.clients.protocols import CarRoute
from app.core.errors import ExternalServiceError
from app.domain.models import Coordinate, LegSource, Place, PlaceCategory, PlaceSource, TravelMode
from app.services.travel_matrix import TravelMatrixService

BASE = Coordinate(35.1796, 129.0756)


class _CountingDirections:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls = 0
        self.fail = fail

    async def route_car(self, origin: Coordinate, destination: Coordinate) -> CarRoute:
        self.calls += 1
        if self.fail:
            raise ExternalServiceError("directions down")
        return CarRoute(duration_sec=600, distance_m=5000, path=(origin, destination))


def _places(n: int) -> list[Place]:
    return [
        Place(
            place_id=str(uuid.uuid4()),
            name=f"장소{i}",
            coordinate=Coordinate(lat=35.1 + i * 0.01, lng=129.0 + i * 0.01),
            category=PlaceCategory.OTHER,
            source=PlaceSource.MOCK,
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# BR-28 — 호출 수가 O(n)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n", [2, 5, 10, 15])
async def test_directions_calls_are_linear_not_quadratic(n: int) -> None:
    """🔴 순진한 구현은 n(n-1) 번 호출한다. 인접 쌍만 실호출해야 한다."""
    directions = _CountingDirections()
    service = TravelMatrixService(directions)
    await service.build_matrix(_places(n), TravelMode.CAR)

    assert directions.calls == n - 1  # 인접 쌍만
    assert directions.calls < n * (n - 1)  # 전수 호출이 아님


async def test_non_adjacent_pairs_are_filled_by_approximation() -> None:
    """최적화 탐색에 필요한 전체 쌍은 근사로 채운다 (외부 호출 없이)."""
    places = _places(4)
    directions = _CountingDirections()
    matrix = await TravelMatrixService(directions).build_matrix(places, TravelMode.CAR)

    far = matrix.get(0, 3, TravelMode.CAR)
    assert far is not None
    assert far.is_estimate is True
    assert far.source is LegSource.HAVERSINE_CAR_FALLBACK

    near = matrix.get(0, 1, TravelMode.CAR)
    assert near is not None
    assert near.source is LegSource.DIRECTIONS_API
    assert near.is_estimate is False


# ---------------------------------------------------------------------------
# CON-1 — 도보·대중교통은 외부 API 를 부르지 않는다
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode", [TravelMode.WALK, TravelMode.TRANSIT])
async def test_walk_and_transit_never_call_directions(mode: TravelMode) -> None:
    directions = _CountingDirections()
    matrix = await TravelMatrixService(directions).build_matrix(_places(5), mode)
    assert directions.calls == 0
    leg = matrix.get(0, 1, mode)
    assert leg is not None and leg.is_estimate is True


async def test_transit_legs_have_no_path() -> None:
    """BR-27 — 대중교통 구간은 실경로를 갖지 않는다."""
    matrix = await TravelMatrixService(_CountingDirections()).build_matrix(
        _places(3), TravelMode.TRANSIT
    )
    for leg in matrix.legs():
        assert leg.path == ()
        assert leg.is_estimate is True


# ---------------------------------------------------------------------------
# BR-26 — Directions 실패 시 근사 폴백
# ---------------------------------------------------------------------------
async def test_directions_failure_falls_back_to_approximation() -> None:
    directions = _CountingDirections(fail=True)
    matrix = await TravelMatrixService(directions).build_matrix(_places(3), TravelMode.CAR)

    leg = matrix.get(0, 1, TravelMode.CAR)
    assert leg is not None
    assert leg.source is LegSource.HAVERSINE_CAR_FALLBACK
    assert leg.is_estimate is True
    assert leg.duration_sec >= 300  # BR-26 최소 5분


async def test_refresh_adjacent_only_updates_new_pairs() -> None:
    """BR-28 — 순서 확정 후 **새로 인접해진 쌍만** 갱신한다."""
    places = _places(5)
    directions = _CountingDirections()
    service = TravelMatrixService(directions)

    matrix = await service.build_matrix(places, TravelMode.CAR)
    initial_calls = directions.calls  # 4

    # 순서를 뒤집으면 인접 쌍이 전부 바뀐다
    reversed_order = [4, 3, 2, 1, 0]
    await service.refresh_adjacent(places, reversed_order, TravelMode.CAR, matrix)

    assert directions.calls == initial_calls + 4  # 새 인접 쌍 4개만


async def test_refresh_is_noop_for_non_car_modes() -> None:
    """CON-1 — 도보·대중교통은 근사가 최종값이므로 갱신이 무의미하다."""
    places = _places(4)
    directions = _CountingDirections()
    service = TravelMatrixService(directions)
    matrix = await service.build_matrix(places, TravelMode.WALK)
    await service.refresh_adjacent(places, [3, 2, 1, 0], TravelMode.WALK, matrix)
    assert directions.calls == 0
