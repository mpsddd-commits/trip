# Functional Design Plan — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 1/3)
**Created**: 2026-08-13T05:15:00Z
**Prior context**: `requirements.md`, `application-design/` 5종(DD-1~DD-25), `unit-of-work*.md`(UD-1~UD-14)
**Unit 책임**: C1~C33 (33 컴포넌트) · Owner FR 15건 · SEC 주 책임 13건 · PBT-R 8건
**Status**: ⛔ 답변 대기 중

---

## 📌 답변 방법

각 질문의 `[Answer]:` 태그 뒤에 알파벳을 적어주세요. 맞는 선택지가 없으면 `X` 를 고르고 직접 설명해 주세요.
작성 후 **"완료"** 또는 **"전부 추천안"** 이라고 알려주시면 산출물 3종을 생성합니다.

---

## 🔴 사전 조사에서 발견한 문제 1건 — 답변 전 꼭 읽어주세요

### FR-13(영업시간 경고)에 쓸 데이터 소스가 없습니다

**네이버 지역검색 API 응답에는 영업시간 필드가 없습니다.** 응답 필드는 다음이 전부입니다:

| 필드 | 내용 |
|---|---|
| `title` | 업체·기관명 (검색어 강조 태그 포함) |
| `link` | 업체·기관 링크 |
| `category` | 분류 |
| `description` | 설명 |
| `telephone` | 전화번호 |
| `address` / `roadAddress` | 지번 / 도로명 주소 |
| `mapx` / `mapy` | 좌표 |

즉 **FR-13 을 구현할 근거 데이터가 확보되지 않습니다.** → **Q10 에서 결정**

### 함께 확인이 필요한 항목 (Build & Test 검증 대상으로 기록)

- `mapx`/`mapy` 의 **좌표계**를 실응답으로 확인해야 합니다. 지역검색 좌표는 과거 KATECH(TM128) 계열이었고 현재는 WGS84 기반 정수 표현으로 알려져 있으나, **문서만으로 단정하지 않고 실측으로 확정**합니다. 잘못 해석하면 지도상 위치가 전부 어긋납니다. → 좌표 변환을 **한 함수에 격리**하고 실측 후 확정 (설계 반영)
- `title` 에 포함되는 강조 태그(`<b>`)는 저장 전에 제거해야 합니다 (SEC-05 관련)

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [ ] `unit-of-work-story-map.md` 의 u1 Owner FR 15건 + 참여 4건 확인
- [ ] Application Design 이월 항목 10건(u1분) 을 질문으로 전환했는지 확인
- [ ] SEC 주 책임 13건의 비즈니스 규칙 수준 요구사항 도출
- [ ] PBT-R 8건의 검증 대상 속성 확정

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [ ] Q1~Q4 AI 생성 파이프라인 (LLM · 그라운딩)
- [ ] Q5~Q9 경로·시간 도메인 로직
- [ ] Q10~Q11 장소 데이터 및 추천
- [ ] Q12~Q14 데이터 모델 및 수명 정책
- [ ] Q15~Q17 오류 처리 및 보안 정책
- [ ] Q18~Q19 비용·규모 통제

### 1.3 필수 산출물 생성
- [ ] `construction/u1-trip-backend/functional-design/domain-entities.md` — 엔티티·관계·속성·제약
- [ ] `construction/u1-trip-backend/functional-design/business-logic-model.md` — 워크플로·알고리즘·데이터 변환·**Testable Properties**(PBT-01)
- [ ] `construction/u1-trip-backend/functional-design/business-rules.md` — BR-xx 비즈니스 규칙 전체 + FR 추적
- [ ] (프론트엔드 컴포넌트 문서는 u2 Functional Design 에서 작성 — 본 유닛 해당 없음)

### 1.4 검증
- [ ] Owner FR 15건 전부 비즈니스 규칙으로 표현 (미매핑 0건)
- [ ] Application Design 이월 10건 전부 해소
- [ ] **Testable Properties** 절 작성 (PBT-01)
- [ ] Security Compliance / PBT Compliance 요약

---

## Part 2. 설계 질문

### 🤖 AI 생성 파이프라인

## Question 1
🔴 **최우선 이월 항목**: C23 `PlaceResolver` 가 LLM 이 만든 장소명과 네이버 검색 결과를 **"같은 장소"로 판정하는 기준**은 무엇입니까? (FR-3, CON-7 — 환각 차단의 핵심)

