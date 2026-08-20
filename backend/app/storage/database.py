"""C30 Database — SQLAlchemy 엔진·세션·PRAGMA 관리.

근거:
    SP-1 / ND-5   WAL + busy_timeout 5초 + synchronous=NORMAL + foreign_keys ON
    SEC-05        SQL 은 파라미터 바인딩만 사용 (문자열 연결 금지)
    SEC-15        세션은 try/finally 로 정리, 오류 시 롤백
    NFR-11        SQLite 파일은 볼륨에 보존
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.logging_config import get_logger

logger = get_logger(__name__)

_BUSY_TIMEOUT_MS = 5_000  # SP-1


def _apply_pragmas(dbapi_connection, _record) -> None:  # type: ignore[no-untyped-def]
    """연결마다 SQLite PRAGMA 를 적용한다 (SP-1)."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


class Database:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self.engine: Engine = self._create_engine(database_path)
        event.listen(self.engine, "connect", _apply_pragmas)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    @staticmethod
    def _create_engine(database_path: str) -> Engine:
        if database_path == ":memory:":
            # 테스트 전용. 스레드 간 동일 연결을 공유해야 하므로 StaticPool 을 쓴다.
            from sqlalchemy.pool import StaticPool

            return create_engine(
                "sqlite://",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                future=True,
            )
        path = Path(database_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # ND-18 — 실제 호출은 스레드 풀에서 이뤄지므로 check_same_thread 를 끈다.
        return create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False},
            future=True,
        )

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """트랜잭션 경계. 예외 시 롤백하고 항상 닫는다 (SEC-15).

        ⚠️ 이 블록 안에서 외부 API 를 호출하지 않는다 (SP-1 — 잠금 시간 최소화).
        """
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def dispose(self) -> None:
        self.engine.dispose()
