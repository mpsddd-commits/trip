"""스키마 생성·버전 관리.

근거:
    NFR-9   재현 가능한 기동. 외부 마이그레이션 도구(Alembic)를 도입하지 않는다
            — 단일 사용자 로컬 배포(Q20=A)에서 스키마 진화 요구가 낮고,
              의존성을 늘리지 않는 편이 SEC-10(공급망) 관점에서도 유리하다.
    SEC-05  DDL 은 ORM 메타데이터로만 생성한다
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from app.core.logging_config import get_logger
from app.storage.models import Base

logger = get_logger(__name__)

SCHEMA_VERSION = 1


def run_migrations(engine: Engine) -> int:
    """테이블을 생성하고 스키마 버전을 기록한다.

    반환값: 적용된 스키마 버전
    """
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        conn.execute(
            text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
        )
        current = conn.execute(text("SELECT version FROM schema_version")).scalar()
        if current is None:
            conn.execute(
                text("INSERT INTO schema_version (version) VALUES (:v)"),
                {"v": SCHEMA_VERSION},
            )
            current = SCHEMA_VERSION
        elif current < SCHEMA_VERSION:
            # 향후 스키마 변경 시 이 지점에 단계별 이행을 추가한다.
            conn.execute(
                text("UPDATE schema_version SET version = :v"), {"v": SCHEMA_VERSION}
            )
            current = SCHEMA_VERSION

    logger.info("schema ready", extra={"schema_version": current})
    return int(current)
