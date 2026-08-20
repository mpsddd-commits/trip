#!/usr/bin/env sh
# 의존성 취약점 스캔 (ID-17 / SEC-10)
#
# 🔴 로컬에 Python·Node 를 설치할 필요가 없습니다. 컨테이너에서 돕니다.
#    (이 프로젝트의 다른 모든 빌드·테스트와 같은 방식입니다.)
#
# ⚠️ 네트워크 접근이 필요합니다. 실패하면 그 사실을 그대로 보고하세요 —
#    "스캔을 못 했다" 와 "취약점이 없다" 는 다릅니다.
#
# 사용법:  ./scripts/audit-deps.sh

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAILED=0

# Git Bash(MSYS)에서 도커 마운트 경로 보정 — build-android.sh 와 같은 이유.
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*)
        MOUNT_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
        export MSYS_NO_PATHCONV=1
        ;;
    *)
        MOUNT_ROOT="$ROOT"
        ;;
esac

echo "=== Python 런타임 의존성 (pip-audit) ==="
docker run --rm -v "$MOUNT_ROOT/backend:/app:ro" -w /app python:3.12-slim sh -c '
    pip install --quiet --no-cache-dir --upgrade pip >/dev/null 2>&1
    pip install --quiet --no-cache-dir pip-audit >/dev/null 2>&1
    pip-audit --progress-spinner off --requirement requirements.txt --strict
' || FAILED=1

echo ""
echo "=== Python 개발 의존성 ==="
docker run --rm -v "$MOUNT_ROOT/backend:/app:ro" -w /app python:3.12-slim sh -c '
    pip install --quiet --no-cache-dir --upgrade pip >/dev/null 2>&1
    pip install --quiet --no-cache-dir pip-audit >/dev/null 2>&1
    pip-audit --progress-spinner off --requirement requirements-dev.txt
' || echo "  (개발 의존성 이슈는 배포에 직접 영향을 주지 않습니다. 다만 방치하지는 마세요.)"

echo ""
echo "=== Node 런타임 의존성 (npm audit) ==="
if [ -f "$ROOT/web/package-lock.json" ]; then
    docker run --rm -v "$MOUNT_ROOT/web:/app" -w /app node:24-alpine \
        npm audit --omit=dev --audit-level=high || FAILED=1
else
    echo "web/package-lock.json 이 없습니다. 건너뜁니다."
fi

echo ""
echo "=== 베이스 이미지 다이제스트 (ID-20 / SEC-10) ==="
echo "Dockerfile 에 고정된 값과 현재 태그가 가리키는 값을 비교합니다."
for pair in "node:24-alpine" "python:3.12-slim" "eclipse-temurin:17-jdk-noble"; do
    current="$(docker buildx imagetools inspect "$pair" --format '{{.Manifest.Digest}}' 2>/dev/null || echo 'inspect 실패')"
    pinned="$(grep -ho "$(printf '%s' "$pair" | cut -d: -f1):[^@]*@sha256:[0-9a-f]*" "$ROOT/Dockerfile" "$ROOT/android/Dockerfile.build" 2>/dev/null | head -1 | sed 's/.*@//')"
    if [ -z "$pinned" ]; then
        echo "  $pair : 고정값을 찾지 못했습니다"
    elif [ "$current" = "$pinned" ]; then
        echo "  $pair : 최신 (변경 없음)"
    else
        echo "  $pair : 상위 이미지가 갱신됐습니다"
        echo "      고정 $pinned"
        echo "      최신 $current"
        echo "      → 검토 후 Dockerfile 의 다이제스트를 교체하세요."
    fi
done

echo ""
if [ "$FAILED" -ne 0 ]; then
    echo "🔴 런타임 의존성에서 문제가 보고되었습니다. 배포 전에 해소하세요 (SEC-10 은 blocking)."
    exit 1
fi
echo "취약점 스캔 완료 — 런타임 의존성에 차단 수준 이슈 없음"
