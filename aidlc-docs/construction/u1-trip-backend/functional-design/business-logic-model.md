# Business Logic Model — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 1/3)
**Created**: 2026-08-13T05:30:00Z

> 기술 비종속 워크플로·알고리즘 정의입니다. 각 단계의 판정 규칙은 `business-rules.md` 의 BR-xx 를 참조합니다.

---

## WF-1. 여행 생성 (FR-1, FR-4)

```
TripSpec 입력
   |
   v  [BR-01~05] 검증: 기간 <= 10일, 인원 1~20, day_end > day_start, 목적지 1~50자
   |
   v  Trip 생성 (UUIDv4) + TripDay N개 생성 (day_index 1..N)
   |
   v  AuditEvent(TRIP_CREATED) 기록
   |
   v  Trip 반환
```
항목은 이 시점에 생성되지 않습니다. AI 생성(WF-2) 또는 수동 추가로 채워집니다.

---

## WF-2. AI 일정 생성 파이프라인 (FR-2, FR-3) — 핵심 워크플로

```
POST /trips/{id}/generate
   |
   v  [C4] RateLimiter: EXPENSIVE 등급 검사 (IP 5회/시간, 전역 50회/일)  [BR-49]
   |
   v  [C28] GenerationJob 생성 -> job_id 즉시 반환 (202)
   |
   +--- 백그라운드 ---------------------------------------------------+
   |                                                                  |
   |  1. DRAFTING     progress 0.00 -> 0.20                           |
   |     [C22] 프롬프트 구성 -> LLM 호출 -> 스키마 검증 [BR-06~09]    |
   |     실패: 최대 2회 재시도 -> 전부 실패 시 job=failed              |
   |     출력: list[list[PlaceCandidate]]  (좌표 없음)                |
   |                                                                  |
   |  2. RESOLVING    progress 0.20 -> 0.60          [최상위 위험 차단]|
   |     [C23] WF-3 그라운딩 알고리즘 실행                             |
   |     출력: resolved: list[Place] / unresolved: list[Candidate]    |
   |     해결률 0% -> job=failed  [BR-13]                              |
   |                                                                  |
   |  3. ROUTING      progress 0.60 -> 0.80                           |
   |     [C24] WF-4 이동시간 행렬 구성                                 |
   |     Directions 실패 -> 하버사인 폴백, is_estimate=true  [BR-26]  |
   |                                                                  |
   |  4. OPTIMIZING   progress 0.80 -> 0.85                           |
   |     [C18] WF-5 순서 최적화 (일자별)                               |
   |     시간 상한 초과 -> 그 시점 최선해 사용  [BR-22]                |
   |                                                                  |
   |  5. SCHEDULING   progress 0.85 -> 0.95                           |
   |     [C15] WF-6 타임라인 계산 + 경고 산출                          |
   |                                                                  |
   |  6. SAVING       progress 0.95 -> 1.00                           |
   |     [C21] Trip / TripDay / ItineraryItem / Place / TravelLeg     |
   |           / UnresolvedCandidate 영속화                            |
   |     실패 -> 전체 롤백, job=failed (fail-closed)  [BR-53]          |
   |                                                                  |
   +------------------------------------------------------------------+
   |
   v  최종 상태 판정  [BR-13]
      unresolved == 0                      -> succeeded
      0 < resolved,  unresolved > 0        -> partial
      resolved == 0                        -> failed
```

### 단계 실패 정책 (NFR-3, SEC-15)

| 단계 | 부분 실패 허용 | 최종 상태 |
|---|---|---|
| DRAFTING | ✕ | `failed` |
| RESOLVING | ○ (1건 이상 해결 시) | `partial` |
| ROUTING | ○ (근사 폴백) | `partial` |
| OPTIMIZING | ○ (최적화 생략) | `partial` |
| SCHEDULING | ○ (경고 부착) | `partial` |
| SAVING | ✕ | `failed` |

---

## WF-3. 그라운딩 알고리즘 (FR-3) 🔴

**목적**: LLM 이 만든 장소명을 실재하는 장소로 해석하고, 해석되지 않은 것을 일정에서 배제합니다.

