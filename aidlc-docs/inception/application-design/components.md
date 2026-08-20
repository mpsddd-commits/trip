# Components — trip

**Stage**: 🔵 INCEPTION - Application Design
**Created**: 2026-08-13T04:35:00Z
**설계 결정 근거**: `inception/plans/application-design-plan.md` Q1~Q16 = 전부 A

> **범위 주의**: 본 문서는 **컴포넌트 식별·책임·인터페이스**까지만 다룹니다.
> 상세 비즈니스 규칙(그라운딩 판정 기준, 최적화 목적함수, 캐시 무효화 조건 등)은 **Functional Design(CONSTRUCTION, 유닛별)** 으로 이월합니다.

---

## 0. 계층 구조 개요

### u1-trip-backend — 계층 기준 패키지 (Q1=A)

```
+---------------------------------------------------------------+
|  api/          라우터 + 요청/응답 스키마 (진입점)              |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|  services/     오케스트레이션 (외부 호출 + 도메인 조합)        |
+---------------------------------------------------------------+
          |                                        |
          v                                        v
+-------------------------------+  +---------------------------+
|  domain/   순수 로직 (I/O 없음)|  |  clients/   외부 API      |
|            의존성 0            |  |  storage/   영속화        |
+-------------------------------+  +---------------------------+
                              |
                              v
+---------------------------------------------------------------+
|  core/         설정 · 로깅 · 보안 · 오류 (횡단 관심사)         |
+---------------------------------------------------------------+
```

**핵심 규칙 (Q12=A)**: `domain/` 은 **아무것도 import 하지 않습니다**. 외부 데이터가 필요하면 호출자가 값으로 주입합니다. 이 규칙이 PBT-R2·R7 을 네트워크 없이 검증 가능하게 만드는 근거입니다.

### 컴포넌트 총계

| 유닛 | 개수 | 범위 |
|---|---|---|
| u1-trip-backend | 33 (C1~C33) | core 5 / clients 8 / domain 7 / services 9 / storage 2 / api 2 |
| u2-trip-web | 16 (W1~W16) | 인프라 3 / 지도 2 / 화면 7 / 공용 4 |
| u3-trip-android | 7 (A1~A7) | 호스트 1 / 설정·하드닝 2 / 브리지 2 / 화면·위치 2 |
| **합계** | **56** | |

---

## 1. u1-trip-backend — `core/` 횡단 관심사

### C1 `Config`
- **목적**: 모든 설정을 환경변수에서 읽어 타입 검증된 단일 객체로 제공 (NFR-15)
- **책임**
  - `.env` / 환경변수 로딩 및 타입·범위 검증 (pydantic-settings)
  - **외부 API 인증 정보 존재 여부 판정** → `credential_status` 로 노출. C13 `ClientFactory` 가 이 값으로 실제/목 구현을 선택 (Q3=A, FR-33)
  - `BIND_HOST` 기본값 `127.0.0.1` 제공 및 `0.0.0.0` 설정 시 경고 로그 (NFR-14, CA-1)
- **인터페이스**: 읽기 전용 싱글턴. 부팅 시 1회 생성, 이후 변경 불가
- **불변식**: 인증 정보 원문은 `__repr__`·로그·오류 응답 어디에도 노출하지 않는다 (SEC-03, SEC-12)

### C2 `LoggingSetup`
- **목적**: 구조화 JSON 로깅과 요청 상관관계 ID 제공 (NFR-8, SEC-03)
- **책임**
  - JSON 포매터 구성 — `timestamp` · `correlation_id` · `level` · `logger` · `message`
  - 요청 단위 correlation ID 생성 및 컨텍스트 전파(ContextVar)
  - **민감값 마스킹 필터** — API 키·토큰 패턴, 좌표 원문
  - 파일 핸들러 + 90일 로테이션 (SEC-14)
- **인터페이스**: `configure_logging(config)`, `get_logger(name)`, `correlation_id_middleware`

### C3 `SecurityHeaders`
- **목적**: 모든 HTML/API 응답에 보안 헤더 부여 (SEC-04)
- **책임**: `Content-Security-Policy`(네이버 지도 SDK 도메인 허용목록), `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` 상시 부여. `Strict-Transport-Security` 는 **HTTPS 요청에만** 부여 (CA-4)
- **인터페이스**: ASGI 미들웨어

