# 안드로이드 APK 컨테이너 빌드 (ID-16 / UD-13)
#
# ⚠️ 최초 실행 시 Android SDK 를 수 GB 내려받습니다. 수 분이 걸립니다.
# ⚠️ 이 빌드는 **컴파일·패키징·단위 테스트까지만** 검증합니다.
#    WebView 로딩 · 지도 앱 인텐트 · 다운로드 · 위치 권한은 실기기에서만 확인됩니다 —
#    android\README.md 의 "실기기 확인 체크리스트 8항목" 을 보세요 (ASM-4).
#
# 사용법:
#   .\scripts\build-android.ps1                              # 에뮬레이터용 (10.0.2.2)
#   .\scripts\build-android.ps1 http://192.168.0.10:8200     # 실기기용

param([string]$BaseUrl = "")

# 🔴 "Stop" 을 쓰면 안 됩니다.
#    docker build 는 진행 상황을 stderr 로 씁니다. Windows PowerShell 5.1 은 네이티브 명령의
#    stderr 를 ErrorRecord 로 감싸므로, ErrorActionPreference=Stop 이면 **빌드가 성공하는 중에도**
#    첫 진행 로그에서 스크립트가 죽습니다. 성공 여부는 $LASTEXITCODE 로 판정합니다.
$ErrorActionPreference = "Continue"
$root = (Resolve-Path "$PSScriptRoot\..").Path

# 도커에 넘길 때는 슬래시 경로를 씁니다.
$mount = $root -replace '\\', '/'

if (-not (Test-Path "$root\android\settings.gradle.kts")) {
    Write-Warning "android\settings.gradle.kts 가 없습니다. u3-trip-android 가 아직 생성되지 않았습니다."
    exit 1
}

# NOTE: gradlew(래퍼 JAR)는 바이너리라 저장소에 두지 않습니다.
#       Dockerfile.build 가 컨테이너 안에 Gradle 배포판을 설치합니다.

New-Item -ItemType Directory -Force -Path "$root\android\out" | Out-Null

Write-Host "빌드 이미지를 준비합니다 (최초 실행 시 수 GB 다운로드)..."
docker build -f "$mount/android/Dockerfile.build" -t trip-android-build "$mount/android"
if ($LASTEXITCODE -ne 0) { Write-Error "이미지 빌드 실패"; exit 1 }

Write-Host "단위 테스트와 APK 빌드를 실행합니다..."
if ($BaseUrl) {
    # 실기기: 접속 주소와 평문 허용 호스트를 함께 넣어야 합니다 (ABR-05).
    $hostOnly = ($BaseUrl -replace '^https?://', '') -replace '[:/].*$', ''
    Write-Host "  접속 주소: $BaseUrl  (평문 허용 호스트: $hostOnly)"
    docker run --rm `
        -v "${mount}/android:/workspace" `
        -v "${mount}/android/out:/out" `
        -e "BASE_URL=$BaseUrl" `
        -e "CLEARTEXT_HOST=$hostOnly" `
        trip-android-build
} else {
    Write-Host "  접속 주소: http://10.0.2.2:8200 (에뮬레이터 기본값)"
    docker run --rm `
        -v "${mount}/android:/workspace" `
        -v "${mount}/android/out:/out" `
        trip-android-build
}
if ($LASTEXITCODE -ne 0) { Write-Error "APK 빌드 실패 — 출력의 오류 메시지를 확인하세요"; exit 1 }

Write-Host ""
Write-Host "완료: android\out\app-debug.apk"
Write-Host "      android\out\test-report\index.html"
Write-Host ""
Write-Host "🔴 설치한 뒤 android\README.md 의 실기기 체크리스트 8항목을 확인하세요."
Write-Host "   컨테이너 빌드가 성공했다는 것은 앱이 동작한다는 뜻이 아닙니다."
