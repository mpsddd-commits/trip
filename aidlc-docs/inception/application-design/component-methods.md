# Component Methods — trip

**Stage**: 🔵 INCEPTION - Application Design
**Created**: 2026-08-13T04:35:00Z

> **범위 주의**: 메서드 **시그니처 · 목적 · 입출력 타입**까지만 정의합니다.
> 상세 비즈니스 규칙(판정 임계값, 목적함수 가중치, 캐시 무효화 조건, 예외 분류)은 **Functional Design(유닛별, CONSTRUCTION)** 으로 이월합니다.
> 타입은 언어 문법이 아니라 **계약 표기**입니다. 실제 시그니처는 Code Generation 에서 확정합니다.

---

## 1. 공통 타입 어휘

| 타입 | 의미 |
|---|---|
| `TripId`, `ItemId`, `PlaceId`, `JobId` | UUIDv4 식별자 (SEC-08) |
| `ShareToken` | 읽기 전용 공유 토큰 — `TripId` 와 별개 (CA-3) |
| `Coordinate` | `{lat: float, lng: float}` — 위도 33~39 / 경도 124~132 (국내, Q2=A) |
| `TravelMode` | `WALK` \| `CAR` \| `TRANSIT` |
| `ItineraryItem` | `{id, place, arrival, departure, stay_minutes, memo, time_fixed: bool}` |
| `TravelLeg` | `{from_index, to_index, mode, duration_sec, distance_m, path: list[Coordinate]?, is_estimate: bool}` |
| `Place` | `{id, name, road_address, category, phone?, coordinate, opening_hours?, source}` |
| `PlaceCandidate` | `{raw_name, category_hint, suggested_stay_minutes, reason}` — **좌표 없음** (C22 출력) |
| `ProblemDetails` | RFC 9457 `{type, title, status, detail, instance, code, correlation_id}` (Q6=A) |
| `Result<T>` | 성공값 또는 도메인 예외 — 부분 실패를 표현 |

---

## 2. `core/`

### C1 `Config`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `load` | `() -> Config` | 환경변수 로딩·검증. 부팅 시 1회 |
| `credential_status` | `() -> dict[ApiName, bool]` | API 별 인증 정보 존재 여부. **C13 이 실제/목 선택에 사용** (FR-33) |
| `is_loopback_only` | `() -> bool` | `BIND_HOST` 가 루프백인지. `0.0.0.0` 이면 경고 로그 (NFR-14) |

### C2 `LoggingSetup`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `configure_logging` | `(config: Config) -> None` | JSON 포매터·마스킹 필터·90일 로테이션 구성 (SEC-03, SEC-14) |
| `get_logger` | `(name: str) -> Logger` | 컴포넌트별 로거 |
| `correlation_middleware` | `(request, call_next) -> Response` | 요청당 correlation ID 생성·전파 |
| `mask_sensitive` | `(record: LogRecord) -> LogRecord` | 키·토큰·좌표 원문 마스킹 |

### C3 `SecurityHeaders`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `apply` | `(request, call_next) -> Response` | CSP·nosniff·DENY·Referrer-Policy 상시 부여. **HSTS 는 HTTPS 요청에만** (SEC-04, CA-4) |

### C4 `RateLimiter`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `check` | `(key: str, tier: EndpointTier) -> None \| RateLimitExceeded` | 등급별 슬라이딩 윈도 판정 (SEC-11) |
| `as_dependency` | `(tier: EndpointTier) -> Dependency` | 라우터에 부착할 의존성 생성 |

### C5 `ErrorHandler`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `handle_domain_error` | `(exc: DomainError) -> ProblemDetails` | 도메인 예외 → 상태 코드·일반화 메시지 매핑 |
| `handle_unexpected` | `(exc: Exception) -> ProblemDetails` | 미처리 예외 포착. **내부 상세는 로그에만** (SEC-09, SEC-15) |

---

## 3. `clients/`

### C6 `BaseHttpClient`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `request` | `(method, url, *, params, json, timeout_profile) -> Response` | 타임아웃·재시도·TLS 강제·계측 (NFR-2, NFR-3, SEC-01) |
| `_should_retry` | `(response \| exception, attempt: int) -> bool` | **4xx 는 재시도하지 않음** |

