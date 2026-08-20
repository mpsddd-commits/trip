# Deployment Architecture — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Infrastructure Design (Unit 1/3)
**Created**: 2026-08-13T06:30:00Z

---

## 1. 파일 배치

```
trip/                                  <- Compose 프로젝트 루트 (UD-14)
+-- docker-compose.yml
+-- Dockerfile                         <- 멀티스테이지 (web-build -> runtime)
+-- .env.example                       <- 커밋됨
+-- .env                               <- .gitignore (실제 인증 정보)
+-- .dockerignore
+-- .gitignore
+-- README.md
|
+-- scripts/
|   +-- backup-db.ps1 / .sh            <- ID-8
|   +-- audit-deps.ps1 / .sh           <- ID-17 (SEC-10)
|   +-- generate-sbom.py               <- ID-18 (SEC-10)
|   +-- build-android.ps1 / .sh        <- ID-16 (UD-13)
|
+-- backend/                           <- u1 소스
+-- web/                               <- u2 소스 (빌드 산출물이 이미지에 복사됨)
+-- android/                           <- u3 소스 + Dockerfile.build
|
+-- data/                              <- 볼륨 (gitignore, WAL 포함)
|   +-- .gitkeep
+-- logs/                              <- 볼륨 (gitignore)
|   +-- .gitkeep
|
+-- aidlc-docs/                        <- 문서 (코드 금지)
```

### `.gitignore` 필수 항목

```
.env
data/*.db
data/*.db-wal
data/*.db-shm
data/backup-*.db
logs/*.jsonl
logs/*.log
__pycache__/
node_modules/
web/dist/
android/build/
android/app/build/
android/.gradle/
*.apk
```

> `web/src/shared/api/generated.ts` 는 **커밋합니다**(UD-3). 이 파일이 없으면 이미지 빌드가 순환합니다.

---

## 2. `docker-compose.yml` 구조

```yaml
name: trip                                    # ID-15 격리

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    image: trip-app:latest
    container_name: trip-app

    ports:
      - "${BIND_HOST:-127.0.0.1}:${PORT:-8200}:8200"   # ID-11 (CA-1 해소)

    env_file: [.env]
    environment:
      TZ: Asia/Seoul

    volumes:
      - ./data:/app/data                      # ID-7
      - ./logs:/app/logs                      # ID-7

    read_only: true                           # ID-6
    tmpfs:
      - /tmp:size=64m                         # ID-19

    user: "10001:10001"                       # ID-6

    deploy:
      resources:
        limits: { memory: 1g, cpus: "1.5" }   # ID-5

    healthcheck:                              # ID-13
      test: ["CMD", "python", "-c", "<urllib 호출>"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

    logging:                                  # ID-14
      driver: json-file
      options: { max-size: "10m", max-file: "3" }

    restart: unless-stopped
```

> **주의**: `read_only: true` 와 볼륨 마운트가 함께 쓰입니다. 볼륨으로 마운트된 경로(`/app/data`, `/app/logs`)와 tmpfs(`/tmp`)는 읽기 전용 제약을 받지 않습니다.

---

## 3. 기동·운용 절차

### 3.1 최초 기동

```
1. cd trip
2. cp .env.example .env          (Windows: Copy-Item)
3. .env 편집 — 인증 정보 입력 (비워두면 목 모드로 동작)
4. docker compose up -d --build
5. http://127.0.0.1:8200 접속
```

**인증 정보가 없어도 기동됩니다** (FR-33). 화면 상단에 "데모 데이터" 배너가 표시되고, `/api/health/ready` 에서 어떤 API 가 목 모드인지 확인할 수 있습니다.

### 3.2 개발 모드 (ID-3)

```
터미널 1:  docker compose up -d              # 백엔드 8200
터미널 2:  cd web && npm run dev             # Vite 5273, /api 프록시

접속: http://localhost:5273
```
`.env` 에 `CORS_ALLOW_ORIGINS=http://localhost:5273` 를 설정합니다 (ND-12).

### 3.3 안드로이드 연동 시 (CA-1)

```
1. .env 에서 BIND_HOST=0.0.0.0 으로 변경
2. docker compose up -d          (기동 로그에 WARN 이 출력됨 — 정상)
3. 에뮬레이터:  BASE_URL = http://10.0.2.2:8200
   실기기:      BASE_URL = http://<PC의 LAN IP>:8200
                 (ipconfig 로 확인, 방화벽에서 8200 인바운드 허용 필요)
4. 사용 후 BIND_HOST=127.0.0.1 로 되돌리기 (권장)
```

> ⚠️ `0.0.0.0` 상태에서는 **같은 네트워크의 누구나** 인증 없이 접근할 수 있습니다 (Q16=A 로 인증 없음).
> 공용 Wi-Fi 에서는 사용하지 마세요.

### 3.4 안드로이드 APK 빌드 (ID-16, UD-13)

```
docker build -f android/Dockerfile.build -t trip-android-build android/
docker run --rm -v "${PWD}/android/out:/out" trip-android-build
# -> android/out/app-debug.apk
```
Compose 와 분리되어 있어 `docker compose up` 은 이 이미지를 받지 않습니다.

