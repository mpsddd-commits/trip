/**
 * 일자 탭 + 일자 요약 — FR-18, WBR-20.
 */
import type { Trip } from "@/shared/api/types";
import { dayColor } from "@/features/map/NaverMapAdapter";
import { dayElapsedMinutes, hasEstimatedTravel, itemsOf, totalStayMinutes } from "@/shared/selectors/trip";
import { Badge } from "@/shared/ui";

export function DayTabs({
  trip,
  selectedDayIndex,
  onSelect,
}: {
  trip: Pick<Trip, "days">;
  selectedDayIndex: number;
  onSelect: (dayIndex: number) => void;
}) {
  return (
    <nav className="day-tabs" aria-label="일자 선택">
      <ul className="day-tabs__list">
        {trip.days.map((day) => {
          const active = day.day_index === selectedDayIndex;
          return (
            <li key={day.day_index}>
              <button
                type="button"
                className={`day-tab ${active ? "day-tab--on" : ""}`}
                aria-current={active ? "page" : undefined}
                onClick={() => onSelect(day.day_index)}
              >
                {/* WBR-24 — 색상 옆에 항상 텍스트가 있다 */}
                <span
                  className="day-tab__swatch"
                  style={{ backgroundColor: dayColor(day.day_index) }}
                  aria-hidden="true"
                />
                {day.day_index}일차
                <span className="day-tab__count">{day.items.length}곳</span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

/** WBR-20 — 일자 요약. 서버 데이터에서 **파생 계산만** 한다. */
export function DayHeader({ trip, dayIndex }: { trip: Pick<Trip, "days">; dayIndex: number }) {
  const items = itemsOf(trip, dayIndex);
  if (items.length === 0) return null;

  const stay = totalStayMinutes(items);
  const elapsed = dayElapsedMinutes(items);
  const travel = Math.max(0, elapsed - stay);

  return (
    <header className="day-header">
      <h2 className="day-header__title">{dayIndex}일차</h2>
      <p className="day-header__stats">
        {items.length}곳 · 머무름 {Math.round(stay / 60)}시간 {stay % 60}분 · 이동 약{" "}
        {Math.round(travel)}분
      </p>
      {/* WBR-22 — 일자 단위로도 추정 여부를 알린다 */}
      {hasEstimatedTravel(items) ? (
        <Badge tone="warn" title="네이버가 대중교통·도보 경로를 제공하지 않아 추정한 값입니다">
          이동시간 추정 포함
        </Badge>
      ) : null}
    </header>
  );
}