```
for each PlaceCandidate c:
    |
    v  1. 질의 구성:  "{trip.destination} {c.raw_name}"          [BR-10]
    |
    v  2. [C7] 지역검색 호출 (display=5)
    |     결과 0건 -> NO_SEARCH_RESULT, 미해결                    [BR-16]
    |     API 실패 -> SEARCH_UNAVAILABLE, 미해결
    |
    v  3. 각 결과에 대해 3조건 판정  [BR-11]
    |
    |     (1) 유사도:  normalize(c.raw_name) vs normalize(result.title)
    |                  similarity >= 0.60 ?
    |     (2) 지역:    result.address 또는 roadAddress 가
    |                  trip.destination 을 포함 ?
    |     (3) 카테고리: c.category_hint 가 있으면
    |                  classify(result.category) == classify(c.category_hint) ?
    |                  (힌트 없으면 이 조건은 통과 처리)
    |
    |     ---> 3조건 전부 참인 결과만 후보로 남김 (AND)
    |
    v  4. 후보 중 유사도 최고값 선택
    |     후보 없음 -> 가장 근접한 결과의 실패 사유를 기록해 미해결   [BR-12]
    |                  (best_candidate_name, best_match_score 저장)
    |
    v  5. 좌표 변환 to_wgs84(mapx, mapy) 후 범위 검증              [BR-15]
    |     범위 밖 -> INVALID_COORDINATE, 미해결
    |
    v  6. title 의 HTML 태그 제거, 카테고리 정규화                  [BR-14]
    |
    v  7. Place 생성 (source=NAVER_LOCAL, resolved_from=c.raw_name,
    |                 match_score=유사도)
    |
    v  8. 중복 제거: 같은 여행 내 동일 좌표(소수 5자리) 또는
                     동일 정규화 이름 -> 앞선 항목 유지, 뒤는 폐기  [BR-17]
```

### 문자열 정규화와 유사도 (BR-11 상세)

```
normalize(s):
    1. 유니코드 NFC 정규화
    2. 소문자화
    3. HTML 태그 제거
    4. 괄호와 그 내용 제거          예) "성심당 (본점)" -> "성심당"
    5. 법인격·수식어 제거            예) "주식회사", "(주)", "본점", "지점", "점"
    6. 공백·특수문자 제거

similarity(a, b):
    a == b                       -> 1.00
    a 가 b 의 부분문자열 (또는 역) -> 0.90
    그 외                         -> 1 - levenshtein(a, b) / max(len(a), len(b))
```

**임계값 0.60 의 성격**: 보수적 값입니다. 미해결이 늘어나는 방향이며, 이는 의도된 것입니다 — 엉뚱한 장소가 조용히 일정에 들어가는 것보다 사용자가 확인 목록을 보는 편이 안전합니다 (CON-7).

---

## WF-4. 이동시간 행렬 구성 (FR-10, FR-16)

```
places[0..n-1], mode 주어짐
   |
   v  for each 인접 쌍 (i, i+1):
      |
      +-- mode == CAR
      |     [C9] Directions 호출 -> {duration, distance, path}
      |     실패 -> [C17] estimate_car_fallback, is_estimate=true   [BR-26]
      |     source = DIRECTIONS_API 또는 HAVERSINE_CAR_FALLBACK
      |
      +-- mode == WALK
      |     [C17] estimate_walk:
      |        haversine(a,b) * 1.3 / 4.5km/h,  최소 3분           [BR-24]
      |     path = null, is_estimate = true
      |
      +-- mode == TRANSIT
            [C17] estimate_transit:
               haversine(a,b) * 1.4 / 20km/h + 10분,  최소 10분    [BR-25]
            path = null, is_estimate = true (항상)                  [BR-27]
   |
   v  DistanceMatrix 조립 (외부 호출 없이 조회만 가능한 값 객체)
```

**호출 절약**: 최적화(WF-5)에는 **모든 쌍(i,j)** 의 거리가 필요하지만, Directions 를 n² 번 호출하지 않습니다.
- 인접 쌍만 실제 API 호출
- 비인접 쌍은 **하버사인 근사로 채움** (최적화 탐색 전용, `is_estimate=true`)
- 최적화로 순서가 확정된 뒤 **새 인접 쌍만 다시 실제 호출** [BR-28]

→ API 호출이 `O(n)` 로 유지됩니다 (NFR-4).

---

## WF-5. 순서 최적화 알고리즘 (FR-8)

**목적함수**: 총 이동시간 최소화 (Q5=A — 단독 지표)

