"""장소 검색·추천 콘텐츠·주변 추천 라우터.

근거: FR-6(5건 페이징), FR-20·21(추천 콘텐츠), FR-22(주변 추천)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import ContainerDep, rate_limit
from app.api.schemas import PagedPlacesOut, PlaceContentOut, SuggestionsOut
from app.core.enums import EndpointTier
from app.core.errors import NotFoundError
from app.domain.models import Coordinate

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get(
    "/search",
    response_model=PagedPlacesOut,  # A-2
    dependencies=[rate_limit(EndpointTier.EXTERNAL)],
)
async def search_places(
    container: ContainerDep,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    page: Annotated[int, Query(ge=1, le=20)] = 1,
) -> dict:
    """FR-6 — 지역검색은 1회 5건이 상한이라 `page` 로 이어 받는다 (CON-2)."""
    paged = await container.place_search.search(q, page=page)
    return paged.to_dict()


@router.get(
    "/content",
    response_model=PlaceContentOut,  # A-2
    dependencies=[rate_limit(EndpointTier.EXTERNAL)],
)
async def place_content(
    container: ContainerDep,
    trip_id: Annotated[str, Query(max_length=36)],
    item_id: Annotated[str, Query(max_length=36)],
) -> dict:
    """FR-20·21 — 추천 콘텐츠.

    BR-40 — 근거 블로그가 3건 미만이면 `highlights` 는 빈 목록이다.
    """
    view = await container.trips.get(trip_id)
    for items in view.days:
        for item in items:
            if item.item_id == item_id:
                content = await container.recommendation.content_for(
                    item.place, region=view.spec.destination
                )
                return content.to_dict()
    raise NotFoundError(f"item not found: {item_id}")


@router.get(
    "/suggestions",
    response_model=SuggestionsOut,  # A-2
    dependencies=[rate_limit(EndpointTier.EXTERNAL)],
)
async def suggestions(
    container: ContainerDep,
    trip_id: Annotated[str, Query(max_length=36)],
    day_index: Annotated[int, Query(ge=1, le=10)],
    keyword: Annotated[str, Query(min_length=1, max_length=50)] = "맛집",
    radius: Annotated[int, Query(ge=100, le=10_000)] = 1500,
) -> dict:
    """FR-22 — 주변 미포함 추천. 이미 담긴 장소는 제외한다."""
    view = await container.trips.get(trip_id)
    if not (1 <= day_index <= len(view.days)):
        raise NotFoundError(f"day not found: {day_index}")

    items = view.days[day_index - 1]
    if not items:
        return {"items": []}

    center = _centroid([item.place.coordinate for item in items])
    query = f"{view.spec.destination} {keyword}"
    places = await container.place_search.nearby_suggestions(
        center,
        keyword=query,
        radius_m=radius,
        exclude=[item.place.coordinate for item in items],
    )
    return {"items": [p.to_dict() for p in places]}


def _centroid(coordinates: list[Coordinate]) -> Coordinate:
    return Coordinate(
        lat=sum(c.lat for c in coordinates) / len(coordinates),
        lng=sum(c.lng for c in coordinates) / len(coordinates),
    )
