"""왕복 속성 기반 테스트 — P-17 ~ P-20 (PBT-02 / PBT-R1).

C14 DomainModels: from_dict(to_dict(x)) == x
C20 IcsBuilder  : parse(build(x)) 의 **보존 항목**이 원본과 일치 (BR-46)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain import ics
from app.domain.models import (
    Coordinate,
    CoordinateOutOfRangeError,
    ItineraryItem,
    Place,
    PlaceCandidate,
    TravelLeg,
    TripSpec,
)
from tests.property.generators import (
    ANY_COORDINATE,
    MEMO_TEXT,
    itinerary_items,
    places,
    travel_legs,
    trip_specs,
)
from app.domain.models import TravelMode

pytestmark = pytest.mark.property


# --- P-17 도메인 값 객체 왕복 ------------------------------------------------
@given(ANY_COORDINATE)
def test_p17_coordinate_roundtrip(value: Coordinate) -> None:
    assert Coordinate.from_dict(value.to_dict()) == value


@given(places())
def test_p17_place_roundtrip(value: Place) -> None:
    assert Place.from_dict(value.to_dict()) == value


@given(itinerary_items(index=0))
def test_p17_item_roundtrip(value: ItineraryItem) -> None:
    assert ItineraryItem.from_dict(value.to_dict()) == value


@given(travel_legs(from_index=0, to_index=1, mode=TravelMode.CAR))
def test_p17_leg_roundtrip(value: TravelLeg) -> None:
    assert TravelLeg.from_dict(value.to_dict()) == value


@given(trip_specs())
def test_p17_trip_spec_roundtrip(value: TripSpec) -> None:
    assert TripSpec.from_dict(value.to_dict()) == value


@given(
    st.builds(
        PlaceCandidate,
        raw_name=st.text(min_size=1, max_size=40),
        category_hint=st.one_of(st.none(), st.text(max_size=20)),
        suggested_stay_minutes=st.one_of(st.none(), st.integers(min_value=1, max_value=720)),
        reason=st.text(max_size=100),
        preferred_time_slot=st.one_of(st.none(), st.sampled_from(["morning", "lunch", "evening"])),
    )
)
def test_p17_candidate_roundtrip(value: PlaceCandidate) -> None:
    assert PlaceCandidate.from_dict(value.to_dict()) == value


# --- P-18 좌표 범위 검증 -----------------------------------------------------
@given(
    st.floats(min_value=-90, max_value=90, allow_nan=False),
    st.floats(min_value=-180, max_value=180, allow_nan=False),
)
def test_p18_out_of_range_is_rejected(lat: float, lng: float) -> None:
    """P-18 국내 범위 밖 좌표는 항상 거부된다 (BR-15)."""
    inside = 33.0 <= lat <= 39.0 and 124.0 <= lng <= 132.0
    if inside:
        assert Coordinate(lat, lng).lat == lat
    else:
        with pytest.raises(CoordinateOutOfRangeError):
            Coordinate(lat, lng)


# --- P-19 / P-20 iCalendar 왕복 ---------------------------------------------
@st.composite
def _timed_items(draw):
    """시각이 채워진 항목 목록. 마이크로초는 iCalendar 에 표현할 수 없어 제거한다."""
    count = draw(st.integers(min_value=1, max_value=6))
    base = datetime(2026, 9, 1, 0, 0, 0, tzinfo=UTC)
    items = []
    cursor = base
    for i in range(count):
        item = draw(itinerary_items(index=i, allow_fixed=False))
        arrival = cursor
        departure = arrival + timedelta(minutes=item.stay_minutes)
        items.append(item.with_times(arrival, departure))
        cursor = departure + timedelta(minutes=10)
    return items


def _normalize_newlines(text: str) -> str:
    """CRLF / 단독 CR 을 LF 로 모은다 — ICS TEXT 가 표현할 수 있는 형태."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


@given(_timed_items())
def test_p19_ics_roundtrip_preserves_documented_fields(items) -> None:
    """P-19 보존 항목이 왕복에서 일치한다 (BR-46).

    손실 항목(travel_mode / warnings / category / phone)은 검증하지 않는다.

    🔴 줄바꿈은 **정규화 후** 비교한다.
       RFC 5545 의 TEXT 값은 줄바꿈을 `
` 이스케이프로만 표현할 수 있고
       단독 CR(``)을 담을 방법이 없다. 따라서 `
` 과 `` 은 `
` 으로 정규화되며
       이것이 규격에 맞는 동작이다. 원문 그대로의 복원을 주장하면 속성이 거짓이 된다.
    """
    text = ics.build("여행", items)
    parsed = ics.parse(text)

    assert len(parsed) == len(items)
    for original, restored in zip(items, parsed, strict=True):
        assert restored["item_id"] == original.item_id
        assert restored["arrival_at"] == original.arrival_at
        assert restored["departure_at"] == original.departure_at
        assert restored["name"] == original.place.name
        assert _normalize_newlines(restored["memo"]) == _normalize_newlines(original.memo or "")
        assert restored["coordinate"] == original.place.coordinate
        assert restored["stay_minutes"] == original.stay_minutes


@given(MEMO_TEXT)
def test_p20_special_characters_survive_roundtrip(memo: str) -> None:
    """P-20 쉼표·세미콜론·역슬래시·개행이 포함된 메모도 왕복 보존 (BR-45)."""
    assert ics.unescape_text(ics.escape_text(memo)) == memo.replace("\r\n", "\n").replace("\r", "\n")
