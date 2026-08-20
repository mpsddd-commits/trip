"""도메인 생성기 (PBT-07 / PBT-R3).

원시 타입 생성기만 쓰지 않고, 업무 제약을 지키는 도메인 객체를 생성한다.
- 좌표: 국내 범위 (BR-15) + 경계값 포함
- 항목: 체류시간 1~720분, 고정/비고정 혼합
- 여행 조건: 기간 1~10일 (BR-01), 인원 1~20 (BR-04)
- 메모: 특수문자·유니코드·빈 문자열·최대 길이 포함 (P-20)
"""

from __future__ import annotations

from datetime import date, time, timedelta

from hypothesis import strategies as st

from app.domain.models import (
    Coordinate,
    ItineraryItem,
    LegSource,
    Place,
    PlaceCategory,
    PlaceSource,
    TravelLeg,
    TravelMode,
    TripSpec,
)

# --- 좌표 ------------------------------------------------------------------
LATITUDES = st.floats(min_value=33.0, max_value=39.0, allow_nan=False, allow_infinity=False)
LONGITUDES = st.floats(min_value=124.0, max_value=132.0, allow_nan=False, allow_infinity=False)


@st.composite
def coordinates(draw) -> Coordinate:
    return Coordinate(lat=draw(LATITUDES), lng=draw(LONGITUDES))


# 경계값을 명시적으로 섞어 넣는다.
BOUNDARY_COORDINATES = st.sampled_from(
    [
        Coordinate(33.0, 124.0),
        Coordinate(39.0, 132.0),
        Coordinate(33.0, 132.0),
        Coordinate(39.0, 124.0),
        Coordinate(37.5665, 126.9780),  # 서울시청
        Coordinate(35.1796, 129.0756),  # 부산
        Coordinate(33.4996, 126.5312),  # 제주
    ]
)

ANY_COORDINATE = st.one_of(coordinates(), BOUNDARY_COORDINATES)


# --- 텍스트 ----------------------------------------------------------------
MEMO_TEXT = st.one_of(
    st.just(""),
    st.text(max_size=200),
    st.sampled_from(
        [
            "쉼표, 포함",
            "세미콜론; 포함",
            "역슬래시 \\ 포함",
            "줄바꿈\n포함",
            "혼합 , ; \\ \n 전부",
            "이모지 🍜 와 한글",
            "a" * 200,
        ]
    ),
)

PLACE_NAME = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")), min_size=1, max_size=40
).filter(lambda s: s.strip() != "")


# --- 장소 / 항목 -----------------------------------------------------------
@st.composite
def places(draw, *, index: int | None = None) -> Place:
    idx = draw(st.integers(min_value=0, max_value=9_999)) if index is None else index
    return Place(
        place_id=f"place-{idx}",
        name=draw(PLACE_NAME),
        coordinate=draw(ANY_COORDINATE),
        category=draw(st.sampled_from(list(PlaceCategory))),
        road_address=draw(st.one_of(st.none(), st.text(max_size=60))),
        source=PlaceSource.MOCK,
    )


@st.composite
def itinerary_items(draw, *, index: int = 0, allow_fixed: bool = True) -> ItineraryItem:
    fixed = draw(st.booleans()) if allow_fixed else False
    fixed_time = (
        time(hour=draw(st.integers(min_value=8, max_value=20)), minute=draw(st.sampled_from([0, 30])))
        if fixed
        else None
    )
    return ItineraryItem(
        item_id=f"item-{index}",
        place=draw(places(index=index)),
        stay_minutes=draw(st.integers(min_value=1, max_value=720)),
        position=index,
        time_fixed=fixed,
        fixed_time=fixed_time,
        travel_mode=draw(st.one_of(st.none(), st.sampled_from(list(TravelMode)))),
        memo=draw(st.one_of(st.none(), MEMO_TEXT)),
    )


@st.composite
def item_lists(draw, *, min_size: int = 0, max_size: int = 15, allow_fixed: bool = True):
    size = draw(st.integers(min_value=min_size, max_value=max_size))
    return [draw(itinerary_items(index=i, allow_fixed=allow_fixed)) for i in range(size)]


# --- 이동 구간 / 행렬 -------------------------------------------------------
@st.composite
def travel_legs(draw, *, from_index: int, to_index: int, mode: TravelMode) -> TravelLeg:
    if mode is TravelMode.TRANSIT:
        source, is_estimate, path = LegSource.HAVERSINE_TRANSIT, True, ()
    elif mode is TravelMode.WALK:
        source, is_estimate, path = LegSource.HAVERSINE_WALK, True, ()
    else:
        source = draw(st.sampled_from([LegSource.DIRECTIONS_API, LegSource.HAVERSINE_CAR_FALLBACK]))
        is_estimate = source is LegSource.HAVERSINE_CAR_FALLBACK
        path = ()
    return TravelLeg(
        from_index=from_index,
        to_index=to_index,
        mode=mode,
        duration_sec=draw(st.integers(min_value=0, max_value=14_400)),
        distance_m=draw(st.integers(min_value=0, max_value=200_000)),
        source=source,
        is_estimate=is_estimate,
        path=path,
    )


@st.composite
def full_matrix_legs(draw, n: int, mode: TravelMode) -> list[TravelLeg]:
    """모든 (i, j) 쌍을 채운 구간 목록. 최적화 탐색에 필요하다."""
    legs: list[TravelLeg] = []
    for i in range(n):
        for j in range(n):
            if i != j:
                legs.append(draw(travel_legs(from_index=i, to_index=j, mode=mode)))
    return legs


# --- 여행 조건 -------------------------------------------------------------
@st.composite
def trip_specs(draw) -> TripSpec:
    start = draw(st.dates(min_value=date(2026, 1, 1), max_value=date(2027, 12, 31)))
    days = draw(st.integers(min_value=1, max_value=10))  # BR-01
    start_hour = draw(st.integers(min_value=5, max_value=12))
    end_hour = draw(st.integers(min_value=start_hour + 1, max_value=23))
    return TripSpec(
        title=draw(PLACE_NAME),
        destination=draw(st.sampled_from(["서울", "부산", "제주", "강릉", "전주"])),
        start_date=start,
        end_date=start + timedelta(days=days - 1),
        party_size=draw(st.integers(min_value=1, max_value=20)),
        style_tags=tuple(draw(st.lists(st.sampled_from(["맛집", "자연", "역사"]), max_size=3))),
        day_start_time=time(hour=start_hour),
        day_end_time=time(hour=end_hour),
        default_travel_mode=draw(st.sampled_from(list(TravelMode))),
    )
