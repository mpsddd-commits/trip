/**
 * W14 NativeBridge — 웹/앱 분기의 **유일한 지점**.
 *
 * 🔴 DD-11 / WBR-28 — 화면 컴포넌트는 `isNative()` 를 직접 보지 않는다.
 *    이 모듈의 함수만 호출한다. 분기가 화면으로 새면 두 경로가 갈라진다.
 *
 * 근거:
 *   WBR-27  폴백 순서 — **브리지 → 앱 스킴 → 웹**
 *   FR-24   앱 미설치 시 웹 폴백
 *   FR-28   시스템 공유 / 위치 권한
 */
import type { DeepLinkUrls } from "../deeplink";
import {
  BRIDGE_NAME,
  INBOUND,
  OUTBOUND,
  isInboundMessage,
  type LocationResultMessage,
  type OutboundMessage,
} from "./protocol";

/** 앱 스킴 실행 후 이 시간 안에 페이지 이탈이 없으면 웹으로 폴백한다 (WBR-27). */
export const SCHEME_FALLBACK_MS = 1_500;

export function isNative(): boolean {
  return typeof window !== "undefined" && typeof window[BRIDGE_NAME]?.postMessage === "function";
}

function post(message: OutboundMessage): boolean {
  const bridge = typeof window === "undefined" ? undefined : window[BRIDGE_NAME];
  if (!bridge) return false;
  try {
    bridge.postMessage(JSON.stringify(message));
    return true;
  } catch {
    return false;
  }
}

/**
 * FR-23 / FR-24 — 네이버지도 열기.
 *
 * ① 안드로이드 브리지가 있으면 위임한다 (u3 가 인텐트 실행, 실패 시 웹)
 * ② 브라우저면 앱 스킴을 시도하고, 이탈이 없으면 웹으로 연다
 */
export function openMap(urls: DeepLinkUrls): void {
  if (post({ type: OUTBOUND.OPEN_MAP, appUrl: urls.app, webUrl: urls.web })) return;

  if (typeof window === "undefined") return;

  let navigated = false;
  const markNavigated = () => {
    if (document.visibilityState === "hidden") navigated = true;
  };
  document.addEventListener("visibilitychange", markNavigated);

  // 앱 스킴 시도. 설치되어 있지 않으면 아무 일도 일어나지 않는다.
  window.location.href = urls.app;

  window.setTimeout(() => {
    document.removeEventListener("visibilitychange", markNavigated);
    if (!navigated) {
      // 앱이 열리지 않았다 — 사용자가 빈 화면을 보지 않도록 웹으로 보낸다.
      window.open(urls.web, "_blank", "noopener,noreferrer");
    }
  }, SCHEME_FALLBACK_MS);
}

/** FR-28 — 공유. 브리지 → Web Share API → 클립보드 순으로 폴백한다. */
export async function share(payload: { title: string; text: string; url: string }): Promise<"native" | "web-share" | "clipboard" | "failed"> {
  if (post({ type: OUTBOUND.SHARE, ...payload })) return "native";

  if (typeof navigator !== "undefined" && typeof navigator.share === "function") {
    try {
      await navigator.share(payload);
      return "web-share";
    } catch {
      // 사용자가 취소했을 수도 있다. 클립보드로 넘어간다.
    }
  }

  if (typeof navigator !== "undefined" && navigator.clipboard) {
    try {
      await navigator.clipboard.writeText(payload.url);
      return "clipboard";
    } catch {
      return "failed";
    }
  }
  return "failed";
}

// ---------------------------------------------------------------------------
// 위치 요청 — 네이티브 응답을 requestId 로 짝짓는다
// ---------------------------------------------------------------------------
type LocationResolver = (value: { lat: number; lng: number } | null) => void;
const pendingLocation = new Map<string, LocationResolver>();

function ensureReceiver(): void {
  if (typeof window === "undefined" || window.__tripBridgeReceive) return;
  window.__tripBridgeReceive = (payload: string) => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(payload);
    } catch {
      return;
    }
    if (!isInboundMessage(parsed)) return;
    if (parsed.type !== INBOUND.LOCATION_RESULT) return;

    const message = parsed as LocationResultMessage;
    const resolve = pendingLocation.get(message.requestId);
    if (!resolve) return;
    pendingLocation.delete(message.requestId);
    resolve(
      message.denied || message.lat === null || message.lng === null
        ? null
        : { lat: message.lat, lng: message.lng },
    );
  };
}

/** FR-28 — 현재 위치. 권한 거부·미지원이면 `null` 을 반환한다(오류로 만들지 않는다). */
export function requestLocation(timeoutMs = 10_000): Promise<{ lat: number; lng: number } | null> {
  if (isNative()) {
    ensureReceiver();
    const requestId = `loc-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    return new Promise((resolve) => {
      pendingLocation.set(requestId, resolve);
      const timer = window.setTimeout(() => {
        pendingLocation.delete(requestId);
        resolve(null);
      }, timeoutMs);
      const wrapped: LocationResolver = (value) => {
        window.clearTimeout(timer);
        resolve(value);
      };
      pendingLocation.set(requestId, wrapped);
      post({ type: OUTBOUND.REQUEST_LOCATION, requestId });
    });
  }

  if (typeof navigator === "undefined" || !navigator.geolocation) {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ lat: position.coords.latitude, lng: position.coords.longitude }),
      () => resolve(null),
      { timeout: timeoutMs, maximumAge: 60_000 },
    );
  });
}
