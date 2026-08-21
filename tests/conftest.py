import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.utils import rate_limit as rate_limit_module

# --- Isolated in-memory SQLite for every test run --------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """The rate limiter keeps global in-memory state keyed by client IP.
    TestClient always presents as the same host, so without a reset the
    limiter would trip partway through an unrelated test after enough
    cumulative requests across the whole suite."""
    rate_limit_module._hits.clear()
    yield
    rate_limit_module._hits.clear()


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def register_and_login(client: TestClient, role: str = "super_admin", email: str = "admin@test.com") -> str:
    client.post(
        "/auth/register",
        json={"name": "Test User", "email": email, "password": "TestPass123", "role": role},
    )
    resp = client.post("/auth/login", json={"email": email, "password": "TestPass123"})
    return resp.json()["access_token"]


@pytest.fixture()
def admin_token(client):
    return register_and_login(client, role="super_admin", email="admin@test.com")


@pytest.fixture()
def admin_auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
