"""C23 PlaceResolver — LLM 장소명을 실재하는 장소로 해석한다. 🔴

**최상위 위험 ①(LLM 환각)의 차단 지점이다.**

근거:
    FR-3    미해결 항목은 일정에 넣지 않고 "확인 필요" 목록으로 분리
    BR-10   질의는 "{목적지} {장소명}" 형태, display=5 (CON-2)
    BR-11   **3조건 AND** — 유사도 >= 0.60 AND 지역 포함 AND 카테고리 대분류 일치
    BR-12   후보가 없으면 가장 근접한 결과의 이름·유사도·실패 사유를 기록
    BR-14   태그 제거 (클라이언트에서 이미 처리됨)
    BR-15   좌표 국내 범위 검증 (클라이언트에서 이미 처리됨)
    BR-16   검색 0건 / API 실패는 미해결 처리하되 파이프라인을 중단하지 않는다
    BR-17   중복 제거 — 먼저 해석된 것을 유지
    BR-18   🔴 **미해결 후보는 어떤 경우에도 ItineraryItem 이 되지 않는다**

이 모듈은 PBT 비대상이다(판정이 외부 데이터 형태에 의존). 대신 경계 예제로
집중 검증한다 (PBT-10, business-logic-model.md §11).
"""

from __future__ import annotations

import asyncio
import re
import unicodedata
import uuid
from dataclasses import dataclass, field

from app.clients.circuit import CircuitOpenError
from app.clients.protocols import LocalSearchClient, SearchedPlace
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger
from app.domain.categories import classify_category
from app.domain.models import (
    Place,
    PlaceCandidate,
    PlaceCategory,
    PlaceSource,
    ResolveFailureCode,
    UnresolvedCandidate,
)

logger = get_logger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = 0.60  # BR-11 ①
_DEDUPE_PRECISION = 5  # BR-17 — 좌표 소수 5자리(약 1m)

# 정규화 시 제거하는 법인격·수식어 (BR-11 정규화 규칙)
_NOISE_WORDS = (
    "주식회사",
    "(주)",
    "㈜",
    "본점",
    "지점",
    "직영점",
    "점",
)
_BRACKETS = re.compile(r"[\(\[\{（【][^\)\]\}）】]*[\)\]\}）】]")
_NON_WORD = re.compile(r"[^0-9a-z가-힣]+")


# ---------------------------------------------------------------------------
# 정규화와 유사도 (BR-11)
# ---------------------------------------------------------------------------
def normalize_name(value: str) -> str:
    """NFC → 소문자 → 괄호 제거 → 법인격 제거 → 공백·특수문자 제거."""
    text = unicodedata.normalize("NFC", value).casefold()
    text = _BRACKETS.sub(" ", text)
    for noise in _NOISE_WORDS:
        text = text.replace(noise.casefold(), " ")
    return _NON_WORD.sub("", text)


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def similarity(a: str, b: str) -> float:
    """BR-11 ① 정규화 문자열 유사도.

    완전 일치 1.00 / 한쪽이 다른 쪽의 부분문자열이면 0.90 /
    그 외에는 `1 - levenshtein / max(len)`.
    """
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.90
    return 1.0 - _levenshtein(na, nb) / max(len(na), len(nb))


# ---------------------------------------------------------------------------
@dataclass(slots=True)
class ResolveResult:
    resolved: list[Place] = field(default_factory=list)
    unresolved: list[UnresolvedCandidate] = field(default_factory=list)
    # 해석된 장소가 어느 일자에 속하는지 (파이프라인이 재조립할 때 사용)
    day_of_place: dict[str, int] = field(default_factory=dict)
    # 원본 후보 정보 (체류시간·시간대 제안 보존 — BR-21, BR-52)
    candidate_of_place: dict[str, PlaceCandidate] = field(default_factory=dict)

    @property
    def resolved_count(self) -> int:
        return len(self.resolved)

    @property
    def unresolved_count(self) -> int:
        return len(self.unresolved)


