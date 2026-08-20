# Logical Components — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - NFR Design (Unit 1/3)
**Created**: 2026-08-13T06:00:00Z

> Application Design 의 C1~C33 에 **NFR 패턴 적용으로 추가되는 논리 컴포넌트**와 그 배치를 정의합니다.

---

## 1. 추가되는 논리 컴포넌트 (L1 ~ L8)

Application Design 의 컴포넌트 33종에 더해, NFR 패턴 구현을 위한 **8종**이 추가됩니다.

| ID | 컴포넌트 | 계층 | 책임 | 근거 패턴 |
|---|---|---|---|---|
| **L1** | `CircuitBreaker` | `clients/` | API 별 실패 계수·상태 전이·open 판정 | RP-2 (ND-1) |
| **L2** | `ExternalSemaphore` | `clients/` | API 별 동시 호출 상한(전역 5) | SP-3 (ND-17) |
| **L3** | `JobRunner` | `services/` | asyncio 태스크 실행·동시 3개 제한·고아 정리·종료 시 취소 | RP-4 (ND-2, ND-3) |
| **L4** | `DbExecutor` | `storage/` | 동기 DB 호출을 스레드 풀에서 실행 | SP-2 (ND-18) |
| **L5** | `AccessLogMiddleware` | `core/` | 요청별 처리시간·외부 호출 수·캐시 적중 기록, P95 초과 시 WARN | PP-5 (ND-10) |
| **L6** | `BodySizeLimitMiddleware` | `core/` | 요청 본문 1MB 상한 | SEP-4 |
| **L7** | `StaticAssetHandler` | `api/` | `web/dist` 서빙 + 캐시 헤더 + SPA catch-all | PP-3 (ND-8) |
| **L8** | `MaintenanceScheduler` | `core/` | 기동 시 1회 + 24시간 주기 정리 | LC-2 (ND-16) |

### 기존 컴포넌트의 확장

| 컴포넌트 | 추가되는 책임 |
|---|---|
| **C6** `BaseHttpClient` | L1 서킷 확인 → L2 세마포어 획득 → 타임아웃·재시도 → C29 계측 |
| **C4** `RateLimiter` | 인메모리 IP 윈도 + SQLite 전역 일일 카운터 (SP-4) |
| **C1** `Config` | 서킷·세마포어·동시성·캐시 TTL 설정 항목 추가, `BIND_HOST` 경고 |
| **C30** `Database` | WAL·`busy_timeout`·`synchronous`·`foreign_keys` PRAGMA 적용 (SP-1) |
| **C28** `JobService` | L3 `JobRunner` 와 협력 (등록/상태 기록은 C28, 실행은 L3) |
| **C2** `LoggingSetup` | 파일 로테이션 90일, 민감값 마스킹 필터 |

**컴포넌트 총계**: u1 = 33 + 8 = **41종**

---

## 2. 요청 처리 파이프라인 (LC-1)

```
                          HTTP 요청
                              |
+-----------------------------v-----------------------------+
|  (1) ErrorHandler                     C5                  |
|  +-------------------------------------------------------+|
|  | (2) CorrelationId                  C2                 ||
|  | +-----------------------------------------------------+|
|  | | (3) AccessLog                    L5                 |||
|  | | +---------------------------------------------------+|
|  | | | (4) SecurityHeaders            C3                 ||||
|  | | | +-------------------------------------------------+|
|  | | | | (5) GZip                                        |||||
|  | | | | +-----------------------------------------------+|
|  | | | | | (6) CORS (개발 시에만)                        ||||||
|  | | | | | +---------------------------------------------+|
|  | | | | | | (7) BodySizeLimit          L6               |||||||
|  | | | | | | +-------------------------------------------+|
|  | | | | | | | (8) RateLimit             C4              ||||||||
|  | | | | | | | +-----------------------------------------+|
|  | | | | | | | |  (9) Router + Schema    C32 C33         |||||||||
|  | | | | | | | |         |                                |
|  | | | | | | | |         v  서비스 계층 (C21~C29)          |
|  | | | | | | | +-----------------------------------------+|
|  | | | | | | +-------------------------------------------+|
|  | | | | | +---------------------------------------------+|
|  | | | | +-----------------------------------------------+|
|  | | | +-------------------------------------------------+|
|  | | +---------------------------------------------------+|
|  | +-----------------------------------------------------+|
|  +-------------------------------------------------------+|
+-----------------------------------------------------------+
```

