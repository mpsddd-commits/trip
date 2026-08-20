"""`GET /api/config` 테스트 — 개정 A-1.

🔴 핵심: **검색 API 키와 LLM 키가 응답에 절대 포함되지 않는다** (SEC-11).
   지도 키만 예외이며, 이는 SDK 특성상 브라우저 노출이 불가피하기 때문이다 (CON-3).
"""

from __future__ import annotations

import inspect

from app.api.routers import config as config_router
from app.api.schemas import RuntimeConfigOut


def test_config_returns_modes_and_limits(api_client) -> None:
    response = api_client.get("/api/config")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"map_client_key", "modes", "limits"}
    assert set(body["limits"]) == {"max_trip_days", "max_items_per_day", "max_items_per_trip"}


def test_limits_match_server_settings(api_client) -> None:
    """WBR-10 — 프론트가 이 값을 폼 검증에 그대로 쓴다. 서버 상한과 같아야 한다."""
    limits = api_client.get("/api/config").json()["limits"]
    assert limits["max_trip_days"] == 10  # BR-01
    assert limits["max_items_per_day"] == 15  # BR-02
    assert limits["max_items_per_trip"] == 100  # BR-02


def test_modes_reports_mock_state(api_client) -> None:
    """FR-33 / WBR-30 — 데모 배너의 데이터 원천."""
    modes = api_client.get("/api/config").json()["modes"]
    assert modes
    assert set(modes.values()) <= {"real", "mock"}


def test_map_key_is_null_when_unset(api_client) -> None:
    assert api_client.get("/api/config").json()["map_client_key"] is None


# ---------------------------------------------------------------------------
# 🔴 비밀 노출 방지 (SEC-11)
# ---------------------------------------------------------------------------
_FORBIDDEN_FIELDS = (
    "naver_client_id",
    "naver_client_secret",
    "ncp_client_id",
    "ncp_client_secret",
    "anthropic_api_key",
    "api_key",
    "secret",
)


def test_schema_has_no_secret_fields() -> None:
    """응답 스키마 자체에 비밀 필드가 없어야 한다 — 실수로 채워질 경로를 없앤다."""
    fields = set(RuntimeConfigOut.model_fields)
    assert fields == {"map_client_key", "modes", "limits"}
    for forbidden in _FORBIDDEN_FIELDS:
        assert forbidden not in fields


def test_response_body_contains_no_secret_values(api_client) -> None:
    """실제 응답 본문에 **비밀 값**이 섞이지 않는지 확인한다.

    🔴 이전 판은 응답 본문에서 `"anthropic"` 같은 **벤더 이름**을 찾아 실패했다.
       그런데 `modes` 는 FR-33 이 요구하는 필드이고 `{"anthropic": "mock"}` 처럼
       **어떤 기능이 데모인지** 알리는 값이다. 비밀이 아니다.
       이름이 아니라 **값의 모양**을 검사해야 의미가 있다.
    """
    body = api_client.get("/api/config").json()
    raw = api_client.get("/api/config").text

    # 실제 자격증명의 모양이 본문에 나타나면 안 된다.
    for marker in ("client_secret", "sk-ant-", "x-ncp-apigw", "x-naver-client"):
        assert marker.lower() not in raw.lower()

    # modes 의 값은 mock/real 두 가지뿐이다 — 키 값이 실려 나갈 자리가 없다.
    assert set(body["modes"].values()) <= {"mock", "real"}


def test_configured_secret_values_never_appear_in_body(tmp_path, monkeypatch) -> None:
    """설정에 실제 값이 채워져 있어도 본문에 나오지 않는다.

    가짜 자격증명을 환경변수로 주입해 앱을 새로 띄우고, 그 문자열이 응답 어디에도
    없음을 확인한다. 필드 이름 목록을 유지보수하지 않아도 되므로 비밀 설정이
    새로 추가돼도 자동으로 걸린다.

    ⚠️ `Config` 는 frozen 모델이라 `monkeypatch.setattr` 로는 바꿀 수 없다.
       환경변수를 세우고 `get_config.cache_clear()` 로 다시 읽게 하는 것이 유일한 경로다.
    """
    from fastapi.testclient import TestClient

    from app.core.config import get_config
    from app.main import create_app

    sentinel = "SENTINEL-SECRET-VALUE-9f3a"
    monkeypatch.setenv("DATABASE_PATH", ":memory:")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "static"))
    for name in (
        "NAVER_CLIENT_ID",
        "NAVER_CLIENT_SECRET",
        "NCP_API_KEY_ID",
        "NCP_API_KEY",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.setenv(name, sentinel)

    get_config.cache_clear()
    try:
        with TestClient(create_app()) as client:
            raw = client.get("/api/config").text
        assert sentinel not in raw
    finally:
        get_config.cache_clear()



def test_router_does_not_reference_secret_settings() -> None:
    """구조 검증 — 라우터 소스가 비밀 설정을 읽지 않아야 한다.

    나중에 누가 편의를 위해 키를 하나 더 실으면 즉시 실패한다.
    """
    source = inspect.getsource(config_router)
    for forbidden in ("naver_client_secret", "ncp_client_secret", "anthropic_api_key"):
        assert forbidden not in source, f"설정 라우터가 비밀 값을 참조합니다: {forbidden}"


def test_config_makes_no_external_calls(api_client) -> None:
    """ND-14 — 설정 조회가 외부 API 를 부르면 안 된다."""
    before = api_client.get("/api/health/ready").json()["quota"]
    for _ in range(5):
        api_client.get("/api/config")
    after = api_client.get("/api/health/ready").json()["quota"]
    assert before == after
