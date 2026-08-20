"""AI 생성 API 테스트 — FR-2, DD-5, BR-13, QG-7(목 모드 전 과정 동작)."""

from __future__ import annotations

import time


def _create(client, payload) -> str:
    return client.post("/api/trips", json=payload).json()["trip_id"]


def _wait(client, job_id: str, *, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/jobs/{job_id}").json()
        if body["state"] in ("succeeded", "partial", "failed"):
            return body
        time.sleep(0.05)
    raise AssertionError("job did not finish in time")


def test_generation_returns_202_immediately(api_client, sample_trip_payload) -> None:
    """DD-5 / NFR-1 — HTTP 응답을 60초 붙잡지 않는다."""
    trip_id = _create(api_client, sample_trip_payload)

    started = time.time()
    response = api_client.post(f"/api/trips/{trip_id}/generate", json=sample_trip_payload)
    elapsed = time.time() - started

    assert response.status_code == 202
    assert elapsed < 2.0
    body = response.json()
    assert body["state"] == "queued"
    assert body["job_id"]


def test_mock_mode_completes_full_pipeline(api_client, sample_trip_payload) -> None:
    """🔴 QG-7 / FR-33 — 인증 정보 0개로도 전 과정이 동작해야 한다."""
    trip_id = _create(api_client, sample_trip_payload)
    job_id = api_client.post(
        f"/api/trips/{trip_id}/generate", json=sample_trip_payload
    ).json()["job_id"]

    result = _wait(api_client, job_id)
    assert result["state"] in ("succeeded", "partial")
    assert result["resolved_count"] > 0
    assert result["progress"] == 1.0

    trip = api_client.get(f"/api/trips/{trip_id}").json()
    total_items = sum(len(day["items"]) for day in trip["days"])
    assert total_items > 0

    # 타임라인이 채워졌다 (FR-9)
    first_day = trip["days"][0]["items"]
    assert first_day and first_day[0]["arrival_at"] is not None


def test_generated_places_have_domestic_coordinates(api_client, sample_trip_payload) -> None:
    """BR-15 — 좌표계 오해석이 있으면 여기서 드러난다."""
    trip_id = _create(api_client, sample_trip_payload)
    job_id = api_client.post(
        f"/api/trips/{trip_id}/generate", json=sample_trip_payload
    ).json()["job_id"]
    _wait(api_client, job_id)

    trip = api_client.get(f"/api/trips/{trip_id}").json()
    for day in trip["days"]:
        for item in day["items"]:
            coordinate = item["place"]["coordinate"]
            assert 33.0 <= coordinate["lat"] <= 39.0
            assert 124.0 <= coordinate["lng"] <= 132.0


def test_unknown_job_returns_404(api_client) -> None:
    response = api_client.get("/api/jobs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_generation_on_missing_trip_returns_404(api_client, sample_trip_payload) -> None:
    response = api_client.post(
        "/api/trips/00000000-0000-0000-0000-000000000000/generate",
        json=sample_trip_payload,
    )
    assert response.status_code == 404


def test_job_status_exposes_unresolved_count(api_client, sample_trip_payload) -> None:
    """FR-3 — 사용자에게 "확인 필요" 개수를 알려야 한다."""
    trip_id = _create(api_client, sample_trip_payload)
    job_id = api_client.post(
        f"/api/trips/{trip_id}/generate", json=sample_trip_payload
    ).json()["job_id"]
    result = _wait(api_client, job_id)
    assert "unresolved_count" in result
    assert "resolved_count" in result
