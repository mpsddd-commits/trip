# NFR Design Patterns — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - NFR Design (Unit 1/3)
**Created**: 2026-08-13T06:00:00Z
**결정 근거**: `construction/plans/u1-trip-backend-nfr-design-plan.md` Q1~Q16 = 전부 A

---

## 0. 답변 분석에서 검출한 문제 2건

전부 A 로 확정된 답변들을 교차 검증한 결과, **답변만으로는 결정되지 않는 충돌 2건**이 드러났습니다. 설계 결정으로 해소합니다.

### ⚠️ 검출 1 — 동시성이 중첩되어 외부 API 부하가 곱해짐

`Q3=A`(job 동시 3개) × `Q6=A`(job 내부 외부 호출 동시 3~5) 를 그대로 두면
**최대 3 × 5 = 15개의 외부 호출이 동시에** 나갑니다. 네이버 검색 API 에 순간 부하를 주고 레이트 리밋을 유발할 수 있습니다.

→ **ND-17 로 해소**: **전역 외부 호출 세마포어**를 둡니다. job 동시성과 무관하게 API 별 동시 호출을 **최대 5개**로 제한 [설정 `EXTERNAL_CONCURRENCY=5`]. job 내부 병렬도는 이 전역 상한 아래에서만 유효합니다.

### ⚠️ 검출 2 — 동기 DB 드라이버가 이벤트 루프를 막음

`Q2=A`(asyncio 태스크) × `Q5=A`(SQLite) 조합에서, 표준 SQLite 드라이버는 **동기(blocking)** 입니다.
백그라운드 job 이 저장하는 동안 이벤트 루프가 멈추면 **동시에 들어온 API 요청 전체가 지연**됩니다.

→ **ND-18 로 해소**: DB 접근을 **스레드 풀에서 실행**합니다(`run_in_threadpool` 계열). 세션은 스레드 로컬로 관리하고 트랜잭션은 짧게 유지합니다. `aiosqlite` 도입은 하지 않습니다 — SQLAlchemy 동기 API 를 그대로 쓰는 편이 단순하고, 스레드 풀로 충분합니다.

> 이 2건은 사용자 판단 사항이 아니라 답변 조합의 논리적 귀결이므로 추가 질문 없이 설계에 반영했습니다.

---

## 1. 복원력 패턴

### RP-1. 계층형 장애 대응 (NFR-2, NFR-3, SEC-15)

외부 호출 하나에 **4겹**의 방어가 적용됩니다.

```
요청
  |
  v  [1] 서킷 브레이커 (ND-1)
  |     open 상태면 호출하지 않고 즉시 폴백
  |
  v  [2] 전역 세마포어 (ND-17)
  |     API 별 동시 5개 초과 시 대기
  |
  v  [3] 타임아웃 (BR-47)
  |     연결 5초 / 읽기 10초 (LLM 은 120초)
  |
  v  [4] 재시도 (BR-47)
  |     지수 백오프 최대 3회, 4xx 는 재시도 안 함
  |
  v  실패 확정 -> 폴백 (RP-3)
```

### RP-2. 서킷 브레이커 규격 (ND-1, Q1=A)

| 항목 | 값 |
|---|---|
| 적용 대상 | `NAVER_LOCAL` / `NAVER_BLOG` / `NAVER_IMAGE` / `NCP_DIRECTIONS` / `NCP_GEOCODING` / `ANTHROPIC` — **API 별로 독립** |
| open 전환 | 연속 실패 **5회** [설정 `CIRCUIT_FAILURE_THRESHOLD=5`] |
| open 유지 | **60초** [설정 `CIRCUIT_OPEN_SECONDS=60`] |
| half-open | 1회 시도 허용 → 성공 시 closed, 실패 시 다시 open |
| 실패로 세는 것 | 타임아웃, 5xx, 연결 오류 |
| **실패로 세지 않는 것** | 4xx (요청 문제이지 서비스 장애가 아님), 쿼터 소진 |
| 상태 저장 | 인메모리 (프로세스 수명) |
| 전환 시 | `AuditEvent` 기록 + WARN 로그 (SEC-14) |

