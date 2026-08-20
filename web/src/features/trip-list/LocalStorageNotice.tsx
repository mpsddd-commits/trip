/**
 * 로컬 저장 고지 — WBR-06.
 *
 * 🔴 백엔드는 여행 목록 API 를 **의도적으로 제공하지 않는다**(DD-21 / BR-39 — 열거 취약점 방지).
 *    그래서 "내 여행"은 이 브라우저에만 존재하고, 데이터를 지우면 다시 열 수 없다.
 *    이는 설계상 예견된 결과이지만 **사용자에게는 데이터 유실로 보인다.**
 *    그래서 숨기지 않고 상시로 알린다.
 */
import { Banner } from "@/shared/ui";

export function LocalStorageNotice({ hasTrips }: { hasTrips: boolean }) {
  return (
    <Banner tone="info">
      <strong>여행 목록은 이 브라우저에만 저장됩니다.</strong>
      <br />
      브라우저 데이터를 지우거나 다른 기기에서 열면 목록이 비어 있습니다.
      {hasTrips ? (
        <>
          {" "}
          각 여행의 <strong>공유 링크</strong>를 만들어 두면 어디서든 열 수 있고, 아래{" "}
          <strong>목록 내보내기</strong>로 백업할 수 있습니다.
        </>
      ) : null}
    </Banner>
  );
}

/** 최초 여행 생성 직후 1회 안내 (WBR-06). */
export function FirstTripNotice({ onDismiss }: { onDismiss: () => void }) {
  return (
    <Banner tone="warn" dismissible onDismiss={onDismiss}>
      첫 여행이 저장되었습니다. 이 목록은 <strong>이 브라우저에만</strong> 남습니다 — 로그인이
      없는 대신 아무도 여러분의 일정을 조회할 수 없는 구조입니다. 중요한 일정은 공유 링크를 만들어
      두세요.
    </Banner>
  );
}
