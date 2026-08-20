# Infrastructure Design — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Infrastructure Design (Unit 1/3)
**Created**: 2026-08-13T06:30:00Z
**결정 근거**: `construction/plans/u1-trip-backend-infrastructure-design-plan.md` Q1~Q18 = 전부 A

---

## 0. 답변 분석에서 검출한 문제 2건

### ⚠️ 검출 1 — 읽기 전용 루트에서 Python 바이트코드 쓰기 실패

`Q6=A`(볼륨 외 읽기 전용 루트 파일시스템)를 적용하면, Python 이 런타임에 `__pycache__/*.pyc` 를 쓰려다 실패합니다.
치명적 오류는 아니지만 **매 import 마다 경고가 발생하고 기동이 느려집니다.**

→ **ID-19 로 해소**:
- `PYTHONDONTWRITEBYTECODE=1` 설정 (런타임 쓰기 시도 자체를 없앰)
- 빌드 단계에서 `compileall` 로 **미리 컴파일**해 기동 속도 확보
- `/tmp` 는 tmpfs 로 마운트 (임시 파일용)

### ⚠️ 검출 2 — 다이제스트를 지금 확정할 수 없음

`Q2=A`(태그 + 다이제스트 병기)는 재현성 확보에 필요하지만, **다이제스트 값은 실제 이미지를 받아봐야 알 수 있습니다.**
설계 문서에 임의의 값을 적으면 거짓 정보가 됩니다.

→ **ID-20 으로 해소**: Dockerfile 에 `# DIGEST-PENDING` 주석과 함께 태그만 먼저 고정하고, **Build & Test 에서 실측 다이제스트로 교체**합니다. 이 미결 상태를 Build & Test 검증 항목에 등록합니다.

> 두 건 모두 사용자 판단 사항이 아닌 기술적 귀결이므로 추가 질문 없이 반영했습니다.

---

## 1. 배포 모델

### 1.1 전체 구조 (UD-8 — 단일 컨테이너)

```
+-----------------------------------------------------------------+
|  호스트 (Windows 10, Docker Desktop 29.6.2)                     |
|                                                                 |
|   Compose 프로젝트: trip          (격리 축 1)                   |
|   네트워크: trip_default          (격리 축 2)                   |
|                                                                 |
|   +---------------------------------------------------------+   |
|   |  컨테이너 trip-app          이미지: trip-app:latest      |   |
|   |                                                         |   |
|   |  +------------------------+  +------------------------+ |   |
|   |  |  uvicorn (워커 1개)    |  |  /app/static           | |   |
|   |  |  FastAPI               |  |  (web/dist 복사본)     | |   |
|   |  |  /api/*                |  |  SPA catch-all         | |   |
|   |  +------------------------+  +------------------------+ |   |
|   |                                                         |   |
|   |  비루트 uid 10001 / 읽기 전용 루트 FS                    |   |
|   |  쓰기 가능: /app/data  /app/logs  /tmp(tmpfs)           |   |
|   |  내부 바인딩: 0.0.0.0:8200                              |   |
|   +---------------------------------------------------------+   |
|          |                    |                    |            |
|          v                    v                    v            |
|   ./data (bind)        ./logs (bind)       포트 매핑            |
|   SQLite + WAL         JSON 로그           ${BIND_HOST}:8200    |
|                                                                 |
+-----------------------------------------------------------------+
                              |
                   기본: 127.0.0.1 (로컬 브라우저 전용)
                   전환: 0.0.0.0   (안드로이드 연동 시에만)
```

### 1.2 컨테이너 명세