### C4 `RateLimiter`
- **목적**: 인증 없는 공개 엔드포인트의 외부 비용 남용 차단 (SEC-11, CA-5 — 최상위 위험 ②)
- **책임**
  - 클라이언트 단위 슬라이딩 윈도 제한
  - **엔드포인트 등급별 정책** — LLM 호출 경로는 엄격, 조회 경로는 완화
  - 전역 일일 상한 도달 시 차단 (C28 `QuotaService` 와 연동)
  - 초과 시 보안 이벤트 로깅 (SEC-14)
- **인터페이스**: 라우터 의존성(dependency) 또는 미들웨어
- **이월**: 구체적 임계값·윈도 크기 → Functional Design(u1)

### C5 `ErrorHandler`
- **목적**: 전역 예외 처리 및 RFC 9457 Problem Details 응답 (Q6=A, SEC-09, SEC-15)
- **책임**
  - 도메인 예외 → HTTP 상태 코드 매핑
  - **사용자 노출 메시지 일반화** — 스택트레이스·내부 경로·프레임워크 버전 미노출
  - 내부 상세는 correlation ID 와 함께 로그에만 기록
  - 미처리 예외 포착 후 안전 응답 (fail-closed)
- **인터페이스**: `{type, title, status, detail, instance, code, correlation_id}`

---

## 2. u1-trip-backend — `clients/` 외부 API

> **설계 원칙 (Q2=A)**: 각 외부 API 는 **Protocol(인터페이스) + 실제 구현 + 목 구현** 3중 구조입니다.
> 재시도·타임아웃·계측은 `BaseHttpClient` 한 곳에, 캐시는 데코레이터 한 곳에 있습니다.

### C6 `BaseHttpClient`
- **목적**: 모든 외부 HTTP 호출의 공통 실행 정책 (NFR-2, NFR-3)
- **책임**
  - 연결 5초 / 읽기 10초 타임아웃 (LLM 은 읽기 120초)
  - **지수 백오프 재시도 최대 3회, 4xx 는 재시도하지 않음**
  - TLS 1.2+ 강제 (SEC-01)
  - 호출 계측 → C28 `QuotaService` 에 사용량 보고
  - 오류를 도메인 예외로 변환 (SEC-15)
- **인터페이스**: `request(method, url, **kwargs) -> Response`

### C7 `LocalSearchClient` *(Protocol)*
- **목적**: 네이버 지역검색 — **장소 그라운딩의 유일한 진실 공급원** (FR-3, FR-6)
- **책임**: 질의어로 장소명·도로명주소·카테고리·전화·좌표 조회. **1회 최대 5건 제약(CON-2)** 을 `start` 기반 페이징으로 노출
- **구현체**: `NaverLocalSearchClient` / `MockLocalSearchClient`
- **⚠️ 중요도**: 이 클라이언트가 실패하면 AI 일정 생성 전체가 불가합니다 (execution-plan §1.3)

### C8 `ContentSearchClient` *(Protocol)*
- **목적**: 네이버 블로그·이미지 검색 — 추천 콘텐츠 근거 확보 (FR-20, FR-21)
- **구현체**: `NaverContentSearchClient` / `MockContentSearchClient`

### C9 `DirectionsClient` *(Protocol)*
- **목적**: NCP Directions 5 — **자동차 경로 전용** (CON-1)
- **책임**: 출발·도착 좌표로 소요시간·거리·경로 좌표열 조회
- **구현체**: `NcpDirectionsClient` / `MockDirectionsClient`
- **명시적 비책임**: 대중교통·도보 경로는 이 클라이언트가 제공하지 않습니다. 도보는 C17 이 근사하고, 대중교통은 `nmap://` 딥링크로 위임합니다 (Q7=A)

### C10 `GeocodingClient` *(Protocol)*
- **목적**: NCP Geocoding / Reverse Geocoding — 주소 ↔ 좌표 변환
- **구현체**: `NcpGeocodingClient` / `MockGeocodingClient`

