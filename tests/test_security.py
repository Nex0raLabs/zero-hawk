import os
import tempfile

os.environ["OPENPROSPECT_HOME"] = tempfile.mkdtemp(prefix="openprospect-security-test-")

from fastapi.testclient import TestClient
from openprospect.app import app
from openprospect.security import get_dashboard_token


def test_dashboard_requires_private_token():
    client = TestClient(app, base_url="http://127.0.0.1")
    response = client.get("/")
    assert response.status_code == 200
    assert "Private local dashboard" in response.text
    assert client.post("/api/companies", json={"name": "Blocked"}).status_code == 401


def test_dashboard_token_exchange_sets_http_only_cookie():
    client = TestClient(app, base_url="http://127.0.0.1")
    response = client.post("/auth/exchange", json={"token": get_dashboard_token()})
    assert response.status_code == 200
    cookie = response.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert client.get("/").status_code == 200
    assert client.post("/api/companies", json={"name": "Allowed"}).status_code == 200


def test_dashboard_rejects_wrong_token_and_non_loopback_host():
    client = TestClient(app, base_url="http://127.0.0.1")
    assert client.post("/auth/exchange", json={"token": "wrong"}).status_code == 401
    assert client.get("/", headers={"host": "example.com"}).status_code == 403
