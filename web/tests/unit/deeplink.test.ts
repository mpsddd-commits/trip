/**
 * W13 DeepLinkBuilder 예제 테스트 (PBT-10 — 속성 테스트와 병행).
 *
 * 속성 테스트가 일반 규칙을 보는 반면, 여기서는 **실제로 만들어지는 URL 모양**을 못박는다.
 * 딥링크는 형식이 조금만 틀려도 앱이 열리지 않으므로 구체 예시가 필요하다.
 */
import { describe, expect, it } from "vitest";

import { APP_NAME, decodeParams, placeUrl, routeUrl } from "@/shared/deeplink";

const GWANGALLI = { name: "광안리 해수욕장", coordinate: { lat: 35.153, lng: 129.118 } };
const HAEUNDAE = { name: "해운대 해수욕장", coordinate: { lat: 35.1587, lng: 129.1604 } };

describe("장소 보기 URL (FR-23)", () => {
  it("nmap://place 스킴과 필수 파라미터를 담는다", () => {
    const { app } = placeUrl(GWANGALLI);
    expect(app.startsWith("nmap://place?")).toBe(true);

    const params = decodeParams(app.split("?")[1] ?? "");
    expect(params.lat).toBe("35.153000");
    expect(params.lng).toBe("129.118000");
    expect(params.name).toBe("광안리 해수욕장");
    // 앱이 호출 주체를 식별하는 값. 빠지면 네이버지도가 열리지 않는다.
    expect(params.appname).toBe(APP_NAME);
  });

  it("한글 장소명이 URL 인코딩된다", () => {
    const { app } = placeUrl(GWANGALLI);
    expect(app).toContain("%EA%B4%91%EC%95%88%EB%A6%AC");
    expect(app).not.toContain(" ");
  });

  it("웹 폴백은 map.naver.com 을 가리킨다 (FR-24)", () => {
    expect(placeUrl(GWANGALLI).web.startsWith("https://map.naver.com/")).toBe(true);
  });
});

describe("길찾기 URL (FR-23, FR-12)", () => {
  it("대중교통은 route/public — CON-1 위임 지점", () => {
    const { app } = routeUrl(GWANGALLI, HAEUNDAE, "TRANSIT");
    expect(app.startsWith("nmap://route/public?")).toBe(true);
  });

  it("자동차와 도보도 각각의 세그먼트를 쓴다", () => {
    expect(routeUrl(GWANGALLI, HAEUNDAE, "CAR").app).toContain("route/car");
    expect(routeUrl(GWANGALLI, HAEUNDAE, "WALK").app).toContain("route/walk");
  });

  it("출발·도착 좌표와 이름을 모두 담는다", () => {
    const params = decodeParams(routeUrl(GWANGALLI, HAEUNDAE, "TRANSIT").app.split("?")[1] ?? "");
    expect(params.slat).toBe("35.153000");
    expect(params.sname).toBe("광안리 해수욕장");
    expect(params.dlat).toBe("35.158700");
    expect(params.dname).toBe("해운대 해수욕장");
    expect(params.appname).toBe(APP_NAME);
  });
});

describe("특수문자 장소명", () => {
  it("앰퍼샌드가 파라미터 구분자를 깨지 않는다", () => {
    const place = { name: "돼지국밥 & 수육", coordinate: { lat: 35.1, lng: 129.0 } };
    const params = decodeParams(placeUrl(place).app.split("?")[1] ?? "");
    expect(params.name).toBe("돼지국밥 & 수육");
    expect(params.appname).toBe(APP_NAME); // & 로 잘려나가지 않았다
  });

  it("물음표를 포함한 이름도 안전하다", () => {
    const place = { name: "여기?저기", coordinate: { lat: 35.1, lng: 129.0 } };
    const params = decodeParams(placeUrl(place).app.split("?")[1] ?? "");
    expect(params.name).toBe("여기?저기");
  });
});
