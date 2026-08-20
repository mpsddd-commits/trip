/**
 * W13 DeepLinkBuilder — 네이버지도 딥링크 URL 생성. **순수 함수.**
 *
 * 🔴 WBR-28 / DD-11 — URL 생성은 **이 파일에만** 존재한다.
 *    u3(안드로이드)는 URL 을 만들지 않고 받아서 실행만 한다. 규칙을 이중 구현하지 않기 위함.
 *
 * 근거:
 *   FR-23   장소 보기 / 길찾기 딥링크
 *   FR-24   앱 미설치 시 `map.naver.com` 웹 폴백
 *   FR-12   대중교통은 `route/public` — **앱 내부 추정치가 아닌 실제 안내를 위임**하는 지점 (CON-1)
 *   WP-01   `decodeParams(encodeParams(x)) == x`
 *   WP-02   항상 `app` 과 `web` 두 값을 모두 만든다
 *   WP-03   `TRANSIT` 이면 `route/public`
 *   WP-04   좌표 정밀도 6자리 이상 보존
 */
import type { Coordinate, TravelMode } from "../api/types";

export interface DeepLinkUrls {
  app: string;
  web: string;
}

/** 네이버지도 앱이 호출 주체를 식별하는 값. 앱 스킴에 필수. */
export const APP_NAME = "trip.local";

const APP_SCHEME = "nmap://";
const WEB_BASE = "https://map.naver.com/p/directions";
const WEB_SEARCH = "https://map.naver.com/p/search";

/** WP-04 — 좌표는 소수점 6자리로 고정한다(약 0.1m). 반올림 손실을 문서화된 범위로 묶는다. */
export function formatCoord(value: number): string {
  return value.toFixed(6);
}

/** WP-01 — 왕복 가능한 인코딩. 한글·공백·특수문자를 안전하게 담는다. */
export function encodeParams(params: Record<string, string>): string {
  return Object.entries(params)
    .filter(([, value]) => value !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
    .join("&");
}

/**
 * WP-01 왕복의 역방향.
 *
 * 🔴 `defineProperty` 를 쓰는 이유:
 *    일반 대입(`result[key] = value`)은 키가 `__proto__` 일 때 **자기 속성을 만들지 않고
 *    프로토타입을 바꾼다.** 그러면 왕복이 깨진다.
 *    같은 부류의 결함을 `polling.ts::stepLabel` 에서 속성 테스트가 반례 `"toString"` 으로
 *    이미 잡았다. 여기서도 선제적으로 막는다.
 */
export function decodeParams(query: string): Record<string, string> {
  const result: Record<string, string> = {};
  if (query === "") return result;
  for (const pair of query.split("&")) {
    const index = pair.indexOf("=");
    if (index < 0) continue;
    const key = decodeURIComponent(pair.slice(0, index));
    const value = decodeURIComponent(pair.slice(index + 1));
    Object.defineProperty(result, key, {
      value,
      enumerable: true,
      writable: true,
      configurable: true,
    });
  }
  return result;
}

/** WP-03 — 이동수단 ↔ 앱 경로 세그먼트 */
export function routeSegment(mode: TravelMode): "public" | "car" | "walk" {
  switch (mode) {
    case "TRANSIT":
      return "public";
    case "CAR":
      return "car";
    case "WALK":
      return "walk";
    default:
      // 알 수 없는 값이면 대중교통으로 둔다 — CON-1 상 가장 안전한 위임 대상.
      return "public";
  }
}

interface PlaceLike {
  name: string;
  coordinate: Coordinate;
}

/** FR-23 — 장소 보기 */
export function placeUrl(place: PlaceLike): DeepLinkUrls {
  const lat = formatCoord(place.coordinate.lat);
  const lng = formatCoord(place.coordinate.lng);
  const app = `${APP_SCHEME}place?${encodeParams({
    lat,
    lng,
    name: place.name,
    appname: APP_NAME,
  })}`;
  const web = `${WEB_SEARCH}/${encodeURIComponent(place.name)}?c=${lng},${lat},15,0,0,0,dh`;
  return { app, web };
}

/** FR-23 / FR-12 — 길찾기 */
export function routeUrl(from: PlaceLike, to: PlaceLike, mode: TravelMode): DeepLinkUrls {
  const segment = routeSegment(mode);
  const app = `${APP_SCHEME}route/${segment}?${encodeParams({
    slat: formatCoord(from.coordinate.lat),
    slng: formatCoord(from.coordinate.lng),
    sname: from.name,
    dlat: formatCoord(to.coordinate.lat),
    dlng: formatCoord(to.coordinate.lng),
    dname: to.name,
    appname: APP_NAME,
  })}`;

  const web = `${WEB_BASE}/${encodeParams({
    from: `${formatCoord(from.coordinate.lng)},${formatCoord(from.coordinate.lat)},${from.name}`,
    to: `${formatCoord(to.coordinate.lng)},${formatCoord(to.coordinate.lat)},${to.name}`,
    mode: segment,
  })}`;

  return { app, web };
}
