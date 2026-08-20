"""런타임 설정 라우터 — 개정 A-1.

근거:
    u2 Functional Design Q4=A / `u2-trip-web/functional-design/domain-entities.md` §5
        지도 SDK 키를 프론트에 전달할 경로가 없어 추가한다.
        빌드 시 주입(`VITE_`) 방식은 키를 바꿀 때마다 **이미지 재빌드**가 필요해
        `.env` 수정만으로 반영되지 않는다 — README 의 기동 절차와 어긋나는 함정.

    WBR-10  폼 상한을 서버가 내려준다 (프론트 하드코딩 방지)
    WBR-30  데모 모드 배너의 데이터 원천
    SEC-11  🔴 **검색 API 키와 LLM 키는 포함하지 않는다**
    CON-3   `map_client_key` 는 구조상 브라우저 노출. 도메인 화이트리스트로 방어
    ND-14   외부 API 를 호출하지 않는다
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import ContainerDep, rate_limit
from app.api.schemas import LimitsOut, RuntimeConfigOut
from app.core.enums import EndpointTier

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/config", response_model=RuntimeConfigOut, dependencies=[rate_limit(EndpointTier.CHEAP)])
async def get_runtime_config(container: ContainerDep) -> RuntimeConfigOut:
    """프론트가 부팅 시 1회 조회하는 런타임 설정 (WBR-32).

    외부 API 를 호출하지 않으므로 쿼터를 소모하지 않는다.
    """
    config = container.config
    return RuntimeConfigOut(
        # CON-3 — 지도 SDK 는 브라우저에서 직접 네이버 서버와 통신하므로 키가 필요하다.
        map_client_key=config.ncp_map_client_key,
        # FR-33 — 어떤 기능이 데모 데이터인지 프론트가 배너로 알린다.
        modes=container.factory.active_modes(),
        limits=LimitsOut(
            max_trip_days=config.max_trip_days,
            max_items_per_day=config.max_items_per_day,
            max_items_per_trip=config.max_items_per_trip,
        ),
    )
