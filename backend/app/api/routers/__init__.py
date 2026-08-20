"""C32 ApiRouters — HTTP 엔드포인트.

🔴 BR-39 / SEC-08: **여행 목록을 반환하는 엔드포인트가 없다.**
   계정이 없는 구성에서 목록 API 는 열거 취약점이 된다.
   사용자의 여행 목록은 브라우저 로컬 저장소의 trip_id 집합으로 구성한다 (DD-21).
"""

from app.api.routers.config import router as config_router
from app.api.routers.export import router as export_router
from app.api.routers.generation import router as generation_router
from app.api.routers.health import router as health_router
from app.api.routers.places import router as places_router
from app.api.routers.share import router as share_router
from app.api.routers.trips import router as trips_router

ALL_ROUTERS = (
    trips_router,
    generation_router,
    places_router,
    share_router,
    export_router,
    config_router,  # 개정 A-1 — 런타임 설정 (u2 지도 키 전달)
    health_router,
)

__all__ = ["ALL_ROUTERS"]
