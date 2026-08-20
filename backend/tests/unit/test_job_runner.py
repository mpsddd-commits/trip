"""L3 JobRunner + C29 QuotaService + C4 RateLimiter 테스트.

근거: ND-3(동시 3), RP-4(고아 정리), BR-49(레이트 리밋), SP-4(전역 상한 영속)
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.enums import ApiName, EndpointTier
from app.core.errors import RateLimitError
from app.core.rate_limit import RateLimiter
from app.services.job_runner import JobRunner
from app.services.quota_service import QuotaService


# ---------------------------------------------------------------------------
# L3 JobRunner — ND-3
# ---------------------------------------------------------------------------
async def test_concurrency_is_capped() -> None:
    """ND-3 — 전역 동시 3개를 넘지 않는다."""
    runner = JobRunner(max_concurrent=3)
    peak = {"value": 0}
    active = {"value": 0}
    release = asyncio.Event()

    async def work() -> None:
        active["value"] += 1
        peak["value"] = max(peak["value"], active["value"])
        await release.wait()
        active["value"] -= 1

    for i in range(10):
        runner.submit(f"job-{i}", work)

    await asyncio.sleep(0.05)
    assert peak["value"] <= 3

    release.set()
    await asyncio.sleep(0.05)
    assert peak["value"] <= 3


async def test_submit_returns_immediately() -> None:
    """DD-5 — 슬롯이 없어도 등록은 즉시 반환된다 (job_id 는 이미 발급됨)."""
    runner = JobRunner(max_concurrent=1)
    started = asyncio.Event()

    async def blocking() -> None:
        started.set()
        await asyncio.sleep(10)

    runner.submit("j1", blocking)
    await started.wait()
    runner.submit("j2", blocking)  # 예외 없이 즉시 반환
    assert runner.active_count == 2
    await runner.shutdown(timeout=1.0)


async def test_job_failure_does_not_crash_runner() -> None:
    runner = JobRunner(max_concurrent=2)
    done = asyncio.Event()

    async def boom() -> None:
        raise RuntimeError("의도적 실패")

    async def ok() -> None:
        done.set()

    runner.submit("bad", boom)
    runner.submit("good", ok)
    await asyncio.wait_for(done.wait(), timeout=1.0)


async def test_shutdown_cancels_running_tasks() -> None:
    runner = JobRunner(max_concurrent=2)

    async def forever() -> None:
        await asyncio.sleep(100)

    runner.submit("j", forever)
    await asyncio.sleep(0.01)
    await runner.shutdown(timeout=1.0)
    assert runner.active_count == 0

    with pytest.raises(RuntimeError):
        runner.submit("after", forever)


# ---------------------------------------------------------------------------
# C29 QuotaService — SP-4, BR-50
# ---------------------------------------------------------------------------
def test_quota_blocks_when_limit_reached() -> None:
    quota = QuotaService(daily_limits={ApiName.NAVER_LOCAL.value: 3})
    for _ in range(3):
        assert quota.is_exhausted(ApiName.NAVER_LOCAL) is False
        quota.record(ApiName.NAVER_LOCAL)
    assert quota.is_exhausted(ApiName.NAVER_LOCAL) is True


def test_quota_without_limit_never_blocks() -> None:
    quota = QuotaService(daily_limits={})
    for _ in range(1000):
        quota.record(ApiName.NAVER_BLOG)
    assert quota.is_exhausted(ApiName.NAVER_BLOG) is False


async def test_loaded_counts_prevent_restart_bypass() -> None:
    """SP-4 — 재시작해도 이미 쓴 만큼이 반영되어야 한다."""

    async def load() -> dict[str, int]:
        return {ApiName.NAVER_LOCAL.value: 3}

    quota = QuotaService(daily_limits={ApiName.NAVER_LOCAL.value: 3}, load_fn=load)
    await quota.load()
    assert quota.is_exhausted(ApiName.NAVER_LOCAL) is True


async def test_flush_sends_only_pending_delta() -> None:
    flushed: list[dict[str, int]] = []

    async def flush(pending: dict[str, int]) -> None:
        flushed.append(dict(pending))

    quota = QuotaService(flush_fn=flush)
    quota.record(ApiName.NAVER_LOCAL)
    quota.record(ApiName.NAVER_LOCAL)
    await quota.flush()
    await quota.flush()  # 두 번째는 보낼 것이 없다

    assert flushed == [{ApiName.NAVER_LOCAL.value: 2}]


# ---------------------------------------------------------------------------
# C4 RateLimiter — BR-49
# ---------------------------------------------------------------------------
def _limiter(counter: QuotaService | None = None) -> RateLimiter:
    return RateLimiter(
        expensive_per_hour=5,
        expensive_global_per_day=50,
        external_per_min=60,
        cheap_per_min=300,
        global_counter=counter,
    )


def test_expensive_tier_limits_per_ip_per_hour() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.check("1.2.3.4", EndpointTier.EXPENSIVE, now=0.0)
    with pytest.raises(RateLimitError):
        limiter.check("1.2.3.4", EndpointTier.EXPENSIVE, now=0.0)


def test_window_slides() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.check("1.2.3.4", EndpointTier.EXPENSIVE, now=0.0)
    limiter.check("1.2.3.4", EndpointTier.EXPENSIVE, now=3601.0)  # 1시간 경과


def test_different_ips_are_independent() -> None:
    limiter = _limiter()
    for _ in range(5):
        limiter.check("1.1.1.1", EndpointTier.EXPENSIVE, now=0.0)
    limiter.check("2.2.2.2", EndpointTier.EXPENSIVE, now=0.0)


def test_global_daily_cap_blocks_across_ips() -> None:
    """CA-5 — 한 IP 를 우회해도 전역 상한에 걸린다."""
    quota = QuotaService()
    limiter = RateLimiter(
        expensive_per_hour=100,
        expensive_global_per_day=3,
        external_per_min=60,
        cheap_per_min=300,
        global_counter=quota,
    )
    for index in range(3):
        limiter.check(f"ip-{index}", EndpointTier.EXPENSIVE, now=0.0)
    with pytest.raises(RateLimitError):
        limiter.check("ip-other", EndpointTier.EXPENSIVE, now=0.0)


def test_cheap_tier_allows_more() -> None:
    limiter = _limiter()
    for _ in range(300):
        limiter.check("1.2.3.4", EndpointTier.CHEAP, now=0.0)
    with pytest.raises(RateLimitError):
        limiter.check("1.2.3.4", EndpointTier.CHEAP, now=0.0)
