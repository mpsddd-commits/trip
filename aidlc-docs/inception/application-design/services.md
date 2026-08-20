# Services — trip

**Stage**: 🔵 INCEPTION - Application Design
**Created**: 2026-08-13T04:35:00Z

> **서비스 계층의 정의 (Q12=A)**: 서비스는 **외부 호출과 순수 도메인 로직을 조합**하는 계층입니다.
> 계산·판정 로직을 직접 갖지 않고 `domain/` 에 위임하며, 영속화는 `storage/` 에, 외부 호출은 `clients/` 에 맡깁니다.
> 이 규율이 깨지면 PBT 대상이 서비스로 새어나가 네트워크 없는 테스트가 불가능해집니다.

---

## 1. 서비스 목록과 경계

| 서비스 | 유형 | 핵심 책임 | 계산 로직 위임 대상 |
|---|---|---|---|
| **C25** `ItineraryGenerationService` | 오케스트레이터 | AI 생성 파이프라인 전 과정 조율 | C22·C23·C24·C18·C15 |
| **C21** `TripService` | 도메인 서비스 | 여행 생명주기, 식별자·공유 토큰 | — (CRUD 중심) |
| **C22** `LlmDraftGenerator` | 통합 서비스 | 프롬프트 구성, 응답 스키마 검증 | — |
| **C23** `PlaceResolver` 🔴 | 통합 서비스 | 장소명 → 실장소 그라운딩 | — (판정 규칙 자체가 책임) |
| **C24** `TravelMatrixService` | 통합 서비스 | 수단별 소스 선택, 행렬 조립 | C17(근사), C16(자료구조) |
| **C26** `PlaceSearchService` | 통합 서비스 | 검색·페이징·주변 후보 | — |
| **C27** `RecommendationService` | 통합 서비스 | 추천 콘텐츠 조립 | C22(요약) |
| **C28** `JobService` | 인프라 서비스 | 비동기 작업 수명 | — |
| **C29** `QuotaService` | 인프라 서비스 | 사용량 계측·상한 | — |

**오케스트레이터는 C25 하나뿐입니다.** 다른 서비스는 단일 관심사만 다루며, 서로를 직접 호출하지 않고 C25 가 조율합니다(예외: C27 이 C22 의 요약 메서드를 사용, C24 가 C17 을 사용 — 둘 다 하위 방향).

---

## 2. 주 오케스트레이션 — AI 일정 생성 (Q5=A + Q9=A)

이 흐름이 제품의 중심이자 **최상위 위험 ①(LLM 환각)의 차단 경로**입니다.

```
[사용자] --POST /trips/{id}/generate--> [C32 Router]
                                            |
                                            | C4 RateLimiter 통과 (SEC-11)
                                            v
                                     [C25 GenerationService.start]
                                            |
                                            | C28 JobService.enqueue
                                            v
                                     job_id 즉시 반환 (202)
                                            |
                    +-----------------------+------------------------+
                    |                                                |
             [프론트 W7]                                   [백그라운드 파이프라인]
                    |                                                |
          GET /jobs/{id} 폴링                                        v
                    |                              +--------------------------------+
                    |                              | 1. DRAFTING                    |
                    |<-----progress----------------|    C22 -> C11 LlmClient        |
                    |                              |    응답 스키마 검증 (SEC-13)   |
                    |                              +--------------------------------+
                    |                                                |
                    |                              +--------------------------------+
                    |                              | 2. RESOLVING             (핵심)|
                    |<-----progress----------------|    C23 -> C7 LocalSearch       |
                    |                              |    미해결 항목 분리 (FR-3)     |
                    |                              +--------------------------------+
                    |                                                |
                    |                              +--------------------------------+
                    |                              | 3. ROUTING                     |
                    |<-----progress----------------|    C24 -> C9 Directions / C17  |
                    |                              |    DistanceMatrix 조립         |
                    |                              +--------------------------------+
                    |                                                |
                    |                              +--------------------------------+
                    |                              | 4. OPTIMIZING (선택)           |
                    |<-----progress----------------|    C18 RouteOptimizer (순수)   |
                    |                              +--------------------------------+
                    |                                                |
                    |                              +--------------------------------+
                    |                              | 5. SCHEDULING                  |
                    |<-----progress----------------|    C15 TimelineCalculator (순수)|
                    |                              +--------------------------------+
                    |                                                |
                    |                              +--------------------------------+
                    |<-----succeeded / partial-----| 6. SAVING                      |
                    |                              |    C21 -> C31 TripRepository   |
                    v                              +--------------------------------+
        일정 + "확인 필요" 목록 표시
```

