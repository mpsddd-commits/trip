"""C25 ItineraryGenerationService 통합 테스트 (네트워크 비의존).

근거: WF-2 6단계, BR-13 상태 판정, BR-18 미해결 배제, BR-52 체류시간, BR-53 원자성
"""

from __future__ import annotations

from datetime import date, time

import pytest

from app.clients.protocols import CarRoute, LlmResponse, SearchedPlace
from app.core.errors import ExternalServiceError
from app.domain.estimator import EstimatorParams
from app.domain.models import Coordinate, JobState, TravelMode, TripSpec
from app.domain.optimizer import DETERMINISTIC_LIMITS
from app.services.generation_service import ItineraryGenerationService
from app.services.job_service import JobService
from app.services.llm_draft import LlmDraftGenerator
from app.services.place_resolver import PlaceResolver
from app.services.travel_matrix import TravelMatrixService
from app.services.trip_service import TripService
from app.storage.database import Database
from app.storage.db_executor import DbExecutor
from app.storage.migrations import run_migrations

BUSAN = Coordinate(35.1796, 129.0756)

SPEC = TripSpec(
    title="부산 2일",
    destination="부산",
    start_date=date(2026, 9, 1),
    end_date=date(2026, 9, 2),
    day_start_time=time(9, 0),
    day_end_time=time(21, 0),
    default_travel_mode=TravelMode.WALK,
)

DRAFT = {
    "days": [
        {
            "day_index": 1,
            "places": [
                {"raw_name": "광안리 해수욕장", "reason": "야경", "suggested_stay_minutes": 90},
                {"raw_name": "돼지국밥집", "reason": "식사"},
            ],
        },
        {
            "day_index": 2,
            "places": [{"raw_name": "감천문화마을", "reason": "사진"}],
        },
    ]
}


class _Llm:
    def __init__(self, payload=DRAFT) -> None:
        self.payload = payload

    async def complete(self, *, system, user, max_tokens, tool_schema=None) -> LlmResponse:
        import json

        return LlmResponse(text=json.dumps(self.payload, ensure_ascii=False))


class _Search:
    """질의의 장소명을 그대로 돌려주는 검색기 — 그라운딩이 성공한다."""

    def __init__(self, *, unknown: set[str] | None = None, fail: bool = False) -> None:
        self.unknown = unknown or set()
        self.fail = fail

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        if self.fail:
            raise ExternalServiceError("search down")
        name = query.removeprefix("부산 ").strip()
        if name in self.unknown:
            return []
        return [
            SearchedPlace(
                name=name,
                coordinate=Coordinate(
                    lat=35.1 + (len(name) % 7) * 0.01, lng=129.0 + (len(name) % 5) * 0.01
                ),
                category_raw="여행>관광,명소",
                road_address="부산광역시 수영구 광안해변로 1",
                address="부산광역시 수영구 광안동",
            )
        ]


class _Directions:
    async def route_car(self, origin: Coordinate, destination: Coordinate) -> CarRoute:
        return CarRoute(duration_sec=600, distance_m=5000, path=(origin, destination))


@pytest.fixture()
def wiring():
    database = Database(":memory:")
    run_migrations(database.engine)
    executor = DbExecutor(max_workers=2)
    yield database, executor
    executor.shutdown()
    database.dispose()


def _service(wiring, search: _Search, llm: _Llm | None = None):
    database, executor = wiring
    trips = TripService(database, executor)
    jobs = JobService(database, executor)
    return (
        ItineraryGenerationService(
            draft_generator=LlmDraftGenerator(llm or _Llm()),
            resolver=PlaceResolver(search),
            matrix_service=TravelMatrixService(_Directions()),
            trip_service=trips,
            job_service=jobs,
            estimator_params=EstimatorParams(),
            optimize_limits=DETERMINISTIC_LIMITS,
        ),
        trips,
        jobs,
    )


