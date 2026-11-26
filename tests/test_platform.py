import os
from openprospect.compliance import privacy_checklist, dns_report
from openprospect.conversations import ensure_schema, add_message, list_conversations
from openprospect.messaging import email_status, imap_status
from openprospect.automation import loop_status, pause_loop

def test_unified_conversation_storage(monkeypatch,tmp_path):
    monkeypatch.setenv("OPENPROSPECT_HOME",str(tmp_path))
    ensure_schema()
    add_message("email","<one@example.test>","one@example.test","Hello","Interested","inbound")
    add_message("email","<two@example.test>","one@example.test","Re: Hello","Thanks","inbound")
    rows=list_conversations()
    assert rows[0]["channel"]=="email"
    assert rows[0]["contact_address"]=="one@example.test"
    assert rows[0]["unread"]==1
    with __import__("openprospect.db",fromlist=["connect"]).connect() as conn:
        count=conn.execute("SELECT COUNT(*) FROM conversation_messages").fetchone()[0]
    assert count==2

def test_mailbox_connection_status_is_honest(monkeypatch):
    for key in ("ZERO_HAWK_SMTP_HOST","ZERO_HAWK_SMTP_USER","ZERO_HAWK_SMTP_PASSWORD","ZERO_HAWK_FROM_EMAIL","ZERO_HAWK_IMAP_HOST","ZERO_HAWK_IMAP_USER","ZERO_HAWK_IMAP_PASSWORD"):
        monkeypatch.delenv(key,raising=False)
    assert email_status()["configured"] is False
    assert "ZERO_HAWK_SMTP_HOST" in email_status()["missing"]
    assert imap_status()["configured"] is False

def test_privacy_checklist_is_explicit():
    items=privacy_checklist()
    assert any("opt-out" in x["item"] for x in items)
    assert any("lawful basis" in x["item"] for x in items)

def test_dns_report_requires_domain():
    import pytest
    with pytest.raises(ValueError): dns_report("not a domain")

def test_autonomous_loop_defaults_paused():
    assert loop_status()["running"] is False
    assert "never" in loop_status()["mode"]
    pause_loop()
