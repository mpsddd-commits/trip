# Code Generation Plan — u3-trip-android (Part 1)

**Stage**: 🟢 CONSTRUCTION - Code Generation (Unit 3/3, 마지막 유닛)
**Created**: 2026-08-14T20:35:00Z
**Status**: ⛔ 사용자 승인 대기

> 이 문서가 **Code Generation 의 단일 진실 공급원**입니다. Part 2 는 아래 단계를 순서대로 실행합니다.

---

## 0. 유닛 컨텍스트

| 항목 | 값 |
|---|---|
| 코드 위치 | **`trip/android/`** (`aidlc-docs/` 아래 아님) |
| 언어 / 빌드 | Kotlin / Gradle (Kotlin DSL) |
| 컴포넌트 | **A1 ~ A7 (7종)** |
| Owner FR | **FR-27, FR-28, FR-29, FR-30** (4건) |
| 참여 FR | FR-12, FR-23, FR-24, FR-26 |
| 의존 | u2 — **런타임 URL + 브리지 계약만**. u2 의 소스·빌드 산출물을 참조하지 않음 (UD-5) |
| 규칙 | **ABR-01 ~ ABR-43 (26개)** |
| PBT | **N/A** — 대체 예제 기반 단위 테스트 5종 |

### 컴포넌트 → 파일 배정

| ID | 컴포넌트 | 파일 |
|---|---|---|
| **A1** | `MainActivity` | `MainActivity.kt` |
| **A2** | `WebViewConfigurator` | `webview/WebViewConfigurator.kt` |
| **A3** | `BridgeHandler` | `bridge/BridgeHandler.kt` + `bridge/BridgeProtocol.kt` |
| **A4** | `IntentLauncher` | `intent/IntentLauncher.kt` |
| **A5** | `LocationProvider` | `location/LocationProvider.kt` |
| **A6** | `OfflineScreen` | `ui/ErrorScreen.kt` + `res/layout/activity_main.xml` |
| **A7** | `AppConfig` | `config/AppConfig.kt` |

---

## 1. 🔴 착수 전 발견 — u2 코드 대조 결과 3건

Functional Design 승인 후 u2 의 `shared/bridge/` 를 다시 읽어 계약이 실제로 맞물리는지 확인했습니다.

### 발견 A — `bridgeReady` 를 u2 가 소비하지 않습니다

u2 의 `ensureReceiver()` 는 **`requestLocation()` 이 호출될 때 처음으로** `window.__tripBridgeReceive` 를 심습니다.
`onPageFinished` 직후에 `bridgeReady` 를 보내면 그 시점에 **콜백이 아직 없습니다.**
게다가 u2 의 수신부는 `locationResult` 가 아닌 메시지를 그냥 무시합니다 — `bridgeReady` 는 **소비처가 없습니다.**

→ **조치**: `bridgeReady` 는 계약에 남기되, u3 는 **`typeof window.__tripBridgeReceive === 'function'` 가드 안에서만** 호출합니다.
　현 시점 소비처가 없다는 사실을 코드 주석과 계약 문서에 명시합니다. **계약을 임의로 삭제하지 않습니다** — 문서가 단일 진실 공급원이고 u2 가 나중에 쓸 수 있습니다.
　ABR-33 을 "가드 후 전송, 소비처 없음을 인지"로 구체화합니다.

### 발견 B — 브리지 객체의 모양은 두 경로가 동일합니다 ✅

u2 는 `window.tripBridge.postMessage(string)` 하나만 봅니다 (`isNative()`).
- `addWebMessageListener(webView, "tripBridge", origins, listener)` → `window.tripBridge.postMessage` 주입 ✅
- `addJavascriptInterface(obj, "tripBridge")` + `@JavascriptInterface fun postMessage(s: String)` → 동일 모양 ✅

**두 경로가 u2 입장에서 구분되지 않습니다.** 폴백이 정상 동작합니다. 확인 완료.

### 발견 C — u2 는 앱에서도 위치 타임아웃을 스스로 겁니다 ✅

u2 의 `requestLocation(timeoutMs = 10_000)` 이 자체 타이머로 `null` 을 반환합니다.
따라서 u3 가 회신을 못 해도 UI 가 영구히 멈추지는 않습니다. 다만 **10초를 기다립니다.**
→ ABR-27(항상 회신)은 유효합니다. u3 타임아웃을 **8초**로 두어 u2 의 10초보다 먼저 회신합니다.
　같은 값(10초)으로 두면 어느 쪽이 먼저 발동할지 경합이 생깁니다.

---

## 2. 🔴 빌드에 관한 사전 고지 2건

### 고지 1 — `gradle-wrapper.jar` 는 제가 만들 수 없습니다

Gradle 래퍼는 **바이너리 JAR** 입니다. 텍스트로 생성할 수 없습니다.
→ **대응**: `Dockerfile.build` 가 **Gradle 이 이미 설치된 이미지**를 쓰고, 컨테이너 안에서
　`gradle wrapper --gradle-version …` 로 래퍼를 생성한 뒤 `assembleDebug` 를 실행합니다.
　`gradlew` 없이도 빌드가 성립합니다. 리포지터리에는 래퍼 **설정 파일만**(`gradle-wrapper.properties`) 둡니다.

