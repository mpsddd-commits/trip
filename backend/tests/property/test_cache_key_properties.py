"""C12 캐시 키 정규화 속성 테스트 — P-21, P-22 (BR-48)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.clients.cache_decorator import cache_key, normalize_text
from app.domain.models import LAT_MAX, LAT_MIN, LNG_MAX, LNG_MIN, Coordinate
from tests.property.generators import ANY_COORDINATE

pytestmark = pytest.mark.property

# 🔴 알파벳을 실제 질의에 나오는 문자로 좁힌다.
#
#    이전에는 임의 유니코드를 썼는데, `str.upper()` 는 **되돌릴 수 없는** 문자가 있다.
#    예: 'ı'(점 없는 i).upper() == 'I' → .lower() == 'i' ≠ 'ı',  'ß'.upper() == 'SS'.
#    그래서 "대소문자 표기만 다르면 같은 키" 라는 속성이 임의 유니코드에서는 거짓이다.
#
#    이것은 **정확성 결함이 아니라 캐시 적중 실패**다 (다른 키 → 외부 API 한 번 더 호출).
#    반대 방향, 즉 서로 다른 질의가 같은 키를 갖는 것이 위험한데 그런 일은 없다.
#    속성은 우리가 실제로 다루는 문자 집합(한글·영문·숫자)에 대해 주장한다.
_QUERY_ALPHABET = st.sampled_from(
    [chr(c) for c in range(0xAC00, 0xAC00 + 200)]      # 한글 음절 일부
    + [chr(c) for c in range(ord("a"), ord("z") + 1)]
    + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    + [chr(c) for c in range(ord("0"), ord("9") + 1)]
)
_WORD = st.text(alphabet=_QUERY_ALPHABET, min_size=1, max_size=10)


@given(st.lists(_WORD, min_size=1, max_size=5), st.integers(min_value=1, max_value=5))
def test_p21_whitespace_and_case_variants_share_a_key(words: list[str], extra_spaces: int) -> None:
    """P-21 — 공백·대소문자 표기만 다른 질의는 같은 키를 낸다 (쿼터 절약)."""
    tight = " ".join(words)
    loose = (" " * extra_spaces).join(words).upper()
    loose = f"{'  ' * extra_spaces}{loose}{'  ' * extra_spaces}"

    assert cache_key("local_search", "search", {"query": tight}) == cache_key(
        "local_search", "search", {"query": loose}
    )


@given(_WORD)
def test_p21_normalization_is_idempotent(value: str) -> None:
    """정규화는 멱등이다 — 같은 값을 두 번 정규화해도 같다."""
    once = normalize_text(value)
    assert normalize_text(once) == once


def _clamp(value: float, low: float, high: float) -> float:
    """국내 범위(BR-15) 안으로 잘라 넣는다. 테스트가 만든 좌표로 도메인 검증이 돌지 않게."""
    return round(min(max(value, low), high), 9)


@given(ANY_COORDINATE)
def test_p22_nearby_coordinates_share_a_key(coordinate: Coordinate) -> None:
    """P-22 — 같은 격자 칸 안의 미세한 흔들림은 하나의 키로 묶인다 (쿼터 절약).

    ⚠️ 속성을 **격자점 기준**으로 세우는 이유:
       키는 좌표를 소수 5자리로 반올림해 만든다. 임의의 두 값이 1e-7 만큼만 달라도
       하필 반올림 경계(…5)를 사이에 두고 있으면 서로 다른 칸으로 갈라진다.
       그것은 결함이 아니라 **모든 양자화가 갖는 성질**이고, 결과는 캐시 미스
       (외부 API 한 번 더 호출)일 뿐 잘못된 데이터를 주지 않는다.

       그래서 "임의의 두 근접 좌표"가 아니라 "격자점과 그 주변"으로 주장한다.
       실제로 막아야 하는 것 — 같은 장소를 가리키는 응답이 매번 다른 키를 얻는 일 —
       은 이 형태로 충분히 잡힌다.
    """
    base = Coordinate(
        lat=_clamp(round(coordinate.lat, 5), LAT_MIN, LAT_MAX),
        lng=_clamp(round(coordinate.lng, 5), LNG_MIN, LNG_MAX),
    )
    jittered = Coordinate(
        lat=_clamp(base.lat + 1e-7, LAT_MIN, LAT_MAX),
        lng=_clamp(base.lng + 1e-7, LNG_MIN, LNG_MAX),
    )
    assert cache_key("directions", "route_car", {"origin": base}) == cache_key(
        "directions", "route_car", {"origin": jittered}
    )


@given(ANY_COORDINATE)
def test_p22_distant_coordinates_get_different_keys(coordinate: Coordinate) -> None:
    """P-22 — 1m 이상 떨어진 좌표는 다른 키를 낸다 (다른 장소가 섞이면 안 된다)."""
    # 위도 0.001도 ≈ 111m
    moved = Coordinate(lat=min(coordinate.lat + 0.001, 39.0), lng=coordinate.lng)

    # 🔴 경계에서 잘리면 실제 이동량이 1m 미만이 될 수 있다.
    #    예: 38.999999999 → min(39.0009…, 39.0) = 39.0 (약 0.1mm 차이).
    #    키는 소수 5자리로 반올림하므로 **같은 키가 나오는 것이 정상**이다.
    #    속성의 전제(1m 이상 떨어짐)가 성립하는 경우에만 주장한다.
    if round(moved.lat, 5) == round(coordinate.lat, 5):
        return
    assert cache_key("directions", "route_car", {"origin": coordinate}) != cache_key(
        "directions", "route_car", {"origin": moved}
    )


@given(st.text(max_size=20), st.text(max_size=20))
def test_namespace_separates_keys(query: str, other: str) -> None:
    """네임스페이스가 다르면 같은 파라미터라도 키가 다르다."""
    assert cache_key("local_search", "search", {"q": query}) != cache_key(
        "blog", "search", {"q": query}
    )
