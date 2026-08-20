#!/usr/bin/env sh
# SQLite 백업 (ID-8)
#
# ⚠️ `data/` 폴더를 그냥 복사하면 WAL 에만 있는 트랜잭션이 누락됩니다 (ID-9).
#    sqlite3 CLI 가 slim 이미지에 없어 Python 표준 라이브러리를 사용합니다.
#
# 사용법:  ./scripts/backup-db.sh

set -eu

TIMESTAMP=$(date +%Y%m%d-%H%M%S)

echo "SQLite 백업을 시작합니다..."
docker compose exec -T app python -c "
import sqlite3
src = sqlite3.connect('/app/data/trip.db')
dst = sqlite3.connect('/app/data/backup-${TIMESTAMP}.db')
with dst:
    src.backup(dst)
dst.close(); src.close()
print('backup-${TIMESTAMP}.db')
"
echo "완료: data/backup-${TIMESTAMP}.db"
