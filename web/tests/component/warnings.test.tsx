/**
 * 컴포넌트 테스트 — 사용자에게 **정직하게 알리는** 규칙들 (PBT-10).
 *
 * WBR-22  추정 이동시간에 "추정" 배지
 * WBR-25  partial 을 구체적으로 알린다
 * WBR-26  실패 사유 6종을 사용자 언어로
 * WBR-29  "확인 필요" 는 접어도 개수가 남는다
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { UnresolvedPanel } from "@/features/generation/UnresolvedPanel";
import { LegRow } from "@/features/timeline/LegRow";
import type { ItineraryItem, UnresolvedCandidate } from "@/shared/api/types";

// ---------------------------------------------------------------------------
function makeItem(overrides: Partial<ItineraryItem> = {}): ItineraryItem {
  return {
    item_id: "item-1",
    place: {
      place_id: "p1",
      name: "광안리 해수욕장",
      coordinate: { lat: 35.153, lng: 129.118 },
      category: "ATTRACTION",
      road_address: null,
      address: null,
      category_raw: null,
      phone: null,
      naver_link: null,
      source: "MOCK",
      resolved_from: null,
      match_score: null,
      opening_hours: null,
    },
    stay_minutes: 60,
    position: 0,
    arrival_at: "2026-09-01T01:00:00+00:00",
    departure_at: "2026-09-01T02:00:00+00:00",
    time_fixed: false,
    fixed_time: null,
    travel_mode: null,
    memo: null,
    warnings: [],
    ...overrides,
  } as ItineraryItem;
}

describe("WBR-22 — 추정 이동시간을 확정값처럼 보이게 하지 않는다", () => {
  const to = makeItem({
    item_id: "item-2",
    arrival_at: "2026-09-01T02:30:00+00:00",
    departure_at: "2026-09-01T03:00:00+00:00",
  });

  it("서버가 추정 경고를 주면 '추정' 배지가 뜬다", () => {
    const from = makeItem({
      warnings: [{ type: "ESTIMATED_TRAVEL_TIME", detail: "추정치입니다" }],
    });
    render(
      <ul>
        <LegRow from={from} to={to} defaultMode="TRANSIT" canEdit onChangeMode={vi.fn()} />
      </ul>,
    );
    expect(screen.getByText("추정")).toBeInTheDocument();
  });

  it("경고가 없으면 배지를 만들어내지 않는다 (WBR-04)", () => {
    render(
      <ul>
        <LegRow from={makeItem()} to={to} defaultMode="CAR" canEdit onChangeMode={vi.fn()} />
      </ul>,
    );
    expect(screen.queryByText("추정")).not.toBeInTheDocument();
  });

  it("길찾기 버튼으로 네이버지도에 위임한다 (FR-12)", () => {
    render(
      <ul>
        <LegRow from={makeItem()} to={to} defaultMode="TRANSIT" canEdit onChangeMode={vi.fn()} />
      </ul>,
    );
    expect(screen.getByRole("button", { name: "네이버지도로 길찾기" })).toBeInTheDocument();
  });

  it("오프라인이면 이동수단을 바꿀 수 없다 (WBR-35)", () => {
    render(
      <ul>
        <LegRow from={makeItem()} to={to} defaultMode="WALK" canEdit={false} onChangeMode={vi.fn()} />
      </ul>,
    );
    expect(screen.getByRole("combobox")).toBeDisabled();
  });
});

// ---------------------------------------------------------------------------
describe("BR-18 의 UI 측 대응 — 미해결 장소를 숨기지 않는다", () => {
  const unresolved: UnresolvedCandidate[] = [
    {
      raw_name: "없는맛집",
      day_index: 1,
      category_hint: "음식점",
      reason: "현지 인기",
      failure_code: "LOW_SIMILARITY",
      best_candidate_name: "있는맛집",
      best_match_score: 0.42,
    },
    {
      raw_name: "먼곳",
      day_index: 2,
      category_hint: null,
      reason: "",
      failure_code: "OUT_OF_REGION",
      best_candidate_name: null,
      best_match_score: null,
    },
  ];

  it("개수와 사유를 사용자 언어로 보여준다 (WBR-25·26)", () => {
    render(<UnresolvedPanel unresolved={unresolved} onSearchAndAdd={vi.fn()} />);
    expect(screen.getByText("2곳")).toBeInTheDocument();
    expect(screen.getByText("이름이 비슷한 곳을 찾지 못했습니다")).toBeInTheDocument();
    expect(screen.getByText("목적지 밖에 있는 것 같습니다")).toBeInTheDocument();
  });

  it("가장 근접했던 후보와 유사도를 알려준다 (BR-12)", () => {
    render(<UnresolvedPanel unresolved={unresolved} onSearchAndAdd={vi.fn()} />);
    expect(screen.getByText(/있는맛집/)).toBeInTheDocument();
    expect(screen.getByText(/42%/)).toBeInTheDocument();
  });

  it("접어도 개수 배지는 남는다 (WBR-29)", async () => {
    const user = userEvent.setup();
    render(<UnresolvedPanel unresolved={unresolved} onSearchAndAdd={vi.fn()} />);

    await user.click(screen.getByRole("button", { expanded: true }));

    expect(screen.queryByText("이름이 비슷한 곳을 찾지 못했습니다")).not.toBeInTheDocument();
    expect(screen.getByText("2곳")).toBeInTheDocument(); // 개수는 계속 보인다
  });

  it("직접 검색해 담기로 이어진다", async () => {
    const user = userEvent.setup();
    const onSearchAndAdd = vi.fn();
    render(<UnresolvedPanel unresolved={unresolved} onSearchAndAdd={onSearchAndAdd} />);

    await user.click(screen.getAllByRole("button", { name: "직접 검색해 담기" })[0]!);
    expect(onSearchAndAdd).toHaveBeenCalledWith("없는맛집");
  });

  it("미해결이 없으면 아무것도 렌더링하지 않는다", () => {
    const { container } = render(<UnresolvedPanel unresolved={[]} onSearchAndAdd={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });
});
