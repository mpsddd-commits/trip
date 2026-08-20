# Functional Design Plan — u2-trip-web

**Stage**: 🟢 CONSTRUCTION - Functional Design (Unit 2/3)
**Created**: 2026-08-14T00:30:00Z
**Prior context**: u1 구현 완료(API 19개, OpenAPI 스키마 확정), `application-design/`, `unit-of-work*.md`
**Unit 책임**: W1~W16 (16 컴포넌트) · Owner FR 15건 · 참여 FR 14건 · SEC 부분 5건 · PBT-R 4건
**Status**: ⛔ 답변 대기 중

---

## 📌 답변 방법

`[Answer]:` 태그 뒤에 알파벳을 적어주세요. **"완료"** 또는 **"전부 추천안"** 이라고 알려주시면 산출물 4종을 생성합니다.

---

## 🔴 사전 분석에서 발견한 문제 2건 — 답변 전 꼭 읽어주세요

### 문제 1. 여행 목록 API가 없어서, 브라우저 데이터를 지우면 여행에 접근할 수 없습니다

**DD-21 / BR-39** 에 따라 백엔드는 `GET /api/trips`(목록)를 **의도적으로 제공하지 않습니다.**
계정이 없는 구성에서 목록 API는 열거 취약점이기 때문입니다. 이 결정은 유지되어야 합니다.

그 귀결로 **"내 여행 목록"은 브라우저 로컬 저장소의 `trip_id` 집합**으로만 구성됩니다. 따라서:

| 상황 | 결과 |
|---|---|
| 브라우저 데이터 삭제 / 시크릿 모드 종료 | **여행에 다시 접근할 수 없음** (서버에는 남아 있으나 UUID를 모름) |
| 다른 기기·브라우저에서 접속 | 목록이 비어 있음 |
| 안드로이드 앱 ↔ PC 브라우저 | 목록이 공유되지 않음 |

설계상 예견된 결과이지만, **사용자에게는 데이터 유실로 보입니다.** → **Q3에서 완화책을 결정합니다.**

### 문제 2. 지도 SDK 키를 프론트에 전달할 경로가 아직 없습니다

`NCP_MAP_CLIENT_KEY` 는 구조상 브라우저에 노출됩니다(CON-3). 그런데 현재 u1은
`/api/health/ready` 에서 **`map_client_key_configured` (불리언)만** 노출하고 키 값은 주지 않습니다.

전달 방법은 두 가지이고 성격이 다릅니다.

| 방식 | 장점 | 단점 |
|---|---|---|
| **빌드 시 주입** (`VITE_MAP_CLIENT_KEY`) | 런타임 요청 불필요 | **키를 바꿀 때마다 이미지 재빌드**. `.env` 만 고쳐서는 반영 안 됨 |
| **런타임 설정 엔드포인트** (`GET /api/config`) | `.env` 수정 후 재시작만으로 반영. 목 모드 배너도 같이 전달 | 최초 렌더 전에 요청 1회 필요 |

→ **Q4에서 결정합니다.** (선택에 따라 u1에 엔드포인트 1개 추가가 필요합니다)

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [ ] u1 OpenAPI 스키마에서 엔드포인트 19개와 응답 형태 확인
- [ ] Owner FR 15건 + 참여 FR 14건의 화면 귀속 확인
- [ ] W1~W16 컴포넌트별 책임 재확인
- [ ] u3와의 브리지 계약 3종(`openMap`/`share`/`requestLocation`) 확인

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [ ] Q1~Q4 데이터 흐름·상태·설정 전달
- [ ] Q5~Q8 화면 구조와 상호작용
- [ ] Q9~Q12 지도·딥링크 통합
- [ ] Q13~Q15 오류·오프라인·degrade 표현
- [ ] Q16~Q18 기술 선택과 접근성

### 1.3 필수 산출물 생성
- [ ] `construction/u2-trip-web/functional-design/domain-entities.md` — 클라이언트 타입·상태 소유권
- [ ] `construction/u2-trip-web/functional-design/business-logic-model.md` — 화면 흐름·알고리즘·**Testable Properties**
- [ ] `construction/u2-trip-web/functional-design/business-rules.md` — WBR-xx 규칙 + FR 추적
- [ ] `construction/u2-trip-web/functional-design/frontend-components.md` — **컴포넌트 계층·props/state·상호작용·폼 검증·API 연결점**

