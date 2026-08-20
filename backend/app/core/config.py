"""C1 Config — 환경변수 기반 설정 단일 공급원.

근거:
    NFR-15  모든 설정은 환경변수로 주입, 소스에 인증 정보 미포함
    SEP-3   인증 정보는 SecretStr 로 보관하고 repr/로그/오류에 노출하지 않음
    FR-33   인증 정보 누락은 오류가 아니라 목(mock) 모드 전환 신호
    NFR-14 / ID-11  BIND_HOST 는 Compose 포트 매핑용. 0.0.0.0 이면 경고
    logical-components.md §5 설정 47개
"""

from __future__ import annotations

import functools
import logging

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.enums import ApiName

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


class Config(BaseSettings):
    """읽기 전용 설정 객체. 부팅 시 1회 생성한다."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    # ------------------------------------------------------------------
    # 인증 정보 — 전부 선택. 비어 있으면 해당 API 만 목 모드로 동작한다 (FR-33)
    # ------------------------------------------------------------------
    naver_client_id: SecretStr | None = None
    naver_client_secret: SecretStr | None = None
    ncp_client_id: SecretStr | None = None
    ncp_client_secret: SecretStr | None = None
    # 지도 SDK 클라이언트 키는 구조상 브라우저에 노출된다 (CON-3).
    # 도메인 화이트리스트로만 방어 가능하며, 그 사실을 README 에 명시한다.
    ncp_map_client_key: str | None = None
    anthropic_api_key: SecretStr | None = None

    # ------------------------------------------------------------------
    # 서버 / 배포
    # ------------------------------------------------------------------
    bind_host: str = "127.0.0.1"
    port: int = 8200
    cors_allow_origins: str = ""  # 쉼표 구분. 비어 있으면 CORS 미들웨어 비활성 (ND-12)
    database_path: str = "./data/trip.db"
    log_dir: str = "./logs"
    log_level: str = "INFO"
    app_timezone: str = "Asia/Seoul"
    static_dir: str = "./static"

    # ------------------------------------------------------------------
    # 복원력 (RP-1, RP-2 / BR-47)
    # ------------------------------------------------------------------
    http_connect_timeout_sec: float = 5.0
    http_read_timeout_sec: float = 10.0
    llm_read_timeout_sec: float = 120.0
    http_max_retries: int = 3
    circuit_failure_threshold: int = 5
    circuit_open_seconds: float = 60.0

    # ------------------------------------------------------------------
    # 동시성 (SP-3 / ND-3, ND-17, ND-18)
    # ------------------------------------------------------------------
    max_concurrent_jobs: int = 3
    job_parallelism: int = 5
    external_concurrency: int = 5
    db_thread_pool_size: int = 8

    # ------------------------------------------------------------------
    # 레이트 리밋 / 쿼터 (BR-49, BR-50)
    # ------------------------------------------------------------------
    rate_expensive_per_hour: int = 5
    rate_expensive_global_per_day: int = 50
    rate_external_per_min: int = 60
    rate_cheap_per_min: int = 300
    quota_naver_local_per_day: int = 25_000

    # ------------------------------------------------------------------
    # 캐시 / 수명 (BR-48, BR-56, BR-57, BR-59)
    # ------------------------------------------------------------------
    cache_ttl_local_search_days: int = 7
    cache_ttl_directions_days: int = 1
    cache_ttl_content_days: int = 3
    cache_ttl_geocode_days: int = 30
    cache_grace_days: int = 7
    job_retention_hours: int = 24
    audit_retention_days: int = 90

    # ------------------------------------------------------------------
    # 도메인 규칙 설정값 (BR-01 ~ BR-26, BR-52)
    # ------------------------------------------------------------------
    max_trip_days: int = 10
    max_items_per_day: int = 15
    max_items_per_trip: int = 100
    max_request_body_bytes: int = 1_048_576

    llm_model: str = "claude-sonnet-5"
    llm_max_retries: int = 2
    llm_max_tokens: int = 8_000

    resolve_similarity_threshold: float = Field(default=0.60, ge=0.0, le=1.0)

    walk_detour: float = 1.3
    walk_speed_kmh: float = 4.5
    walk_min_sec: int = 180
    transit_detour: float = 1.4
    transit_speed_kmh: float = 20.0
    transit_wait_sec: int = 600
    transit_min_sec: int = 600
    car_fallback_detour: float = 1.4
    car_fallback_speed_kmh: float = 30.0
    car_min_sec: int = 300

    optimize_no_improve_limit: int = 50
    optimize_max_iter: int = 1000
    optimize_time_limit_ms: int = 200

    # ------------------------------------------------------------------
    # 검증
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def _validate(self) -> "Config":
        if self.walk_speed_kmh <= 0 or self.transit_speed_kmh <= 0 or self.car_fallback_speed_kmh <= 0:
            raise ValueError("이동 속도 설정은 0보다 커야 합니다.")
        if self.max_items_per_day <= 0 or self.max_trip_days <= 0:
            raise ValueError("MAX_ITEMS_PER_DAY 와 MAX_TRIP_DAYS 는 1 이상이어야 합니다.")
        if self.optimize_time_limit_ms <= 0:
            raise ValueError("OPTIMIZE_TIME_LIMIT_MS 는 1 이상이어야 합니다.")
        return self

    # ------------------------------------------------------------------
    # 파생 정보
    # ------------------------------------------------------------------
    def credential_status(self) -> dict[ApiName, bool]:
        """API 별 인증 정보 보유 여부.

        C13 ClientFactory 가 이 값으로 실제 구현과 목 구현을 선택한다 (DD-3, FR-33).
        값 자체는 절대 반환하지 않는다 (SEP-3).
        """
        naver = bool(self.naver_client_id and self.naver_client_secret)
        ncp = bool(self.ncp_client_id and self.ncp_client_secret)
        return {
            ApiName.NAVER_LOCAL: naver,
            ApiName.NAVER_BLOG: naver,
            ApiName.NAVER_IMAGE: naver,
            ApiName.NCP_DIRECTIONS: ncp,
            ApiName.NCP_GEOCODING: ncp,
            ApiName.ANTHROPIC: bool(self.anthropic_api_key),
        }

    def is_loopback_only(self) -> bool:
        """BIND_HOST 가 루프백 전용인지 (NFR-14)."""
        return self.bind_host in _LOOPBACK_HOSTS

    def cors_origins(self) -> list[str]:
        """허용 오리진 목록. 와일드카드는 어떤 경우에도 반환하지 않는다 (ND-12, SEC-08)."""
        origins = [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]
        return [o for o in origins if o != "*"]

    def cache_ttl_days(self, namespace: str) -> int:
        """캐시 네임스페이스별 TTL(일)."""
        return {
            "local_search": self.cache_ttl_local_search_days,
            "directions": self.cache_ttl_directions_days,
            "blog": self.cache_ttl_content_days,
            "image": self.cache_ttl_content_days,
            "geocode": self.cache_ttl_geocode_days,
        }.get(namespace, 1)

    def __repr__(self) -> str:  # pragma: no cover - 방어적 표현
        """인증 정보가 표현식에 새어나가지 않도록 요약만 반환한다 (SEP-3, SEC-12)."""
        return f"<Config bind_host={self.bind_host} port={self.port}>"

    __str__ = __repr__


@functools.lru_cache(maxsize=1)
def get_config() -> Config:
    """설정 싱글턴. 부팅 시 1회 생성되고 이후 변경되지 않는다."""
    config = Config()
    if not config.is_loopback_only():
        # NFR-14 / SEC-07 — 루프백 밖 노출은 의도적 선택이어야 하며 흔적을 남긴다.
        logging.getLogger(__name__).warning(
            "BIND_HOST=%s — 서비스가 루프백 밖으로 노출됩니다. "
            "인증이 없는 구성이므로 같은 네트워크의 누구나 접근할 수 있습니다. "
            "안드로이드 연동이 끝나면 127.0.0.1 로 되돌리세요.",
            config.bind_host,
        )
    return config