### C7 `LocalSearchClient` *(Protocol)*
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `search` | `(query: str, *, start: int = 1, display: int = 5) -> list[Place]` | 지역검색. **display 최대 5 제약** (CON-2) |
| `search_nearby` | `(center: Coordinate, radius_m: int, category: str?) -> list[Place]` | 주변 후보 (FR-22) |

구현체: `NaverLocalSearchClient`, `MockLocalSearchClient`

### C8 `ContentSearchClient` *(Protocol)*
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `search_blogs` | `(query: str, limit: int) -> list[BlogPost]` | 리뷰 근거 확보 (FR-20) |
| `search_images` | `(query: str, limit: int) -> list[ImageRef]` | 썸네일 + 출처 (FR-21) |

### C9 `DirectionsClient` *(Protocol)*
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `route_car` | `(origin: Coordinate, destination: Coordinate, waypoints: list[Coordinate]?) -> CarRoute` | **자동차 경로 전용** (CON-1) |

> 대중교통·도보 메서드는 **의도적으로 정의하지 않습니다.** 네이버가 제공하지 않는 기능을 인터페이스에 두면 호출자가 존재한다고 오해합니다.

### C10 `GeocodingClient` *(Protocol)*
| 메서드 | 시그니처 |
|---|---|
| `geocode` | `(address: str) -> Coordinate \| None` |
| `reverse_geocode` | `(coordinate: Coordinate) -> str \| None` |

### C11 `LlmClient` *(Protocol)*
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `complete` | `(system: str, user: str, *, max_tokens: int) -> LlmResponse` | 전송만 담당. **프롬프트 구성·응답 검증은 C22 의 책임** |

### C12 `CachingClientDecorator`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `wrap` | `(client: T, *, ttl: timedelta, namespace: str) -> T` | 동일 인터페이스 유지 데코레이터 (Q11=A) |
| `_cache_key` | `(namespace, method, args) -> str` | 정규화 파라미터 해시 |
| `purge_expired` | `() -> int` | 만료 항목 정리 |

### C13 `ClientFactory`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `build_all` | `(config: Config) -> ClientBundle` | 인증 정보 유무에 따라 실제/목 선택 + 캐시 데코레이터 합성 (Q3=A) |
| `active_modes` | `() -> dict[ApiName, "real" \| "mock"]` | `/health` 및 프론트 배너용 (FR-33) |

---

## 4. `domain/` — 순수 함수 (I/O 없음)

### C14 `DomainModels`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `Coordinate.validate` | `(lat, lng) -> Coordinate` | 국내 범위 검증 |
| `ItineraryItem.with_times` | `(arrival, departure) -> ItineraryItem` | 불변 갱신 |
| `to_dict` / `from_dict` | `(...) -> dict` / `(dict) -> T` | **PBT-R1 왕복 대상** |

### C15 `TimelineCalculator`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `compute` | `(items: list[ItineraryItem], legs: DistanceMatrix, day_start: time, fixed: set[ItemId]) -> list[ItineraryItem]` | 시각 전파 (FR-9) |
| `total_duration` | `(items) -> timedelta` | 하루 총 소요 |

**PBT 속성 (PBT-R2)**: 시각 단조 증가 / 고정 항목 시각 불변 / 항목 개수·구성 보존 / 체류·이동시간 비음수

### C16 `DistanceMatrix`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `get` | `(from_idx: int, to_idx: int, mode: TravelMode) -> TravelLeg` | 구간 조회. **API 호출 없음** |
| `from_legs` | `(legs: list[TravelLeg]) -> DistanceMatrix` | C24 가 조립해 전달 |
| `total` | `(order: list[int], mode) -> int` | 주어진 순서의 총 이동시간(초) |

### C17 `TravelTimeEstimator`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `haversine_m` | `(a: Coordinate, b: Coordinate) -> float` | 두 좌표 거리 |
| `estimate_walk` | `(a, b, *, detour: float = 1.3, speed_kmh: float = 4.5) -> TravelLeg` | 도보 근사 (FR-10) |
| `estimate_transit` | `(a, b) -> TravelLeg` | 대중교통 근사. **`is_estimate=True` 필수 부착** (CON-1) |
| `estimate_car_fallback` | `(a, b) -> TravelLeg` | Directions 실패 시 폴백 (NFR-3) |