A) ⭐ **다중 조건 AND** — ① 정규화 문자열 유사도 ≥ 0.6 (공백·특수문자·법인격 제거 후) **그리고** ② 검색 결과가 요청 지역 범위 내 **그리고** ③ 카테고리 힌트가 있으면 대분류 일치. 3개 중 하나라도 실패하면 미해결 처리
　→ 보수적. 거짓 매칭(엉뚱한 장소가 일정에 들어감)보다 미해결(사용자가 확인)이 안전하다는 판단

B) **유사도 단독** — 문자열 유사도만으로 판정 (단순, 오탐 위험)

C) **1순위 결과 무조건 채택** — 검색 결과 첫 번째를 그대로 사용 (⚠️ 환각 차단 실패)

D) **LLM 재확인** — 검색 결과 목록을 다시 LLM 에 보내 "이 중 맞는 것"을 고르게 함 (비용·지연 증가, 환각 재유입 가능)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
그라운딩 **미해결 항목이 많을 때** 어떻게 처리합니까? (FR-3, DD-23 `partial` 상태)

A) ⭐ **비율 기준 3단계** — 해결률 100%: `succeeded` / 1~99%: `partial` + 미해결 목록 노출 / 0%: `failed`. **미해결 항목은 일정에 넣지 않고 별도 목록으로만 제시**

B) **개수 기준** — 미해결 3건 이하면 무시하고 진행

C) **전건 해결 필수** — 하나라도 실패하면 전체 재생성

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
C22 `LlmDraftGenerator` 의 **모델과 응답 형식**은? (SEC-13 — 응답 스키마 검증 필수)

A) ⭐ **`claude-sonnet-5` + 구조화 출력(도구 호출) 강제** — 모델이 정해진 JSON 스키마로만 답하도록 강제하고, 수신 후 서버에서 **한 번 더 스키마 검증**. 검증 실패 시 최대 2회 재시도 후 `failed`

B) **`claude-opus-5` + 구조화 출력** — 품질 우선, 비용·지연 증가

C) 자유 텍스트 응답 후 파싱 (⚠️ SEC-13 위반 소지, 파싱 실패율 높음)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
LLM 에게 **좌표를 물어보지 않는다**는 원칙(DD-12)은 확정입니다. 그렇다면 LLM 출력에서 **어떤 필드까지 신뢰**합니까?

A) ⭐ **장소명·카테고리 힌트·권장 체류시간·추천 사유·권장 시간대만 수용.** 주소·좌표·전화·영업시간·가격은 **수용하지 않음**(네이버 검색 결과로만 채움)
　→ 사실성이 중요한 필드는 전부 외부 소스에서 확보

B) 주소도 수용해서 그라운딩 질의 정확도를 높임 (환각 주소가 검색을 오도할 위험)

C) 전부 수용하고 검색 결과로 덮어쓰기

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🗺️ 경로·시간 도메인 로직

## Question 5
C18 `RouteOptimizer` 의 **목적함수**는 무엇을 최소화합니까? (FR-8)

A) ⭐ **총 이동시간 단독** — 가장 단순하고 PBT 불변식("결과 ≤ 입력")이 명확히 성립

B) **이동시간 + 시간대 적합도 페널티** — 예: 식당은 식사 시간대에, 야경 명소는 저녁에 배치 (LLM 이 준 `권장 시간대` 활용). 품질은 좋아지나 "총 이동시간 비악화" 불변식이 깨져 PBT-R2 수정 필요

C) 이동시간 + 이동거리 가중합

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
C18 의 **탐색 종료 조건**은? (n 이 커지면 2-opt 가 오래 걸립니다)

A) ⭐ **3중 상한** — ① 개선 없는 반복 50회 **또는** ② 총 반복 1000회 **또는** ③ 경과 200ms 중 먼저 도달하는 것. 상한 도달 시 그 시점 최선해 반환(항상 유효한 해)
　→ NFR-1(500ms)을 지키면서 결과가 항상 존재

B) 완전 수렴까지 실행 (n 이 크면 지연)

C) 고정 반복 횟수만

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
C15 `TimelineCalculator` 에서 **고정 시각 항목과 이동시간이 충돌**할 때(앞 일정이 길어져 고정 시각에 못 맞춤) 어떻게 합니까? (이월 항목)

