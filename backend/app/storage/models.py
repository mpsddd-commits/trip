"""ORM 매핑 — 12 테이블.

근거: domain-entities.md §2, §3
    BR-54  여행 하드 삭제 시 하위 전부 연쇄 삭제
    BR-36  share_token 은 trip_id 와 독립. UNIQUE 인덱스
    BR-59  audit_events 는 **추가 전용** — 수정·삭제 연산을 제공하지 않는다
    SEC-05 파라미터 바인딩만 사용 (ORM 이 보장)

시간은 전부 UTC 로 저장한다 (NFR-7).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """항상 **타임존이 붙은 UTC** 를 돌려주는 DateTime.

    🔴 왜 필요한가:
       ``DateTime(timezone=True)`` 로 선언해도 **SQLite 는 타임존을 저장하지 않는다.**
       SQLAlchemy 가 돌려주는 값은 tzinfo 가 없는 naive datetime 이다. 그러면

         · aware 인 ``utcnow()`` 와 비교할 때 ``TypeError`` 가 나고
         · ``isoformat()`` 이 오프셋 없는 문자열(``2026-09-10T00:00:00``)을 만든다.

       두 번째가 특히 조용하다. 그 문자열을 받은 브라우저의 ``new Date()`` 는 이것을
       **현지 시각**으로 해석하므로, KST 사용자에게는 일정 전체가 **9시간 어긋나** 보인다.
       오류도 경고도 나지 않는다. 실제로 09:00 시작 일정이 00:00 으로 표시됐다.

       컬럼마다 따로 막으면 새 컬럼이 생길 때 또 빠진다. 타입 하나로 처리한다.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self) -> None:
        super().__init__(timezone=True)

    def process_bind_param(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        # 애플리케이션 코드는 항상 aware 값을 만든다(`utcnow()`).
        # 혹시 naive 가 들어오면 UTC 로 간주한다 — 저장 규약이 UTC 이기 때문이다 (NFR-7).
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: object) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def utcnow() -> datetime:
    return datetime.now(tz=UTC)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# 여행 애그리게이트
# ---------------------------------------------------------------------------
class TripRow(Base):
    __tablename__ = "trips"

    trip_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    destination: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    party_size: Mapped[int] = mapped_column(Integer, default=2)
    style_tags: Mapped[str] = mapped_column(String(200), default="")  # 쉼표 구분
    day_start_time: Mapped[str] = mapped_column(String(8), default="09:00:00")
    day_end_time: Mapped[str] = mapped_column(String(8), default="21:00:00")
    default_travel_mode: Mapped[str] = mapped_column(String(16), default="TRANSIT")
    budget_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # BR-36 — trip_id 로부터 도출되지 않는 독립 난수
    share_token: Mapped[str | None] = mapped_column(String(43), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), default=utcnow, onupdate=utcnow
    )

    days: Mapped[list["TripDayRow"]] = relationship(
        back_populates="trip", cascade="all, delete-orphan", order_by="TripDayRow.day_index"
    )
    unresolved: Mapped[list["UnresolvedCandidateRow"]] = relationship(
        cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_trips_share_token", "share_token"),)


class TripDayRow(Base):
    __tablename__ = "trip_days"

    day_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trip_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trips.trip_id", ondelete="CASCADE"), index=True
    )
    day_index: Mapped[int] = mapped_column(Integer)
    date: Mapped[date] = mapped_column(Date)

    trip: Mapped[TripRow] = relationship(back_populates="days")
    items: Mapped[list["ItineraryItemRow"]] = relationship(
        back_populates="day", cascade="all, delete-orphan", order_by="ItineraryItemRow.position"
    )

    __table_args__ = (UniqueConstraint("trip_id", "day_index", name="uq_trip_day_index"),)


class PlaceRow(Base):
    __tablename__ = "places"

    place_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(24), default="OTHER")
    category_raw: Mapped[str | None] = mapped_column(String(120), nullable=True)
    road_address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    naver_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="NAVER_LOCAL")
    resolved_from: Mapped[str | None] = mapped_column(String(120), nullable=True)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    opening_hours: Mapped["OpeningHoursRow | None"] = relationship(
        back_populates="place", cascade="all, delete-orphan", uselist=False
    )
    content: Mapped["PlaceContentRow | None"] = relationship(
        back_populates="place", cascade="all, delete-orphan", uselist=False
    )

    __table_args__ = (Index("ix_places_coord", "latitude", "longitude"),)


class OpeningHoursRow(Base):
    """BR-35 — **사용자가 입력한 경우에만 레코드가 존재한다.**

    외부 API 나 LLM 이 이 테이블을 채우는 경로는 존재하지 않는다.
    """

    __tablename__ = "opening_hours"

    place_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("places.place_id", ondelete="CASCADE"), primary_key=True
    )
    weekday_rules_json: Mapped[str] = mapped_column(Text, default="[]")
    entered_by_user: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utcnow)

    place: Mapped[PlaceRow] = relationship(back_populates="opening_hours")