### C11 `LlmClient` *(Protocol)*
- **목적**: Claude API 호출 (FR-2, FR-20)
- **책임**: 메시지 전송, 토큰 사용량 보고, 응답 텍스트 반환
- **구현체**: `AnthropicLlmClient` / `MockLlmClient`
- **명시적 비책임**: 프롬프트 구성과 **응답 스키마 검증은 C22 `LlmDraftGenerator` 의 책임**입니다. 이 클라이언트는 전송만 담당합니다 (관심사 분리, SEC-11)

### C12 `CachingClientDecorator`
- **목적**: 외부 응답 TTL 캐시로 쿼터·비용 절약 (NFR-4, Q11=A)
- **책임**
  - 동일 인터페이스를 감싸는 데코레이터 — **서비스 계층은 캐시 존재를 알지 못함**
  - 캐시 키 산출(정규화된 질의 파라미터 해시), TTL 판정, 만료 항목 정리
  - TTL: 지역검색 7일 / Directions 1일 / 블로그·이미지 3일
- **적용 범위**: **실제 구현체에만 적용**합니다. 목 구현체는 이미 결정적이므로 감싸지 않습니다 (DD-6)
- **비대상**: `LlmClient` 는 동일 입력에도 다른 출력이 유효하므로 캐시하지 않습니다

### C13 `ClientFactory`
- **목적**: 인증 정보 유무에 따른 구현체 선택과 데코레이터 합성 (Q3=A, FR-33)
- **책임**
  - C1 `Config.credential_status` 확인 → 실제 또는 목 구현 생성
  - 합성 순서: `BaseHttpClient` → `Real*Client` → `CachingClientDecorator`
  - **부분 목 모드 지원** — 예: 지도 키는 있고 LLM 키만 없는 경우, LLM 만 목으로 대체
  - 활성 모드를 기동 로그와 `/health` 에 노출 → 프론트가 "데모 데이터" 배너 표시 (FR-33)
- **인터페이스**: FastAPI 의존성 주입 제공자

---

## 3. u1-trip-backend — `domain/` 순수 로직 (의존성 0)

> **불변 규칙 (Q10=A, Q12=A)**: 이 계층의 모든 함수는 **I/O 를 수행하지 않습니다.**
> 외부 데이터는 전부 인자로 주입됩니다. 그 결과 전체가 PBT 대상이 됩니다.

### C14 `DomainModels`
- **목적**: 값 객체 정의 — `Trip` · `TripDay` · `ItineraryItem` · `Place` · `Coordinate` · `TravelLeg` · `TimeWindow` · `PlaceContent`
- **책임**: 불변 데이터 구조 + 생성 시 유효성 보장(좌표 범위, 시각 순서, 비음수 체류시간)
- **PBT 후보**: JSON 직렬화 왕복 (PBT-R1)

### C15 `TimelineCalculator`
- **목적**: 항목 순서와 이동시간으로 각 항목의 도착·출발 시각을 산출 (FR-9)
- **입력**: 항목 목록, 구간별 이동시간(C16 산출), 하루 활동 시작 시각, 고정 시각 항목
- **출력**: 시각이 채워진 타임라인
- **PBT 후보 (PBT-R2)**: 시각 단조 증가 / 고정 시각 항목 불변 / 체류·이동시간 비음수 / 항목 개수 보존

### C16 `DistanceMatrix`
- **목적**: 구간별 이동시간·거리를 담는 값 객체 (C15·C17 의 입력)
- **책임**: `(from_index, to_index, mode)` → `(duration, distance, path?)` 조회. **자기 자신은 어떤 API 도 호출하지 않으며**, C24 `TravelMatrixService` 가 채워서 전달합니다

### C17 `TravelTimeEstimator`
- **목적**: 외부 경로 API 없이 이동시간을 근사 (FR-10, CON-1)
- **책임**
  - 도보: 하버사인 거리 × 보정계수(기본 1.3) ÷ 보행속도(기본 4.5 km/h)
  - 대중교통: 근사식 + **"실제와 다를 수 있음" 플래그를 결과에 부착** (FR-10)
  - 자동차: Directions 결과 부재 시 폴백 근사
- **PBT 후보**: 거리·시간 비음수 / 거리 증가 시 시간 단조 증가 / 동일 지점 간 0

