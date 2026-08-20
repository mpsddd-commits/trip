/**
 * 라우팅 — Q5=A (라우트 4종).
 *
 * WBR-41·42 — 라우트 단위 코드 분할. **지도 SDK 가 포함된 작업 화면은 목록·생성 화면에서
 *              내려받지 않는다.**
 */
import { Suspense, lazy } from "react";
import { Route, Routes } from "react-router-dom";

import { Skeleton } from "@/shared/ui";

const TripListPage = lazy(() =>
  import("@/features/trip-list/TripListPage").then((m) => ({ default: m.TripListPage })),
);
const TripCreateWizard = lazy(() =>
  import("@/features/trip-create/TripCreateWizard").then((m) => ({ default: m.TripCreateWizard })),
);
const TripWorkspace = lazy(() =>
  import("@/features/trip-workspace/TripWorkspace").then((m) => ({ default: m.TripWorkspace })),
);
const SharedTripView = lazy(() =>
  import("@/features/share/SharedTripView").then((m) => ({ default: m.SharedTripView })),
);

function NotFound() {
  return (
    <main className="page">
      <h1>페이지를 찾을 수 없습니다</h1>
    </main>
  );
}

export function AppRoutes() {
  return (
    <Suspense fallback={<Skeleton lines={6} label="화면 불러오는 중" />}>
      <Routes>
        <Route path="/" element={<TripListPage />} />
        <Route path="/trips/new" element={<TripCreateWizard />} />
        <Route path="/trips/:tripId" element={<TripWorkspace />} />
        <Route path="/shared/:token" element={<SharedTripView />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}
