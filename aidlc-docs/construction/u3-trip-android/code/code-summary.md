# Code Generation Summary — u3-trip-android

**Stage**: 🟢 CONSTRUCTION - Code Generation (Unit 3/3)
**Completed**: 2026-08-14T21:20:00Z
**계획서**: `construction/plans/u3-trip-android-code-generation-plan.md` (Step 1~16 전건 완료)

---

## 1. 실측 결과 — **컨테이너 빌드·테스트 성공**

| 검증 | 결과 |
|---|---|
| 이미지 빌드 (`Dockerfile.build`) | ✅ 성공 (Gradle 8.11.1 + Android SDK 35 + Build-Tools 35.0.0) |
| Kotlin 컴파일 | ✅ 오류 0건 (경고 2건 — 플랫폼 deprecation) |
| 단위 테스트 | ✅ **47 passed / 0 failed** (2.9초) |
| `assembleDebug` | ✅ 성공 — `android/out/app-debug.apk` **4.18 MB** |

### 🔴 CON-6 / ASM-4 해소

Workspace Detection 시점에는 로컬 JDK·Android SDK 부재로 **"APK 빌드 검증 불가"** 로 판단했고,
`ASM-4`(사용자가 Android Studio 에서 빌드)를 미확정 가정으로 남겨 두었습니다.
**컨테이너에서 APK 가 실제로 만들어졌으므로 두 항목 모두 해소됩니다.**

### 빌드 변형 분리 실측 (ABR-02, ABR-04)

| 확인 | 결과 |
|---|---|
| debug `BuildConfig.BASE_URL` | `"http://10.0.2.2:8200"` ✅ |
| release `BuildConfig.BASE_URL` | `""` ✅ — 주소 미지정 시 앱이 설정 오류 화면을 띄운다 |
| debug 병합 매니페스트 | `networkSecurityConfig="@xml/network_security_config"` ✅ |
| **release 병합 매니페스트** | `networkSecurityConfig` **없음** ✅ — 평문 전면 차단 유지 |
| `-PcleartextHost=192.168.0.10` 주입 | 생성 XML 에 도메인 4개(기본 3 + 주입 1) ✅ |
| `-PbaseUrl` 주입 | `BuildConfig.BASE_URL = "http://192.168.0.10:8200"` ✅ |

---

## 2. 생성 파일 (33개)

| 구분 | 파일 |
|---|---|
| Gradle (6) | `settings.gradle.kts` · `build.gradle.kts` · `gradle.properties` · `gradle/libs.versions.toml` · `gradle/wrapper/gradle-wrapper.properties` · `app/build.gradle.kts` |
| 설정 (3) | `app/proguard-rules.pro` · `.gitignore` · `.dockerignore` |
| 매니페스트 (3) | `main/AndroidManifest.xml` · `debug/AndroidManifest.xml` · `main/res/xml/data_extraction_rules.xml` |
| 리소스 (7) | `layout/activity_main.xml` · `values/{strings,colors,themes,ic_launcher_background}.xml` · `values-night/colors.xml` · `drawable/ic_launcher_foreground.xml` · `mipmap-anydpi-v26/ic_launcher{,_round}.xml` |
| Kotlin (12) | 아래 표 |
| 테스트 (6) | `AppConfigTest` · `UrlAllowListTest` · `BridgeProtocolTest` · `JsEncodingTest` · `BackPressPolicyTest` · `StructureTest` |
| 배포·문서 (2) | `Dockerfile.build` · `README.md` |

### 컴포넌트 → 파일

| ID | 컴포넌트 | 파일 | 줄 |
|---|---|---|---|
| **A1** | `MainActivity` | `MainActivity.kt` | 218 |
| **A2** | `WebViewConfigurator` | `webview/WebViewConfigurator.kt` | 75 |
| **A3** | `BridgeHandler` | `bridge/BridgeHandler.kt` + `bridge/BridgeProtocol.kt` | 186 + 137 |
| **A4** | `IntentLauncher` | `intent/IntentLauncher.kt` | 103 |
| **A5** | `LocationProvider` | `location/LocationProvider.kt` | 165 |
| **A6** | `OfflineScreen` | `ui/ErrorScreen.kt` | 82 |
| **A7** | `AppConfig` | `config/AppConfig.kt` | 105 |
| 보조 | 내비게이션·오류 정책 | `webview/TripWebViewClient.kt` | 97 |
| 보조 | `window.open` 가로채기 | `webview/TripWebChromeClient.kt` | 71 |
| 보조 | 다운로드 | `webview/DownloadHandler.kt` | 91 |
| 보조 | 뒤로가기 판정 | `ui/BackPressPolicy.kt` | 46 |

---

## 3. ABR 커버리지 (26/26)

