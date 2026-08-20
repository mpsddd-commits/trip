# Code Generation 종합 요약 — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 18~19 / 최종)
**Created**: 2026-08-14T00:10:00Z
**계획**: `construction/plans/u1-trip-backend-code-generation-plan.md` — **19단계 전부 완료**

---

## 1. 생성 파일 집계

| 위치 | 파일 수 | 내용 |
|---|---|---|
| `trip/backend/app/` | **63** | core 10 · domain 9 · clients 13 · services 11 · storage 7 · api 11 · 진입점 2 |
| `trip/backend/tests/` | **32** | 예제 테스트 · PBT · 픽스처 · conftest |
| `trip/backend/` (루트) | 3 | `pyproject.toml` · `requirements.txt` · `requirements-dev.txt` |
| `trip/scripts/` | 7 | 백업 2 · 의존성 스캔 2 · SBOM 1 · 안드로이드 빌드 2 |
| `trip/` (루트) | 6 | `Dockerfile` · `docker-compose.yml` · `.env.example` · `.gitignore` · `.dockerignore` · `README.md` |
| `trip/android/` | 1 | `Dockerfile.build` |
| `trip/data/`, `trip/logs/` | 2 | `.gitkeep` |
| **애플리케이션 코드 합계** | **114** | |
| `aidlc-docs/.../code/` | 5 | 계층별 요약 4 + 본 문서 |

**계획 예상 103개 → 실제 114개** (조정으로 추가된 파일과 스크립트 분량 차이)

### 검증
- ✅ **애플리케이션 코드가 `aidlc-docs/` 밖에만 존재** (QG-6)
- ✅ `python -m compileall` **exit 0**
- ✅ `python scripts/generate-sbom.py` **실행 성공** (구성 요소 6개, Node 는 u2 미생성으로 건너뜀)
- ✅ 중복 파일 0건

---

## 2. 컴포넌트 구현 현황

| 계층 | 설계 | 구현 | 상태 |
|---|---|---|---|
| core | C1~C5, L5, L6, L8 | 8 + `enums.py` | ✅ |
| domain | C14~C20 | 7 + `categories.py` | ✅ |
| clients | C6~C13, L1, L2 | 10 + `protocols.py`, `mocks.py` | ✅ |
| services | C21~C29, L3 | 10 | ✅ |
| storage | C30, C31, L4 | 3 + `models.py`, `migrations.py`, `mappers.py` | ✅ |
| api | C32, C33, L7 | 3 + 라우터 6 + `deps.py` | ✅ |
| **합계** | **41종** | **41종 전부 구현** | ✅ |

---

## 3. 설계 대비 조정 (총 12건, 전부 위반 아님)

| # | 단계 | 조정 | 사유 |
|---|---|---|---|
| 1 | Step 1 | Hypothesis 프로파일을 `pyproject.toml` → `tests/conftest.py` | **Hypothesis 는 pyproject 를 읽지 않는다** |
| 2 | Step 2 | `core/enums.py` 신설 | 공통 열거형 집중으로 순환 import 방지 |
| 3 | Step 3 | `EstimatorParams`·`OptimizeLimits` 를 도메인 내 dataclass 로 | **DD-16(의존성 0) 유지 수단** |
| 4 | Step 2 | `RateLimiter` 전역 카운터 Protocol 주입 | ND-8 에 명시된 방식 |
| 5 | Step 6 | `recover_orphans` 대상에 `queued` 포함 | 대기 job 도 프로세스 종료 시 고아 |
| 6 | Step 9 | **`anthropic` SDK 미사용** → `BaseHttpClient` 직접 호출 | SDK 사용 시 서킷·세마포어·쿼터·재시도를 **전부 우회**. 의존성 1개 감소(SEC-10) |
| 7 | Step 9 | 캐시 데코레이터를 클라이언트별 래퍼 4종으로 | Protocol 마다 시그니처가 달라 범용 `__getattr__` 은 타입 안전성이 무너짐 |
| 8 | Step 12 | `domain/categories.py` 신설 | BR-11 ③ 와 BR-52 양쪽에서 사용 |
| 9 | Step 12 | `storage/mappers.py` 신설 | 매핑을 서비스에 두면 C21 비대화, ORM 에 두면 도메인 지식 누출 |
| 10 | Step 15 | `api/deps.py` 컨테이너 신설 | `main.py` 배선 집중 시 라우터가 전역 상태에 의존 |
| 11 | Step 15 | 라우터 7파일 → 6파일 | `routes` 와 `trips` 가 같은 자원을 다뤄 분리 시 로직 중복 |
| 12 | Step 15 | 레이트 리밋을 미들웨어 → **라우터 의존성** | 등급이 엔드포인트마다 다름. 라우트 정의에 붙어야 누락이 드러남 |

---

## 4. 🔴 설계 문서 정정 3건

구현 과정에서 **설계 문서 자체의 오류·누락**을 발견했습니다.

