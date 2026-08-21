import datetime


def _setup_confirmed_booking(client, headers, days_until_tour, base_price=1000, travelers=1):
    dest = client.post("/destinations", json={"name": "Manali", "country": "India"}, headers=headers).json()
    start = (datetime.date.today() + datetime.timedelta(days=days_until_tour)).isoformat()
    end = (datetime.date.today() + datetime.timedelta(days=days_until_tour + 5)).isoformat()
    pkg = client.post(
        "/packages",
        json={
            "package_name": "Trip",
            "destination_id": dest["id"],
            "duration_days": 5,
            "base_price": base_price,
            "max_capacity": 10,
            "start_date": start,
            "end_date": end,
            "status": "Draft",
        },
        headers=headers,
    ).json()
    client.put(f"/packages/{pkg['id']}", json={"status": "Published"}, headers=headers)

    cust = client.post(
        "/customers",
        json={"name": "Cust", "email": f"cust{days_until_tour}@test.com", "phone": "1234567890"},
        headers=headers,
    ).json()

    booking = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": travelers},
        headers=headers,
    ).json()

    client.post(
        f"/payments/{booking['id']}",
        json={"amount": booking["total_amount"], "payment_method": "UPI", "transaction_id": f"TXN-{days_until_tour}-{travelers}"},
        headers=headers,
    )
    return booking, pkg


def test_refund_90_percent_when_15_plus_days_out(client, admin_auth_headers):
    booking, _ = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=20, base_price=1000)
    resp = client.post(f"/bookings/{booking['id']}/cancel", json={"reason": "test"}, headers=admin_auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["refund_percentage"] == 90.0
    assert body["refund_amount"] == 900.0  # 90% of 1000


def test_refund_70_percent_for_7_to_14_days(client, admin_auth_headers):
    booking, _ = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=10, base_price=1000)
    resp = client.post(f"/bookings/{booking['id']}/cancel", json={}, headers=admin_auth_headers)
    assert resp.json()["refund_percentage"] == 70.0
    assert resp.json()["refund_amount"] == 700.0


def test_refund_40_percent_for_2_to_6_days(client, admin_auth_headers):
    booking, _ = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=4, base_price=1000)
    resp = client.post(f"/bookings/{booking['id']}/cancel", json={}, headers=admin_auth_headers)
    assert resp.json()["refund_percentage"] == 40.0
    assert resp.json()["refund_amount"] == 400.0


def test_no_refund_under_2_days(client, admin_auth_headers):
    booking, _ = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=1, base_price=1000)
    resp = client.post(f"/bookings/{booking['id']}/cancel", json={}, headers=admin_auth_headers)
    assert resp.json()["refund_percentage"] == 0.0
    assert resp.json()["refund_amount"] == 0.0


def test_cancellation_restores_package_slots(client, admin_auth_headers):
    booking, pkg = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=20, travelers=3)
    before = client.get(f"/packages/{pkg['id']}", headers=admin_auth_headers).json()
    assert before["available_slots"] == 7  # 10 - 3

    client.post(f"/bookings/{booking['id']}/cancel", json={}, headers=admin_auth_headers)

    after = client.get(f"/packages/{pkg['id']}", headers=admin_auth_headers).json()
    assert after["available_slots"] == 10


def test_cannot_cancel_twice(client, admin_auth_headers):
    booking, _ = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=20)
    client.post(f"/bookings/{booking['id']}/cancel", json={}, headers=admin_auth_headers)
    second = client.post(f"/bookings/{booking['id']}/cancel", json={}, headers=admin_auth_headers)
    assert second.status_code == 400


def test_duplicate_transaction_id_rejected(client, admin_auth_headers):
    booking, _ = _setup_confirmed_booking(client, admin_auth_headers, days_until_tour=20, base_price=500)
    # attempt a second payment reusing the same transaction_id used in setup
    resp = client.post(
        f"/payments/{booking['id']}",
        json={"amount": 100, "payment_method": "Card", "transaction_id": "TXN-20-1"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 409


def test_payment_cannot_exceed_booking_amount(client, admin_auth_headers):
    dest = client.post("/destinations", json={"name": "Goa", "country": "India"}, headers=admin_auth_headers).json()
    pkg = client.post(
        "/packages",
        json={
            "package_name": "Goa Trip",
            "destination_id": dest["id"],
            "duration_days": 3,
            "base_price": 1000,
            "max_capacity": 5,
            "start_date": "2026-12-01",
            "end_date": "2026-12-04",
        },
        headers=admin_auth_headers,
    ).json()
    client.put(f"/packages/{pkg['id']}", json={"status": "Published"}, headers=admin_auth_headers)
    cust = client.post(
        "/customers", json={"name": "Test Customer", "email": "c1@test.com", "phone": "9990001111"}, headers=admin_auth_headers
    ).json()
    booking = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 1},
        headers=admin_auth_headers,
    ).json()

    resp = client.post(
        f"/payments/{booking['id']}",
        json={"amount": booking["total_amount"] + 500, "payment_method": "UPI", "transaction_id": "TXN-OVER"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400
