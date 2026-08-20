# Infrastructure Design Plan — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Infrastructure Design (Unit 1/3, u1 전용)
**Created**: 2026-08-13T06:15:00Z
**입력**: `functional-design/` 3종, `nfr-design/` 2종 (L1~L8, ND-1~ND-18, 설정 47개)
**Status**: ⛔ 답변 대기 중

---

## 🔎 환경 실측 결과 (2026-08-13, 본 스테이지 사전 조사)

### 기존 컨테이너 현황

| 컨테이너 | 상태 | 포트 |
|---|---|---|
| `news-app` | **Up 7시간 (healthy)** | `127.0.0.1:8100 → 8000` |
| `miniproject-backend-1` | Exited (9일 전) | `0.0.0.0:8000 → 8000` |
| `miniproject-frontend-1` | Exited (9일 전) | `0.0.0.0:3000 → 3000` |
| `miniproject-database-1` | Exited (9일 전) | `0.0.0.0:5432 → 5432` |

### 포트 가용성

| 포트 | 상태 | 판정 |
|---|---|---|
| 8000 / 3000 / 5432 | miniproject 점유 이력 (중지 중이나 재기동 가능) | **회피** |
| 8100 | **news-app 가동 중** | **회피** |
| **8200** | 사용 이력·리스닝 없음 | ✅ **사용 가능** |
| **5273** | 사용 이력·리스닝 없음 | ✅ **사용 가능** (개발 서버) |

→ NFR-13(포트 8200)이 실측으로 확인되었습니다. **다른 프로젝트와의 충돌 0건.**

---

## 📌 답변 방법

`[Answer]:` 태그 뒤에 알파벳을 적어주세요. **"완료"** 또는 **"전부 추천안"** 이라고 알려주시면 산출물을 생성합니다.

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [ ] L1~L8 논리 컴포넌트 중 인프라 자원이 필요한 것 식별
- [ ] 설정 47개를 환경변수 목록으로 확정
- [ ] SEC-07 / SEC-10 (Infrastructure Design 이월 2건) 해소 방안 확정
- [ ] NFR-9 / NFR-11 / NFR-13 / NFR-14 (이월 4건) 해소 방안 확정
- [ ] 기존 프로젝트(news, miniproject)와의 격리 6축 검증

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [ ] Q1~Q3 배포 환경
- [ ] Q4~Q6 컴퓨트
- [ ] Q7~Q9 스토리지
- [ ] Q10 메시징
- [ ] Q11~Q12 네트워킹
- [ ] Q13~Q14 모니터링
- [ ] Q15~Q16 공유 인프라 및 격리
- [ ] Q17~Q18 공급망 보안 (SEC-10)

### 1.3 필수 산출물 생성
- [ ] `construction/u1-trip-backend/infrastructure-design/infrastructure-design.md`
- [ ] `construction/u1-trip-backend/infrastructure-design/deployment-architecture.md`
- [ ] (공유 인프라 문서는 Q15 결과에 따라 결정)

### 1.4 검증
- [ ] 이월 NFR 4건 · SEC 2건 전부 해소
- [ ] 기존 프로젝트와 6축(파일/프로젝트명/네트워크/포트/볼륨/이미지) 격리 확인
- [ ] Security Compliance / PBT Compliance 요약

---

## Part 2. 설계 질문

### 🌍 배포 환경

## Question 1
**배포 대상**을 확정합니다. (Q20=A 로 로컬 Docker Compose 확정됨)

A) ⭐ **로컬 Docker Compose 단독** — 클라우드 배포는 범위 제외(OUT-9). 다만 **운영 전환 시 필요한 사항(TLS 종단, `BIND_HOST`, 시크릿 관리)을 문서로 남김**

B) 로컬 + 클라우드 IaC(Terraform/CDK) 산출물까지 생성

C) 로컬 직접 실행만 (Docker 없이)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
**베이스 이미지 고정 방식**은? (SEC-10 — `latest` 금지)

A) ⭐ **버전 태그 + 다이제스트 병기** — `python:3.12-slim@sha256:...` 형태로 고정하고, 다이제스트는 최초 빌드 시 실측값으로 채움. 갱신 시 다이제스트를 의도적으로 교체
　→ SEC-10 의 "`latest` 미사용 + 검증된 베이스" 요건을 가장 확실히 충족

B) 버전 태그만 (`python:3.12-slim`) — 간단하나 태그가 이동하면 재현성 저하

C) 다이제스트만

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
개발 시 **Vite dev 서버**를 어떻게 띄웁니까? (UD-8 — 운영은 FastAPI 가 정적 자산 서빙)

A) ⭐ **호스트에서 직접 실행 + `/api` 프록시** — `npm run dev` 로 `5273` 에 띄우고 Vite 프록시가 `/api` 를 `8200` 으로 전달. Compose 에는 dev 서비스를 넣지 않음
　→ 개발용 컨테이너를 추가하지 않아 Compose 가 운영 구성 그대로 유지됩니다