| 항목 | 값 | 근거 |
|---|---|---|
| Compose 프로젝트명 | `trip` | Q15=A (격리) |
| 서비스명 | `app` / 컨테이너명 `trip-app` | Q15=A |
| 이미지명 | `trip-app:latest` (로컬 빌드) | Q15=A |
| 베이스 (런타임) | `python:3.12-slim` + 다이제스트 | Q2=A, UD-9, ID-20 |
| 베이스 (빌드) | `node:24-alpine` + 다이제스트 | UD-3, ID-20 |
| 실행 사용자 | **비루트 `appuser` (uid 10001)** | Q6=A, SEC-09 |
| 루트 파일시스템 | **읽기 전용** | Q6=A, SEC-09 |
| 쓰기 가능 경로 | `/app/data`, `/app/logs` (볼륨), `/tmp` (tmpfs 64MB) | Q6=A, ID-19 |
| 메모리 제한 | **1GB** | Q5=A |
| CPU 제한 | **1.5** | Q5=A |
| 재시작 정책 | `unless-stopped` | |
| uvicorn 워커 | **1 (고정, 환경변수로 노출하지 않음)** | **Q4=A, SP-5** |

> 🔴 **워커 1개 고정의 이유**: 서킷 브레이커(L1)·IP 레이트 리밋(C4)·job 세마포어(L3)가 전부 **프로세스 내 상태**입니다.
> 워커를 늘리면 각 워커가 따로 세기 시작해 이 통제들이 **오류 없이 조용히 무력화**됩니다.
> Dockerfile 의 CMD 에 하드코딩하고, 코드 주석과 README 에 사유를 명시합니다.

---

## 2. 이미지 빌드 (멀티스테이지)

```
+---------------------------------------------------------------+
|  stage 1: web-build            node:24-alpine@sha256:<PENDING>|
|                                                               |
|   COPY web/package*.json  ->  npm ci                          |
|   COPY web/               ->  npm run build                   |
|   산출: /build/dist                                           |
|                                                               |
|   * 커밋된 API 타입을 사용하므로 백엔드 기동 불필요 (UD-3)     |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|  stage 2: runtime         python:3.12-slim@sha256:<PENDING>   |
|                                                               |
|   ENV PYTHONDONTWRITEBYTECODE=1  PYTHONUNBUFFERED=1   (ID-19) |
|   COPY backend/requirements.txt -> pip install --no-cache-dir  |
|   COPY backend/app/  -> /app/app/                             |
|   COPY --from=web-build /build/dist -> /app/static            |
|   RUN python -m compileall -q /app/app          (ID-19)       |
|   RUN useradd appuser uid=10001 ; chown /app/data /app/logs   |
|   USER appuser                                                |
|   EXPOSE 8200                                                 |
|   CMD uvicorn app.main:app --host 0.0.0.0 --port 8200         |
|       --workers 1                                (Q4=A 고정)  |
+---------------------------------------------------------------+
```

**예상 이미지 크기**: 약 **250~400MB**
(참고: news 프로젝트는 Playwright Chromium 포함으로 1.98GB 였습니다. 본 유닛은 브라우저 의존이 없어 훨씬 작습니다. **실측은 Build & Test 에서 확인**합니다.)

---

## 3. 네트워킹 (Q11=A — CA-1 해소의 실제 구현 지점)

### 3.1 포트 매핑 구조

```
Compose:  ports: - "${BIND_HOST:-127.0.0.1}:8200:8200"
                     |                        |     |
                     |                        |     +-- 컨테이너 내부 (항상 0.0.0.0)
                     |                        +-------- 호스트 포트
                     +--------------------------------- 노출 인터페이스 (여기가 통제점)
```

**컨테이너 내부는 항상 `0.0.0.0` 에 바인딩**합니다. 컨테이너 안에서 루프백에 바인딩하면 Docker 포트 포워딩이 아예 동작하지 않기 때문입니다. **외부 노출 범위는 Compose 매핑 좌측이 결정**합니다.

### 3.2 환경별 조합표

| 환경 | `.env` 의 `BIND_HOST` | 접근 주소 | 안드로이드 `BASE_URL` |
|---|---|---|---|
| 로컬 브라우저 전용 (**기본**) | `127.0.0.1` | `http://127.0.0.1:8200` | — |
| 개발 (Vite dev) | `127.0.0.1` | 웹 `http://localhost:5273` → `/api` 프록시 → `8200` | — |
| 안드로이드 **에뮬레이터** | `0.0.0.0` | | `http://10.0.2.2:8200` |
| 안드로이드 **실기기** (같은 LAN) | `0.0.0.0` | | `http://<PC의 LAN IP>:8200` |
| 운영 (범위 외) | 프록시 뒤 | | `https://<도메인>` |