class ItineraryItemRow(Base):
    __tablename__ = "itinerary_items"

    item_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trip_days.day_id", ondelete="CASCADE"), index=True
    )
    place_id: Mapped[str] = mapped_column(String(36), ForeignKey("places.place_id"))
    position: Mapped[int] = mapped_column(Integer)
    arrival_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    departure_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    stay_minutes: Mapped[int] = mapped_column(Integer, default=60)
    time_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    fixed_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    travel_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    memo: Mapped[str | None] = mapped_column(String(500), nullable=True)
    warnings_json: Mapped[str] = mapped_column(Text, default="[]")

    day: Mapped[TripDayRow] = relationship(back_populates="items")
    place: Mapped[PlaceRow] = relationship()

    __table_args__ = (UniqueConstraint("day_id", "position", name="uq_day_position"),)


class TravelLegRow(Base):
    __tablename__ = "travel_legs"

    leg_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trip_days.day_id", ondelete="CASCADE"), index=True
    )
    from_item_id: Mapped[str] = mapped_column(String(36))
    to_item_id: Mapped[str] = mapped_column(String(36))
    mode: Mapped[str] = mapped_column(String(16))
    duration_sec: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(32))
    is_estimate: Mapped[bool] = mapped_column(Boolean, default=True)
    path_json: Mapped[str] = mapped_column(Text, default="[]")


class UnresolvedCandidateRow(Base):
    """FR-3 / BR-18 — 그라운딩 실패 후보. **ItineraryItem 이 되지 못한 것들.**"""

    __tablename__ = "unresolved_candidates"

    candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trip_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trips.trip_id", ondelete="CASCADE"), index=True
    )
    day_index: Mapped[int] = mapped_column(Integer)
    raw_name: Mapped[str] = mapped_column(String(120))
    category_hint: Mapped[str | None] = mapped_column(String(60), nullable=True)
    reason: Mapped[str] = mapped_column(String(500), default="")
    failure_code: Mapped[str] = mapped_column(String(32))
    best_candidate_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    best_match_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class PlaceContentRow(Base):
    """FR-20 / BR-40 — sources 가 3건 미만이면 highlights 는 반드시 빈 목록."""

    __tablename__ = "place_contents"

    place_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("places.place_id", ondelete="CASCADE"), primary_key=True
    )
    highlights_json: Mapped[str] = mapped_column(Text, default="[]")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    images_json: Mapped[str] = mapped_column(Text, default="[]")
    is_ai_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    generated_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utcnow)

    place: Mapped[PlaceRow] = relationship(back_populates="content")


# ---------------------------------------------------------------------------
# 운영 테이블
# ---------------------------------------------------------------------------
class GenerationJobRow(Base):
    __tablename__ = "generation_jobs"

    job_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    trip_id: Mapped[str] = mapped_column(String(36), index=True)
    state: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    step: Mapped[str | None] = mapped_column(String(24), nullable=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    resolved_count: Mapped[int] = mapped_column(Integer, default=0)
    unresolved_count: Mapped[int] = mapped_column(Integer, default=0)
    problem_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), default=utcnow, onupdate=utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class ExternalCacheRow(Base):
    __tablename__ = "external_cache"

    cache_key: Mapped[str] = mapped_column(String(64), primary_key=True)
    namespace: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(UtcDateTime(), index=True)


class ApiUsageRow(Base):
    """BR-50 — 사용량 일자는 **KST 기준**이다."""

    __tablename__ = "api_usage"

    api_name: Mapped[str] = mapped_column(String(32), primary_key=True)
    usage_date: Mapped[date] = mapped_column(Date, primary_key=True)
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    daily_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AuditEventRow(Base):
    """SEC-14 / BR-59 — **추가 전용.**

    애플리케이션은 이 테이블에 대한 UPDATE·DELETE 연산을 제공하지 않는다.
    (보존 기간 경과분 정리만 예외이며, 이는 `purge_older_than` 한 곳에서만 수행된다.)
    """

    __tablename__ = "audit_events"

    event_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime(), default=utcnow, index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)
    correlation_id: Mapped[str] = mapped_column(String(64), default="-")
    subject_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="{}")


ALL_TABLES = (
    TripRow,
    TripDayRow,
    PlaceRow,
    OpeningHoursRow,
    ItineraryItemRow,
    TravelLegRow,
    UnresolvedCandidateRow,
    PlaceContentRow,
    GenerationJobRow,
    ExternalCacheRow,
    ApiUsageRow,
    AuditEventRow,
)
