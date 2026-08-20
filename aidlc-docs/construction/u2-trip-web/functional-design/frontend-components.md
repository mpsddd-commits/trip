# Frontend Components — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 2/3)
**Created**: 2026-08-14T01:00:00Z
**근거**: `functional-design.md` Step 6 — 계층·props/state·상호작용·폼 검증·API 연결점

---

## 1. 라우트 구성 (Q5=A)

| 라우트 | 화면 | 주요 컴포넌트 | 코드 분할 |
|---|---|---|---|
| `/` | 내 여행 목록 | `TripListPage` | 초기 번들 |
| `/trips/new` | 생성 마법사 | `TripCreateWizard` (W6) | 지연 |
| `/trips/:tripId` | **메인 — 타임라인 + 지도** | `TripWorkspace` | 지연 (지도 SDK 포함) |
| `/shared/:token` | 읽기 전용 공유 | `SharedTripView` (W12) | 지연 |

`/trips/:tripId?job=<id>` 로 진입하면 `GenerationProgress`(W7)를 오버레이로 표시합니다.

---

## 2. 컴포넌트 계층

```
App
+-- RuntimeConfigProvider          W2  ── GET /api/config 1회 (WBR-32)
+-- QueryClientProvider            W2  ── persist: ['trip', *] 만 (Q16=A)
+-- OfflineGate                    W15 ── 온라인 감지 + 편집 차단 (WBR-35)
+-- DemoModeBanner                 W16 ── 닫을 수 없음 (WBR-30)
+-- ToastHost                      W16
+-- ErrorBoundary                  W16 ── SEC-15 부분 책임
    |
    +-- [/] TripListPage
    |     +-- TripCard[]                  ── 404 시 [목록에서 제거] (WBR-09)
    |     +-- LocalStorageNotice          ── 상시 고지 (WBR-06)
    |     +-- ListExportImport            ── 내보내기/가져오기 (WBR-07·08)
    |
    +-- [/trips/new] TripCreateWizard        W6
    |     +-- DestinationStep
    |     +-- DateRangeStep
    |     +-- PreferenceStep                 ── 스타일 태그·인원·예산
    |     +-- ScheduleStep                   ── 하루 시작/종료·이동수단
    |     +-- ReviewStep                     ── [AI로 만들기] / [빈 일정으로 시작]
    |
    +-- [/trips/:id] TripWorkspace
    |     +-- TripHeader                     ── 제목·기간·[공유]·[.ics]·[삭제]
    |     +-- UnresolvedPanel                W7  ── 접이식 상시 노출 (WBR-29)
    |     +-- DayTabs                        ── 일자 선택 (FR-18)
    |     +-- ResponsiveSplit                ── ≥1024 2단 / 그 미만 탭 (Q6=A)
    |     |     +-- TimelineView             W8
    |     |     |     +-- DayHeader          ── 총 이동·체류 시간 (WBR-20)
    |     |     |     +-- DndContext         ── @dnd-kit (Q17=A)
    |     |     |     |     +-- ItemCard[]   ── 번호·시각·체류·메모·경고 배지
    |     |     |     +-- LegRow[]           ── 이동수단·시간·"추정" 배지·[길찾기]
    |     |     |     +-- AddItemButton      ── PlaceSearchPanel 열기
    |     |     |     +-- OptimizeButton     ── FR-8
    |     |     +-- MapView                  W5
    |     |           +-- NaverMapAdapter    W4  ── 선언적 props (DD-18)
    |     |           +-- MapLegend          ── 일자 색·선 종류 설명 (WBR-23·24)
    |     |           +-- MapFallback        ── 로딩 실패 안내 (WBR-40)
    |     +-- PlaceDetailPanel               W9  ── 시트(모바일)/사이드(데스크톱)
    |     +-- PlaceSearchPanel               W10
    |     +-- RecommendationPanel            W11
    |     +-- GenerationProgress             W7  ── 오버레이 (job 폴링)
    |
    +-- [/shared/:token] SharedTripView       W12 ── 편집 UI 없음 (SEC-08)
```

**규칙**: `SharedTripView` 는 `TimelineView`·`MapView` 를 **읽기 전용 모드**로 재사용하되,
편집 컴포넌트(`DndContext`·`AddItemButton`·`OptimizeButton`)를 **렌더링하지 않습니다.**
`readOnly` 플래그로 숨기는 것이 아니라 **트리에 넣지 않습니다** (DD-25 의 UI 측 대응).

---

## 3. 주요 컴포넌트 명세

### W6 `TripCreateWizard`

| 항목 | 내용 |
|---|---|
| **props** | 없음 (라우트 진입) |
| **로컬 state** | `step: 0~4`, `draft: TripSpecIn` |
| **API** | `GET /api/config`(상한) → `POST /api/trips` → `POST /api/trips/{id}/generate` |
| **검증** | 아래 §4 |
| **완료 후** | `localStorage` 에 `SavedTripRef` 추가 (WBR-05) + 최초 1회 안내 (WBR-06) |