```
입력: items[0..n-1], matrix, mode, constraints
   |
   v  1. 고정 위치 분리                                            [BR-19]
   |     fixed = {i : items[i].time_fixed 또는 constraints.fixed_positions}
   |     movable = 나머지 인덱스
   |     anchor_start / anchor_end 도 고정으로 취급
   |
   v  2. n <= 8 이면 완전탐색(brute_force) 사용                    [BR-23]
   |     (PBT-R7 오라클과 동일 경로)
   |
   v  3. 초기해: 최근접 이웃
   |     anchor_start 부터 시작, 미방문 중 이동시간 최소 선택
   |
   v  4. 2-opt 개선 반복
   |     구간 (i, j) 뒤집기 -> 고정 위치가 이동하면 폐기
   |                        -> 총 이동시간이 줄면 채택
   |     종료 조건 (먼저 도달하는 것):                              [BR-22]
   |        - 개선 없는 반복 50회
   |        - 총 반복 1000회
   |        - 경과 200ms
   |
   v  5. 최선해 반환 (항상 유효한 순서)
```

**핵심 불변식** (PBT-R2 로 검증)
1. 결과의 항목 집합 == 입력의 항목 집합 (개수·구성 동일)
2. 고정 위치 항목의 인덱스 불변
3. `total(결과) <= total(입력)` — 최선해를 항상 보존하므로 악화 불가

> **Q5=A 선택의 부수 효과**: 목적함수가 총 이동시간 단독이므로 불변식 3이 자명하게 성립합니다.
> 시간대 적합도를 목적함수에 넣었다면(B안) 이 불변식이 깨져 PBT-R2 를 수정해야 했습니다.

**LLM `preferred_time_slot` 의 사용처**: 최적화 목적함수에는 **쓰지 않습니다.** 초안 단계의 항목 배치 순서에만 반영되고, 사용자가 "순서 최적화"를 실행하면 무시됩니다 [BR-21]. UI 표시용으로 보존합니다.

---

## WF-6. 타임라인 계산 알고리즘 (FR-9)

```
입력: items(순서 확정), matrix, day_start_time, day_end_time
   |
   v  cursor = day_start_time (KST)
   |
   v  for i in 0..n-1:
      |
      +-- items[i].time_fixed 인가?
      |     예: arrival = fixed_time                               [BR-31]
      |         cursor > fixed_time 이면
      |            -> FIXED_TIME_CONFLICT 경고 부착                [BR-32]
      |            -> 그래도 arrival 은 fixed_time 유지 (밀지 않음)
      |     아니오: arrival = cursor
      |
      v  departure = arrival + stay_minutes
      |
      v  영업시간 정보가 있으면 판정                                [BR-35]
      |     arrival 이 영업시간 밖 -> OUTSIDE_OPENING_HOURS 경고
      |     정보 없으면 아무 경고도 만들지 않음
      |
      v  departure > day_end_time -> DAY_OVERFLOW 경고            [BR-33]
      |     (다음 날로 옮기지 않음)
      |
      v  leg = matrix.get(i, i+1, mode)
      |     leg.is_estimate -> ESTIMATED_TRAVEL_TIME 경고         [BR-27]
      |
      v  cursor = departure + leg.duration
```

**핵심 불변식** (PBT-R2 로 검증)
1. `arrival[i] <= departure[i] <= arrival[i+1]` — 시각 단조 증가
2. 고정 항목의 `arrival` 은 항상 `fixed_time` 과 일치
3. 항목 개수·순서 보존
4. `stay_minutes >= 1`, `leg.duration >= 0` — 비음수

**시간대 처리**: 계산은 KST 로 하고 저장은 UTC 로 변환합니다 (NFR-7).

---

## WF-7. 추천 콘텐츠 생성 (FR-20, FR-21)

```
Place 주어짐
   |
   v  [C8] 블로그 검색: "{place.name} {지역}"  (최대 10건)
   |     실패 -> sources = [], highlights = [] 로 종료 (degrade)   [BR-42]
   |
   v  블로그 3건 미만?                                              [BR-40]
   |     예 -> highlights = [] , sources = 확보분 그대로 노출
   |            (요약 생성하지 않음 — DD-24)
   |     아니오 -> 계속
   |
   v  [C22] LLM 요약 호출
   |     카테고리별 지시:
   |        RESTAURANT / CAFE  -> "대표 메뉴 3~5개"
   |        그 외              -> "관람 포인트 3~5개"
   |     입력: 블로그 제목·발췌만 (본문 크롤링 안 함)              [BR-41]
   |     실패 -> highlights = [] (sources 는 유지)
   |
   v  [C8] 이미지 검색 (최대 6건) -> images (출처 필수)
   |     실패 -> images = []
   |
   v  PlaceContent {highlights, sources, images, is_ai_summary: true}
```