### 고지 2 — 컨테이너 APK 빌드는 대용량 다운로드가 필요합니다

Android SDK Platform 35 + Build-Tools + 의존성으로 **1~2GB** 를 내려받습니다.
네트워크·시간·디스크가 필요하고, `sdkmanager --licenses` 동의가 선행되어야 합니다.
→ Build & Test 에서 **실측을 시도**하되(CON-6 해소 목적), 실패 시 원인을 정직하게 기록하고
　정적 검토 결과로 대체합니다. **성공을 가정하지 않습니다.**

---

## 3. 생성 단계 (Step 1 ~ Step 16)

### 📁 프로젝트 구조 설정

- [ ] **Step 1 — 루트 Gradle 구성**
  `android/settings.gradle.kts` · `android/build.gradle.kts` · `android/gradle.properties`
  · `android/gradle/libs.versions.toml` (버전 카탈로그, **버전 고정 — SEC-10**)
  · `android/gradle/wrapper/gradle-wrapper.properties` · `android/.gitignore`
  → ABR-01 (`baseUrl` 프로퍼티 정의 지점)

- [ ] **Step 2 — 앱 모듈 빌드 스크립트**
  `android/app/build.gradle.kts` — minSdk 26 / targetSdk 35 / compileSdk 35 (ABR: Q1=A)
  · `buildConfigField("String", "BASE_URL", …)` — debug/release 분리 (ABR-01)
  · `-PbaseUrl` · `-PcleartextHost` 주입 처리 (ABR-04)
  · `android/app/proguard-rules.pro` — `@JavascriptInterface` 유지 규칙 **필수**
  → 🔴 R8 이 `@JavascriptInterface` 메서드를 제거하면 **release 에서만 브리지가 죽습니다**

### 📁 매니페스트 · 리소스

- [ ] **Step 3 — 매니페스트 3종**
  `app/src/main/AndroidManifest.xml` — `INTERNET`, 위치 권한, `<queries>` (ABR: 도메인문서 §6)
  `app/src/debug/AndroidManifest.xml` — `networkSecurityConfig` 참조 (**debug 전용** — ABR-04)
  `app/src/debug/res/xml/network_security_config.xml` — 개발 주소 한정 (ABR-05)

- [ ] **Step 4 — 리소스**
  `res/layout/activity_main.xml` (WebView + 오류 화면 + 진행 표시)
  · `res/values/strings.xml` (**모든 사용자 문구를 여기에** — 하드코딩 금지)
  · `res/values/themes.xml` · `res/values/colors.xml`
  → ABR-43 (네이티브 UI 최소화)

### 📁 비즈니스 로직 생성

- [ ] **Step 5 — A7 `AppConfig`** — `config/AppConfig.kt`
  `baseUrl` 검증(빈 값·형식) · `allowedOrigin` 산출 · `isUrlAllowed(url)`
  → ABR-02, ABR-03, ABR-14 / **단위 테스트 대상**

- [ ] **Step 6 — A3 계약** — `bridge/BridgeProtocol.kt`
  u2 `protocol.ts` 의 **정확한 대응물**. sealed class 5종 + `parse(json)` + `encode(msg)`
  → 알 수 없는 type·잘못된 JSON 은 `null` 반환 (ABR-25) / **단위 테스트 대상**

- [ ] **Step 7 — A3 `BridgeHandler`** — `bridge/BridgeHandler.kt`
  `addWebMessageListener` 등록 + `@JavascriptInterface` 폴백 (Q8=A)
  · 회신은 전부 `webView.post { }` (ABR-30) · `JSONObject.quote` 인코딩 (ABR-31)
  · `bridgeReady` 는 **수신부 존재 가드 후** 전송 (발견 A)
  → WF-A3, WF-A7

- [ ] **Step 8 — A4 `IntentLauncher`** — `intent/IntentLauncher.kt`
  try-intent + `ActivityNotFoundException` 폴백 (ABR-20, ABR-21) · `ACTION_SEND` 공유
  · 외부 링크 → 시스템 브라우저 (ABR-14)
  → **URL 을 만들지 않고 받아서 실행만 함** — WF-A4

- [ ] **Step 9 — A5 `LocationProvider`** — `location/LocationProvider.kt`
  `ActivityResultContracts` 권한 요청 · 거부 = `denied:true` (ABR-26)
  · **8초 타임아웃** 후 `null` 회신 (ABR-27, 발견 C)
  → `LocationManager` 사용 — **Play Services 의존성을 넣지 않습니다** (APK 크기·컨테이너 빌드 단순화)

- [ ] **Step 10 — A2 `WebViewConfigurator`** — `webview/WebViewConfigurator.kt`
  하드닝 일괄 적용 (ABR-10~13, ABR-16) → **구조 테스트 대상**

