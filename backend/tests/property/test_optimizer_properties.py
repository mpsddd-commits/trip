"""C18 RouteOptimizer 속성 기반 테스트 — P-06 ~ P-10 (PBT-03 / PBT-05 / PBT-R2 / PBT-R7)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.matrix import DistanceMatrix
from app.domain.models import OptimizeConstraints, TravelMode
from app.domain.optimizer import (
    BRUTE_FORCE_MAX_N,
    DETERMINISTIC_LIMITS,
    brute_force,
    optimize,
)
from tests.property.generators import full_matrix_legs, item_lists

pytestmark = pytest.mark.property


@st.composite
def _scenario(draw, *, min_size: int = 2, max_size: int = 12):
    items = draw(item_lists(min_size=min_size, max_size=max_size))
    mode = draw(st.sampled_from(list(TravelMode)))
    legs = draw(full_matrix_legs(len(items), mode))
    return items, DistanceMatrix.from_legs(legs), mode


@given(_scenario())
def test_p06_item_set_is_preserved(scenario) -> None:
    """P-06 결과 항목 집합 == 입력 항목 집합."""
    items, matrix, mode = scenario
    result = optimize(items, matrix, mode, limits=DETERMINISTIC_LIMITS)
    assert len(result) == len(items)
    assert sorted(i.item_id for i in result) == sorted(i.item_id for i in items)


@given(_scenario())
def test_p07_fixed_positions_are_stable(scenario) -> None:
    """P-07 고정 위치 항목의 인덱스 불변 (BR-19)."""
    items, matrix, mode = scenario
    result = optimize(items, matrix, mode, limits=DETERMINISTIC_LIMITS)
    for index, original in enumerate(items):
        if original.time_fixed:
            assert result[index].item_id == original.item_id


@given(_scenario())
def test_p08_never_worse_than_input(scenario) -> None:
    """P-08 total(결과) <= total(입력) — 비악화 (BR-20)."""
    items, matrix, mode = scenario
    result = optimize(items, matrix, mode, limits=DETERMINISTIC_LIMITS)

    id_to_index = {item.item_id: index for index, item in enumerate(items)}
    before = matrix.total(list(range(len(items))), mode)
    after = matrix.total([id_to_index[i.item_id] for i in result], mode)
    assert after <= before


@given(_scenario(min_size=2, max_size=BRUTE_FORCE_MAX_N))
def test_p09_matches_brute_force_oracle(scenario) -> None:
    """P-09 n <= 8 에서 완전탐색 오라클과 총 이동시간이 일치 (PBT-05)."""
    items, matrix, mode = scenario
    id_to_index = {item.item_id: index for index, item in enumerate(items)}

    optimized = optimize(items, matrix, mode, limits=DETERMINISTIC_LIMITS)
    oracle = brute_force(items, matrix, mode, OptimizeConstraints())

    cost_opt = matrix.total([id_to_index[i.item_id] for i in optimized], mode)
    cost_oracle = matrix.total([id_to_index[i.item_id] for i in oracle], mode)
    assert cost_opt == cost_oracle


@given(_scenario())
def test_p10_is_deterministic(scenario) -> None:
    """P-10 동일 입력에서 결과 동일.

    ⚠️ 시간 상한(BR-22)이 걸리면 벽시계에 의존해 결정성이 깨질 수 있으므로,
    이 속성은 DETERMINISTIC_LIMITS(시간 상한 비활성)에서만 주장한다.
    실제 서비스는 DEFAULT_LIMITS 를 쓰며 결정성을 요구하지 않는다.
    """
    items, matrix, mode = scenario
    first = optimize(items, matrix, mode, limits=DETERMINISTIC_LIMITS)
    second = optimize(items, matrix, mode, limits=DETERMINISTIC_LIMITS)
    assert [i.item_id for i in first] == [i.item_id for i in second]
