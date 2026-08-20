/**
 * 네이버 지도 SDK 로더.
 *
 * 🔴 미확정 사항의 격리 지점 (계획 §7-1)
 *    SDK 스크립트 URL 과 전역 객체 형태는 **Build & Test 에서 실 로딩으로 확정**한다.
 *    잘못되면 이 파일 하나만 고치면 된다.
 *
 * 근거:
 *   WBR-40  실패 사유를 구분해 표시한다 — **도메인 미등록이 가장 흔한 설정 실수**(CON-3)
 *   WBR-41  지도 화면에 들어올 때만 내려받는다 (목록·생성 화면에서는 로드하지 않음)
 *   SEC-04  스크립트 출처는 CSP `script-src` 허용목록과 일치해야 한다
 *   A-1     키는 `GET /api/config` 에서 받는다 (빌드 시 주입하지 않음)
 */

/** ⚠️ Build & Test 검증 대상. CSP `script-src` 의 `https://oapi.map.naver.com` 과 일치해야 한다. */
export const SDK_ORIGIN = "https://oapi.map.naver.com";
export const SDK_PATH = "/openapi/v3/maps.js";

export type SdkLoadFailure = "no-key" | "network" | "auth" | "unknown";

export class MapSdkError extends Error {
  constructor(readonly reason: SdkLoadFailure, message: string) {
    super(message);
    this.name = "MapSdkError";
  }
}

/** WBR-40 — 사용자에게 보여줄 문구. 원인별로 다음 행동이 다르다. */
export const FAILURE_MESSAGES: Record<SdkLoadFailure, string> = {
  "no-key": "지도 키가 설정되지 않았습니다. 관리자에게 문의하거나 .env 를 확인해 주세요.",
  network: "네트워크 문제로 지도를 불러오지 못했습니다.",
  auth: "지도 키가 거부되었습니다. 네이버 클라우드 플랫폼에서 이 주소를 Web 서비스 URL 로 등록했는지 확인해 주세요.",
  unknown: "지도를 불러오지 못했습니다.",
};

let loadPromise: Promise<void> | null = null;

interface NaverMapsGlobal {
  maps?: unknown;
}

declare global {
  interface Window {
    naver?: NaverMapsGlobal;
    /** SDK 가 인증 실패 시 호출하는 전역 콜백 (도메인 미등록 등) */
    navermap_authFailure?: () => void;
  }
}

export function isSdkLoaded(): boolean {
  return typeof window !== "undefined" && window.naver?.maps !== undefined;
}

/**
 * SDK 를 1회만 로드한다. 이미 로드됐으면 즉시 반환한다.
 *
 * 실패 사유를 구분하기 위해 `navermap_authFailure` 전역 콜백을 함께 건다 —
 * 인증 실패(도메인 미등록)는 스크립트 `onerror` 가 아니라 이 콜백으로 온다.
 */
export function loadNaverMapSdk(clientKey: string | null): Promise<void> {
  if (isSdkLoaded()) return Promise.resolve();
  if (loadPromise) return loadPromise;

  if (!clientKey) {
    return Promise.reject(new MapSdkError("no-key", FAILURE_MESSAGES["no-key"]));
  }

  loadPromise = new Promise<void>((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${SDK_ORIGIN}${SDK_PATH}?ncpKeyId=${encodeURIComponent(clientKey)}`;
    script.async = true;

    const cleanup = () => {
      delete window.navermap_authFailure;
    };

    // 도메인 화이트리스트 미등록 시 SDK 가 이 콜백을 호출한다 (CON-3).
    window.navermap_authFailure = () => {
      cleanup();
      loadPromise = null;
      reject(new MapSdkError("auth", FAILURE_MESSAGES.auth));
    };

    script.onload = () => {
      cleanup();
      if (isSdkLoaded()) {
        resolve();
      } else {
        loadPromise = null;
        reject(new MapSdkError("unknown", FAILURE_MESSAGES.unknown));
      }
    };
    script.onerror = () => {
      cleanup();
      loadPromise = null;
      reject(new MapSdkError("network", FAILURE_MESSAGES.network));
    };

    document.head.appendChild(script);
  });

  return loadPromise;
}

/** 테스트용 — 로더 상태 초기화 */
export function resetSdkLoader(): void {
  loadPromise = null;
}
