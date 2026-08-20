# Domain Entities — u3-trip-android

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 3/3)
**Created**: 2026-08-14T20:20:00Z
**결정 근거**: `construction/plans/u3-trip-android-functional-design-plan.md` Q1~Q14 = 전부 A

> **u3 는 도메인을 갖지 않습니다.** 여행·장소·일정은 u1 이 소유하고 u2 가 표현합니다.
> u3 는 **WebView 껍데기**이며, 본 문서는 **앱 설정과 브리지 계약 타입**만 정의합니다.
> UD-5 — u3 는 u2 의 소스·빌드 산출물을 참조하지 않고 **런타임 URL 로만** 의존합니다.

---

## 1. 빌드 설정 (Q1=A, Q2=A)

| 항목 | 값 | 근거 |
|---|---|---|
| `minSdk` | **26** (Android 8.0) | `WebViewCompat.addWebMessageListener` 안정 동작 (DD-19) |
| `targetSdk` / `compileSdk` | **35** | 최신 정책 준수 |
| `applicationId` | `local.trip.app` | 배포 스토어 없음 — 로컬 설치 전용 |
| `versionCode` / `versionName` | 1 / `0.1.0` | |

### `BuildConfig.BASE_URL` — 빌드 변형별 기본값 (CA-1, FR-27)

| 변형 | 기본값 | 용도 |
|---|---|---|
| `debug` | `http://10.0.2.2:8200` | 에뮬레이터에서 호스트 루프백 |
| `release` | **빈 문자열** | 빌드 시 반드시 지정. 지정하지 않으면 **기동 즉시 오류 화면** |

**실기기 연동**: `./gradlew assembleDebug -PbaseUrl=http://192.168.0.10:8200`

> 🔴 **소스에 주소를 박지 않습니다.** 릴리스 빌드에 개발 주소가 섞이는 것을 막기 위해
> `release` 기본값을 비워 두고, 비어 있으면 실행을 거부합니다 (ABR-02).

---

## 2. 네트워크 정책 (Q3=A) 🔴

### 문제
CA-1 이 정한 접속 주소는 평문 HTTP 입니다. **Android 9(API 28)부터 평문이 기본 차단**되므로
아무 조치 없이 빌드하면 앱이 백엔드에 접속하지 못하고 **빈 화면**만 뜹니다. 오류도 나지 않습니다.

### 결정 — `network_security_config.xml` + **debug 빌드에만 적용**

```
res/xml/network_security_config.xml   (debug 소스셋에만 배치)
    cleartextTrafficPermitted="false"          ← 기본값: 전면 차단
    <domain-config cleartextTrafficPermitted="true">
        10.0.2.2        (에뮬레이터 → 호스트)
        localhost
        127.0.0.1
        192.168.0.0/16 대역은 도메인 지정이 불가하므로 실기기 IP 를 빌드 시 주입
    </domain-config>
```

| 방식 | 채택 | 이유 |
|---|---|---|
| `network_security_config` (debug 전용) | ✅ | 개발 주소만 열리고 **릴리스는 평문 전면 차단 유지** (CON-5 와 정합) |
| `android:usesCleartextTraffic="true"` | ❌ | **모든 도메인**에 적용되고 릴리스 매니페스트에도 남는다 |

> ⚠️ 사설 IP 대역은 `domain-config` 에 CIDR 로 쓸 수 없습니다. 실기기 IP 는
> `-PcleartextHost=192.168.0.10` 로 주입해 debug 매니페스트 병합 시 추가합니다 (ABR-04).

---

## 3. 앱 상태

u3 는 영속 상태를 갖지 않습니다. 일정·목록·캐시는 전부 u2(WebView) 안에 있습니다.

