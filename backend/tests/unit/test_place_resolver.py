"""C23 PlaceResolver 경계 예제 테스트 🔴 — BR-11, BR-12, BR-16, BR-17, BR-18.

이 모듈은 PBT 비대상이다(판정이 외부 데이터 형태에 의존). 대신 **판정 경계를
직접 겨냥한 예제**로 검증한다 (PBT-10).
"""

from __future__ import annotations

import pytest

from app.clients.protocols import SearchedPlace
from app.core.errors import ExternalServiceError
from app.domain.models import Coordinate, PlaceCandidate, ResolveFailureCode
from app.services.place_resolver import PlaceResolver, normalize_name, similarity

BUSAN = Coordinate(35.1796, 129.0756)


class _StubSearch:
    def __init__(self, results: list[SearchedPlace] | Exception) -> None:
        self._results = results
        self.queries: list[str] = []

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        self.queries.append(query)
        if isinstance(self._results, Exception):
            raise self._results
        return self._results


def _result(name: str, *, address: str = "부산광역시 수영구 광안동", category: str = "여행>관광,명소") -> SearchedPlace:
    return SearchedPlace(
        name=name,
        coordinate=BUSAN,
        category_raw=category,
        road_address=address,
        address=address,
    )


def _candidate(name: str, hint: str | None = None) -> PlaceCandidate:
    return PlaceCandidate(raw_name=name, category_hint=hint, reason="테스트")


async def _resolve(search, candidate, destination="부산", threshold=0.60):
    resolver = PlaceResolver(search, similarity_threshold=threshold)
    return await resolver.resolve_many([[candidate]], destination)


# ---------------------------------------------------------------------------
# 정규화·유사도 (BR-11 ①)
# ---------------------------------------------------------------------------
def test_normalize_removes_brackets_and_corporate_noise() -> None:
    assert normalize_name("성심당 (본점)") == normalize_name("성심당")
    assert normalize_name("(주)해운대 횟집") == normalize_name("해운대 횟집")


def test_identical_names_score_one() -> None:
    assert similarity("광안리 해수욕장", "광안리 해수욕장") == 1.0


def test_substring_names_score_high() -> None:
    assert similarity("광안리", "광안리 해수욕장") == pytest.approx(0.90)


def test_unrelated_names_score_low() -> None:
    assert similarity("광안리 해수욕장", "전주 한옥마을") < 0.6


# ---------------------------------------------------------------------------
# BR-11 — 3조건 AND
# ---------------------------------------------------------------------------
async def test_exact_match_resolves() -> None:
    result = await _resolve(_StubSearch([_result("광안리 해수욕장")]), _candidate("광안리 해수욕장"))
    assert result.resolved_count == 1
    assert result.unresolved_count == 0
    assert result.resolved[0].resolved_from == "광안리 해수욕장"
    assert result.resolved[0].match_score == 1.0


async def test_low_similarity_is_rejected() -> None:
    """① 유사도 < 0.60 이면 미해결."""
    result = await _resolve(_StubSearch([_result("전혀 다른 이름의 가게")]), _candidate("광안리 해수욕장"))
    assert result.resolved_count == 0
    assert result.unresolved[0].failure_code is ResolveFailureCode.LOW_SIMILARITY
    # BR-12 — 가장 근접했던 결과를 남긴다
    assert result.unresolved[0].best_candidate_name == "전혀 다른 이름의 가게"
    assert result.unresolved[0].best_match_score is not None


async def test_similarity_threshold_boundary() -> None:
    """임계값 경계 — 0.60 미만은 거부, 0.60 이상은 통과."""
    search = _StubSearch([_result("광안리 해수욕장")])
    strict = await _resolve(search, _candidate("광안리 해수욕장"), threshold=1.0)
    assert strict.resolved_count == 1  # 완전 일치는 1.0 이므로 통과

    partial = await _resolve(
        _StubSearch([_result("광안리 해수욕장")]), _candidate("광안리"), threshold=0.95
    )
    assert partial.resolved_count == 0  # 부분 일치 0.90 < 0.95
    assert partial.unresolved[0].failure_code is ResolveFailureCode.LOW_SIMILARITY