**degrade 원칙**: 이 워크플로의 **어떤 실패도 장소 상세 화면 전체를 막지 않습니다.** 실패한 섹션만 비어 있습니다 (NFR-3).

---

## WF-8. `.ics` 내보내기 (FR-26)

```
Trip -> VCALENDAR
   |
   v  각 ItineraryItem -> VEVENT
   |     UID       = item_id@trip.local
   |     DTSTART   = arrival_at   (TZID=Asia/Seoul)
   |     DTEND     = departure_at (TZID=Asia/Seoul)
   |     SUMMARY   = place.name
   |     LOCATION  = place.road_address 또는 address
   |     DESCRIPTION = memo + 경고 요약
   |     GEO       = latitude;longitude
   |
   v  텍스트 이스케이프: 쉼표·세미콜론·역슬래시·개행               [BR-45]
   v  줄 길이 75옥텟 접기(folding)
```

**왕복 손실 항목 (PBT-R1 에서 허용 오차로 문서화)** [BR-46]
| 항목 | 손실 여부 |
|---|---|
| `item_id`, 시각, 장소명, 주소, 메모, 좌표 | ✅ 보존 |
| `stay_minutes` | ✅ (DTEND - DTSTART 로 복원) |
| `travel_mode`, `warnings`, `place.category`, `phone` | ❌ **손실** (VEVENT 표준 필드 없음) |

→ 왕복 속성은 **보존 항목에 한해** 검증합니다.

---

## WF-9. 공유 (FR-25)

```
POST /trips/{id}/share
   |
   v  share_token = 암호학적 난수 32바이트 -> base64url (43자)     [BR-36]
   |     trip_id 와 수학적 관계 없음
   v  AuditEvent(SHARE_TOKEN_ISSUED)
   v  {share_token, url} 반환

GET /shared/{token}
   |
   v  토큰으로 Trip 조회 (trip_id 로는 조회 불가)
   v  ReadOnlyTrip 반환 — 편집 연산이 정의되지 않은 타입           [BR-37]

DELETE /trips/{id}/share
   |
   v  share_token = null  -> 기존 링크 즉시 무효화                 [BR-38]
   v  AuditEvent(SHARE_TOKEN_REVOKED)
```

---

## WF-10. 캐시·쿼터 (NFR-4)

```
외부 API 호출 요청
   |
   v  [C29] is_exhausted(api) ?                                   [BR-50]
   |     예 -> QuotaExhaustedError (호출하지 않음)
   |           AuditEvent(QUOTA_EXHAUSTED)
   |
   v  [C12] cache_key 산출 -> 조회                                 [BR-48]
   |     적중 && 미만료 -> 캐시 응답 반환 (쿼터 미소모)
   |
   v  [C6] 실제 호출
   |     타임아웃: 연결 5초 / 읽기 10초 (LLM 은 120초)
   |     재시도: 지수 백오프 최대 3회, 4xx 는 재시도 안 함         [BR-47]
   |
   v  [C29] record(api, 1)   — 성공·실패 모두 계측
   v  [C12] 응답 캐시 저장 (namespace 별 TTL)
```

**캐시 키 정규화** (Q17=A, BR-48)
```
문자열 파라미터: NFC 정규화 -> 소문자 -> 공백 축약 -> trim
좌표 파라미터  : 소수점 5자리 반올림 (약 1m)
페이징 파라미터: 그대로 포함
-> namespace + method + 정규화 파라미터 -> SHA-256
```

---

## 11. Testable Properties (PBT-01)

### C15 `TimelineCalculator` — 불변식 (PBT-03, PBT-R2)

| # | 속성 | 분류 |
|---|---|---|
| P-01 | 출력 항목 개수 == 입력 항목 개수 | Invariant |
| P-02 | 출력 항목 집합(id) == 입력 항목 집합 | Invariant |
| P-03 | `arrival[i] <= departure[i] <= arrival[i+1]` 단조 증가 | Invariant |
| P-04 | 고정 항목의 `arrival` KST 시각 == `fixed_time` | Invariant |
| P-05 | 모든 `stay_minutes >= 1`, 모든 `leg.duration >= 0` | Invariant |

### C18 `RouteOptimizer` — 불변식 + 오라클 (PBT-03, PBT-05, PBT-R2·R7)

