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


def test_company_dedupe_matches_normalized_name_across_sources():
    ident = add_company("Seven Seafood & Grill", "", source="openstreetmap")
    assert find_company_duplicate("", "", "Seven Seafood and Grill")["id"] == ident
    assert find_company_duplicate("", "", "Seven Seafood & Grill")["id"] == ident
    assert add_company("Seven Seafood & Grill", "", source="google_maps") == ident
    assert len([x for x in list_companies(100) if x["name"] == "Seven Seafood & Grill"]) == 1


def test_google_maps_search_link_available_without_api_key(monkeypatch):
    from openprospect.discovery import discover_google_maps
    monkeypatch.delenv("ZERO_HAWK_GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    result = discover_google_maps("Nairobi, Kenya", "restaurant", 10)
    assert result["configured"] is False
    assert "google.com/maps/search" in result["maps_url"]
    assert result["results"] == []


def test_google_maps_discovery_page_offers_free_search_and_manual_save():
    client = _client()
    page = client.get("/discover/google")
    assert page.status_code == 200
    assert "No Google Cloud account, API key or bank card" in page.text
    response = client.post(
        "/discover/google",
        data={"city": "Nairobi, Kenya", "category": "restaurant"},
    )
    assert response.status_code == 200
    assert "google.com/maps/search" in response.text
    assert "google.com/search" in response.text


def test_google_maps_manual_save_deduplicates_business():
    client = _client()
    data = {
        "name": "Free Maps Test Cafe",
        "website": "https://freemapstest.example",
        "phone": "0712345678",
        "email": "",
        "location": "Nairobi, Kenya",
        "source_url": "https://www.google.com/maps/search/?api=1&query=Free+Maps+Test+Cafe",
    }
    first = client.post("/discover/google/save", data=data)
    second = client.post("/discover/google/save", data=data)
    assert first.status_code == 200 and "Business saved" in first.text
    assert second.status_code == 200 and "Already saved" in second.text


def test_google_maps_search_never_calls_paid_places_api(monkeypatch):
    from openprospect.discovery import discover_google_maps
    monkeypatch.setenv("ZERO_HAWK_GOOGLE_MAPS_API_KEY", "should-not-be-used")
    result = discover_google_maps("Nairobi, Kenya", "restaurant", 10)
    assert result["configured"] is False
    assert result["results"] == []
    assert "no API key" in result["message"].lower()
    assert "google.com/maps/search" in result["maps_url"]



def test_google_maps_routes_are_registered_once_for_free_mode():
    routes = [
        route for route in app.routes
        if getattr(route, "path", None) == "/discover/google"
    ]
    assert sum("GET" in getattr(route, "methods", set()) for route in routes) == 1
    assert sum("POST" in getattr(route, "methods", set()) for route in routes) == 1
