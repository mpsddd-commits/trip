"""C29 QuotaService — 외부 API 사용량 계측과 일일 상한.

근거:
    NFR-4   지역검색 25,000회/일 등 쿼터 관리
    BR-50   상한 도달 시 **호출하지 않고 즉시 거부**. 일자는 KST 기준
    BR-51   쿼터 소진을 보안 이벤트로 기록 (SEC-14)
    SP-4    **전역 일일 카운터는 영속화한다** — 재시작으로 비용 통제가 우회되면 안 됨
    ND-8    `QuotaGate` / `GlobalDailyCounter` Protocol 구현체

⚠️ 파생 결정 (CD-1):
    `QuotaGate.record()` 는 **async 컨텍스트에서 동기 호출**된다(C6 내부).
    여기서 SQLite 에 직접 쓰면 이벤트 루프가 막힌다 (ND-18 위반).
    따라서 **인메모리 증가 + 주기 플러시 + 기동 시 로드** 구조를 쓴다.
      - 기동 시: DB 의 오늘 값을 메모리로 로드 → 재시작 우회 방지 (SP-4 목적 달성)
      - 운영 중: 메모리에서 증가 (논블로킹)
      - 주기·종료 시: DB 로 플러시 (L8 스케줄러)
    손실 위험은 "비정상 종료 시 마지막 플러시 이후 카운트"로 한정되며,
    이는 상한을 **느슨하게** 만들지언정 우회를 허용하지 않는다.
"""

from __future__ import annotations

import threading
from collections.abc import Awaitable, Callable

from app.core.enums import ApiName, AuditEventType
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# C4 RateLimiter 가 사용하는 전역 키 (BR-49)
GLOBAL_EXPENSIVE_KEY = "RATE_EXPENSIVE_GLOBAL"


class QuotaService:
    def __init__(
        self,
        *,
        daily_limits: dict[str, int] | None = None,
        load_fn: Callable[[], Awaitable[dict[str, int]]] | None = None,
        flush_fn: Callable[[dict[str, int]], Awaitable[None]] | None = None,
    ) -> None:
        self._limits = daily_limits or {}
        self._load_fn = load_fn
        self._flush_fn = flush_fn
        self._counts: dict[str, int] = {}
        self._errors: dict[str, int] = {}
        self._pending: dict[str, int] = {}
        self._lock = threading.Lock()
        self._exhausted_logged: set[str] = set()

    # ------------------------------------------------------------------
    # 수명 주기
    # ------------------------------------------------------------------
    async def load(self) -> None:
        """기동 시 DB 의 오늘 값을 메모리로 올린다 (SP-4)."""
        if self._load_fn is None:
            return
        loaded = await self._load_fn()
        with self._lock:
            self._counts.update(loaded)
        logger.info("quota loaded", extra={"keys": len(loaded)})

    async def flush(self) -> int:
        """메모리 증가분을 DB 에 반영한다. 스케줄러(L8)와 종료 훅이 호출한다."""
        if self._flush_fn is None:
            return 0
        with self._lock:
            pending, self._pending = self._pending, {}
        if not pending:
            return 0
        await self._flush_fn(pending)
        return sum(pending.values())

    # ------------------------------------------------------------------
    # QuotaGate (C6 이 호출 — 동기, 논블로킹이어야 한다)
    # ------------------------------------------------------------------
    def record(self, api: ApiName, *, error: bool = False) -> None:
        with self._lock:
            self._counts[api.value] = self._counts.get(api.value, 0) + 1
            self._pending[api.value] = self._pending.get(api.value, 0) + 1
            if error:
                self._errors[api.value] = self._errors.get(api.value, 0) + 1

    def is_exhausted(self, api: ApiName) -> bool:
        limit = self._limits.get(api.value)
        if limit is None:
            return False
        with self._lock:
            used = self._counts.get(api.value, 0)
        if used >= limit and api.value not in self._exhausted_logged:
            self._exhausted_logged.add(api.value)
            # BR-51 / SEC-14 — 보안 이벤트로 남긴다.
            logger.warning(
                "quota exhausted",
                extra={
                    "api": api.value,
                    "used": used,
                    "limit": limit,
                    "event_type": AuditEventType.QUOTA_EXHAUSTED.value,
                },
            )
        return used >= limit

    # ------------------------------------------------------------------
    # GlobalDailyCounter (C4 RateLimiter 가 호출)
    # ------------------------------------------------------------------
    def increment_and_get(self, key: str) -> int:
        with self._lock:
            value = self._counts.get(key, 0) + 1
            self._counts[key] = value
            self._pending[key] = self._pending.get(key, 0) + 1
            return value

    def peek(self, key: str) -> int:
        with self._lock:
            return self._counts.get(key, 0)

    # ------------------------------------------------------------------
    def usage_today(self) -> dict[str, dict[str, int]]:
        """FR-34 — `/api/health/ready` 노출용."""
        with self._lock:
            return {
                key: {
                    "call_count": count,
                    "error_count": self._errors.get(key, 0),
                    "daily_limit": self._limits.get(key, 0) or None,
                }
                for key, count in sorted(self._counts.items())
            }
