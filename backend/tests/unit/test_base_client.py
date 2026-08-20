"""C6 BaseHttpClient 단위 테스트 — BR-47, SEC-01, RP-1.

httpx.MockTransport 로 네트워크 없이 검증한다 (NFR-10).
"""

from __future__ import annotations

import httpx
import pytest

from app.clients.base import BaseHttpClient, QuotaGate
from app.clients.circuit import CircuitBreaker, CircuitState
from app.clients.semaphore import ExternalSemaphore
from app.core.enums import ApiName
from app.core.errors import ExternalServiceError


class _CountingQuota(QuotaGate):
    def __init__(self) -> None:
        self.calls = 0
        self.errors = 0

    def is_exhausted(self, api: ApiName) -> bool:
        return False

    def record(self, api: ApiName, *, error: bool = False) -> None:
        self.calls += 1
        if error:
            self.errors += 1


def _client(handler, *, max_retries: int = 3, circuit: CircuitBreaker | None = None,
            quota: QuotaGate | None = None) -> BaseHttpClient:
    transport = httpx.MockTransport(handler)
    return BaseHttpClient(
        httpx.AsyncClient(transport=transport),
        circuit=circuit or CircuitBreaker(),
        semaphore=ExternalSemaphore(limit=5),
        quota=quota,
        max_retries=max_retries,
    )


async def test_successful_request_returns_response() -> None:
    http = _client(lambda request: httpx.Response(200, json={"ok": True}))
    response = await http.request(ApiName.NAVER_LOCAL, "GET", "https://example.invalid/x", timeout=1.0)
    assert response.json() == {"ok": True}


async def test_non_tls_url_is_rejected() -> None:
    """SEC-01 — 평문 HTTP 로 외부를 호출하지 않는다."""
    http = _client(lambda request: httpx.Response(200))
    with pytest.raises(ExternalServiceError):
        await http.request(ApiName.NAVER_LOCAL, "GET", "http://example.invalid/x", timeout=1.0)


async def test_4xx_is_not_retried() -> None:
    """BR-47 — 4xx 는 재시도하지 않는다."""
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(400, json={"error": "bad request"})

    http = _client(handler)
    with pytest.raises(ExternalServiceError):
        await http.request(ApiName.NAVER_LOCAL, "GET", "https://example.invalid/x", timeout=1.0)
    assert attempts["n"] == 1


async def test_4xx_does_not_open_circuit() -> None:
    """RP-2 — 4xx 는 요청 문제이지 서비스 장애가 아니다."""
    circuit = CircuitBreaker(failure_threshold=2)
    http = _client(lambda request: httpx.Response(404), circuit=circuit)

    for _ in range(5):
        with pytest.raises(ExternalServiceError):
            await http.request(ApiName.NAVER_LOCAL, "GET", "https://example.invalid/x", timeout=1.0)

    assert circuit.state_of(ApiName.NAVER_LOCAL) is CircuitState.CLOSED


async def test_5xx_is_retried_then_fails() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        return httpx.Response(503)

    http = _client(handler, max_retries=2)
    with pytest.raises(ExternalServiceError):
        await http.request(ApiName.NAVER_LOCAL, "GET", "https://example.invalid/x", timeout=1.0)
    assert attempts["n"] == 3  # 최초 1회 + 재시도 2회


async def test_transport_error_is_retried_and_counted() -> None:
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        raise httpx.ConnectError("boom", request=request)

    quota = _CountingQuota()
    http = _client(handler, max_retries=1, quota=quota)
    with pytest.raises(ExternalServiceError):
        await http.request(ApiName.NAVER_LOCAL, "GET", "https://example.invalid/x", timeout=1.0)
    assert attempts["n"] == 2
    assert quota.errors == 2  # 성공·실패 모두 계측한다


async def test_repeated_failures_open_the_circuit() -> None:
    """RP-2 — 장애성 실패가 쌓이면 서킷이 열린다."""
    circuit = CircuitBreaker(failure_threshold=2, open_seconds=60.0)
    http = _client(lambda request: httpx.Response(500), max_retries=0, circuit=circuit)

    for _ in range(2):
        with pytest.raises(ExternalServiceError):
            await http.request(ApiName.NCP_DIRECTIONS, "GET", "https://example.invalid/x", timeout=1.0)

    assert circuit.state_of(ApiName.NCP_DIRECTIONS) is CircuitState.OPEN

    # 열린 뒤에는 호출하지 않고 즉시 실패한다 (RP-3 폴백 전환 지점)
    from app.clients.circuit import CircuitOpenError

    with pytest.raises(CircuitOpenError):
        await http.request(ApiName.NCP_DIRECTIONS, "GET", "https://example.invalid/x", timeout=1.0)
