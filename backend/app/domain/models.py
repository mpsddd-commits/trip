"""C14 DomainModels — 순수 값 객체와 도메인 열거형.

근거:
    domain-entities.md §2, §4, §5
    BR-15   좌표는 국내 범위(위도 33~39 / 경도 124~132)를 벗어나면 생성 거부
    BR-08   PlaceCandidate 에는 주소·좌표·전화 필드가 **존재하지 않는다**
    P-17    from_dict(to_dict(x)) == x  (PBT-02 / PBT-R1)
    P-18    Coordinate 는 범위 밖 입력을 항상 거부

DD-16: 이 모듈은 app 내부의 어떤 계층도 import 하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, time
from enum import StrEnum
from typing import Any, Self

# --- 국내 좌표 범위 (BR-15) ------------------------------------------------
LAT_MIN, LAT_MAX = 33.0, 39.0
LNG_MIN, LNG_MAX = 124.0, 132.0


class CoordinateOutOfRangeError(ValueError):
    """좌표가 국내 범위를 벗어났다.

    좌표계를 잘못 해석하면(지역검색 mapx/mapy 미확정 사항) 값이 이 범위를
    크게 벗어난다. 조용히 저장되는 대신 즉시 실패시켜 오류를 드러낸다.
    """


# ---------------------------------------------------------------------------
# 열거형
# ---------------------------------------------------------------------------
class TravelMode(StrEnum):
    WALK = "WALK"
    CAR = "CAR"
    TRANSIT = "TRANSIT"


class PlaceCategory(StrEnum):
    RESTAURANT = "RESTAURANT"
    CAFE = "CAFE"
    ATTRACTION = "ATTRACTION"
    MUSEUM = "MUSEUM"
    SHOPPING = "SHOPPING"
    ACCOMMODATION = "ACCOMMODATION"
    OTHER = "OTHER"


class PlaceSource(StrEnum):
    NAVER_LOCAL = "NAVER_LOCAL"
    USER_MANUAL = "USER_MANUAL"
    MOCK = "MOCK"


class LegSource(StrEnum):
    DIRECTIONS_API = "DIRECTIONS_API"
    HAVERSINE_WALK = "HAVERSINE_WALK"
    HAVERSINE_TRANSIT = "HAVERSINE_TRANSIT"
    HAVERSINE_CAR_FALLBACK = "HAVERSINE_CAR_FALLBACK"


class WarningType(StrEnum):
    OUTSIDE_OPENING_HOURS = "OUTSIDE_OPENING_HOURS"
    FIXED_TIME_CONFLICT = "FIXED_TIME_CONFLICT"
    DAY_OVERFLOW = "DAY_OVERFLOW"
    ESTIMATED_TRAVEL_TIME = "ESTIMATED_TRAVEL_TIME"


class ResolveFailureCode(StrEnum):
    NO_SEARCH_RESULT = "NO_SEARCH_RESULT"
    LOW_SIMILARITY = "LOW_SIMILARITY"
    OUT_OF_REGION = "OUT_OF_REGION"
    CATEGORY_MISMATCH = "CATEGORY_MISMATCH"
    INVALID_COORDINATE = "INVALID_COORDINATE"
    SEARCH_UNAVAILABLE = "SEARCH_UNAVAILABLE"


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class GenerationStep(StrEnum):
    DRAFTING = "DRAFTING"
    RESOLVING = "RESOLVING"
    ROUTING = "ROUTING"
    OPTIMIZING = "OPTIMIZING"
    SCHEDULING = "SCHEDULING"
    SAVING = "SAVING"


class BudgetLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# BR-52 — 카테고리별 기본 체류시간(분). LLM 제안값이 있으면 그쪽이 우선한다.
DEFAULT_STAY_MINUTES: dict[PlaceCategory, int] = {
    PlaceCategory.RESTAURANT: 60,
    PlaceCategory.CAFE: 40,
    PlaceCategory.ATTRACTION: 90,
    PlaceCategory.MUSEUM: 120,
    PlaceCategory.SHOPPING: 90,
    PlaceCategory.ACCOMMODATION: 30,
    PlaceCategory.OTHER: 60,
}


# ---------------------------------------------------------------------------
# 값 객체
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Coordinate:
    lat: float
    lng: float

    def __post_init__(self) -> None:
        # BR-15 / P-18
        if not (LAT_MIN <= self.lat <= LAT_MAX and LNG_MIN <= self.lng <= LNG_MAX):
            raise CoordinateOutOfRangeError(
                f"좌표가 국내 범위를 벗어났습니다: lat={self.lat}, lng={self.lng}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {"lat": self.lat, "lng": self.lng}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(lat=float(data["lat"]), lng=float(data["lng"]))


@dataclass(frozen=True, slots=True)
class DayRule:
    weekday: int  # 0=월 ... 6=일
    open: time | None = None
    close: time | None = None
    closed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "weekday": self.weekday,
            "open": self.open.isoformat() if self.open else None,
            "close": self.close.isoformat() if self.close else None,
            "closed": self.closed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            weekday=int(data["weekday"]),
            open=time.fromisoformat(data["open"]) if data.get("open") else None,
            close=time.fromisoformat(data["close"]) if data.get("close") else None,
            closed=bool(data.get("closed", False)),
        )


@dataclass(frozen=True, slots=True)
class OpeningHours:
    """사용자가 직접 입력한 영업시간 (BR-35, Q10=A).

    외부 API 나 LLM 에서 자동 수집하지 않는다. `entered_by_user` 는 항상 True 다.
    """

    weekday_rules: tuple[DayRule, ...] = ()
    entered_by_user: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "weekday_rules": [r.to_dict() for r in self.weekday_rules],
            "entered_by_user": self.entered_by_user,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            weekday_rules=tuple(DayRule.from_dict(r) for r in data.get("weekday_rules", [])),
            entered_by_user=bool(data.get("entered_by_user", True)),
        )


@dataclass(frozen=True, slots=True)
class Place:
    place_id: str
    name: str
    coordinate: Coordinate
    category: PlaceCategory = PlaceCategory.OTHER
    road_address: str | None = None
    address: str | None = None
    category_raw: str | None = None
    phone: str | None = None
    naver_link: str | None = None
    source: PlaceSource = PlaceSource.NAVER_LOCAL
    resolved_from: str | None = None
    match_score: float | None = None
    opening_hours: OpeningHours | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "place_id": self.place_id,
            "name": self.name,
            "coordinate": self.coordinate.to_dict(),
            "category": self.category.value,
            "road_address": self.road_address,
            "address": self.address,
            "category_raw": self.category_raw,
            "phone": self.phone,
            "naver_link": self.naver_link,
            "source": self.source.value,
            "resolved_from": self.resolved_from,
            "match_score": self.match_score,
            "opening_hours": self.opening_hours.to_dict() if self.opening_hours else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        oh = data.get("opening_hours")
        return cls(
            place_id=data["place_id"],
            name=data["name"],
            coordinate=Coordinate.from_dict(data["coordinate"]),
            category=PlaceCategory(data.get("category", PlaceCategory.OTHER.value)),
            road_address=data.get("road_address"),
            address=data.get("address"),
            category_raw=data.get("category_raw"),
            phone=data.get("phone"),
            naver_link=data.get("naver_link"),
            source=PlaceSource(data.get("source", PlaceSource.NAVER_LOCAL.value)),
            resolved_from=data.get("resolved_from"),
            match_score=data.get("match_score"),
            opening_hours=OpeningHours.from_dict(oh) if oh else None,
        )


@dataclass(frozen=True, slots=True)
class ItemWarning:
    type: WarningType
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type.value, "detail": self.detail}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(type=WarningType(data["type"]), detail=data["detail"])


@dataclass(frozen=True, slots=True)
class TravelLeg:
    from_index: int
    to_index: int
    mode: TravelMode
    duration_sec: int
    distance_m: int
    source: LegSource
    is_estimate: bool
    path: tuple[Coordinate, ...] = ()

    def __post_init__(self) -> None:
        # P-11 — 비음수 보장
        if self.duration_sec < 0 or self.distance_m < 0:
            raise ValueError("이동시간·거리는 음수가 될 수 없습니다.")
        # BR-27 — 대중교통은 항상 근사이며 실경로를 갖지 않는다
        if self.mode is TravelMode.TRANSIT and (not self.is_estimate or self.path):
            raise ValueError("대중교통 구간은 항상 근사치이며 경로 좌표를 가질 수 없습니다.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_index": self.from_index,
            "to_index": self.to_index,
            "mode": self.mode.value,
            "duration_sec": self.duration_sec,
            "distance_m": self.distance_m,
            "source": self.source.value,
            "is_estimate": self.is_estimate,
            "path": [c.to_dict() for c in self.path],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            from_index=int(data["from_index"]),
            to_index=int(data["to_index"]),
            mode=TravelMode(data["mode"]),
            duration_sec=int(data["duration_sec"]),
            distance_m=int(data["distance_m"]),
            source=LegSource(data["source"]),
            is_estimate=bool(data["is_estimate"]),
            path=tuple(Coordinate.from_dict(c) for c in data.get("path", [])),
        )


@dataclass(frozen=True, slots=True)
class ItineraryItem:
    item_id: str
    place: Place
    stay_minutes: int
    position: int = 0
    arrival_at: datetime | None = None
    departure_at: datetime | None = None
    time_fixed: bool = False
    fixed_time: time | None = None
    travel_mode: TravelMode | None = None
    memo: str | None = None
    warnings: tuple[ItemWarning, ...] = ()

    def __post_init__(self) -> None:
        if self.stay_minutes < 1:
            raise ValueError("체류시간은 1분 이상이어야 합니다.")
        if self.time_fixed and self.fixed_time is None:
            raise ValueError("time_fixed 인 항목은 fixed_time 이 필요합니다.")

    def with_times(self, arrival: datetime, departure: datetime) -> "ItineraryItem":
        return replace(self, arrival_at=arrival, departure_at=departure)

    def with_warnings(self, warnings: tuple[ItemWarning, ...]) -> "ItineraryItem":
        return replace(self, warnings=warnings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "place": self.place.to_dict(),
            "stay_minutes": self.stay_minutes,
            "position": self.position,
            "arrival_at": self.arrival_at.isoformat() if self.arrival_at else None,
            "departure_at": self.departure_at.isoformat() if self.departure_at else None,
            "time_fixed": self.time_fixed,
            "fixed_time": self.fixed_time.isoformat() if self.fixed_time else None,
            "travel_mode": self.travel_mode.value if self.travel_mode else None,
            "memo": self.memo,
            "warnings": [w.to_dict() for w in self.warnings],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            item_id=data["item_id"],
            place=Place.from_dict(data["place"]),
            stay_minutes=int(data["stay_minutes"]),
            position=int(data.get("position", 0)),
            arrival_at=datetime.fromisoformat(data["arrival_at"]) if data.get("arrival_at") else None,
            departure_at=datetime.fromisoformat(data["departure_at"]) if data.get("departure_at") else None,
            time_fixed=bool(data.get("time_fixed", False)),
            fixed_time=time.fromisoformat(data["fixed_time"]) if data.get("fixed_time") else None,
            travel_mode=TravelMode(data["travel_mode"]) if data.get("travel_mode") else None,
            memo=data.get("memo"),
            warnings=tuple(ItemWarning.from_dict(w) for w in data.get("warnings", [])),
        )


@dataclass(frozen=True, slots=True)
class PlaceCandidate:
    """LLM 초안이 제시한 장소 후보 (BR-08).

    🔴 주소·좌표·전화·영업시간·가격 필드가 **의도적으로 존재하지 않는다.**
    사실성이 중요한 값은 전부 네이버 지역검색 그라운딩(C23)으로만 채워진다.
    """

    raw_name: str
    category_hint: str | None = None
    suggested_stay_minutes: int | None = None
    reason: str = ""
    preferred_time_slot: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_name": self.raw_name,
            "category_hint": self.category_hint,
            "suggested_stay_minutes": self.suggested_stay_minutes,
            "reason": self.reason,
            "preferred_time_slot": self.preferred_time_slot,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            raw_name=data["raw_name"],
            category_hint=data.get("category_hint"),
            suggested_stay_minutes=data.get("suggested_stay_minutes"),
            reason=data.get("reason", ""),
            preferred_time_slot=data.get("preferred_time_slot"),
        )


@dataclass(frozen=True, slots=True)
class UnresolvedCandidate:
    """그라운딩에 실패한 후보 (BR-12, BR-18).

    이 값은 ItineraryItem 이 되지 못하고 "확인 필요" 목록으로만 노출된다.
    """

    candidate: PlaceCandidate
    day_index: int
    failure_code: ResolveFailureCode
    best_candidate_name: str | None = None
    best_match_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "day_index": self.day_index,
            "failure_code": self.failure_code.value,
            "best_candidate_name": self.best_candidate_name,
            "best_match_score": self.best_match_score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            candidate=PlaceCandidate.from_dict(data["candidate"]),
            day_index=int(data["day_index"]),
            failure_code=ResolveFailureCode(data["failure_code"]),
            best_candidate_name=data.get("best_candidate_name"),
            best_match_score=data.get("best_match_score"),
        )


@dataclass(frozen=True, slots=True)
class TripSpec:
    """여행 생성 입력 (FR-1)."""

    title: str
    destination: str
    start_date: date
    end_date: date
    party_size: int = 2
    style_tags: tuple[str, ...] = ()
    day_start_time: time = time(9, 0)
    day_end_time: time = time(21, 0)
    default_travel_mode: TravelMode = TravelMode.TRANSIT
    budget_level: BudgetLevel | None = None

    @property
    def day_count(self) -> int:
        return (self.end_date - self.start_date).days + 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "destination": self.destination,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "party_size": self.party_size,
            "style_tags": list(self.style_tags),
            "day_start_time": self.day_start_time.isoformat(),
            "day_end_time": self.day_end_time.isoformat(),
            "default_travel_mode": self.default_travel_mode.value,
            "budget_level": self.budget_level.value if self.budget_level else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            title=data["title"],
            destination=data["destination"],
            start_date=date.fromisoformat(data["start_date"]),
            end_date=date.fromisoformat(data["end_date"]),
            party_size=int(data.get("party_size", 2)),
            style_tags=tuple(data.get("style_tags", [])),
            day_start_time=time.fromisoformat(data.get("day_start_time", "09:00:00")),
            day_end_time=time.fromisoformat(data.get("day_end_time", "21:00:00")),
            default_travel_mode=TravelMode(data.get("default_travel_mode", TravelMode.TRANSIT.value)),
            budget_level=BudgetLevel(data["budget_level"]) if data.get("budget_level") else None,
        )


@dataclass(frozen=True, slots=True)
class OptimizeConstraints:
    """순서 최적화 제약 (BR-19)."""

    anchor_start: str | None = None
    anchor_end: str | None = None
    fixed_item_ids: frozenset[str] = field(default_factory=frozenset)