**해결하는 문제**: 네이버 장애 시 AI 생성 파이프라인이 15개 항목 × 10초 = **150초를 기다리는 상황**을 3~4회 실패 후 즉시 폴백으로 바꿉니다.

### RP-3. API 별 폴백 전략 (NFR-3)

| API | 실패·서킷 open 시 | 결과 |
|---|---|---|
| `NCP_DIRECTIONS` | C17 하버사인 근사 (BR-26) | `is_estimate=true` 부착, 파이프라인 계속 |
| `NAVER_BLOG` / `NAVER_IMAGE` | 빈 목록 (BR-42) | 해당 섹션만 비고 나머지 정상 |
| `NAVER_LOCAL` | 미해결 처리 (BR-16) | job `partial` 또는 `failed` |
| `NCP_GEOCODING` | 좌표 없이 진행 | 해당 기능만 비활성 |
| `ANTHROPIC` | **폴백 없음** | job `failed` — 초안 없이는 파이프라인이 성립하지 않음 |

> **ANTHROPIC 만 폴백이 없는 이유**: 나머지는 "품질 저하"로 흡수되지만 초안은 파이프라인의 입력 그 자체입니다. 이 경우에도 **수동 편집 경로(FR-5~8)는 정상 동작**하므로 제품 전체가 멈추지는 않습니다 (ASM-3).

### RP-4. 백그라운드 작업 복원력 (ND-2, ND-3, Q2=A, Q3=A)

| 패턴 | 내용 |
|---|---|
| 실행 방식 | `asyncio` 태스크, 프로세스 내 (별도 워커·브로커 없음 — UD-8 정합) |
| 동시성 | **전역 3개** [설정 `MAX_CONCURRENT_JOBS=3`]. 초과 시 `queued` 로 대기, `job_id` 는 즉시 반환 |
| **고아 작업 정리** | **기동 시 `running` 상태로 남아 있는 job 을 전부 `failed` 로 전환** — 프로세스가 비정상 종료되면 그 job 은 영원히 `running` 으로 남기 때문 |
| 취소 | 앱 종료 시 실행 중 태스크를 정상 취소하고 job 을 `failed` 로 기록 |
| 재시도 | **제공하지 않음** (ND-4, Q4=A) — `partial` 결과는 이미 저장되어 있고 미해결 장소는 직접 검색해 담을 수 있음 (BR-18) |

### RP-5. Fail-closed 원칙 (SEC-15)

| 상황 | 동작 |
|---|---|
| 저장 실패 | 전체 롤백, `job=failed` (BR-53). 부분 저장 금지 |
| 쿼터 소진 | 호출하지 않고 즉시 거부 (BR-50) |
| 레이트 리밋 초과 | 라우터 진입 전 차단 (BR-49) |
| 예상치 못한 예외 | 전역 핸들러가 포착 → 고정 문구 응답 (BR-58) |
| 검증 실패 | 처리하지 않고 거부 — 부분 수용 없음 |

---

## 2. 확장성·동시성 패턴

### SP-1. SQLite 동시성 (ND-5, Q5=A)

| 설정 | 값 | 이유 |
|---|---|---|
| `journal_mode` | **WAL** | 읽기와 쓰기가 서로를 막지 않음 |
| `busy_timeout` | **5000ms** | 순간 경합 시 즉시 실패 대신 대기 |
| `synchronous` | **NORMAL** | WAL 과 함께 쓰면 안전성 대비 성능이 합리적 |
| `foreign_keys` | **ON** | 참조 무결성 (BR-54 하드 삭제 시 연쇄) |
| 트랜잭션 | **짧게 유지** — 외부 API 호출을 트랜잭션 안에서 하지 않음 | 잠금 시간 최소화 |

### SP-2. DB 접근의 이벤트 루프 격리 (ND-18 — 검출 2 해소)

```
async 라우터 / async job
        |
        v  run_in_threadpool(...)
+---------------------------+
|  스레드 풀                |
|   SQLAlchemy 동기 세션    |
|   짧은 트랜잭션           |
+---------------------------+
        |
        v  SQLite (WAL)
```
**규칙**: `async` 컨텍스트에서 **동기 DB 호출을 직접 하지 않습니다.** 전부 스레드 풀 경유입니다.