### 3.5 백업 (ID-8)

```
docker compose exec app python -c "import sqlite3,datetime; \
  ts=datetime.datetime.now().strftime('%Y%m%d-%H%M%S'); \
  src=sqlite3.connect('/app/data/trip.db'); \
  dst=sqlite3.connect(f'/app/data/backup-{ts}.db'); \
  src.backup(dst); dst.close(); src.close()"
```
**`data/` 폴더 단순 복사는 권장하지 않습니다** — WAL 에만 있는 트랜잭션이 누락될 수 있습니다.

### 3.6 정지·초기화

```
docker compose down                  # 컨테이너만 정지 (데이터 유지)
docker compose down && rm -rf data/* logs/*    # 완전 초기화
```

---

## 4. 다른 프로젝트와의 동시 운용 (ID-15)

```
+---------------------------------------------------------------+
|  Docker Desktop                                               |
|                                                               |
|  +---------------------+  +---------------------+             |
|  |  프로젝트 news      |  |  프로젝트 trip      |             |
|  |  net: news_default  |  |  net: trip_default  |             |
|  |  127.0.0.1:8100     |  |  127.0.0.1:8200     |             |
|  |  이미지 news-app    |  |  이미지 trip-app    |             |
|  +---------------------+  +---------------------+             |
|                                                               |
|  +---------------------------------------------+              |
|  |  프로젝트 miniproject (중지 중)             |              |
|  |  3000 / 8000 / 5432                         |              |
|  +---------------------------------------------+              |
+---------------------------------------------------------------+
```

**6축 전부 분리** — 파일 경로 / 프로젝트명 / 네트워크 / 포트 / 볼륨 / 이미지명
→ 세 프로젝트를 **동시에 기동해도 충돌하지 않습니다.** Build & Test 에서 `news-app` 과 동시 가동을 실측 확인합니다.

---

## 5. 운영 배포 시 필요한 사항 (범위 외 — 문서화만, ID-1)

현재 범위는 로컬 배포입니다(OUT-9). 외부에 노출하려면 아래가 **선행되어야** 합니다.

| # | 항목 | 이유 |
|---|---|---|
| 1 | **리버스 프록시 + TLS 종단** | CON-5 — 현재 구성에 TLS 없음. SEC-01·SEC-04(HSTS) 완전 충족의 전제 |
| 2 | **인증 도입** | Q16=A 로 인증이 없습니다. 공개 노출 시 누구나 UUID 만 알면 접근 가능 |
| 3 | **시크릿 관리** | `.env` 파일 대신 시크릿 매니저 (SEC-12) |
| 4 | **다중 인스턴스 전환 준비** | SP-5 — 서킷·레이트 리밋·job 세마포어가 프로세스 내 상태. Redis + PostgreSQL 전환 필요 |
| 5 | **레이트 리밋 재검토** | BR-49 값은 개인 사용 기준. 공개 시 훨씬 엄격해야 함 |
| 6 | **지도 SDK 키 도메인 화이트리스트** | CON-3 — 실제 도메인 등록 필요 |
| 7 | **백업 자동화** | ID-8 은 수동 스크립트만 제공 |

> 이 목록은 "나중에 하면 되는 일"이 아니라 **하나라도 빠지면 공개 배포를 하면 안 되는 조건**입니다.

---

## 6. Build & Test 검증 항목 (인프라 관련)

기존 6건(NFR Design)에 더해 다음을 추가합니다.

| # | 항목 | 판정 기준 |
|---|---|---|
| I-1 | 이미지 빌드 성공 | 멀티스테이지 2단계 완료, 크기 실측 (예상 250~400MB) |
| I-2 | **다이제스트 실측 교체 (ID-20)** | `# DIGEST-PENDING` 을 실제 sha256 으로 교체 → **SEC-10 완결** |
| I-3 | 컨테이너 기동 + healthy 전환 | `docker compose ps` 에서 healthy |
| I-4 | 루프백 전용 바인딩 확인 | 기본 상태에서 `127.0.0.1:8200` 만 리스닝 |
| I-5 | 비루트 실행 확인 | `id` 결과 uid=10001 |
| I-6 | **읽기 전용 FS 확인** | `/app/app` 쓰기 시도 실패, `/app/data` 쓰기 성공 |
| I-7 | 볼륨 보존 확인 | `down` → `up` 후 데이터 유지 |
| I-8 | 타임존 확인 | 컨테이너 내부 KST |
| I-9 | **news-app 과 동시 기동** | 두 컨테이너 모두 healthy, 포트 충돌 없음 |
| I-10 | 목 모드 기동 확인 | `.env` 없이 기동 → 전 화면 동작 + 배너 (FR-33, QG-7) |
| I-11 | 정적 자산 캐시 헤더 | 해시 자산 `immutable`, `index.html` `no-cache` |
| I-12 | 의존성 스캔 실행 (ID-17) | `pip-audit` / `npm audit` 결과 보고 |
| I-13 | SBOM 생성 (ID-18) | 산출물 존재 확인 |
| I-14 | **안드로이드 컨테이너 빌드 (UD-13)** | `assembleDebug` 성공 → **CON-6 해소·SC-7 실측 승격** |
