# Services 계층 구현 요약 — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 14)
**Created**: 2026-08-13T08:20:00Z
**대상 단계**: Step 12(생성) · Step 13(테스트)

---

## 1. 생성 파일 (18개, 누적 81개)

| 파일 | 컴포넌트 | 핵심 구현 |
|---|---|---|
| `services/place_resolver.py` | **C23** 🔴 | **3조건 AND 판정**(BR-11) + 정규화·유사도 + 미해결 분리 + 중복 제거 |
| `services/llm_draft.py` | **C22** | 도구 스키마 강제(BR-06) + 서버 2차 검증(BR-07) + **5개 필드만 수용**(BR-08) |
| `services/travel_matrix.py` | **C24** | **Directions 호출 O(n)**(BR-28) + 근사 폴백(BR-26) |
| `services/generation_service.py` | **C25** | 6단계 파이프라인 오케스트레이션 |
| `services/trip_service.py` | **C21** | CRUD + 공유 토큰 + 검증 + 감사 + 원자적 교체 |
| `services/place_search.py` | **C26** | 5건 페이징 + 주변 추천 |
| `services/recommendation.py` | **C27** | **근거 3건 미만이면 요약 없음**(BR-40) + 부분 실패 격리 |
| `services/job_service.py` | **C28** | job 수명 + `decide_final_state`(BR-13) |
| `services/job_runner.py` | **L3** | asyncio 태스크 + 동시 3 + 종료 취소 |
| `services/quota_service.py` | **C29** | 인메모리 계측 + 주기 플러시 + 상한 판정 |
| `domain/categories.py` | — | 카테고리 정규화 (신규, §3 조정 1) |
| `storage/mappers.py` | — | 도메인 ↔ ORM 매핑 (신규, §3 조정 2) |
| 테스트 6종 | — | **67건** |

### 테스트 구성

| 파일 | 건수 | 겨냥하는 규칙 |
|---|---|---|
| `test_place_resolver.py` | 16 | BR-11 3조건 경계 / BR-12 / BR-16 / BR-17 / **BR-18** |
| `test_llm_draft.py` | 9 | BR-06~09 / **스키마에 사실 필드 부재 검증** |
| `test_travel_matrix.py` | 8 | **BR-28 호출 수 O(n)** / CON-1 / BR-26 |
| `test_recommendation.py` | 8 | **BR-40** / BR-42~44 |
| `test_job_runner.py` | 13 | ND-3 / SP-4 / BR-49 |
| `test_generation_pipeline.py` | 7 | WF-2 / BR-13 / **BR-18** / BR-52 |

---

## 2. 🔴 구현 중 발견한 문제 1건 — 최적화 후 행렬 인덱스 재기준화

`DistanceMatrix` 는 `(from_index, to_index)` 로 조회하는데, **최적화 전 인덱스는 원래 배열 기준**이고 **타임라인 계산기(C15)는 `(위치 i, 위치 i+1)` 로 조회**합니다.

최적화로 순서가 바뀐 뒤 원본 행렬을 그대로 넘기면 **엉뚱한 구간의 이동시간을 읽습니다.** 설계 문서에는 이 재기준화 단계가 명시되어 있지 않았습니다.

→ `ItineraryGenerationService._reindex()` 를 추가해 확정 순서 기준으로 인덱스를 재부여합니다.
→ `test_full_pipeline_succeeds` 와 `test_positions_are_contiguous` 가 결과 정합성을 확인합니다.

이는 설계 위반이 아니라 **설계에 빠져 있던 구현 세부**입니다. `business-logic-model.md` WF-2 의 4→5단계 사이에 해당합니다.

---

## 3. 파생 결정 1건 — 쿼터 계측 방식 (CD-1)

`QuotaGate.record()` 는 `BaseHttpClient` 내부에서 **async 컨텍스트로부터 동기 호출**됩니다. 여기서 SQLite 에 직접 쓰면 **이벤트 루프가 막혀 ND-18 을 위반**합니다.

**해소**: 인메모리 증가 + 주기 플러시 + 기동 시 로드
- 기동 시 DB 의 오늘 값을 메모리로 로드 → **재시작 우회 방지 (SP-4 목적 달성)**
- 운영 중 메모리 증가 (논블로킹)
- 주기·종료 시 DB 플러시 (L8 스케줄러가 호출)

