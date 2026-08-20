/**
 * 일정 항목 카드 — FR-5, FR-7, FR-9, FR-13, FR-17.
 *
 * 근거:
 *   WBR-21  경고 배지 4종 — **서버가 준 것만** 표시한다 (WBR-04)
 *   WBR-24  번호 + 색상 + 라벨 (색상 단독 금지)
 *   WBR-37  키보드로 순서 변경 가능 (@dnd-kit 키보드 센서)
 *   WBR-38  `aria-label` 부여
 *   WBR-35  오프라인이면 편집 비활성
 */
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import type { ItineraryItem, WarningType } from "@/shared/api/types";
import { dayColor } from "@/features/map/NaverMapAdapter";
import { Badge, Button, type BadgeTone } from "@/shared/ui";

/** WBR-21 — 서버 경고 4종의 표시 문구와 톤 */
const WARNING_VIEW: Map<WarningType, { label: string; tone: BadgeTone }> = new Map([
  ["FIXED_TIME_CONFLICT", { label: "시간 충돌", tone: "danger" }],
  ["DAY_OVERFLOW", { label: "종료시각 초과", tone: "warn" }],
  ["OUTSIDE_OPENING_HOURS", { label: "영업시간 밖", tone: "warn" }],
  ["ESTIMATED_TRAVEL_TIME", { label: "이동시간 추정", tone: "info" }],
]);

/** 생성 타입에서 시각은 `string | null | undefined` 다 (서버가 계산 전이면 없음). */
function toKstTime(iso: string | null | undefined): string {
  if (!iso) return "--:--";
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Seoul",
  });
}

interface Props {
  item: ItineraryItem;
  order: number;
  dayIndex: number;
  selected: boolean;
  canEdit: boolean;
  onSelect: () => void;
  onOpenDetail: () => void;
  onRemove: () => void;
}

export function ItemCard({
  item,
  order,
  dayIndex,
  selected,
  canEdit,
  onSelect,
  onOpenDetail,
  onRemove,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: item.item_id,
    disabled: !canEdit, // WBR-35
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.6 : 1,
  };

  // WBR-21 — 서버가 준 경고만. 여기서 만들어내지 않는다.
  const warnings = item.warnings
    .map((w) => ({ ...WARNING_VIEW.get(w.type), detail: w.detail }))
    .filter((w): w is { label: string; tone: BadgeTone; detail: string } => w.label !== undefined);

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`item-card ${selected ? "item-card--selected" : ""}`}
      // WBR-38 — 스크린리더에 순서·시각·장소를 함께 알린다
      aria-label={`${dayIndex}일차 ${order}번, ${toKstTime(item.arrival_at)} ${item.place.name}`}
    >
      <button
        type="button"
        className="item-card__order"
        style={{ backgroundColor: dayColor(dayIndex) }}
        onClick={onSelect}
        aria-label={`${order}번 항목 선택`}
      >
        {order}
      </button>

      <div className="item-card__body" onClick={onSelect} role="presentation">
        <p className="item-card__time">
          {toKstTime(item.arrival_at)} – {toKstTime(item.departure_at)}
          <span className="item-card__stay"> · {item.stay_minutes}분 머무름</span>
        </p>
        <p className="item-card__name">{item.place.name}</p>
        {item.place.road_address ? (
          <p className="item-card__address">{item.place.road_address}</p>
        ) : null}
        {item.memo ? <p className="item-card__memo">{item.memo}</p> : null}

        {warnings.length > 0 ? (
          <div className="item-card__warnings">
            {warnings.map((warning) => (
              <Badge key={warning.label} tone={warning.tone} title={warning.detail}>
                {warning.label}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>

      <div className="item-card__actions">
        <Button variant="ghost" onClick={onOpenDetail}>
          상세
        </Button>
        {canEdit ? (
          <>
            {/* WBR-37 — 키보드로도 순서를 바꿀 수 있어야 한다 */}
            <button
              type="button"
              className="item-card__handle"
              aria-label={`${item.place.name} 순서 변경 (방향키로 이동)`}
              {...attributes}
              {...listeners}
            >
              ⠿
            </button>
            <Button variant="ghost" onClick={onRemove} aria-label={`${item.place.name} 삭제`}>
              삭제
            </Button>
          </>
        ) : null}
      </div>
    </li>
  );
}
