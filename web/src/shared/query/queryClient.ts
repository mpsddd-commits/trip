/**
 * W2 QueryClient — 서버 상태의 유일한 소유자.
 *
 * 근거:
 *   DD-17          서버 데이터는 Query 가, UI 상태는 Zustand 가 소유한다
 *   Q16=A / WBR-32 persist 대상은 `['trip', *]` **뿐**
 *   DD-14          🔴 `['job', *]` 는 persist 하지 않는다 —
 *                  완료된 진행률이 재방문 시 되살아나는 것을 막는다
 *   FR-31          오프라인에서 저장된 일정 조회
 */
import { QueryClient } from "@tanstack/react-query";
import { createAsyncStoragePersister } from "@tanstack/query-async-storage-persister";
import { get, set, del } from "idb-keyval";

import { isPersistable } from "./keys";

const ONE_DAY_MS = 24 * 60 * 60 * 1000;

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // 오프라인에서도 캐시된 값을 즉시 보여준다 (FR-31).
        staleTime: 30_000,
        gcTime: 7 * ONE_DAY_MS,
        retry: (failureCount, error) => {
          // 오프라인이면 재시도해도 소용없다 — 즉시 캐시로 폴백한다 (WBR-35).
          if (typeof error === "object" && error !== null && "offline" in error) return false;
          return failureCount < 2;
        },
        refetchOnWindowFocus: false,
      },
      mutations: { retry: 0 },
    },
  });
}

/** IndexedDB persister. `['trip', *]` 만 저장한다. */
export function createTripPersister() {
  return createAsyncStoragePersister({
    storage: {
      getItem: async (key: string) => (await get<string>(key)) ?? null,
      setItem: async (key: string, value: string) => {
        await set(key, value);
      },
      removeItem: async (key: string) => {
        await del(key);
      },
    },
    key: "trip-query-cache",
    throttleTime: 1_000,
  });
}

/**
 * `PersistQueryClientProvider` 에 넘길 옵션.
 *
 * 🔴 `shouldDehydrateQuery` 가 이 설계의 핵심이다.
 *    여기서 `job` 을 걸러내지 않으면 DD-14 가 깨진다.
 */
export const persistOptions = {
  persister: createTripPersister(),
  maxAge: 7 * ONE_DAY_MS,
  dehydrateOptions: {
    shouldDehydrateQuery: (query: { queryKey: readonly unknown[]; state: { status: string } }) =>
      query.state.status === "success" && isPersistable(query.queryKey),
  },
} as const;
