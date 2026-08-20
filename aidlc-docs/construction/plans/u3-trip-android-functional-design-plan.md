# Functional Design Plan — u3-trip-android

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 3/3, 마지막 유닛)
**Created**: 2026-08-14T20:00:00Z
**Prior context**: u1·u2 구현 완료. 브리지 계약 5종 확정, 웹 호스팅 URL 확정
**Unit 책임**: A1~A7 (7 컴포넌트) · Owner FR 4건(FR-27·28·29·30) · 참여 FR 3건(FR-12·23·24)
**Status**: ⛔ 답변 대기 중

---

## 📌 답변 방법

`[Answer]:` 태그 뒤에 알파벳을 적어주세요. **"완료"** 또는 **"전부 추천안"** 이라고 알려주시면 산출물 3종을 생성합니다.

---

## 🔴 u2 코드를 대조하며 발견한 문제 3건 — 답변 전 꼭 읽어주세요

세 건 모두 **"WebView 는 브라우저가 아니다"** 에서 옵니다. 웹에서 되는 것이 앱에서 조용히 안 됩니다.

### 문제 1. 안드로이드 9 이상은 평문 HTTP 를 차단합니다

CA-1 로 확정한 안드로이드 접속 주소는 **`http://10.0.2.2:8200`**(에뮬레이터) / `http://<LAN IP>:8200`(실기기)입니다.
그런데 **Android 9(API 28)부터 평문 HTTP 가 기본 차단**됩니다. 아무 조치 없이 빌드하면
앱이 백엔드에 접속하지 못하고 **빈 화면만 뜹니다.**

허용 방법은 두 가지이고 위험도가 다릅니다.

| 방법 | 범위 | 위험 |
|---|---|---|
| `android:usesCleartextTraffic="true"` | **모든 도메인** | 릴리스 빌드에도 남으면 어떤 평문 통신이든 허용 |
| `network_security_config.xml` 도메인 한정 | `10.0.2.2` 등 **개발 주소만** | 릴리스에서는 평문 전면 차단 유지 |

→ **Q3 에서 결정합니다.**

### 문제 2. `.ics` 내보내기가 앱에서 동작하지 않습니다

u2 의 `TripHeader` 는 `<a href="/api/trips/.../export.ics" download>` 로 캘린더를 내려받습니다.
**WebView 는 다운로드를 스스로 처리하지 않습니다.** `DownloadListener` 를 붙이지 않으면
버튼을 눌러도 **아무 일도 일어나지 않습니다.** (오류도 나지 않아 원인을 찾기 어렵습니다)

→ FR-26 이 앱에서 무력화됩니다. **Q5 에서 결정합니다.**

### 문제 3. 딥링크 **웹 폴백**이 앱에서 동작하지 않습니다

u2 의 `shared/bridge/index.ts` 는 네이티브 브리지가 없을 때 `window.open(webUrl)` 로 폴백합니다.
그런데 **WebView 는 `setSupportMultipleWindows(true)` + `onCreateWindow` 구현이 없으면 `window.open` 을 무시**합니다.

앱에서는 브리지가 있으니 이 경로를 타지 않는 게 정상이지만, **브리지 전달이 실패하면
사용자는 아무 반응도 못 봅니다.** 또 u2 가 앱 안에서 다른 이유로 `window.open` 을 쓰게 되면 같은 문제가 생깁니다.

→ **Q6 에서 결정합니다.**

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [ ] u2 의 브리지 계약 5종(`openMap`/`share`/`requestLocation` ↔ `locationResult`/`bridgeReady`) 확인
- [ ] Owner FR 4건 + 참여 FR 3건의 앱 측 책임 확정
- [ ] A1~A7 컴포넌트 책임 재확인
- [ ] SEC 주 책임 2건(SEC-09 하드닝, SEC-08 오리진) · 부분 2건 확인

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [ ] Q1~Q3 빌드 구성과 네트워크 정책
- [ ] Q4~Q7 WebView 동작과 하드닝
- [ ] Q8~Q11 브리지 구현
- [ ] Q12~Q14 화면·권한·오류

### 1.3 필수 산출물 생성
- [ ] `construction/u3-trip-android/functional-design/domain-entities.md` — 앱 상태·설정
- [ ] `construction/u3-trip-android/functional-design/business-logic-model.md` — 흐름·**Testable Properties**
- [ ] `construction/u3-trip-android/functional-design/business-rules.md` — ABR-xx + FR 추적

### 1.4 검증
- [ ] Owner FR 4건 전부 규칙으로 표현
- [ ] 브리지 계약 5종의 앱 측 처리 명세
- [ ] Security / PBT Compliance 요약 (**u3 는 PBT N/A** — 근거 명시)

---

## Part 2. 설계 질문

### 📦 빌드 구성과 네트워크 정책

