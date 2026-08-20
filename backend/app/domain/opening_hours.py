"""C19 OpeningHoursChecker — 영업시간 밖 도착 판정.

근거:
    BR-35 / FR-13(개정)
        네이버 지역검색 API 는 영업시간을 제공하지 않는다.
        영업시간은 **사용자가 직접 입력한 경우에만** 존재하며,
        레코드가 없으면 어떤 경고도 만들지 않는다(거짓 경고 방지).
"""

from __future__ import annotations

from datetime import datetime

from app.domain.models import ItemWarning, Place, WarningType


def check_opening_hours(place: Place, arrival_local: datetime) -> ItemWarning | None:
    """도착 시각이 영업시간 밖이면 경고를 반환한다.

    영업시간 정보가 없으면 **항상 None** 이다 (BR-35).
    """
    hours = place.opening_hours
    if hours is None or not hours.weekday_rules:
        return None

    weekday = arrival_local.weekday()
    rule = next((r for r in hours.weekday_rules if r.weekday == weekday), None)
    if rule is None:
        # 해당 요일 규칙이 없으면 판단 근거가 없으므로 경고하지 않는다.
        return None

    if rule.closed:
        return ItemWarning(
            type=WarningType.OUTSIDE_OPENING_HOURS,
            detail="입력하신 영업시간 기준으로 휴무일입니다.",
        )

    if rule.open is None or rule.close is None:
        return None

    at = arrival_local.time()
    if rule.open <= rule.close:
        inside = rule.open <= at <= rule.close
    else:
        # 자정을 넘기는 영업시간 (예: 18:00 ~ 02:00)
        inside = at >= rule.open or at <= rule.close

    if inside:
        return None

    return ItemWarning(
        type=WarningType.OUTSIDE_OPENING_HOURS,
        detail=(
            f"입력하신 영업시간({rule.open.strftime('%H:%M')}~{rule.close.strftime('%H:%M')}) "
            "밖에 도착할 수 있습니다."
        ),
    )
