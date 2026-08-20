"""공유 라우터 — FR-25, BR-36 ~ BR-39, SEC-08.

🔴 `GET /api/shared/{token}` 은 **읽기 전용 타입**을 반환한다 (BR-37, DD-25).
   공유 경로에는 편집 엔드포인트가 존재하지 않는다.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from app.api.deps import ContainerDep, rate_limit
from app.api.schemas import ReadOnlyTripOut, ShareTokenOut
from app.core.enums import EndpointTier

router = APIRouter(prefix="/api", tags=["share"])


@router.post(
    "/trips/{trip_id}/share",
    response_model=ShareTokenOut,  # A-2
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def issue_share_token(trip_id: str, container: ContainerDep) -> dict:
    """BR-36 — 암호학적 난수 43자. `trip_id` 와 수학적 관계가 없다."""
    token = await container.trips.issue_share_token(trip_id)
    return {"share_token": token, "url": f"/shared/{token}"}


@router.delete(
    "/trips/{trip_id}/share",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def revoke_share_token(trip_id: str, container: ContainerDep) -> Response:
    """BR-38 — 폐기 시 기존 링크가 즉시 무효화된다."""
    await container.trips.revoke_share_token(trip_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/shared/{share_token}",
    # 🔴 A-2 + DD-25 — `share_token` 필드가 **스키마에 없는** 별도 모델을 쓴다.
    #    열람자에게 토큰을 돌려주지 않는 것이 응답 타입 수준에서 보장된다.
    response_model=ReadOnlyTripOut,
    dependencies=[rate_limit(EndpointTier.CHEAP)],
)
async def get_shared_trip(
    share_token: Annotated[str, Path(min_length=20, max_length=64)],
    container: ContainerDep,
) -> dict:
    """BR-37 — 편집 연산이 정의되지 않은 타입을 반환한다.

    응답에 `share_token` 을 포함하지 않는다 — 열람자가 토큰을 재발급·폐기할
    권한이 없기 때문이다.
    """
    view = await container.trips.get_by_share_token(share_token)
    return view.to_dict()
