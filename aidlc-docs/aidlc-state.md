# AI-DLC State Tracking — trip

## Project Information
- **Project Name**: trip — 여행 일정 생성 + 시간표 + 네이버지도 연동 경로/장소 추천 웹·안드로이드 애플리케이션
- **Project Type**: Greenfield
- **Start Date**: 2026-08-13T03:39:29Z
- **Current Phase**: ✅ **완료** (INCEPTION → CONSTRUCTION → OPERATIONS)
- **Current Stage**: **전 스테이지 완료** — 승인 게이트 12/12
- **AI-DLC Rules Version**: 1.0.1 (`c:\Users\403\IDE\.aidlc-rule-details`)

## Workspace State
- **Existing Code**: No
- **Programming Languages**: (미정 — Requirements Analysis에서 확정)
- **Build System**: (미정)
- **Project Structure**: Empty (신규 생성)
- **Reverse Engineering Needed**: No
- **Workspace Root**: `c:\Users\403\IDE\trip`

### 워크스페이스 분리 결정
상위 디렉터리 `c:\Users\403\IDE` 에는 이미 별개의 AI-DLC 프로젝트가 존재합니다
(`260731_AI-DLC_news/news` — 완료, `aidlc-docs/` 점유). 사용자 요청이 "trip이라는 폴더에 만들어주세요"
이므로 본 요청은 기존 프로젝트의 resume 이 아닌 **독립 신규 프로젝트**로 판단합니다.
따라서 워크스페이스 루트를 `c:\Users\403\IDE\trip`, 문서 루트를 `trip/aidlc-docs/` 로 둡니다.
이 결정은 Requirements Analysis Question 1 에서 사용자가 재정의할 수 있습니다.

### 로컬 개발 환경 실측 (2026-08-13)
| 항목 | 결과 | 영향 |
|---|---|---|
| Node.js | v24.18.0 ✅ | 웹/JS 스택 사용 가능 |
| npm | 11.16.0 ✅ | 동일 |
| JDK (`java`) | ❌ 미설치 | 안드로이드 로컬 직접 빌드 불가 |
| Android SDK | ❌ 미설치 (`%LOCALAPPDATA%\Android\Sdk` 없음) | 로컬 APK 빌드·에뮬레이터 검증 불가 |

### 환경 재실측 (2026-08-13, Units Generation 시점)
| 항목 | 결과 | 영향 |
|---|---|---|
| **Docker** | ✅ **29.6.2, 데몬 실행 중** | 🔴 **컨테이너로 안드로이드 APK 빌드 가능 → CON-6/ASM-4 재검토 대상 (Q13)** |
| Docker Compose | ✅ v5.3.1 | 다중 컨테이너 구성 가능 |
| **Python** | ⚠️ **3.14.6** | 최신 버전 — 일부 패키지 휠 부재 위험. 컨테이너 3.12 고정 검토 (Q9) |

→ Workspace Detection 시점에는 Docker 를 확인하지 않아 CON-6 을 "검증 불가"로 확정했습니다. 재실측 결과 **선택 가능한 사항**으로 바뀌었습니다.

### 포트 충돌 회피 참고
| 사용 중 | 프로젝트 |
|---|---|
| 8000 / 5173 | petmate (과거 프로젝트) |
| 8100 | news |
| **8200 / 5273 (제안)** | **trip** |

## Code Location Rules
- **Application Code**: `trip/` (워크스페이스 루트) — NEVER in `trip/aidlc-docs/`
- **Documentation**: `trip/aidlc-docs/` only
- **Structure patterns**: See `construction/code-generation.md` Critical Rules

## Extension Configuration
| Extension | Enabled | Enforcement Mode | Decided At |
|---|---|---|---|
| Security Baseline | **Yes** | **Blocking** (SECURITY-01~15) | Requirements Analysis (Q23=A) |
| Resiliency Baseline | **No** | — | Requirements Analysis (Q24=B) |
| Property-Based Testing | **Yes** | **Partial** — PBT-02·03·07·08·09 blocking, 나머지 advisory | Requirements Analysis (Q25=B) |

Rules loaded: `extensions/security/baseline/security-baseline.md`, `extensions/testing/property-based/property-based-testing.md`
Rules NOT loaded (opted out): `extensions/resiliency/baseline/resiliency-baseline.md`
→ 이후 **모든 스테이지 완료 시 "Security Compliance" 와 "PBT Compliance" 요약을 필수로 제시**하며, blocking finding 이 있으면 다음 스테이지로 진행하지 않습니다.

## Technology Stack (Requirements Analysis에서 확정, 2026-08-13)
| Layer | Decision | 근거 |
|---|---|---|
| Backend | Python + FastAPI | Q14=A |
| Frontend | React + TypeScript + Vite | Q15=A |
| Android | Kotlin WebView 래퍼 (`BuildConfig.BASE_URL` 주입) | Q12=A, CA-1 |
| Database | SQLite 단일 파일 (서버가 원본) | Q17=A |
| Client cache | IndexedDB (읽기 전용) | Q19=A, CA-6 |
| Map | NCP Maps — Web Dynamic Map + Directions 5 + Geocoding | Q5=A |
| Place data | 네이버 검색 API — 지역 + 블로그 + 이미지 | Q6=A, Q8=A |
| Transit routing | ⚠️ 공식 API 없음 → `nmap://` 딥링크 위임 | Q7=A, CON-1 |
| LLM | Claude API (Anthropic) | Q4=A |
| Auth | 없음 (익명 + UUIDv4 + 읽기 전용 공유 토큰) | Q16=A, CA-3 |
| Runtime | Docker Compose, `127.0.0.1:8200` (`BIND_HOST` 로 전환 가능) | Q20=A, NFR-14 |
| Test | pytest + Hypothesis / Vitest + fast-check, 네트워크 비의존 | Q22=A, Q25=B |

