"""Usage analytics, Help, PWA assets, kill switch and lint API."""
from __future__ import annotations
import html
import datetime as dt
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from .db import connect, list_activity
from .sendpolicy import is_paused, set_paused, in_office_hours
from .ui import MANIFEST, SERVICE_WORKER

router = APIRouter()

def _page(title: str, sub: str, body: str) -> str:
    from .app import shell
    return shell(f"<h1>{html.escape(title)}</h1><p class='muted'>{sub}</p>{body}")

@router.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return JSONResponse(MANIFEST, media_type="application/manifest+json")

@router.get("/sw.js", include_in_schema=False)
def sw():
    return Response(SERVICE_WORKER, media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})

def _count(sql: str, args=()) -> int:
    with connect() as c:
        return c.execute(sql, args).fetchone()[0]

def funnel() -> list[tuple[str, int]]:
    return [
        ("Companies found", _count("SELECT COUNT(*) FROM companies")),
        ("With website", _count("SELECT COUNT(*) FROM companies WHERE website<>''")),
        ("Profiled", _count("SELECT COUNT(DISTINCT company_id) FROM observations")),
        ("Contacts", _count("SELECT COUNT(*) FROM contacts")),
        ("Verified emails", _count("SELECT COUNT(*) FROM contacts WHERE email_status='verified'")),
        ("Drafts written", _count("SELECT COUNT(*) FROM drafts")),
        ("Approved", _count("SELECT COUNT(*) FROM drafts WHERE status IN ('approved','sent')")),
        ("Emails sent", _count("SELECT COUNT(*) FROM activity WHERE event='email_sent'")),
    ]

def sends_by_day(days: int = 14) -> list[tuple[str, int]]:
    out = []
    today = dt.date.today()
    for i in range(days - 1, -1, -1):
        d = (today - dt.timedelta(days=i)).isoformat()
        out.append((d[5:], _count("SELECT COUNT(*) FROM activity WHERE event='email_sent' AND date(created_at)=?", (d,))))
    return out

def _bars(rows: list[tuple[str, int]]) -> str:
    top = max([v for _, v in rows] + [1])
    return "".join(
        f"<div style='display:grid;grid-template-columns:150px 1fr 48px;gap:12px;align-items:center;margin:9px 0'>"
        f"<span class='muted'>{html.escape(k)}</span><div class='bar'><i style='width:{max(2, v * 100 // top) if v else 0}%'></i></div><b>{v}</b></div>"
        for k, v in rows)

@router.get("/usage", response_class=HTMLResponse)
def usage():
    f = funnel()
    days = sends_by_day()
    sent = f[-1][1]
    replies = _count("SELECT COUNT(*) FROM conversation_messages WHERE direction='inbound'") if _table("conversation_messages") else 0
    bounces = _count("SELECT COUNT(*) FROM activity WHERE event LIKE '%bounce%'")
    opt = _count("SELECT COUNT(*) FROM suppressions")
    rr = f"{replies * 100 // sent}%" if sent else "—"
    cards = "".join(f"<div class='card'><div class='lbl'>{k}</div><div class='number'>{v}</div></div>" for k, v in
                    [("Emails sent", sent), ("Replies", replies), ("Reply rate", rr), ("Bounces", bounces), ("Suppressed", opt)])
    ai = _count("SELECT COUNT(*) FROM activity WHERE event LIKE 'ai_%'")
    return _page("Usage", "Pipeline funnel and sending activity. Everything is counted from your local database.",
                 f"<div class='grid'>{cards}</div><div class='cols'><section><h2>Pipeline funnel</h2>{_bars(f)}</section>"
                 f"<section><h2>Emails sent · last 14 days</h2>{_bars(days)}</section></div>"
                 f"<section><h2>AI usage</h2><p class='muted'>AI calls logged: <b>{ai}</b>. Claude Code, Codex and Ollama run on your own subscription or hardware, so there is no per-call fee from Zero Hawk. Signal profiling makes zero AI calls.</p></section>")