### 3.3 `BIND_HOST=0.0.0.0` 의 위험 고지 (SEC-07, NFR-14)

| 사항 | 내용 |
|---|---|
| 노출 범위 | **같은 네트워크의 모든 기기**가 접근 가능 |
| 인증 | **없음** (Q16=A) — 접근한 사람은 UUID 를 알면 여행을 조회·편집할 수 있음 |
| 완화 | ① 기본값을 루프백으로 유지 ② 기동 시 **WARN 로그 출력**(C1) ③ README 에 명시 ④ 사용 후 되돌리기 안내 |
| 운영 배포 | **반드시 리버스 프록시 TLS 종단 필요** (CON-5) |

### 3.4 리버스 프록시 (Q12=A)

**구성에 포함하지 않습니다.** UD-8 로 단일 컨테이너가 API 와 정적 자산을 모두 서빙하므로 프록시가 할 일이 없습니다.
운영 배포 시 TLS 종단 목적으로 필요하다는 사실만 `deployment-architecture.md` 에 남깁니다.

---

## 4. 스토리지

### 4.1 볼륨 (Q7=A, Q9=A, UD-10)

| 호스트 경로 | 컨테이너 경로 | 내용 | 권한 |
|---|---|---|---|
| `./data` | `/app/data` | `trip.db`, `trip.db-wal`, `trip.db-shm` | 쓰기 |
| `./logs` | `/app/logs` | `app.jsonl` + 로테이션 파일 | 쓰기 |
| (tmpfs) | `/tmp` | 임시 파일 (64MB) | 쓰기 |
| — | `/app/app`, `/app/static` | 코드·정적 자산 | **읽기 전용** |

바인드 마운트를 선택한 이유: 호스트에서 SQLite 파일을 바로 열어보고 로그를 `tail` 할 수 있습니다. news 프로젝트도 같은 방식이라 운영 감각이 일관됩니다.

### 4.2 WAL 파일 취급 (Q9=A)

SQLite WAL 은 `-wal`·`-shm` 파일이 **DB 파일과 같은 디렉터리에 있어야** 정상 동작합니다. 볼륨에 함께 보관하고 `.gitignore` 에 등록합니다.

**⚠️ 백업 주의**: `data/` 폴더를 단순 복사하면 WAL 에만 있고 DB 본체에 반영되지 않은 트랜잭션이 누락될 수 있습니다. `.backup` 명령을 써야 일관된 스냅샷을 얻습니다.

### 4.3 백업 (Q8=A)

`scripts/backup-db.sh` (및 `.ps1`) 제공 — `sqlite3 .backup` 기반. **자동 스케줄은 걸지 않습니다.**

```
docker compose exec app python -c \
  "import sqlite3; src=sqlite3.connect('/app/data/trip.db'); \
   dst=sqlite3.connect('/app/data/backup-<timestamp>.db'); src.backup(dst)"
```
> `sqlite3` CLI 가 slim 이미지에 없으므로 Python 표준 라이브러리의 `Connection.backup()` 을 사용합니다.

---

## 5. 메시징 (Q10=A)

**⚪ N/A — 메시지 브로커·큐 서비스를 도입하지 않습니다.**

| 필요 기능 | 대체 구현 |
|---|---|
| job 큐 | SQLite `JobRepository` + 프로세스 내 세마포어 (ND-2, ND-3) |
| 비동기 실행 | `asyncio` 태스크 (L3 `JobRunner`) |
| 재시도 | 제공하지 않음 (ND-4) |

Redis·RabbitMQ 컨테이너가 없어 구성이 단순해지고, 이 선택의 한계(다중 인스턴스 불가)는 NFR Design SP-5 에 문서화되어 있습니다.

---

## 6. 모니터링·로깅

