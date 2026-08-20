# Business Logic Model — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 2/3)
**Created**: 2026-08-14T01:00:00Z

---

## 0. 답변 교차 검증에서 검출한 문제 1건

### ⚠️ Q6(모바일 탭 전환) × FR-19(지도 ↔ 타임라인 양방향 하이라이트)

모바일에서 타임라인과 지도가 **탭으로 분리**되면, 두 패널이 동시에 보이지 않으므로
"양방향 하이라이트"가 화면상 성립하지 않습니다. 그대로 두면 FR-19 가 데스크톱에서만 동작합니다.

→ **WD-1 로 해소**: 선택 상태(`selectedItemId`)를 **탭과 무관하게 유지**하고,
   - 지도 탭에서 마커를 선택 → 타임라인 탭으로 전환 시 **해당 항목으로 스크롤 + 강조**
   - 타임라인에서 항목 선택 → 지도 탭 전환 시 **해당 마커로 뷰포트 이동 + 강조**
   - 탭 전환 버튼에 선택 항목명을 표시해 맥락을 잃지 않게 함

즉 **동시 표시가 아니라 상태 연속성**으로 FR-19 를 만족시킵니다. 이 해석을 `business-rules.md` WBR-18 에 명문화합니다.

---

## WF-W1. 여행 생성 (FR-1, FR-2)

```
[/trips/new] TripCreateWizard (W6)
   |
   v  폼 검증 — 서버 상한(config.limits)과 동일 값 사용 (WBR-10)
   |
   v  POST /api/trips            -> trip_id
   |
   v  localStorage 에 SavedTripRef 추가 (WBR-05)
   |     최초 저장이면 "이 브라우저에만 저장됩니다" 안내 1회 (WBR-06)
   |
   v  "AI로 일정 만들기" 선택?
      |
      +-- 예  --> POST /api/trips/{id}/generate  -> 202 {job_id}
      |            v
      |         [GenerationProgress W7] 폴링 (WF-W2)
      |
      +-- 아니오 --> /trips/{id} 로 이동 (빈 일정에서 수동 편집)
```

---

## WF-W2. 생성 진행 폴링 (Q2=A, DD-5)

```
job_id 확보
   |
   v  간격 결정 (WBR-11)
   |     경과 0~10초  : 1초
   |     경과 10초~   : 2초
   |     경과 90초 초과: 폴링 중단 + "시간이 오래 걸립니다" 안내 + 수동 새로고침 버튼
   |
   v  문서가 백그라운드? --> 폴링 일시 중지, 복귀 시 즉시 1회 조회 (WBR-12)
   |
   v  GET /api/jobs/{job_id}
   |
   +-- state=running   --> 단계 라벨 표시 (WBR-13)
   |      DRAFTING   "여행 아이디어를 구상하고 있어요"
   |      RESOLVING  "실제로 있는 장소인지 확인하고 있어요"
   |      ROUTING    "이동 경로를 계산하고 있어요"
   |      OPTIMIZING "동선을 다듬고 있어요"
   |      SCHEDULING "시간표를 만들고 있어요"
   |      SAVING     "저장하고 있어요"
   |
   +-- state=succeeded --> ['trip', id] 무효화 후 /trips/{id} 이동
   |
   +-- state=partial   --> WF-W3 (부분 결과 안내)
   |
   +-- state=failed    --> 오류 표시 + "다시 시도" (새 job 생성 — ND-4 재시도 API 없음)
```

**진행률 표시**: 서버가 준 `progress` 를 그대로 씁니다. 클라이언트에서 추정하지 않습니다 (WBR-04).

---

## WF-W3. 부분 결과 안내 (Q13=A, DD-23)

`partial` 은 **실패가 아니라 품질 저하**입니다. 그 내용을 구체적으로 알립니다.

```
job.state == "partial"
   |
   v  요약 문장 조립 (WBR-25)
   |     unresolved_count > 0  -> "N곳을 찾지 못했습니다"
   |     추정 구간 존재         -> "일부 이동시간은 추정치입니다"
   |
   v  "확인 필요" 패널을 **접이식으로 상시 노출** (닫아도 배지는 남음)
   |     각 항목: 원래 이름 · 실패 사유 · 가장 근접했던 후보 · 유사도
   |     버튼: [직접 검색해 담기] -> PlaceSearchPanel 을 해당 이름으로 미리 채워 열기
   |
   v  일정 자체는 정상 표시 (미해결은 일정에 없음 — BR-18)
```

