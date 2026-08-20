"""여행 CRUD·항목 편집·순서 최적화 라우터.

근거: FR-4, FR-5, FR-7, FR-8, FR-9, FR-11, FR-13
      BR-39 — 목록 엔드포인트 없음
"""

from __future__ import annotations

import uuid
from dataclasses import replace

from fastapi import APIRouter, Response, status

from app.api.deps import ContainerDep, rate_limit
from app.api.schemas import (
    ItemCreate,
    ItemPatch,
    OpeningHoursIn,
    OptimizeIn,
    ReorderIn,
    TripMetaPatch,
    TripOut,
    TripSpecIn,
)
from app.core.enums import EndpointTier
from app.core.errors import NotFoundError, ValidationError
from app.domain.categories import classify_category, default_stay_minutes
from app.domain.models import (
    DayRule,
    ItineraryItem,
    OpeningHours,
    OptimizeConstraints,
    Place,
    PlaceSource,
)
from app.domain.optimizer import OptimizeLimits, optimize
from app.domain.timeline import compute as compute_timeline

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=TripOut,  # A-2 — 무타입 응답 제거
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def create_trip(payload: TripSpecIn, container: ContainerDep) -> dict:
    trip_id = await container.trips.create(payload.to_domain())
    view = await container.trips.get(trip_id)
    return view.to_dict()


@router.get("/{trip_id}", response_model=TripOut, dependencies=[rate_limit(EndpointTier.CHEAP)])
async def get_trip(trip_id: str, container: ContainerDep) -> dict:
    view = await container.trips.get(trip_id)
    return view.to_dict()


