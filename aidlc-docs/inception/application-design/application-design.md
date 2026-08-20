# Application Design — trip (통합 문서)

**Stage**: 🔵 INCEPTION - Application Design
**Created**: 2026-08-13T04:35:00Z
**Status**: 승인 대기

**구성 문서**
| 문서 | 내용 |
|---|---|
| [components.md](components.md) | 컴포넌트 56종 정의 · 책임 · 인터페이스 · FR 커버리지 · SEC 소유자 |
| [component-methods.md](component-methods.md) | 메서드 시그니처 · 입출력 타입 · API 엔드포인트 계약 · 브리지 계약 |
| [services.md](services.md) | 서비스 경계 · 오케스트레이션 흐름 · 실패 처리 · 상태 소유권 |
| [component-dependency.md](component-dependency.md) | 계층 규칙 · 의존성 그래프 · 순환 검증 · 데이터 흐름 |
| 본 문서 | 답변 분석 · 설계 결정(DD) 25건 · 검증 결과 · 이월 항목 |

---

## 1. 설계 입력 답변 분석 (규칙 Step 8)

`application-design-plan.md` Q1~Q16 = **전부 A**

### 1.1 모호성 검사
"mix of", "somewhere between", "not sure", "depends" 류 응답 **0건**. 모든 답변이 단일 선택지입니다.

### 1.2 모순 검사 — 4개 조합을 교차 검증

| 조합 | 검증 결과 |
|---|---|
| Q1(계층 패키지) × Q12(단방향 계층 규칙) | ✅ 상호 강화. 계층 구성이 곧 의존 규칙의 강제 수단 |
| Q2(Protocol 추상화) × Q3(주입 기반 목 모드) × Q11(캐시 데코레이터) | ✅ **동일한 이음매를 공유**. 셋 다 "클라이언트 인터페이스" 지점에서 작동하므로 합성 순서만 정하면 충돌 없음 → DD-6 |
| Q5(job 폴링) × Q13(TanStack Query) × Q16(Query persist) | ⚠️ **1건 주의**: job 상태까지 IndexedDB 에 persist 되면 재방문 시 완료된 진행률이 되살아남 → **DD-14 로 해소**(persist 제외 목록 지정) |
| Q10(순수 함수 도메인) × Q11(캐시) × Q22(네트워크 비의존 테스트) | ✅ 정합. 캐시가 클라이언트 계층에 있어 도메인 순수성을 침범하지 않음 |

**추가 질문이 필요한 모호성: 0건.** Q5×Q16 의 주의 사항은 설계 결정(DD-14)으로 해소했으며 사용자 판단이 필요한 성격이 아닙니다.

### 1.3 답변에서 도출된 파생 결정
사용자가 직접 답하지 않았으나 답변 조합에서 **논리적으로 따라 나오는** 결정 8건을 DD-6·7·8·14·21·22·23·24·25 로 명시했습니다. 이견이 있으면 승인 게이트에서 지적해 주세요.

---

## 2. 아키텍처 요약

```
+---------------------------------------------------------------------+
|                        u3-trip-android (Kotlin)                     |
|   A1 MainActivity  A2 WebViewConfigurator  A3 BridgeHandler         |
|   A4 IntentLauncher  A5 LocationProvider  A6 Offline  A7 AppConfig  |
+---------------------------------------------------------------------+
                    |  WebMessage (오리진 제한)  |  Intent (nmap://)
                    v                            v
+---------------------------------------------------------------------+
|                        u2-trip-web (React + TS)                     |
|                                                                     |
|  features/     W6 Wizard   W7 Progress   W8 Timeline                |
|                W9 PlaceDetail  W10 Search  W11 Recommend  W12 Share |
|                W5 MapView --> W4 NaverMapAdapter --> [Naver SDK]    |
|                                                                     |
|  shared/       W1 ApiClient   W2 QueryClient   W3 UiStore           |
|                W13 DeepLink   W14 Bridge   W15 Offline   W16 Ui     |
+---------------------------------------------------------------------+
                    |  REST (JSON) + job 폴링
                    v
+---------------------------------------------------------------------+
|                     u1-trip-backend (FastAPI)                       |
|                                                                     |
|  api/       C32 Routers            C33 Schemas                      |
|  services/  C25 Generation(orch)   C21 Trip   C22 LlmDraft          |
|             C23 PlaceResolver(!)   C24 TravelMatrix  C26 Search     |
|             C27 Recommend  C28 Job  C29 Quota                       |
|  domain/    C14 Models  C15 Timeline  C16 Matrix  C17 Estimator     |
|             C18 Optimizer  C19 OpeningHours  C20 Ics    [의존성 0]  |
|  clients/   C13 Factory  C12 Cache  C6 BaseHttp                     |
|             C7 Local  C8 Content  C9 Directions  C10 Geo  C11 Llm   |
|  storage/   C30 Database           C31 Repositories                 |
|  core/      C1 Config  C2 Logging  C3 Headers  C4 RateLimit  C5 Err |
+---------------------------------------------------------------------+
       |            |             |              |            |
       v            v             v              v            v
   [SQLite]  [NCP Directions] [네이버 검색] [NCP Geocoding] [Claude API]
```

