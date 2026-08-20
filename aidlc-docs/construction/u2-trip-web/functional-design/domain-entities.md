# Domain Entities — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 2/3)
**Created**: 2026-08-14T01:00:00Z
**결정 근거**: `construction/plans/u2-trip-web-functional-design-plan.md` Q1~Q18 = 전부 A

> **u2 는 도메인의 소유자가 아닙니다.** 여행·장소·일정의 정의는 u1 이 갖고,
> u2 는 **OpenAPI 에서 생성한 타입을 소비**합니다 (UD-3, DD-10).
> 따라서 본 문서는 **클라이언트 고유 타입**과 **상태 소유권**을 정의합니다.

---

## 1. 타입 원천 — 생성 타입과 수기 타입의 경계

```
u1 Pydantic 스키마 (C33)
        |
        v  FastAPI /api/openapi.json
        |
        v  npm run gen:api  (openapi-typescript)
web/src/shared/api/generated.ts     ← 🔴 저장소에 커밋 (UD-3)
        |
        +--> 서버 자원 타입 (Trip / ItineraryItem / Place / JobStatus / ProblemDetails ...)
        |
web/src/shared/types/*.ts           ← 수기 작성
        +--> 클라이언트 고유 타입 (아래 §2)
```

**규칙 (WBR-01)**: `generated.ts` 를 손으로 수정하지 않습니다. 서버 스키마가 바뀌면 재생성합니다.
**규칙 (WBR-02)**: 서버가 소유하는 개념을 `shared/types/` 에 **다시 정의하지 않습니다.** 생성 타입을 재사용합니다.

> 커밋이 필수인 이유: `generated.ts` 가 없으면 Docker 웹 빌드 스테이지가 백엔드 기동을 요구해
> **빌드가 순환**합니다 (UD-3, `Dockerfile` stage 1 주석 참조).

---

## 2. 클라이언트 고유 타입

### 2.1 `SavedTripRef` — 로컬 여행 목록 항목 (Q3=A)

| 속성 | 타입 | 설명 |
|---|---|---|
| `trip_id` | `string` | UUIDv4 |
| `title` | `string` | 목록 표시용 사본 |
| `destination` | `string` | 목록 표시용 사본 |
| `start_date` / `end_date` | `string` (ISO date) | 목록 표시용 사본 |
| `share_token` | `string \| null` | 발급했다면 보관 — **복구 수단** |
| `saved_at` | `string` (ISO datetime) | 정렬용 |

🔴 **이 타입이 존재하는 이유와 그 대가**
백엔드는 여행 목록 API 를 제공하지 않습니다 (DD-21 / BR-39 — 계정이 없는 구성에서 목록은 열거 취약점).
그래서 "내 여행"은 **이 배열에만** 존재합니다. 브라우저 데이터를 지우면 서버에 데이터가 남아 있어도
UUID 를 알 수 없어 **접근할 수 없습니다.**
→ 완화책은 `business-rules.md` WBR-05 ~ WBR-08 (고지 · 공유 링크 안내 · 내보내기/가져오기).

### 2.2 `TripListExport` — 목록 백업 형식 (Q3=A ④)

```
{
  "format": "trip-list-export",
  "version": 1,
  "exported_at": "<ISO datetime>",
  "trips": SavedTripRef[]
}
```
**PBT 대상**: `import(export(x)) == x` (WP-01)

### 2.3 `RuntimeConfig` — 런타임 설정 (Q4=A)

`GET /api/config` 응답. **u1 에 추가가 필요한 엔드포인트입니다** (§5 참조).

| 속성 | 타입 | 용도 |
|---|---|---|
| `map_client_key` | `string \| null` | 지도 SDK 초기화 (CON-3 — 브라우저 노출은 구조상 불가피) |
| `modes` | `Record<ApiName, "real" \| "mock">` | 데모 배너 (FR-33, WBR-30) |
| `limits` | `{ max_trip_days, max_items_per_day, max_items_per_trip }` | 폼 검증을 서버 상한과 일치시킴 |

> 이 값들은 **모두 이미 공개되어도 무방한 정보**입니다. 검색·LLM 키는 포함되지 않습니다 (SEC-11).

### 2.4 `UiState` — Zustand 가 소유하는 화면 상태 (DD-17)

| 속성 | 타입 | 설명 |
|---|---|---|
| `selectedDayIndex` | `number` | 현재 보고 있는 일자 |
| `selectedItemId` | `string \| null` | 지도 ↔ 타임라인 양방향 하이라이트 (FR-19) |
| `draggingOrder` | `string[] \| null` | 드래그 중 임시 순서 (Q7=A 낙관적 업데이트) |
| `mobilePane` | `"timeline" \| "map"` | 모바일 탭 (Q6=A) |
| `detailPlaceId` | `string \| null` | 장소 상세 패널 대상 |

