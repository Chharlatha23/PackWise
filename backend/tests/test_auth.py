import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db, get_user_db
from app.main import app
from app.models.user import User, PasswordReset
from app.services.auth_service import create_access_token, _OAUTH_STATES, verify_password

# Test in-memory database setup
TEST_DB_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_DB_ENGINE)
Base.metadata.create_all(bind=TEST_DB_ENGINE)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_user_db] = override_get_db
client = TestClient(app)


def test_google_login_generates_url_and_state():
    """Verify that /api/v1/auth/google/login generates a Google auth URL with CSRF state."""
    with patch("app.core.config.settings.GOOGLE_CLIENT_ID", "dummy_google_client_id"):
        response = client.get("/api/v1/auth/google/login")
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["authorization_url"]
        assert "dummy_google_client_id" in data["authorization_url"]
        assert data["state"] in _OAUTH_STATES


def test_google_callback_invalid_state_rejected():
    """Verify that an invalid or expired state token is rejected with CSRF failure redirect."""
    response = client.get("/api/v1/auth/google/callback?code=mock_code&state=non_existent_state", follow_redirects=False)
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "error=" in location
    assert "CSRF" in location or "state" in location.lower()


def test_google_callback_error_query_param_handled():
    """Verify that OAuth user cancellation or error returns gracefully with error parameter."""
    response = client.get("/api/v1/auth/google/callback?error=access_denied", follow_redirects=False)
    assert response.status_code in (302, 307)
    location = response.headers["location"]
    assert "access_denied" in location


def test_google_callback_success_creates_user_and_token():
    """Verify valid OAuth code exchange issues JWT token and redirects user to frontend."""
    from app.services.auth_service import generate_oauth_state
    valid_state = generate_oauth_state()

    mock_token_resp = MagicMock()
    mock_token_resp.status_code = 200
    mock_token_resp.json.return_value = {"access_token": "mock_google_access_token"}

    mock_userinfo_resp = MagicMock()
    mock_userinfo_resp.status_code = 200
    mock_userinfo_resp.json.return_value = {
        "sub": "google-user-12345",
        "email": "testpackwise@example.com",
        "email_verified": True,
        "name": "PackWise Tester",
        "picture": "https://example.com/avatar.jpg"
    }

    with patch("app.core.config.settings.GOOGLE_CLIENT_ID", "mock_id"), \
         patch("app.core.config.settings.GOOGLE_CLIENT_SECRET", "mock_secret"), \
         patch("httpx.AsyncClient.post", return_value=mock_token_resp), \
         patch("httpx.AsyncClient.get", return_value=mock_userinfo_resp), \
         patch("app.services.auth_service.send_welcome_email") as mock_welcome:

        response = client.get(
            f"/api/v1/auth/google/callback?code=valid_code&state={valid_state}",
            follow_redirects=False
        )
        assert response.status_code in (302, 307)
        location = response.headers["location"]
        assert "token=" in location

        # Verify user was saved in DB
        db = TestSessionLocal()
        user = db.query(User).filter(User.email == "testpackwise@example.com").first()
        assert user is not None
        assert user.google_id == "google-user-12345"
        assert user.name == "PackWise Tester"
        db.close()

        # Welcome email should be called for newly created user
        mock_welcome.assert_called_once_with("testpackwise@example.com", "PackWise Tester")


def test_registration_success_and_welcome_email():
    """Verify traditional email registration hashes password and triggers welcome email."""
    with patch("app.services.auth_service.send_welcome_email") as mock_welcome:
        reg_payload = {
            "name": "Alice Packaging",
            "email": "alice@foodpack.org",
            "password": "SecurePassword123!"
        }
        response = client.post("/api/v1/auth/register", json=reg_payload)
        assert response.status_code == 201
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "alice@foodpack.org"
        assert data["user"]["name"] == "Alice Packaging"

        # Verify password in DB is hashed and verify_password works
        db = TestSessionLocal()
        user = db.query(User).filter(User.email == "alice@foodpack.org").first()
        assert user is not None
        assert user.password_hash != "SecurePassword123!"
        assert verify_password("SecurePassword123!", user.password_hash)
        db.close()

        # Check welcome email was dispatched
        mock_welcome.assert_called_once_with("alice@foodpack.org", "Alice Packaging")


def test_registration_duplicate_email_rejected():
    """Verify registering an already existing email returns HTTP 400."""
    reg_payload = {
        "name": "Duplicate User",
        "email": "alice@foodpack.org",
        "password": "AnotherPassword456!"
    }
    response = client.post("/api/v1/auth/register", json=reg_payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_login_successful_with_password():
    """Verify login with correct email and password returns JWT token."""
    login_payload = {
        "email": "alice@foodpack.org",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@foodpack.org"


def test_login_invalid_password_returns_401():
    """Verify login with wrong password returns 401."""
    login_payload = {
        "email": "alice@foodpack.org",
        "password": "WrongPassword!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "incorrect password" in response.json()["detail"].lower()


def test_login_nonexistent_email_returns_401():
    """Verify login with non-existent email returns 401 advising registration."""
    login_payload = {
        "email": "nobody@foodpack.org",
        "password": "AnyPassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "no account found" in response.json()["detail"].lower()


def test_forgot_password_flow_and_reset():
    """Verify complete forgot-password and reset-password flow."""
    with patch("app.services.auth_service.send_password_reset_email") as mock_reset_email:
        # 1. Request reset
        response = client.post("/api/v1/auth/forgot-password", json={"email": "alice@foodpack.org"})
        assert response.status_code == 200
        assert mock_reset_email.called
        token_sent = mock_reset_email.call_args[0][1]
        assert token_sent is not None

        # 2. Reset password with valid token
        reset_resp = client.post("/api/v1/auth/reset-password", json={
            "token": token_sent,
            "new_password": "BrandNewPassword789!"
        })
        assert reset_resp.status_code == 200

        # 3. Old password fails, new password succeeds
        fail_login = client.post("/api/v1/auth/login", json={
            "email": "alice@foodpack.org",
            "password": "SecurePassword123!"
        })
        assert fail_login.status_code == 401

        succ_login = client.post("/api/v1/auth/login", json={
            "email": "alice@foodpack.org",
            "password": "BrandNewPassword789!"
        })
        assert succ_login.status_code == 200

        # 4. Same token cannot be reused
        reuse_resp = client.post("/api/v1/auth/reset-password", json={
            "token": token_sent,
            "new_password": "AnotherNewPassword!"
        })
        assert reuse_resp.status_code == 400


def test_protected_route_without_token_returns_401():
    """Verify that /api/v1/auth/me rejects unauthenticated requests."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_protected_route_with_valid_token_returns_user():
    """Verify that /api/v1/auth/me returns the user profile when supplied a valid JWT."""
    db = TestSessionLocal()
    user = User(
        email="jwtuser@example.com",
        name="JWT User",
        google_id="jwt-123",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    db.close()

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "jwtuser@example.com"
    assert data["name"] == "JWT User"


def test_logout_endpoint():
    """Verify that /api/v1/auth/logout succeeds with an authenticated user."""
    db = TestSessionLocal()
    user = User(email="logoutuser@example.com", name="Logout User", is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "email": user.email, "name": user.name})
    db.close()

    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
