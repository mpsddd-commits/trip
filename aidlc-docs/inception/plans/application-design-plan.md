# Application Design Plan — trip

**Stage**: 🔵 INCEPTION - Application Design
**Created**: 2026-08-13T04:20:00Z
**Prior context loaded**: `requirements.md` (FR 34 / NFR 15 / SEC 15 / PBT-R 8 / CON 8), `execution-plan.md` (유닛 3개 분해), `aidlc-state.md`
**Status**: ⛔ 답변 대기 중

---

## 📌 답변 방법

각 질문의 `[Answer]:` 태그 뒤에 알파벳을 적어주세요. 맞는 선택지가 없으면 `X` 를 고르고 직접 설명해 주세요.
작성 후 채팅에 **"완료"**, 또는 **"전부 추천안(⭐)으로"** 라고 알려주시면 진행합니다.

---

## Part 1. 실행 계획 (체크리스트)

### 1.1 분석
- [ ] `requirements.md` 의 FR 34건을 기능 영역으로 군집화
- [ ] 유닛 3개(u1/u2/u3) 경계와 기능 영역 매핑
- [ ] 외부 시스템 4종의 통합 지점 식별
- [ ] SEC-01~15 중 컴포넌트 수준에서 소유자가 필요한 통제 식별

### 1.2 설계 결정 (Part 2 질문으로 수집)
- [ ] Q1~Q4 컴포넌트 식별 및 조직화 방식 확정
- [ ] Q5~Q8 컴포넌트 메서드 및 인터페이스 계약 확정
- [ ] Q9~Q11 서비스 계층 오케스트레이션 방식 확정
- [ ] Q12~Q14 컴포넌트 의존성 및 통신 패턴 확정
- [ ] Q15~Q16 설계 패턴 및 아키텍처 스타일 확정

### 1.3 필수 산출물 생성
- [ ] `inception/application-design/components.md` — 컴포넌트 정의, 책임, 인터페이스
- [ ] `inception/application-design/component-methods.md` — 메서드 시그니처, 입출력 타입 (상세 비즈니스 규칙은 Functional Design 이월)
- [ ] `inception/application-design/services.md` — 서비스 정의, 책임, 오케스트레이션
- [ ] `inception/application-design/component-dependency.md` — 의존성 매트릭스, 통신 패턴, 데이터 흐름도
- [ ] `inception/application-design/application-design.md` — 위 4종 통합 문서 + 설계 결정(DD) 목록

### 1.4 검증
- [ ] 순환 의존성 0건 확인
- [ ] FR 34건 전부 최소 1개 컴포넌트에 매핑 (미매핑 0건)
- [ ] SEC 15건 각각 소유 컴포넌트 지정 또는 N/A 판정
- [ ] Functional Design 이월 항목 명시적 목록화
- [ ] **Security Compliance** 요약 작성 (blocking 확장)
- [ ] **PBT Compliance** 요약 작성 (Partial — PBT-01 property 후보 식별)

---

## Part 2. 설계 질문

### 📁 컴포넌트 식별 (Component Identification)

## Question 1
**백엔드(u1) 패키지 구성 기준**을 무엇으로 합니까?

A) ⭐ **계층 기준** — `api/`(라우터) · `services/`(오케스트레이션) · `domain/`(순수 로직) · `clients/`(외부 API) · `storage/`(영속화) · `core/`(설정·로깅·보안)
　→ 순수 도메인 로직(`domain/`)이 격리되어 PBT-R2 불변식 테스트가 쉬워집니다

B) **도메인 기준** — `trip/` · `place/` · `routing/` · `recommendation/` 각각 내부에 라우터·서비스·저장소를 둠

C) **하이브리드** — 도메인별로 나누되 외부 클라이언트와 코어는 공유 계층으로 분리

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
**외부 API 클라이언트 4종**(NCP Directions, 네이버 지역검색, 네이버 블로그·이미지 검색, Claude)을 어떻게 조직합니까?

A) ⭐ **공통 베이스 + 개별 클라이언트** — 재시도·타임아웃·로깅·쿼터 계측을 담은 `BaseHttpClient` 를 상속/합성하고, 각 API마다 전용 클라이언트 클래스를 둔다. 각 클라이언트는 **Protocol(인터페이스)로 추상화**해 테스트에서 목 구현으로 교체
　→ NFR-2·3·4와 FR-33(목 모드)이 한 곳에서 처리됩니다

B) **완전 독립** — 각 API마다 공유 없이 독립 클라이언트 (중복 발생, 단순)

C) **단일 파사드** — `ExternalApiGateway` 하나가 모든 외부 호출을 메서드로 노출

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 3
**FR-33 목(mock) 데이터 모드**를 어느 지점에서 구현합니까?

A) ⭐ **클라이언트 교체** — 기동 시 인증 정보 유무를 확인해 실제 구현체 또는 `Mock*Client` 를 주입(의존성 주입). 상위 서비스는 차이를 모름
　→ 서비스·도메인 코드에 `if mock:` 분기가 전혀 생기지 않습니다