B) Compose 에 dev 프로파일 서비스 추가

C) 개발도 매번 이미지 빌드

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 💻 컴퓨트

## Question 4
**uvicorn 워커 수**는? (SP-5 — 단일 프로세스 전제)

A) ⭐ **워커 1개 고정** — 인메모리 서킷·레이트 리밋·job 세마포어가 프로세스 내 상태이므로(SP-5) **워커를 늘리면 이 통제들이 깨집니다.** 설정으로 노출하지 않고 1로 고정하며, 그 이유를 문서와 주석에 명시

B) CPU 코어 수만큼 (⚠️ SP-5 의 상태 공유 전제 위반)

C) 환경변수로 조정 가능하게 (⚠️ 잘못 늘릴 여지)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
**컨테이너 리소스 제한**을 둡니까?

A) ⭐ **메모리 1GB / CPU 1.5 제한** [설정] — Playwright 같은 무거운 의존성이 없어 넉넉합니다. 제한을 두면 폭주 시 호스트 전체가 영향받는 것을 막습니다

B) 제한 없음

C) 더 타이트하게 (512MB)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
**컨테이너 사용자와 파일시스템** 정책은? (SEC-09)

A) ⭐ **비루트 사용자(uid 10001) + 볼륨 외 읽기 전용 루트 파일시스템** — `data`·`logs` 볼륨과 `/tmp` 만 쓰기 가능. 애플리케이션 코드 영역은 읽기 전용
　→ 침해 시 코드 변조를 막습니다

B) 비루트 사용자만 (읽기 전용 루트 미적용)

C) 기본 루트 사용자

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 💾 스토리지

## Question 7
**볼륨 방식**은? (UD-10 — `trip/data`, `trip/logs`)

A) ⭐ **바인드 마운트** (`./data:/app/data`, `./logs:/app/logs`) — 호스트에서 SQLite 파일과 로그를 바로 열어볼 수 있어 개발·디버깅에 유리. news 프로젝트도 같은 방식

B) named volume — 격리는 좋으나 파일 접근이 번거로움

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8
**DB 백업**을 어떻게 합니까?

A) ⭐ **백업 스크립트 제공 + 수동 실행** — `sqlite3 .backup` 기반 스크립트를 제공하되 자동 스케줄은 걸지 않음. 바인드 마운트라 `data/` 폴더 복사로도 충분함을 문서화
　→ 개인 로컬 사용에 맞는 최소 구성

B) 자동 일일 백업 태스크 추가 (L8 스케줄러에 통합)

C) 백업 없음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
**WAL 파일**(`-wal`, `-shm`)을 어떻게 다룹니까? (SP-1)

A) ⭐ **볼륨에 함께 보관 + `.gitignore` 등록** — WAL 파일이 DB 파일과 같은 디렉터리에 있어야 정상 동작합니다. 백업 시에는 `.backup` 명령을 써서 일관된 스냅샷을 얻도록 안내

B) 별도 경로 지정

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 📬 메시징

## Question 10
**메시지 큐·브로커**를 도입합니까? (ND-2 — 프로세스 내 asyncio 태스크로 결정됨)

A) ⭐ **도입하지 않음 — 명시적 N/A** — job 큐는 SQLite `JobRepository` + 프로세스 내 세마포어로 충족됩니다(ND-2, ND-3). Redis·RabbitMQ 등 추가 컨테이너 없음
　→ 이 결정의 한계(다중 인스턴스 불가)는 SP-5 에 이미 문서화됨

B) Redis 도입 (job 큐 + 레이트 리밋 상태 공유)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🌐 네트워킹

## Question 11
**포트 매핑과 `BIND_HOST` 전환**을 어떻게 구성합니까? (CA-1, NFR-14 — 안드로이드 연동의 핵심)

A) ⭐ **Compose 포트 매핑을 환경변수로** — `"${BIND_HOST:-127.0.0.1}:8200:8200"` 형태. 컨테이너 내부는 항상 `0.0.0.0`, **외부 노출 범위는 Compose 매핑이 결정**. 기본은 루프백이고 안드로이드 실기기 연동 시에만 `.env` 에서 `BIND_HOST=0.0.0.0` 으로 전환
　→ 애플리케이션 코드 변경 없이 노출 범위를 바꿀 수 있고, 기본값이 안전합니다

B) 애플리케이션이 직접 `BIND_HOST` 로 바인딩 (컨테이너 내부 바인딩과 외부 노출이 뒤섞임)

C) 항상 `0.0.0.0` 노출 (⚠️ SEC-07 위반)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 12
**리버스 프록시(Nginx/Caddy)** 를 구성에 포함합니까?