# ---------------------------------------------------------------------------
async def test_full_pipeline_succeeds(wiring) -> None:
    """WF-2 — 6단계가 끝까지 진행되고 일정이 저장된다."""
    service, trips, jobs = _service(wiring, _Search())
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)

    state = await service.run_pipeline(job_id, trip_id, SPEC)
    assert state is JobState.SUCCEEDED

    view = await trips.get(trip_id)
    assert len(view.days) == 2
    assert len(view.days[0]) == 2
    assert len(view.days[1]) == 1
    assert view.unresolved == []

    # 타임라인이 채워졌다
    first = view.days[0][0]
    assert first.arrival_at is not None and first.departure_at is not None


async def test_partial_when_some_places_unresolved(wiring) -> None:
    """BR-13 — 1~99% 해결이면 partial, 미해결은 별도 목록으로 노출."""
    service, trips, jobs = _service(wiring, _Search(unknown={"돼지국밥집"}))
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)

    state = await service.run_pipeline(job_id, trip_id, SPEC)
    assert state is JobState.PARTIAL

    view = await trips.get(trip_id)
    assert len(view.unresolved) == 1
    assert view.unresolved[0]["raw_name"] == "돼지국밥집"

    # 🔴 BR-18 — 미해결 후보가 일정 항목이 되지 않았다
    all_names = {item.place.name for day in view.days for item in day}
    assert "돼지국밥집" not in all_names

    status = await jobs.get_status(job_id)
    assert status.state is JobState.PARTIAL
    assert status.unresolved_count == 1


async def test_failed_when_nothing_resolves(wiring) -> None:
    """BR-13 — 전건 미해결이면 failed."""
    service, trips, jobs = _service(
        wiring, _Search(unknown={"광안리 해수욕장", "돼지국밥집", "감천문화마을"})
    )
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)

    state = await service.run_pipeline(job_id, trip_id, SPEC)
    assert state is JobState.FAILED

    status = await jobs.get_status(job_id)
    assert status.problem["code"] == "ALL_UNRESOLVED"


async def test_search_outage_marks_failed_without_crashing(wiring) -> None:
    """BR-16 — 검색 전면 장애도 예외가 아니라 상태로 표현된다."""
    service, trips, jobs = _service(wiring, _Search(fail=True))
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)

    state = await service.run_pipeline(job_id, trip_id, SPEC)
    assert state is JobState.FAILED


async def test_stay_minutes_prefers_llm_then_category(wiring) -> None:
    """BR-52 — LLM 제안값 우선, 없으면 카테고리 기본값."""
    service, trips, jobs = _service(wiring, _Search())
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)
    await service.run_pipeline(job_id, trip_id, SPEC)

    view = await trips.get(trip_id)
    by_name = {item.place.name: item for day in view.days for item in day}
    assert by_name["광안리 해수욕장"].stay_minutes == 90  # LLM 제안값
    assert by_name["돼지국밥집"].stay_minutes == 90  # ATTRACTION 기본값 (분류 결과)


async def test_job_progress_is_recorded(wiring) -> None:
    service, trips, jobs = _service(wiring, _Search())
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)

    status = await jobs.get_status(job_id)
    assert status.state is JobState.QUEUED

    await service.run_pipeline(job_id, trip_id, SPEC)
    status = await jobs.get_status(job_id)
    assert status.progress == 1.0
    assert status.resolved_count == 3


async def test_positions_are_contiguous(wiring) -> None:
    """ItineraryItemRow 의 (day_id, position) UNIQUE 제약을 만족해야 한다."""
    service, trips, jobs = _service(wiring, _Search())
    trip_id = await trips.create(SPEC)
    job_id = await jobs.enqueue(trip_id)
    await service.run_pipeline(job_id, trip_id, SPEC)

    view = await trips.get(trip_id)
    for items in view.days:
        assert [i.position for i in items] == list(range(len(items)))
