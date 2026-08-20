"""C16 DistanceMatrix — 구간별 이동시간·거리 값 객체.

근거:
    business-logic-model.md WF-4
    이 객체는 **어떤 API 도 호출하지 않는다.** C24 TravelMatrixService 가 조립해 넘긴다.
    덕분에 C15·C18 이 네트워크 없이 실행되고 PBT 대상이 된다.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from app.domain.models import TravelLeg, TravelMode


class DistanceMatrix:
    """`(from_index, to_index, mode)` → `TravelLeg` 조회 전용 구조."""

    __slots__ = ("_legs",)

    def __init__(self, legs: Iterable[TravelLeg] = ()) -> None:
        self._legs: dict[tuple[int, int, TravelMode], TravelLeg] = {
            (leg.from_index, leg.to_index, leg.mode): leg for leg in legs
        }

    @classmethod
    def from_legs(cls, legs: Iterable[TravelLeg]) -> "DistanceMatrix":
        return cls(legs)

    def get(self, from_index: int, to_index: int, mode: TravelMode) -> TravelLeg | None:
        if from_index == to_index:
            return None
        return self._legs.get((from_index, to_index, mode))

    def duration(self, from_index: int, to_index: int, mode: TravelMode) -> int:
        """구간 소요시간(초). 자기 자신은 0, 미등록 구간도 0으로 취급한다.

        미등록을 0 으로 두는 이유: 최적화(C18)는 부분적으로 채워진 행렬에서도
        항상 유효한 순서를 반환해야 한다 (BR-22).
        """
        if from_index == to_index:
            return 0
        leg = self._legs.get((from_index, to_index, mode))
        return leg.duration_sec if leg is not None else 0

    def total(self, order: Sequence[int], mode: TravelMode) -> int:
        """주어진 방문 순서의 총 이동시간(초)."""
        return sum(
            self.duration(order[i], order[i + 1], mode) for i in range(len(order) - 1)
        )

    def legs(self) -> tuple[TravelLeg, ...]:
        return tuple(self._legs.values())

    def __len__(self) -> int:
        return len(self._legs)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<DistanceMatrix legs={len(self._legs)}>"