### C18 `RouteOptimizer`
- **목적**: 일자별 방문 순서 최적화 (FR-8)
- **책임**
  - 총 이동시간 최소화 (최근접 이웃 초기해 + 2-opt 개선)
  - **제약**: 숙소를 시작·종료로 고정하는 옵션, 시각이 고정된 항목의 위치 보존
- **입력**: 항목 목록 + `DistanceMatrix` + 제약 → **출력**: 재배열된 항목 목록
- **PBT 후보 (PBT-R2, PBT-R7)**: 항목 집합 보존(개수·구성 동일) / 고정 항목 위치 불변 / 결과 총 이동시간 ≤ 입력 총 이동시간 / n≤8 에서 완전탐색 오라클과 일치
- **이월**: 목적함수 가중치, 반복 종료 조건 → Functional Design(u1)

### C19 `OpeningHoursChecker`
- **목적**: 배정 시각이 영업시간 밖인지 판정 (FR-13)
- **책임**: 영업시간 정보가 **있을 때만** 경고를 산출. 정보가 없으면 경고하지 않음(거짓 경고 방지)

### C20 `IcsBuilder`
- **목적**: 일정을 iCalendar 형식으로 직렬화 (FR-26)
- **책임**: 항목당 VEVENT 생성, `Asia/Seoul` 시간대 고정, 특수문자 이스케이프
- **PBT 후보 (PBT-R1)**: 직렬화 → 파싱 왕복이 원본 필드를 보존 (손실 필드는 명시적으로 문서화)

---

## 4. u1-trip-backend — `services/` 오케스트레이션

### C21 `TripService`
- **목적**: 여행 생명주기 관리 (FR-4, FR-5, FR-7, FR-25)
- **책임**: 생성·조회·수정·삭제, 항목 추가/삭제/순서변경/일자이동, **UUIDv4 식별자 발급**, **읽기 전용 공유 토큰 발급·폐기**(FR-25, SEC-08), 변경 감사 로깅(SEC-13)
- **⚠️ 보안 책임**: 편집 경로와 공유 조회 경로의 권한을 분리합니다 (CA-3)

### C22 `LlmDraftGenerator`
- **목적**: LLM 일정 초안 생성 (FR-2)
- **책임**
  - 여행 조건 → 프롬프트 구성
  - C11 `LlmClient` 호출
  - **응답을 엄격한 스키마로 검증**하고 실패 시 거부 (SEC-13 — 신뢰할 수 없는 데이터 역직렬화 금지)
  - 스키마 불일치 시 제한적 재시도
- **출력**: **좌표 없는 장소명 후보 목록** — 좌표는 C23 이 부여합니다

### C23 `PlaceResolver` 🔴
- **목적**: LLM 이 만든 장소명을 실재하는 장소로 해석 (FR-3) — **최상위 위험 ①(LLM 환각)의 차단 지점**
- **책임**
  - 장소명 후보를 C7 `LocalSearchClient` 로 조회
  - 후보와 검색 결과의 **일치 여부 판정** → 실좌표·도로명주소·카테고리·전화 부여
  - **해석 실패 항목은 일정에 넣지 않고 "확인 필요" 목록으로 분리** (FR-3)
  - 중복 장소 병합
- **독립 컴포넌트인 이유 (Q9=A)**: 이 판정 규칙이 제품 신뢰성의 핵심이므로, 단위 테스트로 직접 겨냥할 수 있어야 합니다
- **이월**: 일치 판정 기준(문자열 유사도 임계값, 카테고리 정합, 거리 허용 범위) → **Functional Design(u1) 최우선 항목**

### C24 `TravelMatrixService`
- **목적**: 구간별 이동시간·경로 확보 (FR-10, FR-16)
- **책임**: 이동수단별로 C9 `DirectionsClient`(자동차) 또는 C17 `TravelTimeEstimator`(도보·대중교통) 를 선택 호출하고, 결과를 C16 `DistanceMatrix` 로 조립. Directions 실패 시 근사 폴백 (NFR-3)
- **경계**: 계산식은 도메인(C17)에, **호출과 조립만** 이 서비스에 둡니다