## 미확정 가정 (승인 게이트 확인 요망)
| ID | 가정 | 틀렸을 경우 |
|---|---|---|
| ASM-1 | NCP Maps 키 보유 | FR-33 목 데이터 모드로 흡수 — 재설계 불요 |
| ASM-2 | 네이버 검색 API 키 보유 | 동일 |
| ASM-3 | Anthropic API 키 보유 | AI 생성만 비활성, 수동 편집은 동작 |
| ~~ASM-4~~ | ~~APK 빌드는 사용자가 Android Studio 에서 수행~~ | ✅ **해소 2026-08-14** — 컨테이너에서 APK 실측 빌드 성공 (4.18MB). CON-6 도 함께 해소 |

## Stage Progress

### 🔵 INCEPTION PHASE
- [x] Workspace Detection — **완료 2026-08-13** (Greenfield, 승인 불요 정보성 단계)
- [x] Reverse Engineering — **SKIPPED** (Greenfield, 분석할 기존 코드 없음)
- [x] Requirements Analysis — **APPROVED 2026-08-13**. 답변 25건(전부 ⭐), 모순 8건 해소. 산출물: `inception/requirements/requirement-verification-questions.md`, `inception/requirements/requirements.md` (FR 34 / NFR 15 / SEC 15 / PBT-R 8 / CON 8 / OUT 10 / SC 10)
- [x] User Stories — **SKIP** (단일 페르소나, FR 34건이 이미 수용 기준 수준, 단독 개발)
- [x] Workflow Planning — **APPROVED 2026-08-13**. 산출물: `inception/plans/execution-plan.md`
- [x] Application Design — **APPROVED 2026-08-13**. 설계 질문 16건 확정(전부 A), 파생 결정 8건 도출. 산출물: `inception/plans/application-design-plan.md` + `inception/application-design/` 5종. 설계 결정 **DD-1~DD-25** 확정

## Application Design 결정 요약 (2026-08-13)
- **컴포넌트 56종**: u1 33 (core 5 / clients 8 / domain 7 / services 9 / storage 2 / api 2) · u2 16 · u3 7
- **계층 규칙**: `api → services → domain|clients|storage → core`. **`domain/` 은 의존성 0** — PBT 실행 가능성의 근거
- **주요 결정**: 계층 기준 패키지 / 외부 API Protocol+Base+개별 구현 / 목 모드는 주입 시점 분기 / AI 생성은 비동기 job+폴링 / RFC 9457 오류 / OpenAPI→TS 타입 생성 / 딥링크는 프론트 단일 소유 / 그라운딩(C23) 독립 컴포넌트 / 최적화·타임라인은 순수 함수 / 캐시는 클라이언트 데코레이터 / Query(서버)+Zustand(UI) 분리 / 지도 SDK 어댑터 격리 / 브리지 오리진 허용목록
- **파생 결정 8건**: 캐시는 실구현체만 감쌈 / Protocol 주입 2건 / JobStatus persist 제외 / 목록 API 미제공(열거 방지) / Directions 에 대중교통 메서드 미정의 / job `partial` 상태 도입 / 근거 없는 AI 요약 미노출 / 공유는 읽기 전용 타입 반환
- **검증**: 순환 의존성 **0건** / FR 미매핑 **0건** / SEC 소유자 미지정 **0건**
- **PBT 대상 7종**: C14·C15·C16·C17·C18·C20·W13
- **Functional Design 이월 11건** (최우선: C23 그라운딩 판정 기준)
- [x] Units Generation — **APPROVED 2026-08-13**. Part 1 질문 14건 확정(전부 A) + Part 2 산출물 3종 생성. 결정 **UD-1~UD-14** 확정
- ✅ **🔵 INCEPTION PHASE 완료** (실행 5 / SKIP 2)

## Units Generation 결정 요약 (2026-08-13)
| Unit | 디렉터리 | 스택 | 컴포넌트 | Owner FR |
|---|---|---|---|---|
| `u1-trip-backend` | `trip/backend/` | Python **3.12** / FastAPI | C1~C33 (33) | 15 |
| `u2-trip-web` | `trip/web/` | TypeScript / React + Vite | W1~W16 (16) | 15 |
| `u3-trip-android` | `trip/android/` | Kotlin / Gradle | A1~A7 (7) | 4 |

- **배포 (UD-8)**: **단일 컨테이너** — FastAPI 가 `web/dist` 정적 자산 서빙. 포트 8200 하나, 오리진 하나 → CORS·`BASE_URL` 이원화 문제 소멸
- **빌드 (UD-3)**: 멀티스테이지 `node:24-alpine`(web) → `python:3.12-slim`(runtime). **생성된 API 타입을 커밋해야 빌드 순환이 생기지 않음**
- **계약 3종**: ① OpenAPI→TS 타입(빌드 시 강제) ② 브리지 메시지 5종(문서가 단일 진실 공급원) ③ `BIND_HOST`↔`BuildConfig.BASE_URL`
- **🔴 UD-13**: **안드로이드 APK 를 Docker 컨테이너에서 빌드 실측 시도** → CON-6 / ASM-4 / SC-7 개정됨
- **검증**: 컴포넌트 56종 중복·누락 0건 / FR 34건 미배정·Owner 중복 0건 / 유닛 간 순환 0건
- **u3 는 PBT N/A** (순수 계산 로직 없음)

### 🟢 CONSTRUCTION PHASE
- [x] Functional Design **u1-trip-backend** — **APPROVED 2026-08-13**. 질문 19건 확정(전부 A). 산출물: `construction/plans/u1-trip-backend-functional-design-plan.md` + `construction/u1-trip-backend/functional-design/` 3종
- [x] Functional Design **u2-trip-web** — **APPROVED 2026-08-14**. 질문 18건 확정(전부 A). 산출물: 계획서 + `construction/u2-trip-web/functional-design/` **4종**

