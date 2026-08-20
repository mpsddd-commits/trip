/**
 * 런타임 설정 제공자 — 개정 A-1 (`GET /api/config`).
 *
 * 근거:
 *   Q4=A    지도 SDK 키를 **런타임에** 받는다. 빌드 시 주입은 키 변경마다 이미지 재빌드가 필요
 *   WBR-32  부팅 시 1회 조회하고 캐시한다. **persist 하지 않는다**(서버 설정 변경이 즉시 반영되어야 함)
 *   WBR-10  폼 상한(`limits`)을 여기서 받아 쓴다 — 프론트에 숫자를 하드코딩하지 않는다
 *   WBR-30  데모 배너의 데이터 원천
 *   WBR-31  설정 조회에 실패해도 앱은 뜬다 (지도만 비활성)
 */
import { createContext, useContext, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { Limits, RuntimeConfig } from "../api/types";
import { queryKeys } from "../query/keys";

/** 서버 응답을 받기 전/실패 시의 보수적 기본값. 서버 값이 오면 대체된다. */
export const FALLBACK_LIMITS: Limits = {
  max_trip_days: 10,
  max_items_per_day: 15,
  max_items_per_trip: 100,
};

interface RuntimeConfigContextValue {
  config: RuntimeConfig | null;
  limits: Limits;
  /** 설정 조회 실패 — 지도는 비활성이지만 나머지는 동작한다 (WBR-31) */
  failed: boolean;
  loading: boolean;
}

const RuntimeConfigContext = createContext<RuntimeConfigContextValue>({
  config: null,
  limits: FALLBACK_LIMITS,
  failed: false,
  loading: true,
});

export function RuntimeConfigProvider({ children }: { children: ReactNode }) {
  const { data, isPending, isError } = useQuery({
    queryKey: queryKeys.config(),
    queryFn: () => api.getConfig(),
    // WBR-32 — 부팅 시 1회. 서버 설정이 바뀌면 새로고침으로 반영된다.
    staleTime: Infinity,
    gcTime: Infinity,
    retry: 1,
  });

  const value: RuntimeConfigContextValue = {
    config: data ?? null,
    // WBR-10 — 서버가 준 상한을 쓰되, 못 받았으면 보수적 기본값으로 폼이 멈추지 않게 한다.
    limits: data?.limits ?? FALLBACK_LIMITS,
    failed: isError,
    loading: isPending,
  };

  return <RuntimeConfigContext.Provider value={value}>{children}</RuntimeConfigContext.Provider>;
}

export function useRuntimeConfig(): RuntimeConfigContextValue {
  return useContext(RuntimeConfigContext);
}

/** 지도 SDK 초기화에 쓰는 키. 없으면 지도 영역만 안내로 대체된다 (WBR-31, WBR-40). */
export function useMapClientKey(): string | null {
  return useRuntimeConfig().config?.map_client_key ?? null;
}