### W8 `TimelineView`

| 항목 | 내용 |
|---|---|
| **props** | `days: TripDay[]`, `selectedDayIndex`, `selectedItemId`, `readOnly`, `offline` |
| **state** | 없음 — 임시 순서는 `UiState.draggingOrder` (WBR-03) |
| **이벤트** | `onSelectItem` · `onReorder` · `onMoveDay` · `onPatchItem` · `onRemoveItem` |
| **API** | `PUT .../order` · `PATCH .../items/{id}` · `DELETE .../items/{id}` · `POST .../optimize` |
| **접근성** | `@dnd-kit` 키보드 센서. 항목마다 `aria-label="1번 광안리 해수욕장, 10시 도착"` (WBR-37·38) |
| **비활성 조건** | `offline` 이면 드래그·편집 버튼 비활성 (WBR-35) |

### W4 `NaverMapAdapter` (DD-18)

```
props {
  clientKey : string | null
  markers   : { id, lat, lng, label:number, dayIndex:number, selected:boolean }[]
  polylines : { path:{lat,lng}[], dayIndex:number, style:"solid"|"dashed" }[]
  focus     : { bounds } | { center, zoom } | null
  onMarkerClick(id): void
  onLoadError(reason: "no-key"|"network"|"auth"|"unknown"): void
}
```

**책임 경계**: SDK 로딩·인스턴스 수명·마커 add/remove 등 **명령형 API 는 전부 이 컴포넌트 내부**에 갇힙니다.
바깥은 위 props 만 다룹니다. 목 모드에서는 동일 인터페이스의 대체 구현으로 교체할 수 있습니다.

### W9 `PlaceDetailPanel`

| 항목 | 내용 |
|---|---|
| **props** | `placeId`, `tripId`, `itemId`, `readOnly` |
| **API** | `GET /api/places/content?trip_id=&item_id=` |
| **표시** | 주소·전화·카테고리 → **추천(highlights)** → **근거 블로그 링크** → 이미지(출처 병기) |
| **규칙** | `highlights` 가 비어 있으면 **"AI 요약" 영역을 아예 렌더링하지 않고** 블로그 링크만 보여준다 (BR-40 의 UI 측 대응) |
| **버튼** | [네이버지도에서 보기] · [길찾기] → W13 → W14 |

### W7 `UnresolvedPanel` + `GenerationProgress`

| 항목 | 내용 |
|---|---|
| **UnresolvedPanel props** | `unresolved: UnresolvedCandidate[]`, `onSearchAndAdd(name)` |
| **표시** | 원래 이름 · 실패 사유(6종 한국어) · 가장 근접했던 후보 · 유사도 |
| **동작** | [직접 검색해 담기] → `PlaceSearchPanel` 을 해당 이름으로 미리 채워 연다 |
| **GenerationProgress** | 단계 라벨 6종 + 서버 `progress` 막대 + 90초 초과 시 안내 (WBR-11·13) |

### W13 `DeepLinkBuilder` (순수 함수 — PBT 대상)

```
placeUrl(place)                    -> { app, web }
routeUrl(from, to, mode)           -> { app, web }
encodeParams(params)               -> string
```
**어떤 React 의존도 없습니다.** 그래서 fast-check 로 직접 검증합니다 (WP-01~WP-04).

### W14 `NativeBridge`

```
isNative(): boolean                       // window.tripBridge 존재 여부
openMap(urls): void                       // 브리지 → 앱 스킴 → 웹 (WBR-27)
share(payload): void                      // 브리지 → Web Share API → 클립보드
requestLocation(): Promise<Coord | null>  // 브리지 → Geolocation API → null
```
**웹과 앱의 분기는 이 파일 한 곳에만 존재합니다.** 화면 컴포넌트는 `isNative()` 를 직접 보지 않습니다.

---

## 4. 폼 검증 규칙 (WBR-10)

`TripCreateWizard` 는 **서버 상한과 동일한 값**을 `GET /api/config` 에서 받아 사용합니다.

| 필드 | 규칙 | 서버 대응 |
|---|---|---|
| `title` | 1~100자, 필수 | BR-04 |
| `destination` | 1~50자, 필수 | BR-04 |
| `start_date` / `end_date` | `end >= start`, 기간 ≤ `limits.max_trip_days` | BR-01 |
| `party_size` | 1~20 | BR-04 |
| `style_tags` | 0~8개, 각 20자 이하 | BR-04 |
| `day_start_time` / `day_end_time` | `end > start` | BR-03 |
| `default_travel_mode` | 3종 중 하나 | — |

| 항목 편집 필드 | 규칙 |
|---|---|
| `stay_minutes` | 1~720 |
| `memo` | 0~500자 |
| `fixed_time` | `time_fixed` 가 참이면 필수 |
| 영업시간 `open`/`close` | `closed` 가 거짓이면 둘 다 필요 |