**정적 자산 경로**: `/api/*` 이외의 경로는 **(9) 단계에서 L7 `StaticAssetHandler`** 로 위임됩니다. 보안 헤더·gzip 은 동일하게 적용되고, 레이트 리밋은 `CHEAP` 등급을 적용합니다.

---

## 3. 외부 호출 파이프라인

```
서비스 (C21~C29)
     |
     v
+---------------------------+
| C12 CachingDecorator      |  캐시 적중? --> 즉시 반환 (외부 호출 0)
+---------------------------+
     | 미적중
     v
+---------------------------+
| C29 QuotaService          |  일일 상한 도달? --> QuotaExhaustedError
+---------------------------+
     | 통과
     v
+---------------------------+
| L1 CircuitBreaker         |  open? --> 폴백 (RP-3)
+---------------------------+
     | closed / half-open
     v
+---------------------------+
| L2 ExternalSemaphore      |  API별 동시 5 초과? --> 대기
+---------------------------+
     | 획득
     v
+---------------------------+
| C6 BaseHttpClient         |  타임아웃 + 지수 백오프 재시도(4xx 제외)
|   httpx.AsyncClient       |  (앱 수명 단일 인스턴스, 커넥션 풀 재사용)
+---------------------------+
     |
     +--> 성공: C29 계측 + C12 캐시 저장 + L1 성공 기록
     +--> 실패: C29 계측 + L1 실패 기록 --> 폴백 (RP-3)
```

> **순서 근거**: 캐시가 가장 앞이라 **적중 시 쿼터·서킷·세마포어를 전혀 건드리지 않습니다.**
> 쿼터가 서킷보다 앞인 이유는, 쿼터 소진은 "정상 동작 중 상한 도달"이라 서킷 실패로 세면 안 되기 때문입니다 (RP-2).

---

## 4. 백그라운드 작업 구조

```
POST /trips/{id}/generate
        |
        v  C4 RateLimiter (EXPENSIVE 등급)
        v  C28 JobService.enqueue  -->  SQLite JobRepository
        |
        v  L3 JobRunner.submit
        |     |
        |     +-- 실행 슬롯 3개 미만? --> 즉시 asyncio 태스크 시작
        |     +-- 3개 도달?          --> queued 유지, 슬롯 반환 시 시작
        |
        v  job_id 반환 (202)

[L3 JobRunner 내부]
        |
        v  C25 ItineraryGenerationService._run_pipeline
        |     각 단계마다 C28.update(step, progress)
        |     외부 호출은 §3 파이프라인 경유 (L2 전역 상한 적용)
        |     DB 접근은 L4 DbExecutor 경유 (이벤트 루프 비차단)
        |
        v  종료 시 C28.update(state=succeeded|partial|failed)

[앱 기동 시]
        v  L3.recover_orphans()  --  running 상태 job 전부 failed 로 전환
[앱 종료 시]
        v  L3.shutdown()         --  실행 중 태스크 취소, job=failed 기록
```

---

## 5. 설정 항목 목록 (C1 `Config`)

Infrastructure Design 에서 `.env.example` 로 구체화됩니다.

### 5.1 인증 정보 (전부 선택 — 없으면 목 모드)

| 변수 | 용도 |
|---|---|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | 네이버 검색 API (지역·블로그·이미지) |
| `NCP_CLIENT_ID` / `NCP_CLIENT_SECRET` | NCP Maps (Directions·Geocoding) |
| `NCP_MAP_CLIENT_KEY` | **지도 SDK 클라이언트 키 — 프론트에 전달됨** (CON-3) |
| `ANTHROPIC_API_KEY` | Claude API |

### 5.2 서버·배포

| 변수 | 기본값 | 근거 |
|---|---|---|
| `BIND_HOST` | `127.0.0.1` | NFR-14, CA-1 — `0.0.0.0` 설정 시 경고 로그 |
| `PORT` | `8200` | NFR-13 |
| `CORS_ALLOW_ORIGINS` | (비어 있음) | SEP-2 — 개발 시에만 지정 |
| `DATABASE_PATH` | `/app/data/trip.db` | UD-10 |
| `LOG_DIR` | `/app/logs` | UD-10 |
| `LOG_LEVEL` | `INFO` | |

### 5.3 복원력

