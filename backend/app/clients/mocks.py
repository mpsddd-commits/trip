"""목(mock) 구현 — 인증 정보가 없어도 전 화면이 동작하게 한다.

근거:
    FR-33 / DD-3
        인증 정보 유무에 따른 분기는 **C13 주입 시점에만** 존재한다.
        서비스·도메인 코드에는 `if mock:` 이 하나도 없다.
    DD-6  목 구현은 **캐시 데코레이터로 감싸지 않는다** — 이미 결정적이다.
    NFR-10 테스트가 네트워크에 의존하지 않게 하는 수단이기도 하다.

목 데이터는 **결정적**이다. 같은 질의에 항상 같은 결과를 준다.
"""

from __future__ import annotations

import hashlib
import json

from app.clients.protocols import BlogPost, CarRoute, ImageRef, LlmResponse, SearchedPlace
from app.domain.estimator import estimate_car_fallback
from app.domain.models import Coordinate

# 지역별 대표 좌표 — 목 결과를 목적지 근처에 두기 위한 기준점
_REGION_ANCHORS: dict[str, Coordinate] = {
    "서울": Coordinate(37.5665, 126.9780),
    "부산": Coordinate(35.1796, 129.0756),
    "제주": Coordinate(33.4996, 126.5312),
    "강릉": Coordinate(37.7519, 128.8761),
    "전주": Coordinate(35.8242, 127.1480),
    "경주": Coordinate(35.8562, 129.2247),
}
_DEFAULT_ANCHOR = _REGION_ANCHORS["서울"]

_MOCK_CATEGORIES = [
    "음식점>한식",
    "카페,디저트",
    "여행>관광,명소",
    "문화,예술>박물관",
    "쇼핑>시장",
]


def _stable_offset(seed: str, scale: float = 0.02) -> tuple[float, float]:
    """질의에서 결정적인 미세 좌표 오프셋을 만든다."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    lat_off = (digest[0] / 255.0 - 0.5) * scale
    lng_off = (digest[1] / 255.0 - 0.5) * scale
    return lat_off, lng_off


def _anchor_for(query: str) -> Coordinate:
    for region, coordinate in _REGION_ANCHORS.items():
        if region in query:
            return coordinate
    return _DEFAULT_ANCHOR


class MockLocalSearchClient:
    """C7 목 구현.

    질의에 포함된 장소명을 그대로 결과 이름에 담아 **그라운딩(C23)이 성공**하도록
    한다. 목 모드에서도 파이프라인 전체가 동작해야 하기 때문이다 (FR-33, QG-7).
    """

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        anchor = _anchor_for(query)
        # 질의는 "{목적지} {장소명}" 형태다 (BR-10). 뒤쪽을 장소명으로 본다.
        parts = query.split()
        base_name = " ".join(parts[1:]) if len(parts) > 1 else query
        results: list[SearchedPlace] = []
        for index in range(min(display, 5)):
            seed = f"{query}#{start}#{index}"
            lat_off, lng_off = _stable_offset(seed)
            name = base_name if index == 0 else f"{base_name} {index + 1}호점"
            results.append(
                SearchedPlace(
                    name=name,
                    coordinate=Coordinate(
                        lat=round(anchor.lat + lat_off, 6),
                        lng=round(anchor.lng + lng_off, 6),
                    ),
                    category_raw=_MOCK_CATEGORIES[index % len(_MOCK_CATEGORIES)],
                    road_address=f"{parts[0] if parts else '서울'} 데모로 {index + 1}길 {index + 10}",
                    address=f"{parts[0] if parts else '서울'} 데모동 {index + 1}-{index + 10}",
                    phone=None,
                    link="https://example.invalid/demo",
                )
            )
        return results


class MockContentSearchClient:
    async def search_blogs(self, query: str, *, limit: int = 10) -> list[BlogPost]:
        count = min(limit, 5)
        return [
            BlogPost(
                title=f"[데모] {query} 방문기 {i + 1}",
                link=f"https://example.invalid/blog/{i + 1}",
                blogger_name=f"데모블로거{i + 1}",
                post_date="20260801",
                description=f"{query} 에 다녀온 데모 후기입니다. 실제 데이터가 아닙니다.",
            )
            for i in range(count)
        ]

    async def search_images(self, query: str, *, limit: int = 6) -> list[ImageRef]:
        return [
            ImageRef(
                thumbnail_url=f"https://example.invalid/img/{i + 1}.jpg",
                link=f"https://example.invalid/img/{i + 1}",
                source_title=f"[데모] {query} 사진 {i + 1}",
            )
            for i in range(min(limit, 3))
        ]


class MockDirectionsClient:
    """C9 목 구현 — 하버사인 근사로 자동차 경로를 흉내 낸다."""

    async def route_car(self, origin: Coordinate, destination: Coordinate) -> CarRoute:
        leg = estimate_car_fallback(origin, destination, 0, 1)
        return CarRoute(
            duration_sec=leg.duration_sec,
            distance_m=leg.distance_m,
            path=(origin, destination),
        )


class MockGeocodingClient:
    async def geocode(self, address: str) -> Coordinate | None:
        anchor = _anchor_for(address)
        lat_off, lng_off = _stable_offset(address)
        return Coordinate(lat=round(anchor.lat + lat_off, 6), lng=round(anchor.lng + lng_off, 6))

    async def reverse_geocode(self, coordinate: Coordinate) -> str | None:
        return "데모 주소 (실제 데이터 아님)"


class MockLlmClient:
    """C11 목 구현 — 구조화 출력 스키마에 맞는 결정적 초안을 만든다.

    C22 의 스키마 검증(BR-07)을 통과해야 하므로 형식을 정확히 지킨다.
    """

    _TEMPLATES = [
        ("맛집", "음식점", 60, "lunch"),
        ("카페", "카페", 40, "afternoon"),
        ("전망대", "관광명소", 90, "evening"),
        ("박물관", "박물관", 120, "morning"),
        ("시장", "쇼핑", 90, "afternoon"),
    ]

    async def complete(
        self, *, system: str, user: str, max_tokens: int, tool_schema: dict | None = None
    ) -> LlmResponse:
        destination, day_count = self._read_hints(user)
        days = []
        for day_index in range(day_count):
            items = []
            for slot in range(3):
                suffix, hint, stay, when = self._TEMPLATES[
                    (day_index * 3 + slot) % len(self._TEMPLATES)
                ]
                items.append(
                    {
                        "raw_name": f"{destination} 데모{suffix}{day_index + 1}{slot + 1}",
                        "category_hint": hint,
                        "suggested_stay_minutes": stay,
                        "reason": "데모 모드에서 생성된 예시 일정입니다. 실제 추천이 아닙니다.",
                        "preferred_time_slot": when,
                    }
                )
            days.append({"day_index": day_index + 1, "places": items})
        return LlmResponse(
            text=json.dumps({"days": days}, ensure_ascii=False),
            input_tokens=0,
            output_tokens=0,
            stop_reason="tool_use" if tool_schema else "end_turn",
        )

    @staticmethod
    def _read_hints(user: str) -> tuple[str, int]:
        destination = next((r for r in _REGION_ANCHORS if r in user), "서울")
        day_count = 2
        for token in user.replace("일차", " ").split():
            if token.isdigit() and 1 <= int(token) <= 10:
                day_count = int(token)
                break
        return destination, day_count
