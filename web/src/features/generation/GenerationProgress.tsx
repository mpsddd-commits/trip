/**
 * W7 GenerationProgress — AI 생성 진행 표시 (FR-2, DD-5).
 *
 * 근거:
 *   WBR-11  적응형 폴링 간격 + 90초 상한
 *   WBR-12  백그라운드 탭에서는 멈춘다
 *   WBR-13  단계 라벨은 사용자 언어로. **진행률은 서버 값을 그대로 쓴다**(WBR-04)
 *   WBR-25  `partial` 은 구체적으로 알린다
 *   ND-4    재시도 API 가 없다 — 실패 시 새 생성을 시작한다
 */
import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import type { JobStatus } from "@/shared/api/types";
import { queryKeys } from "@/shared/query/keys";
import { isTerminal, nextPoll, stepLabel } from "@/shared/selectors/polling";
import { Banner, Button, Sheet } from "@/shared/ui";

interface Props {
  tripId: string;
  jobId: string;
  onFinished: (status: JobStatus) => void;
  onClose: () => void;
}

export function GenerationProgress({ tripId, jobId, onFinished, onClose }: Props) {
  const queryClient = useQueryClient();
  const startedAt = useRef(Date.now());
  const [timedOut, setTimedOut] = useState(false);
  const finishedRef = useRef(false);

  const { data, refetch } = useQuery({
    queryKey: queryKeys.job(jobId),
    queryFn: ({ signal }) => api.getJob(jobId, signal),
    // WBR-11·12 — 간격은 순수 함수가 정한다. 백그라운드에서는 멈춘다.
    refetchInterval: (query) => {
      const state = query.state.data?.state;
      if (state && isTerminal(state)) return false;
      if (timedOut) return false;
      const decision = nextPoll(Date.now() - startedAt.current);
      if (decision.action === "stop") {
        setTimedOut(true);
        return false;
      }
      return decision.intervalMs;
    },
    refetchIntervalInBackground: false,
  });

  useEffect(() => {
    if (!data || finishedRef.current) return;
    if (!isTerminal(data.state)) return;
    finishedRef.current = true;
    // 생성이 끝나면 여행 데이터를 새로 받는다.
    void queryClient.invalidateQueries({ queryKey: queryKeys.trip(tripId) });
    onFinished(data);
  }, [data, onFinished, queryClient, tripId]);

  const progress = Math.round((data?.progress ?? 0) * 100);
  const terminal = data ? isTerminal(data.state) : false;

  return (
    <Sheet open title="일정을 만들고 있어요" onClose={onClose}>
      {timedOut && !terminal ? (
        <Banner tone="warn">
          시간이 오래 걸리고 있습니다. 잠시 후 아래 버튼으로 상태를 다시 확인해 주세요.
        </Banner>
      ) : null}

      <p className="progress__label">{stepLabel(data?.step)}</p>

      <div
        className="progress"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="일정 생성 진행률"
      >
        <div className="progress__bar" style={{ width: `${progress}%` }} />
      </div>
      <p className="progress__percent">{progress}%</p>

      {data && data.resolved_count + data.unresolved_count > 0 ? (
        <p className="progress__counts">
          확인된 장소 {data.resolved_count}곳
          {data.unresolved_count > 0 ? ` · 확인 필요 ${data.unresolved_count}곳` : ""}
        </p>
      ) : null}

      {data?.state === "failed" ? (
        <Banner tone="danger">
          일정을 만들지 못했습니다. 조건을 조금 바꿔 다시 시도해 주세요.
        </Banner>
      ) : null}

      <div className="form-actions">
        {timedOut && !terminal ? (
          <Button variant="secondary" onClick={() => void refetch()}>
            상태 다시 확인
          </Button>
        ) : null}
        <Button variant="ghost" onClick={onClose}>
          {terminal ? "닫기" : "백그라운드에서 계속"}
        </Button>
      </div>
    </Sheet>
  );
}
