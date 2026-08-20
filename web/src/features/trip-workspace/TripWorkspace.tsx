/**
 * 메인 작업 화면 — 타임라인 + 지도 (FR-14 ~ FR-19).
 *
 * 🔴 WBR-18 (WD-1) — 모바일에서 두 패널이 탭으로 갈리므로 FR-19(양방향 하이라이트)를
 *    "동시 표시"가 아니라 **"상태 연속성"** 으로 만족시킨다:
 *    `selectedItemId` 를 탭과 무관하게 유지하고, 전환 후 해당 항목으로 스크롤·뷰포트를 맞춘다.
 *
 * WBR-39  ≥1024 2단 / 그 미만 탭 전환
 * WBR-35  오프라인이면 편집 비활성
 */
import { useCallback, useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import type { ItemCreate, TravelMode } from "@/shared/api/types";
import { useOfflineGate } from "@/shared/offline/OfflineGate";
import { queryKeys } from "@/shared/query/keys";
import { findItem, itemsOf } from "@/shared/selectors/trip";
import { useUiStore } from "@/shared/store/uiStore";
import { EmptyState, Skeleton, ToastHost, type ToastItem } from "@/shared/ui";

import { GenerationProgress } from "@/features/generation/GenerationProgress";
import { UnresolvedPanel } from "@/features/generation/UnresolvedPanel";
import { MapView } from "@/features/map/MapView";
import { PlaceDetailPanel } from "@/features/place/PlaceDetailPanel";
import { PlaceSearchPanel } from "@/features/place/PlaceSearchPanel";
import { RecommendationPanel } from "@/features/place/RecommendationPanel";
import { DayTabs } from "@/features/timeline/DayTabs";
import { TimelineView } from "@/features/timeline/TimelineView";

import { TripHeader } from "./TripHeader";
import { useTripMutations } from "./useTripMutations";

export function TripWorkspace() {
  const { tripId = "" } = useParams<{ tripId: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const jobId = searchParams.get("job");

  const { canEdit } = useOfflineGate();
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);

  const selectedDayIndex = useUiStore((s) => s.selectedDayIndex);
  const selectDay = useUiStore((s) => s.selectDay);
  const selectedItemId = useUiStore((s) => s.selectedItemId);
  const detailItemId = useUiStore((s) => s.detailItemId);
  const closeDetail = useUiStore((s) => s.closeDetail);
  const mobilePane = useUiStore((s) => s.mobilePane);
  const setMobilePane = useUiStore((s) => s.setMobilePane);
  const openSearchWith = useUiStore((s) => s.openSearchWith);
  const closeSearch = useUiStore((s) => s.closeSearch);

  const notifyError = useCallback((message: string, correlationId: string | null) => {
    setToasts((prev) => [
      ...prev,
      { id: `${Date.now()}-${prev.length}`, tone: "danger", message, correlationId },
    ]);
  }, []);

  const mutations = useTripMutations(tripId, { notifyError });

  const { data: trip, isPending, isError } = useQuery({
    queryKey: queryKeys.trip(tripId),
    queryFn: ({ signal }) => api.getTrip(tripId, signal),
    enabled: tripId !== "",
  });

  // WBR-18 — 탭을 바꿔도 선택은 유지된다. 전환 후 해당 항목으로 스크롤한다.
  useEffect(() => {
    if (!selectedItemId || mobilePane !== "timeline") return;
    const element = document.querySelector(`[data-item-id="${selectedItemId}"]`);
    element?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [selectedItemId, mobilePane]);

  const handleAdd = useCallback(
    (item: ItemCreate) => {
      mutations.addItem.mutate({ dayIndex: selectedDayIndex, item });
      setSearchOpen(false);
      closeSearch();
    },
    [mutations.addItem, selectedDayIndex, closeSearch],
  );

  const handleSearchAndAdd = useCallback(
    (name: string) => {
      openSearchWith(name);
      setSearchOpen(true);
    },
    [openSearchWith],
  );

  if (isPending) return <Skeleton lines={8} label="여행 불러오는 중" />;

  if (isError || !trip) {
    return (
      <main className="page">
        <EmptyState
          title="여행을 불러오지 못했습니다"
          description="주소를 확인하거나 목록에서 다시 열어 보세요."
        />
      </main>
    );
  }

  const dayItems = itemsOf(trip, selectedDayIndex);
  const detailItem = detailItemId ? findItem(trip, detailItemId) : undefined;

  return (
    <main className="page page--workspace">
      <TripHeader
        trip={trip}
        canEdit={canEdit}
        onIssueShare={() => mutations.issueShare.mutate()}
        onRevokeShare={() => mutations.revokeShare.mutate()}
        onNotify={(message) =>
          setToasts((prev) => [
            ...prev,
            { id: `${Date.now()}-${prev.length}`, tone: "info", message },
          ])
        }
      />

      {/* WBR-29 — 미해결 장소를 접이식으로 상시 노출 */}
      <UnresolvedPanel unresolved={trip.unresolved} onSearchAndAdd={handleSearchAndAdd} />

      <DayTabs trip={trip} selectedDayIndex={selectedDayIndex} onSelect={selectDay} />

      {/* WBR-39 — 모바일은 탭 전환, 데스크톱은 2단 (CSS 가 결정) */}
      <div className="pane-switch" role="tablist" aria-label="타임라인과 지도 전환">
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === "timeline"}
          className={`pane-switch__tab ${mobilePane === "timeline" ? "pane-switch__tab--on" : ""}`}
          onClick={() => setMobilePane("timeline")}
        >
          시간표
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === "map"}
          className={`pane-switch__tab ${mobilePane === "map" ? "pane-switch__tab--on" : ""}`}
          onClick={() => setMobilePane("map")}
        >
          지도
          {/* WBR-18 — 전환 버튼에 선택 항목을 표시해 맥락을 잃지 않게 한다 */}
          {selectedItemId ? <span className="pane-switch__hint"> · 선택됨</span> : null}
        </button>
      </div>

      <div className={`workspace workspace--${mobilePane}`}>
        <section className="workspace__timeline" aria-label="시간표">
          <TimelineView
            trip={trip}
            dayIndex={selectedDayIndex}
            canEdit={canEdit}
            busy={mutations.busy}
            onReorder={(itemIds) =>
              mutations.reorder.mutate({ dayIndex: selectedDayIndex, itemIds })
            }
            onRemoveItem={(itemId) => mutations.removeItem.mutate(itemId)}
            onChangeMode={(itemId, mode: TravelMode) =>
              mutations.patchItem.mutate({ itemId, patch: { travel_mode: mode } })
            }
            onOptimize={() => mutations.optimize.mutate(selectedDayIndex)}
            onAddPlace={() => setSearchOpen(true)}
          />

          {dayItems.length > 0 ? (
            <RecommendationPanel
              tripId={tripId}
              dayIndex={selectedDayIndex}
              canEdit={canEdit}
              onAdd={handleAdd}
            />
          ) : null}
        </section>

        <section className="workspace__map" aria-label="지도">
          <MapView trip={trip} dayFilter={selectedDayIndex} />
        </section>
      </div>

      <PlaceSearchPanel
        open={searchOpen}
        dayIndex={selectedDayIndex}
        canEdit={canEdit}
        onClose={() => {
          setSearchOpen(false);
          closeSearch();
        }}
        onAdd={handleAdd}
      />

      <PlaceDetailPanel
        open={detailItem !== undefined}
        tripId={tripId}
        item={detailItem}
        canEdit={canEdit}
        onClose={closeDetail}
        onSaveOpeningHours={(itemId, hours) =>
          mutations.setOpeningHours.mutate({ itemId, hours })
        }
      />

      {jobId ? (
        <GenerationProgress
          tripId={tripId}
          jobId={jobId}
          onFinished={(status) => {
            // WBR-25 — partial 은 구체적으로 알린다
            if (status.state === "partial") {
              const parts: string[] = [];
              if (status.unresolved_count > 0) {
                parts.push(`${status.unresolved_count}곳을 찾지 못했습니다`);
              }
              parts.push("일부 이동시간은 추정치입니다");
              setToasts((prev) => [
                ...prev,
                {
                  id: `job-${status.job_id}`,
                  tone: "warn",
                  message: `일정을 만들었습니다. 다만 ${parts.join(", ")}.`,
                },
              ]);
            }
          }}
          onClose={() => {
            searchParams.delete("job");
            setSearchParams(searchParams, { replace: true });
          }}
        />
      ) : null}

      <ToastHost
        toasts={toasts}
        onDismiss={(id) => setToasts((prev) => prev.filter((t) => t.id !== id))}
      />
    </main>
  );
}