**PBT 속성**: 거리·시간 비음수 / 동일 지점 = 0 / 거리 단조성 / 대칭성

### C18 `RouteOptimizer`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `optimize` | `(items: list[ItineraryItem], matrix: DistanceMatrix, mode: TravelMode, constraints: OptimizeConstraints) -> list[ItineraryItem]` | 순서 최적화 (FR-8) |
| `_nearest_neighbor` | `(matrix, start_idx, allowed) -> list[int]` | 초기해 |
| `_two_opt` | `(order, matrix) -> list[int]` | 개선 |
| `brute_force` | `(items, matrix) -> list[ItineraryItem]` | **n≤8 전용 참조 구현 — PBT-R7 오라클** |

`OptimizeConstraints` = `{anchor_start: ItemId?, anchor_end: ItemId?, fixed_positions: set[ItemId]}`

**PBT 속성 (PBT-R2, PBT-R7)**: 집합 보존 / 앵커·고정 항목 위치 불변 / `total(결과) <= total(입력)` / n≤8 에서 `brute_force` 와 일치

### C19 `OpeningHoursChecker`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `check` | `(place: Place, arrival: datetime) -> Warning \| None` | 영업시간 밖 판정. **정보 없으면 `None`** (거짓 경고 방지, FR-13) |

### C20 `IcsBuilder`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `build` | `(trip: Trip) -> str` | VEVENT 생성, `Asia/Seoul` 고정 (FR-26) |
| `parse` | `(ics: str) -> Trip` | **PBT-R1 왕복 검증용** |

---

## 5. `services/`

### C21 `TripService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `create` | `(spec: TripSpec) -> Trip` | UUIDv4 발급 (FR-4, SEC-08) |
| `get` | `(trip_id: TripId) -> Trip` | 조회 |
| `get_by_share_token` | `(token: ShareToken) -> ReadOnlyTrip` | **읽기 전용 반환 타입** (FR-25, CA-3) |
| `update_meta` / `delete` | `(trip_id, ...) -> ...` | 이름 변경·삭제 |
| `add_item` / `remove_item` | `(trip_id, day_index, ...) -> Trip` | 항목 편집 (FR-5) |
| `reorder_items` | `(trip_id, day_index, order: list[ItemId]) -> Trip` | 드래그 결과 반영 |
| `move_item_to_day` | `(trip_id, item_id, target_day: int) -> Trip` | 일자 간 이동 |
| `update_item` | `(trip_id, item_id, patch: ItemPatch) -> Trip` | 시각·체류·메모·이동수단 (FR-7, FR-11) |
| `issue_share_token` / `revoke_share_token` | `(trip_id) -> ShareToken` / `(trip_id) -> None` | 공유 토큰 수명 (FR-25) |

### C22 `LlmDraftGenerator`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `generate_draft` | `(spec: TripSpec) -> list[list[PlaceCandidate]]` | 일자별 후보. **좌표 없음** (FR-2) |
| `_build_prompt` | `(spec) -> tuple[str, str]` | 시스템·사용자 프롬프트 |
| `_validate_response` | `(raw: str) -> list[list[PlaceCandidate]]` | **엄격 스키마 검증, 불일치 시 거부** (SEC-13) |
| `summarize_place` | `(place: Place, blogs: list[BlogPost]) -> PlaceContent` | 추천 요약 (FR-20). **근거 링크 필수 포함** |

### C23 `PlaceResolver` 🔴
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `resolve_many` | `(candidates: list[PlaceCandidate], region: str) -> ResolveResult` | 그라운딩 일괄 수행 (FR-3) |
| `_resolve_one` | `(candidate, region) -> Place \| Unresolved` | 단건 해석 |
| `_is_match` | `(candidate, place) -> bool` | **일치 판정 — 기준은 Functional Design 이월 (최우선 항목)** |
| `_dedupe` | `(places) -> list[Place]` | 중복 병합 |

`ResolveResult` = `{resolved: list[Place], unresolved: list[PlaceCandidate]}` — **미해결 항목은 일정에 넣지 않고 사용자에게 노출** (FR-3)

