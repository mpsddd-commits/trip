/**
 * 데모 모드 배너 — WBR-30.
 *
 * 🔴 **닫을 수 없다.** 데모 데이터를 실제 정보로 오해하면 사용자가 존재하지 않는 가게를
 *    찾아가게 된다. 불편하더라도 상시 노출이 옳다.
 */
import { useRuntimeConfig } from "@/shared/config/RuntimeConfigProvider";
import { demoApis, demoLabel } from "@/shared/selectors/trip";
import { Banner } from "@/shared/ui";

export function DemoModeBanner() {
  const { config, failed } = useRuntimeConfig();

  if (failed) {
    // WBR-31 — 설정을 못 받아도 앱은 동작한다. 다만 상태를 숨기지 않는다.
    return (
      <Banner tone="warn">
        서버 설정을 불러오지 못했습니다. 지도 등 일부 기능이 제한될 수 있습니다.
      </Banner>
    );
  }

  const apis = demoApis(config);
  if (apis.length === 0) return null;

  return (
    <Banner tone="warn">
      <strong>데모 데이터로 동작 중입니다</strong> ({demoLabel(apis)}). 표시되는 장소와 추천은{" "}
      <strong>실제 정보가 아닙니다.</strong> 실제 데이터를 쓰려면 <code>.env</code> 에 API 인증
      정보를 넣고 다시 시작하세요.
    </Banner>
  );
}
