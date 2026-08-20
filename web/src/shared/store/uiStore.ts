/**
 * W3 UiStore — 화면 상태만 보관한다.
 *
 * 근거:
 *   WBR-03   🔴 **서버 데이터를 담지 않는다.** 식별자와 UI 플래그만 보관한다
 *   FR-19 / WBR-18
 *            `selectedItemId` 는 지도 ↔ 타임라인을 잇는 유일한 연결점이다.
 *            모바일에서 탭이 갈려도 이 값을 유지해 "상태 연속성"으로 FR-19 를 만족시킨다
 *   Q7=A     `draggingOrder` 는 낙관적 업데이트의 임시 순서
 */
import { create } from "zustand";

export type MobilePane = "timeline" | "map";

interface UiState {
  selectedDayIndex: number;
  selectedItemId: string | null;
  /** 드래그 중 임시 순서. 서버 확정 시 null 로 되돌린다 (WBR-17). */
  draggingOrder: string[] | null;
  mobilePane: MobilePane;
  detailItemId: string | null;
  /** 검색 패널을 특정 이름으로 미리 채워 열 때 사용 (WBR-29) */
  searchPrefill: string | null;

  selectDay: (dayIndex: number) => void;
  selectItem: (itemId: string | null) => void;
  setDraggingOrder: (order: string[] | null) => void;
  setMobilePane: (pane: MobilePane) => void;
  openDetail: (itemId: string) => void;
  closeDetail: () => void;
  openSearchWith: (name: string) => void;
  closeSearch: () => void;
  reset: () => void;
}

const initial = {
  selectedDayIndex: 1,
  selectedItemId: null,
  draggingOrder: null,
  mobilePane: "timeline" as MobilePane,
  detailItemId: null,
  searchPrefill: null,
};

export const useUiStore = create<UiState>((set) => ({
  ...initial,

  selectDay: (dayIndex) => set({ selectedDayIndex: dayIndex, selectedItemId: null }),

  // WBR-18 — 선택은 탭 전환과 무관하게 유지된다.
  selectItem: (itemId) => set({ selectedItemId: itemId }),

  setDraggingOrder: (order) => set({ draggingOrder: order }),
  setMobilePane: (pane) => set({ mobilePane: pane }),

  openDetail: (itemId) => set({ detailItemId: itemId, selectedItemId: itemId }),
  closeDetail: () => set({ detailItemId: null }),

  openSearchWith: (name) => set({ searchPrefill: name }),
  closeSearch: () => set({ searchPrefill: null }),

  reset: () => set(initial),
}));
