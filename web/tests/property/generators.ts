/**
 * 도메인 생성기 (PBT-07 / PBT-R3).
 *
 * 원시 타입 생성기만 쓰지 않고 업무 제약을 지키는 값을 만든다.
 * - 좌표: 국내 범위 (u1 의 BR-15 와 동일 제약)
 * - 장소명: 한글·영문·공백·특수문자·이모지 포함
 * - 경과 시간: 0 ~ 300초 (폴링 상한 90초를 넘는 구간 포함)
 */
import fc from "fast-check";

import type { Coordinate, ItineraryItem, Place, TravelMode } from "@/shared/api/types";
import type { SavedTripRef } from "@/shared/storage/tripList";

// --- 좌표 (BR-15 와 동일 범위) ------------------------------------------------
export const arbCoordinate = (): fc.Arbitrary<Coordinate> =>
  fc.record({
    lat: fc.double({ min: 33, max: 39, noNaN: true }),
    lng: fc.double({ min: 124, max: 132, noNaN: true }),
  });

/** 경계값을 명시적으로 섞는다. */
export const arbBoundaryCoordinate = (): fc.Arbitrary<Coordinate> =>
  fc.constantFrom<Coordinate>(
    { lat: 33, lng: 124 },
    { lat: 39, lng: 132 },
    { lat: 37.5665, lng: 126.978 },
    { lat: 35.1796, lng: 129.0756 },
    { lat: 33.4996, lng: 126.5312 },
  );

export const arbAnyCoordinate = (): fc.Arbitrary<Coordinate> =>
  fc.oneof(arbCoordinate(), arbBoundaryCoordinate());

// --- 텍스트 -------------------------------------------------------------------
/** 한글·영문·공백·특수문자·이모지를 섞는다 (WP-01 왕복 검증용) */
export const arbPlaceName = (): fc.Arbitrary<string> =>
  fc.oneof(
    fc.string({ minLength: 1, maxLength: 30 }),
    fc.constantFrom(
      "광안리 해수욕장",
      "돼지국밥 & 수육",
      "카페, 디저트",
      "세미콜론; 포함",
      "역슬래시 \\ 포함",
      "이모지 🍜 포함",
      "  앞뒤 공백  ",
      "?query=1&x=2",
      "100% 맛집",
    ),
    fc.unicodeString({ minLength: 1, maxLength: 20 }),
  );

export const arbTravelMode = (): fc.Arbitrary<TravelMode> =>
  fc.constantFrom<TravelMode>("WALK", "CAR", "TRANSIT");

// --- 장소 / 항목 ---------------------------------------------------------------
export const arbPlace = (): fc.Arbitrary<Place> =>
  fc.record({
    place_id: fc.uuid(),
    name: arbPlaceName(),
    coordinate: arbAnyCoordinate(),
    category: fc.constantFrom("RESTAURANT", "CAFE", "ATTRACTION", "MUSEUM", "SHOPPING", "ACCOMMODATION", "OTHER"),
    road_address: fc.option(fc.string({ maxLength: 40 }), { nil: null }),
    address: fc.option(fc.string({ maxLength: 40 }), { nil: null }),
    category_raw: fc.option(fc.string({ maxLength: 30 }), { nil: null }),
    phone: fc.option(fc.string({ maxLength: 20 }), { nil: null }),
    naver_link: fc.option(fc.webUrl(), { nil: null }),
    source: fc.constantFrom("NAVER_LOCAL", "USER_MANUAL", "MOCK"),
    resolved_from: fc.option(arbPlaceName(), { nil: null }),
    match_score: fc.option(fc.double({ min: 0, max: 1, noNaN: true }), { nil: null }),
    opening_hours: fc.constant(null),
  }) as fc.Arbitrary<Place>;

const WARNING_TYPES = [
  "OUTSIDE_OPENING_HOURS",
  "FIXED_TIME_CONFLICT",
  "DAY_OVERFLOW",
  "ESTIMATED_TRAVEL_TIME",
] as const;

export const arbItineraryItem = (): fc.Arbitrary<ItineraryItem> =>
  fc
    .record({
      item_id: fc.uuid(),
      place: arbPlace(),
      stay_minutes: fc.integer({ min: 1, max: 720 }),
      position: fc.integer({ min: 0, max: 14 }),
      offsetMinutes: fc.integer({ min: 0, max: 600 }),
      timed: fc.boolean(),
      warnings: fc.array(
        fc.record({ type: fc.constantFrom(...WARNING_TYPES), detail: fc.string({ maxLength: 40 }) }),
        { maxLength: 4 },
      ),
      memo: fc.option(fc.string({ maxLength: 100 }), { nil: null }),
      travel_mode: fc.option(arbTravelMode(), { nil: null }),
    })
    .map(({ offsetMinutes, timed, ...rest }) => {
      const base = Date.UTC(2026, 8, 1, 0, 0, 0);
      const arrival = new Date(base + offsetMinutes * 60_000);
      const departure = new Date(arrival.getTime() + rest.stay_minutes * 60_000);
      return {
        ...rest,
        arrival_at: timed ? arrival.toISOString() : null,
        departure_at: timed ? departure.toISOString() : null,
        time_fixed: false,
        fixed_time: null,
      } as ItineraryItem;
    });

// --- 로컬 여행 목록 -------------------------------------------------------------
export const arbSavedTripRef = (): fc.Arbitrary<SavedTripRef> =>
  fc.record({
    trip_id: fc.uuid(),
    title: fc.string({ minLength: 1, maxLength: 40 }),
    destination: fc.constantFrom("서울", "부산", "제주", "강릉", "전주"),
    start_date: fc.constantFrom("2026-09-01", "2026-10-05", "2027-01-02"),
    end_date: fc.constantFrom("2026-09-03", "2026-10-07", "2027-01-04"),
    share_token: fc.option(fc.string({ minLength: 43, maxLength: 43 }), { nil: null }),
    saved_at: fc
      .integer({ min: 0, max: 100_000 })
      .map((offset) => new Date(Date.UTC(2026, 0, 1) + offset * 60_000).toISOString()),
  });

/** `trip_id` 가 서로 다른 목록 (병합 규칙 검증용) */
export const arbTripList = (): fc.Arbitrary<SavedTripRef[]> =>
  fc
    .array(arbSavedTripRef(), { maxLength: 10 })
    .map((refs) => {
      const seen = new Set<string>();
      return refs.filter((r) => (seen.has(r.trip_id) ? false : (seen.add(r.trip_id), true)));
    });

// --- 경과 시간 -----------------------------------------------------------------
export const arbElapsedMs = (): fc.Arbitrary<number> =>
  fc.oneof(
    fc.integer({ min: -5_000, max: 300_000 }),
    fc.constantFrom(0, 9_999, 10_000, 10_001, 89_999, 90_000, 90_001),
  );
