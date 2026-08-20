"""C24 TravelMatrixService — 구간별 이동시간·경로 확보.

근거:
    FR-10   이동수단별 소요시간 산출
    BR-26   Directions 실패 시 하버사인 폴백 + `is_estimate=True`
    BR-28   🔴 **Directions 호출을 O(n) 으로 유지한다.**
            최적화 탐색용 비인접 쌍은 하버사인으로 채우고,
            순서 확정 후 **새로 인접해진 쌍만** 실호출한다
    BR-29   동일 구간·수단 결과는 캐시된다 (C12 소관)
    BR-30   항목 이동수단이 없으면 여행 기본값

경계: 계산식은 domain(C17)에, **호출과 조립만** 이 서비스에 둔다.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.clients.circuit import CircuitOpenError
from app.clients.protocols import DirectionsClient
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger
from app.domain.estimator import EstimatorParams, estimate, estimate_car_fallback
from app.domain.matrix import DistanceMatrix
from app.domain.models import LegSource, Place, TravelLeg, TravelMode

logger = get_logger(__name__)


class TravelMatrixService:
    def __init__(
        self,
        directions: DirectionsClient,
        *,
        params: EstimatorParams | None = None,
        parallelism: int = 5,
    ) -> None:
        self._directions = directions
        self._params = params or EstimatorParams()
        self._parallelism = parallelism
        self.directions_calls = 0  # 관측·테스트용 (BR-28 검증)

    # ------------------------------------------------------------------
    async def build_matrix(
        self, places: Sequence[Place], mode: TravelMode, *, order: Sequence[int] | None = None
    ) -> DistanceMatrix:
        """행렬을 조립한다.

        - `order` 의 인접 쌍만 실제 소스(자동차=Directions)로 채운다 — **O(n)**
        - 나머지 모든 쌍은 하버사인 근사로 채운다 (최적화 탐색 전용)
        """
        count = len(places)
        if count < 2:
            return DistanceMatrix()

        sequence = list(order) if order is not None else list(range(count))
        adjacent = {(sequence[i], sequence[i + 1]) for i in range(len(sequence) - 1)}

        legs: list[TravelLeg] = []

        # 1) 비인접 쌍 — 외부 호출 없이 근사로 채운다 (BR-28)
        for i in range(count):
            for j in range(count):
                if i == j or (i, j) in adjacent:
                    continue
                legs.append(
                    estimate(mode, places[i].coordinate, places[j].coordinate, i, j, self._params)
                )

        # 2) 인접 쌍 — 실제 소스 (SP-3 제한 동시성)
        semaphore = asyncio.Semaphore(self._parallelism)
        tasks = [
            self._leg_for(semaphore, places, i, j, mode) for i, j in sorted(adjacent)
        ]
        legs.extend(await asyncio.gather(*tasks))

        return DistanceMatrix.from_legs(legs)

    async def refresh_adjacent(
        self,
        places: Sequence[Place],
        order: Sequence[int],
        mode: TravelMode,
        base: DistanceMatrix,
    ) -> DistanceMatrix:
        """BR-28 — 순서 확정 후 **새로 인접해진 쌍만** 실호출로 갱신한다."""
        semaphore = asyncio.Semaphore(self._parallelism)
        pairs = [(order[i], order[i + 1]) for i in range(len(order) - 1)]
        stale = [
            (i, j)
            for i, j in pairs
            if (leg := base.get(i, j, mode)) is None or leg.source is not LegSource.DIRECTIONS_API
        ]
        if not stale or mode is not TravelMode.CAR:
            # 자동차가 아니면 근사가 최종값이다 (CON-1) — 추가 호출이 무의미하다.
            return base

        refreshed = await asyncio.gather(
            *[self._leg_for(semaphore, places, i, j, mode) for i, j in stale]
        )
        merged = {(leg.from_index, leg.to_index, leg.mode): leg for leg in base.legs()}
        for leg in refreshed:
            merged[(leg.from_index, leg.to_index, leg.mode)] = leg
        return DistanceMatrix.from_legs(merged.values())

    async def recompute_leg(
        self, places: Sequence[Place], from_index: int, to_index: int, mode: TravelMode
    ) -> TravelLeg:
        """FR-11 — 단일 구간 재계산 (이동수단 변경 시)."""
        semaphore = asyncio.Semaphore(1)
        return await self._leg_for(semaphore, places, from_index, to_index, mode)

    # ------------------------------------------------------------------
    async def _leg_for(
        self,
        semaphore: asyncio.Semaphore,
        places: Sequence[Place],
        i: int,
        j: int,
        mode: TravelMode,
    ) -> TravelLeg:
        origin, destination = places[i].coordinate, places[j].coordinate

        # 도보·대중교통은 외부 경로 API 가 없다 (CON-1). 근사가 최종값이다.
        if mode is not TravelMode.CAR:
            return estimate(mode, origin, destination, i, j, self._params)

        async with semaphore:
            try:
                self.directions_calls += 1
                route = await self._directions.route_car(origin, destination)
            except (ExternalServiceError, CircuitOpenError) as exc:
                # BR-26 / RP-3 — 근사 폴백. 파이프라인은 계속된다.
                logger.warning("Directions 실패로 근사 폴백", extra={"detail": str(exc)})
                return estimate_car_fallback(origin, destination, i, j, self._params)

        return TravelLeg(
            from_index=i,
            to_index=j,
            mode=TravelMode.CAR,
            duration_sec=route.duration_sec,
            distance_m=route.distance_m,
            source=LegSource.DIRECTIONS_API,
            is_estimate=False,
            path=route.path,
        )
