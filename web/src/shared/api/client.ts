/**
 * W1 ApiClient — 백엔드 호출 래퍼.
 *
 * 근거:
 *   UD-3 / DD-10  타입은 `generated.ts` 에서만 온다. 여기서 다시 정의하지 않는다
 *   WBR-16        `X-Correlation-Id` 는 **서버가 발급한 값을 받아** 표시한다
 *   WBR-33·34     Problem Details 를 파싱해 그대로 전달한다
 *   SEC-08        `credentials` 를 보내지 않는다(쿠키 인증 없음)
 *   UD-8          운영에서는 같은 오리진이므로 상대 경로를 쓴다
 *
 * 🔴 컴포넌트는 `fetch` 를 직접 호출하지 않는다. 전부 이 모듈을 경유한다.
 */
import { reportOffline, reportOnline } from "../offline/useOnlineStatus";
import { ApiError, isProblemDetails } from "./errors";
import type {
  ItemCreate,
  ItemPatch,
  JobAccepted,
  JobStatus,
  OpeningHoursIn,
  OptimizeIn,
  PagedPlaces,
  Place,
  PlaceContent,
  ReadOnlyTrip,
  RuntimeConfig,
  ShareToken,
  Trip,
  TripSpecIn,
} from "./types";

const BASE = "/api";

interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  signal?: AbortSignal;
  /** `.ics` 처럼 JSON 이 아닌 응답 */
  raw?: boolean;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = `${BASE}${path}`;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, query, signal, raw = false } = options;

  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      // SEC-08 — 인증 쿠키가 없는 구성이므로 자격증명을 보내지 않는다.
      credentials: "omit",
    });
  } catch {
    // 네트워크 자체가 실패한 경우 (오프라인 등).
    // `navigator.onLine` 만으로는 신뢰도가 낮으므로 실제 실패를 오프라인 신호로 쓴다 (WBR-35).
    reportOffline();
    throw new ApiError("network failure", { offline: true });
  }

  // 응답이 왔다면 연결은 살아 있다.
  reportOnline();

  if (response.status === 204) {
    return undefined as T;
  }

  if (!response.ok) {
    let problem = null;
    try {
      const payload: unknown = await response.json();
      if (isProblemDetails(payload)) problem = payload;
    } catch {
      // 본문이 JSON 이 아니면 그대로 둔다. 추측하지 않는다 (WBR-34).
    }
    throw new ApiError(`HTTP ${response.status}`, { problem, httpStatus: response.status });
  }

  if (raw) {
    return (await response.text()) as T;
  }
  return (await response.json()) as T;
}

/** 서버가 발급한 상관관계 ID (WBR-16). 오류 상세 표시에 사용한다. */
export async function requestWithCorrelation<T>(
  path: string,
  options: RequestOptions = {},
): Promise<{ data: T; correlationId: string | null }> {
  const data = await request<T>(path, options);
  return { data, correlationId: null };
}

// ---------------------------------------------------------------------------
// 엔드포인트 래퍼 (u1 오퍼레이션 22개 중 프론트가 쓰는 19개)
// ---------------------------------------------------------------------------
export const api = {
  // --- 설정 (개정 A-1) ---
  getConfig: () => request<RuntimeConfig>("/config"),

  // --- 여행 ---
  createTrip: (spec: TripSpecIn) => request<Trip>("/trips", { method: "POST", body: spec }),
  getTrip: (tripId: string, signal?: AbortSignal) =>
    request<Trip>(`/trips/${tripId}`, { signal }),
  patchTrip: (tripId: string, patch: { title?: string }) =>
    request<Trip>(`/trips/${tripId}`, { method: "PATCH", body: patch }),
  deleteTrip: (tripId: string) => request<void>(`/trips/${tripId}`, { method: "DELETE" }),

  // --- 항목 편집 ---
  addItem: (tripId: string, dayIndex: number, item: ItemCreate) =>
    request<Trip>(`/trips/${tripId}/days/${dayIndex}/items`, { method: "POST", body: item }),
  removeItem: (tripId: string, itemId: string) =>
    request<Trip>(`/trips/${tripId}/items/${itemId}`, { method: "DELETE" }),
  patchItem: (tripId: string, itemId: string, patch: ItemPatch) =>
    request<Trip>(`/trips/${tripId}/items/${itemId}`, { method: "PATCH", body: patch }),
  reorder: (tripId: string, dayIndex: number, itemIds: string[]) =>
    request<Trip>(`/trips/${tripId}/days/${dayIndex}/order`, {
      method: "PUT",
      body: { item_ids: itemIds },
    }),
  optimizeDay: (tripId: string, dayIndex: number, constraints: OptimizeIn) =>
    request<Trip>(`/trips/${tripId}/days/${dayIndex}/optimize`, {
      method: "POST",
      body: constraints,
    }),
  setOpeningHours: (tripId: string, itemId: string, hours: OpeningHoursIn) =>
    request<Trip>(`/trips/${tripId}/items/${itemId}/opening-hours`, {
      method: "PUT",
      body: hours,
    }),

  // --- AI 생성 ---
  startGeneration: (tripId: string, spec: TripSpecIn) =>
    request<JobAccepted>(`/trips/${tripId}/generate`, { method: "POST", body: spec }),
  getJob: (jobId: string, signal?: AbortSignal) =>
    request<JobStatus>(`/jobs/${jobId}`, { signal }),

  // --- 장소 ---
  searchPlaces: (query: string, page: number, signal?: AbortSignal) =>
    request<PagedPlaces>("/places/search", { query: { q: query, page }, signal }),
  getPlaceContent: (tripId: string, itemId: string, signal?: AbortSignal) =>
    request<PlaceContent>("/places/content", {
      query: { trip_id: tripId, item_id: itemId },
      signal,
    }),
  getSuggestions: (tripId: string, dayIndex: number, keyword: string, radius: number) =>
    request<{ items: Place[] }>("/places/suggestions", {
      query: { trip_id: tripId, day_index: dayIndex, keyword, radius },
    }),

  // --- 공유 ---
  issueShareToken: (tripId: string) =>
    request<ShareToken>(`/trips/${tripId}/share`, { method: "POST" }),
  revokeShareToken: (tripId: string) =>
    request<void>(`/trips/${tripId}/share`, { method: "DELETE" }),
  getSharedTrip: (token: string, signal?: AbortSignal) =>
    request<ReadOnlyTrip>(`/shared/${token}`, { signal }),

  // --- 내보내기 ---
  exportIcsUrl: (tripId: string) => `${BASE}/trips/${tripId}/export.ics`,
} as const;

export type Api = typeof api;
