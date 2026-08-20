/**
 * Vite 설정.
 *
 * 근거:
 *   NFR-13 / ID-3  개발 서버는 5273 (기존 프로젝트 5173 과 충돌 회피)
 *   ID-3           `/api` 를 8200 으로 프록시한다. Compose 에 dev 서비스를 넣지 않는다
 *   WBR-42         라우트 단위 코드 분할 + 초기 번들 1MB(gzip) 목표
 *   UD-8           운영에서는 이 산출물(`dist/`)이 FastAPI 이미지에 복사된다
 */
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5273,
    strictPort: true,
    proxy: {
      // 개발 중에는 백엔드가 별도 포트에 있다. 운영에서는 같은 오리진이라 프록시가 사라진다.
      "/api": {
        target: "http://127.0.0.1:8200",
        changeOrigin: false,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    rollupOptions: {
      output: {
        // WBR-41 — 지도 SDK 래퍼와 벤더를 분리해 목록·생성 화면에서 내려받지 않게 한다.
        manualChunks: {
          vendor: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query", "@tanstack/react-query-persist-client"],
          dnd: ["@dnd-kit/core", "@dnd-kit/sortable", "@dnd-kit/utilities"],
        },
      },
    },
  },
});
