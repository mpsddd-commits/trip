"""C8 NaverContentSearchClient — 블로그·이미지 검색.

근거:
    FR-20   추천 콘텐츠의 **근거** 확보
    FR-21   썸네일 + 출처
    BR-41   블로그 **제목과 발췌만** 사용한다. 본문을 크롤링하지 않는다 (CON-8)
    BR-42   실패해도 해당 섹션만 비우고 나머지는 정상 반환 (NFR-3)
"""

from __future__ import annotations

import httpx

from app.clients.base import BaseHttpClient
from app.clients.naver_local import strip_tags
from app.clients.protocols import BlogPost, ImageRef
from app.core.enums import ApiName

BLOG_ENDPOINT = "https://openapi.naver.com/v1/search/blog.json"
IMAGE_ENDPOINT = "https://openapi.naver.com/v1/search/image"


class NaverContentSearchClient:
    def __init__(
        self, http: BaseHttpClient, client_id: str, client_secret: str, *, read_timeout: float = 10.0
    ) -> None:
        self._http = http
        self._headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        self._read_timeout = read_timeout

    async def search_blogs(self, query: str, *, limit: int = 10) -> list[BlogPost]:
        response: httpx.Response = await self._http.request(
            ApiName.NAVER_BLOG,
            "GET",
            BLOG_ENDPOINT,
            headers=self._headers,
            params={"query": query, "display": min(limit, 30), "sort": "sim"},
            timeout=self._read_timeout,
        )
        return [
            BlogPost(
                title=strip_tags(item.get("title", "")),
                link=item.get("link", ""),
                blogger_name=item.get("bloggername") or None,
                post_date=item.get("postdate") or None,
                # BR-41 — API 가 주는 발췌만 사용한다. 본문을 가져오지 않는다.
                description=strip_tags(item.get("description", "")),
            )
            for item in response.json().get("items", [])
        ]

    async def search_images(self, query: str, *, limit: int = 6) -> list[ImageRef]:
        response: httpx.Response = await self._http.request(
            ApiName.NAVER_IMAGE,
            "GET",
            IMAGE_ENDPOINT,
            headers=self._headers,
            params={"query": query, "display": min(limit, 30), "sort": "sim"},
            timeout=self._read_timeout,
        )
        return [
            ImageRef(
                thumbnail_url=item.get("thumbnail", ""),
                link=item.get("link", ""),
                # FR-21 / CON-8 — 출처를 반드시 함께 보관한다.
                source_title=strip_tags(item.get("title", "")),
            )
            for item in response.json().get("items", [])
        ]
