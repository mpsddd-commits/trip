"""헬스체크 테스트 — FR-34, ND-14.

🔴 핵심: **헬스체크가 외부 API 를 호출하지 않는다.**
   컨테이너 헬스체크는 30초마다 실행되므로, 여기서 지역검색을 부르면
   헬스체크만으로 하루 2,880회를 소모한다.
"""

from __future__ import annotations

import inspect

from app.api.routers import health as health_router


def test_liveness_is_always_ok(api_client) -> None:
    response = api_client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_modes_and_quota(api_client) -> None:
    response = api_client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] is True
    assert set(body) >= {"status", "modes", "quota", "circuits", "database"}


def test_readiness_reports_mock_mode(api_client) -> None:
    """FR-33 — 프론트가 이 값을 보고 "데모 데이터" 배너를 띄운다."""
    body = api_client.get("/api/health/ready").json()
    assert set(body["modes"].values()) == {"mock"}


def test_readiness_never_leaks_credentials(api_client) -> None:
    """SEP-3 — 키 값이 아니라 **설정 여부만** 노출한다."""
    raw = api_client.get("/api/health/ready").text
    assert "map_client_key_configured" in raw
    for leaked in ("client_secret", "api_key", "sk-ant"):
        assert leaked not in raw.lower()


def test_health_endpoints_make_no_external_calls(api_client) -> None:
    """ND-14 — 호출 후 쿼터 카운터가 증가하지 않아야 한다."""
    before = api_client.get("/api/health/ready").json()["quota"]
    for _ in range(5):
        api_client.get("/api/health")
        api_client.get("/api/health/ready")
    after = api_client.get("/api/health/ready").json()["quota"]
    assert before == after


def test_health_module_does_not_touch_external_clients() -> None:
    """구조 검증 — 헬스 라우터 소스에 외부 클라이언트 호출이 없어야 한다."""
    source = inspect.getsource(health_router)
    for forbidden in ("local_search", "content_search", "directions", "geocoding", ".llm"):
        assert forbidden not in source, f"헬스체크가 외부 클라이언트를 참조합니다: {forbidden}"
