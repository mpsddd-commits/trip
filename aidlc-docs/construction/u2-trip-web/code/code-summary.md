# Code Generation 종합 요약 — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 15 / 최종)
**Created**: 2026-08-14T19:35:00Z
**계획**: `construction/plans/u2-trip-web-code-generation-plan.md` — **15단계 전부 완료**

---

## 1. 🔴 u1 과 결정적으로 다른 점 — **실제로 실행했습니다**

u1 은 규칙상 테스트를 작성만 하고 실행은 Build & Test 로 미뤘습니다.
u2 는 `generated.ts` 생성을 위해 의존성 설치가 필요했고, 그 김에 **전 과정을 실측**했습니다.

| 검증 | 결과 |
|---|---|
| `npm install` | ✅ 330 패키지, **`package-lock.json` 생성 (SEC-10)** |
| `npx tsc -b --noEmit` | ✅ **오류 0건** |
| `npx vitest run` | ✅ **79 passed / 0 failed** (7 파일) |
| `npm run build` | ✅ **성공** — 143 모듈, 1.48초 |
| 반복 실행 | ✅ 10회 연속 통과 (시드 무작위) |

### 번들 크기 실측 (NFR-12 / WBR-42 — 목표 1MB gzip)

| 청크 | raw | gzip |
|---|---|---|
| `index` (앱 코드) | 186.4 kB | 60.7 kB |
| `query` (TanStack) | 46.6 kB | 13.9 kB |
| `vendor` (React·Router) | 44.0 kB | 15.9 kB |
| `index.css` | 12.3 kB | 3.0 kB |
| **초기 로드 합계** | **289 kB** | **≈ 93.5 kB** |
| `TripWorkspace` (지연) | 30.1 kB | 11.9 kB |
| `dnd` (지연) | 45.9 kB | 15.3 kB |

→ **목표의 약 9%.** 코드 분할이 동작해 목록·생성 화면에서 지도·드래그 코드를 내려받지 않습니다 (WBR-41).

---

## 2. 🔴 실행으로 발견한 결함 4건

### 결함 1 — PBT 가 프로토타입 오염 버그를 잡았습니다 (가장 중요)

`polling.property.test.ts` 의 속성이 실패. fast-check 축소 **반례: `"toString"`**.

```ts
const STEP_LABELS: Record<string, string> = { ... };
return STEP_LABELS[step] ?? "진행하고 있어요";   // ← "toString" 이면 함수를 반환
```

`Object.prototype` 상속 속성이 새어나와 `?? 기본값` 이 발동하지 않고, `.length` 가 0 이 됩니다.
**화면에 빈 라벨이 뜹니다.**

→ `Map` 으로 교체. **같은 부류인 `selectors/trip.ts::API_LABELS` 도 찾아 선제 수정.** 회귀 테스트 추가.
→ 예제 기반 테스트로는 나오기 어렵습니다. 누가 `"toString"` 을 단계 이름으로 넣어보겠습니까.

### 결함 2 — `decodeParams` 의 `__proto__` 키

WP-01 왕복 속성이 **약 10회 중 1회** 실패(시드 의존). `result[key] = value` 는 키가 `__proto__` 일 때
자기 속성을 만들지 않고 프로토타입을 바꿉니다. → `Object.defineProperty` 로 교체.

⚠️ **정직 기록**: 원 반례를 직접 포착하지는 못했습니다(시드 재현 실패). 실패 위치·기전이 결함 1과
일치해 같은 부류로 판단했고, 이 수정은 어떤 경우에도 옳은 변경입니다. 이후 10회 연속 통과.

### 결함 3 — 존재하지 않는 의존성 버전

`@tanstack/query-async-storage-persister@5.62.11` 이 **배포되지 않은 버전**(`ETARGET`).
이 패키지는 `5.68.0` 부터 존재 → TanStack 3종을 `5.69.2` 로 정렬. `@types/node` 누락도 추가.

### 결함 4 — 구조 테스트의 오탐 (테스트 자체의 결함)

