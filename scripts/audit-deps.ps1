# 의존성 취약점 스캔 (ID-17 / SEC-10)
#
# 🔴 로컬에 Python·Node 를 설치할 필요가 없습니다. 컨테이너에서 돕니다.
#    (이 프로젝트의 다른 모든 빌드·테스트와 같은 방식입니다.)
#
# ⚠️ 네트워크 접근이 필요합니다. 실패하면 그 사실을 그대로 보고하세요 —
#    "스캔을 못 했다" 와 "취약점이 없다" 는 다릅니다.
#
# 사용법:  .\scripts\audit-deps.ps1

$ErrorActionPreference = "Continue"
$root = (Resolve-Path "$PSScriptRoot\..").Path
$mount = $root -replace '\\', '/'
$failed = $false

# 🔴 컨테이너 **안에서** stderr 를 stdout 으로 합칩니다.
#    Windows PowerShell 5.1 은 네이티브 명령의 stderr 한 줄 한 줄을 ErrorRecord 로 감싸서
#    "No known vulnerabilities found" 같은 정상 메시지까지 빨간 오류처럼 보여줍니다.
#    바깥에서 2>&1 을 하면 $LASTEXITCODE 판정까지 흐트러지므로 안에서 처리합니다.
$auditScript = @'
pip install --quiet --no-cache-dir --upgrade pip >/dev/null 2>&1
pip install --quiet --no-cache-dir pip-audit >/dev/null 2>&1
pip-audit --progress-spinner off --requirement REQFILE STRICTFLAG 2>&1
'@

Write-Host "=== Python 런타임 의존성 (pip-audit) ==="
$cmd = $auditScript.Replace("REQFILE", "requirements.txt").Replace("STRICTFLAG", "--strict")
docker run --rm -v "${mount}/backend:/app:ro" -w /app python:3.12-slim sh -c $cmd
if ($LASTEXITCODE -ne 0) { $failed = $true }

Write-Host ""
Write-Host "=== Python 개발 의존성 ==="
$cmd = $auditScript.Replace("REQFILE", "requirements-dev.txt").Replace("STRICTFLAG", "")
docker run --rm -v "${mount}/backend:/app:ro" -w /app python:3.12-slim sh -c $cmd
if ($LASTEXITCODE -ne 0) {
    Write-Host "  (개발 의존성 이슈는 배포에 직접 영향을 주지 않습니다. 다만 방치하지는 마세요.)"
}

Write-Host ""
Write-Host "=== Node 런타임 의존성 (npm audit) ==="
if (Test-Path "$root\web\package-lock.json") {
    docker run --rm -v "${mount}/web:/app" -w /app node:24-alpine sh -c "npm audit --omit=dev --audit-level=high 2>&1"
    if ($LASTEXITCODE -ne 0) { $failed = $true }
} else {
    Write-Host "web\package-lock.json 이 없습니다. 건너뜁니다."
}

Write-Host ""
Write-Host "=== 베이스 이미지 다이제스트 (ID-20 / SEC-10) ==="
Write-Host "Dockerfile 에 고정된 값과 현재 태그가 가리키는 값을 비교합니다."
$pinnedText = (Get-Content "$root\Dockerfile", "$root\android\Dockerfile.build" -Raw) -join "`n"
foreach ($image in @("node:24-alpine", "python:3.12-slim", "eclipse-temurin:17-jdk-noble")) {
    $current = docker buildx imagetools inspect $image --format '{{.Manifest.Digest}}' 2>$null
    $name = $image.Split(":")[0]
    $m = [regex]::Match($pinnedText, [regex]::Escape($name) + ":[^@\s]*@(sha256:[0-9a-f]+)")
    if (-not $m.Success) {
        Write-Host "  $image : 고정값을 찾지 못했습니다"
    } elseif ($current -eq $m.Groups[1].Value) {
        Write-Host "  $image : 최신 (변경 없음)"
    } else {
        Write-Host "  $image : 상위 이미지가 갱신됐습니다"
        Write-Host "      고정 $($m.Groups[1].Value)"
        Write-Host "      최신 $current"
        Write-Host "      -> 검토 후 Dockerfile 의 다이제스트를 교체하세요."
    }
}

Write-Host ""
if ($failed) {
    Write-Host "🔴 런타임 의존성에서 문제가 보고되었습니다. 배포 전에 해소하세요 (SEC-10 은 blocking)."
    exit 1
}
Write-Host "취약점 스캔 완료 - 런타임 의존성에 차단 수준 이슈 없음"
