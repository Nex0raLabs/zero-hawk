from __future__ import annotations
from .config import env_value

import os
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit


def db_path() -> Path:
    configured = env_value("ZERO_HAWK_HOME")
    legacy_home = Path.home() / ".openprospect"
    home = Path(configured) if configured else (legacy_home if legacy_home.exists() else Path.home() / ".zero-hawk")
    home.mkdir(parents=True, exist_ok=True)
    legacy_db = home / "openprospect.db"
    current_db = home / "zero-hawk.db"
    # Continue using an existing database in-place; fresh installs get a branded filename.
    return legacy_db if legacy_db.exists() else current_db


def connect():
    c = sqlite3.connect(db_path(), timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript("""
    CREATE TABLE IF NOT EXISTS companies(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,website TEXT DEFAULT '',
      industry TEXT DEFAULT '',location TEXT DEFAULT '',notes TEXT DEFAULT '',
      phone TEXT DEFAULT '',email TEXT DEFAULT '',socials TEXT DEFAULT '',
      source TEXT DEFAULT 'manual',source_url TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS contacts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,company_id INTEGER NOT NULL,name TEXT DEFAULT '',
      title TEXT DEFAULT '',email TEXT DEFAULT '',phone TEXT DEFAULT '',source_url TEXT DEFAULT '',
      email_status TEXT DEFAULT 'unknown',email_verification_reason TEXT DEFAULT '',verified_at TEXT DEFAULT '',
      notes TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS campaigns(
      id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,description TEXT DEFAULT '',
      status TEXT DEFAULT 'draft',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS drafts(
      id INTEGER PRIMARY KEY AUTOINCREMENT,company_id INTEGER,contact_id INTEGER,campaign_id INTEGER,
      channel TEXT DEFAULT 'email',subject TEXT DEFAULT '',body TEXT NOT NULL,
      status TEXT DEFAULT 'draft',approved_at TEXT DEFAULT '',created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL,
      FOREIGN KEY(contact_id) REFERENCES contacts(id) ON DELETE SET NULL,
      FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL);
    CREATE TABLE IF NOT EXISTS suppressions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,value TEXT NOT NULL UNIQUE,reason TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS activity(
      id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,details TEXT DEFAULT '',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS observations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,company_id INTEGER NOT NULL,signal_code TEXT NOT NULL,
      label TEXT DEFAULT '',weight INTEGER DEFAULT 0,confidence REAL DEFAULT 0.0,
      evidence_url TEXT DEFAULT '',observed_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE CASCADE);
    """)
    # Additive migration for databases created by earlier Zero Hawk releases.
    columns = {row["name"] for row in c.execute("PRAGMA table_info(companies)")}
    for name in ("phone", "email", "socials"):
        if name not in columns:
            c.execute(f"ALTER TABLE companies ADD COLUMN {name} TEXT DEFAULT ''")
    contact_columns = {row["name"] for row in c.execute("PRAGMA table_info(contacts)")}
    for name in ("email_verification_reason", "verified_at"):
        if name not in contact_columns:
            c.execute(f"ALTER TABLE contacts ADD COLUMN {name} TEXT DEFAULT ''")
    return c


def _domain(value: str) -> str:
    candidate = (value or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = "https://" + candidate
    try:
        return (urlsplit(candidate).hostname or "").lower().removeprefix("www.")
    except ValueError:
        return ""


def _phone_key(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("254"):
        return digits
    if digits.startswith("0") and len(digits) == 10:
        return "254" + digits[1:]
    if (digits.startswith("7") or digits.startswith("1")) and len(digits) == 9:
        return "254" + digits
    return digits


def _name_key(value: str) -> str:
    value = (value or "").lower().replace("&", " and ")
    value = re.sub(r"\b(limited|ltd|llc|inc|plc|company|co)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def find_company_duplicate(website: str = "", phone: str = "", name: str = ""):
    domain = _domain(website)
    phone_key = _phone_key(phone)
    name_key = _name_key(name)
    with connect() as c:
        rows = c.execute("SELECT id, name, website, phone FROM companies ORDER BY id").fetchall()
    for row in rows:
        if domain and _domain(row["website"]) == domain:
            return dict(row)
        if phone_key and _phone_key(row["phone"]) == phone_key:
            return dict(row)
        if name_key and _name_key(row["name"]) == name_key:
            return dict(row)
    return None


def log(event, details=""):
    with connect() as c:
        c.execute("INSERT INTO activity(event,details) VALUES(?,?)", (event, details))


def add_company(name, website="", industry="", location="", notes="", source="manual", source_url="", phone="", email="", socials=""):
    with connect() as c:
        domain = _domain(website)
        phone_key = _phone_key(phone)
        name_key = _name_key(name)
        for row in c.execute("SELECT id, name, website, phone FROM companies ORDER BY id").fetchall():
            if ((domain and _domain(row["website"]) == domain)
                or (phone_key and _phone_key(row["phone"]) == phone_key)
                or (name_key and _name_key(row["name"]) == name_key)):
                return row["id"]
        cur = c.execute(
            "INSERT INTO companies(name,website,industry,location,notes,source,source_url,phone,email,socials) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (name.strip(), website.strip(), industry.strip(), location.strip(), notes.strip(),
             source, source_url, phone.strip(), email.strip(), socials.strip()),
        )
        ident = cur.lastrowid
    log("company_added", f"{name} ({source})")
    return ident


def list_companies(limit=200):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM companies ORDER BY id DESC LIMIT ?", (limit,))]


def add_contact(company_id, name="", title="", email="", phone="", source_url="", email_status="unknown", notes=""):
    # Imported/manual records cannot self-assert deliverability.
    if email_status == "verified":
        email_status = "unverified"
    if email_status not in {"unknown", "unverified", "risky", "guess", "invalid"}:
        email_status = "unknown"
    with connect() as c:
        cur = c.execute(
            "INSERT INTO contacts(company_id,name,title,email,phone,source_url,email_status,notes) VALUES(?,?,?,?,?,?,?,?)",
            (company_id, name, title, email, phone, source_url, email_status, notes),
        )
        return cur.lastrowid


def list_contacts(limit=500):
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT contacts.*,companies.name company_name FROM contacts "
            "JOIN companies ON companies.id=contacts.company_id ORDER BY contacts.id DESC LIMIT ?",
            (limit,),
        )]


def add_campaign(name, description=""):
    with connect() as c:
        cur = c.execute("INSERT INTO campaigns(name,description) VALUES(?,?)", (name, description))
        return cur.lastrowid


def list_campaigns():
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM campaigns ORDER BY id DESC")]


def add_draft(body, company_id=None, contact_id=None, campaign_id=None, subject="", channel="email"):
    with connect() as c:
        cur = c.execute(
            "INSERT INTO drafts(body,company_id,contact_id,campaign_id,subject,channel) VALUES(?,?,?,?,?,?)",
            (body, company_id, contact_id, campaign_id, subject, channel),
        )
        return cur.lastrowid


def list_drafts():
    with connect() as c:
        return [dict(r) for r in c.execute(
            "SELECT drafts.*,companies.name company_name,contacts.email contact_email FROM drafts "
            "LEFT JOIN companies ON companies.id=drafts.company_id "
            "LEFT JOIN contacts ON contacts.id=drafts.contact_id ORDER BY drafts.id DESC"
        )]


def set_draft_status(draft_id, status):
    if status not in ("draft", "approved", "rejected", "sent"):
        raise ValueError("Invalid draft status")
    with connect() as c:
        c.execute(
            "UPDATE drafts SET status=?,approved_at=CASE WHEN ?='approved' THEN CURRENT_TIMESTAMP ELSE approved_at END WHERE id=?",
            (status, status, draft_id),
        )
    log("draft_" + status, str(draft_id))


def add_suppression(value, reason="user request"):
    with connect() as c:
        c.execute("INSERT OR IGNORE INTO suppressions(value,reason) VALUES(?,?)", (value.strip().lower(), reason))
    log("suppression_added", value)


def is_suppressed(value):
    normalized = value.strip().lower()
    domain = normalized.rsplit("@", 1)[1] if "@" in normalized else normalized
    with connect() as c:
        return c.execute("SELECT 1 FROM suppressions WHERE value IN (?,?)", (normalized, domain)).fetchone() is not None


def list_activity(limit=100):
    with connect() as c:
        return [dict(r) for r in c.execute("SELECT * FROM activity ORDER BY id DESC LIMIT ?", (limit,))]


def save_company_observations(company_id, signals):
    with connect() as c:
        if not c.execute("SELECT id FROM companies WHERE id=?", (company_id,)).fetchone():
            raise ValueError("Company not found.")
        for signal in signals:
            c.execute(
                "INSERT INTO observations(company_id,signal_code,label,weight,confidence,evidence_url) VALUES(?,?,?,?,?,?)",
                (company_id, signal.get("code", ""), signal.get("label", ""),
                 int(signal.get("weight", 0)), float(signal.get("confidence", 0)),
                 signal.get("evidence_url", "")),
            )


def list_observations(limit=500):
    with connect() as c:
        return [dict(row) for row in c.execute(
            "SELECT observations.*,companies.name company_name FROM observations "
            "JOIN companies ON companies.id=observations.company_id "
            "ORDER BY observations.id DESC LIMIT ?", (limit,)
        )]


def set_contact_email_status(contact_id, status, reason=""):
    if status not in {"unknown", "unverified", "verified", "risky", "guess", "invalid"}:
        raise ValueError("Invalid email verification status.")
    with connect() as c:
        c.execute(
            "UPDATE contacts SET email_status=?,email_verification_reason=?,"
            "verified_at=CASE WHEN ?='verified' THEN CURRENT_TIMESTAMP ELSE '' END WHERE id=?",
            (status, reason, status, contact_id),
        )


def set_contact_email(contact_id, email, status="guess", reason=""):
    if status not in {"unverified", "verified", "risky", "guess", "invalid"}:
        raise ValueError("Invalid email status.")
    with connect() as c:
        c.execute(
            "UPDATE contacts SET email=?,email_status=?,email_verification_reason=?,"
            "verified_at=CASE WHEN ?='verified' THEN CURRENT_TIMESTAMP ELSE '' END WHERE id=?",
            (email.strip(), status, reason, status, contact_id),
        )