A) ⭐ **고정 시각을 지키고 충돌을 경고로 표시** — 고정 항목의 시각은 절대 변경하지 않고(PBT-R2 불변식 유지), 도착 불가 상황을 `conflict` 플래그로 표시해 사용자가 판단하게 함

B) **앞 항목의 체류시간을 자동 축소**해 맞춤 (사용자 의도 훼손)

C) **고정 시각을 밀어냄** (고정의 의미 상실, PBT 불변식 위반)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8
하루 활동 **종료 시각을 초과**하는 일정은 어떻게 처리합니까?

A) ⭐ **경고만 표시하고 그대로 유지** — 초과분을 `overflow` 로 표시. 자동으로 다음 날로 옮기지 않음(사용자 일정 의도 존중)

B) 초과 항목을 자동으로 다음 날 앞쪽에 이동

C) 초과 항목 자동 삭제

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
C17 `TravelTimeEstimator` 의 **근사 파라미터 구체값**은? (이월 항목, CON-1)

A) ⭐ **도보**: 하버사인 × 1.3 ÷ 4.5km/h, 최소 3분 / **대중교통**: 하버사인 × 1.4 ÷ 20km/h + 고정 대기 10분, 최소 10분 / **자동차 폴백**: 하버사인 × 1.4 ÷ 30km/h(시내), 최소 5분
　→ 전부 `.env` 로 조정 가능하게 두고, 대중교통은 `is_estimate=True` 배지 필수

B) 더 보수적인 값(느리게 추정) — 일정이 여유로워지지만 비현실적으로 늘어짐

C) 실측 데이터 기반 보정 도입 (데이터 없음 — 이번 범위 밖)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 📍 장소 데이터 및 추천

## Question 10
🔴 **위 사전 조사 참조**: 네이버 지역검색 API 는 **영업시간을 제공하지 않습니다.** FR-13(영업시간 경고)을 어떻게 합니까?

A) ⭐ **사용자 수동 입력 + 정보 있을 때만 경고** — 장소별로 영업시간을 사용자가 선택적으로 입력할 수 있게 하고, **입력된 경우에만** C19 가 경고를 산출. 미입력 장소는 경고 없음(거짓 경고 방지). FR-13 은 "정보가 있을 때만 동작"으로 축소 확정
　→ 구현 비용 최소, 거짓 정보 위험 0

B) **LLM 추정값 사용** — 카테고리 기반으로 LLM 이 일반적 영업시간을 추정 (⚠️ CON-7 위반 — 근거 없는 사실 주장)

C) **한국관광공사 TourAPI 추가 연동** — 관광지·문화시설의 이용시간을 공공데이터로 확보 (신규 API 키·구현 추가. 음식점은 여전히 미해결)

D) **FR-13 을 범위에서 제외** — 영업시간 경고 기능을 없앰

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
C27 `RecommendationService` 의 **추천 콘텐츠 품질 기준**은? (FR-20, DD-24 — 근거 없으면 미노출)

A) ⭐ **블로그 3건 이상 확보 시에만 요약 생성** — 3건 미만이면 요약 없이 원문 링크만 노출. 요약은 3~5개 항목(대표 메뉴 또는 관람 포인트)으로 제한하고 **각 항목이 어느 블로그에서 왔는지 표시하지 않음**(요약 특성상 혼합) — 대신 전체 근거 목록을 함께 노출

B) 블로그 1건만 있어도 요약 (근거 빈약)

C) 요약 없이 블로그 제목·발췌만 나열 (LLM 비용 0, 가독성 낮음)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🗄️ 데이터 모델 및 수명 정책

## Question 12
**여행 데이터 삭제** 방식은? (FR-4, SEC-13 감사)

A) ⭐ **하드 삭제 + 감사 로그 기록** — 여행 삭제 시 관련 행을 실제로 제거하되, 삭제 사실(시각·trip_id·항목 수)을 감사 로그에 남김. 계정이 없어 복구 요청 주체가 없으므로 소프트 삭제의 이득이 작음

B) **소프트 삭제** — `deleted_at` 표시만 하고 데이터 유지 (복구 가능, 저장 증가)

C) 소프트 삭제 후 30일 뒤 자동 하드 삭제

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13
**공유 토큰 수명**은? (FR-25, SEC-08)

A) ⭐ **무기한 + 수동 폐기** — 토큰은 만료되지 않고 사용자가 명시적으로 폐기(재발급)할 때까지 유효. 여행 삭제 시 함께 무효화

