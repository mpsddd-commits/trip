# Unit of Work — trip

**Stage**: 🔵 INCEPTION - Units Generation (Part 2: Generation)
**Created**: 2026-08-13T05:00:00Z
**결정 근거**: `inception/plans/unit-of-work-plan.md` Q1~Q14 = 전부 A

---

## 1. 유닛 정의

시스템을 **3개 유닛**으로 분해합니다 (Q11=A — 현행 유지). 분해 기준은 **실행 환경 + 언어 + 빌드 산출물**입니다.

### u1-trip-backend

| 항목 | 내용 |
|---|---|
| **디렉터리** | `trip/backend/` (Q12=A) |
| **언어 / 런타임** | Python **3.12** (컨테이너 고정, Q9=A) |
| **프레임워크** | FastAPI + SQLAlchemy + pydantic-settings |
| **빌드 / 패키징** | pip + `requirements.txt` (락 고정) → Docker 이미지 |
| **테스트** | pytest + **Hypothesis** (PBT-R5) |
| **배포 산출물** | Docker 이미지 1개 — **웹 정적 자산 포함** (Q8=A) |
| **컴포넌트** | **C1 ~ C33 (33종)** |
| **FR 소유** | 15건 |
| **의존** | 없음 (최상위) |

**책임**
- REST API 제공 및 요청 검증
- SQLite 영속화 (여행·작업·캐시·쿼터·감사)
- 외부 API 통합 4종 — 네이버 지역검색 / 네이버 블로그·이미지 / NCP Directions·Geocoding / Claude
- AI 일정 생성 파이프라인과 **장소 그라운딩**
- 이동시간 산출, 순서 최적화, 타임라인 계산 (순수 도메인)
- `.ics` 내보내기, 공유 토큰 발급·폐기
- 보안 통제 대부분 (헤더·검증·레이트 리밋·감사·전역 오류)
- **빌드된 웹 정적 자산 서빙** (Q8=A)

**명시적 비책임**: 지도 렌더링, UI 상태, 딥링크 URL 생성(DD-11)

---

### u2-trip-web

| 항목 | 내용 |
|---|---|
| **디렉터리** | `trip/web/` (Q12=A) |
| **언어 / 런타임** | TypeScript / Node.js 24 (빌드 시에만) |
| **프레임워크** | React 19 + Vite + TanStack Query + Zustand |
| **빌드 / 패키징** | npm + `package-lock.json` → 정적 자산 `dist/` |
| **테스트** | Vitest + **fast-check** (PBT-R5) |
| **배포 산출물** | 정적 파일 — **u1 이미지에 복사되어 함께 배포** (Q8=A) |
| **컴포넌트** | **W1 ~ W16 (16종)** |
| **FR 소유** | 15건 |
| **의존** | u1 (OpenAPI 스키마 — **빌드 시 타입 생성**, Q3=A) |

**책임**
- 여행 생성 마법사, 진행 표시, 드래그 편집 타임라인
- 지도 렌더링·마커·폴리라인 (SDK 는 W4 어댑터에 격리)
- 장소 검색·상세·추천 화면
- **딥링크 URL 생성 단일 소유** (DD-11)
- 오프라인 캐시(IndexedDB) 및 편집 차단
- 반응형·접근성 (NFR-5, NFR-6)

**명시적 비책임**: 외부 API 직접 호출(SEC-11 — 검색·LLM 키는 백엔드 전용), 비즈니스 계산

---

### u3-trip-android

| 항목 | 내용 |
|---|---|
| **디렉터리** | `trip/android/` (Q12=A) |
| **언어 / 런타임** | Kotlin / Android |
| **빌드** | Gradle (Kotlin DSL) — **컨테이너 빌드**, Q13=A |
| **테스트** | 정적 검토 + **컨테이너 `assembleDebug` 실측 시도** |
| **배포 산출물** | APK (debug) |
| **컴포넌트** | **A1 ~ A7 (7종)** |
| **FR 소유** | 4건 |
| **의존** | u2 (**런타임 URL + 브리지 계약만**, Q5=A) |