### 단계별 실패 처리 (NFR-3, SEC-15)

| 단계 | 실패 시 | job 상태 |
|---|---|---|
| 1 DRAFTING | LLM 스키마 검증 실패 → 제한 재시도 후 중단 | `failed` |
| 2 RESOLVING | **일부 미해결은 정상 경로** — 미해결 목록과 함께 진행. **전건 미해결이면 중단** | `partial` / `failed` |
| 3 ROUTING | Directions 실패 → C17 근사 폴백으로 계속 | `partial` (근사 플래그) |
| 4 OPTIMIZING | 시간 상한 초과 → 최적화 없이 입력 순서 유지 | `partial` |
| 5 SCHEDULING | 고정 시각 충돌 → 경고와 함께 계속 | `partial` |
| 6 SAVING | 저장 실패 → 전체 실패 (fail-closed) | `failed` |

> **`partial` 은 실패가 아니라 "일부 품질 저하"입니다.** 프론트(W7)는 이를 사용자에게 구체적으로 알려야 합니다 — "3곳을 찾지 못했습니다", "이동시간이 추정치입니다".

---

## 3. 보조 오케스트레이션

### 3.1 순서 최적화 (FR-8)

```
POST /trips/{id}/days/{d}/optimize
   |
   v
C21 TripService.get  -->  해당 일자 항목 목록
   |
   v
C24 TravelMatrixService.build_matrix  -->  DistanceMatrix (캐시 적중 시 외부 호출 0)
   |
   v
C18 RouteOptimizer.optimize (순수)  -->  재배열된 항목
   |
   v
C15 TimelineCalculator.compute (순수)  -->  시각 재산출
   |
   v
C21 TripService.reorder_items  -->  저장 후 Trip 반환
```
**동기 처리입니다.** 캐시된 행렬을 쓰면 외부 호출이 없어 NFR-1(500ms)을 지킬 수 있습니다.

### 3.2 항목 편집 후 타임라인 재계산 (FR-5, FR-7, FR-9)

순서·체류시간·이동수단이 바뀌면 **C15 만 다시 돌립니다.** 이동수단이 바뀐 경우에만 C24 의 단일 구간 재계산(`recompute_leg`)을 호출합니다 — 전체 행렬을 다시 만들지 않습니다(쿼터 절약, NFR-4).

### 3.3 추천 콘텐츠 (FR-20, FR-21)

```
GET /places/{id}/content
   |
   v
C27 RecommendationService.content_for
   |
   +--> C8 ContentSearchClient.search_blogs   (실패 시 빈 목록)
   +--> C8 ContentSearchClient.search_images  (실패 시 빈 목록)
   |
   v
   블로그 결과가 있으면 --> C22.summarize_place (LLM 요약)
   블로그 결과가 없으면 --> 요약 생략 (CON-7: 근거 없는 요약 금지)
   |
   v
PlaceContent {highlights, sources, images, is_ai_summary}
```
**degrade 규칙**: 이 경로의 어떤 실패도 장소 상세 화면 전체를 막지 않습니다. 실패한 섹션만 비어 있습니다.

### 3.4 공유 (FR-25, SEC-08)

```
POST /trips/{id}/share  -->  C21.issue_share_token  -->  {share_token, url}
GET  /shared/{token}    -->  C21.get_by_share_token -->  ReadOnlyTrip
DELETE /trips/{id}/share -> C21.revoke_share_token  -->  204
```
- `share_token` 은 `trip_id` 와 **독립된 값**입니다. 토큰을 알아도 `trip_id` 를 역산할 수 없어야 합니다
- `get_by_share_token` 은 **편집 메서드가 없는 타입**을 반환합니다 — 타입 수준에서 쓰기를 막습니다 (CA-3)
- 토큰 폐기 시 기존 링크는 즉시 무효화됩니다

