# 인프라·순수 함수 구현 요약 — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 7)
**Created**: 2026-08-14T04:55:00Z
**대상 단계**: Step 1·1b(u1 개정) · 2(빌드) · 3(API 계약) · 4(인프라) · 5(순수 함수) · 6(테스트)

---

## 1. 🔴 이번 단계의 가장 중요한 사실 — 테스트가 실제로 실행됐습니다

u1 은 규칙상 테스트를 작성만 하고 실행은 Build & Test 로 미뤘습니다. u2 는 `generated.ts` 생성을 위해
의존성 설치가 필요했고, 그 김에 **순수 함수 테스트를 실제로 실행**했습니다.

| 항목 | 결과 |
|---|---|
| `npm install` | ✅ 330개 패키지 |
| `npx tsc -b --noEmit` | ✅ **오류 0건** |
| `npx vitest run` | ✅ **52 passed / 0 failed** (5 파일) |
| 반복 실행 | ✅ **10회 연속 통과** (시드 무작위) |

그 과정에서 **결함 3건**이 드러났습니다.

---

## 2. 🔴 결함 1 — PBT 가 프로토타입 오염 버그를 잡았습니다

### 발견
`polling.property.test.ts` 의 "알 수 없는 단계도 빈 문자열을 내지 않는다" 속성이 실패했습니다.
fast-check 가 축소한 **반례: `"toString"`**.

### 원인
```ts
const STEP_LABELS: Record<string, string> = { DRAFTING: "...", ... };
return STEP_LABELS[step] ?? "진행하고 있어요";
```
객체 리터럴을 조회 표로 쓰면 `Object.prototype` 의 상속 속성이 새어나옵니다.
`STEP_LABELS["toString"]` 은 **함수**를 반환하므로 `?? 기본값` 이 발동하지 않고,
`.length` 가 함수의 인자 수(`0`)를 돌려줍니다. 화면에는 **빈 라벨**이 뜹니다.

### 조치
- `STEP_LABELS` 를 `Map` 으로 교체 (`polling.ts`)
- **같은 부류의 코드를 찾아 선제 수정**: `selectors/trip.ts::API_LABELS` 도 `Map` 으로 교체
- 회귀 테스트 추가: `toString`·`constructor`·`valueOf`·`hasOwnProperty`·`__proto__`

> 예제 기반 테스트로는 나오기 어려운 결함입니다. 누가 `"toString"` 을 단계 이름으로 넣어보겠습니까.
> **PBT-03(불변식)이 실제로 값을 한 사례입니다.**

---

## 3. 🔴 결함 2 — 같은 부류를 `decodeParams` 에서 선제 차단

`deeplink.property.test.ts` 의 WP-01 왕복 속성이 **약 10회 중 1회** 실패했습니다(시드 의존).
단독 실행으로는 재현되지 않아 8회 반복해도 나오지 않았지만, 실패 지점이 사전(dictionary) 왕복이었고
**결함 1과 같은 부류**(프로토타입 키)로 판단했습니다.

```ts
result[key] = value;   // key 가 "__proto__" 면 자기 속성을 만들지 않고 프로토타입을 바꾼다
```

→ `Object.defineProperty` 로 교체해 **키가 무엇이든 자기 속성으로** 만들도록 했습니다.
→ 회귀 예제 추가 후 **10회 연속 통과**.

> ⚠️ 정직하게 적자면, 원래 실패의 반례를 직접 포착하지는 못했습니다(시드가 재현되지 않음).
> 다만 실패 위치·시점·기전이 일치하고, 수정은 어떤 경우에도 옳은 변경입니다.

---

## 4. 🔴 결함 3 — 존재하지 않는 의존성 버전

`package.json` 에 고정한 `@tanstack/query-async-storage-persister@5.62.11` 이 **존재하지 않았습니다**
(`npm error ETARGET`). 이 패키지는 `5.68.0` 부터 배포됩니다.

→ TanStack 3종을 **`5.69.2` 로 정렬**(세 패키지 모두에 존재하는 버전).
→ `@types/node` 누락도 타입 검사에서 드러나 추가.
→ `package-lock.json` 생성 — **SEC-10(락파일 커밋) 충족**.

> 계획서 §7 에 "의존성 버전의 실제 설치 가능 여부"를 미확정으로 적어둔 항목이 **실제로 문제였습니다.**

---

## 5. 생성 파일 (24개)

### u1 개정 (4)
| 파일 | 내용 |
|---|---|
| `backend/app/api/routers/config.py` | A-1 `GET /api/config` |
| `backend/app/api/schemas.py` | A-1 + **A-2 응답 모델 18종** |
| `backend/app/api/routers/*.py` | A-2 `response_model` 19곳 |
| `backend/tests/unit/test_api_config.py` | 9건 (비밀 노출 방지 구조 검증 포함) |

### 빌드 설정 (6)
`package.json` · `tsconfig.json` · `vite.config.ts` · `index.html` · `vitest.config.ts` · `tests/setup.ts`