- [ ] **Step 11 — WebView 클라이언트 2종**
  `webview/TripWebViewClient.kt` — `shouldOverrideUrlLoading`(ABR-14) · `onReceivedSslError`(ABR-15)
  　· `onReceivedError` **최초 로드 판별**(ABR-41)
  `webview/TripWebChromeClient.kt` — `onCreateWindow`(ABR-22) · 진행률
  `webview/DownloadHandler.kt` — `DownloadListener` + 오리진 검증 + **브라우저 폴백**(ABR-23, ABR-24)

- [ ] **Step 12 — A1 `MainActivity` + A6 오류 화면**
  `MainActivity.kt` — 기동 검증(ABR-02) · 조립 · 뒤로가기(ABR-42) · `onDestroy`(ABR-32)
  `ui/ErrorScreen.kt` — `BASE_URL` 표시 + 재시도 (ABR-40)
  → WF-A1, WF-A8, WF-A9

### 📁 테스트

- [ ] **Step 13 — 단위 테스트 5종** (`app/src/test/java/...`)
  ① `AppConfigTest` — 빈 값·형식 오류·오리진 경계(호스트/포트/스킴)
  ② `BridgeProtocolTest` — 5종 왕복 · 잘못된 JSON · 알 수 없는 type · 필드 누락
  ③ `JsEncodingTest` — 따옴표·개행·유니코드·백슬래시 이스케이프
  ④ `BackPressTest` — 이중 입력 시각 경계 (2초 전후)
  ⑤ `UrlAllowListTest` — 서브도메인·포트 불일치·스킴 다름 거부
  → **JUnit + Robolectric 없이** 순수 JVM 테스트로 구성 (`JSONObject` 만 `org.json` 로 대체)

- [ ] **Step 14 — 구조 테스트** (`app/src/test/java/.../StructureTest.kt`)
  소스를 읽어 **금지 패턴이 없는지** 검사 — u2 의 `design-rules.test.ts` 와 같은 방식
  · `allowFileAccess(true)` 없음 · `setGeolocationEnabled(true)` 없음
  · `proceed()` 호출 없음 (ABR-15) · `usesCleartextTraffic` 없음
  · Kotlin 소스에 `http://` 리터럴 없음 (ABR-01) · 브리지 계약 5종 외 `@JavascriptInterface` 없음
  → **주석 제거 후 검사** (u2 에서 오탐 4건이 났던 교훈)

### 📁 배포 산출물 · 문서

- [ ] **Step 15 — `android/Dockerfile.build`**
  Gradle + JDK 17 이미지 → Android SDK 설치 → 라이선스 동의 → `gradle wrapper` → `assembleDebug`
  · `-PbaseUrl` 을 빌드 인자로 전달 · APK 를 볼륨으로 추출
  → CON-6 / ASM-4 해소 시도. **성공을 가정하지 않음**

- [ ] **Step 16 — 문서**
  `android/README.md` — 빌드 방법(컨테이너/Android Studio) · 실기기 IP 설정 ·
  　**실기기 확인 체크리스트 8항목**(`business-rules.md` §9 이관) · 릴리스 전 필수 조치
  `construction/u3-trip-android/code/code-summary.md` — 생성 요약 · ABR 매핑 · FR 매핑

---

## 4. 실행 순서 근거

의존 방향을 따라 **안쪽부터** 만듭니다: 설정(A7) → 계약 → 브리지(A3) → 실행기(A4·A5) → WebView(A2) → 액티비티(A1).
u1 은 `domain` → `services` → `api`, u2 는 `shared` → `features` → `app` 이었고 같은 원칙입니다.
거꾸로 만들면 아래 계층이 위 계층 모양에 끌려갑니다.

---

## 5. 검증 계획

| 검증 | 방법 | 실행 시점 |
|---|---|---|
| Kotlin 컴파일 | 컨테이너 `assembleDebug` | Step 15 이후 |
| 단위 테스트 | 컨테이너 `gradle test` | Step 15 이후 |
| 구조 테스트 | 위와 동일 (Step 14) | 동일 |
| ABR 커버리지 | 26개 규칙 전건 코드 매핑표 | Step 16 |
| FR 커버리지 | Owner 4건 + 참여 4건 | Step 16 |
| **실기기 동작** | ❌ **불가** — 사용자가 §9 체크리스트로 확인 | — |

> 🔴 **다시 강조**: u3 의 대표적 실패는 전부 **컴파일을 통과합니다.**
> 컨테이너 빌드가 성공해도 앱이 동작한다는 뜻이 아닙니다. 이 한계를 요약 문서에도 남깁니다.

---

## 6. 예상 규모

| 구분 | 개수 |
|---|---|
| Gradle · 설정 | 7 |
| 매니페스트 · 리소스 | 7 |
| Kotlin 소스 (A1~A7 + 보조) | 12 |
| 테스트 | 6 |
| 배포 · 문서 | 3 |
| **합계** | **약 35개 파일** |

---

## 7. 승인

**"승인"** 또는 **"진행"** 이라고 알려주시면 Step 1 부터 순서대로 실행합니다.
계획 수정이 필요하면 해당 Step 번호를 지정해 주세요.