B) **서비스 내부 분기** — 각 서비스에서 설정 플래그를 확인해 분기

C) **라우터 분기** — 목 모드 전용 라우터를 별도로 등록

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
**프론트엔드(u2) 폴더 구성 기준**을 무엇으로 합니까?

A) ⭐ **기능(feature) 기준** — `features/trip-create/` · `features/timeline/` · `features/map/` · `features/place-detail/` 각각에 컴포넌트·훅·타입을 두고, `shared/`(UI 기본요소·API 클라이언트·유틸)를 공유

B) **타입 기준** — `components/` · `hooks/` · `pages/` · `api/` · `utils/`

C) **페이지 기준** — 라우트 단위로만 분리

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔧 컴포넌트 메서드 및 인터페이스 (Component Methods)

## Question 5
⚠️ **NFR-1 은 AI 일정 생성에 최대 60초를 허용합니다.** HTTP 요청-응답을 그대로 60초 붙잡으면 프록시·브라우저 타임아웃과 사용자 이탈 위험이 있습니다. 어떻게 처리합니까?

A) ⭐ **비동기 작업 + 폴링** — `POST /trips/{id}/generate` 가 `job_id` 를 즉시 반환하고, 프론트가 `GET /jobs/{job_id}` 를 폴링해 진행 상태(초안 생성 중 → 장소 그라운딩 중 → 완료)를 표시
　→ 진행 표시(NFR-1) 요건을 자연스럽게 충족하고, 오래 걸리는 그라운딩 루프를 안전하게 담습니다

B) **SSE 스트리밍** — 서버가 진행 이벤트를 스트리밍 (구현 복잡도 증가, 프록시 환경 민감)

C) **동기 요청** — 단순하지만 60초 블로킹 (⚠️ 타임아웃 위험)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
**API 응답의 오류 포맷**을 무엇으로 합니까? (SEC-09: 내부 상세 미노출, SEC-15: 일반화된 사용자 메시지)

A) ⭐ **RFC 9457 Problem Details** — `{type, title, status, detail, instance}` + 프로젝트 확장 필드(`code`, `correlation_id`). 표준 포맷이라 프론트 처리 일관성 확보

B) **커스텀 포맷** — `{error: {code, message}}`

C) **FastAPI 기본** — `{detail: "..."}`

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 7
**백엔드 ↔ 프론트엔드 타입 계약**을 어떻게 유지합니까?

A) ⭐ **OpenAPI 자동 생성** — FastAPI 가 노출하는 OpenAPI 스키마에서 TypeScript 타입을 생성(`openapi-typescript`)하고, 생성 스크립트를 빌드 절차에 포함
　→ u1↔u2 계약 불일치(execution-plan §2 coordination point)를 기계적으로 차단

B) **수동 타입 정의** — 프론트에서 필요한 타입을 직접 작성

C) **공유 JSON Schema 파일** — 양쪽이 같은 스키마 파일을 읽음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 8
**`nmap://` 딥링크 URL 생성 책임**을 어디에 둡니까? (FR-23·24, u2·u3 양쪽에서 필요)

A) ⭐ **프론트엔드 공용 유틸** — `shared/deeplink.ts` 가 URL을 생성하고, 안드로이드는 이 URL을 브리지로 전달받아 인텐트만 실행. 로직 단일화 + 순수 함수라 단위 테스트 용이

B) **백엔드 생성** — API 응답에 딥링크 URL 포함

C) **각자 구현** — 웹과 안드로이드가 각각 생성

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🎯 서비스 계층 (Service Layer Design)

## Question 9
**AI 일정 생성 파이프라인**(FR-2 초안 → FR-3 그라운딩 → 일정 저장)을 어떤 구조로 오케스트레이션합니까?

A) ⭐ **명시적 단계 파이프라인** — `ItineraryGenerationService` 가 `LlmDraftGenerator` → `PlaceResolver`(그라운딩) → `TimelineCalculator` → `TripRepository` 를 순서대로 호출하고, 각 단계는 독립 컴포넌트로 단위 테스트 가능. 단계별 진행 상태를 job 에 기록(Q5=A와 연결)
　→ 최상위 위험 ①(LLM 환각)의 차단 지점인 그라운딩이 **독립 컴포넌트로 격리**되어 규칙 검증이 쉬워집니다

B) **단일 서비스 메서드** — 하나의 큰 메서드 안에서 순차 처리

C) **이벤트 기반** — 단계마다 이벤트를 발행하고 핸들러가 이어받음 (로컬 단일 프로세스에는 과함)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 10
**순서 최적화(FR-8)와 타임라인 계산(FR-9)** 로직을 어디에 둡니까?

