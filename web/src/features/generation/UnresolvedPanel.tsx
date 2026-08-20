/**
 * W7 UnresolvedPanel — "확인 필요" 장소 목록.
 *
 * 🔴 이 패널이 BR-18 의 사용자 측 대응이다.
 *    서버는 그라운딩에 실패한 장소를 **일정에 넣지 않는다.** 그대로 두면 사용자는
 *    "AI가 3곳을 빼먹었다"고만 느낀다. 그래서 왜 빠졌는지, 무엇을 하면 되는지 보여준다.
 *
 * 근거:
 *   WBR-25  구체적으로 알린다
 *   WBR-26  실패 사유 6종을 사용자 언어로
 *   WBR-29  **접이식으로 상시 노출**. 닫아도 개수 배지는 남는다
 */
import { useState } from "react";

import type { ResolveFailureCode, UnresolvedCandidate } from "@/shared/api/types";
import { Badge, Button } from "@/shared/ui";

/** WBR-26 — 사용자가 다음에 뭘 할지 알 수 있는 문구로 쓴다. */
const FAILURE_TEXT: Map<ResolveFailureCode, string> = new Map([
  ["NO_SEARCH_RESULT", "검색 결과가 없었습니다"],
  ["LOW_SIMILARITY", "이름이 비슷한 곳을 찾지 못했습니다"],
  ["OUT_OF_REGION", "목적지 밖에 있는 것 같습니다"],
  ["CATEGORY_MISMATCH", "종류가 맞지 않았습니다"],
  ["INVALID_COORDINATE", "위치 정보를 확인하지 못했습니다"],
  ["SEARCH_UNAVAILABLE", "검색 서비스에 일시적인 문제가 있었습니다"],
]);

function failureText(code: ResolveFailureCode): string {
  return FAILURE_TEXT.get(code) ?? "확인하지 못했습니다";
}

interface Props {
  unresolved: UnresolvedCandidate[];
  onSearchAndAdd: (name: string) => void;
}

export function UnresolvedPanel({ unresolved, onSearchAndAdd }: Props) {
  const [open, setOpen] = useState(true);

  if (unresolved.length === 0) return null;

  return (
    <section className="unresolved" aria-label="확인이 필요한 장소">
      <header className="unresolved__header">
        <button
          type="button"
          className="unresolved__toggle"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {/* WBR-29 — 닫아도 개수는 계속 보인다 */}
          확인 필요 <Badge tone="warn">{unresolved.length}곳</Badge>
          <span aria-hidden="true">{open ? "▲" : "▼"}</span>
        </button>
      </header>

      {open ? (
        <>
          <p className="unresolved__intro">
            AI가 제안했지만 <strong>실제로 있는 곳인지 확인하지 못해 일정에 넣지 않았습니다.</strong>{" "}
            직접 검색해 담을 수 있습니다.
          </p>
          <ul className="unresolved__list">
            {unresolved.map((candidate, index) => (
              <li key={`${candidate.raw_name}-${index}`} className="unresolved__item">
                <div className="unresolved__info">
                  <p className="unresolved__name">
                    {candidate.raw_name}
                    <span className="unresolved__day"> · {candidate.day_index}일차 제안</span>
                  </p>
                  <p className="unresolved__reason">{failureText(candidate.failure_code)}</p>
                  {candidate.best_candidate_name ? (
                    <p className="unresolved__hint">
                      가장 비슷했던 곳: <strong>{candidate.best_candidate_name}</strong>
                      {typeof candidate.best_match_score === "number"
                        ? ` (유사도 ${Math.round(candidate.best_match_score * 100)}%)`
                        : ""}
                    </p>
                  ) : null}
                  {candidate.reason ? (
                    <p className="unresolved__why">추천 이유: {candidate.reason}</p>
                  ) : null}
                </div>
                <Button variant="secondary" onClick={() => onSearchAndAdd(candidate.raw_name)}>
                  직접 검색해 담기
                </Button>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