### C24 `TravelMatrixService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `build_matrix` | `(places: list[Place], mode: TravelMode) -> DistanceMatrix` | 수단별 소스 선택 후 조립 (FR-10) |
| `_leg_for` | `(a, b, mode) -> TravelLeg` | 자동차=C9 / 도보·대중교통=C17. 실패 시 근사 폴백 |
| `recompute_leg` | `(trip_id, item_id, mode) -> TravelLeg` | 단일 구간 재계산 (FR-11) |

### C25 `ItineraryGenerationService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `start` | `(trip_id: TripId, spec: TripSpec) -> JobId` | job 등록 후 즉시 반환 (Q5=A) |
| `_run_pipeline` | `(job_id, trip_id, spec) -> None` | C22 → C23 → C24 → C18 → C15 → C21 순차 실행 |
| `_report_step` | `(job_id, step: GenerationStep, progress: float) -> None` | 단계 전이 기록 |

`GenerationStep` = `DRAFTING` \| `RESOLVING` \| `ROUTING` \| `OPTIMIZING` \| `SCHEDULING` \| `SAVING`

### C26 `PlaceSearchService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `search` | `(query: str, page: int) -> PagedPlaces` | 5건 제약 페이징 (FR-6, CON-2) |
| `nearby_suggestions` | `(trip_id, day_index, radius_m) -> list[Place]` | **이미 포함된 장소 제외** (FR-22) |

### C27 `RecommendationService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `content_for` | `(place: Place) -> PlaceContent` | 메뉴/관람 포인트 + 근거 링크 + 사진 (FR-20, FR-21) |
| `content_for_many` | `(places) -> dict[PlaceId, PlaceContent]` | 일괄 조회 |

`PlaceContent` = `{highlights: list[str], sources: list[BlogRef], images: list[ImageRef], is_ai_summary: True}` — **`sources` 가 비면 요약을 노출하지 않습니다** (CON-7)

### C28 `JobService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `enqueue` | `(kind: JobKind, payload: dict) -> JobId` | 등록 |
| `get_status` | `(job_id) -> JobStatus` | 프론트 폴링 대상 (Q5=A) |
| `update` | `(job_id, *, step, progress, result?, error?) -> None` | 진행 기록 |
| `purge_completed` | `(older_than: timedelta) -> int` | 정리 |

`JobStatus` = `{state, step?, progress, result?, problem?: ProblemDetails}` — state ∈ `queued` \| `running` \| `succeeded` \| `failed` \| `partial`

### C29 `QuotaService`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| `record` | `(api: ApiName, count: int = 1) -> None` | C6 이 호출 |
| `usage_today` | `() -> dict[ApiName, QuotaUsage]` | `/health` 노출 (FR-34) |
| `is_exhausted` | `(api: ApiName) -> bool` | 상한 도달 판정 (NFR-4) |

---

## 6. `storage/`

### C30 `Database`
| 메서드 | 시그니처 |
|---|---|
| `create_engine` | `(config) -> Engine` |
| `session_scope` | `() -> ContextManager[Session]` — try/finally 정리 (SEC-15) |
| `run_migrations` | `() -> None` |

### C31 `Repositories`
| 리포지토리 | 주요 메서드 |
|---|---|
| `TripRepository` | `save(trip)` / `find(trip_id)` / `find_by_share_token(token)` / `delete(trip_id)` |
| `CacheRepository` | `get(key)` / `put(key, value, ttl)` / `purge_expired()` |
| `JobRepository` | `insert(job)` / `update(job_id, patch)` / `find(job_id)` / `delete_older_than(ts)` |
| `QuotaRepository` | `increment(api, date, n)` / `get(api, date)` |
| `AuditLogRepository` | `append(event)` — **추가 전용. 수정·삭제 메서드를 정의하지 않음** (SEC-14) |

---

## 7. `api/`

### C32 `ApiRouters` — 엔드포인트 계약

