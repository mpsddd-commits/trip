/**
 * 지도 범례.
 *
 * 근거:
 *   WBR-23  선 종류의 의미를 설명한다 — 점선이 "추정"임을 알려야 한다 (CON-1)
 *   WBR-24  일자 색상에 **텍스트 라벨을 병기**한다 (NFR-6 — 색상 단독 금지)
 */
import { dayColor } from "./NaverMapAdapter";

export function MapLegend({ dayIndices, hasDashed }: { dayIndices: number[]; hasDashed: boolean }) {
  if (dayIndices.length === 0) return null;

  return (
    <div className="map-legend" aria-label="지도 범례">
      <ul className="map-legend__days">
        {dayIndices.map((dayIndex) => (
          <li key={dayIndex} className="map-legend__item">
            <span
              className="map-legend__swatch"
              style={{ backgroundColor: dayColor(dayIndex) }}
              aria-hidden="true"
            />
            {/* WBR-24 — 색상만으로 구분하지 않는다 */}
            <span className="map-legend__label">{dayIndex}일차</span>
          </li>
        ))}
      </ul>

      {hasDashed ? (
        <p className="map-legend__note">
          점선 구간의 이동시간은 <strong>추정치</strong>입니다. 네이버는 대중교통·도보 경로를
          제공하지 않아, 정확한 안내는 <strong>네이버지도로 길찾기</strong>를 눌러 확인하세요.
        </p>
      ) : null}
    </div>
  );
}
