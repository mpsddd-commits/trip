# Build Instructions — trip

**실측 일시**: 2026-08-14 (Build and Test 스테이지)
**실측 환경**: Windows 10 Pro / Docker 29.7.2 / Compose v5.4.0

> 🔴 **로컬에 Python·Node·JDK 를 설치할 필요가 없습니다.** 모든 빌드가 컨테이너 안에서 돕니다.
> 실제로 이 프로젝트의 검증은 전부 컨테이너에서 수행됐습니다.

---

## 전제 조건

| 항목 | 요구 | 비고 |
|---|---|---|
| Docker | 24 이상 | 실측 29.7.2 |
| Docker Compose | v2.24 이상 | `env_file` 의 `required: false` 를 씁니다 |
| 디스크 | 앱 ~2GB / 안드로이드 빌드 추가 ~4GB | Android SDK 가 큽니다 |
| 네트워크 | 최초 빌드 시 필요 | 이후는 캐시 |
| 자격증명 | **불필요** | 없으면 목 모드로 동작합니다 (FR-33) |

---

## 1. 애플리케이션 (u1 + u2, 단일 컨테이너)

```bash
cd trip
docker compose build      # 멀티스테이지: node:24-alpine(web) -> python:3.12-slim(runtime)
docker compose up -d
```

접속: <http://127.0.0.1:8200>

**산출물**: `trip-app:latest` — 실측 **285MB** (설계 예상 250~400MB 범위 안)

**빌드 단계**
1. `web-build` — `npm ci` → `vite build` → `/build/dist`
2. `runtime` — `pip install -r requirements.txt` → 앱 코드 + `dist` 를 `./static` 으로 복사
3. `compileall` 로 문법 검증 → uid 10001 비루트 사용자 생성

> 🔴 **베이스 이미지는 다이제스트로 고정돼 있습니다** (SEC-10 / ID-20).
> 태그는 같은 이름으로 다른 내용이 올 수 있지만 다이제스트는 그럴 수 없습니다.
> 갱신할 때는 이렇게 확인합니다:
> ```bash
> docker buildx imagetools inspect python:3.12-slim --format '{{.Manifest.Digest}}'
> ```

## 2. 안드로이드 APK (u3)

```bash
docker build -f android/Dockerfile.build -t trip-android-build android/
docker run --rm -v "c:/경로/trip/android:/workspace" -v "c:/경로/trip/android/out:/out" trip-android-build
```

**산출물**: `android/out/app-debug.apk` — 실측 **4.18MB**

> ⚠️ Windows Git Bash 에서는 `MSYS_NO_PATHCONV=1` 을 앞에 붙이고 **Windows 형식 절대경로**를 쓰세요.
> `/c/...` 형식은 마운트가 **조용히 무시**되어 이미지 안의 옛 소스로 빌드됩니다.
> 실제로 이 문제로 고친 코드가 반영되지 않아 같은 오류가 반복됐습니다.

---

## 성공 판정

| 대상 | 기대 출력 |
|---|---|
| `docker compose build` | `Image trip-app:latest Built` |
| `docker compose ps` | `trip-app  Up ... (healthy)` — 기동 후 약 20~30초 |
| `curl 127.0.0.1:8200/api/health` | `200` |
| 안드로이드 | `빌드 성공: /out/app-debug.apk` |

### 허용되는 경고

| 경고 | 판단 |
|---|---|
| `StarletteDeprecationWarning: install httpx2 instead` | 테스트 클라이언트만 해당. 동작에 영향 없음 |
| Kotlin `databaseEnabled`/`saveFormData` deprecated | 플랫폼 API. 대체재가 없고 ABR-12 가 요구 |
| `JSONArgsRecommended` (Dockerfile.build CMD) | 셸 형식을 의도적으로 사용 (인자 조립 필요) |

---

## 문제 해결

### `env file .env not found`
`docker-compose.yml` 의 `env_file` 에 `required: false` 가 있는지 확인하세요.
**자격증명 없이도 기동돼야 합니다** (FR-33). 이 항목이 빠져 있어 실제로 기동이 실패했습니다.

### 안드로이드 빌드가 옛 코드로 도는 경우
마운트가 무시된 것입니다. 위의 `MSYS_NO_PATHCONV=1` 항목을 보세요.
확인 방법: `docker run --rm -v "...:/workspace" trip-android-build cat /workspace/settings.gradle.kts`

### `pydantic-core` 휠을 찾지 못함
로컬 Python 3.14 로 설치를 시도한 경우입니다. 컨테이너는 3.12 로 고정돼 있으니
로컬 설치 대신 컨테이너를 쓰세요 (UD-9).