### SP-3. 외부 호출 동시성 (ND-6, ND-17, Q6=A)

```
job A ---+
job B ---+---> [전역 세마포어: API 별 최대 5]  ---> httpx.AsyncClient (커넥션 풀 재사용)
job C ---+
```

| 항목 | 값 |
|---|---|
| 클라이언트 | `httpx.AsyncClient` — **앱 수명 동안 단일 인스턴스, 커넥션 풀 재사용** |
| job 내부 병렬도 | 그라운딩 등 독립 호출은 동시 3~5 [설정 `JOB_PARALLELISM=5`] |
| **전역 상한** | **API 별 동시 5** [설정 `EXTERNAL_CONCURRENCY=5`] — job 동시성과 곱해지지 않음 (ND-17) |

**효과 (NFR-1)**: 그라운딩 15건 순차 호출 시 약 7.5초 → 병렬 시 약 2~3초.

### SP-4. 레이트 리밋 상태 배치 (ND-7, Q7=A)

| 대상 | 저장 위치 | 재시작 시 |
|---|---|---|
| IP 단위 슬라이딩 윈도 | **인메모리** | 초기화 (허용) |
| **전역 일일 상한** | **SQLite `ApiUsage`** | **유지** — 재시작으로 비용 통제가 우회되면 안 됨 |

> 이 분리가 핵심입니다. IP 윈도가 초기화되는 것은 감수할 수 있지만, **일일 50회 AI 생성 상한이 재시작으로 리셋되면 상한의 의미가 없습니다.**

### SP-5. 확장 한계의 명시 (SEC-11 오남용 설계)

이 유닛은 **단일 프로세스·단일 컨테이너 전제**입니다 (UD-8). 다중 인스턴스로 확장하면 다음이 깨집니다:

| 항목 | 다중 인스턴스에서 깨지는 이유 |
|---|---|
| IP 레이트 리밋 | 인메모리라 인스턴스별로 따로 셈 |
| 서킷 브레이커 | 인메모리라 인스턴스별 상태 분리 |
| job 동시성 제한 | 프로세스 내 세마포어 |
| SQLite | 파일 잠금 경합 |

→ 확장이 필요해지면 **공유 상태 저장소(Redis)와 PostgreSQL 로의 전환이 선행**되어야 합니다. 현 범위(Q20=A 로컬 배포)에서는 문제가 되지 않으며, **이 한계를 문서화하는 것 자체가 SEC-11 의 "오남용 시나리오 고려" 요건 충족**입니다.

---

## 3. 성능 패턴

### PP-1. 캐시 계층 (NFR-4, DD-15)

```
서비스  --(캐시 존재를 모름)-->  CachingClientDecorator  -->  실제 클라이언트
                                        |
                                        v
                                  SQLite ExternalCache (TTL)
```

| namespace | TTL | 비고 |
|---|---|---|
| `local_search` | 7일 | 가장 호출량이 많음 |
| `directions` | 1일 | 교통 상황 변동 고려 |
| `blog` / `image` | 3일 | |
| `geocode` | 30일 | 주소↔좌표는 거의 불변 |
| (LLM) | **캐시 안 함** | 동일 입력에도 다른 출력이 유효 |

**키 정규화**: BR-48 (NFC → 소문자 → 공백 축약, 좌표 5자리 반올림, SHA-256)

### PP-2. 외부 호출 절감 (BR-28)

| 상황 | 호출 수 |
|---|---|
| 순진한 구현 (모든 쌍 Directions) | `O(n²)` — 15개 항목이면 210회 |
| **본 설계** | **`O(n)`** — 인접 14회 + 최적화 후 재조회 최대 14회 |

비인접 쌍은 하버사인 근사로 채워 최적화 탐색에만 사용하고, 순서 확정 후 새 인접 쌍만 실호출합니다.

### PP-3. 정적 자산 캐시 (ND-8, Q8=A)

| 대상 | 헤더 |
|---|---|
| 해시 파일명 자산 (`assets/*.[hash].js|css`) | `Cache-Control: public, max-age=31536000, immutable` |
| `index.html` | `Cache-Control: no-cache` |
| API 응답 | `Cache-Control: no-store` (개인 일정 데이터) |

