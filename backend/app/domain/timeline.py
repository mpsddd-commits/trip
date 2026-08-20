"""C15 TimelineCalculator — 방문 순서와 이동시간으로 시각을 산출한다.

근거:
    BR-31   time_fixed 항목의 도착 시각은 항상 fixed_time 과 일치 (절대 밀지 않음)
    BR-32   고정 시각 도착이 불가능하면 FIXED_TIME_CONFLICT 경고만 부착
    BR-33   day_end_time 초과 시 DAY_OVERFLOW 경고. 다음 날로 옮기지 않음
    BR-34   모든 경고는 표시 전용이며 저장·조회를 차단하지 않는다
    BR-35   영업시간 경고는 OpeningHours 레코드가 있을 때만
    BR-27   근사 이동시간 구간에 ESTIMATED_TRAVEL_TIME 경고
    P-01~P-05

⚠️ P-03(시각 단조 증가) 정밀화:
    Functional Design 은 "arrival[i] <= departure[i] <= arrival[i+1]" 를 무조건
    성립하는 불변식으로 기술했으나, BR-31/BR-32 와 함께 두면 성립하지 않는다.
    고정 시각이 앞 일정의 종료보다 이르면 시각을 밀지 않고 경고만 부착하므로
    그 지점에서 역전이 발생한다.
    따라서 정확한 불변식은 다음과 같다:
        **FIXED_TIME_CONFLICT 경고가 없는 구간에서만 단조 증가한다.**
    이 정밀화는 domain-summary.md 와 Build & Test 보고서에 기록한다.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.matrix import DistanceMatrix
from app.domain.models import (
    ItemWarning,
    ItineraryItem,
    TravelMode,
    WarningType,
)
from app.domain.opening_hours import check_opening_hours

KST = ZoneInfo("Asia/Seoul")


def _combine(day: date, at: time, tz: ZoneInfo) -> datetime:
    """KST 로 조합한 뒤 UTC 로 변환한다 (NFR-7 — 저장 UTC / 계산 KST)."""
    return datetime.combine(day, at, tzinfo=tz).astimezone(UTC)


def compute(
    items: list[ItineraryItem],
    matrix: DistanceMatrix,
    *,
    day: date,
    day_start: time,
    day_end: time,
    default_mode: TravelMode,
    tz: ZoneInfo = KST,
) -> list[ItineraryItem]:
    """항목 목록에 도착·출발 시각과 경고를 채워 반환한다.

    입력 항목의 개수·구성·순서를 보존한다 (P-01, P-02).
    """
    if not items:
        return []

    day_end_dt = _combine(day, day_end, tz)
    cursor = _combine(day, day_start, tz)
    result: list[ItineraryItem] = []

    for index, item in enumerate(items):
        warnings: list[ItemWarning] = []

        if item.time_fixed and item.fixed_time is not None:
            arrival = _combine(day, item.fixed_time, tz)  # BR-31 — 절대 밀지 않는다
            if cursor > arrival:
                # BR-32 — 물리적으로 도착 불가. 시각은 유지하고 경고만 남긴다.
                late_min = int((cursor - arrival).total_seconds() // 60)
                warnings.append(
                    ItemWarning(
                        type=WarningType.FIXED_TIME_CONFLICT,
                        detail=f"앞 일정 때문에 약 {late_min}분 늦게 도착할 수 있습니다.",
                    )
                )
        else:
            arrival = cursor

        departure = arrival + timedelta(minutes=item.stay_minutes)

        # BR-35 — 사용자가 입력한 영업시간이 있을 때만 판정한다.
        opening_warning = check_opening_hours(item.place, arrival.astimezone(tz))
        if opening_warning is not None:
            warnings.append(opening_warning)

        # BR-33 — 초과해도 자동으로 옮기거나 지우지 않는다.
        if departure > day_end_dt:
            over_min = int((departure - day_end_dt).total_seconds() // 60)
            warnings.append(
                ItemWarning(
                    type=WarningType.DAY_OVERFLOW,
                    detail=f"하루 활동 종료 시각을 약 {over_min}분 초과합니다.",
                )
            )

        mode = item.travel_mode or default_mode
        leg = matrix.get(index, index + 1, mode) if index + 1 < len(items) else None
        if leg is not None and leg.is_estimate:
            # BR-27 — 근사치임을 사용자에게 반드시 알린다.
            warnings.append(
                ItemWarning(
                    type=WarningType.ESTIMATED_TRAVEL_TIME,
                    detail="이동시간은 추정치입니다. 정확한 경로는 네이버지도에서 확인하세요.",
                )
            )

        result.append(item.with_times(arrival, departure).with_warnings(tuple(warnings)))
        cursor = departure + timedelta(seconds=leg.duration_sec if leg else 0)

    return result


def total_duration(items: list[ItineraryItem]) -> timedelta:
    """하루 전체 소요시간. 시각이 채워지지 않았으면 0 을 반환한다."""
    timed = [i for i in items if i.arrival_at and i.departure_at]
    if not timed:
        return timedelta(0)
    return max(i.departure_at for i in timed) - min(i.arrival_at for i in timed)  # type: ignore[type-var]
