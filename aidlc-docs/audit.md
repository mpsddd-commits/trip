# AI-DLC Audit Log — trip 프로젝트

이 파일은 trip 프로젝트(워크스페이스 루트: `c:\Users\403\IDE\trip`)의 모든 사용자 입력과 AI 응답을 기록합니다.
**중요**: 이 파일은 항상 추가(append)만 하며, 절대 전체를 덮어쓰지 않습니다.

---

## Initial User Request
**Timestamp**: 2026-08-13T03:39:29Z
**User Input**: "AI-DLC를 이용해서 여행관련 안드로이드 연동 웹/어플리케이션을 만들고 싶습니다. trip이라는 폴더에 만들어주세요. 여행일정을 짜주고 시간표제공 및 여행경로를 지도에서 보고 시간순서에 맞춰 이동경로. 위치. 장소관련 내용 추천내용(메뉴나 명소 등)을 네이버지도와 연계해서 사용할 수 있게 만들어주세요."
**AI Response**: "AI-DLC 워크플로우 시작. 환영 메시지 표시 → Workspace Detection 실행."
**Context**: INCEPTION PHASE 진입 / 신규 요청 접수

---

## Workspace Detection
**Timestamp**: 2026-08-13T03:39:29Z
**User Input**: "(N/A — 자동 실행 단계, 사용자 입력 없음)"
**AI Response**: "워크스페이스 스캔 완료. Greenfield 판정. Reverse Engineering SKIP."
**Context**: INCEPTION - Workspace Detection

**Findings**:
- 상위 워크스페이스 `c:\Users\403\IDE` 에 별개의 완료된 AI-DLC 프로젝트 `260731_AI-DLC_news/news` 존재
  (자체 `news/aidlc-docs/` 보유, OPERATIONS 완료). 본 요청은 resume 대상이 아님.
- 사용자 요청이 "trip이라는 폴더에" 이므로 **독립 신규 프로젝트**로 판단.
  워크스페이스 루트 `c:\Users\403\IDE\trip`, 문서 루트 `trip/aidlc-docs/`.
- `trip/` 폴더 신규 생성 — 기존 소스코드 0건 → **Greenfield**.
- Reverse Engineering 단계: 불필요 (SKIP).
- 이 워크스페이스 루트 결정은 Requirements Analysis Question 1 에서 사용자 확인/재정의 가능.

**로컬 환경 실측**:
- Node.js v24.18.0 ✅ / npm 11.16.0 ✅
- JDK 미설치 ❌ / Android SDK 미설치 ❌ → 안드로이드 네이티브 빌드·APK 검증 불가.
  이 제약은 Requirements Analysis Q13/Q14 에서 명시적으로 사용자 결정 필요.
- 포트 8000/5173(petmate), 8100(news) 사용 이력 → trip 은 8200/5273 제안.

**Rule Details 로딩 완료**: `.aidlc-rule-details/` v1.0.1
- `common/process-overview.md`, `common/welcome-message.md`, `common/terminology.md`,
  `common/question-format-guide.md`, `common/depth-levels.md`
- `inception/workspace-detection.md`, `inception/requirements-analysis.md`

**Extensions 스캔 완료** (opt-in 파일만 로딩, 전체 룰은 opt-in 후 지연 로딩):
- `extensions/security/baseline/security-baseline.opt-in.md`
- `extensions/resiliency/baseline/resiliency-baseline.opt-in.md`
- `extensions/testing/property-based/property-based-testing.opt-in.md`

---

## Requirements Analysis — Intent Analysis
**Timestamp**: 2026-08-13T03:39:29Z
**User Input**: "(N/A — 자동 분석)"
**AI Response**: "의도 분석 완료. Comprehensive Depth 적용 결정."
**Context**: INCEPTION - Requirements Analysis / Step 2~3

- **Request Clarity**: Incomplete — 목표 기능은 명확하나 플랫폼 형태, 데이터 소스, 인증, 배포, 외부 API 자격증명 등 다수 미정
- **Request Type**: New Project (Greenfield)
- **Initial Scope Estimate**: Cross-system (웹 프론트 + 백엔드 + 안드로이드 + 외부 API 3종 이상)
- **Initial Complexity Estimate**: Complex
- **Depth Decision**: **Comprehensive** — 다중 플랫폼, 외부 유료/쿼터 제한 API 의존, 자격증명 취급, 미설치 빌드 툴체인 존재

---

## Requirements Analysis — Questions Presented
**Timestamp**: 2026-08-13T03:39:29Z
**User Input**: "(대기 중)"
**AI Response**: "`trip/aidlc-docs/inception/requirements/requirement-verification-questions.md` 생성 (질문 25개, 확장 opt-in 3건 포함). 사용자 답변 대기 (⛔ GATE)."
**Context**: INCEPTION - Requirements Analysis / Step 6 GATE

---

## Requirements Analysis — Answers Received
**Timestamp**: 2026-08-13T03:52:00Z
**User Input**: "전부 추천안"
**AI Response**: "25개 질문 전부 ⭐ 추천안으로 확정. 모순/모호성 분석 수행 후 requirements.md 생성."
**Context**: INCEPTION - Requirements Analysis / Step 6

**확정된 답변 (⭐ 추천안 전체 적용)**:
Q1: A / Q2: A / Q3: A / Q4: A / Q5: A / Q6: A / Q7: A / Q8: A / Q9: A / Q10: A
Q11: A / Q12: A / Q13: A / Q14: A / Q15: A / Q16: A / Q17: A / Q18: A / Q19: A / Q20: A
Q21: A / Q22: A / **Q23: A** / **Q24: B** / **Q25: B**

**Extension 결정 확정**:
- Security Baseline: **Yes (Blocking)** (Q23=A) → `extensions/security/baseline/security-baseline.md` **로딩 완료**
- Resiliency Baseline: **No** (Q24=B) → `resiliency-baseline.md` 미로딩
- Property-Based Testing: **Yes — Partial** (Q25=B) → `extensions/testing/property-based/property-based-testing.md` **로딩 완료**.
  Partial 모드: PBT-02, PBT-03, PBT-07, PBT-08, PBT-09 만 blocking. 나머지는 advisory.

---

## Requirements Analysis — 모순·모호성 분석
**Timestamp**: 2026-08-13T03:52:00Z
**User Input**: "(N/A — 자동 분석)"
**AI Response**: "충돌·모호성 8건 검출. 전부 설계로 해소 가능하다고 판단하여 clarification 파일 생성 없이 requirements.md 내 §3 에 해소안 기록. 사용자는 승인 게이트에서 이견 제기 가능."
**Context**: INCEPTION - Requirements Analysis / Step 6 (Contradiction Detection)

| ID | 심각도 | 충돌 | 해소 |
|---|---|---|---|
| CA-1 | 🔴 | Q12(안드로이드 WebView) ↔ Q20(127.0.0.1 루프백) — 기기에서 호스트 루프백 접근 불가 | `BIND_HOST` 환경변수 + `BuildConfig.BASE_URL` 주입 (FR-27, NFR-14, CON-4) |
| CA-2 | 🟠 | Q16(인증 없음) ↔ SECURITY-08/12 | SECURITY-12 N/A, SECURITY-08 은 UUIDv4 + 열거 방지로 변형 적용 (SEC-08) |
| CA-3 | 🟠 | Q16(익명) ↔ Q18(공유 링크) — 사실상 Q16 D 와 동일 | 여행 ID(UUIDv4)와 읽기 전용 공유 토큰 분리 (FR-25) |
| CA-4 | 🟠 | Q20(로컬 HTTP) ↔ SECURITY-01/04(TLS·HSTS) | 문서화된 예외. 외부 API 구간은 TLS 1.2+ 완전 준수, HSTS 는 HTTPS 시에만 (SEC-01, SEC-04, CON-5) |
| CA-5 | 🟡 | Q16(인증 없음) ↔ Q4(유료 LLM) — 비용 남용 노출 | 레이트 리밋 + 일일 상한 필수 (SEC-11, NFR-4) |
| CA-6 | 🟡 | Q19(오프라인) ↔ Q17(서버 SQLite) | 서버가 원본, 클라이언트 IndexedDB 는 읽기 전용 캐시. 오프라인 편집 차단 (FR-31, FR-32, OUT-6) |
| CA-7 | 🟡 | SECURITY-02/06/07/14 ↔ 로컬 단독 배포 | SEC-02·06 N/A, SEC-07 부분, SEC-14 는 로컬 파일 로그 90일 로테이션으로 축소 |
| CA-8 | 🟡 | Q22(단위 테스트) ↔ PBT-08(CI 통합) | 시드 로깅·재현 명령 필수, CI 설정 파일은 제공하되 실행은 사용자 재량 (PBT-R4, CON-6) |

**미확정 가정 4건 기록 (ASM-1~4)**: NCP 키 / 네이버 검색 키 / Anthropic 키 보유 여부, 안드로이드 빌드는 사용자 수행.
→ ASM-1~3 은 FR-33(목 데이터 폴백 모드)로 흡수되어 가정이 틀려도 산출물 동일. ASM-4 는 CON-6·SC-7 에 명시.

---

## Requirements Analysis — Document Generated
**Timestamp**: 2026-08-13T03:52:00Z
**User Input**: "(대기 중 — 승인 게이트)"
**AI Response**: "`inception/requirements/requirements.md` 생성 완료. FR 34 / NFR 15 / SEC 15 / PBT-R 8 / CON 8 / OUT 10 / SC 10. 사용자 승인 대기."
**Context**: INCEPTION - Requirements Analysis / Step 7~9

**Security Compliance 요약 (Requirements Analysis 스테이지)**:
- 적용: SEC-03, 04, 05, 08, 09, 10, 11, 13, 14, 15
- 부분 적용(근거 문서화): SEC-01, 07, 12, 14
- N/A(해당 리소스 없음): SEC-02, SEC-06
- **Blocking security findings: 0건** — 전 항목이 요구사항 문서 §8 에 판정·근거와 함께 기록됨

**PBT Compliance 요약 (Requirements Analysis 스테이지)**:
- Partial 모드 blocking 대상 PBT-02·03·07·08·09 → 각각 PBT-R1·R2·R3·R4·R5 로 요구사항화 완료
- advisory PBT-01·05·10 → PBT-R6·R7·R8 로 기록
- PBT-04(멱등성), PBT-06(상태 기반) → 현 단계에서 해당 컴포넌트 미식별. Functional Design 에서 재평가
- **Blocking PBT findings: 0건**

---

## Requirements Analysis — Approval
**Timestamp**: 2026-08-13T04:05:00Z
**AI Prompt**: "Approve & Continue — 승인하고 Workflow Planning 으로 진행"
**User Response**: "Approve"
**Status**: **Approved**
**Context**: INCEPTION - Requirements Analysis 승인 완료. ASM-1~4 에 대한 이견 제기 없음 → 가정 그대로 확정.

---

## Workflow Planning
**Timestamp**: 2026-08-13T04:05:00Z
**User Input**: "(N/A — 승인 후 자동 진행)"
**AI Response**: "`inception/plans/execution-plan.md` 생성. 유닛 3개 분해, 실행 13 / SKIP 3 결정. 사용자 승인 대기 (⛔ GATE)."
**Context**: INCEPTION - Workflow Planning / Step 1~9

**Scope & Impact**: User-facing ✅ / Structural ✅ / Data model ✅ / API ✅ / NFR ✅ — 전 영역 신규(Greenfield)
**Risk**: Medium-High / Rollback: Easy / Testing: Moderate-Complex

**Units of Work 결정 (Sequential u1 → u2 → u3)**:
- `u1-trip-backend` (Python/FastAPI) — API·SQLite·외부 클라이언트 4종·AI 생성+그라운딩·타임라인·최적화·보안
- `u2-trip-web` (TypeScript/Vite) — 지도·타임라인 UI·딥링크·IndexedDB 캐시
- `u3-trip-android` (Kotlin/Gradle) — WebView 래퍼·JS 브리지

**스테이지 결정 및 사유**:
| 스테이지 | 결정 | 사유 |
|---|---|---|
| User Stories | **SKIP** | 단일 페르소나(계정 없음), FR 34건이 이미 수용 기준 수준, 단독 개발 |
| Application Design | **EXECUTE** | 신규 컴포넌트 전면. 책임 경계·의존 방향 미확정 시 순환 의존·중복 구현 위험 |
| Units Generation | **EXECUTE** | 언어·빌드·배포 산출물·PBT 프레임워크가 전부 다른 3개 단위 |
| Functional Design ×3 | **EXECUTE** | 그라운딩 판정 기준, 타임라인 시각 전파, 최적화 목적함수·제약, 캐시 정책 등 비즈니스 규칙 다수 |
| NFR Requirements | **SKIP** | 기술 스택·NFR 15·SEC 15·PBT 프레임워크(PBT-09) 전부 Requirements Analysis 에서 확정 완료 |
| NFR Design ×1 (u1) | **EXECUTE** | Security Baseline blocking, 통제 대부분이 백엔드(SEC-04·05·08·11·12·14·15) |
| Infrastructure Design ×1 (u1) | **EXECUTE** | Compose·볼륨·포트 8200·`BIND_HOST`(CA-1 해소 핵심)·환경변수·이미지 고정 |
| Code Generation ×3 | **EXECUTE** | ALWAYS |
| Build and Test | **EXECUTE** | ALWAYS. u1·u2 실측, u3 정적 검토만 (CON-6/ASM-4) |

**Security Compliance (Workflow Planning 스테이지)**: 본 스테이지는 계획 문서만 산출하므로 SEC-01~15 전부 **해당 없음(설계·코드 산출물 부재)**. 다만 실행 계획에 SEC 강제 지점(NFR Design, Code Generation, Build and Test)을 명시적으로 배치함. **Blocking findings: 0건**
**PBT Compliance (Workflow Planning 스테이지)**: PBT-01 적용 지점을 Functional Design ×3 에 배치, PBT-08 을 Build and Test 에 배치. **Blocking findings: 0건**
**Resiliency**: 확장 없음(사용자 opt-out) [Requirements Analysis]

---

## Workflow Planning — Approval
**Timestamp**: 2026-08-13T04:20:00Z
**AI Prompt**: "Approve & Continue — 승인하고 Application Design 으로 진행"
**User Response**: "승인하고"
**Status**: **Approved**
**Context**: INCEPTION - Workflow Planning 승인 완료. 실행 13 / SKIP 3, 유닛 3개 분해 확정. User Stories·NFR Requirements 추가 요청 없음.

---

