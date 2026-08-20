/**
 * W11 RecommendationPanel — 주변 미포함 장소 추천 (FR-22).
 *
 * 서버가 이미 담긴 장소를 제외해 준다. 클라이언트는 표시와 담기만 한다.
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import type { ItemCreate } from "@/shared/api/types";
import { queryKeys } from "@/shared/query/keys";
import { Button, EmptyState, Skeleton } from "@/shared/ui";

const KEYWORDS = ["맛집", "카페", "명소", "쇼핑"] as const;

interface Props {
  tripId: string;
  dayIndex: number;
  canEdit: boolean;
  onAdd: (item: ItemCreate) => void;
}

export function RecommendationPanel({ tripId, dayIndex, canEdit, onAdd }: Props) {
  const [keyword, setKeyword] = useState<string>(KEYWORDS[0]);

  const { data, isFetching } = useQuery({
    queryKey: queryKeys.suggestions(tripId, dayIndex, keyword),
    queryFn: () => api.getSuggestions(tripId, dayIndex, keyword, 1500),
    enabled: canEdit,
  });

  return (
    <section className="recommendation" aria-label="주변 추천">
      <header className="recommendation__header">
        <h3>이 근처에 더 가볼 만한 곳</h3>
        <div className="chip-group">
          {KEYWORDS.map((word) => (
            <button
              key={word}
              type="button"
              className={`chip ${keyword === word ? "chip--on" : ""}`}
              aria-pressed={keyword === word}
              onClick={() => setKeyword(word)}
            >
              {word}
            </button>
          ))}
        </div>
      </header>

      {isFetching ? <Skeleton lines={2} label="추천 불러오는 중" /> : null}

      {!isFetching && (data?.items.length ?? 0) === 0 ? (
        <EmptyState title="추천할 만한 곳을 찾지 못했습니다" />
      ) : null}

      <ul className="recommendation__list">
        {(data?.items ?? []).map((place) => (
          <li key={place.place_id} className="recommendation__item">
            <div>
              <p className="recommendation__name">{place.name}</p>
              {place.road_address ? (
                <p className="recommendation__address">{place.road_address}</p>
              ) : null}
            </div>
            <Button
              variant="secondary"
              disabled={!canEdit}
              onClick={() =>
                onAdd({
                  name: place.name,
                  latitude: place.coordinate.lat,
                  longitude: place.coordinate.lng,
                  category_raw: place.category_raw ?? null,
                  road_address: place.road_address ?? null,
                  address: place.address ?? null,
                  phone: place.phone ?? null,
                  stay_minutes: null,
                  memo: null,
                })
              }
            >
              담기
            </Button>
          </li>
        ))}
      </ul>
    </section>
  );
}
