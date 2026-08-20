"""C12 CachingClientDecorator 동작 테스트 — DD-15, NFR-4."""

from __future__ import annotations

from app.clients.cache_decorator import CacheStore, CachedLocalSearchClient
from app.clients.protocols import SearchedPlace
from app.domain.models import Coordinate


class _MemoryStore(CacheStore):
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.puts = 0

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def put(self, key: str, namespace: str, payload: str, ttl_days: int) -> None:
        self.data[key] = payload
        self.puts += 1


class _CountingLocalSearch:
    def __init__(self) -> None:
        self.calls = 0

    async def search(self, query: str, *, start: int = 1, display: int = 5) -> list[SearchedPlace]:
        self.calls += 1
        return [
            SearchedPlace(
                name=f"{query} 결과",
                coordinate=Coordinate(35.1796, 129.0756),
                category_raw="음식점>한식",
                road_address="부산 중앙대로 1",
            )
        ]


async def test_second_call_is_served_from_cache() -> None:
    inner = _CountingLocalSearch()
    store = _MemoryStore()
    cached = CachedLocalSearchClient(inner, store, ttl_days=7)

    first = await cached.search("부산 돼지국밥")
    second = await cached.search("부산 돼지국밥")

    assert inner.calls == 1  # 외부 호출은 한 번뿐
    assert first == second
    assert store.puts == 1


async def test_cached_value_roundtrips_exactly() -> None:
    """캐시를 거친 값이 원본과 동일해야 한다 (직렬화 왕복)."""
    inner = _CountingLocalSearch()
    store = _MemoryStore()
    cached = CachedLocalSearchClient(inner, store, ttl_days=7)

    original = await cached.search("서울 경복궁")
    restored = await cached.search("서울 경복궁")

    assert restored[0].name == original[0].name
    assert restored[0].coordinate == original[0].coordinate
    assert restored[0].road_address == original[0].road_address


async def test_whitespace_variants_hit_the_same_entry() -> None:
    """BR-48 — 표기 차이로 쿼터를 낭비하지 않는다."""
    inner = _CountingLocalSearch()
    cached = CachedLocalSearchClient(inner, _MemoryStore(), ttl_days=7)

    await cached.search("부산  돼지국밥")
    await cached.search("부산 돼지국밥 ")

    assert inner.calls == 1


async def test_different_paging_uses_different_entries() -> None:
    """페이징 파라미터는 키에 포함된다 (BR-48)."""
    inner = _CountingLocalSearch()
    cached = CachedLocalSearchClient(inner, _MemoryStore(), ttl_days=7)

    await cached.search("부산 맛집", start=1)
    await cached.search("부산 맛집", start=6)

    assert inner.calls == 2