Vite 가 파일명에 콘텐츠 해시를 넣으므로 영구 캐시가 안전하고, 진입점만 매번 검증하면 재배포 반영이 보장됩니다.

### PP-4. 응답 압축 (ND-9, Q9=A)

**1KB 초과 응답에 gzip 적용.** 경로 좌표열(`TravelLeg.path`)이 가장 큰 수혜 대상입니다.

### PP-5. 성능 관측 (ND-10, Q10=A)

요청마다 구조화 로그에 기록:
```
{correlation_id, method, path, status, duration_ms, external_calls, cache_hits, db_queries}
```
- P95 목표(500ms, NFR-1) 초과 시 **WARN 레벨**로 승격
- 별도 메트릭 백엔드 도입하지 않음 (SEC-14 축소 적용과 정합)
- job 은 단계별 소요시간을 별도 기록

---

## 4. 보안 패턴

### SEP-1. 보안 헤더 (ND-11, Q11=A, SEC-04)

| 헤더 | 값 |
|---|---|
| `Content-Security-Policy` | 아래 §4.1 |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` — **HTTPS 요청에만 부여** (CA-4) |

#### 4.1 CSP 기준선

```
default-src  'self';
script-src   'self' https://oapi.map.naver.com;
style-src    'self' 'unsafe-inline';
img-src      'self' data: https:;
connect-src  'self' https://*.map.naver.com;
font-src     'self' data:;
object-src   'none';
base-uri     'self';
frame-ancestors 'none';
```

**`unsafe-inline` 예외 문서화 (SEC-04 검증 요건)**
- **`style-src` 에만** 허용합니다. 네이버 지도 SDK 가 마커·컨트롤에 인라인 스타일을 주입하므로 제거하면 지도가 깨집니다
- **`script-src` 에는 절대 허용하지 않습니다.** `unsafe-eval` 도 사용하지 않습니다
- `img-src` 에 `https:` 를 넓게 허용하는 이유: 지도 타일과 네이버 이미지 검색 결과의 호스트가 다양하고 고정적이지 않습니다. 스크립트 실행 권한이 아니므로 위험도가 낮습니다

> ⚠️ **Build & Test 검증 항목**: 지도 SDK 를 실제 로드해 **CSP 위반이 콘솔에 뜨지 않는지 확인**하고, 필요한 도메인을 실측으로 확정합니다. 위 목록은 기준선입니다.

### SEP-2. CORS (ND-12, Q12=A, SEC-08)

| 환경 | 정책 |
|---|---|
| 운영 (UD-8 단일 오리진) | **CORS 미들웨어 비활성** — 동일 오리진이라 불필요 |
| 개발 | `CORS_ALLOW_ORIGINS` 에 **명시된 오리진만** (예: `http://localhost:5273`) |
| 금지 | **와일드카드 `*` 는 어떤 환경에서도 사용하지 않음** |

단일 오리진 구성(UD-8) 덕분에 CORS 가 구조적으로 필요 없어졌고, 이것이 SEC-08 준수를 단순하게 만듭니다.

### SEP-3. 인증 정보 관리 (ND-13, Q13=A, SEC-12)

```
환경변수 / .env (git 제외)
        |
        v  C1 Config — pydantic-settings 로 타입 검증
        |
        +--> credential_status  -->  C13 ClientFactory  -->  실제 또는 목 구현
        |
        +--> SecretStr 로 보관 (repr/str 에 노출 안 됨)
```

| 규칙 | 내용 |
|---|---|
| 저장 | 환경변수 + `.env`(git 제외) + `.env.example` 템플릿 |
| 검증 | 기동 시 형식 확인. **누락은 오류가 아니라 목 모드 전환** (FR-33) |
| 노출 | 로그·오류 응답·`__repr__`·`/health` 어디에도 값 미노출. **어떤 API 가 목 모드인지만** 표기 |
| 마스킹 | C2 로깅 필터가 키 패턴을 마스킹 (SEC-03) |
| 하드코딩 | 소스·설정 파일에 **일절 금지** |

### SEP-4. 입력 검증 다층화 (SEC-05)

