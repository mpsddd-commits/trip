/**
 * 온라인 상태 감지 (W15 의 일부).
 *
 * 근거:
 *   FR-31·32 / WBR-35·36
 *   `navigator.onLine` 은 "랜선이 꽂혀 있다" 수준의 신호라 신뢰도가 낮다.
 *   따라서 **API 호출 실패(ApiError.offline)도 함께 관찰**해 오프라인으로 전환한다.
 */
import { useEffect, useState } from "react";

let manualOffline = false;
const listeners = new Set<(offline: boolean) => void>();

/** W1 ApiClient 가 네트워크 실패를 감지했을 때 호출한다. */
export function reportOffline(): void {
  if (manualOffline) return;
  manualOffline = true;
  for (const listener of listeners) listener(true);
}

/** 요청이 성공하면 오프라인 판정을 해제한다. */
export function reportOnline(): void {
  if (!manualOffline) return;
  manualOffline = false;
  for (const listener of listeners) listener(false);
}

function currentOffline(): boolean {
  if (manualOffline) return true;
  return typeof navigator !== "undefined" && navigator.onLine === false;
}

export function useOnlineStatus(): { online: boolean; offline: boolean } {
  const [offline, setOffline] = useState<boolean>(currentOffline);

  useEffect(() => {
    const sync = () => setOffline(currentOffline());
    const onManual = (value: boolean) => setOffline(value || currentOffline());

    window.addEventListener("online", sync);
    window.addEventListener("offline", sync);
    listeners.add(onManual);
    sync();

    return () => {
      window.removeEventListener("online", sync);
      window.removeEventListener("offline", sync);
      listeners.delete(onManual);
    };
  }, []);

  return { online: !offline, offline };
}

/** 테스트용 초기화 */
export function resetOfflineState(): void {
  manualOffline = false;
  listeners.clear();
}
