"""First-party website training with conservative, local heuristic extraction."""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

USER_AGENT = "OpenProspect/0.2 (+https://github.com/linkto254-bot/openprospect)"
MAX_BYTES = 1_500_000
PAGE_LIMIT = 3


class _Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = False
        self.title_text: list[str] = []
        self.text: list[str] = []
        self.links: list[str] = []
        self.meta: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        if tag == "title":
            self.title = True
        if tag == "meta":
            key = (a.get("name") or a.get("property") or "").lower()
            if key in {"description", "og:description", "og:site_name"} and a.get("content"):
                self.meta[key] = str(a["content"])
        if tag == "a" and a.get("href"):
            self.links.append(str(a["href"]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self.title = False

    def handle_data(self, data: str) -> None:
        value = re.sub(r"\s+", " ", data).strip()
        if value:
            self.text.append(value)
            if self.title:
                self.title_text.append(value)


def _public_http_url(url: str) -> urllib.parse.SplitResult:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Use a complete public http:// or https:// website URL.")
    if parsed.username or parsed.password:
        raise ValueError("Website URLs containing credentials are not allowed.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("Local network addresses are not allowed.")
    try:
        addresses = {ipaddress.ip_address(host)}
    except ValueError:
        try:
            addresses = {ipaddress.ip_address(item[4][0]) for item in socket.getaddrinfo(host, None)}
        except OSError as exc:
            raise ValueError(f"Could not resolve website host: {exc}") from exc
    if not addresses or any(not addr.is_global for addr in addresses):
        raise ValueError("Private, loopback and non-public website addresses are blocked.")
    return parsed


class _PublicRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Validate every redirect target before urllib opens the next connection."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _public_http_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_SAFE_OPENER = urllib.request.build_opener(_PublicRedirectHandler())


def _fetch(url: str, timeout: int = 15) -> tuple[str, str]:
    _public_http_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with _SAFE_OPENER.open(request, timeout=timeout) as response:
        final_url = response.geturl()
        _public_http_url(final_url)
        content_type = response.headers.get("Content-Type", "")
        if content_type and "html" not in content_type.lower():
            raise ValueError(f"Skipped non-HTML page ({content_type}).")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raw = raw[:MAX_BYTES]
    return final_url, raw.decode("utf-8", "replace")


def _allowed_by_robots(url: str) -> bool:
    parsed = urllib.parse.urlsplit(url)
    robots_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(robots_url)
    try:
        _public_http_url(robots_url)
        request = urllib.request.Request(robots_url, headers={"User-Agent": USER_AGENT})
        with _SAFE_OPENER.open(request, timeout=10) as response:
            _public_http_url(response.geturl())
            body = response.read(256_000).decode("utf-8", "replace")
        parser.parse(body.splitlines())
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            parser.parse([])
        else:
            return False
    except Exception:
        return False
    return parser.can_fetch(USER_AGENT, url)


def _page_data(url: str) -> dict[str, Any]:
    if not _allowed_by_robots(url):
        return {"url": url, "blocked": True, "text": "", "title": "", "description": "", "links": []}
    final_url, source = _fetch(url)
    page = _Page()
    page.feed(source)
    text = re.sub(r"\s+", " ", " ".join(page.text))[:12000]
    return {
        "url": final_url,
        "blocked": False,
        "title": " ".join(page.title_text)[:300],
        "description": page.meta.get("description") or page.meta.get("og:description", ""),
        "text": text,
        "links": page.links,
    }


def _extract_training(pages: list[dict[str, Any]], source_url: str) -> dict[str, Any]:
    all_text = " ".join(p.get("text", "") for p in pages)
    lower = all_text.lower()
    emails = sorted(set(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", all_text, re.I)))
    prices = sorted(set(re.findall(r"(?:KES|KSh|USD|\$)\s?[\d,]+(?:\.\d{1,2})?", all_text, re.I)))
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", all_text) if len(s.strip()) > 35]
    keywords = {
        "buyers": ["businesses", "restaurants", "startups", "companies", "individuals", "teams", "customers"],
        "proof_points": ["years", "clients", "trusted", "certified", "award", "results", "portfolio", "projects"],
        "objections": ["faq", "questions", "support", "guarantee", "refund", "pricing", "delivery", "warranty"],
    }
    found = {key: [w for w in words if w in lower] for key, words in keywords.items()}
    return {
        "source_url": source_url,
        "trained_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "company": pages[0].get("title", "") if pages else "",
        "product": sentences[:8],
        "buyers": found["buyers"],
        "pricing": prices,
        "proof_points": found["proof_points"],
        "tone_of_voice": " ".join(sentences[:3])[:1000],
        "objections": found["objections"],
        "emails_published": emails,
        "pages_read": [{"url": p.get("url"), "title": p.get("title"), "blocked": p.get("blocked", False)} for p in pages],
        "icp": "",
        "offer": "",
        "banned_phrases": [],
        "signature": "",
        "language": "English",
        "default_cta": "Would you be open to a short conversation?",
    }


def train_website(url: str, home: str | Path | None = None) -> dict[str, Any]:
    """Read the homepage and up to two same-site contact/about pages, then save JSON."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    root = _public_http_url(url)
    homepage = _page_data(url)
    pages = [homepage]
    candidates: list[str] = []
    for href in homepage.get("links", []):
        absolute = urllib.parse.urljoin(homepage["url"], href)
        parsed = urllib.parse.urlsplit(absolute)
        if parsed.hostname != root.hostname:
            continue
        path = parsed.path.lower()
        if any(word in path for word in ("contact", "about", "service", "product")) and absolute not in candidates:
            candidates.append(absolute)
    for candidate in candidates[: PAGE_LIMIT - 1]:
        time.sleep(1.0)
        try:
            pages.append(_page_data(candidate))
        except Exception as exc:
            pages.append({"url": candidate, "blocked": True, "error": str(exc), "text": ""})
    result = _extract_training(pages, url)
    home_path = Path(home) if home else Path.home() / ".openprospect"
    home_path.mkdir(parents=True, exist_ok=True)
    target = home_path / "company-training.json"
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result["_config_path"] = str(target)
    return result


def load_training(home: str | Path | None = None) -> dict[str, Any]:
    target = (Path(home) if home else Path.home() / ".openprospect") / "company-training.json"
    if not target.exists():
        return {}
    return json.loads(target.read_text(encoding="utf-8"))


def save_training(payload: dict[str, Any], home: str | Path | None = None) -> dict[str, Any]:
    allowed = {"icp", "offer", "banned_phrases", "signature", "language", "default_cta"}
    current = load_training(home)
    if not current:
        raise ValueError("Train on your website before editing the company profile.")
    for key in allowed:
        if key in payload:
            current[key] = payload[key]
    target = (Path(home) if home else Path.home() / ".openprospect") / "company-training.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return current