### 1.4 검증
- [ ] Owner FR 15건 전부 규칙으로 표현
- [ ] u1 API 19개의 소비 지점 매핑
- [ ] Security / PBT Compliance 요약

---

## Part 2. 설계 질문

### 🔄 데이터 흐름·상태·설정

## Question 1
**서버 데이터 캐시 키 설계**를 어떻게 합니까? (W2 TanStack Query)

A) ⭐ **자원 계층 키** — `['trip', tripId]` / `['job', jobId]` / `['placeContent', placeId]` / `['placeSearch', query, page]`. 편집 후에는 **`['trip', tripId]` 만 무효화**하고 나머지는 유지
　→ 백엔드가 편집 API에서 **여행 전체를 반환**하므로(u1 구현), 응답으로 캐시를 직접 갱신해 추가 요청이 발생하지 않습니다

B) 단일 키에 전체 상태를 담고 매번 전체 무효화

C) 캐시 없이 매번 요청

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
**AI 생성 job 폴링 정책**은? (FR-2, DD-5 — 최대 60초)

A) ⭐ **적응형 간격 + 상한** — 처음 10초는 1초 간격, 이후 2초 간격, **총 90초 초과 시 중단하고 "시간이 오래 걸립니다" 안내**. 탭이 백그라운드면 폴링을 멈추고 복귀 시 재개
　→ 서버 부하와 반응성의 균형. 무한 폴링으로 방치되는 상황을 막습니다

B) 고정 1초 간격, 무기한

C) 고정 5초 간격

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
🔴 **위 문제 1 참조**: 브라우저 데이터를 지우면 여행에 접근할 수 없습니다. 어떻게 완화합니까?

A) ⭐ **로컬 목록 + 명시적 경고 + 공유 링크 안내** — 여행 목록을 `localStorage` 에 보관하되,
　① 첫 여행 생성 시 "이 브라우저에만 저장됩니다" 안내
　② 목록 화면에 상시 고지
　③ **각 여행에서 공유 링크를 만들어 두면 어디서든 열 수 있다**는 점을 안내(FR-25 재활용)
　④ 여행 목록을 **JSON 파일로 내보내기/가져오기** 제공
　→ 백엔드 변경 없이 완화. DD-21(열거 차단)을 유지합니다

B) **백엔드에 목록 API 추가** — UX는 좋아지나 **DD-21·BR-39·SEC-08 을 뒤집습니다**(열거 취약점)

C) **로그인 도입** — Q16=A(인증 없음), OUT-2 를 뒤집습니다. 범위가 크게 늘어납니다

D) 완화 없이 로컬 목록만 (사용자가 모른 채 잃음)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
🔴 **위 문제 2 참조**: 지도 SDK 키를 프론트에 어떻게 전달합니까?

A) ⭐ **런타임 설정 엔드포인트 `GET /api/config` 를 u1에 추가** — 지도 키 + 목 모드 현황 + 규모 상한을 한 번에 내려줍니다. `.env` 수정 후 재시작만으로 반영되고, 이미지 재빌드가 필요 없습니다
　→ u1에 엔드포인트 **1개 추가**가 필요합니다(엔드포인트 19 → 20)

B) **빌드 시 주입** (`VITE_MAP_CLIENT_KEY`) — 런타임 요청이 없으나, 키를 바꿀 때마다 **이미지 재빌드**가 필요합니다

C) `/api/health/ready` 를 확장해 키를 포함 — 헬스체크에 비밀성 있는 값을 섞는 것은 관심사 혼재

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🖥️ 화면 구조와 상호작용

## Question 5
**화면(라우트) 구성**을 어떻게 합니까?

A) ⭐ **4개 라우트** — `/`(내 여행 목록) · `/trips/new`(생성 마법사) · `/trips/:id`(**메인 — 타임라인+지도 통합**) · `/shared/:token`(읽기 전용)
　→ 메인 화면 하나에서 편집과 지도를 함께 보는 구조. 화면 전환 없이 작업이 이어집니다

