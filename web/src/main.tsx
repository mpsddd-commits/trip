/**
 * 진입점.
 *
 * SEC-04 — 인라인 스크립트를 만들지 않는다. 모든 코드는 모듈로 로드된다.
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import "./styles.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("#root 요소를 찾을 수 없습니다.");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
