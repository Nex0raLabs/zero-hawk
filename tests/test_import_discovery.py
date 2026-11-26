import os
import tempfile

os.environ["OPENPROSPECT_HOME"] = tempfile.mkdtemp(prefix="openprospect-import-test-")

from fastapi.testclient import TestClient
from openprospect.app import app
from openprospect.db import add_company, find_company_duplicate, list_companies
from openprospect.security import get_dashboard_token


def _client():
    client = TestClient(app, base_url="http://127.0.0.1")
    client.post("/auth/exchange", json={"token": get_dashboard_token()})
    return client


def test_company_dedupe_normalizes_domain_and_kenyan_phone():
    add_company("Demo Restaurant", "https://www.demo.example", phone="0712345678")
    assert find_company_duplicate("http://demo.example/menu", "")["id"]
    assert find_company_duplicate("", "+254 712 345 678")["id"]


def test_company_csv_import_skips_duplicate_domain():
    client = _client()
    content = b"""name,website,phone,industry,location
First Cafe,https://first.example,0711111111,cafe,Nairobi
Duplicate Cafe,https://www.first.example,0722222222,cafe,Nairobi
"""
    response = client.post(
        "/import/companies.csv",
        files={"file": ("companies.csv", content, "text/csv")},
    )
    assert response.status_code == 200
    assert "Imported 1; skipped 1" in response.text
    assert any(row["name"] == "First Cafe" for row in list_companies(100))
