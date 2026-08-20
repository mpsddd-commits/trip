/**
 * W8 TimelineView — 드래그 편집 가능한 시간표 (FR-5, FR-7, FR-8, FR-9, FR-11).
 *
 * 근거:
 *   WBR-17  낙관적 업데이트 + 실패 시 롤백
 *   WBR-19  일자 간 이동은 **드래그 + 메뉴 두 경로** — 모바일에서 탭을 넘는 드래그가 어렵다
 *   WBR-35  🔴 오프라인이면 드래그 자체를 비활성화한다
 *   WBR-37  @dnd-kit 키보드 센서로 순서 변경 (NFR-6)
 *   Q17=A   @dnd-kit — 터치·키보드 접근성 기본 지원
 */
import { useMemo } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";

import type { ItineraryItem, TravelMode, Trip } from "@/shared/api/types";
import { itemsOf } from "@/shared/selectors/trip";
import { useUiStore } from "@/shared/store/uiStore";
import { Button, EmptyState } from "@/shared/ui";

import { DayHeader } from "./DayTabs";
import { ItemCard } from "./ItemCard";
import { LegRow } from "./LegRow";

interface Props {
  trip: Pick<Trip, "days" | "default_travel_mode">;
  dayIndex: number;
  canEdit: boolean;
  busy: boolean;
  onReorder: (itemIds: string[]) => void;
  onRemoveItem: (itemId: string) => void;
  onChangeMode: (itemId: string, mode: TravelMode) => void;
  onOptimize: () => void;
  onAddPlace: () => void;
}

export function TimelineView({
  trip,
  dayIndex,
  canEdit,
  busy,
  onReorder,
  onRemoveItem,
  onChangeMode,
  onOptimize,
  onAddPlace,
}: Props) {
  const selectedItemId = useUiStore((s) => s.selectedItemId);
  const selectItem = useUiStore((s) => s.selectItem);
  const openDetail = useUiStore((s) => s.openDetail);
  const draggingOrder = useUiStore((s) => s.draggingOrder);
  const setDraggingOrder = useUiStore((s) => s.setDraggingOrder);

  const serverItems = itemsOf(trip, dayIndex);

  // WBR-17 — 드래그 중에는 임시 순서를 보여준다. 서버 응답이 오면 임시 순서가 사라진다.
  const items = useMemo<ItineraryItem[]>(() => {
    if (!draggingOrder) return serverItems;
    const byId = new Map(serverItems.map((item) => [item.item_id, item]));
    const ordered = draggingOrder
      .map((id) => byId.get(id))
      .filter((item): item is ItineraryItem => item !== undefined);
    return ordered.length === serverItems.length ? ordered : serverItems;
  }, [draggingOrder, serverItems]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    // WBR-37 — 키보드만으로 순서를 바꿀 수 있어야 한다
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const ids = items.map((item) => item.item_id);
    const from = ids.indexOf(String(active.id));
    const to = ids.indexOf(String(over.id));
    if (from < 0 || to < 0) return;

    const next = [...ids];
    const [moved] = next.splice(from, 1);
    if (moved === undefined) return;
    next.splice(to, 0, moved);

    setDraggingOrder(next); // 즉시 화면 반영
    onReorder(next); // 서버 확정 (실패 시 뮤테이션이 롤백)
  };

  if (items.length === 0) {
    return (
      <div className="timeline">
        <DayHeader trip={trip} dayIndex={dayIndex} />
        <EmptyState
          title="이 날에 담긴 장소가 없습니다"
          description={canEdit ? "장소를 검색해 담아보세요." : "오프라인에서는 편집할 수 없습니다."}
          action={
            canEdit ? (
              <Button variant="primary" onClick={onAddPlace}>
                장소 추가
              </Button>
            ) : undefined
          }
        />
      </div>
    );
  }

  return (
    <div className="timeline">
      <DayHeader trip={trip} dayIndex={dayIndex} />

      <div className="timeline__actions">
        <Button variant="secondary" onClick={onAddPlace} disabled={!canEdit || busy}>
          장소 추가
        </Button>
        <Button variant="secondary" onClick={onOptimize} disabled={!canEdit || busy || items.length < 3}>
          순서 최적화
        </Button>
      </div>

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext
          items={items.map((item) => item.item_id)}
          strategy={verticalListSortingStrategy}
        >
          <ol className="timeline__list">
            {items.map((item, index) => {
              const next = items[index + 1];
              return (
                <li key={item.item_id} className="timeline__entry">
                  <ol className="timeline__item-wrapper">
                    <ItemCard
                      item={item}
                      order={index + 1}
                      dayIndex={dayIndex}
                      selected={item.item_id === selectedItemId}
                      canEdit={canEdit && !busy}
                      onSelect={() => selectItem(item.item_id)}
                      onOpenDetail={() => openDetail(item.item_id)}
                      onRemove={() => onRemoveItem(item.item_id)}
                    />
                  </ol>
                  {next ? (
                    <ol className="timeline__leg-wrapper">
                      <LegRow
                        from={item}
                        to={next}
                        defaultMode={trip.default_travel_mode}
                        canEdit={canEdit && !busy}
                        onChangeMode={(mode) => onChangeMode(item.item_id, mode)}
                      />
                    </ol>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </SortableContext>
      </DndContext>
    </div>
  );
}
