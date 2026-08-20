# Clients 계층 구현 요약 — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 11)
**Created**: 2026-08-13T07:50:00Z
**대상 단계**: Step 9(생성) · Step 10(테스트)

---

## 1. 생성 파일 (17개, 누적 63개)

| 파일 | 컴포넌트 | 핵심 구현 |
|---|---|---|
| `clients/circuit.py` | **L1** | API 별 독립 서킷. closed → open(60s) → half-open(탐침 1회) |
| `clients/semaphore.py` | **L2** | API 별 전역 동시 5 (ND-17) |
| `clients/base.py` | **C6** | TLS 강제 + 서킷 + 세마포어 + 타임아웃 + 지수 백오프 + 쿼터 계측 |
| `clients/protocols.py` | C7~C11 | Protocol 5종 + 전송 DTO 5종 + `ClientBundle` |
| `clients/cache_decorator.py` | **C12** | 키 정규화(BR-48) + 클라이언트별 캐시 래퍼 4종 |
| `clients/naver_local.py` | **C7** | 지역검색 + **`to_wgs84()` 좌표 변환 격리** + 태그 제거 |
| `clients/naver_content.py` | **C8** | 블로그·이미지 검색 |
| `clients/ncp_directions.py` | **C9** | 자동차 경로 전용 |
| `clients/ncp_geocoding.py` | **C10** | 주소 ↔ 좌표 |
| `clients/anthropic_llm.py` | **C11** | Claude Messages API 직접 호출 + 구조화 출력 강제 |
| `clients/mocks.py` | — | 목 구현 5종 (결정적) |
| `clients/factory.py` | **C13** | 인증 정보 판정 → 구현 선택 → 데코레이터 합성 |
| `tests/fixtures/external_responses.py` | — | 응답 샘플 7종 |
| `tests/unit/test_base_client.py` | — | 7건 |
| `tests/unit/test_circuit_breaker.py` | — | 7건 |
| `tests/unit/test_cache_decorator.py` | — | 4건 |
| `tests/unit/test_factory_mock_mode.py` | — | 8건 (구조 검증 2건 포함) |
| `tests/unit/test_naver_local_parsing.py` | — | 8건 |
| `tests/property/test_cache_key_properties.py` | — | **P-21, P-22** + 3건 |

---

## 2. 🔴 좌표계 미확정 사항의 격리 (계획 §6-1)

지역검색 `mapx`/`mapy` 의 좌표계는 **아직 확정할 수 없습니다.** 변환을 **단 하나의 함수**에 가뒀습니다.

```
app/clients/naver_local.py::to_wgs84(mapx, mapy) -> Coordinate
```

**현재 가정**: `mapx`=경도, `mapy`=위도. 값이 정수 배율 표현이면 `1e7` 로 나눈다.

**가정이 틀렸을 때의 동작 — 조용히 실패하지 않습니다.**
1. 변환 결과가 국내 범위(33~39 / 124~132)를 벗어나면 `CoordinateConversionError`
2. `_parse` 는 해당 항목만 건너뛰고 경고 로그를 남긴다 (NFR-3 — 검색 전체는 실패하지 않음)
3. `Coordinate.__post_init__` 가 2차 방어 (BR-15)

`test_wrong_coordinate_system_raises_instead_of_silently_saving` 가 KATECH 계열 값(311111, 552222)을 넣어 **예외가 나는지** 확인합니다.

→ Build & Test 에서 실응답 확인 후 **이 함수 한 곳만** 수정하면 됩니다.

---

## 3. 🔴 설계 문서 정정 1건 — `clients → domain` 의존

`component-dependency.md` 의 매트릭스는 `clients → domain` 을 **"—"(의존 없음)** 으로 표기했으나, 구현 결과 **7개 파일에서 의존이 발생**했고 이는 **바람직한 방향**입니다.

| 사유 | 내용 |
|---|---|
| DTO 의 좌표 타입 | `SearchedPlace`·`CarRoute` 가 `domain.models.Coordinate` 를 쓴다. 여기서 **국내 범위 검증(BR-15)이 가장 바깥에서 걸린다** |
| 근사 로직 재사용 | `MockDirectionsClient` 가 `domain.estimator` 를 재사용해 중복 구현을 피한다 |

