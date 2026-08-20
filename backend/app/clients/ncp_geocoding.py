"""C10 NcpGeocodingClient — 주소 ↔ 좌표 변환.

⚠️ 미확정: 엔드포인트·헤더는 Build & Test 에서 실호출로 확정한다 (C9 와 동일 사유).
"""

from __future__ import annotations

import httpx

from app.clients.base import BaseHttpClient
from app.clients.ncp_directions import HEADER_KEY, HEADER_KEY_ID
from app.core.enums import ApiName
from app.core.logging_config import get_logger
from app.domain.models import Coordinate, CoordinateOutOfRangeError

logger = get_logger(__name__)

GEOCODE_ENDPOINT = "https://naveropenapi.apigw.ntruss.com/map-geocode/v2/geocode"
REVERSE_ENDPOINT = "https://naveropenapi.apigw.ntruss.com/map-reversegeocode/v2/gc"


class NcpGeocodingClient:
    def __init__(
        self, http: BaseHttpClient, client_id: str, client_secret: str, *, read_timeout: float = 10.0
    ) -> None:
        self._http = http
        self._headers = {HEADER_KEY_ID: client_id, HEADER_KEY: client_secret}
        self._read_timeout = read_timeout

    async def geocode(self, address: str) -> Coordinate | None:
        response: httpx.Response = await self._http.request(
            ApiName.NCP_GEOCODING,
            "GET",
            GEOCODE_ENDPOINT,
            headers=self._headers,
            params={"query": address},
            timeout=self._read_timeout,
        )
        addresses = response.json().get("addresses") or []
        if not addresses:
            return None
        first = addresses[0]
        try:
            return Coordinate(lat=float(first["y"]), lng=float(first["x"]))
        except (CoordinateOutOfRangeError, KeyError, TypeError, ValueError):
            logger.warning("지오코딩 좌표가 국내 범위를 벗어났습니다")
            return None

    async def reverse_geocode(self, coordinate: Coordinate) -> str | None:
        response: httpx.Response = await self._http.request(
            ApiName.NCP_GEOCODING,
            "GET",
            REVERSE_ENDPOINT,
            headers=self._headers,
            params={
                "coords": f"{coordinate.lng},{coordinate.lat}",
                "output": "json",
                "orders": "roadaddr,addr",
            },
            timeout=self._read_timeout,
        )
        results = response.json().get("results") or []
        if not results:
            return None
        region = results[0].get("region", {})
        parts = [
            region.get(f"area{i}", {}).get("name", "")
            for i in range(1, 5)
        ]
        land = results[0].get("land", {})
        if land.get("name"):
            parts.append(land["name"])
        if land.get("number1"):
            parts.append(land["number1"])
        joined = " ".join(p for p in parts if p).strip()
        return joined or None
