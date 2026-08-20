# Code Generation Plan — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 1 (Planning), Unit 1/3
**Created**: 2026-08-13T06:45:00Z
**Status**: ⛔ 승인 대기 중

> **이 문서는 Code Generation 의 단일 진실 공급원입니다.**
> Part 2(Generation)는 아래 단계를 **순서대로, 쓰여 있는 대로만** 실행합니다. 임의 판단으로 벗어나지 않습니다.

---

## 1. 유닛 컨텍스트

| 항목 | 내용 |
|---|---|
| **유닛** | `u1-trip-backend` |
| **코드 위치** | `c:\Users\403\IDE\trip\backend\` — **`aidlc-docs/` 에는 절대 코드를 두지 않음** |
| **문서 위치** | `aidlc-docs/construction/u1-trip-backend/code/` (마크다운만) |
| **배포 산출물 위치** | `c:\Users\403\IDE\trip\` 루트 (Dockerfile, compose, .env.example, scripts) |
| **프로젝트 유형** | Greenfield 다중 유닛 → `{unit}/src` 패턴 변형 (`backend/app/`) |
| **언어·런타임** | Python 3.12 (컨테이너 고정, UD-9) |
| **의존 유닛** | 없음 (u1 은 최상위) |
| **후속 유닛에 제공하는 계약** | **OpenAPI 스키마** → u2 가 TS 타입 생성 (UD-3) |

### 구현 대상

| 구분 | 수량 | 출처 |
|---|---|---|
| Application Design 컴포넌트 | C1 ~ C33 (33종) | `application-design/components.md` |
| NFR 논리 컴포넌트 | L1 ~ L8 (8종) | `nfr-design/logical-components.md` |
| **컴포넌트 합계** | **41종** | |
| 비즈니스 규칙 | BR-01 ~ BR-60 (60건) | `functional-design/business-rules.md` |
| 검증 속성 (PBT) | P-01 ~ P-22 (22종) | `functional-design/business-logic-model.md` §11 |
| Owner FR | 15건 | `unit-of-work-story-map.md` |
| 설계 결정 | DD(25) + UD(14) + ND(18) + ID(20) | 각 스테이지 산출물 |
| 설정 항목 | 약 47개 | `nfr-design/logical-components.md` §5 |

### 데이터베이스 엔티티 (u1 소유)

`Trip` / `TripDay` / `ItineraryItem` / `Place` / `OpeningHours` / `TravelLeg` / `UnresolvedCandidate` / `PlaceContent` / `GenerationJob` / `ExternalCache` / `ApiUsage` / `AuditEvent` — **12 테이블**

### 서비스 경계

- **제공**: REST API 19개 엔드포인트 (`application-design/component-methods.md` §7)
- **소비**: 네이버 지역검색·블로그·이미지, NCP Directions·Geocoding, Anthropic Claude
- **비책임**: 지도 렌더링, UI 상태, 딥링크 URL 생성(DD-11)

---

## 2. 생성 원칙 (전 단계 공통)

| # | 원칙 | 근거 |
|---|---|---|
| 1 | **`domain/` 은 어떤 것도 import 하지 않는다** (표준 라이브러리 제외) | DD-16, PBT 실행 가능성 |
| 2 | 서비스 코드에 `if mock:` 분기를 만들지 않는다 — 목 선택은 C13 주입 시점에만 | DD-3 |
| 3 | 서비스 코드에 재시도 루프·캐시 조회를 두지 않는다 — C6·C12 소관 | DD-2, DD-15 |
| 4 | 모든 외부 응답(네이버·LLM)을 **검증 후 수용**한다 | BR-07, BR-14, SEC-13 |
| 5 | 사용자 노출 오류 문구는 **6종 고정 문구만** 사용한다 | BR-58, SEC-09 |
| 6 | 인증 정보를 소스·로그·오류 응답에 남기지 않는다 | SEC-12 |
| 7 | SQL 은 **파라미터 바인딩만** — 문자열 연결 금지 | SEC-05 |
| 8 | 의존성은 **정확한 버전으로 고정**한다 | SEC-10 |
| 9 | `async` 컨텍스트에서 **동기 DB 호출을 직접 하지 않는다** — L4 경유 | ND-18 |
| 10 | 테스트는 **네트워크에 의존하지 않는다** | NFR-10, Q22=A |
| 11 | PBT 는 **셰링킹 활성 + 시드 로깅** | PBT-08, PBT-R4 |
| 12 | 각 파일 상단에 담당 컴포넌트 ID(C·L)와 주요 BR 을 주석으로 명시 | 추적성 |

---

## 3. 실행 단계

### 🔹 Step 1. 프로젝트 구조 생성 ✅
- [x] `trip/backend/` 디렉터리 트리 생성 (`app/{core,clients,domain,services,storage,api}`, `tests/{unit,property,fixtures}`)
- [x] 패키지 마커 `__init__.py` 생성
- [x] `pyproject.toml` — 프로젝트 메타, pytest 설정. **Hypothesis 는 pyproject 를 읽지 않으므로 프로파일은 `tests/conftest.py` 에 등록**(정정)
- [x] `requirements.txt` / `requirements-dev.txt` — **정확한 버전 고정** (SEC-10)
- [ ] `trip/data/.gitkeep`, `trip/logs/.gitkeep` — Step 18(배포 산출물)로 이동

### 🔹 Step 2. core 계층 생성 (C1~C5, L5, L6, L8) ✅
- [x] `app/core/enums.py` — **신설**. ApiName / EndpointTier / ErrorCode / AuditEventType (순환 import 방지)
- [x] `app/core/config.py` — C1. 설정 47개, `SecretStr`, `credential_status()`, `BIND_HOST` 경고 (SEP-3, ID-11)
- [x] `app/core/logging_config.py` — C2. JSON 포매터, correlation ID(ContextVar), **민감값 마스킹 필터**, 90일 로테이션 (SEC-03, SEC-14)
- [x] `app/core/errors.py` — C5. 도메인 예외 6종 + Problem Details + **고정 문구 매핑** (BR-58, Q15=A)
- [x] `app/core/security_headers.py` — C3. **CSP §4.1** + nosniff/DENY/Referrer, HSTS 는 HTTPS 시에만 (SEP-1, CA-4)
- [x] `app/core/rate_limit.py` — C4. 3등급, 인메모리 IP 윈도 + 전역 일일 카운터 Protocol 주입 (BR-49, SP-4, ND-8)
- [x] `app/core/access_log.py` — L5. 처리시간·외부호출수·캐시적중 기록, P95 초과 WARN (PP-5)
- [x] `app/core/body_limit.py` — L6. 1MB 상한 (BR-05)
- [x] `app/core/scheduler.py` — L8. 기동 시 1회 + 24시간 주기 정리 (BR-60, LC-2)

### 🔹 Step 3. domain 계층 생성 (C14~C20) — **순수, 의존성 0** ✅
- [x] `app/domain/models.py` — C14. 값 객체 12종 + 열거형 9종 + `to_dict`/`from_dict`, **좌표 국내 범위 검증** (BR-15)
- [x] `app/domain/matrix.py` — C16. `DistanceMatrix`
- [x] `app/domain/estimator.py` — C17. 하버사인, 도보·대중교통·자동차폴백 (BR-24~26), **TRANSIT 은 항상 `is_estimate`** (BR-27)
- [x] `app/domain/optimizer.py` — C18. 최근접이웃 + 2-opt + **`brute_force` 오라클**, 3중 종료 조건 (BR-19~23)
- [x] `app/domain/timeline.py` — C15. 시각 전파, 고정 시각 유지, 경고 산출 (BR-31~35)
- [x] `app/domain/opening_hours.py` — C19. **레코드 있을 때만 판정** (BR-35)
- [x] `app/domain/ics.py` — C20. VEVENT 생성 + 이스케이프 + 75옥텟 접기 + 파싱 (BR-45, BR-46)

### 🔹 Step 4. domain 테스트 (예제 + PBT) ✅
- [x] `tests/conftest.py` — Hypothesis 프로파일 등록 (셰링킹 활성 + `print_blob`, PBT-08)
- [x] `tests/property/generators.py` — 도메인 생성기 7종 (PBT-R3, PBT-07)
- [x] `tests/property/test_timeline_properties.py` — **P-01 ~ P-05**
- [x] `tests/property/test_optimizer_properties.py` — **P-06 ~ P-10** (오라클 비교 포함)
- [x] `tests/property/test_estimator_properties.py` — **P-11 ~ P-16** + 보조 1건
- [x] `tests/property/test_roundtrip_properties.py` — **P-17 ~ P-20**
- [x] `tests/unit/test_domain_examples.py` — 경계 예제 **16건**

### 🔹 Step 5. domain 요약 문서 ✅
- [x] `aidlc-docs/construction/u1-trip-backend/code/domain-summary.md` — 구현 파일·BR 매핑·속성 매핑·**P-03 정정 기록**

### 🔹 Step 6. storage 계층 생성 (C30, C31, L4) ✅
- [x] `app/storage/database.py` — C30. 엔진, **WAL·busy_timeout·synchronous·foreign_keys PRAGMA** (SP-1), 세션 스코프
- [x] `app/storage/db_executor.py` — L4. **전용 스레드 풀 실행** (ND-18)
- [x] `app/storage/models.py` — ORM 매핑 **12 테이블** + 인덱스 5 + 유니크 제약 3
- [x] `app/storage/repositories.py` — C31. Trip / Cache / Job / Quota / **AuditLog(추가 전용)** (SEC-14)
- [x] `app/storage/migrations.py` — 스키마 생성 + `schema_version` (Alembic 미도입)

### 🔹 Step 7. storage 테스트 ✅
- [x] `tests/unit/test_repositories.py` — **11건**. CRUD·하드삭제 연쇄(BR-54)·공유 토큰 조회(BR-37)·캐시 유예(BR-57)·고아 복구(RP-4)·쿼터 영속(SP-4)
- [x] `tests/unit/test_audit_append_only.py` — **3건**. 금지 메서드 부재 + `purge_older_than` 인자 검증 (SEC-14)

### 🔹 Step 8. storage 요약 문서 ✅
- [x] `code/storage-summary.md` — 테이블 12종·연쇄 규칙·구조 검증 지점·조정 2건

### 🔹 Step 9. clients 계층 생성 (C6~C13, L1, L2) ✅
- [x] `app/clients/circuit.py` — L1. API 별 서킷 (RP-2), **4xx·쿼터는 실패로 세지 않음**
- [x] `app/clients/semaphore.py` — L2. **API 별 전역 동시 5** (ND-17)
- [x] `app/clients/base.py` — C6. `httpx.AsyncClient` 단일 인스턴스, TLS 강제, 타임아웃·재시도(4xx 제외)·계측 (BR-47, SEC-01)
- [x] `app/clients/cache_decorator.py` — C12. TTL 래퍼 4종, **키 정규화** (BR-48)
- [x] `app/clients/protocols.py` — C7~C11 Protocol + DTO. **DirectionsClient 에 대중교통·도보 메서드 미정의** (DD-22)
- [x] `app/clients/naver_local.py` — C7. **태그 제거(BR-14) + `to_wgs84()` 단일 좌표 변환 격리**
- [x] `app/clients/naver_content.py` — C8. 블로그·이미지 (BR-41 본문 미크롤링)
- [x] `app/clients/ncp_directions.py` — C9 (자동차만)
- [x] `app/clients/ncp_geocoding.py` — C10
- [x] `app/clients/anthropic_llm.py` — C11. **`claude-sonnet-5`, 구조화 출력 강제** (BR-06). **SDK 대신 BaseHttpClient 직접 호출**(조정 1)
- [x] `app/clients/mocks.py` — 목 구현 5종 (결정적, 그라운딩 통과 가능)
- [x] `app/clients/factory.py` — C13. 인증 정보 판정 → 실제/목 선택 → **캐시는 실구현에만** (DD-6)

### 🔹 Step 10. clients 테스트 ✅
- [x] `tests/unit/test_base_client.py` — **7건**. TLS 거부·4xx 미재시도·4xx 서킷 미계수·5xx 재시도·서킷 개방
- [x] `tests/unit/test_circuit_breaker.py` — **7건**. open/half-open/탐침/API 독립성
- [x] `tests/unit/test_cache_decorator.py` — **4건** + `tests/property/test_cache_key_properties.py` **P-21·P-22**
- [x] `tests/unit/test_factory_mock_mode.py` — **8건**. 구현 선택 + **구조 검증 2건**(목 분기 격리, domain 의존성 0)
- [x] `tests/unit/test_naver_local_parsing.py` — **8건**. 태그 제거 + **좌표계 오류 시 예외 확인**
- [x] `tests/fixtures/external_responses.py` — 응답 샘플 7종 (⚠️ 문서 기반, 실응답 미검증)

### 🔹 Step 11. clients 요약 문서 ✅
- [x] `code/clients-summary.md` — 좌표 변환 격리 · **`clients → domain` 매트릭스 정정** · 조정 2건

### 🔹 Step 12. services 계층 생성 (C21~C29, L3) ✅
- [x] `app/services/trip_service.py` — C21. CRUD, **UUIDv4·공유 토큰 분리**(BR-36), 검증(BR-01~04), 감사, 원자적 교체(BR-53)
- [x] `app/services/llm_draft.py` — C22. 도구 스키마 강제(BR-06), **서버 2차 검증 + 2회 재시도**(BR-07), **5개 필드만 수용**(BR-08)
- [x] `app/services/place_resolver.py` — **C23 🔴 3조건 AND(BR-11), 미해결 분리(BR-12·18), 중복 제거(BR-17)**
- [x] `app/services/travel_matrix.py` — C24. **비인접은 근사·확정 후 인접만 실호출** (BR-28)
- [x] `app/services/generation_service.py` — C25. 6단계 파이프라인 + **행렬 재기준화**(§2 발견 사항)
- [x] `app/services/place_search.py` — C26. 5건 페이징 + 주변 추천 (FR-6, FR-22)
- [x] `app/services/recommendation.py` — C27. **블로그 3건 미만이면 요약 생성 안 함** (BR-40)
- [x] `app/services/job_service.py` — C28. 등록·상태·정리 + `decide_final_state`(BR-13)
- [x] `app/services/job_runner.py` — L3. asyncio 태스크, **동시 3 제한 + 종료 취소** (ND-2, ND-3)
- [x] `app/services/quota_service.py` — C29. **인메모리 계측 + 주기 플러시 + 기동 로드** (CD-1)
- [x] `app/domain/categories.py` — 신규 (조정 1)
- [x] `app/storage/mappers.py` — 신규 (조정 2)

### 🔹 Step 13. services 테스트 ✅
- [x] `tests/unit/test_place_resolver.py` — **16건**. 유사도 경계, 지역·카테고리 불일치, 검색 0건·실패, 중복, **BR-18**
- [x] `tests/unit/test_generation_pipeline.py` — **7건**. `succeeded`/`partial`/`failed` 판정, BR-18, BR-52, position 연속성
- [x] `tests/unit/test_llm_draft.py` — **9건**. 스키마 거부·재시도, **스키마에 사실 필드 부재 + 응답의 금지 필드 미수용**
- [x] `tests/unit/test_travel_matrix.py` — **8건**. **호출 수 정확히 n-1** (n=2·5·10·15), CON-1, 폴백
- [x] `tests/unit/test_recommendation.py` — **8건**. 근거 2건 → 요약 없음 + **LLM 호출도 안 함**
- [x] `tests/unit/test_job_runner.py` — **13건**. 동시 3 제한, 종료 취소, 쿼터·레이트 리밋(SP-4 포함)
- [x] ~~`test_quota_rate_limit.py`~~ — `test_job_runner.py` 에 통합 (동일 관심사)

### 🔹 Step 14. services 요약 문서 ✅
- [x] `code/services-summary.md` — 행렬 재기준화 발견 · CD-1 파생 결정 · 환각 차단 코드 경로

### 🔹 Step 15. api 계층 생성 (C32, C33, L7) ✅
- [x] `app/api/schemas.py` — C33. 스키마 12종, `extra="forbid"`, **길이·범위·좌표 제약**(BR-01~05, BR-15)
- [x] `app/api/deps.py` — **컨테이너·배선 신설** (조정 1)
- [x] `app/api/routers/` — trips / generation / places / share / export / health **6파일, 엔드포인트 19개**. `GET /api/trips` **미제공**(BR-39). `routes` 는 `trips` 에 통합(조정 2)
- [x] `app/api/static.py` — L7. 정적 서빙 + **캐시 헤더**(ND-8) + SPA catch-all
- [x] `app/main.py` — **미들웨어 9단계**(LC-1), 수명주기(고아정리·스케줄러·클라이언트 풀), 전역 오류

### 🔹 Step 16. api 테스트 ✅
- [x] `tests/unit/test_api_trips.py` — **14건**. CRUD, 검증, **목록 엔드포인트 부재(OpenAPI 확인)**, 영업시간
- [x] `tests/unit/test_api_generation.py` — **6건**. 202 즉시 반환, **목 모드 전 파이프라인 동작(QG-7)**, 좌표 범위
- [x] `tests/unit/test_api_share.py` — **7건**. 토큰 독립성, 폐기 즉시 무효, **공유 경로에 쓰기 메서드 부재(OpenAPI 확인)**
- [x] `tests/unit/test_security_headers.py` — **9건**. CSP `script-src` unsafe 불허, HSTS 조건부, CORS 와일드카드 차단
- [x] `tests/unit/test_error_responses.py` — **9건**. 고정 문구 6종, **누출 마커 9종 검사**, 문서 엔드포인트 비활성
- [x] `tests/unit/test_health.py` — **6건**. 쿼터 미소모 확인 + **소스 검사로 외부 클라이언트 미참조 강제**

### 🔹 Step 17. api 요약 문서 ✅
- [x] `code/api-summary.md` — 미들웨어 조립 · API 표면의 규칙 · 조정 3건

### 🔹 Step 18. 배포 산출물 생성 (`trip/` 루트) ✅
- [x] `Dockerfile` — 멀티스테이지. **`DIGEST-PENDING` 주석**(ID-20), `PYTHONDONTWRITEBYTECODE=1` + `compileall`(ID-19), 비루트 10001, **`--workers 1` 하드코딩 + 사유 주석 12줄**(ID-4)
- [x] `docker-compose.yml` — **`${BIND_HOST:-127.0.0.1}:8200:8200`**(ID-11), `read_only` + tmpfs, 리소스 제한, 헬스체크(Python), 로그 드라이버
- [x] `.env.example` — **47개 항목 + 위험 고지 주석**
- [x] `.dockerignore` / `.gitignore` — **`generated.ts` 는 커밋 대상**임을 명시(UD-3)
- [x] `scripts/backup-db.ps1` / `.sh` — `Connection.backup()` + **폴더 복사 금지 경고**(ID-8, ID-9)
- [x] `scripts/audit-deps.ps1` / `.sh` — pip-audit + npm audit (ID-17, SEC-10)
- [x] `scripts/generate-sbom.py` — CycloneDX 1.5, **실행 확인 완료**(구성 요소 6개) (ID-18, SEC-10)
- [x] `android/Dockerfile.build` + `scripts/build-android.ps1` / `.sh` (ID-16, UD-13)
- [x] `data/.gitkeep`, `logs/.gitkeep`

### 🔹 Step 19. 문서 생성 ✅
- [x] `trip/README.md` — 개요, 핵심 동작 3가지, 기동 절차, **`BIND_HOST` 위험 고지**, 백엔드 단독 실행, 안드로이드 연동, 비용 통제, **운영 배포 선행 조건 7건**, 알려진 제약
- [x] `code/code-summary.md` — 파일 114개 집계, **조정 12건**, **설계 문서 정정 3건**, 추적성 검증, **미검증 10건**

---

## 4. 추적성 계획

각 단계 완료 시 다음을 확인합니다.

| 대상 | 검증 방법 |
|---|---|
| Owner FR 15건 | 구현 파일 주석 + `code-summary.md` 매핑표 |
| BR-01 ~ BR-60 | 구현 위치 매핑표 (미구현 0건 목표) |
| P-01 ~ P-22 | PBT 테스트 함수 1:1 대응 |
| SEC 주 책임 13건 | 구현 지점 매핑표 |
| DD·UD·ND·ID | 위반 여부 자체 점검 |

---

## 5. 예상 규모

| 구분 | 예상 파일 수 |
|---|---|
| `app/core/` | 8 |
| `app/domain/` | 7 |
| `app/storage/` | 5 |
| `app/clients/` | 12 |
| `app/services/` | 10 |
| `app/api/` | 10 |
| 패키지 마커 | 7 |
| 테스트 | 22 |
| 픽스처 | 5 |
| 배포·스크립트 | 10 |
| 문서 (aidlc-docs) | 7 |
| **합계** | **약 103개** |

**단계 수**: 19 / **예상 세션**: 2~3

---

## 6. 알려진 미확정 사항 (Code Generation 시점)

생성 시점에 **확정할 수 없는 항목**입니다. 코드에 격리해 두고 Build & Test 에서 해소합니다.

| # | 항목 | 격리 방법 | 해소 시점 |
|---|---|---|---|
| 1 | 지역검색 `mapx`/`mapy` **좌표계** | `to_wgs84()` **단일 함수**에 격리 (Step 9) | Build & Test — 실응답 확인 |
| 2 | 베이스 이미지 **다이제스트** (ID-20) | `# DIGEST-PENDING` 주석 | Build & Test I-2 — **SEC-10 완결 조건** |
| 3 | **CSP 허용 도메인** | 설정 상수로 분리 | Build & Test — SDK 로딩 실측 |
| 4 | 네이버·NCP **실 API 응답 형식** | 픽스처 기반 테스트 + 파싱 계층 분리 | Build & Test (인증 정보 있을 때) |
| 5 | 안드로이드 빌드 성공 여부 | `Dockerfile.build` 제공 | Build & Test I-14 — **CON-6 해소 조건** |

> 이 5건을 **지금 확정된 것처럼 쓰지 않습니다.** 코드 주석과 `code-summary.md` 에 미검증 상태로 명시합니다.

---

## 7. 승인 요청

**본 계획은 19단계, 약 103개 파일, 41개 컴포넌트를 생성합니다.**

Part 2 진행 시:
- 단계를 **순서대로** 실행하고 완료 즉시 `[x]` 로 표시합니다
- 계획에 없는 것을 만들지 않습니다
- 애플리케이션 코드는 `trip/backend/` 와 `trip/` 루트에만, 문서는 `aidlc-docs/` 에만 둡니다
- **테스트는 작성하되 실행은 Build & Test 스테이지**에서 합니다