**핵심 규칙은 그대로입니다**: `domain` 은 여전히 아무것도 참조하지 않습니다. 방향은 단방향(L2 내부)이고 **순환 0건**입니다.
→ `component-dependency.md` §3 에 정정 주석을 달았고, `test_domain_layer_has_no_app_imports` 가 역방향을 강제합니다.

---

## 4. 설계 조정 2건

| # | 조정 | 사유 | 위반 여부 |
|---|---|---|---|
| 1 | **`anthropic` SDK 미사용** — Messages API 를 `BaseHttpClient` 로 직접 호출 | ① SDK 를 쓰면 서킷(L1)·세마포어(L2)·쿼터 계측(C29)·재시도(BR-47)를 **전부 우회**한다 ② 의존성 1개 감소 = 공급망 표면 축소 (SEC-10) | ❌ 아님 — RP-1 4겹 방어 유지 수단 |
| 2 | `CachingClientDecorator` 를 **클라이언트별 래퍼 4종**으로 구현 | Protocol 마다 메서드 시그니처가 달라 범용 `__getattr__` 데코레이터는 타입 안전성이 무너진다. 인터페이스 동일성(DD-15)은 유지됨 | ❌ 아님 |

---

## 5. 구조로 강제한 규칙

| 규칙 | 강제 수단 |
|---|---|
| **DD-3** 목 분기는 C13 에만 | `test_no_mock_branching_outside_the_factory` — `services/`·`domain/` 소스에서 `if is_mock` / 목 클래스 import / `Mock*Client` 참조를 정규식으로 검사 |
| **DD-16** domain 의존성 0 | `test_domain_layer_has_no_app_imports` — `from app.(?!domain)` 패턴 검사 |
| **DD-6** 목은 캐시로 감싸지 않음 | `test_mock_client_is_not_wrapped_with_cache` |
| **DD-22** Directions 에 대중교통 메서드 없음 | `protocols.py` 에 메서드 미정의 |
| **BR-47** 4xx 미재시도 | `test_4xx_is_not_retried` — 호출 횟수 1회 확인 |
| **RP-2** 4xx 는 서킷 실패 아님 | `test_4xx_does_not_open_circuit` — 5회 4xx 후에도 CLOSED |

---

## 6. 목 모드가 파이프라인 전체를 살리는 방식 (FR-33, QG-7)

`MockLocalSearchClient` 는 질의 `"{목적지} {장소명}"` 에서 **장소명을 그대로 결과 이름으로 반환**합니다.
그래야 그라운딩(C23)의 유사도 판정(BR-11)을 통과해 **목 모드에서도 일정이 생성**됩니다.

`MockLlmClient` 는 C22 의 스키마 검증(BR-07)을 통과하도록 형식을 정확히 지킨 초안을 만듭니다.

→ 인증 정보가 하나도 없어도 `생성 → 그라운딩 → 경로 → 최적화 → 타임라인 → 저장` 전 과정이 동작합니다.

---

## 7. 미검증 항목 (Build & Test 대기)

| # | 항목 | 영향 |
|---|---|---|
| 1 | **지역검색 좌표계** | 틀리면 지도상 전 지점 어긋남 → `to_wgs84()` 만 수정 |
| 2 | **NCP 엔드포인트·헤더 이름** | 도메인 변경 이력 있음. `ncp_directions.py` 상수로 분리됨 |
| 3 | 네이버·NCP·Anthropic 실응답 형식 | 픽스처는 **문서 기반 예시**이며 실응답 미검증 |
| 4 | 테스트 실행 결과 (34건) | Build & Test |

---

## 8. Compliance — Step 9~11

**Security**
- SEC-01 ✅ `https://` 아닌 URL 은 호출 전 거부 (`test_non_tls_url_is_rejected`)
- SEC-03 ✅ 로그에 키 값 미기록. 목 모드 경고는 **어떤 API 인지만** 표기
- SEC-05 ✅ 태그·엔티티 제거 후 저장 (BR-14)
- SEC-10 ✅ 의존성 1개 감소 (`anthropic` SDK 제거)
- SEC-11 ✅ 서킷·세마포어로 외부 부하 억제
- SEC-13 ✅ 구조화 출력 없으면 **수용 거부** (`_parse` 에서 예외)
- SEC-15 ✅ 모든 외부 호출에 명시적 예외 처리 + 폴백 지점 제공
**Blocking findings: 0건**

**PBT**: P-21·P-22 구현 완료 (`test_cache_key_properties.py`). **Blocking findings: 0건**
