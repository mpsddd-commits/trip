/**
 * 애플리케이션 조립.
 *
 * Provider 중첩 순서가 의미를 갖는다:
 *   PersistQueryClientProvider  — 서버 상태 (['trip', *] 만 persist)
 *   └ RuntimeConfigProvider     — /api/config (WBR-32). Query 가 필요하므로 안쪽
 *     └ OfflineGate             — 편집 차단. Query 무효화를 하므로 안쪽
 *       └ DemoModeBanner + 라우트
 */
import { BrowserRouter } from "react-router-dom";
import { PersistQueryClientProvider } from "@tanstack/react-query-persist-client";

import { createQueryClient, persistOptions } from "@/shared/query/queryClient";
import { RuntimeConfigProvider } from "@/shared/config/RuntimeConfigProvider";
import { OfflineGate } from "@/shared/offline/OfflineGate";

import { DemoModeBanner } from "@/features/shell/DemoModeBanner";
import { AppRoutes } from "./router";

const queryClient = createQueryClient();

export function App() {
  return (
    <PersistQueryClientProvider client={queryClient} persistOptions={persistOptions}>
      <RuntimeConfigProvider>
        <BrowserRouter>
          <OfflineGate>
            <DemoModeBanner />
            <AppRoutes />
          </OfflineGate>
        </BrowserRouter>
      </RuntimeConfigProvider>
    </PersistQueryClientProvider>
  );
}
