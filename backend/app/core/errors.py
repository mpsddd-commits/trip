"""C5 ErrorHandler — 도메인 예외 6종 + RFC 9457 Problem Details.

근거:
    BR-58   사용자 노출 문구는 6종 고정. 스택트레이스·내부 경로·예외 원문 미노출
    SEC-09  프로덕션 오류 응답에 내부 정보 노출 금지
    SEC-15  전역 예외 핸들러 + fail-closed
    Q6=A    RFC 9457 Problem Details 형식
"""

from __future__ import annotations

from typing import Any

from app.core.enums import ErrorCode

# BR-58 — 이 표에 없는 문구를 사용자에게 노출하지 않는다.
USER_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "입력값을 확인해 주세요.",
    ErrorCode.NOT_FOUND: "요청하신 정보를 찾을 수 없습니다.",
    ErrorCode.RATE_LIMITED: "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
    ErrorCode.QUOTA_EXHAUSTED: "오늘 사용 가능한 외부 서비스 호출량을 모두 사용했습니다.",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "외부 서비스에 일시적인 문제가 있습니다.",
    ErrorCode.INTERNAL_ERROR: "일시적인 오류가 발생했습니다.",
}

HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.QUOTA_EXHAUSTED: 429,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    ErrorCode.INTERNAL_ERROR: 500,
}

_TITLES: dict[ErrorCode, str] = {
    ErrorCode.VALIDATION_ERROR: "Validation Error",
    ErrorCode.NOT_FOUND: "Not Found",
    ErrorCode.RATE_LIMITED: "Rate Limited",
    ErrorCode.QUOTA_EXHAUSTED: "Quota Exhausted",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "External Service Error",
    ErrorCode.INTERNAL_ERROR: "Internal Error",
}


class DomainError(Exception):
    """모든 도메인 예외의 기반.

    `internal_detail` 은 로그 전용이며 사용자 응답에 포함되지 않는다 (SEC-09).
    """

    code: ErrorCode = ErrorCode.INTERNAL_ERROR

    def __init__(self, internal_detail: str = "", **context: Any) -> None:
        super().__init__(internal_detail or self.code.value)
        self.internal_detail = internal_detail
        self.context = context


class ValidationError(DomainError):
    code = ErrorCode.VALIDATION_ERROR


class NotFoundError(DomainError):
    code = ErrorCode.NOT_FOUND


class RateLimitError(DomainError):
    code = ErrorCode.RATE_LIMITED


class QuotaExhaustedError(DomainError):
    code = ErrorCode.QUOTA_EXHAUSTED


class ExternalServiceError(DomainError):
    code = ErrorCode.EXTERNAL_SERVICE_ERROR


class InternalError(DomainError):
    code = ErrorCode.INTERNAL_ERROR


def problem_details(
    code: ErrorCode,
    *,
    instance: str,
    correlation_id: str,
) -> tuple[int, dict[str, Any]]:
    """RFC 9457 Problem Details 본문을 만든다.

    `detail` 에는 **고정 문구만** 넣는다. 예외 메시지를 넣지 않는다 (BR-58).
    """
    status = HTTP_STATUS[code]
    body = {
        "type": f"about:blank#{code.value.lower()}",
        "title": _TITLES[code],
        "status": status,
        "detail": USER_MESSAGES[code],
        "instance": instance,
        "code": code.value,
        "correlation_id": correlation_id,
    }
    return status, body