### 6.1 Docker 헬스체크 (Q13=A, ND-14)

```yaml
healthcheck:
  test: ["CMD", "python", "-c",
         "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8200/api/health',timeout=3).status==200 else 1)"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 20s
```

| 결정 | 이유 |
|---|---|
| `curl` 대신 Python | `python:3.12-slim` 에 `curl` 이 없음 (news 프로젝트에서 동일 이슈 확인됨) |
| `/api/health`(liveness) 사용 | **외부 API 를 호출하지 않는 경로** — 헬스체크가 쿼터를 소모하면 안 됨 (ND-14) |
| `start_period 20s` | 기동 시 마이그레이션 + 고아 job 정리 시간 확보 |

### 6.2 로깅 (Q14=A, SEC-14)

| 채널 | 구성 | 목적 |
|---|---|---|
| **파일 (주)** | `/app/logs/app.jsonl`, 일 단위 로테이션, **90일 보존** (L8) | SEC-14 장기 보존 |
| **Docker 드라이버 (보조)** | `json-file`, `max-size=10m`, `max-file=3` | `docker logs` 실시간 확인, 디스크 폭주 방지 |

로그에 인증 정보·좌표 원문·요청 본문 전체는 기록하지 않습니다 (SEC-03, C2 마스킹 필터).

---

## 7. 공유 인프라 — 완전 격리 (Q15=A)

**`construction/shared-infrastructure.md` 를 생성하지 않습니다.** 기존 프로젝트와 6축 전부 분리되기 때문입니다.

| 축 | trip | news (가동 중) | miniproject (중지) | 충돌 |
|---|---|---|---|---|
| 파일 경로 | `c:\...\IDE\trip\` | `c:\...\IDE\260731_AI-DLC_news\news\` | `c:\...\IDE\260729…\miniproject\` | ✅ 없음 |
| Compose 프로젝트명 | `trip` | `news` | `miniproject` | ✅ 없음 |
| 네트워크 | `trip_default` | `news_default` | `miniproject_default` | ✅ 없음 |
| **포트** | **8200** (+ 개발 5273) | 8100 | 3000 / 8000 / 5432 | ✅ **실측 확인** |
| 볼륨 | `./data`, `./logs` (trip 하위) | news 하위 | miniproject 하위 | ✅ 없음 |
| 이미지명 | `trip-app` | `news-app` | `miniproject-*` | ✅ 없음 |

→ **동시 기동 가능.** Build & Test 에서 `news-app` 과 동시 가동을 실측 확인합니다.

---

## 8. 안드로이드 빌드 컨테이너 (Q16=A, UD-13)

`android/Dockerfile.build` 를 **단독 파일로 제공**하고 Compose 에는 넣지 않습니다.

| 항목 | 내용 |
|---|---|
| 베이스 | JDK 17 (Temurin 계열) + Android SDK cmdline-tools |
| 빌드 명령 | `./gradlew assembleDebug` |
| 산출물 추출 | 컨테이너에서 호스트로 `app-debug.apk` 복사 |
| 실행 시점 | **Build & Test 에서 1회** |
| Compose 미포함 이유 | `docker compose up` 시 수 GB 이미지를 받는 사태 방지 |
| 실패 시 | 정적 검토 판정으로 되돌리고 **원인을 Build & Test 보고서에 명시** (CON-6 개정 조건) |

⚠️ 이 빌드는 **컴파일·패키징까지만** 검증합니다. WebView 로딩·인텐트 실행·위치 권한은 실기기 확인이 필요합니다.

---

## 9. 공급망 보안 (SEC-10 — blocking 해소)

| 요건 | 구현 | 결정 |
|---|---|---|
| 의존성 버전 고정 | `requirements.txt` 정확한 버전 + `package-lock.json` 커밋 | UD-3, SEC-10 |
| **`latest` 태그 금지** | 베이스 이미지에 버전 태그 + 다이제스트 | Q2=A, **ID-20** |
| 취약점 스캐너 | `scripts/audit-deps.sh` — `pip-audit` + `npm audit` | Q17=A |
| SBOM | `scripts/generate-sbom.py` — `pip freeze` + `npm ls --json` → CycloneDX 지향 JSON | Q18=A |
| 미사용 의존성 제거 | Code Generation 에서 실제 import 대조 | SEC-10 |
| 신뢰 레지스트리 | PyPI / npm 공식만 사용 | SEC-10 |

**⚠️ 미결 (ID-20)**: 다이제스트 값은 실제 pull 후에만 알 수 있어 지금은 `# DIGEST-PENDING` 플레이스홀더입니다. **Build & Test 에서 실측값으로 교체**하며, 교체 전까지 SEC-10 은 "부분 충족"입니다.