**규칙**: 클라이언트 검증은 **편의**이지 방어가 아닙니다. 서버 검증(SEC-05)을 대체하지 않으며,
서버가 400 을 주면 그대로 표시합니다 (WBR-33).

---

## 5. API 연결점 (u1 엔드포인트 ↔ 화면)

| 엔드포인트 | 사용 컴포넌트 | 캐시 키 |
|---|---|---|
| `GET /api/config` ⚠️ **u1 추가 필요** | `RuntimeConfigProvider` | `['config']` (persist 제외) |
| `POST /api/trips` | W6 | — (성공 시 `['trip', id]` 세팅) |
| `GET /api/trips/{id}` | `TripWorkspace`, `TripListPage` | `['trip', id]` (**persist 대상**) |
| `PATCH /api/trips/{id}` | `TripHeader` | 응답으로 캐시 갱신 |
| `DELETE /api/trips/{id}` | `TripHeader` | 캐시 제거 + 로컬 목록 제거 |
| `POST /api/trips/{id}/days/{d}/items` | W10 → W8 | 응답으로 갱신 |
| `DELETE /api/trips/{id}/items/{id}` | W8 | 응답으로 갱신 |
| `PATCH /api/trips/{id}/items/{id}` | W8, W9 | 응답으로 갱신 |
| `PUT /api/trips/{id}/days/{d}/order` | W8 (드래그) | 낙관적 + 응답 확정 |
| `POST /api/trips/{id}/days/{d}/optimize` | W8 | 응답으로 갱신 |
| `PUT .../items/{id}/opening-hours` | W9 | 응답으로 갱신 |
| `POST /api/trips/{id}/generate` | W6, `TripHeader` | → `['job', jobId]` |
| `GET /api/jobs/{id}` | W7 | `['job', id]` (**persist 제외** — DD-14) |
| `GET /api/places/search` | W10 | `['placeSearch', q, page]` |
| `GET /api/places/content` | W9 | `['placeContent', placeId]` |
| `GET /api/places/suggestions` | W11 | `['suggestions', tripId, day]` |
| `POST /api/trips/{id}/share` | `TripHeader` | 로컬 목록에 토큰 저장 (WBR-05) |
| `DELETE /api/trips/{id}/share` | `TripHeader` | 로컬 목록에서 토큰 제거 |
| `GET /api/shared/{token}` | W12 | `['shared', token]` |
| `GET /api/trips/{id}/export.ics` | `TripHeader` | 직접 다운로드 (캐시 없음) |
| `GET /api/health/ready` | (미사용) | 데모 모드는 `/api/config` 로 통일 |

**20개 중 19개를 소비합니다.** `/api/health` 는 컨테이너 헬스체크 전용입니다.

---

## 6. 반응형 레이아웃 (Q6=A, WBR-39)

| 구간 | 폭 | 배치 |
|---|---|---|
| 모바일 | 360 ~ 767 | 일자 탭 + **타임라인/지도 하단 탭 전환**. 상세는 바텀 시트 |
| 태블릿 | 768 ~ 1023 | 동일하되 여백 확대, 상세는 사이드 시트 |
| 데스크톱 | ≥ 1024 | 좌 타임라인(고정 폭) / 우 지도(가변). 상세는 우측 패널 |

🔴 **탭 전환 시에도 `selectedItemId` 를 유지**하고, 전환 후 해당 항목으로 스크롤·뷰포트를 맞춥니다 (WBR-18).
이것이 모바일에서 FR-19 를 만족시키는 방식입니다.

---

## 7. 상태 흐름 요약

```
사용자 입력
    |
    v  컴포넌트 이벤트 핸들러
    |
    +-- UI 상태 변경 --> Zustand (W3)  --> 즉시 리렌더
    |
    +-- 서버 변경   --> W1 ApiClient --> u1
                            |
                            v  응답(여행 전체)
                            |
                        Query 캐시 직접 갱신 (WBR-14)
                            |
                            v  구독 컴포넌트 리렌더
                            |
                        IndexedDB persist (['trip', *] 만)
```

---

## 8. 테스트 계획 (Code Generation 대상)

| 유형 | 대상 | 도구 |
|---|---|---|
| **PBT** | W13 딥링크, 목록 내보내기/가져오기, 선택자, 폴링 간격 (WP-01~11) | fast-check |
| 단위 | 폼 검증, 오류 문구 조립, 오프라인 게이트 | Vitest |
| 컴포넌트 | 타임라인 드래그(키보드 포함), 미해결 패널, 데모 배너 | Testing Library |
| 어댑터 | `NaverMapAdapter` 를 목 구현으로 교체해 props 반영 검증 | Vitest |
| 구조 | **공유 화면 트리에 편집 컴포넌트가 없음** / 지도 SDK 가 목록 화면에서 로드되지 않음 | Vitest |

**네트워크 비의존**: API 는 MSW 또는 목 클라이언트로 대체합니다 (NFR-10).
