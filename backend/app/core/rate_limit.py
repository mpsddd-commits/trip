"""C4 RateLimiter — 등급별 레이트 리밋.

근거:
    BR-49   3등급 — EXPENSIVE(IP 5/시간 + 전역 50/일) / EXTERNAL(60/분) / CHEAP(300/분)
    SEC-11  공개 엔드포인트의 외부 비용 남용 차단 (CA-5)
    SP-4    IP 슬라이딩 윈도는 인메모리, **전역 일일 상한은 영속화**
    ND-8    전역 카운터는 Protocol 로 주입 — core 가 services 구체 타입에 의존하지 않는다

SP-5 전제: 단일 프로세스(uvicorn 워커 1개, ID-4). 워커를 늘리면 IP 윈도가
          워커별로 분리되어 이 통제가 오류 없이 무력화된다.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Protocol

from app.core.enums import EndpointTier
from app.core.errors import RateLimitError


class GlobalDailyCounter(Protocol):
    """전역 일일 카운터 (SQLite 영속). C29 QuotaService 가 구현한다."""

    def increment_and_get(self, key: str) -> int:
        """오늘(KST) 카운터를 1 증가시키고 증가 후 값을 반환한다."""
        ...

    def peek(self, key: str) -> int:
        """증가 없이 오늘 값을 조회한다."""
        ...


class _SlidingWindow:
    """고정 창 길이의 슬라이딩 윈도 카운터 (인메모리)."""

    def __init__(self, limit: int, window_sec: float) -> None:
        self.limit = limit
        self.window_sec = window_sec
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check_and_add(self, key: str, now: float) -> bool:
        with self._lock:
            events = self._events[key]
            cutoff = now - self.window_sec
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= self.limit:
                return False
            events.append(now)
            return True

    def prune(self, now: float) -> None:
        with self._lock:
            cutoff = now - self.window_sec
            for key in list(self._events):
                events = self._events[key]
                while events and events[0] <= cutoff:
                    events.popleft()
                if not events:
                    del self._events[key]


GLOBAL_EXPENSIVE_KEY = "RATE_EXPENSIVE_GLOBAL"


class RateLimiter:
    def __init__(
        self,
        *,
        expensive_per_hour: int,
        expensive_global_per_day: int,
        external_per_min: int,
        cheap_per_min: int,
        global_counter: GlobalDailyCounter | None = None,
    ) -> None:
        self._windows: dict[EndpointTier, _SlidingWindow] = {
            EndpointTier.EXPENSIVE: _SlidingWindow(expensive_per_hour, 3600.0),
            EndpointTier.EXTERNAL: _SlidingWindow(external_per_min, 60.0),
            EndpointTier.CHEAP: _SlidingWindow(cheap_per_min, 60.0),
        }
        self._expensive_global_per_day = expensive_global_per_day
        self._global_counter = global_counter

    def check(self, key: str, tier: EndpointTier, *, now: float | None = None) -> None:
        """차단 대상이면 RateLimitError 를 던진다.

        검사 순서가 중요하다. IP 윈도를 먼저 보고, 통과한 요청만 전역 일일
        카운터를 증가시킨다. 그래야 한 IP 의 폭주가 전역 상한을 소모하지 못한다.
        """
        current = time.monotonic() if now is None else now
        window = self._windows[tier]
        if not window.check_and_add(key, current):
            raise RateLimitError(f"tier={tier.value} key={key} window limit exceeded")

        if tier is EndpointTier.EXPENSIVE and self._global_counter is not None:
            used = self._global_counter.increment_and_get(GLOBAL_EXPENSIVE_KEY)
            if used > self._expensive_global_per_day:
                raise RateLimitError(
                    f"global daily limit exceeded: {used}/{self._expensive_global_per_day}"
                )

    def prune(self) -> None:
        """만료된 윈도 항목을 정리한다. L8 스케줄러가 주기적으로 호출한다."""
        now = time.monotonic()
        for window in self._windows.values():
            window.prune(now)
