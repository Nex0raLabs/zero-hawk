"""Outbound send policy: global pause switch, recipient-local office hours, jitter."""
from __future__ import annotations
from .config import env_value
import datetime as dt
import json, os, random
from .db import db_path

def _file():
    return db_path().with_name("send-policy.json")

def _load() -> dict:
    try:
        return json.loads(_file().read_text("utf-8"))
    except Exception:
        return {}

def _save(d: dict) -> None:
    _file().write_text(json.dumps(d, indent=2), "utf-8")

def is_paused() -> bool:
    return bool(_load().get("paused", False))

def set_paused(paused: bool) -> None:
    d = _load(); d["paused"] = bool(paused); _save(d)

def in_office_hours(now_utc: dt.datetime | None = None, tz_offset: float = 3.0, start: int = 8, end: int = 18) -> bool:
    """Mon-Fri, start<=hour<end in the recipient's zone (default East Africa Time, UTC+3)."""
    now = (now_utc or dt.datetime.now(dt.timezone.utc)) + dt.timedelta(hours=tz_offset)
    return now.weekday() < 5 and start <= now.hour < end

def jitter_seconds(low: int = 45, high: int = 180) -> int:
    return random.randint(low, high)

def check_send_allowed(now_utc: dt.datetime | None = None) -> None:
    """Raise RuntimeError when sending must not happen right now."""
    if is_paused():
        raise RuntimeError("Sending is paused (global kill switch). Resume it on the Controls page.")
    if env_value("ZERO_HAWK_ENFORCE_OFFICE_HOURS", "1") != "0":
        tz = float(env_value("ZERO_HAWK_TZ_OFFSET", "3"))
        if not in_office_hours(now_utc, tz):
            raise RuntimeError("Outside office hours (Mon–Fri 08:00–18:00 recipient time). Set ZERO_HAWK_ENFORCE_OFFICE_HOURS=0 to override.")
