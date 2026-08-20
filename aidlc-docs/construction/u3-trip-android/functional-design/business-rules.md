# Business Rules — u3-trip-android

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 3/3)
**Created**: 2026-08-14T20:20:00Z
**규칙 접두사**: `ABR-` (Android Business Rule) — u1 의 `BR-`, u2 의 `WBR-` 과 구분

---

## 1. 빌드·설정 (ABR-01 ~ ABR-05)

| ID | 규칙 | 근거 |
|---|---|---|
| **ABR-01** | `BASE_URL` 은 `gradle.properties` / `-PbaseUrl` 로만 주입한다. **Kotlin 소스에 주소 리터럴을 두지 않는다** | Q2=A, SEC-01 |
| **ABR-02** | 🔴 `BuildConfig.BASE_URL` 이 비어 있으면 **WebView 를 로드하지 않고** 설정 오류 화면을 띄운다 | Q2=A. release 기본값이 빈 문자열이므로 주소 지정을 잊으면 여기서 걸린다 |
| **ABR-03** | `BASE_URL` 은 `http://` 또는 `https://` 로 시작하고 파싱 가능한 URL 이어야 한다. 아니면 ABR-02 와 같은 오류 화면 | 잘못된 주소로 인한 무증상 실패 방지 |
| **ABR-04** | `network_security_config.xml` 은 **debug 소스셋에만** 배치한다. release 매니페스트는 이 파일을 참조하지 않는다 | Q3=A. 릴리스에 평문 허용이 새어 나가지 않게 |
| **ABR-05** | 평문 허용 도메인은 **개발 주소로 한정**한다 (`10.0.2.2`, `localhost`, `127.0.0.1`, 주입된 실기기 IP). `<base-config cleartextTrafficPermitted="true">` 를 쓰지 않는다 | Q3=A, SEC-05 |

---

## 2. WebView 하드닝 (ABR-10 ~ ABR-16)

| ID | 규칙 | 근거 |
|---|---|---|
| **ABR-10** | `allowFileAccess`·`allowContentAccess`·`allowFileAccessFromFileURLs`·`allowUniversalAccessFromFileURLs` 를 **모두 `false`** 로 둔다 | Q4=A, SEC-09 |
| **ABR-11** | `mixedContentMode` 는 `NEVER_ALLOW` | SEC-05 |
| **ABR-12** | `domStorageEnabled` 와 `databaseEnabled` 는 `true` | FR-31 오프라인 캐시가 IndexedDB 를 쓴다. 끄면 **저장된 일정이 앱에서만 사라진다** |
| **ABR-13** | 🔴 `setGeolocationEnabled(false)`. 위치는 **브리지 경로로만** 처리한다 | 켜 두면 위치 요청 경로가 둘이 되고 권한 대화상자가 이중으로 뜬다 |
| **ABR-14** | `shouldOverrideUrlLoading` — **허용 오리진 밖의 URL 은 WebView 에서 로드하지 않고** 시스템 브라우저 인텐트로 내보낸다 | Q7=A, SEC-08 |
| **ABR-15** | `onReceivedSslError` 에서 **`proceed()` 를 호출하지 않는다.** 항상 `cancel()` | SEC-05. 인증서 오류를 무시하면 TLS 가 무의미해진다 |
| **ABR-16** | WebView 디버깅(`setWebContentsDebuggingEnabled`)은 **debug 빌드에서만** 켠다 | SEC-13 |

---

## 3. 브리지 (ABR-20 ~ ABR-27)

| ID | 규칙 | 근거 |
|---|---|---|
| **ABR-20** | 🔴 딥링크 URL 을 **앱이 만들지 않는다.** `openMap` 페이로드의 `appUrl`/`webUrl` 을 그대로 실행한다 | DD-11, WBR-28. URL 생성 책임은 u2 의 W13 단독 |
| **ABR-21** | `appUrl` 실행이 `ActivityNotFoundException` 이면 `webUrl` 로 폴백한다. 둘 다 실패하면 **토스트로 알린다** — 조용히 실패하지 않는다 | Q10=A, FR-24 |
| **ABR-22** | `onCreateWindow` 는 새 WebView 를 유지하지 않는다. URL 만 추출해 시스템 브라우저로 넘기고 임시 WebView 를 파기한다 | Q6=A |
| **ABR-23** | `DownloadListener` 는 **허용 오리진의 URL 만** 처리한다 | SEC-08 |
| **ABR-24** | 🔴 다운로드 등록·수행이 실패하면 **시스템 브라우저 폴백**을 제공한다 | **AD-1** — `DownloadManager` 는 시스템 프로세스라 앱의 평문 허용 설정이 적용되지 않는다 |
| **ABR-25** | 브리지가 받는 메시지는 **계약 5종만** 처리한다. 알 수 없는 `type`·잘못된 JSON 은 **무시하고 로그만 남긴다** — 예외를 던지지 않는다 | SEC-11. 예외가 나면 WebView 콜백이 죽는다 |
| **ABR-26** | 🔴 위치 권한 거부는 **오류가 아니다.** `locationResult { denied: true }` 로 회신하고 앱은 정상 동작을 유지한다 | Q11=A, FR-28 |
| **ABR-27** | 모든 `requestLocation` 은 **반드시 회신한다.** 조회 실패·타임아웃(10초)도 `lat/lng = null` 로 회신한다 | 미회신은 u2 를 대기 상태에 묶는다 |

---

## 4. 스레드·수명 (ABR-30 ~ ABR-33)

