"""AI 일정 생성 라우터 — 비동기 job + 폴링.

근거:
    FR-2 / DD-5 / Q5=A   202 + job_id 즉시 반환, 프론트가 폴링
    BR-49                EXPENSIVE 등급 (IP 5회/시간 + 전역 50회/일)
    CA-5                 인증 없는 공개 경로의 비용 남용 차단
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import ContainerDep, rate_limit
from app.api.schemas import JobAccepted, JobStatusOut, TripSpecIn
from app.core.enums import EndpointTier
from app.core.errors import NotFoundError

router = APIRouter(prefix="/api", tags=["generation"])


@router.post(
    "/trips/{trip_id}/generate",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=JobAccepted,
    dependencies=[rate_limit(EndpointTier.EXPENSIVE)],  # BR-49 — 가장 엄격한 등급
)
async def start_generation(
    trip_id: str, payload: TripSpecIn, container: ContainerDep
) -> JobAccepted:
    """일정 생성을 시작하고 **즉시** job_id 를 반환한다.

    NFR-1 — 최대 60초가 걸리므로 HTTP 응답을 붙잡지 않는다.
    """
    spec = payload.to_domain()
    container.trips.validate_spec(spec)
    await container.trips.get(trip_id)  # 존재 확인 (없으면 NotFoundError)

    job_id = await container.jobs.enqueue(trip_id)
    container.runner.submit(
        job_id, lambda: container.generation.run_pipeline(job_id, trip_id, spec)
    )
    return JobAccepted(job_id=job_id, trip_id=trip_id, state="queued")


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusOut,  # A-2
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def get_job(job_id: str, container: ContainerDep) -> dict:
    """진행 상태 폴링 (WF-2 6단계).

    `partial` 은 실패가 아니라 품질 저하다 (DD-23). 프론트는 이를 구체적으로
    알려야 한다 — "3곳을 찾지 못했습니다", "이동시간이 추정치입니다".
    """
    status_view = await container.jobs.get_status(job_id)
    if status_view is None:
        raise NotFoundError(f"job not found: {job_id}")
    return status_view.to_dict()
