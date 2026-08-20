"""`.ics` 내보내기 라우터 — FR-26, BR-45, BR-46."""

from __future__ import annotations

from fastapi import APIRouter, Response

from app.api.deps import ContainerDep, rate_limit
from app.core.enums import EndpointTier
from app.domain import ics

router = APIRouter(prefix="/api/trips", tags=["export"])


@router.get("/{trip_id}/export.ics", dependencies=[rate_limit(EndpointTier.CHEAP)])
async def export_ics(trip_id: str, container: ContainerDep) -> Response:
    """일정을 iCalendar 로 내보낸다.

    BR-46 — `travel_mode`·`warnings`·`category`·`phone` 은 VEVENT 표준 필드가
    없어 손실된다(X- 속성으로만 내보내고 되읽지 않는다).
    """
    view = await container.trips.get(trip_id)
    items = [item for day in view.days for item in day]
    body = ics.build(view.spec.title, items)
    filename = f"trip-{trip_id[:8]}.ics"
    return Response(
        content=body,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # SEC-04 관련 — 개인 일정이므로 캐시하지 않는다
            "Cache-Control": "no-store",
        },
    )