| ABR | 구현 위치 | 테스트 |
|---|---|---|
| ABR-01 주소 주입만 | `app/build.gradle.kts` `buildConfigField` | `StructureTest` 주소 리터럴 검사 |
| ABR-02 빈 주소 → 오류 화면 | `MainActivity.onCreate` / `AppConfig.resolve` | `AppConfigTest` |
| ABR-03 형식 오류 → 오류 화면 | `AppConfig.parseOrigin` | `AppConfigTest` |
| ABR-04 debug 전용 NSC | `debug/AndroidManifest.xml` | `StructureTest` + 병합 매니페스트 실측 |
| ABR-05 개발 주소 한정 | 생성 `network_security_config.xml` | 생성물 실측 |
| ABR-10 파일 접근 차단 | `WebViewConfigurator` | `StructureTest` |
| ABR-11 혼합 콘텐츠 차단 | 동일 | `StructureTest` |
| ABR-12 DOM Storage 유지 | 동일 | — |
| ABR-13 WebView 위치 비활성 | 동일 | `StructureTest` |
| ABR-14 오리진 밖 내비 차단 | `TripWebViewClient.shouldOverrideUrlLoading` | `UrlAllowListTest` |
| ABR-15 SSL 오류 무시 금지 | `TripWebViewClient.onReceivedSslError` | `StructureTest` |
| ABR-16 디버깅 debug 한정 | `WebViewConfigurator` + `BuildConfig.WEBVIEW_DEBUG` | BuildConfig 실측 |
| ABR-20 URL 생성 금지 | `IntentLauncher` (받아서 실행만) | — |
| ABR-21 폴백 후 토스트 | `IntentLauncher.openMap` | 실기기 #4 |
| ABR-22 `onCreateWindow` | `TripWebChromeClient` | 실기기 #3 |
| ABR-23 다운로드 오리진 검증 | `DownloadHandler` | `UrlAllowListTest` |
| ABR-24 다운로드 브라우저 폴백 | 동일 | 실기기 #2 |
| ABR-25 계약 5종만 처리 | `BridgeProtocol.parse` | `BridgeProtocolTest` |
| ABR-26 거부는 오류 아님 | `MainActivity.onRequestLocation` | 실기기 #5 |
| ABR-27 항상 회신 (8초) | `LocationProvider` + `MainActivity` | 실기기 #5 |
| ABR-30 UI 스레드 회신 | `BridgeHandler.dispatch` / `send` | — |
| ABR-31 `JSONObject.quote` | `BridgeHandler.buildScript` | `JsEncodingTest` |
| ABR-32 `onDestroy` 정리 | `MainActivity` / `releaseSafely` | — |
| ABR-33 `bridgeReady` 가드 | `BridgeHandler.buildScript` | — |
| ABR-40 주소 표시 | `ErrorScreen.showConnectionFailure` | — |
| ABR-41 최초 로드만 덮기 | `TripWebViewClient.firstLoadSucceeded` | 실기기 #6 |
| ABR-42 뒤로가기 | `BackPressPolicy` | `BackPressPolicyTest` |
| ABR-43 UI 최소화 | `activity_main.xml` | — |

## 4. FR 커버리지

**Owner (4/4)**: FR-27 `MainActivity`+`AppConfig` · FR-28 `BridgeHandler`+`LocationProvider`+`IntentLauncher`
· FR-29 `BackPressPolicy` · FR-30 `ErrorScreen`+`TripWebViewClient`
**참여 (4/4)**: FR-12 위치 · FR-23 지도 인텐트 · FR-24 웹 폴백 · FR-26 `.ics` 다운로드

---

## 5. 생성 중 발견·수정한 결함 5건

| # | 결함 | 조치 |
|---|---|---|
| 1 | `bridgeReady` 를 u2 가 소비하지 않음 — `__tripBridgeReceive` 가 위치 요청 때만 설치됨 | 계약 유지 + **수신부 존재 가드**. 소비처 부재를 주석·문서에 명시 |
| 2 | u2 도 위치 타임아웃 10초 보유 → 같은 값이면 경합 | u3 타임아웃을 **8초**로 설정 |
| 3 | `DownloadManager` 가 앱 네트워크 정책 밖 (AD-1) | 실패 감지 후 **시스템 브라우저 폴백** |
| 4 | 🔴 **`StructureTest` 오탐 2건** — 매니페스트 주석의 `usesCleartextTraffic`, 로그 문자열의 `@JavascriptInterface` | `stripXmlComments()` 추가 + 로그 문구 변경. **u2 에서 겪은 것과 같은 유형** |
| 5 | `gradle-wrapper.jar` 바이너리 부재 | 컨테이너가 Gradle 배포판을 직접 설치 |

### ⚠️ Gradle 스크립트 컴파일 오류 1건
`settings.gradle.kts` 의 `includeGroupByRegex` 정규식 이스케이프가 깨져 빌드 실패
→ 저장소 필터링은 최적화일 뿐이므로 제거하고 `google()` 로 단순화.

---

## 6. 🔴 자동 검증이 닿지 않는 범위

컨테이너 빌드가 성공했다는 것은 **컴파일과 패키징이 된다**는 뜻이지
**앱이 동작한다**는 뜻이 아닙니다.

평문 차단 · 다운로드 무시 · `window.open` 무시 · 위치 미회신 — 네 가지 대표 실패는
전부 컴파일을 통과하고 예외도 내지 않습니다. `README.md` 의 **실기기 확인 체크리스트 8항목**이
이 공백을 메우는 유일한 수단이며, 사용자가 APK 를 설치해 직접 확인해야 합니다.

`StructureTest` 는 그중 **"하드닝이 나중에 풀리는"** 부분만 자동으로 막습니다.