**책임**
- WebView 호스팅 및 하드닝
- JS ↔ 네이티브 브리지 3종 (오리진 제한)
- 네이버지도 앱 인텐트 실행 및 웹 폴백
- 시스템 공유, 위치 권한
- 뒤로가기 처리, 오프라인 안내

**명시적 비책임**: 딥링크 URL 생성(받아서 실행만 함, DD-11), 비즈니스 로직, **u2 의 소스·빌드 산출물 참조**(Q5=A)

---

## 2. 컴포넌트 배정 검증

| 유닛 | 배정 컴포넌트 | 개수 |
|---|---|---|
| u1-trip-backend | C1~C5(core) · C6~C13(clients) · C14~C20(domain) · C21~C29(services) · C30~C31(storage) · C32~C33(api) | **33** |
| u2-trip-web | W1~W3(인프라) · W4~W5(지도) · W6~W12(화면) · W13~W16(공용) | **16** |
| u3-trip-android | A1~A7 | **7** |
| **합계** | | **56** |

✅ **중복 배정 0건 / 미배정 0건** — `application-design/components.md` 의 56종과 정확히 일치

---

## 3. 코드 조직화 전략 (Greenfield 다중 유닛 — 필수 항목)

`code-generation.md` 의 greenfield multi-unit 패턴을 따르되, 디렉터리 이름은 **역할 기준**을 사용합니다 (Q12=A).
문서상 유닛 ID(`u1-trip-backend`)는 유지하고, 디렉터리는 `backend/` 로 둡니다.

```
trip/
+-- aidlc-docs/                     AI-DLC 문서 (코드 금지)
|
+-- backend/                        [u1-trip-backend]
|   +-- app/
|   |   +-- api/                    C32 라우터 · C33 스키마
|   |   +-- services/               C21~C29
|   |   +-- domain/                 C14~C20  (의존성 0)
|   |   +-- clients/                C6~C13
|   |   +-- storage/                C30~C31
|   |   +-- core/                   C1~C5
|   |   +-- main.py
|   +-- tests/
|   |   +-- unit/                   예제 기반 테스트
|   |   +-- property/               Hypothesis PBT
|   |   +-- fixtures/               외부 API 목 응답
|   +-- pyproject.toml
|   +-- requirements.txt            버전 고정 (SEC-10)
|
+-- web/                            [u2-trip-web]
|   +-- src/
|   |   +-- features/
|   |   |   +-- trip-create/        W6
|   |   |   +-- generation/         W7
|   |   |   +-- timeline/           W8
|   |   |   +-- map/                W4 W5
|   |   |   +-- place/              W9 W10 W11
|   |   |   +-- share/              W12
|   |   +-- shared/
|   |   |   +-- api/                W1  (생성된 타입 포함)
|   |   |   +-- query/              W2
|   |   |   +-- store/              W3
|   |   |   +-- deeplink/           W13
|   |   |   +-- bridge/             W14
|   |   |   +-- offline/            W15
|   |   |   +-- ui/                 W16
|   |   +-- main.tsx
|   +-- tests/
|   |   +-- unit/
|   |   +-- property/               fast-check PBT
|   +-- package.json
|   +-- package-lock.json           버전 고정 (SEC-10)
|   +-- vite.config.ts
|
+-- android/                        [u3-trip-android]
|   +-- app/
|   |   +-- src/main/java/.../      A1~A7
|   |   +-- src/main/AndroidManifest.xml
|   |   +-- build.gradle.kts
|   +-- gradle/
|   +-- build.gradle.kts
|   +-- settings.gradle.kts
|   +-- gradle.properties
|   +-- Dockerfile.build            컨테이너 APK 빌드 (Q13=A)
|
+-- data/                           SQLite 볼륨 (Q10=A)
+-- logs/                           로그 볼륨 (Q10=A)
|
+-- docker-compose.yml              (Q14=A)
+-- Dockerfile                      멀티스테이지: web 빌드 -> backend 이미지
+-- .env.example                    환경변수 단일 지점 (Q14=A)
+-- .gitignore
+-- README.md
```

### 3.1 배포 구조 (Q8=A — 단일 컨테이너)

