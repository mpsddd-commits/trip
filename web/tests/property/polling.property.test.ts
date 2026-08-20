/**
 * 폴링 간격 속성 테스트 — WP-10, WP-11 (PBT-03).
 *
 * 근거: WBR-11 (0~10초 1초 / 이후 2초 / 90초 초과 중단)
 */
import fc from "fast-check";
import { describe, expect, it } from "vitest";

import {
  FAST_INTERVAL_MS,
  FAST_PHASE_MS,
  POLL_TIMEOUT_MS,
  SLOW_INTERVAL_MS,
  isTerminal,
  nextPoll,
  stepLabel,
} from "@/shared/selectors/polling";
import { arbElapsedMs } from "./generators";

describe("WP-10 간격 규칙", () => {
  it("폴링할 때 간격은 항상 1000ms 이상이다", () => {
    fc.assert(
      fc.property(arbElapsedMs(), (elapsed) => {
        const decision = nextPoll(elapsed);
        if (decision.action === "poll") {
          expect(decision.intervalMs).toBeGreaterThanOrEqual(1_000);
        }
      }),
    );
  });

  it("경과가 늘어도 간격이 줄지 않는다 (단조 비감소)", () => {
    fc.assert(
      fc.property(arbElapsedMs(), arbElapsedMs(), (a, b) => {
        const [small, large] = a <= b ? [a, b] : [b, a];
        const first = nextPoll(small);
        const second = nextPoll(large);
        if (first.action === "poll" && second.action === "poll") {
          expect(second.intervalMs).toBeGreaterThanOrEqual(first.intervalMs);
        }
      }),
    );
  });

  it("빠른 구간과 느린 구간의 경계가 정확하다", () => {
    expect(nextPoll(0)).toEqual({ action: "poll", intervalMs: FAST_INTERVAL_MS });
    expect(nextPoll(FAST_PHASE_MS - 1)).toEqual({ action: "poll", intervalMs: FAST_INTERVAL_MS });
    expect(nextPoll(FAST_PHASE_MS)).toEqual({ action: "poll", intervalMs: SLOW_INTERVAL_MS });
  });

  it("음수 경과도 안전하게 처리한다 (시계 오차 방어)", () => {
    fc.assert(
      fc.property(fc.integer({ min: -100_000, max: -1 }), (negative) => {
        expect(nextPoll(negative)).toEqual({ action: "poll", intervalMs: FAST_INTERVAL_MS });
      }),
    );
  });
});

describe("WP-11 상한 도달 시 중단", () => {
  it("90초를 넘으면 항상 stop 이다", () => {
    fc.assert(
      fc.property(fc.integer({ min: POLL_TIMEOUT_MS + 1, max: 10_000_000 }), (elapsed) => {
        expect(nextPoll(elapsed)).toEqual({ action: "stop", reason: "timeout" });
      }),
    );
  });

  it("90초 이하에서는 계속 폴링한다", () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: POLL_TIMEOUT_MS }), (elapsed) => {
        expect(nextPoll(elapsed).action).toBe("poll");
      }),
    );
  });

  it("상한은 NFR-1(60초)보다 여유가 있다", () => {
    expect(POLL_TIMEOUT_MS).toBeGreaterThan(60_000);
  });
});

describe("종료 상태 판정", () => {
  it("succeeded / partial / failed 만 종료다", () => {
    expect(isTerminal("succeeded")).toBe(true);
    expect(isTerminal("partial")).toBe(true);
    expect(isTerminal("failed")).toBe(true);
    expect(isTerminal("queued")).toBe(false);
    expect(isTerminal("running")).toBe(false);
  });

  it("partial 은 종료지만 실패가 아니다 (DD-23)", () => {
    expect(isTerminal("partial")).toBe(true);
    expect(isTerminal("partial")).not.toBe(isTerminal("unknown-state"));
  });
});

describe("단계 라벨 (WBR-13)", () => {
  it("6단계가 모두 사용자 언어로 번역된다", () => {
    for (const step of ["DRAFTING", "RESOLVING", "ROUTING", "OPTIMIZING", "SCHEDULING", "SAVING"]) {
      expect(stepLabel(step)).not.toBe(step);
      expect(stepLabel(step).length).toBeGreaterThan(0);
    }
  });

  it("알 수 없는 단계도 빈 문자열을 내지 않는다", () => {
    fc.assert(
      fc.property(fc.option(fc.string(), { nil: null }), (step) => {
        expect(stepLabel(step).length).toBeGreaterThan(0);
      }),
    );
  });

  it("Object.prototype 속성 이름을 넣어도 안전하다 (PBT 가 잡은 회귀)", () => {
    // 객체 리터럴 조회 표였을 때 `STEP_LABELS["toString"]` 이 함수를 반환해
    // `?? 기본값` 이 발동하지 않던 결함. 반례 "toString" 으로 발견됨.
    for (const key of ["toString", "constructor", "valueOf", "hasOwnProperty", "__proto__"]) {
      expect(typeof stepLabel(key)).toBe("string");
      expect(stepLabel(key)).toBe("진행하고 있어요");
    }
  });
});