A) ⭐ **포함하지 않음** — UD-8 로 단일 컨테이너가 API 와 정적 자산을 모두 서빙하므로 프록시가 할 일이 없습니다. **운영 배포 시 TLS 종단용으로 필요하다는 사실만 문서에 남김**(CON-5)

B) Caddy 를 포함해 로컬에서도 HTTPS 사용 (자체 서명 인증서 신뢰 문제, 안드로이드 WebView 에서 추가 설정 필요)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 📊 모니터링

## Question 13
**Docker 헬스체크**를 어떻게 구성합니까? (ND-14 — 2단계 헬스체크)

A) ⭐ **`/api/health`(liveness)를 Python 인터프리터로 호출** — `curl` 이 slim 이미지에 없으므로 `python -c "urllib.request..."` 사용. interval 30s / timeout 5s / retries 3 / start_period 20s
　→ 외부 API 를 호출하지 않는 경로라 쿼터를 소모하지 않습니다

B) `/api/health/ready`(readiness)를 헬스체크로 사용 (DB 접근 포함, 부하 약간 증가)

C) 헬스체크 없음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**컨테이너 로그**를 어떻게 다룹니까? (SEC-14 — 90일 보존)

A) ⭐ **파일 로깅(볼륨) 주 + Docker 로그 드라이버 보조** — 애플리케이션이 `/app/logs` 에 JSON 로그를 쓰고 90일 로테이션(L8). Docker 로그 드라이버는 `json-file` 에 `max-size=10m, max-file=3` 으로 제한해 디스크 폭주 방지
　→ 장기 보존은 볼륨이, 실시간 확인은 `docker logs` 가 담당

B) Docker 로그 드라이버만 사용 (90일 보존 요건 충족 어려움)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔗 공유 인프라·격리

## Question 15
기존 프로젝트(`news-app` 가동 중, `miniproject` 중지)와 **인프라를 공유**합니까?

A) ⭐ **완전 격리 — 공유 인프라 문서 미생성** — 전용 Compose 프로젝트명(`trip`), 전용 네트워크, 전용 볼륨, 전용 포트(8200), 전용 이미지명(`trip-app`). 기존 프로젝트와 6축 전부 분리
　→ 서로의 기동·중지가 영향을 주지 않습니다

B) 공용 네트워크를 만들어 프로젝트 간 통신 가능하게

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 16
**안드로이드 빌드 컨테이너**(UD-13)를 어떻게 구성합니까?

A) ⭐ **`android/Dockerfile.build` 단독 + Compose 미포함** — 앱 실행과 무관한 일회성 빌드이므로 `docker build` 로 직접 실행하고, 산출된 APK 를 컨테이너에서 호스트로 복사. Compose 서비스로 넣지 않음
　→ `docker compose up` 이 수 GB 이미지를 받는 사태를 방지

B) Compose 에 `profiles: [build]` 로 추가

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔐 공급망 보안 (SEC-10 — blocking)

## Question 17
**의존성 취약점 스캔**을 어떻게 구성합니까? (SEC-10)

A) ⭐ **스크립트 + 문서 제공, 실행은 Build & Test 에서 시도** — `pip-audit`(Python)·`npm audit`(Node)를 실행하는 스크립트를 제공하고, Build & Test 에서 실행해 결과를 보고. 네트워크 접근이 필요하므로 실패 시 그 사실을 명시
　→ SEC-10 의 "스캐너가 CI/CD 에 포함되거나 빌드 지침에 문서화" 요건 충족

B) CI 설정 파일에만 포함 (실행 안 함)

C) 스캔 미구성 (⚠️ SEC-10 위반 — blocking)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 18
**SBOM(Software Bill of Materials)** 을 생성합니까? (SEC-10)

A) ⭐ **생성 스크립트 제공 + Build & Test 에서 1회 생성** — `pip freeze` + `npm ls --json` 기반의 단순 SBOM(CycloneDX 형식 지향)을 산출물로 남김. 외부 도구 설치가 필요하면 대체 형식으로 진행하고 그 사실을 명시

B) 락파일(`requirements.txt`, `package-lock.json`)로 갈음하고 SBOM 미생성 (⚠️ SEC-10 의 SBOM 항목 미충족)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

**"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.
`construction/u1-trip-backend/infrastructure-design/` 산출물을 생성하고 승인을 요청합니다.

> ⚠️ **Q4 를 특히 확인해 주세요.** uvicorn 워커를 1개로 **고정**하는 결정입니다.
> NFR Design 의 SP-5 대로 서킷 브레이커·레이트 리밋·job 세마포어가 전부 프로세스 내 상태이므로,
> 워커를 늘리면 **이 통제들이 조용히 깨집니다**(각 워커가 따로 셈). 설정으로 노출조차 하지 않는 편이 안전합니다.