### 정정 1 — P-03 불변식 (Functional Design)
"시각 단조 증가"를 무조건 성립하는 불변식으로 기술했으나 **BR-31·BR-32와 동시에 성립할 수 없습니다.**
고정 시각 도착이 불가능할 때 시각을 밀지 않고 경고만 붙이므로 그 지점에서 역전이 생깁니다.
→ **"`FIXED_TIME_CONFLICT` 경고가 없는 구간에서만 단조 증가"** 로 정밀화.
📄 `domain-summary.md` §2

### 정정 2 — `clients → domain` 의존 (Application Design)
의존성 매트릭스에 "—(없음)"으로 표기했으나 **7개 파일에서 의존이 발생**하며, 이는 바람직합니다.
DTO 가 `Coordinate` 를 쓰면서 **국내 범위 검증(BR-15)이 가장 바깥에서** 걸립니다.
→ `component-dependency.md` §3 에 정정 주석. 순환은 여전히 0건.
📄 `clients-summary.md` §3

### 정정 3 — 최적화 후 행렬 인덱스 재기준화 (Functional Design)
WF-2 의 4→5단계 사이에 **인덱스 재기준화 단계가 빠져 있었습니다.**
순서가 바뀐 뒤 원본 행렬을 그대로 넘기면 **엉뚱한 구간의 이동시간을 읽습니다.**
→ `_reindex()` 추가.
📄 `services-summary.md` §2

---

## 5. 파생 결정 1건 — CD-1 쿼터 계측

`QuotaGate.record()` 는 async 컨텍스트에서 **동기 호출**됩니다. SQLite 직접 쓰기는 ND-18 위반입니다.
→ **인메모리 증가 + 주기 플러시 + 기동 시 로드**. SP-4 목적(재시작 우회 방지)은 로드 경로가 달성합니다.
📄 `services-summary.md` §3

---

## 6. 추적성 검증

### FR (Owner 15건)

| FR | 구현 위치 |
|---|---|
| FR-2 AI 초안 | `services/llm_draft.py` |
| FR-3 그라운딩 | `services/place_resolver.py` 🔴 |
| FR-4 CRUD | `services/trip_service.py`, `api/routers/trips.py` |
| FR-6 검색·페이징 | `services/place_search.py`, `api/routers/places.py` |
| FR-8 순서 최적화 | `domain/optimizer.py` |
| FR-9 타임라인 | `domain/timeline.py` |
| FR-10 이동시간 | `services/travel_matrix.py`, `domain/estimator.py` |
| FR-13 영업시간 경고 | `domain/opening_hours.py`, `api/routers/trips.py` |
| FR-20·21 추천 | `services/recommendation.py` |
| FR-22 주변 추천 | `services/place_search.py` |
| FR-25 공유 | `services/trip_service.py`, `api/routers/share.py` |
| FR-26 `.ics` | `domain/ics.py`, `api/routers/export.py` |
| FR-33 목 모드 | `clients/factory.py`, `clients/mocks.py` |
| FR-34 헬스·쿼터 | `api/routers/health.py`, `services/quota_service.py` |

**미매핑 0건** ✅

### BR-01 ~ BR-60
**전건 구현 위치 확정.** 계층별 요약 문서에 매핑 기록.
**미구현 0건** ✅

### P-01 ~ P-22 (PBT)
**전건 테스트 함수 작성.** `tests/property/` 5파일.
**미작성 0건** ✅

### SEC 주 책임 13건
전건 구현 지점 확정 — 상세는 §8.

---

## 7. 테스트 현황 (작성 완료, 실행은 Build & Test)

| 파일군 | 건수 |
|---|---|
| domain 예제 | 16 |
| PBT (P-01~P-22) | 22종 + 보조 5 |
| storage | 14 |
| clients | 34 |
| services | 67 |
| api | 48 |
| **합계** | **약 206건** |

### 설계 규칙 자체를 검사하는 구조 테스트 8건

동작이 아니라 **규칙이 코드에 남아 있는지**를 봅니다. 나중에 누가 규칙을 무너뜨리면 즉시 실패합니다.

| 테스트 | 지키는 규칙 |
|---|---|
| `test_no_list_all_method_exists` | BR-39 — 리포지토리에 목록 메서드 부재 |
| `test_no_trip_list_endpoint` | BR-39 — **OpenAPI 스키마**에 목록 경로 부재 |
| `test_repository_exposes_no_mutation_methods` | SEC-14 — 감사 로그 추가 전용 |
| `test_purge_only_accepts_a_retention_cutoff` | SEC-14 — 개별 이벤트 삭제 경로 부재 |
| `test_no_mock_branching_outside_the_factory` | DD-3 — 목 분기가 서비스·도메인에 없음 |
| `test_domain_layer_has_no_app_imports` | DD-16 — domain 의존성 0 |
| `test_no_write_endpoints_under_shared_path` | BR-37 — **OpenAPI 스키마**의 공유 경로가 GET 전용 |
| `test_health_module_does_not_touch_external_clients` | ND-14 — 헬스체크가 외부 API 미호출 |

---

## 8. Security Compliance — Code Generation 전체