## Application Design — Plan Presented
**Timestamp**: 2026-08-13T04:20:00Z
**User Input**: "(대기 중)"
**AI Response**: "`inception/plans/application-design-plan.md` 생성. 체크리스트 + 설계 질문 16개(컴포넌트 식별 4 / 메서드·인터페이스 4 / 서비스 계층 3 / 의존성 3 / 설계 패턴 2). 사용자 답변 대기 (⛔ GATE)."
**Context**: INCEPTION - Application Design / Step 2~7 GATE

---

## Application Design — Answers Received & Analyzed
**Timestamp**: 2026-08-13T04:35:00Z
**User Input**: "전부 추천안"
**AI Response**: "설계 질문 16개 전부 ⭐(=A) 확정. 모호성 0건, 모순 검사 4개 조합 수행 후 산출물 5종 생성."
**Context**: INCEPTION - Application Design / Step 7~10

**확정된 답변**: Q1~Q16 = 전부 **A**

**모호성 분석 (Step 8)**:
- "mix of" / "somewhere between" / "not sure" / "depends" 류 응답 **0건**
- 모순 교차 검증 4개 조합 수행:
  - Q1×Q12 (계층 패키지 × 단방향 규칙) → ✅ 상호 강화
  - Q2×Q3×Q11 (Protocol × 목 주입 × 캐시 데코레이터) → ✅ 동일 이음매 공유, 합성 순서만 확정 → DD-6
  - Q5×Q13×Q16 (job 폴링 × Query × persist) → ⚠️ 1건 검출: job 상태가 IndexedDB 에 persist 되면 재방문 시 완료된 진행률 부활 → **DD-14 로 해소**
  - Q10×Q11×Q22 (순수 도메인 × 캐시 × 네트워크 비의존 테스트) → ✅ 정합
- **추가 질문 필요 없음 (Step 9 follow-up 생성 안 함)** — 검출된 1건은 사용자 판단이 아닌 설계 결정으로 해소 가능
- **파생 결정 8건** (DD-6·7·8·14·21·22·23·24·25) 을 명시하고 승인 게이트에서 이견 확인하도록 기록

**생성 산출물 5종**:
`inception/application-design/` — `components.md` / `component-methods.md` / `services.md` / `component-dependency.md` / `application-design.md`

**설계 검증 결과**:
- 컴포넌트 **56종** (u1 33 / u2 16 / u3 7)
- **순환 의존성 0건** / **FR 미매핑 0건** (FR-1~34) / **SEC 소유자 미지정 0건**
- `domain/` 외부 의존 0건 (PBT 실행 가능성 확보)
- PBT 대상 컴포넌트 7종 식별 (C14·C15·C16·C17·C18·C20·W13)
- Functional Design 이월 **11건**

**Security Compliance (Application Design 스테이지)**:
준수 12 / 부분 1(SEC-12 사용자 인증 N/A) / N/A 2(SEC-02·06) / 이월 1(SEC-10 → Infrastructure Design)
**Blocking security findings: 0건**

**PBT Compliance (Application Design 스테이지)**:
blocking 5종 중 PBT-02·03·07 설계 완료, PBT-09 확정(Hypothesis/fast-check), PBT-08 은 Code Generation 이월
advisory: PBT-01 표기 완료, PBT-05 오라클 정의(C18 `brute_force`), PBT-04·06 후보 없음(Functional Design 재평가), PBT-10 이월
**Blocking PBT findings: 0건**

**Resiliency**: 확장 없음(사용자 opt-out)

---

## Application Design — Awaiting Approval
**Timestamp**: 2026-08-13T04:35:00Z
**User Input**: "(대기 중)"
**AI Response**: "산출물 5종 생성 완료. 사용자 승인 대기 (⛔ GATE). 승인 시 Units Generation 진행."
**Context**: INCEPTION - Application Design / Step 12~13

---

## Application Design — Approval
**Timestamp**: 2026-08-13T04:50:00Z
**AI Prompt**: "Approve & Continue — 승인하고 Units Generation 으로 진행"
**User Response**: "Approve"
**Status**: **Approved**
**Context**: INCEPTION - Application Design 승인 완료. DD-1~DD-25 확정. 파생 결정 8건에 이견 없음.

---

## Units Generation (Part 1: Planning) — 환경 재실측
**Timestamp**: 2026-08-13T04:50:00Z
**User Input**: "(N/A — 자동 실행)"
**AI Response**: "배포·빌드 관련 질문의 근거 확보를 위해 로컬 환경 재확인. **Docker 데몬 실행 중 확인 → CON-6/ASM-4 재검토 필요 판정.**"
**Context**: INCEPTION - Units Generation / Step 3 사전 조사

| 항목 | 결과 | 영향 |
|---|---|---|
| Docker | ✅ 29.6.2, 데몬 실행 중 | **안드로이드 APK 컨테이너 빌드 가능 → CON-6 해소 가능성** |
| Docker Compose | ✅ v5.3.1 | 다중 컨테이너 구성 가능 |
| Python | ⚠️ **3.14.6** | 최신 버전, 일부 패키지 휠 부재 위험 → 컨테이너 3.12 고정 검토 (Q9) |
| Node.js / npm | ✅ v24.18.0 / 11.16.0 | u2 로컬 빌드 가능 |
| JDK / Android SDK | ❌ 미설치 | 로컬 직접 빌드는 여전히 불가 |

🔴 **중요**: Workspace Detection 시점에는 Docker 를 확인하지 않아 CON-6("안드로이드 검증 불가")과 ASM-4 를 확정했습니다.
Docker 가 동작하므로 이는 **선택 가능한 사항**이 되었으며, Q13 으로 사용자에게 재결정을 요청합니다.

---

## Units Generation (Part 1: Planning) — Plan Presented
**Timestamp**: 2026-08-13T04:50:00Z
**User Input**: "(대기 중)"
**AI Response**: "`inception/plans/unit-of-work-plan.md` 생성. 체크리스트 + 분해 질문 14개(FR 그룹핑 2 / 의존·통신 3 / 팀 정렬 2 / 기술·배포 3 / 도메인 경계 1 / 코드 조직화 3). 사용자 답변 대기 (⛔ GATE)."
**Context**: INCEPTION - Units Generation / Part 1 Step 1~6 GATE

---

## Units Generation (Part 1) — Answers Received & Analyzed
**Timestamp**: 2026-08-13T05:00:00Z
**User Input**: "전부 추천안"
**AI Response**: "분해 질문 14개 전부 ⭐(=A) 확정. 모호성 0건, 모순 교차 검증 5개 조합 수행."
**Context**: INCEPTION - Units Generation / Part 1 Step 7~8

**확정된 답변**: Q1~Q14 = 전부 **A**

**모호성 분석 (Step 7)**:
- "mix of" / "somewhere between" / "not sure" / "depends" 류 응답 **0건**
- 모순 교차 검증 5개 조합:
  - Q8(단일 컨테이너) × Q12(web 별도 디렉터리) → ✅ 멀티스테이지 Dockerfile 로 해소. `web/dist` 를 backend 이미지에 복사
  - Q8(단일 오리진) × Q5(런타임 URL 의존) × CA-1 → ✅ **상호 강화**. 오리진이 하나라 `BASE_URL` 관리 지점이 단일화됨
  - Q3(타입 커밋) × Q8(멀티스테이지 빌드) → ✅ **커밋이 필수 조건임이 드러남**. 커밋 없으면 web 빌드가 백엔드 기동을 요구해 빌드 순환 발생 → `unit-of-work.md` §3.2 에 명시
  - Q13(컨테이너 안드로이드 빌드) × Q6(엄격 순차) → ✅ u3 코드 생성 후 Build & Test 시점에 실행. 순서 충돌 없음
  - Q9(python 3.12 컨테이너) × Q13(Android SDK 이미지) → ✅ 별도 이미지, 간섭 없음
- **추가 질문 필요 없음 (Step 8 follow-up 생성 안 함)**

**⚠️ 요구사항 개정 3건 (Q13=A 의 귀결)**:
| 문서 | 항목 | 개정 내용 |
|---|---|---|
| `requirements.md` | **CON-6** | "APK 빌드 불가" → **"컨테이너로 빌드 실측 시도"**. 단 기기·에뮬레이터 실행 검증은 여전히 불가 |
| `requirements.md` | **ASM-4** | "사용자가 Android Studio 에서 수행" → **"컨테이너 빌드 실측, 실행 검증만 사용자 몫"** |
| `requirements.md` | **SC-7** | 검증 단계를 Code Generation → **Build & Test 실측**으로 승격 |

근거: Workspace Detection 시점에 Docker 를 확인하지 않아 CON-6 을 과도하게 보수적으로 확정했음. Units Generation 사전 조사에서 정정.

---

## Units Generation (Part 2: Generation) — Artifacts Created
**Timestamp**: 2026-08-13T05:00:00Z
**User Input**: "(Part 1 승인은 '전부 추천안' 응답에 포함된 것으로 처리 — Step 16 게이트에서 통합 검토)"
**AI Response**: "산출물 3종 생성 완료. 유닛 결정 UD-1~UD-14 확정."
**Context**: INCEPTION - Units Generation / Part 2 Step 12~15

**생성 산출물 3종**:
`inception/application-design/` — `unit-of-work.md` / `unit-of-work-dependency.md` / `unit-of-work-story-map.md`

**유닛 확정**:
| Unit | 디렉터리 | 언어/런타임 | 컴포넌트 | Owner FR |
|---|---|---|---|---|
| u1-trip-backend | `trip/backend/` | Python 3.12 / FastAPI | C1~C33 (33) | 15 |
| u2-trip-web | `trip/web/` | TypeScript / React+Vite | W1~W16 (16) | 15 |
| u3-trip-android | `trip/android/` | Kotlin / Gradle | A1~A7 (7) | 4 |

**결정 UD-1 ~ UD-14** — 상세는 `unit-of-work.md` §6

**검증 결과**:
- 컴포넌트 56종 배정 — **중복 0건 / 누락 0건**
- FR 34건 배정 — **미배정 0건 / Owner 중복 0건**
- 유닛 간 순환 — **0건** (u2→u1 은 개발 시점, u1→u2 는 패키징 시점으로 분리)
- NFR 15 / SEC 15(N/A 2 포함) / PBT-R 8 전건 귀속
- u3 는 PBT **N/A** 판정 (순수 계산 로직 없음, 딥링크 생성조차 u2 소유 — DD-11)

**Security Compliance (Units Generation 스테이지)**:
본 스테이지는 분해 문서만 산출. SEC 15건의 **유닛 귀속을 확정**하여 이후 스테이지의 강제 지점을 명확히 함.
SEC-10(공급망)이 세 유닛 전부에 해당함을 명시. **Blocking findings: 0건**

**PBT Compliance (Units Generation 스테이지)**:
PBT-R 8건의 유닛 귀속 확정. PBT-R5(프레임워크)는 u1 Hypothesis / u2 fast-check 로 배정. u3 N/A 근거 문서화.
**Blocking findings: 0건**

**Resiliency**: 확장 없음(사용자 opt-out) [Application Design]

---

## Units Generation — Approval
**Timestamp**: 2026-08-13T05:15:00Z
**AI Prompt**: "Approve & Continue — 승인하고 🟢 CONSTRUCTION PHASE (u1-trip-backend Functional Design) 로 진입"
**User Response**: "승인하고"
**Status**: **Approved**
**Context**: INCEPTION - Units Generation 승인 완료. **🔵 INCEPTION PHASE 전체 완료** (실행 5 / SKIP 2). UD-1~UD-14 확정. CON-6/ASM-4/SC-7 개정 승인됨.

---

## 🟢 CONSTRUCTION PHASE 진입 — u1-trip-backend Functional Design
**Timestamp**: 2026-08-13T05:15:00Z
**User Input**: "(N/A — 자동 진행)"
**AI Response**: "u1 Functional Design 사전 조사 수행. **FR-13 구현 불가 사유 발견.**"
**Context**: CONSTRUCTION - Functional Design (u1) / Step 1~3

### 🔴 사전 조사 발견 사항 — FR-13 데이터 소스 부재
**네이버 지역검색 API 응답에 영업시간 필드가 없습니다.**
제공 필드: `title` / `link` / `category` / `description` / `telephone` / `address` / `roadAddress` / `mapx` / `mapy`

→ 승인된 요구사항 FR-13(영업시간 밖 배정 시 경고)을 **원래 계획대로 구현할 수 없습니다.**
→ Q10 으로 사용자 재결정 요청 (축소 / LLM 추정 / TourAPI 추가 / 범위 제외)

### ⚠️ Build & Test 검증 대상으로 기록
- 지역검색 `mapx`/`mapy` 의 **좌표계를 실응답으로 확정**해야 함. 문서만으로 단정하지 않음.
  잘못 해석하면 지도상 전 지점이 어긋남 → **좌표 변환을 단일 함수에 격리**하도록 설계 반영
- `title` 필드의 `<b>` 강조 태그는 저장 전 제거 필요 (SEC-05)

---