## Functional Design 결정 요약 — u2-trip-web (2026-08-14)
- **비즈니스 규칙 WBR-01 ~ WBR-42 (42건)**, **Testable Properties WP-01 ~ WP-11**
- **WBR-04**: 서버가 산출한 값(시각·이동시간·경고)을 클라이언트에서 **다시 계산하지 않음** — 두 곳에서 계산하면 반드시 어긋남
- **WBR-18 (WD-1)**: Q6(모바일 탭 전환) × FR-19(양방향 하이라이트) 충돌 → **"동시 표시"가 아니라 "상태 연속성"으로 FR-19 를 만족**시키는 해석 확정
- **WBR-06~08**: 브라우저 데이터 삭제 시 여행 접근 불가 문제 → 상시 고지 + 공유 링크 안내 + **목록 내보내기/가져오기**로 완화 (DD-21 유지)
- **WBR-22**: 추정 이동시간에 반드시 "추정" 배지 (CON-1 을 사용자에게 정직하게 노출)
- **WBR-25·29**: `partial` 을 구체적으로 알리고 "확인 필요" 패널 상시 노출
- **WBR-30**: 데모 모드는 **닫을 수 없는 배너**
- **PBT-04(멱등성)는 u2 에서 N/A 아님** — 목록 가져오기가 멱등 (WP-06)
- 🔴 **u1 개정 요청 A-1**: `GET /api/config` 추가 (엔드포인트 19 → 20). u2 Code Generation 시작 시 적용
- [x] Functional Design **u3-trip-android** — **APPROVED 2026-08-14**. 질문 14건 확정(전부 A). 산출물 3종. **ABR-01~43** · 교차검증 추가 검출 **AD-1·AD-2**

## Functional Design 결정 요약 — u1-trip-backend (2026-08-13)
- **엔티티 13종** (Trip / TripDay / ItineraryItem / Place / **OpeningHours(신설)** / TravelLeg / **UnresolvedCandidate** / PlaceContent / GenerationJob / ExternalCache / ApiUsage / AuditEvent + 값 객체군), 열거형 6종
- **워크플로 10종** (WF-1~WF-10), **비즈니스 규칙 BR-01~BR-60 (60건)**, **Testable Properties P-01~P-22**
- **그라운딩 판정 (BR-11)**: 유사도 ≥ 0.60 **AND** 목적지 범위 내 **AND** 카테고리 대분류 일치 — 3조건 AND
- **BR-18**: 미해결 후보는 어떤 경우에도 `ItineraryItem` 이 되지 않음 (환각 차단 최종 방어선)
- **BR-08**: `PlaceCandidate` 에 주소·좌표·전화 필드가 타입상 존재하지 않음
- **BR-28**: Directions 호출을 `O(n)` 으로 유지 (비인접 쌍은 근사, 확정 후 인접 쌍만 실호출)
- **BR-49**: 레이트 리밋 3등급 — AI 생성 IP당 5회/시간 + 전역 50회/일
- **⚠️ FR-13 축소 확정 (BR-35)**: 네이버 지역검색이 영업시간을 제공하지 않아 **사용자 입력 시에만 경고**
- **PBT-04 · PBT-06 은 N/A 확정** (근거 명시)
- [ ] NFR Requirements — **SKIP** (기술 스택·NFR·SEC·PBT 프레임워크 전부 Requirements Analysis 에서 확정)
- [x] NFR Design **u1-trip-backend** — **APPROVED 2026-08-13**. 질문 16건 확정(전부 A) + 파생 결정 2건. 산출물: `construction/plans/u1-trip-backend-nfr-design-plan.md` + `construction/u1-trip-backend/nfr-design/` 2종

## NFR Design 결정 요약 — u1-trip-backend (2026-08-13)
- **패턴 5군**: 복원력 RP-1~5 / 확장성 SP-1~5 / 성능 PP-1~5 / 보안 SEP-1~7 / 구성 LC-1~2
- **논리 컴포넌트 8종 추가** (L1 CircuitBreaker / L2 ExternalSemaphore / L3 JobRunner / L4 DbExecutor / L5 AccessLog / L6 BodySizeLimit / L7 StaticAssetHandler / L8 MaintenanceScheduler) → **u1 총 41종**
- **설계 결정 ND-1 ~ ND-18**, **설정 항목 약 47개**
- **⚠️ 파생 결정 2건 (답변 조합 충돌 해소)**:
  - **ND-17** — job 동시 3 × 호출 동시 5 = 15 동시 호출 위험 → **API 별 전역 세마포어(5)**
  - **ND-18** — asyncio × 동기 SQLite → 이벤트 루프 차단 → **DB 접근을 스레드 풀에서 실행**
- **CSP**: `unsafe-inline` 은 `style-src` 에만 (지도 SDK 인라인 스타일), 사유 문서화 → **SEC-04 충족**
- **RP-3 폴백**: Directions→근사 / 블로그·이미지→빈 목록 / 지역검색→미해결 / **ANTHROPIC 만 폴백 없음**
- **SP-4**: IP 윈도 인메모리, **전역 일일 상한은 SQLite 영속화**(재시작 우회 방지)
- **ND-14**: 헬스체크가 외부 API 를 호출하지 않음(쿼터 소모 방지)
- `domain/` 에 NFR 컴포넌트 **0개** — DD-16 유지 확인
- [x] Infrastructure Design **u1-trip-backend** — **APPROVED 2026-08-13**. 질문 18건 확정(전부 A) + 파생 결정 2건. 산출물: `construction/plans/u1-trip-backend-infrastructure-design-plan.md` + `construction/u1-trip-backend/infrastructure-design/` 2종

