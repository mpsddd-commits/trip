"""C18 RouteOptimizer — 일자별 방문 순서 최적화.

근거:
    BR-19   time_fixed / anchor_start / anchor_end / fixed_item_ids 는 위치 고정
    BR-20   목적함수는 **총 이동시간 단독** (거리·비용·시간대 적합도 미포함)
    BR-21   LLM preferred_time_slot 은 최적화에 사용하지 않는다
    BR-22   종료 조건 3중 — 개선 없는 반복 50 / 총 반복 1000 / 경과 200ms
    BR-23   n <= 8 이면 완전탐색(brute_force) 사용 — PBT 오라클과 동일 경로
    P-06~P-10  집합 보존 / 고정 위치 불변 / 비악화 / 오라클 일치 / 결정성
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import permutations

from app.domain.matrix import DistanceMatrix
from app.domain.models import ItineraryItem, OptimizeConstraints, TravelMode

BRUTE_FORCE_MAX_N = 8


@dataclass(frozen=True, slots=True)
class OptimizeLimits:
    """BR-22 종료 조건.

    `time_limit_ms=None` 이면 시계를 보지 않는다. PBT(P-10 결정성)는 이 모드로
    실행한다 — 벽시계에 의존하면 동일 입력에도 결과가 달라질 수 있기 때문이다.
    """

    no_improve_limit: int = 50
    max_iter: int = 1000
    time_limit_ms: int | None = 200


DEFAULT_LIMITS = OptimizeLimits()
DETERMINISTIC_LIMITS = OptimizeLimits(time_limit_ms=None)


def _fixed_positions(
    items: Sequence[ItineraryItem], constraints: OptimizeConstraints
) -> frozenset[int]:
    """재배열 대상에서 제외할 인덱스 집합 (BR-19)."""
    fixed: set[int] = set()
    for index, item in enumerate(items):
        if item.time_fixed or item.item_id in constraints.fixed_item_ids:
            fixed.add(index)
        if constraints.anchor_start is not None and item.item_id == constraints.anchor_start:
            fixed.add(index)
        if constraints.anchor_end is not None and item.item_id == constraints.anchor_end:
            fixed.add(index)
    return frozenset(fixed)


def _apply_order(items: Sequence[ItineraryItem], order: Sequence[int]) -> list[ItineraryItem]:
    from dataclasses import replace

    return [replace(items[src], position=pos) for pos, src in enumerate(order)]


def _nearest_neighbour(
    movable: Sequence[int],
    matrix: DistanceMatrix,
    mode: TravelMode,
    start_from: int | None,
) -> list[int]:
    """최근접 이웃 초기해. 동점이면 원래 인덱스가 작은 쪽을 택해 결정성을 보장한다."""
    remaining = list(movable)
    if not remaining:
        return []
    if start_from is None:
        current = remaining.pop(0)
    else:
        current = start_from
    route = [current] if start_from is None else []
    while remaining:
        nxt = min(remaining, key=lambda cand: (matrix.duration(current, cand, mode), cand))
        remaining.remove(nxt)
        route.append(nxt)
        current = nxt
    return route


def _two_opt(
    order: list[int],
    matrix: DistanceMatrix,
    mode: TravelMode,
    fixed: frozenset[int],
    limits: OptimizeLimits,
    clock: Callable[[], float],
) -> list[int]:
    """2-opt 개선. 고정 위치를 움직이는 뒤집기는 폐기한다 (BR-19, BR-22)."""
    best = list(order)
    best_cost = matrix.total(best, mode)
    started = clock()
    iterations = 0
    no_improve = 0
    n = len(best)

    while iterations < limits.max_iter and no_improve < limits.no_improve_limit:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # 고정 위치가 포함된 구간은 뒤집지 않는다.
                if any(pos in fixed for pos in range(i, j + 1)):
                    continue
                candidate = best[:i] + best[i : j + 1][::-1] + best[j + 1 :]
                cost = matrix.total(candidate, mode)
                if cost < best_cost:
                    best, best_cost = candidate, cost
                    improved = True
            iterations += 1
            if iterations >= limits.max_iter:
                break
            if limits.time_limit_ms is not None:
                if (clock() - started) * 1000.0 >= limits.time_limit_ms:
                    return best
        no_improve = 0 if improved else no_improve + 1
        if not improved:
            break
    return best


def brute_force(
    items: Sequence[ItineraryItem],
    matrix: DistanceMatrix,
    mode: TravelMode,
    constraints: OptimizeConstraints | None = None,
) -> list[ItineraryItem]:
    """완전탐색 참조 구현 (BR-23).

    n <= BRUTE_FORCE_MAX_N 에서만 호출한다. PBT P-09 의 오라클이자
    실제 최적화 경로이기도 하다 — 두 구현이 갈라지지 않도록 하나만 유지한다.
    """
    if len(items) <= 1:
        return list(items)
    constraints = constraints or OptimizeConstraints()
    fixed = _fixed_positions(items, constraints)
    indices = list(range(len(items)))
    movable = [i for i in indices if i not in fixed]

    best_order: list[int] | None = None
    best_cost: int | None = None
    for perm in permutations(movable):
        order: list[int] = []
        it = iter(perm)
        for pos in indices:
            order.append(pos if pos in fixed else next(it))
        cost = matrix.total(order, mode)
        if best_cost is None or cost < best_cost:
            best_cost, best_order = cost, order
    return _apply_order(items, best_order or indices)


def optimize(
    items: Sequence[ItineraryItem],
    matrix: DistanceMatrix,
    mode: TravelMode,
    constraints: OptimizeConstraints | None = None,
    limits: OptimizeLimits = DEFAULT_LIMITS,
    clock: Callable[[], float] = time.monotonic,
) -> list[ItineraryItem]:
    """방문 순서를 최적화한다.

    항상 유효한 순서를 반환하며, 결과의 총 이동시간은 입력보다 크지 않다 (P-08).
    """
    # 🔴 n == 2 를 여기서 잘라내면 안 된다.
    #    이동 시간 행렬은 **비대칭**이다 (일방통행·대중교통 방향별 배차).
    #    A→B 와 B→A 가 다르므로 두 항목뿐이어도 뒤집는 편이 빠를 수 있다.
    #    이전 구현은 `len(items) <= 2` 에서 입력 순서를 그대로 돌려주어
    #    2개짜리 하루가 **절대 재정렬되지 않았다.** P-08(비악화)은 만족하므로
    #    조용히 최적이 아닌 답을 냈고, PBT 오라클 비교(P-09)가 이를 잡았다.
    if len(items) <= 1:
        return _apply_order(items, list(range(len(items))))

    constraints = constraints or OptimizeConstraints()

    if len(items) <= BRUTE_FORCE_MAX_N:
        return brute_force(items, matrix, mode, constraints)

    indices = list(range(len(items)))
    fixed = _fixed_positions(items, constraints)
    movable = [i for i in indices if i not in fixed]

    # 초기해: 고정 위치는 자리를 지키고 가변 항목만 최근접 이웃으로 재배열
    heuristic = _nearest_neighbour(movable, matrix, mode, start_from=None)
    seeded: list[int] = []
    it = iter(heuristic)
    for pos in indices:
        seeded.append(pos if pos in fixed else next(it))

    improved = _two_opt(seeded, matrix, mode, fixed, limits, clock)

    # P-08 — 어떤 경우에도 입력보다 나빠지지 않는다.
    base_cost = matrix.total(indices, mode)
    candidates = [(matrix.total(improved, mode), improved), (base_cost, indices)]
    _, winner = min(candidates, key=lambda pair: pair[0])
    return _apply_order(items, winner)