---

## 4. 횡단 관심사의 적용 지점

| 관심사 | 적용 위치 | 서비스가 하지 않는 것 |
|---|---|---|
| 인증 정보 관리 | C1 → C13 | 서비스는 키를 직접 읽지 않습니다 |
| 실제/목 선택 | C13 (주입 시점) | 서비스에 `if mock:` 분기 없음 (Q3=A) |
| 캐시 | C12 (데코레이터) | 서비스는 캐시 존재를 모름 (Q11=A) |
| 재시도·타임아웃 | C6 | 서비스에 재시도 루프 없음 |
| 쿼터 계측 | C6 → C29 | 서비스가 카운터를 증가시키지 않음 |
| 레이트 리밋 | C4 (라우터 의존성) | 서비스 진입 전에 차단 |
| 보안 헤더 | C3 (미들웨어) | — |
| 오류 응답 변환 | C5 (전역 핸들러) | 서비스는 도메인 예외만 던짐 |
| 로깅·correlation | C2 | 서비스는 `get_logger` 만 사용 |
| 감사 로깅 | C21 → C31 `AuditLogRepository` | 변경 서비스만 기록 |

> 이 표가 **"서비스 코드가 짧아야 하는 이유"** 입니다. 서비스는 조율만 하고, 정책은 전부 바깥에 있습니다.

---

## 5. 프론트엔드 서비스 계층 (u2)

| 계층 | 담당 | 규칙 |
|---|---|---|
| **W1** `ApiClient` | HTTP 호출, 타입 안전성, Problem Details 파싱 | 컴포넌트가 `fetch` 를 직접 호출하지 않음 |
| **W2** `QueryClientSetup` | 서버 상태 캐시·재검증·폴링·IndexedDB persist | **서버 데이터의 유일한 소유자** (Q13=A) |
| **W3** `UiStore` | 선택·드래그·하이라이트 등 UI 상태 | **서버 데이터를 복제하지 않음** |

### 상태 소유권 경계 (Q13=A, Q16=A)

```
+-------------------------------------------------------------+
|  TanStack Query (W2)          |  Zustand (W3)               |
+-------------------------------+-----------------------------+
|  Trip / Place / PlaceContent  |  selectedDayIndex           |
|  PagedPlaces / suggestions    |  selectedItemId             |
|  JobStatus (persist 제외)     |  draggingOrder (임시)       |
|                               |  mapHighlightId             |
+-------------------------------+-----------------------------+
|  IndexedDB 에 persist         |  메모리에만 존재            |
|  -> 오프라인 조회 (FR-31)     |  -> 새로고침 시 초기화       |
+-------------------------------------------------------------+
```

**⚠️ DD-14**: `JobStatus` 는 persist 대상에서 제외합니다. 완료된 작업 상태가 IndexedDB 에 남으면 재방문 시 이미 끝난 진행률이 되살아납니다.

### 낙관적 업데이트 정책

드래그로 순서를 바꿀 때 화면은 즉시 반영하고(W3의 `draggingOrder`), 서버 응답이 오면 Query 캐시를 갱신합니다. 실패 시 원래 순서로 되돌리고 토스트로 알립니다. **오프라인 상태에서는 W15 `OfflineGate` 가 편집 자체를 차단**하므로 이 경로에 들어오지 않습니다 (FR-32).

---

## 6. u1 ↔ u2 ↔ u3 조율 계약

| 경계 | 계약 | 강제 수단 |
|---|---|---|
| u1 → u2 | OpenAPI 스키마 | **`openapi-typescript` 로 TS 타입 자동 생성** (Q7=A). 스키마가 바뀌면 타입 오류로 즉시 드러남 |
| u2 → u3 | 브리지 메시지 3종 (`openMap` / `share` / `requestLocation`) | `component-methods.md` §9 의 페이로드 정의. 양쪽에 동일 상수 정의 |
| u3 → u1 | `BuildConfig.BASE_URL` ↔ `BIND_HOST` | Infrastructure Design(u1)에서 환경별 조합표 작성 (CA-1) |

