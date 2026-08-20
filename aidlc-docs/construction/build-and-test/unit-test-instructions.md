# Unit Test Execution — trip

**실측 일시**: 2026-08-14

## 실행

```bash
# u1 백엔드 (pytest + Hypothesis)
docker run --rm -v "c:/경로/trip/backend:/app" -w /app python:3.12-slim sh -c \
  "pip install -q -r requirements-dev.txt && python -m pytest"

# u2 웹 (Vitest + fast-check)
docker run --rm -v "c:/경로/trip/web:/app" -w /app node:24-alpine sh -c \
  "npm ci && npx vitest run"

# u3 안드로이드 (JUnit)
docker run --rm -v "c:/경로/trip/android:/workspace" trip-android-build \
  sh -c "gradle --no-daemon testDebugUnitTest"
```

## 실측 결과

| 유닛 | 결과 | 소요 | 비고 |
|---|---|---|---|
| **u1-trip-backend** | ✅ **234 passed / 0 failed** | 80초 | 예제 기반 + PBT |
| **u2-trip-web** | ✅ **79 passed / 0 failed** | 21초 | 구조 테스트 18건 포함 |
| **u3-trip-android** | ✅ **47 passed / 0 failed** | 3초 | PBT N/A, 구조 테스트 포함 |
| **합계** | ✅ **360 passed** | | |

## 리포트 위치

| 유닛 | 경로 |
|---|---|
| u1 | 표준 출력 (`--junitxml` 로 파일 생성 가능) |
| u2 | 표준 출력 |
| u3 | `android/out/test-report/index.html` |

---

## 🔴 이 실행에서 드러난 것

첫 실행에서 **35건 이상이 한꺼번에 실패**했습니다. 원인은 하나였습니다 —
`SensitiveFilter` 가 모든 로그 인자를 문자열로 바꿔서, `%d` 를 쓰는 로그가 예외를 냈습니다.
`Filter` 는 `Handler.emit()` 의 try/except **밖**에서 돌기 때문에 그 예외가
**로그를 호출한 코드까지 그대로 튀어나왔습니다.** httpx 가 요청마다 `%d` 로 상태 코드를 남기므로
사실상 모든 API 테스트가 죽었습니다.

이것을 고치자 남은 실패 11건이 드러났고, 그중 **3건이 추가 실제 결함**이었습니다.
자세한 내용은 `test-results.md` 를 보세요.

**교훈**: 광범위한 실패는 원인이 하나인 경우가 많습니다. 개별 테스트를 손대기 전에
가장 흔한 예외 메시지 하나를 끝까지 따라가는 편이 빠릅니다.

## 테스트가 실패할 때

1. `--tb=short` 로 첫 실패의 전체 트레이스백을 봅니다.
2. **같은 예외 타입이 반복되는지** 먼저 확인합니다 — 공통 원인일 가능성이 높습니다.
3. Hypothesis 실패는 `Falsifying example` 을 그대로 읽습니다. 축소된 반례가 원인을 거의 지목합니다.
4. 속성 테스트가 실패하면 **코드가 틀렸는지 속성이 과했는지**를 먼저 판단하세요.
   양쪽 다 있었습니다 (`test-results.md` §3).