---

## 3. 설계 결정 (DD-1 ~ DD-25)

### 사용자 답변 기반 (DD-1 ~ DD-5, DD-9 ~ DD-13, DD-15 ~ DD-20)

| ID | 결정 | 근거 | 효과 |
|---|---|---|---|
| **DD-1** | 백엔드는 **계층 기준 패키지**(`api`/`services`/`domain`/`clients`/`storage`/`core`) | Q1=A | `domain/` 격리로 PBT 가능 |
| **DD-2** | 외부 API 는 **Protocol + BaseHttpClient + 개별 구현체** | Q2=A | 재시도·타임아웃·계측이 한 곳 (NFR-2·3·4) |
| **DD-3** | 목 모드는 **C13 주입 시점에서만** 분기 | Q3=A | 서비스·도메인에 `if mock:` 0건 (FR-33) |
| **DD-4** | 프론트는 **기능(feature) 기준** 구성 + `shared/` | Q4=A | 화면 단위 응집 |
| **DD-5** | AI 생성은 **비동기 job + 폴링**(202 → `job_id`) | Q5=A | 60초 블로킹 회피, 진행 표시 (NFR-1) |
| **DD-9** | 오류 응답은 **RFC 9457 Problem Details** + `code`·`correlation_id` | Q6=A | 프론트 처리 일관성 (SEC-09, SEC-15) |
| **DD-10** | **OpenAPI → TypeScript 타입 자동 생성** | Q7=A | u1↔u2 계약 불일치를 컴파일 오류로 검출 |
| **DD-11** | `nmap://` URL 생성은 **W13 프론트 순수 함수 단일 소유** | Q8=A | 웹·앱 이중 구현 방지, 단위 테스트 용이 |
| **DD-12** | 생성 파이프라인은 **명시적 단계 구성**, 그라운딩은 **C23 독립 컴포넌트** | Q9=A | 최상위 위험 ①의 차단점을 직접 테스트 가능 |
| **DD-13** | 순서 최적화·타임라인 계산은 **I/O 없는 순수 함수**, 이동시간은 **행렬로 주입** | Q10=A | PBT-R2·R7 을 네트워크 없이 실행 (Q22=A) |
| **DD-15** | 외부 응답 캐시는 **클라이언트 데코레이터 + SQLite 저장** | Q11=A | 서비스가 캐시를 모름, 재기동 후에도 유지 (NFR-4·11) |
| **DD-16** | **단방향 계층 규칙**, `domain/` 은 의존성 0 | Q12=A | 순환 0건 (검증 완료) |
| **DD-17** | 프론트 상태는 **TanStack Query(서버) + Zustand(UI)** 로 분리 | Q13=A | 소유권 명확, FR-19 양방향 하이라이트 구현 단순화 |
| **DD-18** | 지도 SDK 는 **W4 어댑터로 격리**, 바깥에는 선언적 props 만 | Q14=A | 명령형 API 와 React 렌더링 충돌을 한 곳에 가둠 |
| **DD-19** | 안드로이드 브리지는 **`addWebMessageListener` + 오리진 허용목록**, 구형은 `@JavascriptInterface` 폴백 | Q15=A | 임의 페이지의 브리지 접근 차단 (SEC-08, SEC-11) |
| **DD-20** | 오프라인은 **Query persist → IndexedDB** | Q16=A | 별도 동기화 코드 최소화 (FR-31) |

### 파생 결정 (DD-6 ~ DD-8, DD-14, DD-21 ~ DD-25)

