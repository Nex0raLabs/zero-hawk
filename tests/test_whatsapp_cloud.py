import hashlib
import hmac
import json

from openprospect.whatsapp_cloud import (
    cloud_api_status,
    consume_webhook,
    send_text,
    send_template,
    verify_webhook_signature,
)
from openprospect.conversations import get_conversation, list_conversations, list_messages


def test_cloud_api_configuration_is_reported_without_exposing_secrets(monkeypatch):
    for key in (
        "ZERO_HAWK_WA_CLOUD_TOKEN",
        "ZERO_HAWK_WA_PHONE_NUMBER_ID",
        "ZERO_HAWK_WA_VERIFY_TOKEN",
        "ZERO_HAWK_WA_APP_SECRET",
    ):
        monkeypatch.delenv(key, raising=False)
    status = cloud_api_status()
    assert status["configured"] is False
    assert "ZERO_HAWK_WA_CLOUD_TOKEN" in status["missing"]
    assert status["webhook_ready"] is False
    assert "ZERO_HAWK_WA_APP_SECRET" in status["webhook_missing"]


def test_meta_webhook_signature_verification(monkeypatch):
    monkeypatch.setenv("ZERO_HAWK_WA_APP_SECRET", "test-app-secret")
    body = b'{"object":"whatsapp_business_account"}'
    digest = hmac.new(b"test-app-secret", body, hashlib.sha256).hexdigest()
    assert verify_webhook_signature(body, "sha256=" + digest)
    assert not verify_webhook_signature(body, "sha256=wrong")
    assert not verify_webhook_signature(body, "")


def test_webhook_persists_inbound_message_and_status(monkeypatch, tmp_path):
    monkeypatch.setenv("ZERO_HAWK_HOME", str(tmp_path))
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "contacts": [{"wa_id": "254700000001", "profile": {"name": "Test Contact"}}],
                    "messages": [{
                        "id": "wamid.test-inbound",
                        "from": "254700000001",
                        "type": "text",
                        "text": {"body": "I am interested in your website package"},
                    }],
                    "statuses": [],
                }
            }]
        }]
    }
    result = consume_webhook(payload)
    assert result == {"messages": 1, "statuses": 0}
    conversations = list_conversations()
    row = next(item for item in conversations if item["channel"] == "whatsapp")
    assert row["contact_address"] == "254700000001"
    assert list_messages(row["id"])[0]["body"] == "I am interested in your website package"


def test_cloud_send_requires_explicit_approval(monkeypatch):
    monkeypatch.setenv("ZERO_HAWK_WA_CLOUD_TOKEN", "fake-token")
    monkeypatch.setenv("ZERO_HAWK_WA_PHONE_NUMBER_ID", "123456789")
    import pytest
    with pytest.raises(RuntimeError, match="explicitly approved"):
        send_text(to="254700000001", text="Test", approved=False)


def test_template_send_requires_explicit_approval(monkeypatch):
    monkeypatch.setenv("ZERO_HAWK_WA_CLOUD_TOKEN", "fake-token")
    monkeypatch.setenv("ZERO_HAWK_WA_PHONE_NUMBER_ID", "123456789")
    import pytest
    with pytest.raises(RuntimeError, match="explicitly approved"):
        send_template(to="254700000001", template_name="hello_world", approved=False)