| Rule | 판정 | 구현 지점 |
|---|---|---|
| SEC-01 | ✅ | `clients/base.py` — `https://` 아닌 URL 호출 전 거부 |
| SEC-02 | ⚪ N/A | 중간자 없음 |
| SEC-03 | ✅ | `core/logging_config.py` — 마스킹 필터 4종, 90일 로테이션 |
| SEC-04 | ✅ | `core/security_headers.py` — CSP + 3종. `script-src` unsafe 불허 검증 |
| SEC-05 | ✅ | `api/schemas.py`(`extra="forbid"`) + `domain/models.py`(좌표) + ORM 바인딩 |
| SEC-06 | ⚪ N/A | IAM 없음 |
| SEC-07 | ✅ | `core/config.py` 경고 + `docker-compose.yml` 포트 매핑 |
| SEC-08 | ✅ | UUIDv4 · `secrets.token_urlsafe(32)` · 읽기 전용 타입 · 목록 API 부재 · CORS 화이트리스트 |
| SEC-09 | ✅ | 고정 문구 6종 · `docs_url=None` · 비루트 · 읽기 전용 FS |
| SEC-10 | ⚠️ **부분** | 버전 고정 ✅ · 스캔 스크립트 ✅ · SBOM ✅ · **다이제스트 미결(ID-20)** |
| SEC-11 | ✅ | 서킷 · 세마포어 · 3등급 레이트 리밋 · 규모 상한 |
| SEC-12 | ✅ | `SecretStr` · `__repr__` 재정의 · `.env` gitignore · 하드코딩 0건 |
| SEC-13 | ✅ | LLM 응답 스키마 2차 검증 · 감사 로깅 |
| SEC-14 | ✅ | 추가 전용 감사 · 90일 · 보안 이벤트 로깅 |
| SEC-15 | ✅ | 전역 오류 미들웨어(최외곽) · fail-closed · 세션 정리 |

**Blocking security findings: 0건** ✅
**⚠️ SEC-10 은 부분 충족** — Build & Test I-2 에서 다이제스트를 채우지 못하면 **blocking 으로 승격**됩니다.

## PBT Compliance

| Rule | 판정 |
|---|---|
| PBT-01 | ✅ Testable Properties 문서화 |
| PBT-02 | ✅ P-17~P-20 (도메인·ICS 왕복) |
| PBT-03 | ✅ P-01~P-16 (타임라인·최적화·거리) |
| PBT-04 | ⚪ N/A — `optimize()` 는 멱등성 미주장 (근거 명시) |
| PBT-05 | ✅ P-09 완전탐색 오라클 |
| PBT-06 | ⚪ N/A — job 상태 전이 선형 |
| PBT-07 | ✅ 도메인 생성기 7종 |
| PBT-08 | ✅ `conftest.py` — 셰링킹 활성 + `print_blob` |
| PBT-09 | ✅ Hypothesis |
| PBT-10 | ✅ 예제 기반 병행 (C23·C22 는 PBT 비대상 명시) |

**Blocking PBT findings: 0건** ✅

---

## 9. ⚠️ 미검증 항목 (Build & Test 대기)

**이 항목들을 검증된 것처럼 기술하지 않았습니다.**

| # | 항목 | 격리 위치 | 해소 |
|---|---|---|---|
| 1 | **테스트 실행 결과 (약 206건)** | — | Build & Test |
| 2 | **지역검색 좌표계** | `naver_local.py::to_wgs84()` **단일 함수** | Build & Test — 실응답 |
| 3 | **베이스 이미지 다이제스트** | `Dockerfile` `# DIGEST-PENDING` | Build & Test I-2 — **SEC-10 완결 조건** |
| 4 | **CSP 허용 도메인** | `security_headers.py::CSP_DIRECTIVES` 상수 | Build & Test — SDK 로딩 실측 |
| 5 | **NCP 엔드포인트·헤더 이름** | `ncp_directions.py` 상수 | Build & Test — 실호출 |
| 6 | 실 API 응답 형식 | 픽스처 + 파싱 계층 분리 | Build & Test (키 보유 시) |
| 7 | 의존성 버전 설치 가능 여부 | `requirements.txt` | Build & Test — `pip install` |
| 8 | 미들웨어 실행 순서 실동작 | `main.py` | Build & Test |
| 9 | 유사도 0.60 임계값 적정성 | `.env` 조정 가능 | Build & Test |
| 10 | **이미지 빌드** | — | ⚠️ `web/` 부재로 **u2 생성 후에만 가능** |

### 🔴 특히 중요한 제약

**`docker compose build` 는 지금 실패합니다.** `Dockerfile` stage 1 이 `web/` 을 요구하기 때문입니다.
이는 설계대로이며(UD-8 단일 컨테이너), u2 생성 후 해소됩니다.
현재 u1 을 확인하려면 `README.md` 의 "백엔드 단독 실행" 절차를 쓰세요.

---

## 10. 다음 단계

`u2-trip-web` Functional Design → Code Generation → `u3-trip-android` → **Build and Test**

Build & Test 에서 해소할 검증 항목: 위 §9 의 10건 + NFR Design 예약 6건 + Infrastructure Design I-1~I-14