async def test_out_of_region_is_rejected() -> None:
    """② 검색 결과 주소가 목적지를 포함하지 않으면 미해결."""
    result = await _resolve(
        _StubSearch([_result("광안리 해수욕장", address="서울특별시 강남구")]),
        _candidate("광안리 해수욕장"),
        destination="부산",
    )
    assert result.resolved_count == 0
    assert result.unresolved[0].failure_code is ResolveFailureCode.OUT_OF_REGION


async def test_category_mismatch_is_rejected() -> None:
    """③ 카테고리 힌트가 있으면 대분류가 일치해야 한다."""
    result = await _resolve(
        _StubSearch([_result("광안리 해수욕장", category="음식점>한식")]),
        _candidate("광안리 해수욕장", hint="관광명소"),
    )
    assert result.resolved_count == 0
    assert result.unresolved[0].failure_code is ResolveFailureCode.CATEGORY_MISMATCH


async def test_missing_category_hint_skips_third_condition() -> None:
    """힌트가 없으면 카테고리 조건은 통과 처리한다."""
    result = await _resolve(
        _StubSearch([_result("광안리 해수욕장", category="음식점>한식")]),
        _candidate("광안리 해수욕장", hint=None),
    )
    assert result.resolved_count == 1


# ---------------------------------------------------------------------------
# BR-16 — 검색 실패·0건
# ---------------------------------------------------------------------------
async def test_empty_search_result_is_unresolved() -> None:
    result = await _resolve(_StubSearch([]), _candidate("존재하지 않는 장소"))
    assert result.unresolved[0].failure_code is ResolveFailureCode.NO_SEARCH_RESULT


async def test_search_failure_does_not_break_pipeline() -> None:
    """BR-16 — API 실패는 미해결 처리하되 예외를 밖으로 던지지 않는다."""
    result = await _resolve(_StubSearch(ExternalServiceError("down")), _candidate("광안리"))
    assert result.resolved_count == 0
    assert result.unresolved[0].failure_code is ResolveFailureCode.SEARCH_UNAVAILABLE


# ---------------------------------------------------------------------------
# BR-10 / BR-17 / BR-18
# ---------------------------------------------------------------------------
async def test_query_is_destination_plus_name() -> None:
    """BR-10 — 질의는 "{목적지} {장소명}"."""
    search = _StubSearch([_result("광안리 해수욕장")])
    await _resolve(search, _candidate("광안리 해수욕장"), destination="부산")
    assert search.queries == ["부산 광안리 해수욕장"]


async def test_duplicates_keep_the_first_resolution() -> None:
    """BR-17 — 같은 좌표·이름은 앞선 것을 유지한다."""
    search = _StubSearch([_result("광안리 해수욕장")])
    resolver = PlaceResolver(search)
    result = await resolver.resolve_many(
        [[_candidate("광안리 해수욕장"), _candidate("광안리 해수욕장")]], "부산"
    )
    assert result.resolved_count == 1


async def test_unresolved_never_becomes_a_place() -> None:
    """🔴 BR-18 — 미해결 후보는 어떤 경우에도 Place 가 되지 않는다."""
    search = _StubSearch([_result("완전히 무관한 상호명입니다")])
    resolver = PlaceResolver(search)
    result = await resolver.resolve_many(
        [[_candidate("광안리 해수욕장"), _candidate("해운대 해수욕장")]], "부산"
    )
    assert result.resolved == []
    assert result.unresolved_count == 2
    resolved_names = {p.name for p in result.resolved}
    unresolved_names = {u.candidate.raw_name for u in result.unresolved}
    assert resolved_names.isdisjoint(unresolved_names)


async def test_resolved_place_never_carries_opening_hours() -> None:
    """BR-35 — 외부 데이터로 영업시간을 채우는 경로가 없다."""
    result = await _resolve(_StubSearch([_result("광안리 해수욕장")]), _candidate("광안리 해수욕장"))
    assert result.resolved[0].opening_hours is None
