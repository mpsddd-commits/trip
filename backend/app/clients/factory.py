"""C13 ClientFactory — 인증 정보에 따른 구현체 선택과 데코레이터 합성.

근거:
    DD-3 / FR-33
        인증 정보 유무 분기는 **이 지점에만** 존재한다.
        서비스·도메인 코드에는 `if mock:` 이 없다.
    DD-6  캐시 데코레이터는 **실제 구현체에만** 적용한다. 목은 감싸지 않는다.
    합성 순서: BaseHttpClient -> Real*Client -> Cached*Client
    부분 목 모드 지원: 지도 키는 있고 LLM 키만 없는 경우 LLM 만 목으로 대체
"""

from __future__ import annotations

import httpx

from app.clients.base import BaseHttpClient, QuotaGate
from app.clients.cache_decorator import (
    CacheStore,
    CachedContentSearchClient,
    CachedDirectionsClient,
    CachedGeocodingClient,
    CachedLocalSearchClient,
)
from app.clients.circuit import CircuitBreaker
from app.clients.mocks import (
    MockContentSearchClient,
    MockDirectionsClient,
    MockGeocodingClient,
    MockLlmClient,
    MockLocalSearchClient,
)
from app.clients.naver_content import NaverContentSearchClient
from app.clients.naver_local import NaverLocalSearchClient
from app.clients.ncp_directions import NcpDirectionsClient
from app.clients.ncp_geocoding import NcpGeocodingClient
from app.clients.anthropic_llm import AnthropicLlmClient
from app.clients.protocols import ClientBundle
from app.clients.semaphore import ExternalSemaphore
from app.core.config import Config
from app.core.enums import ApiName
from app.core.logging_config import get_logger

logger = get_logger(__name__)

MODE_REAL = "real"
MODE_MOCK = "mock"


