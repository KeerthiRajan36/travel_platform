from app.models.booking import Booking, BookingStatus


def _complete_booking_directly(db_session, booking_id: int):
    """Test helper: bypass the normal lifecycle to mark a booking Completed,
    since there is no dedicated 'complete tour' endpoint in this API surface
    (tours complete automatically once their end_date passes, in a real
    scheduled job). Uses the same test-scoped session the TestClient is
    wired to, via dependency override, so the change is visible to the API."""
    booking = db_session.get(Booking, booking_id)
    booking.booking_status = BookingStatus.COMPLETED
    db_session.add(booking)
    db_session.commit()


def _setup_booking(client, headers):
    dest = client.post("/destinations", json={"name": "Manali", "country": "India"}, headers=headers).json()
    pkg = client.post(
        "/packages",
        json={
            "package_name": "Trip",
            "destination_id": dest["id"],
            "duration_days": 5,
            "base_price": 1000,
            "max_capacity": 10,
            "start_date": "2026-12-01",
            "end_date": "2026-12-06",
        },
        headers=headers,
    ).json()
    client.put(f"/packages/{pkg['id']}", json={"status": "Published"}, headers=headers)
    cust = client.post(
        "/customers", json={"name": "Test Customer", "email": "review_cust@test.com", "phone": "9990001111"}, headers=headers
    ).json()
    booking = client.post(
        "/bookings",
        json={"customer_id": cust["id"], "package_id": pkg["id"], "number_of_travelers": 1},
        headers=headers,
    ).json()
    return booking, cust, pkg


def test_cannot_review_non_completed_booking(client, admin_auth_headers):
    booking, cust, _ = _setup_booking(client, admin_auth_headers)
    resp = client.post(
        f"/reviews?customer_id={cust['id']}",
        json={"booking_id": booking["id"], "rating": 5},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 400


def test_review_completed_booking_succeeds(client, admin_auth_headers, db_session):
    booking, cust, pkg = _setup_booking(client, admin_auth_headers)
    _complete_booking_directly(db_session, booking["id"])

    resp = client.post(
        f"/reviews?customer_id={cust['id']}",
        json={"booking_id": booking["id"], "rating": 4, "review_text": "Great!"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["rating"] == 4

    listing = client.get(f"/packages/{pkg['id']}/reviews")
    assert len(listing.json()) == 1


def test_one_review_per_booking(client, admin_auth_headers, db_session):
    booking, cust, _ = _setup_booking(client, admin_auth_headers)
    _complete_booking_directly(db_session, booking["id"])

    first = client.post(
        f"/reviews?customer_id={cust['id']}",
        json={"booking_id": booking["id"], "rating": 5},
        headers=admin_auth_headers,
    )
    assert first.status_code == 201

    second = client.post(
        f"/reviews?customer_id={cust['id']}",
        json={"booking_id": booking["id"], "rating": 3},
        headers=admin_auth_headers,
    )
    assert second.status_code == 409


def test_rating_must_be_between_1_and_5(client, admin_auth_headers, db_session):
    booking, cust, _ = _setup_booking(client, admin_auth_headers)
    _complete_booking_directly(db_session, booking["id"])

    resp = client.post(
        f"/reviews?customer_id={cust['id']}",
        json={"booking_id": booking["id"], "rating": 7},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 422
