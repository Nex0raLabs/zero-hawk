"""Glue between stored drafts and the deterministic lint."""
from __future__ import annotations
from .db import connect
from .lint import lint_draft

def lint_for_draft(draft_id: int):
    with connect() as c:
        d = c.execute("SELECT drafts.*,contacts.email_status st FROM drafts LEFT JOIN contacts ON contacts.id=drafts.contact_id WHERE drafts.id=?", (draft_id,)).fetchone()
    if not d:
        return None
    try:
        from .training import load_training
        banned = load_training().get("banned_phrases", [])
    except Exception:
        banned = []
    ch = d["channel"] or "email"
    return lint_draft(d["subject"] or "", d["body"] or "", channel=ch, email_status=(d["st"] or "unknown") if ch == "email" else "verified", banned=banned)