| 계층 | 검증 |
|---|---|
| 미들웨어 | 요청 본문 크기 상한 1MB |
| 스키마 (C33) | 타입·길이·범위·형식 |
| 도메인 (C14) | 좌표 국내 범위, 시각 순서, 비음수 (BR-15) |
| 저장 (C30) | **파라미터 바인딩만** — 문자열 연결 금지 |
| 외부 데이터 | 지역검색 `title` HTML 태그 제거 (BR-14), LLM 응답 스키마 검증 (BR-07) |

**외부에서 들어온 데이터도 신뢰하지 않습니다.** 네이버 응답과 LLM 응답 모두 검증 대상입니다.

### SEP-5. 접근 제어 (SEC-08)

| 패턴 | 구현 |
|---|---|
| 자원 식별 | UUIDv4 — 순차 ID 없음 |
| 공유 분리 | `share_token` 은 독립 난수, 읽기 전용 타입 반환 (BR-36, BR-37) |
| **열거 차단** | **목록 API 미제공** (BR-39) |
| 경로 선언 | 전 경로를 명시적 public 으로 표기 (계정 없음 — CA-2) |
| CORS | 화이트리스트 (SEP-2) |

### SEP-6. 감사·모니터링 (ND-14, SEC-13, SEC-14)

| 항목 | 내용 |
|---|---|
| 감사 대상 | 여행 생성·수정·삭제, 공유 토큰 발급·폐기, 레이트 리밋 초과, 쿼터 소진, 외부 인증 실패, LLM 스키마 거부, **서킷 브레이커 전환** |
| 저장 | `AuditEvent` — **추가 전용**(수정·삭제 연산 미정의) |
| 보존 | **90일** |
| 로그 파일 | 일 단위 로테이션, 90일 보관 |
| 미포함 | 인증 정보, 좌표 원문, 요청 본문 전체 |

### SEP-7. 헬스체크 (ND-14, Q14=A, FR-34)

| 엔드포인트 | 내용 | 외부 호출 |
|---|---|---|
| `GET /api/health` | liveness — 프로세스 응답만. 항상 200 | **없음** |
| `GET /api/health/ready` | readiness — DB 접근 확인 + 목 모드 현황 + 쿼터 사용량 + 서킷 상태 | **없음** |

> **헬스체크가 외부 API 를 호출하지 않는 이유**: 컨테이너 헬스체크는 주기적으로 실행됩니다. 여기서 지역검색을 호출하면 **헬스체크만으로 일일 쿼터를 소모**합니다.

---

## 5. 논리 컴포넌트 구성

### LC-1. 미들웨어 순서 (ND-15, Q15=A)

```
요청
  |
  v  (1) ErrorHandler          <- 가장 바깥. 어디서 터져도 Problem Details
  v  (2) CorrelationId         <- 이후 모든 로그에 ID 부착
  v  (3) AccessLog             <- 처리시간 측정 시작
  v  (4) SecurityHeaders       <- 응답 경로에서 헤더 부여
  v  (5) GZip                  <- 1KB 초과 압축
  v  (6) CORS (개발 시에만)
  v  (7) BodySizeLimit         <- 1MB 초과 거부
  v  (8) RateLimit             <- 등급별 차단
  v  (9) Router + Schema       <- 검증 후 서비스 호출
```

**순서 근거**
- **(1) 이 가장 바깥**: (2)~(8) 어느 미들웨어에서 예외가 나도 사용자는 고정 문구를 받습니다 (BR-58, SEC-15)
- **(2) 가 (3) 앞**: 접근 로그에도 correlation ID 가 붙습니다
- **(8) 이 (9) 바로 앞**: 차단된 요청은 스키마 검증·비즈니스 로직에 닿지 않아 자원을 쓰지 않습니다
- **(7) 이 (8) 앞**: 거대 본문은 레이트 리밋 계산 전에 잘라냅니다

### LC-2. 정리 스케줄러 (ND-16, Q16=A, BR-60)

`asyncio` 주기 태스크를 앱 수명 주기에 연결합니다.

| 시점 | 작업 |
|---|---|
| 기동 시 1회 | **고아 job 정리**(`running` → `failed`) + job/캐시 정리 |
| 24시간마다 | 완료 job 24시간 경과분 삭제, 캐시 만료+7일 경과분 삭제, 감사 로그 90일 경과분 삭제 |
| 종료 시 | 태스크 정상 취소 |

