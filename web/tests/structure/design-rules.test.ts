/**
 * 구조 테스트 — 설계 규칙이 코드에 남아 있는지 검사한다.
 *
 * 동작이 아니라 **규칙**을 본다. 나중에 누가 편의를 위해 규칙을 무너뜨리면 즉시 실패한다.
 * (u1 에서 같은 방식이 효과가 있었다: 목록 API 부재·감사 로그 추가 전용 등)
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const ROOT = join(process.cwd(), "src");

function walk(dir: string, out: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (/\.tsx?$/.test(entry)) out.push(full);
  }
  return out;
}

/**
 * 🔴 주석을 제거하고 검사한다.
 *
 * 이 파일들은 "왜 이 규칙이 있는지"를 주석으로 길게 설명한다. 예를 들어
 * `SharedTripView.tsx` 의 주석에는 "`DndContext` 를 import 하지 않는다" 라는 문장이 있다.
 * 원문 그대로 검사하면 **설명 문구가 위반으로 잡히는 오탐**이 난다(실제로 4건 발생했다).
 * 구조 테스트는 코드를 봐야지 산문을 보면 안 된다.
 */
function stripComments(source: string): string {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, " ") // 블록 주석
    .replace(/(^|[^:])\/\/.*$/gm, "$1 ") // 줄 주석 (URL 의 `://` 는 보존)
    .replace(/<!--[\s\S]*?-->/g, " "); // HTML 주석
}

const FILES = walk(ROOT).map((path) => {
  const raw = readFileSync(path, "utf8");
  return {
    path: relative(ROOT, path).replace(/\\/g, "/"),
    raw,
    text: stripComments(raw),
  };
});

function find(pathFragment: string): string {
  const file = FILES.find((f) => f.path.includes(pathFragment));
  if (!file) throw new Error(`파일을 찾을 수 없습니다: ${pathFragment}`);
  return file.text;
}

function findRaw(pathFragment: string): string {
  const file = FILES.find((f) => f.path.includes(pathFragment));
  if (!file) throw new Error(`파일을 찾을 수 없습니다: ${pathFragment}`);
  return file.raw;
}

// ---------------------------------------------------------------------------
describe("WBR-28 / DD-11 — 딥링크 URL 생성은 W13 한 곳에만", () => {
  it("`nmap://` 리터럴이 deeplink 모듈 밖에 없다", () => {
    const offenders = FILES.filter(
      (f) => f.text.includes("nmap://") && !f.path.startsWith("shared/deeplink/"),
    ).map((f) => f.path);
    expect(offenders).toEqual([]);
  });

  it("`map.naver.com` 웹 폴백 URL 도 deeplink 모듈에만 있다", () => {
    // `features/map/loadSdk.ts` 의 `oapi.map.naver.com` 은 **SDK 스크립트 출처**이지
    // 딥링크가 아니다. 지도 로더는 예외로 둔다.
    const offenders = FILES.filter(
      (f) =>
        f.text.includes("map.naver.com") &&
        !f.path.startsWith("shared/deeplink/") &&
        f.path !== "features/map/loadSdk.ts",
    ).map((f) => f.path);
    expect(offenders).toEqual([]);
  });

  it("지도 로더가 참조하는 것은 SDK 출처뿐이다 (딥링크가 아님)", () => {
    const loader = find("features/map/loadSdk.ts");
    expect(loader).toContain("oapi.map.naver.com");
    expect(loader).not.toContain("nmap://");
  });
});

