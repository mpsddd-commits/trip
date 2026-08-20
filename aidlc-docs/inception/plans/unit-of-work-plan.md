# Unit of Work Plan — trip

**Stage**: 🔵 INCEPTION - Units Generation (Part 1: Planning)
**Created**: 2026-08-13T04:50:00Z
**Prior context**: `requirements.md`, `execution-plan.md`, `application-design/` 5종 (컴포넌트 56종, DD-1~DD-25)
**Status**: ⛔ 답변 대기 중

---

## 📌 답변 방법

각 질문의 `[Answer]:` 태그 뒤에 알파벳을 적어주세요. 맞는 선택지가 없으면 `X` 를 고르고 직접 설명해 주세요.
작성 후 **"완료"** 또는 **"전부 추천안"** 이라고 알려주시면 Part 2(Generation)로 진행합니다.

---

## 🔎 환경 재실측 결과 (2026-08-13) — Q13·Q6 의 근거

이전 스테이지에서 "JDK·Android SDK 없음"만 확인했는데, 이번에 추가로 확인한 결과입니다.

| 항목 | 결과 | 의미 |
|---|---|---|
| **Docker** | ✅ **29.6.2, 데몬 실행 중** | 컨테이너 기반 빌드 가능 |
| **Docker Compose** | ✅ v5.3.1 | 다중 컨테이너 구성 가능 |
| Node.js / npm | ✅ v24.18.0 / 11.16.0 | u2 로컬 빌드 가능 |
| **Python** | ⚠️ **3.14.6** | 최신 버전이라 일부 패키지에 사전 빌드 휠이 없을 수 있음 → 컨테이너는 3.12 고정 권장 |
| JDK / Android SDK | ❌ 미설치 | 로컬 직접 빌드 불가 — **단 Docker 로 우회 가능** |

> 🔴 **CON-6/ASM-4 재검토 필요**: Docker 가 동작하므로 **Android SDK 컨테이너 이미지로 APK 빌드를 실측할 수 있습니다.**
> 이전 스테이지에서 "검증 불가"로 확정했던 항목이 선택지가 되었습니다. → **Q13**

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [x] `application-design/` 컴포넌트 56종을 유닛별로 배정 검증
- [x] 유닛 간 계약 3종(OpenAPI / 브리지 메시지 / BASE_URL↔BIND_HOST) 명세화
- [x] FR 34건의 유닛 귀속 확인 (User Stories SKIP → **FR 기준 매핑**)
- [x] SEC 15건·PBT-R 8건의 유닛 귀속 확인

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [x] Q1~Q2 스토리(FR) 그룹핑 방식 확정
- [x] Q3~Q5 유닛 간 의존·통신·계약 검증 방식 확정
- [x] Q6~Q7 팀 정렬 및 개발 순서 확정
- [x] Q8~Q10 기술·배포 고려사항 확정
- [x] Q11 비즈니스 도메인 경계 확정
- [x] Q12~Q14 코드 조직화 전략 확정 (Greenfield 다중 유닛)

### 1.3 필수 산출물 생성
- [x] `inception/application-design/unit-of-work.md` — 유닛 정의·책임·컴포넌트 배정·**코드 조직화 전략(Greenfield 필수)**
- [x] `inception/application-design/unit-of-work-dependency.md` — 유닛 의존성 매트릭스·계약·개발 순서
- [x] `inception/application-design/unit-of-work-story-map.md` — **FR → 유닛 매핑**(User Stories SKIP 대체)

### 1.4 검증
- [x] 유닛 경계와 의존성 유효성 확인 (순환 0건)
- [x] 컴포넌트 56종 전부 정확히 1개 유닛에 배정 (중복·누락 0건)
- [x] FR 34건 전부 유닛에 배정 (미배정 0건)
- [x] 각 유닛이 독립적으로 Functional Design 가능한 상태인지 확인
- [x] **Security Compliance** 요약
- [x] **PBT Compliance** 요약

---

## Part 2. 분해 질문

### 📦 스토리(FR) 그룹핑

## Question 1
User Stories 스테이지를 SKIP 했으므로 `unit-of-work-story-map.md` 에 매핑할 "스토리"가 없습니다. 무엇을 매핑 단위로 삼습니까?

A) ⭐ **FR(기능 요구사항) 34건을 매핑 단위로 사용** — `requirements.md` 의 FR-1~FR-34 를 유닛에 배정. 추적성이 요구사항 문서와 직결됨

B) **FR 을 사용자 여정 단위로 재군집화**한 뒤 매핑 (일정 만들기 / 일정 다듬기 / 현장에서 쓰기 등)

C) 이 시점에 User Stories 를 뒤늦게 생성해서 매핑

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
**FR 을 유닛에 배정하는 기준**은 무엇입니까? 다수 FR 이 여러 유닛에 걸쳐 있습니다(예: FR-23 딥링크는 u2·u3 양쪽).

