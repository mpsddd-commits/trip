"""L6 BodySizeLimit — 요청 본문 크기 상한 미들웨어.

근거:
    BR-05   요청 본문 크기 상한 1MB
    SEC-05  프레임워크 또는 게이트웨이 수준에서 본문 크기 제한
    LC-1    레이트 리밋 앞 단계 — 거대 본문을 먼저 잘라낸다
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.errors import ValidationError


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    raise ValidationError(
                        f"content-length {declared} exceeds limit {self.max_bytes}"
                    )
            except ValueError as exc:
                raise ValidationError("invalid content-length header") from exc
        return await call_next(request)