> 🔴 **2026-08-14 정정 (u2 Code Generation 실기동 검증)**
> 아래 표는 설계 시점의 **19개**를 기술했으나, 실제 구현은 **22개 오퍼레이션**입니다.
> | 구분 | 내용 |
> |---|---|
> | 추가 3 | `GET /api/health/ready`(ND-14 readiness) · `PUT /api/trips/{id}/items/{id}/opening-hours`(FR-13 사용자 입력) · `GET /api/config`(개정 A-1) |
> | 변경 1 | `GET /api/places/{place_id}/content` → **`GET /api/places/content?trip_id=&item_id=`** (장소가 여행 항목에 종속되므로 항목 기준 조회가 정확) |
>
> **개정 A-2**: 최초 구현은 라우터가 `-> dict` 를 반환해 OpenAPI 가 22개 중 **17개 응답을 무타입(`object`)** 으로
> 생성했습니다. 이는 UD-3/DD-10 의 목적(계약 불일치를 컴파일 오류로 검출)을 무력화하므로,
> 응답 모델 **17종**을 정의하고 `response_model` 을 부여했습니다.
> → 실측 결과 **타입 있는 응답 19 / 무타입 0** (나머지 3개는 `204` 또는 `text/calendar` 로 JSON 본문 없음).

| 메서드 · 경로 | 요청 | 응답 | FR |
|---|---|---|---|
| `POST /api/trips` | `TripSpec` | `Trip` | FR-1, FR-4 |
| `GET /api/trips/{trip_id}` | — | `Trip` | FR-4 |
| `PATCH /api/trips/{trip_id}` | `TripMetaPatch` | `Trip` | FR-4 |
| `DELETE /api/trips/{trip_id}` | — | `204` | FR-4 |
| `POST /api/trips/{trip_id}/items` | `ItemCreate` | `Trip` | FR-5 |
| `DELETE /api/trips/{trip_id}/items/{item_id}` | — | `Trip` | FR-5 |
| `PATCH /api/trips/{trip_id}/items/{item_id}` | `ItemPatch` | `Trip` | FR-7, FR-11 |
| `PUT /api/trips/{trip_id}/days/{day}/order` | `list[ItemId]` | `Trip` | FR-5 |
| `POST /api/trips/{trip_id}/days/{day}/optimize` | `OptimizeConstraints` | `Trip` | FR-8 |
| `POST /api/trips/{trip_id}/generate` | `TripSpec` | `{job_id}` **202** | FR-2, Q5=A |
| `GET /api/jobs/{job_id}` | — | `JobStatus` | FR-2 |
| `GET /api/places/search` | `?q&page` | `PagedPlaces` | FR-6 |
| `GET /api/places/{place_id}/content` | — | `PlaceContent` | FR-20, FR-21 |
| `GET /api/trips/{trip_id}/days/{day}/suggestions` | `?radius` | `list[Place]` | FR-22 |
| `POST /api/trips/{trip_id}/share` | — | `{share_token, url}` | FR-25 |
| `DELETE /api/trips/{trip_id}/share` | — | `204` | FR-25 |
| `GET /api/shared/{share_token}` | — | `ReadOnlyTrip` | FR-25 |
| `GET /api/trips/{trip_id}/export.ics` | — | `text/calendar` | FR-26 |
| `GET /api/health` | — | `{status, modes, quota}` | FR-33, FR-34 |

> **의도적으로 제공하지 않는 것**: `GET /api/trips` (전체 목록). 계정이 없는 상태에서 목록을 노출하면 열거 공격이 성립합니다 (SEC-08, CA-2).
> 사용자의 여행 목록은 **브라우저 로컬 저장소에 보관된 `TripId` 집합**으로 구성합니다.

### C33 `ApiSchemas`
| 메서드 | 시그니처 | 목적 |
|---|---|---|
| (Pydantic 모델군) | — | 타입·길이·범위·형식 검증, 본문 크기 상한 (SEC-05) |
| `to_openapi` | `() -> dict` | **프론트 TS 타입의 원천** (Q7=A) |

---

## 8. `u2-trip-web` 주요 인터페이스

### W13 `DeepLinkBuilder` — 순수 함수 (Q8=A)
| 함수 | 시그니처 | 목적 |
|---|---|---|
| `placeUrl` | `(place: Place) -> {app: string, web: string}` | `nmap://place` + 웹 폴백 (FR-23, FR-24) |
| `routeUrl` | `(from: Place, to: Place, mode: TravelMode) -> {app: string, web: string}` | `nmap://route/public\|car\|walk` |
| `encodeParams` | `(params) -> string` | URL 인코딩. **PBT 후보(왕복)** |

