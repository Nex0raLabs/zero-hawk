import datetime as dt
import pytest
from fastapi.testclient import TestClient
from openprospect.phones import normalize_phone, is_mobile_ke
from openprospect.lint import lint_draft
from openprospect import sendpolicy

@pytest.mark.parametrize("raw,want",[("0712 345 678","+254712345678"),("+254 712-345-678","+254712345678"),("254712345678","+254712345678"),
  ("712345678","+254712345678"),("020 2345678","+254202345678"),("+44 20 7946 0958","+442079460958"),("123",""),("","")])
def test_phone_e164(raw,want):
    assert normalize_phone(raw)==want

def test_mobile_detection():
    assert is_mobile_ke("+254712345678") and not is_mobile_ke("+254202345678")

def test_lint_blocks_problems():
    r=lint_draft("Hello","Hi {{first_name}}, click here! "+"word "*200,email_status="guess",banned=["synergy"])
    assert not r["ok"]
    t=" ".join(r["errors"])
    assert "merge tag" in t and "Too long" in t and "guess" in t

def test_lint_passes_clean():
    body="Hi Amina, I noticed your cafe takes bookings only by phone. We build simple online booking for small restaurants in Nairobi and could set one up this week. Would a short call on Thursday suit you?"
    assert lint_draft("Online booking for your cafe",body)["ok"]

def test_banned_phrase(monkeypatch):
    assert not lint_draft("Hi","We offer synergy to everyone in town today and want to talk soon about it please.",banned=["Synergy"])["ok"]

def test_office_hours():
    sat=dt.datetime(2026,11,28,9,0,tzinfo=dt.timezone.utc); thu=dt.datetime(2026,11,26,9,0,tzinfo=dt.timezone.utc)
    assert not sendpolicy.in_office_hours(sat) and sendpolicy.in_office_hours(thu)
    assert not sendpolicy.in_office_hours(dt.datetime(2026,11,26,22,0,tzinfo=dt.timezone.utc))

def test_kill_switch_blocks(monkeypatch,tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME",str(tmp_path)); monkeypatch.setenv("OPENPROSPECT_ENFORCE_OFFICE_HOURS","0")
    sendpolicy.check_send_allowed()
    sendpolicy.set_paused(True)
    with pytest.raises(RuntimeError,match="paused"): sendpolicy.check_send_allowed()

def test_dashboard_pages_render(monkeypatch,tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME",str(tmp_path))
    from openprospect.app import app
    c=TestClient(app,base_url="http://127.0.0.1")
    from openprospect.security import get_dashboard_token
    assert c.post("/auth/exchange",json={"token":get_dashboard_token()}).status_code==200
    for path in ["/","/usage","/help","/controls","/drafts","/companies","/settings","/manifest.webmanifest","/sw.js","/api/status"]:
        r=c.get(path); assert r.status_code==200,(path,r.status_code,r.text[:200])
    assert "Ctrl K" in c.get("/").text


def test_zero_hawk_environment_preferred_with_legacy_fallback(monkeypatch):
    from openprospect.config import env_value
    monkeypatch.setenv("OPENPROSPECT_PORT", "5001")
    assert env_value("ZERO_HAWK_PORT", "5555") == "5001"
    monkeypatch.setenv("ZERO_HAWK_PORT", "6001")
    assert env_value("OPENPROSPECT_PORT", "5555") == "6001"


def test_autopilot_settings_persist_and_enforce_minimum(monkeypatch, tmp_path):
    from openprospect.automation import loop_status, _write_settings, pause_loop
    monkeypatch.setenv("ZERO_HAWK_HOME", str(tmp_path))
    _write_settings(enabled=False, interval_seconds=60, batch_size=99)
    state = loop_status()
    assert state["enabled"] is False
    assert state["interval_seconds"] == 900
    assert state["batch_size"] == 25
    pause_loop()


def test_autopilot_controls_toggle(monkeypatch, tmp_path):
    monkeypatch.setenv("ZERO_HAWK_HOME", str(tmp_path))
    from openprospect.app import app
    from openprospect.security import get_dashboard_token
    from openprospect.automation import pause_loop, loop_status
    client = TestClient(app, base_url="http://127.0.0.1")
    assert client.post("/auth/exchange", json={"token": get_dashboard_token()}).status_code == 200
    assert client.post("/controls/start", follow_redirects=False).status_code == 303
    assert loop_status()["enabled"] is True
    page = client.get("/controls")
    assert "Turn Autopilot OFF" in page.text and "15 min" in page.text
    assert client.post("/controls/pause", follow_redirects=False).status_code == 303
    assert loop_status()["enabled"] is False
    pause_loop()


def test_saved_autopilot_resumes_on_app_startup(monkeypatch, tmp_path):
    monkeypatch.setenv("ZERO_HAWK_HOME", str(tmp_path))
    from openprospect.automation import _write_settings, loop_status, pause_loop
    from openprospect.app import app
    _write_settings(enabled=True, interval_seconds=900, batch_size=1)
    with TestClient(app, base_url="http://127.0.0.1"):
        assert loop_status()["running"] is True
    assert loop_status()["enabled"] is False  # worker stopped with process shutdown
    assert loop_status()["running"] is False
    assert _read_autopilot_preference(tmp_path) is True
    pause_loop()


def _read_autopilot_preference(path):
    import json
    return json.loads((path / "autopilot.json").read_text("utf-8"))["enabled"]
