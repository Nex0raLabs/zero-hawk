"""Official WhatsApp Business Cloud API client and webhook verification.

Credentials are read only from the local environment. Outbound messages require
an explicit approval flag and obey the shared global pause + a daily cap.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import urllib.error
import urllib.request
from .config import env_value
from .db import connect, is_suppressed, log


def cloud_api_status() -> dict:
    send_keys = ("ZERO_HAWK_WA_CLOUD_TOKEN", "ZERO_HAWK_WA_PHONE_NUMBER_ID")
    webhook_keys = ("ZERO_HAWK_WA_VERIFY_TOKEN", "ZERO_HAWK_WA_APP_SECRET")
    missing = [key for key in send_keys if not env_value(key)]
    webhook_missing = [key for key in webhook_keys if not env_value(key)]
    return {
        "configured": not missing,
        "missing": missing,
        "webhook_ready": not webhook_missing,
        "webhook_missing": webhook_missing,
        "phone_number_id": env_value("ZERO_HAWK_WA_PHONE_NUMBER_ID", ""),
        "api_version": env_value("ZERO_HAWK_WA_API_VERSION", "v27.0"),
    }


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    secret = env_value("ZERO_HAWK_WA_APP_SECRET", "")
    if not secret or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def send_text(*, to: str, text: str, approved: bool = False) -> dict:
    cfg = cloud_api_status()
    if not cfg["configured"]:
        raise RuntimeError("WhatsApp Cloud API is not configured: " + ", ".join(cfg["missing"]))
    if not approved:
        raise RuntimeError("Message must be explicitly approved before sending.")
    digits = re.sub(r"\D", "", str(to or ""))
    if not re.fullmatch(r"[1-9][0-9]{7,14}", digits):
        raise ValueError("Recipient must be an international phone number, e.g. 2547XXXXXXXX.")
    message = str(text or "").strip()
    if not message:
        raise ValueError("Message text is required.")
    if len(message) > 4096:
        raise ValueError("WhatsApp text messages must be 4096 characters or fewer.")
    if is_suppressed(digits) or is_suppressed("+" + digits):
        raise RuntimeError("This WhatsApp number is on the suppression list.")
    from .sendpolicy import check_send_allowed
    check_send_allowed()
    cap = max(1, min(int(env_value("ZERO_HAWK_WA_DAILY_SEND_LIMIT", "25")), 100))
    with connect() as conn:
        sent_today = conn.execute(
            "SELECT COUNT(*) FROM activity WHERE event='whatsapp_sent' AND date(created_at,'localtime')=date('now','localtime')"
        ).fetchone()[0]
    if sent_today >= cap:
        raise RuntimeError("WhatsApp daily sending limit reached (" + str(cap) + ").")
    version = cfg["api_version"]
    url = "https://graph.facebook.com/" + version + "/" + cfg["phone_number_id"] + "/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": digits,
        "type": "text",
        "text": {"preview_url": False, "body": message},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + env_value("ZERO_HAWK_WA_CLOUD_TOKEN"),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError("Meta WhatsApp API rejected the send (" + str(exc.code) + "): " + detail) from exc
    message_id = ((result.get("messages") or [{}])[0]).get("id", "")
    if not message_id:
        raise RuntimeError("Meta returned no message ID; delivery is not confirmed.")
    log("whatsapp_sent", digits + " | " + message_id)
    return {"sent": True, "id": message_id, "to": digits, "response": result}


def consume_webhook(payload: dict) -> dict:
    """Persist inbound message events and record delivery/read status events."""
    from .conversations import add_message, update_message_status
    added = 0
    statuses = 0
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            contacts = {
                str(item.get("wa_id", "")): item.get("profile", {}).get("name", "")
                for item in (value.get("contacts") or [])
            }
            for msg in value.get("messages", []) or []:
                sender = str(msg.get("from", ""))
                kind = str(msg.get("type", "unknown"))
                if kind == "text":
                    body = str((msg.get("text") or {}).get("body", ""))
                elif kind == "button":
                    body = str((msg.get("button") or {}).get("text", "[Button reply]"))
                elif kind == "interactive":
                    interactive = msg.get("interactive") or {}
                    body = str((interactive.get("button_reply") or interactive.get("list_reply") or {}).get("title", "[Interactive reply]"))
                else:
                    body = "[" + kind + " message received]"
                if sender and msg.get("id"):
                    add_message("whatsapp", str(msg["id"]), sender, contacts.get(sender, "WhatsApp conversation"), body, "inbound")
                    added += 1
            for status in value.get("statuses", []) or []:
                message_id = str(status.get("id", ""))
                state = str(status.get("status", ""))
                if message_id and state:
                    update_message_status(message_id, state)
                    log("whatsapp_" + state, message_id)
                    statuses += 1
    return {"messages": added, "statuses": statuses}

def test_connection() -> dict:
    cfg = cloud_api_status()
    if not cfg["configured"]:
        raise RuntimeError("WhatsApp Cloud API is not configured: " + ", ".join(cfg["missing"]))
    url = "https://graph.facebook.com/" + cfg["api_version"] + "/" + cfg["phone_number_id"] + "?fields=display_phone_number,verified_name,quality_rating"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + env_value("ZERO_HAWK_WA_CLOUD_TOKEN")})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError("Meta connection check failed (" + str(exc.code) + "): " + detail) from exc

def send_template(*, to: str, template_name: str, language: str = "en_US",
                  body_parameters: list[str] | None = None, approved: bool = False) -> dict:
    """Send an approved Meta template, including optional positional BODY parameters."""
    cfg = cloud_api_status()
    if not cfg["configured"]:
        raise RuntimeError("WhatsApp Cloud API is not configured: " + ", ".join(cfg["missing"]))
    if not approved:
        raise RuntimeError("Template message must be explicitly approved before sending.")
    digits = re.sub(r"\D", "", str(to or ""))
    if not re.fullmatch(r"[1-9][0-9]{7,14}", digits):
        raise ValueError("Recipient must be an international phone number, e.g. 2547XXXXXXXX.")
    name = str(template_name or "").strip()
    if not re.fullmatch(r"[a-z0-9_]{1,512}", name):
        raise ValueError("Template name must use lowercase letters, numbers and underscores.")
    lang = str(language or "en_US").strip()
    if not re.fullmatch(r"[a-z]{2,3}_[A-Z]{2}", lang):
        raise ValueError("Language must look like en_US.")
    if is_suppressed(digits) or is_suppressed("+" + digits):
        raise RuntimeError("This WhatsApp number is on the suppression list.")
    from .sendpolicy import check_send_allowed
    check_send_allowed()
    cap = max(1, min(int(env_value("ZERO_HAWK_WA_DAILY_SEND_LIMIT", "25")), 100))
    with connect() as conn:
        sent_today = conn.execute(
            "SELECT COUNT(*) FROM activity WHERE event='whatsapp_sent' AND date(created_at)=date('now','localtime')"
        ).fetchone()[0]
    if sent_today >= cap:
        raise RuntimeError("WhatsApp daily sending limit reached (" + str(cap) + ").")
    params = [str(value)[:1024] for value in (body_parameters or []) if str(value).strip()]
    if len(params) > 20:
        raise ValueError("A maximum of 20 BODY parameters is supported by this form.")
    template = {"name": name, "language": {"code": lang}}
    if params:
        template["components"] = [{
            "type": "body",
            "parameters": [{"type": "text", "text": value} for value in params],
        }]
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": digits,
        "type": "template",
        "template": template,
    }
    url = "https://graph.facebook.com/" + cfg["api_version"] + "/" + cfg["phone_number_id"] + "/messages"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + env_value("ZERO_HAWK_WA_CLOUD_TOKEN"),
                 "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:2000]
        raise RuntimeError("Meta WhatsApp template send failed (" + str(exc.code) + "): " + detail) from exc
    message_id = ((result.get("messages") or [{}])[0]).get("id", "")
    if not message_id:
        raise RuntimeError("Meta returned no message ID; template delivery is not confirmed.")
    log("whatsapp_sent", digits + " | template " + name + " | " + message_id)
    return {"sent": True, "id": message_id, "to": digits, "template": name, "response": result}
