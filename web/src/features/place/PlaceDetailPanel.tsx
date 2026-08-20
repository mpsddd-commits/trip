/**
 * W9 PlaceDetailPanel — 장소 상세 (FR-17, FR-20, FR-21, FR-13).
 *
 * 🔴 BR-40 의 UI 측 대응:
 *    서버는 근거 블로그가 3건 미만이면 `highlights` 를 빈 목록으로 준다.
 *    그때는 **"AI 요약" 영역을 아예 렌더링하지 않는다.** 빈 제목만 남기면
 *    사용자는 "요약이 로딩 중인가?" 하고 기다리게 된다.
 *
 * 근거:
 *   BR-44 / CON-8  근거 링크와 이미지 출처를 반드시 함께 보여준다
 *   FR-23          네이버지도 열기
 *   FR-13 / BR-35  영업시간은 **사용자가 입력**한다
 */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import type { ItineraryItem, OpeningHoursIn } from "@/shared/api/types";
import { openMap } from "@/shared/bridge";
import { placeUrl } from "@/shared/deeplink";
import { queryKeys } from "@/shared/query/keys";
import { Badge, Button, Sheet, Skeleton } from "@/shared/ui";

interface Props {
  open: boolean;
  tripId: string;
  item: ItineraryItem | undefined;
  canEdit: boolean;
  onClose: () => void;
  onSaveOpeningHours: (itemId: string, hours: OpeningHoursIn) => void;
}

const WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"];

export function PlaceDetailPanel({
  open,
  tripId,
  item,
  canEdit,
  onClose,
  onSaveOpeningHours,
}: Props) {
  const [hoursOpen, setHoursOpen] = useState(false);
  const [weekday, setWeekday] = useState(0);
  const [openTime, setOpenTime] = useState("11:00");
  const [closeTime, setCloseTime] = useState("21:00");

  const { data, isPending } = useQuery({
    queryKey: queryKeys.placeContent(item?.place.place_id ?? "none"),
    queryFn: ({ signal }) => api.getPlaceContent(tripId, item?.item_id ?? "", signal),
    enabled: open && item !== undefined,
  });

  if (!item) return null;
  const place = item.place;

  return (
    <Sheet open={open} title={place.name} onClose={onClose}>
      <section className="place-detail">
        {place.road_address ? <p className="place-detail__address">{place.road_address}</p> : null}
        {place.phone ? <p className="place-detail__phone">{place.phone}</p> : null}
        {place.category_raw ? <Badge tone="neutral">{place.category_raw}</Badge> : null}

        <Button variant="secondary" onClick={() => openMap(placeUrl(place))}>
          네이버지도에서 보기
        </Button>

        {/* --- 추천 콘텐츠 --- */}
        {isPending ? (
          <Skeleton lines={3} label="추천 정보 불러오는 중" />
        ) : (
          <>
            {/* 🔴 BR-40 — highlights 가 비면 요약 영역 자체를 렌더링하지 않는다 */}
            {data && data.highlights.length > 0 ? (
              <div className="place-detail__highlights">
                <h3>
                  {place.category === "RESTAURANT" || place.category === "CAFE"
                    ? "대표 메뉴"
                    : "관람 포인트"}
                  <Badge tone="info" title="블로그 후기를 근거로 AI가 요약했습니다">
                    AI 요약
                  </Badge>
                </h3>
                <ul>
                  {data.highlights.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {/* BR-44 / CON-8 — 근거를 반드시 함께 노출한다 */}
            {data && data.sources.length > 0 ? (
              <div className="place-detail__sources">
                <h3>근거 후기</h3>
                <ul>
                  {data.sources.map((source) => (
                    <li key={source.link}>
                      <a href={source.link} target="_blank" rel="noopener noreferrer">
                        {source.title}
                      </a>
                      {source.blogger_name ? <span> · {source.blogger_name}</span> : null}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {data && data.images.length > 0 ? (
              <div className="place-detail__images">
                {data.images.map((image) => (
                  <a key={image.link} href={image.link} target="_blank" rel="noopener noreferrer">
                    <img src={image.thumbnail_url} alt={image.source_title || place.name} loading="lazy" />
                  </a>
                ))}
              </div>
            ) : null}
          </>
        )}

        {/* --- 영업시간 (FR-13 / BR-35 — 사용자 입력 전용) --- */}
        <div className="place-detail__hours">
          <h3>영업시간</h3>
          {place.opening_hours && place.opening_hours.weekday_rules.length > 0 ? (
            <ul>
              {place.opening_hours.weekday_rules.map((rule) => (
                <li key={rule.weekday}>
                  {WEEKDAYS[rule.weekday]}요일{" "}
                  {rule.closed
                    ? "휴무"
                    : `${(rule.open ?? "").slice(0, 5)} ~ ${(rule.close ?? "").slice(0, 5)}`}
                </li>
              ))}
            </ul>
          ) : (
            <p className="place-detail__hint">
              네이버 검색은 영업시간을 제공하지 않습니다. 직접 입력하면 도착 시각이 영업시간 밖일 때
              알려드립니다.
            </p>
          )}

          {canEdit ? (
            hoursOpen ? (
              <div className="hours-form">
                <select value={weekday} onChange={(e) => setWeekday(Number(e.target.value))} aria-label="요일">
                  {WEEKDAYS.map((label, index) => (
                    <option key={label} value={index}>
                      {label}요일
                    </option>
                  ))}
                </select>
                <input type="time" value={openTime} onChange={(e) => setOpenTime(e.target.value)} aria-label="영업 시작" />
                <input type="time" value={closeTime} onChange={(e) => setCloseTime(e.target.value)} aria-label="영업 종료" />
                <Button
                  variant="primary"
                  onClick={() => {
                    onSaveOpeningHours(item.item_id, {
                      weekday_rules: [
                        {
                          weekday,
                          open: `${openTime}:00`,
                          close: `${closeTime}:00`,
                          closed: false,
                        },
                      ],
                    });
                    setHoursOpen(false);
                  }}
                >
                  저장
                </Button>
              </div>
            ) : (
              <Button variant="ghost" onClick={() => setHoursOpen(true)}>
                영업시간 입력
              </Button>
            )
          ) : null}
        </div>
      </section>
    </Sheet>
  );
}
