"""C33 ApiSchemas — 요청·응답 스키마.

근거:
    SEC-05  타입·길이·범위·형식 검증. 이 스키마가 1차 방어선이다
    BR-01~05  규모·형식 제약
    Q7=A / UD-3  이 스키마가 OpenAPI 를 통해 **프론트 TS 타입의 원천**이 된다
    BR-39   목록 응답 스키마를 정의하지 않는다 (열거 방지)
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.models import (
    BudgetLevel,
    Coordinate,
    GenerationStep,
    ItineraryItem,
    JobState,
    PlaceCategory,
    PlaceSource,
    ResolveFailureCode,
    TravelMode,
    TripSpec,
    WarningType,
)

_Title = Annotated[str, Field(min_length=1, max_length=100)]
_Destination = Annotated[str, Field(min_length=1, max_length=50)]
_Memo = Annotated[str, Field(max_length=500)]


class TripSpecIn(BaseModel):
    """FR-1 — 여행 생성 입력."""

    model_config = ConfigDict(extra="forbid")

    title: _Title
    destination: _Destination
    start_date: date
    end_date: date
    party_size: Annotated[int, Field(ge=1, le=20)] = 2
    style_tags: Annotated[list[Annotated[str, Field(max_length=20)]], Field(max_length=8)] = []
    day_start_time: time = time(9, 0)
    day_end_time: time = time(21, 0)
    default_travel_mode: TravelMode = TravelMode.TRANSIT
    budget_level: BudgetLevel | None = None

    @model_validator(mode="after")
    def _check(self) -> "TripSpecIn":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if self.day_end_time <= self.day_start_time:
            raise ValueError("day_end_time must be after day_start_time")
        return self

    def to_domain(self) -> TripSpec:
        return TripSpec(
            title=self.title,
            destination=self.destination,
            start_date=self.start_date,
            end_date=self.end_date,
            party_size=self.party_size,
            style_tags=tuple(self.style_tags),
            day_start_time=self.day_start_time,
            day_end_time=self.day_end_time,
            default_travel_mode=self.default_travel_mode,
            budget_level=self.budget_level,
        )


class TripMetaPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: _Title | None = None


class ItemPatch(BaseModel):
    """FR-7, FR-11 — 항목 편집."""

    model_config = ConfigDict(extra="forbid")

    stay_minutes: Annotated[int, Field(ge=1, le=720)] | None = None
    memo: _Memo | None = None
    travel_mode: TravelMode | None = None
    time_fixed: bool | None = None
    fixed_time: time | None = None

    @model_validator(mode="after")
    def _check(self) -> "ItemPatch":
        if self.time_fixed and self.fixed_time is None:
            raise ValueError("fixed_time is required when time_fixed is true")
        return self


class ItemCreate(BaseModel):
    """FR-5 — 검색 결과에서 항목 추가."""

    model_config = ConfigDict(extra="forbid")

    name: Annotated[str, Field(min_length=1, max_length=120)]
    latitude: Annotated[float, Field(ge=33.0, le=39.0)]  # BR-15
    longitude: Annotated[float, Field(ge=124.0, le=132.0)]  # BR-15
    category_raw: Annotated[str, Field(max_length=120)] | None = None
    road_address: Annotated[str, Field(max_length=200)] | None = None
    address: Annotated[str, Field(max_length=200)] | None = None
    phone: Annotated[str, Field(max_length=40)] | None = None
    stay_minutes: Annotated[int, Field(ge=1, le=720)] | None = None
    memo: _Memo | None = None

    def coordinate(self) -> Coordinate:
        return Coordinate(lat=self.latitude, lng=self.longitude)


class ReorderIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_ids: Annotated[list[Annotated[str, Field(max_length=36)]], Field(max_length=15)]


class OptimizeIn(BaseModel):
    """FR-8 — 순서 최적화 제약 (BR-19)."""

    model_config = ConfigDict(extra="forbid")

    anchor_start: Annotated[str, Field(max_length=36)] | None = None
    anchor_end: Annotated[str, Field(max_length=36)] | None = None


class DayRuleIn(BaseModel):
    """FR-13 — **사용자 입력 영업시간** (BR-35). 외부에서 채우는 경로는 없다."""

    model_config = ConfigDict(extra="forbid")

    weekday: Annotated[int, Field(ge=0, le=6)]
    open: time | None = None
    close: time | None = None
    closed: bool = False


class OpeningHoursIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weekday_rules: Annotated[list[DayRuleIn], Field(max_length=7)]


class JobAccepted(BaseModel):
    job_id: str
    trip_id: str
    state: Literal["queued"]


class ProblemDetails(BaseModel):
    """Q6=A — RFC 9457. `detail` 은 **고정 문구만** 담는다 (BR-58)."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
    code: str
    correlation_id: str


# ---------------------------------------------------------------------------
# 응답 모델 (개정 A-2)
#
# 🔴 배경: 라우터가 `-> dict` 를 반환하던 시기에는 OpenAPI 가 22개 중 17개 응답을
#    `{"type":"object"}`(무타입)으로 생성했다. 그러면 `openapi-typescript` 가 만드는
#    TS 타입이 `unknown` 이 되어 **UD-3/DD-10 의 목적("계약 불일치를 컴파일 오류로
#    검출")이 완전히 무력화**된다. 실기동으로 확인 후 응답 모델을 도입했다.
#
# 원칙: 이 모델들은 도메인 값 객체의 `to_dict()` 출력과 **필드 이름·구조가 일치**해야 한다.
#       어긋나면 FastAPI 응답 검증에서 실패하므로, 계약 불일치가 런타임에 드러난다.
# ---------------------------------------------------------------------------
class CoordinateOut(BaseModel):
    lat: float
    lng: float


