/**
 * 오류 표현 조립.
 *
 * 근거:
 *   BR-58   백엔드는 **고정 문구 6종만** 반환한다. 프론트는 그 문구를 바꾸지 않는다
 *   WBR-33  "어떤 동작이 실패했는지(프론트) + 백엔드 고정 문구" 로 조립한다
 *   WBR-34  추측성 원인을 덧붙이지 않는다
 *   SEC-09  correlation_id 는 접어둔 상세에만 넣는다
 */

/** RFC 9457 Problem Details (u1 `core/errors.py` 와 대응). */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  code: ErrorCode;
  correlation_id: string;
}

export type ErrorCode =
  | "VALIDATION_ERROR"
  | "NOT_FOUND"
  | "RATE_LIMITED"
  | "QUOTA_EXHAUSTED"
  | "EXTERNAL_SERVICE_ERROR"
  | "INTERNAL_ERROR";

/** 네트워크 단절 등 서버 응답 자체가 없는 경우 */
export const OFFLINE_CODE = "OFFLINE" as const;

export class ApiError extends Error {
  readonly problem: ProblemDetails | null;
  readonly httpStatus: number;
  readonly offline: boolean;

  constructor(message: string, options: { problem?: ProblemDetails | null; httpStatus?: number; offline?: boolean } = {}) {
    super(message);
    this.name = "ApiError";
    this.problem = options.problem ?? null;
    this.httpStatus = options.httpStatus ?? 0;
    this.offline = options.offline ?? false;
  }

  get code(): ErrorCode | typeof OFFLINE_CODE | null {
    if (this.offline) return OFFLINE_CODE;
    return this.problem?.code ?? null;
  }

  get correlationId(): string | null {
    return this.problem?.correlation_id ?? null;
  }
}

/**
 * WBR-33 — 사용자에게 보여줄 문구를 만든다.
 *
 * `action` 은 프론트가 아는 맥락이다("일정을 저장하지 못했습니다").
 * `detail` 은 백엔드가 준 고정 문구이며 **그대로** 사용한다 (WBR-34).
 */
export function describeError(error: unknown, action: string): { message: string; correlationId: string | null } {
  if (error instanceof ApiError) {
    if (error.offline) {
      return { message: `${action} 오프라인 상태입니다.`, correlationId: null };
    }
    if (error.problem) {
      return { message: `${action} ${error.problem.detail}`, correlationId: error.problem.correlation_id };
    }
    return { message: `${action} 잠시 후 다시 시도해 주세요.`, correlationId: null };
  }
  // 예상치 못한 예외의 원문을 사용자에게 노출하지 않는다 (SEC-09 와 같은 취지).
  return { message: `${action} 잠시 후 다시 시도해 주세요.`, correlationId: null };
}

/** 응답 본문이 Problem Details 형태인지 판정한다. */
export function isProblemDetails(value: unknown): value is ProblemDetails {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate.status === "number" &&
    typeof candidate.detail === "string" &&
    typeof candidate.code === "string"
  );
}
