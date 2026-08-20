"""횡단 열거형 정의.

컴포넌트: C1 Config / C4 RateLimiter / C5 ErrorHandler / C29 QuotaService 공용
근거: domain-entities.md §4.5, §4.6 / business-rules.md BR-49, BR-58

배치 주석: 설계상 별도 컴포넌트는 아니지만, core·clients·services·storage 가
공통으로 참조하는 열거형을 한 곳에 모아 순환 import 를 방지한다.
"""

from __future__ import annotations

from enum import StrEnum


class ApiName(StrEnum):
    """외부 API 식별자 (쿼터 계측·서킷 브레이커·세마포어의 키)."""

    NAVER_LOCAL = "NAVER_LOCAL"
    NAVER_BLOG = "NAVER_BLOG"
    NAVER_IMAGE = "NAVER_IMAGE"
    NCP_DIRECTIONS = "NCP_DIRECTIONS"
    NCP_GEOCODING = "NCP_GEOCODING"
    ANTHROPIC = "ANTHROPIC"


class EndpointTier(StrEnum):
    """레이트 리밋 등급 (BR-49).

    EXPENSIVE : AI 생성 — IP당 5회/시간 + 전역 50회/일
    EXTERNAL  : 검색·추천·경로 — IP당 60회/분
    CHEAP     : 조회·편집·정적 — IP당 300회/분
    """

    EXPENSIVE = "EXPENSIVE"
    EXTERNAL = "EXTERNAL"
    CHEAP = "CHEAP"


class ErrorCode(StrEnum):
    """오류 분류 6종 (BR-58, Q15=A).

    이 6종 외의 코드를 추가하지 않는다. 사용자 노출 문구는 USER_MESSAGES 에
    고정되어 있으며, 예외 원문·스택트레이스·내부 경로는 절대 노출하지 않는다.
    """

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AuditEventType(StrEnum):
    """감사 이벤트 종류 (SEC-13, SEC-14, BR-51)."""

    TRIP_CREATED = "TRIP_CREATED"
    TRIP_UPDATED = "TRIP_UPDATED"
    TRIP_DELETED = "TRIP_DELETED"
    SHARE_TOKEN_ISSUED = "SHARE_TOKEN_ISSUED"
    SHARE_TOKEN_REVOKED = "SHARE_TOKEN_REVOKED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    QUOTA_EXHAUSTED = "QUOTA_EXHAUSTED"
    EXTERNAL_AUTH_FAILED = "EXTERNAL_AUTH_FAILED"
    LLM_SCHEMA_REJECTED = "LLM_SCHEMA_REJECTED"
    CIRCUIT_OPENED = "CIRCUIT_OPENED"
    CIRCUIT_CLOSED = "CIRCUIT_CLOSED"
