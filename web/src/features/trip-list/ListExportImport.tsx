/**
 * 여행 목록 내보내기/가져오기 — WBR-07, WBR-08.
 *
 * 브라우저 데이터를 잃었을 때의 **실질적 복구 수단**이다.
 * 순수 로직은 `shared/storage/tripListExport.ts` 에 있고 PBT 로 검증된다 (WP-05·06).
 */
import { useRef, useState } from "react";

import {
  ImportFormatError,
  exportList,
  mergeLists,
  parseExport,
} from "@/shared/storage/tripListExport";
import { listSavedTrips, type SavedTripRef } from "@/shared/storage/tripList";
import { Button } from "@/shared/ui";

const STORAGE_KEY = "trip.savedTrips.v1";

interface Props {
  trips: SavedTripRef[];
  onImported: (merged: SavedTripRef[]) => void;
  onError: (message: string) => void;
}

export function ListExportImport({ trips, onImported, onError }: Props) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [busy, setBusy] = useState(false);

  const handleExport = () => {
    const payload = exportList(trips, new Date().toISOString());
    const blob = new Blob([JSON.stringify(payload, null, 2)], {
      type: "application/json;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `trip-list-${new Date().toISOString().slice(0, 10)}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const handleFile = async (file: File) => {
    setBusy(true);
    try {
      const text = await file.text();
      const parsed = parseExport(text);
      // WBR-08 — 멱등 병합. 같은 파일을 두 번 넣어도 늘지 않는다.
      const merged = mergeLists(listSavedTrips(), parsed.trips);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      onImported(merged);
    } catch (error) {
      // 형식이 아니면 추측하지 않고 그대로 알린다.
      onError(
        error instanceof ImportFormatError
          ? error.message
          : "파일을 읽지 못했습니다. 다시 시도해 주세요.",
      );
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="list-backup">
      <Button variant="ghost" onClick={handleExport} disabled={trips.length === 0}>
        목록 내보내기
      </Button>
      <Button variant="ghost" onClick={() => inputRef.current?.click()} disabled={busy}>
        목록 가져오기
      </Button>
      <input
        ref={inputRef}
        type="file"
        accept="application/json,.json"
        className="visually-hidden"
        aria-label="여행 목록 파일 선택"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) void handleFile(file);
        }}
      />
    </div>
  );
}
