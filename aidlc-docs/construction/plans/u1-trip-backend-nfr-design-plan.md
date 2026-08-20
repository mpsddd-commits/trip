# NFR Design Plan — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - NFR Design (Unit 1/3, u1 전용)
**Created**: 2026-08-13T05:45:00Z
**Status**: ⛔ 답변 대기 중

> **입력 출처 안내**: NFR Requirements 스테이지는 실행 계획대로 **SKIP** 되었습니다(기술 스택·NFR·SEC 가 Requirements Analysis 에서 확정됨).
> 따라서 본 스테이지는 `nfr-requirements/` 대신 다음을 입력으로 사용합니다:
> - `requirements.md` §7 **NFR-1 ~ NFR-15**
> - `requirements.md` §8 **SEC-01 ~ SEC-15** (Security Baseline **blocking**)
> - `functional-design/business-rules.md` **BR-47 ~ BR-51**(외부 호출·캐시·쿼터·레이트 리밋), **BR-58**(오류 문구)

---

## 📌 답변 방법

`[Answer]:` 태그 뒤에 알파벳을 적어주세요. 작성 후 **"완료"** 또는 **"전부 추천안"** 이라고 알려주시면 산출물 2종을 생성합니다.

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [ ] NFR-1~15 를 패턴 적용 대상으로 분류
- [ ] SEC-01~15 중 u1 주 책임 13건의 **구현 지점(논리 컴포넌트)** 확정
- [ ] BR-47~51 의 런타임 동작을 패턴으로 표현
- [ ] Application Design 의 C1~C33 중 NFR 담당 컴포넌트 식별

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [ ] Q1~Q4 복원력 패턴
- [ ] Q5~Q7 확장성·동시성 패턴
- [ ] Q8~Q10 성능 패턴
- [ ] Q11~Q14 보안 패턴
- [ ] Q15~Q16 논리 컴포넌트 구성

### 1.3 필수 산출물 생성
- [ ] `construction/u1-trip-backend/nfr-design/nfr-design-patterns.md` — 적용 패턴 · NFR/SEC 매핑 · 동작 규격
- [ ] `construction/u1-trip-backend/nfr-design/logical-components.md` — 논리 컴포넌트 · 배치 · 미들웨어 순서 · 설정 목록

### 1.4 검증
- [ ] NFR 15건 전부 패턴 또는 명시적 N/A 로 처리
- [ ] **SEC 15건 전부 구현 지점 확정** (blocking 확장)
- [ ] Security Compliance / PBT Compliance 요약

---

## Part 2. 설계 질문

### 🛡️ 복원력 패턴

## Question 1
외부 API 4종에 **서킷 브레이커**를 도입합니까? (현재 BR-47 은 재시도·타임아웃만 규정)

A) ⭐ **경량 서킷 브레이커 도입** — API 별로 연속 실패 5회 시 60초 open, 이후 half-open 1회 시도 [설정]. open 상태에서는 **호출하지 않고 즉시 폴백**(근사 계산·빈 결과·목 데이터)
　→ 네이버·NCP 장애 시 매 요청이 10초 타임아웃을 기다리는 것을 막습니다. AI 생성 파이프라인이 15개 항목 × 10초 = 150초 지연되는 상황을 회피

B) **재시도·타임아웃만 유지** — 서킷 없음 (구현 단순, 장애 시 지연 누적)

C) 서킷 + 벌크헤드(API 별 동시 호출 수 제한)까지

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
AI 생성 백그라운드 작업을 **어떤 방식으로 실행**합니까? (Q5=A 비동기 job, C28)

A) ⭐ **`asyncio` 태스크 + 프로세스 내 실행** — FastAPI 이벤트 루프에서 실행하고 job 상태를 SQLite 에 기록. **기동 시 `running` 상태로 남은 job 을 `failed` 로 정리**(고아 작업 방지)
　→ 단일 컨테이너(UD-8)에 맞는 최소 구성. 별도 워커·브로커 불필요

B) **별도 워커 프로세스 + 큐** (Celery/RQ + Redis) — 확장성은 좋으나 컨테이너·의존성 추가 (UD-8 단일 컨테이너 방침과 충돌)

C) `ThreadPoolExecutor` 사용

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
**동시 실행 job 수**를 제한합니까?

A) ⭐ **전역 동시 3개로 제한** [설정 `MAX_CONCURRENT_JOBS=3`]. 초과 요청은 `queued` 상태로 대기시키고 순차 처리. 대기 중에도 `job_id` 는 즉시 반환
　→ 단일 사용자 환경에서 3개면 충분하고, 외부 API 동시 부하도 억제됩니다

