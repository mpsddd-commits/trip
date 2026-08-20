/**
 * 선택자 속성 테스트 — WP-07 ~ WP-09 (PBT-03).
 *
 * 🔴 핵심 검증: **클라이언트가 서버 값을 만들어내지 않는다** (WBR-04).
 */
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import {
  dayElapsedMinutes,
  demoApis,
  hasEstimatedTravel,
  isDemoMode,
  totalStayMinutes,
  unresolvedCount,
  warningsOf,
} from "@/shared/selectors/trip";
import { arbItineraryItem } from "./generators";

const arbItems = (maxLength = 15) => fc.array(arbItineraryItem(), { maxLength });

describe("WP-07 시간 합계", () => {
  it("총 체류시간은 항상 0 이상이다", () => {
    fc.assert(
      fc.property(arbItems(), (items) => {
        expect(totalStayMinutes(items)).toBeGreaterThanOrEqual(0);
      }),
    );
  });

  it("빈 목록은 0 이다", () => {
    expect(totalStayMinutes([])).toBe(0);
    expect(dayElapsedMinutes([])).toBe(0);
  });

  it("항목을 추가하면 총 체류시간이 줄지 않는다 (단조성)", () => {
    fc.assert(
      fc.property(arbItems(10), arbItineraryItem(), (items, extra) => {
        expect(totalStayMinutes([...items, extra])).toBeGreaterThanOrEqual(totalStayMinutes(items));
      }),
    );
  });

  it("시각이 없는 항목만 있으면 경과 시간은 0 이다 — 추정하지 않는다", () => {
    fc.assert(
      fc.property(arbItems(), (items) => {
        const untimed = items.map((i) => ({ ...i, arrival_at: null, departure_at: null }));
        expect(dayElapsedMinutes(untimed)).toBe(0);
      }),
    );
  });

  it("경과 시간은 항상 0 이상이다", () => {
    fc.assert(
      fc.property(arbItems(), (items) => {
        expect(dayElapsedMinutes(items)).toBeGreaterThanOrEqual(0);
      }),
    );
  });
});

describe("WP-08 경고는 서버가 준 것의 부분집합", () => {
  it("선택자가 경고를 새로 만들어내지 않는다", () => {
    fc.assert(
      fc.property(arbItineraryItem(), (item) => {
        const returned = warningsOf(item);
        expect(returned.length).toBe(item.warnings.length);
        for (const warning of returned) {
          expect(item.warnings).toContainEqual(warning);
        }
      }),
    );
  });

  it("추정 배지는 서버가 ESTIMATED_TRAVEL_TIME 을 준 경우에만 참이다", () => {
    fc.assert(
      fc.property(arbItems(), (items) => {
        const expected = items.some((i) =>
          i.warnings.some((w) => w.type === "ESTIMATED_TRAVEL_TIME"),
        );
        expect(hasEstimatedTravel(items)).toBe(expected);
      }),
    );
  });

  it("경고가 없는 항목만 있으면 추정 배지도 없다", () => {
    fc.assert(
      fc.property(arbItems(), (items) => {
        const clean = items.map((i) => ({ ...i, warnings: [] }));
        expect(hasEstimatedTravel(clean)).toBe(false);
      }),
    );
  });
});

describe("WP-09 데모 모드 판정", () => {
  const arbModes = () =>
    fc.dictionary(
      fc.constantFrom("NAVER_LOCAL", "NAVER_BLOG", "NCP_DIRECTIONS", "ANTHROPIC"),
      fc.constantFrom("real", "mock"),
      { maxKeys: 4 },
    );

  it("mock 이 하나라도 있을 때에만 데모 모드다", () => {
    fc.assert(
      fc.property(arbModes(), (modes) => {
        const expected = Object.values(modes).includes("mock");
        expect(isDemoMode({ modes })).toBe(expected);
      }),
    );
  });

  it("데모 API 목록은 mock 인 것만 담는다", () => {
    fc.assert(
      fc.property(arbModes(), (modes) => {
        for (const api of demoApis({ modes })) {
          expect(modes[api]).toBe("mock");
        }
      }),
    );
  });

  it("설정을 못 받았으면 데모 모드로 단정하지 않는다", () => {
    expect(isDemoMode(null)).toBe(false);
    expect(demoApis(undefined)).toEqual([]);
  });
});

describe("미해결 개수", () => {
  it("항상 0 이상이고 목록 길이와 같다", () => {
    fc.assert(
      fc.property(fc.array(fc.record({ day_index: fc.integer({ min: 1, max: 10 }) }), { maxLength: 20 }), (list) => {
        expect(unresolvedCount({ unresolved: list as never })).toBe(list.length);
      }),
    );
  });
});