A) ⭐ **순수 함수 도메인 모듈** — `domain/optimizer.py`, `domain/timeline.py` 에 I/O 없는 순수 함수로 배치. 이동시간은 인자로 주입받는 **거리·시간 행렬(matrix)** 형태로 전달
　→ PBT-R2(집합 보존·단조 증가·비음수) 와 PBT-R7(완전탐색 오라클 비교)을 네트워크 없이 검증 가능 (Q22=A 요건과 정합)

B) **서비스 계층 내부** — 서비스가 외부 API를 호출하면서 계산도 수행

C) **프론트엔드에서 계산** — 클라이언트가 최적화 수행 (⚠️ API 키 노출, PBT 불가)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 11
**외부 API 캐시(NFR-4)** 를 어느 계층에 둡니까?

A) ⭐ **클라이언트 데코레이터** — `CachedDirectionsClient(DirectionsClient)` 처럼 동일 인터페이스를 감싸는 데코레이터로 구현하고, 캐시는 SQLite 테이블에 저장(TTL 컬럼)
　→ 서비스는 캐시 존재를 모르고, 캐시 정책 변경이 한 곳에 국한됩니다. NFR-11(볼륨 보존)과도 정합

B) **서비스 계층 캐시** — 각 서비스가 조회 전 캐시를 확인

C) **인메모리 캐시만** — 프로세스 재시작 시 소실 (쿼터 절약 효과 제한적)

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🔗 컴포넌트 의존성 (Component Dependencies)

## Question 12
**의존성 방향 규칙**을 어떻게 강제합니까?

A) ⭐ **단방향 계층 규칙** — `api → services → domain`, `services → clients/storage`, **`domain` 은 아무것도 의존하지 않음**(순수). 역방향 import 금지를 설계 문서에 명문화하고 코드 리뷰·테스트로 확인

B) **느슨한 규칙** — 순환만 피하고 계층 간 자유롭게 호출

C) **의존성 역전 전면 적용** — 모든 계층 경계에 Protocol 정의

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 13
**프론트엔드 상태 관리**를 무엇으로 합니까?

A) ⭐ **TanStack Query(서버 상태) + Zustand(클라이언트 상태)** — 서버 데이터는 Query가 캐시·재검증·폴링(Q5=A의 job 폴링)을 담당하고, 드래그 편집 중인 임시 순서·선택된 일자·지도 하이라이트 같은 UI 상태만 Zustand
　→ FR-19(양방향 하이라이트)와 FR-31(오프라인 캐시, Query persist)이 자연스럽게 얹힙니다

B) **Redux Toolkit** 단일 스토어

C) **React Context + useReducer** — 외부 라이브러리 없음

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 14
**네이버 지도 SDK 를 React 에서 어떻게 다룹니까?**

A) ⭐ **전용 어댑터 컴포넌트로 격리** — `features/map/NaverMapAdapter` 가 SDK 로딩·인스턴스 수명·마커/폴리라인 명령형 API를 캡슐화하고, 바깥에는 선언적 props(마커 목록·경로·선택 항목)만 노출
　→ SDK 가 명령형이라 React 렌더링과 충돌하기 쉬운 지점을 한 곳에 가둡니다. 목 모드(FR-33)에서 대체 구현으로 교체도 용이

B) **컴포넌트에서 직접 SDK 호출** — 어댑터 없이 useEffect 안에서 처리

C) **서드파티 래퍼 라이브러리 사용**

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

### 🏛️ 설계 패턴 (Design Patterns)

## Question 15
**안드로이드(u3) JS↔네이티브 브리지** 구현 방식은?

A) ⭐ **`WebViewCompat.addWebMessageListener`** — 오리진 허용목록을 지정할 수 있어 임의 페이지가 브리지를 잡는 것을 막습니다. 미지원 기기에서는 `@JavascriptInterface` 로 폴백
　→ SEC-08(오리진 제한)·SEC-11(공격면 최소화) 관점에서 더 안전합니다

B) **`@JavascriptInterface` 만 사용** — 구현 단순, 전 버전 호환. 단 오리진 제한이 없어 로드되는 모든 페이지에 노출됨

C) **커스텀 URL 스킴 가로채기** — `shouldOverrideUrlLoading` 으로 처리

X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 16
**오프라인 캐시(FR-31·32)** 를 어떤 방식으로 구현합니까?

A) ⭐ **TanStack Query persist → IndexedDB** — 서버 상태 캐시를 IndexedDB에 그대로 영속화하고, 온라인 복귀 시 자동 재검증. 별도 동기화 코드가 거의 필요 없음 (Q13=A와 직결)

B) **Service Worker + Cache API** — 네트워크 계층에서 가로채기 (PWA 성격 강화, 디버깅 난도 상승)

C) **직접 IndexedDB 접근 계층 구현**

X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## ✅ 답변 완료 후

채팅에 **"완료"** 또는 **"전부 추천안"** 이라고 알려주세요.
답변의 모호성·모순을 분석한 뒤(규칙 Step 8~9), 문제가 없으면 `application-design/` 산출물 5종을 생성하고 승인을 요청합니다.