| 변수 | 기본값 |
|---|---|
| `HTTP_CONNECT_TIMEOUT_SEC` | `5` |
| `HTTP_READ_TIMEOUT_SEC` | `10` |
| `LLM_READ_TIMEOUT_SEC` | `120` |
| `HTTP_MAX_RETRIES` | `3` |
| `CIRCUIT_FAILURE_THRESHOLD` | `5` |
| `CIRCUIT_OPEN_SECONDS` | `60` |

### 5.4 동시성

| 변수 | 기본값 | 비고 |
|---|---|---|
| `MAX_CONCURRENT_JOBS` | `3` | |
| `JOB_PARALLELISM` | `5` | job 내부 병렬 호출 |
| `EXTERNAL_CONCURRENCY` | `5` | **API 별 전역 상한 (ND-17)** |
| `DB_THREAD_POOL_SIZE` | `8` | L4 |

### 5.5 레이트 리밋·쿼터

| 변수 | 기본값 |
|---|---|
| `RATE_EXPENSIVE_PER_HOUR` | `5` |
| `RATE_EXPENSIVE_GLOBAL_PER_DAY` | `50` |
| `RATE_EXTERNAL_PER_MIN` | `60` |
| `RATE_CHEAP_PER_MIN` | `300` |
| `QUOTA_NAVER_LOCAL_PER_DAY` | `25000` |

### 5.6 캐시·수명

| 변수 | 기본값 |
|---|---|
| `CACHE_TTL_LOCAL_SEARCH_DAYS` | `7` |
| `CACHE_TTL_DIRECTIONS_DAYS` | `1` |
| `CACHE_TTL_CONTENT_DAYS` | `3` |
| `CACHE_TTL_GEOCODE_DAYS` | `30` |
| `CACHE_GRACE_DAYS` | `7` |
| `JOB_RETENTION_HOURS` | `24` |
| `AUDIT_RETENTION_DAYS` | `90` |

### 5.7 도메인 규칙 (BR 설정값)

| 변수 | 기본값 | BR |
|---|---|---|
| `MAX_TRIP_DAYS` | `10` | BR-01 |
| `MAX_ITEMS_PER_DAY` | `15` | BR-02 |
| `MAX_ITEMS_PER_TRIP` | `100` | BR-02 |
| `LLM_MODEL` | `claude-sonnet-5` | BR-06 |
| `LLM_MAX_RETRIES` | `2` | BR-07 |
| `RESOLVE_SIMILARITY_THRESHOLD` | `0.60` | BR-11 |
| `WALK_DETOUR` / `WALK_SPEED_KMH` / `WALK_MIN_SEC` | `1.3` / `4.5` / `180` | BR-24 |
| `TRANSIT_DETOUR` / `TRANSIT_SPEED_KMH` / `TRANSIT_WAIT_SEC` / `TRANSIT_MIN_SEC` | `1.4` / `20` / `600` / `600` | BR-25 |
| `CAR_FALLBACK_DETOUR` / `CAR_FALLBACK_SPEED_KMH` / `CAR_MIN_SEC` | `1.4` / `30` / `300` | BR-26 |
| `OPTIMIZE_NO_IMPROVE_LIMIT` / `OPTIMIZE_MAX_ITER` / `OPTIMIZE_TIME_LIMIT_MS` | `50` / `1000` / `200` | BR-22 |
| `MAX_REQUEST_BODY_BYTES` | `1048576` | BR-05 |

**총 설정 항목: 약 47개**

---

## 6. 컴포넌트 배치 (패키지)

```
backend/app/
+-- core/
|   +-- config.py              C1  + 설정 47종
|   +-- logging_config.py      C2  + 로테이션·마스킹
|   +-- security_headers.py    C3  + CSP §4.1
|   +-- rate_limit.py          C4  + 인메모리 윈도 / SQLite 일일
|   +-- errors.py              C5  + Problem Details
|   +-- access_log.py          L5
|   +-- body_limit.py          L6
|   +-- scheduler.py           L8
+-- clients/
|   +-- base.py                C6  + 서킷·세마포어 통합
|   +-- circuit.py             L1
|   +-- semaphore.py           L2
|   +-- cache_decorator.py     C12
|   +-- factory.py             C13
|   +-- naver_local.py         C7   (Protocol + Real + Mock)
|   +-- naver_content.py       C8
|   +-- ncp_directions.py      C9
|   +-- ncp_geocoding.py       C10
|   +-- anthropic_llm.py       C11
+-- domain/                    C14~C20  (의존성 0 — NFR 컴포넌트 없음)
+-- services/                  C21~C29
|   +-- job_runner.py          L3
+-- storage/
|   +-- database.py            C30 + PRAGMA
|   +-- db_executor.py         L4
|   +-- repositories/          C31
+-- api/
    +-- routers/               C32
    +-- schemas/               C33
    +-- static.py              L7
```

