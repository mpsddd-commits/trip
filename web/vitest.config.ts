/**
 * Vitest 설정.
 *
 * NFR-10 — 테스트는 네트워크에 의존하지 않는다.
 * PBT-08 / PBT-R4 — fast-check 는 기본 셰링킹을 유지하고 실패 시 시드를 출력한다
 *                   (설정은 tests/setup.ts 에서 등록).
 */
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.{test,property.test}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/shared/api/generated.ts"],
    },
  },
});
