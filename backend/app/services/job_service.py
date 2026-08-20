"""C28 JobService — 비동기 작업 등록·상태 조회.

근거:
    Q5=A / DD-5   AI 생성은 202 + job_id 반환 후 폴링
    BR-13         해결률에 따른 상태 판정 — succeeded / partial / failed
    DD-23         `partial` 은 실패가 아니라 품질 저하
    BR-56         완료 후 24시간 뒤 정리
    ND-18         DB 접근은 전부 DbExecutor 경유
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any

from app.core.logging_config import get_logger
from app.domain.models import GenerationStep, JobState
from app.storage.database import Database
from app.storage.db_executor import DbExecutor
from app.storage.models import GenerationJobRow, utcnow
from app.storage.repositories import JobRepository

logger = get_logger(__name__)

# 단계별 진행률 (WF-2)
STEP_PROGRESS: dict[GenerationStep, float] = {
    GenerationStep.DRAFTING: 0.20,
    GenerationStep.RESOLVING: 0.60,
    GenerationStep.ROUTING: 0.80,
    GenerationStep.OPTIMIZING: 0.85,
    GenerationStep.SCHEDULING: 0.95,
    GenerationStep.SAVING: 1.00,
}


@dataclass(frozen=True, slots=True)
class JobStatus:
    job_id: str
    trip_id: str
    state: JobState
    step: GenerationStep | None
    progress: float
    resolved_count: int
    unresolved_count: int
    problem: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "trip_id": self.trip_id,
            "state": self.state.value,
            "step": self.step.value if self.step else None,
            "progress": self.progress,
            "resolved_count": self.resolved_count,
            "unresolved_count": self.unresolved_count,
            "problem": self.problem,
        }


class JobService:
    def __init__(self, database: Database, executor: DbExecutor) -> None:
        self._db = database
        self._executor = executor

    # ------------------------------------------------------------------
    async def enqueue(self, trip_id: str) -> str:
        job_id = str(uuid.uuid4())

        def _insert() -> None:
            with self._db.session_scope() as session:
                JobRepository(session).insert(
                    GenerationJobRow(job_id=job_id, trip_id=trip_id, state=JobState.QUEUED.value)
                )

        await self._executor.run(_insert)
        return job_id

    async def get_status(self, job_id: str) -> JobStatus | None:
        def _find() -> JobStatus | None:
            with self._db.session_scope() as session:
                row = JobRepository(session).find(job_id)
                return self._to_status(row) if row else None

        return await self._executor.run(_find)

    async def mark_running(self, job_id: str, step: GenerationStep) -> None:
        await self._update(
            job_id,
            state=JobState.RUNNING.value,
            step=step.value,
            progress=STEP_PROGRESS[step],
        )

    async def mark_counts(self, job_id: str, resolved: int, unresolved: int) -> None:
        await self._update(job_id, resolved_count=resolved, unresolved_count=unresolved)

    async def finish(
        self, job_id: str, state: JobState, *, problem: dict[str, Any] | None = None
    ) -> None:
        await self._update(
            job_id,
            state=state.value,
            progress=1.0,
            completed_at=utcnow(),
            problem_json=json.dumps(problem, ensure_ascii=False) if problem else None,
        )
        logger.info("job finished", extra={"job_id": job_id, "state": state.value})

    async def recover_orphans(self) -> int:
        """RP-4 — 기동 시 running·queued 로 남은 job 을 failed 로 전환한다."""
        problem = json.dumps(
            {"code": "INTERNAL_ERROR", "reason": "process restarted"}, ensure_ascii=False
        )

        def _recover() -> int:
            with self._db.session_scope() as session:
                return JobRepository(session).recover_orphans(problem)

        count = await self._executor.run(_recover)
        if count:
            logger.warning("orphan jobs recovered", extra={"count": count})
        return count

    async def purge_completed(self, retention_hours: int) -> int:
        def _purge() -> int:
            with self._db.session_scope() as session:
                return JobRepository(session).purge_completed(retention_hours)

        return await self._executor.run(_purge)

    # ------------------------------------------------------------------
    async def _update(self, job_id: str, **fields: Any) -> None:
        def _apply() -> None:
            with self._db.session_scope() as session:
                JobRepository(session).update(job_id, **fields)

        await self._executor.run(_apply)

    @staticmethod
    def _to_status(row: GenerationJobRow) -> JobStatus:
        return JobStatus(
            job_id=row.job_id,
            trip_id=row.trip_id,
            state=JobState(row.state),
            step=GenerationStep(row.step) if row.step else None,
            progress=row.progress,
            resolved_count=row.resolved_count,
            unresolved_count=row.unresolved_count,
            problem=json.loads(row.problem_json) if row.problem_json else None,
        )


def decide_final_state(resolved: int, unresolved: int) -> JobState:
    """BR-13 — 해결률에 따른 최종 상태 판정.

    100% -> succeeded / 1~99% -> partial / 0% -> failed
    """
    if resolved == 0:
        return JobState.FAILED
    if unresolved == 0:
        return JobState.SUCCEEDED
    return JobState.PARTIAL
