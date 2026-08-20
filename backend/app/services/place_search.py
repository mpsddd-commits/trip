"""C26 PlaceSearchService — 사용자 직접 장소 검색과 주변 추천.

근거:
    FR-6    장소 검색 + **5건 제약 페이징** (CON-2)
    FR-22   주변 미포함 장소 추천
    BR-10   질의 구성
    BR-17   좌표 기준 중복 판정
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.clients.circuit import CircuitOpenError
from app.clients.protocols import LocalSearchClient
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger
from app.domain.categories import classify_category
from app.domain.estimator import haversine_m
from app.domain.models import Coordinate, Place, PlaceSource

logger = get_logger(__name__)

PAGE_SIZE = 5  # CON-2 — API 상한과 동일


@dataclass(frozen=True, slots=True)
class PagedPlaces:
    items: list[Place]
    page: int
    page_size: int
    has_more: bool

    def to_dict(self) -> dict:
        return {
            "items": [p.to_dict() for p in self.items],
            "page": self.page,
            "page_size": self.page_size,
            "has_more": self.has_more,
        }


class PlaceSearchService:
    def __init__(self, local_search: LocalSearchClient) -> None:
        self._search = local_search

    async def search(self, query: str, *, page: int = 1) -> PagedPlaces:
        """FR-6 — 지역검색은 1회 5건이 상한이므로 `start` 로 페이징한다."""
        page = max(1, page)
        start = (page - 1) * PAGE_SIZE + 1
        try:
            results = await self._search.search(query, start=start, display=PAGE_SIZE)
        except (ExternalServiceError, CircuitOpenError) as exc:
            logger.warning("장소 검색 실패", extra={"detail": str(exc)})
            return PagedPlaces(items=[], page=page, page_size=PAGE_SIZE, has_more=False)

        items = [
            Place(
                place_id=str(uuid.uuid4()),
                name=r.name,
                coordinate=r.coordinate,
                category=classify_category(r.category_raw),
                category_raw=r.category_raw,
                road_address=r.road_address,
                address=r.address,
                phone=r.phone,
                naver_link=r.link,
                source=PlaceSource.NAVER_LOCAL,
            )
            for r in results
        ]
        # 5건이 꽉 찼으면 다음 페이지가 있을 수 있다.
        return PagedPlaces(
            items=items, page=page, page_size=PAGE_SIZE, has_more=len(items) == PAGE_SIZE
        )

    async def nearby_suggestions(
        self,
        center: Coordinate,
        *,
        keyword: str,
        radius_m: int = 1500,
        exclude: list[Coordinate] | None = None,
    ) -> list[Place]:
        """FR-22 — 반경 내 후보에서 **이미 포함된 장소를 제외**한다."""
        paged = await self.search(keyword)
        excluded = exclude or []
        suggestions: list[Place] = []
        for place in paged.items:
            if haversine_m(center, place.coordinate) > radius_m:
                continue
            # BR-17 과 동일한 기준(약 1m)으로 중복 판정
            if any(haversine_m(place.coordinate, other) < 1.0 for other in excluded):
                continue
            suggestions.append(place)
        return suggestions