```
+---------------------------------------------------------------+
|  Docker 이미지 trip-app                                       |
|                                                               |
|  +-------------------------+  +----------------------------+  |
|  |  FastAPI (uvicorn)      |  |  /static  (web/dist 복사)  |  |
|  |  /api/*                 |  |  SPA catch-all 라우트      |  |
|  +-------------------------+  +----------------------------+  |
|                                                               |
|  포트 8200 (컨테이너 내부 0.0.0.0)                            |
+---------------------------------------------------------------+
                    |
                    |  Compose 포트 매핑  ${BIND_HOST}:8200
                    v
    기본:      127.0.0.1:8200   (로컬 브라우저 전용)
    안드로이드: 0.0.0.0:8200    (에뮬레이터 10.0.2.2 / 실기기 LAN IP)
```

**단일 오리진의 이점** (Q8=A 선택 근거)
- CORS 설정이 사실상 불필요 — SEC-08 의 오리진 화이트리스트 관리 부담 감소
- 안드로이드 `BASE_URL` 이 하나로 통일 (CA-1 해소가 단순해짐)
- 배포 산출물이 이미지 1개 — 버전 불일치가 원천적으로 발생하지 않음

**개발 시**: Vite dev 서버(`5273`)를 별도로 띄우고 `/api` 를 `8200` 으로 프록시합니다. 운영 빌드에서는 프록시가 사라집니다.

### 3.2 멀티스테이지 빌드 순서

```
[stage 1: web-build]   node:24-alpine
    web/ 복사 -> npm ci -> npm run build -> /dist
                              |
                              | (생성된 API 타입은 저장소에 커밋되어 있음 — Q3=A)
                              | -> 이 스테이지는 백엔드 실행 없이 독립 빌드 가능
                              v
[stage 2: runtime]     python:3.12-slim         <- Q9=A
    backend/ 복사 -> pip install -r requirements.txt
    stage 1 의 /dist -> /app/static 복사
    비루트 사용자로 전환 -> uvicorn 기동
```

> **Q3=A(생성 타입 커밋)의 실질적 이유가 여기 있습니다.** 타입을 커밋해 두지 않으면 web 빌드 스테이지가 백엔드를 기동해 OpenAPI 를 뽑아야 하고, 그러면 빌드가 순환 구조가 됩니다.

### 3.3 안드로이드 컨테이너 빌드 (Q13=A)

`android/Dockerfile.build` 로 Android SDK + JDK 이미지를 구성해 `./gradlew assembleDebug` 를 실행합니다.

| 항목 | 내용 |
|---|---|
| 실행 시점 | **Build & Test 스테이지** |
| 성공 시 | CON-6 해소, **SC-7 이 실측 판정**으로 승격, ASM-4 무효화 |
| 실패·시간 초과 시 | 정적 검토 판정으로 되돌리고 **그 사실과 원인을 Build & Test 보고서에 명시** |
| 예상 비용 | 이미지 다운로드 수 GB + 최초 빌드 수 분 |
| 산출물 | `app-debug.apk` (호스트로 추출) |

⚠️ 이 빌드는 **컴파일·패키징까지만** 검증합니다. 실기기·에뮬레이터에서의 동작(WebView 로딩, 네이버지도 앱 인텐트, 위치 권한)은 여전히 사용자 확인이 필요합니다.

---

## 4. 유닛별 SEC / PBT 귀속

### SEC 귀속

| Rule | u1 | u2 | u3 | 비고 |
|---|:-:|:-:|:-:|---|
| SEC-01 전송·저장 암호화 | ● | | | 루프백 예외 CA-4 |
| SEC-02 중간자 로깅 | | | | **N/A** |
| SEC-03 애플리케이션 로깅 | ● | | | |
| SEC-04 보안 헤더 | ● | ○ | | u2 는 CSP 를 위반하지 않도록 인라인 스크립트 금지 |
| SEC-05 입력 검증 | ● | ○ | | u2 는 클라이언트 측 1차 검증(보조) |
| SEC-06 IAM | | | | **N/A** |
| SEC-07 네트워크 구성 | ● | | | `BIND_HOST` |
| SEC-08 접근 제어 | ● | | ○ | u3 는 브리지 오리진 제한 |
| SEC-09 하드닝 | ● | | ● | u3 는 WebView 하드닝 |
| SEC-10 공급망 | ● | ● | ● | **세 유닛 모두 락파일·버전 고정 필수** |
| SEC-11 안전한 설계 | ● | | ○ | 레이트 리밋(u1), 브리지 최소 노출(u3) |
| SEC-12 자격증명 | ● | | | 사용자 인증은 N/A |
| SEC-13 무결성 | ● | ○ | | u2 는 외부 스크립트 SRI |
| SEC-14 알림·모니터링 | ● | | | |
| SEC-15 예외 처리 | ● | ○ | | u2 는 에러 바운더리 |

