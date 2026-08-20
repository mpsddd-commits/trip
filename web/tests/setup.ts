/**
 * 테스트 공통 설정.
 *
 * PBT-08 / PBT-R4:
 *   - 셰링킹은 fast-check 기본값(활성)을 유지한다. 비활성화하지 않는다.
 *   - `verbose` 로 실패 시 반례를 출력하고, 시드를 로그에 남긴다.
 *   - CI 에서는 실행 횟수를 늘린다: VITEST_PROFILE=ci
 *
 * NFR-10: 네트워크 의존을 원천 차단한다.
 */
import "@testing-library/jest-dom/vitest";
import fc from "fast-check";
import { afterEach, beforeAll, vi } from "vitest";
import { cleanup } from "@testing-library/react";

const isCi = process.env.VITEST_PROFILE === "ci";

fc.configureGlobal({
  numRuns: isCi ? 500 : 200,
  verbose: fc.VerbosityLevel.Verbose,
  // 시드를 고정하지 않는다 — 새로운 반례를 찾기 위함. 실패 시 시드가 출력된다.
});

beforeAll(() => {
  // 테스트에서 실제 네트워크로 나가면 즉시 실패시킨다 (NFR-10).
  vi.stubGlobal(
    "fetch",
    vi.fn(() => {
      throw new Error(
        "테스트에서 실제 fetch 를 호출했습니다. 목 클라이언트나 MSW 를 사용하세요 (NFR-10).",
      );
    }),
  );
});

afterEach(() => {
  cleanup();
  localStorage.clear();
});
