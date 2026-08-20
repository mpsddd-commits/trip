# Domain 계층 구현 요약 — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 5)
**Created**: 2026-08-13T07:00:00Z
**대상 단계**: Step 1(구조) · Step 2(core) · Step 3(domain) · Step 4(domain 테스트)

---

## 1. 생성 파일

### 프로젝트 기반 (Step 1)

| 파일 | 내용 |
|---|---|
| `backend/pyproject.toml` | pytest 설정 (`asyncio_mode=auto`, `property` 마커) |
| `backend/requirements.txt` | 런타임 의존성 **8개, 정확한 버전 고정** (SEC-10) |
| `backend/requirements-dev.txt` | 테스트·감사 의존성 4개 |
| `backend/app/__init__.py` 외 6개 | 패키지 마커 |

### core 계층 (Step 2) — C1~C5, L5, L6, L8

| 파일 | 컴포넌트 | 핵심 구현 |
|---|---|---|
| `app/core/enums.py` | — | `ApiName` / `EndpointTier` / `ErrorCode` / `AuditEventType` |
| `app/core/config.py` | **C1** | 설정 47개, `SecretStr`, `credential_status()`, **`BIND_HOST` 경고 로그**, `__repr__` 재정의로 인증 정보 노출 차단 |
| `app/core/logging_config.py` | **C2** | JSON 포매터, correlation ID(ContextVar), **민감값 마스킹 필터 4종**, 90일 로테이션 |
| `app/core/errors.py` | **C5** | 도메인 예외 6종 + `USER_MESSAGES` **고정 문구표** + RFC 9457 생성기 |
| `app/core/security_headers.py` | **C3** | CSP 기준선 상수 + HSTS는 HTTPS 시에만 (CA-4) |
| `app/core/body_limit.py` | **L6** | `content-length` 1MB 상한 |
| `app/core/access_log.py` | **L5** | correlation ID 미들웨어 + 처리시간·외부호출·캐시적중 로깅 |
| `app/core/rate_limit.py` | **C4** | 3등급 슬라이딩 윈도 + **전역 일일 카운터는 Protocol 주입** |
| `app/core/scheduler.py` | **L8** | 기동 시 1회 + 24시간 주기, 개별 작업 실패 격리 |

### domain 계층 (Step 3) — C14~C20, **의존성 0**

| 파일 | 컴포넌트 | 핵심 구현 |
|---|---|---|
| `app/domain/models.py` | **C14** | 값 객체 12종 + 열거형 9종 + `to_dict`/`from_dict` |
| `app/domain/matrix.py` | **C16** | 조회 전용 행렬. API 호출 없음 |
| `app/domain/estimator.py` | **C17** | 하버사인 + 도보·대중교통·자동차폴백 (BR-24~26) |
| `app/domain/optimizer.py` | **C18** | 최근접이웃 + 2-opt + **`brute_force` 오라클**, 3중 종료 조건 |
| `app/domain/timeline.py` | **C15** | 시각 전파 + 경고 4종 산출 |
| `app/domain/opening_hours.py` | **C19** | 사용자 입력 있을 때만 판정, 자정 넘김 처리 |
| `app/domain/ics.py` | **C20** | VEVENT 생성·파싱, 이스케이프, 75옥텟 접기, VTIMEZONE |

### 테스트 (Step 4)

| 파일 | 대상 |
|---|---|
| `tests/conftest.py` | Hypothesis 프로파일 — **셰링킹 활성 + `print_blob`**(PBT-08) |
| `tests/property/generators.py` | 도메인 생성기 7종 (PBT-07) |
| `tests/property/test_timeline_properties.py` | **P-01 ~ P-05** |
| `tests/property/test_optimizer_properties.py` | **P-06 ~ P-10** |
| `tests/property/test_estimator_properties.py` | **P-11 ~ P-16** + 보조 1건 |
| `tests/property/test_roundtrip_properties.py` | **P-17 ~ P-20** |
| `tests/unit/test_domain_examples.py` | 경계 예제 **16건** (PBT-10) |

**생성 파일 합계: 33개** (마커 5 포함)

---

## 2. 🔴 설계 정정 1건 — P-03 불변식

### 문제
Functional Design(`business-logic-model.md` §11)은 P-03 을 다음과 같이 무조건 성립하는 불변식으로 기술했습니다.

> `arrival[i] <= departure[i] <= arrival[i+1]` — 시각 단조 증가

그러나 이는 **BR-31·BR-32 와 동시에 성립할 수 없습니다.**
고정 시각 항목의 도착이 물리적으로 불가능할 때, BR-32 는 **시각을 밀지 않고 경고만 부착**하도록 규정합니다. 그 지점에서 `departure[i] > arrival[i+1]` 이 되어 단조성이 깨집니다.

### 정정
정확한 불변식은 다음과 같습니다.

> **`arrival[i] <= departure[i]` 는 항상 성립한다.**
> **`departure[i] <= arrival[i+1]` 은 `FIXED_TIME_CONFLICT` 경고가 없는 구간에서만 성립한다.**

