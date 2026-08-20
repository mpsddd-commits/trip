# Business Logic Model — u3-trip-android

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 3/3)
**Created**: 2026-08-14T20:20:00Z

---

## 0. 답변 교차 검증에서 검출한 사항 2건

### ⚠️ 검출 1 — `DownloadManager` 는 앱의 네트워크 정책을 따르지 않습니다

`Q5=A`(DownloadManager 로 `.ics` 저장) × `Q3=A`(평문 허용을 **앱의** `network_security_config` 로 한정).

`DownloadManager` 는 **시스템 프로세스(`com.android.providers.downloads`)** 에서 동작하므로
**우리 앱의 네트워크 보안 설정이 적용되지 않습니다.** 평문 HTTP 다운로드의 성공 여부가
기기·OS 버전에 따라 달라질 수 있습니다.

→ **AD-1 로 해소**: 다운로드 실패를 감지해 **시스템 브라우저 폴백**을 둡니다.
　`DownloadManager` 등록 후 상태를 확인하지 않고 낙관적으로 두지 않고,
　실패 시 사용자에게 "브라우저에서 내려받기" 경로를 제시합니다 (ABR-24).
→ **Build & Test 검증 항목**으로 등록합니다. 실기기 확인이 필요합니다.

### ⚠️ 검출 2 — `evaluateJavascript` 는 UI 스레드에서만 호출할 수 있습니다

`Q9=A`(evaluateJavascript 로 응답) × `addWebMessageListener` 의 콜백 스레드.

`WebViewCompat.addWebMessageListener` 는 지정한 `Executor` 에서 콜백을 호출합니다.
위치 권한 결과도 액티비티 콜백에서 옵니다. **WebView API 는 UI 스레드 전용**이므로
어느 경로에서든 `evaluateJavascript` 호출 전에 UI 스레드로 넘겨야 합니다.

→ **AD-2 로 해소**: 모든 웹 회신은 `webView.post { ... }` 로 UI 스레드에서 실행합니다 (ABR-31).

---

## WF-A1. 앱 기동 (FR-27)

```
MainActivity.onCreate
   |
   v  BuildConfig.BASE_URL 검증 (ABR-02)
   |     비어 있음 --> 오류 화면 "접속 주소가 설정되지 않았습니다" + 종료 안내
   |                   (release 빌드에서 주소 지정을 잊은 경우)
   |
   v  WebView 생성 + 하드닝 적용 (A2 / WF-A2)
   |
   v  BridgeHandler 부착 (A3 / WF-A3)
   |     addWebMessageListener 지원? --> 오리진 목록과 함께 등록
   |     미지원                      --> @JavascriptInterface 폴백 등록
   |
   v  DownloadListener 부착 (A4 / WF-A5)
   v  WebChromeClient.onCreateWindow 부착 (WF-A6)
   |
   v  loadUrl(BASE_URL)
   |
   +-- onPageFinished  --> bridgeReady 전송 (ABR-33)
   |
   +-- onReceivedError (**최초 로드에서만**) --> 오프라인 화면 (WF-A8)
```

---

## WF-A2. WebView 하드닝 (Q4=A, SEC-09)

| 설정 | 값 | 이유 |
|---|---|---|
| `javaScriptEnabled` | ✅ | u2 가 React 앱 |
| `domStorageEnabled` | ✅ | **오프라인 캐시(IndexedDB)에 필요** (FR-31) |
| `databaseEnabled` | ✅ | 동일 |
| `allowFileAccess` | ❌ | 로컬 파일 접근 차단 |
| `allowContentAccess` | ❌ | 콘텐츠 프로바이더 차단 |
| `allowFileAccessFromFileURLs` | ❌ | |
| `allowUniversalAccessFromFileURLs` | ❌ | |
| `mixedContentMode` | `NEVER_ALLOW` | HTTPS 페이지에 HTTP 리소스 금지 |
| `setGeolocationEnabled` | ❌ | **위치는 브리지로만** — WebView 자체 권한 대화상자를 쓰지 않는다 |
| `setSupportMultipleWindows` | ✅ | `window.open` 가로채기용 (WF-A6) |
| `userAgentString` | 기본 + ` TripApp/0.1` | u2 가 앱 여부를 판단할 보조 수단 |

