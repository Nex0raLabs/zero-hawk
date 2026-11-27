import os
import tempfile

from openprospect import profiling


def test_profile_detects_buying_signals_from_company_pages(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    pages = {
        "https://sample.example/": (
            "https://sample.example/",
            '<html><head><title>Sample Restaurant</title><meta name="description" content="Local dining"></head>'
            '<body><p>Copyright 2020 Sample Restaurant. We serve fresh meals.</p>'
            '<a href="/contact">Contact</a><a href="/careers">Careers</a></body></html>',
        ),
        "https://sample.example/contact": (
            "https://sample.example/contact",
            '<html><body>Contact us at hello@sample.example or call +254 712 345 678</body></html>',
        ),
        "https://sample.example/careers": (
            "https://sample.example/careers",
            '<html><body>Join our team. Hiring now.</body></html>',
        ),
    }
    monkeypatch.setattr(profiling, "_allowed_by_robots", lambda url: True)
    monkeypatch.setattr(profiling, "_fetch", lambda url: pages[url])
    monkeypatch.setattr(profiling.time, "sleep", lambda seconds: None)

    result = profiling.profile_website("https://sample.example/")
    codes = {signal["code"] for signal in result["signals"]}
    assert result["title"] == "Sample Restaurant"
    assert "hello@sample.example" in result["emails"]
    assert "NO_MOBILE_VIEWPORT" in codes
    assert "NO_SCHEMA_MARKUP" in codes
    assert "NO_WHATSAPP_BUTTON" in codes
    assert "NO_ONLINE_BOOKING" in codes
    assert "HIRING_PAGE" in codes
    assert result["score"] > 0
    assert all(signal["evidence_url"] for signal in result["signals"])


def test_custom_signal_rules_are_editable_and_applied(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    profiling.save_signal_rules({
        "_custom_rules": [{
            "code": "HAS_VEGAN_MENU",
            "label": "Publishes a vegan menu",
            "keywords": ["vegan menu"],
            "weight": 7,
            "enabled": True,
        }]
    })
    rules = profiling.load_signal_rules()
    assert rules["_custom_rules"][0]["code"] == "HAS_VEGAN_MENU"

    monkeypatch.setattr(profiling, "_allowed_by_robots", lambda url: True)
    monkeypatch.setattr(profiling, "_fetch", lambda url: (
        "https://sample.example/",
        '<html><head><title>Sample</title><meta name="viewport" content="width=device-width"></head>'
        '<body>See our vegan menu today. <a href="/contact">Contact</a></body></html>',
    ))
    result = profiling.profile_website("https://sample.example/")
    assert "HAS_VEGAN_MENU" in {signal["code"] for signal in result["signals"]}


def test_signal_observations_keep_company_and_evidence(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    from openprospect.db import add_company, save_company_observations, list_observations
    company_id = add_company("Evidence Cafe", "https://evidence.example")
    save_company_observations(company_id, [{
        "code": "NO_ONLINE_BOOKING",
        "label": "No online booking",
        "weight": 12,
        "confidence": 0.75,
        "evidence_url": "https://evidence.example/",
    }])
    rows = list_observations()
    assert rows[0]["company_name"] == "Evidence Cafe"
    assert rows[0]["evidence_url"] == "https://evidence.example/"
    assert rows[0]["confidence"] == 0.75



def test_profile_recognizes_contact_anchor_text_without_contact_url(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    monkeypatch.setattr(profiling, "_allowed_by_robots", lambda url: True)
    monkeypatch.setattr(profiling, "_fetch", lambda url: (
        "https://sample.example/",
        '<html><head><title>Sample Restaurant</title><meta name="viewport" content="width=device-width"></head>'
        '<body><nav><a href="#footer">Contact Us</a></nav><p>Welcome.</p></body></html>',
    ))
    result = profiling.profile_website("https://sample.example/")
    assert "NO_CONTACT_PAGE" not in {signal["code"] for signal in result["signals"]}
