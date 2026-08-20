/**
 * W13 DeepLinkBuilder 속성 테스트 — WP-01 ~ WP-04 (PBT-02, PBT-03).
 */
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import {
  decodeParams,
  encodeParams,
  formatCoord,
  placeUrl,
  routeSegment,
  routeUrl,
} from "@/shared/deeplink";
import { arbAnyCoordinate, arbPlaceName, arbTravelMode } from "./generators";

const arbPlaceLike = () =>
  fc.record({ name: arbPlaceName(), coordinate: arbAnyCoordinate() });

describe("WP-01 파라미터 인코딩 왕복", () => {
  it("한글·공백·특수문자·이모지를 포함해도 왕복 보존된다", () => {
    fc.assert(
      fc.property(
        fc.dictionary(
          fc.string({ minLength: 1, maxLength: 10 }).filter((k) => k.trim() !== ""),
          arbPlaceName().filter((v) => v !== ""),
          { maxKeys: 6 },
        ),
        (params) => {
          const restored = decodeParams(encodeParams(params));
          expect(restored).toEqual(params);
        },
      ),
    );
  });

  it("빈 값은 인코딩에서 제외된다 (URL 오염 방지)", () => {
    expect(encodeParams({ a: "1", b: "" })).toBe("a=1");
  });

  it("프로토타입 오염 키도 자기 속성으로 왕복한다 (회귀)", () => {
    // 일반 대입은 `__proto__` 를 자기 속성으로 만들지 않고 프로토타입을 바꾼다.
    // `stepLabel` 에서 속성 테스트가 같은 부류의 결함을 잡았기에 선제 방어했다.
    for (const key of ["__proto__", "constructor", "toString", "prototype"]) {
      const restored = decodeParams(encodeParams({ [key]: "값" }));
      expect(Object.hasOwn(restored, key)).toBe(true);
      expect(restored[key]).toBe("값");
    }
  });
});

describe("WP-02 앱·웹 URL 을 항상 함께 만든다", () => {
  it("장소 보기는 두 URL 을 모두 반환한다", () => {
    fc.assert(
      fc.property(arbPlaceLike(), (place) => {
        const urls = placeUrl(place);
        expect(urls.app.startsWith("nmap://")).toBe(true);
        expect(urls.web.startsWith("https://map.naver.com/")).toBe(true);
      }),
    );
  });

  it("길찾기도 두 URL 을 모두 반환한다 (FR-24 폴백 보장)", () => {
    fc.assert(
      fc.property(arbPlaceLike(), arbPlaceLike(), arbTravelMode(), (from, to, mode) => {
        const urls = routeUrl(from, to, mode);
        expect(urls.app.length).toBeGreaterThan(0);
        expect(urls.web.length).toBeGreaterThan(0);
        expect(urls.app.startsWith("nmap://route/")).toBe(true);
      }),
    );
  });
});

describe("WP-03 이동수단 ↔ 경로 세그먼트", () => {
  it("TRANSIT 은 항상 route/public 을 쓴다 (CON-1 위임 지점)", () => {
    fc.assert(
      fc.property(arbPlaceLike(), arbPlaceLike(), (from, to) => {
        expect(routeUrl(from, to, "TRANSIT").app).toContain("nmap://route/public");
      }),
    );
  });

  it("각 이동수단이 서로 다른 세그먼트로 매핑된다", () => {
    expect(routeSegment("TRANSIT")).toBe("public");
    expect(routeSegment("CAR")).toBe("car");
    expect(routeSegment("WALK")).toBe("walk");
  });
});

describe("WP-04 좌표 정밀도", () => {
  it("소수점 6자리를 유지한다 (약 0.1m)", () => {
    fc.assert(
      fc.property(arbAnyCoordinate(), (coordinate) => {
        const formatted = formatCoord(coordinate.lat);
        expect(formatted.split(".")[1]?.length).toBe(6);
        // 반올림 오차가 문서화된 범위(0.5 x 10^-6) 안에 있다
        expect(Math.abs(Number(formatted) - coordinate.lat)).toBeLessThanOrEqual(5e-7);
      }),
    );
  });

  it("URL 에 담긴 좌표를 되읽어도 정밀도가 유지된다", () => {
    fc.assert(
      fc.property(arbPlaceLike(), (place) => {
        const query = placeUrl(place).app.split("?")[1] ?? "";
        const params = decodeParams(query);
        expect(Math.abs(Number(params.lat) - place.coordinate.lat)).toBeLessThanOrEqual(5e-7);
        expect(Math.abs(Number(params.lng) - place.coordinate.lng)).toBeLessThanOrEqual(5e-7);
      }),
    );
  });

  it("장소명이 URL 파라미터로 안전하게 왕복한다", () => {
    fc.assert(
      fc.property(arbPlaceLike(), (place) => {
        const query = placeUrl(place).app.split("?")[1] ?? "";
        expect(decodeParams(query).name).toBe(place.name);
      }),
    );
  });
});