B) **발급 후 30일 자동 만료**

C) 무기한, 폐기 기능 없음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**작업(job) 레코드와 캐시**의 보존 기간은? (C28, C12)

A) ⭐ **job: 완료 후 24시간 보존 후 정리 / 캐시: TTL 만료 후 7일 유예 뒤 정리.** 정리는 기동 시 + 하루 1회 백그라운드 실행

B) job·캐시 무기한 보존 (DB 무한 증가)

C) job 은 조회 즉시 삭제

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### ⚠️ 오류 처리 및 보안 정책

## Question 15
**예외 분류 체계**를 어떻게 구성합니까? (이월 항목, SEC-09·SEC-15)

A) ⭐ **6종 분류** — `ValidationError`(400) / `NotFoundError`(404) / `RateLimitError`(429) / `QuotaExhaustedError`(429) / `ExternalServiceError`(502) / `InternalError`(500). 각각 **사용자 노출 문구를 고정 매핑**하고 내부 상세는 로그에만
　→ 문구가 고정되어 내부 구조가 메시지로 새어나가지 않음

B) 더 세분화된 분류 (10종 이상)

C) FastAPI 기본 예외만 사용

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 16
C4 `RateLimiter` 의 **임계값과 등급**은? (이월 항목, SEC-11, CA-5 — 비용 남용 차단)

A) ⭐ **3등급** — `EXPENSIVE`(AI 생성): IP당 **5회/시간**, 전역 **50회/일** / `EXTERNAL`(검색·추천·경로): IP당 **60회/분** / `CHEAP`(조회·편집): IP당 **300회/분**. 전부 `.env` 조정 가능
　→ AI 생성이 가장 비싼 경로이므로 가장 엄격하게

B) 단일 등급으로 전체 IP당 100회/분

C) 레이트 리밋 없음 (⚠️ SEC-11 위반)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 17
C12 **캐시 키 정규화** 규칙은? (이월 항목, NFR-4)

A) ⭐ **질의 문자열은 소문자화 + 공백 정규화 + 유니코드 NFC 정규화 후 해시**, 좌표는 **소수점 5자리(약 1m)로 반올림** 후 해시. 페이징 파라미터는 키에 포함
　→ 사소한 표기 차이로 캐시가 갈라져 쿼터를 낭비하는 것을 방지

B) 원본 파라미터를 그대로 직렬화해 해시 (적중률 낮음)

C) 좌표는 3자리(약 100m)로 반올림 (적중률 높으나 다른 장소가 같은 키가 될 위험)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 💰 비용·규모 통제

## Question 18
**여행 규모 상한**을 둡니까? (LLM 비용·응답 시간 통제)

A) ⭐ **기간 최대 10일 / 하루 항목 최대 15개 / 여행당 총 항목 100개** — 초과 시 검증 오류. 전부 `.env` 조정 가능
　→ 그라운딩은 항목당 검색 1회이므로 항목 수가 곧 외부 호출 수

B) 상한 없음 (⚠️ 30일 × 20개 = 600회 검색 + 대형 LLM 호출)

C) 더 보수적으로 (5일 / 하루 10개)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 19
**기본 체류시간**을 카테고리별로 다르게 둡니까? (FR-7 기본값)

A) ⭐ **카테고리 매핑 + 기본값** — 음식점 60분 / 카페 40분 / 관광명소 90분 / 박물관·전시 120분 / 쇼핑 90분 / 숙소 체크인 30분 / 그 외 60분. LLM 이 제시한 권장 체류시간이 있으면 **그것을 우선**하고, 없으면 이 표를 사용

B) 전부 60분 고정

C) LLM 값만 사용하고 없으면 사용자가 직접 입력

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

**"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.
답변의 모호성·모순을 분석한 뒤 `construction/u1-trip-backend/functional-design/` 산출물 3종을 생성하고 승인을 요청합니다.

> ⚠️ **Q10 을 특히 검토해 주세요.** FR-13(영업시간 경고)은 승인하신 요구사항에 들어 있지만,
> 네이버 지역검색 API 가 영업시간을 주지 않아 **원래 계획대로는 구현할 수 없습니다.**
> 추천안(A)은 기능을 없애지 않되 "사용자가 입력한 경우에만 동작"하도록 축소하는 방향입니다.
