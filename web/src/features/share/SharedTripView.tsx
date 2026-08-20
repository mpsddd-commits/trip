/**
 * W12 SharedTripView — 공유 링크 읽기 전용 화면 (FR-25).
 *
 * 🔴 DD-25 / BR-37 의 UI 측 대응
 *    편집 컴포넌트를 `readOnly` 플래그로 **숨기는 것이 아니라 트리에 넣지 않는다.**
 *    - `DndContext` · `AddItemButton` · `OptimizeButton` 을 import 하지 않는다
 *    - 응답 타입 `ReadOnlyTrip` 에는 `share_token` 필드가 **없다**(A-2) —
 *      토큰을 읽으려 하면 컴파일 오류가 난다
 *
 *    구조 테스트(`tests/structure/shared-view.test.tsx`)가 이를 강제한다.
 */
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import type { ItineraryItem } from "@/shared/api/types";
import { queryKeys } from "@/shared/query/keys";
import { dayElapsedMinutes, hasEstimatedTravel, totalStayMinutes } from "@/shared/selectors/trip";
import { Badge, Banner, EmptyState, Skeleton } from "@/shared/ui";

function toKstTime(iso: string | null | undefined): string {
  if (!iso) return "--:--";
  return new Date(iso).toLocaleTimeString("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Seoul",
  });
}

function ReadOnlyItem({ item, order }: { item: ItineraryItem; order: number }) {
  return (
    <li className="item-card item-card--readonly">
      <span className="item-card__order item-card__order--static">{order}</span>
      <div className="item-card__body">
        <p className="item-card__time">
          {toKstTime(item.arrival_at)} – {toKstTime(item.departure_at)}
        </p>
        <p className="item-card__name">{item.place.name}</p>
        {item.place.road_address ? (
          <p className="item-card__address">{item.place.road_address}</p>
        ) : null}
        {item.memo ? <p className="item-card__memo">{item.memo}</p> : null}
      </div>
    </li>
  );
}

export function SharedTripView() {
  const { token = "" } = useParams<{ token: string }>();

  const { data, isPending, isError } = useQuery({
    queryKey: queryKeys.shared(token),
    queryFn: ({ signal }) => api.getSharedTrip(token, signal),
    enabled: token !== "",
    retry: false,
  });

  if (isPending) return <Skeleton lines={6} label="공유된 일정 불러오는 중" />;

  if (isError || !data) {
    return (
      <main className="page">
        <EmptyState
          title="일정을 찾을 수 없습니다"
          description="링크가 만료되었거나 공유가 해제되었을 수 있습니다."
        />
      </main>
    );
  }

  return (
    <main className="page page--shared">
      <Banner tone="info">공유된 일정입니다. 보기 전용이며 수정할 수 없습니다.</Banner>

      <header className="page__header">
        <h1>{data.title}</h1>
        <p className="page__meta">
          {data.destination} · {data.start_date} ~ {data.end_date} · {data.party_size}명
        </p>
      </header>

      {data.days.map((day) => {
        const stay = totalStayMinutes(day.items);
        const elapsed = dayElapsedMinutes(day.items);
        return (
          <section key={day.day_index} className="shared-day">
            <header className="day-header">
              <h2 className="day-header__title">{day.day_index}일차</h2>
              <p className="day-header__stats">
                {day.items.length}곳 · 머무름 {Math.round(stay / 60)}시간 {stay % 60}분 · 이동 약{" "}
                {Math.max(0, Math.round(elapsed - stay))}분
              </p>
              {/* WBR-22 — 공유 화면에서도 추정 여부를 숨기지 않는다 */}
              {hasEstimatedTravel(day.items) ? (
                <Badge tone="warn">이동시간 추정 포함</Badge>
              ) : null}
            </header>

            {day.items.length === 0 ? (
              <p className="shared-day__empty">담긴 장소가 없습니다.</p>
            ) : (
              <ol className="timeline__list">
                {day.items.map((item, index) => (
                  <ReadOnlyItem key={item.item_id} item={item} order={index + 1} />
                ))}
              </ol>
            )}
          </section>
        );
      })}
    </main>
  );
}