| 상태 | 보관 위치 | 수명 |
|---|---|---|
| WebView 히스토리 | WebView 내부 | 액티비티 수명 |
| `pendingLocationRequests` | `BridgeHandler` 인메모리 `Map` | 요청~응답 (타임아웃 10초) |
| `lastBackPressAt` | `MainActivity` 필드 | 2초 (이중 뒤로가기 판정) |
| `loadFailed` | `MainActivity` 필드 | 재시도 시 초기화 |

**SharedPreferences·Room·파일 저장을 사용하지 않습니다.** 상태를 두면 u2 와 이중 관리가 됩니다.

---

## 4. 브리지 계약 타입 (UD-4)

> 🔴 **`unit-of-work-dependency.md` §2 계약 ②가 단일 진실 공급원입니다.**
> 아래 정의와 u2 의 `shared/bridge/protocol.ts` 는 그 문서의 복제본입니다.
> 변경 시 **문서를 먼저 고치고** 양쪽 코드를 맞춥니다.

### 웹 → 네이티브 (3종)

| `type` | 페이로드 | 앱의 처리 |
|---|---|---|
| `openMap` | `{ appUrl, webUrl }` | 인텐트 시도 → 실패 시 `webUrl` (ABR-20) |
| `share` | `{ title, text, url }` | `ACTION_SEND` 시스템 공유 시트 |
| `requestLocation` | `{ requestId }` | 권한 요청 → 좌표 또는 `denied` 회신 |

### 네이티브 → 웹 (2종)

| `type` | 페이로드 | 전달 방식 |
|---|---|---|
| `locationResult` | `{ requestId, lat, lng, denied }` | `evaluateJavascript` → `window.__tripBridgeReceive` |
| `bridgeReady` | `{ version }` | 페이지 로드 완료 후 1회 |

### 🔴 확장 금지 (SEC-08, SEC-11)

위 5종 외의 메시지를 추가하지 않습니다. **특히 다음은 금지**합니다:
파일 읽기/쓰기 · 임의 인텐트 실행 · 저장소 접근 · 연락처·사진 접근 · 앱 설정 변경.

브리지는 WebView 에 로드되는 **모든 페이지가 잠재적 호출자**입니다. 하나를 열면 그만큼 공격면이 커집니다.

---

## 5. 허용 오리진 (SEC-08)

```
ALLOWED_ORIGINS = [ BuildConfig.BASE_URL 의 scheme://host:port ]
```

| 대상 | 처리 |
|---|---|
| 허용 오리진 내 URL | WebView 안에서 로드 |
| 그 밖의 모든 URL | **시스템 브라우저로 내보냄** (ABR-14) |
| 브리지 메시지 | **허용 오리진에서 온 것만** 처리 (`addWebMessageListener` 의 오리진 목록) |

폴백 경로(`@JavascriptInterface`)에서도 A2 가 오리진 밖 내비게이션을 차단하므로
**노출 범위는 동일**합니다 (Q8=A).

---

## 6. 권한 (Q11=A)

| 권한 | 시점 | 거부 시 |
|---|---|---|
| `INTERNET` | 설치 시 (일반 권한) | — |
| `ACCESS_FINE_LOCATION` / `ACCESS_COARSE_LOCATION` | **웹이 `requestLocation` 을 보낼 때만** | `denied: true` 회신. **오류로 만들지 않는다** |

앱 첫 실행에 미리 묻지 않습니다. 맥락 없는 권한 요청은 거부율이 높고,
거부가 앱 전체를 막으면 안 됩니다.

### `<queries>` 선언 (Android 11+)

```
<queries>
    <package android:name="com.nhn.android.nmap" />   <!-- 네이버지도 -->
    <intent><action android:name="android.intent.action.VIEW" />
            <data android:scheme="nmap" /></intent>
</queries>
```

> ⚠️ 이 선언을 빠뜨리면 **설치돼 있어도 없다고 판정**될 수 있습니다.
> 다만 판정 자체는 `ActivityNotFoundException` 으로 하므로(ABR-20) 이중 안전장치입니다.
