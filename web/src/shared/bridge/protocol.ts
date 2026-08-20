/**
 * u2 ↔ u3 브리지 메시지 계약.
 *
 * 🔴 UD-4 — **`unit-of-work-dependency.md` §2 계약 ②가 단일 진실 공급원이다.**
 *    이 파일과 u3 의 `BridgeProtocol.kt` 는 그 문서의 복제본이다.
 *    변경할 때는 **문서를 먼저 고치고** 양쪽 코드를 맞춘다.
 *
 * SEC-08 / SEC-11 — 아래 5종 외의 메시지를 추가하지 않는다.
 *   파일 접근·임의 인텐트 실행·저장소 접근을 노출하는 메시지는 **금지**한다.
 */

/** 웹이 전역에 심는 브리지 객체 이름. u3 의 `addWebMessageListener` 와 일치해야 한다. */
export const BRIDGE_NAME = "tripBridge";

// --- 웹 → 네이티브 -----------------------------------------------------------
export const OUTBOUND = {
  OPEN_MAP: "openMap",
  SHARE: "share",
  REQUEST_LOCATION: "requestLocation",
} as const;

export type OutboundType = (typeof OUTBOUND)[keyof typeof OUTBOUND];

export interface OpenMapMessage {
  type: typeof OUTBOUND.OPEN_MAP;
  appUrl: string;
  webUrl: string;
}

export interface ShareMessage {
  type: typeof OUTBOUND.SHARE;
  title: string;
  text: string;
  url: string;
}

export interface RequestLocationMessage {
  type: typeof OUTBOUND.REQUEST_LOCATION;
  requestId: string;
}

export type OutboundMessage = OpenMapMessage | ShareMessage | RequestLocationMessage;

// --- 네이티브 → 웹 -----------------------------------------------------------
export const INBOUND = {
  LOCATION_RESULT: "locationResult",
  BRIDGE_READY: "bridgeReady",
} as const;

export interface LocationResultMessage {
  type: typeof INBOUND.LOCATION_RESULT;
  requestId: string;
  lat: number | null;
  lng: number | null;
  denied: boolean;
}

export interface BridgeReadyMessage {
  type: typeof INBOUND.BRIDGE_READY;
  version: string;
}

export type InboundMessage = LocationResultMessage | BridgeReadyMessage;

// --- 전역 타입 ---------------------------------------------------------------
export interface TripBridge {
  postMessage(payload: string): void;
}

declare global {
  interface Window {
    [BRIDGE_NAME]?: TripBridge;
    /** 네이티브가 응답을 전달하는 콜백 (u3 가 호출) */
    __tripBridgeReceive?: (payload: string) => void;
  }
}

export function isInboundMessage(value: unknown): value is InboundMessage {
  if (typeof value !== "object" || value === null) return false;
  const type = (value as { type?: unknown }).type;
  return type === INBOUND.LOCATION_RESULT || type === INBOUND.BRIDGE_READY;
}