**규칙 (WBR-03)**: 이 스토어는 **서버 데이터를 담지 않습니다.** 식별자와 UI 플래그만 보관합니다.

### 2.5 `DeepLinkUrls` — 딥링크 결과 (DD-11)

```
{ app: string; web: string }
```
`app` = `nmap://…`, `web` = `https://map.naver.com/…`
**PBT 대상**: URL 인코딩 왕복 (WP-02)

### 2.6 `Toast` / `BannerState`

| 타입 | 용도 |
|---|---|
| `Toast` | `{ id, level: "info"\|"warn"\|"error", message, correlationId? }` (WBR-33) |
| `BannerState` | `{ demoMode: string[] }` — 데모인 API 이름 목록 (WBR-30) |

---

## 3. 상태 소유권 경계 (DD-17, Q1=A, Q16=A)

```
+---------------------------+----------------------------+---------------------------+
|  TanStack Query (W2)      |  Zustand (W3)              |  localStorage             |
|  서버 데이터의 유일 소유자 |  UI 상태만                  |  로컬 목록                 |
+---------------------------+----------------------------+---------------------------+
|  ['trip', tripId]         |  selectedDayIndex          |  SavedTripRef[]           |
|  ['job', jobId]           |  selectedItemId            |  (약 1KB 미만)            |
|  ['placeContent', id]     |  draggingOrder             |                           |
|  ['placeSearch', q, page] |  mobilePane                |                           |
|  ['suggestions', ...]     |  detailPlaceId             |                           |
|  ['config']               |                            |                           |
+---------------------------+----------------------------+---------------------------+
|  IndexedDB persist:       |  메모리만 —                 |  브라우저 데이터 삭제 시   |
|  ['trip', *] **만**       |  새로고침 시 초기화          |  소실 (WBR-05 고지 대상)  |
+---------------------------+----------------------------+---------------------------+
```

### persist 제외 대상과 이유 (Q16=A)

| 제외 | 이유 |
|---|---|
| `['job', *]` | **DD-14** — 완료된 진행률이 재방문 시 되살아난다 |
| `['placeSearch', *]` | 신선도. 오래된 검색 결과를 보여주면 안 된다 |
| `['placeContent', *]` | 용량. 블로그·이미지 메타가 누적된다 |
| `['config']` | 서버 설정이 바뀌면 즉시 반영되어야 한다 |

> ⚠️ **저장 매체가 둘(localStorage + IndexedDB)이라는 사실은 문제 1을 완화하지 않습니다.**
> 브라우저 데이터 삭제는 **둘 다** 지웁니다. 실질적 복구 수단은 **공유 링크와 목록 내보내기**뿐입니다 (WBR-06~08).

---

## 4. 서버 자원의 클라이언트 표현

생성 타입을 그대로 쓰되, 화면에서 자주 쓰는 파생값은 **선택자(selector)로 계산**하고 저장하지 않습니다.

| 파생값 | 계산 근거 | 규칙 |
|---|---|---|
| 일자별 총 이동시간 | `days[i].items` 의 leg 합 | WBR-20 |
| 미해결 후보 개수 | `trip.unresolved.length` | WBR-25 |
| 데모 모드 여부 | `config.modes` 에 `"mock"` 포함 | WBR-30 |
| 추정 구간 존재 여부 | 항목의 `ESTIMATED_TRAVEL_TIME` 경고 | WBR-22 |
| 경고 배지 목록 | `item.warnings` | WBR-21 |

**규칙 (WBR-04)**: 서버가 준 값을 클라이언트에서 **다시 계산하지 않습니다.**
시각·이동시간·경고는 u1 이 산출한 값을 그대로 표시합니다. 두 곳에서 계산하면 반드시 어긋납니다.

---

## 5. 🔴 u1 개정 요청 1건 — `GET /api/config` (Q4=A)

지도 SDK 키를 프론트에 전달할 경로가 현재 없습니다. 런타임 엔드포인트 방식을 선택했으므로
**u1 에 엔드포인트 1개를 추가해야 합니다.**

| 항목 | 내용 |
|---|---|
| 경로 | `GET /api/config` |
| 등급 | `CHEAP` (BR-49) |
| 응답 | `RuntimeConfig` (§2.3) |
| 외부 호출 | **없음** — 설정 값만 반환 |
| 노출 위험 | 없음. 지도 키는 어차피 브라우저에 노출되며(CON-3) 도메인 화이트리스트로 방어. 검색·LLM 키는 포함하지 않음 |
| 영향 | 엔드포인트 **19 → 20**. `component-methods.md` §7 갱신 필요 |
| 적용 시점 | **u2 Code Generation 시작 시** (u1 코드에 최소 변경) |

**선택 근거**: 빌드 시 주입(`VITE_`) 방식은 키를 바꿀 때마다 **이미지 재빌드**가 필요합니다.
`.env` 만 고쳐서 반영되지 않는 것은 운영상 함정입니다 (README 의 기동 절차와 어긋남).
