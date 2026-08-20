/**
 * W5 MapView — 여행 데이터를 지도 props 로 변환한다.
 *
 * 이 컴포넌트는 **SDK 를 전혀 모른다.** 도메인 → 선언적 props 변환만 한다 (DD-18).
 *
 * 근거:
 *   FR-15  번호 마커 + 일자별 색상
 *   FR-16  경로 폴리라인 (자동차=실경로 실선 / 도보·대중교통=점선)
 *   FR-18  일자 필터
 *   FR-19 / WBR-18  선택 항목 강조 — 탭이 갈려도 상태는 유지된다
 *   WBR-24  번호 + 색상 + 라벨 3중
 */
import { useCallback, useMemo } from "react";

import type { Trip } from "@/shared/api/types";
import { useMapClientKey } from "@/shared/config/RuntimeConfigProvider";
import { itemsOf } from "@/shared/selectors/trip";
import { useUiStore } from "@/shared/store/uiStore";

import { MapLegend } from "./MapLegend";
import { NaverMapAdapter, type MapMarker, type MapPolyline } from "./NaverMapAdapter";

interface MapViewProps {
  trip: Pick<Trip, "days">;
  /** null 이면 전체 일자를 함께 표시한다 (FR-18) */
  dayFilter: number | null;
}

export function MapView({ trip, dayFilter }: MapViewProps) {
  const clientKey = useMapClientKey();
  const selectedItemId = useUiStore((s) => s.selectedItemId);
  const selectItem = useUiStore((s) => s.selectItem);

  const dayIndices = useMemo(
    () => (dayFilter === null ? trip.days.map((d) => d.day_index) : [dayFilter]),
    [dayFilter, trip.days],
  );

  const markers = useMemo<MapMarker[]>(() => {
    const result: MapMarker[] = [];
    for (const dayIndex of dayIndices) {
      itemsOf(trip, dayIndex).forEach((item, position) => {
        const label = position + 1;
        result.push({
          id: item.item_id,
          lat: item.place.coordinate.lat,
          lng: item.place.coordinate.lng,
          label,
          dayIndex,
          selected: item.item_id === selectedItemId,
          // WBR-38 — 색상이 아니라 텍스트로 정보를 전달한다
          ariaLabel: `${dayIndex}일차 ${label}번 ${item.place.name}`,
        });
      });
    }
    return result;
  }, [dayIndices, trip, selectedItemId]);

  const polylines = useMemo<MapPolyline[]>(() => {
    const result: MapPolyline[] = [];
    for (const dayIndex of dayIndices) {
      const items = itemsOf(trip, dayIndex);
      for (let index = 0; index < items.length - 1; index += 1) {
        const from = items[index];
        const to = items[index + 1];
        if (!from || !to) continue;
        // WBR-23 — 실경로가 없는 구간(도보·대중교통·폴백)은 점선으로 구분한다.
        //           서버가 준 경고를 근거로 판단하며, 여기서 추정하지 않는다 (WBR-04).
        const estimated = from.warnings.some((w) => w.type === "ESTIMATED_TRAVEL_TIME");
        result.push({
          path: [
            { lat: from.place.coordinate.lat, lng: from.place.coordinate.lng },
            { lat: to.place.coordinate.lat, lng: to.place.coordinate.lng },
          ],
          dayIndex,
          style: estimated ? "dashed" : "solid",
        });
      }
    }
    return result;
  }, [dayIndices, trip]);

  const handleMarkerClick = useCallback(
    (id: string) => {
      // FR-19 — 마커 선택이 타임라인 강조로 이어진다 (WBR-18)
      selectItem(id);
    },
    [selectItem],
  );

  return (
    <div className="map-view">
      <NaverMapAdapter
        clientKey={clientKey}
        markers={markers}
        polylines={polylines}
        onMarkerClick={handleMarkerClick}
      />
      <MapLegend dayIndices={dayIndices} hasDashed={polylines.some((p) => p.style === "dashed")} />
    </div>
  );
}
