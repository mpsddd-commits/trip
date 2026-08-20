"""오류 응답 테스트 — BR-58, SEC-09, SEC-15, Q6=A(RFC 9457).

🔴 핵심: **사용자 응답에 내부 정보가 절대 새어나가지 않는다.**
"""

from __future__ import annotations

import pytest

from app.core.enums import ErrorCode
from app.core.errors import HTTP_STATUS, USER_MESSAGES

_LEAK_MARKERS = (
    "Traceback",
    "File \"",
    "sqlalchemy",
    "sqlite",
    "/app/",
    "app.services",
    "app.storage",
    "fastapi",
    "pydantic",
    "Exception",
)


def test_all_error_codes_have_fixed_messages() -> None:
    """BR-58 — 6종 코드 전부에 고정 문구가 매핑되어 있다."""
    assert set(USER_MESSAGES) == set(ErrorCode)
    assert set(HTTP_STATUS) == set(ErrorCode)
    assert len(ErrorCode) == 6


def test_messages_contain_no_internal_hints() -> None:
    for message in USER_MESSAGES.values():
        for marker in _LEAK_MARKERS:
            assert marker.lower() not in message.lower()


def test_not_found_returns_problem_details(api_client) -> None:
    response = api_client.get("/api/trips/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    body = response.json()
    for field in ("type", "title", "status", "detail", "instance", "code", "correlation_id"):
        assert field in body
    assert body["detail"] == USER_MESSAGES[ErrorCode.NOT_FOUND]


def test_validation_error_hides_field_details(api_client, sample_trip_payload) -> None:
    """SEC-09 — 어떤 필드가 왜 틀렸는지는 로그에만 남긴다."""
    response = api_client.post("/api/trips", json={**sample_trip_payload, "party_size": -1})
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == USER_MESSAGES[ErrorCode.VALIDATION_ERROR]
    raw = response.text
    assert "party_size" not in raw
    assert "ensure this value" not in raw


@pytest.mark.parametrize(
    "path",
    [
        "/api/trips/00000000-0000-0000-0000-000000000000",
        "/api/jobs/00000000-0000-0000-0000-000000000000",
        "/api/shared/00000000000000000000000000",
    ],
)
def test_no_stack_trace_in_any_error_response(api_client, path: str) -> None:
    raw = api_client.get(path).text
    for marker in _LEAK_MARKERS:
        assert marker not in raw


def test_correlation_id_is_returned_for_tracing(api_client) -> None:
    """NFR-8 — 사용자에게는 상관관계 ID 만 준다. 상세는 로그에서 찾는다."""
    response = api_client.get("/api/trips/00000000-0000-0000-0000-000000000000")
    assert response.json()["correlation_id"]
    assert response.headers["X-Correlation-Id"]


def test_incoming_correlation_id_is_preserved(api_client) -> None:
    response = api_client.get("/api/health", headers={"X-Correlation-Id": "trace-123"})
    assert response.headers["X-Correlation-Id"] == "trace-123"


def test_api_docs_are_not_exposed(api_client) -> None:
    """SEC-09 — 샘플·문서 엔드포인트를 배포에 노출하지 않는다."""
    assert api_client.get("/docs").status_code in (404, 405)
    assert api_client.get("/redoc").status_code in (404, 405)


def test_unknown_api_path_returns_json_not_spa(api_client) -> None:
    """SPA catch-all 이 `/api/*` 를 삼키면 안 된다."""
    response = api_client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