---

## 7. Security Compliance — Application Design 스테이지

| Rule | 판정 | 근거 |
|---|---|---|
| SEC-01 | ✅ 준수 | C6 TLS 강제 / C30 파일 권한. 루프백 예외는 CA-4 문서화 |
| SEC-02 | ⚪ N/A | 네트워크 중간자(LB/GW/CDN) 없음 |
| SEC-03 | ✅ 준수 | C2 가 구조화 로깅·correlation·마스킹 소유 |
| SEC-04 | ✅ 준수 | C3 미들웨어 |
| SEC-05 | ✅ 준수 | C33 스키마 검증 + C30 파라미터 바인딩 |
| SEC-06 | ⚪ N/A | IAM 리소스 없음 |
| SEC-07 | ✅ 준수 | C1 `BIND_HOST` 기본 루프백. 상세는 Infrastructure Design |
| SEC-08 | ✅ 준수 | C21 UUID·토큰 분리, C32 목록 API 미제공·CORS 화이트리스트, A3 오리진 제한 |
| SEC-09 | ✅ 준수 | C5 일반화 응답, A2 WebView 하드닝 |
| SEC-10 | ⏭ 이월 | 의존성 고정·스캔·SBOM → Infrastructure Design / Code Generation |
| SEC-11 | ✅ 준수 | C4 레이트 리밋, C13 자격증명 격리, C11↔C22 관심사 분리 |
| SEC-12 | ✅ 준수(부분) | 사용자 인증 N/A. 하드코딩 금지는 C1 이 소유 |
| SEC-13 | ✅ 준수 | C22 LLM 응답 스키마 검증(역직렬화 안전), C31 감사 로깅 |
| SEC-14 | ✅ 준수 | C2 90일 로테이션, C29 소진 이벤트, C31 추가 전용 감사 테이블 |
| SEC-15 | ✅ 준수 | C5 전역 핸들러, C6 외부 호출 예외 처리, C30 세션 정리 |

**Blocking security findings: 0건** ✅

---

## 8. PBT Compliance — Application Design 스테이지

| Rule | 판정 | 근거 |
|---|---|---|
| PBT-01 *(advisory)* | ✅ | 컴포넌트별 속성 후보를 `components.md`·`component-methods.md` 에 표기. 정식 "Testable Properties" 절은 Functional Design 에서 작성 |
| PBT-02 *(blocking)* | ⏭ 설계 완료 | 왕복 대상 식별 — C14 `to_dict`/`from_dict`, C20 `build`/`parse`, W13 `encodeParams` |
| PBT-03 *(blocking)* | ⏭ 설계 완료 | 불변식 대상 식별 — C15 단조성·개수 보존, C18 집합 보존·앵커 불변·비악화, C17 비음수·대칭성 |
| PBT-04 *(advisory)* | ⚪ 후보 없음 | 현 설계에 멱등성을 주장하는 연산 없음. Functional Design 에서 재평가 |
| PBT-05 *(advisory)* | ✅ | C18 `brute_force` 를 오라클로 정의 (n≤8) |
| PBT-06 *(advisory)* | ⚪ 후보 낮음 | 상태 컴포넌트는 C28 `JobService` 뿐이며 상태 전이가 선형. Functional Design 에서 재평가 |
| PBT-07 *(blocking)* | ⏭ 설계 완료 | 도메인 생성기 대상 확정 — `Coordinate`(국내 범위), `ItineraryItem`, `TripSpec`, `DistanceMatrix` |
| PBT-08 *(blocking)* | ⏭ Code Generation | 시드 로깅·셰링킹 설정은 코드 생성 시점 항목 |
| PBT-09 *(blocking)* | ✅ | Hypothesis(u1) / fast-check(u2) — `aidlc-state.md` Technology Stack 에 기록 완료 |
| PBT-10 *(advisory)* | ⏭ Code Generation | 예제 기반 테스트 병행은 코드 생성 항목 |

**Blocking PBT findings: 0건** ✅ (⏭ 는 해당 스테이지가 아직 오지 않은 항목으로, 미준수가 아닙니다)

**Resiliency**: 확장 없음(사용자 opt-out)
