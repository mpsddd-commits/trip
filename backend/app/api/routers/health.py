"""헬스체크 라우터 — FR-34, ND-14.

🔴 **두 엔드포인트 모두 외부 API 를 호출하지 않는다.**
   컨테이너 헬스체크는 주기적으로 실행되므로, 여기서 지역검색을 부르면
   헬스체크만으로 일일 쿼터를 소모한다.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep, rate_limit
from app.api.schemas import HealthOut, ReadinessOut
from app.core.enums import EndpointTier
from app.core.logging_config import get_logger

router = APIRouter(prefix="/api/health", tags=["health"])
logger = get_logger(__name__)


@router.get("", response_model=HealthOut)
async def liveness() -> dict:
    """프로세스 응답 여부만 확인한다. Docker 헬스체크 대상 (ID-13)."""
    return {"status": "ok"}


@router.get(
    "/ready",
    response_model=ReadinessOut,  # A-2
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def readiness(container: ContainerDep) -> dict:
    """DB 접근 + 목 모드 현황 + 쿼터 + 서킷 상태.

    FR-33 — 프론트는 `modes` 를 보고 "데모 데이터" 배너를 띄운다.
    """
    database_ok = await _check_database(container)
    modes = container.factory.active_modes()
    return {
        "status": "ok" if database_ok else "degraded",
        "modes": modes,
        "quota": container.quota.usage_today(),
        "circuits": container.factory.circuit_snapshot(),
        "database": database_ok,
        # CON-3 — 지도 SDK 키는 프론트에 노출되므로 **설정 여부만** 알린다.
        "map_client_key_configured": bool(container.config.ncp_map_client_key),
    }


async def _check_database(container) -> bool:  # type: ignore[no-untyped-def]
    from sqlalchemy import text

    def _ping() -> bool:
        with container.database.session_scope() as session:
            session.execute(text("SELECT 1"))
        return True

    try:
        return await container.executor.run(_ping)
    except Exception:  # noqa: BLE001 - 헬스체크가 예외로 죽으면 안 된다
        logger.exception("database health check failed")
        return False
