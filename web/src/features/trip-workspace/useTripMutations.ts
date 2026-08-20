/**
 * 여행 편집 뮤테이션 모음.
 *
 * 🔴 WBR-14 — u1 의 편집 API 는 **여행 전체를 반환**한다.
 *    따라서 응답으로 캐시를 **직접 갱신**하고 추가 GET 을 하지 않는다.
 *    (`invalidateQueries` 를 쓰면 불필요한 왕복이 한 번 더 생긴다)
 *
 * WBR-15  무효화 대상은 `['trip', tripId]` 뿐. 검색·추천 캐시는 유지한다
 * WBR-17  드래그는 낙관적 업데이트 + 실패 시 롤백
 * WBR-35  오프라인이면 애초에 호출하지 않는다 (호출자가 `canEdit` 로 막는다)
 */
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import { describeError } from "@/shared/api/errors";
import type { ItemCreate, ItemPatch, OpeningHoursIn, Trip } from "@/shared/api/types";
import { queryKeys } from "@/shared/query/keys";
import { useUiStore } from "@/shared/store/uiStore";

export interface MutationFeedback {
  notifyError: (message: string, correlationId: string | null) => void;
}

export function useTripMutations(tripId: string, feedback: MutationFeedback) {
  const queryClient = useQueryClient();
  const setDraggingOrder = useUiStore((s) => s.setDraggingOrder);

  /** WBR-14 — 응답(여행 전체)으로 캐시를 직접 갱신한다. */
  const applyTrip = (trip: Trip) => {
    queryClient.setQueryData(queryKeys.trip(tripId), trip);
  };

  const fail = (action: string) => (cause: unknown) => {
    const { message, correlationId } = describeError(cause, action);
    feedback.notifyError(message, correlationId);
  };

  const addItem = useMutation({
    mutationFn: ({ dayIndex, item }: { dayIndex: number; item: ItemCreate }) =>
      api.addItem(tripId, dayIndex, item),
    onSuccess: applyTrip,
    onError: fail("장소를 추가하지 못했습니다."),
  });

  const removeItem = useMutation({
    mutationFn: (itemId: string) => api.removeItem(tripId, itemId),
    onSuccess: applyTrip,
    onError: fail("장소를 삭제하지 못했습니다."),
  });

  const patchItem = useMutation({
    mutationFn: ({ itemId, patch }: { itemId: string; patch: ItemPatch }) =>
      api.patchItem(tripId, itemId, patch),
    onSuccess: applyTrip,
    onError: fail("변경 사항을 저장하지 못했습니다."),
  });

  const reorder = useMutation({
    mutationFn: ({ dayIndex, itemIds }: { dayIndex: number; itemIds: string[] }) =>
      api.reorder(tripId, dayIndex, itemIds),
    onSuccess: (trip) => {
      applyTrip(trip);
      setDraggingOrder(null); // 서버가 확정했으므로 임시 순서를 버린다
    },
    onError: (cause) => {
      // WBR-17 — 원래 순서로 되돌린다. 화면과 서버가 갈라진 채로 두지 않는다.
      setDraggingOrder(null);
      fail("순서를 저장하지 못했습니다.")(cause);
    },
  });

  const optimize = useMutation({
    mutationFn: (dayIndex: number) => api.optimizeDay(tripId, dayIndex, {}),
    onSuccess: applyTrip,
    onError: fail("순서를 최적화하지 못했습니다."),
  });

  const setOpeningHours = useMutation({
    mutationFn: ({ itemId, hours }: { itemId: string; hours: OpeningHoursIn }) =>
      api.setOpeningHours(tripId, itemId, hours),
    onSuccess: applyTrip,
    onError: fail("영업시간을 저장하지 못했습니다."),
  });

  const issueShare = useMutation({
    mutationFn: () => api.issueShareToken(tripId),
    onSuccess: () => {
      // 공유 토큰은 여행 본문에 포함되므로 이때만 재조회한다.
      void queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) });
    },
    onError: fail("공유 링크를 만들지 못했습니다."),
  });

  const revokeShare = useMutation({
    mutationFn: () => api.revokeShareToken(tripId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) });
    },
    onError: fail("공유 링크를 해제하지 못했습니다."),
  });

  return {
    addItem,
    removeItem,
    patchItem,
    reorder,
    optimize,
    setOpeningHours,
    issueShare,
    revokeShare,
    busy:
      addItem.isPending ||
      removeItem.isPending ||
      patchItem.isPending ||
      reorder.isPending ||
      optimize.isPending ||
      setOpeningHours.isPending,
  };
}