## Functional Design (u1-trip-backend) — Plan Presented
**Timestamp**: 2026-08-13T05:15:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u1-trip-backend-functional-design-plan.md` 생성. 체크리스트 + 설계 질문 19개(AI 파이프라인 4 / 경로·시간 5 / 장소·추천 2 / 데이터 수명 3 / 오류·보안 3 / 비용·규모 2). Application Design 이월 10건 전부 질문으로 전환. 사용자 답변 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Functional Design (u1) / Step 4~5 GATE

---

## Functional Design (u1-trip-backend) — Answers Received & Artifacts Created
**Timestamp**: 2026-08-13T05:30:00Z
**User Input**: "전부 추천안"
**AI Response**: "설계 질문 19개 전부 ⭐(=A) 확정. 모호성 0건, 모순 교차 검증 6개 조합 수행 후 산출물 3종 생성."
**Context**: CONSTRUCTION - Functional Design (u1) / Step 5~6

**확정된 답변**: Q1~Q19 = 전부 **A**

**모호성 분석 (Step 5)**:
- "depends" / "maybe" / "not sure" / "mix of" 류 응답 **0건**
- 모순 교차 검증 6개 조합:
  - Q4(LLM `preferred_time_slot` 수용) × Q5(목적함수는 총 이동시간 단독) → ⚠️ **용도 불명확 검출**. 수용은 하되 최적화에는 쓰지 않음 → **BR-21 로 용도 명문화**(초안 배치·표시 전용)
  - Q5(단독 지표) × PBT-R2("결과 ≤ 입력" 불변식) → ✅ **상호 강화**. B안이었다면 불변식이 깨져 PBT-R2 수정이 필요했음
  - Q7(고정 시각 유지 + 경고) × Q8(overflow 경고 유지) → ✅ 동일 철학("자동 수정하지 않고 표시만") → BR-34 로 일반화
  - Q1(3조건 AND) × Q18(하루 15개 상한) → ✅ 항목 수 = 지역검색 호출 수. BR-02 가 비용 상한임을 명시
  - Q6(200ms 상한) × NFR-1(P95 500ms) → ✅ 캐시된 행렬 사용 시 여유. BR-28(호출 O(n) 유지)로 보강
  - Q10(사용자 입력 영업시간) × 도메인 모델 → ⚠️ **엔티티 추가 필요 검출**. `OpeningHours`(`entered_by_user=true` 고정) 신설 → BR-35
- **추가 질문 필요 없음** — 검출된 2건은 설계 결정으로 해소

**⚠️ 요구사항 개정 1건**:
| 문서 | 항목 | 개정 |
|---|---|---|
| `requirements.md` | **FR-13** | "영업시간 정보를 확보한 장소에 대해 경고" → **"사용자가 입력한 경우에만 경고. 외부 데이터로 자동 확보하지 않음"** (Q10=A) |
근거: 네이버 지역검색 API 응답에 영업시간 필드 부재. LLM 추정은 CON-7 위반이므로 배제.

**생성 산출물 3종**:
`construction/u1-trip-backend/functional-design/` — `domain-entities.md` / `business-logic-model.md` / `business-rules.md`

**설계 결과**:
- 엔티티 **13종** (핵심 8 + 운영 4 + 값 객체군), 열거형 **6종**
- 워크플로 **10종** (WF-1 ~ WF-10) — 그라운딩(WF-3)·최적화(WF-5)·타임라인(WF-6) 알고리즘 상세화
- 비즈니스 규칙 **BR-01 ~ BR-60 (60건)**
- **Testable Properties P-01 ~ P-22 (22종)** — PBT-01 충족
- Application Design 이월 **10건 전부 해소** (+ 신규 발견 1건 해소)
- Owner FR 15건 **미매핑 0건**

**핵심 설계 결정**:
- **BR-18**: 미해결 후보는 어떤 경우에도 `ItineraryItem` 이 되지 않음 — 환각 차단 최종 방어선
- **BR-08**: `PlaceCandidate` 타입에 주소·좌표·전화 필드가 **존재하지 않음** — 실수로 수용할 경로 자체를 제거
- **BR-15**: 좌표 국내 범위 밖이면 저장 거부 — 좌표계 오해석을 조기 노출
- **BR-28**: 최적화용 비인접 거리는 근사로 채우고 확정 후 인접 쌍만 실호출 → Directions 호출 O(n) 유지
- **BR-39**: 여행 목록 API 미제공 (열거 방지)
- **BR-40**: 블로그 3건 미만이면 요약 생성 안 함

**Security Compliance (Functional Design u1)**:
준수 10 / N/A 2(SEC-02·06) / 후속 스테이지 소관 3(SEC-04·07·10) — **Blocking findings: 0건**

**PBT Compliance (Functional Design u1)**:
blocking 5종 중 PBT-02·03·07·09 충족, PBT-08 은 Code Generation 이월.
advisory: PBT-01·05·10 충족, **PBT-04·06 은 N/A 로 확정**(근거 명시 — `optimize()` 는 멱등성 미주장, job 상태 전이는 선형)
**Blocking findings: 0건**

**Resiliency**: 확장 없음(사용자 opt-out)

---

## Functional Design (u1-trip-backend) — Approval
**Timestamp**: 2026-08-13T05:45:00Z
**AI Prompt**: "Continue to Next Stage — 승인하고 NFR Design (u1) 으로 진행"
**User Response**: "승인하고"
**Status**: **Approved**
**Context**: CONSTRUCTION - Functional Design (u1) 승인 완료. BR-01~BR-60 확정. FR-13 축소 개정 승인됨. BR-11 임계값 0.60 / BR-49 레이트 리밋 / BR-02 규모 상한에 이견 없음.

---

## NFR Design (u1-trip-backend) — Plan Presented
**Timestamp**: 2026-08-13T05:45:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u1-trip-backend-nfr-design-plan.md` 생성. 체크리스트 + 설계 질문 16개(복원력 4 / 확장성·동시성 3 / 성능 3 / 보안 4 / 논리 컴포넌트 2). 사용자 답변 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - NFR Design (u1) / Step 2~5 GATE

**입력 출처 주의**: NFR Requirements 스테이지가 실행 계획대로 SKIP 되어 `nfr-requirements/` 산출물이 없습니다.
대신 `requirements.md` §7(NFR-1~15) · §8(SEC-01~15) 과 `functional-design/business-rules.md` BR-47~51·BR-58 을 입력으로 사용했습니다.

---

## NFR Design (u1-trip-backend) — Answers Received & Artifacts Created
**Timestamp**: 2026-08-13T06:00:00Z
**User Input**: "전부 추천안"
**AI Response**: "설계 질문 16개 전부 ⭐(=A) 확정. 모호성 0건, **답변 조합 충돌 2건 검출 및 해소** 후 산출물 2종 생성."
**Context**: CONSTRUCTION - NFR Design (u1) / Step 5~6

**확정된 답변**: Q1~Q16 = 전부 **A**

**모호성 분석 (Step 5)**:
- "depends" / "maybe" / "not sure" / "mix of" 류 응답 **0건**
- **⚠️ 답변 조합 충돌 2건 검출** (답변만으로는 결정되지 않는 사항):

| # | 충돌 | 해소 |
|---|---|---|
| 1 | Q3(job 동시 3) × Q6(job 내 외부 호출 동시 3~5) → **최대 15개 동시 외부 호출**. 네이버 API 순간 부하·레이트 리밋 유발 위험 | **ND-17** — API 별 **전역 세마포어(5)** 도입. job 동시성과 곱해지지 않음 |
| 2 | Q2(asyncio 태스크) × Q5(SQLite 동기 드라이버) → job 저장 중 **이벤트 루프 차단 → 동시 API 요청 전체 지연** | **ND-18** — DB 접근을 **스레드 풀에서 실행**. `async` 컨텍스트에서 동기 DB 직접 호출 금지 |

두 건 모두 사용자 판단이 아닌 논리적 귀결이므로 추가 질문 없이 설계에 반영.

**생성 산출물 2종**:
`construction/u1-trip-backend/nfr-design/` — `nfr-design-patterns.md` / `logical-components.md`

**설계 결과**:
- **패턴 5군**: 복원력 RP-1~RP-5 / 확장성 SP-1~SP-5 / 성능 PP-1~PP-5 / 보안 SEP-1~SEP-7 / 구성 LC-1~LC-2
- **논리 컴포넌트 8종 추가** (L1~L8) → u1 컴포넌트 총 **41종**
- **설계 결정 ND-1 ~ ND-18** (파생 2건 포함)
- **설정 항목 약 47개** 목록화
- 미들웨어 9단계 순서 확정 — 오류 핸들러 최외곽, 레이트 리밋 라우터 직전
- 외부 호출 파이프라인 6단계 확정 — **캐시가 최선두**(적중 시 쿼터·서킷·세마포어 미접촉)

**핵심 결정**:
- **RP-3 폴백 표**: Directions→근사 / 블로그·이미지→빈 목록 / 지역검색→미해결 / **ANTHROPIC 만 폴백 없음**(초안은 파이프라인 입력 그 자체)
- **SP-4**: IP 윈도는 인메모리 허용, **전역 일일 상한은 SQLite 영속화** — 재시작으로 비용 통제 우회 방지
- **SP-5**: 단일 프로세스 전제의 **확장 한계를 명시적으로 문서화** → SEC-11 "오남용 시나리오 고려" 요건 충족
- **ND-14**: 헬스체크가 **외부 API 를 호출하지 않음** — 헬스체크만으로 쿼터를 소모하는 것 방지
- **CSP §4.1**: `unsafe-inline` 을 **`style-src` 에만** 허용하고 사유 문서화. `script-src`·`unsafe-eval` 은 불허 (SEC-04 검증 요건)
- `domain/` 에 NFR 컴포넌트 **0개** — DD-16(의존성 0) 유지 확인

**Security Compliance (NFR Design u1)**:
준수 11 / N/A 2(SEC-02·06) / Infrastructure Design 이월 2(SEC-07·10) — **Blocking findings: 0건**
특히 **SEC-04 를 CSP 허용목록 + 예외 사유 문서화로 충족**(blocking 항목)

**PBT Compliance (NFR Design u1)**:
본 스테이지는 런타임 패턴만 다루며 순수 함수를 추가하지 않음. PBT-08 은 Code Generation 소관.
**Blocking findings: 0건**

**Resiliency**: 확장 없음(사용자 opt-out). 단 RP-1~RP-5 로 자체 반영.

**Build & Test 검증 예약 6건**: CSP 실측 / 좌표계 확정 / WAL 동시성 / 서킷 동작 / 고아 job 정리 / 정적 캐시 헤더

---

## NFR Design (u1-trip-backend) — Approval
**Timestamp**: 2026-08-13T06:15:00Z
**AI Prompt**: "Continue to Next Stage — 승인하고 Infrastructure Design (u1) 으로 진행"
**User Response**: "승인하고"
**Status**: **Approved**
**Context**: CONSTRUCTION - NFR Design (u1) 승인 완료. ND-1~ND-18 확정(파생 2건 포함). 서킷·동시성·캐시 TTL 임계값에 이견 없음.

---

## Infrastructure Design (u1-trip-backend) — 환경 실측
**Timestamp**: 2026-08-13T06:15:00Z
**User Input**: "(N/A — 자동 실행)"
**AI Response**: "포트 충돌 회피 근거 확보를 위해 컨테이너·리스닝 포트 실측."
**Context**: CONSTRUCTION - Infrastructure Design (u1) / Step 1~3 사전 조사

| 컨테이너 | 상태 | 포트 |
|---|---|---|
| `news-app` | **Up 7시간 (healthy)** | `127.0.0.1:8100 → 8000` |
| `miniproject-backend-1` | Exited (9일 전) | `0.0.0.0:8000` |
| `miniproject-frontend-1` | Exited (9일 전) | `0.0.0.0:3000` |
| `miniproject-database-1` | Exited (9일 전) | `0.0.0.0:5432` |

리스닝 포트 실측: `127.0.0.1:8100` 만 확인. **8200 / 5273 은 사용 이력·리스닝 없음** → NFR-13 실측 확인. 충돌 0건.

---

