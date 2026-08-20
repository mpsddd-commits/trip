# Requirements Verification Questions — trip

**Stage**: 🔵 INCEPTION - Requirements Analysis (Comprehensive Depth)
**Generated**: 2026-08-13T03:39:29Z
**Status**: ⛔ 답변 대기 중

---

## 📌 답변 방법

각 질문의 `[Answer]:` 태그 **뒤에** 알파벳 한 글자를 적어주세요. 예: `[Answer]: A`
선택지 중 맞는 것이 없으면 마지막 `X) Other` 를 고르고 태그 뒤에 직접 설명해 주세요. 예: `[Answer]: X - 카카오맵도 같이 쓰고 싶음`
전부 작성하신 뒤 채팅에 **"완료"** 라고 알려주시면 다음 단계로 진행합니다.
빠르게 진행하고 싶으시면 **"전부 추천안(⭐)으로"** 라고만 알려주셔도 됩니다.

---

## 🔎 사전 조사 결과 (답변 전 꼭 읽어주세요)

요청하신 "네이버지도 연계"는 **하나의 API가 아니라 서로 다른 3개 서비스의 조합**이며, 각각 발급처·비용·제약이 다릅니다.
아래 표가 Q5~Q8, Q10 답변의 근거가 됩니다.

| # | 서비스 | 발급처 | 이 프로젝트에서의 용도 | 핵심 제약 |
|---|---|---|---|---|
| ① | **Maps — Web Dynamic Map** | 네이버 클라우드 플랫폼(NCP) | 웹 화면에 지도 렌더링, 마커, 경로 폴리라인 | 무료 쿼터 초과 시 과금. 결제수단 등록 필요 |
| ② | **Maps — Mobile Dynamic Map (Android SDK)** | NCP | 안드로이드 **네이티브** 지도 화면 | 안드로이드 네이티브 개발 시에만 해당 |
| ③ | **Maps — Directions 5 / 15** | NCP | 지점 간 **경로 좌표 + 소요시간 + 거리** | ⚠️ **자동차 경로만 제공. 대중교통·도보 경로 공식 API 없음** |
| ④ | **Maps — Geocoding / Reverse Geocoding** | NCP | 주소 ↔ 좌표 변환 | — |
| ⑤ | **검색 API — 지역(local)** | 네이버 개발자센터 | 장소명·주소·카테고리·전화·좌표 조회 | ⚠️ **1회 최대 5건**, 일 25,000회 |
| ⑥ | **검색 API — 블로그 / 이미지** | 네이버 개발자센터 | 장소 리뷰·사진 기반 추천 보강 | 일 25,000회 |
| ⑦ | **네이버지도 앱 딥링크 (`nmap://`)** | 발급 불필요 | 앱/웹에서 **네이버지도 앱을 직접 실행**해 길찾기·장소보기 | ⚠️ **대중교통 길찾기는 이 방법으로만 가능**. 앱 미설치 시 폴백 필요 |

> **결론**: "대중교통 기준 이동시간"까지 앱 안에서 계산하려면 공식 네이버 API로는 불가능하며,
> ⑦ 딥링크로 네이버지도 앱에 넘기거나 / 별도 데이터 소스를 쓰거나 / 자동차·도보 기준으로 근사해야 합니다. → **Q7에서 결정**

---

## Question 1
프로젝트 워크스페이스 루트를 `c:\Users\403\IDE\trip` 으로, AI-DLC 문서를 `trip/aidlc-docs/` 에 두는 구성이 맞습니까?

A) ⭐ 예 — `trip/` 을 독립 워크스페이스 루트로 사용 (애플리케이션 코드도 `trip/` 아래)

B) 아니오 — 상위 `c:\Users\403\IDE` 를 루트로 쓰고 `trip/` 은 하위 모듈로만 취급

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 2
이 앱의 **주 사용 지역**은 어디입니까? (네이버지도는 국내 데이터가 압도적으로 정확하고, 해외는 경로·장소 API 지원이 제한적입니다)

A) ⭐ 국내(한국) 여행 전용

B) 국내 + 해외 (해외는 지도 표시만, 경로/추천은 제한적으로)

C) 해외 여행 위주

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 3
**여행 일정(itinerary)을 만드는 방식**은 무엇입니까? 이 선택이 시스템 복잡도를 가장 크게 좌우합니다.

A) ⭐ **AI 자동 생성** — 사용자가 목적지·기간·인원·취향(맛집/자연/역사 등)·예산을 입력하면 LLM이 일자별 일정 초안을 생성하고, 사용자가 드래그로 수정