## Question 1
**최소 지원 SDK(minSdk)** 를 무엇으로 합니까?

A) ⭐ **API 26 (Android 8.0)** — `WebViewCompat.addWebMessageListener` 가 안정적으로 동작하고(Q15=A / DD-19),
　국내 기기 커버리지가 사실상 전부입니다. targetSdk 는 35

B) API 21 (Android 5.0) — 커버리지는 넓으나 구형 WebView 대응 코드가 늘어납니다

C) API 30 이상 — 코드는 가장 단순하나 구형 기기를 버립니다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
**접속 주소(`BASE_URL`)** 를 어떻게 주입합니까? (CA-1, FR-27)

A) ⭐ **`gradle.properties` → `BuildConfig.BASE_URL`, 빌드 변형별 기본값** —
　`debug` = `http://10.0.2.2:8200`(에뮬레이터), `release` = 빈 값(빌드 시 반드시 지정).
　실기기는 `-PbaseUrl=http://<LAN IP>:8200` 으로 덮어씁니다
　→ 소스에 주소를 박지 않고, 릴리스에 개발 주소가 섞이지 않습니다

B) 앱 내 설정 화면에서 사용자가 입력 — 유연하지만 화면·저장소가 늘고, 오입력 시 원인 파악이 어렵습니다

C) 소스에 상수로 하드코딩

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
🔴 **문제 1 참조**: 평문 HTTP 차단을 어떻게 풉니까?

A) ⭐ **`network_security_config.xml` 로 개발 주소만 허용 + debug 빌드에만 적용** —
　`10.0.2.2`·`localhost`·사설 IP 대역만 평문 허용하고, **release 빌드는 평문 전면 차단** 유지.
　`usesCleartextTraffic` 은 쓰지 않습니다
　→ 개발은 되고, 릴리스에는 구멍이 남지 않습니다 (CON-5 의 "운영은 TLS 필수"와 정합)

B) `android:usesCleartextTraffic="true"` — 한 줄로 끝나지만 **모든 도메인**에 적용되고 릴리스에도 남습니다

C) 개발에도 TLS 를 도입 — 자체 서명 인증서 신뢰 설정이 필요해 부담이 큽니다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🌐 WebView 동작과 하드닝

## Question 4
**WebView 하드닝 수준**은? (SEC-09, A2)

A) ⭐ **필요한 것만 켜고 나머지는 끈다** —
　JavaScript ✅ / DOM Storage ✅(오프라인 캐시에 필요) / **파일 접근 ❌** /
　**콘텐츠 프로바이더 접근 ❌** / 혼합 콘텐츠 ❌ / 지오로케이션은 **브리지로만**(WebView 권한 대화상자 미사용) /
　**허용 오리진 밖 내비게이션 차단**(외부 링크는 시스템 브라우저로)
　→ 공격면을 최소화하면서 u2 가 필요로 하는 기능은 전부 제공합니다

B) 기본 설정 + JavaScript 만 활성 — 오프라인 캐시(IndexedDB)가 동작하지 않습니다

C) 전부 허용 (⚠️ SEC-09 위반)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
🔴 **문제 2 참조**: `.ics` 다운로드(FR-26)를 어떻게 처리합니까?

A) ⭐ **`DownloadListener` + 시스템 `DownloadManager`** — WebView 가 다운로드를 감지하면
　`DownloadManager` 에 넘겨 알림과 함께 저장하고, 완료 시 캘린더 앱으로 열 수 있게 합니다
　→ 사용자가 익숙한 방식이고 저장 위치도 명확합니다

B) **인텐트로 시스템 브라우저에 위임** — 구현은 가장 간단하지만 앱 밖으로 나가고,
　백엔드가 루프백 바인딩이면 브라우저에서 접근이 안 될 수 있습니다

C) 미지원 — 앱에서는 `.ics` 버튼이 동작하지 않는 채로 둡니다 (⚠️ FR-26 무력화)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
🔴 **문제 3 참조**: `window.open` 을 어떻게 다룹니까?

A) ⭐ **`setSupportMultipleWindows(true)` + `onCreateWindow` 에서 URL 을 가로채 시스템 브라우저로** —
　새 창을 만들지 않고 **URL 만 추출해 인텐트로 넘깁니다.** 브리지가 실패해도 사용자가 반응을 봅니다
　→ 딥링크 웹 폴백(FR-24)의 최후 경로가 앱에서도 살아 있습니다

B) 무시 — 브리지가 있으니 이 경로는 안 탄다고 가정 (⚠️ 브리지 실패 시 무반응)

C) WebView 안에서 새 창을 실제로 띄운다 — 뒤로가기·수명 관리가 복잡해집니다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
**외부 링크**(블로그 후기·이미지 출처 등)를 어떻게 엽니까?