class PlaceResolver:
    def __init__(
        self,
        local_search: LocalSearchClient,
        *,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        parallelism: int = 5,
    ) -> None:
        self._search = local_search
        self._threshold = similarity_threshold
        self._parallelism = parallelism

    # ------------------------------------------------------------------
    async def resolve_many(
        self, candidates_by_day: list[list[PlaceCandidate]], destination: str
    ) -> ResolveResult:
        """일자별 후보 전체를 해석한다.

        SP-3 — 제한된 동시성으로 병렬 호출한다. 전역 상한(ND-17)은 L2 가 담당한다.
        """
        semaphore = asyncio.Semaphore(self._parallelism)
        tasks = [
            self._guarded(semaphore, candidate, day_index, destination)
            for day_index, candidates in enumerate(candidates_by_day, start=1)
            for candidate in candidates
        ]
        outcomes = await asyncio.gather(*tasks)

        result = ResolveResult()
        seen_names: set[str] = set()
        seen_coords: set[tuple[float, float]] = set()

        for day_index, candidate, place, failure in outcomes:
            if place is None:
                result.unresolved.append(
                    UnresolvedCandidate(
                        candidate=candidate,
                        day_index=day_index,
                        failure_code=failure.code,
                        best_candidate_name=failure.best_name,
                        best_match_score=failure.best_score,
                    )
                )
                continue

            # BR-17 — 중복 제거. 먼저 해석된 것을 유지한다.
            key_name = normalize_name(place.name)
            key_coord = (
                round(place.coordinate.lat, _DEDUPE_PRECISION),
                round(place.coordinate.lng, _DEDUPE_PRECISION),
            )
            if key_name in seen_names or key_coord in seen_coords:
                continue
            seen_names.add(key_name)
            seen_coords.add(key_coord)

            result.resolved.append(place)
            result.day_of_place[place.place_id] = day_index
            result.candidate_of_place[place.place_id] = candidate

        logger.info(
            "grounding completed",
            extra={
                "resolved": result.resolved_count,
                "unresolved": result.unresolved_count,
                "destination": destination,
            },
        )
        return result

    # ------------------------------------------------------------------
    async def _guarded(
        self,
        semaphore: asyncio.Semaphore,
        candidate: PlaceCandidate,
        day_index: int,
        destination: str,
    ) -> tuple[int, PlaceCandidate, Place | None, "_Failure"]:
        async with semaphore:
            place, failure = await self._resolve_one(candidate, destination)
            return day_index, candidate, place, failure

    async def _resolve_one(
        self, candidate: PlaceCandidate, destination: str
    ) -> tuple[Place | None, "_Failure"]:
        query = f"{destination} {candidate.raw_name}".strip()  # BR-10
        try:
            results = await self._search.search(query, display=5)
        except (ExternalServiceError, CircuitOpenError) as exc:
            # BR-16 — 파이프라인을 중단하지 않는다.
            logger.warning("지역검색 실패로 미해결 처리", extra={"detail": str(exc)})
            return None, _Failure(ResolveFailureCode.SEARCH_UNAVAILABLE)

        if not results:
            return None, _Failure(ResolveFailureCode.NO_SEARCH_RESULT)

        best_place: SearchedPlace | None = None
        best_score = -1.0
        best_failure = ResolveFailureCode.LOW_SIMILARITY
        matched: tuple[SearchedPlace, float] | None = None

        for result in results:
            score = similarity(candidate.raw_name, result.name)
            if score > best_score:
                best_score, best_place = score, result

            ok, failure_code = self._is_match(candidate, result, score, destination)
            if ok:
                if matched is None or score > matched[1]:
                    matched = (result, score)
            elif failure_code is not None and score >= best_score:
                best_failure = failure_code

        if matched is None:
            # BR-12 — 가장 근접했던 결과를 사용자 판단 보조로 남긴다.
            return None, _Failure(
                best_failure,
                best_name=best_place.name if best_place else None,
                best_score=round(best_score, 3) if best_score >= 0 else None,
            )

        place = self._to_place(candidate, matched[0], matched[1])
        return place, _Failure(ResolveFailureCode.LOW_SIMILARITY)  # 미사용

    # ------------------------------------------------------------------
    def _is_match(
        self,
        candidate: PlaceCandidate,
        result: SearchedPlace,
        score: float,
        destination: str,
    ) -> tuple[bool, ResolveFailureCode | None]:
        """BR-11 — **3조건 AND**. 하나라도 실패하면 후보에서 제외한다."""
        # ① 유사도
        if score < self._threshold:
            return False, ResolveFailureCode.LOW_SIMILARITY

        # ② 지역 — 검색 결과 주소가 목적지를 포함하는가
        if not self._in_region(result, destination):
            return False, ResolveFailureCode.OUT_OF_REGION

        # ③ 카테고리 — 힌트가 있을 때만 검사한다 (없으면 통과)
        if candidate.category_hint:
            hinted = classify_category(candidate.category_hint)
            actual = classify_category(result.category_raw)
            if hinted is not PlaceCategory.OTHER and actual is not hinted:
                return False, ResolveFailureCode.CATEGORY_MISMATCH

        return True, None

    @staticmethod
    def _in_region(result: SearchedPlace, destination: str) -> bool:
        """목적지 문자열이 주소에 포함되는지.

        목적지가 비어 있으면 이 조건은 통과 처리한다(판단 근거가 없으므로).
        """
        target = normalize_name(destination)
        if not target:
            return True
        haystack = normalize_name(
            " ".join(filter(None, [result.road_address, result.address]))
        )
        return target in haystack

    @staticmethod
    def _to_place(candidate: PlaceCandidate, result: SearchedPlace, score: float) -> Place:
        return Place(
            place_id=str(uuid.uuid4()),
            name=result.name,
            coordinate=result.coordinate,
            category=classify_category(result.category_raw or candidate.category_hint),
            category_raw=result.category_raw,
            road_address=result.road_address,
            address=result.address,
            phone=result.phone,
            naver_link=result.link,
            source=PlaceSource.NAVER_LOCAL,
            resolved_from=candidate.raw_name,  # 추적성
            match_score=round(score, 3),
            opening_hours=None,  # BR-35 — 외부에서 채우지 않는다
        )


@dataclass(frozen=True, slots=True)
class _Failure:
    code: ResolveFailureCode
    best_name: str | None = None
    best_score: float | None = None
