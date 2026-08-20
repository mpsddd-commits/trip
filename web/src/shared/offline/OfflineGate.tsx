/**
 * W15 OfflineGate — 오프라인 시 편집을 차단한다.
 *
 * 🔴 WBR-35 — 오프라인에서는 **낙관적 업데이트를 시도조차 하지 않는다.**
 *    시도하면 화면과 서버가 갈라지고, 복귀 시 어느 쪽이 옳은지 알 수 없게 된다.
 *    편집을 막았기 때문에 충돌 병합이 필요 없다 (OUT-6).
 *
 * WBR-36 — 온라인 복귀 시 서버가 항상 우선. `['trip', *]` 를 재검증한다.
 */
import { createContext, useContext, useEffect, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../query/keys";
import { Banner } from "../ui";
import { useOnlineStatus } from "./useOnlineStatus";

interface OfflineContextValue {
  offline: boolean;
  /** 편집 가능 여부. 컴포넌트는 이 값으로 버튼·드래그를 비활성화한다. */
  canEdit: boolean;
}

const OfflineContext = createContext<OfflineContextValue>({ offline: false, canEdit: true });

export function OfflineGate({ children }: { children: ReactNode }) {
  const { offline } = useOnlineStatus();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (offline) return;
    // WBR-36 — 복귀 시 서버 데이터를 다시 확인한다. 로컬 변경을 밀어올리지 않는다.
    void queryClient.invalidateQueries({ queryKey: queryKeys.tripPrefix() });
  }, [offline, queryClient]);

  return (
    <OfflineContext.Provider value={{ offline, canEdit: !offline }}>
      {offline ? (
        <Banner tone="warn">
          오프라인입니다. 저장된 일정만 볼 수 있어요. 편집·검색·AI 생성은 연결되면 다시 사용할 수
          있습니다.
        </Banner>
      ) : null}
      {children}
    </OfflineContext.Provider>
  );
}

export function useOfflineGate(): OfflineContextValue {
  return useContext(OfflineContext);
}

/**
 * WBR-35 — 편집 동작을 감싸는 가드.
 *
 * 오프라인이면 실행하지 않고 `false` 를 반환한다. 호출자는 안내만 띄우면 된다.
 */
export function guardEdit(canEdit: boolean, action: () => void): boolean {
  if (!canEdit) return false;
  action();
  return true;
}
