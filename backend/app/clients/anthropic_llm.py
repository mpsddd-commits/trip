"""C11 AnthropicLlmClient — Claude API 호출 (전송 전담).

근거:
    BR-06   모델 `claude-sonnet-5`, **구조화 출력(도구 호출)로 스키마 강제**
    BR-08   이 클라이언트는 전송만 한다. 프롬프트 구성·응답 검증은 C22 책임
    BR-47   LLM 은 읽기 타임아웃 120초
    RP-3    실패 시 **폴백 없음** — 초안은 파이프라인의 입력 그 자체

설계 조정 (code-summary 기록):
    `anthropic` SDK 대신 **BaseHttpClient 를 통한 직접 호출**을 사용한다.
    사유 ① SDK 를 쓰면 서킷·세마포어·쿼터 계측·재시도(RP-1 4겹)를 우회한다.
         ② 의존성 1개 감소 — 공급망 표면 축소 (SEC-10).
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.clients.base import BaseHttpClient
from app.clients.protocols import LlmResponse
from app.core.enums import ApiName
from app.core.errors import ExternalServiceError

ENDPOINT = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
STRUCTURED_TOOL_NAME = "emit_result"


class AnthropicLlmClient:
    def __init__(
        self,
        http: BaseHttpClient,
        api_key: str,
        *,
        model: str = "claude-sonnet-5",
        read_timeout: float = 120.0,
    ) -> None:
        self._http = http
        self._headers = {
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        self._model = model
        self._read_timeout = read_timeout

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        tool_schema: dict[str, Any] | None = None,
    ) -> LlmResponse:
        body: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if tool_schema is not None:
            # BR-06 — 모델이 정해진 JSON 스키마로만 답하도록 강제한다.
            body["tools"] = [
                {
                    "name": STRUCTURED_TOOL_NAME,
                    "description": "정해진 스키마로 결과를 반환한다.",
                    "input_schema": tool_schema,
                }
            ]
            body["tool_choice"] = {"type": "tool", "name": STRUCTURED_TOOL_NAME}

        response: httpx.Response = await self._http.request(
            ApiName.ANTHROPIC,
            "POST",
            ENDPOINT,
            headers=self._headers,
            json=body,
            timeout=self._read_timeout,
        )
        return self._parse(response.json(), structured=tool_schema is not None)

    @staticmethod
    def _parse(payload: dict, *, structured: bool) -> LlmResponse:
        usage = payload.get("usage", {})
        blocks = payload.get("content", []) or []

        if structured:
            for block in blocks:
                if block.get("type") == "tool_use" and block.get("name") == STRUCTURED_TOOL_NAME:
                    return LlmResponse(
                        text=json.dumps(block.get("input", {}), ensure_ascii=False),
                        input_tokens=int(usage.get("input_tokens", 0) or 0),
                        output_tokens=int(usage.get("output_tokens", 0) or 0),
                        stop_reason=payload.get("stop_reason"),
                    )
            # 구조화 출력을 강제했는데 도구 블록이 없다 — 수용하지 않는다 (SEC-13).
            raise ExternalServiceError("LLM 응답에 구조화 결과가 없습니다")

        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        )
        return LlmResponse(
            text=text,
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
            stop_reason=payload.get("stop_reason"),
        )