A) ⭐ **주 담당 유닛 1개 + 참여 유닛 표기** — 각 FR 에 "Owner" 유닛 하나를 지정하고 관여하는 유닛을 부가 표기. 책임 소재가 명확해 Functional Design 범위가 흐려지지 않음

B) **관여하는 모든 유닛에 동등 배정** — 중복 허용

C) **FR 을 유닛 경계에 맞게 쪼갬** — FR-23 을 FR-23a(웹) / FR-23b(앱)로 분할 (요구사항 문서 변경 필요)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔗 유닛 간 의존과 통신

## Question 3
**u1 ↔ u2 API 계약**의 불일치를 어느 시점에 잡습니까? (DD-10: OpenAPI → TS 타입 생성)

A) ⭐ **빌드 시 타입 생성 + 타입 검사** — `npm run gen:api` 로 백엔드 OpenAPI 에서 TS 타입을 생성하고, `tsc` 가 불일치를 컴파일 오류로 검출. 생성된 타입 파일은 저장소에 커밋(오프라인 빌드 가능)

B) **런타임 계약 테스트 추가** — A + 백엔드 응답을 실제로 검증하는 통합 테스트 (⚠️ Q22=A 의 "네트워크 비의존" 방침과 충돌)

C) **수동 동기화** — 스키마 변경 시 사람이 맞춤

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
**u2 ↔ u3 브리지 메시지 계약**(`openMap` / `share` / `requestLocation`)을 어떻게 동기화합니까?

A) ⭐ **단일 정의 파일 + 양쪽 복제, 계약 문서를 단일 진실 공급원으로** — `unit-of-work-dependency.md` 에 페이로드 스키마를 확정하고, TS 와 Kotlin 각각에 상수·데이터 클래스를 두되 **변경 시 문서를 먼저 고치는 규율**을 명문화

B) **JSON Schema 파일에서 양쪽 코드 생성** (Kotlin 생성기 도입 필요 — 도구 부담)

C) 문자열 리터럴을 각자 사용 (오타 위험)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
u3 는 u2 를 **WebView 로 로드**하므로 코드 의존이 아니라 **런타임 URL 의존**입니다. 이를 어떻게 다룹니까?

A) ⭐ **런타임 의존으로 명시하고 계약을 URL + 브리지 2가지로 한정** — u3 는 u2 의 소스·빌드 산출물을 전혀 참조하지 않음. 이 경계 덕분에 u2 를 재배포해도 APK 재빌드가 불필요

B) **u2 빌드 산출물을 APK 에 번들** — 오프라인 완결성은 좋아지나 웹 갱신마다 앱 재배포 필요

C) 하이브리드 — 초기 화면만 번들, 나머지는 원격

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 👥 팀 정렬 및 개발 순서

## Question 6
**개발·설계 진행 순서**를 어떻게 합니까? (execution-plan §2 는 Sequential u1 → u2 → u3 로 계획)

A) ⭐ **엄격 순차 u1 → u2 → u3** — 각 유닛의 Functional Design → Code Generation 을 끝내고 다음으로. 계약이 확정된 상태에서 다음 유닛이 시작되어 재작업이 없음

B) **u1 완료 후 u2·u3 병렬** — u3 의 껍데기(A1·A2·A7)는 브리지 계약만 있으면 시작 가능

C) 세 유닛 Functional Design 을 먼저 모두 마친 뒤 Code Generation 3회

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
**유닛별 승인 게이트 빈도**는? (현재 계획상 Functional Design 3회 + Code Generation 3회 = 최소 6회 게이트)

A) ⭐ **계획대로 유닛마다 게이트** — 유닛 완료 시점마다 검토·중단·수정 가능

B) **u2·u3 는 묶어서 1회 게이트** — 프론트엔드 계열을 한 번에 검토 (게이트 2회 감소, 되돌림 비용 증가)

C) **전 유닛 완료 후 1회 게이트** — 최소 개입 (⚠️ 중간 방향 수정 불가)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### ⚙️ 기술·배포 고려사항

## Question 8
**u1 과 u2 의 배포 형태**는? (Q20=A 로 Docker Compose 확정)

A) ⭐ **단일 컨테이너 — FastAPI 가 빌드된 프론트 정적 자산을 서빙** — 이미지 1개, 포트 1개(8200), CORS 문제 없음, 안드로�드 WebView 도 같은 오리진. 개발 시에는 Vite dev 서버(5273)를 별도로 띄우고 프록시

B) **컨테이너 2개** — 백엔드(8200) + Nginx 정적 서빙(8201). 역할 분리는 명확하나 CORS·오리진 설정이 늘고 안드로이드 BASE_URL 이 이원화

