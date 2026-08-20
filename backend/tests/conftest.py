"""pytest 공통 설정과 픽스처.

PBT-08 / PBT-R4:
    - 셰링킹은 Hypothesis 기본값(활성)을 유지한다. 비활성화하지 않는다.
    - 실패 시 재현용 blob(@reproduce_failure)과 최소 반례를 출력하도록 print_blob 을 켠다.
    - CI 프로파일은 예제 수를 늘린다. 활성화: HYPOTHESIS_PROFILE=ci

NFR-10: API 테스트도 네트워크에 의존하지 않는다.
    인증 정보를 비운 채 기동하므로 C13 이 목 구현을 주입한다 (FR-33, DD-3).
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from hypothesis import HealthCheck, Verbosity, settings

settings.register_profile(
    "default",
    max_examples=200,
    deadline=None,
    print_blob=True,
    derandomize=False,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "ci",
    max_examples=500,
    deadline=None,
    print_blob=True,
    derandomize=False,
    verbosity=Verbosity.normal,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


# ---------------------------------------------------------------------------
# API 테스트용 앱 픽스처
# ---------------------------------------------------------------------------
_CREDENTIAL_ENV = (
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "NCP_CLIENT_ID",
    "NCP_CLIENT_SECRET",
    "NCP_MAP_CLIENT_KEY",
    "ANTHROPIC_API_KEY",
)


@pytest.fixture()
def api_client(tmp_path, monkeypatch) -> Iterator:
    """인메모리 DB + 목 클라이언트로 기동한 TestClient."""
    from fastapi.testclient import TestClient

    from app.core.config import get_config

    # 실 인증 정보가 환경에 있어도 테스트는 목 모드로 돈다 (NFR-10).
    for name in _CREDENTIAL_ENV:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATABASE_PATH", ":memory:")
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("STATIC_DIR", str(tmp_path / "static"))
    # 레이트 리밋이 테스트를 방해하지 않도록 넉넉히 (BR-49 자체는 별도 테스트에서 검증)
    monkeypatch.setenv("RATE_CHEAP_PER_MIN", "10000")
    monkeypatch.setenv("RATE_EXTERNAL_PER_MIN", "10000")
    monkeypatch.setenv("RATE_EXPENSIVE_PER_HOUR", "1000")
    monkeypatch.setenv("RATE_EXPENSIVE_GLOBAL_PER_DAY", "10000")

    get_config.cache_clear()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        yield client
    get_config.cache_clear()


@pytest.fixture()
def sample_trip_payload() -> dict:
    return {
        "title": "부산 2박3일",
        "destination": "부산",
        "start_date": "2026-09-01",
        "end_date": "2026-09-02",
        "party_size": 2,
        "style_tags": ["맛집"],
        "default_travel_mode": "WALK",
    }