B) **수동 작성 + 추천 보조** — 사용자가 장소를 직접 검색해 담고, 시스템은 순서 최적화와 근처 추천만 제공 (LLM 불필요)

C) **템플릿 기반** — 미리 정의된 코스(예: "부산 2박3일 미식")를 고르고 커스터마이즈 (LLM 불필요)

D) A + B + C 전부

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 4
Q3에서 AI 자동 생성(A 또는 D)을 선택하셨다면, **어떤 LLM**을 사용합니까? (아니라면 D를 선택하세요)

A) ⭐ **Claude API** (Anthropic) — `claude-sonnet-5` 등, API 키 필요

B) OpenAI API

C) 로컬 LLM (Ollama 등)

D) LLM 사용 안 함 (Q3에서 B 또는 C 선택)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 5
**네이버 클라우드 플랫폼(NCP) Maps** 계정/키를 이미 보유하고 계십니까? (지도 렌더링·경로 계산에 필수)

A) ⭐ 보유하고 있음 — 발급받은 Client ID/Secret 을 `.env` 에 넣어 사용

B) 아직 없음 — **발급 안내 문서를 만들고, 키 없이도 앱이 동작하도록 목(mock) 데이터 폴백 모드를 구현**

C) 발급할 계획 없음 — 네이버지도 **앱 딥링크(`nmap://`)만** 사용하고 자체 지도 렌더링은 하지 않음 (비용 0원)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 6
**네이버 개발자센터 검색 API**(지역/블로그/이미지) 키를 보유하고 계십니까? (장소 검색·추천에 사용)

A) ⭐ 보유하고 있음

B) 아직 없음 — 발급 안내 + 목 데이터 폴백 모드 구현

C) 사용하지 않음 — 장소 데이터는 다른 소스(Q8)에서만 확보

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 7
⚠️ **가장 중요한 결정**: 사전 조사 ③⑦번 항목대로 **대중교통 경로/소요시간 API는 네이버 공식 제공이 없습니다.** 어떻게 처리할까요?

A) ⭐ **하이브리드** — 앱 내부 시간표는 Directions API(**자동차 기준**) + 도보 근사치로 계산해 표시하고, 사용자가 "길찾기" 버튼을 누르면 **네이버지도 앱 딥링크로 넘겨 실제 대중교통 안내**를 받게 함 (앱 미설치 시 웹 지도로 폴백)

B) **자동차 기준만** — 렌터카/자차 여행 전제. Directions API 결과를 그대로 시간표에 사용

C) **도보/거리 근사만** — 외부 경로 API 없이 좌표 간 거리 × 평균 이동속도로 소요시간 추정 (API 비용 0원, 정확도 낮음)

D) **한국관광공사·대중교통 공공데이터(TAGO/ODsay 등) 추가 연동**으로 대중교통 소요시간을 직접 계산 (별도 키 발급·구현량 증가)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 8
**장소 추천 콘텐츠**(맛집 메뉴, 명소 설명, 사진)는 어디에서 가져옵니까? (복수 선택 원하시면 X에 적어주세요)

A) ⭐ **네이버 검색 API 조합** — 지역검색(좌표·카테고리) + 블로그검색(리뷰 요약) + 이미지검색(썸네일)

B) **한국관광공사 TourAPI(공공데이터포털)** — 관광지·음식점·숙박 공식 데이터, 무료, 국내 한정

C) **LLM 지식만** — 별도 API 없이 모델이 아는 명소/메뉴를 생성 (⚠️ 최신성·정확성 보장 안 됨, 폐업 정보 가능)

D) A + B 조합 (네이버 = 실시간성, TourAPI = 신뢰성)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 9
**시간표(타임라인) 화면**에 반드시 들어가야 할 항목은 무엇입니까?

A) ⭐ 시각 + 장소명 + 체류시간 + **이동수단/이동시간** + 메모

B) A + **영업시간 검증**(문 닫은 시간에 배정되면 경고) + 예상 비용

C) A + B + **날씨 정보** 연동

D) 시각과 장소명만 있는 간단한 목록

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 10
**지도 화면에서 "시간 순서 이동경로"**를 어떻게 시각화합니까?

A) ⭐ 번호 마커(①②③…) + **경로 폴리라인** + 일자별 색상 구분 + 마커 클릭 시 장소 상세 패널

B) A + **타임라인 슬라이더**로 시간대별 애니메이션 재생