외부 스케줄러·cron·APScheduler 를 도입하지 않습니다 (UD-8 단일 컨테이너).

---

## 6. NFR 커버리지

| NFR | 적용 패턴 | 상태 |
|---|---|---|
| NFR-1 응답시간 | SP-3(병렬), PP-1(캐시), PP-2(호출절감), BR-22(200ms 상한), PP-5(관측) | ✅ |
| NFR-2 타임아웃 | RP-1 | ✅ |
| NFR-3 재시도·degrade | RP-1, RP-2, RP-3 | ✅ |
| NFR-4 캐시·쿼터 | PP-1, PP-2, SP-4 | ✅ |
| NFR-5 반응형 | ⚪ u2 소관 | N/A |
| NFR-6 접근성 | ⚪ u2 소관 | N/A |
| NFR-7 시간대 | 저장 UTC / 계산·표시 KST (WF-6) | ✅ |
| NFR-8 구조화 로깅 | PP-5, SEP-6 | ✅ |
| NFR-9 재현 가능 빌드 | ⏭ Infrastructure Design | ⏭ |
| NFR-10 네트워크 비의존 테스트 | C13 목 주입 (DD-3), 서킷·세마포어는 목에 미적용 | ✅ |
| NFR-11 볼륨 보존 | ⏭ Infrastructure Design | ⏭ |
| NFR-12 번들 크기 | PP-3, PP-4 (u2 와 공동) | ✅ |
| NFR-13 포트 8200 | ⏭ Infrastructure Design | ⏭ |
| NFR-14 `BIND_HOST` | ⏭ Infrastructure Design (C1 이 경고 로그 담당) | ⏭ |
| NFR-15 환경변수 주입 | SEP-3 | ✅ |

**미처리 NFR: 0건** ✅ (N/A 2건, Infrastructure Design 이월 4건)

---

## 7. Compliance 요약 — NFR Design (u1)

### Security Compliance

| Rule | 판정 | 구현 지점 |
|---|---|---|
| SEC-01 | ✅ | RP-1(TLS 강제) / SP-1(파일 권한은 Infra) |
| SEC-02 | ⚪ N/A | 중간자 없음 |
| SEC-03 | ✅ | SEP-6, PP-5, SEP-3(마스킹) |
| SEC-04 | ✅ | **SEP-1 + CSP §4.1** — `unsafe-inline` 은 style 에만, 사유 문서화 |
| SEC-05 | ✅ | SEP-4 다층 검증 |
| SEC-06 | ⚪ N/A | IAM 없음 |
| SEC-07 | ⏭ | Infrastructure Design (`BIND_HOST`, 포트) |
| SEC-08 | ✅ | SEP-2(CORS), SEP-5(UUID·토큰·열거 차단) |
| SEC-09 | ✅ | BR-58 고정 문구, 디렉터리 리스팅 비활성(LC-1) |
| SEC-10 | ⏭ | Infrastructure Design (버전 고정·스캔·SBOM) |
| SEC-11 | ✅ | RP-2·RP-4·SP-3·SP-4(레이트 리밋), **SP-5(오남용·확장 한계 문서화)** |
| SEC-12 | ✅ | SEP-3 (사용자 인증은 N/A) |
| SEC-13 | ✅ | SEP-4(LLM 응답 검증), SEP-6(감사) |
| SEC-14 | ✅ | SEP-6 (추가 전용·90일·보안 이벤트 알림 로깅) |
| SEC-15 | ✅ | RP-5 fail-closed, LC-1 전역 핸들러, SP-2(세션 정리) |

**Blocking security findings: 0건** ✅ (⏭ 2건은 Infrastructure Design 소관)

### PBT Compliance
본 스테이지는 런타임 패턴을 다루며 순수 함수를 새로 만들지 않습니다.
PBT-02·03·07·09 는 Functional Design 에서 충족, **PBT-08(셰링킹·시드)은 Code Generation 소관**.
**Blocking PBT findings: 0건** ✅

### Resiliency
확장 없음(사용자 opt-out). 단 RP-1~RP-5 로 재시도·타임아웃·서킷·폴백·fail-closed 를 자체 반영했습니다.
