import json
import pytest

from openprospect import training


def test_training_extracts_public_company_facts():
    pages = [{
        "url": "https://example.com/",
        "title": "Example Studio",
        "text": "We build websites for restaurants and small businesses. Our team has served 50 clients. Plans start at KES 12,000. Contact hello@example.com for support.",
    }]
    result = training._extract_training(pages, "https://example.com/")
    assert result["company"] == "Example Studio"
    assert result["pricing"] == ["KES 12,000"]
    assert "restaurants" in result["buyers"]
    assert "hello@example.com" in result["emails_published"]
    assert result["icp"] == ""
    assert result["default_cta"]


def test_training_saves_and_edits_local_profile(tmp_path):
    training.train_website  # public entry point exists
    seed = training._extract_training([{"title": "Local Co", "text": "We serve local businesses."}], "https://example.com")
    (tmp_path / "company-training.json").write_text(json.dumps(seed), encoding="utf-8")
    saved = training.save_training({
        "icp": "Independent restaurants",
        "offer": "Website redesign",
        "banned_phrases": ["guaranteed results"],
        "signature": "Artcraft Studio",
        "language": "English",
        "default_cta": "Can we talk?",
    }, tmp_path)
    loaded = training.load_training(tmp_path)
    assert saved["icp"] == loaded["icp"] == "Independent restaurants"
    assert loaded["banned_phrases"] == ["guaranteed results"]
    assert loaded["offer"] == "Website redesign"


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "http://127.0.0.1/admin",
    "http://localhost/",
    "https://user:pass@example.com/",
])
def test_training_rejects_unsafe_url_forms(url):
    with pytest.raises(ValueError):
        training._public_http_url(url)


def test_training_requires_existing_profile_before_edit(tmp_path):
    with pytest.raises(ValueError):
        training.save_training({"icp": "restaurants"}, tmp_path)


def test_training_redirect_handler_rejects_private_destination():
    handler = training._PublicRedirectHandler()
    request = __import__("urllib.request", fromlist=["Request"]).Request("https://public.example/")
    with pytest.raises(ValueError, match="Private, loopback"):
        handler.redirect_request(
            request, None, 302, "Found", {}, "http://127.0.0.1/admin"
        )
