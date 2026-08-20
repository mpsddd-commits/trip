"""L2 ExternalSemaphore — API 별 전역 동시 호출 상한.

근거:
    ND-17 (파생 결정)
        Q3(job 동시 3개) x Q6(job 내부 호출 동시 3~5) 를 그대로 두면
        **최대 15개 외부 호출이 동시에** 나가 네이버 API 에 순간 부하를 준다.
        job 동시성과 곱해지지 않도록 API 별 전역 상한을 둔다.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.core.enums import ApiName


class ExternalSemaphore:
    """API 별 `asyncio.Semaphore` 모음.

    이벤트 루프 밖에서 생성될 수 있으므로 세마포어는 최초 사용 시점에 만든다.
    """

    def __init__(self, limit: int = 5) -> None:
        self.limit = limit
        self._semaphores: dict[ApiName, asyncio.Semaphore] = {}

    def _semaphore(self, api: ApiName) -> asyncio.Semaphore:
        semaphore = self._semaphores.get(api)
        if semaphore is None:
            semaphore = asyncio.Semaphore(self.limit)
            self._semaphores[api] = semaphore
        return semaphore

    @asynccontextmanager
    async def acquire(self, api: ApiName) -> AsyncIterator[None]:
        semaphore = self._semaphore(api)
        await semaphore.acquire()
        try:
            yield
        finally:
            semaphore.release()

    def available(self, api: ApiName) -> int:
        """대략적인 잔여 슬롯 수 (관측용)."""
        semaphore = self._semaphores.get(api)
        return self.limit if semaphore is None else semaphore._value  # noqa: SLF001
