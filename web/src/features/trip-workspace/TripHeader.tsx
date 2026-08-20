/**
 * 여행 헤더 — 제목·기간·공유·내보내기 (FR-4, FR-25, FR-26).
 *
 * WBR-05 — 공유 토큰을 발급하면 로컬 목록에도 기록한다(복구 수단).
 */
import { Link } from "react-router-dom";

import { api } from "@/shared/api/client";
import type { Trip } from "@/shared/api/types";
import { share } from "@/shared/bridge";
import { updateShareToken } from "@/shared/storage/tripList";
import { Badge, Button } from "@/shared/ui";

interface Props {
  trip: Trip;
  canEdit: boolean;
  onIssueShare: () => void;
  onRevokeShare: () => void;
  onNotify: (message: string) => void;
}

export function TripHeader({ trip, canEdit, onIssueShare, onRevokeShare, onNotify }: Props) {
  const shareUrl = trip.share_token
    ? `${window.location.origin}/shared/${trip.share_token}`
    : null;

  const handleShare = async () => {
    if (!shareUrl) return;
    updateShareToken(trip.trip_id, trip.share_token ?? null); // WBR-05
    const result = await share({
      title: trip.title,
      text: `${trip.destination} 여행 일정`,
      url: shareUrl,
    });
    if (result === "clipboard") onNotify("공유 링크를 클립보드에 복사했습니다.");
    if (result === "failed") onNotify("공유에 실패했습니다. 링크를 직접 복사해 주세요.");
  };

  return (
    <header className="trip-header">
      <div className="trip-header__main">
        <Link to="/" className="trip-header__back">
          ← 목록
        </Link>
        <h1 className="trip-header__title">{trip.title}</h1>
        <p className="trip-header__meta">
          {trip.destination} · {trip.start_date} ~ {trip.end_date} · {trip.party_size}명
        </p>
      </div>

      <div className="trip-header__actions">
        <a className="btn btn--ghost" href={api.exportIcsUrl(trip.trip_id)} download>
          캘린더(.ics) 내보내기
        </a>

        {trip.share_token ? (
          <>
            <Badge tone="info">공유 중</Badge>
            <Button variant="secondary" onClick={() => void handleShare()}>
              링크 공유
            </Button>
            <Button
              variant="ghost"
              disabled={!canEdit}
              onClick={() => {
                updateShareToken(trip.trip_id, null);
                onRevokeShare();
              }}
            >
              공유 해제
            </Button>
          </>
        ) : (
          <Button variant="secondary" disabled={!canEdit} onClick={onIssueShare}>
            공유 링크 만들기
          </Button>
        )}
      </div>
    </header>
  );
}
