"""C27 RecommendationService 테스트 — BR-40 ~ BR-44, DD-24."""

from __future__ import annotations

import uuid

from app.clients.protocols import BlogPost, ImageRef, LlmResponse
from app.core.errors import ExternalServiceError
from app.domain.models import Coordinate, Place, PlaceCategory, PlaceSource
from app.services.llm_draft import LlmDraftGenerator
from app.services.recommendation import RecommendationService

PLACE = Place(
    place_id=str(uuid.uuid4()),
    name="돼지국밥집",
    coordinate=Coordinate(35.1796, 129.0756),
    category=PlaceCategory.RESTAURANT,
    source=PlaceSource.MOCK,
)


class _StubContent:
    def __init__(self, blog_count: int, *, blogs_fail: bool = False, images_fail: bool = False) -> None:
        self.blog_count = blog_count
        self.blogs_fail = blogs_fail
        self.images_fail = images_fail

    async def search_blogs(self, query: str, *, limit: int = 10) -> list[BlogPost]:
        if self.blogs_fail:
            raise ExternalServiceError("blog down")
        return [
            BlogPost(title=f"후기{i}", link=f"https://example.invalid/{i}", description="맛있음")
            for i in range(self.blog_count)
        ]

    async def search_images(self, query: str, *, limit: int = 6) -> list[ImageRef]:
        if self.images_fail:
            raise ExternalServiceError("image down")
        return [ImageRef(thumbnail_url="t", link="l", source_title="s")]


class _StubLlm:
    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, *, system, user, max_tokens, tool_schema=None) -> LlmResponse:
        self.calls += 1
        return LlmResponse(text='{"highlights": ["돼지국밥", "수육", "밀면"]}')


def _service(content, llm=None) -> RecommendationService:
    return RecommendationService(content, LlmDraftGenerator(llm or _StubLlm()))


# ---------------------------------------------------------------------------
# BR-40 — 근거 3건 미만이면 요약 없음
# ---------------------------------------------------------------------------
async def test_summary_requires_three_sources() -> None:
    llm = _StubLlm()
    content = await _service(_StubContent(blog_count=2), llm).content_for(PLACE)

    assert content.highlights == []  # 🔴 근거 부족 → 요약 생성 안 함
    assert len(content.sources) == 2  # 확보한 링크는 그대로 노출
    assert llm.calls == 0  # LLM 을 부르지도 않는다 (비용 절약)


async def test_summary_generated_with_enough_sources() -> None:
    llm = _StubLlm()
    content = await _service(_StubContent(blog_count=5), llm).content_for(PLACE)

    assert len(content.highlights) == 3
    assert llm.calls == 1
    assert len(content.sources) == 5


async def test_highlights_never_exceed_five() -> None:
    """BR-43 — 3~5개로 제한."""
    content = await _service(_StubContent(blog_count=10)).content_for(PLACE)
    assert len(content.highlights) <= 5


async def test_summary_always_marked_as_ai() -> None:
    """BR-44 / CON-7 — AI 요약임을 명시한다."""
    content = await _service(_StubContent(blog_count=5)).content_for(PLACE)
    assert content.is_ai_summary is True


# ---------------------------------------------------------------------------
# BR-42 — 부분 실패 격리
# ---------------------------------------------------------------------------
async def test_blog_failure_yields_empty_sections_not_error() -> None:
    content = await _service(_StubContent(blog_count=5, blogs_fail=True)).content_for(PLACE)
    assert content.sources == []
    assert content.highlights == []  # 근거가 없으니 요약도 없다


async def test_image_failure_does_not_affect_summary() -> None:
    content = await _service(_StubContent(blog_count=5, images_fail=True)).content_for(PLACE)
    assert content.images == []
    assert len(content.highlights) == 3  # 요약은 정상


async def test_summary_failure_keeps_sources() -> None:
    class _FailingLlm:
        async def complete(self, *, system, user, max_tokens, tool_schema=None):
            raise ExternalServiceError("llm down")

    content = await _service(_StubContent(blog_count=5), _FailingLlm()).content_for(PLACE)
    assert content.highlights == []
    assert len(content.sources) == 5  # 근거 링크는 살아 있다


# ---------------------------------------------------------------------------
# 직렬화
# ---------------------------------------------------------------------------
async def test_to_dict_includes_sources_and_flag() -> None:
    content = await _service(_StubContent(blog_count=5)).content_for(PLACE)
    payload = content.to_dict()
    assert payload["is_ai_summary"] is True
    assert len(payload["sources"]) == 5
    assert "link" in payload["sources"][0]