class DayRuleOut(BaseModel):
    weekday: int
    open: time | None = None
    close: time | None = None
    closed: bool = False


class OpeningHoursOut(BaseModel):
    """BR-35 — 사용자가 입력한 경우에만 존재한다(대개 `null`)."""

    weekday_rules: list[DayRuleOut] = []
    entered_by_user: bool = True


class PlaceOut(BaseModel):
    place_id: str
    name: str
    coordinate: CoordinateOut
    category: PlaceCategory
    road_address: str | None = None
    address: str | None = None
    category_raw: str | None = None
    phone: str | None = None
    naver_link: str | None = None
    source: PlaceSource
    # 그라운딩 추적성 (FR-3) — 어떤 후보에서 어떤 유사도로 해석됐는지
    resolved_from: str | None = None
    match_score: float | None = None
    opening_hours: OpeningHoursOut | None = None


class ItemWarningOut(BaseModel):
    type: WarningType
    detail: str


class ItineraryItemOut(BaseModel):
    item_id: str
    place: PlaceOut
    stay_minutes: int
    position: int
    arrival_at: datetime | None = None
    departure_at: datetime | None = None
    time_fixed: bool = False
    fixed_time: time | None = None
    travel_mode: TravelMode | None = None
    memo: str | None = None
    warnings: list[ItemWarningOut] = []


class TripDayOut(BaseModel):
    day_index: int
    items: list[ItineraryItemOut]


class UnresolvedOut(BaseModel):
    """FR-3 / BR-18 — 일정에 들어가지 못한 후보. 프론트가 "확인 필요"로 노출한다."""

    raw_name: str
    day_index: int
    category_hint: str | None = None
    reason: str = ""
    failure_code: ResolveFailureCode
    best_candidate_name: str | None = None
    best_match_score: float | None = None


class _TripBase(BaseModel):
    trip_id: str
    title: str
    destination: str
    start_date: date
    end_date: date
    party_size: int
    style_tags: list[str] = []
    day_start_time: time
    day_end_time: time
    default_travel_mode: TravelMode
    budget_level: BudgetLevel | None = None
    days: list[TripDayOut]


class TripOut(_TripBase):
    unresolved: list[UnresolvedOut] = []
    share_token: str | None = None


class ReadOnlyTripOut(_TripBase):
    """BR-37 / DD-25 — 공유 조회 응답.

    🔴 `share_token` 을 포함하지 않는다. 열람자는 토큰을 재발급·폐기할 권한이 없다.
    """

    read_only: Literal[True] = True


class JobStatusOut(BaseModel):
    job_id: str
    trip_id: str
    state: JobState
    step: GenerationStep | None = None
    progress: float
    resolved_count: int
    unresolved_count: int
    problem: dict[str, Any] | None = None


class PagedPlacesOut(BaseModel):
    items: list[PlaceOut]
    page: int
    page_size: int
    has_more: bool


class SuggestionsOut(BaseModel):
    items: list[PlaceOut]


class BlogRefOut(BaseModel):
    title: str
    link: str
    blogger_name: str | None = None
    post_date: str | None = None


class ImageRefOut(BaseModel):
    thumbnail_url: str
    link: str
    source_title: str = ""


class PlaceContentOut(BaseModel):
    """FR-20·21 / BR-40 — `sources` 가 3건 미만이면 `highlights` 는 반드시 빈 목록이다."""

    place_id: str
    highlights: list[str] = []
    sources: list[BlogRefOut] = []
    images: list[ImageRefOut] = []
    is_ai_summary: bool = True


class ShareTokenOut(BaseModel):
    share_token: str
    url: str


class LimitsOut(BaseModel):
    """폼 검증 상한. 프론트가 숫자를 하드코딩하지 않도록 서버가 내려준다 (WBR-10)."""

    max_trip_days: int
    max_items_per_day: int
    max_items_per_trip: int


class RuntimeConfigOut(BaseModel):
    """개정 A-1 — `GET /api/config` 응답.

    🔴 **검색 API 키와 LLM 키는 절대 포함하지 않는다** (SEC-11).
    `map_client_key` 만 예외인데, 지도 SDK 특성상 브라우저에 노출될 수밖에 없고
    도메인 화이트리스트로 방어하기 때문이다 (CON-3).
    """

    map_client_key: str | None
    modes: dict[str, str]
    limits: LimitsOut


class HealthOut(BaseModel):
    status: Literal["ok"]


class QuotaUsageOut(BaseModel):
    call_count: int
    error_count: int
    daily_limit: int | None = None


class ReadinessOut(BaseModel):
    status: Literal["ok", "degraded"]
    modes: dict[str, str]
    quota: dict[str, QuotaUsageOut]
    circuits: dict[str, str]
    database: bool
    # CON-3 — 키 값이 아니라 **설정 여부만** 알린다 (SEP-3)
    map_client_key_configured: bool


def item_to_response(item: ItineraryItem) -> dict:
    return item.to_dict()