**손실 범위**: 비정상 종료 시 마지막 플러시 이후 카운트. 이는 상한을 **느슨하게** 만들 뿐 우회를 허용하지 않습니다.
`test_loaded_counts_prevent_restart_bypass` 가 로드 경로를 검증합니다.

---

## 4. 설계 대비 조정 2건 (파일 추가)

| # | 조정 | 사유 | 위반 여부 |
|---|---|---|---|
| 1 | `domain/categories.py` 신설 | 카테고리 정규화가 BR-11 ③(그라운딩)과 BR-52(체류시간) 양쪽에서 쓰인다. `models.py` 비대화 방지. domain 내부 모듈이므로 DD-16 유지 | ❌ 아님 |
| 2 | `storage/mappers.py` 신설 | 매핑을 서비스에 두면 C21 이 비대해지고, ORM 모델에 두면 도메인 지식이 storage 로 샌다 | ❌ 아님 |

---

## 5. 환각 차단의 코드 상 위치 (BR-18)

```
LlmDraftGenerator._to_candidate()
    └─ PlaceCandidate 는 raw_name / category_hint / stay / reason / time_slot 5개만
       (주소·좌표·전화 필드가 타입에 없다)
                 |
                 v
PlaceResolver._is_match()   ← 3조건 AND (BR-11)
    ├─ 통과 → Place 생성 (source=NAVER_LOCAL, resolved_from 기록)
    └─ 실패 → UnresolvedCandidate
                 |
                 v
ItineraryGenerationService._group_by_day()
    └─ resolution.resolved 만 순회한다.
       🔴 resolution.unresolved 는 이 함수에 **들어오지도 않는다.**
                 |
                 v
TripService.replace_itinerary(days, unresolved)
    └─ days 와 unresolved 를 **다른 테이블**에 저장한다.
```

`test_unresolved_never_becomes_a_place`(단위)와 `test_partial_when_some_places_unresolved`(통합)가 양쪽에서 확인합니다.

---

## 6. BR-28(호출 O(n))의 실제 구현

```
build_matrix(places, mode)
  ├─ 비인접 쌍 (i,j)  → 하버사인 근사, 외부 호출 0
  └─ 인접 쌍 (i,i+1)  → Directions 실호출          ... n-1 회

optimize()  ← 전체 쌍이 채워져 있어야 탐색 가능

refresh_adjacent(order)
  └─ 새로 인접해진 쌍만 실호출                      ... 최대 n-1 회
```

`test_directions_calls_are_linear_not_quadratic` 이 n=2·5·10·15 에서 **정확히 n-1 회**임을 확인합니다. 순진한 구현이라면 n=15 에서 210회입니다.

도보·대중교통은 외부 경로 API 자체가 없으므로(CON-1) **호출 0회**이며, `refresh_adjacent` 도 no-op 입니다.

---

## 7. 미검증 항목

| # | 항목 | 해소 |
|---|---|---|
| 1 | 테스트 실행 결과 (누적 115건) | Build & Test |
| 2 | 실 LLM 이 도구 스키마를 지키는지 | Build & Test (키 보유 시) |
| 3 | 실제 지역검색 결과에서 유사도 0.60 임계값의 적정성 | Build & Test — 필요 시 `.env` 로 조정 |
| 4 | 쿼터 플러시 주기의 적정성 (CD-1) | Build & Test |

---

## 8. Compliance — Step 12~14

**Security**
- SEC-05 ✅ `TripService.validate_spec` 이 BR-01~04 강제
- SEC-08 ✅ UUIDv4 + `secrets.token_urlsafe(32)` 공유 토큰 + 읽기 전용 타입 반환
- SEC-11 ✅ 레이트 리밋·쿼터·규모 상한
- SEC-13 ✅ LLM 응답 스키마 2차 검증 + 감사 로깅
- SEC-14 ✅ 쿼터 소진·토큰 발급/폐기·삭제를 감사 이벤트로 기록
- SEC-15 ✅ 파이프라인 전 구간 예외 처리, 저장 실패 시 전체 롤백(BR-53)
**Blocking findings: 0건**

**PBT**: services 는 I/O 오케스트레이션으로 PBT 비대상. 예제 기반 67건으로 검증 (PBT-10).
**Blocking findings: 0건**
