/**
 * 여행 목록 내보내기/가져오기 속성 테스트 — WP-05, WP-06 (PBT-02, PBT-04).
 *
 * 🔴 이 기능은 "브라우저 데이터를 지우면 여행에 접근할 수 없다"는 문제의
 *    **실질적 복구 수단**이다 (WBR-07·08). 왕복과 멱등이 깨지면 복구가 실패한다.
 */
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import {
  ImportFormatError,
  exportList,
  importList,
  mergeLists,
  parseExport,
} from "@/shared/storage/tripListExport";
import { arbSavedTripRef, arbTripList } from "./generators";

const byId = (list: { trip_id: string }[]) => [...list].sort((a, b) => a.trip_id.localeCompare(b.trip_id));

describe("WP-05 내보내기 → 가져오기 왕복", () => {
  it("원본 목록이 집합으로 보존된다", () => {
    fc.assert(
      fc.property(arbTripList(), (trips) => {
        const restored = importList(exportList(trips, "2026-08-14T00:00:00Z"));
        expect(restored).toEqual(byId(trips));
      }),
    );
  });

  it("JSON 직렬화를 거쳐도 보존된다 (실제 파일 경로)", () => {
    fc.assert(
      fc.property(arbTripList(), (trips) => {
        const text = JSON.stringify(exportList(trips, "2026-08-14T00:00:00Z"));
        expect(importList(parseExport(text))).toEqual(byId(trips));
      }),
    );
  });

  it("내보내기는 결정적이다 — 같은 입력이면 같은 파일", () => {
    fc.assert(
      fc.property(arbTripList(), (trips) => {
        const a = JSON.stringify(exportList(trips, "2026-08-14T00:00:00Z"));
        const b = JSON.stringify(exportList([...trips].reverse(), "2026-08-14T00:00:00Z"));
        expect(a).toBe(b);
      }),
    );
  });
});

describe("WP-06 가져오기 멱등성", () => {
  it("같은 파일을 두 번 넣어도 목록이 늘지 않는다", () => {
    fc.assert(
      fc.property(arbTripList(), arbTripList(), (current, incoming) => {
        const once = mergeLists(current, incoming);
        const twice = mergeLists(once, incoming);
        expect(twice).toEqual(once);
      }),
    );
  });

  it("병합은 항목을 잃지 않는다 (양쪽 trip_id 의 합집합)", () => {
    fc.assert(
      fc.property(arbTripList(), arbTripList(), (current, incoming) => {
        const merged = mergeLists(current, incoming);
        const expected = new Set([...current, ...incoming].map((r) => r.trip_id));
        expect(new Set(merged.map((r) => r.trip_id))).toEqual(expected);
      }),
    );
  });

  it("같은 trip_id 는 saved_at 이 최신인 쪽이 남는다", () => {
    fc.assert(
      fc.property(arbSavedTripRef(), (ref) => {
        const older = { ...ref, saved_at: "2026-01-01T00:00:00.000Z", title: "old" };
        const newer = { ...ref, saved_at: "2026-12-31T00:00:00.000Z", title: "new" };
        expect(mergeLists([older], [newer])[0]?.title).toBe("new");
        expect(mergeLists([newer], [older])[0]?.title).toBe("new");
      }),
    );
  });
});

describe("가져오기 형식 검증 — 추측하지 않는다", () => {
  it("JSON 이 아니면 거부한다", () => {
    expect(() => parseExport("not json")).toThrow(ImportFormatError);
  });

  it("다른 형식의 JSON 을 거부한다", () => {
    expect(() => parseExport(JSON.stringify({ hello: "world" }))).toThrow(ImportFormatError);
  });

  it("지원하지 않는 버전을 거부한다", () => {
    const payload = { format: "trip-list-export", version: 99, trips: [] };
    expect(() => parseExport(JSON.stringify(payload))).toThrow(ImportFormatError);
  });

  it("형식은 맞지만 항목이 손상된 경우 그 항목만 걸러낸다", () => {
    const payload = {
      format: "trip-list-export",
      version: 1,
      exported_at: "2026-08-14T00:00:00Z",
      trips: [{ nope: true }, null, 42],
    };
    expect(parseExport(JSON.stringify(payload)).trips).toEqual([]);
  });
});