| ID | 결정 | 도출 근거 |
|---|---|---|
| **DD-6** | 캐시 데코레이터는 **실제 구현체에만** 적용. 목 구현체는 감싸지 않음 | Q2·Q3·Q11 조합. 목은 이미 결정적이라 캐시가 무의미하고, 테스트에 TTL 변수를 끌어들임 |
| **DD-7** | C12 → C31 `CacheRepository` 는 **Protocol 주입** | 계층 규칙 3. `clients/` 가 `storage/` 구체 타입에 묶이면 양방향 결합 발생 |
| **DD-8** | C6·C4 → C29 `QuotaService` 는 **계측 인터페이스 주입** | 동일. 클라이언트·코어가 서비스 구체 타입을 의존하지 않게 함 |
| **DD-14** | **`JobStatus` 는 IndexedDB persist 제외** | Q5×Q16 교차 검증에서 발견. 완료된 진행률이 재방문 시 되살아나는 문제 |
| **DD-21** | **`GET /api/trips`(전체 목록) 을 제공하지 않음.** 사용자의 여행 목록은 브라우저 로컬 저장소의 `TripId` 집합으로 구성 | Q16(인증 없음) + SEC-08. 계정 없는 상태의 목록 API 는 열거 취약점 |
| **DD-22** | `DirectionsClient` 에 **대중교통·도보 메서드를 정의하지 않음** | CON-1. 없는 기능을 인터페이스에 두면 호출자가 존재한다고 오해 |
| **DD-23** | job 상태에 **`partial` 을 도입** — 그라운딩 일부 실패, 이동시간 근사 폴백, 최적화 생략을 실패와 구분 | NFR-3 degrade 정책. 사용자에게 품질 저하를 구체적으로 알리기 위함 |
| **DD-24** | **근거(블로그 링크)가 없으면 AI 요약을 노출하지 않음** | CON-7. 근거 없는 요약은 환각 노출 경로 |
| **DD-25** | 공유 조회는 **편집 메서드가 없는 타입**(`ReadOnlyTrip`)을 반환 | CA-3. 타입 수준에서 쓰기를 차단해 실수를 컴파일 시점으로 이동 |

---

## 4. 설계 검증 결과

| 검증 항목 | 결과 |
|---|---|
| 컴포넌트 총계 | 56종 (u1 33 / u2 16 / u3 7) |
| **순환 의존성** | **0건** ✅ (`component-dependency.md` §4) |
| **FR 미매핑** | **0건** ✅ — FR-1~34 전부 최소 1개 컴포넌트에 매핑 (`components.md` §9) |
| **SEC 소유자 미지정** | **0건** ✅ — 13건 지정 + N/A 2건(SEC-02·06) (`components.md` §10) |
| `domain/` 외부 의존 | **0건** ✅ |
| 서비스 간 순환 호출 | **0건** ✅ |
| PBT 대상 컴포넌트 식별 | C14·C15·C16·C17·C18·C20·W13 — **7종** |
| Functional Design 이월 | **11건** (`component-methods.md` §10) |

---

## 5. Functional Design 이월 항목 (우선순위 순)

| # | 항목 | 유닛 | 우선도 |
|---|---|---|---|
| 1 | **C23 그라운딩 일치 판정 기준** (유사도 임계값·카테고리 정합·거리 허용 범위) | u1 | 🔴 |
| 2 | C22 LLM 응답 스키마 정의 및 재시도 정책 | u1 | 🔴 |
| 3 | C18 목적함수 가중치·2-opt 종료 조건·시간 상한 | u1 | 🟠 |
| 4 | C15 고정 시각 항목과 이동시간 충돌 처리 | u1 | 🟠 |
| 5 | C4 레이트 리밋 임계값·윈도·엔드포인트 등급 | u1 | 🟠 |
| 6 | A3 폴백 경로의 오리진 검증 구현 방식 | u3 | 🟠 |
| 7 | C12 캐시 키 정규화·무효화 조건 | u1 | 🟡 |
| 8 | C31 테이블 스키마·인덱스·제약 | u1 | 🟡 |
| 9 | 예외 분류 체계 및 사용자 노출 문구 매핑 | u1 | 🟡 |
| 10 | C17 보정계수·보행속도·대중교통 근사식 구체값 | u1 | 🟡 |
| 11 | W8 드래그 상호작용 세부 및 낙관적 업데이트 롤백 | u2 | 🟡 |

---

## 6. Compliance 요약

### Security Compliance (Blocking 확장)
준수 12 / 부분 준수 1(SEC-12 — 사용자 인증 N/A) / N/A 2(SEC-02·06) / 이월 1(SEC-10 → Infrastructure Design)
**Blocking security findings: 0건** ✅
상세: [services.md §7](services.md)

### PBT Compliance (Partial 모드)
blocking 5종(PBT-02·03·07·08·09) 중 3종 설계 완료·1종 확정·1종 Code Generation 이월. advisory 5종 중 2종 충족·2종 후보 없음·1종 이월
**Blocking PBT findings: 0건** ✅
상세: [services.md §8](services.md)

### Resiliency
확장 없음(사용자 opt-out). 단 재시도·타임아웃·폴백은 NFR-2·3 으로 C6·C24 에 자체 반영됨

---

## 7. 다음 단계

**Units Generation** — 본 설계의 컴포넌트 56종을 3개 유닛(`u1-trip-backend` / `u2-trip-web` / `u3-trip-android`)으로 공식 배정하고, 유닛 간 계약(OpenAPI 스키마, 브리지 메시지 3종, `BASE_URL`↔`BIND_HOST`)을 확정합니다.