| # | 속성 | 분류 |
|---|---|---|
| P-06 | 결과 항목 집합 == 입력 항목 집합 | Invariant |
| P-07 | 고정 위치 항목의 인덱스 불변 | Invariant |
| P-08 | `total(결과) <= total(입력)` — 비악화 | Invariant |
| P-09 | `n <= 8` 에서 `optimize()` 총 이동시간 == `brute_force()` 총 이동시간 | Oracle |
| P-10 | 동일 입력·동일 시드에서 결과 동일 (결정성) | Invariant |

### C17 `TravelTimeEstimator` — 불변식 (PBT-03)

| # | 속성 | 분류 |
|---|---|---|
| P-11 | 모든 결과의 `duration_sec >= 0`, `distance_m >= 0` | Invariant |
| P-12 | `haversine(a, a) == 0` | Invariant |
| P-13 | `haversine(a, b) == haversine(b, a)` — 대칭성 | Invariant |
| P-14 | 세 점에 대해 `haversine(a,c) <= haversine(a,b) + haversine(b,c)` — 삼각부등식 | Invariant |
| P-15 | `mode=TRANSIT` 결과는 항상 `is_estimate == true` | Invariant |
| P-16 | 최소 시간 보장: WALK ≥ 180초, TRANSIT ≥ 600초, CAR 폴백 ≥ 300초 | Invariant |

### C14 `DomainModels` — 왕복 (PBT-02, PBT-R1)

| # | 속성 | 분류 |
|---|---|---|
| P-17 | `from_dict(to_dict(x)) == x` — 전 도메인 값 객체 | Round-trip |
| P-18 | `Coordinate` 생성은 국내 범위 밖 입력을 항상 거부 | Invariant |

### C20 `IcsBuilder` — 왕복 (PBT-02, PBT-R1)

| # | 속성 | 분류 |
|---|---|---|
| P-19 | `parse(build(trip))` 의 **보존 항목**이 원본과 일치 (손실 항목은 WF-8 표에 문서화) | Round-trip |
| P-20 | 특수문자(쉼표·세미콜론·역슬래시·개행)를 포함한 메모도 왕복 보존 | Round-trip |

### C12 캐시 키 — 정규화 (PBT-02 보조)

| # | 속성 | 분류 |
|---|---|---|
| P-21 | 공백·대소문자·유니코드 표기만 다른 질의는 **같은 키**를 산출 | Invariant |
| P-22 | 1m 이상 떨어진 좌표는 **다른 키**를 산출 | Invariant |

### 도메인 생성기 (PBT-07, PBT-R3)

| 생성기 | 범위 |
|---|---|
| `coordinates()` | lat 33.0~39.0, lng 124.0~132.0 + 경계값 포함 |
| `itinerary_items()` | stay 1~720분, 고정/비고정 혼합, 0~15개 |
| `trip_specs()` | 기간 1~10일, 인원 1~20, 유효 시각 범위 |
| `distance_matrices()` | 대칭·비대칭 혼합, duration 0~14400초 |
| `memo_text()` | 특수문자·유니코드·빈 문자열·최대 길이 포함 |

**셰링킹·시드** (PBT-08, PBT-R4): Hypothesis 기본 셰링킹 활성. 실패 시 시드와 최소 반례를 출력. CI 설정 파일 제공(실행은 사용자 재량).

### PBT 비대상

| 컴포넌트 | 사유 |
|---|---|
| C23 `PlaceResolver` | 판정 규칙이 외부 데이터 형태에 의존. **예제 기반 테스트로 검증**(경계 유사도 0.59/0.60/0.61, 지역 불일치, 카테고리 불일치, 좌표 범위 밖 등) — PBT-10 |
| C22 `LlmDraftGenerator` | LLM 응답이 비결정적. 스키마 검증 로직만 예제 기반 테스트 |
| C21·C24~C29 | I/O 오케스트레이션. 목 기반 예제 테스트 |

**PBT-04(멱등성)**: 재평가 결과 — `optimize()` 는 `optimize(optimize(x)) == optimize(x)` 가 **성립하지 않을 수 있습니다**(2-opt 는 지역 최적해에서 멈추며 시간 상한에 걸리면 실행마다 도달점이 다를 수 있음). 멱등성을 주장하지 않으므로 **N/A** 로 유지합니다.
**PBT-06(상태 기반)**: `GenerationJob` 의 상태 전이는 선형(`queued → running → 종료`)이고 분기가 없어 상태 기반 PBT 의 이득이 낮습니다. **N/A** 유지.