### W14 `NativeBridge`
| 함수 | 시그니처 | 목적 |
|---|---|---|
| `isNative` | `() -> boolean` | 브리지 존재 감지 |
| `openMap` | `(urls: {app, web}) -> void` | 네이티브면 인텐트 위임, 아니면 `window.open` 폴백 |
| `share` | `(payload) -> void` | 시스템 공유 시트 또는 Web Share API |
| `requestLocation` | `() -> Promise<Coordinate \| null>` | 네이티브 권한 또는 Geolocation API |

### W4 `NaverMapAdapter` — 선언적 props (Q14=A)
```
props: {
  markers:   Array<{id, coordinate, label: number, dayIndex, selected}>
  polylines: Array<{path: Coordinate[], dayIndex, style: "solid" | "dashed"}>
  focus:     {bounds} | {center, zoom}
  onMarkerClick: (id) => void
}
```
> SDK 의 명령형 API(인스턴스 생성·마커 add/remove·수명 관리)는 **전부 이 컴포넌트 내부에 갇힙니다.**

### W15 `OfflineGate`
| 함수 | 시그니처 | 목적 |
|---|---|---|
| `useOnlineStatus` | `() -> boolean` | 온라인 감지 |
| `guardEdit` | `(action) -> action \| blocked` | 오프라인 시 편집 차단 (FR-32) |

---

## 9. `u3-trip-android` 브리지 계약 (u2 ↔ u3 조율 지점)

### A3 `BridgeHandler` — 노출 메서드 (최소 집합만)

| 메시지 | 페이로드 | 동작 |
|---|---|---|
| `openMap` | `{appUrl, webUrl}` | A4 가 인텐트 시도 → 실패 시 웹 URL (FR-23, FR-24) |
| `share` | `{title, text, url}` | 시스템 공유 시트 (FR-28) |
| `requestLocation` | `{}` | 권한 요청 후 `{lat, lng}` 또는 `null` 회신 (FR-28) |

**보안 계약 (Q15=A, SEC-08)**:
- `WebViewCompat.addWebMessageListener` 에 **허용 오리진 목록**을 지정합니다
- 미지원 기기에서만 `@JavascriptInterface` 폴백을 사용하며, 이때도 A2 가 허용 오리진 외 내비게이션을 차단합니다
- **위 3개 외의 메서드를 추가하지 않습니다.** 파일 접근·임의 인텐트 실행·저장소 접근을 노출하는 메서드는 금지합니다

| 컴포넌트 | 주요 메서드 |
|---|---|
| **A1** `MainActivity` | `onCreate()` / `onBackPressed()` — WebView 히스토리 우선 (FR-29) |
| **A2** `WebViewConfigurator` | `configure(webView)` — 하드닝 일괄 적용 (SEC-09) |
| **A4** `IntentLauncher` | `openExternal(appUrl, webUrl)` / `share(payload)` |
| **A5** `LocationProvider` | `requestCurrent(): Coordinate?` |
| **A7** `AppConfig` | `baseUrl(): String` — `BuildConfig.BASE_URL` (FR-27, CA-1) |

---

## 10. Functional Design 이월 항목 (11건)

| # | 항목 | 담당 유닛 | 우선도 |
|---|---|---|---|
| 1 | **C23 그라운딩 일치 판정 기준** — 문자열 유사도 임계값, 카테고리 정합, 거리 허용 범위 | u1 | 🔴 최우선 |
| 2 | C22 LLM 응답 스키마 정의 및 재시도 정책 | u1 | 🔴 |
| 3 | C18 목적함수 가중치·2-opt 종료 조건·시간 상한 | u1 | 🟠 |
| 4 | C15 고정 시각 항목과 이동시간이 충돌할 때의 처리 | u1 | 🟠 |
| 5 | C4 레이트 리밋 임계값·윈도·등급 분류 | u1 | 🟠 |
| 6 | C12 캐시 키 정규화 규칙·무효화 조건 | u1 | 🟡 |
| 7 | C31 상세 테이블 스키마·인덱스·제약 | u1 | 🟡 |
| 8 | 예외 분류 체계와 사용자 노출 문구 매핑 | u1 | 🟡 |
| 9 | C17 보정계수·보행속도·대중교통 근사식의 구체값 | u1 | 🟡 |
| 10 | W8 드래그 상호작용 세부 및 낙관적 업데이트 롤백 | u2 | 🟡 |
| 11 | A3 폴백 경로의 오리진 검증 구현 방식 | u3 | 🟠 |
