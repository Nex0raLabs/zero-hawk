from __future__ import annotations

import json
import re
import time
import urllib.parse
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .training import _allowed_by_robots, _fetch


class _ProfileParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []
        self.link_texts: list[str] = []
        self._active_link = False
        self._active_link_text: list[str] = []
        self.meta: dict[str, str] = {}
        self.has_schema = False
        self.has_viewport = False

    def handle_starttag(self, tag: str, attrs) -> None:
        data = dict(attrs)
        if tag == "a":
            self._active_link = True
            self._active_link_text = []
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            name = (data.get("name") or data.get("property") or "").lower()
            if name in {"description", "og:description"} and data.get("content"):
                self.meta[name] = str(data["content"])
            if name == "viewport":
                self.has_viewport = True
        if tag == "script" and data.get("type", "").lower() == "application/ld+json":
            self.has_schema = True
        if tag == "a" and data.get("href"):
            self.links.append(str(data["href"]))
        if data.get("itemscope") and data.get("itemtype", "").startswith("https://schema.org"):
            self.has_schema = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.in_title = False
        if tag == "a" and self._active_link:
            label = re.sub(r"\s+", " ", " ".join(self._active_link_text)).strip()
            self.link_texts.append(label)
            self._active_link = False
            self._active_link_text = []

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.text_parts.append(value)
            if self.in_title:
                self.title_parts.append(value)
            if self._active_link:
                self._active_link_text.append(value)


DEFAULT_RULES = {
    "NO_SSL": {"enabled": True, "weight": 20, "label": "Website does not use HTTPS"},
    "NO_MOBILE_VIEWPORT": {"enabled": True, "weight": 12, "label": "No mobile viewport declaration found"},
    "NO_SCHEMA_MARKUP": {"enabled": True, "weight": 8, "label": "No schema.org structured data found"},
    "NO_WHATSAPP_BUTTON": {"enabled": True, "weight": 8, "label": "No WhatsApp contact link found"},
    "NO_ONLINE_BOOKING": {"enabled": True, "weight": 12, "label": "No online booking or appointment path found"},
    "NO_ONLINE_ORDERING": {"enabled": True, "weight": 8, "label": "No online ordering path found"},
    "NO_CONTACT_PAGE": {"enabled": True, "weight": 8, "label": "No contact page link found"},
    "STALE_COPYRIGHT": {"enabled": True, "weight": 5, "label": "Copyright year appears outdated"},
    "SLOW_LOAD": {"enabled": True, "weight": 10, "label": "Homepage response took more than four seconds"},
    "HIRING_PAGE": {"enabled": True, "weight": 0, "label": "Careers or hiring page found"},
}


def load_signal_rules() -> dict[str, dict[str, Any]]:
    from .db import db_path
    path = db_path().parent / "signal-rules.json"
    rules = {key: dict(value) for key, value in DEFAULT_RULES.items()}
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            for key, value in saved.items():
                if key == "_custom_rules" and isinstance(value, list):
                    rules["_custom_rules"] = value
                elif key in rules and isinstance(value, dict):
                    rules[key].update(value)
        except (OSError, ValueError):
            pass
    return rules


