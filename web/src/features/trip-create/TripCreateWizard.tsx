/**
 * W6 TripCreateWizard — 여행 생성 (FR-1, FR-2).
 *
 * 근거:
 *   WBR-10  🔴 폼 상한은 **`GET /api/config` 의 `limits`** 를 쓴다. 숫자를 하드코딩하지 않는다
 *           (서버 상한과 어긋나면 사용자가 이유 없이 거부당한다)
 *   WBR-05  생성 후 로컬 목록에 저장
 *   WBR-06  최초 생성 시 1회 안내
 *   WBR-33  오류는 "동작 + 백엔드 문구" 로 조립
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";

import { api } from "@/shared/api/client";
import { describeError } from "@/shared/api/errors";
import type { TravelMode, TripSpecIn } from "@/shared/api/types";
import { useRuntimeConfig } from "@/shared/config/RuntimeConfigProvider";
import { isFirstTrip, saveTripRef } from "@/shared/storage/tripList";
import { Button } from "@/shared/ui";

const STYLE_TAGS = ["맛집", "자연", "역사", "쇼핑", "휴식", "액티비티"] as const;
const TRAVEL_MODES: { value: TravelMode; label: string; note?: string }[] = [
  { value: "TRANSIT", label: "대중교통", note: "이동시간은 추정치로 표시됩니다" },
  { value: "CAR", label: "자동차" },
  { value: "WALK", label: "도보" },
];

function today(offsetDays = 0): string {
  const date = new Date();
  date.setDate(date.getDate() + offsetDays);
  return date.toISOString().slice(0, 10);
}

export function TripCreateWizard() {
  const navigate = useNavigate();
  const { limits } = useRuntimeConfig(); // WBR-10

  const [form, setForm] = useState<TripSpecIn>({
    title: "",
    destination: "",
    start_date: today(7),
    end_date: today(9),
    party_size: 2,
    style_tags: [],
    day_start_time: "09:00:00",
    day_end_time: "21:00:00",
    default_travel_mode: "TRANSIT",
    budget_level: null,
  });
  const [error, setError] = useState<string | null>(null);

  const dayCount =
    Math.floor(
      (Date.parse(form.end_date) - Date.parse(form.start_date)) / 86_400_000,
    ) + 1;
  const tooLong = Number.isFinite(dayCount) && dayCount > limits.max_trip_days;
  const invalidRange = !Number.isFinite(dayCount) || dayCount < 1;
  const canSubmit =
    form.title.trim() !== "" && form.destination.trim() !== "" && !tooLong && !invalidRange;

  const create = useMutation({
    mutationFn: async (withAi: boolean) => {
      const trip = await api.createTrip(form);
      saveTripRef({
        trip_id: trip.trip_id,
        title: trip.title,
        destination: trip.destination,
        start_date: trip.start_date,
        end_date: trip.end_date,
        share_token: null,
      });
      if (!withAi) return { tripId: trip.trip_id, jobId: null };
      const job = await api.startGeneration(trip.trip_id, form);
      return { tripId: trip.trip_id, jobId: job.job_id };
    },
    onSuccess: ({ tripId, jobId }) => {
      const suffix = jobId ? `?job=${jobId}` : "";
      navigate(`/trips/${tripId}${suffix}`);
    },
    onError: (cause) => {
      const { message } = describeError(cause, "여행을 만들지 못했습니다.");
      setError(message);
    },
  });

  const firstTime = isFirstTrip();

  return (
    <main className="page page--create">
      <h1>새 여행 만들기</h1>

      <form
        className="form"
        onSubmit={(event) => {
          event.preventDefault();
          if (canSubmit) create.mutate(true);
        }}
      >
        <label className="field">
          <span className="field__label">여행 이름</span>
          <input
            className="field__input"
            value={form.title}
            maxLength={100}
            required
            placeholder="예: 부산 2박3일"
            onChange={(e) => setForm({ ...form, title: e.target.value })}
          />
        </label>

        <label className="field">
          <span className="field__label">목적지</span>
          <input
            className="field__input"
            value={form.destination}
            maxLength={50}
            required
            placeholder="예: 부산"
            onChange={(e) => setForm({ ...form, destination: e.target.value })}
          />
          <span className="field__hint">국내 여행만 지원합니다.</span>
        </label>

        <div className="field-row">
          <label className="field">
            <span className="field__label">시작일</span>
            <input
              type="date"
              className="field__input"
              value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })}
            />
          </label>
          <label className="field">
            <span className="field__label">종료일</span>
            <input
              type="date"
              className="field__input"
              value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })}
            />
          </label>
        </div>

        {/* WBR-10 — 상한 문구도 서버 값에서 만든다 */}
        {tooLong ? (
          <p className="form-error" role="alert">
            여행 기간은 최대 {limits.max_trip_days}일까지 가능합니다. (현재 {dayCount}일)
          </p>
        ) : null}
        {invalidRange ? (
          <p className="form-error" role="alert">
            종료일이 시작일보다 빠릅니다.
          </p>
        ) : null}

        <label className="field">
          <span className="field__label">인원</span>
          <input
            type="number"
            className="field__input"
            min={1}
            max={20}
            value={form.party_size ?? 2}
            onChange={(e) => setForm({ ...form, party_size: Number(e.target.value) })}
          />
        </label>

        <fieldset className="field">
          <legend className="field__label">여행 스타일 (최대 8개)</legend>
          <div className="chip-group">
            {STYLE_TAGS.map((tag) => {
              const selected = (form.style_tags ?? []).includes(tag);
              return (
                <button
                  key={tag}
                  type="button"
                  className={`chip ${selected ? "chip--on" : ""}`}
                  aria-pressed={selected}
                  onClick={() =>
                    setForm({
                      ...form,
                      style_tags: selected
                        ? (form.style_tags ?? []).filter((t) => t !== tag)
                        : [...(form.style_tags ?? []), tag].slice(0, 8),
                    })
                  }
                >
                  {tag}
                </button>
              );
            })}
          </div>
        </fieldset>

        <div className="field-row">
          <label className="field">
            <span className="field__label">하루 시작</span>
            <input
              type="time"
              className="field__input"
              value={(form.day_start_time ?? "09:00:00").slice(0, 5)}
              onChange={(e) => setForm({ ...form, day_start_time: `${e.target.value}:00` })}
            />
          </label>
          <label className="field">
            <span className="field__label">하루 종료</span>
            <input
              type="time"
              className="field__input"
              value={(form.day_end_time ?? "21:00:00").slice(0, 5)}
              onChange={(e) => setForm({ ...form, day_end_time: `${e.target.value}:00` })}
            />
          </label>
        </div>

        <fieldset className="field">
          <legend className="field__label">주 이동수단</legend>
          <div className="chip-group">
            {TRAVEL_MODES.map((mode) => (
              <button
                key={mode.value}
                type="button"
                className={`chip ${form.default_travel_mode === mode.value ? "chip--on" : ""}`}
                aria-pressed={form.default_travel_mode === mode.value}
                onClick={() => setForm({ ...form, default_travel_mode: mode.value })}
              >
                {mode.label}
              </button>
            ))}
          </div>
          {/* CON-1 을 입력 시점에 미리 알린다 */}
          {form.default_travel_mode === "TRANSIT" ? (
            <span className="field__hint">
              대중교통 이동시간은 추정치로 표시되고, 정확한 안내는 네이버지도로 연결됩니다.
            </span>
          ) : null}
        </fieldset>

        {error ? (
          <p className="form-error" role="alert">
            {error}
          </p>
        ) : null}

        {firstTime ? (
          <p className="field__hint">
            만든 여행은 <strong>이 브라우저에만</strong> 저장됩니다.
          </p>
        ) : null}

        <div className="form-actions">
          <Button variant="primary" type="submit" disabled={!canSubmit || create.isPending}>
            {create.isPending ? "만드는 중…" : "AI로 일정 만들기"}
          </Button>
          <Button
            variant="secondary"
            disabled={!canSubmit || create.isPending}
            onClick={() => create.mutate(false)}
          >
            빈 일정으로 시작
          </Button>
        </div>
      </form>
    </main>
  );
}
