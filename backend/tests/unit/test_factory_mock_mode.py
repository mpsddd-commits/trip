"""C13 ClientFactory 테스트 — DD-3, DD-6, FR-33.

인증 정보 유무에 따른 분기가 **이 지점에만** 존재하는지 확인한다.
"""

from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

from app.clients.cache_decorator import CacheStore, CachedLocalSearchClient
from app.clients.factory import MODE_MOCK, MODE_REAL, ClientFactory
from app.clients.mocks import MockLlmClient, MockLocalSearchClient
from app.clients.naver_local import NaverLocalSearchClient
from app.core.config import Config
from app.core.enums import ApiName


class _NoopStore(CacheStore):
    async def get(self, key: str) -> str | None:
        return None

    async def put(self, key: str, namespace: str, payload: str, ttl_days: int) -> None:
        return None


def _config(**overrides) -> Config:
    base = {
        "naver_client_id": None,
        "naver_client_secret": None,
        "ncp_client_id": None,
        "ncp_client_secret": None,
        "anthropic_api_key": None,
    }
    base.update(overrides)
    return Config(**base)


@pytest.fixture()
async def _closing():
    factories: list[ClientFactory] = []
    yield factories
    for factory in factories:
        await factory.aclose()


async def test_no_credentials_yields_all_mock(_closing) -> None:
    """FR-33 — 인증 정보 없이도 전 기능이 목 모드로 동작한다 (QG-7)."""
    factory = ClientFactory(_config())
    _closing.append(factory)
    bundle = factory.build_all()

    assert isinstance(bundle.local_search, MockLocalSearchClient)
    assert isinstance(bundle.llm, MockLlmClient)
    assert set(factory.active_modes().values()) == {MODE_MOCK}
    assert factory.is_fully_real() is False


async def test_partial_credentials_yield_partial_mock(_closing) -> None:
    """부분 목 모드 — 네이버 키는 있고 LLM 키만 없는 경우."""
    factory = ClientFactory(
        _config(naver_client_id="id", naver_client_secret="secret"),
        cache_store=_NoopStore(),
    )
    _closing.append(factory)
    bundle = factory.build_all()

    modes = factory.active_modes()
    assert modes[ApiName.NAVER_LOCAL.value] == MODE_REAL
    assert modes[ApiName.ANTHROPIC.value] == MODE_MOCK
    assert modes[ApiName.NCP_DIRECTIONS.value] == MODE_MOCK
    assert isinstance(bundle.llm, MockLlmClient)


async def test_real_client_is_wrapped_with_cache(_closing) -> None:
    """DD-15 — 실제 구현체는 캐시 데코레이터로 감싼다."""
    factory = ClientFactory(
        _config(naver_client_id="id", naver_client_secret="secret"),
        cache_store=_NoopStore(),
    )
    _closing.append(factory)
    bundle = factory.build_all()
    assert isinstance(bundle.local_search, CachedLocalSearchClient)


async def test_mock_client_is_not_wrapped_with_cache(_closing) -> None:
    """DD-6 — 목은 이미 결정적이므로 캐시로 감싸지 않는다."""
    factory = ClientFactory(_config(), cache_store=_NoopStore())
    _closing.append(factory)
    bundle = factory.build_all()
    assert isinstance(bundle.local_search, MockLocalSearchClient)
    assert not isinstance(bundle.local_search, CachedLocalSearchClient)


async def test_mock_local_search_supports_grounding(_closing) -> None:
    """목 모드에서도 그라운딩(C23)이 성공해야 파이프라인 전체가 동작한다."""
    client = MockLocalSearchClient()
    results = await client.search("부산 광안리 해수욕장")
    assert results
    assert results[0].name == "광안리 해수욕장"  # 질의의 장소명을 그대로 반환
    assert 33.0 <= results[0].coordinate.lat <= 39.0


async def test_mock_results_are_deterministic() -> None:
    """DD-6 의 전제 — 목은 결정적이므로 캐시가 불필요하다."""
    client = MockLocalSearchClient()
    first = await client.search("제주 성산일출봉")
    second = await client.search("제주 성산일출봉")
    assert first == second


# ---------------------------------------------------------------------------
# 구조 검증 — DD-3
# ---------------------------------------------------------------------------
_SERVICE_LIKE_DIRS = ("services", "domain")

# 목 모드 **분기**를 나타내는 패턴만 잡는다.
# `PlaceSource.MOCK` 처럼 출처를 기록하는 열거형 참조는 정상이므로 제외한다.
_MOCK_BRANCH_PATTERNS = (
    re.compile(r"\bif\s+[^\n]*\bis_mock\b"),
    re.compile(r"\bif\s+[^\n]*\bmock_mode\b"),
    re.compile(r"\bif\s+[^\n]*\buse_mock\b"),
    re.compile(r"\bfrom\s+app\.clients\.mocks\b"),
    re.compile(r"\bimport\s+.*\bmocks\b"),
    re.compile(r"\bMock[A-Z]\w*Client\b"),
)


def test_no_mock_branching_outside_the_factory() -> None:
    """DD-3 — 서비스·도메인 계층에 목 모드 분기가 새어나가면 안 된다.

    목 선택은 C13 주입 시점에만 존재해야 한다. 누군가 편의를 위해
    `if is_mock:` 을 넣거나 목 클래스를 직접 import 하면 이 테스트가 실패한다.
    """
    app_root = Path(inspect.getfile(ClientFactory)).parent.parent
    offenders: list[str] = []
    for directory in _SERVICE_LIKE_DIRS:
        for path in (app_root / directory).rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for pattern in _MOCK_BRANCH_PATTERNS:
                if pattern.search(text):
                    offenders.append(f"{path.relative_to(app_root)} :: {pattern.pattern}")
    assert not offenders, f"서비스/도메인 계층에 목 분기가 있습니다: {offenders}"


def test_domain_layer_has_no_app_imports() -> None:
    """DD-16 — `domain/` 은 app 내부의 다른 계층을 import 하지 않는다.

    이 규칙이 깨지면 PBT(P-01~P-22)를 네트워크·DB 없이 실행할 수 없게 된다.
    """
    app_root = Path(inspect.getfile(ClientFactory)).parent.parent
    forbidden = re.compile(r"^\s*(?:from|import)\s+app\.(?!domain)", re.MULTILINE)
    offenders = [
        str(path.relative_to(app_root))
        for path in (app_root / "domain").rglob("*.py")
        if forbidden.search(path.read_text(encoding="utf-8"))
    ]
    assert not offenders, f"domain 계층이 다른 계층을 import 합니다: {offenders}"
