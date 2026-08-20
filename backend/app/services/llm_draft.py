"""C22 LlmDraftGenerator — LLM 초안 생성과 응답 검증.

근거:
    FR-2    일자별 방문 장소 초안
    BR-06   `claude-sonnet-5`, **구조화 출력(도구 호출)로 스키마 강제**
    BR-07   수신 후 **서버에서 한 번 더 검증**, 실패 시 최대 2회 재시도 후 failed
    BR-08   수용 필드는 **5개뿐**. 주소·좌표·전화·영업시간·가격은 수용하지 않는다
    BR-09   상한 초과 항목은 잘라낸다 (오류가 아님)
    BR-21   `preferred_time_slot` 은 배치·표시용. 최적화에 쓰지 않는다
    SEC-13  신뢰할 수 없는 데이터를 검증 없이 역직렬화하지 않는다
"""

from __future__ import annotations

import json
from typing import Any

from app.clients.protocols import BlogPost, LlmClient
from app.core.enums import AuditEventType
from app.core.errors import ExternalServiceError, InternalError
from app.core.logging_config import get_logger
from app.domain.models import Place, PlaceCandidate, PlaceCategory, TripSpec

logger = get_logger(__name__)

MAX_STAY_MINUTES = 720
_TIME_SLOTS = ("morning", "lunch", "afternoon", "evening", "night")

