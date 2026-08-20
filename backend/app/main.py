"""애플리케이션 진입점 — 미들웨어 9단계 조립과 수명 주기.

근거:
    LC-1 / ND-15  미들웨어 순서 (바깥 → 안쪽)
        (1) ErrorHandler → (2) CorrelationId → (3) AccessLog → (4) SecurityHeaders
        → (5) GZip → (6) CORS(개발 시) → (7) BodySizeLimit → (8) RateLimit
        → (9) Router + Schema
    RP-4          기동 시 고아 job 정리 / 종료 시 태스크 취소
    ID-4          uvicorn 워커는 **1개 고정** (Dockerfile CMD 참조)
    BR-58         사용자 노출 오류는 고정 문구 6종만

⚠️ 워커를 늘리면 서킷(L1)·IP 레이트 리밋(C4)·job 세마포어(L3)가 워커별로
   분리되어 **오류 없이 조용히 무력화**된다 (SP-5). 늘리지 말 것.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.deps import Container
from app.api.routers import ALL_ROUTERS
from app.api.static import CachingStaticFiles, build_spa_router
from app.core.access_log import AccessLogMiddleware, CorrelationIdMiddleware
from app.core.body_limit import BodySizeLimitMiddleware
from app.core.config import get_config
from app.core.enums import ErrorCode
from app.core.errors import DomainError, problem_details
from app.core.logging_config import configure_logging, get_correlation_id, get_logger
from app.core.security_headers import SecurityHeadersMiddleware

logger = get_logger(__name__)
PROBLEM_MEDIA_TYPE = "application/problem+json"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container: Container = app.state.container
    await container.startup()
    logger.info(
        "application started",
        extra={
            "bind_host": container.config.bind_host,
            "port": container.config.port,
            "modes": container.factory.active_modes(),
        },
    )
    try:
        yield
    finally:
        await container.shutdown()
        logger.info("application stopped")


def _problem_response(request: Request, code: ErrorCode) -> JSONResponse:
    status_code, body = problem_details(
        code, instance=request.url.path, correlation_id=get_correlation_id()
    )
    return JSONResponse(body, status_code=status_code, media_type=PROBLEM_MEDIA_TYPE)


class GlobalErrorMiddleware(BaseHTTPMiddleware):
    """(1) 가장 바깥 — 어떤 미들웨어에서 터져도 Problem Details 로 응답한다.

    SEC-09 / SEC-15 / BR-58 — 스택트레이스·내부 경로·예외 원문을 노출하지 않는다.
    """

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        try:
            return await call_next(request)
        except DomainError as exc:
            logger.warning(
                "domain error",
                extra={"code": exc.code.value, "detail": exc.internal_detail},
            )
            return _problem_response(request, exc.code)
        except Exception:  # noqa: BLE001
            logger.exception("unhandled error")
            return _problem_response(request, ErrorCode.INTERNAL_ERROR)


def create_app(container: Container | None = None) -> FastAPI:
    config = get_config()
    configure_logging(config.log_dir, config.log_level, config.audit_retention_days)

    app = FastAPI(
        title="trip API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None,  # SEC-09 — 샘플·문서 엔드포인트를 배포에 노출하지 않는다
        redoc_url=None,
        openapi_url="/api/openapi.json",  # UD-3 — 프론트 타입 생성의 원천
    )
    app.state.container = container or Container.build(config)

    # --- 미들웨어는 등록 역순으로 실행된다. LC-1 순서를 만들려면 역순으로 add 한다. ---
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=config.max_request_body_bytes)  # (7)
    origins = config.cors_origins()
    if origins:  # (6) — ND-12: 와일드카드 금지, 개발 시에만 명시 오리진
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
            allow_headers=["Content-Type", "X-Correlation-Id"],
        )
    app.add_middleware(GZipMiddleware, minimum_size=1024)  # (5)
    app.add_middleware(SecurityHeadersMiddleware)  # (4)
    app.add_middleware(AccessLogMiddleware)  # (3)
    app.add_middleware(CorrelationIdMiddleware)  # (2)
    app.add_middleware(GlobalErrorMiddleware)  # (1) 가장 바깥

    # --- 예외 핸들러 (라우터 내부에서 발생한 것) ---
    @app.exception_handler(DomainError)
    async def _domain_error(request: Request, exc: DomainError) -> JSONResponse:
        logger.warning("domain error", extra={"code": exc.code.value, "detail": exc.internal_detail})
        return _problem_response(request, exc.code)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # SEC-09 — 어떤 필드가 왜 틀렸는지는 로그에만 남긴다.
        logger.info("request validation failed", extra={"errors": str(exc.errors())[:500]})
        return _problem_response(request, ErrorCode.VALIDATION_ERROR)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error")
        return _problem_response(request, ErrorCode.INTERNAL_ERROR)

    # --- (9) 라우터 ---
    for router in ALL_ROUTERS:
        app.include_router(router)

    # --- L7 정적 자산 (UD-8) ---
    static_dir = Path(config.static_dir)
    if (static_dir / "assets").is_dir():
        app.mount(
            "/assets",
            CachingStaticFiles(directory=static_dir / "assets"),
            name="assets",
        )
    app.include_router(build_spa_router(static_dir))  # catch-all 은 마지막

    return app


# ⚠️ 모듈 수준에서 `app = create_app()` 을 두지 않는다.
#    그렇게 하면 `import app.main` 만으로 Container 가 만들어져
#    DB 파일 생성·마이그레이션·HTTP 클라이언트 풀 생성이 **import 부작용**으로 일어난다.
#    (OpenAPI 스키마를 뽑거나 테스트를 실행할 때 컨테이너가 이중 생성되는 것을 실측으로 확인했다.)
#    uvicorn 은 팩토리 모드로 기동한다:
#        uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8200 --workers 1
