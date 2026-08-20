"""C27 RecommendationService — 장소별 추천 콘텐츠 조립.

근거:
    FR-20   음식점=대표 메뉴 / 그 외=관람 포인트, **근거 링크 필수**
    FR-21   이미지 + 출처
    BR-40   🔴 **블로그 근거가 3건 미만이면 요약을 생성하지 않는다** (DD-24, CON-7)
    BR-41   제목·발췌만 사용. 본문 크롤링 금지 (CON-8)
    BR-42   블로그·이미지·요약 중 무엇이 실패해도 나머지는 정상 반환 (NFR-3)
    BR-43   highlights 는 3~5개
    BR-44   `is_ai_summary=True` + 근거·출처 동반
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.clients.circuit import CircuitOpenError
from app.clients.protocols import BlogPost, ContentSearchClient, ImageRef
from app.core.errors import ExternalServiceError
from app.core.logging_config import get_logger
from app.domain.models import Place
from app.services.llm_draft import LlmDraftGenerator

logger = get_logger(__name__)

MIN_SOURCES_FOR_SUMMARY = 3  # BR-40


@dataclass(frozen=True, slots=True)
class PlaceContent:
    place_id: str
    highlights: list[str] = field(default_factory=list)
    sources: list[BlogPost] = field(default_factory=list)
    images: list[ImageRef] = field(default_factory=list)
    is_ai_summary: bool = True

    def to_dict(self) -> dict:
        return {
            "place_id": self.place_id,
            "highlights": self.highlights,
            "sources": [
                {
                    "title": b.title,
                    "link": b.link,
                    "blogger_name": b.blogger_name,
                    "post_date": b.post_date,
                }
                for b in self.sources
            ],
            "images": [
                {"thumbnail_url": i.thumbnail_url, "link": i.link, "source_title": i.source_title}
                for i in self.images
            ],
            "is_ai_summary": self.is_ai_summary,
        }


class RecommendationService:
    def __init__(
        self,
        content_search: ContentSearchClient,
        draft_generator: LlmDraftGenerator,
        *,
        min_sources: int = MIN_SOURCES_FOR_SUMMARY,
    ) -> None:
        self._content = content_search
        self._llm = draft_generator
        self._min_sources = min_sources

    async def content_for(self, place: Place, *, region: str = "") -> PlaceContent:
        query = f"{region} {place.name}".strip()

        blogs = await self._safe(self._content.search_blogs(query, limit=10), "블로그 검색", [])
        images = await self._safe(self._content.search_images(query, limit=6), "이미지 검색", [])

        highlights: list[str] = []
        if len(blogs) >= self._min_sources:
            # BR-40 — 근거가 충분할 때만 요약한다.
            highlights = await self._safe(
                self._llm.summarize_place(place, blogs), "요약 생성", []
            )
        else:
            logger.info(
                "근거 부족으로 요약을 생성하지 않습니다",
                extra={"place": place.name, "sources": len(blogs)},
            )

        # 불변식 (BR-40): 근거가 부족하면 highlights 는 반드시 비어 있다.
        if len(blogs) < self._min_sources:
            highlights = []

        return PlaceContent(
            place_id=place.place_id,
            highlights=highlights[:5],  # BR-43
            sources=blogs,
            images=images,
            is_ai_summary=True,  # BR-44
        )

    async def content_for_many(
        self, places: list[Place], *, region: str = ""
    ) -> dict[str, PlaceContent]:
        results: dict[str, PlaceContent] = {}
        for place in places:
            results[place.place_id] = await self.content_for(place, region=region)
        return results

    @staticmethod
    async def _safe(awaitable, label: str, fallback):  # type: ignore[no-untyped-def]
        """BR-42 — 부분 실패를 해당 섹션에만 가둔다."""
        try:
            return await awaitable
        except (ExternalServiceError, CircuitOpenError, ValueError, KeyError) as exc:
            logger.warning(f"{label} 실패", extra={"detail": str(exc)})
            return fallback