class ClientFactory:
    def __init__(
        self,
        config: Config,
        *,
        cache_store: CacheStore | None = None,
        quota: QuotaGate | None = None,
    ) -> None:
        self.config = config
        self._cache_store = cache_store
        self._quota = quota
        self._modes: dict[ApiName, str] = {}
        self._http_client: httpx.AsyncClient | None = None
        # ND-14 — `/api/health/ready` 가 서킷 상태를 노출할 수 있도록 보관한다.
        self.circuit: CircuitBreaker | None = None

    # ------------------------------------------------------------------
    def build_all(self) -> ClientBundle:
        config = self.config
        credentials = config.credential_status()

        # SP-3 / ND-6 — 앱 수명 동안 단일 인스턴스, 커넥션 풀 재사용
        self._http_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            follow_redirects=True,
        )
        self.circuit = CircuitBreaker(
            failure_threshold=config.circuit_failure_threshold,
            open_seconds=config.circuit_open_seconds,
        )
        http = BaseHttpClient(
            self._http_client,
            circuit=self.circuit,
            semaphore=ExternalSemaphore(limit=config.external_concurrency),
            quota=self._quota,
            max_retries=config.http_max_retries,
        )

        naver_id = config.naver_client_id.get_secret_value() if config.naver_client_id else ""
        naver_secret = (
            config.naver_client_secret.get_secret_value() if config.naver_client_secret else ""
        )
        ncp_id = config.ncp_client_id.get_secret_value() if config.ncp_client_id else ""
        ncp_secret = (
            config.ncp_client_secret.get_secret_value() if config.ncp_client_secret else ""
        )
        llm_key = config.anthropic_api_key.get_secret_value() if config.anthropic_api_key else ""

        # --- 지역검색 (C7) ---
        if credentials[ApiName.NAVER_LOCAL]:
            local = self._wrap(
                CachedLocalSearchClient,
                NaverLocalSearchClient(
                    http, naver_id, naver_secret, read_timeout=config.http_read_timeout_sec
                ),
                config.cache_ttl_days("local_search"),
            )
            self._modes[ApiName.NAVER_LOCAL] = MODE_REAL
        else:
            local = MockLocalSearchClient()  # DD-6 — 목은 캐시로 감싸지 않는다
            self._modes[ApiName.NAVER_LOCAL] = MODE_MOCK

        # --- 블로그·이미지 (C8) ---
        if credentials[ApiName.NAVER_BLOG]:
            content = self._wrap(
                CachedContentSearchClient,
                NaverContentSearchClient(
                    http, naver_id, naver_secret, read_timeout=config.http_read_timeout_sec
                ),
                config.cache_ttl_days("blog"),
            )
            self._modes[ApiName.NAVER_BLOG] = MODE_REAL
            self._modes[ApiName.NAVER_IMAGE] = MODE_REAL
        else:
            content = MockContentSearchClient()
            self._modes[ApiName.NAVER_BLOG] = MODE_MOCK
            self._modes[ApiName.NAVER_IMAGE] = MODE_MOCK

        # --- Directions (C9) ---
        if credentials[ApiName.NCP_DIRECTIONS]:
            directions = self._wrap(
                CachedDirectionsClient,
                NcpDirectionsClient(
                    http, ncp_id, ncp_secret, read_timeout=config.http_read_timeout_sec
                ),
                config.cache_ttl_days("directions"),
            )
            self._modes[ApiName.NCP_DIRECTIONS] = MODE_REAL
        else:
            directions = MockDirectionsClient()
            self._modes[ApiName.NCP_DIRECTIONS] = MODE_MOCK

        # --- Geocoding (C10) ---
        if credentials[ApiName.NCP_GEOCODING]:
            geocoding = self._wrap(
                CachedGeocodingClient,
                NcpGeocodingClient(
                    http, ncp_id, ncp_secret, read_timeout=config.http_read_timeout_sec
                ),
                config.cache_ttl_days("geocode"),
            )
            self._modes[ApiName.NCP_GEOCODING] = MODE_REAL
        else:
            geocoding = MockGeocodingClient()
            self._modes[ApiName.NCP_GEOCODING] = MODE_MOCK

        # --- LLM (C11) — 캐시 대상 아님 ---
        if credentials[ApiName.ANTHROPIC]:
            llm = AnthropicLlmClient(
                http, llm_key, model=config.llm_model, read_timeout=config.llm_read_timeout_sec
            )
            self._modes[ApiName.ANTHROPIC] = MODE_REAL
        else:
            llm = MockLlmClient()
            self._modes[ApiName.ANTHROPIC] = MODE_MOCK

        mock_apis = [api.value for api, mode in self._modes.items() if mode == MODE_MOCK]
        if mock_apis:
            # SEP-3 — 어떤 API 가 목 모드인지만 알린다. 키 값은 절대 로그에 남기지 않는다.
            logger.warning("목 데이터 모드로 동작합니다", extra={"mock_apis": mock_apis})

        return ClientBundle(
            local_search=local,
            content_search=content,
            directions=directions,
            geocoding=geocoding,
            llm=llm,
        )

    def _wrap(self, decorator_cls, inner, ttl_days: int):  # type: ignore[no-untyped-def]
        """캐시 저장소가 주입된 경우에만 감싼다 (DD-15)."""
        if self._cache_store is None:
            return inner
        return decorator_cls(inner, self._cache_store, ttl_days)

    # ------------------------------------------------------------------
    def active_modes(self) -> dict[str, str]:
        """`/api/health/ready` 와 프론트 배너용 (FR-33)."""
        return {api.value: mode for api, mode in self._modes.items()}

    def is_fully_real(self) -> bool:
        return all(mode == MODE_REAL for mode in self._modes.values())

    def circuit_snapshot(self) -> dict[str, str]:
        """ND-14 — 헬스체크용 서킷 상태."""
        return self.circuit.snapshot() if self.circuit is not None else {}

    async def aclose(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