B) 타임라인과 지도를 **별도 라우트**로 분리 (`/trips/:id/timeline`, `/trips/:id/map`)

C) 단일 페이지에 모든 것 (목록·생성·편집)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
메인 화면에서 **타임라인과 지도의 배치**는? (NFR-5 — 최소 360px 지원)

A) ⭐ **반응형 2단 → 탭 전환** — 데스크톱(≥1024px)은 좌 타임라인 / 우 지도 2단, 태블릿·모바일은 **하단 탭으로 전환**하되 선택 항목은 양쪽에서 유지
　→ 모바일에서 두 패널을 억지로 나누면 둘 다 못 쓰게 됩니다

B) 항상 2단 (모바일에서 매우 좁아짐)

C) 지도를 배경으로 깔고 타임라인을 오버레이 시트로

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
**드래그 앤 드롭 순서 변경**(FR-5)의 상호작용 규칙은?

A) ⭐ **낙관적 업데이트 + 실패 시 롤백** — 드롭 즉시 화면 반영(W3 임시 상태), 서버 응답으로 확정. 실패하면 원래 순서로 되돌리고 토스트. **오프라인이면 드래그 자체를 비활성화**(FR-32)
　→ 체감 반응성을 확보하면서 불일치를 남기지 않습니다

B) 서버 응답을 기다린 뒤 반영 (안전하나 느림)

C) 로컬에만 반영하고 "저장" 버튼으로 일괄 전송

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8
**일자 간 항목 이동**(FR-5)을 지원합니까?

A) ⭐ **지원 — 드래그로 다른 일자 탭에 드롭** + 컨텍스트 메뉴의 "다른 날로 이동"
　→ 모바일에서 드래그로 일자를 넘기기 어려우므로 메뉴 경로를 함께 제공합니다

B) 컨텍스트 메뉴로만 지원

C) 미지원 (같은 일자 내 순서 변경만)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🗺️ 지도·딥링크 통합

## Question 9
**지도 SDK 로딩 실패** 시 어떻게 합니까? (키 없음 / 네트워크 / 도메인 미등록)

A) ⭐ **지도 영역만 대체 표시** — "지도를 불러올 수 없습니다" + 사유 + **장소 목록은 그대로 사용 가능**. 타임라인 편집은 영향 없음
　→ NFR-3 degrade 원칙과 동일. 지도가 없다고 일정 편집이 막히면 안 됩니다

B) 전체 화면 오류

C) 정적 지도 이미지로 폴백 (별도 API 필요)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
**마커 번호와 일자 색상**(FR-15)을 어떻게 표현합니까? (NFR-6 — 색상만으로 정보 전달 금지)

A) ⭐ **번호 + 색상 + 일자 배지 3중** — 마커에 방문 순번(①②③), 일자별 색상, 그리고 **일자 라벨("1일차")을 툴팁·범례에 병기**
　→ 색각 이상 사용자도 번호와 라벨로 구분할 수 있습니다

B) 색상만 (NFR-6 위반)

C) 번호만 (일자 구분 불가)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
**대중교통 구간 표시**(FR-12, BR-27)를 어떻게 합니까?

A) ⭐ **점선 + "추정" 배지 + 딥링크 버튼** — 지도에는 점선(실경로 없음), 타임라인에는 소요시간 옆 "추정" 배지와 **"네이버지도로 길찾기"** 버튼
　→ CON-1(네이버가 대중교통 경로 API를 제공하지 않음)을 사용자에게 정직하게 드러냅니다

B) 실선으로 그리고 배지 없음 (⚠️ 추정치를 확정처럼 보이게 함)

C) 대중교통 구간은 아예 표시하지 않음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 12
**딥링크 실행**(FR-23, FR-24)의 폴백 순서는?

A) ⭐ **네이티브 브리지 → 앱 스킴 → 웹** — ① 안드로이드 앱이면 브리지로 위임(W14) ② 아니면 `nmap://` 시도 후 일정 시간 내 이탈이 없으면 ③ `map.naver.com` 웹으로 이동
　→ 브라우저에서 앱 스킴이 실패해도 사용자가 빈 화면을 보지 않습니다

