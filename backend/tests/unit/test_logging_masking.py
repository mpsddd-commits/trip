"""C2 로깅 마스킹 회귀 테스트 (SEC-03).

🔴 이 파일이 지키는 것: **로그 호출이 애플리케이션을 죽이지 않는다.**

Build and Test 에서 u1 테스트 다수가 하나의 원인으로 실패했다.
`SensitiveFilter` 가 모든 로그 인자를 `str()` 로 바꾸는 바람에
`%d` 를 쓰는 로그(httpx 가 요청마다 남긴다)가 TypeError 를 냈고,
`Filter` 는 `Handler.emit()` 의 try/except **밖**에서 실행되므로
그 예외가 로그를 호출한 코드까지 그대로 튀어나갔다.
"""

from __future__ import annotations

import logging

from app.core.logging_config import JsonFormatter, SensitiveFilter, MASK


def _record(msg: str, *args: object) -> logging.LogRecord:
    return logging.LogRecord(
        name="test", level=logging.INFO, pathname=__file__, lineno=1,
        msg=msg, args=args, exc_info=None,
    )


class TestNumericFormatting:
    """형 보존 — 이것이 깨지면 서드파티 로그가 요청을 죽인다."""

    def test_percent_d_with_int_argument_survives(self) -> None:
        record = _record('HTTP Request: %s %s "%s %d %s"', "GET", "http://x/y", "HTTP/1.1", 200, "OK")
        SensitiveFilter().filter(record)
        # 이전 구현에서는 여기서 TypeError 가 났다.
        assert record.getMessage() == 'HTTP Request: GET http://x/y "HTTP/1.1 200 OK"'

    def test_percent_f_with_float_argument_survives(self) -> None:
        record = _record("소요 %.2f초", 1.5)
        SensitiveFilter().filter(record)
        assert record.getMessage() == "소요 1.50초"

    def test_percent_r_preserves_repr(self) -> None:
        record = _record("값 %r", ["a", 1])
        SensitiveFilter().filter(record)
        assert record.getMessage() == "값 ['a', 1]"

    def test_dict_style_args_preserve_types(self) -> None:
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__, lineno=1,
            msg="%(method)s %(status)d", args={"method": "GET", "status": 204}, exc_info=None,
        )
        SensitiveFilter().filter(record)
        assert record.getMessage() == "GET 204"


class TestMaskingStillWorks:
    """형을 보존하면서도 비밀은 여전히 가려져야 한다 (SEC-03)."""

    def test_secret_in_message_is_masked(self) -> None:
        record = _record("요청 헤더 X-NCP-APIGW-API-KEY: abcd1234efgh")
        SensitiveFilter().filter(record)
        message = record.getMessage()
        assert "abcd1234efgh" not in message
        assert MASK in message

    def test_secret_in_string_argument_is_masked(self) -> None:
        record = _record("헤더 %s", "authorization: Bearer zzzz9999")
        SensitiveFilter().filter(record)
        message = record.getMessage()
        assert "zzzz9999" not in message
        assert MASK in message

    def test_anthropic_key_shape_is_masked(self) -> None:
        # 🔴 실제 키처럼 보이는 문자열을 소스에 두지 않는다.
        #    GitHub 시크릿 스캐닝(push protection)에 걸리면 푸시가 막힌다.
        #    접두사는 패턴 검증에 필요하므로 남기고, 뒤는 명백히 가짜로 둔다.
        fake_key = "sk-ant-" + "api03-NOT-A-REAL-KEY-FOR-TESTS-ONLY"
        record = _record("키 %s", fake_key)
        SensitiveFilter().filter(record)
        assert fake_key not in record.getMessage()

    def test_secret_inside_non_string_argument_is_caught_by_formatter(self) -> None:
        # 🔴 필터는 비문자열을 건드리지 않는다. 그래서 포매터가 2차 방어선이 된다.
        payload = {"api_key": "supersecretvalue"}
        record = _record("설정 %s", payload)
        SensitiveFilter().filter(record)
        rendered = JsonFormatter().format(record)
        assert "supersecretvalue" not in rendered
        assert MASK in rendered