## Infrastructure Design 결정 요약 — u1-trip-backend (2026-08-13)
- **설계 결정 ID-1 ~ ID-20**. `shared-infrastructure.md` **미생성** (6축 완전 격리)
- **컨테이너**: `trip-app`, 비루트 uid 10001, **읽기 전용 루트 FS**, 메모리 1GB·CPU 1.5, `restart: unless-stopped`
- **🔴 ID-4**: **uvicorn 워커 1개 하드코딩, 환경변수 미노출** — 늘리면 서킷·레이트 리밋·job 세마포어가 오류 없이 무력화 (SP-5)
- **ID-11 (CA-1 해소 구현 지점)**: 포트 매핑 `"${BIND_HOST:-127.0.0.1}:8200:8200"`. 컨테이너 내부는 **항상 `0.0.0.0`**, 노출 범위는 Compose 좌측이 통제
- **빌드**: 멀티스테이지 `node:24-alpine` → `python:3.12-slim`, 예상 250~400MB
- **격리 실측**: trip(8200) / news(8100, 가동 중) / miniproject(3000·8000·5432, 중지) — 6축 전부 분리, 충돌 0건
- **⚠️ 파생 결정 2건**:
  - **ID-19** — 읽기전용 FS × Python `.pyc` 충돌 → `PYTHONDONTWRITEBYTECODE=1` + 빌드 시 `compileall` + `/tmp` tmpfs
  - **ID-20** — 다이제스트를 지금 알 수 없음 → `# DIGEST-PENDING` 후 **Build & Test I-2 에서 실측 교체**
- **⚠️ SEC-10 부분 충족**: 다이제스트 미결. **I-2 실패 시 blocking 으로 승격**
- **Build & Test 인프라 검증 I-1 ~ I-14 등록** (I-14 = 안드로이드 컨테이너 빌드 → CON-6 해소 조건)
- [ ] Code Generation **u1-trip-backend** — Part 1 **APPROVED 2026-08-13**. Part 2 **진행 중 (Step 5/19)**
  - ✅ Step 1 구조 / Step 2 core(C1~C5, L5, L6, L8) / Step 3 domain(C14~C20) / Step 4 domain 테스트(P-01~P-22) / Step 5 요약
  - 생성 파일 **33개**, `python -m compileall` **통과**
  - 🔴 **설계 정정 1건**: P-03(시각 단조 증가)은 BR-31/32 와 동시 성립 불가 → **"FIXED_TIME_CONFLICT 경고가 없는 구간에서만 단조 증가"** 로 정밀화. `domain-summary.md` §2 기록
  - 배치 조정 3건: `core/enums.py` 신설 / `EstimatorParams`·`OptimizeLimits` 도메인 내 정의 / RateLimiter 전역 카운터 Protocol 주입
  - ✅ Step 6 storage(C30·C31·L4, **12 테이블**) / Step 7 storage 테스트(14건) / Step 8 요약
  - 누적 생성 파일 **40개**, `compileall` 통과
  - 구조 검증 테스트 도입: `TripRepository` 목록 메서드 부재(BR-39) / `AuditLogRepository` 수정·삭제 메서드 부재(SEC-14)
  - 조정: `recover_orphans` 대상에 `queued` 포함 (대기 job 도 프로세스 종료 시 고아)
  - ✅ Step 9 clients(C6~C13, L1 서킷, L2 세마포어, 목 5종) / Step 10 테스트(34건) / Step 11 요약
  - 누적 생성 파일 **63개**, `compileall` 통과
  - 🔴 **설계 문서 정정 2건째**: `component-dependency.md` 매트릭스의 `clients → domain` 을 "—"에서 **"X"로 정정**. DTO 가 `Coordinate` 를 쓰면서 국내 범위 검증(BR-15)이 가장 바깥에서 걸리는 구조. 순환 0건, `domain` 은 여전히 아무것도 참조 안 함
  - 조정 2건: **`anthropic` SDK 미사용**(SDK 사용 시 서킷·세마포어·쿼터·재시도를 전부 우회 → BaseHttpClient 직접 호출, 의존성 1개 감소) / 캐시 데코레이터를 클라이언트별 래퍼 4종으로 구현
  - **좌표계 미확정을 `to_wgs84()` 단일 함수에 격리** — 범위 밖이면 예외로 즉시 노출
  - 구조 검증 테스트 2건 추가: 목 분기가 services·domain 에 없는지 / domain 이 다른 계층을 import 하지 않는지
  - ✅ Step 12 services(C21~C29, L3) / Step 13 테스트(67건) / Step 14 요약
  - 누적 생성 파일 **81개**, `compileall` 통과, 누적 테스트 **115건**
  - 🔴 **구현 중 설계 누락 발견**: 최적화로 순서가 바뀌면 `DistanceMatrix` 인덱스가 원본 기준이라 타임라인이 엉뚱한 구간을 읽음 → `_reindex()` 추가. `business-logic-model.md` WF-2 의 4→5단계 사이에 빠져 있던 세부
  - **파생 결정 CD-1**: `QuotaGate.record()` 가 async 에서 동기 호출되어 DB 직접 쓰기 시 이벤트 루프 차단(ND-18 위반) → **인메모리 증가 + 주기 플러시 + 기동 시 로드**. SP-4 목적(재시작 우회 방지)은 로드 경로로 달성
  - 조정 2건: `domain/categories.py` 신설 / `storage/mappers.py` 신설
  - ✅ Step 15 api(C32 라우터 6파일·**엔드포인트 19개**, C33 스키마, L7 정적, `main.py` 미들웨어 9단계) / Step 16 테스트(48건) / Step 17 요약
  - 누적 생성 파일 **98개**, `compileall` 통과, 누적 테스트 **163건**
  - 조정 3건: `api/deps.py` 컨테이너 신설 / 라우터 7→6파일(`routes`를 `trips`에 통합) / 레이트 리밋을 미들웨어가 아닌 **라우터 의존성**으로(등급이 라우트 정의에 붙어 누락이 드러남)
  - **OpenAPI 스키마를 검사하는 구조 테스트 2건**: 여행 목록 엔드포인트 부재(BR-39) / 공유 경로에 쓰기 메서드 부재(BR-37)
  - ✅ Step 18 배포 산출물(Dockerfile·compose·.env.example 47항목·스크립트 7·안드로이드 빌드) / Step 19 문서(README·code-summary)
  - **19/19 단계 완료. 애플리케이션 코드 114개 파일, 테스트 약 206건**
  - `compileall` exit 0 / SBOM 생성기 실행 확인 / 코드가 `aidlc-docs/` 밖에만 존재(QG-6)
  - **설계 문서 정정 3건**: P-03 불변식 / `clients→domain` 매트릭스 / 최적화 후 행렬 재기준화 누락
  - **조정 12건 · 파생 결정 1건(CD-1)** — 전부 위반 아님, `code-summary.md` §3~5 기록
  - **구조 테스트 8건** — 설계 규칙이 코드에 남아 있는지 검사(목록 API 부재·감사 추가전용·목 분기 격리·domain 의존성 0 등)
  - ⚠️ **SEC-10 부분 충족** — 다이제스트 미결(ID-20). Build & Test I-2 실패 시 blocking 승격
  - ⚠️ **`docker compose build` 는 현재 실패** — `web/`(u2) 부재. 설계대로이며 u2 생성 후 해소
