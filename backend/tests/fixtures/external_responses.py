"""외부 API 응답 샘플 (NFR-10 — 네트워크 비의존 테스트).

⚠️ 이 픽스처는 **문서 기반으로 작성한 예시**이며 실응답으로 검증되지 않았다.
   Build & Test 에서 실호출 결과와 대조해 갱신한다 (code-generation-plan §6-4).
"""

from __future__ import annotations

# 지역검색 — mapx/mapy 는 WGS84 x 1e7 정수 표현이라는 **가정** (to_wgs84 참조)
NAVER_LOCAL_OK = {
    "lastBuildDate": "Thu, 13 Aug 2026 07:30:00 +0900",
    "total": 2,
    "start": 1,
    "display": 2,
    "items": [
        {
            "title": "<b>광안리</b> 해수욕장",
            "link": "https://example.invalid/1",
            "category": "여행>관광,명소>해수욕장",
            "description": "",
            "telephone": "",
            "address": "부산광역시 수영구 광안2동",
            "roadAddress": "부산광역시 수영구 광안해변로 219",
            "mapx": "1291180000",
            "mapy": "351530000",
        },
        {
            "title": "돼지국밥 &amp; 수육",
            "link": "https://example.invalid/2",
            "category": "음식점>한식>국밥",
            "description": "",
            "telephone": "051-000-0000",
            "address": "부산광역시 동구 초량동",
            "roadAddress": "부산광역시 동구 중앙대로 000",
            "mapx": "1290350000",
            "mapy": "351150000",
        },
    ],
}

# 좌표계 가정이 틀린 경우를 흉내 낸 응답 (KATECH 계열 값)
NAVER_LOCAL_BAD_COORD = {
    "items": [
        {
            "title": "좌표 이상",
            "link": "",
            "category": "",
            "description": "",
            "telephone": "",
            "address": "",
            "roadAddress": "",
            "mapx": "311111",
            "mapy": "552222",
        }
    ]
}

NAVER_BLOG_OK = {
    "items": [
        {
            "title": "<b>광안리</b> 맛집 후기",
            "link": "https://example.invalid/blog/1",
            "description": "밀면과 돼지국밥이 좋았습니다",
            "bloggername": "여행자A",
            "postdate": "20260801",
        },
        {
            "title": "부산 2박3일",
            "link": "https://example.invalid/blog/2",
            "description": "해운대 &amp; 광안리 코스",
            "bloggername": "여행자B",
            "postdate": "20260802",
        },
    ]
}

NAVER_IMAGE_OK = {
    "items": [
        {
            "title": "광안대교 야경",
            "link": "https://example.invalid/img/1",
            "thumbnail": "https://example.invalid/img/1_th.jpg",
        }
    ]
}

# Directions 5 — duration 은 밀리초
NCP_DIRECTIONS_OK = {
    "code": 0,
    "route": {
        "traoptimal": [
            {
                "summary": {"distance": 12500, "duration": 1_500_000},
                "path": [[129.0756, 35.1796], [129.1180, 35.1530]],
            }
        ]
    },
}

NCP_DIRECTIONS_EMPTY = {"code": 0, "route": {}}

# Anthropic Messages API — 구조화 출력(tool_use) 응답
ANTHROPIC_TOOL_USE_OK = {
    "id": "msg_demo",
    "type": "message",
    "role": "assistant",
    "stop_reason": "tool_use",
    "usage": {"input_tokens": 100, "output_tokens": 200},
    "content": [
        {
            "type": "tool_use",
            "id": "toolu_demo",
            "name": "emit_result",
            "input": {
                "days": [
                    {
                        "day_index": 1,
                        "places": [
                            {
                                "raw_name": "광안리 해수욕장",
                                "category_hint": "관광명소",
                                "suggested_stay_minutes": 90,
                                "reason": "야경이 좋습니다",
                                "preferred_time_slot": "evening",
                            }
                        ],
                    }
                ]
            },
        }
    ],
}

# 구조화 출력을 강제했는데 텍스트만 온 경우 (SEC-13 — 수용하지 않아야 한다)
ANTHROPIC_TEXT_ONLY = {
    "id": "msg_demo2",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 20},
    "content": [{"type": "text", "text": "죄송하지만 도구를 쓰지 않았습니다."}],
}
