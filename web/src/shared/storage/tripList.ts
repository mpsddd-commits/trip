/**
 * 로컬 여행 목록 (`localStorage`).
 *
 * 🔴 이 파일이 존재하는 이유와 그 대가
 *    백엔드는 여행 목록 API 를 **의도적으로 제공하지 않는다** (DD-21 / BR-39 —
 *    계정이 없는 구성에서 목록은 열거 취약점). 그래서 "내 여행"은 여기에만 존재한다.
 *    브라우저 데이터를 지우면 서버에 데이터가 남아 있어도 UUID 를 몰라 **접근할 수 없다.**
 *
 * 근거:
 *   WBR-05  여행 생성·토큰 발급 시 저장
 *   WBR-06  상시 고지 (UI 측 책임)
 *   WBR-07  내보내기
 *   WBR-08  가져오기는 **멱등** (WP-06)
 *   WBR-09  서버에서 404 면 자동 삭제하지 않고 사용자에게 확인받는다
 */

const STORAGE_KEY = "trip.savedTrips.v1";

export interface SavedTripRef {
  trip_id: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  /** 발급했다면 보관한다 — **브라우저 데이터를 잃었을 때의 복구 수단** (WBR-06) */
  share_token: string | null;
  saved_at: string;
}

export interface TripListExport {
  format: "trip-list-export";
  version: 1;
  exported_at: string;
  trips: SavedTripRef[];
}

// ---------------------------------------------------------------------------
function readRaw(): SavedTripRef[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isSavedTripRef) : [];
  } catch {
    // 손상된 값이 있어도 앱이 죽지 않게 한다. 조용히 비우지는 않는다 — 덮어쓰지 않을 뿐.
    return [];
  }
}

function writeRaw(refs: SavedTripRef[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(refs));
}

export function isSavedTripRef(value: unknown): value is SavedTripRef {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.trip_id === "string" &&
    typeof v.title === "string" &&
    typeof v.destination === "string" &&
    typeof v.start_date === "string" &&
    typeof v.end_date === "string" &&
    typeof v.saved_at === "string" &&
    (v.share_token === null || typeof v.share_token === "string")
  );
}

// ---------------------------------------------------------------------------
/** 저장된 순서: 최근 저장 순 내림차순 */
export function listSavedTrips(): SavedTripRef[] {
  return [...readRaw()].sort((a, b) => b.saved_at.localeCompare(a.saved_at));
}

export function saveTripRef(ref: Omit<SavedTripRef, "saved_at"> & { saved_at?: string }): SavedTripRef[] {
  const saved: SavedTripRef = { ...ref, saved_at: ref.saved_at ?? new Date().toISOString() };
  const others = readRaw().filter((r) => r.trip_id !== saved.trip_id);
  const next = [...others, saved];
  writeRaw(next);
  return next;
}

export function updateShareToken(tripId: string, shareToken: string | null): SavedTripRef[] {
  const next = readRaw().map((r) => (r.trip_id === tripId ? { ...r, share_token: shareToken } : r));
  writeRaw(next);
  return next;
}

/** WBR-09 — 사용자가 명시적으로 요청했을 때만 호출한다. 404 를 봤다고 자동 삭제하지 않는다. */
export function removeTripRef(tripId: string): SavedTripRef[] {
  const next = readRaw().filter((r) => r.trip_id !== tripId);
  writeRaw(next);
  return next;
}

export function isFirstTrip(): boolean {
  return readRaw().length === 0;
}

/** 테스트·초기화용 */
export function clearTripRefs(): void {
  localStorage.removeItem(STORAGE_KEY);
}
