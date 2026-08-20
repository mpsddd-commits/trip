"""L1 CircuitBreaker — API 별 독립 서킷.

근거:
    RP-2 / ND-1
        연속 실패 5회 -> 60초 open -> half-open 1회 시도
        **4xx 와 쿼터 소진은 실패로 세지 않는다** (서비스 장애가 아니라 요청 문제)
    SEC-14  상태 전환을 보안 이벤트로 로깅

해결하는 문제:
    네이버·NCP 장애 시 그라운딩 15건이 각각 10초 타임아웃을 기다려
    파이프라인이 150초 지연되는 상황. 3~4회 실패 후 즉시 폴백으로 전환한다.

SP-5 전제: 상태는 인메모리다. 다중 인스턴스로 확장하면 인스턴스별로 분리된다.
"""

from __future__ import annotations

import threading
import time
from enum import StrEnum

from app.core.enums import ApiName
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """서킷이 열려 있어 호출하지 않았다. 호출자는 폴백(RP-3)으로 진행한다."""

    def __init__(self, api: ApiName) -> None:
        super().__init__(f"circuit open: {api.value}")
        self.api = api


class _ApiCircuit:
    def __init__(self, threshold: int, open_seconds: float) -> None:
        self.threshold = threshold
        self.open_seconds = open_seconds
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.opened_at = 0.0
        self._probe_in_flight = False


class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, open_seconds: float = 60.0) -> None:
        self.failure_threshold = failure_threshold
        self.open_seconds = open_seconds
        self._circuits: dict[ApiName, _ApiCircuit] = {}
        self._lock = threading.Lock()

    def _circuit(self, api: ApiName) -> _ApiCircuit:
        circuit = self._circuits.get(api)
        if circuit is None:
            circuit = _ApiCircuit(self.failure_threshold, self.open_seconds)
            self._circuits[api] = circuit
        return circuit

    def state_of(self, api: ApiName) -> CircuitState:
        with self._lock:
            return self._circuit(api).state

    def before_call(self, api: ApiName, *, now: float | None = None) -> None:
        """호출 직전 판정. 열려 있으면 CircuitOpenError 를 던진다."""
        current = time.monotonic() if now is None else now
        with self._lock:
            circuit = self._circuit(api)
            if circuit.state is CircuitState.CLOSED:
                return
            if circuit.state is CircuitState.OPEN:
                if current - circuit.opened_at < self.open_seconds:
                    raise CircuitOpenError(api)
                # 유예 시간이 지났다 — half-open 으로 전환해 1회만 허용한다.
                circuit.state = CircuitState.HALF_OPEN
                circuit._probe_in_flight = True
                return
            # HALF_OPEN — 탐침이 이미 나가 있으면 추가 호출을 막는다.
            if circuit._probe_in_flight:
                raise CircuitOpenError(api)
            circuit._probe_in_flight = True

    def record_success(self, api: ApiName) -> None:
        with self._lock:
            circuit = self._circuit(api)
            was_open = circuit.state is not CircuitState.CLOSED
            circuit.state = CircuitState.CLOSED
            circuit.failures = 0
            circuit._probe_in_flight = False
        if was_open:
            logger.info("circuit closed", extra={"api": api.value})

    def record_failure(self, api: ApiName, *, now: float | None = None) -> None:
        """장애성 실패만 전달한다. 4xx·쿼터 소진은 호출하지 않는다 (RP-2)."""
        current = time.monotonic() if now is None else now
        opened = False
        with self._lock:
            circuit = self._circuit(api)
            circuit._probe_in_flight = False
            circuit.failures += 1
            if circuit.state is CircuitState.HALF_OPEN or circuit.failures >= self.failure_threshold:
                if circuit.state is not CircuitState.OPEN:
                    opened = True
                circuit.state = CircuitState.OPEN
                circuit.opened_at = current
        if opened:
            logger.warning(
                "circuit opened",
                extra={"api": api.value, "open_seconds": self.open_seconds},
            )

    def snapshot(self) -> dict[str, str]:
        """`/api/health/ready` 노출용 (ND-14)."""
        with self._lock:
            return {api.value: circuit.state.value for api, circuit in self._circuits.items()}
