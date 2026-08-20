"""C22 LlmDraftGenerator 테스트 — BR-06 ~ BR-09, SEC-13."""

from __future__ import annotations

import json
from datetime import date, time

import pytest

from app.clients.protocols import LlmResponse
from app.core.errors import InternalError
from app.domain.models import TravelMode, TripSpec
from app.services.llm_draft import DRAFT_TOOL_SCHEMA, LlmDraftGenerator

SPEC = TripSpec(
    title="부산 여행",
    destination="부산",
    start_date=date(2026, 9, 1),
    end_date=date(2026, 9, 2),
    day_start_time=time(9, 0),
    day_end_time=time(21, 0),
    default_travel_mode=TravelMode.TRANSIT,
)


class _StubLlm:
    def __init__(self, *payloads: object) -> None:
        self._payloads = list(payloads)
        self.calls = 0
        self.last_tool_schema: dict | None = None

    async def complete(self, *, system, user, max_tokens, tool_schema=None) -> LlmResponse:
        self.calls += 1
        self.last_tool_schema = tool_schema
        payload = self._payloads[min(self.calls - 1, len(self._payloads) - 1)]
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        return LlmResponse(text=text)


def _valid_payload() -> dict:
    return {
        "days": [
            {
                "day_index": 1,
                "places": [
                    {
                        "raw_name": "광안리 해수욕장",
                        "category_hint": "관광명소",
                        "suggested_stay_minutes": 90,
                        "reason": "야경",
                        "preferred_time_slot": "evening",
                    }
                ],
            },
            {"day_index": 2, "places": [{"raw_name": "감천문화마을", "reason": "사진"}]},
        ]
    }


# ---------------------------------------------------------------------------
async def test_valid_response_is_parsed() -> None:
    llm = _StubLlm(_valid_payload())
    days = await LlmDraftGenerator(llm).generate_draft(SPEC)
    assert len(days) == 2
    assert days[0][0].raw_name == "광안리 해수욕장"
    assert days[0][0].suggested_stay_minutes == 90
    assert days[1][0].suggested_stay_minutes is None  # 미지정은 None (BR-52 에서 보완)


async def test_structured_output_is_forced() -> None:
    """BR-06 — 도구 호출 스키마를 반드시 전달한다."""
    llm = _StubLlm(_valid_payload())
    await LlmDraftGenerator(llm).generate_draft(SPEC)
    assert llm.last_tool_schema == DRAFT_TOOL_SCHEMA


def test_schema_forbids_factual_fields() -> None:
    """BR-08 — 스키마 자체에 주소·좌표·전화 필드가 없어야 한다."""
    place_props = DRAFT_TOOL_SCHEMA["properties"]["days"]["items"]["properties"]["places"]["items"][
        "properties"
    ]
    assert set(place_props) == {
        "raw_name",
        "category_hint",
        "suggested_stay_minutes",
        "reason",
        "preferred_time_slot",
    }
    for forbidden in ("address", "road_address", "coordinate", "lat", "lng", "phone", "opening_hours"):
        assert forbidden not in place_props


async def test_forbidden_fields_in_response_are_not_ingested() -> None:
    """BR-08 — 모델이 주소·좌표를 넣어 보내도 **읽지 않는다.**"""
    payload = {
        "days": [
            {
                "day_index": 1,
                "places": [
                    {
                        "raw_name": "광안리 해수욕장",
                        "reason": "야경",
                        "address": "부산 어딘가 (환각 가능)",
                        "lat": 35.1,
                        "lng": 129.1,
                        "phone": "051-000-0000",
                    }
                ],
            }
        ]
    }
    days = await LlmDraftGenerator(_StubLlm(payload)).generate_draft(SPEC)
    candidate = days[0][0]
    assert candidate.raw_name == "광안리 해수욕장"
    for forbidden in ("address", "lat", "lng", "phone"):
        assert not hasattr(candidate, forbidden)


async def test_malformed_response_is_retried_then_fails() -> None:
    """BR-07 — 스키마 불일치는 최대 2회 재시도 후 실패."""
    llm = _StubLlm("not json at all")
    with pytest.raises(InternalError):
        await LlmDraftGenerator(llm, max_retries=2).generate_draft(SPEC)
    assert llm.calls == 3  # 최초 1 + 재시도 2


async def test_recovers_when_second_attempt_is_valid() -> None:
    llm = _StubLlm("broken", _valid_payload())
    days = await LlmDraftGenerator(llm, max_retries=2).generate_draft(SPEC)
    assert llm.calls == 2
    assert days[0][0].raw_name == "광안리 해수욕장"


async def test_items_over_limit_are_truncated_not_rejected() -> None:
    """BR-09 — 상한 초과는 오류가 아니라 잘라낸다."""
    payload = {
        "days": [
            {
                "day_index": 1,
                "places": [{"raw_name": f"장소{i}", "reason": "r"} for i in range(20)],
            }
        ]
    }
    days = await LlmDraftGenerator(_StubLlm(payload), max_items_per_day=15).generate_draft(SPEC)
    assert len(days[0]) == 15


async def test_missing_day_is_filled_with_empty_list() -> None:
    payload = {"days": [{"day_index": 1, "places": [{"raw_name": "장소", "reason": "r"}]}]}
    days = await LlmDraftGenerator(_StubLlm(payload)).generate_draft(SPEC)
    assert len(days) == 2
    assert days[1] == []


async def test_invalid_stay_minutes_is_dropped() -> None:
    payload = {
        "days": [
            {
                "day_index": 1,
                "places": [
                    {"raw_name": "장소", "reason": "r", "suggested_stay_minutes": 99999}
                ],
            }
        ]
    }
    days = await LlmDraftGenerator(_StubLlm(payload)).generate_draft(SPEC)
    assert days[0][0].suggested_stay_minutes is None
