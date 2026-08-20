"""C7 응답 파싱과 좌표 변환 — BR-14, BR-15, 미확정 좌표계 방어.

🔴 `to_wgs84` 의 좌표계 가정은 **미검증**이다. 이 테스트는 가정이 맞을 때의
   동작과, **가정이 틀렸을 때 조용히 넘어가지 않는지**를 함께 확인한다.
"""

from __future__ import annotations

import pytest

from app.clients.naver_local import (
    CoordinateConversionError,
    NaverLocalSearchClient,
    strip_tags,
    to_wgs84,
)
from tests.fixtures.external_responses import NAVER_LOCAL_BAD_COORD, NAVER_LOCAL_OK


# ---------------------------------------------------------------------------
# BR-14 — 태그·엔티티 제거
# ---------------------------------------------------------------------------
def test_strip_tags_removes_emphasis_markup() -> None:
    assert strip_tags("<b>광안리</b> 해수욕장") == "광안리 해수욕장"


def test_strip_tags_decodes_entities() -> None:
    assert strip_tags("돼지국밥 &amp; 수육") == "돼지국밥 & 수육"


def test_parsed_names_contain_no_angle_brackets() -> None:
    """SEC-05 — 저장되는 이름에 마크업이 남으면 안 된다."""
    places = NaverLocalSearchClient._parse(NAVER_LOCAL_OK)
    for place in places:
        assert "<" not in place.name and ">" not in place.name


# ---------------------------------------------------------------------------
# 좌표 변환 (미확정 가정)
# ---------------------------------------------------------------------------
def test_scaled_integer_coordinates_are_converted() -> None:
    """가정이 맞을 때: 1e7 배율 정수 -> WGS84."""
    coordinate = to_wgs84("1291180000", "351530000")
    assert coordinate.lat == pytest.approx(35.153, abs=1e-3)
    assert coordinate.lng == pytest.approx(129.118, abs=1e-3)


def test_decimal_coordinates_pass_through() -> None:
    coordinate = to_wgs84("129.118", "35.153")
    assert coordinate.lat == pytest.approx(35.153, abs=1e-6)


def test_wrong_coordinate_system_raises_instead_of_silently_saving() -> None:
    """🔴 좌표계 가정이 틀리면 **즉시 드러나야 한다** (BR-15).

    KATECH 계열 값을 그대로 넣으면 국내 범위를 벗어나므로 예외가 나야 한다.
    """
    with pytest.raises(CoordinateConversionError):
        to_wgs84("311111", "552222")


def test_unparsable_coordinates_raise() -> None:
    with pytest.raises(CoordinateConversionError):
        to_wgs84("없음", None)


def test_bad_coordinate_item_is_skipped_not_fatal() -> None:
    """NFR-3 — 항목 하나의 좌표 오류가 검색 전체를 실패시키지 않는다."""
    places = NaverLocalSearchClient._parse(NAVER_LOCAL_BAD_COORD)
    assert places == []


def test_parse_maps_all_documented_fields() -> None:
    places = NaverLocalSearchClient._parse(NAVER_LOCAL_OK)
    assert len(places) == 2
    first = places[0]
    assert first.name == "광안리 해수욕장"
    assert first.road_address == "부산광역시 수영구 광안해변로 219"
    assert first.category_raw == "여행>관광,명소>해수욕장"
    # 영업시간 필드는 응답에 없다 — FR-13 축소 확정의 근거 (BR-35)
    assert not hasattr(first, "opening_hours")