---

## 10. 환경변수 파일 구성 (Q14 UD, NFR-15)

`.env.example` 를 `trip/` 루트에 두고 실제 `.env` 는 `.gitignore` 에 등록합니다 (UD-14).

```
# ===== 인증 정보 (비우면 해당 API 만 목 모드) =====
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
NCP_CLIENT_ID=
NCP_CLIENT_SECRET=
NCP_MAP_CLIENT_KEY=        # 프론트에 전달됨 — 도메인 화이트리스트 필수 (CON-3)
ANTHROPIC_API_KEY=

# ===== 배포 =====
BIND_HOST=127.0.0.1        # 안드로이드 실기기 연동 시에만 0.0.0.0 (경고 로그 발생)
PORT=8200
TZ=Asia/Seoul

# ===== 나머지 40여 개 =====
# nfr-design/logical-components.md §5 참조 — 전부 기본값 보유
```

**설정 원칙**: 인증 정보 6개를 제외한 모든 항목이 **기본값을 가집니다.** `.env` 없이도 목 모드로 기동됩니다 (FR-33).

---

## 11. 이월 항목 해소 확인

| ID | 이월 내용 | 해소 |
|---|---|---|
| **NFR-9** | 재현 가능 빌드 | §2 멀티스테이지 + §9 버전·다이제스트 고정 (ID-20 미결 1건) |
| **NFR-11** | 볼륨 보존 | §4.1 바인드 마운트 |
| **NFR-13** | 포트 8200 | §7 **실측 확인** (충돌 0건) |
| **NFR-14** | `BIND_HOST` | §3.1~3.3 Compose 매핑 통제 + 경고 로그 |
| **SEC-07** | 네트워크 구성 | §3.3 기본 루프백 + 위험 고지 + §1.2 비루트·읽기전용 |
| **SEC-10** | 공급망 | §9 (다이제스트만 미결 — ID-20) |

**미해소: 0건** (ID-20 은 Build & Test 에서 값을 채우는 실행 항목)

---

## 12. 설계 결정 (ID-1 ~ ID-20)

