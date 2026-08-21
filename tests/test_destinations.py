def test_create_and_get_destination(client, admin_auth_headers):
    resp = client.post(
        "/destinations",
        json={"name": "Manali", "country": "India", "best_season": "Summer"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    dest_id = resp.json()["id"]

    get_resp = client.get(f"/destinations/{dest_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Manali"


def test_get_nonexistent_destination_404(client):
    resp = client.get("/destinations/9999")
    assert resp.status_code == 404


def test_filter_destinations_by_country_and_season(client, admin_auth_headers):
    client.post("/destinations", json={"name": "Manali", "country": "India", "best_season": "Summer"}, headers=admin_auth_headers)
    client.post("/destinations", json={"name": "Paris", "country": "France", "best_season": "Spring"}, headers=admin_auth_headers)

    resp = client.get("/destinations?country=India")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Manali"

    resp2 = client.get("/destinations?best_season=Spring")
    assert resp2.json()["total"] == 1
    assert resp2.json()["items"][0]["name"] == "Paris"


def test_update_and_soft_delete_destination(client, admin_auth_headers):
    resp = client.post("/destinations", json={"name": "Kerala", "country": "India"}, headers=admin_auth_headers)
    dest_id = resp.json()["id"]

    upd = client.put(f"/destinations/{dest_id}", json={"description": "Backwaters"}, headers=admin_auth_headers)
    assert upd.status_code == 200
    assert upd.json()["description"] == "Backwaters"

    delete_resp = client.delete(f"/destinations/{dest_id}", headers=admin_auth_headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/destinations/{dest_id}")
    assert get_resp.status_code == 404
