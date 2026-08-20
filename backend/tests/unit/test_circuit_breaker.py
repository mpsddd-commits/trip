"""L1 CircuitBreaker 단위 테스트 — RP-2 / ND-1."""

from __future__ import annotations

import pytest

from app.clients.circuit import CircuitBreaker, CircuitOpenError, CircuitState
from app.core.enums import ApiName

API = ApiName.NAVER_LOCAL


def test_starts_closed() -> None:
    assert CircuitBreaker().state_of(API) is CircuitState.CLOSED


def test_opens_after_threshold_failures() -> None:
    breaker = CircuitBreaker(failure_threshold=3, open_seconds=60.0)
    for _ in range(2):
        breaker.record_failure(API, now=0.0)
    assert breaker.state_of(API) is CircuitState.CLOSED
    breaker.record_failure(API, now=0.0)
    assert breaker.state_of(API) is CircuitState.OPEN


def test_open_circuit_blocks_calls() -> None:
    breaker = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    breaker.record_failure(API, now=0.0)
    with pytest.raises(CircuitOpenError):
        breaker.before_call(API, now=10.0)


def test_half_open_allows_single_probe() -> None:
    breaker = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    breaker.record_failure(API, now=0.0)

    breaker.before_call(API, now=61.0)  # 첫 탐침은 허용
    assert breaker.state_of(API) is CircuitState.HALF_OPEN

    with pytest.raises(CircuitOpenError):
        breaker.before_call(API, now=61.5)  # 탐침 진행 중에는 추가 호출 차단


def test_probe_success_closes_circuit() -> None:
    breaker = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    breaker.record_failure(API, now=0.0)
    breaker.before_call(API, now=61.0)
    breaker.record_success(API)
    assert breaker.state_of(API) is CircuitState.CLOSED
    breaker.before_call(API, now=62.0)  # 예외 없이 통과


def test_probe_failure_reopens_circuit() -> None:
    breaker = CircuitBreaker(failure_threshold=5, open_seconds=60.0)
    for _ in range(5):
        breaker.record_failure(API, now=0.0)
    breaker.before_call(API, now=61.0)
    breaker.record_failure(API, now=61.0)
    assert breaker.state_of(API) is CircuitState.OPEN
    with pytest.raises(CircuitOpenError):
        breaker.before_call(API, now=62.0)


def test_circuits_are_independent_per_api() -> None:
    """RP-2 — API 별로 독립이다. 하나가 죽어도 나머지는 계속 동작한다."""
    breaker = CircuitBreaker(failure_threshold=1, open_seconds=60.0)
    breaker.record_failure(ApiName.NCP_DIRECTIONS, now=0.0)
    assert breaker.state_of(ApiName.NCP_DIRECTIONS) is CircuitState.OPEN
    assert breaker.state_of(ApiName.NAVER_LOCAL) is CircuitState.CLOSED
    breaker.before_call(ApiName.NAVER_LOCAL, now=1.0)  # 예외 없음


def test_snapshot_reports_states() -> None:
    breaker = CircuitBreaker(failure_threshold=1)
    breaker.record_failure(API, now=0.0)
    assert breaker.snapshot()[API.value] == "open"