**실패 사유 표시 문구** (WBR-26)

| `failure_code` | 사용자 문구 |
|---|---|
| `NO_SEARCH_RESULT` | 검색 결과가 없었습니다 |
| `LOW_SIMILARITY` | 이름이 비슷한 곳을 찾지 못했습니다 |
| `OUT_OF_REGION` | 목적지 밖에 있는 것 같습니다 |
| `CATEGORY_MISMATCH` | 종류가 맞지 않았습니다 |
| `INVALID_COORDINATE` | 위치 정보를 확인하지 못했습니다 |
| `SEARCH_UNAVAILABLE` | 검색 서비스에 일시적인 문제가 있었습니다 |

---

## WF-W4. 항목 편집 — 낙관적 업데이트 (Q7=A, FR-5, FR-7)

```
드래그 시작
   |
   v  오프라인? --> 드래그 비활성 + 배너 (WBR-35, FR-32)
   |
   v  드롭 --> UiState.draggingOrder 에 임시 순서 기록 -> 화면 즉시 반영
   |
   v  PUT /api/trips/{id}/days/{d}/order
   |
   +-- 성공 --> 응답(여행 전체)으로 ['trip', id] 캐시를 **직접 갱신**
   |             draggingOrder = null
   |             ⚠️ 추가 GET 을 하지 않는다 (WBR-14)
   |
   +-- 실패 --> draggingOrder = null (원래 순서 복원)
                 토스트: "순서를 저장하지 못했습니다" + 백엔드 문구 (WBR-33)
```

**동일 패턴**을 항목 추가·삭제·수정·최적화·영업시간 입력에 적용합니다.
u1 의 편집 API 는 전부 **여행 전체를 반환**하므로 캐시 갱신 후 재조회가 필요 없습니다 (Q1=A).

---

## WF-W5. 지도 렌더링 (FR-14 ~ FR-19)

```
[RuntimeConfig] map_client_key 존재?
   |
   +-- 없음 --> 지도 영역에 안내 표시 (WBR-40)
   |             "지도 키가 설정되지 않았습니다" + 나머지 기능 정상
   |
   v  SDK 스크립트 동적 로드
   |
   +-- 실패 --> 지도 영역만 대체 표시 (Q9=A, WBR-40)
   |             사유 구분: 네트워크 / 도메인 미등록(인증 오류) / 알 수 없음
   |             ⚠️ 타임라인 편집은 영향받지 않는다
   |
   v  NaverMapAdapter 초기화 (W4)
   |
   v  선언적 props 로 갱신
         markers   : 번호 + 일자색 + 선택 여부
         polylines : 자동차=실경로 실선 / 도보·대중교통=점선 (WBR-23)
         focus     : 선택 일자의 bounds
```

**마커 표기 3중** (Q10=A, NFR-6): 번호(①②③) + 일자 색상 + **일자 라벨 텍스트**.
색상만으로 정보를 전달하지 않습니다.

---

## WF-W6. 딥링크 실행 (Q12=A, FR-23, FR-24)

```
W13 DeepLinkBuilder — 순수 함수로 URL 2종 생성
   |     nmap://place?lat=..&lng=..&name=..&appname=..
   |     nmap://route/public|car|walk?slat=..&slng=..&sname=..&dlat=..&dlng=..&dname=..&appname=..
   |     web  : https://map.naver.com/... (동일 좌표·이름)
   v
W14 NativeBridge
   |
   +-- isNative() (안드로이드 브리지 존재) --> postMessage {type:"openMap", appUrl, webUrl}
   |                                          → u3 가 인텐트 실행, 실패 시 웹 (u3 책임)
   |
   +-- 브라우저 --> ① location = appUrl 시도
                     ② 1.5초 내 페이지 이탈(visibilitychange)이 없으면
                     ③ window.open(webUrl) (WBR-27)
```

**규칙 (WBR-28)**: URL 생성은 **W13 한 곳에만** 존재합니다. u3 는 URL 을 만들지 않고 받아서 실행만 합니다 (DD-11).

---

## WF-W7. 오프라인 (FR-31, FR-32, Q16=A)

```
online 상태 감지 (navigator.onLine + fetch 실패 관찰)
   |
   +-- 오프라인 진입
   |     v  상단 배너: "오프라인입니다. 저장된 일정만 볼 수 있어요"
   |     v  편집·검색·AI 생성 버튼 **비활성** (WBR-35)
   |     v  ['trip', *] persist 캐시에서 조회 (읽기 전용)
   |     v  지도·검색·추천 영역은 비활성 안내
   |
   +-- 온라인 복귀
         v  ['trip', *] 재검증 (서버 우선 — CA-6)
         v  배너 해제 + 편집 재활성
```

