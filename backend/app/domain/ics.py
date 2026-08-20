"""C20 IcsBuilder — 일정을 iCalendar(.ics) 로 직렬화하고 되읽는다.

근거:
    FR-26   일정 내보내기
    BR-45   쉼표·세미콜론·역슬래시·개행 이스케이프, 75옥텟 줄 접기, TZID=Asia/Seoul
    BR-46   보존 항목과 손실 항목을 명시한다
    P-19    parse(build(x)) 의 **보존 항목**이 원본과 일치
    P-20    특수문자를 포함한 메모도 왕복 보존

보존 항목: item_id / 도착·출발 시각(초 단위) / 장소명 / 주소 / 메모 / 좌표 / 체류시간
손실 항목: travel_mode / warnings / category / phone
          → VEVENT 표준 필드가 없다. X- 속성으로 내보내되 되읽지 않는다 (BR-46).
⚠️ 초 미만(마이크로초) 정밀도는 iCalendar 형식에 없어 손실된다.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.domain.models import Coordinate, ItineraryItem

KST = ZoneInfo("Asia/Seoul")
TZID = "Asia/Seoul"
PRODID = "-//trip//AI-DLC//KO"
_MAX_OCTETS = 75


# ---------------------------------------------------------------------------
# 텍스트 이스케이프 (BR-45)
# ---------------------------------------------------------------------------
def escape_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def unescape_text(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            out.append({"n": "\n", "N": "\n", ";": ";", ",": ",", "\\": "\\"}.get(nxt, nxt))
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _fold(line: str) -> list[str]:
    """75옥텟 기준 줄 접기 (BR-45). 멀티바이트 문자를 쪼개지 않는다."""
    encoded = line.encode("utf-8")
    if len(encoded) <= _MAX_OCTETS:
        return [line]

    folded: list[str] = []
    current = ""
    limit = _MAX_OCTETS
    for ch in line:
        candidate = current + ch
        if len(candidate.encode("utf-8")) > limit:
            folded.append(current)
            current = ch
            limit = _MAX_OCTETS - 1  # 이어지는 줄은 선행 공백 1옥텟을 차지한다
        else:
            current = candidate
    if current:
        folded.append(current)
    return [folded[0]] + [" " + part for part in folded[1:]]


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return [line for line in lines if line]


def _fmt_dt(value: datetime) -> str:
    return value.astimezone(KST).strftime("%Y%m%dT%H%M%S")


def _parse_dt(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=KST).astimezone(UTC)


# ---------------------------------------------------------------------------
# 생성
# ---------------------------------------------------------------------------
def build(title: str, items: list[ItineraryItem], *, now: datetime | None = None) -> str:
    stamp = (now or datetime.now(tz=UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{escape_text(title)}",
        # 대한민국은 서머타임이 없어 고정 오프셋으로 충분하다.
        "BEGIN:VTIMEZONE",
        f"TZID:{TZID}",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:+0900",
        "TZOFFSETTO:+0900",
        "TZNAME:KST",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

    for item in items:
        if item.arrival_at is None or item.departure_at is None:
            continue
        place = item.place
        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{item.item_id}@trip.local")
        lines.append(f"DTSTAMP:{stamp}")
        lines.append(f"DTSTART;TZID={TZID}:{_fmt_dt(item.arrival_at)}")
        lines.append(f"DTEND;TZID={TZID}:{_fmt_dt(item.departure_at)}")
        lines.append(f"SUMMARY:{escape_text(place.name)}")
        location = place.road_address or place.address or ""
        lines.append(f"LOCATION:{escape_text(location)}")
        lines.append(f"DESCRIPTION:{escape_text(item.memo or '')}")
        lines.append(f"GEO:{place.coordinate.lat};{place.coordinate.lng}")
        # 아래는 손실 항목 (BR-46) — 내보내되 되읽지 않는다.
        if item.travel_mode is not None:
            lines.append(f"X-TRIP-TRAVEL-MODE:{item.travel_mode.value}")
        if item.warnings:
            joined = ",".join(w.type.value for w in item.warnings)
            lines.append(f"X-TRIP-WARNINGS:{joined}")
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    folded: list[str] = []
    for line in lines:
        folded.extend(_fold(line))
    return "\r\n".join(folded) + "\r\n"


# ---------------------------------------------------------------------------
# 파싱 (왕복 검증용)
# ---------------------------------------------------------------------------
_PROP = re.compile(r"^(?P<name>[A-Za-z0-9\-]+)(?P<params>;[^:]*)?:(?P<value>.*)$")


def parse(ics_text: str) -> list[dict[str, Any]]:
    """VEVENT 의 **보존 항목**만 되읽는다 (BR-46).

    반환 형식: {"item_id", "arrival_at", "departure_at", "name", "location",
               "memo", "coordinate", "stay_minutes"}
    """
    events: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in _unfold(ics_text):
        if line == "BEGIN:VEVENT":
            current = {}
            continue
        if line == "END:VEVENT":
            if current is not None:
                arrival = current.get("arrival_at")
                departure = current.get("departure_at")
                if arrival and departure:
                    current["stay_minutes"] = int((departure - arrival).total_seconds() // 60)
                events.append(current)
            current = None
            continue
        if current is None:
            continue

        match = _PROP.match(line)
        if match is None:
            continue
        name = match.group("name").upper()
        value = match.group("value")

        if name == "UID":
            current["item_id"] = value.removesuffix("@trip.local")
        elif name == "DTSTART":
            current["arrival_at"] = _parse_dt(value)
        elif name == "DTEND":
            current["departure_at"] = _parse_dt(value)
        elif name == "SUMMARY":
            current["name"] = unescape_text(value)
        elif name == "LOCATION":
            current["location"] = unescape_text(value)
        elif name == "DESCRIPTION":
            current["memo"] = unescape_text(value)
        elif name == "GEO":
            lat_s, _, lng_s = value.partition(";")
            current["coordinate"] = Coordinate(lat=float(lat_s), lng=float(lng_s))
        # X-TRIP-* 는 의도적으로 무시한다 (BR-46 손실 항목)

    return events