구조 테스트 4건이 실패했는데 **전부 주석의 설명 문구를 코드로 오탐**한 것이었습니다.
예: `SharedTripView.tsx` 주석의 "`DndContext` 를 import 하지 않는다" 라는 **문장**이 위반으로 잡혔습니다.

→ `stripComments()` 를 도입해 **코드만 검사**하도록 수정. 자동 생성 배너 검사만 원문을 봅니다.
→ 구조 테스트를 쓸 때 반드시 만나는 함정이라 헬퍼에 사유를 적어 두었습니다.

---

## 3. u1 개정 2건 (승인 후 적용)

| ID | 내용 | 결과 |
|---|---|---|
| **A-1** | `GET /api/config` 추가 — 지도 키·데모 모드·폼 상한 전달 | 엔드포인트 19 → **22 오퍼레이션** |
| **A-2** | **응답 모델 18종 + 라우트 19곳 `response_model`** | 무타입 응답 **17 → 0**, 스키마 15 → 41 |

**A-2 의 부수 효과**: `ReadOnlyTripOut` 에 `share_token` 필드가 **스키마상 없습니다.**
공유 응답에 토큰이 섞이는 실수가 **타입 수준에서 차단**됩니다(DD-25). 전에는 코드 규율에만 의존했습니다.

추가로 `main.py` 의 **import 부작용**을 제거했습니다(모듈 수준 `app = create_app()` → `uvicorn --factory`).
스키마 추출 시 컨테이너가 두 번 생성되는 것을 로그로 실측해 발견했습니다.

---

## 4. 생성 파일 (60개)

| 위치 | 수 | 내용 |
|---|---|---|
| `web/src/` | **44** | shared 20 · features 21 · 진입점·라우팅·스타일 3 |
| `web/tests/` | **9** | property 5 · unit 1 · structure 1 · component 1 · setup 1 |
| `web/` 루트 | **7** | `package.json` · `package-lock.json` · `tsconfig.json` · `vite.config.ts` · `vitest.config.ts` · `index.html` · `openapi.json` |
| u1 개정 | — | `routers/config.py` 신규 · `schemas.py` · 라우터 6 · 테스트 1 |
| 문서 | 2 | `infra-summary.md` · 본 문서 |

**커밋 필수 2건**: `openapi.json` · `src/shared/api/generated.ts`
(없으면 Docker 웹 빌드가 백엔드 기동을 요구해 **순환** — UD-3)

---

## 5. 설계 규칙이 코드 구조로 남은 지점 (구조 테스트 18건이 강제)

| 규칙 | 구현 | 검사 |
|---|---|---|
| **WBR-28 / DD-11** 딥링크 단일 소유 | `nmap://` 리터럴이 `shared/deeplink/` 에만 | ✅ |
| **DD-11** 웹/앱 분기 단일 소유 | `isNative()` 가 `shared/bridge/` 밖에 없음 | ✅ |
| **DD-18** 지도 SDK 격리 | `window.naver` 가 `features/map/` 밖에 없음 | ✅ |
| **DD-25 / BR-37** 공유는 읽기 전용 | `SharedTripView` 가 `@dnd-kit`·`TimelineView`·`useTripMutations` 를 import 하지 않음 | ✅ |
| **WBR-10** 폼 상한 미하드코딩 | `limits.max_trip_days` 사용 | ✅ |
| **WBR-04** 재계산 금지 | 선택자에 `new Date(` 없음 (`Date.parse` 만) | ✅ |
| **SEC-04** 인라인 스크립트 금지 | `index.html` 의 script 는 전부 `src` 보유, `dangerouslySetInnerHTML` 0건 | ✅ |
| **WBR-01** 생성 타입 불가침 | 자동 생성 배너 존재, `types.ts` 는 별칭만 | ✅ |
| **WBR-03** 스토어에 서버 데이터 금지 | `uiStore` 에 도메인 타입 없음 | ✅ |
| **DD-14** job persist 금지 | `isPersistable` 이 `trip` 만 통과 | ✅ |
| **NFR-10** 네트워크 비의존 | `setup.ts` 가 `fetch` 차단 | ✅ |