B) 제한 없음 (레이트 리밋 BR-49 로만 통제)

C) 전역 1개 (완전 직렬)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
**부분 실패한 job 의 재시도**를 지원합니까?

A) ⭐ **재시도 API 미제공 — 사용자가 다시 생성 요청** — `partial` 상태의 결과는 이미 저장되어 있고, 미해결 장소는 직접 검색해 담을 수 있습니다(BR-18). 재시도 상태 관리를 추가하지 않음

B) 실패 단계부터 이어서 재시도하는 API 제공 (중간 상태 영속화 필요, 복잡도 증가)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 📈 확장성·동시성 패턴

## Question 5
**SQLite 동시성**을 어떻게 다룹니까? (백그라운드 job 이 쓰는 동안 API 요청이 읽습니다)

A) ⭐ **WAL 모드 + `busy_timeout` 5초 + 쓰기 직렬화** — WAL 로 읽기·쓰기 동시성을 확보하고, 애플리케이션 수준에서 쓰기 트랜잭션을 짧게 유지. `synchronous=NORMAL`
　→ SQLite 의 `database is locked` 오류를 실무적으로 회피하는 표준 구성

B) 기본 저널 모드 유지 (쓰기 중 읽기 차단)

C) PostgreSQL 로 변경 (Q17=A 결정 번복)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
외부 HTTP 호출을 **동기/비동기** 중 무엇으로 합니까?

A) ⭐ **`httpx.AsyncClient` 비동기 + 커넥션 풀 재사용** — 그라운딩 15건을 **제한된 동시성(동시 3~5)으로 병렬 호출**해 파이프라인 시간을 크게 단축. 커넥션 풀은 앱 수명 동안 재사용
　→ 순차 호출 시 15건 × 평균 0.5초 = 7.5초가 2~3초로 줄어듭니다 (NFR-1)

B) **동기 `httpx.Client` 순차 호출** — 구현 단순, 파이프라인 지연 증가

C) 비동기 + 무제한 병렬 (⚠️ 외부 API 에 순간 부하, 레이트 리밋 유발 위험)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
**레이트 리밋 상태**를 어디에 저장합니까? (BR-49)

A) ⭐ **인메모리(프로세스 내) + 전역 일일 카운터만 SQLite** — IP 단위 슬라이딩 윈도는 메모리에(재시작 시 초기화 허용), **전역 일일 상한은 SQLite 에 영속화**(재시작으로 우회되면 비용 통제가 무의미)
　→ 단일 프로세스 배포(UD-8)에서 정확하고, 비용에 직결되는 부분만 영속화

B) 전부 SQLite (매 요청 DB 접근)

C) 전부 인메모리 (⚠️ 재시작으로 일일 상한 우회 가능)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### ⚡ 성능 패턴

## Question 8
**정적 자산 서빙**의 캐시 정책은? (UD-8 — FastAPI 가 `web/dist` 서빙)

A) ⭐ **해시 파일명 자산은 `immutable, max-age=31536000`, `index.html` 은 `no-cache`** — Vite 가 파일명에 해시를 넣으므로 안전하게 영구 캐시할 수 있고, 진입점만 매번 검증
　→ 재배포 시 갱신 문제 없이 반복 방문이 빨라집니다 (NFR-12)

B) 전부 `no-cache`

C) 전부 장기 캐시 (⚠️ 배포 후 갱신 안 됨)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
**응답 압축**을 적용합니까?

A) ⭐ **gzip 압축 (1KB 초과 응답)** — 경로 좌표열(`path`)과 정적 자산이 큽니다. 표준 미들웨어로 적용

B) 압축 없음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
**성능 목표(NFR-1)의 측정 방법**은?

A) ⭐ **요청별 처리시간을 구조화 로그에 기록 + 임계 초과 시 WARN** — `correlation_id` · 경로 · 상태코드 · 소요시간(ms) · 외부 호출 횟수를 로그에 남기고, P95 목표(500ms) 초과 시 경고. 별도 메트릭 백엔드는 도입하지 않음
　→ 로컬 단일 배포에 맞는 최소 구성 (SEC-14 축소 적용과 정합)

B) Prometheus 메트릭 엔드포인트 추가 (수집기 없이는 활용도 낮음)

C) 측정하지 않음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔒 보안 패턴

## Question 11
**CSP(Content-Security-Policy)** 를 어떻게 구성합니까? (SEC-04 — 네이버 지도 SDK 가 외부 스크립트를 로드합니다)

