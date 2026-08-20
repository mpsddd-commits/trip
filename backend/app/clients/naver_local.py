"""C7 NaverLocalSearchClient — 네이버 지역검색.

근거:
    FR-3    **장소 그라운딩의 유일한 진실 공급원**
    FR-6    사용자 직접 검색 + 페이징
    CON-2   1회 최대 5건, 일 25,000회
    BR-14   `title` 의 HTML 강조 태그를 저장 전에 제거
    BR-15   좌표는 국내 범위 검증을 통과해야 한다

🔴 미확정 사항 (code-generation-plan §6-1):
    응답의 `mapx`/`mapy` 좌표계는 **Build & Test 에서 실응답으로 확정**한다.
    잘못 해석하면 지도상 전 지점이 어긋나므로, 변환을 아래 `to_wgs84()`
    **단 하나의 함수에 격리**했다. 실측 후 이 함수만 고치면 된다.
"""

from __future__ import annotations

import re

import httpx

from app.clients.base import BaseHttpClient
from app.clients.protocols import SearchedPlace
from app.core.enums import ApiName
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger
from app.domain.models import (
    LAT_MAX,
    LAT_MIN,
    LNG_MAX,
    LNG_MIN,
    Coordinate,
    CoordinateOutOfRangeError,
)

logger = get_logger(__name__)

ENDPOINT = "https://openapi.naver.com/v1/search/local.json"
MAX_DISPLAY = 5  # CON-2 — API 상한

_TAG = re.compile(r"<[^>]+>")
_ENTITIES = {
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#39;": "'",
    "&apos;": "'",
    "&nbsp;": " ",
}

# WGS84 를 정수로 표현할 때 쓰이는 배율 (경도 127.0 -> 1270000000)
_WGS84_SCALE = 1e7


class CoordinateConversionError(ExternalServiceError):
    """좌표 변환 결과가 국내 범위를 벗어났다.

    좌표계 가정이 틀렸다는 신호이므로 조용히 넘기지 않는다.
    """


def strip_tags(value: str) -> str:
    """BR-14 — `<b>` 등 강조 태그와 HTML 엔티티를 제거한다 (SEC-05)."""
    text = _TAG.sub("", value)
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    return text.strip()


def to_wgs84(mapx: str | int | float, mapy: str | int | float) -> Coordinate:
    """지역검색 좌표를 WGS84 로 변환한다.

    🔴 **미검증 가정**: 현재는 `mapx`=경도, `mapy`=위도이며 값이 정수형이면
       `1e7` 로 나눈 WGS84 라고 가정한다. 과거에는 KATECH(TM128) 계열이었고
       현재는 WGS84 정수 표현으로 알려져 있으나, **문서만으로 단정하지 않는다.**

    Build & Test 에서 실응답을 받아 확정하며, 가정이 틀리면 이 함수만 수정한다.
    변환 결과가 국내 범위를 벗어나면 `CoordinateConversionError` 를 던져
    잘못된 좌표가 조용히 저장되는 것을 막는다 (BR-15).
    """
    try:
        raw_lng = float(mapx)
        raw_lat = float(mapy)
    except (TypeError, ValueError) as exc:
        raise CoordinateConversionError(f"좌표 파싱 실패: mapx={mapx!r}, mapy={mapy!r}") from exc

    # 이미 소수 형태면 그대로, 정수 배율 표현이면 1e7 로 나눈다.
    lng = raw_lng / _WGS84_SCALE if abs(raw_lng) > 1_000 else raw_lng
    lat = raw_lat / _WGS84_SCALE if abs(raw_lat) > 1_000 else raw_lat

    if not (LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX):
        raise CoordinateConversionError(
            "좌표계 가정이 맞지 않습니다. Build & Test 에서 실응답으로 확정하세요. "
            f"raw=({mapx!r}, {mapy!r}) -> ({lat}, {lng})"
        )
    try:
        return Coordinate(lat=lat, lng=lng)
    except CoordinateOutOfRangeError as exc:  # pragma: no cover - 위 검사와 중복 방어
        raise CoordinateConversionError(str(exc)) from exc


class NaverLocalSearchClient:
    def __init__(self, http: BaseHttpClient, client_id: str, client_secret: str, *, read_timeout: float = 10.0) -> None:
        self._http = http
        self._headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        self._read_timeout = read_timeout

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        params = {
            "query": query,
            "display": min(display, MAX_DISPLAY),  # CON-2
            "start": max(1, start),
            "sort": "random",
        }
        response: httpx.Response = await self._http.request(
            ApiName.NAVER_LOCAL,
            "GET",
            ENDPOINT,
            headers=self._headers,
            params=params,
            timeout=self._read_timeout,
        )
        return self._parse(response.json())

    @staticmethod
    def _parse(payload: dict) -> list[SearchedPlace]:
        results: list[SearchedPlace] = []
        for item in payload.get("items", []):
            try:
                coordinate = to_wgs84(item.get("mapx"), item.get("mapy"))
            except CoordinateConversionError as exc:
                # 개별 항목의 좌표 오류가 검색 전체를 실패시키지 않는다 (NFR-3).
                # 다만 흔적은 남긴다 — 좌표계 가정이 틀린 신호일 수 있다.
                logger.warning("좌표 변환 실패로 항목을 건너뜁니다", extra={"detail": str(exc)})
                continue
            results.append(
                SearchedPlace(
                    name=strip_tags(item.get("title", "")),
                    coordinate=coordinate,
                    category_raw=item.get("category") or None,
                    road_address=item.get("roadAddress") or None,
                    address=item.get("address") or None,
                    phone=item.get("telephone") or None,
                    link=item.get("link") or None,
                )
            )
        return results
