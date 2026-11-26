"""Free email hygiene checks. SMTP probes never send message content."""
from __future__ import annotations

import re
import secrets
import smtplib
import time
from email.utils import parseaddr
from typing import Any

ROLE_ACCOUNTS = {
    "admin", "billing", "careers", "contact", "enquiries", "hello", "help",
    "hr", "info", "jobs", "legal", "marketing", "office", "orders", "postmaster",
    "privacy", "sales", "service", "support", "team", "webmaster",
}

DISPOSABLE_DOMAINS = {
    "10minutemail.com", "guerrillamail.com", "mailinator.com", "temp-mail.org",
    "tempmail.com", "yopmail.com", "getnada.com", "throwawaymail.com",
    "trashmail.com", "dispostable.com", "fakeinbox.com", "sharklasers.com",
    "maildrop.cc", "minuteinbox.com", "mohmal.com", "emailondeck.com",
}
EMAIL_RE = re.compile(r"^[A-Z0-9.!#$%&'*+/=?^_{}|~-]+@[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?)+$", re.I)


def _smtp_check(mx_host: str, address: str, timeout: float = 5.0) -> dict[str, Any]:
    """Probe RCPT acceptance and a random address to identify catch-all mail servers."""
    server = smtplib.SMTP(timeout=timeout)
    try:
        server.connect(mx_host, 25)
        server.ehlo_or_helo_if_needed()
        server.mail("probe@zero-hawk.invalid")
        target_code, target_message = server.rcpt(address)
        server.rset()
        random_address = f"op-{secrets.token_hex(8)}@{address.rsplit('@', 1)[1]}"
        server.mail("probe@zero-hawk.invalid")
        random_code, random_message = server.rcpt(random_address)
        return {
            "target_accepted": 200 <= target_code < 300,
            "target_code": target_code,
            "target_message": target_message.decode("utf-8", "replace") if isinstance(target_message, bytes) else str(target_message),
            "catch_all": 200 <= random_code < 300,
            "catch_all_code": random_code,
            "catch_all_message": random_message.decode("utf-8", "replace") if isinstance(random_message, bytes) else str(random_message),
        }
    finally:
        try:
            server.quit()
        except Exception:
            server.close()


def verify_email(address: str, *, smtp_probe: bool = True, is_guess: bool = False) -> dict[str, Any]:
    raw = (address or "").strip()
    _, parsed_address = parseaddr(raw)
    candidate = parsed_address.strip()
    result: dict[str, Any] = {
        "address": candidate or raw,
        "status": "invalid",
        "syntax_valid": False,
        "mx_found": False,
        "disposable": False,
        "role_account": False,
        "catch_all": False,
        "smtp_probe": "not_run",
        "reason": "",
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if not candidate or not EMAIL_RE.fullmatch(candidate):
        result["reason"] = "Email syntax is invalid."
        return result
    local, domain = candidate.rsplit("@", 1)
    if local.startswith(".") or local.endswith(".") or ".." in local:
        result["reason"] = "Email local part has invalid dot placement."
        return result
    try:
        domain = domain.encode("idna").decode("ascii").lower()
    except UnicodeError:
        result["reason"] = "Email domain is not valid IDNA."
        return result
    candidate = f"{local}@{domain}"
    result["address"] = candidate
    result["syntax_valid"] = True
    result["role_account"] = local.lower() in ROLE_ACCOUNTS
    result["disposable"] = domain in DISPOSABLE_DOMAINS
    if result["disposable"]:
        result["reason"] = "Disposable email domain."
        return result

    try:
        import dns.resolver
        answers = dns.resolver.resolve(domain, "MX", lifetime=4.0)
        mx_hosts = [
            str(record.exchange).rstrip(".")
            for record in sorted(answers, key=lambda record: record.preference)
            if str(record.exchange).rstrip(".")
        ]
    except Exception as exc:
        result["status"] = "risky"
        result["reason"] = f"MX lookup unavailable or no MX record: {exc}"
        return result

    if not mx_hosts:
        result["reason"] = "No mail exchanger was published for this domain."
        return result
    result["mx_found"] = True
    if not smtp_probe:
        result["status"] = "guess" if is_guess else "risky"
        result["reason"] = "MX exists; SMTP recipient acceptance was not checked."
        return result

    probe = None
    last_error = ""
    for host in mx_hosts[:2]:
        try:
            probe = _smtp_check(host, candidate)
            break
        except Exception as exc:
            last_error = str(exc)
    if probe is None:
        result["status"] = "guess" if is_guess else "risky"
        result["smtp_probe"] = "blocked_or_unavailable"
        result["reason"] = f"SMTP RCPT probe could not complete: {last_error or 'no response'}"
        return result

    result["smtp_probe"] = "completed"
    result["catch_all"] = bool(probe["catch_all"])
    result["smtp_target_code"] = probe["target_code"]
    if not probe["target_accepted"]:
        message = str(probe["target_message"])
        result["status"] = "guess" if is_guess else "risky"
        result["reason"] = f"SMTP did not confirm this mailbox: {message}"
    elif probe["catch_all"]:
        result["status"] = "guess" if is_guess else "risky"
        result["reason"] = "Domain accepts a random recipient; mailbox cannot be distinguished (catch-all)."
    elif is_guess:
        result["status"] = "verified"
        result["reason"] = "SMTP accepted the generated address and rejected a random recipient; the guess is now verified."
    else:
        result["status"] = "verified"
        result["reason"] = "MX exists and SMTP accepted this recipient but rejected a random address."
    return result


def is_deliverable(result: dict[str, Any]) -> bool:
    return result.get("status") == "verified" and not result.get("catch_all", False)


def learn_email_pattern(samples: list[dict[str, str]]) -> str:
    """Infer a conservative local-part pattern from named, published addresses."""
    scores = {"first.last": 0, "firstlast": 0, "firstinitiallast": 0, "first": 0}
    for sample in samples:
        name = (sample.get("name") or "").strip().lower().split()
        email = (sample.get("email") or "").strip().lower()
        if len(name) < 2 or "@" not in email:
            continue
        first, last = re.sub(r"[^a-z]", "", name[0]), re.sub(r"[^a-z]", "", name[-1])
        local = email.split("@", 1)[0]
        if local == f"{first}.{last}":
            scores["first.last"] += 1
        elif local == first + last:
            scores["firstlast"] += 1
        elif local == first[:1] + last:
            scores["firstinitiallast"] += 1
        elif local == first:
            scores["first"] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] else ""


def guess_email(first_name: str, last_name: str, domain: str, pattern: str = "") -> dict[str, str]:
    first = re.sub(r"[^a-z]", "", (first_name or "").lower())
    last = re.sub(r"[^a-z]", "", (last_name or "").lower())
    host = (domain or "").strip().lower().removeprefix("www.")
    if not first or not host or "." not in host:
        raise ValueError("A first name and valid company domain are required.")
    formats = {
        "first.last": f"{first}.{last}" if last else first,
        "firstlast": first + last if last else first,
        "firstinitiallast": first[:1] + last if last else first,
        "first": first,
    }
    if pattern not in formats:
        pattern = "first.last" if last else "first"
    return {"address": formats[pattern] + "@" + host, "status": "guess", "pattern": pattern}