## Infrastructure Design (u1-trip-backend) — Plan Presented
**Timestamp**: 2026-08-13T06:15:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u1-trip-backend-infrastructure-design-plan.md` 생성. 체크리스트 + 설계 질문 18개(배포환경 3 / 컴퓨트 3 / 스토리지 3 / 메시징 1 / 네트워킹 2 / 모니터링 2 / 공유인프라 2 / 공급망보안 2). 사용자 답변 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Infrastructure Design (u1) / Step 4~5 GATE

**⚠️ Q4 주의 환기**: uvicorn 워커를 **1개로 고정**하는 결정. SP-5 대로 서킷·레이트 리밋·job 세마포어가 프로세스 내 상태이므로 워커를 늘리면 통제가 조용히 깨짐. 설정으로 노출하지 않는 안을 권고.

---

## Infrastructure Design (u1-trip-backend) — Answers Received & Artifacts Created
**Timestamp**: 2026-08-13T06:30:00Z
**User Input**: "전부 추천안"
**AI Response**: "설계 질문 18개 전부 ⭐(=A) 확정. 모호성 0건, **기술적 충돌 2건 검출 및 해소** 후 산출물 2종 생성."
**Context**: CONSTRUCTION - Infrastructure Design (u1) / Step 5~6

**확정된 답변**: Q1~Q18 = 전부 **A**

**모호성 분석 (Step 5)**:
- 모호 응답 **0건**
- **⚠️ 기술적 충돌 2건 검출**:

| # | 충돌 | 해소 |
|---|---|---|
| 1 | Q6(읽기 전용 루트 FS) × Python 런타임 → `__pycache__/*.pyc` 쓰기 실패로 매 import 경고·기동 지연 | **ID-19** — `PYTHONDONTWRITEBYTECODE=1` + 빌드 시 `compileall` 사전 컴파일 + `/tmp` tmpfs(64MB) |
| 2 | Q2(다이제스트 고정) × 현시점 정보 부재 → **다이제스트 값을 지금 알 수 없음.** 임의 기입은 거짓 정보 | **ID-20** — `# DIGEST-PENDING` 플레이스홀더로 두고 **Build & Test(I-2)에서 실측 교체**. 그때까지 **SEC-10 은 "부분 충족"** 으로 명시 |

**생성 산출물 2종**:
`construction/u1-trip-backend/infrastructure-design/` — `infrastructure-design.md` / `deployment-architecture.md`
**`shared-infrastructure.md` 미생성** — Q15=A(6축 완전 격리)

**설계 결과**:
- **설계 결정 ID-1 ~ ID-20** (파생 2건 포함)
- 컨테이너 명세: 비루트 uid 10001 / **읽기 전용 루트 FS** / 메모리 1GB·CPU 1.5 / **uvicorn 워커 1개 고정**
- 멀티스테이지 빌드: `node:24-alpine`(web) → `python:3.12-slim`(runtime), 예상 250~400MB
- **포트 매핑 `${BIND_HOST:-127.0.0.1}:8200:8200`** — CA-1 해소의 실제 구현 지점
- 6축 격리 검증표 작성 (trip / news / miniproject)
- 환경별 `BIND_HOST` ↔ `BASE_URL` 조합표 작성
- **Build & Test 인프라 검증 항목 I-1 ~ I-14 등록**

**핵심 결정**:
- **ID-4**: uvicorn 워커 1개를 **하드코딩하고 환경변수로 노출조차 하지 않음** — 늘리면 서킷·레이트 리밋·job 세마포어가 오류 없이 무력화됨
- **ID-11**: 컨테이너 내부는 **항상 `0.0.0.0`**, 외부 노출 범위는 **Compose 매핑 좌측**이 통제. 컨테이너 안에서 루프백 바인딩하면 포트 포워딩이 동작하지 않기 때문
- **ID-8**: 백업은 `sqlite3` CLI 부재로 Python `Connection.backup()` 사용. **`data/` 단순 복사는 WAL 트랜잭션 누락 위험**이라 비권장으로 명시
- **ID-16**: 안드로이드 빌드 이미지를 Compose 에서 제외 — `docker compose up` 이 수 GB 이미지를 받는 사태 방지
- **ID-10**: 메시지 브로커 **명시적 N/A**
- `deployment-architecture.md` §5 에 **운영 배포 선행 조건 7건**을 "빠지면 공개 배포 금지" 수준으로 기술

**이월 항목 해소**: NFR-9 / NFR-11 / NFR-13(실측) / NFR-14 / SEC-07 → **전부 해소**. SEC-10 은 다이제스트만 미결(ID-20)

**Security Compliance (Infrastructure Design u1)**:
준수 12 / N/A 2(SEC-02·06) / **부분 1(SEC-10 — 다이제스트 미결)**
**Blocking findings: 0건** — 단, **Build & Test I-2 에서 다이제스트를 채우지 못하면 SEC-10 이 blocking 으로 승격**됨을 명시

**PBT Compliance**: 인프라 설계는 순수 함수 미포함. **Blocking findings: 0건**

**Resiliency**: 확장 없음(사용자 opt-out). `restart: unless-stopped` + 헬스체크로 기본 복구성 확보.

---

## Infrastructure Design (u1-trip-backend) — Approval
**Timestamp**: 2026-08-13T06:45:00Z
**AI Prompt**: "Continue to Next Stage — 승인하고 Code Generation (u1) 으로 진행"
**User Response**: "승인하고"
**Status**: **Approved**
**Context**: CONSTRUCTION - Infrastructure Design (u1) 승인 완료. ID-1~ID-20 확정. **u1 설계 3종(Functional·NFR·Infrastructure) 전부 완료.**

---

## Code Generation Part 1 (Planning) — u1-trip-backend
**Timestamp**: 2026-08-13T06:45:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u1-trip-backend-code-generation-plan.md` 생성. **19단계 / 약 103개 파일 / 41개 컴포넌트**. 사용자 승인 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 1 Step 1~7 GATE

**코드 위치 확정**:
- 애플리케이션 코드: `c:\Users\403\IDE\trip\backend\` + `c:\Users\403\IDE\trip\` 루트(배포 산출물)
- 문서: `aidlc-docs/construction/u1-trip-backend/code/` (마크다운만)
- **`aidlc-docs/` 에 코드를 두지 않음** (code-generation.md Critical Rules)

**단계 구성 (19단계)**:
Step 1 구조 → Step 2 core → Step 3~5 domain(생성·테스트·요약) → Step 6~8 storage → Step 9~11 clients → Step 12~14 services → Step 15~17 api → Step 18 배포 산출물 → Step 19 문서

**생성 원칙 12개 명문화**: `domain/` 의존성 0, 서비스에 `if mock:` 금지, 재시도·캐시는 C6·C12 소관, 외부 응답 검증 후 수용, 오류 문구 6종 고정, 인증 정보 미노출, 파라미터 바인딩만, 버전 고정, async 에서 동기 DB 직접 호출 금지, 네트워크 비의존 테스트, PBT 셰링킹·시드, 파일 상단 컴포넌트·BR 주석

**⚠️ 알려진 미확정 5건 (코드에 격리, Build & Test 에서 해소)**:
| # | 항목 | 격리 |
|---|---|---|
| 1 | 지역검색 `mapx`/`mapy` 좌표계 | `to_wgs84()` 단일 함수 |
| 2 | 베이스 이미지 다이제스트 (ID-20) | `# DIGEST-PENDING` — **SEC-10 완결 조건** |
| 3 | CSP 허용 도메인 | 설정 상수 분리 |
| 4 | 네이버·NCP 실 응답 형식 | 픽스처 + 파싱 계층 분리 |
| 5 | 안드로이드 빌드 성공 여부 | `Dockerfile.build` — **CON-6 해소 조건** |

이 5건을 확정된 것처럼 기술하지 않고 미검증 상태로 명시하기로 계획에 반영함.

---

## Code Generation Part 1 — Approval
**Timestamp**: 2026-08-13T07:00:00Z
**AI Prompt**: "Approve — 승인하고 Part 2 코드 생성 실행"
**User Response**: "승인하고"
**Status**: **Approved**
**Context**: CONSTRUCTION - Code Generation (u1) Part 1 승인 완료. 19단계 계획 확정.

---

## Code Generation Part 2 — u1-trip-backend / Step 1~5 완료
**Timestamp**: 2026-08-13T07:00:00Z
**User Input**: "(N/A — 계획 실행)"
**AI Response**: "Step 1(구조) · Step 2(core) · Step 3(domain) · Step 4(domain 테스트) · Step 5(요약) 완료. 생성 파일 33개. `python -m compileall` 통과."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 2 Step 10~14 (진행 중)

**생성 파일 33개**
- 기반 3: `pyproject.toml` / `requirements.txt` / `requirements-dev.txt`
- 패키지 마커 11
- core 9 (C1~C5, L5, L6, L8 + `enums.py` 신설)
- domain 7 (C14~C20) — **의존성 0 유지**
- 테스트 7 (`conftest.py`, 생성기, PBT 4종, 예제 1종)

**🔴 설계 정정 1건 — P-03 불변식**
Functional Design 은 P-03 을 "arrival[i] <= departure[i] <= arrival[i+1] 무조건 성립"으로 기술했으나,
**BR-31(고정 시각 유지) · BR-32(밀지 않고 경고만)와 동시에 성립할 수 없음**을 구현 중 발견.
→ 정확한 불변식: **`arrival[i] <= departure[i]` 는 항상 / `departure[i] <= arrival[i+1]` 은 `FIXED_TIME_CONFLICT` 경고가 없는 구간에서만**
→ 반영: `domain/timeline.py` docstring, `test_p03_times_are_monotonic_where_no_conflict`, `domain-summary.md` §2
→ **설계 위반이 아니라 속성 서술의 부정확이며, BR-31·BR-32 는 그대로 유지**

**배치 조정 3건 (설계 위반 아님)**
1. `core/enums.py` 신설 — 공통 열거형 집중으로 순환 import 방지 (계획상 core 8 → 9파일)
2. `EstimatorParams` / `OptimizeLimits` 를 도메인 내 dataclass 로 정의 — **DD-16(의존성 0) 유지 수단**
3. `RateLimiter` 전역 카운터를 Protocol 주입 — ND-8 에 이미 명시된 방식

**정정 1건 (계획 대비)**
`pyproject.toml` 의 `[tool.hypothesis]` 섹션은 **Hypothesis 가 읽지 않음**. 프로파일 등록을 `tests/conftest.py` 로 이동.

**PBT 구현 현황**: P-01~P-22 전건 테스트 함수 작성 완료. 생성기 7종.
**P-10 결정성**은 시간 상한 비활성(`DETERMINISTIC_LIMITS`)에서만 주장하도록 명시 — 벽시계 의존 시 결정성이 깨지기 때문.

**Security Compliance (Step 1~5)**: SEC-03·05·09·10·11·12·14 준수. **Blocking findings: 0건**
**PBT Compliance (Step 1~5)**: PBT-02·03·07·08·09·10 충족. **Blocking findings: 0건**

**⚠️ 테스트는 작성만 완료. 실행은 Build & Test 스테이지** (code-generation.md 규칙).

---

## Code Generation Part 2 — u1-trip-backend / Step 6~8 완료
**Timestamp**: 2026-08-13T07:20:00Z
**User Input**: "승인"
**AI Response**: "Step 6(storage 생성) · Step 7(storage 테스트) · Step 8(요약) 완료. 파일 7개 추가(누적 40개). `compileall` 통과."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 2 Step 10~14 (진행 중)

**생성 파일 7개**
`storage/database.py`(C30) / `storage/db_executor.py`(L4) / `storage/models.py`(12테이블) /
`storage/repositories.py`(C31, 리포지토리 5종) / `storage/migrations.py` /
`tests/unit/test_repositories.py`(11건) / `tests/unit/test_audit_append_only.py`(3건)

**설계 규칙을 코드 구조로 못박은 지점 3건**
1. **BR-39 / SEC-08** — `TripRepository` 에 목록 조회 메서드를 정의하지 않음. `test_no_list_all_method_exists` 가 `dir()` 를 직접 검사해 나중에 추가되면 실패
2. **SEC-14 / BR-59** — `AuditLogRepository` 공개 메서드가 정확히 4개(`append`/`count`/`recent`/`purge_older_than`). 금지 메서드명 9종 부재 + `purge_older_than` 인자가 `days` 하나뿐임을 검증
3. **SP-4** — `QuotaRepository` 카운터가 세션 재생성 후에도 유지됨을 검증. 재시작으로 비용 통제가 우회되면 안 되기 때문

**조정 2건 (설계 위반 아님)**
1. `recover_orphans` 대상에 **`queued` 포함** — 계획서에는 `running` 만 적혀 있었으나 대기 job 도 프로세스 종료 시 실행 주체가 사라져 고아가 된다 (RP-4 의도 부합)
2. `TripRepository` 에 명시적 `update` 메서드 없음 — 세션 내 ORM 객체 변경으로 갱신

**의도적 비연쇄 결정**: `places` 는 여행 삭제로 사라지지 않음. 다른 여행에서 재사용될 수 있음.

**Security Compliance (Step 6~8)**: SEC-05·08·13·14·15 준수. 문자열 연결 SQL **0건**. **Blocking findings: 0건**
**PBT Compliance**: storage 는 순수 함수 없음 → PBT 비대상, 예제 테스트로 검증 (PBT-10). **Blocking findings: 0건**

**미검증**: 테스트 실행 결과 / WAL 동시성 실측 / 파일 SQLite 의 PRAGMA 실제 적용(인메모리에서는 WAL 무시됨)

---

## Code Generation Part 2 — u1-trip-backend / Step 9~11 완료
**Timestamp**: 2026-08-13T07:50:00Z
**User Input**: "승인"
**AI Response**: "Step 9(clients 생성) · Step 10(테스트) · Step 11(요약) 완료. 파일 17개 추가(누적 63개). `compileall` 통과."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 2 Step 10~14 (진행 중)

**생성 파일 17개**
`circuit.py`(L1) / `semaphore.py`(L2) / `base.py`(C6) / `protocols.py` / `cache_decorator.py`(C12) /
`naver_local.py`(C7) / `naver_content.py`(C8) / `ncp_directions.py`(C9) / `ncp_geocoding.py`(C10) /
`anthropic_llm.py`(C11) / `mocks.py` / `factory.py`(C13) / 픽스처 1 / 테스트 5(34건)

**🔴 설계 문서 정정 2건째 — `clients → domain` 의존**
`component-dependency.md` 매트릭스는 `clients → domain` 을 **"—"(의존 없음)** 으로 표기했으나,
구현 결과 **7개 파일에서 의존**이 발생했고 이는 **바람직한 방향**임을 확인:
- DTO(`SearchedPlace`·`CarRoute`)가 `Coordinate` 를 사용 → **국내 범위 검증(BR-15)이 가장 바깥에서 걸림**
- `MockDirectionsClient` 가 `domain.estimator` 재사용 → 중복 구현 방지

→ `component-dependency.md` §3 에 정정 주석 추가. **순환 0건**, `domain` 은 여전히 아무것도 참조하지 않음.
→ `test_domain_layer_has_no_app_imports` 로 역방향을 코드에서 강제.

**설계 조정 2건 (위반 아님)**
1. **`anthropic` SDK 미사용** — Messages API 를 `BaseHttpClient` 로 직접 호출.
   사유 ① SDK 사용 시 서킷(L1)·세마포어(L2)·쿼터 계측(C29)·재시도(BR-47)를 **전부 우회**
        ② 의존성 1개 감소 = 공급망 표면 축소 (SEC-10). `requirements.txt` 에서 제거 + 사유 주석
2. `CachingClientDecorator` 를 클라이언트별 래퍼 4종으로 구현 — Protocol 마다 시그니처가 달라
   범용 `__getattr__` 데코레이터는 타입 안전성이 무너짐. 인터페이스 동일성(DD-15)은 유지

**좌표계 미확정의 격리 (계획 §6-1)**
`to_wgs84()` **단일 함수**에 가둠. 가정이 틀리면:
① `CoordinateConversionError` ② `_parse` 가 해당 항목만 건너뛰고 경고(NFR-3) ③ `Coordinate.__post_init__` 2차 방어
`test_wrong_coordinate_system_raises_instead_of_silently_saving` 가 KATECH 값으로 예외 발생을 확인.

**구조 검증 테스트 2건 신규**
- `test_no_mock_branching_outside_the_factory` — services·domain 소스에서 `if is_mock` / 목 클래스 import / `Mock*Client` 참조를 정규식 검사 (DD-3)
- `test_domain_layer_has_no_app_imports` — `from app.(?!domain)` 검사 (DD-16)

**목 모드가 파이프라인 전체를 살리는 방식 (QG-7)**
`MockLocalSearchClient` 가 질의의 장소명을 그대로 반환해 그라운딩 유사도 판정(BR-11)을 통과시킴.
`MockLlmClient` 는 C22 스키마 검증(BR-07)을 통과하는 형식을 정확히 지킴.
→ 인증 정보 0개로도 생성→그라운딩→경로→최적화→타임라인→저장 전 과정 동작.

**Security Compliance (Step 9~11)**: SEC-01(TLS 강제·테스트) / SEC-03 / SEC-05(BR-14) / SEC-10(의존성 감소) / SEC-11(서킷·세마포어) / SEC-13(구조화 출력 없으면 거부) / SEC-15 준수. **Blocking findings: 0건**
**PBT Compliance**: P-21·P-22 구현 완료. **Blocking findings: 0건**

**미검증 4건**: 좌표계 / NCP 엔드포인트·헤더 / 실응답 형식(픽스처는 문서 기반) / 테스트 실행 결과

---

## Code Generation Part 2 — u1-trip-backend / Step 12~14 완료
**Timestamp**: 2026-08-13T08:20:00Z
**User Input**: "승인"
**AI Response**: "Step 12(services 생성) · Step 13(테스트 67건) · Step 14(요약) 완료. 파일 18개 추가(누적 81개). `compileall` 통과."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 2 Step 10~14 (진행 중)

**생성 파일 18개**
`place_resolver.py`(C23 🔴) / `llm_draft.py`(C22) / `travel_matrix.py`(C24) / `generation_service.py`(C25) /
`trip_service.py`(C21) / `place_search.py`(C26) / `recommendation.py`(C27) / `job_service.py`(C28) /
`job_runner.py`(L3) / `quota_service.py`(C29) / `domain/categories.py`(신규) / `storage/mappers.py`(신규) / 테스트 6종(67건)

**🔴 구현 중 설계 누락 발견 — 최적화 후 행렬 인덱스 재기준화**
`DistanceMatrix` 는 `(from_index, to_index)` 로 조회하는데, **최적화 전 인덱스는 원본 배열 기준**이고
**C15 는 `(위치 i, 위치 i+1)` 로 조회**한다. 순서가 바뀐 뒤 원본 행렬을 그대로 넘기면
**엉뚱한 구간의 이동시간을 읽는다.** `business-logic-model.md` WF-2 의 4→5단계 사이에 이 단계가 없었다.
→ `ItineraryGenerationService._reindex()` 추가. 설계 위반이 아니라 **빠져 있던 구현 세부**.

**파생 결정 CD-1 — 쿼터 계측 방식**
`QuotaGate.record()` 는 `BaseHttpClient` 내부에서 **async 컨텍스트로부터 동기 호출**된다.
여기서 SQLite 에 직접 쓰면 **이벤트 루프가 막혀 ND-18 위반**.
→ **인메모리 증가 + 주기 플러시(L8) + 기동 시 로드** 구조.
   SP-4 목적(재시작으로 비용 통제 우회 방지)은 **기동 시 로드**로 달성.
   손실 범위는 "마지막 플러시 이후 카운트"로 한정 — 상한을 느슨하게 만들 뿐 우회를 허용하지 않음.

**조정 2건 (파일 추가, 위반 아님)**
1. `domain/categories.py` — 카테고리 정규화가 BR-11 ③ 와 BR-52 양쪽에서 쓰임. domain 내부이므로 DD-16 유지
2. `storage/mappers.py` — 매핑을 서비스에 두면 C21 비대화, ORM 에 두면 도메인 지식 누출

**테스트에서 겨냥한 핵심 규칙**
- **BR-18** — `test_unresolved_never_becomes_a_place`(단위) + `test_partial_when_some_places_unresolved`(통합) 양쪽 검증
- **BR-28** — `test_directions_calls_are_linear_not_quadratic` 이 n=2·5·10·15 에서 **정확히 n-1 회** 확인. 순진한 구현은 n=15 에서 210회
- **BR-08** — 스키마 자체에 주소·좌표·전화 필드가 없음을 검증 + 모델이 보내도 **읽지 않음**을 검증
- **BR-40** — 블로그 2건이면 요약 없음 + **LLM 을 호출하지도 않음**(비용 절약)
- **SP-4** — `test_loaded_counts_prevent_restart_bypass`
- **CA-5** — `test_global_daily_cap_blocks_across_ips` (IP 를 바꿔도 전역 상한에 걸림)

**Step 13 계획 대비 조정**: `test_quota_rate_limit.py` 를 별도로 만들지 않고 `test_job_runner.py` 에 통합(동일 관심사).

**Security Compliance (Step 12~14)**: SEC-05·08·11·13·14·15 준수. **Blocking findings: 0건**
**PBT Compliance**: services 는 I/O 오케스트레이션으로 PBT 비대상, 예제 67건으로 검증(PBT-10). **Blocking findings: 0건**

**미검증**: 테스트 실행(누적 115건) / 실 LLM 의 스키마 준수 / 유사도 0.60 임계값 적정성 / 쿼터 플러시 주기

---

## Code Generation Part 2 — u1-trip-backend / Step 15~17 완료
**Timestamp**: 2026-08-13T08:50:00Z
**User Input**: "승인"
**AI Response**: "Step 15(api 생성) · Step 16(테스트 48건) · Step 17(요약) 완료. 파일 17개 추가(누적 98개). `compileall` 통과."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 2 Step 10~14 (진행 중)

**생성 파일 17개**
`api/schemas.py`(C33) / `api/deps.py`(컨테이너, 신규) / 라우터 6종(C32, **엔드포인트 19개**) /
`api/static.py`(L7) / `main.py`(미들웨어 9단계) / 테스트 6종(48건)

**설계 대비 조정 3건 (위반 아님)**
1. `api/deps.py` 신설 — `main.py` 에 배선을 전부 넣으면 라우터가 전역 상태에 의존해 테스트가 어려워짐
2. 라우터 **7파일 → 6파일** (`routes` 를 `trips` 에 통합) — 순서 최적화·이동시간 재계산이 항목 편집과 같은 자원을 다뤄
   분리하면 `_recompute_and_save` 가 중복됨. **엔드포인트 19개는 그대로**
3. 레이트 리밋을 **미들웨어가 아닌 라우터 의존성**으로 — 등급이 엔드포인트마다 다름(BR-49).
   라우트 정의에 등급이 붙어 있어야 새 라우트 추가 시 누락이 드러남. LC-1 의 실행 위치(라우터 직전)는 동일

**미들웨어 조립 주의**: FastAPI 는 **등록 역순**으로 실행하므로 LC-1 순서를 만들기 위해 역순으로 `add_middleware` 함.
`GlobalErrorMiddleware` 가 가장 마지막에 등록되어 **가장 바깥**에서 동작 → (2)~(8) 어디서 터져도 Problem Details 응답.

**OpenAPI 스키마를 검사하는 구조 테스트 2건 (신규 방식)**
- `test_no_trip_list_endpoint` — 스키마에 `GET /api/trips` 가 없음을 확인 (BR-39, 열거 차단)
- `test_no_write_endpoints_under_shared_path` — `/api/shared/*` 의 메서드 집합이 `{get}` 뿐임을 확인 (BR-37, DD-25)
→ 라우트가 나중에 추가되면 즉시 실패한다.

**소스 검사 테스트 1건**
- `test_health_module_does_not_touch_external_clients` — 헬스 라우터 소스에 `local_search`·`directions`·`.llm` 등이
  나타나지 않음을 확인 (ND-14). 헬스체크는 30초마다 실행되므로 외부 호출이 섞이면 하루 2,880회를 소모함.

**Security Compliance (Step 15~17)**: SEC-04·05·08·09·11·15 준수.
누출 마커 9종(Traceback / sqlalchemy / /app/ / fastapi 등)이 오류 응답에 없음을 검증. **Blocking findings: 0건**
**PBT Compliance**: api 는 I/O 경계로 PBT 비대상, 예제 48건(PBT-10). **Blocking findings: 0건**

**미검증 4건**: 테스트 실행(누적 163건) / 미들웨어 실행 순서 실동작 / CSP 도메인 충분성 / 정적 캐시 헤더(Vite 산출물 필요)

---

## Code Generation Part 2 — u1-trip-backend / Step 18~19 완료 (19/19)
**Timestamp**: 2026-08-14T00:10:00Z
**User Input**: "진행"
**AI Response**: "Step 18(배포 산출물) · Step 19(문서) 완료. **19단계 전부 완료**. 애플리케이션 코드 114개 파일. 사용자 승인 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Code Generation (u1) / Part 2 Step 14~15

**생성 파일 16개 (누적 114개 + 문서 5개)**
`Dockerfile` / `docker-compose.yml` / `.env.example`(47항목) / `.gitignore` / `.dockerignore` / `README.md` /
`scripts/` 7종 / `android/Dockerfile.build` / `data/.gitkeep` / `logs/.gitkeep` /
`code/code-summary.md`

**실측 검증**
- `python -m compileall` **exit 0**
- `python scripts/generate-sbom.py` **실행 성공** — 구성 요소 6개, Node 는 u2 미생성으로 건너뜀
- 애플리케이션 코드가 `aidlc-docs/` 밖에만 존재 (**QG-6 충족**)
- 파일 집계: `backend/app` 63 · `backend/tests` 32 · `backend` 루트 3 · `scripts` 7 · `trip` 루트 6 · `android` 1 · `.gitkeep` 2 = **114**

**🔴 설계 문서 정정 3건 (구현 중 발견) — 종합**
1. **P-03 불변식** — "시각 단조 증가"가 BR-31·BR-32 와 동시 성립 불가 → "충돌 경고가 없는 구간에서만"으로 정밀화
2. **`clients → domain` 의존** — 매트릭스에 "없음"으로 표기됐으나 실제로 필요하고 바람직 → 정정 주석 추가
3. **최적화 후 행렬 재기준화** — WF-2 4→5단계 사이에 누락 → `_reindex()` 추가

**설계 대비 조정 12건 / 파생 결정 1건(CD-1)** — 전부 위반 아님. `code-summary.md` §3~5 에 사유 기록

**구조 테스트 8건** — 동작이 아니라 **규칙이 코드에 남아 있는지** 검사:
목록 메서드 부재 / OpenAPI 목록 경로 부재 / 감사 로그 추가 전용 / purge 인자 제한 /
목 분기 격리 / domain 의존성 0 / 공유 경로 GET 전용 / 헬스체크 외부 미호출

**추적성**: Owner FR 15건 **미매핑 0** / BR-01~60 **미구현 0** / P-01~P-22 **미작성 0** / SEC 13건 구현 지점 확정

**Security Compliance (Code Generation 전체)**:
준수 13 / N/A 2(SEC-02·06) / **부분 1(SEC-10 — 다이제스트 미결 ID-20)**
**Blocking findings: 0건** — 단, **Build & Test I-2 에서 다이제스트를 채우지 못하면 SEC-10 이 blocking 으로 승격**

**PBT Compliance**: PBT-01·02·03·05·07·08·09·10 충족 / PBT-04·06 N/A(근거 명시). **Blocking findings: 0건**

**⚠️ 미검증 10건 (검증된 것처럼 기술하지 않음)**
테스트 실행(약 206건) / 좌표계 / 다이제스트 / CSP 도메인 / NCP 엔드포인트·헤더 / 실 API 응답 형식 /
의존성 설치 가능 여부 / 미들웨어 순서 실동작 / 유사도 임계값 적정성 /
**이미지 빌드 — `web/`(u2) 부재로 현재 `docker compose build` 실패 (설계대로, u2 생성 후 해소)**

---

## Code Generation (u1-trip-backend) — Approval
**Timestamp**: 2026-08-14T00:30:00Z
**AI Prompt**: "Continue to Next Stage — 승인하고 u2-trip-web Functional Design 으로 진행"
**User Response**: "진행"
**Status**: **Approved**
**Context**: CONSTRUCTION - Code Generation (u1) 승인 완료. 19단계 / 114파일 / 테스트 약 206건.
설계 문서 정정 3건·조정 12건·파생 결정 1건에 이견 없음. SEC-10 부분 충족 상태 승인됨.

---

## Functional Design (u2-trip-web) — 사전 분석
**Timestamp**: 2026-08-14T00:30:00Z
**User Input**: "(N/A — 자동 분석)"
**AI Response**: "u1 API 계약과 설계 결정을 대조해 **구조적 문제 2건 발견**. 질문으로 전환."
**Context**: CONSTRUCTION - Functional Design (u2) / Step 1~3

### 🔴 발견 1 — 브라우저 데이터 삭제 시 여행 접근 불가
DD-21 / BR-39 로 `GET /api/trips`(목록)를 **의도적으로 제공하지 않음**(열거 취약점 방지).
그 귀결로 "내 여행 목록"이 `localStorage` 의 `trip_id` 집합에만 존재한다.
→ 브라우저 데이터 삭제·시크릿 모드 종료·다른 기기 접속 시 **여행에 다시 접근할 수 없다.**
   (서버에는 남아 있으나 UUID 를 모름)
→ 설계상 예견된 결과이나 **사용자에게는 데이터 유실로 보인다.** Q3 으로 완화책 결정 요청.
   B안(목록 API 추가)은 DD-21·BR-39·SEC-08 을 뒤집으므로 권장하지 않음.

### 🔴 발견 2 — 지도 SDK 키를 프론트에 전달할 경로 부재
`NCP_MAP_CLIENT_KEY` 는 구조상 브라우저에 노출되어야 하나(CON-3),
u1 은 `/api/health/ready` 에서 **`map_client_key_configured`(불리언)만** 노출하고 값을 주지 않는다.
→ 전달 방식 2가지의 성격이 다름:
   빌드 시 주입(`VITE_`) = 키 변경 시 **이미지 재빌드 필요**
   런타임 엔드포인트(`GET /api/config`) = `.env` 수정 + 재시작만으로 반영, 단 **u1 에 엔드포인트 1개 추가**
→ Q4 로 결정 요청. A안 선택 시 엔드포인트 19 → 20.

---

## Functional Design (u2-trip-web) — Plan Presented
**Timestamp**: 2026-08-14T00:30:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u2-trip-web-functional-design-plan.md` 생성. 체크리스트 + 설계 질문 18개(데이터 흐름·설정 4 / 화면 구조 4 / 지도·딥링크 4 / 오류·오프라인 3 / 기술·접근성 3). 사용자 답변 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Functional Design (u2) / Step 4~5 GATE

**주의 환기**: Q3·Q4 는 지금 결정하지 않으면 구현 중 임시방편으로 처리될 위험이 있음을 계획서에 명시.
Q18(접근성)은 **근거 없는 WCAG 준수 선언을 하지 않는 안**을 추천안으로 제시.

---

## Functional Design (u2-trip-web) — Answers Received & Artifacts Created
**Timestamp**: 2026-08-14T01:00:00Z
**User Input**: "전부 추천안"
**AI Response**: "설계 질문 18개 전부 ⭐(=A) 확정. 모호성 0건, 교차 검증에서 충돌 1건 검출·해소 후 산출물 4종 생성."
**Context**: CONSTRUCTION - Functional Design (u2) / Step 5~6

**확정된 답변**: Q1~Q18 = 전부 **A**

**모호성 분석 (Step 5)**: 모호 응답 **0건**.

**⚠️ 교차 검증 충돌 1건 검출 → WD-1 로 해소**
`Q6(모바일 탭 전환)` × `FR-19(지도 ↔ 타임라인 양방향 하이라이트)`
모바일에서 두 패널이 탭으로 분리되면 **동시에 보이지 않으므로 "양방향 하이라이트"가 화면상 성립하지 않는다.**
그대로 두면 FR-19 가 데스크톱에서만 동작한다.
→ **"동시 표시"가 아니라 "상태 연속성"으로 FR-19 를 만족**시키는 해석을 확정:
   `selectedItemId` 를 탭과 무관하게 유지하고, 전환 후 해당 항목으로 스크롤·뷰포트 이동.
→ `business-rules.md` **WBR-18** 에 명문화.

**생성 산출물 4종**
`construction/u2-trip-web/functional-design/` — `domain-entities.md` / `business-logic-model.md` /
`business-rules.md` / **`frontend-components.md`**

**설계 결과**
- 클라이언트 고유 타입 **6종** (`SavedTripRef`·`TripListExport`·`RuntimeConfig`·`UiState`·`DeepLinkUrls`·`Toast`)
- 화면 흐름 **WF-W1 ~ WF-W8**, 비즈니스 규칙 **WBR-01 ~ WBR-42 (42건)**
- **Testable Properties WP-01 ~ WP-11** (fast-check)
- 컴포넌트 계층·props/state·폼 검증·**API 연결점 20개 매핑** 확정
- Owner FR 15건 **미매핑 0건**

**핵심 결정**
- **WBR-04**: 서버 산출값을 클라이언트에서 재계산 금지 — 두 곳에서 계산하면 반드시 어긋난다
- **WBR-06~08**: 브라우저 데이터 삭제 시 여행 접근 불가 → 상시 고지 + 공유 링크 안내 + **목록 내보내기/가져오기**.
  **DD-21(목록 API 부재)은 뒤집지 않는다** — B안(목록 API 추가)은 SEC-08 위반
- **WBR-22**: 추정 이동시간에 반드시 "추정" 배지 (CON-1 을 정직하게 노출)
- **WBR-28**: 딥링크 URL 생성은 W13 한 곳에만 (DD-11)
- **WBR-30**: 데모 모드는 닫을 수 없는 배너
- **SharedTripView 는 편집 컴포넌트를 `readOnly` 로 숨기지 않고 트리에 넣지 않는다** (DD-25 의 UI 측 대응)
- **PBT-04(멱등성)가 u2 에서는 N/A 가 아님** — 목록 가져오기가 멱등 (WP-06)

**🔴 u1 개정 요청 A-1 — `GET /api/config` 추가 (Q4=A)**
지도 SDK 키를 프론트에 전달할 경로가 없어 런타임 설정 엔드포인트를 추가한다.
- 응답: `map_client_key` · `modes` · `limits` (**검색·LLM 키는 포함하지 않음**)
- 근거: 빌드 시 주입(`VITE_`) 방식은 키 변경 시 **이미지 재빌드**가 필요해 `.env` 수정만으로 반영되지 않음 — 운영상 함정
- 영향: 엔드포인트 **19 → 20**, `component-methods.md` §7 갱신 필요
- 적용 시점: **u2 Code Generation 시작 시**

**Security Compliance (Functional Design u2)**: SEC-04·05·08·13·15 부분 책임 명시. **Blocking findings: 0건**
**PBT Compliance**: PBT-01·02·03·04·07·09·10 충족, PBT-08 은 Code Generation 이월. **Blocking findings: 0건**

---

## Functional Design (u2-trip-web) — Approval
**Timestamp**: 2026-08-14T01:20:00Z
**AI Prompt**: "Continue to Next Stage — 승인하고 u2 Code Generation 으로 진행"
**User Response**: "진행"
**Status**: **Approved**
**Context**: CONSTRUCTION - Functional Design (u2) 승인 완료. WBR-01~42 확정.
**WBR-18(FR-19 를 상태 연속성으로 해석)과 u1 개정 A-1(`GET /api/config` 추가)이 함께 승인됨.**

---

## Code Generation Part 1 (Planning) — u2-trip-web
**Timestamp**: 2026-08-14T01:20:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u2-trip-web-code-generation-plan.md` 생성. **15단계 / 약 85개 파일**. 사용자 승인 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Code Generation (u2) / Part 1 Step 1~7 GATE

**코드 위치**: `c:\Users\403\IDE\trip\web\` (+ A-1 은 `trip\backend\`). 문서는 `aidlc-docs/construction/u2-trip-web/code/`

**⚠️ Step 1 은 승인된 u1 코드를 변경합니다 (개정 A-1)**
- 신규: `backend/app/api/routers/config.py`, `backend/tests/unit/test_api_config.py`
- 수정: `backend/app/api/routers/__init__.py`, `backend/app/api/schemas.py`
- 엔드포인트 **19 → 20**. `component-methods.md` §7 갱신 필요
- 테스트에서 **검색·LLM 키가 응답에 없음**을 검증 (SEC-11)

**생성 원칙 14개 명문화** — 특히:
서버 산출값 재계산 금지(WBR-04) / 편집 응답으로 캐시 직접 갱신(WBR-14) /
추정 배지 필수(WBR-22) / 딥링크는 W13 단일 소유(WBR-28) / 웹·앱 분기는 W14 단일 소유 /
**공유 화면은 편집 컴포넌트를 숨기지 않고 트리에서 제외**(DD-25) / 인라인 스크립트 금지(SEC-04) /
폼 상한 하드코딩 금지(WBR-10)

**구조 테스트 4건 계획** — 규칙이 코드에 남아 있는지 검사:
공유 화면 편집 컴포넌트 부재 / 폼 상한 하드코딩 부재 / `nmap://` 리터럴이 W13 밖에 없음 / 인라인 스크립트 부재

**⚠️ 미확정 5건**: 지도 SDK 스크립트 URL·전역 객체 / CSP 도메인 충분성 / 의존성 설치 가능 여부 /
`generated.ts` 실제 생성 결과 / 번들 크기

**🔴 `generated.ts` 주의**: u1 을 실제 기동해야 생성 가능.
Part 2 에서 기동에 실패하면 **수기 타입으로 대체하지 않고 그 사실을 보고**하기로 계획에 명시.

---

## Code Generation Part 1 (u2) — Approval
**Timestamp**: 2026-08-14T03:40:00Z
**AI Prompt**: "Approve — 승인하고 Part 2 코드 생성 실행"
**User Response**: "진행"
**Status**: **Approved**
**Context**: CONSTRUCTION - Code Generation (u2) Part 1 승인. 15단계 계획 확정.

---

## Code Generation Part 2 (u2) — Step 1 완료 및 실기동 검증
**Timestamp**: 2026-08-14T03:55:00Z
**User Input**: "(계획 실행)"
**AI Response**: "개정 A-1 적용 완료. **u1 을 python:3.12 컨테이너에서 실제 기동해 OpenAPI 스키마 추출 성공.** 그 과정에서 결함 3건 발견."
**Context**: CONSTRUCTION - Code Generation (u2) / Part 2 Step 1~3

### Step 1 산출물 (개정 A-1)
신규 `api/routers/config.py` · `tests/unit/test_api_config.py`(9건) / 수정 `api/schemas.py` · `api/routers/__init__.py`
테스트는 **응답 스키마에 비밀 필드가 없음** + **라우터 소스가 비밀 설정을 참조하지 않음**을 구조적으로 검증 (SEC-11).

### 실기동 결과 (예상 밖의 성과)
`docker run python:3.12-slim` 으로 u1 기동 성공. 로그 실측 확인:
- `schema ready (schema_version 1)` — 마이그레이션 동작
- `목 데이터 모드로 동작합니다 mock_apis=[6종]` — C13 목 주입 동작 (FR-33)
- JSON 구조화 로깅 + correlation_id 동작 (NFR-8)
- **`requirements.txt` 가 python:3.12 에서 정상 설치** — UD-9 선택이 옳았음이 확인됨

### 🔴 결함 1 — 로컬 Python 3.14 의존성 설치 불가 (예견됨, 조치 불요)
`pydantic-core` 가 3.14 휠을 제공하지 않고, 소스 빌드는 **PyO3 0.22.6 의 최대 지원이 3.13** 이라 실패.
→ **UD-9(컨테이너 3.12 고정)의 근거가 실측으로 확인됨.** README 의 "로컬 3.14 는 비보증" 표기가 정확했음.
→ 조치 불요. 다만 Build & Test 는 **반드시 컨테이너에서** 수행해야 함을 확정.

### 🔴 결함 2 — `main.py` import 부작용 (수정 완료)
모듈 수준 `app = create_app()` 때문에 `import app.main` 만으로 Container 가 생성됨
(DB 파일·마이그레이션·HTTP 클라이언트 풀). 스키마 추출 시 **컨테이너가 두 번 생성되는 것을 로그로 실측**.
→ **수정**: 모듈 수준 `app` 제거, `uvicorn app.main:create_app --factory` 로 전환. `Dockerfile` CMD 갱신.
→ 참고: news 프로젝트에서도 동일 유형의 결함이 Build & Test 에서 발견된 바 있음.

### 🔴 결함 3 — OpenAPI 응답 무타입 (⛔ 사용자 결정 대기)
**22개 오퍼레이션 중 17개의 성공 응답이 `{"type":"object"}`(무타입)** 으로 생성됨.
원인: 라우터가 `-> dict` 를 반환해 FastAPI 가 응답 스키마를 만들지 못함.
영향: **`openapi-typescript` 가 만들 TS 타입이 `unknown` 이 되어,
      UD-3/DD-10 의 목적("계약 불일치를 컴파일 오류로 검출")이 완전히 무력화됨.**
      u2 는 타입 안전성 없이 `any` 를 다루게 되고, WBR-01·02 도 의미를 잃음.

타입이 있는 응답: `GET /api/config`, `POST /api/trips/{id}/generate` 2개뿐.

→ **개정 A-2 제안**: u1 에 응답 모델을 정의하고 라우트에 `response_model` 을 부여. 사용자 결정 요청.

---

## 개정 A-2 — Approval & 적용
**Timestamp**: 2026-08-14T04:10:00Z
**AI Prompt**: "A-2 적용(권장) / 미적용하고 진행 / 다른 방식"
**User Response**: "권장적용"
**Status**: **Approved — A-2 적용**
**Context**: CONSTRUCTION - Code Generation (u2) / Step 1b

### 적용 내역
- **응답 모델 17종 신설** (`api/schemas.py`): `CoordinateOut` · `DayRuleOut` · `OpeningHoursOut` ·
  `PlaceOut` · `ItemWarningOut` · `ItineraryItemOut` · `TripDayOut` · `UnresolvedOut` ·
  `TripOut` · `ReadOnlyTripOut` · `JobStatusOut` · `PagedPlacesOut` · `SuggestionsOut` ·
  `BlogRefOut` · `ImageRefOut` · `PlaceContentOut` · `ShareTokenOut` · `QuotaUsageOut`
- **라우터 19곳에 `response_model` 부여** — trips 9 / generation 1 / places 3 / share 2 / health 2 / config 1 / 기존 1
- `main.py` import 부작용 제거 + `Dockerfile` CMD `--factory` 전환

### 실측 결과 (재기동 후 스키마 재추출)
| 지표 | 이전 | 이후 |
|---|---|---|
| 타입 있는 응답 | 2 | **19** |
| 무타입(`object`) 응답 | **17** | **0** |
| OpenAPI 스키마 수 | 15 | **41** |

나머지 3개 오퍼레이션은 `204`(여행 삭제·공유 폐기) 또는 `text/calendar`(`.ics`) 로 JSON 본문이 없어 정상.

### 부수 효과 — DD-25 가 타입으로 보장됨
`ReadOnlyTripOut` 에 `share_token` 필드가 **스키마상 존재하지 않는다.**
공유 조회 응답에 토큰이 섞이는 실수가 **응답 타입 수준에서 차단**된다 (기존에는 코드 규율에만 의존).

### 생성된 타입
`web/openapi.json` (u1 실기동 추출) → `openapi-typescript@7` → `web/src/shared/api/generated.ts` **1,650줄**.
두 파일 모두 커밋 대상 (UD-3 — 없으면 Docker 웹 빌드 스테이지가 백엔드 기동을 요구해 순환).

### 문서 정정
`component-methods.md` §7 에 정정 블록 추가 — 오퍼레이션 **19 → 22**, 경로 변경 1건, A-2 경위.

---

## Code Generation Part 2 (u2) — Step 2~7 완료 및 **테스트 실제 실행**
**Timestamp**: 2026-08-14T04:55:00Z
**User Input**: "진행"
**AI Response**: "Step 2~7 완료. **의존성 설치 → 타입 검사 → 테스트 실행까지 실제로 수행**했고 결함 3건을 발견·수정."
**Context**: CONSTRUCTION - Code Generation (u2) / Part 2 Step 11~14

### 실측 검증 (u1 과 달리 이번에는 실행까지 완료)
| 검증 | 결과 |
|---|---|
| `npm install` | ✅ 330 패키지. **`package-lock.json` 생성 → SEC-10(락파일) 충족** |
| `npx tsc -b --noEmit` | ✅ **오류 0건** |
| `npx vitest run` | ✅ **52 passed / 0 failed** (5 파일) |
| 반복 실행 | ✅ **10회 연속 통과** (시드 무작위, `derandomize:false`) |

### 🔴 결함 1 — PBT 가 프로토타입 오염 버그를 발견 (가장 중요)
`polling.property.test.ts` 의 "알 수 없는 단계도 빈 문자열을 내지 않는다" 속성 실패.
fast-check 축소 **반례: `"toString"`**.

원인: 객체 리터럴을 조회 표로 쓰면 `Object.prototype` 상속 속성이 새어나온다.
`STEP_LABELS["toString"]` 이 **함수**를 반환해 `?? 기본값` 이 발동하지 않고,
`.length` 가 함수 인자 수(0)를 돌려준다 → 화면에 **빈 라벨**.

조치: `STEP_LABELS` 를 `Map` 으로 교체 + **같은 부류인 `selectors/trip.ts::API_LABELS` 도 선제 수정**
+ 회귀 테스트(`toString`·`constructor`·`valueOf`·`hasOwnProperty`·`__proto__`).

→ 예제 기반 테스트로는 나오기 어려운 결함. **PBT-03 이 실제로 값을 한 첫 사례.**

### 🔴 결함 2 — `decodeParams` 의 `__proto__` 키 (선제 차단)
WP-01 왕복 속성이 **약 10회 중 1회** 실패(시드 의존). 실패 지점이 사전 왕복이었고
결함 1과 같은 부류로 판단해 `Object.defineProperty` 로 교체 + 회귀 예제 추가 → 10회 연속 통과.

⚠️ **정직 기록**: 원래 실패의 반례를 직접 포착하지는 못했다(시드 재현 실패).
   다만 실패 위치·기전이 일치하며, 이 수정은 어떤 경우에도 옳은 변경이다.

### 🔴 결함 3 — 존재하지 않는 의존성 버전
`@tanstack/query-async-storage-persister@5.62.11` 이 **배포되지 않은 버전**(`npm error ETARGET`).
이 패키지는 `5.68.0` 부터 존재 → TanStack 3종을 **`5.69.2`** 로 정렬. `@types/node` 누락도 추가.
→ 계획서 §7 의 미확정 항목("의존성 설치 가능 여부")이 **실제로 문제였음**이 확인됨.

### 생성 파일 24개
u1 개정 4 / 빌드 설정 6 / API 계약 5 / 인프라 5 / 순수 함수 4 / 테스트 6
(`code/infra-summary.md` 별도)

### WP 속성 현황
**WP-01 ~ WP-11 전건 구현·통과** ✅

### Security Compliance (Step 1~7)
SEC-04·08·09·10·11 준수. **SEC-10 은 `package-lock.json` 생성으로 u2 측 요건 충족**
(u1 의 다이제스트 미결은 여전히 Build & Test I-2 대기). **Blocking findings: 0건**

### PBT Compliance
PBT-02·03·04·07·08·09·10 충족. **PBT-08(셰링킹)이 실제로 반례를 축소해 결함을 드러냄을 확인.**
**Blocking findings: 0건**

### 해소된 미확정 2건
- ~~의존성 설치 가능 여부~~ → ✅ 해소 (락파일 생성)
- ~~`generated.ts` 실제 생성 결과~~ → ✅ 해소 (1,650줄 실제 타입)

---

## Code Generation Part 2 (u2) — Step 8~15 완료 (15/15)
**Timestamp**: 2026-08-14T19:35:00Z
**User Input**: "진행" (× 3회) + 의도 확인 응답 "이어서 진행"
**AI Response**: "Step 8~15 완료. **u2 Code Generation 15/15 완료.** 타입 검사·테스트·프로덕션 빌드까지 전부 실측. 사용자 승인 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Code Generation (u2) / Part 2 Step 14~15

**의도 확인 기록**: 사용자 입력이 "진행 / 재시작" 으로 상충해 `AskUserQuestion` 으로 확인.
선택지 3종(이어서 진행 / u2 만 재생성 / 프로젝트 전체 재시작) 중 **"이어서 진행"** 선택됨.
→ 전체 재시작은 코드 140여 개 파일과 승인 게이트 7회를 폐기하는 작업이라 임의 판단하지 않았다.

### 최종 실측 결과
| 검증 | 결과 |
|---|---|
| `tsc -b --noEmit` | ✅ 오류 0건 |
| `vitest run` | ✅ **79 passed / 0 failed** (7 파일) |
| `npm run build` | ✅ 143 모듈, 1.48초 |
| 번들 크기 | **초기 gzip ≈ 93.5KB** — NFR-12 목표(1MB) 대비 약 9% |
| 코드 분할 | ✅ `TripWorkspace`(11.9KB) · `dnd`(15.3KB) 가 지연 로드 (WBR-41) |

### 🔴 결함 4 — 구조 테스트 자체의 오탐 (신규 발견)
구조 테스트 18건 중 4건이 실패했는데 **전부 주석의 설명 문구를 코드로 오탐**한 것이었다.
예: `SharedTripView.tsx` 주석의 "`DndContext` 를 import 하지 않는다" 라는 **문장**이 위반으로 잡힘.
`loadSdk.ts` 의 `oapi.map.naver.com`(SDK 출처)도 딥링크로 오인됨.
→ `stripComments()` 도입해 **코드만 검사**하도록 수정. 자동 생성 배너 검사만 원문 사용.
→ 이 함정은 구조 테스트를 쓸 때 반드시 만나므로 헬퍼에 사유를 명시했다.

### 생성 파일 60개 + u1 개정
`web/src` 44 · `web/tests` 9 · `web/` 루트 7 / u1 개정(`config.py` 신규 · `schemas.py` · 라우터 6 · 테스트 1)
**커밋 필수**: `openapi.json`, `src/shared/api/generated.ts` (없으면 Docker 웹 빌드가 순환 — UD-3)

### 구조 테스트 18건이 강제하는 규칙
딥링크 단일 소유(WBR-28) · 웹/앱 분기 단일 소유(DD-11) · 지도 SDK 격리(DD-18) ·
공유 화면에 편집 컴포넌트 부재(DD-25) · 폼 상한 미하드코딩(WBR-10) · 재계산 금지(WBR-04) ·
인라인 스크립트 금지(SEC-04) · 생성 타입 불가침(WBR-01) · 스토어에 서버 데이터 금지(WBR-03) ·
job persist 금지(DD-14) · 네트워크 비의존(NFR-10)

### 추적성
WP-01~WP-11 **전건 통과** / WBR-01~WBR-42 **전건 구현** / Owner FR 15건 **미매핑 0건**

### Security Compliance (u2 전체)
SEC-04·05·08·09·10·11·13 준수. **Blocking findings: 0건**
### PBT Compliance
PBT-01·02·03·04·07·08·09·10 충족. **Blocking findings: 0건**

### ⚠️ 해소된 제약
~~"`web/` 부재로 `docker compose build` 실패"~~ → **해소.** 실제 이미지 빌드는 Build & Test 에서 확인.

### 남은 미검증 4건
지도 SDK 실제 로딩 / CSP 도메인 충분성 / 실 API 응답 정합 / u1+u2 통합 이미지 빌드

---

## Code Generation (u2-trip-web) — Approval
**Timestamp**: 2026-08-14T20:00:00Z
**AI Prompt**: "Continue to Next Stage — 승인하고 u3-trip-android Functional Design 으로 진행"
**User Response**: "승인"
**Status**: **Approved**
**Context**: CONSTRUCTION - Code Generation (u2) 승인 완료. 15단계 / 60파일 / 79 테스트 통과 / 빌드 성공.
u1 개정 A-1·A-2, 결함 4건 수정, 구조 테스트 18건에 이견 없음.

---

## Functional Design (u3-trip-android) — 사전 분석
**Timestamp**: 2026-08-14T20:00:00Z
**User Input**: "(N/A — 자동 분석)"
**AI Response**: "u2 구현 코드를 대조해 **구조적 문제 3건 발견**. 전부 '웹에서는 되는데 앱에서만 조용히 안 되는' 유형."
**Context**: CONSTRUCTION - Functional Design (u3) / Step 1~3

### 🔴 발견 1 — Android 9+ 평문 HTTP 차단
CA-1 로 확정한 안드로이드 접속 주소는 `http://10.0.2.2:8200`(에뮬레이터) / `http://<LAN IP>:8200`(실기기).
**Android 9(API 28)부터 평문 HTTP 가 기본 차단**되므로 조치 없이 빌드하면 앱이 백엔드에 접속하지 못하고
**빈 화면**만 뜬다.
→ Q3 으로 결정 요청. 추천안은 `network_security_config.xml` **개발 주소 한정 + debug 빌드에만** 적용
   (`usesCleartextTraffic` 은 모든 도메인에 적용되고 릴리스에도 남으므로 배제).

### 🔴 발견 2 — WebView 는 다운로드를 처리하지 않음
u2 `TripHeader` 의 `.ics` 내보내기는 `<a download>` 다. **WebView 는 `DownloadListener` 없이는
다운로드를 무시**한다. 버튼을 눌러도 **아무 일도 일어나지 않고 오류도 나지 않는다.**
→ FR-26 이 앱에서 무력화된다. Q5 로 결정 요청.

### 🔴 발견 3 — WebView 는 `window.open` 을 기본 무시
u2 `shared/bridge/index.ts` 의 웹 폴백은 `window.open(webUrl)` 이다.
**`setSupportMultipleWindows(true)` + `onCreateWindow` 구현이 없으면 무시**된다.
앱에서는 브리지가 있어 이 경로를 안 타는 게 정상이지만, **브리지 전달이 실패하면 무반응**이 된다.
→ FR-24(웹 폴백)의 최후 경로가 앱에서 사라진다. Q6 으로 결정 요청.

> 세 건 모두 **오류가 나지 않아** Build & Test 의 컨테이너 빌드(컴파일·패키징)로는 잡히지 않는다.
> 실기기에서야 드러나므로 설계 시점에 결정해 둔다.

---

## Functional Design (u3-trip-android) — Plan Presented
**Timestamp**: 2026-08-14T20:00:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u3-trip-android-functional-design-plan.md` 생성. 체크리스트 + 설계 질문 14개(빌드·네트워크 3 / WebView 4 / 브리지 4 / 화면·오류 3). 사용자 답변 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Functional Design (u3) / Step 4~5 GATE

### 📋 문서 드리프트 발견
`component-methods.md` §7 = **19개** vs 실제 = **22개 오퍼레이션**.
추가: `/api/health/ready`, `.../opening-hours`, `/api/config`(A-1)
변경: `GET /api/places/{place_id}/content` → `GET /api/places/content?trip_id=&item_id=`
→ A-2 적용 시 함께 정정 예정.

---

## Functional Design (u3-trip-android) — Answers Received & Artifacts Generated
**Timestamp**: 2026-08-14T20:20:00Z
**User Input**: "전부 추천안"
**AI Response**: "Q1~Q14 = 전부 A 로 확정. 교차 검증 후 산출물 3종 생성."
**Context**: CONSTRUCTION - Functional Design (u3) / Step 5~7

### 확정 답변 (14/14 = A)
| Q | 결정 |
|---|---|
| Q1 | minSdk 26 / targetSdk 35 |
| Q2 | `gradle.properties` → `BuildConfig.BASE_URL` (debug `http://10.0.2.2:8200`, release 빈 값) |
| Q3 | `network_security_config.xml` — 개발 주소 한정 + **debug 소스셋 전용** |
| Q4 | 선택적 하드닝 (JS ✅ / DOM Storage ✅ / 파일 접근 ❌ / mixed content ❌ / 오리진 밖 내비 차단) |
| Q5 | `DownloadListener` + `DownloadManager` |
| Q6 | `setSupportMultipleWindows(true)` + `onCreateWindow` → URL 추출 후 시스템 브라우저 |
| Q7 | 외부 링크 → 시스템 브라우저 |
| Q8 | `addWebMessageListener` + 허용 오리진, `@JavascriptInterface` 폴백 |
| Q9 | `evaluateJavascript` + `JSONObject.quote` 인코딩 |
| Q10 | try-intent + `ActivityNotFoundException` 폴백 (+`<queries>` 이중 안전장치) |
| Q11 | 위치 권한은 웹 요청 시에만, 거부는 `denied: true` (오류 아님) |
| Q12 | 오프라인 화면은 **최초 로드 실패 시에만** (이후는 u2 `OfflineGate`) |
| Q13 | WebView 히스토리 우선 → 최상위에서 이중 입력 종료 |
| Q14 | 네이티브 UI 최소화 (WebView + 오류 화면 + 로딩 + 토스트) |

### 모순·모호성 분석 (Step 5 필수) — 신규 검출 2건

**⚠️ AD-1 — `DownloadManager` 는 앱의 네트워크 정책을 따르지 않는다**
Q5=A × Q3=A 교차. `DownloadManager` 는 시스템 프로세스(`com.android.providers.downloads`)에서
동작하므로 **우리 앱의 `network_security_config` 가 적용되지 않는다.** 평문 HTTP 다운로드 성공 여부가
기기·OS 에 따라 달라질 수 있다.
→ **해소**: 다운로드 실패 시 **시스템 브라우저 폴백** 제공 (ABR-24). Build & Test 실기기 검증 항목 등록.

**⚠️ AD-2 — `evaluateJavascript` 는 UI 스레드 전용**
Q9=A × `addWebMessageListener` 의 Executor 콜백 스레드 교차. 브리지 콜백과 권한 결과 콜백이
UI 스레드가 아닐 수 있는데 WebView API 는 UI 스레드 전용이다. 위반 시 예외 또는 무증상 실패.
→ **해소**: 모든 웹 회신을 `webView.post { }` 로 UI 스레드에서 실행 (ABR-30).

**모순 없음 확인**: Q3(release 평문 차단) × Q2(release BASE_URL 빈 값) 정합 —
릴리스는 HTTPS 도메인 주입이 전제. Q6 × Q7 은 동일 메커니즘(시스템 브라우저)으로 수렴.
Q4(오리진 밖 차단) × Q8(폴백 경로) — A2 가 2차 방어를 하므로 두 경로의 노출 범위가 동일.
Q13(종료 토스트) × Q14(UI 최소화) — 토스트는 허용 범위 내.

### 생성 산출물 3종
- `construction/u3-trip-android/functional-design/domain-entities.md`
  — u3 는 도메인 없음을 명시. 빌드 설정 / 네트워크 정책 / 앱 상태 / **브리지 계약 5종** / 허용 오리진 / 권한·`<queries>`
- `construction/u3-trip-android/functional-design/business-logic-model.md`
  — AD-1·AD-2 검출 기록, WF-A1~WF-A9 (기동·하드닝·브리지·지도·다운로드·window.open·위치·오프라인·뒤로가기),
    **PBT N/A 판정 + 대체 예제 기반 테스트 5종**
- `construction/u3-trip-android/functional-design/business-rules.md`
  — **ABR-01~ABR-43 (26개 규칙)**, FR 추적성(소유 FR-27·28·29·30 / 참여 FR-12·23·24·26),
    SEC 추적성(SEC-01·05·08·09·11·13), **§9 실기기 확인 체크리스트 8항목**

### 🔴 자동 검증 한계 명시
u3 의 핵심 결함 유형(평문 차단·다운로드 무시·`window.open` 무시·위치 미회신)은 **전부 컴파일이 통과하고
오류도 나지 않는다.** 컨테이너 빌드(CON-6)는 컴파일·패키징까지만 검증하므로 잡히지 않는다.
→ `business-rules.md` §9 에 실기기 확인 체크리스트 8항목을 남기고, Build & Test 보고서·README 에 이관한다.

---

## Functional Design (u3-trip-android) — APPROVED
**Timestamp**: 2026-08-14T20:30:00Z
**User Input**: "승인"
**AI Response**: "u3 Functional Design 승인. 산출물 3종 확정. Code Generation Part 1 (계획) 착수."
**Context**: CONSTRUCTION - Functional Design (u3) / Step 7 GATE 통과 — 승인 게이트 **9/12** 완료

---

## Code Generation (u3-trip-android) — Part 1 Plan Presented
**Timestamp**: 2026-08-14T20:35:00Z
**User Input**: "(대기 중)"
**AI Response**: "`construction/plans/u3-trip-android-code-generation-plan.md` 생성. Step 1~16, 약 35개 파일. 승인 대기 (⛔ GATE)."
**Context**: CONSTRUCTION - Code Generation (u3) / Part 1 Step 1~7

### 🔴 착수 전 u2 코드 대조 — 발견 3건

**발견 A — `bridgeReady` 를 u2 가 소비하지 않는다**
u2 `shared/bridge/index.ts` 의 `ensureReceiver()` 는 `requestLocation()` 호출 시점에야
`window.__tripBridgeReceive` 를 심는다. `onPageFinished` 직후 `bridgeReady` 를 보내면 **콜백이 없다.**
또한 u2 수신부는 `locationResult` 외 메시지를 무시한다 → `bridgeReady` 는 **소비처가 없다.**
→ 조치: 계약은 유지(문서가 단일 진실 공급원)하되 u3 는 `typeof window.__tripBridgeReceive === 'function'`
　가드 안에서만 전송. 소비처 부재를 코드 주석에 명시. ABR-33 구체화.

**발견 B — 브리지 객체 모양은 두 경로가 동일 ✅**
u2 는 `window.tripBridge.postMessage(string)` 하나만 본다. `addWebMessageListener` 와
`addJavascriptInterface` 가 **u2 입장에서 구분되지 않는다** → Q8=A 의 폴백이 정상 성립. 확인 완료.

**발견 C — u2 도 위치 타임아웃 10초를 자체 보유 ✅**
미회신이어도 UI 가 영구히 멈추지는 않으나 10초를 기다린다.
→ u3 타임아웃을 **8초**로 설정해 u2 보다 먼저 회신. 같은 값이면 경합이 생긴다.

### 🔴 빌드 사전 고지 2건
1. **`gradle-wrapper.jar` 는 바이너리라 생성 불가** → `Dockerfile.build` 가 Gradle 설치 이미지에서
   `gradle wrapper` 를 실행. 리포지터리에는 `gradle-wrapper.properties` 만 둔다.
2. **컨테이너 APK 빌드는 Android SDK 1~2GB 다운로드 + 라이선스 동의 필요** →
   Build & Test 에서 실측을 **시도**하되 성공을 가정하지 않는다. 실패 시 원인을 정직하게 기록.

### 계획 요약
Step 1~2 Gradle / Step 3~4 매니페스트·리소스 / Step 5~12 A7→계약→A3→A4→A5→A2→클라이언트→A1·A6
(의존 방향 안쪽부터) / Step 13~14 단위 테스트 5종 + 구조 테스트 / Step 15 `Dockerfile.build` / Step 16 문서
→ **약 35개 파일**

### ⚠️ ProGuard 주의 기록
R8 이 `@JavascriptInterface` 메서드를 제거하면 **release 빌드에서만 브리지가 죽는다.**
`proguard-rules.pro` 에 유지 규칙을 반드시 넣는다 (Step 2).

---

## Code Generation (u3-trip-android) — APPROVED & EXECUTED
**Timestamp**: 2026-08-14T21:20:00Z
**User Input**: "진행"
**AI Response**: "Step 1~16 전건 실행. 컨테이너 빌드·테스트 **실측 성공**. 파일 33개."
**Context**: CONSTRUCTION - Code Generation (u3) / Part 2 — 승인 게이트 **10/12**

### 실측 결과
| 검증 | 결과 |
|---|---|
| 이미지 빌드 | ✅ Gradle 8.11.1 + Android SDK 35 + Build-Tools 35.0.0 |
| Kotlin 컴파일 | ✅ 오류 0건 (경고 2건 — 플랫폼 deprecation) |
| 단위 테스트 | ✅ **47 passed / 0 failed** (2.9초) |
| `assembleDebug` | ✅ `android/out/app-debug.apk` **4.18 MB** |

### 🔴 CON-6 / ASM-4 해소
컨테이너에서 APK 가 실제로 만들어졌다. Workspace Detection 시점의 "APK 빌드 검증 불가" 판단과
ASM-4(사용자가 Android Studio 에서 빌드) 가정이 **둘 다 해소**됐다.

### 빌드 변형 분리 실측
- debug `BASE_URL` = `http://10.0.2.2:8200` / release `BASE_URL` = `""` (ABR-02 동작 확인)
- debug 병합 매니페스트에 `networkSecurityConfig` **있음** / release 에 **없음** → ABR-04 성립
- `-PcleartextHost=192.168.0.10` 주입 시 생성 XML 도메인 3 → 4
- `-PbaseUrl` 주입 시 `BuildConfig.BASE_URL` 반영

### 생성 중 발견·수정 5건
1. `bridgeReady` 를 u2 가 소비하지 않음 → 계약 유지 + 수신부 존재 가드, 주석 명시
2. u2 위치 타임아웃 10초와 경합 → u3 를 **8초**로
3. AD-1 `DownloadManager` 정책 밖 → 시스템 브라우저 폴백
4. 🔴 **`StructureTest` 오탐 2건** — 매니페스트 주석의 `usesCleartextTraffic`,
   로그 **문자열**의 `@JavascriptInterface`. `stripXmlComments()` 추가 + 로그 문구 변경.
   **u2 의 `design-rules.test.ts` 에서 겪은 것과 같은 유형이 반복됐다.**
   교훈: 주석뿐 아니라 **문자열 리터럴**도 오탐원이다.
5. `gradle-wrapper.jar` 바이너리 부재 → 컨테이너가 Gradle 배포판 직접 설치

### ⚠️ 빌드 오류 1건
`settings.gradle.kts` 의 `includeGroupByRegex` 이스케이프 손상으로 스크립트 컴파일 실패.
저장소 필터링은 최적화일 뿐이므로 제거하고 `google()` 로 단순화.

### 🔴 자동 검증 한계 (재확인)
컨테이너 빌드 성공 = 컴파일·패키징 가능. **동작 보증이 아니다.**
평문 차단·다운로드 무시·`window.open` 무시·위치 미회신은 전부 컴파일을 통과한다.
→ `android/README.md` 의 **실기기 확인 체크리스트 8항목**이 유일한 검증 수단.

---

## Build and Test — EXECUTED
**Timestamp**: 2026-08-14T22:40:00Z
**User Input**: "진행"
**AI Response**: "전 유닛 빌드·테스트 실측. **실제 결함 6건 발견·수정**, 의존성 취약점 16건 해소, I-1~I-14 전건 통과."
**Context**: CONSTRUCTION - Build and Test / Step 1~6

### 실측 요약
| 항목 | 결과 |
|---|---|
| 단위 테스트 | ✅ **360 passed / 0 failed** (u1 234 · u2 79 · u3 47) |
| 이미지 빌드 | ✅ `trip-app:latest` **285MB** |
| 통합 검증 | ✅ **I-1 ~ I-14 전건 통과** |
| 의존성 취약점 | ✅ Python 13→0, npm 3 high→0 |

### 🔴 발견한 실제 결함 6건 (전부 수정·재검증)
1. **`SensitiveFilter` 가 모든 로그 인자를 `str()` 로 변환** → `%d` 로그가 TypeError.
   `Filter` 는 `emit()` 의 try/except 밖에서 돌아 **예외가 호출부로 튀어나간다.**
   httpx 가 요청마다 `%d` 를 쓰므로 사실상 전 API 500. u1 테스트 35건 이상이 이것 하나로 실패.
   → 문자열 인자만 마스킹 + `JsonFormatter` 2차 방어. 회귀 테스트 11건 추가.
2. **`CacheRepository.get()` naive/aware datetime 비교** → 캐시를 **읽을 때마다** TypeError.
   SQLite 는 tz 를 저장하지 않는다. 쓰기는 성공해서 증상이 늦게 드러난다. → `_as_utc()`.
3. **`optimize()` 가 `len<=2` 에서 입력 순서 반환** → 비대칭 행렬에서 2개짜리 하루가
   절대 재정렬되지 않는다. **오류가 나지 않는다.** PBT P-09 완전탐색 오라클이 잡았다. → `len<=1`.
4. **영업시간이 저장되지 않음** — `opening_hours_to_row()` 가 **아무도 호출하지 않는 죽은 코드**였다.
   PUT 이 200 을 돌려주고 값은 사라진다. FR-13 무력. → 저장 경로에 병합 추가, 컨테이너에서 왕복 확인.
5. **`.env` 없이 `docker compose up` 실패** — `env_file` 에 `required: false` 누락.
   FR-33/I-10 의 "자격증명 없이 목 모드" 와 정면 충돌. → `required: false`.
6. **마스킹이 토큰을 남김** — `Authorization: Bearer <토큰>` 에서 "Bearer" 를 값으로 보고 가린 뒤
   **토큰을 그대로 로그에 남겼다.** 파이썬 repr 형태(`'api_key': 'v'`)도 미인식. → 패턴 개정.

### 수정한 테스트 결함 6건
BR-25 최소시간 기대값(600→602) / P-21 유니코드 대문자 비가역성 / P-22 좌표 범위 이탈 /
P-22 반올림 경계 / P-19 ICS 는 단독 CR 을 표현할 수 없음 / config 벤더명 오탐.
→ **통과시키려 기대값만 바꾸지 않고**, 왜 원래 주장이 성립하지 않는지를 각 파일에 기록.

### 🔴 의존성 조치 (SEC-10 blocking)
- **starlette 0.41.3 → 1.6.0** (CVE 7건, 런타임 의존성). fastapi 0.115.6 → **0.141.1** 동반.
- pytest 8.3.4 → 9.0.3, pytest-asyncio 0.25.0 → 1.3.0, pip 25.0.1 → 26.2.1 (Dockerfile `--upgrade pip`).
- **react-router-dom 7.1.1 → 7.18.2** (high 3건 / 권고 14건, 동일 메이저).
  `<Link>`/`useNavigate` 백슬래시 오픈 리다이렉트는 SSR 없이 써도 해당된다.
- 업그레이드 후 u1 234건 · u2 79건 전부 통과. 코드 수정 불필요.

### I-2 다이제스트 고정 → **SEC-10 완결**
`node:24-alpine@sha256:d32cdf61…` · `python:3.12-slim@sha256:2c941e86…` ·
`eclipse-temurin:17-jdk-noble@sha256:f8857ccb…`

### ⚠️ 환경 이슈 1건 (문서화)
Windows Git Bash 에서 `-v "/c/..."` 형식 바인드 마운트가 **조용히 무시**된다.
이미지 안의 옛 소스로 빌드돼 같은 오류가 반복됐다. → `MSYS_NO_PATHCONV=1` + Windows 절대경로.
`build-instructions.md` 문제 해결 절에 기록.

### 🔴 검증하지 못한 범위 (정직 기록)
실 API 연동(자격증명 없음) · 지도 실제 렌더링(NCP 키 없음) · **안드로이드 앱 실동작**(기기 없음).
u3 의 대표 실패 4종은 전부 컴파일을 통과하므로 `android/README.md` 의
**실기기 확인 체크리스트 8항목**이 유일한 검증 수단이다.

### 산출물
`construction/build-and-test/` — `build-instructions.md` · `unit-test-instructions.md` ·
`integration-test-instructions.md` · `performance-test-instructions.md`(N/A 판정) ·
`test-results.md` · `sbom/{backend,web}-sbom.json`

---

## Operations — EXECUTED
**Timestamp**: 2026-08-14T23:30:00Z
**User Input**: "진행해주세요"
**AI Response**: "Operations 는 룰셋상 플레이스홀더. 향후 범위를 이 프로젝트에 맞게 채우고, **README 가 약속한 스크립트 4종을 실제로 검증**했다."
**Context**: OPERATIONS

### 룰셋 상태
AI-DLC v1.0.1 의 `operations/operations.md` 는 **플레이스홀더**이며
"워크플로가 CONSTRUCTION 의 Build and Test 로 끝난다" 고 명시한다.
따라서 정해진 산출물 형식이 없다. 룰셋이 제시한 향후 범위
(배포·모니터링·장애 대응·유지보수·프로덕션 준비도)를 이 프로젝트에 맞게 작성했다.

### 🔴 발견한 결함 4건 — README 가 약속한 도구가 동작하지 않았다

**결함 1 — `build-android.sh` / `.ps1` 이 항상 실패**
`android/gradlew` 존재를 확인하는데, 래퍼 JAR 은 **바이너리라 의도적으로 두지 않았다**
(컨테이너가 Gradle 을 설치한다). 그 결과 스크립트가 즉시 종료되면서
`"u3-trip-android 가 아직 생성되지 않았습니다"` 라는 **사실과 다른 메시지**를 냈다.
→ 검사 대상을 `settings.gradle.kts` 로 변경. 소스 마운트 추가.
　`BASE_URL` 인자를 받아 실기기 빌드까지 지원하도록 확장.

**결함 2 — Git Bash 에서 도커 마운트가 조용히 무시됨**
MSYS 가 `/c/...` 경로를 변환하지 못해 마운트가 **오류 없이** 실패한다.
이미지 안의 옛 소스로 빌드되어 "고쳤는데 왜 그대로지" 상황이 반복됐다.
→ `uname` 으로 MSYS 를 감지해 `pwd -W` 로 경로를 변환하고 `MSYS_NO_PATHCONV=1` 을 설정.

**결함 3 — 🔴 모든 `.ps1` 이 Windows PowerShell 5.1 에서 파싱 실패**
UTF-8 BOM 이 없어 한글 주석이 cp949 로 잘못 해석되고 **구문 오류**가 났다.
`backup-db.ps1` 포함 **3개 전부** 해당. 사용자가 Windows 이므로 README 의 안내를 그대로
따라하면 전부 실패했을 것이다.
→ 3개 파일에 UTF-8 BOM 추가. `Parser::ParseFile` 로 전부 검증.

**결함 4 — PowerShell 5.1 의 네이티브 stderr 처리**
① `build-android.ps1` 의 `$ErrorActionPreference = "Stop"` 때문에 `docker build` 의
　**진행 로그(stderr)** 만으로 스크립트가 죽었다. → `"Continue"` + `$LASTEXITCODE` 판정.
② `audit-deps.ps1` 에서 `pip-audit` 의 정상 메시지("No known vulnerabilities found")가
　빨간 ErrorRecord 로 표시됐다. → 컨테이너 **안에서** `2>&1` 로 합침.

### 검증 (전부 실행해서 확인)
| 스크립트 | Bash | PowerShell |
|---|---|---|
| `build-android` | ✅ APK 생성 | ✅ APK 생성 |
| `audit-deps` | ✅ 취약점 0 + 다이제스트 비교 | ✅ 동일 |
| `backup-db` | ✅ 백업 파일 생성 | ✅ 백업 파일 생성 |
| `generate-sbom.py` | ✅ 430 컴포넌트 | (동일 스크립트) |

### 개선 — `audit-deps` 에 다이제스트 드리프트 점검 추가
고정한 `@sha256:` 과 현재 태그가 가리키는 값을 비교한다.
다이제스트 고정은 재현성을 위한 것이지 "영원히 안 바꾸겠다"는 뜻이 아니다.
고정만 하고 갱신하지 않으면 알려진 취약점을 안고 가게 되므로 점검 수단을 넣었다.

### 산출물
- `aidlc-docs/operations/operations-guide.md` (302줄) — 10개 절:
  시스템 성격 · 일상 운영 · 백업/복구 · 실 API 전환 · 비용 통제 · 유지보수 ·
  장애 대응 · 안드로이드 · 프로덕션 준비도 · 알려진 제약
- `scripts/` 4종 수정 (sh 2 · ps1 3, BOM 포함)
- `README.md` 갱신 — `--factory` 기동 정정, `.env` 선택 사항 명시, 문서 표 확장

### README 정정 사항
- `uvicorn app.main:app` → **`uvicorn app.main:create_app --factory`**
  (모듈 수준 `app` 을 제거했으므로 기존 안내로는 기동 불가였다)
- "`.env` 를 만들고 시작" → **`.env` 없이 바로 기동** (Build and Test 의 `required: false` 반영)
- "u1 만 있는 현재 상태" 등 옛 표현 정리