C) 번호 마커만 (경로선 없음 — Directions API 호출 없이 비용 절감)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 11
**일정 순서 최적화**(방문 순서를 자동으로 재배열해 이동거리·시간 최소화) 기능이 필요합니까?

A) ⭐ 예 — 일자별로 "순서 최적화" 버튼 제공 (외판원 문제 근사 알고리즘)

B) 예 + 숙소를 시작/종료점으로 고정하는 제약 조건 포함

C) 아니오 — 사용자가 정한 순서 그대로 유지

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 12
"**안드로이드 연동 웹/어플리케이션**"의 구체적 형태는 무엇입니까? 이것이 프로젝트 구조를 결정합니다.

A) ⭐ **웹앱 + 안드로이드 WebView 래퍼** — 반응형 웹앱 하나를 만들고, 얇은 Kotlin WebView 앱으로 감싸 APK 배포. 네이버지도 앱 딥링크는 네이티브 브리지로 처리. (구현량 최소, 기능 대부분 확보)

B) **PWA(설치형 웹앱)** — 별도 안드로이드 프로젝트 없이 홈 화면 설치 + 오프라인 캐시. APK 없음

C) **웹 + 안드로이드 네이티브 앱 별도 구현** — 백엔드 API 공유, 안드로이드는 Kotlin + Naver Map Android SDK 로 풀 네이티브 (최고 품질, 구현량 최대)

D) **Capacitor / React Native 크로스플랫폼**

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 13
⚠️ **환경 제약 확인**: 현재 이 PC에는 **JDK와 Android SDK가 설치되어 있지 않습니다.** 따라서 제가 APK를 실제로 빌드하거나 에뮬레이터로 검증할 수 없습니다. 안드로이드 산출물을 어느 수준까지 만들까요?

A) ⭐ **소스 + 빌드 설정 완성 + 빌드 안내서 제공** — Gradle 프로젝트·매니페스트·Kotlin 코드를 전부 생성하되, 실제 APK 빌드는 사용자가 Android Studio에서 수행. Build & Test 단계에서 **웹 부분만 실측 검증**

B) **JDK/Android SDK를 먼저 설치**하고 진행 — 설치 후 제가 APK 빌드까지 실측 검증 (설치에 시간 소요, 용량 수 GB)

C) **안드로이드 산출물 제외** — 이번 사이클은 반응형 웹/PWA 까지만 만들고, 안드로이드는 다음 사이클로 미룸

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 14
**백엔드 기술 스택**은 무엇으로 합니까?

A) ⭐ **Python + FastAPI** (기존 news 프로젝트와 동일 계열 — 팀 숙련도 재사용)

B) **Node.js + NestJS** (프론트와 언어 통일, 이 PC에 Node v24 설치됨)

C) **Java + Spring Boot** (⚠️ 현재 JDK 미설치)

D) **백엔드 없음** — 프론트엔드에서 API 직접 호출 + 브라우저 로컬 저장 (⚠️ API 키가 클라이언트에 노출됨)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 15
**프론트엔드 기술 스택**은 무엇으로 합니까?

A) ⭐ **React + TypeScript + Vite** (드래그앤드롭 일정 편집·지도 상호작용에 적합)

B) **Next.js** (SSR/SEO 필요 시)

C) **서버사이드 템플릿**(Jinja2/Thymeleaf) + 최소 JS (구현 단순, 상호작용 제한적)

D) **Vue 3 + Vite**

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 16
**사용자 인증/계정** 기능이 필요합니까?

A) ⭐ **없음(단일 사용자)** — 로그인 없이 사용, 일정은 로컬/서버에 익명 저장. 개인정보 처리 없음

B) **이메일 + 비밀번호 자체 회원가입**

C) **네이버 로그인(OAuth)** 연동

D) 익명 사용 + 일정 공유용 **비밀 링크(UUID)** 만 제공

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 17
**데이터 저장소**는 무엇으로 합니까?

A) ⭐ **SQLite 단일 파일** (로컬 실행, 백업 간단)

B) **PostgreSQL** (Docker Compose 로 함께 기동)

C) **브라우저 로컬 저장만** (IndexedDB/localStorage — 서버 DB 없음, 기기 간 동기화 불가)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 18
**일정 내보내기/공유** 기능 범위는?

A) ⭐ **공유 링크 + 캘린더(.ics) 내보내기**

B) A + **PDF/이미지 형태 여행 일정표 저장**