### C25 `ItineraryGenerationService`
- **목적**: AI 일정 생성 파이프라인 오케스트레이션 (Q9=A)
- **파이프라인**: `C22 초안` → `C23 그라운딩` → `C24 이동시간 행렬` → `C18 순서 최적화(선택)` → `C15 타임라인 계산` → `C21 저장`
- **책임**: 단계 전이마다 C27 `JobService` 에 진행 상태 기록, 단계 실패 시 부분 결과와 실패 사유 보존
- **경계**: 이 서비스는 **조율만** 하며 계산·판정 로직을 직접 갖지 않습니다

### C26 `PlaceSearchService`
- **목적**: 사용자 직접 장소 검색 (FR-6, FR-22)
- **책임**: 질의 검색 + **5건 제약 페이징**(CON-2), 주변 추천 후보 조회(반경 필터)

### C27 `RecommendationService`
- **목적**: 장소별 추천 콘텐츠 생성 (FR-20, FR-21)
- **책임**
  - C8 로 블로그·이미지 조회
  - C11 로 요약 생성 — 음식점은 대표 메뉴, 관광지는 관람 포인트
  - **근거 블로그 링크와 이미지 출처를 결과에 필수 포함** (CON-7, CON-8)
  - 요약을 "AI 요약" 으로 표시하는 플래그 부착
- **degrade 정책**: 블로그·이미지 실패 시 해당 섹션만 비우고 나머지는 정상 반환 (NFR-3)

### C28 `JobService`
- **목적**: 장시간 작업의 비동기 실행과 상태 조회 (Q5=A, NFR-1)
- **책임**: job 등록 → `job_id` 즉시 반환, 백그라운드 실행, 단계별 진행률·상태·결과·오류 저장, 완료 job 정리
- **상태**: `queued` → `running(step)` → `succeeded` / `failed` / `partial`

### C29 `QuotaService`
- **목적**: 외부 API 일일 사용량 계측과 상한 관리 (NFR-4, FR-34)
- **책임**: API 별 일일 카운터 증가·조회, 상한 임박·도달 판정, 도달 시 C4 `RateLimiter` 와 협력해 차단하고 사용자에게 안내, 소진을 보안 이벤트로 로깅 (SEC-14)
- **기준**: 지역검색 25,000회/일 (CON-2)

---

## 5. u1-trip-backend — `storage/` 영속화

### C30 `Database`
- **목적**: SQLAlchemy 엔진·세션 관리 (Q17=A)
- **책임**: 엔진 생성, 세션 수명 관리(요청 단위), 스키마 마이그레이션 적용, **파라미터 바인딩만 사용**(SEC-05 — 문자열 연결 금지)

### C31 `Repositories`
- **목적**: 테이블별 영속화 접근. 5개 리포지토리를 하나의 컴포넌트로 묶습니다
  - `TripRepository` — 여행·일자·항목·장소 (FR-4)
  - `CacheRepository` — 외부 API 캐시 + TTL (C12 가 사용)
  - `JobRepository` — 작업 상태 (C28 이 사용)
  - `QuotaRepository` — 일일 사용량 (C29 가 사용)
  - `AuditLogRepository` — 변경 이력·보안 이벤트 (SEC-13, SEC-14). **애플리케이션은 이 테이블을 삭제·수정하지 않고 추가만 합니다**
- **이월**: 상세 스키마·인덱스 → Functional Design(u1)

---

## 6. u1-trip-backend — `api/` 진입점

### C32 `ApiRouters`
- **목적**: HTTP 엔드포인트 노출. 라우터 모듈 묶음
  - `trips` — 여행 CRUD, 항목 편집 (FR-4~7)
  - `generation` — AI 생성 시작 + job 상태 조회 (FR-2, Q5=A)
  - `places` — 장소 검색, 상세, 추천 (FR-6, FR-20~22)
  - `routes` — 이동시간 재계산, 순서 최적화 (FR-8, FR-10)
  - `share` — 공유 토큰 발급·폐기, 읽기 전용 조회 (FR-25)
  - `export` — `.ics` 내보내기 (FR-26)
  - `health` — 헬스체크, 목 모드 여부, 쿼터 사용량 (FR-34)
- **책임**: 요청 검증 위임, 서비스 호출, 응답 직렬화. **비즈니스 로직 금지**
- **보안**: 전 경로를 명시적 public 으로 선언하고(CA-2), 자원 참조는 UUID 로만, **목록 열거 API 미제공** (SEC-08). CORS 는 허용 오리진 화이트리스트

