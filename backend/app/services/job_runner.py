"""L3 JobRunner — 백그라운드 작업 실행기.

근거:
    ND-2 / Q2=A   프로세스 내 asyncio 태스크. 별도 워커·브로커 없음 (UD-8 정합)
    ND-3 / Q3=A   **전역 동시 3개**. 초과 요청은 queued 로 대기, job_id 는 즉시 반환
    ND-4 / Q4=A   재시도 API 미제공
    RP-4          기동 시 고아 job 정리 / 종료 시 실행 중 태스크 정상 취소

SP-5 전제: 단일 프로세스(uvicorn 워커 1개, ID-4). 워커를 늘리면 이 세마포어가
          워커별로 분리되어 동시 실행 상한이 무력화된다.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core.logging_config import get_logger

logger = get_logger(__name__)

JobCoroutine = Callable[[], Awaitable[None]]


class JobRunner:
    def __init__(self, max_concurrent: int = 3) -> None:
        self.max_concurrent = max_concurrent
        self._semaphore: asyncio.Semaphore | None = None
        self._tasks: set[asyncio.Task[None]] = set()
        self._shutting_down = False

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    # ------------------------------------------------------------------
    def submit(self, job_id: str, coroutine_factory: JobCoroutine) -> None:
        """작업을 등록한다. 슬롯이 없으면 대기하지만 **즉시 반환**한다."""
        if self._shutting_down:
            raise RuntimeError("애플리케이션 종료 중에는 작업을 등록할 수 없습니다")

        task = asyncio.create_task(self._run(job_id, coroutine_factory), name=f"job:{job_id}")
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _run(self, job_id: str, coroutine_factory: JobCoroutine) -> None:
        async with self._get_semaphore():
            logger.info("job started", extra={"job_id": job_id})
            try:
                await coroutine_factory()
            except asyncio.CancelledError:
                logger.warning("job cancelled", extra={"job_id": job_id})
                raise
            except Exception:  # noqa: BLE001 - 작업 실패가 서버를 멈추면 안 된다
                logger.exception("job failed", extra={"job_id": job_id})

    # ------------------------------------------------------------------
    @property
    def active_count(self) -> int:
        return len(self._tasks)

    async def shutdown(self, timeout: float = 10.0) -> None:
        """종료 시 실행 중 태스크를 정상 취소한다."""
        self._shutting_down = True
        if not self._tasks:
            return
        for task in list(self._tasks):
            task.cancel()
        await asyncio.wait(list(self._tasks), timeout=timeout)
        self._tasks.clear()