def _table(name: str) -> bool:
    with connect() as c:
        return c.execute("SELECT 1 FROM sqlite_master WHERE name=?", (name,)).fetchone() is not None

@router.post("/controls/kill")
def kill():
    set_paused(True)
    from .db import log
    log("send_paused", "Global kill switch engaged")
    return RedirectResponse("/controls", 303)

@router.post("/controls/resume")
def resume():
    set_paused(False)
    from .db import log
    log("send_resumed", "Global kill switch released")
    return RedirectResponse("/controls", 303)

@router.get("/api/status")
def status():
    return {"paused": is_paused(), "office_hours_now": in_office_hours(), "funnel": dict(funnel())}

@router.get("/api/lint/{draft_id}")
def lint_api(draft_id: int):
    from .drafting import lint_for_draft
    r = lint_for_draft(draft_id)
    if r is None:
        raise HTTPException(404, "Draft not found")
    return r

HELP = """
<section><h2>What is Zero Hawk?</h2><p>A free, local-first outreach workspace. It finds businesses from OpenStreetMap, reads their public websites, scores buying signals, verifies contacts, drafts personalised messages with <i>your</i> AI, and sends only what you approve. Everything stays in one folder on your machine.</p></section>
<section><h2>Getting started</h2><ol class='steps' style='list-style:none'>
<li><span class='dot'>1</span><div><b>Connect email</b><br><span class='muted'>Set the SMTP/IMAP variables in <code>.env</code> (Gmail app password works). See <a href='/connections'>Inboxes</a>.</span></div></li>
<li><span class='dot'>2</span><div><b>Train on your product</b><br><span class='muted'>Open <a href='/train'>Your company</a>, paste your website, review and edit the profile.</span></div></li>
<li><span class='dot'>3</span><div><b>Discover and profile</b><br><span class='muted'><a href='/discover'>Discover</a> businesses in your city, then open <a href='/signals'>Signals</a> to see who looks ready.</span></div></li>
<li><span class='dot'>4</span><div><b>Review and approve</b><br><span class='muted'>Drafts appear in <a href='/drafts'>Outbox</a> with a lint check. Fix errors, approve, send.</span></div></li></ol></section>
<section><h2>Keyboard shortcuts</h2><p><code>Ctrl/⌘ K</code> command palette · <code>G</code> then <code>T</code> Today, <code>O</code> Outbox, <code>C</code> Companies, <code>D</code> Discover, <code>S</code> Settings, <code>H</code> Help</p></section>
<section><h2>Fixing the usual problems</h2><table><tr><th>Symptom</th><th>Fix</th></tr>
<tr><td>“SMTP is not configured”</td><td>Fill ZERO_HAWK_SMTP_HOST / USER / PASSWORD / FROM_EMAIL in <code>.env</code>, restart.</td></tr>
<tr><td>“Outside office hours”</td><td>Sending is Mon–Fri 08:00–18:00 East Africa Time. Adjust <code>ZERO_HAWK_TZ_OFFSET</code> or set <code>ZERO_HAWK_ENFORCE_OFFICE_HOURS=0</code>.</td></tr>
<tr><td>“Sending is paused”</td><td>Release the kill switch on <a href='/controls'>Controls</a>.</td></tr>
<tr><td>Draft cannot be approved</td><td>The lint found errors (merge tags, banned phrases, unverified recipient). Edit and retry.</td></tr>
<tr><td>AI not connected</td><td>Pick a provider in <a href='/settings'>Settings</a> and press Test connection. Ollama is free and local.</td></tr>
<tr><td>Discovery returns little</td><td>OpenStreetMap coverage varies; try a different category or import a CSV.</td></tr></table></section>
<section><h2>Responsible use</h2><p class='muted'>A published email address is not consent. Use lawful bases, honour opt-outs immediately, keep volumes low, and follow Kenya’s Data Protection Act 2019 and the rules of any country you contact. See <a href='/compliance'>Compliance</a>.</p></section>"""

@router.get("/help", response_class=HTMLResponse)
def help_page():
    return _page("Help", "What Zero Hawk is, how it works, and how to fix the usual problems.", HELP)