### C33 `ApiSchemas`
- **목적**: 요청·응답 Pydantic 스키마 (SEC-05)
- **책임**: 타입·길이·범위·형식 검증, 문자열 최대 길이 명시, 요청 본문 크기 상한, HTML 이스케이프. **이 스키마가 OpenAPI 를 통해 프론트 타입의 원천이 됩니다** (Q7=A)

---

## 7. u2-trip-web — 프론트엔드 (기능 기준 구성, Q4=A)

### 인프라

| ID | 컴포넌트 | 책임 |
|---|---|---|
| **W1** | `ApiClient` | 백엔드 호출 래퍼. **OpenAPI 에서 생성된 타입** 사용(Q7=A), Problem Details 오류 파싱, correlation ID 전달 |
| **W2** | `QueryClientSetup` | TanStack Query 설정 + **IndexedDB persist**(Q13=A, Q16=A). 재검증·폴링 정책. ⚠️ **job 상태는 persist 대상에서 제외** (DD-14) |
| **W3** | `UiStore` | Zustand — 선택된 일자, 선택된 항목, 드래그 중 임시 순서, 지도 하이라이트 대상. **서버 데이터는 담지 않음** |

### 지도

| ID | 컴포넌트 | 책임 |
|---|---|---|
| **W4** | `NaverMapAdapter` | 지도 SDK 로딩·인스턴스 수명·마커/폴리라인 명령형 API 캡슐화. 바깥에는 **선언적 props 만** 노출 (Q14=A). 목 모드에서 대체 구현으로 교체 가능 |
| **W5** | `MapView` | 번호 마커 ①②③, 일자별 색상, 경로 폴리라인(자동차=실경로 / 도보·대중교통=점선), 일자 필터, 뷰포트 자동 조정 (FR-14~18) |

### 화면

| ID | 컴포넌트 | 책임 |
|---|---|---|
| **W6** | `TripCreateWizard` | 목적지·기간·인원·스타일·시각·이동수단·예산 입력 (FR-1) |
| **W7** | `GenerationProgress` | job 폴링 + 단계별 진행 표시(초안 → 그라운딩 → 완료), **"확인 필요" 장소 목록 제시** (FR-2, FR-3, NFR-1) |
| **W8** | `TimelineView` | 드래그 앤 드롭 순서 변경, 시각·체류시간·메모 편집, 이동수단 선택, 영업시간 경고 배지, 순서 최적화 버튼 (FR-5·7·8·9·11·13) |
| **W9** | `PlaceDetailPanel` | 주소·전화·카테고리·추천 콘텐츠·사진·출처·네이버지도 열기 (FR-17, FR-20, FR-21) |
| **W10** | `PlaceSearchPanel` | 장소 검색 + "더 보기" 페이징 (FR-6) |
| **W11** | `RecommendationPanel` | 주변 미포함 추천 장소 + 한 번에 담기 (FR-22) |
| **W12** | `SharedTripView` | 공유 토큰 기반 **읽기 전용** 화면 (FR-25) |

### 공용

| ID | 컴포넌트 | 책임 |
|---|---|---|
| **W13** | `DeepLinkBuilder` | `nmap://place`, `nmap://route/public\|car\|walk` URL 생성 + `map.naver.com` 폴백 URL. **순수 함수** (Q8=A, FR-23, FR-24) |
| **W14** | `NativeBridge` | 안드로이드 브리지 존재 감지 → 있으면 네이티브 위임, 없으면 웹 폴백. **웹과 앱의 분기를 이 한 곳에 가둠** |
| **W15** | `OfflineGate` | 온라인 상태 감지, 오프라인 시 **편집 차단 + 안내 배너**, 온라인 복귀 시 재검증 트리거 (FR-31, FR-32) |
| **W16** | `SharedUi` | 버튼·모달·토스트·스켈레톤 등 기본 요소. 반응형 3구간, 키보드 접근성, **색상 단독 정보 전달 금지**(일자는 색 + 번호 병기) (NFR-5, NFR-6) |

---

## 8. u3-trip-android — 안드로이드 (Kotlin)

> ⚠️ **검증 한계**: 로컬 JDK·Android SDK 부재로 컴파일·APK 빌드·기기 실행을 검증할 수 없습니다 (CON-6, ASM-4).

