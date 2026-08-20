"""L8 MaintenanceScheduler — 정리 작업 주기 실행.

근거:
    BR-60   기동 시 1회 + 하루 1회 실행
    BR-56   완료 job 24시간 뒤 정리
    BR-57   캐시 TTL 만료 + 7일 유예 뒤 삭제
    BR-59   감사 로그 90일 보존
    LC-2 / ND-16  asyncio 주기 태스크. 외부 스케줄러·cron 미도입
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from app.core.logging_config import get_logger

logger = get_logger(__name__)

MaintenanceTask = Callable[[], Awaitable[int]]


class MaintenanceScheduler:
    """등록된 정리 작업을 기동 시 1회, 이후 주기적으로 실행한다."""

    def __init__(self, interval_sec: float = 24 * 3600.0) -> None:
        self.interval_sec = interval_sec
        self._tasks: list[tuple[str, MaintenanceTask]] = []
        self._runner: asyncio.Task[None] | None = None

    def register(self, name: str, task: MaintenanceTask) -> None:
        self._tasks.append((name, task))

    async def run_once(self) -> dict[str, int]:
        """등록된 작업을 1회 실행한다. 개별 실패는 전체를 중단시키지 않는다."""
        results: dict[str, int] = {}
        for name, task in self._tasks:
            try:
                results[name] = await task()
            except Exception:  # noqa: BLE001 - 정리 실패가 서비스를 멈추면 안 된다
                logger.exception("maintenance task failed", extra={"task": name})
                results[name] = -1
        logger.info("maintenance completed", extra={"results": results})
        return results

    async def _loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self.interval_sec)
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("maintenance loop error")

    async def start(self) -> None:
        """기동 시 1회 실행 후 주기 루프를 띄운다 (BR-60)."""
        await self.run_once()
        self._runner = asyncio.create_task(self._loop(), name="maintenance-scheduler")

    async def stop(self) -> None:
        if self._runner is None:
            return
        self._runner.cancel()
        try:
            await self._runner
        except asyncio.CancelledError:
            pass
        finally:
            self._runner = None
