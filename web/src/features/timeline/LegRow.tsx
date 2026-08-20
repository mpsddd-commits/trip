/**
 * 이동 구간 표시 — FR-10, FR-11, FR-12.
 *
 * 🔴 WBR-22 — **추정 이동시간에는 반드시 "추정" 배지를 붙인다.**
 *    네이버는 대중교통·도보 경로 API 를 제공하지 않으므로(CON-1) 이 값은 추정치다.
 *    확정값처럼 보이게 하면 사용자가 그 시간을 믿고 일정을 짠다.
 */
import type { ItineraryItem, TravelMode } from "@/shared/api/types";
import { openMap } from "@/shared/bridge";
import { routeUrl } from "@/shared/deeplink";
import { Badge, Button } from "@/shared/ui";

const MODE_LABEL: Map<TravelMode, string> = new Map([
  ["WALK", "도보"],
  ["CAR", "자동차"],
  ["TRANSIT", "대중교통"],
]);

function minutesBetween(from: ItineraryItem, to: ItineraryItem): number | null {
  if (!from.departure_at || !to.arrival_at) return null;
  const diff = Date.parse(to.arrival_at) - Date.parse(from.departure_at);
  return diff >= 0 ? Math.round(diff / 60_000) : null;
}

interface Props {
  from: ItineraryItem;
  to: ItineraryItem;
  defaultMode: TravelMode;
  canEdit: boolean;
  onChangeMode: (mode: TravelMode) => void;
}

export function LegRow({ from, to, defaultMode, canEdit, onChangeMode }: Props) {
  const mode = from.travel_mode ?? defaultMode;
  // WBR-04 — 소요시간은 서버가 채운 시각의 차이다. 여기서 새로 계산하지 않는다.
  const minutes = minutesBetween(from, to);
  const estimated = from.warnings.some((w) => w.type === "ESTIMATED_TRAVEL_TIME");

  const handleDirections = () => {
    openMap(routeUrl(from.place, to.place, mode));
  };

  return (
    <li className="leg-row">
      <span className="leg-row__line" aria-hidden="true" />
      <div className="leg-row__content">
        <label className="leg-row__mode">
          <span className="visually-hidden">이동수단</span>
          <select
            value={mode}
            disabled={!canEdit}
            onChange={(event) => onChangeMode(event.target.value as TravelMode)}
          >
            {[...MODE_LABEL.entries()].map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>

        <span className="leg-row__duration">
          {minutes === null ? "이동시간 미계산" : `약 ${minutes}분`}
        </span>

        {/* WBR-22 — 추정치임을 반드시 드러낸다 */}
        {estimated ? (
          <Badge tone="warn" title="네이버가 대중교통·도보 경로를 제공하지 않아 추정한 값입니다">
            추정
          </Badge>
        ) : null}

        {/* FR-12 — 정확한 안내는 네이버지도 앱에 위임한다 */}
        <Button variant="ghost" onClick={handleDirections}>
          네이버지도로 길찾기
        </Button>
      </div>
    </li>
  );
}
