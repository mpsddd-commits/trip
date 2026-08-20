/**
 * 서버 자원 타입 별칭.
 *
 * WBR-01 / WBR-02 — `generated.ts` 를 손으로 고치지 않고, 서버 개념을 다시 정의하지도 않는다.
 *                    여기서는 **이름만 짧게** 붙인다. 구조는 전부 생성 타입에서 온다.
 *
 * 개정 A-2 덕분에 이 타입들이 실제 구조를 갖는다.
 * (그 전에는 응답이 `object` 로 생성되어 전부 `unknown` 이었다.)
 */
import type { components } from "./generated";

type Schemas = components["schemas"];

// --- 여행 -------------------------------------------------------------------
export type Trip = Schemas["TripOut"];
export type ReadOnlyTrip = Schemas["ReadOnlyTripOut"];
export type TripDay = Schemas["TripDayOut"];
export type ItineraryItem = Schemas["ItineraryItemOut"];
export type Place = Schemas["PlaceOut"];
export type Coordinate = Schemas["CoordinateOut"];
export type ItemWarning = Schemas["ItemWarningOut"];
export type OpeningHours = Schemas["OpeningHoursOut"];
export type DayRule = Schemas["DayRuleOut"];

/** FR-3 / BR-18 — 일정에 들어가지 못한 후보. "확인 필요" 목록의 원소. */
export type UnresolvedCandidate = Schemas["UnresolvedOut"];

// --- 생성 작업 ---------------------------------------------------------------
export type JobStatus = Schemas["JobStatusOut"];
export type JobAccepted = Schemas["JobAccepted"];
export type JobState = Schemas["JobState"];
export type GenerationStep = Schemas["GenerationStep"];

// --- 장소 -------------------------------------------------------------------
export type PagedPlaces = Schemas["PagedPlacesOut"];
export type PlaceContent = Schemas["PlaceContentOut"];
export type BlogRef = Schemas["BlogRefOut"];
export type ImageRef = Schemas["ImageRefOut"];

// --- 입력 -------------------------------------------------------------------
export type TripSpecIn = Schemas["TripSpecIn"];
export type ItemCreate = Schemas["ItemCreate"];
export type ItemPatch = Schemas["ItemPatch"];
export type OpeningHoursIn = Schemas["OpeningHoursIn"];
export type OptimizeIn = Schemas["OptimizeIn"];

// --- 기타 -------------------------------------------------------------------
export type RuntimeConfig = Schemas["RuntimeConfigOut"];
export type Limits = Schemas["LimitsOut"];
export type ShareToken = Schemas["ShareTokenOut"];
export type TravelMode = Schemas["TravelMode"];
export type PlaceCategory = Schemas["PlaceCategory"];
export type WarningType = Schemas["WarningType"];
export type ResolveFailureCode = Schemas["ResolveFailureCode"];

/**
 * 🔴 `ReadOnlyTrip` 에는 `share_token` 필드가 **스키마상 존재하지 않는다** (DD-25, A-2).
 *    공유 화면에서 토큰을 읽으려 하면 컴파일 오류가 난다.
 */
