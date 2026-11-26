from types import SimpleNamespace

import dns.resolver

from openprospect import verification


def test_email_syntax_and_disposable_domain_checks():
    invalid = verification.verify_email("not-an-email", smtp_probe=False)
    assert invalid["status"] == "invalid"
    assert not invalid["syntax_valid"]

    disposable = verification.verify_email("person@mailinator.com", smtp_probe=False)
    assert disposable["status"] == "invalid"
    assert disposable["disposable"] is True


def test_email_verified_only_when_mx_and_non_catchall_smtp_accept(monkeypatch):
    monkeypatch.setattr(
        dns.resolver, "resolve",
        lambda domain, record_type, lifetime: [SimpleNamespace(preference=10, exchange="mx.example.test.")],
    )
    monkeypatch.setattr(verification, "_smtp_check", lambda host, address: {
        "target_accepted": True, "target_code": 250, "target_message": "accepted",
        "catch_all": False, "catch_all_code": 550, "catch_all_message": "unknown recipient",
    })
    result = verification.verify_email("info@example.test")
    assert result["status"] == "verified"
    assert result["role_account"] is True
    assert verification.is_deliverable(result)


def test_catchall_and_guessed_addresses_never_become_deliverable(monkeypatch):
    monkeypatch.setattr(
        dns.resolver, "resolve",
        lambda domain, record_type, lifetime: [SimpleNamespace(preference=10, exchange="mx.example.test.")],
    )
    monkeypatch.setattr(verification, "_smtp_check", lambda host, address: {
        "target_accepted": True, "target_code": 250, "target_message": "accepted",
        "catch_all": True, "catch_all_code": 250, "catch_all_message": "accepted",
    })
    catchall = verification.verify_email("alex@example.test")
    assert catchall["status"] == "risky"
    assert not verification.is_deliverable(catchall)

    guess = verification.verify_email("alex@example.test", is_guess=True)
    assert guess["status"] == "guess"
    assert not verification.is_deliverable(guess)


def test_email_pattern_learning_and_guess_labels():
    pattern = verification.learn_email_pattern([
        {"name": "Nora Vale", "email": "nora.vale@example.test"},
        {"name": "Alex Kim", "email": "alex.kim@example.test"},
    ])
    assert pattern == "first.last"
    guess = verification.guess_email("Jamie", "Fox", "example.test", pattern)
    assert guess == {
        "address": "jamie.fox@example.test",
        "status": "guess",
        "pattern": "first.last",
    }


def test_contact_verify_action_persists_result(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    from fastapi.testclient import TestClient
    from openprospect import app as app_module
    from openprospect.db import add_company, add_contact, connect
    from openprospect.security import get_dashboard_token

    company_id = add_company("Mail Test Co")
    contact_id = add_contact(company_id, name="Test Person", email="person@example.test")
    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    client.post("/auth/exchange", json={"token": get_dashboard_token()})
    monkeypatch.setattr(app_module, "verify_email", lambda address, is_guess=False: {
        "address": address, "status": "verified", "reason": "SMTP accepted recipient and rejected random address.",
        "mx_found": True, "role_account": False, "catch_all": False,
    })
    response = client.post(f"/contact/{contact_id}/verify")
    assert response.status_code == 200
    assert "verified" in response.text
    with connect() as conn:
        row = conn.execute("SELECT email_status FROM contacts WHERE id=?", (contact_id,)).fetchone()
    assert row["email_status"] == "verified"


def test_manual_import_cannot_mark_contact_verified(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    from openprospect.db import add_company, add_contact, connect
    company_id = add_company("Manual Status Co")
    contact_id = add_contact(company_id, email="person@example.test", email_status="verified")
    with connect() as conn:
        row = conn.execute("SELECT email_status FROM contacts WHERE id=?", (contact_id,)).fetchone()
    assert row["email_status"] == "unverified"


def test_generated_guess_only_promotes_after_non_catchall_smtp(monkeypatch):
    monkeypatch.setattr(
        dns.resolver, "resolve",
        lambda domain, record_type, lifetime: [SimpleNamespace(preference=10, exchange="mx.example.test.")],
    )
    monkeypatch.setattr(verification, "_smtp_check", lambda host, address: {
        "target_accepted": True, "target_code": 250, "target_message": "accepted",
        "catch_all": False, "catch_all_code": 550, "catch_all_message": "unknown recipient",
    })
    result = verification.verify_email("jamie.fox@example.test", is_guess=True)
    assert result["status"] == "verified"
    assert verification.is_deliverable(result)


def test_contact_guess_route_learns_published_company_pattern(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME", str(tmp_path))
    from fastapi.testclient import TestClient
    from openprospect import app as app_module
    from openprospect.db import add_company, add_contact, connect
    from openprospect.security import get_dashboard_token

    company_id = add_company("Pattern Co", "https://pattern.example")
    add_contact(company_id, name="Alice Smith", email="alice.smith@pattern.example", source_url="https://pattern.example/team")
    add_contact(company_id, name="Bob Jones", email="bob.jones@pattern.example", source_url="https://pattern.example/team")
    target_id = add_contact(company_id, name="Jamie Fox")
    client = TestClient(app_module.app, base_url="http://127.0.0.1")
    client.post("/auth/exchange", json={"token": get_dashboard_token()})
    response = client.post(f"/contact/{target_id}/guess")
    assert response.status_code == 200
    with connect() as conn:
        row = conn.execute("SELECT email,email_status FROM contacts WHERE id=?", (target_id,)).fetchone()
    assert row["email"] == "jamie.fox@pattern.example"
    assert row["email_status"] == "guess"
