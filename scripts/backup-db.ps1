# SQLite 백업 (ID-8)
#
# ⚠️ `data/` 폴더를 그냥 복사하면 안 됩니다.
#    WAL 에만 있고 DB 본체에 반영되지 않은 트랜잭션이 누락됩니다 (ID-9).
#    sqlite3 CLI 는 python:slim 이미지에 없으므로 표준 라이브러리의
#    Connection.backup() 을 사용합니다.
#
# 사용법:  .\scripts\backup-db.ps1

$ErrorActionPreference = "Stop"

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$script = @"
import sqlite3, sys
src = sqlite3.connect('/app/data/trip.db')
dst = sqlite3.connect('/app/data/backup-$timestamp.db')
with dst:
    src.backup(dst)
dst.close(); src.close()
print('backup-$timestamp.db')
"@

Write-Host "SQLite 백업을 시작합니다..."
docker compose exec -T app python -c $script
if ($?) {
    Write-Host "완료: data/backup-$timestamp.db"
    Write-Host "참고: 백업 파일도 .gitignore 대상입니다."
}
