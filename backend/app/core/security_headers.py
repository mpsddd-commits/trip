"""C3 SecurityHeaders — HTTP 보안 헤더 미들웨어.

근거:
    SEC-04  CSP / X-Content-Type-Options / X-Frame-Options / Referrer-Policy 필수
    CA-4    HSTS 는 HTTPS 요청에만 부여 (로컬 루프백 HTTP 예외)
    SEP-1 / nfr-design §4.1  CSP 기준선

⚠️ 미확정 (code-generation-plan §6-3):
    CSP 의 지도 SDK 허용 도메인은 **Build & Test 에서 실측으로 확정**한다.
    아래 값은 설계 기준선이며, 실제 SDK 로딩 시 위반이 발생하면 이 상수만 수정한다.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# --- CSP 기준선 (nfr-design/nfr-design-patterns.md §4.1) -------------------
# unsafe-inline 예외 문서화 (SEC-04 검증 요건):
#   style-src 에만 허용한다. 네이버 지도 SDK 가 마커·컨트롤에 인라인 스타일을
#   주입하므로 제거하면 지도가 깨진다.
#   script-src 에는 절대 허용하지 않으며 unsafe-eval 도 사용하지 않는다.
#   img-src 의 https: 는 지도 타일과 이미지 검색 결과의 호스트가 고정적이지 않기
#   때문이며, 스크립트 실행 권한이 아니므로 위험도가 낮다.
CSP_DIRECTIVES: tuple[str, ...] = (
    "default-src 'self'",
    "script-src 'self' https://oapi.map.naver.com",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https:",
    "connect-src 'self' https://*.map.naver.com",
    "font-src 'self' data:",
    "object-src 'none'",
    "base-uri 'self'",
    "frame-ancestors 'none'",
)

CSP_VALUE = "; ".join(CSP_DIRECTIVES)
HSTS_VALUE = "max-age=31536000; includeSubDomains"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        response: Response = await call_next(request)

        response.headers.setdefault("Content-Security-Policy", CSP_VALUE)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # CA-4 — 평문 HTTP 로 HSTS 를 보내면 의미가 없고 오해를 부른다.
        if _is_https(request):
            response.headers.setdefault("Strict-Transport-Security", HSTS_VALUE)

        return response


def _is_https(request: Request) -> bool:
    if request.url.scheme == "https":
        return True
    # 리버스 프록시 뒤에 놓이는 운영 배포(CON-5)를 대비한 판정
    return request.headers.get("x-forwarded-proto", "").lower() == "https"
