"""C7~C11 클라이언트 인터페이스와 전송 DTO.

근거:
    DD-2   외부 API 는 Protocol + 실제 구현 + 목 구현 3중 구조
    DD-22  **DirectionsClient 에 대중교통·도보 메서드를 정의하지 않는다.**
           네이버가 제공하지 않는 기능을 인터페이스에 두면 호출자가
           존재한다고 오해한다 (CON-1)
    BR-08  LLM 클라이언트는 전송만 담당. 프롬프트 구성·스키마 검증은 C22 책임
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from app.domain.models import Coordinate


# ---------------------------------------------------------------------------
# 전송 DTO
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class SearchedPlace:
    """네이버 지역검색 결과 1건 (정제 후).

    `title` 의 `<b>` 강조 태그는 이미 제거되어 있고(BR-14),
    좌표는 WGS84 로 변환되어 국내 범위 검증을 통과한 값이다(BR-15).
    """

    name: str
    coordinate: Coordinate
    category_raw: str | None = None
    road_address: str | None = None
    address: str | None = None
    phone: str | None = None
    link: str | None = None


@dataclass(frozen=True, slots=True)
class BlogPost:
    title: str
    link: str
    blogger_name: str | None = None
    post_date: str | None = None
    description: str = ""


@dataclass(frozen=True, slots=True)
class ImageRef:
    thumbnail_url: str
    link: str
    source_title: str = ""


@dataclass(frozen=True, slots=True)
class CarRoute:
    """NCP Directions 5 결과 — **자동차 경로 전용** (CON-1)."""

    duration_sec: int
    distance_m: int
    path: tuple[Coordinate, ...] = ()


@dataclass(frozen=True, slots=True)
class LlmResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None


# ---------------------------------------------------------------------------
# 클라이언트 인터페이스
# ---------------------------------------------------------------------------
@runtime_checkable
class LocalSearchClient(Protocol):
    """네이버 지역검색 (C7) — 장소 그라운딩의 유일한 진실 공급원 (FR-3)."""

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        """지역 검색. `display` 는 API 상한 5 를 넘을 수 없다 (CON-2)."""
        ...


@runtime_checkable
class ContentSearchClient(Protocol):
    """네이버 블로그·이미지 검색 (C8) — 추천 콘텐츠 근거 (FR-20, FR-21)."""

    async def search_blogs(self, query: str, *, limit: int = 10) -> list[BlogPost]: ...

    async def search_images(self, query: str, *, limit: int = 6) -> list[ImageRef]: ...


@runtime_checkable
class DirectionsClient(Protocol):
    """NCP Directions (C9).

    🔴 **대중교통·도보 메서드가 의도적으로 없다** (DD-22, CON-1).
       도보는 C17 이 근사하고, 대중교통은 `nmap://` 딥링크로 위임한다.
    """

    async def route_car(self, origin: Coordinate, destination: Coordinate) -> CarRoute: ...


@runtime_checkable
class GeocodingClient(Protocol):
    """NCP Geocoding / Reverse Geocoding (C10)."""

    async def geocode(self, address: str) -> Coordinate | None: ...

    async def reverse_geocode(self, coordinate: Coordinate) -> str | None: ...


@runtime_checkable
class LlmClient(Protocol):
    """Claude API (C11). 전송만 담당한다 (BR-08 관심사 분리)."""

    async def complete(
        self, *, system: str, user: str, max_tokens: int, tool_schema: dict | None = None
    ) -> LlmResponse: ...


@dataclass(frozen=True, slots=True)
class ClientBundle:
    """C13 ClientFactory 가 조립해 반환하는 묶음."""

    local_search: LocalSearchClient
    content_search: ContentSearchClient
    directions: DirectionsClient
    geocoding: GeocodingClient
    llm: LlmClient
