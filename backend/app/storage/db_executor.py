"""L4 DbExecutor — 동기 DB 호출을 스레드 풀에서 실행한다.

근거:
    ND-18 (파생 결정)
        Q2(asyncio 백그라운드 작업) × Q5(동기 SQLite 드라이버) 조합에서,
        job 이 저장하는 동안 이벤트 루프가 막히면 **동시에 들어온 API 요청 전체가
        지연**된다. 따라서 async 컨텍스트에서 동기 DB 를 직접 호출하지 않는다.

    생성 원칙 9: `async` 컨텍스트에서 동기 DB 호출 금지 — 전부 이 모듈 경유.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


class DbExecutor:
    """DB 전용 스레드 풀.

    일반 이벤트 루프 기본 실행자와 분리해, DB 부하가 다른 블로킹 작업을
    굶기지 않도록 한다.
    """

    def __init__(self, max_workers: int = 8) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="db")

    async def run(self, fn: Callable[P, T], /, *args: P.args, **kwargs: P.kwargs) -> T:
        loop = asyncio.get_running_loop()
        if kwargs:
            return await loop.run_in_executor(self._pool, lambda: fn(*args, **kwargs))
        return await loop.run_in_executor(self._pool, fn, *args)  # type: ignore[arg-type]

    def shutdown(self) -> None:
        self._pool.shutdown(wait=True, cancel_futures=False)
