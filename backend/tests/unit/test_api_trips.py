"""여행 CRUD·편집 API 테스트 — FR-4, FR-5, FR-7, BR-01~05, BR-39."""

from __future__ import annotations


def _create(client, payload) -> str:
    response = client.post("/api/trips", json=payload)
    assert response.status_code == 201
    return response.json()["trip_id"]


def test_create_and_get_trip(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)

    response = api_client.get(f"/api/trips/{trip_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["destination"] == "부산"
    assert len(body["days"]) == 2
    assert body["days"][0]["items"] == []


def test_trip_id_is_uuid_not_sequential(api_client, sample_trip_payload) -> None:
    """SEC-08 — 추측 가능한 순차 ID 를 쓰지 않는다."""
    first = _create(api_client, sample_trip_payload)
    second = _create(api_client, sample_trip_payload)
    assert first != second
    assert len(first) == 36 and first.count("-") == 4


def test_no_trip_list_endpoint(api_client) -> None:
    """🔴 BR-39 / SEC-08 — 목록 엔드포인트가 존재하면 열거가 가능해진다."""
    response = api_client.get("/api/trips")
    assert response.status_code in (404, 405)

    schema = api_client.get("/api/openapi.json").json()
    assert "/api/trips" not in schema["paths"] or "get" not in schema["paths"]["/api/trips"]


def test_unknown_trip_returns_404_problem(api_client) -> None:
    response = api_client.get("/api/trips/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "NOT_FOUND"
    assert body["detail"] == "요청하신 정보를 찾을 수 없습니다."


def test_trip_longer_than_limit_is_rejected(api_client, sample_trip_payload) -> None:
    """BR-01 — 기간 10일 초과 거부."""
    payload = {**sample_trip_payload, "end_date": "2026-09-30"}
    response = api_client.post("/api/trips", json=payload)
    assert response.status_code == 400
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_end_before_start_is_rejected(api_client, sample_trip_payload) -> None:
    payload = {**sample_trip_payload, "end_date": "2026-08-01"}
    assert api_client.post("/api/trips", json=payload).status_code == 400


def test_unknown_field_is_rejected(api_client, sample_trip_payload) -> None:
    """SEC-05 — `extra="forbid"` 로 예상치 못한 입력을 거부한다."""
    payload = {**sample_trip_payload, "admin": True}
    assert api_client.post("/api/trips", json=payload).status_code == 400


def test_party_size_out_of_range_is_rejected(api_client, sample_trip_payload) -> None:
    payload = {**sample_trip_payload, "party_size": 999}
    assert api_client.post("/api/trips", json=payload).status_code == 400


# ---------------------------------------------------------------------------
# 항목 편집
# ---------------------------------------------------------------------------
def _item_payload(**overrides) -> dict:
    payload = {
        "name": "광안리 해수욕장",
        "latitude": 35.1531,
        "longitude": 129.1180,
        "category_raw": "여행>관광,명소",
        "road_address": "부산광역시 수영구 광안해변로 219",
    }
    payload.update(overrides)
    return payload


def test_add_and_remove_item(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)

    added = api_client.post(f"/api/trips/{trip_id}/days/1/items", json=_item_payload())
    assert added.status_code == 200
    items = added.json()["days"][0]["items"]
    assert len(items) == 1
    assert items[0]["arrival_at"] is not None  # FR-9 — 타임라인 자동 계산

    item_id = items[0]["item_id"]
    removed = api_client.delete(f"/api/trips/{trip_id}/items/{item_id}")
    assert removed.json()["days"][0]["items"] == []


def test_out_of_country_coordinate_is_rejected(api_client, sample_trip_payload) -> None:
    """BR-15 — 스키마 수준에서 국내 범위를 강제한다."""
    trip_id = _create(api_client, sample_trip_payload)
    response = api_client.post(
        f"/api/trips/{trip_id}/days/1/items",
        json=_item_payload(latitude=0.0, longitude=0.0),
    )
    assert response.status_code == 400


def test_patch_item_updates_stay_and_memo(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)
    item_id = api_client.post(
        f"/api/trips/{trip_id}/days/1/items", json=_item_payload()
    ).json()["days"][0]["items"][0]["item_id"]

    response = api_client.patch(
        f"/api/trips/{trip_id}/items/{item_id}",
        json={"stay_minutes": 120, "memo": "야경 보기"},
    )
    item = response.json()["days"][0]["items"][0]
    assert item["stay_minutes"] == 120
    assert item["memo"] == "야경 보기"


def test_reorder_requires_same_item_set(api_client, sample_trip_payload) -> None:
    """순서 변경은 항목 집합을 보존해야 한다 (P-06 과 같은 취지)."""
    trip_id = _create(api_client, sample_trip_payload)
    api_client.post(f"/api/trips/{trip_id}/days/1/items", json=_item_payload())

    response = api_client.put(
        f"/api/trips/{trip_id}/days/1/order", json={"item_ids": ["없는-아이디"]}
    )
    assert response.status_code == 400


def test_opening_hours_is_user_entered_only(api_client, sample_trip_payload) -> None:
    """BR-35 — 영업시간은 이 엔드포인트로만 채워진다."""
    trip_id = _create(api_client, sample_trip_payload)
    item_id = api_client.post(
        f"/api/trips/{trip_id}/days/1/items", json=_item_payload()
    ).json()["days"][0]["items"][0]["item_id"]

    # 입력 전에는 영업시간 정보가 없다 (외부에서 채우지 않으므로)
    before = api_client.get(f"/api/trips/{trip_id}").json()
    assert before["days"][0]["items"][0]["place"]["opening_hours"] is None

    response = api_client.put(
        f"/api/trips/{trip_id}/items/{item_id}/opening-hours",
        json={"weekday_rules": [{"weekday": 1, "open": "11:00:00", "close": "21:00:00"}]},
    )
    place = response.json()["days"][0]["items"][0]["place"]
    assert place["opening_hours"]["entered_by_user"] is True


def test_delete_trip(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)
    assert api_client.delete(f"/api/trips/{trip_id}").status_code == 204
    assert api_client.get(f"/api/trips/{trip_id}").status_code == 404