describe("DD-11 — 웹/앱 분기는 W14 한 곳에만", () => {
  it("`isNative()` 를 화면 컴포넌트가 직접 호출하지 않는다", () => {
    const offenders = FILES.filter(
      (f) => /\bisNative\s*\(/.test(f.text) && !f.path.startsWith("shared/bridge/"),
    ).map((f) => f.path);
    expect(offenders).toEqual([]);
  });
});

describe("DD-18 — 지도 SDK 는 어댑터 안에만", () => {
  it("`window.naver` 참조가 map 모듈 밖에 없다", () => {
    const offenders = FILES.filter(
      (f) => f.text.includes("window.naver") && !f.path.startsWith("features/map/"),
    ).map((f) => f.path);
    expect(offenders).toEqual([]);
  });

  it("MapView 는 SDK 를 모른다 — 선언적 props 만 다룬다", () => {
    const mapView = find("features/map/MapView.tsx");
    expect(mapView).not.toContain("window.naver");
    expect(mapView).not.toContain("new maps.");
  });
});

describe("DD-25 / BR-37 — 공유 화면에 편집 컴포넌트가 없다", () => {
  const shared = find("features/share/SharedTripView.tsx");

  it("드래그 컨텍스트를 import 하지 않는다", () => {
    expect(shared).not.toContain("@dnd-kit");
    expect(shared).not.toContain("DndContext");
  });

  it("편집용 컴포넌트를 트리에 넣지 않는다", () => {
    for (const forbidden of ["TimelineView", "PlaceSearchPanel", "useTripMutations", "TripHeader"]) {
      expect(shared).not.toContain(forbidden);
    }
  });

  it("`share_token` 을 읽지 않는다 (타입에도 없다)", () => {
    expect(shared).not.toContain("share_token");
  });
});

describe("WBR-10 — 폼 상한을 하드코딩하지 않는다", () => {
  it("생성 마법사가 서버 limits 를 사용한다", () => {
    const wizard = find("features/trip-create/TripCreateWizard.tsx");
    expect(wizard).toContain("limits.max_trip_days");
    // 상한 숫자를 직접 박아두지 않았는지 확인
    expect(wizard).not.toMatch(/>\s*10\s*\)/);
  });
});

describe("WBR-04 — 클라이언트가 서버 값을 다시 계산하지 않는다", () => {
  it("선택자는 시각을 만들어내지 않는다 (Date 생성 금지)", () => {
    const selectors = find("shared/selectors/trip.ts");
    expect(selectors).not.toContain("new Date(");
    // 파싱은 허용된다 — 서버가 준 문자열을 읽을 뿐이다
    expect(selectors).toContain("Date.parse");
  });
});

describe("SEC-04 — 인라인 스크립트를 만들지 않는다", () => {
  it("index.html 에 인라인 script 블록이 없다", () => {
    // HTML 주석에도 `<script>` 라는 **설명 문구**가 있으므로 주석을 먼저 제거한다.
    const html = stripComments(readFileSync(join(process.cwd(), "index.html"), "utf8"));
    const scripts = html.match(/<script[^>]*>/g) ?? [];
    expect(scripts.length).toBeGreaterThan(0); // 진입 스크립트는 있어야 한다
    for (const tag of scripts) {
      expect(tag).toContain("src="); // src 있는 module 스크립트만 허용
    }
    expect(html).not.toMatch(/<script[^>]*>[\s\S]*?\S[\s\S]*?<\/script>/);
  });

  it("dangerouslySetInnerHTML 을 쓰지 않는다", () => {
    const offenders = FILES.filter((f) => f.text.includes("dangerouslySetInnerHTML")).map(
      (f) => f.path,
    );
    expect(offenders).toEqual([]);
  });
});

describe("WBR-01 — 생성 타입을 손대지 않는다", () => {
  it("generated.ts 에 자동 생성 표시가 있다", () => {
    // 이 배너는 주석이므로 **원문**을 봐야 한다 (stripComments 를 거치면 사라진다).
    expect(findRaw("shared/api/generated.ts").slice(0, 500)).toMatch(
      /auto-generated|do not make direct changes/i,
    );
  });

  it("서버 개념을 다시 정의하지 않는다 — types.ts 는 별칭만", () => {
    const types = find("shared/api/types.ts");
    // interface/ 로 새 구조를 정의하지 않는다
    expect(types).not.toMatch(/^\s*(export\s+)?interface\s+Trip\b/m);
    expect(types).toContain('from "./generated"');
  });
});

describe("WBR-03 — UI 스토어에 서버 데이터가 없다", () => {
  it("스토어가 도메인 타입을 담지 않는다", () => {
    const store = find("shared/store/uiStore.ts");
    for (const forbidden of ["Trip", "ItineraryItem", "Place["]) {
      expect(store).not.toContain(forbidden);
    }
  });
});

describe("DD-14 — job 은 persist 하지 않는다", () => {
  it("persist 판정이 trip 접두사만 통과시킨다", () => {
    const keys = find("shared/query/keys.ts");
    expect(keys).toMatch(/isPersistable[\s\S]*queryKey\[0\]\s*===\s*"trip"/);
  });
});

describe("NFR-10 — 테스트가 실제 네트워크를 쓰지 않는다", () => {
  it("setup 이 fetch 를 차단한다", () => {
    const setup = readFileSync(join(process.cwd(), "tests", "setup.ts"), "utf8");
    expect(setup).toContain("stubGlobal");
    expect(setup).toContain("fetch");
  });
});
