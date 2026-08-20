# Code Generation Plan — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 1 (Planning), Unit 2/3
**Created**: 2026-08-14T01:20:00Z
**Status**: ⛔ 승인 대기 중

> **이 문서는 Code Generation 의 단일 진실 공급원입니다.**
> Part 2 는 아래 단계를 **순서대로, 쓰여 있는 대로만** 실행합니다.

---

## 1. 유닛 컨텍스트

| 항목 | 내용 |
|---|---|
| **유닛** | `u2-trip-web` |
| **코드 위치** | `c:\Users\403\IDE\trip\web\` — **`aidlc-docs/` 에 코드 금지** |
| **문서 위치** | `aidlc-docs/construction/u2-trip-web/code/` (마크다운만) |
| **언어·런타임** | TypeScript / Node.js 24 (빌드 시에만) |
| **프레임워크** | React 19 · Vite · TanStack Query · Zustand · @dnd-kit |
| **테스트** | Vitest · **fast-check**(PBT-R5) · Testing Library |
| **의존 유닛** | u1 (OpenAPI 스키마 — 빌드 시 타입 생성, UD-3) |
| **후속 유닛에 제공** | 브리지 계약 3종 + 호스팅 URL (u3) |

### 구현 대상

| 구분 | 수량 |
|---|---|
| 컴포넌트 | W1~W16 (16종) |
| 비즈니스 규칙 | WBR-01 ~ WBR-42 (42건) |
| 검증 속성 | WP-01 ~ WP-11 (11종) |
| Owner FR | 15건 (+ 참여 14건의 화면) |
| 소비 엔드포인트 | **20개** (A-1 포함) |

---

## 2. 🔴 u1 개정 A-1 — `GET /api/config` (Step 1 에서 선행)

u2 는 지도 SDK 키를 이 엔드포인트로 받습니다. **u2 코드보다 먼저 추가해야** 타입 생성이 가능합니다.

| 항목 | 내용 |
|---|---|
| 경로 | `GET /api/config`, 등급 `CHEAP` |
| 응답 | `map_client_key` · `modes` · `limits{max_trip_days, max_items_per_day, max_items_per_trip}` |
| 포함하지 않는 것 | **검색·LLM 키** (SEC-11) |
| 외부 호출 | 없음 |
| 영향 | u1 엔드포인트 19 → 20. `application-design/component-methods.md` §7 갱신 |
| 변경 파일 | `backend/app/api/routers/config.py`(신규) · `routers/__init__.py` · `api/schemas.py` · 테스트 1건 |

**승인된 u1 코드를 변경하므로** 변경 내역을 `code-summary.md` 와 `audit.md` 에 명시합니다.

---

## 3. 생성 원칙 (전 단계 공통)

| # | 원칙 | 근거 |
|---|---|---|
| 1 | `generated.ts` 를 손으로 고치지 않는다. **저장소에 커밋한다** | WBR-01, UD-3 |
| 2 | 서버가 소유하는 개념을 다시 정의하지 않는다 | WBR-02 |
| 3 | Zustand 에 **서버 데이터를 담지 않는다** | WBR-03 |
| 4 | 🔴 **서버가 산출한 값을 다시 계산하지 않는다** (시각·이동시간·경고) | WBR-04 |
| 5 | 편집 응답으로 캐시를 직접 갱신하고 추가 GET 을 하지 않는다 | WBR-14 |
| 6 | 추정 이동시간에는 **반드시 "추정" 배지**를 붙인다 | WBR-22, CON-1 |
| 7 | 딥링크 URL 생성은 **W13 한 곳에만** 둔다 | WBR-28, DD-11 |
| 8 | 웹/앱 분기는 **W14 한 곳에만** 둔다 | DD-11 |
| 9 | 공유 화면 트리에 **편집 컴포넌트를 넣지 않는다** (숨기는 것이 아님) | DD-25 |
| 10 | 인라인 `<script>` 를 만들지 않는다 (CSP `script-src`) | SEC-04 |
| 11 | 폼 상한은 `/api/config` 의 `limits` 를 쓰고 숫자를 하드코딩하지 않는다 | WBR-10 |
| 12 | 테스트는 네트워크에 의존하지 않는다 (MSW/목 클라이언트) | NFR-10 |
| 13 | PBT 는 셰링킹 활성 + 시드 로깅 | PBT-08 |
| 14 | 각 파일 상단에 담당 컴포넌트 ID(W)와 주요 WBR 을 주석으로 명시 | 추적성 |

---

## 4. 실행 단계 (15단계)

### 🔹 Step 1. u1 개정 A-1 적용 ✅
- [x] `backend/app/api/schemas.py` — `RuntimeConfigOut` · `LimitsOut` 추가
- [x] `backend/app/api/routers/config.py` — `GET /api/config` (신규)
- [x] `backend/app/api/routers/__init__.py` — 라우터 등록
- [x] `backend/tests/unit/test_api_config.py` — **9건**. 응답 스키마·본문·라우터 소스에 비밀 값 부재 검증
- [x] `python -m compileall` 확인

### 🔹 Step 1b. 🔴 실기동 검증에서 발견한 결함 2건 수정 (계획 외 — 사용자 승인 후 추가) ✅
- [x] **`main.py` import 부작용 제거** — 모듈 수준 `app = create_app()` 삭제, `uvicorn --factory` 전환, `Dockerfile` CMD 갱신
- [x] **개정 A-2: 응답 모델 17종 추가** — `TripOut`·`ReadOnlyTripOut`·`ItineraryItemOut`·`PlaceOut`·`CoordinateOut`·`OpeningHoursOut`·`DayRuleOut`·`ItemWarningOut`·`TripDayOut`·`UnresolvedOut`·`JobStatusOut`·`PagedPlacesOut`·`SuggestionsOut`·`PlaceContentOut`·`BlogRefOut`·`ImageRefOut`·`ShareTokenOut`·`QuotaUsageOut`
- [x] 라우터 19곳에 `response_model` 부여 (trips 9 · generation 1 · places 3 · share 2 · health 2 · config 1 · 기존 1)
- [x] **실측 확인: 타입 있는 응답 19 / 무타입 0** (이전 2 / 17)
- [x] `component-methods.md` §7 문서 드리프트 정정 (19 → 22 오퍼레이션)

### 🔹 Step 2. 프로젝트 구조·빌드 설정 ✅
- [x] `web/package.json` — 의존성 **정확한 버전 고정**(SEC-10), 스크립트 8종
- [x] `web/tsconfig.json` — strict + `noUncheckedIndexedAccess`
- [x] `web/vite.config.ts` — 포트 **5273**, `/api` 프록시 → 8200, `manualChunks` 코드 분할
- [x] `web/index.html` — **인라인 스크립트 없음 + 사유 주석**(SEC-04)
- [x] `web/vitest.config.ts` · `web/tests/setup.ts` — fast-check 전역 설정 + **실 `fetch` 호출 시 즉시 실패**(NFR-10)
- [ ] `web/.gitignore` — 루트 `.gitignore` 로 충분. Step 15 에서 재확인

### 🔹 Step 3. API 계약 (W1) — 부분 완료
- [x] `web/openapi.json` — **u1 을 python:3.12 컨테이너에서 실기동해 추출** (커밋 대상, `gen:api` 재현용)
- [x] `src/shared/api/generated.ts` — `openapi-typescript@7` 로 생성. **1,650줄, 실제 타입**. 커밋 대상
- [x] `src/shared/api/types.ts` — 생성 타입의 **이름 별칭만** (WBR-01·02). 구조 재정의 없음
- [x] `src/shared/api/client.ts` — W1. Problem Details 파싱, `credentials: omit`, 엔드포인트 래퍼 19종
- [x] `src/shared/api/errors.ts` — `ApiError` + `describeError` 조립 (WBR-33·34)

### 🔹 Step 4. 인프라 (W2, W3) ✅
- [x] `src/shared/query/keys.ts` — 캐시 키 팩토리 + `isPersistable` (WBR-15)
- [x] `src/shared/query/queryClient.ts` — W2. **`shouldDehydrateQuery` 로 `['trip', *]` 만 persist**(DD-14)
- [x] `src/shared/store/uiStore.ts` — W3. **서버 데이터 미포함**(WBR-03), `selectItem` 이 탭과 무관(WBR-18)
- [x] `src/shared/config/RuntimeConfigProvider.tsx` — `/api/config` 1회 조회 + `FALLBACK_LIMITS`(WBR-32·31)
- [x] `src/shared/storage/tripList.ts` — `localStorage` 목록 (WBR-05·09)

### 🔹 Step 5. 순수 함수 (PBT 대상) ✅
- [x] `src/shared/deeplink/index.ts` — W13. `placeUrl`·`routeUrl`·`encodeParams`·`decodeParams`·`routeSegment` (WBR-28)
- [x] `src/shared/selectors/trip.ts` — 합계·필터·판정만. **재계산 없음**(WBR-04·20·21·22·25·30)
- [x] `src/shared/selectors/polling.ts` — `nextPoll`·`isTerminal`·`stepLabel` (WBR-11·12·13)
- [x] `src/shared/storage/tripListExport.ts` — `exportList`·`parseExport`·`mergeLists`(멱등) (WBR-07·08)

### 🔹 Step 6. 순수 함수 테스트 (PBT + 예제) ✅ — **실제 실행 완료**
- [x] `tests/property/generators.ts` — 도메인 생성기 **8종** (PBT-07)
- [x] `tests/property/deeplink.property.test.ts` — **WP-01 ~ WP-04** + 프로토타입 키 회귀
- [x] `tests/property/tripList.property.test.ts` — **WP-05, WP-06**(멱등) + 형식 검증 4건
- [x] `tests/property/selectors.property.test.ts` — **WP-07 ~ WP-09**
- [x] `tests/property/polling.property.test.ts` — **WP-10, WP-11** + 회귀 1건
- [x] `tests/unit/deeplink.test.ts` — 경계 예제(한글·앰퍼샌드·물음표·좌표 정밀도)
- [x] 🔴 **실행 결과: 52 passed / 0 failed, 10회 연속 통과. `tsc --noEmit` 오류 0건**
- [x] 🔴 **PBT 가 결함 1건 발견** — `stepLabel` 프로토타입 오염(반례 `"toString"`). 같은 부류 2곳 수정

### 🔹 Step 7. 인프라 요약 문서 ✅
- [x] `code/infra-summary.md` — 결함 3건·WP 현황·구조 규칙 매핑

### 🔹 Step 8. 공용 UI·오프라인·브리지 (W14, W15, W16) ✅
- [x] `src/shared/ui/index.tsx` — W16. Button·Badge·Banner·Skeleton·Sheet·ToastHost·EmptyState (NFR-6)
- [x] `src/shared/offline/useOnlineStatus.ts` — `navigator.onLine` + **실제 요청 실패 관찰** 병행
- [x] `src/shared/offline/OfflineGate.tsx` — W15. 편집 차단 + 복귀 시 재검증 (WBR-35·36)
- [x] `src/shared/bridge/protocol.ts` — **u3 와 공유하는 메시지 5종**(UD-4). 문서가 단일 진실 공급원임을 명시
- [x] `src/shared/bridge/index.ts` — W14. **브리지 → 앱 스킴 → 웹** 3단 폴백 (WBR-27)
- [x] `client.ts` 에 `reportOffline`/`reportOnline` 연결 — 오프라인 감지를 실제 요청 결과에 기반

### 🔹 Step 9. 지도 (W4, W5) ✅
- [x] `src/features/map/loadSdk.ts` — 지연 로딩 + **실패 사유 4종 구분**. `navermap_authFailure` 로 **도메인 미등록**을 별도 포착 (WBR-40·41)
- [x] `src/features/map/NaverMapAdapter.tsx` — W4. **SDK 명령형 API 를 여기에만 가둠**(DD-18). 번호 SVG 마커
- [x] `src/features/map/MapView.tsx` — W5. 도메인 → 선언적 props 변환. **SDK 를 전혀 모른다**
- [x] `src/features/map/MapLegend.tsx` — 일자 색 + **텍스트 라벨 병기**, 점선=추정 설명 (WBR-23·24)
- [x] ~~`MapFallback.tsx`~~ — 어댑터 내부 분기로 충분해 별도 파일 미생성
- [x] `tsc --noEmit` 오류 0건 / `vitest` 52 passed 유지

### 🔹 Step 10. 화면 — 목록·생성 (W6)
- [ ] `src/features/trip-list/TripListPage.tsx` + `TripCard.tsx` + `LocalStorageNotice.tsx` + `ListExportImport.tsx` (WBR-06~09)
- [ ] `src/features/trip-create/TripCreateWizard.tsx` + 단계 5종 (WBR-10)

### 🔹 Step 11. 화면 — 생성 진행·타임라인 (W7, W8)
- [ ] `src/features/generation/GenerationProgress.tsx` — 단계 라벨 6종 (WBR-11·13)
- [ ] `src/features/generation/UnresolvedPanel.tsx` — **접이식 상시 노출**(WBR-25·26·29)
- [ ] `src/features/timeline/TimelineView.tsx` — W8. @dnd-kit, 키보드 지원 (WBR-17·37)
- [ ] `src/features/timeline/ItemCard.tsx` · `LegRow.tsx` — **"추정" 배지**(WBR-22), 경고 배지 4종(WBR-21)
- [ ] `src/features/timeline/DayTabs.tsx` · `DayHeader.tsx`

### 🔹 Step 12. 화면 — 장소·공유 (W9, W10, W11, W12)
- [ ] `src/features/place/PlaceDetailPanel.tsx` — W9. **highlights 비면 요약 영역 미렌더**(BR-40 대응)
- [ ] `src/features/place/PlaceSearchPanel.tsx` — W10. 5건 페이징 (FR-6)
- [ ] `src/features/place/RecommendationPanel.tsx` — W11 (FR-22)
- [ ] `src/features/share/SharedTripView.tsx` — W12. **편집 컴포넌트를 트리에 넣지 않음**(DD-25)

### 🔹 Step 13. 조립 (라우팅·App)
- [ ] `src/router.tsx` — 라우트 4종 + 코드 분할 (WBR-42)
- [ ] `src/App.tsx` — Provider 중첩 + DemoModeBanner (WBR-30)
- [ ] `src/features/trip-workspace/TripWorkspace.tsx` — ResponsiveSplit (WBR-18·39)
- [ ] `src/main.tsx`

### 🔹 Step 14. 컴포넌트·구조 테스트
- [ ] `tests/unit/tripList.test.ts` · `offline.test.ts` · `errors.test.ts`
- [ ] `tests/component/timeline.test.tsx` — 드래그(키보드 포함), 경고 배지
- [ ] `tests/component/unresolved.test.tsx` — 미해결 표시·[직접 검색해 담기]
- [ ] `tests/component/mapAdapter.test.tsx` — 목 SDK 로 props 반영 검증
- [ ] `tests/structure/shared-view.test.tsx` — 🔴 **공유 화면 트리에 편집 컴포넌트 부재**
- [ ] `tests/structure/no-hardcoded-limits.test.ts` — 🔴 폼 상한 하드코딩 부재 (WBR-10)
- [ ] `tests/structure/deeplink-single-source.test.ts` — 🔴 `nmap://` 리터럴이 W13 밖에 없음 (WBR-28)
- [ ] `tests/structure/no-inline-script.test.ts` — 🔴 `index.html` 에 인라인 스크립트 부재 (SEC-04)

