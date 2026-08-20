"""보안 헤더·CORS 테스트 — SEC-04, SEC-08, CA-4, ND-11, ND-12."""

from __future__ import annotations

import pytest

from app.core.security_headers import CSP_DIRECTIVES, CSP_VALUE


def test_required_headers_are_present(api_client) -> None:
    """SEC-04 — 4종 헤더는 항상 부여된다."""
    response = api_client.get("/api/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Content-Security-Policy"] == CSP_VALUE


def test_hsts_is_absent_over_plain_http(api_client) -> None:
    """CA-4 — 평문 HTTP 로 HSTS 를 보내면 의미가 없고 오해를 부른다."""
    response = api_client.get("/api/health")
    assert "Strict-Transport-Security" not in response.headers


def test_hsts_is_present_behind_tls_proxy(api_client) -> None:
    """운영 배포(CON-5)에서 리버스 프록시 뒤에 놓이면 부여된다."""
    response = api_client.get("/api/health", headers={"x-forwarded-proto": "https"})
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


# ---------------------------------------------------------------------------
# CSP 세부 (SEC-04 검증 요건)
# ---------------------------------------------------------------------------
def test_csp_never_allows_unsafe_script() -> None:
    """🔴 `script-src` 에 `unsafe-inline` / `unsafe-eval` 을 절대 허용하지 않는다."""
    script_src = next(d for d in CSP_DIRECTIVES if d.startswith("script-src"))
    assert "unsafe-inline" not in script_src
    assert "unsafe-eval" not in script_src
    assert "unsafe-eval" not in CSP_VALUE


def test_csp_unsafe_inline_is_limited_to_styles() -> None:
    """예외는 `style-src` 하나뿐이며 사유가 문서화되어 있다 (지도 SDK 인라인 스타일)."""
    with_unsafe = [d for d in CSP_DIRECTIVES if "unsafe-inline" in d]
    assert len(with_unsafe) == 1
    assert with_unsafe[0].startswith("style-src")


def test_csp_restricts_defaults_and_framing() -> None:
    assert "default-src 'self'" in CSP_DIRECTIVES
    assert "object-src 'none'" in CSP_DIRECTIVES
    assert "frame-ancestors 'none'" in CSP_DIRECTIVES


def test_csp_allows_naver_map_sdk() -> None:
    """지도 SDK 가 로드되어야 한다. ⚠️ 실제 도메인은 Build & Test 에서 확정한다."""
    assert "oapi.map.naver.com" in CSP_VALUE
    assert "map.naver.com" in CSP_VALUE


# ---------------------------------------------------------------------------
# CORS (ND-12, SEC-08)
# ---------------------------------------------------------------------------
def test_cors_is_disabled_by_default(api_client) -> None:
    """UD-8 단일 오리진이므로 기본적으로 CORS 미들웨어가 붙지 않는다."""
    response = api_client.get(
        "/api/health", headers={"Origin": "https://evil.example"}
    )
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


@pytest.mark.parametrize("value", ["*", " * ", "*,http://localhost:5273"])
def test_wildcard_origin_is_never_accepted(value: str) -> None:
    """SEC-08 — 와일드카드는 어떤 경우에도 허용 목록에 들어가지 않는다."""
    from app.core.config import Config

    config = Config(cors_allow_origins=value)
    assert "*" not in config.cors_origins()


def test_explicit_dev_origin_is_parsed() -> None:
    from app.core.config import Config

    config = Config(cors_allow_origins="http://localhost:5273, http://127.0.0.1:5273")
    assert config.cors_origins() == ["http://localhost:5273", "http://127.0.0.1:5273"]