A) ⭐ **명시적 허용목록** — `default-src 'self'`; `script-src 'self' https://oapi.map.naver.com`; `img-src 'self' data: https:`(지도 타일·검색 이미지); `connect-src 'self' https://*.map.naver.com`; `style-src 'self' 'unsafe-inline'`(지도 SDK 가 인라인 스타일을 주입) — **`unsafe-inline` 은 style 에만 허용하고 사유를 문서화**, `script-src` 에는 절대 허용하지 않음
　→ SEC-04 검증 기준("`unsafe-inline`/`unsafe-eval` 은 문서화된 사유 필요")을 충족

B) `default-src 'self'` 만 (⚠️ 지도 SDK 로딩 실패)

C) CSP 미적용 (⚠️ SEC-04 위반 — blocking)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

> ⚠️ 실제 허용 도메인은 **Build & Test 에서 지도 SDK 로딩 실측으로 확정**합니다. 위 목록은 설계 기준선입니다.

## Question 12
**CORS 정책**은? (UD-8 로 웹·API 가 같은 오리진이 되었습니다)

A) ⭐ **기본은 CORS 비활성(동일 오리진), 개발 모드에서만 Vite dev 서버 오리진 허용** [설정 `CORS_ALLOW_ORIGINS`] — 와일드카드 금지, 개발용 오리진은 명시적 목록으로만
　→ SEC-08 의 "와일드카드 금지" 요건을 구조적으로 만족

B) 항상 `http://localhost:*` 허용

C) `*` 허용 (⚠️ SEC-08 위반)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13
**인증 정보 관리** 방식은? (SEC-12 — 하드코딩 금지)

A) ⭐ **환경변수 + `.env` 파일(git 제외) + `.env.example` 템플릿** — 기동 시 필수 항목 검증, **누락 시 목 모드로 자동 전환**(FR-33)하고 어떤 API 가 목 모드인지 로그·`/health` 에 표기. 값은 로그·오류 응답·`__repr__` 어디에도 노출하지 않음

B) 별도 시크릿 관리 서비스 연동 (로컬 배포에 과함)

C) 설정 파일에 평문 저장 후 파일 권한으로만 보호

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**헬스체크의 깊이**는? (FR-34)

A) ⭐ **2단계** — `/api/health`(liveness): 프로세스 응답만, 항상 200 · `/api/health/ready`(readiness): DB 접근 + 목 모드 현황 + 쿼터 사용량 반환. **외부 API 를 실제로 호출하지 않음**(헬스체크가 쿼터를 소모하면 안 됨)

B) 단일 엔드포인트로 통합

C) readiness 에서 외부 API 도 실제 호출해 확인 (⚠️ 쿼터 소모)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🧩 논리 컴포넌트

## Question 15
**미들웨어 실행 순서**를 어떻게 정합니까? (요청 처리 파이프라인)

A) ⭐ **바깥 → 안쪽**: `① 오류 핸들러 → ② correlation ID → ③ 접근 로깅 → ④ 보안 헤더 → ⑤ gzip → ⑥ CORS(개발 시) → ⑦ 본문 크기 제한 → ⑧ 레이트 리밋 → ⑨ 라우터(스키마 검증)`
　→ 오류 핸들러가 가장 바깥이라 **어떤 미들웨어에서 터져도 Problem Details 로 응답**되고, 레이트 리밋이 라우터 직전이라 차단된 요청은 비즈니스 로직에 닿지 않습니다

B) 프레임워크 기본 순서 사용

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 16
**정리 작업 스케줄러**(BR-60 — job·캐시·로그 정리)를 어떻게 구현합니까?

A) ⭐ **`asyncio` 주기 태스크 (앱 수명 주기에 연결)** — 기동 시 1회 실행 후 24시간마다 반복. 종료 시 정상 취소. 외부 스케줄러·cron 불필요
　→ 단일 컨테이너(UD-8)에 부합

B) APScheduler 도입

C) 별도 cron 컨테이너

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

**"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.
`construction/u1-trip-backend/nfr-design/` 산출물 2종을 생성하고 승인을 요청합니다.

> ⚠️ **Q11(CSP) 은 blocking 항목입니다.** SEC-04 는 Security Baseline 의 강제 규칙이며, 지도 SDK 를 로드하려면
> 허용목록이 필요합니다. 실제 도메인은 Build & Test 에서 실측으로 확정하되, 설계 기준선을 지금 정합니다.