| ID | 규칙 | 근거 |
|---|---|---|
| **ABR-30** | 🔴 웹으로 보내는 모든 회신은 `webView.post { ... }` 로 **UI 스레드에서** 실행한다 | **AD-2** — WebView API 는 UI 스레드 전용. 브리지 콜백과 권한 콜백은 다른 스레드일 수 있다 |
| **ABR-31** | `evaluateJavascript` 로 넘기는 문자열 값은 **`JSONObject.quote` 로 인코딩**한다. 문자열 연결로 JS 를 조립하지 않는다 | Q9=A, SEC-11. 장소명에 따옴표가 들어가면 스크립트가 깨진다 |
| **ABR-32** | `onDestroy` 에서 WebView 를 부모 뷰에서 떼어내고 `destroy()` 한다. 대기 중인 위치 요청은 폐기한다 | 메모리 누수·죽은 참조 방지 |
| **ABR-33** | `bridgeReady` 는 `onPageFinished` **이후 1회만** 보낸다. 페이지 재로드 시 다시 보낸다 | u2 가 브리지 가용 여부를 이것으로 판정 |

---

## 5. 화면·내비게이션 (ABR-40 ~ ABR-43)

| ID | 규칙 | 근거 |
|---|---|---|
| **ABR-40** | 최초 로드 실패 화면에는 **현재 `BASE_URL` 을 표시**하고 [다시 시도] 를 제공한다 | Q12=A. 실패 원인 1위가 주소 오설정이다 |
| **ABR-41** | 🔴 **최초 로드 이후의 오류는 앱이 화면을 덮지 않는다.** u2 의 `OfflineGate` 가 저장된 일정을 보여준다 | Q12=A, FR-30. 덮으면 오프라인 기능을 가린다 |
| **ABR-42** | 뒤로가기는 **WebView 히스토리 우선**, 최상위에서 2초 내 재입력 시 종료 | Q13=A, FR-29 |
| **ABR-43** | 네이티브 UI 는 **WebView·오류 화면·로딩 표시·토스트**로 제한한다. 툴바·탭·설정 화면을 만들지 않는다 | Q14=A. u2 와 UI 를 이중 관리하지 않는다 |

---

## 6. FR 추적성

### 소유 (u3 가 구현 책임)

| FR | 규칙 |
|---|---|
| **FR-27** WebView 컨테이너 | ABR-01~05, ABR-10~16, ABR-40 |
| **FR-28** 네이티브 브리지 | ABR-25~27, ABR-30~33 |
| **FR-29** 뒤로가기 | ABR-42 |
| **FR-30** 앱 오프라인 동작 | ABR-41 |

### 참여 (u1/u2 소유, u3 가 경로를 제공)

| FR | u3 의 역할 |
|---|---|
| **FR-12** 위치 기반 | 권한 획득·좌표 전달만. 판단은 u2 |
| **FR-23** 지도 앱 연동 | 인텐트 실행만 (ABR-20) |
| **FR-24** 딥링크 폴백 | `webUrl` 폴백 + `onCreateWindow` (ABR-21, ABR-22) |
| **FR-26** `.ics` 내보내기 | `DownloadListener` (ABR-23, ABR-24) |

---

## 7. SEC 추적성

| SEC | 충족 규칙 |
|---|---|
| SEC-01 비밀정보 하드코딩 금지 | ABR-01 |
| SEC-05 전송 구간 보호 | ABR-04, ABR-05, ABR-11, ABR-15 |
| SEC-08 오리진 제한 | ABR-14, ABR-23, 도메인문서 §5 |
| SEC-09 클라이언트 하드닝 | ABR-10~13 |
| SEC-11 주입 방지 | ABR-25, ABR-31 |
| SEC-13 디버그 노출 방지 | ABR-16 |

> **미해당**: SEC-02·03·04(인증/인가 — 앱에 인증 없음), SEC-06·07(서버측), SEC-12(서버 로깅),
> SEC-14·15(u1 소유). 근거는 `security-baseline` 적용표에 이미 기록됨.

---

## 8. PBT 판정

**u3 는 PBT 대상이 아닙니다** (`unit-of-work.md` §4 확정). 순수 계산 로직이 없습니다.
대체 검증은 `business-logic-model.md` §10 의 예제 기반 단위 테스트 5종 + 구조 테스트입니다.

---

## 9. 🔴 실기기 확인 체크리스트 — 자동 검증이 닿지 않는 항목

컨테이너 빌드(CON-6)는 **컴파일·패키징까지만** 검증합니다. 아래는 **APK 를 설치해야 드러나며,
전부 "오류 없이 조용히 아무 일도 안 일어나는" 형태**로 실패합니다.

| # | 확인 방법 | 실패 시 증상 | 관련 규칙 |
|---|---|---|---|
| 1 | 앱 실행 → 일정 목록이 보이는가 | **빈 흰 화면** (평문 차단) | ABR-04, ABR-05 |
| 2 | 일정 상세 → `.ics` 내보내기 | **버튼을 눌러도 무반응** | ABR-23, ABR-24 |
| 3 | 지도에서 "네이버지도로 열기" → 앱 미설치 상태 | **무반응** (`window.open` 무시) | ABR-22 |
| 4 | 네이버지도 설치 상태에서 같은 동작 | 앱이 안 열리고 웹으로 감 | ABR-20, ABR-21 |
| 5 | "내 위치" 사용 → 권한 거부 선택 | **무한 로딩** (미회신) | ABR-26, ABR-27 |
| 6 | 비행기 모드 → 앱 재실행 | 오류 화면이 저장된 일정을 덮음 | ABR-41 |
| 7 | 상세 화면에서 뒤로가기 | 목록이 아니라 앱이 종료됨 | ABR-42 |
| 8 | 따옴표(`"`)가 든 장소명이 있는 일정에서 위치 요청 | 회신이 도착하지 않음 | ABR-31 |

이 목록은 Build & Test 보고서와 `README` 에 그대로 옮깁니다.
