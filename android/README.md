# trip-android (u3)

여행 일정 웹앱(u2)을 담는 **WebView 래퍼**입니다.
비즈니스 로직을 갖지 않습니다 — 일정·장소·경로는 전부 백엔드(u1)와 웹(u2)이 처리합니다.

앱이 하는 일은 넷뿐입니다: **WebView 호스팅 · 네이티브 브리지 · 지도 앱 인텐트 · 오프라인 안내.**

---

## 빌드

### 컨테이너 빌드 (권장 — JDK·Android SDK 설치 불필요)

```bash
# 1) 빌드 이미지 (최초 1회, Android SDK 내려받기 때문에 몇 분 걸립니다)
docker build -f android/Dockerfile.build -t trip-android-build android/

# 2) APK 생성 (단위 테스트 → assembleDebug)
docker run --rm -v "c:/경로/trip/android:/workspace" -v "c:/경로/trip/android/out:/out" trip-android-build
#    → android/out/app-debug.apk
#    → android/out/test-report/index.html
```

> Windows Git Bash 에서는 경로 변환 때문에 `MSYS_NO_PATHCONV=1` 을 앞에 붙이고
> **Windows 형식 절대경로**(`c:/...`)를 쓰세요. `/c/...` 형식은 마운트가 조용히 무시됩니다.

### 실기기로 붙일 때

에뮬레이터가 아니라 실제 폰에서 쓰려면 **PC 의 LAN IP** 를 두 곳에 넣어야 합니다.

```bash
docker run --rm \
  -v "c:/경로/trip/android:/workspace" -v "c:/경로/trip/android/out:/out" \
  -e BASE_URL=http://192.168.0.10:8200 \
  -e CLEARTEXT_HOST=192.168.0.10 \
  trip-android-build
```

그리고 백엔드가 LAN 에서 보이도록 바인드 주소를 바꿔야 합니다:

```bash
BIND_HOST=0.0.0.0 docker compose up -d
```

> ⚠️ `BIND_HOST=0.0.0.0` 은 같은 네트워크의 누구나 접속할 수 있다는 뜻입니다.
> 이 앱에는 인증이 없습니다(CA-3). 신뢰할 수 있는 네트워크에서만 쓰세요.

### Android Studio

`android/` 폴더를 열면 됩니다. Gradle 래퍼 JAR 은 저장소에 없지만 IDE 가 만들어 줍니다.
접속 주소는 `gradle.properties` 의 `baseUrl` 을 고치거나 실행 구성에 `-PbaseUrl=…` 을 넣으세요.

### 릴리스 빌드

```bash
gradle assembleRelease -PreleaseBaseUrl=https://내서버주소
```

**주소를 주지 않으면 앱이 실행되지 않습니다.** WebView 대신 설정 오류 화면이 뜹니다.
개발 주소가 릴리스에 섞여 나가는 사고를 막기 위한 의도된 동작입니다 (ABR-02).

---

## 🔴 실기기 확인 체크리스트 8항목

**여기가 이 문서에서 가장 중요한 부분입니다.**

컨테이너 빌드는 **컴파일·패키징·단위 테스트까지만** 검증합니다.
아래 항목들은 전부 **컴파일을 통과하고 예외도 내지 않으면서** 실패합니다.
증상이 "오류"가 아니라 **"아무 일도 일어나지 않음"** 이라 로그로도 잘 안 잡힙니다.
APK 를 설치한 뒤 직접 눌러 보는 수밖에 없습니다.

| # | 확인 방법 | 실패하면 이렇게 보입니다 | 관련 규칙 |
|---|---|---|---|
| 1 | 앱 실행 → 일정 목록이 뜨는가 | **빈 흰 화면** (평문 HTTP 차단) | ABR-04, ABR-05 |
| 2 | 일정 상세 → `.ics` 내보내기 | **눌러도 무반응** | ABR-23, ABR-24 |
| 3 | 네이버지도 앱을 **지운 상태**에서 "지도로 열기" | **무반응** (`window.open` 무시) | ABR-22 |
| 4 | 네이버지도 앱을 **설치한 상태**에서 같은 동작 | 앱이 안 열리고 웹으로 감 | ABR-20, ABR-21 |
| 5 | "내 위치" → 권한 대화상자에서 **거부** 선택 | **무한 로딩** | ABR-26, ABR-27 |
| 6 | 비행기 모드로 바꾸고 앱 재실행 | 오류 화면이 저장된 일정을 덮음 | ABR-41 |
| 7 | 상세 화면에서 뒤로가기 | 목록으로 안 가고 앱이 종료됨 | ABR-42 |
| 8 | 따옴표(`"`)가 든 장소명이 있는 일정에서 위치 요청 | 회신이 도착하지 않음 | ABR-31 |

