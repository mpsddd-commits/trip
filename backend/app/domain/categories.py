"""장소 카테고리 정규화 (순수 함수).

근거:
    domain-entities.md §4.2  카테고리 ↔ 기본 체류시간 매핑
    BR-52   기본 체류시간은 카테고리에서 나온다
    BR-11 ③ 그라운딩의 카테고리 대분류 일치 판정에 사용

배치 주석: `models.py` 가 커져 분리했다. domain 내부 모듈이므로 DD-16 유지.
"""

from __future__ import annotations

from app.domain.models import DEFAULT_STAY_MINUTES, PlaceCategory

# 판정 순서가 중요하다. 더 구체적인 키워드를 앞에 둔다.
_KEYWORD_TABLE: tuple[tuple[PlaceCategory, tuple[str, ...]], ...] = (
    (PlaceCategory.CAFE, ("카페", "디저트", "베이커리", "제과", "커피", "브런치")),
    (PlaceCategory.MUSEUM, ("박물관", "미술관", "전시", "기념관", "과학관", "갤러리")),
    (
        PlaceCategory.ACCOMMODATION,
        ("숙박", "호텔", "펜션", "게스트하우스", "모텔", "리조트", "민박"),
    ),
    (PlaceCategory.SHOPPING, ("쇼핑", "시장", "백화점", "아울렛", "마트", "상가", "면세")),
    (
        PlaceCategory.RESTAURANT,
        ("음식점", "한식", "중식", "일식", "양식", "분식", "food", "맛집", "횟집", "고깃집"),
    ),
    (
        PlaceCategory.ATTRACTION,
        ("관광", "명소", "공원", "해수욕장", "해변", "전망", "산", "사찰", "궁", "테마파크", "체험"),
    ),
)


def classify_category(raw: str | None) -> PlaceCategory:
    """지역검색 분류 문자열 또는 LLM 카테고리 힌트를 정규 카테고리로 변환한다.

    판별할 수 없으면 `OTHER` 를 반환한다 — 추측하지 않는다.
    """
    if not raw:
        return PlaceCategory.OTHER
    text = raw.casefold()
    for category, keywords in _KEYWORD_TABLE:
        if any(keyword.casefold() in text for keyword in keywords):
            return category
    return PlaceCategory.OTHER


def default_stay_minutes(category: PlaceCategory) -> int:
    """BR-52 — 카테고리별 기본 체류시간."""
    return DEFAULT_STAY_MINUTES[category]