### 🔹 Step 15. 요약 문서
- [ ] `code/components-summary.md` — 화면·컴포넌트 구현 요약
- [ ] `code/code-summary.md` — 파일 목록·조정 사항·**미검증 항목**·FR/WBR/WP 추적성

---

## 5. 추적성 계획

| 대상 | 검증 방법 |
|---|---|
| Owner FR 15건 | 파일 주석 + `code-summary.md` 매핑표 |
| WBR-01 ~ WBR-42 | 구현 위치 매핑표 |
| WP-01 ~ WP-11 | PBT 테스트 함수 1:1 |
| SEC 부분 책임 5건 | 구현 지점 명시 |
| API 20개 | 소비 지점 매핑 |

---

## 6. 예상 규모

| 구분 | 예상 파일 수 |
|---|---|
| 빌드 설정 | 7 |
| `src/shared/` | 22 |
| `src/features/` | 28 |
| 진입점·라우팅 | 3 |
| 테스트 | 18 |
| u1 개정(A-1) | 4 |
| 문서 | 3 |
| **합계** | **약 85개** |

**예상 세션**: 2~3

---

## 7. 알려진 미확정 사항

| # | 항목 | 격리 | 해소 |
|---|---|---|---|
| 1 | **지도 SDK 스크립트 URL·전역 객체 형태** | `features/map/loadSdk.ts` 단일 파일 | Build & Test — 실 로딩 |
| 2 | **CSP 허용 도메인 충분성** | u1 `security_headers.py` 상수 | Build & Test — 콘솔 위반 확인 |
| 3 | 의존성 버전의 실제 설치 가능 여부 | `package.json` | Build & Test — `npm ci` |
| 4 | `generated.ts` 실제 생성 결과 | — | u1 기동 후 `npm run gen:api` |
| 5 | 번들 크기 1MB 목표 달성 여부 | — | Build & Test — 빌드 산출물 측정 |

> ⚠️ **`generated.ts` 는 u1 을 실제로 기동해야 만들 수 있습니다.**
> Part 2 에서 u1 을 로컬 기동해 스키마를 뽑고, 실패하면 **수기 타입으로 대체하지 않고** 그 사실을 보고합니다.

---

## 8. 승인 요청

**15단계, 약 85개 파일.** Part 2 진행 시:
- 단계를 순서대로 실행하고 완료 즉시 `[x]` 표시
- 계획에 없는 것을 만들지 않음
- 코드는 `trip/web/`(+ A-1 은 `trip/backend/`)에만, 문서는 `aidlc-docs/` 에만
- **테스트는 작성하되 실행은 Build & Test 스테이지**