> **`domain/` 에 NFR 컴포넌트가 하나도 없습니다.** 서킷·세마포어·캐시·스레드 풀은 전부 바깥 계층에 있습니다.
> 이것이 DD-16(의존성 0)이 지켜지고 있다는 증거이며, PBT-R2·R7 을 네트워크 없이 실행할 수 있는 근거입니다.

---

## 7. 설계 결정 (ND-1 ~ ND-18)

| ID | 결정 | 근거 |
|---|---|---|
| **ND-1** | API 별 독립 경량 서킷 브레이커 (실패 5회 → 60초 open) | Q1=A |
| **ND-2** | 백그라운드 작업은 프로세스 내 `asyncio` 태스크 + 기동 시 고아 정리 | Q2=A |
| **ND-3** | job 전역 동시 3개, 초과는 `queued` | Q3=A |
| **ND-4** | job 재시도 API 미제공 | Q4=A |
| **ND-5** | SQLite WAL + `busy_timeout` 5초 + `synchronous=NORMAL` | Q5=A |
| **ND-6** | `httpx.AsyncClient` 비동기 + 커넥션 풀 재사용 | Q6=A |
| **ND-7** | IP 레이트 리밋은 인메모리, **전역 일일 상한은 SQLite 영속화** | Q7=A |
| **ND-8** | 해시 자산 `immutable` 영구 캐시 / `index.html` `no-cache` / API `no-store` | Q8=A |
| **ND-9** | 1KB 초과 응답 gzip | Q9=A |
| **ND-10** | 처리시간 구조화 로깅 + P95 초과 WARN, 메트릭 백엔드 미도입 | Q10=A |
| **ND-11** | CSP 명시적 허용목록. `unsafe-inline` 은 **style 에만**, 사유 문서화 | Q11=A, SEC-04 |
| **ND-12** | 운영은 CORS 비활성(단일 오리진), 개발만 명시 오리진. **와일드카드 금지** | Q12=A |
| **ND-13** | 환경변수 + `.env` + `SecretStr`. 누락은 오류가 아니라 목 모드 전환 | Q13=A |
| **ND-14** | 헬스체크 2단계, **외부 API 미호출** | Q14=A |
| **ND-15** | 미들웨어 9단계. 오류 핸들러 최외곽, 레이트 리밋 라우터 직전 | Q15=A |
| **ND-16** | `asyncio` 주기 태스크 정리 스케줄러 | Q16=A |
| **ND-17** | ⚠️ **파생** — API 별 전역 외부 호출 세마포어(5). job 동시성과 곱해지지 않도록 | Q3×Q6 충돌 해소 |
| **ND-18** | ⚠️ **파생** — DB 접근을 스레드 풀에서 실행. `async` 컨텍스트에서 동기 DB 직접 호출 금지 | Q2×Q5 충돌 해소 |

---

## 8. Build & Test 검증 예약 항목

| # | 항목 | 이유 |
|---|---|---|
| 1 | **CSP 허용 도메인 실측** | 지도 SDK 로드 시 CSP 위반이 콘솔에 뜨지 않는지 확인. §4.1 은 기준선 |
| 2 | 지역검색 `mapx`/`mapy` **좌표계 확정** | 오해석 시 지도 전 지점이 어긋남. `to_wgs84()` 단일 함수에 격리됨 |
| 3 | SQLite WAL 하에서 job 쓰기 + API 읽기 **동시성 실측** | `database is locked` 미발생 확인 |
| 4 | 서킷 브레이커 동작 확인 | 목 클라이언트로 연속 실패 유도 → open 전환 → 폴백 확인 |
| 5 | 고아 job 정리 확인 | 강제 종료 후 재기동 시 `running` job 이 `failed` 로 바뀌는지 |
| 6 | 정적 자산 캐시 헤더 확인 | 해시 자산 `immutable`, `index.html` `no-cache` |
