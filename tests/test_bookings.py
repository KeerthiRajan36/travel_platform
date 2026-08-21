def _setup_package(client, headers, max_capacity=5, status="Published", base_price=10000):
    dest = client.post("/destinations", json={"name": "Manali", "country": "India"}, headers=headers).json()
    pkg = client.post(
        "/packages",
        json={
            "package_name": "Manali Trip",
            "destination_id": dest["id"],
            "duration_days": 5,
            "base_price": base_price,
            "max_capacity": max_capacity,
            "start_date": "2026-12-01",
            "end_date": "2026-12-06",
            "status": "Draft",
        },
        headers=headers,
    ).json()
    if status != "Draft":
        client.put(f"/packages/{pkg['id']}", json={"status": status}, headers=headers)
        pkg["status"] = status
    return pkg


def _setup_customer(client, headers, email="cust@test.com"):
    return client.post(
        "/customers",
        json={"name": "Test Customer", "email": email, "phone": "1234567890"},
        headers=headers,
    ).json()


def test_booking_total_amount_calculation(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, status="Published", base_price=1000)
    cust = _setup_customer(client, admin_auth_headers)

    resp = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 2, "tax": 100, "discount": 50},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["base_amount"] == 2000.0
    assert body["total_amount"] == 2050.0  # 2000 + 100 - 50
    assert body["booking_status"] == "Pending"


def test_cannot_book_draft_package(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, status="Draft")
    cust = _setup_customer(client, admin_auth_headers)

    resp = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 1},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400


def test_cannot_book_cancelled_package(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, status="Published")
    client.put(f"/packages/{pkg['id']}", json={"status": "Cancelled"}, headers=admin_auth_headers)
    cust = _setup_customer(client, admin_auth_headers)

    resp = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 1},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400


def test_prevent_overbooking(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, max_capacity=3, status="Published")
    cust = _setup_customer(client, admin_auth_headers)

    resp = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 4},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 409


def test_duplicate_active_booking_rejected(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, max_capacity=10, status="Published")
    cust = _setup_customer(client, admin_auth_headers)

    first = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 1},
        headers=admin_auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 1},
        headers=admin_auth_headers,
    )
    assert second.status_code == 409


def test_payment_confirms_booking_and_reduces_slots(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, max_capacity=5, status="Published", base_price=1000)
    cust = _setup_customer(client, admin_auth_headers)

    booking = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 2},
        headers=admin_auth_headers,
    ).json()

    pay = client.post(
        f"/payments/{booking['id']}",
        json={"amount": booking["total_amount"], "payment_method": "UPI", "transaction_id": "TXN-100"},
        headers=admin_auth_headers,
    )
    assert pay.status_code == 201
    assert pay.json()["payment_status"] == "Success"

    booking_after = client.get(f"/bookings/{booking['id']}", headers=admin_auth_headers).json()
    assert booking_after["booking_status"] == "Confirmed"

    package_after = client.get(f"/packages/{pkg['id']}", headers=admin_auth_headers).json()
    assert package_after["available_slots"] == 3


def test_simple_cancel_restores_slots(client, admin_auth_headers):
    pkg = _setup_package(client, admin_auth_headers, max_capacity=5, status="Published", base_price=1000)
    cust = _setup_customer(client, admin_auth_headers)

    booking = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 2},
        headers=admin_auth_headers,
    ).json()
    client.post(
        f"/payments/{booking['id']}",
        json={"amount": booking["total_amount"], "payment_method": "UPI", "transaction_id": "TXN-200"},
        headers=admin_auth_headers,
    )

    cancel = client.put(f"/bookings/{booking['id']}/cancel", headers=admin_auth_headers)
    assert cancel.status_code == 200
    assert cancel.json()["booking_status"] == "Cancelled"

    package_after = client.get(f"/packages/{pkg['id']}", headers=admin_auth_headers).json()
    assert package_after["available_slots"] == 5