@router.patch("/{trip_id}", response_model=TripOut, dependencies=[rate_limit(EndpointTier.CHEAP)])
async def patch_trip(trip_id: str, payload: TripMetaPatch, container: ContainerDep) -> dict:
    view = await container.trips.get(trip_id)
    if payload.title is not None:
        spec = replace(view.spec, title=payload.title)
        await _rewrite(container, trip_id, view, spec=spec)
    return (await container.trips.get(trip_id)).to_dict()


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[rate_limit(EndpointTier.CHEAP)])
async def delete_trip(trip_id: str, container: ContainerDep) -> Response:
    await container.trips.delete(trip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# 항목 편집 (FR-5, FR-7, FR-11)
# ---------------------------------------------------------------------------
@router.post(
    "/{trip_id}/days/{day_index}/items",
    response_model=TripOut,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def add_item(
    trip_id: str, day_index: int, payload: ItemCreate, container: ContainerDep
) -> dict:
    view = await container.trips.get(trip_id)
    _check_day(view, day_index)

    category = classify_category(payload.category_raw)
    place = Place(
        place_id=str(uuid.uuid4()),
        name=payload.name,
        coordinate=payload.coordinate(),  # BR-15 검증은 Coordinate 가 수행
        category=category,
        category_raw=payload.category_raw,
        road_address=payload.road_address,
        address=payload.address,
        phone=payload.phone,
        source=PlaceSource.USER_MANUAL,
    )
    item = ItineraryItem(
        item_id=str(uuid.uuid4()),
        place=place,
        stay_minutes=payload.stay_minutes or default_stay_minutes(category),
        memo=payload.memo,
    )
    days = _days(view)
    days[day_index - 1].append(item)
    await _recompute_and_save(container, trip_id, view, days)
    return (await container.trips.get(trip_id)).to_dict()


@router.delete(
    "/{trip_id}/items/{item_id}",
    response_model=TripOut,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def remove_item(trip_id: str, item_id: str, container: ContainerDep) -> dict:
    view = await container.trips.get(trip_id)
    days = [[i for i in items if i.item_id != item_id] for items in _days(view)]
    await _recompute_and_save(container, trip_id, view, days)
    return (await container.trips.get(trip_id)).to_dict()


@router.patch(
    "/{trip_id}/items/{item_id}",
    response_model=TripOut,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def patch_item(
    trip_id: str, item_id: str, payload: ItemPatch, container: ContainerDep
) -> dict:
    view = await container.trips.get(trip_id)
    found = False
    days = _days(view)
    for items in days:
        for index, item in enumerate(items):
            if item.item_id != item_id:
                continue
            found = True
            items[index] = replace(
                item,
                stay_minutes=payload.stay_minutes or item.stay_minutes,
                memo=payload.memo if payload.memo is not None else item.memo,
                travel_mode=payload.travel_mode or item.travel_mode,
                time_fixed=payload.time_fixed if payload.time_fixed is not None else item.time_fixed,
                fixed_time=payload.fixed_time or item.fixed_time,
            )
    if not found:
        raise NotFoundError(f"item not found: {item_id}")
    await _recompute_and_save(container, trip_id, view, days)
    return (await container.trips.get(trip_id)).to_dict()


@router.put(
    "/{trip_id}/days/{day_index}/order",
    response_model=TripOut,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def reorder(
    trip_id: str, day_index: int, payload: ReorderIn, container: ContainerDep
) -> dict:
    view = await container.trips.get(trip_id)
    _check_day(view, day_index)
    days = _days(view)
    by_id = {item.item_id: item for item in days[day_index - 1]}
    if set(payload.item_ids) != set(by_id):
        # 순서 변경은 집합을 보존해야 한다 (P-06 과 같은 취지)
        raise ValidationError("order must contain exactly the items of that day")
    days[day_index - 1] = [by_id[item_id] for item_id in payload.item_ids]
    await _recompute_and_save(container, trip_id, view, days)
    return (await container.trips.get(trip_id)).to_dict()


@router.post(
    "/{trip_id}/days/{day_index}/optimize",
    response_model=TripOut,
    dependencies=[rate_limit(EndpointTier.EXTERNAL)],
)
async def optimize_day(
    trip_id: str, day_index: int, payload: OptimizeIn, container: ContainerDep
) -> dict:
    """FR-8 — 순서 최적화. 캐시가 적중하면 외부 호출 없이 끝난다 (BR-29)."""
    view = await container.trips.get(trip_id)
    _check_day(view, day_index)
    days = _days(view)
    items = days[day_index - 1]
    if len(items) < 3:
        return view.to_dict()

    mode = view.spec.default_travel_mode
    places = [item.place for item in items]
    matrix = await container.generation._matrix.build_matrix(places, mode)  # noqa: SLF001
    ordered = optimize(
        items,
        matrix,
        mode,
        OptimizeConstraints(anchor_start=payload.anchor_start, anchor_end=payload.anchor_end),
        limits=_limits(container),
    )
    days[day_index - 1] = ordered
    await _recompute_and_save(container, trip_id, view, days)
    return (await container.trips.get(trip_id)).to_dict()


# ---------------------------------------------------------------------------
# 영업시간 (FR-13 / BR-35 — 사용자 입력 전용)
# ---------------------------------------------------------------------------
@router.put(
    "/{trip_id}/items/{item_id}/opening-hours",
    response_model=TripOut,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def set_opening_hours(
    trip_id: str, item_id: str, payload: OpeningHoursIn, container: ContainerDep
) -> dict:
    """BR-35 — 영업시간은 **여기서만** 채워진다. 외부 API·LLM 경로는 없다."""
    view = await container.trips.get(trip_id)
    hours = OpeningHours(
        weekday_rules=tuple(
            DayRule(weekday=r.weekday, open=r.open, close=r.close, closed=r.closed)
            for r in payload.weekday_rules
        )
    )
    days = _days(view)
    found = False
    for items in days:
        for index, item in enumerate(items):
            if item.item_id == item_id:
                found = True
                items[index] = replace(item, place=replace(item.place, opening_hours=hours))
    if not found:
        raise NotFoundError(f"item not found: {item_id}")
    await _recompute_and_save(container, trip_id, view, days)
    return (await container.trips.get(trip_id)).to_dict()


# ---------------------------------------------------------------------------
# 내부 유틸
# ---------------------------------------------------------------------------
def _days(view) -> list[list[ItineraryItem]]:  # type: ignore[no-untyped-def]
    return [list(items) for items in view.days]


def _check_day(view, day_index: int) -> None:  # type: ignore[no-untyped-def]
    if not (1 <= day_index <= len(view.days)):
        raise NotFoundError(f"day not found: {day_index}")


def _limits(container: ContainerDep) -> OptimizeLimits:  # type: ignore[valid-type]
    config = container.config
    return OptimizeLimits(
        no_improve_limit=config.optimize_no_improve_limit,
        max_iter=config.optimize_max_iter,
        time_limit_ms=config.optimize_time_limit_ms,
    )


async def _recompute_and_save(container, trip_id, view, days) -> None:  # type: ignore[no-untyped-def]
    """FR-9 — 편집 후 타임라인을 다시 계산한다.

    BR-29 — 장소가 그대로면 캐시가 적중해 외부 호출이 발생하지 않는다.
    """
    from datetime import timedelta

    mode = view.spec.default_travel_mode
    recomputed: list[list[ItineraryItem]] = []
    for day_index, items in enumerate(days, start=1):
        if not items:
            recomputed.append([])
            continue
        places = [item.place for item in items]
        matrix = await container.generation._matrix.build_matrix(places, mode)  # noqa: SLF001
        recomputed.append(
            compute_timeline(
                items,
                matrix,
                day=view.spec.start_date + timedelta(days=day_index - 1),
                day_start=view.spec.day_start_time,
                day_end=view.spec.day_end_time,
                default_mode=mode,
            )
        )
    await container.trips.replace_itinerary(trip_id, recomputed, [])


async def _rewrite(container, trip_id, view, *, spec) -> None:  # type: ignore[no-untyped-def]
    """제목 등 메타 변경. 현재는 제목만 지원한다."""

    def _apply() -> None:
        from app.storage.repositories import TripRepository

        with container.database.session_scope() as session:
            row = TripRepository(session).find(trip_id)
            if row is None:
                raise NotFoundError(f"trip not found: {trip_id}")
            row.title = spec.title

    await container.executor.run(_apply)
