"""애플리케이션 컨테이너와 FastAPI 의존성.

배치 주석: 계획서에 없던 파일이다. `main.py` 에 배선을 전부 넣으면 라우터가
전역 상태에 의존하게 되고 테스트가 어려워진다. 조립을 한 곳에 모았다.

근거:
    DD-3   목 선택은 C13 주입 시점에만 — 이 컨테이너가 그 지점이다
    ND-18  DB 접근은 DbExecutor 경유
    BR-49  라우터마다 등급별 레이트 리밋 의존성 부착
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.clients.cache_decorator import CacheStore
from app.clients.factory import ClientFactory
from app.core.config import Config
from app.core.enums import ApiName, EndpointTier
from app.core.logging_config import get_logger
from app.core.rate_limit import RateLimiter
from app.core.scheduler import MaintenanceScheduler
from app.domain.estimator import EstimatorParams
from app.domain.optimizer import OptimizeLimits
from app.services.generation_service import ItineraryGenerationService
from app.services.job_runner import JobRunner
from app.services.job_service import JobService
from app.services.llm_draft import LlmDraftGenerator
from app.services.place_resolver import PlaceResolver
from app.services.place_search import PlaceSearchService
from app.services.quota_service import QuotaService
from app.services.recommendation import RecommendationService
from app.services.travel_matrix import TravelMatrixService
from app.services.trip_service import TripService
from app.storage.database import Database
from app.storage.db_executor import DbExecutor
from app.storage.migrations import run_migrations
from app.storage.repositories import (
    AuditLogRepository,
    CacheRepository,
    QuotaRepository,
)

logger = get_logger(__name__)


class RepositoryCacheStore(CacheStore):
    """DD-7 — C12 가 storage 구체 타입에 의존하지 않도록 하는 어댑터."""

    def __init__(self, database: Database, executor: DbExecutor) -> None:
        self._db = database
        self._executor = executor

    async def get(self, key: str) -> str | None:
        def _get() -> str | None:
            with self._db.session_scope() as session:
                return CacheRepository(session).get(key)

        return await self._executor.run(_get)

    async def put(self, key: str, namespace: str, payload: str, ttl_days: int) -> None:
        def _put() -> None:
            with self._db.session_scope() as session:
                CacheRepository(session).put(key, namespace, payload, ttl_days)

        await self._executor.run(_put)


@dataclass
class Container:
    config: Config
    database: Database
    executor: DbExecutor
    quota: QuotaService
    rate_limiter: RateLimiter
    factory: ClientFactory
    trips: TripService
    jobs: JobService
    runner: JobRunner
    generation: ItineraryGenerationService
    place_search: PlaceSearchService
    recommendation: RecommendationService
    scheduler: MaintenanceScheduler

    # ------------------------------------------------------------------
    @classmethod
    def build(cls, config: Config) -> "Container":
        database = Database(config.database_path)
        run_migrations(database.engine)
        executor = DbExecutor(max_workers=config.db_thread_pool_size)

        quota = QuotaService(
            daily_limits={ApiName.NAVER_LOCAL.value: config.quota_naver_local_per_day},
            load_fn=_make_quota_loader(database, executor),
            flush_fn=_make_quota_flusher(database, executor),
        )
        rate_limiter = RateLimiter(
            expensive_per_hour=config.rate_expensive_per_hour,
            expensive_global_per_day=config.rate_expensive_global_per_day,
            external_per_min=config.rate_external_per_min,
            cheap_per_min=config.rate_cheap_per_min,
            global_counter=quota,
        )

        factory = ClientFactory(
            config,
            cache_store=RepositoryCacheStore(database, executor),
            quota=quota,
        )
        clients = factory.build_all()

        estimator_params = EstimatorParams(
            walk_detour=config.walk_detour,
            walk_speed_kmh=config.walk_speed_kmh,
            walk_min_sec=config.walk_min_sec,
            transit_detour=config.transit_detour,
            transit_speed_kmh=config.transit_speed_kmh,
            transit_wait_sec=config.transit_wait_sec,
            transit_min_sec=config.transit_min_sec,
            car_fallback_detour=config.car_fallback_detour,
            car_fallback_speed_kmh=config.car_fallback_speed_kmh,
            car_min_sec=config.car_min_sec,
        )
        optimize_limits = OptimizeLimits(
            no_improve_limit=config.optimize_no_improve_limit,
            max_iter=config.optimize_max_iter,
            time_limit_ms=config.optimize_time_limit_ms,
        )

        draft = LlmDraftGenerator(
            clients.llm,
            max_tokens=config.llm_max_tokens,
            max_retries=config.llm_max_retries,
            max_items_per_day=config.max_items_per_day,
        )
        trips = TripService(
            database,
            executor,
            max_trip_days=config.max_trip_days,
            max_items_per_day=config.max_items_per_day,
            max_items_per_trip=config.max_items_per_trip,
        )
        jobs = JobService(database, executor)

        return cls(
            config=config,
            database=database,
            executor=executor,
            quota=quota,
            rate_limiter=rate_limiter,
            factory=factory,
            trips=trips,
            jobs=jobs,
            runner=JobRunner(max_concurrent=config.max_concurrent_jobs),
            generation=ItineraryGenerationService(
                draft_generator=draft,
                resolver=PlaceResolver(
                    clients.local_search,
                    similarity_threshold=config.resolve_similarity_threshold,
                    parallelism=config.job_parallelism,
                ),
                matrix_service=TravelMatrixService(
                    clients.directions,
                    params=estimator_params,
                    parallelism=config.job_parallelism,
                ),
                trip_service=trips,
                job_service=jobs,
                estimator_params=estimator_params,
                optimize_limits=optimize_limits,
            ),
            place_search=PlaceSearchService(clients.local_search),
            recommendation=RecommendationService(clients.content_search, draft),
            scheduler=MaintenanceScheduler(),
        )

    # ------------------------------------------------------------------
    async def startup(self) -> None:
        await self.quota.load()  # SP-4 — 재시작 우회 방지
        await self.jobs.recover_orphans()  # RP-4 — 고아 job 정리

        self.scheduler.register("quota_flush", self.quota.flush)
        self.scheduler.register(
            "purge_jobs", lambda: self.jobs.purge_completed(self.config.job_retention_hours)
        )
        self.scheduler.register("purge_cache", self._purge_cache)
        self.scheduler.register("purge_audit", self._purge_audit)
        self.scheduler.register("prune_rate_limit", self._prune_rate_limit)
        await self.scheduler.start()

    async def shutdown(self) -> None:
        await self.scheduler.stop()
        await self.runner.shutdown()
        await self.quota.flush()  # 종료 전 마지막 플러시 (CD-1)
        await self.factory.aclose()
        self.executor.shutdown()
        self.database.dispose()

    # ------------------------------------------------------------------
    async def _purge_cache(self) -> int:
        def _run() -> int:
            with self.database.session_scope() as session:
                return CacheRepository(session).purge_expired(self.config.cache_grace_days)

        return await self.executor.run(_run)

    async def _purge_audit(self) -> int:
        def _run() -> int:
            with self.database.session_scope() as session:
                return AuditLogRepository(session).purge_older_than(
                    self.config.audit_retention_days
                )

        return await self.executor.run(_run)

    async def _prune_rate_limit(self) -> int:
        self.rate_limiter.prune()
        return 0


def _make_quota_loader(database: Database, executor: DbExecutor):  # type: ignore[no-untyped-def]
    async def _load() -> dict[str, int]:
        def _run() -> dict[str, int]:
            with database.session_scope() as session:
                usage = QuotaRepository(session).usage_today()
                return {key: value["call_count"] for key, value in usage.items()}

        return await executor.run(_run)

    return _load


def _make_quota_flusher(database: Database, executor: DbExecutor):  # type: ignore[no-untyped-def]
    async def _flush(pending: dict[str, int]) -> None:
        def _run() -> None:
            with database.session_scope() as session:
                repo = QuotaRepository(session)
                for key, delta in pending.items():
                    repo.increment(key, count=delta)

        await executor.run(_run)

    return _flush


# ---------------------------------------------------------------------------
# FastAPI 의존성
# ---------------------------------------------------------------------------
def get_container(request: Request) -> Container:
    return request.app.state.container


ContainerDep = Annotated[Container, Depends(get_container)]


def rate_limit(tier: EndpointTier):  # type: ignore[no-untyped-def]
    """BR-49 — 등급별 레이트 리밋 의존성. 라우터 직전에 차단한다 (LC-1 단계 8)."""

    async def _dependency(request: Request, container: ContainerDep) -> None:
        client_key = request.client.host if request.client else "unknown"
        container.rate_limiter.check(client_key, tier)

    return Depends(_dependency)
