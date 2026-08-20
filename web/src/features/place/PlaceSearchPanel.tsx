/**
 * W10 PlaceSearchPanel — 장소 검색 (FR-6).
 *
 * 근거:
 *   CON-2   지역검색은 1회 5건이 상한 → `page` 로 "더 보기"
 *   WBR-29  "확인 필요" 항목에서 넘어오면 이름을 **미리 채운 채** 열린다
 *   WBR-35  오프라인이면 검색을 시도하지 않는다
 */
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import type { ItemCreate, Place } from "@/shared/api/types";
import { queryKeys } from "@/shared/query/keys";
import { useUiStore } from "@/shared/store/uiStore";
import { Button, EmptyState, Sheet, Skeleton } from "@/shared/ui";

interface Props {
  open: boolean;
  dayIndex: number;
  canEdit: boolean;
  onClose: () => void;
  onAdd: (item: ItemCreate) => void;
}

function toItemCreate(place: Place): ItemCreate {
  return {
    name: place.name,
    latitude: place.coordinate.lat,
    longitude: place.coordinate.lng,
    category_raw: place.category_raw ?? null,
    road_address: place.road_address ?? null,
    address: place.address ?? null,
    phone: place.phone ?? null,
    stay_minutes: null,
    memo: null,
  };
}

export function PlaceSearchPanel({ open, dayIndex, canEdit, onClose, onAdd }: Props) {
  const prefill = useUiStore((s) => s.searchPrefill);
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [page, setPage] = useState(1);
  const [collected, setCollected] = useState<Place[]>([]);

  // WBR-29 — 미해결 항목에서 넘어온 이름을 채워 준다
  useEffect(() => {
    if (prefill) {
      setQuery(prefill);
      setSubmitted(prefill);
      setPage(1);
      setCollected([]);
    }
  }, [prefill]);

  const { data, isFetching } = useQuery({
    queryKey: queryKeys.placeSearch(submitted, page),
    queryFn: ({ signal }) => api.searchPlaces(submitted, page, signal),
    enabled: open && submitted.trim() !== "",
  });

  useEffect(() => {
    if (!data) return;
    setCollected((prev) => (page === 1 ? data.items : [...prev, ...data.items]));
  }, [data, page]);

  const handleSearch = () => {
    setSubmitted(query.trim());
    setPage(1);
    setCollected([]);
  };

  return (
    <Sheet open={open} title="장소 검색" onClose={onClose}>
      <div className="search-bar">
        <label className="field">
          <span className="visually-hidden">검색어</span>
          <input
            className="field__input"
            value={query}
            placeholder="예: 광안리 해수욕장"
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleSearch();
            }}
          />
        </label>
        <Button variant="primary" onClick={handleSearch} disabled={!canEdit}>
          검색
        </Button>
      </div>

      {isFetching && collected.length === 0 ? <Skeleton lines={4} label="검색 중" /> : null}

      {submitted !== "" && !isFetching && collected.length === 0 ? (
        <EmptyState title="검색 결과가 없습니다" description="다른 이름으로 찾아보세요." />
      ) : null}

      <ul className="search-results">
        {collected.map((place) => (
          <li key={place.place_id} className="search-result">
            <div>
              <p className="search-result__name">{place.name}</p>
              {place.road_address ? (
                <p className="search-result__address">{place.road_address}</p>
              ) : null}
              {place.category_raw ? (
                <p className="search-result__category">{place.category_raw}</p>
              ) : null}
            </div>
            <Button
              variant="secondary"
              disabled={!canEdit}
              onClick={() => onAdd(toItemCreate(place))}
              aria-label={`${place.name} ${dayIndex}일차에 담기`}
            >
              담기
            </Button>
          </li>
        ))}
      </ul>

      {/* CON-2 — 1회 5건이 상한이라 이어 받는다 */}
      {data?.has_more ? (
        <Button variant="ghost" onClick={() => setPage((p) => p + 1)} disabled={isFetching}>
          {isFetching ? "불러오는 중…" : "더 보기"}
        </Button>
      ) : null}
    </Sheet>
  );
}