> 🔴 `setGeolocationEnabled(false)` 인 이유: 켜 두면 WebView 가 **자체 권한 대화상자**를 띄워
> 브리지 경로(FR-28)와 **두 개의 위치 요청 경로**가 생깁니다. 하나로 모읍니다.

---

## WF-A3. 브리지 메시지 처리 (FR-28, Q8=A)

```
웹 --postMessage(JSON)--> BridgeHandler
   |
   v  오리진 검증 (addWebMessageListener 가 1차, 폴백 경로는 A2 가 2차)
   |
   v  JSON 파싱 실패 --> **조용히 무시**한다 (ABR-30)
   |                    로그만 남기고 예외를 밖으로 던지지 않는다
   |
   +-- "openMap"          --> WF-A4
   +-- "share"            --> ACTION_SEND 시스템 공유 시트
   +-- "requestLocation"  --> WF-A7
   +-- 그 밖의 type       --> **무시** (ABR-30 — 계약 5종 외에는 처리하지 않는다)
```

---

## WF-A4. 네이버지도 열기 (FR-23, FR-24, Q10=A)

```
openMap { appUrl, webUrl }
   |
   v  Intent(ACTION_VIEW, appUrl) 실행 시도
   |
   +-- 성공 --> 네이버지도 앱이 열린다
   |
   +-- ActivityNotFoundException --> Intent(ACTION_VIEW, webUrl) 로 폴백
         |
         +-- 이것도 실패 --> 토스트 "지도를 열 수 없습니다" (ABR-21)
```

**`queryIntentActivities` 사전 조회를 쓰지 않는 이유** (Q10=A):
Android 11+ 의 패키지 가시성 제한 때문에 `<queries>` 선언이 필요하고,
**선언을 빠뜨리면 설치돼 있어도 "없다"고 판정**합니다. 예외 처리가 더 견고합니다.
(`<queries>` 는 이중 안전장치로 함께 선언합니다.)

> 🔴 **URL 은 앱이 만들지 않습니다.** u2 의 W13 이 만든 것을 받아 실행만 합니다 (DD-11, WBR-28).

---

## WF-A5. `.ics` 다운로드 (FR-26, Q5=A) 🔴

**문제**: WebView 는 `<a download>` 나 `Content-Disposition: attachment` 를 스스로 처리하지 않습니다.
`DownloadListener` 가 없으면 **버튼을 눌러도 아무 일도 일어나지 않고 오류도 나지 않습니다.**

```
DownloadListener.onDownloadStart(url, ua, contentDisposition, mimeType, size)
   |
   v  허용 오리진의 URL 인가? --> 아니면 무시 (ABR-23)
   |
   v  DownloadManager.Request 등록
   |     제목: "여행 일정.ics"
   |     알림: 완료 시 표시
   |     저장: 공용 Downloads
   |
   +-- 등록 실패 / 다운로드 실패 --> **시스템 브라우저 폴백** (AD-1, ABR-24)
   |                                토스트로 안내
   |
   +-- 완료 --> 알림에서 캘린더 앱으로 열 수 있다
```

⚠️ **AD-1** — `DownloadManager` 는 시스템 프로세스라 **앱의 평문 허용 설정이 적용되지 않습니다.**
개발 환경(HTTP)에서 실패할 수 있으므로 폴백을 반드시 둡니다. **Build & Test 실기기 검증 항목.**

---

## WF-A6. `window.open` 가로채기 (FR-24, Q6=A) 🔴

**문제**: WebView 는 `setSupportMultipleWindows(true)` + `onCreateWindow` 없이는 `window.open` 을 **무시**합니다.
u2 의 딥링크 웹 폴백이 이 함수를 쓰므로, 브리지 전달이 실패하면 **사용자는 아무 반응도 못 봅니다.**

```
WebChromeClient.onCreateWindow
   |
   v  새 WebView 를 만들지 않는다
   |
   v  임시 WebView 를 만들어 WebViewTransport 로 넘기고,
   |  그 WebViewClient 의 shouldOverrideUrlLoading 에서 **URL 만 추출**
   |
   v  시스템 브라우저 인텐트로 전달 (ABR-22)
   v  임시 WebView 즉시 파기
```

새 창을 실제로 띄우지 않습니다. 뒤로가기·수명 관리가 복잡해지고 u3 의 "껍데기" 원칙(Q14=A)에 어긋납니다.

