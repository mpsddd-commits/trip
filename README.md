# trip

여행 일정을 AI가 만들고, 시간표·이동경로·장소 추천을 **네이버지도** 위에서 확인하며,
실제 길찾기는 네이버지도 앱으로 넘기는 웹앱 + 안드로이드 앱.

AI-DLC(AI-Driven Development Life Cycle)로 설계·구현했습니다. 모든 설계 결정과 근거는
[`aidlc-docs/`](aidlc-docs/) 에 있습니다.

---

## 구성

| 유닛 | 디렉터리 | 스택 | 상태 |
|---|---|---|---|
| `u1-trip-backend` | [`backend/`](backend/) | Python 3.12 · FastAPI · SQLite | ✅ 구현 완료 |
| `u2-trip-web` | `web/` | TypeScript · React · Vite | ⏳ 미생성 |
| `u3-trip-android` | `android/` | Kotlin · WebView 래퍼 | ⏳ 미생성 (빌드 Dockerfile 만 존재) |

> ⚠️ **현재는 `u1` 만 생성된 상태입니다.**
> `docker compose build` 는 `web/` 이 없어 실패합니다. 이는 정상이며, `u2` 생성 후 동작합니다.
> 지금 백엔드만 확인하려면 아래 [백엔드 단독 실행](#백엔드-단독-실행-u1-만-있는-현재-상태) 을 보세요.

---

## 핵심 동작 3가지

### 1. AI가 만든 장소는 그대로 믿지 않습니다
LLM은 **장소 이름과 분류 힌트만** 제시합니다. 주소·좌표·전화번호는 타입에조차 없습니다.
모든 장소는 **네이버 지역검색으로 대조**해 실좌표를 얻고, 3조건(이름 유사도 ≥ 0.60 **AND**
목적지 범위 내 **AND** 카테고리 일치)을 전부 통과해야 일정에 들어갑니다.

통과하지 못한 장소는 **일정에 넣지 않고** "확인 필요" 목록으로 따로 보여줍니다.

### 2. 대중교통 소요시간은 추정치입니다
**네이버는 대중교통·도보 경로 API를 제공하지 않습니다.** 자동차 경로만 제공합니다.
따라서 앱 안의 대중교통 이동시간은 추정치이며 배지로 표시되고, 정확한 안내는
**"네이버지도로 길찾기"** 버튼(`nmap://` 딥링크)이 네이버지도 앱에 넘깁니다.

### 3. 영업시간은 직접 입력해야 합니다
네이버 지역검색 응답에 **영업시간 필드가 없습니다.** 그래서 영업시간은 사용자가 장소별로
직접 입력했을 때만 저장되고, 그때만 "영업시간 밖 도착" 경고가 뜹니다.
근거 없는 추정으로 잘못된 경고를 띄우지 않기 위한 선택입니다.

---

## 빠른 시작

### 준비물
- Docker Desktop
- (선택) API 인증 정보 — **없어도 데모 데이터로 전 화면이 동작합니다**

### 실행

```bash
cd trip
docker compose up -d --build
```

**리눅스에서는 최초 1회만 이 명령이 먼저 필요합니다:**

```bash
sudo chown -R 10001:10001 data logs
```

컨테이너가 uid 10001 로 돌고 `data/`·`logs/` 를 바인드 마운트하는데,
호스트 디렉터리 소유자가 우선하기 때문입니다. 하지 않으면 SQLite 를 만들지 못해
컨테이너가 죽습니다. **Windows·macOS 의 Docker Desktop 에서는 필요 없습니다** —
파일 공유 계층이 소유권을 무시합니다.

이게 전부입니다. **`.env` 는 없어도 됩니다** — 인증 정보가 없으면 데모 데이터로 동작합니다.
실제 API 를 붙이려면 그때 만드세요:

```bash
cp .env.example .env          # Windows: Copy-Item .env.example .env
# .env 에 인증 정보를 넣고
docker compose up -d
```

http://127.0.0.1:8200 으로 접속합니다.

### API 인증 정보 (전부 선택)

| 변수 | 발급처 | 없으면 |
|---|---|---|
| `NAVER_CLIENT_ID` / `NAVER_CLIENT_SECRET` | [네이버 개발자센터](https://developers.naver.com) | 장소 검색·추천이 데모 데이터 |
| `NCP_CLIENT_ID` / `NCP_CLIENT_SECRET` | [네이버 클라우드 플랫폼](https://www.ncloud.com) | 자동차 경로가 직선 근사 |
| `NCP_MAP_CLIENT_KEY` | 동일 | 지도가 렌더링되지 않음 |
| `ANTHROPIC_API_KEY` | [Anthropic Console](https://console.anthropic.com) | AI 자동 생성 비활성 (수동 편집은 정상) |

어떤 API가 데모 모드인지는 `GET /api/health/ready` 의 `modes` 에서 확인할 수 있습니다.

> ⚠️ **`NCP_MAP_CLIENT_KEY` 는 구조상 브라우저에 노출됩니다.**
> NCP 콘솔에서 **Web 서비스 URL(도메인 화이트리스트)** 을 반드시 등록하세요.
> 나머지 키는 백엔드에서만 사용되며 클라이언트로 나가지 않습니다.

---

## 백엔드 단독 실행 (개발용)

전체 스택은 위의 `docker compose` 로 충분합니다. 백엔드만 따로 띄우고 싶을 때만 쓰세요.

```bash
cd trip/backend
python -m venv .venv && . .venv/Scripts/activate      # Linux/macOS: . .venv/bin/activate
pip install -r requirements-dev.txt
DATABASE_PATH=../data/trip.db LOG_DIR=../logs   uvicorn app.main:create_app --factory --port 8200
```

> 🔴 **`--factory` 가 필요합니다.** `app.main` 에는 모듈 수준 `app` 객체가 없습니다.
> 임포트만으로 컨테이너(DB 연결·클라이언트)가 만들어지는 것을 막기 위해 일부러 없앴습니다.

- OpenAPI 스키마: <http://127.0.0.1:8200/api/openapi.json>
- 헬스체크: <http://127.0.0.1:8200/api/health>

> ⚠️ 로컬 Python 이 3.13 이상이면 `pydantic-core` 휠이 없어 설치가 실패할 수 있습니다.
> 컨테이너는 3.12 로 고정돼 있습니다 (UD-9). 막히면 컨테이너를 쓰세요:
> ```bash
> docker run --rm -v "$PWD/backend:/app" -w /app python:3.12-slim >   sh -c "pip install -q -r requirements-dev.txt && python -m pytest"
> ```

### 테스트

```bash
cd trip/backend
pytest                              # 전체 (234건)
pytest -m property                  # 속성 기반 테스트(PBT)만
HYPOTHESIS_PROFILE=ci pytest        # 예제 수를 늘려 실행
```

속성 테스트는 실패 시 **시드와 최소 반례**를 출력합니다. 그대로 재현할 수 있습니다.

실제로 이 방식이 잡아낸 결함이 있습니다 — 항목이 2개인 날은 경로가 **절대 재정렬되지 않았습니다.**
이동시간 행렬이 비대칭인데 코드가 `n<=2` 를 건너뛰었기 때문입니다. 오류가 전혀 나지 않는
종류의 버그라, 완전탐색 오라클과 대조하는 속성 테스트가 아니었으면 발견하지 못했습니다.

**전체 테스트 360건**: 백엔드 234 · 웹 79 · 안드로이드 47.

---

## 안드로이드 연동

안드로이드 기기에서는 **개발 PC의 `127.0.0.1` 에 접근할 수 없습니다.** 노출 범위를 바꿔야 합니다.

```bash
# .env 수정
BIND_HOST=0.0.0.0

docker compose up -d
```

| 환경 | 앱의 `BASE_URL` |
|---|---|
| 에뮬레이터 | `http://10.0.2.2:8200` |
| 실기기 (같은 Wi-Fi) | `http://<PC의 LAN IP>:8200` — `ipconfig` 로 확인, 방화벽에서 8200 인바운드 허용 |

> 🔴 **`BIND_HOST=0.0.0.0` 상태에서는 같은 네트워크의 누구나 접근할 수 있습니다.**
> 이 앱에는 로그인이 없습니다. 여행 UUID를 아는 사람은 조회·편집이 가능합니다.
> **공용 Wi-Fi에서는 사용하지 마세요.** 연동이 끝나면 `127.0.0.1` 로 되돌리세요.
> 기동 로그에 경고(WARN)가 출력되는 것은 정상입니다.

### APK 빌드

로컬에 JDK·Android SDK가 없어도 컨테이너로 빌드합니다.

```bash
# 에뮬레이터용 (10.0.2.2)
./scripts/build-android.sh                            # Windows: .\scripts\build-android.ps1

# 실기기용 — 접속 주소를 인자로 넘기면 평문 허용 호스트까지 함께 설정됩니다
./scripts/build-android.sh http://192.168.0.10:8200
# → android/out/app-debug.apk
# → android/out/test-report/index.html
```

⚠️ 최초 실행 시 Android SDK 이미지를 **수 GB** 내려받습니다.
🔴 이 빌드는 **컴파일·패키징·단위 테스트까지만** 검증합니다.
WebView 로딩 · 지도 앱 인텐트 · 다운로드 · 위치 권한은 **실기기에서만** 확인됩니다.
설치한 뒤 [android/README.md](android/README.md) 의 **실기기 확인 체크리스트 8항목**을 실행하세요 —
네 가지 대표 실패는 전부 컴파일을 통과하고 **오류도 내지 않습니다.**

---

## 운영·유지보수

### 백업

```bash
./scripts/backup-db.sh            # Windows: .\scripts\backup-db.ps1
```

> ⚠️ **`data/` 폴더를 그냥 복사하는 것은 백업이 아닙니다.**
> WAL에만 있고 DB 본체에 반영되지 않은 트랜잭션이 누락됩니다. 위 스크립트를 쓰세요.

### 의존성 점검 / SBOM

```bash
./scripts/audit-deps.sh           # Windows: .\scriptsudit-deps.ps1
python scripts/generate-sbom.py   # → sbom.json (CycloneDX 1.5)
```

`audit-deps` 는 세 가지를 봅니다 — Python 의존성 · Node 의존성 ·
**베이스 이미지 다이제스트 드리프트**(고정한 `@sha256:` 이 상위 태그와 달라졌는지).
로컬에 Python·Node 를 설치할 필요 없이 컨테이너에서 돕니다.

### 로그

`logs/app.jsonl` 에 구조화 JSON으로 기록되며 일 단위 로테이션·90일 보존입니다.
API 키와 좌표 원문은 마스킹되어 기록되지 않습니다.

### 정지 / 초기화

```bash
docker compose down                          # 데이터 유지
docker compose down && rm -rf data/* logs/*  # 완전 초기화
```

---

## 비용 통제

인증 정보를 넣으면 외부 API 호출이 실제 비용으로 이어집니다. 기본값으로 다음 상한이 걸려 있습니다.

| 항목 | 기본값 | 설정 키 |
|---|---|---|
| AI 생성 (IP당) | 5회/시간 | `RATE_EXPENSIVE_PER_HOUR` |
| AI 생성 (전역) | **50회/일** | `RATE_EXPENSIVE_GLOBAL_PER_DAY` |
| 검색·경로 (IP당) | 60회/분 | `RATE_EXTERNAL_PER_MIN` |
| 지역검색 쿼터 | 25,000회/일 | `QUOTA_NAVER_LOCAL_PER_DAY` |
| 여행 규모 | 10일 / 하루 15곳 | `MAX_TRIP_DAYS`, `MAX_ITEMS_PER_DAY` |

전역 일일 상한은 **DB에 기록되어 재시작으로 초기화되지 않습니다.**
외부 응답은 캐시되며(지역검색 7일 / 경로 1일), 경로 API 호출은 항목 수에 비례(`O(n)`)하도록 설계되어 있습니다.

---

## 🔴 외부에 공개하기 전에 반드시 필요한 것

현재 구성은 **로컬 사용 전용**입니다. 인터넷에 노출하려면 아래가 **모두** 선행되어야 합니다.
하나라도 빠지면 공개해서는 안 됩니다.

1. **리버스 프록시 + TLS 종단** — 현재 구성에 HTTPS가 없습니다
2. **인증 도입** — 지금은 로그인이 없어 UUID만 알면 누구나 접근합니다
3. **시크릿 관리** — `.env` 파일 대신 시크릿 매니저
4. **다중 인스턴스 전환 준비** — 서킷 브레이커·레이트 리밋·작업 세마포어가 프로세스 내 상태입니다.
   **워커를 늘리면 이 통제들이 오류 없이 조용히 무력화됩니다.** Redis + PostgreSQL 전환이 선행되어야 합니다
5. **레이트 리밋 재검토** — 현재 값은 개인 사용 기준입니다
6. **지도 SDK 키 도메인 화이트리스트** 등록
7. **백업 자동화** — 현재는 수동 스크립트만 제공합니다

---

## 운영

일상 운영·백업·실 API 전환·장애 대응·프로덕션 준비도는
**[운영 가이드](aidlc-docs/operations/operations-guide.md)** 에 정리돼 있습니다.

- 백업은 반드시 `scripts/backup-db.*` 로 하세요 — `data/` 폴더 복사는 백업이 아닙니다 (WAL)
- 브라우저 데이터를 지우면 여행 목록이 사라집니다. 서버 백업으로는 막을 수 없습니다
- APK 를 새로 배포할 때마다 `android/README.md` 의 **실기기 체크리스트 8항목**을 확인하세요

---

## 문서

| 문서 | 내용 |
|---|---|
| [`aidlc-docs/aidlc-state.md`](aidlc-docs/aidlc-state.md) | 진행 상태와 모든 결정 요약 |
| [`aidlc-docs/audit.md`](aidlc-docs/audit.md) | 전체 의사결정 감사 추적 |
| [`aidlc-docs/inception/requirements/requirements.md`](aidlc-docs/inception/requirements/requirements.md) | 요구사항 FR 34 / NFR 15 / SEC 15 |
| [`aidlc-docs/inception/application-design/`](aidlc-docs/inception/application-design/) | 컴포넌트 설계 · 유닛 분해 |
| [`aidlc-docs/construction/u1-trip-backend/`](aidlc-docs/construction/u1-trip-backend/) | u1 상세 설계 · 비즈니스 규칙 BR-01~60 |
| [`aidlc-docs/construction/u2-trip-web/`](aidlc-docs/construction/u2-trip-web/) | u2 화면 설계 · 규칙 WBR-01~42 |
| [`aidlc-docs/construction/u3-trip-android/`](aidlc-docs/construction/u3-trip-android/) | u3 앱 설계 · 규칙 ABR-01~43 |
| [`aidlc-docs/construction/build-and-test/`](aidlc-docs/construction/build-and-test/) | **빌드·테스트 실측 결과** · SBOM · 발견한 결함 6건 |
| [`aidlc-docs/operations/operations-guide.md`](aidlc-docs/operations/operations-guide.md) | **운영 가이드** — 백업 · 장애 대응 · 프로덕션 준비도 |
| [`android/README.md`](android/README.md) | 안드로이드 빌드 · **실기기 확인 체크리스트 8항목** |

---

## 알려진 제약

| 제약 | 내용 |
|---|---|
| **대중교통 경로** | 네이버 공식 API 없음. 앱 내부는 추정치, 정확한 안내는 딥링크 위임 |
| **영업시간** | 지역검색이 제공하지 않음. 사용자 입력 시에만 경고 |
| **해외 여행** | 미지원 (국내 전용) |
| **다중 사용자** | 로그인·협업 편집 없음 |
| **오프라인** | 저장된 일정 조회만. 지도·검색·AI는 온라인 필요 |
| **좌표계** | 지역검색 `mapx`/`mapy` 해석은 **실응답으로 검증 전**입니다. 변환은 `to_wgs84()` 한 함수에 격리되어 있습니다 |

---

## 라이선스

**GNU General Public License v3.0** — 전문은 [`LICENSE`](LICENSE) 에 있습니다.

```
trip — 여행 일정 생성 + 시간표 + 네이버지도 연동 웹·안드로이드 애플리케이션
Copyright (C) 2026  HSLee

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
```

### 무엇을 뜻하나요

| 할 수 있는 것 | 조건 |
|---|---|
| 사용 · 복제 · 수정 · 배포 · 상업적 이용 | **수정본을 배포할 때 소스를 GPL-3.0 으로 함께 공개**해야 합니다 |

> ⚠️ **네트워크 서비스는 배포가 아닙니다.** 누군가 이 코드를 고쳐 자기 서버에 올리고
> 서비스만 제공하는 경우, GPL-3.0 은 소스 공개를 요구하지 않습니다.
> 그것까지 막으려면 AGPL-3.0 이 필요합니다 — 의도적으로 GPL-3.0 을 선택했습니다.

### 의존성 라이선스

런타임 의존성은 전부 허용형이라 GPL-3.0 과 충돌하지 않습니다.

| 구성 | 라이선스 |
|---|---|
| FastAPI · Starlette · Pydantic · SQLAlchemy · httpx | MIT / BSD |
| React · Vite · TanStack Query · Zustand · dnd-kit | MIT |
| Kotlin · AndroidX · Material | Apache-2.0 |

전체 목록은 [SBOM](aidlc-docs/construction/build-and-test/sbom/) 에 있습니다
(CycloneDX 1.6, 백엔드 57 · 웹 20 컴포넌트).

> 네이버 지도·검색 API 와 Claude API 는 **각자 발급받아 사용**합니다.
> 이 저장소는 그 서비스들의 이용 약관에 어떤 권리도 부여하지 않습니다.