| ID | 컴포넌트 | 책임 |
|---|---|---|
| **A1** | `MainActivity` | WebView 호스트, 생명주기, **하드웨어 뒤로가기 → WebView 히스토리 우선 소비** (FR-29) |
| **A2** | `WebViewConfigurator` | WebView 하드닝 — JavaScript 활성 범위 최소화, **파일 접근·콘텐츠 접근 비활성**, 혼합 콘텐츠 차단, 허용 오리진 외 내비게이션 차단 (SEC-09, SEC-11) |
| **A3** | `BridgeHandler` | **`WebViewCompat.addWebMessageListener` + 오리진 허용목록** (Q15=A, SEC-08). 미지원 기기는 `@JavascriptInterface` 폴백. 노출 메서드는 최소 집합만 |
| **A4** | `IntentLauncher` | 웹이 만든 URL(W13)로 네이버지도 앱 인텐트 실행, **미설치 시 웹 URL 폴백**, 시스템 공유 시트 (FR-23, FR-24, FR-28) |
| **A5** | `LocationProvider` | 위치 권한 요청 및 현재 좌표 전달. 권한 거부 시 기능만 비활성 (FR-28) |
| **A6** | `OfflineScreen` | 네트워크 단절 시 안내 화면 + 재시도 (FR-30) |
| **A7** | `AppConfig` | `BuildConfig.BASE_URL` 주입 — debug(개발 서버) / release(운영 주소) 빌드 변형 분리 (FR-27, CA-1) |

---

## 9. FR 커버리지 매트릭스 (미매핑 0건 확인)

| FR | 컴포넌트 | FR | 컴포넌트 |
|---|---|---|---|
| FR-1 | W6, C33 | FR-18 | W5, W3 |
| FR-2 | C22, C11, C25 | FR-19 | W5, W8, W3 |
| FR-3 | **C23**, C7 | FR-20 | C27, C8, C11, W9 |
| FR-4 | C21, C31 | FR-21 | C27, C8, W9 |
| FR-5 | C21, W8 | FR-22 | C26, W11 |
| FR-6 | C26, C7, W10 | FR-23 | W13, W14, A3, A4 |
| FR-7 | C21, W8 | FR-24 | W13, A4 |
| FR-8 | **C18**, C24, W8 | FR-25 | C21, W12 |
| FR-9 | **C15**, W8 | FR-26 | C20, C32 |
| FR-10 | C24, C9, C17 | FR-27 | A1, A7 |
| FR-11 | C24, W8 | FR-28 | A3, A4, A5 |
| FR-12 | W13, W8 | FR-29 | A1 |
| FR-13 | C19, W8 | FR-30 | A6 |
| FR-14 | W4, W5 | FR-31 | W2, W15 |
| FR-15 | W5 | FR-32 | W15, W2 |
| FR-16 | W5, C24 | FR-33 | **C13**, C1, W16 |
| FR-17 | W9, W5 | FR-34 | C29, C32 |

**미매핑 FR: 0건** ✅

---

## 10. SEC 소유 컴포넌트 지정

| SEC | 소유 컴포넌트 | SEC | 소유 컴포넌트 |
|---|---|---|---|
| SEC-01 | C6(전송) / C30(저장) — 루프백 예외 CA-4 | SEC-09 | C5, A2, C30 |
| SEC-02 | **N/A** (중간자 없음) | SEC-10 | 빌드 구성 (Infrastructure Design 이월) |
| SEC-03 | C2 | SEC-11 | **C4**, C13, C11↔C22 분리 |
| SEC-04 | C3 | SEC-12 | C1 (하드코딩 금지) / 사용자 인증은 N/A |
| SEC-05 | **C33**, C30 | SEC-13 | **C22**(LLM 응답 검증), C31(감사), W1(SRI) |
| SEC-06 | **N/A** (IAM 없음) | SEC-14 | C2, C29, C31 |
| SEC-07 | C1(`BIND_HOST`) — Infrastructure Design 이월 | SEC-15 | **C5**, C6, C30 |
| SEC-08 | **C21**(UUID·토큰 분리), C32(public 선언·CORS·열거 금지), A3(오리진) | | |

**미지정 SEC: 0건** ✅ (N/A 2건 포함)