### 반영 위치
- `app/domain/timeline.py` 모듈 docstring
- `tests/property/test_timeline_properties.py::test_p03_times_are_monotonic_where_no_conflict`
- 본 문서 및 Build & Test 보고서

> 이는 **구현이 설계를 위반한 것이 아니라, 설계 문서의 속성 서술이 부정확했던 경우**입니다. BR-31·BR-32 는 그대로 유지됩니다.

---

## 3. 설계 대비 배치 조정 (3건)

| # | 조정 | 사유 | 설계 위반 여부 |
|---|---|---|---|
| 1 | `app/core/enums.py` **신설** (계획상 core 8파일 → 9파일) | `ApiName`·`ErrorCode` 등을 core·clients·services·storage 가 공통 참조. 한 곳에 모아 순환 import 방지 | ❌ 아님 |
| 2 | `EstimatorParams` / `OptimizeLimits` **도메인 내 dataclass 로 정의** | DD-16(의존성 0) 유지. 설정값을 import 하지 않고 주입받기 위함 | ❌ 아님 — 오히려 규칙 준수 수단 |
| 3 | `C4 RateLimiter` 의 전역 카운터를 **Protocol 주입** | ND-8. core 가 services 구체 타입에 의존하지 않도록 | ❌ 아님 — 설계에 명시됨 |

---

## 4. 규칙 준수 자체 점검

| 생성 원칙 | 준수 여부 | 근거 |
|---|---|---|
| 1. `domain/` 의존성 0 | ✅ | `app/domain/*` 의 import 는 표준 라이브러리 + `app.domain.*` 뿐 |
| 4. 외부 응답 검증 후 수용 | ⏭ | clients·services 단계(Step 9~13) |
| 5. 오류 문구 6종 고정 | ✅ | `errors.USER_MESSAGES` 외 경로 없음 |
| 6. 인증 정보 미노출 | ✅ | `SecretStr` + `Config.__repr__` 재정의 + 마스킹 필터 |
| 8. 의존성 버전 고정 | ✅ | 범위 지정자(`>=`, `~=`) 0건 |
| 10. 네트워크 비의존 테스트 | ✅ | domain 테스트는 I/O 없음 |
| 11. PBT 셰링킹·시드 | ✅ | `conftest.py` — `print_blob=True`, `derandomize=False` |
| 12. 파일 상단 컴포넌트·BR 주석 | ✅ | 전 파일 docstring 에 명시 |

---

## 5. 구현된 BR 매핑

| BR 범위 | 구현 위치 |
|---|---|
| BR-05 (본문 크기) | `core/body_limit.py` |
| BR-08 (후보 필드 제한) | `domain/models.py::PlaceCandidate` — 필드 5개만 존재 |
| BR-15 (좌표 범위) | `domain/models.py::Coordinate.__post_init__` |
| BR-19~23 (최적화) | `domain/optimizer.py` |
| BR-24~27 (이동시간) | `domain/estimator.py`, `domain/models.py::TravelLeg.__post_init__` |
| BR-31~35 (타임라인·경고) | `domain/timeline.py`, `domain/opening_hours.py` |
| BR-45, BR-46 (ics) | `domain/ics.py` |
| BR-49 (레이트 리밋) | `core/rate_limit.py` |
| BR-52 (기본 체류시간) | `domain/models.py::DEFAULT_STAY_MINUTES` |
| BR-58 (오류 문구) | `core/errors.py::USER_MESSAGES` |
| BR-60 (정리 주기) | `core/scheduler.py` |

나머지 BR(그라운딩·LLM·캐시·쿼터·공유·수명)은 Step 6~15 에서 구현합니다.

---

## 6. 미검증 항목 (Build & Test 대기)

| # | 항목 | 상태 |
|---|---|---|
| 1 | **테스트 실행 결과** | 작성만 완료. 실행은 Build & Test (규칙상) |
| 2 | 의존성 버전의 실제 설치 가능 여부 | `pip install` 실측 필요 |
| 3 | ICS 왕복 정밀도 (마이크로초 손실) | 생성기가 초 단위만 만들도록 제한. 실측 확인 필요 |
| 4 | 2-opt 200ms 상한의 실제 도달 여부 | 항목 15개 기준 실측 필요 |

---

## 7. Compliance — Step 1~5

**Security**: SEC-03(마스킹·로테이션) ✅ / SEC-05(본문 상한·좌표 검증) ✅ / SEC-09(고정 문구) ✅ / SEC-10(버전 고정) ✅ / SEC-11(레이트 리밋 골격) ✅ / SEC-12(SecretStr·repr 차단) ✅ / SEC-14(90일 로테이션) ✅
**Blocking findings: 0건**

**PBT**: PBT-02(P-17~P-20) ✅ / PBT-03(P-01~P-16) ✅ / PBT-07(생성기 7종) ✅ / PBT-08(셰링킹·blob) ✅ / PBT-09(Hypothesis) ✅ / PBT-10(예제 16건 병행) ✅
**Blocking findings: 0건**