- [ ] Code Generation **u2-trip-web** — **⛔ Part 1 계획 승인 대기**. 산출물: `construction/plans/u2-trip-web-code-generation-plan.md` (**15단계 / 약 85 파일**)
  - Step 1 에 **u1 개정 A-1**(`GET /api/config`) 선행 포함 — 승인된 u1 코드 변경
- [x] Code Generation **u3-trip-android** — **완료 2026-08-14**. Step 1~16 전건. 파일 33개. 컨테이너 빌드·테스트 **실측 성공** (47 passed / APK 4.18MB) → **CON-6·ASM-4 해소**
- [x] Build and Test — **완료 2026-08-14**. 단위 **360 passed** (u1 234·u2 79·u3 47) · I-1~I-14 **전건 통과** · 이미지 285MB · **실제 결함 6건 발견·수정** · 의존성 취약점 16건 해소

## Units of Work (Workflow Planning 에서 결정, Units Generation 에서 확정)
| Unit | 언어/빌드 | 책임 | 의존 |
|---|---|---|---|
| `u1-trip-backend` | Python / FastAPI + Docker | REST API, SQLite, 외부 API 클라이언트 4종, AI 생성+그라운딩, 타임라인 계산, 순서 최적화, `.ics`, 공유, 보안 미들웨어 | — |
| `u2-trip-web` | TypeScript / Vite | 지도·마커·폴리라인, 드래그 편집 타임라인, 장소 상세, 딥링크 URL, IndexedDB 캐시 | u1 |
| `u3-trip-android` | Kotlin / Gradle | WebView 래퍼, JS 브리지, 인텐트·공유·위치, 오프라인 화면 | u2 |

업데이트 전략: **Sequential** (u1 → u2 → u3). Critical path: u1 API 계약 → u2 → u3 URL.

### 🟡 OPERATIONS PHASE
- [x] Operations (PLACEHOLDER) — **완료 2026-08-14**. 룰셋상 플레이스홀더이나 향후 범위를 프로젝트에 맞게 작성. `operations/operations-guide.md` (10개 절) + **스크립트 4종 실동작 검증·수정**

## Execution Plan Summary
- **실행 스테이지**: 13개 / **SKIP**: User Stories, NFR Requirements(전 유닛), NFR Design·Infrastructure Design 의 u2·u3 분
- **승인 게이트**: 약 12회 / **예상**: 9~11 작업 세션
- **Risk Level**: **Medium-High** / **Rollback**: Easy / **Testing**: Moderate-Complex
- **최상위 위험 3건**: ① LLM 환각 장소(FR-3 그라운딩으로 차단) ② 외부 쿼터·비용 소진(레이트 리밋) ③ 안드로이드 실측 검증 불가(CON-6)
- **Quality Gates**: QG-1 ~ QG-8 (`inception/plans/execution-plan.md` §7)

## Current Status
- **Lifecycle Phase**: ✅ **완료** — INCEPTION · CONSTRUCTION · OPERATIONS
- **Current Stage**: ✅ **전 스테이지 완료** — 승인 게이트 **12/12**
- **Next Action**: 없음. 프로젝트 완료.
- **Status**: ✅ **COMPLETE**

