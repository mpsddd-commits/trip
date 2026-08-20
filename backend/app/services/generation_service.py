"""C25 ItineraryGenerationService — AI 일정 생성 파이프라인 오케스트레이터.

근거:
    WF-2 / Q9=A   명시적 6단계 파이프라인. **조율만 하고 계산·판정을 갖지 않는다**
    DD-5          202 + job_id 반환 후 폴링
    BR-13         해결률에 따른 상태 판정
    BR-18         🔴 미해결 후보는 ItineraryItem 이 되지 않는다
    BR-52         체류시간 = LLM 제안값 우선, 없으면 카테고리 기본값
    BR-53         저장 실패 시 전체 롤백 (fail-closed)
    RP-3          ANTHROPIC 실패는 폴백 없음 → failed

단계별 실패 정책 (nfr-design RP-3 / services.md §2):
    DRAFTING   실패 -> failed
    RESOLVING  부분 실패 -> partial / 전건 실패 -> failed
    ROUTING    실패 -> 근사 폴백으로 계속 (partial)
    OPTIMIZING 실패·상한 -> 최적화 생략하고 계속 (partial)
    SCHEDULING 충돌 -> 경고 부착하고 계속
    SAVING     실패 -> failed (부분 저장 금지)
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, timedelta

from app.core.errors import DomainError, InternalError
from app.core.logging_config import get_logger
from app.domain.categories import default_stay_minutes
from app.domain.estimator import EstimatorParams
from app.domain.matrix import DistanceMatrix
from app.domain.models import (
    GenerationStep,
    ItineraryItem,
    JobState,
    Place,
    TripSpec,
)
from app.domain.optimizer import OptimizeLimits, optimize
from app.domain.timeline import compute as compute_timeline
from app.services.job_service import JobService, decide_final_state
from app.services.llm_draft import LlmDraftGenerator
from app.services.place_resolver import PlaceResolver, ResolveResult
from app.services.travel_matrix import TravelMatrixService
from app.services.trip_service import TripService

logger = get_logger(__name__)


class ItineraryGenerationService:
    def __init__(
        self,
        *,
        draft_generator: LlmDraftGenerator,
        resolver: PlaceResolver,
        matrix_service: TravelMatrixService,
        trip_service: TripService,
        job_service: JobService,
        estimator_params: EstimatorParams,
        optimize_limits: OptimizeLimits,
    ) -> None:
        self._draft = draft_generator
        self._resolver = resolver
        self._matrix = matrix_service
        self._trips = trip_service
        self._jobs = job_service
        self._params = estimator_params
        self._limits = optimize_limits

    # ------------------------------------------------------------------
    async def run_pipeline(self, job_id: str, trip_id: str, spec: TripSpec) -> JobState:
        """6단계를 순서대로 실행한다. 각 단계 전이를 job 에 기록한다."""
        try:
            # 1. DRAFTING -------------------------------------------------
            await self._jobs.mark_running(job_id, GenerationStep.DRAFTING)
            candidates_by_day = await self._draft.generate_draft(spec)
            if not any(candidates_by_day):
                await self._jobs.finish(
                    job_id, JobState.FAILED, problem={"code": "EMPTY_DRAFT"}
                )
                return JobState.FAILED

            # 2. RESOLVING (환각 차단 지점) ---------------------------------
            await self._jobs.mark_running(job_id, GenerationStep.RESOLVING)
            resolution = await self._resolver.resolve_many(candidates_by_day, spec.destination)
            await self._jobs.mark_counts(
                job_id, resolution.resolved_count, resolution.unresolved_count
            )
            if resolution.resolved_count == 0:
                # BR-13 — 전건 미해결이면 실패
                await self._jobs.finish(
                    job_id,
                    JobState.FAILED,
                    problem={
                        "code": "ALL_UNRESOLVED",
                        "unresolved_count": resolution.unresolved_count,
                    },
                )
                return JobState.FAILED

            days = self._group_by_day(resolution, spec)

            # 3~5. 일자별 경로·최적화·타임라인 -------------------------------
            await self._jobs.mark_running(job_id, GenerationStep.ROUTING)
            scheduled: list[list[ItineraryItem]] = []
            for day_index, items in enumerate(days, start=1):
                scheduled.append(await self._plan_day(job_id, spec, day_index, items))

            # 6. SAVING ---------------------------------------------------
            await self._jobs.mark_running(job_id, GenerationStep.SAVING)
            await self._trips.replace_itinerary(trip_id, scheduled, resolution.unresolved)

            state = decide_final_state(resolution.resolved_count, resolution.unresolved_count)
            await self._jobs.finish(job_id, state)
            return state

        except DomainError as exc:
            logger.warning("generation failed", extra={"job_id": job_id, "code": exc.code.value})
            await self._jobs.finish(job_id, JobState.FAILED, problem={"code": exc.code.value})
            return JobState.FAILED
        except Exception as exc:  # noqa: BLE001 - 어떤 예외도 job 을 매달아두지 않는다
            logger.exception("generation crashed", extra={"job_id": job_id})
            await self._jobs.finish(
                job_id, JobState.FAILED, problem={"code": InternalError.code.value}
            )
            raise exc from None

    # ------------------------------------------------------------------
    async def _plan_day(
        self, job_id: str, spec: TripSpec, day_index: int, items: list[ItineraryItem]
    ) -> list[ItineraryItem]:
        """한 일자에 대해 ROUTING → OPTIMIZING → SCHEDULING 을 수행한다."""
        if not items:
            return []

        places = [item.place for item in items]
        mode = spec.default_travel_mode

        # ROUTING — 비인접은 근사, 인접만 실호출 (BR-28)
        matrix: DistanceMatrix = await self._matrix.build_matrix(places, mode)

        # OPTIMIZING — 실패해도 입력 순서로 계속 (BR-22)
        await self._jobs.mark_running(job_id, GenerationStep.OPTIMIZING)
        try:
            ordered = optimize(items, matrix, mode, limits=self._limits)
        except Exception:  # noqa: BLE001
            logger.warning("최적화 실패로 입력 순서를 유지합니다", extra={"day": day_index})
            ordered = items

        # 확정된 순서의 인접 쌍만 실호출로 갱신 (BR-28)
        index_of = {item.item_id: index for index, item in enumerate(items)}
        order = [index_of[item.item_id] for item in ordered]
        matrix = await self._matrix.refresh_adjacent(places, order, mode, matrix)

        # 타임라인 계산에 쓰이는 행렬은 **재배열된 순서 기준**이어야 한다.
        reindexed = self._reindex(matrix, order, mode)

        # SCHEDULING
        await self._jobs.mark_running(job_id, GenerationStep.SCHEDULING)
        return compute_timeline(
            ordered,
            reindexed,
            day=self._day_date(spec, day_index),
            day_start=spec.day_start_time,
            day_end=spec.day_end_time,
            default_mode=mode,
        )

    @staticmethod
    def _day_date(spec: TripSpec, day_index: int) -> date:
        return spec.start_date + timedelta(days=day_index - 1)

    @staticmethod
    def _reindex(matrix: DistanceMatrix, order: list[int], mode) -> DistanceMatrix:  # type: ignore[no-untyped-def]
        """행렬 인덱스를 재배열된 위치 기준으로 변환한다.

        C15 는 `(위치 i, 위치 i+1)` 로 조회하므로, 원래 인덱스 기준 행렬을
        그대로 넘기면 엉뚱한 구간을 읽는다.
        """
        legs = []
        for position in range(len(order) - 1):
            leg = matrix.get(order[position], order[position + 1], mode)
            if leg is not None:
                legs.append(replace(leg, from_index=position, to_index=position + 1))
        return DistanceMatrix.from_legs(legs)

    # ------------------------------------------------------------------
    def _group_by_day(self, resolution: ResolveResult, spec: TripSpec) -> list[list[ItineraryItem]]:
        """해석된 장소를 일자별 항목으로 조립한다.

        🔴 BR-18 — `resolution.unresolved` 는 여기에 **절대 들어오지 않는다.**
        """
        days: list[list[ItineraryItem]] = [[] for _ in range(spec.day_count)]
        for place in resolution.resolved:
            day_index = resolution.day_of_place.get(place.place_id, 1)
            if not (1 <= day_index <= spec.day_count):
                day_index = 1
            candidate = resolution.candidate_of_place.get(place.place_id)
            days[day_index - 1].append(self._to_item(place, candidate))

        # 일자 내 위치를 0부터 연속으로 부여한다 (ItineraryItemRow 의 UNIQUE 제약).
        return [
            [replace(item, position=position) for position, item in enumerate(items)]
            for items in days
        ]

    @staticmethod
    def _to_item(place: Place, candidate) -> ItineraryItem:  # type: ignore[no-untyped-def]
        # BR-52 — LLM 제안값 우선, 없으면 카테고리 기본값
        stay = None
        if candidate is not None:
            stay = candidate.suggested_stay_minutes
        return ItineraryItem(
            item_id=str(uuid.uuid4()),
            place=place,
            stay_minutes=stay or default_stay_minutes(place.category),
        )
