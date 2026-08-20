"""L5 AccessLog + 상관관계 ID 미들웨어.

근거:
    NFR-8   요청 상관관계 ID
    PP-5    처리시간 / 외부 호출 수 / 캐시 적중 기록, P95 목표 초과 시 WARN
    NFR-1   API 응답 P95 500ms (외부 API 대기 제외)
"""

from __future__ import annotations

import logging
import time
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.logging_config import get_logger, new_correlation_id, set_correlation_id

logger = get_logger(__name__)

# 요청 단위 계측 카운터. C6 BaseHttpClient / C12 CachingDecorator 가 증가시킨다.
_external_calls: ContextVar[int] = ContextVar("external_calls", default=0)
_cache_hits: ContextVar[int] = ContextVar("cache_hits", default=0)

SLOW_REQUEST_MS = 500.0  # NFR-1


def record_external_call() -> None:
    _external_calls.set(_external_calls.get() + 1)


def record_cache_hit() -> None:
    _cache_hits.set(_cache_hits.get() + 1)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """요청마다 상관관계 ID 를 생성하고 응답 헤더로 되돌려준다."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        incoming = request.headers.get("x-correlation-id")
        correlation_id = incoming if incoming and len(incoming) <= 64 else new_correlation_id()
        set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers["X-Correlation-Id"] = correlation_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        _external_calls.set(0)
        _cache_hits.set(0)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000.0
            external = _external_calls.get()
            # 외부 API 대기는 NFR-1 목표에서 제외한다.
            level = (
                logging.WARNING
                if duration_ms > SLOW_REQUEST_MS and external == 0
                else logging.INFO
            )
            logger.log(
                level,
                "request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status,
                    "duration_ms": round(duration_ms, 2),
                    "external_calls": external,
                    "cache_hits": _cache_hits.get(),
                },
            )
