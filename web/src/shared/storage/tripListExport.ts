/**
 * 여행 목록 내보내기/가져오기 — 순수 함수 (PBT 대상).
 *
 * 근거:
 *   WBR-07  내보내기 — 브라우저 데이터를 잃었을 때의 **실질적 복구 수단**
 *   WBR-08  가져오기는 `trip_id` 기준 병합이며 **멱등**하다
 *   WP-05   `importList(exportList(x))` 가 원본과 집합 동등
 *   WP-06   같은 파일을 두 번 넣어도 목록이 늘지 않는다 (멱등)
 *
 * 이 모듈은 React·localStorage 에 의존하지 않는다 — 그래서 fast-check 로 직접 검증한다.
 */
import { isSavedTripRef, type SavedTripRef, type TripListExport } from "./tripList";

export const EXPORT_FORMAT = "trip-list-export" as const;
export const EXPORT_VERSION = 1 as const;

export function exportList(trips: SavedTripRef[], exportedAt: string): TripListExport {
  return {
    format: EXPORT_FORMAT,
    version: EXPORT_VERSION,
    exported_at: exportedAt,
    // 결정적 산출물을 위해 trip_id 로 정렬한다 (같은 입력 → 같은 파일).
    trips: [...trips].sort((a, b) => a.trip_id.localeCompare(b.trip_id)),
  };
}

export class ImportFormatError extends Error {}

/** 파일 내용을 파싱한다. 형식이 아니면 **추측하지 않고** 오류를 던진다. */
export function parseExport(text: string): TripListExport {
  let payload: unknown;
  try {
    payload = JSON.parse(text);
  } catch {
    throw new ImportFormatError("JSON 형식이 아닙니다.");
  }
  if (typeof payload !== "object" || payload === null) {
    throw new ImportFormatError("내용을 읽을 수 없습니다.");
  }
  const candidate = payload as Record<string, unknown>;
  if (candidate.format !== EXPORT_FORMAT) {
    throw new ImportFormatError("여행 목록 내보내기 파일이 아닙니다.");
  }
  if (candidate.version !== EXPORT_VERSION) {
    throw new ImportFormatError(`지원하지 않는 버전입니다: ${String(candidate.version)}`);
  }
  const trips = Array.isArray(candidate.trips) ? candidate.trips.filter(isSavedTripRef) : [];
  return {
    format: EXPORT_FORMAT,
    version: EXPORT_VERSION,
    exported_at: typeof candidate.exported_at === "string" ? candidate.exported_at : "",
    trips,
  };
}

/**
 * WBR-08 — `trip_id` 기준 병합. **멱등**하다.
 *
 * 같은 `trip_id` 가 양쪽에 있으면 **`saved_at` 이 더 최근인 쪽**을 남긴다.
 * 동률이면 기존 항목을 유지한다(가져오기가 기존 정보를 덮어쓰지 않게).
 */
export function mergeLists(current: SavedTripRef[], incoming: SavedTripRef[]): SavedTripRef[] {
  const byId = new Map<string, SavedTripRef>();
  for (const ref of current) byId.set(ref.trip_id, ref);
  for (const ref of incoming) {
    const existing = byId.get(ref.trip_id);
    if (existing === undefined || ref.saved_at > existing.saved_at) {
      byId.set(ref.trip_id, ref);
    }
  }
  return [...byId.values()].sort((a, b) => a.trip_id.localeCompare(b.trip_id));
}

/** 내보내기 결과를 다시 목록으로 되돌린다 (WP-05). */
export function importList(exported: TripListExport): SavedTripRef[] {
  return mergeLists([], exported.trips);
}
