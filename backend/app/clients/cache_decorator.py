"""C12 CachingClientDecorator — 외부 응답 TTL 캐시.

근거:
    DD-15 / Q11=A  동일 인터페이스를 감싸는 데코레이터. **서비스는 캐시를 모른다**
    DD-6           **실제 구현체에만 적용한다.** 목 구현은 이미 결정적이므로 감싸지 않는다
    BR-48          키 정규화 — NFC -> 소문자 -> 공백 축약, 좌표 5자리 반올림, SHA-256
    NFR-4          TTL: 지역검색 7일 / Directions 1일 / 블로그·이미지 3일 / 지오코딩 30일
    P-21, P-22     정규화 속성

⚠️ LLM 응답은 캐시하지 않는다 — 동일 입력에도 다른 출력이 유효하다.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import asdict
from typing import Any

from app.clients.protocols import (
    BlogPost,
    CarRoute,
    ContentSearchClient,
    DirectionsClient,
    GeocodingClient,
    ImageRef,
    LocalSearchClient,
    SearchedPlace,
)
from app.core.access_log import record_cache_hit
from app.domain.models import Coordinate

_WHITESPACE = re.compile(r"\s+")
COORD_PRECISION = 5  # BR-48 — 약 1m


def normalize_text(value: str) -> str:
    """BR-48 — 표기 차이로 캐시가 갈라져 쿼터를 낭비하지 않게 한다."""
    normalized = unicodedata.normalize("NFC", value)
    normalized = _WHITESPACE.sub(" ", normalized).strip()
    return normalized.casefold()


def normalize_coordinate(coordinate: Coordinate) -> tuple[float, float]:
    return (round(coordinate.lat, COORD_PRECISION), round(coordinate.lng, COORD_PRECISION))


def _normalize_param(value: Any) -> Any:
    if isinstance(value, str):
        return normalize_text(value)
    if isinstance(value, Coordinate):
        return normalize_coordinate(value)
    if isinstance(value, (list, tuple)):
        return [_normalize_param(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_param(v) for k, v in sorted(value.items())}
    return value


def cache_key(namespace: str, method: str, params: dict[str, Any]) -> str:
    """BR-48 — 정규화된 파라미터의 SHA-256."""
    payload = json.dumps(
        {"ns": namespace, "m": method, "p": _normalize_param(params)},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class CacheStore:
    """C31 CacheRepository 주입 지점 (DD-7 — clients 가 storage 구체 타입에 의존하지 않는다)."""

    async def get(self, key: str) -> str | None:  # pragma: no cover - 기본 구현
        return None

    async def put(self, key: str, namespace: str, payload: str, ttl_days: int) -> None:  # pragma: no cover
        return None


class _CacheCore:
    def __init__(self, store: CacheStore, namespace: str, ttl_days: int) -> None:
        self.store = store
        self.namespace = namespace
        self.ttl_days = ttl_days

    async def get_or_call(
        self,
        method: str,
        params: dict[str, Any],
        factory: Callable[[], Awaitable[Any]],
        *,
        encode: Callable[[Any], Any],
        decode: Callable[[Any], Any],
    ) -> Any:
        key = cache_key(self.namespace, method, params)
        cached = await self.store.get(key)
        if cached is not None:
            record_cache_hit()
            return decode(json.loads(cached))
        value = await factory()
        await self.store.put(
            key, self.namespace, json.dumps(encode(value), ensure_ascii=False, default=str),
            self.ttl_days,
        )
        return value


def _coord_to_dict(coordinate: Coordinate) -> dict[str, float]:
    return {"lat": coordinate.lat, "lng": coordinate.lng}


# ---------------------------------------------------------------------------
class CachedLocalSearchClient:
    """C7 을 감싸는 캐시 데코레이터. 인터페이스가 동일하다."""

    def __init__(self, inner: LocalSearchClient, store: CacheStore, ttl_days: int = 7) -> None:
        self._inner = inner
        self._cache = _CacheCore(store, "local_search", ttl_days)

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        return await self._cache.get_or_call(
            "search",
            {"query": query, "start": start, "display": display},
            lambda: self._inner.search(query, start=start, display=display),
            encode=lambda places: [
                {**asdict(p), "coordinate": _coord_to_dict(p.coordinate)} for p in places
            ],
            decode=lambda raw: [
                SearchedPlace(**{**d, "coordinate": Coordinate(**d["coordinate"])}) for d in raw
            ],
        )


class CachedContentSearchClient:
    def __init__(self, inner: ContentSearchClient, store: CacheStore, ttl_days: int = 3) -> None:
        self._inner = inner
        self._cache = _CacheCore(store, "blog", ttl_days)
        self._image_cache = _CacheCore(store, "image", ttl_days)

    async def search_blogs(self, query: str, *, limit: int = 10) -> list[BlogPost]:
        return await self._cache.get_or_call(
            "search_blogs",
            {"query": query, "limit": limit},
            lambda: self._inner.search_blogs(query, limit=limit),
            encode=lambda posts: [asdict(p) for p in posts],
            decode=lambda raw: [BlogPost(**d) for d in raw],
        )

    async def search_images(self, query: str, *, limit: int = 6) -> list[ImageRef]:
        return await self._image_cache.get_or_call(
            "search_images",
            {"query": query, "limit": limit},
            lambda: self._inner.search_images(query, limit=limit),
            encode=lambda images: [asdict(i) for i in images],
            decode=lambda raw: [ImageRef(**d) for d in raw],
        )


class CachedDirectionsClient:
    def __init__(self, inner: DirectionsClient, store: CacheStore, ttl_days: int = 1) -> None:
        self._inner = inner
        self._cache = _CacheCore(store, "directions", ttl_days)

    async def route_car(self, origin: Coordinate, destination: Coordinate) -> CarRoute:
        return await self._cache.get_or_call(
            "route_car",
            {"origin": origin, "destination": destination},
            lambda: self._inner.route_car(origin, destination),
            encode=lambda route: {
                "duration_sec": route.duration_sec,
                "distance_m": route.distance_m,
                "path": [_coord_to_dict(c) for c in route.path],
            },
            decode=lambda raw: CarRoute(
                duration_sec=raw["duration_sec"],
                distance_m=raw["distance_m"],
                path=tuple(Coordinate(**c) for c in raw.get("path", [])),
            ),
        )


class CachedGeocodingClient:
    def __init__(self, inner: GeocodingClient, store: CacheStore, ttl_days: int = 30) -> None:
        self._inner = inner
        self._cache = _CacheCore(store, "geocode", ttl_days)

    async def geocode(self, address: str) -> Coordinate | None:
        return await self._cache.get_or_call(
            "geocode",
            {"address": address},
            lambda: self._inner.geocode(address),
            encode=lambda c: _coord_to_dict(c) if c else None,
            decode=lambda raw: Coordinate(**raw) if raw else None,
        )

    async def reverse_geocode(self, coordinate: Coordinate) -> str | None:
        return await self._cache.get_or_call(
            "reverse_geocode",
            {"coordinate": coordinate},
            lambda: self._inner.reverse_geocode(coordinate),
            encode=lambda s: s,
            decode=lambda raw: raw,
        )