| ID | 결정 | 근거 |
|---|---|---|
| **ID-1** | 로컬 Docker Compose 단독. 운영 전환 요건은 문서로만 | Q1=A, OUT-9 |
| **ID-2** | 베이스 이미지 버전 태그 + 다이제스트 병기 | Q2=A, SEC-10 |
| **ID-3** | Vite dev 서버는 호스트 직접 실행 + `/api` 프록시. Compose 미포함 | Q3=A |
| **ID-4** | **uvicorn 워커 1개 고정, 환경변수 미노출** | **Q4=A, SP-5** |
| **ID-5** | 메모리 1GB / CPU 1.5 제한 | Q5=A |
| **ID-6** | 비루트 uid 10001 + 읽기 전용 루트 FS | Q6=A, SEC-09 |
| **ID-7** | 바인드 마운트 (`./data`, `./logs`) | Q7=A, UD-10 |
| **ID-8** | 백업 스크립트 제공, 자동 스케줄 없음. `Connection.backup()` 사용 | Q8=A |
| **ID-9** | WAL 파일은 볼륨에 함께 보관 + `.gitignore` | Q9=A |
| **ID-10** | 메시지 브로커 **N/A** | Q10=A, ND-2 |
| **ID-11** | 포트 매핑 `${BIND_HOST:-127.0.0.1}:8200:8200`, 컨테이너 내부는 항상 `0.0.0.0` | **Q11=A, CA-1** |
| **ID-12** | 리버스 프록시 미포함. 운영 TLS 요건만 문서화 | Q12=A, CON-5 |
| **ID-13** | 헬스체크는 Python 인터프리터로 `/api/health` 호출 (외부 API 미호출) | Q13=A, ND-14 |
| **ID-14** | 파일 로깅 주(90일) + Docker 드라이버 보조(10m×3) | Q14=A, SEC-14 |
| **ID-15** | 기존 프로젝트와 **6축 완전 격리**. `shared-infrastructure.md` 미생성 | Q15=A |
| **ID-16** | 안드로이드 빌드는 `Dockerfile.build` 단독, Compose 미포함 | Q16=A, UD-13 |
| **ID-17** | `pip-audit` + `npm audit` 스크립트 제공, Build & Test 에서 실행 | Q17=A, SEC-10 |
| **ID-18** | SBOM 생성 스크립트 제공, Build & Test 에서 1회 생성 | Q18=A, SEC-10 |
| **ID-19** | ⚠️ **파생** — `PYTHONDONTWRITEBYTECODE=1` + 빌드 시 `compileall` + `/tmp` tmpfs | 읽기 전용 FS × Python 충돌 해소 |
| **ID-20** | ⚠️ **파생** — 다이제스트는 `# DIGEST-PENDING` 플레이스홀더로 두고 **Build & Test 에서 실측 교체** | 다이제스트를 사전에 알 수 없음 |

---

## 13. Compliance 요약 — Infrastructure Design (u1)

### Security Compliance

| Rule | 판정 | 근거 |
|---|---|---|
| SEC-01 | ✅ | 외부 호출 TLS(RP-1). 로컬 루프백 예외는 CA-4 문서화. SQLite 는 볼륨 파일 권한 |
| SEC-02 | ⚪ N/A | LB·API GW·CDN 없음 |
| SEC-03 | ✅ | §6.2 파일 로깅 + 마스킹 |
| SEC-04 | ✅ | NFR Design SEP-1 (본 스테이지 변경 없음) |
| SEC-05 | ✅ | NFR Design SEP-4 |
| SEC-06 | ⚪ N/A | IAM 리소스 없음 |
| SEC-07 | ✅ | §3.3 기본 루프백 + 경고 + 위험 고지, §1.2 비루트·읽기 전용 FS, 불필요 포트 미개방 |
| SEC-08 | ✅ | NFR Design SEP-2·SEP-5 |
| SEC-09 | ✅ | §1.2 비루트·읽기 전용, 샘플 페이지 미배포, 에러 일반화(BR-58), 지원 버전 사용 |
| SEC-10 | ⚠️ **부분** | §9 — 락파일·`latest` 금지·스캐너·SBOM 전부 설계됨. **다이제스트 값만 미결(ID-20)** → Build & Test 에서 완결 |
| SEC-11 | ✅ | NFR Design RP·SP 군 + §5(브로커 미도입으로 공격면 축소) |
| SEC-12 | ✅ | §10 `.env` + `.gitignore`, 하드코딩 없음 |
| SEC-13 | ✅ | NFR Design SEP-4·SEP-6 |
| SEC-14 | ✅ | §6.2 90일 보존 |
| SEC-15 | ✅ | NFR Design RP-5 |

**Blocking security findings: 0건** ✅
**⚠️ SEC-10 은 "부분 충족"** — 설계는 완료되었고 다이제스트 실측만 남았습니다. **Build & Test 에서 값을 채우지 못하면 그때 blocking finding 으로 승격**됩니다.

### PBT Compliance
인프라 설계는 순수 함수를 다루지 않습니다. PBT-08(셰링킹·시드)은 Code Generation 소관.
**Blocking PBT findings: 0건** ✅

### Resiliency
확장 없음(사용자 opt-out). 컨테이너 `restart: unless-stopped` + 헬스체크로 기본 복구성 확보.
