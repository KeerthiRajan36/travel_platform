import datetime


def _make_destination(client, headers):
    resp = client.post("/destinations", json={"name": "Manali", "country": "India"}, headers=headers)
    return resp.json()["id"]


def test_create_package_success(client, admin_auth_headers):
    dest_id = _make_destination(client, admin_auth_headers)
    start = (datetime.date.today() + datetime.timedelta(days=10)).isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=15)).isoformat()

    resp = client.post(
        "/packages",
        json={
            "package_name": "Manali Trip",
            "destination_id": dest_id,
            "duration_days": 5,
            "base_price": 10000,
            "max_capacity": 10,
            "start_date": start,
            "end_date": end,
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["available_slots"] == 10
    assert body["status"] == "Draft"


def test_end_date_must_be_after_start_date(client, admin_auth_headers):
    dest_id = _make_destination(client, admin_auth_headers)
    resp = client.post(
        "/packages",
        json={
            "package_name": "Bad Trip",
            "destination_id": dest_id,
            "duration_days": 5,
            "base_price": 10000,
            "max_capacity": 10,
            "start_date": "2026-05-10",
            "end_date": "2026-05-01",
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 422


def test_capacity_must_be_positive(client, admin_auth_headers):
    dest_id = _make_destination(client, admin_auth_headers)
    resp = client.post(
        "/packages",
        json={
            "package_name": "Zero Cap Trip",
            "destination_id": dest_id,
            "duration_days": 5,
            "base_price": 10000,
            "max_capacity": 0,
            "start_date": "2026-05-01",
            "end_date": "2026-05-10",
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 422


def test_nonexistent_destination_rejected(client, admin_auth_headers):
    resp = client.post(
        "/packages",
        json={
            "package_name": "Ghost Trip",
            "destination_id": 999,
            "duration_days": 5,
            "base_price": 10000,
            "max_capacity": 5,
            "start_date": "2026-05-01",
            "end_date": "2026-05-10",
        },
        headers=admin_auth_headers,
    )
    assert resp.status_code == 404


def test_filter_packages_by_price_range(client, admin_auth_headers):
    dest_id = _make_destination(client, admin_auth_headers)
    for name, price in [("Cheap", 1000), ("Mid", 5000), ("Expensive", 20000)]:
        client.post(
            "/packages",
            json={
                "package_name": name,
                "destination_id": dest_id,
                "duration_days": 3,
                "base_price": price,
                "max_capacity": 5,
                "start_date": "2026-05-01",
                "end_date": "2026-05-05",
            },
            headers=admin_auth_headers,
        )

    resp = client.get("/packages?min_price=2000&max_price=10000")
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["package_name"] == "Mid"
