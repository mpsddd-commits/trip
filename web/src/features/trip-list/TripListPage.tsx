/**
 * 내 여행 목록 — WBR-05 ~ WBR-09.
 *
 * 목록은 `localStorage` 에만 있고(DD-21), 각 항목의 존재 여부는 서버에 물어 확인한다.
 * 서버에 없으면 **자동 삭제하지 않고** 사용자에게 확인받는다 (WBR-09).
 */
import { useCallback, useState } from "react";
import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import { ApiError } from "@/shared/api/errors";
import { queryKeys } from "@/shared/query/keys";
import {
  listSavedTrips,
  removeTripRef,
  type SavedTripRef,
} from "@/shared/storage/tripList";
import { Badge, Button, EmptyState, Skeleton } from "@/shared/ui";

import { ListExportImport } from "./ListExportImport";
import { LocalStorageNotice } from "./LocalStorageNotice";

export function TripListPage() {
  const [refs, setRefs] = useState<SavedTripRef[]>(() => listSavedTrips());
  const [error, setError] = useState<string | null>(null);

  const results = useQueries({
    queries: refs.map((ref) => ({
      queryKey: queryKeys.trip(ref.trip_id),
      queryFn: () => api.getTrip(ref.trip_id),
      retry: false,
    })),
  });

  const handleRemove = useCallback((tripId: string) => {
    setRefs(removeTripRef(tripId));
  }, []);

  return (
    <main className="page page--list">
      <header className="page__header">
        <h1>내 여행</h1>
        <Link to="/trips/new" className="btn btn--primary">
          새 여행 만들기
        </Link>
      </header>

      <LocalStorageNotice hasTrips={refs.length > 0} />
      {error ? <p className="form-error" role="alert">{error}</p> : null}

      {refs.length === 0 ? (
        <EmptyState
          title="아직 저장된 여행이 없습니다"
          description="목적지와 기간만 정하면 AI가 일정 초안을 만들어 드립니다."
          action={
            <Link to="/trips/new" className="btn btn--primary">
              첫 여행 만들기
            </Link>
          }
        />
      ) : (
        <ul className="trip-cards">
          {refs.map((ref, index) => {
            const result = results[index];
            const missing = result?.error instanceof ApiError && result.error.httpStatus === 404;
            return (
              <li key={ref.trip_id} className="trip-card">
                {result?.isPending ? (
                  <Skeleton lines={2} label={`${ref.title} 불러오는 중`} />
                ) : missing ? (
                  // WBR-09 — 자동 삭제하지 않는다.
                  <div className="trip-card__missing">
                    <p>
                      <strong>{ref.title}</strong>
                      <br />
                      서버에서 삭제된 여행입니다.
                    </p>
                    <Button variant="ghost" onClick={() => handleRemove(ref.trip_id)}>
                      목록에서 제거
                    </Button>
                  </div>
                ) : (
                  <Link to={`/trips/${ref.trip_id}`} className="trip-card__link">
                    <h2 className="trip-card__title">{ref.title}</h2>
                    <p className="trip-card__meta">
                      {ref.destination} · {ref.start_date} ~ {ref.end_date}
                    </p>
                    {ref.share_token ? <Badge tone="info">공유 링크 있음</Badge> : null}
                  </Link>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <footer className="page__footer">
        <ListExportImport trips={refs} onImported={setRefs} onError={setError} />
      </footer>
    </main>
  );
}