### ✅ Operations 완료 (2026-08-14)
AI-DLC v1.0.1 의 Operations 는 **플레이스홀더**입니다 (룰셋이 "워크플로가 Build and Test 로
끝난다" 고 명시). 정해진 산출물 형식이 없으므로 룰셋이 제시한 향후 범위를 이 프로젝트에
맞게 작성했습니다.

**산출물**: `operations/operations-guide.md` (302줄, 10개 절) — 시스템 성격 · 일상 운영 ·
백업/복구 · 실 API 전환 · 비용 통제 · 유지보수 · 장애 대응 · 안드로이드 · 프로덕션 준비도 · 제약

### 🔴 Operations 가 찾아낸 결함 4건 — README 가 약속한 도구가 동작하지 않았다
| # | 결함 | 조치 |
|---|---|---|
| 1 | `build-android.*` 가 **항상 실패** — 안 쓰기로 한 `gradlew` 를 찾고, 없으면 "u3 가 생성되지 않았다"는 **틀린 메시지** | 검사 대상을 `settings.gradle.kts` 로 변경, 소스 마운트·실기기 인자 추가 |
| 2 | Git Bash 에서 도커 마운트가 **조용히 무시** → 이미지 안 옛 소스로 빌드 | `uname` 감지 + `pwd -W` 경로 변환 |
| 3 | 🔴 **모든 `.ps1` 이 Windows PowerShell 5.1 에서 파싱 실패** — UTF-8 BOM 부재로 한글 주석이 cp949 로 깨짐 | 3개 파일에 BOM 추가, `Parser::ParseFile` 로 검증 |
| 4 | PowerShell 5.1 이 네이티브 stderr 를 오류로 취급 — `docker build` 진행 로그만으로 스크립트 사망 | `ErrorActionPreference=Continue` + `$LASTEXITCODE`, 컨테이너 안에서 `2>&1` |

**검증**: 4종 전부 Bash·PowerShell 양쪽에서 실행해 APK 생성 · 취약점 0 · 백업 파일 생성 확인.

### 개선 — `audit-deps` 에 다이제스트 드리프트 점검 추가
고정한 `@sha256:` 과 현재 태그를 비교합니다. 다이제스트 고정은 재현성을 위한 것이지
"영원히 안 바꾸겠다"는 뜻이 아닙니다. 고정만 하고 갱신하지 않으면 알려진 취약점을 안고 갑니다.

### README 정정
`uvicorn app.main:app` → **`uvicorn app.main:create_app --factory`** (모듈 수준 `app` 을
제거했으므로 기존 안내로는 기동 불가였습니다) · `.env` 없이 바로 기동 명시 · 문서 표 확장.

### ✅ Build and Test 실측 (2026-08-14)
| 항목 | 결과 |
|---|---|
| 단위 테스트 | ✅ **360 passed / 0 failed** (u1 234 · u2 79 · u3 47) |
| 이미지 빌드 | ✅ `trip-app:latest` **285MB** (예상 250~400MB) |
| 통합 검증 | ✅ **I-1 ~ I-14 전건 통과** |
| 의존성 취약점 | ✅ Python **13 → 0** · npm **3 high → 0** |
| 안드로이드 APK | ✅ 4.18MB — **CON-6 · ASM-4 해소** |

### 🔴 Build and Test 가 찾아낸 실제 결함 6건 — 전부 수정·재검증
| # | 결함 | 왜 위험한가 |
|---|---|---|
| 1 | `SensitiveFilter` 가 모든 로그 인자를 `str()` 로 변환 → `%d` 로그가 TypeError | `Filter` 는 `emit()` 의 try/except **밖**이라 예외가 호출부로 튀어나간다. httpx 가 요청마다 `%d` 를 쓰므로 **전 API 500** |
| 2 | `CacheRepository.get()` naive/aware 비교 | 캐시를 **읽을 때마다** 예외. 쓰기는 성공해 증상이 늦게 드러난다 |
| 3 | `optimize()` 가 `len<=2` 에서 입력 그대로 반환 | 행렬이 **비대칭**이라 2개짜리 하루가 절대 재정렬 안 됨. **오류가 나지 않는다** — PBT 오라클만이 잡았다 |
| 4 | 영업시간 미저장 — `opening_hours_to_row()` 가 **죽은 코드** | PUT 이 200 을 주고 값은 사라진다. FR-13 무력 |
| 5 | `.env` 없이 `docker compose up` 실패 | FR-33 "자격증명 없이 목 모드" 와 정면 충돌 |
| 6 | `Bearer <토큰>` 에서 "Bearer" 만 가리고 **토큰을 남김** | SEC-03 마스킹의 구멍 |

**테스트 결함도 6건 수정** — 통과시키려 기대값만 바꾸지 않고 왜 원래 주장이 성립하지 않는지 기록.

### 🔴 의존성 업그레이드 (SEC-10 blocking)
`starlette 0.41.3 → 1.6.0` (CVE 7건, 런타임) · `fastapi 0.115.6 → 0.141.1` ·
`react-router-dom 7.1.1 → 7.18.2` (high 3 / 권고 14) · pytest·pip 갱신.
업그레이드 후 전 테스트 통과, 코드 수정 불필요.

### I-2 다이제스트 고정 → **SEC-10 완결**
node·python·temurin 3종 전부 `@sha256:` 고정.

> 🔴 **검증하지 못한 범위**: 실 API 연동(키 없음) · 지도 렌더링(NCP 키 없음) ·
> **안드로이드 앱 실동작**(기기 없음). u3 대표 실패 4종은 전부 컴파일을 통과하므로
> `android/README.md` 의 **실기기 체크리스트 8항목**이 유일한 수단이다.

### ✅ u3 Code Generation 완료 — **컨테이너 빌드·테스트 실측 성공**
| 검증 | 결과 |
|---|---|
| Kotlin 컴파일 | ✅ 오류 0건 (경고 2건 — 플랫폼 deprecation) |
| 단위 테스트 | ✅ **47 passed / 0 failed** |
| `assembleDebug` | ✅ `android/out/app-debug.apk` **4.18 MB** |
| debug/release 분리 | ✅ release `BASE_URL=""` · release 매니페스트에 `networkSecurityConfig` **없음** |

**생성 파일 33개** (Gradle 6 · 설정 3 · 매니페스트 3 · 리소스 7 · Kotlin 12 · 테스트 6 · 배포·문서 2 — 일부 중복 집계)
**ABR-01~43 전건 구현** / Owner FR 4건·참여 FR 4건 미매핑 0건

### 🔴 CON-6 · ASM-4 해소
컨테이너에서 APK 가 **실제로** 만들어졌다. Workspace Detection 시점의 "APK 빌드 검증 불가" 판단이 뒤집혔다.

### 🔴 u3 생성 중 발견 5건
| # | 발견 | 조치 |
|---|---|---|
| 1 | `bridgeReady` 를 u2 가 소비하지 않음 (`__tripBridgeReceive` 가 위치 요청 때만 설치) | 계약 유지 + 수신부 존재 가드 |
| 2 | u2 위치 타임아웃 10초와 경합 | u3 를 **8초**로 |
| 3 | AD-1 `DownloadManager` 가 앱 네트워크 정책 밖 | 시스템 브라우저 폴백 |
| 4 | **StructureTest 오탐 2건** — 매니페스트 **주석**, 로그 **문자열** | `stripXmlComments()` + 로그 문구 변경. **u2 와 같은 유형 반복** |
| 5 | `gradle-wrapper.jar` 바이너리 부재 | 컨테이너가 Gradle 배포판 직접 설치 |

> 🔴 **컨테이너 빌드 성공 ≠ 동작 보증.** 평문 차단·다운로드 무시·`window.open` 무시·위치 미회신은
> 전부 컴파일을 통과한다. `android/README.md` 의 **실기기 확인 체크리스트 8항목**이 유일한 검증 수단.

### ✅ u3 Functional Design 완료 — 답변 14/14 = A (전부 추천안)
| 산출물 | 내용 |
|---|---|
| `domain-entities.md` | u3 는 도메인 없음 명시. 빌드 설정 · 네트워크 정책 · 앱 상태 · **브리지 계약 5종** · 허용 오리진 · 권한/`<queries>` |
| `business-logic-model.md` | **WF-A1~WF-A9** · AD-1·AD-2 검출 기록 · **PBT N/A 판정 + 대체 테스트 5종** |
| `business-rules.md` | **ABR-01~ABR-43 (26개)** · FR/SEC 추적성 · **§9 실기기 확인 체크리스트 8항목** |

### 🔴 u3 사전 분석 발견 3건 — 전부 "웹에서는 되는데 앱에서만 조용히 안 되는" 문제 → **전건 해소**
| # | 문제 | 결정 |
|---|---|---|
| 1 | **Android 9+ 는 평문 HTTP 차단** → CA-1 의 `http://10.0.2.2:8200` 접속 불가, **빈 화면** | Q3=A — `network_security_config.xml` 개발 주소 한정 + **debug 소스셋 전용** (ABR-04·05) |
| 2 | **WebView 는 다운로드를 스스로 처리하지 않음** → `.ics` 버튼 **무반응**(오류도 없음) | Q5=A — `DownloadListener` + `DownloadManager` (ABR-23·24) |
| 3 | **WebView 는 `window.open` 을 기본 무시** → 딥링크 웹 폴백(FR-24) 앱에서 사망 | Q6=A — `setSupportMultipleWindows` + `onCreateWindow` → 시스템 브라우저 (ABR-22) |

### ⚠️ 답변 교차 검증에서 **추가 검출 2건** (Step 5 모순 분석)
| ID | 내용 | 해소 |
|---|---|---|
| **AD-1** | `DownloadManager` 는 **시스템 프로세스**라 앱의 `network_security_config` 가 적용되지 않는다 → 평문 다운로드가 기기별로 갈릴 수 있음 | 실패 시 **시스템 브라우저 폴백** (ABR-24) + 실기기 검증 항목 |
| **AD-2** | `evaluateJavascript` 는 **UI 스레드 전용**인데 브리지·권한 콜백은 다른 스레드일 수 있음 | 모든 회신을 `webView.post { }` 로 (ABR-30) |

> 🔴 **자동 검증 한계**: u3 의 핵심 결함은 전부 **컴파일이 통과하고 오류도 나지 않는다.**
> 컨테이너 빌드(CON-6)는 컴파일·패키징까지만 본다 → `business-rules.md` §9 체크리스트로 이관.

### ✅ u2 Code Generation 완료 (15/15) — **전 과정 실측**
| 검증 | 결과 |
|---|---|
| `npm install` | ✅ 330 패키지, `package-lock.json` (SEC-10) |
| `tsc -b --noEmit` | ✅ **오류 0건** |
| `vitest run` | ✅ **79 passed / 0 failed** (7 파일) |
| `npm run build` | ✅ 성공. **초기 번들 gzip ≈ 93.5KB** (목표 1MB 의 약 9%) |

**생성 파일 60개** (src 44 · tests 9 · 루트 7) + u1 개정
**구조 테스트 18건**이 설계 규칙(딥링크 단일 소유·지도 SDK 격리·공유 읽기 전용·폼 상한 미하드코딩 등)을 강제
**WP-01~WP-11 전건 통과** / **WBR-01~42 전건 구현** / Owner FR 15건 미매핑 0건

### 🔴 실행으로 발견한 결함 4건
| # | 결함 | 조치 |
|---|---|---|
| 1 | **PBT 가 프로토타입 오염 버그 발견** — `stepLabel("toString")` 이 빈 라벨. 반례 `"toString"` | `Map` 교체 + 같은 부류 `API_LABELS` 선제 수정 + 회귀 |
| 2 | `decodeParams` 의 `__proto__` 키 (10회 중 1회 실패) | `Object.defineProperty`. ⚠️ 원 반례 재현 못 함(정직 기록) |
| 3 | **존재하지 않는 의존성 버전** | TanStack 3종 `5.69.2` 정렬 + `@types/node` |
| 4 | **구조 테스트 오탐 4건** — 주석의 설명 문구를 코드로 오인 | `stripComments()` 도입 |

### u1 개정 2건 (승인 후 적용)
- **A-1** `GET /api/config` — 오퍼레이션 19 → **22**
- **A-2** 응답 모델 18종 + `response_model` 19곳 → **무타입 응답 17 → 0**, 스키마 15 → 41
- 부수: `main.py` **import 부작용 제거** (`uvicorn --factory`)
- 부수: `ReadOnlyTripOut` 에 `share_token` 부재 → **DD-25 가 타입으로 보장됨**

### ⚠️ 해소된 제약
~~`docker compose build` 가 `web/` 부재로 실패~~ → **`web/` 생성으로 해소.** 실제 빌드는 Build & Test 확인

### 🔴 u2 Step 1~7 — **테스트를 실제로 실행했고 결함 3건을 잡았습니다**
| 검증 | 결과 |
|---|---|
| `npm install` | ✅ 330 패키지, **`package-lock.json` 생성 → SEC-10 충족** |
| `npx tsc -b --noEmit` | ✅ **오류 0건** |
| `npx vitest run` | ✅ **52 passed / 0 failed**, **10회 연속 통과** |

| # | 결함 | 조치 |
|---|---|---|
| 1 | 🔴 **PBT 가 프로토타입 오염 버그 발견** — `stepLabel("toString")` 이 함수를 반환해 빈 라벨 표시. 반례 `"toString"` | `Map` 으로 교체 + **같은 부류 `API_LABELS` 선제 수정** + 회귀 테스트 |
| 2 | `decodeParams` 의 `__proto__` 키 — 왕복 속성이 ~10회 중 1회 실패(시드 의존) | `Object.defineProperty` 로 교체. ⚠️ 원 반례는 재현 못 함(정직 기록) |
| 3 | **존재하지 않는 의존성 버전** — `@tanstack/query-async-storage-persister@5.62.11` 부재 | TanStack 3종을 `5.69.2` 로 정렬 + `@types/node` 추가 |

**WP-01 ~ WP-11 전건 구현·통과** ✅ / u2 생성 파일 **24개**

### ✅ Step 1 완료 (개정 A-1)
`GET /api/config` 추가. **u1 을 python:3.12 컨테이너에서 실제 기동해 OpenAPI 스키마 추출 성공.**
부수 확인: `requirements.txt` 가 3.12 에서 정상 설치, 마이그레이션·목 주입·JSON 로깅 동작.

### 🔴 실기동으로 발견한 결함 3건
| # | 결함 | 상태 |
|---|---|---|
| 1 | **로컬 Python 3.14 에서 의존성 설치 불가** — `pydantic-core` 3.14 휠 부재, PyO3 최대 3.13 | ✅ 예견됨. **UD-9(컨테이너 3.12 고정) 근거가 실측 확인됨**. README 의 "3.14 비보증" 표기 정확 |
| 2 | **`main.py` import 부작용** — 모듈 수준 `app = create_app()` 이 import 만으로 DB·마이그레이션·클라이언트 풀 생성. 컨테이너 이중 생성 실측 | ✅ **수정 완료** — 모듈 수준 app 제거, `uvicorn --factory` 로 전환 (Dockerfile 갱신) |
| 3 | 🔴 **22개 중 17개 응답이 OpenAPI 에서 `object`(무타입)** — 라우터가 `-> dict` 를 반환해 스키마가 비어 있음. **생성될 TS 타입이 `unknown` 이 되어 UD-3 의 목적이 무력화됨** | ✅ **개정 A-2 적용 완료** (사용자 승인). 응답 모델 **17종** 추가 + 라우터 19곳 `response_model` 부여 → **실측: 타입 있는 응답 19 / 무타입 0** |

### ✅ Step 3 부분 완료 — 타입 계약 확립
- `web/openapi.json` — u1 실기동으로 추출 (스키마 **15종 → 41종**)
- `web/src/shared/api/generated.ts` — `openapi-typescript@7` 생성, **1,650줄 실제 타입**
- 두 파일 모두 **커밋 대상** (UD-3 — 없으면 Docker 웹 빌드가 순환)
- `ReadOnlyTripOut` 에 `share_token` 필드가 **스키마상 부재** → DD-25 가 응답 타입 수준에서 보장됨

### 📋 문서 드리프트 발견
`component-methods.md` §7 은 엔드포인트 **19개**로 기술했으나 실제 구현은 **22개 오퍼레이션**.
추가분: `/api/health/ready`, `/api/trips/{id}/items/{id}/opening-hours`, `/api/config`(A-1).
변경분: `GET /api/places/{place_id}/content` → `GET /api/places/content?trip_id=&item_id=`.
→ A-2 적용 시 문서를 함께 정정.
- **Status**: 🔄 진행 중 (게이트 없음 — 19단계 완료 후 승인 요청)
- **u1 설계 완료**: Functional(BR-01~60) + NFR(ND-1~18) + Infrastructure(ID-1~20)
- **코드 위치**: `trip/backend/` + `trip/` 루트 — **`aidlc-docs/` 에는 코드 금지**
- **미확정 5건**(코드에 격리 후 Build & Test 해소): 좌표계 / 다이제스트(SEC-10) / CSP 도메인 / 실 API 응답 / 안드로이드 빌드(CON-6)
- **Build & Test 검증 예약 6건**: CSP 실측 / 지역검색 좌표계 확정 / WAL 동시성 / 서킷 동작 / 고아 job 정리 / 정적 캐시 헤더
- **✅ 재결정 완료**: Q10=A — FR-13 을 "사용자 입력 시에만 경고"로 축소 확정 (BR-35). `requirements.md` FR-13 개정됨
- **⚠️ Build & Test 검증 예약**: 지역검색 `mapx`/`mapy` 좌표계 실측 확정 (오해석 시 지도 전 지점 어긋남) → 좌표 변환을 단일 함수에 격리
- **✅ 재결정 완료**: UD-13 — Docker 컨테이너로 안드로이드 APK 빌드 실측 시도. CON-6 / ASM-4 / SC-7 개정됨
- **Blocking Security Findings**: 0건
- **Blocking PBT Findings**: 0건
