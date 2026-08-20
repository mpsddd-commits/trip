"""C9 NcpDirectionsClient — NCP Directions 5 (자동차 경로 전용).

근거:
    CON-1   **네이버는 대중교통·도보 경로 API 를 제공하지 않는다.**
            이 클라이언트에 해당 메서드를 두지 않는다 (DD-22)
    FR-10   자동차 구간의 소요시간·거리·경로 좌표
    BR-26   호출 실패 시 C17 하버사인 폴백 (호출자 책임)

⚠️ 미확정 (code-generation-plan §6-4):
    NCP 는 API 게이트웨이 도메인과 인증 헤더 이름을 변경해 온 이력이 있다.
    엔드포인트·헤더를 아래 상수로 분리했으며 **Build & Test 에서 실호출로 확정**한다.
"""

from __future__ import annotations

import httpx

from app.clients.base import BaseHttpClient
from app.clients.protocols import CarRoute
from app.core.enums import ApiName
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger
from app.domain.models import Coordinate, CoordinateOutOfRangeError

logger = get_logger(__name__)

# ⚠️ Build & Test 검증 대상 상수
ENDPOINT = "https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving"
HEADER_KEY_ID = "X-NCP-APIGW-API-KEY-ID"
HEADER_KEY = "X-NCP-APIGW-API-KEY"


class NcpDirectionsClient:
    def __init__(
        self, http: BaseHttpClient, client_id: str, client_secret: str, *, read_timeout: float = 10.0
    ) -> None:
        self._http = http
        self._headers = {HEADER_KEY_ID: client_id, HEADER_KEY: client_secret}
        self._read_timeout = read_timeout

    async def route_car(self, origin: Coordinate, destination: Coordinate) -> CarRoute:
        response: httpx.Response = await self._http.request(
            ApiName.NCP_DIRECTIONS,
            "GET",
            ENDPOINT,
            headers=self._headers,
            params={
                # NCP 는 "경도,위도" 순서를 쓴다.
                "start": f"{origin.lng},{origin.lat}",
                "goal": f"{destination.lng},{destination.lat}",
                "option": "traoptimal",
            },
            timeout=self._read_timeout,
        )
        return self._parse(response.json())

    @staticmethod
    def _parse(payload: dict) -> CarRoute:
        routes = (payload.get("route") or {}).get("traoptimal") or []
        if not routes:
            raise ExternalServiceError("Directions 응답에 경로가 없습니다")

        route = routes[0]
        summary = route.get("summary", {})
        # NCP 는 소요시간을 밀리초로 준다.
        duration_ms = int(summary.get("duration", 0) or 0)
        distance_m = int(summary.get("distance", 0) or 0)

        path: list[Coordinate] = []
        for point in route.get("path", []):
            try:
                # path 는 [경도, 위도] 순서
                path.append(Coordinate(lat=float(point[1]), lng=float(point[0])))
            except (CoordinateOutOfRangeError, IndexError, TypeError, ValueError):
                # 경로 좌표 하나가 틀려도 전체를 버리지 않는다 (NFR-3).
                continue

        return CarRoute(
            duration_sec=max(0, duration_ms // 1000),
            distance_m=max(0, distance_m),
            path=tuple(path),
        )
