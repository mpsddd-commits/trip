"""C2 LoggingSetup — 구조화 JSON 로깅 + 상관관계 ID + 민감값 마스킹.

근거:
    NFR-8   구조화 로깅 + 요청 상관관계 ID
    SEC-03  timestamp / correlation_id / level / message 포함, 비밀·PII 미기록
    SEC-14  90일 로테이션 보존
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import re
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

# SEC-03 — 로그 본문에 새어나가면 안 되는 패턴.
# 값 자체를 판별하기는 어려우므로 "키=값" 형태를 넓게 잡아 마스킹한다.
# 🔴 키 뒤에 따옴표가 낀 형태(파이썬 repr `{'api_key': 'v'}`, JSON `"api_key": "v"`)도 잡아야 한다.
#    Build and Test 에서 발견: 딕셔너리를 `%s` 로 로깅하면 이 형태가 되는데
#    따옴표를 고려하지 않은 패턴은 그대로 흘려보냈다.
_Q = r"[\"']?"          # 키/값을 감싸는 따옴표 (있을 수도, 없을 수도)
_VALUE = r"([^\s,;'\"}\]]+)"

_SENSITIVE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(rf"(?i)(x-ncp-apigw-api-key(?:-id)?{_Q}\s*[:=]\s*{_Q}){_VALUE}"),
    re.compile(rf"(?i)(x-naver-client-(?:id|secret){_Q}\s*[:=]\s*{_Q}){_VALUE}"),
    re.compile(
        rf"(?i)((?:api[_-]?key|client[_-]?secret|client[_-]?id|access[_-]?token|"
        rf"secret|password|authorization){_Q}\s*[:=]\s*{_Q}(?:bearer\s+)?){_VALUE}"
    ),
    # 🔴 `Authorization: Bearer <토큰>` — 이전 패턴은 "Bearer" 를 값으로 보고 마스킹한 뒤
    #    정작 **토큰을 그대로 남겼다.** 위 패턴의 `(?:bearer\s+)?` 가 이를 접두사로 넘긴다.
    #    헤더 이름 없이 "Bearer xxx" 만 나오는 경우를 위해 독립 패턴도 둔다.
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9\-._~+/]{8,}=*)"),
    re.compile(r"(sk-ant-[A-Za-z0-9\-_]{8,})"),
)

MASK = "***REDACTED***"


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def set_correlation_id(value: str) -> None:
    _correlation_id.set(value)


def get_correlation_id() -> str:
    return _correlation_id.get()


def mask_sensitive(text: str) -> str:
    """민감값을 마스킹한다 (SEC-03)."""
    masked = text
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.groups >= 2:
            masked = pattern.sub(lambda m: f"{m.group(1)}{MASK}", masked)
        else:
            masked = pattern.sub(MASK, masked)
    return masked


class SensitiveFilter(logging.Filter):
    """포맷 이전에 메시지와 인자를 마스킹한다.

    🔴 **문자열 인자만 손댄다.**

    이전 구현은 모든 인자를 ``str(a)`` 로 바꿔 마스킹했다. 그 결과
    ``logger.info('%s %d', 'GET', 200)`` 처럼 ``%d`` / ``%f`` 를 쓰는 로그가
    ``TypeError: %d format: a real number is required, not str`` 로 죽었다.

    Filter 는 ``Handler.emit()`` 의 try/except **밖**에서 실행되므로 이 예외는
    로깅 내부에서 삼켜지지 않고 **로그를 호출한 코드로 그대로 튀어나간다.**
    httpx 가 요청마다 ``%d`` 로 상태 코드를 남기기 때문에 실제로 요청 처리 중
    예외가 터졌다 (Build and Test 에서 u1 테스트 206건 중 다수가 이 하나 때문에 실패).

    비문자열 인자는 형을 보존하고, 최종 마스킹은 ``JsonFormatter`` 가
    포맷을 마친 문자열에 한 번 더 적용한다 (이중 방어).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_sensitive(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: _mask_arg(v) for k, v in record.args.items()}
            else:
                record.args = tuple(_mask_arg(a) for a in record.args)
        return True


def _mask_arg(value: object) -> object:
    """문자열이면 마스킹하고, 그 밖의 형은 **그대로 둔다**.

    형을 바꾸면 ``%d`` · ``%f`` · ``%r`` 포맷이 깨진다.
    문자열이 아닌 값 안의 비밀은 ``JsonFormatter`` 가 최종 메시지에서 잡는다.
    """
    return mask_sensitive(value) if isinstance(value, str) else value


class JsonFormatter(logging.Formatter):
    """SEC-03 요구 필드를 포함하는 한 줄 JSON 포매터."""

    _RESERVED = frozenset(
        vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
    ) | {"message", "asctime", "taskName"}

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": get_correlation_id(),
            # 🔴 비문자열 인자 안의 비밀을 잡는 2차 방어선.
            #    SensitiveFilter 는 문자열 인자만 손대므로 여기서 최종 메시지를 한 번 더 훑는다.
            "message": mask_sensitive(record.getMessage()),
        }
        for key, value in record.__dict__.items():
            if key not in self._RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            # 스택트레이스는 로그에만 남는다. 사용자 응답에는 절대 포함하지 않는다 (SEC-09).
            payload["exception"] = mask_sensitive(self.formatException(record.exc_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(log_dir: str, log_level: str, retention_days: int = 90) -> None:
    """루트 로거를 구성한다. 애플리케이션 기동 시 1회 호출한다."""
    root = logging.getLogger()
    root.setLevel(log_level.upper())
    for handler in list(root.handlers):
        root.removeHandler(handler)

    formatter = JsonFormatter()
    sensitive_filter = SensitiveFilter()

    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    stream.addFilter(sensitive_filter)
    root.addHandler(stream)

    directory = Path(log_dir)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        # SEC-14 — 일 단위 로테이션, 90일 보존
        file_handler = logging.handlers.TimedRotatingFileHandler(
            directory / "app.jsonl",
            when="midnight",
            backupCount=retention_days,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        root.addHandler(file_handler)
    except OSError:
        # 읽기 전용 파일시스템(ID-6)에서 볼륨이 없을 때도 기동은 계속한다.
        root.warning("로그 디렉터리에 쓸 수 없어 표준 출력 로깅만 사용합니다: %s", log_dir)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