A) ⭐ **허용 오리진 밖은 시스템 브라우저로** — `shouldOverrideUrlLoading` 에서 호스트를 검사해
　우리 서버가 아니면 인텐트로 넘깁니다. WebView 안에 외부 페이지를 띄우지 않습니다
　→ SEC-08(오리진 제한)과 정합하고, 외부 페이지가 브리지에 닿지 않습니다

B) WebView 안에서 연다 (⚠️ 외부 페이지가 앱 컨텍스트에 들어옵니다)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔌 브리지 구현

## Question 8
**브리지 방식**을 확정합니다. (DD-19 / Q15=A 에서 이미 방향은 정해졌습니다)

A) ⭐ **`WebViewCompat.addWebMessageListener` + 허용 오리진 목록**, 미지원 기기는 `@JavascriptInterface` 폴백.
　폴백 시에도 A2 가 **허용 오리진 밖 내비게이션을 차단**하므로 노출 범위가 같습니다

B) `@JavascriptInterface` 만 사용 — 구현은 단순하나 **로드되는 모든 페이지에 브리지가 노출**됩니다

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 9
u2 는 네이티브 응답을 `window.__tripBridgeReceive(payload)` 로 받습니다. **앱은 어떻게 호출**합니까?

A) ⭐ **`evaluateJavascript` 로 호출하되 payload 를 JSON 문자열로 안전하게 인코딩** —
　문자열 이스케이프를 직접 하지 않고 `JSONObject.quote` 로 감쌉니다
　→ 장소 이름에 따옴표·개행이 있어도 JS 구문이 깨지지 않습니다

B) 문자열 연결로 직접 조립 (⚠️ 이스케이프 실수 시 JS 오류 또는 주입)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
**네이버지도 앱 미설치 판정**(FR-24)을 어떻게 합니까?

A) ⭐ **인텐트 실행을 시도하고 `ActivityNotFoundException` 이면 웹 URL 로 폴백** —
　`queryIntentActivities` 로 미리 조회하는 방식은 Android 11+ 의 패키지 가시성 제한 때문에
　`<queries>` 선언이 필요하고, 선언을 빠뜨리면 **설치돼 있어도 없다고 판정**됩니다
　→ 예외 처리 방식이 더 견고합니다. 다만 `<queries>` 도 함께 선언해 둡니다

B) `queryIntentActivities` 로 사전 조회 (⚠️ `<queries>` 누락 시 오판)

C) 항상 웹으로 (⚠️ FR-23 무력화)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
**위치 권한**(FR-28)을 언제 요청합니까?

A) ⭐ **웹이 `requestLocation` 을 보낼 때만** — 앱 시작 시 미리 묻지 않습니다.
　거부되면 **오류가 아니라 `denied: true` 로 응답**하고, 웹은 해당 기능만 비활성합니다
　→ 맥락 없는 권한 요청은 거부율이 높고, 거부가 앱을 막으면 안 됩니다

B) 앱 첫 실행 시 미리 요청

C) 위치 기능 미지원

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 📱 화면·오류

## Question 12
**오프라인 화면**(FR-30)을 언제 띄웁니까?

A) ⭐ **최초 로드 실패 시에만 전체 화면** — 이미 웹이 로드된 뒤의 네트워크 단절은
　**u2 의 `OfflineGate` 가 처리**합니다(저장된 일정 조회 가능). 앱이 덮으면 그 기능을 가립니다
　→ 두 계층이 같은 일을 두 번 하지 않게 합니다

B) 네트워크가 끊길 때마다 전체 화면 (⚠️ u2 의 오프라인 조회를 가림)

C) 오프라인 화면 없음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13
**뒤로가기**(FR-29) 동작은?

A) ⭐ **WebView 히스토리 우선 소비, 없으면 앱 종료.** 단 최상위 화면에서는
　**한 번 더 누르면 종료** 안내(토스트)를 띄웁니다
　→ 실수로 앱이 닫히는 것을 막습니다

B) 히스토리 우선, 없으면 즉시 종료

C) 항상 앱 종료

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**앱이 자체 UI 를 얼마나 갖습니까?**

A) ⭐ **거의 없음 — WebView 전체 화면 + 오류 화면 + 로딩 표시만** —
　툴바·네비게이션을 만들지 않습니다. 웹이 이미 헤더와 라우팅을 갖고 있어 중복입니다
　→ UD-5(런타임 URL 의존)의 취지대로 웹을 재배포해도 앱을 다시 만들 필요가 없습니다

B) 네이티브 툴바 + 뒤로/새로고침 버튼 추가

C) 네이티브 하단 탭 등 본격적인 셸

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

**"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.

> ⚠️ **Q3·Q5·Q6 은 특히 검토해 주세요.**
> 셋 다 **"웹에서는 되는데 앱에서만 조용히 안 되는"** 문제입니다.
> 오류도 나지 않아 Build & Test 에서도 놓치기 쉽고, 실기기에서야 드러납니다.
