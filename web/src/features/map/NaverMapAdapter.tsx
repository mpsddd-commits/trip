/**
 * W4 NaverMapAdapter — 지도 SDK 를 가두는 어댑터.
 *
 * 🔴 DD-18 / Q14=A — SDK 의 **명령형 API(인스턴스 생성·마커 add/remove·수명 관리)는
 *    전부 이 컴포넌트 안에만** 존재한다. 바깥은 아래 props 만 다룬다.
 *    이 경계가 없으면 명령형 SDK 와 React 렌더링이 곳곳에서 충돌한다.
 *
 * 근거:
 *   FR-14·15·16·17·18  지도·마커·폴리라인·상세·일자 필터
 *   WBR-23  자동차=실선 / 도보·대중교통=점선
 *   WBR-24  번호 + 색상 + 라벨 3중 표기 (NFR-6 — 색상 단독 금지)
 *   WBR-40  로딩 실패 사유 구분
 */
import { useEffect, useRef, useState } from "react";

import { FAILURE_MESSAGES, MapSdkError, loadNaverMapSdk, type SdkLoadFailure } from "./loadSdk";

export interface MapMarker {
  id: string;
  lat: number;
  lng: number;
  /** 방문 순번 ①②③ (WBR-24) */
  label: number;
  dayIndex: number;
  selected: boolean;
  /** 스크린리더용 (WBR-38) */
  ariaLabel: string;
}

export interface MapPolyline {
  path: { lat: number; lng: number }[];
  dayIndex: number;
  /** WBR-23 — 실경로는 실선, 근사는 점선 */
  style: "solid" | "dashed";
}

export interface NaverMapAdapterProps {
  clientKey: string | null;
  markers: MapMarker[];
  polylines: MapPolyline[];
  onMarkerClick: (id: string) => void;
  onLoadError?: (reason: SdkLoadFailure, message: string) => void;
}

/** 일자별 색상. 텍스트 라벨과 항상 함께 쓴다 (WBR-24). */
export const DAY_COLORS = [
  "#2563eb",
  "#dc2626",
  "#16a34a",
  "#d97706",
  "#7c3aed",
  "#0891b2",
  "#db2777",
  "#65a30d",
  "#c2410c",
  "#4f46e5",
] as const;

export function dayColor(dayIndex: number): string {
  return DAY_COLORS[(dayIndex - 1) % DAY_COLORS.length] ?? DAY_COLORS[0];
}

/** SDK 타입을 프로젝트에 끌어들이지 않기 위한 최소 형상. */
interface MapsApi {
  Map: new (element: HTMLElement, options: Record<string, unknown>) => MapInstance;
  LatLng: new (lat: number, lng: number) => unknown;
  LatLngBounds: new () => { extend(point: unknown): void };
  Marker: new (options: Record<string, unknown>) => Removable;
  Polyline: new (options: Record<string, unknown>) => Removable;
  Event: { addListener(target: unknown, event: string, handler: () => void): unknown };
}

interface MapInstance {
  fitBounds(bounds: unknown): void;
  setCenter(point: unknown): void;
  setZoom(level: number): void;
}

interface Removable {
  setMap(map: MapInstance | null): void;
}

function markerIcon(marker: MapMarker): Record<string, unknown> {
  const color = dayColor(marker.dayIndex);
  const size = marker.selected ? 34 : 28;
  // WBR-24 — 번호를 마커 안에 그린다. 색상은 보조 수단이다.
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 32 32">
    <circle cx="16" cy="16" r="14" fill="${color}" stroke="#fff" stroke-width="${marker.selected ? 4 : 2}"/>
    <text x="16" y="21" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">${marker.label}</text>
  </svg>`;
  return {
    content: svg,
    anchor: { x: size / 2, y: size / 2 },
  };
}

export function NaverMapAdapter({
  clientKey,
  markers,
  polylines,
  onMarkerClick,
  onLoadError,
}: NaverMapAdapterProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapInstance | null>(null);
  const overlaysRef = useRef<Removable[]>([]);
  const [failure, setFailure] = useState<{ reason: SdkLoadFailure; message: string } | null>(null);
  const [ready, setReady] = useState(false);

  // --- SDK 로딩 (WBR-41 — 이 컴포넌트가 마운트될 때만) ---
  useEffect(() => {
    let cancelled = false;
    loadNaverMapSdk(clientKey)
      .then(() => {
        if (!cancelled) setReady(true);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        const mapError =
          error instanceof MapSdkError
            ? error
            : new MapSdkError("unknown", FAILURE_MESSAGES.unknown);
        setFailure({ reason: mapError.reason, message: mapError.message });
        onLoadError?.(mapError.reason, mapError.message);
      });
    return () => {
      cancelled = true;
    };
  }, [clientKey, onLoadError]);

  // --- 지도 인스턴스 생성 ---
  useEffect(() => {
    if (!ready || !containerRef.current || mapRef.current) return;
    const maps = window.naver?.maps as MapsApi | undefined;
    if (!maps) return;
    mapRef.current = new maps.Map(containerRef.current, {
      zoom: 12,
      center: new maps.LatLng(37.5665, 126.978),
      // 지도 자체 UI 를 최소화한다 — 우리 UI 와 겹치지 않게.
      mapDataControl: false,
      scaleControl: false,
      logoControlOptions: { position: 3 },
    });
  }, [ready]);

  // --- 오버레이 갱신 (명령형 API 는 여기까지만) ---
  useEffect(() => {
    const maps = window.naver?.maps as MapsApi | undefined;
    const map = mapRef.current;
    if (!ready || !maps || !map) return;

    for (const overlay of overlaysRef.current) overlay.setMap(null);
    overlaysRef.current = [];

    for (const line of polylines) {
      if (line.path.length < 2) continue;
      const polyline = new maps.Polyline({
        map,
        path: line.path.map((p) => new maps.LatLng(p.lat, p.lng)),
        strokeColor: dayColor(line.dayIndex),
        strokeWeight: 4,
        strokeOpacity: 0.85,
        // WBR-23 — 근사 구간은 점선으로 구분한다
        strokeStyle: line.style === "dashed" ? "shortdash" : "solid",
      });
      overlaysRef.current.push(polyline);
    }

    for (const marker of markers) {
      const instance = new maps.Marker({
        map,
        position: new maps.LatLng(marker.lat, marker.lng),
        icon: markerIcon(marker),
        title: marker.ariaLabel, // WBR-38
        zIndex: marker.selected ? 100 : 10,
      });
      maps.Event.addListener(instance, "click", () => onMarkerClick(marker.id));
      overlaysRef.current.push(instance);
    }

    if (markers.length > 0) {
      const bounds = new maps.LatLngBounds();
      for (const marker of markers) bounds.extend(new maps.LatLng(marker.lat, marker.lng));
      map.fitBounds(bounds);
    }
  }, [ready, markers, polylines, onMarkerClick]);

  // --- 언마운트 정리 ---
  useEffect(
    () => () => {
      for (const overlay of overlaysRef.current) overlay.setMap(null);
      overlaysRef.current = [];
      mapRef.current = null;
    },
    [],
  );

  if (failure) {
    // WBR-31 — 지도 영역만 대체된다. 타임라인 편집은 영향받지 않는다.
    return (
      <div className="map-fallback" role="status">
        <p className="map-fallback__title">지도를 불러올 수 없습니다</p>
        <p className="map-fallback__reason">{failure.message}</p>
      </div>
    );
  }

  return <div ref={containerRef} className="map-canvas" aria-label="여행 경로 지도" role="application" />;
}
