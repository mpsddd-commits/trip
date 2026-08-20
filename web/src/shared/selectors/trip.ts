/**
 * 여행 파생값 선택자 — 순수 함수 (PBT 대상).
 *
 * 🔴 WBR-04 — **서버가 산출한 값을 다시 계산하지 않는다.**
 *    시각·이동시간·경고는 u1 이 만든 값을 그대로 읽는다. 여기서는 **합계·필터·판정**만 한다.
 *    두 곳에서 계산하면 반드시 어긋난다.
 *
 * 근거:
 *   WBR-20  일자 총 이동시간·체류시간
 *   WBR-21  경고 배지 (서버가 준 것만)
 *   WBR-22  추정 이동시간 표시 판정
 *   WBR-25  미해결 개수
 *   WBR-30  데모 모드 판정
 *   WP-07~WP-09
 */
import type { ItineraryItem, RuntimeConfig, Trip, TripDay, UnresolvedCandidate } from "../api/types";

/** WP-07 — 항목이 1개 이하면 0, 항상 0 이상 */
export function totalStayMinutes(items: readonly ItineraryItem[]): number {
  return items.reduce((sum, item) => sum + Math.max(0, item.stay_minutes), 0);
}

/**
 * 일자 소요 시간(분). 서버가 채운 `arrival_at`/`departure_at` 만 사용한다 (WBR-04).
 * 시각이 없으면 0 을 반환한다 — 추정하지 않는다.
 */
export function dayElapsedMinutes(items: readonly ItineraryItem[]): number {
  const timed = items.filter((i) => i.arrival_at !== null && i.departure_at !== null);
  if (timed.length === 0) return 0;
  const starts = timed.map((i) => Date.parse(i.arrival_at as string));
  const ends = timed.map((i) => Date.parse(i.departure_at as string));
  const span = Math.max(...ends) - Math.min(...starts);
  return span > 0 ? Math.round(span / 60_000) : 0;
}

/** WP-08 — 서버가 준 경고의 부분집합만 반환한다. 클라이언트가 만들어내지 않는다. */
export function warningsOf(item: ItineraryItem): ItineraryItem["warnings"] {
  return item.warnings ?? [];
}

export function hasWarning(item: ItineraryItem, type: string): boolean {
  return warningsOf(item).some((w) => w.type === type);
}

/** WBR-22 — 이 일자에 추정 이동시간이 섞여 있는가 (CON-1 배지 표시 판단) */
export function hasEstimatedTravel(items: readonly ItineraryItem[]): boolean {
  return items.some((item) => hasWarning(item, "ESTIMATED_TRAVEL_TIME"));
}

/** WBR-25 — "확인 필요" 개수 */
export function unresolvedCount(trip: Pick<Trip, "unresolved">): number {
  return trip.unresolved?.length ?? 0;
}

export function unresolvedForDay(
  trip: Pick<Trip, "unresolved">,
  dayIndex: number,
): UnresolvedCandidate[] {
  return (trip.unresolved ?? []).filter((u) => u.day_index === dayIndex);
}

/** WBR-30 — 데모 모드는 `modes` 에 `"mock"` 이 하나라도 있을 때 (WP-09) */
export function demoApis(config: Pick<RuntimeConfig, "modes"> | null | undefined): string[] {
  if (!config) return [];
  return Object.entries(config.modes)
    .filter(([, mode]) => mode === "mock")
    .map(([api]) => api)
    .sort();
}

export function isDemoMode(config: Pick<RuntimeConfig, "modes"> | null | undefined): boolean {
  return demoApis(config).length > 0;
}

/** 일자 조회 헬퍼. 없는 일자는 `undefined` 를 반환한다 — 빈 배열로 속이지 않는다. */
export function dayOf(trip: Pick<Trip, "days">, dayIndex: number): TripDay | undefined {
  return trip.days.find((d) => d.day_index === dayIndex);
}

export function itemsOf(trip: Pick<Trip, "days">, dayIndex: number): ItineraryItem[] {
  return dayOf(trip, dayIndex)?.items ?? [];
}

export function findItem(trip: Pick<Trip, "days">, itemId: string): ItineraryItem | undefined {
  for (const day of trip.days) {
    const found = day.items.find((i) => i.item_id === itemId);
    if (found) return found;
  }
  return undefined;
}

/**
 * 데모 API 이름을 사용자 언어로 (WBR-30).
 *
 * 🔴 `Map` 사용 — 객체 리터럴 조회 표는 `Object.prototype` 상속 속성이 새어나온다.
 *    (`polling.ts` 의 `stepLabel` 에서 PBT 가 같은 유형의 결함을 잡았다.)
 */
const API_LABELS = new Map<string, string>([
  ["NAVER_LOCAL", "장소 검색"],
  ["NAVER_BLOG", "블로그 추천"],
  ["NAVER_IMAGE", "사진"],
  ["NCP_DIRECTIONS", "자동차 경로"],
  ["NCP_GEOCODING", "주소 변환"],
  ["ANTHROPIC", "AI 일정 생성"],
]);

export function demoLabel(apis: readonly string[]): string {
  const labels = apis.map((api) => API_LABELS.get(api) ?? api);
  return [...new Set(labels)].join(" · ");
}
