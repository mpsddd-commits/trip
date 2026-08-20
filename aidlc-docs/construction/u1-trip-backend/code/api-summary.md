# API 계층 구현 요약 — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 17)
**Created**: 2026-08-13T08:50:00Z
**대상 단계**: Step 15(생성) · Step 16(테스트)

---

## 1. 생성 파일 (17개, 누적 98개)

| 파일 | 컴포넌트 | 내용 |
|---|---|---|
| `api/schemas.py` | **C33** | 요청·응답 스키마 12종, `extra="forbid"`, BR-01~05·BR-15 제약 |
| `api/deps.py` | — | **컨테이너 + 배선** (신규, §4 조정 1) |
| `api/routers/trips.py` | **C32** | CRUD·항목 편집·순서 변경·최적화·영업시간 |
| `api/routers/generation.py` | C32 | 202 + job_id, 폴링 |
| `api/routers/places.py` | C32 | 검색·추천 콘텐츠·주변 추천 |
| `api/routers/share.py` | C32 | 토큰 발급·폐기·읽기 전용 조회 |
| `api/routers/export.py` | C32 | `.ics` |
| `api/routers/health.py` | C32 | liveness / readiness |
| `api/static.py` | **L7** | 정적 서빙 + 캐시 헤더 + SPA catch-all |
| `main.py` | — | **미들웨어 9단계** + 수명 주기 + 전역 오류 |
| 테스트 6종 | — | **48건** |

**엔드포인트 총 19개** — `application-design/component-methods.md` §7 과 일치

---

## 2. 미들웨어 조립 (LC-1 / ND-15)

FastAPI 는 **등록 역순**으로 실행하므로, LC-1 순서를 만들기 위해 역순으로 `add_middleware` 합니다.

```
(1) GlobalErrorMiddleware   ← 가장 바깥. (2)~(8) 어디서 터져도 Problem Details
(2) CorrelationIdMiddleware ← 이후 모든 로그에 ID 부착
(3) AccessLogMiddleware     ← 처리시간·외부호출·캐시적중 기록
(4) SecurityHeadersMiddleware
(5) GZipMiddleware (1KB 초과)
(6) CORSMiddleware          ← 오리진이 설정된 경우에만 등록 (ND-12)
(7) BodySizeLimitMiddleware (1MB)
(8) RateLimit               ← 라우터 의존성으로 부착 (등급별)
(9) Router + Schema
```

**(8) 을 라우터 의존성으로 둔 이유**: 등급이 엔드포인트마다 다르기 때문입니다(BR-49). 미들웨어로 만들면 경로 패턴 매칭이 필요해지고, 새 라우트를 추가할 때 등급 지정을 잊기 쉽습니다. 의존성으로 두면 **라우트 정의에 등급이 붙어 있어** 누락이 눈에 띕니다.

---

## 3. 설계 규칙이 API 표면에 남은 지점

| 규칙 | 구현 | 검증 |
|---|---|---|
| **BR-39** 열거 차단 | `GET /api/trips` 를 **정의하지 않음** | `test_no_trip_list_endpoint` — OpenAPI 스키마까지 확인 |
| **BR-37 / DD-25** 공유는 읽기 전용 | `/api/shared/*` 에 GET 만 존재 | `test_no_write_endpoints_under_shared_path` — OpenAPI 의 메서드 집합 검사 |
| **BR-36** 토큰 독립성 | `secrets.token_urlsafe(32)` | `test_share_token_is_independent_of_trip_id` |
| **BR-58** 고정 문구 | 전역 핸들러가 6종 문구만 반환 | `test_no_stack_trace_in_any_error_response` — 누출 마커 9종 검사 |
| **SEC-09** 문서 미노출 | `docs_url=None`, `redoc_url=None` | `test_api_docs_are_not_exposed` |
| **ND-14** 헬스체크가 외부 미호출 | 라우터가 클라이언트를 참조하지 않음 | `test_health_module_does_not_touch_external_clients` — **소스 검사** |
| **SEC-04** CSP | `script-src` 에 unsafe 없음 | `test_csp_never_allows_unsafe_script` |
| **BR-35** 영업시간 사용자 입력 | `PUT .../opening-hours` 가 유일한 경로 | `test_opening_hours_is_user_entered_only` |
| **CA-4** HSTS | HTTPS 요청에만 | `test_hsts_is_absent_over_plain_http` |

---

## 4. 설계 대비 조정 3건

| # | 조정 | 사유 | 위반 여부 |
|---|---|---|---|
| 1 | `api/deps.py` **신설** (컨테이너) | `main.py` 에 배선을 전부 넣으면 라우터가 전역 상태에 의존해 테스트가 어려워진다 | ❌ 아님 |
| 2 | 라우터 파일 **7개 → 6개** (`routes` 를 `trips` 에 통합) | 순서 최적화·이동시간 재계산이 여행 항목 편집과 같은 자원을 다룬다. 파일을 나누면 `_recompute_and_save` 가 중복된다 | ❌ 아님 — 엔드포인트 19개는 그대로 |
| 3 | 레이트 리밋을 **미들웨어가 아닌 라우터 의존성**으로 | 등급이 엔드포인트마다 다름(BR-49). 라우트 정의에 등급이 붙어 있어야 누락이 드러난다 | ❌ 아님 — LC-1 의 실행 위치(라우터 직전)는 동일 |

---

## 5. 편집 후 타임라인 재계산 (FR-9, BR-29)

항목 추가·삭제·수정·순서 변경 후 `_recompute_and_save()` 가 타임라인을 다시 계산합니다.

**외부 호출이 발생하지 않는 이유**: 장소가 그대로면 `build_matrix` 의 인접 쌍 조회가 **캐시에 적중**합니다(BR-29). 이동수단이 바뀐 구간만 새로 호출됩니다.

---

## 6. 미검증 항목

| # | 항목 | 해소 |
|---|---|---|
| 1 | 테스트 실행 결과 (누적 **163건**) | Build & Test |
| 2 | 미들웨어 실행 순서의 실제 동작 | Build & Test — 등록 역순 규칙에 의존 |
| 3 | CSP 허용 도메인의 실제 충분성 | Build & Test — 지도 SDK 로딩 실측 |
| 4 | 정적 자산 캐시 헤더 (Vite 산출물 필요) | Build & Test I-11 |

---

## 7. Compliance — Step 15~17

**Security**
- SEC-04 ✅ 헤더 4종 + CSP. `script-src` unsafe 불허 검증
- SEC-05 ✅ `extra="forbid"` + 길이·범위 제약 + 좌표 국내 범위
- SEC-08 ✅ 목록 API 부재 / 공유 경로 GET 전용 / CORS 와일드카드 차단
- SEC-09 ✅ 문서 엔드포인트 비활성, 고정 문구, 스택트레이스 미노출
- SEC-11 ✅ 등급별 레이트 리밋을 라우트 정의에 부착
- SEC-15 ✅ 전역 오류 미들웨어(최외곽) + 예외 핸들러 3종
**Blocking findings: 0건**

**PBT**: api 계층은 I/O 경계로 PBT 비대상. 예제 48건으로 검증 (PBT-10).
**Blocking findings: 0건**