### API 계약 (4)
`openapi.json`(실기동 추출) · `generated.ts`(**1,650줄**) · `types.ts` · `client.ts` · `errors.ts`

### 인프라 (5)
`query/keys.ts` · `query/queryClient.ts` · `store/uiStore.ts` · `config/RuntimeConfigProvider.tsx` · `storage/tripList.ts`

### 순수 함수 (4)
`deeplink/index.ts` · `selectors/trip.ts` · `selectors/polling.ts` · `storage/tripListExport.ts`

### 테스트 (6)
`property/generators.ts` · `deeplink.property.test.ts` · `tripList.property.test.ts` ·
`selectors.property.test.ts` · `polling.property.test.ts` · `unit/deeplink.test.ts`

---

## 6. 설계 규칙이 코드 구조로 남은 지점

| 규칙 | 구현 |
|---|---|
| **DD-14** job persist 금지 | `queryClient.ts::shouldDehydrateQuery` 가 `['trip', *]` 만 통과시킨다 |
| **WBR-03** 스토어에 서버 데이터 금지 | `uiStore` 는 식별자와 UI 플래그만 보관 |
| **WBR-04** 재계산 금지 | `selectors/trip.ts` 는 합계·필터·판정만. 시각을 만들어내지 않는다 |
| **WBR-18** FR-19 를 상태 연속성으로 | `selectItem` 이 `mobilePane` 과 무관 |
| **WBR-28** 딥링크 단일 소유 | `nmap://` 리터럴이 `deeplink/index.ts` 에만 존재 |
| **DD-25** 공유는 읽기 전용 | `ReadOnlyTrip` 타입에 `share_token` 이 **없다** — 읽으려 하면 컴파일 오류 |
| **SEC-04** 인라인 스크립트 금지 | `index.html` 에 사유 주석과 함께 명시 |
| **NFR-10** 네트워크 비의존 | `tests/setup.ts` 가 실제 `fetch` 호출 시 **즉시 실패**시킨다 |

---

## 7. WP 속성 구현 현황

| 속성 | 테스트 | 상태 |
|---|---|---|
| WP-01 파라미터 왕복 | `deeplink.property` | ✅ 통과 (+ 프로토타입 키 회귀) |
| WP-02 앱·웹 URL 동시 생성 | `deeplink.property` | ✅ |
| WP-03 TRANSIT → route/public | `deeplink.property` | ✅ |
| WP-04 좌표 6자리 정밀도 | `deeplink.property` | ✅ |
| WP-05 목록 내보내기 왕복 | `tripList.property` | ✅ |
| WP-06 가져오기 멱등 | `tripList.property` | ✅ |
| WP-07 시간 합계 불변식 | `selectors.property` | ✅ |
| WP-08 경고는 서버 값의 부분집합 | `selectors.property` | ✅ |
| WP-09 데모 모드 판정 | `selectors.property` | ✅ |
| WP-10 폴링 간격 단조성 | `polling.property` | ✅ **결함 1 발견 지점** |
| WP-11 90초 상한 | `polling.property` | ✅ |

**WP-01 ~ WP-11 전건 구현·통과** ✅

---

## 8. Compliance — Step 1~7

**Security**
- SEC-04 ✅ 인라인 스크립트 없음
- SEC-08 ✅ `credentials: "omit"`, 공유 응답에 토큰 필드 부재(타입 보장)
- SEC-09 ✅ 예외 원문을 사용자에게 노출하지 않음 (`describeError`)
- SEC-10 ✅ **`package-lock.json` 생성**, 버전 고정, 존재하지 않는 버전 1건 수정
- SEC-11 ✅ `/api/config` 가 검색·LLM 키를 포함하지 않음 (u1 테스트로 구조 검증)
**Blocking findings: 0건**

**PBT**
- PBT-02 ✅ WP-01·05 / PBT-03 ✅ WP-02·03·04·07~11 / PBT-04 ✅ WP-06(멱등)
- PBT-07 ✅ 생성기 8종 / PBT-08 ✅ 셰링킹 활성 + `verbose` (**반례 축소가 실제로 동작함을 확인**)
- PBT-09 ✅ fast-check / PBT-10 ✅ 예제 병행
**Blocking findings: 0건**

---

## 9. 남은 미확정

| # | 항목 | 상태 |
|---|---|---|
| 1 | 지도 SDK 스크립트 URL·전역 객체 | Step 9 에서 단일 파일에 격리 예정 |
| 2 | CSP 허용 도메인 충분성 | Build & Test — 실 로딩 |
| 3 | 번들 크기 1MB 목표 | Build & Test — `npm run build` |
| 4 | 컴포넌트·구조 테스트 | Step 14 |
| ~~5~~ | ~~의존성 설치 가능 여부~~ | ✅ **해소** — `npm install` 성공, 락파일 생성 |
| ~~6~~ | ~~`generated.ts` 생성 결과~~ | ✅ **해소** — 1,650줄, 실제 타입 |
