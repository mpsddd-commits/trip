/**
 * 생성 job 폴링 간격 계산 — 순수 함수 (PBT 대상).
 *
 * 근거:
 *   Q2=A / WBR-11  경과 0~10초 1초, 이후 2초, **90초 초과 시 중단**
 *   WBR-12         문서가 백그라운드면 멈춘다 (호출자 책임)
 *   NFR-1          AI 생성은 최대 60초 — 90초 상한은 여유를 둔 값
 *   WP-10          간격은 1000ms 이상이고 경과에 대해 단조 비감소
 *   WP-11          90초 초과 시 항상 `stop`
 */
export const FAST_PHASE_MS = 10_000;
export const FAST_INTERVAL_MS = 1_000;
export const SLOW_INTERVAL_MS = 2_000;
export const POLL_TIMEOUT_MS = 90_000;

export type PollDecision =
  | { action: "poll"; intervalMs: number }
  | { action: "stop"; reason: "timeout" };

/**
 * 경과 시간으로 다음 폴링 동작을 정한다.
 *
 * 음수 입력은 0 으로 취급한다 — 시계 오차로 계산이 깨지지 않게 한다.
 */
export function nextPoll(elapsedMs: number): PollDecision {
  const elapsed = Math.max(0, elapsedMs);
  if (elapsed > POLL_TIMEOUT_MS) {
    return { action: "stop", reason: "timeout" };
  }
  return {
    action: "poll",
    intervalMs: elapsed < FAST_PHASE_MS ? FAST_INTERVAL_MS : SLOW_INTERVAL_MS,
  };
}

/** 종료 상태 판정 — 이 값들에 도달하면 폴링을 멈춘다. */
export const TERMINAL_STATES = ["succeeded", "partial", "failed"] as const;

export function isTerminal(state: string): boolean {
  return (TERMINAL_STATES as readonly string[]).includes(state);
}

/**
 * WBR-13 — 서버 `step` 을 사용자 언어로 번역한다. 진행률은 서버 값을 그대로 쓴다(WBR-04).
 *
 * 🔴 `Map` 을 쓰는 이유 (PBT 가 잡은 결함):
 *    객체 리터럴을 조회 표로 쓰면 `Object.prototype` 의 상속 속성이 새어나온다.
 *    `STEP_LABELS["toString"]` 는 함수를 반환하므로 `?? 기본값` 이 발동하지 않고,
 *    `.length` 가 함수의 인자 수(0)를 돌려준다.
 *    속성 테스트가 반례 `"toString"` 으로 이 결함을 찾아냈다.
 */
const STEP_LABEL_ENTRIES = [
  ["DRAFTING", "여행 아이디어를 구상하고 있어요"],
  ["RESOLVING", "실제로 있는 장소인지 확인하고 있어요"],
  ["ROUTING", "이동 경로를 계산하고 있어요"],
  ["OPTIMIZING", "동선을 다듬고 있어요"],
  ["SCHEDULING", "시간표를 만들고 있어요"],
  ["SAVING", "저장하고 있어요"],
] as const;

export const STEP_LABELS = new Map<string, string>(STEP_LABEL_ENTRIES);

export function stepLabel(step: string | null | undefined): string {
  if (!step) return "준비하고 있어요";
  return STEP_LABELS.get(step) ?? "진행하고 있어요";
}