C) 내보내기 없음 — 앱 내에서만 조회

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 19
**오프라인 사용**(비행기/데이터 없는 환경에서 저장된 일정 조회)을 지원해야 합니까?

A) ⭐ **부분 지원** — 일정·시간표 텍스트는 오프라인 조회 가능, 지도는 온라인 필요

B) **완전 지원** — 지도 타일까지 캐싱 (구현 복잡도·저장공간 크게 증가)

C) 미지원 — 항상 온라인 전제

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 20
**배포/실행 환경**은 어떻게 합니까?

A) ⭐ **로컬 Docker Compose** — `127.0.0.1:8200` 바인딩 (기존 petmate 8000/5173, news 8100 과 충돌 회피)

B) **로컬 직접 실행**(Docker 없이 `npm run dev` / `uvicorn`)

C) **클라우드 배포**(AWS/Vercel 등)까지 포함

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 21
**API 키·시크릿 취급 방침**은? (⚠️ 네이버 지도 Web Dynamic Map 키는 구조상 브라우저에 노출되며, 이는 **도메인/앱 패키지명 화이트리스트**로 방어합니다. 반면 검색 API·LLM 키는 절대 노출되면 안 됩니다)

A) ⭐ **검색 API·LLM 키는 백엔드에서만 사용**하고 프론트는 자체 백엔드만 호출. 지도 키는 프론트 노출 + 도메인 제한 설정 안내 문서 제공

B) 전부 프론트에서 직접 호출 (개인용 로컬 전용, 편의 우선 — ⚠️ 키 유출 위험 감수)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 22
**테스트 범위**는 어디까지 합니까?

A) ⭐ **단위 테스트 중심** — 일정 생성 로직·순서 최적화·시간 계산·외부 API 클라이언트(응답 목킹). 네트워크 비의존

B) A + **E2E 테스트**(Playwright 로 브라우저 시나리오 검증)

C) A + B + **실제 외부 API 통합 테스트**(⚠️ 실 API 쿼터 소모)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 23
## Security Extensions
Should security extension rules be enforced for this project?
(이 프로젝트에 보안 확장 규칙을 강제할까요?)

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
　⭐ 참고: 이 프로젝트는 외부 API 키·개인 여행 일정을 다루므로 권장됩니다

B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 24
## Resiliency Extensions
Should the resiliency baseline be applied to this project?
(이 프로젝트에 복원력(resiliency) 기준선을 적용할까요?)

**이 확장이 무엇인가**: AWS Well-Architected Framework(신뢰성 기둥)에서 파생된 **설계 시점의 방향성 모범사례** 모음을 적용합니다. 내결함성·고가용성·관측가능성·복구가능성 방향으로 요구사항·설계·코드를 유도합니다.

**이 확장이 아닌 것**: 활성화한다고 워크로드가 프로덕션 준비 완료가 되거나 특정 가용성·RTO·RPO 목표가 보증되지 않습니다. 정식 AWS Well-Architected Review 를 대체하지 않습니다.

A) Yes — 복원력 기준선을 설계 지침으로 적용 (업무상 중요한 워크로드에 권장)

B) ⭐ No — 복원력 기준선 생략 (PoC·프로토타입·개인 프로젝트에 적합)
　참고: 외부 API 의존이 많아 **재시도·타임아웃·폴백은 확장과 무관하게 기본 요구사항(NFR)으로 이미 반영**할 예정입니다

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## Question 25
## Property-Based Testing Extension
Should property-based testing (PBT) rules be enforced for this project?
(속성 기반 테스트 규칙을 강제할까요?)

A) Yes — 모든 PBT 규칙을 차단 제약으로 강제 (비즈니스 로직·데이터 변환·직렬화·상태 컴포넌트가 있는 프로젝트에 권장)

B) ⭐ Partial — 순수 함수와 직렬화 왕복에 대해서만 PBT 적용
　참고: 이 프로젝트의 **순서 최적화·시간 계산 로직**은 PBT 효과가 큰 영역입니다

C) No — PBT 규칙 전부 생략 (단순 CRUD·UI 전용·얇은 통합 계층에 적합)

X) Other (please describe after [Answer]: tag below)

[Answer]:

---

## ✅ 답변 완료 후

채팅에 **"완료"** 라고 알려주세요. 제가 답변을 읽고 모순·모호성을 분석한 뒤,
문제가 없으면 `requirements.md`(FR/NFR/제약/범위제외)를 생성하고 승인을 요청합니다.
모순이 발견되면 `requirements-clarification-questions.md` 를 추가로 만들어 확인드립니다.
