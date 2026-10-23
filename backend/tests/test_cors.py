import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_cors_preflight_localhost_allowed():
    """Verify OPTIONS preflight request from http://localhost:5173 is accepted with CORS headers."""
    response = client.options(
        "/api/v1/recommend",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_127_0_0_1_allowed():
    """Verify OPTIONS preflight request from http://127.0.0.1:5173 is accepted with CORS headers."""
    response = client.options(
        "/api/v1/recommend",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_unapproved_origin_rejected():
    """Verify requests or preflights from unapproved origins do not receive allow-origin header."""
    response = client.options(
        "/api/v1/recommend",
        headers={
            "Origin": "http://malicious-site.example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # FastAPI CORSMiddleware responds with 400 or without access-control-allow-origin for unauthorized origins
    assert response.headers.get("access-control-allow-origin") is None or response.status_code == 400


def test_cors_simple_get_health_allowed_origins():
    """Verify actual GET request headers include Access-Control-Allow-Origin for both origins."""
    resp1 = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp1.status_code == 200
    assert resp1.headers.get("access-control-allow-origin") == "http://localhost:5173"

    resp2 = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert resp2.status_code == 200
    assert resp2.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"

    resp3 = client.get("/health", headers={"Origin": "http://untrusted-site.com"})
    assert resp3.status_code == 200
    assert resp3.headers.get("access-control-allow-origin") is None
