"""도메인 값 객체 ↔ ORM 행 매핑.

배치 주석: 계획서에 없던 파일이다. 매핑 로직을 서비스에 두면 C21 이 비대해지고,
ORM 모델에 두면 도메인 지식이 storage 로 새어든다. 전용 모듈로 분리했다.

시간은 UTC 저장 / KST 표시 (NFR-7). 목록형 값은 JSON 문자열로 보관한다.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, time

from app.domain.categories import classify_category
from app.domain.models import (
    Coordinate,
    DayRule,
    ItemWarning,
    ItineraryItem,
    OpeningHours,
    Place,
    PlaceCategory,
    PlaceSource,
    TravelMode,
    TripSpec,
    WarningType,
)
from app.storage.models import (
    ItineraryItemRow,
    OpeningHoursRow,
    PlaceRow,
    TripRow,
    UnresolvedCandidateRow,
)


# --- Place -----------------------------------------------------------------
def place_to_row(place: Place) -> PlaceRow:
    return PlaceRow(
        place_id=place.place_id,
        name=place.name,
        latitude=place.coordinate.lat,
        longitude=place.coordinate.lng,
        category=place.category.value,
        category_raw=place.category_raw,
        road_address=place.road_address,
        address=place.address,
        phone=place.phone,
        naver_link=place.naver_link,
        source=place.source.value,
        resolved_from=place.resolved_from,
        match_score=place.match_score,
    )


def row_to_place(row: PlaceRow) -> Place:
    return Place(
        place_id=row.place_id,
        name=row.name,
        coordinate=Coordinate(lat=row.latitude, lng=row.longitude),
        category=PlaceCategory(row.category),
        category_raw=row.category_raw,
        road_address=row.road_address,
        address=row.address,
        phone=row.phone,
        naver_link=row.naver_link,
        source=PlaceSource(row.source),
        resolved_from=row.resolved_from,
        match_score=row.match_score,
        opening_hours=row_to_opening_hours(row.opening_hours),
    )


def row_to_opening_hours(row: OpeningHoursRow | None) -> OpeningHours | None:
    """BR-35 — 레코드가 없으면 None 이 정상이다."""
    if row is None:
        return None
    rules = tuple(DayRule.from_dict(r) for r in json.loads(row.weekday_rules_json))
    return OpeningHours(weekday_rules=rules, entered_by_user=True)


def opening_hours_to_row(place_id: str, hours: OpeningHours) -> OpeningHoursRow:
    return OpeningHoursRow(
        place_id=place_id,
        weekday_rules_json=json.dumps(
            [r.to_dict() for r in hours.weekday_rules], ensure_ascii=False
        ),
        entered_by_user=True,  # 외부에서 채우는 경로가 없다
    )


# --- ItineraryItem ---------------------------------------------------------
def item_to_row(item: ItineraryItem, day_id: str) -> ItineraryItemRow:
    return ItineraryItemRow(
        item_id=item.item_id,
        day_id=day_id,
        place_id=item.place.place_id,
        position=item.position,
        arrival_at=item.arrival_at,
        departure_at=item.departure_at,
        stay_minutes=item.stay_minutes,
        time_fixed=item.time_fixed,
        fixed_time=item.fixed_time.isoformat() if item.fixed_time else None,
        travel_mode=item.travel_mode.value if item.travel_mode else None,
        memo=item.memo,
        warnings_json=json.dumps([w.to_dict() for w in item.warnings], ensure_ascii=False),
    )


def row_to_item(row: ItineraryItemRow) -> ItineraryItem:
    warnings = tuple(
        ItemWarning(type=WarningType(w["type"]), detail=w["detail"])
        for w in json.loads(row.warnings_json or "[]")
    )
    return ItineraryItem(
        item_id=row.item_id,
        place=row_to_place(row.place),
        stay_minutes=row.stay_minutes,
        position=row.position,
        arrival_at=row.arrival_at,
        departure_at=row.departure_at,
        time_fixed=row.time_fixed,
        fixed_time=time.fromisoformat(row.fixed_time) if row.fixed_time else None,
        travel_mode=TravelMode(row.travel_mode) if row.travel_mode else None,
        memo=row.memo,
        warnings=warnings,
    )


# --- Trip ------------------------------------------------------------------
def spec_to_row(spec: TripSpec, trip_id: str | None = None) -> TripRow:
    return TripRow(
        trip_id=trip_id or str(uuid.uuid4()),
        title=spec.title,
        destination=spec.destination,
        start_date=spec.start_date,
        end_date=spec.end_date,
        party_size=spec.party_size,
        style_tags=",".join(spec.style_tags),
        day_start_time=spec.day_start_time.isoformat(),
        day_end_time=spec.day_end_time.isoformat(),
        default_travel_mode=spec.default_travel_mode.value,
        budget_level=spec.budget_level.value if spec.budget_level else None,
    )


def row_to_spec(row: TripRow) -> TripSpec:
    from app.domain.models import BudgetLevel

    return TripSpec(
        title=row.title,
        destination=row.destination,
        start_date=row.start_date,
        end_date=row.end_date,
        party_size=row.party_size,
        style_tags=tuple(t for t in row.style_tags.split(",") if t),
        day_start_time=time.fromisoformat(row.day_start_time),
        day_end_time=time.fromisoformat(row.day_end_time),
        default_travel_mode=TravelMode(row.default_travel_mode),
        budget_level=BudgetLevel(row.budget_level) if row.budget_level else None,
    )


def day_date(row: TripRow, day_index: int) -> date:
    from datetime import timedelta

    return row.start_date + timedelta(days=day_index - 1)


# --- 미해결 후보 -----------------------------------------------------------
def unresolved_to_row(trip_id: str, unresolved) -> UnresolvedCandidateRow:  # type: ignore[no-untyped-def]
    """BR-18 — 이 행은 ItineraryItem 이 되지 못한 후보만 담는다."""
    return UnresolvedCandidateRow(
        candidate_id=str(uuid.uuid4()),
        trip_id=trip_id,
        day_index=unresolved.day_index,
        raw_name=unresolved.candidate.raw_name,
        category_hint=unresolved.candidate.category_hint,
        reason=unresolved.candidate.reason,
        failure_code=unresolved.failure_code.value,
        best_candidate_name=unresolved.best_candidate_name,
        best_match_score=unresolved.best_match_score,
    )


def default_category_for(hint: str | None) -> PlaceCategory:
    return classify_category(hint)