---

## WF-A7. 위치 요청 (FR-28, Q11=A)

```
requestLocation { requestId }
   |
   v  pendingLocationRequests[requestId] = 대기
   |
   v  권한 보유? --> 아니오 --> ActivityResultContracts.RequestMultiplePermissions
   |                            |
   |                            +-- 거부 --> locationResult { denied: true } (ABR-26)
   |                                        **오류가 아니다.** 웹은 해당 기능만 비활성한다
   |
   v  FusedLocation / LocationManager 로 최근 위치 조회
   |
   +-- 성공 --> locationResult { lat, lng, denied: false }
   +-- 실패·타임아웃(10초) --> locationResult { lat: null, lng: null, denied: false }
   |
   v  webView.post { evaluateJavascript(...) }   ← AD-2 (UI 스레드)
```

**미회신을 만들지 않습니다.** u2 는 10초 타임아웃으로 자체 방어하지만(ABR-27),
앱이 항상 회신하는 편이 사용자에게 빠릅니다.

---

## WF-A8. 오프라인 화면 (FR-30, Q12=A)

```
onReceivedError / onReceivedHttpError
   |
   v  **최초 로드(첫 페이지)** 인가?
   |
   +-- 예   --> 전체 화면 오류: "연결할 수 없습니다"
   |             현재 BASE_URL 표시 + [다시 시도] 버튼
   |             (주소가 틀린 경우가 가장 흔하므로 주소를 보여준다 — ABR-40)
   |
   +-- 아니오 --> **아무것도 하지 않는다** (ABR-41)
                  u2 의 OfflineGate 가 저장된 일정을 보여준다.
                  앱이 덮으면 그 기능을 가린다.
```

**두 계층이 같은 일을 두 번 하지 않게 합니다.**

---

## WF-A9. 뒤로가기 (FR-29, Q13=A)

```
onBackPressed
   |
   v  webView.canGoBack() ? --> 예 --> webView.goBack()
   |
   v  아니오
      |
      v  2초 이내에 뒤로가기를 또 눌렀나?
         |
         +-- 예   --> 앱 종료
         +-- 아니오 --> 토스트 "한 번 더 누르면 종료됩니다" + 시각 기록
```

---

## 10. Testable Properties — **u3 는 PBT 대상이 아닙니다**

| 판정 | 근거 |
|---|---|
| **PBT N/A** | `unit-of-work.md` §4 에서 이미 확정. u3 는 **순수 계산 로직을 갖지 않는다.** 딥링크 URL 생성조차 u2 소유(DD-11)이고, 나머지는 Android 프레임워크 호출·수명 주기 관리다 |

### 대신 검증하는 것 (PBT-10 — 예제 기반)

| 대상 | 방식 | 도구 |
|---|---|---|
| 브리지 메시지 파싱 (JSON → sealed class) | 단위 테스트. 잘못된 JSON·알 수 없는 type·필드 누락 | JUnit |
| 오리진 판정 (`isAllowedOrigin`) | 단위 테스트. 호스트·포트·스킴 경계 | JUnit |
| `JSONObject.quote` 이스케이프 | 단위 테스트. 따옴표·개행·유니코드 포함 이름 | JUnit |
| 뒤로가기 이중 입력 판정 | 단위 테스트. 시각 경계 | JUnit |
| WebView 설정 하드닝 | **구조 테스트** — 금지 설정이 코드에 없는지 소스 검사 | JUnit |

> ⚠️ 계측 테스트(Instrumented / Espresso)는 **기기·에뮬레이터가 필요**하므로 이번 범위에서 제외합니다.
> Build & Test 의 컨테이너 빌드는 **컴파일·패키징까지만** 검증합니다 (CON-6, ASM-4).

---

## 11. 🔴 이 유닛에서 자동 검증이 닿지 않는 것

세 발견(평문 HTTP·다운로드·`window.open`)은 **전부 컴파일이 통과하고 오류도 나지 않습니다.**
컨테이너 빌드로는 잡히지 않으며, **실기기·에뮬레이터에서만 드러납니다.**

→ `business-rules.md` §9 에 **실기기 확인 체크리스트**를 남깁니다. 사용자가 APK 를 설치해
직접 확인해야 하는 항목입니다. 이 한계를 Build & Test 보고서에도 명시합니다.
