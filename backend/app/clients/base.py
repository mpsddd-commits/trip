"""C6 BaseHttpClient — 모든 외부 HTTP 호출의 공통 실행 정책.

근거:
    BR-47   연결 5초 / 읽기 10초 (LLM 120초), 지수 백오프 최대 3회,
            **4xx 는 재시도하지 않는다**
    SEC-01  TLS 1.2+ 강제 (https 스킴만 허용)
    RP-1    서킷 -> 세마포어 -> 타임아웃 -> 재시도 4겹
    ND-17   API 별 전역 세마포어
    SEC-15  모든 외부 호출에 명시적 예외 처리

호출 순서(§ nfr-design 외부 호출 파이프라인):
    쿼터 확인(C29) -> 캐시(C12) -> **서킷(L1) -> 세마포어(L2) -> 이 클라이언트**
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.clients.circuit import CircuitBreaker, CircuitOpenError
from app.clients.semaphore import ExternalSemaphore
from app.core.access_log import record_external_call
from app.core.enums import AuditEventType, ApiName
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_RETRY_BASE_DELAY = 0.5


class QuotaGate:
    """C29 QuotaService 주입 지점 (ND-8 — clients 가 services 구체 타입에 의존하지 않는다)."""

    def is_exhausted(self, api: ApiName) -> bool:  # pragma: no cover - 기본 구현
        return False

    def record(self, api: ApiName, *, error: bool = False) -> None:  # pragma: no cover
        return None


class BaseHttpClient:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        circuit: CircuitBreaker,
        semaphore: ExternalSemaphore,
        quota: QuotaGate | None = None,
        max_retries: int = 3,
    ) -> None:
        self._client = client
        self._circuit = circuit
        self._semaphore = semaphore
        self._quota = quota or QuotaGate()
        self._max_retries = max_retries

    async def request(
        self,
        api: ApiName,
        method: str,
        url: str,
        *,
        timeout: float,
        connect_timeout: float = 5.0,
        **kwargs: Any,
    ) -> httpx.Response:
        # SEC-01 — 평문 HTTP 로 외부를 호출하지 않는다.
        if not url.startswith("https://"):
            raise ExternalServiceError(f"non-TLS external URL rejected: {url}")

        # RP-1 [1] 서킷
        self._circuit.before_call(api)

        timeouts = httpx.Timeout(timeout, connect=connect_timeout)
        last_error: Exception | None = None

        # RP-1 [2] 세마포어
        async with self._semaphore.acquire(api):
            for attempt in range(self._max_retries + 1):
                try:
                    record_external_call()
                    response = await self._client.request(
                        method, url, timeout=timeouts, **kwargs
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    last_error = exc
                    self._quota.record(api, error=True)
                    if attempt >= self._max_retries:
                        break
                    await asyncio.sleep(_RETRY_BASE_DELAY * (2**attempt))
                    continue

                self._quota.record(api, error=response.is_error)

                if 400 <= response.status_code < 500:
                    # BR-47 — 4xx 는 재시도하지 않는다.
                    # RP-2 — 요청 문제이지 서비스 장애가 아니므로 서킷 실패로도 세지 않는다.
                    self._circuit.record_success(api)
                    if response.status_code in (401, 403):
                        logger.warning(
                            "external auth failed",
                            extra={"api": api.value, "event_type": AuditEventType.EXTERNAL_AUTH_FAILED.value},
                        )
                    raise ExternalServiceError(
                        f"{api.value} responded {response.status_code}",
                        status=response.status_code,
                    )

                if response.status_code >= 500:
                    last_error = ExternalServiceError(
                        f"{api.value} responded {response.status_code}"
                    )
                    if attempt >= self._max_retries:
                        break
                    await asyncio.sleep(_RETRY_BASE_DELAY * (2**attempt))
                    continue

                self._circuit.record_success(api)
                return response

        # 재시도를 모두 소진했다 — 장애성 실패로 기록한다.
        self._circuit.record_failure(api)
        logger.warning(
            "external call failed after retries",
            extra={"api": api.value, "attempts": self._max_retries + 1},
        )
        raise ExternalServiceError(f"{api.value} unavailable") from last_error


__all__ = ["BaseHttpClient", "CircuitOpenError", "QuotaGate"]
