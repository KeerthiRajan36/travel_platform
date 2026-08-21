def test_register_creates_user(client):
    resp = client.post(
        "/auth/register",
        json={"name": "Alice", "email": "alice@test.com", "password": "SecurePass1", "role": "customer"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "alice@test.com"
    assert body["role"] == "customer"
    assert "password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"name": "Alice", "email": "dup@test.com", "password": "SecurePass1", "role": "customer"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_success_and_failure(client):
    client.post(
        "/auth/register",
        json={"name": "Bob", "email": "bob@test.com", "password": "SecurePass1", "role": "customer"},
    )
    good = client.post("/auth/login", json={"email": "bob@test.com", "password": "SecurePass1"})
    assert good.status_code == 200
    assert "access_token" in good.json()
    assert "refresh_token" in good.json()

    bad = client.post("/auth/login", json={"email": "bob@test.com", "password": "WrongPassword"})
    assert bad.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, admin_auth_headers):
    resp = client.get("/auth/me", headers=admin_auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@test.com"


def test_change_password_flow(client, admin_auth_headers):
    resp = client.put(
        "/auth/change-password",
        json={"old_password": "TestPass123", "new_password": "NewPass456"},
        headers=admin_auth_headers,
    )
    assert resp.status_code == 200

    # Old password should no longer work.
    old_login = client.post("/auth/login", json={"email": "admin@test.com", "password": "TestPass123"})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", json={"email": "admin@test.com", "password": "NewPass456"})
    assert new_login.status_code == 200


def test_refresh_token_flow(client, admin_token, admin_auth_headers):
    login_resp = client.post("/auth/login", json={"email": "admin@test.com", "password": "TestPass123"})
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_role_based_access_control(client):
    # A customer-role user should not be able to create a destination.
    client.post(
        "/auth/register",
        json={"name": "Cust", "email": "cust@test.com", "password": "SecurePass1", "role": "customer"},
    )
    login = client.post("/auth/login", json={"email": "cust@test.com", "password": "SecurePass1"})
    token = login.json()["access_token"]

    resp = client.post(
        "/destinations",
        json={"name": "Goa", "country": "India"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