def save_signal_rules(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    from .db import db_path
    rules = load_signal_rules()
    for key, value in payload.items():
        if key == "_custom_rules" and isinstance(value, list):
            custom = []
            for item in value[:30]:
                if not isinstance(item, dict):
                    continue
                code = re.sub(r"[^A-Z0-9_]", "", str(item.get("code", "")).upper())[:40]
                keywords = [str(word).strip().lower() for word in item.get("keywords", []) if str(word).strip()][:20]
                if code and keywords and code not in DEFAULT_RULES:
                    custom.append({
                        "code": code, "label": str(item.get("label", code.replace("_", " ").title()))[:120],
                        "keywords": keywords, "weight": max(0, min(30, int(item.get("weight", 5)))),
                        "enabled": bool(item.get("enabled", True)),
                    })
            rules["_custom_rules"] = custom
        elif key in rules and isinstance(value, dict):
            if "enabled" in value:
                rules[key]["enabled"] = bool(value["enabled"])
            if "weight" in value:
                rules[key]["weight"] = max(0, min(30, int(value["weight"])))
    path = db_path().parent / "signal-rules.json"
    path.write_text(json.dumps(rules, indent=2) + "\n", encoding="utf-8")
    return rules


def _parse_page(url: str) -> tuple[str, _ProfileParser, str, float]:
    if not _allowed_by_robots(url):
        raise PermissionError("robots.txt disallows this page.")
    started = time.perf_counter()
    final_url, source = _fetch(url)
    elapsed = time.perf_counter() - started
    parser = _ProfileParser()
    parser.feed(source)
    return final_url, parser, source, elapsed


def _signal(code: str, rules: dict[str, dict[str, Any]], evidence_url: str, confidence: float = 0.9) -> dict[str, Any] | None:
    rule = rules.get(code, {})
    if not rule.get("enabled", False):
        return None
    return {
        "code": code,
        "label": rule.get("label", code.replace("_", " ").title()),
        "weight": int(rule.get("weight", 0)),
        "confidence": confidence,
        "evidence_url": evidence_url,
    }


def profile_website(url: str):
    if not url:
        return {
            "error": "No website URL saved for this company.",
            "signals": [{"code": "NO_WEBSITE", "label": "No website listed", "weight": 40, "confidence": 1.0, "evidence_url": ""}],
            "score": 40,
        }
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    rules = load_signal_rules()
    try:
        final_url, home, raw_home, elapsed = _parse_page(url)
    except Exception as exc:
        return {"error": f"Could not profile website: {exc}", "signals": [], "score": 0}

    parsed = urllib.parse.urlsplit(final_url)
    all_parsers = [home]
    all_sources = [raw_home]
    all_urls = [final_url]
    candidates: list[str] = []
    for href in home.links:
        absolute = urllib.parse.urljoin(final_url, href)
        target = urllib.parse.urlsplit(absolute)
        if target.hostname != parsed.hostname:
            continue
        path = target.path.lower()
        if any(word in path for word in ("contact", "about", "career", "jobs", "team")) and absolute not in candidates:
            candidates.append(absolute)
    for candidate in candidates[:2]:
        time.sleep(1.0)
        try:
            page_url, page, source, _ = _parse_page(candidate)
            all_parsers.append(page)
            all_sources.append(source)
            all_urls.append(page_url)
        except Exception:
            continue

    text = " ".join(" ".join(p.text_parts) for p in all_parsers)
    raw = "\n".join(all_sources)
    emails = sorted(set(re.findall(r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", raw + " " + text)))
    phones = sorted(set(re.findall(r"(?<!\w)(?:\+?\d[\d ().-]{7,}\d)", text)))[:20]
    links = [urllib.parse.urljoin(final_url, link) for page in all_parsers for link in page.links]
    joined = (raw + " " + text + " " + " ".join(links)).lower()
    link_labels = [label.lower() for page in all_parsers for label in page.link_texts]
    has_contact = (
        any(word in link.lower() for link in links for word in ("contact", "get-in-touch"))
        or any("contact" in label or "get in touch" in label for label in link_labels)
    )
    has_booking = any(word in joined for word in ("booking", "book online", "appointment", "reserve a table", "reservations", "schedule online"))
    has_ordering = any(word in joined for word in ("order online", "online ordering", "place order", "delivery menu"))
    has_whatsapp = any(word in joined for word in ("wa.me/", "api.whatsapp.com", "whatsapp.com/send"))
    has_viewport = any(page.has_viewport for page in all_parsers)
    has_schema = any(page.has_schema for page in all_parsers) or "schema.org" in raw.lower()
    years = [int(y) for y in re.findall(r"(?:©|copyright)?\s*(20\d{2})", text, re.I)]
    current_year = time.gmtime().tm_year

    signals = []
    if parsed.scheme != "https":
        signals.append(_signal("NO_SSL", rules, final_url, 1.0))
    if not has_viewport:
        signals.append(_signal("NO_MOBILE_VIEWPORT", rules, final_url, 0.85))
    if not has_schema:
        signals.append(_signal("NO_SCHEMA_MARKUP", rules, final_url, 0.9))
    if not has_whatsapp:
        signals.append(_signal("NO_WHATSAPP_BUTTON", rules, final_url, 0.8))
    if not has_booking:
        signals.append(_signal("NO_ONLINE_BOOKING", rules, final_url, 0.75))
    if not has_ordering:
        signals.append(_signal("NO_ONLINE_ORDERING", rules, final_url, 0.75))
    if not has_contact:
        signals.append(_signal("NO_CONTACT_PAGE", rules, final_url, 0.8))
    if years and max(years) < current_year - 3:
        signals.append(_signal("STALE_COPYRIGHT", rules, final_url, 0.7))
    if elapsed > 4:
        signals.append(_signal("SLOW_LOAD", rules, final_url, 0.8))
    if any(word in link.lower() for link in links for word in ("career", "jobs", "work-with-us")):
        signals.append(_signal("HIRING_PAGE", rules, final_url, 0.9))
    for custom in rules.get("_custom_rules", []):
        if custom.get("enabled", True) and any(word in joined for word in custom.get("keywords", [])):
            signals.append({
                "code": custom["code"], "label": custom.get("label", custom["code"]),
                "weight": int(custom.get("weight", 5)), "confidence": 0.7,
                "evidence_url": final_url,
            })
    signals = [item for item in signals if item]
    score = min(100, sum(int(item["weight"]) for item in signals))
    return {
        "url": final_url,
        "title": " ".join(home.title_parts).strip(),
        "description": home.meta.get("description", "") or home.meta.get("og:description", ""),
        "emails": emails,
        "phones": phones,
        "text": re.sub(r"\s+", " ", unescape(text))[:12000],
        "pages": all_urls,
        "signals": signals,
        "score": score,
        "load_seconds": round(elapsed, 2),
    }
