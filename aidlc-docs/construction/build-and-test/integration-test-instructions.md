# Integration Test Instructions — trip

**실측 일시**: 2026-08-14

## 목적

유닛 간 상호작용을 확인합니다. 이 프로젝트는 **단일 컨테이너 배포**(UD-8)라
u1↔u2 는 같은 오리진 안에서 만나고, u3 는 런타임 URL 로만 붙습니다.

---

## 환경 준비

```bash
cd trip
docker compose up -d
# healthy 까지 약 30초
docker compose ps
```

자격증명은 필요 없습니다. 없으면 목 모드로 돕니다 (FR-33).

---

## 시나리오 1 — u2 → u1 (같은 오리진, 계약 ①)

**확인 대상**: OpenAPI 로 생성한 TS 타입이 실제 응답과 맞는가.

```bash
curl -s http://127.0.0.1:8200/api/config
```

기대: `{"map_client_key":null,"modes":{...6개...},"limits":{...3개...}}`

**실측 결과** ✅ — 모든 API 가 `mock`, 상한 3종이 서버 설정과 일치 (WBR-10).

> 타입 불일치는 **빌드 시점에** `npm run generate:api` + `tsc` 로 걸립니다.
> 런타임 검사는 그 보완재입니다.

## 시나리오 2 — 여행 왕복 (u1 전 계층)

```bash
# 생성
curl -s -X POST http://127.0.0.1:8200/api/trips \
  -H 'Content-Type: application/json' --data-binary @trip.json
# 항목 추가 -> 영업시간 저장 -> 재조회
curl -s -X POST ".../days/1/items"        --data-binary @item.json
curl -s -X PUT  ".../items/{id}/opening-hours" --data-binary @oh.json
curl -s "http://127.0.0.1:8200/api/trips/{id}"
```

**실측 결과** ✅ — 생성 · 항목 추가 · 영업시간 저장 · 재조회 모두 정상.

> 🔴 **재조회까지 해야 의미가 있습니다.** `PUT` 이 200 을 돌려주면서도 값을 저장하지 않는
> 결함이 실제로 있었습니다 (`test-results.md` 결함 4). 응답만 보면 통과합니다.

## 시나리오 3 — 정적 자산 + 보안 헤더 (u2 서빙)

```bash
curl -s -D - -o /dev/null http://127.0.0.1:8200/
curl -s -D - -o /dev/null http://127.0.0.1:8200/assets/index-XXXX.js
```

**실측 결과** ✅ — `index.html` `no-cache`, 해시 자산 `immutable`,
CSP·`X-Frame-Options`·`nosniff`·`Referrer-Policy` 전부 존재.

## 시나리오 4 — `.ics` 내보내기 (FR-26)

```bash
curl -s -D - -o out.ics "http://127.0.0.1:8200/api/trips/{id}/export.ics"
```

**실측 결과** ✅ — `Content-Disposition: attachment`, `text/calendar`,
`VCALENDAR` / `VTIMEZONE:Asia/Seoul` 정상.

> ⚠️ 이 응답이 **안드로이드 WebView 에서 무반응**이 되는 것이 u3 의 대표 실패입니다.
> `DownloadListener` 가 처리해야 하며 실기기 확인이 필요합니다 (u3 체크리스트 #2).

## 시나리오 5 — 볼륨 보존

```bash
docker compose down && docker compose up -d && sleep 30
curl -s -o /dev/null -w "%{http_code}\n" "http://127.0.0.1:8200/api/trips/{id}"
```

**실측 결과** ✅ `200` — SQLite 파일이 `./data` 에 남아 데이터가 보존됩니다.

## 시나리오 6 — 기존 프로젝트와 공존 (ID-15)

```bash
docker ps --format "{{.Names}} {{.Status}} {{.Ports}}"
```

**실측 결과** ✅ `trip-app`(8200) 과 `news-app`(8100) 이 동시에 healthy.
컴포즈 프로젝트 이름이 `trip` 으로 분리돼 네트워크·볼륨이 섞이지 않습니다.

---

## 시나리오 7 — u3 ↔ u2 (계약 ②·③) — ⚠️ **자동 검증 불가**

브리지 계약과 `BuildConfig.BASE_URL` 연결은 **실기기에서만** 확인됩니다.
`android/README.md` 의 **실기기 확인 체크리스트 8항목**을 사용하세요.

정적으로 확인한 것:
- `BridgeProtocol.JS_OBJECT_NAME == "tripBridge"` — u2 의 `BRIDGE_NAME` 과 일치 (JUnit 으로 고정)
- 메시지 5종 왕복 (JUnit)
- 오리진 판정 경계 (JUnit)

확인하지 못한 것: 실제 WebView 로딩 · 인텐트 실행 · 다운로드 · 위치 권한.

---

## 정리

```bash
docker compose down          # 데이터 유지
docker compose down -v       # 볼륨까지 삭제 (바인드 마운트라 ./data 는 남습니다)
```
