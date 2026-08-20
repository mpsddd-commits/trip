/**
 * 캐시 키 팩토리.
 *
 * 근거:
 *   Q1=A / WBR-15  자원 계층 키. 편집 후에는 `trip(tripId)` 만 무효화하고
 *                  검색·추천 캐시는 유지한다 (불필요한 외부 호출 방지 — NFR-4)
 *   Q16=A          persist 대상은 `trip` 접두사뿐이다 (`queryClient.ts` 참조)
 */
export const queryKeys = {
  config: () => ["config"] as const,

  /** 🔴 persist 대상 — 오프라인 조회의 근거 (FR-31) */
  trip: (tripId: string) => ["trip", tripId] as const,
  tripPrefix: () => ["trip"] as const,

  /** ⚠️ persist 제외 — 완료된 진행률이 되살아나면 안 된다 (DD-14) */
  job: (jobId: string) => ["job", jobId] as const,

  placeSearch: (query: string, page: number) => ["placeSearch", query, page] as const,
  placeContent: (placeId: string) => ["placeContent", placeId] as const,
  suggestions: (tripId: string, dayIndex: number, keyword: string) =>
    ["suggestions", tripId, dayIndex, keyword] as const,

  shared: (token: string) => ["shared", token] as const,
} as const;

/** persist 허용 여부 판정 (Q16=A). */
export function isPersistable(queryKey: readonly unknown[]): boolean {
  return queryKey[0] === "trip";
}