● 주 책임 / ○ 부분 책임

### PBT 귀속 (Partial 모드)

| 요구사항 | u1 | u2 | u3 |
|---|:-:|:-:|:-:|
| PBT-R1 왕복 (PBT-02) | ● C14·C20 | ● W13 인코딩 | — |
| PBT-R2 불변식 (PBT-03) | ● C15·C17·C18 | — | — |
| PBT-R3 도메인 생성기 (PBT-07) | ● | ● | — |
| PBT-R4 셰링킹·시드 (PBT-08) | ● | ● | — |
| PBT-R5 프레임워크 (PBT-09) | ● Hypothesis | ● fast-check | — |
| PBT-R6~R8 (advisory) | ● | ○ | — |

**u3 는 PBT N/A** — WebView 래퍼로 순수 계산 로직이 없습니다. `component-dependency.md` 의 설계상 딥링크 URL 생성조차 u2 소유입니다(DD-11).

---

## 5. 유닛 준비 상태 검증

| 유닛 | Functional Design 착수 가능 여부 | 선행 조건 |
|---|---|---|
| u1 | ✅ 즉시 가능 | 없음 |
| u2 | ✅ 가능 | u1 의 OpenAPI 스키마 확정 (Code Generation u1 완료 시점) |
| u3 | ✅ 가능 | u2 의 브리지 계약 확정 + 호스팅 URL |

- 각 유닛이 **독립적으로 설계·구현·테스트 가능**한 경계를 갖습니다
- 유닛 간 통신은 **명세된 계약 3종**으로만 이뤄집니다 (`unit-of-work-dependency.md` §2)
- 순환 의존 **0건**

---

## 6. Units Generation 결정 요약 (UD-1 ~ UD-14)

| ID | 결정 | 근거 |
|---|---|---|
| **UD-1** | FR 34건을 매핑 단위로 사용 (User Stories SKIP 대체) | Q1=A |
| **UD-2** | FR 마다 **Owner 유닛 1개 + 참여 유닛 표기** | Q2=A |
| **UD-3** | OpenAPI → TS 타입 **빌드 시 생성 + 저장소 커밋** | Q3=A |
| **UD-4** | 브리지 계약은 **문서를 단일 진실 공급원**으로, 코드는 양쪽 복제 | Q4=A |
| **UD-5** | u3 → u2 는 **런타임 URL 의존** (소스·빌드 산출물 미참조) | Q5=A |
| **UD-6** | 엄격 순차 진행 u1 → u2 → u3 | Q6=A |
| **UD-7** | 유닛마다 승인 게이트 유지 | Q7=A |
| **UD-8** | **단일 컨테이너** — FastAPI 가 웹 정적 자산 서빙 | Q8=A |
| **UD-9** | 컨테이너 런타임 **`python:3.12-slim` 고정** (로컬 3.14 는 비보증) | Q9=A |
| **UD-10** | 데이터·로그는 `trip/data`, `trip/logs` 볼륨 (u1 전용) | Q10=A |
| **UD-11** | 3유닛 유지 — 도메인 재분할 없음 | Q11=A |
| **UD-12** | 디렉터리는 역할 이름 `backend`/`web`/`android` | Q12=A |
| **UD-13** | **안드로이드 APK 를 컨테이너에서 빌드 시도** (Build & Test) | Q13=A → **CON-6 해소 가능** |
| **UD-14** | 공유 루트 파일(compose·env·README)은 `trip/` 루트 | Q14=A |
