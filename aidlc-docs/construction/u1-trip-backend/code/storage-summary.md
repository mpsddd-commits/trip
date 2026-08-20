# Storage 계층 구현 요약 — u1-trip-backend

**Stage**: 🟢 CONSTRUCTION - Code Generation Part 2 (Step 8)
**Created**: 2026-08-13T07:20:00Z
**대상 단계**: Step 6(생성) · Step 7(테스트)

---

## 1. 생성 파일

| 파일 | 컴포넌트 | 핵심 구현 |
|---|---|---|
| `app/storage/database.py` | **C30** | 엔진 생성, **PRAGMA 4종**(WAL / busy_timeout 5000 / synchronous=NORMAL / foreign_keys=ON), `session_scope` 트랜잭션 경계 |
| `app/storage/db_executor.py` | **L4** | 전용 스레드 풀. `async` 에서 동기 DB 를 직접 호출하지 않게 하는 유일한 통로 (ND-18) |
| `app/storage/models.py` | — | ORM **12 테이블** + 인덱스 5 + 유니크 제약 3 |
| `app/storage/repositories.py` | **C31** | 리포지토리 5종 |
| `app/storage/migrations.py` | — | `create_all` + `schema_version` 테이블 |
| `tests/unit/test_repositories.py` | — | 예제 테스트 **11건** |
| `tests/unit/test_audit_append_only.py` | — | **구조 검증 3건** |

**Step 6~7 생성 파일: 7개** (누적 40개)

---

## 2. 테이블 12종

| 테이블 | 엔티티 | 주요 제약 |
|---|---|---|
| `trips` | Trip | `share_token` **UNIQUE + 인덱스** (BR-36) |
| `trip_days` | TripDay | `(trip_id, day_index)` UNIQUE |
| `places` | Place | `(latitude, longitude)` 인덱스 (중복 판정용, BR-17) |
| `opening_hours` | OpeningHours | `place_id` PK. **레코드 없음이 정상 상태** (BR-35) |
| `itinerary_items` | ItineraryItem | `(day_id, position)` UNIQUE |
| `travel_legs` | TravelLeg | `day_id` 인덱스 |
| `unresolved_candidates` | UnresolvedCandidate | `trip_id` 인덱스 |
| `place_contents` | PlaceContent | `place_id` PK |
| `generation_jobs` | GenerationJob | `state` 인덱스 (고아 복구용) |
| `external_cache` | ExternalCache | `namespace`·`expires_at` 인덱스 |
| `api_usage` | ApiUsage | `(api_name, usage_date)` 복합 PK, **KST 일자** |
| `audit_events` | AuditEvent | `occurred_at`·`event_type` 인덱스 |

**연쇄 삭제 (BR-54)**: `trips` → `trip_days` → `itinerary_items` / `travel_legs`, `trips` → `unresolved_candidates`, `places` → `opening_hours` / `place_contents`
**의도적 비연쇄**: `places` 는 여행 삭제로 사라지지 않는다. 다른 여행에서 재사용될 수 있기 때문.

---

## 3. 설계 규칙이 코드 구조로 남은 지점

### BR-39 / SEC-08 — 열거 차단
`TripRepository` 에 `list_all` · `find_all` · `search` 류 메서드를 **정의하지 않았습니다.**
`test_no_list_all_method_exists` 가 `dir(TripRepository)` 를 직접 검사하므로, 나중에 누가 편의를 위해 추가하면 테스트가 실패합니다.

### SEC-14 / BR-59 — 감사 로그 추가 전용
`AuditLogRepository` 의 공개 메서드는 정확히 **`append` / `count` / `recent` / `purge_older_than` 4개**입니다.
`test_audit_append_only.py` 는 두 가지를 검증합니다.
1. 금지 메서드명 9종이 존재하지 않음
2. `purge_older_than` 의 인자가 **`days` 하나뿐** — 개별 이벤트를 지목할 수 있는 인자를 받으면 실패

### SP-4 — 비용 통제의 영속성
`QuotaRepository` 는 카운터를 SQLite 에 씁니다. `test_quota_counter_persists_across_sessions` 가 세션을 닫았다 다시 열어도 값이 유지되는지 확인합니다. **재시작으로 일일 상한이 리셋되면 상한의 의미가 없기** 때문입니다.

### RP-4 — 고아 job 복구
`recover_orphans` 는 `running` **과 `queued`** 를 모두 대상으로 합니다. 계획서에는 `running` 만 적혀 있었으나, 대기 상태 job 도 프로세스가 죽으면 실행될 주체가 사라지므로 동일하게 고아입니다. (범위 확대 — §5 조정 1)

---

## 4. 동시성 처리 (SP-1, SP-2)

```
async 라우터 / async job
        |
        v  await db_executor.run(sync_fn, ...)
+---------------------------------+
|  ThreadPoolExecutor (prefix=db) |
|    with db.session_scope():     |
|        repo.xxx(...)            |
+---------------------------------+
        |
        v  SQLite (WAL, busy_timeout 5s)
```

**세션 규칙**: `session_scope()` 안에서 **외부 API 를 호출하지 않습니다.** 잠금 시간이 길어지면 WAL 의 이점이 사라집니다.

---

## 5. 설계 대비 조정 (2건)

| # | 조정 | 사유 | 위반 여부 |
|---|---|---|---|
| 1 | `recover_orphans` 대상에 `queued` 포함 | 대기 job 도 프로세스 종료 시 고아가 된다 | ❌ 아님 — RP-4 의도에 부합 |
| 2 | `TripRepository` 에 명시적 `update` 메서드 없음 | SQLAlchemy 세션 내 객체 변경으로 갱신한다. 별도 메서드는 중복 | ❌ 아님 |

---

## 6. 미검증 항목

| # | 항목 | 해소 시점 |
|---|---|---|
| 1 | 테스트 실행 결과 (14건) | Build & Test |
| 2 | **WAL 모드에서 job 쓰기 + API 읽기 동시성** | Build & Test I-3 (NFR Design 예약 항목) |
| 3 | 파일 기반 SQLite 의 PRAGMA 실제 적용 여부 | Build & Test — 인메모리에서는 WAL 이 무시된다 |

---

## 7. Compliance — Step 6~8

**Security**
- SEC-05 ✅ ORM 파라미터 바인딩만 사용. 문자열 연결 SQL 0건
- SEC-08 ✅ 목록 메서드 부재 + 구조 테스트
- SEC-13 ✅ 감사 로그 append 경로
- SEC-14 ✅ 추가 전용 구조 + 90일 정리
- SEC-15 ✅ `session_scope` try/except/finally, 예외 시 롤백
**Blocking findings: 0건**

**PBT**: storage 는 I/O 계층으로 순수 함수가 없어 **PBT 비대상**. 예제 기반 테스트로 검증 (PBT-10).
**Blocking findings: 0건**