B) 항상 웹으로만

C) 앱 스킴만 시도 (미설치 시 아무 반응 없음)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### ⚠️ 오류·오프라인·degrade 표현

## Question 13
**`partial` 결과**(DD-23)를 사용자에게 어떻게 알립니까?

A) ⭐ **구체적으로 알림** — "일정을 만들었습니다. 다만 **3곳을 찾지 못했고**, 일부 이동시간은 추정치입니다." + **"확인 필요" 목록을 접이식 패널로 상시 노출** + 각 항목에 "직접 검색해 담기" 버튼
　→ 미해결 장소가 조용히 사라지지 않게 합니다 (FR-3, BR-18의 사용자 측 대응)

B) "일부 실패" 정도로만 표시

C) `succeeded` 와 동일하게 표시 (미해결 목록을 숨김)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**목(mock) 데이터 모드**(FR-33)를 어떻게 표시합니까?

A) ⭐ **상시 배너 + 어떤 API가 데모인지 명시** — 화면 상단에 닫을 수 없는 배너로 "데모 데이터로 동작 중입니다(장소 검색·AI 생성)" + 설정 안내 링크
　→ 데모 데이터를 실제 정보로 오해하는 것을 막습니다

B) 최초 1회 토스트 후 사라짐

C) 표시하지 않음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 15
**오류 응답 표시**(BR-58 — 백엔드는 고정 문구 6종만 반환)를 어떻게 합니까?

A) ⭐ **고정 문구 + 상관관계 ID + 맥락 보강** — 백엔드 `detail` 을 그대로 보여주되, **어떤 동작이 실패했는지는 프론트가 안다**(예: "일정을 저장하지 못했습니다" + 백엔드 문구). `correlation_id` 는 접어둔 상세에 표시
　→ 백엔드는 내부를 숨기고, 프론트는 맥락을 더합니다

B) 백엔드 문구만 그대로

C) 프론트에서 임의 문구 생성 (백엔드 의미와 어긋날 위험)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🛠️ 기술 선택과 접근성

## Question 16
**오프라인 캐시 범위**(FR-31, Q16=A)는?

A) ⭐ **여행 상세만 persist** — `['trip', *]` 만 IndexedDB에 저장. **`['job', *]` 은 제외(DD-14)**, 검색 결과·추천 콘텐츠도 제외(용량·신선도)
　→ 오프라인에서 "내 일정 확인"이라는 핵심 시나리오만 보장합니다

B) 모든 쿼리 persist (용량 증가, 오래된 검색 결과 노출)

C) 여행 상세 + 추천 콘텐츠까지

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 17
**드래그 앤 드롭 라이브러리**를 무엇으로 합니까?

A) ⭐ **`@dnd-kit`** — 터치·키보드 접근성을 기본 지원(NFR-6). React 19 호환. 번들 크기 적정
　→ 키보드로 순서를 바꿀 수 있어야 접근성 요건을 충족합니다

B) HTML5 Drag and Drop API 직접 사용 (모바일 터치 미지원)

C) `react-beautiful-dnd` (유지보수 중단 상태)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 18
**접근성 수준**(NFR-6)을 어디까지 맞춥니까?

A) ⭐ **핵심 경로 키보드 완주 + 스크린리더 레이블 + 색상 비대체** — 생성→편집→조회 전 과정을 키보드로 수행 가능, 마커·항목에 aria-label, 색상 정보는 항상 텍스트 병기. 자동 검사(axe) 통과를 목표로 하되 **인증 수준은 주장하지 않음**

B) 시각적 대비만 확보

C) 전체 WCAG 2.1 AA 준수 선언 (검증 부담이 크고, 근거 없이 주장하면 허위가 됩니다)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

**"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.

> ⚠️ **Q3 과 Q4 는 특히 검토해 주세요.**
> Q3은 "여행이 사라져 보이는" 사용자 경험 문제이고, Q4는 **u1에 엔드포인트 1개를 추가할지** 여부입니다.
> 두 문제 모두 지금 결정하지 않으면 u2 구현 중에 임시방편으로 처리될 위험이 있습니다.