3번은 앱을 실제로 지웠다 깔아야 확인됩니다. 번거롭지만 이 경로가 가장 잘 깨집니다.

---

## 설계 메모

### 왜 이렇게 얇은가

u2 는 이미 완전한 웹앱입니다. 앱에 화면을 더 만들면 **같은 UI 를 두 곳에서 관리**하게 되고,
반드시 어긋납니다. 그래서 네이티브 UI 는 WebView·진행 표시·오류 화면·토스트로 제한했습니다 (ABR-43).

### 브리지 5종이 전부입니다

`openMap` · `share` · `requestLocation` (웹→앱), `locationResult` · `bridgeReady` (앱→웹).

늘리지 마세요. WebView 에 뜨는 **모든 페이지가 잠재적 호출자**입니다.
파일 접근이나 임의 인텐트 실행을 하나 열면 그만큼 공격면이 커집니다.
계약의 단일 진실 공급원은 `aidlc-docs/inception/application-design/unit-of-work-dependency.md` §2 입니다.

### 딥링크 URL 을 앱이 만들지 않습니다

`nmap://` URL 은 **u2 의 `shared/deeplink` 가 단독으로** 만듭니다 (DD-11).
앱은 받아서 실행만 합니다. 양쪽에서 만들면 웹과 앱의 동작이 갈라집니다.

### `bridgeReady` 는 현재 소비처가 없습니다

u2 의 `__tripBridgeReceive` 는 위치 요청 때 처음 설치되고, `locationResult` 외의 타입을 무시합니다.
계약에 있는 메시지라 유지하되, 앱은 **수신부가 있을 때만** 보냅니다.

### `DownloadManager` 는 앱의 네트워크 정책을 따르지 않습니다

시스템 프로세스에서 동작하기 때문에 `network_security_config` 의 평문 허용이 **적용되지 않습니다.**
개발 환경(HTTP)에서 다운로드가 실패할 수 있어 **시스템 브라우저 폴백**을 뒀습니다 (ABR-24).
체크리스트 2번이 이 경로를 봅니다.

---

## 테스트

```bash
gradle testDebugUnitTest
```

47건 — `AppConfigTest` · `UrlAllowListTest` · `BridgeProtocolTest` · `JsEncodingTest`
· `BackPressPolicyTest` · `StructureTest`.

**PBT 는 하지 않습니다.** u3 에는 순수 계산 로직이 없습니다 (딥링크 URL 생성조차 u2 소유).
대신 `StructureTest` 가 하드닝 규칙이 코드에 남아 있는지 소스를 읽어 검사합니다 —
`allowFileAccess(true)` · `setGeolocationEnabled(true)` · `handler.proceed()` ·
`Intent.parseUri` · 매니페스트의 `usesCleartextTraffic` · 주소 하드코딩 등.

---

## 알려진 제약

| 제약 | 내용 |
|---|---|
| 인증 없음 | 앱에도 로그인이 없습니다 (CA-3). 공유 링크를 아는 사람은 누구나 봅니다 |
| 대중교통 경로 | 네이버가 공식 API 를 제공하지 않습니다 (CON-1). 앱 안의 시간은 **추정치**이고, 실제 길찾기는 네이버지도 앱에 넘깁니다 |
| 계측 테스트 없음 | Espresso 는 기기가 필요해 이번 범위에서 제외했습니다. 위 체크리스트가 그 자리를 대신합니다 |
| 스토어 배포 없음 | `applicationId` 가 `local.trip.app` 입니다. 배포하려면 서명 구성과 ID 를 먼저 정하세요 |
