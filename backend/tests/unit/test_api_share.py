"""공유 API 테스트 — FR-25, BR-36 ~ BR-39, SEC-08, DD-25."""

from __future__ import annotations


def _create(client, payload) -> str:
    return client.post("/api/trips", json=payload).json()["trip_id"]


def test_issue_and_read_share_link(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)

    issued = api_client.post(f"/api/trips/{trip_id}/share")
    assert issued.status_code == 200
    token = issued.json()["share_token"]

    shared = api_client.get(f"/api/shared/{token}")
    assert shared.status_code == 200
    assert shared.json()["read_only"] is True


def test_share_token_is_independent_of_trip_id(api_client, sample_trip_payload) -> None:
    """BR-36 — 토큰에서 trip_id 를 역산할 수 없어야 한다."""
    trip_id = _create(api_client, sample_trip_payload)
    token = api_client.post(f"/api/trips/{trip_id}/share").json()["share_token"]

    assert token != trip_id
    assert trip_id not in token
    assert len(token) >= 40  # 32바이트 base64url

    # trip_id 로 공유 경로에 접근할 수 없다
    assert api_client.get(f"/api/shared/{trip_id}").status_code == 404


def test_shared_view_hides_the_token(api_client, sample_trip_payload) -> None:
    """열람자는 토큰을 재발급·폐기할 권한이 없으므로 노출하지 않는다."""
    trip_id = _create(api_client, sample_trip_payload)
    token = api_client.post(f"/api/trips/{trip_id}/share").json()["share_token"]

    body = api_client.get(f"/api/shared/{token}").json()
    assert "share_token" not in body


def test_revoke_invalidates_link_immediately(api_client, sample_trip_payload) -> None:
    """BR-38."""
    trip_id = _create(api_client, sample_trip_payload)
    token = api_client.post(f"/api/trips/{trip_id}/share").json()["share_token"]
    assert api_client.get(f"/api/shared/{token}").status_code == 200

    assert api_client.delete(f"/api/trips/{trip_id}/share").status_code == 204
    assert api_client.get(f"/api/shared/{token}").status_code == 404


def test_reissue_produces_a_new_token(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)
    first = api_client.post(f"/api/trips/{trip_id}/share").json()["share_token"]
    second = api_client.post(f"/api/trips/{trip_id}/share").json()["share_token"]
    assert first != second
    assert api_client.get(f"/api/shared/{first}").status_code == 404


def test_no_write_endpoints_under_shared_path(api_client) -> None:
    """🔴 BR-37 / DD-25 — 공유 경로에는 편집 엔드포인트가 존재하지 않는다."""
    schema = api_client.get("/api/openapi.json").json()
    shared_paths = [path for path in schema["paths"] if path.startswith("/api/shared")]
    assert shared_paths  # 조회 경로는 있어야 한다
    for path in shared_paths:
        methods = set(schema["paths"][path])
        assert methods <= {"get", "parameters"}, f"{path} 에 쓰기 메서드가 있습니다: {methods}"


def test_deleted_trip_invalidates_share(api_client, sample_trip_payload) -> None:
    trip_id = _create(api_client, sample_trip_payload)
    token = api_client.post(f"/api/trips/{trip_id}/share").json()["share_token"]
    api_client.delete(f"/api/trips/{trip_id}")
    assert api_client.get(f"/api/shared/{token}").status_code == 404
