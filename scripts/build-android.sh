#!/usr/bin/env sh
# 안드로이드 APK 컨테이너 빌드 (ID-16 / UD-13)
#
# ⚠️ 최초 실행 시 Android SDK 를 수 GB 내려받습니다.
# ⚠️ 이 빌드는 **컴파일·패키징·단위 테스트까지만** 검증합니다.
#    WebView 로딩 · 지도 앱 인텐트 · 다운로드 · 위치 권한은 실기기에서만 확인됩니다 —
#    android/README.md 의 "실기기 확인 체크리스트 8항목" 을 보세요 (ASM-4).
#
# 사용법:
#   ./scripts/build-android.sh                                  # 에뮬레이터용 (10.0.2.2)
#   ./scripts/build-android.sh http://192.168.0.10:8200         # 실기기용

set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${1:-}"

# 🔴 Git Bash(MSYS)는 `-v /c/...` 를 도커에 그대로 넘기지 못합니다.
#    마운트가 **조용히 무시되어** 이미지 안의 옛 소스로 빌드됩니다. 오류가 나지 않아
#    "고쳤는데 왜 그대로지?" 로 한참 헤매게 됩니다. 경로를 c:/... 형식으로 바꿔 넘깁니다.
case "$(uname -s 2>/dev/null || echo unknown)" in
    MINGW*|MSYS*|CYGWIN*)
        MOUNT_ROOT="$(cd "$ROOT" && pwd -W 2>/dev/null || echo "$ROOT")"
        export MSYS_NO_PATHCONV=1
        ;;
    *)
        MOUNT_ROOT="$ROOT"
        ;;
esac

if [ ! -f "$ROOT/android/settings.gradle.kts" ]; then
    echo "android/settings.gradle.kts 가 없습니다. u3-trip-android 가 아직 생성되지 않았습니다."
    exit 1
fi

# NOTE: gradlew(래퍼 JAR)는 바이너리라 저장소에 두지 않습니다.
#       Dockerfile.build 가 컨테이너 안에 Gradle 배포판을 설치합니다.

mkdir -p "$ROOT/android/out"

echo "빌드 이미지를 준비합니다 (최초 실행 시 수 GB 다운로드)..."
docker build -f "$MOUNT_ROOT/android/Dockerfile.build" -t trip-android-build "$MOUNT_ROOT/android"

echo "단위 테스트와 APK 빌드를 실행합니다..."
if [ -n "$BASE_URL" ]; then
    # 실기기: 접속 주소와 평문 허용 호스트를 함께 넣어야 합니다 (ABR-05).
    HOST="$(printf '%s' "$BASE_URL" | sed -E 's#^https?://##; s#[:/].*$##')"
    echo "  접속 주소: $BASE_URL  (평문 허용 호스트: $HOST)"
    docker run --rm \
        -v "$MOUNT_ROOT/android:/workspace" \
        -v "$MOUNT_ROOT/android/out:/out" \
        -e BASE_URL="$BASE_URL" \
        -e CLEARTEXT_HOST="$HOST" \
        trip-android-build
else
    echo "  접속 주소: http://10.0.2.2:8200 (에뮬레이터 기본값)"
    docker run --rm \
        -v "$MOUNT_ROOT/android:/workspace" \
        -v "$MOUNT_ROOT/android/out:/out" \
        trip-android-build
fi

echo ""
echo "완료: android/out/app-debug.apk"
echo "      android/out/test-report/index.html"
echo ""
echo "🔴 설치한 뒤 android/README.md 의 실기기 체크리스트 8항목을 확인하세요."
echo "   컨테이너 빌드가 성공했다는 것은 앱이 동작한다는 뜻이 아닙니다."