# BR-06 — 모델이 이 스키마로만 답하도록 강제한다.
# BR-08 — 주소·좌표·전화 등 사실 정보 필드를 **스키마에 두지 않는다.**
DRAFT_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day_index": {"type": "integer", "minimum": 1},
                    "places": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "raw_name": {"type": "string", "minLength": 1, "maxLength": 120},
                                "category_hint": {"type": "string", "maxLength": 40},
                                "suggested_stay_minutes": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": MAX_STAY_MINUTES,
                                },
                                "reason": {"type": "string", "maxLength": 300},
                                "preferred_time_slot": {"type": "string", "enum": list(_TIME_SLOTS)},
                            },
                            "required": ["raw_name", "reason"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["day_index", "places"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["days"],
    "additionalProperties": False,
}

SUMMARY_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "highlights": {
            "type": "array",
            "minItems": 3,
            "maxItems": 5,
            "items": {"type": "string", "minLength": 1, "maxLength": 80},
        }
    },
    "required": ["highlights"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = """당신은 대한민국 국내 여행 일정을 설계하는 도우미입니다.
반드시 지켜야 할 규칙:
1. 장소는 **이름과 분류 힌트만** 제시하세요. 주소·좌표·전화번호·영업시간·가격을 절대 지어내지 마세요.
   그 정보는 시스템이 별도 검색으로 확인합니다.
2. 실제로 존재한다고 확신하는 장소만 제시하세요. 불확실하면 개수를 줄이세요.
3. 하루 일정은 이동 동선이 자연스럽게 이어지도록 배치하세요.
4. 모든 응답은 한국어로 작성하세요."""


class LlmDraftGenerator:
    def __init__(
        self,
        llm: LlmClient,
        *,
        max_tokens: int = 8000,
        max_retries: int = 2,
        max_items_per_day: int = 15,
    ) -> None:
        self._llm = llm
        self._max_tokens = max_tokens
        self._max_retries = max_retries
        self._max_items_per_day = max_items_per_day

    # ------------------------------------------------------------------
    async def generate_draft(self, spec: TripSpec) -> list[list[PlaceCandidate]]:
        """일자별 후보 목록을 만든다. **좌표는 포함되지 않는다** (BR-08)."""
        user_prompt = self._build_user_prompt(spec)
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._llm.complete(
                    system=_SYSTEM_PROMPT,
                    user=user_prompt,
                    max_tokens=self._max_tokens,
                    tool_schema=DRAFT_TOOL_SCHEMA,
                )
                return self._validate_draft(response.text, spec.day_count)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                # BR-07 — 스키마 불일치는 수용하지 않는다 (SEC-13).
                last_error = exc
                logger.warning(
                    "LLM 응답 스키마 검증 실패",
                    extra={
                        "attempt": attempt + 1,
                        "event_type": AuditEventType.LLM_SCHEMA_REJECTED.value,
                    },
                )
                continue
            except ExternalServiceError:
                raise

        raise InternalError(f"LLM 초안 스키마 검증에 반복 실패했습니다: {last_error}")

    def _build_user_prompt(self, spec: TripSpec) -> str:
        tags = ", ".join(spec.style_tags) if spec.style_tags else "특별한 선호 없음"
        budget = spec.budget_level.value if spec.budget_level else "무관"
        return (
            f"목적지: {spec.destination}\n"
            f"기간: {spec.day_count}일 ({spec.start_date} ~ {spec.end_date})\n"
            f"인원: {spec.party_size}명\n"
            f"여행 스타일: {tags}\n"
            f"하루 활동 시간: {spec.day_start_time.strftime('%H:%M')} ~ "
            f"{spec.day_end_time.strftime('%H:%M')}\n"
            f"주 이동수단: {spec.default_travel_mode.value}\n"
            f"예산 수준: {budget}\n\n"
            f"위 조건으로 {spec.day_count}일 일정을 만들어 주세요. "
            f"하루에 3~5곳을 넘지 마세요."
        )

    # ------------------------------------------------------------------
    def _validate_draft(self, raw_text: str, day_count: int) -> list[list[PlaceCandidate]]:
        """BR-07 — 서버 측 2차 검증. BR-08 — 5개 필드만 수용한다."""
        payload = json.loads(raw_text)
        if not isinstance(payload, dict):
            raise ValueError("응답 최상위가 객체가 아닙니다")

        days_raw = payload.get("days")
        if not isinstance(days_raw, list) or not days_raw:
            raise ValueError("days 배열이 없습니다")

        by_index: dict[int, list[PlaceCandidate]] = {}
        for day in days_raw:
            if not isinstance(day, dict):
                raise ValueError("일자 항목이 객체가 아닙니다")
            index = day.get("day_index")
            if not isinstance(index, int) or index < 1:
                raise ValueError(f"day_index 가 유효하지 않습니다: {index!r}")
            places_raw = day.get("places")
            if not isinstance(places_raw, list):
                raise ValueError("places 배열이 없습니다")

            candidates: list[PlaceCandidate] = []
            for item in places_raw:
                candidate = self._to_candidate(item)
                if candidate is not None:
                    candidates.append(candidate)
            # BR-09 — 상한 초과는 잘라낸다 (오류가 아님)
            by_index[index] = candidates[: self._max_items_per_day]

        # 일자 수를 요청과 맞춘다. 모자란 날은 빈 목록으로 둔다.
        return [by_index.get(index, []) for index in range(1, day_count + 1)]

    @staticmethod
    def _to_candidate(item: object) -> PlaceCandidate | None:
        """BR-08 — **5개 필드만** 읽는다. 나머지 키는 존재하더라도 읽지 않는다."""
        if not isinstance(item, dict):
            return None
        raw_name = item.get("raw_name")
        if not isinstance(raw_name, str) or not raw_name.strip():
            return None

        stay = item.get("suggested_stay_minutes")
        if not isinstance(stay, int) or not (1 <= stay <= MAX_STAY_MINUTES):
            stay = None

        slot = item.get("preferred_time_slot")
        if slot not in _TIME_SLOTS:
            slot = None

        hint = item.get("category_hint")
        reason = item.get("reason")
        return PlaceCandidate(
            raw_name=raw_name.strip()[:120],
            category_hint=hint.strip()[:40] if isinstance(hint, str) and hint.strip() else None,
            suggested_stay_minutes=stay,
            reason=reason.strip()[:300] if isinstance(reason, str) else "",
            preferred_time_slot=slot,
        )

    # ------------------------------------------------------------------
    async def summarize_place(self, place: Place, blogs: list[BlogPost]) -> list[str]:
        """FR-20 — 대표 메뉴 / 관람 포인트 3~5개.

        호출자(C27)가 **블로그 3건 이상**임을 보장한 뒤에만 부른다 (BR-40).
        """
        is_food = place.category in (PlaceCategory.RESTAURANT, PlaceCategory.CAFE)
        target = "대표 메뉴" if is_food else "관람 포인트"
        excerpts = "\n".join(
            f"- {b.title}: {b.description}"[:300] for b in blogs[:10]
        )  # BR-41 — 제목·발췌만
        user = (
            f"장소: {place.name} ({place.category.value})\n"
            f"아래는 이 장소에 대한 블로그 검색 결과의 제목과 발췌입니다.\n"
            f"{excerpts}\n\n"
            f"이 근거만 사용해 {target} 3~5개를 뽑아 주세요. "
            f"근거에 없는 내용을 지어내지 마세요."
        )
        response = await self._llm.complete(
            system=_SYSTEM_PROMPT,
            user=user,
            max_tokens=1000,
            tool_schema=SUMMARY_TOOL_SCHEMA,
        )
        payload = json.loads(response.text)
        highlights = payload.get("highlights", [])
        if not isinstance(highlights, list):
            return []
        cleaned = [h.strip()[:80] for h in highlights if isinstance(h, str) and h.strip()]
        return cleaned[:5]  # BR-43