---

## 6. WP 속성 (PBT) — 전건 통과

WP-01 왕복 · WP-02 앱/웹 동시 · WP-03 TRANSIT→public · WP-04 좌표 정밀도 ·
WP-05 목록 왕복 · WP-06 가져오기 멱등 · WP-07 시간 합계 · WP-08 경고 부분집합 ·
WP-09 데모 판정 · WP-10 폴링 단조성 · WP-11 90초 상한 → **11/11 ✅**

---

## 7. FR 추적성 (Owner 15건)

| FR | 구현 |
|---|---|
| FR-1 조건 입력 | `TripCreateWizard` |
| FR-5 항목 추가·삭제·드래그 | `TimelineView` + `useTripMutations` |
| FR-7 시각·체류·메모 편집 | `ItemCard` · `PlaceDetailPanel` |
| FR-11 이동수단 선택 | `LegRow` |
| FR-12 대중교통 딥링크 | `LegRow` + `shared/deeplink` |
| FR-14 지도 렌더링 | `NaverMapAdapter` · `loadSdk` |
| FR-15 번호·색상 마커 | `MapView` · `NaverMapAdapter` |
| FR-16 경로 폴리라인 | `MapView` |
| FR-17 장소 상세 | `PlaceDetailPanel` |
| FR-18 일자 필터 | `DayTabs` · `MapView` |
| FR-19 양방향 하이라이트 | `uiStore.selectItem` + `TripWorkspace` 스크롤 (WBR-18) |
| FR-23·24 딥링크·폴백 | `shared/deeplink` + `shared/bridge` |
| FR-31 오프라인 조회 | `queryClient` persist |
| FR-32 오프라인 편집 차단 | `OfflineGate` |

**미매핑 0건** ✅ / **WBR-01~42 전건 구현** ✅

---

## 8. Compliance

**Security**
- SEC-04 ✅ 인라인 스크립트 0건, `dangerouslySetInnerHTML` 0건 (구조 테스트)
- SEC-05 ✅ 클라이언트 검증은 편의일 뿐 서버 검증을 대체하지 않음
- SEC-08 ✅ `credentials: "omit"`, 공유 응답에 토큰 필드 부재(타입 보장)
- SEC-09 ✅ 예외 원문 미노출 (`describeError`)
- SEC-10 ✅ **`package-lock.json` 커밋**, 존재하지 않는 버전 1건 수정
- SEC-11 ✅ `/api/config` 가 검색·LLM 키를 포함하지 않음 (u1 구조 테스트)
- SEC-13 ✅ 외부 CDN 스크립트는 지도 SDK 뿐(CSP 허용목록과 일치)
**Blocking findings: 0건**

**PBT**: PBT-01·02·03·04·07·08·09·10 충족. **PBT-08(셰링킹)이 실제로 반례를 축소해 결함을 드러냄.**
**Blocking findings: 0건**

---

## 9. 남은 미검증 (Build & Test)

| # | 항목 | 비고 |
|---|---|---|
| 1 | **지도 SDK 실제 로딩** | `loadSdk.ts` 의 URL·전역 객체 형태. 키 필요 |
| 2 | **CSP 허용 도메인 충분성** | 실 로딩 시 콘솔 위반 확인 |
| 3 | 실 API 응답과의 정합 | 인증 정보 보유 시 |
| 4 | u1+u2 통합 이미지 빌드 | `docker compose build` — **이제 `web/` 이 있으므로 가능** |
| ~~5~~ | ~~의존성 설치·타입·테스트·번들~~ | ✅ **전부 실측 완료** |

> 🔴 이전에 "u2 부재로 `docker compose build` 실패"라고 보고했던 제약이 **해소되었습니다.**
> 다만 실제 이미지 빌드는 Build & Test 에서 확인합니다.

---

## 10. 다음 단계

`u3-trip-android` Functional Design → Code Generation → **Build and Test**
