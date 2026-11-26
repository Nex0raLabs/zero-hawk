"""Deterministic pre-send lint. No model calls; every rule is explainable."""
from __future__ import annotations
import re

MERGE = re.compile(r"(\{\{.*?\}\}|\{[a-z_ ]+\}|\[[A-Z][A-Za-z _]*\]|<[A-Z][A-Za-z _]*>|%\w+%)")
SPAM = ("act now", "100% free", "guarantee", "risk-free", "click here", "limited time", "make money", "winner", "urgent", "no obligation")
LINK = re.compile(r"https?://\S+|www\.\S+", re.I)

def lint_draft(subject: str, body: str, *, channel: str = "email", email_status: str = "verified",
               banned: list[str] | None = None, max_words: int | None = None, max_links: int = 1) -> dict:
    errors, warnings = [], []
    text = f"{subject}\n{body}"
    low = text.lower()
    limit = max_words or (60 if channel == "whatsapp" else 150)
    words = len(re.findall(r"\b\w+\b", body))
    if not body.strip():
        errors.append("Message body is empty.")
    if channel == "email" and not (subject or "").strip():
        errors.append("Subject line is missing.")
    if MERGE.search(text):
        errors.append("Unresolved merge tag found: " + MERGE.search(text).group(0))
    for phrase in banned or []:
        if phrase.strip() and phrase.strip().lower() in low:
            errors.append(f"Banned phrase used: “{phrase.strip()}”.")
    if words > limit:
        errors.append(f"Too long: {words} words (limit {limit}).")
    if len(LINK.findall(body)) > max_links:
        errors.append(f"Too many links ({len(LINK.findall(body))}); maximum {max_links}.")
    if channel == "email" and email_status != "verified":
        errors.append(f"Recipient email is “{email_status or 'unknown'}”; only verified addresses can be sent to.")
    hits = [w for w in SPAM if w in low]
    if hits:
        warnings.append("Spam-trigger wording: " + ", ".join(hits))
    if subject and subject.isupper() and len(subject) > 6:
        warnings.append("Subject is ALL CAPS.")
    if text.count("!") > 1:
        warnings.append("More than one exclamation mark.")
    if channel == "email" and words < 25 and body.strip():
        warnings.append("Very short; may read as low-effort.")
    return {"ok": not errors, "errors": errors, "warnings": warnings, "words": words}