**서버가 항상 우선입니다.** 오프라인 중 편집을 막았으므로 충돌 병합이 필요 없습니다 (OUT-6).

---

## WF-W8. 여행 목록 관리 (Q3=A)

```
[/] TripListPage
   |
   v  localStorage 의 SavedTripRef[] 읽기
   |
   v  각 항목에 대해 GET /api/trips/{id} (병렬, 실패는 개별 처리)
   |     404 --> "서버에서 삭제된 여행입니다" 표시 + [목록에서 제거] 버튼 (WBR-09)
   |
   v  화면 하단 상시 고지 (WBR-06)
   |     "여행 목록은 이 브라우저에만 저장됩니다.
   |      브라우저 데이터를 지우면 다시 열 수 없습니다.
   |      [목록 내보내기]  [목록 가져오기]  각 여행의 [공유 링크]도 복구 수단이 됩니다."
   |
   v  내보내기 --> TripListExport JSON 다운로드 (WBR-07)
   v  가져오기 --> JSON 병합 (trip_id 기준 중복 제거) (WBR-08)
```

---

## 11. Testable Properties (PBT-01 / PBT-R1·R3·R4)

u2 의 PBT 대상은 **순수 함수**에 한정합니다 (`unit-of-work.md` §4 — PBT-R1·R3·R4·R5).

### W13 `DeepLinkBuilder` — 왕복·불변식 (PBT-02, PBT-03)

| # | 속성 | 분류 |
|---|---|---|
| **WP-01** | `decodeParams(encodeParams(x)) == x` — 한글·공백·특수문자 포함 | Round-trip |
| **WP-02** | 생성된 URL 은 항상 `app` / `web` 두 값을 모두 갖는다 (한쪽만 생기지 않음) | Invariant |
| **WP-03** | `mode` 가 `TRANSIT` 이면 앱 URL 은 `route/public` 을 사용한다 | Invariant |
| **WP-04** | 좌표는 URL 에서 소수점 정밀도를 잃지 않는다 (6자리 이상 보존) | Invariant |

### 목록 내보내기/가져오기 — 왕복 (PBT-02)

| # | 속성 | 분류 |
|---|---|---|
| **WP-05** | `importList(exportList(x)) == x` — 순서 무관 집합 동등 | Round-trip |
| **WP-06** | 가져오기는 **멱등**하다 — 같은 파일을 두 번 넣어도 목록이 늘지 않는다 | Idempotence |

### 선택자(selector) — 불변식 (PBT-03)

| # | 속성 | 분류 |
|---|---|---|
| **WP-07** | 일자 총 이동시간 ≥ 0, 항목이 1개 이하면 0 | Invariant |
| **WP-08** | 경고 배지 목록은 서버가 준 `warnings` 의 부분집합이다 (클라이언트가 만들어내지 않음) | Invariant |
| **WP-09** | 데모 배너는 `modes` 에 `"mock"` 이 하나라도 있을 때에만 표시된다 | Invariant |

### 폴링 간격 계산 — 불변식 (PBT-03)

| # | 속성 | 분류 |
|---|---|---|
| **WP-10** | 간격은 항상 1000ms 이상이고, 경과 시간에 대해 단조 비감소한다 | Invariant |
| **WP-11** | 경과 90초를 넘으면 항상 `stop` 을 반환한다 | Invariant |

### 도메인 생성기 (PBT-07, PBT-R3)

| 생성기 | 범위 |
|---|---|
| `savedTripRefs()` | 유효 UUID · 한글 제목 · ISO 날짜 · 토큰 유/무 |
| `coordinates()` | 국내 범위 (u1 과 동일 제약) |
| `placeNames()` | 한글·영문·공백·특수문자·이모지 포함 |
| `elapsedMs()` | 0 ~ 300,000 |

**프레임워크**: fast-check (PBT-R5). 셰링킹 활성 + 시드 로깅 (PBT-R4).

### PBT 비대상

| 대상 | 사유 |
|---|---|
| React 컴포넌트 렌더링 | 예제 기반 테스트로 검증 (PBT-10) |
| `NaverMapAdapter` | 외부 SDK 의존. 목 어댑터로 예제 검증 |
| API 클라이언트 | I/O 경계. MSW 등으로 목킹해 예제 검증 |