C) 프론트는 컨테이너 없이 정적 호스팅

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
⚠️ **로컬 Python 이 3.14.6** 입니다. 최신 버전이라 일부 패키지(특히 네이티브 확장)에 사전 빌드 휠이 없을 수 있습니다.

A) ⭐ **컨테이너 런타임을 `python:3.12-slim` 으로 고정하고, 로컬 실행도 컨테이너 기준을 권장** — 재현성 확보(NFR-9). 로컬 3.14 직접 실행은 "지원하지만 보증하지 않음"으로 문서화

B) **로컬 3.14 를 기준으로 맞춤** — 컨테이너도 3.14 사용 (⚠️ 패키지 호환성 위험)

C) 3.11 등 더 보수적인 버전으로 고정

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
**u1 의 SQLite 파일과 로그**를 유닛 경계 관점에서 어디에 둡니까?

A) ⭐ **u1 소유 볼륨** — `trip/data/`, `trip/logs/` 를 Compose 볼륨으로 마운트. u2·u3 는 접근하지 않음 (NFR-11)

B) 유닛 디렉터리 내부 — `trip/backend/data/`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🏢 비즈니스 도메인 경계

## Question 11
현재 유닛 분해는 **실행 환경 기준**(백엔드/웹/안드로이드)입니다. 도메인 기준으로 더 쪼갤 필요가 있습니까? (예: 추천 기능을 별도 서비스로)

A) ⭐ **현행 3유닛 유지** — 단일 사용자·로컬 배포·계정 없음(Q16=A) 환경에서 도메인 분할은 배포·운영 복잡도만 늘리고 이득이 없음. 도메인 경계는 **u1 내부 패키지 수준**에서 이미 표현됨

B) **추천·콘텐츠 도메인을 u4 로 분리** — 외부 API 의존이 몰려 있어 독립 배포 시 장애 격리 이점

C) **AI 생성 파이프라인을 u4 로 분리** — LLM 비용·지연이 다른 기능과 성격이 다름

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 📁 코드 조직화 전략 (Greenfield 다중 유닛 — 필수 결정)

## Question 12
**디렉터리 구조**를 어떻게 합니까? (`code-generation.md` 의 greenfield multi-unit 패턴은 `{unit-name}/src/`)

A) ⭐ **역할 이름 사용** — `trip/backend/` · `trip/web/` · `trip/android/`
　→ 문서상 유닛 ID(`u1-trip-backend`)는 유지하되 디렉터리는 읽기 쉬운 이름 사용. 실무 관행에 부합

B) **유닛 ID 그대로 사용** — `trip/u1-trip-backend/` · `trip/u2-trip-web/` · `trip/u3-trip-android/`
　→ 문서-코드 대응이 기계적으로 명확하나 경로가 길고 낯섦

C) **모노리스 패턴** — `trip/src/backend/` · `trip/src/web/`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13
🔴 **Docker 가 동작하므로 안드로이드 APK 를 컨테이너에서 빌드·검증할 수 있습니다.** 이전 스테이지에서 "검증 불가"(CON-6/ASM-4)로 확정했던 항목을 재결정합니다.

A) ⭐ **Gradle 빌드용 Dockerfile 을 산출물로 제공하되, 실제 빌드 실행은 Build & Test 에서 시도** — Android SDK 컨테이너 이미지(수 GB)를 내려받아 `assembleDebug` 를 실행합니다. **성공하면 CON-6 이 해소되고 SC-7 이 실측 판정**이 됩니다. 실패·시간 초과 시 정적 검토로 되돌리고 그 사실을 보고서에 명시
　→ 비용: 이미지 다운로드 수 GB + 최초 빌드 수 분. 이득: u3 컴파일 오류를 실제로 잡을 수 있음

B) **현행 유지 — 정적 검토만** — Dockerfile 도 만들지 않음. 시간·용량 절약

C) **Dockerfile 은 제공하되 실행하지 않음** — 사용자가 원할 때 직접 실행

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**공유 루트 파일**(`docker-compose.yml`, `.env.example`, 최상위 `README.md`)을 어디에 둡니까?

A) ⭐ **`trip/` 루트에 배치** — Compose 가 u1·u2 를 함께 다루므로 루트가 자연스러움. `.env` 도 루트 1개로 통합해 환경변수 관리 지점을 단일화

B) 각 유닛 디렉터리에 분산 배치

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

**"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.
답변의 모호성·모순을 분석한 뒤(규칙 Step 7~8), 승인을 받고 **Part 2(Generation)** 에서 산출물 3종을 생성합니다.

> ⚠️ **Q13 은 특히 검토해 주세요.** 이전에 "안드로이드는 검증할 수 없다"고 보고드렸는데, Docker 확인 결과 우회 경로가 있습니다.
> 다만 이미지 다운로드에 수 GB, 최초 빌드에 수 분이 걸립니다. 비용을 감수할 가치가 있는지는 사용자 판단 사항입니다.
