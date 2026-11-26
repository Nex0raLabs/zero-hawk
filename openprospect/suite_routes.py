"""Sellbird-style setup, calendar and TrulyInbox warmup integration."""
from __future__ import annotations
import html, json, os, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timedelta
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from .db import connect, log
from .config import env_value
from .ui import render_shell

router = APIRouter()

def e(v):
    return html.escape(str(v or ""), quote=True)

def page(body, path=None):
    if path is None:
        path = "/warmup" if ("Email warmup" in body or "Mailbox health" in body) else ("/calendar" if "<h1>Calendar" in body else "/setup")
    return HTMLResponse(render_shell(body, path))

def init_suite_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS zh_calendar_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
          starts_at TEXT NOT NULL, ends_at TEXT NOT NULL DEFAULT '',
          kind TEXT NOT NULL DEFAULT 'meeting', notes TEXT DEFAULT '',
          status TEXT DEFAULT 'scheduled', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS zh_booking_links(
          id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL,
          url TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)

def ti_request(path, method="GET", payload=None):
    key = env_value("ZERO_HAWK_TRULYINBOX_API_KEY", "") or ""
    workspace = env_value("ZERO_HAWK_TRULYINBOX_WORKSPACE_ID", "") or ""
    if not key or not workspace:
        raise RuntimeError("Add ZERO_HAWK_TRULYINBOX_API_KEY and ZERO_HAWK_TRULYINBOX_WORKSPACE_ID to your .env file. Keep the key private.")
    base = "https://lynx-api.trulyinbox.com/v2/workspaces/" + urllib.parse.quote(str(workspace), safe="")
    url = base + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + key, "Accept": "application/json",
        "Content-Type": "application/json"
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:1000]
        raise RuntimeError(f"TrulyInbox returned HTTP {exc.code}: {detail}")
    except Exception as exc:
        raise RuntimeError(f"Could not reach TrulyInbox: {exc}")
    if isinstance(result, dict) and result.get("success") is False:
        raise RuntimeError(result.get("errorMessage") or result.get("error", {}).get("message") or "TrulyInbox request failed.")
    return result.get("data", result) if isinstance(result, dict) else result

@router.get("/setup", response_class=HTMLResponse)
def setup_hub():
    init_suite_db()
    sections = [
      ("Get started", [("Install ZERO HAWK","Already complete","/"),("Add provider keys","SMTP, AI and address-checking settings","/settings"),("Connect your email","SMTP and IMAP mailbox connection","/connections"),("Train your company profile","Offer, ideal customer and writing voice","/train"),("Warm up your mailbox","TrulyInbox warmup integration","/warmup")]),
      ("Sending", [("Inboxes","Mailboxes and sending status","/connections"),("Domains and email records","SPF, DKIM, DMARC and MX checks","/settings"),("Sending mode and keys","Provider settings and API keys","/settings"),("Limits and rules","Daily limits, quiet hours and stop switch","/controls"),("Opt-outs and bounces","Suppression and unsubscribe controls","/compliance")]),
      ("Finding people", [("Your company","Company profile and offer","/train"),("Signals","Buying signals and evidence","/signals"),("Find businesses","Discover local businesses","/discover"),("People and contacts","Saved people and verification","/contacts")]),
      ("Inbound", [("Leads from forms","Inbound lead capture and routing","/inbox"),("Conversations","Email and WhatsApp inbox","/inbox"),("Brand mentions","Mention monitoring setup","/signals"),("Texting and consent","WhatsApp and contact permissions","/whatsapp")]),
      ("Your agent", [("Connect and permissions","AI provider and approval boundaries","/settings"),("Agent activity","Review actions and history","/activity"),("Autopilot","Start, pause and inspect the research loop","/controls")]),
      ("Account", [("Calendar and bookings","Meetings, schedule and booking link","/calendar"),("Engine","Automation status and event log","/controls"),("Events and webhooks","Outbound event integrations","/activity"),("Activity","Full action history","/activity"),("Help","Setup guide and local data","/help")]),
      ("Everything ZERO HAWK does", [("Feature suite","Companies, people, campaigns, warmup, inbox and analytics","/suite")])
    ]
    blocks = []
    for title, items in sections:
        rows = "".join(f"<li><span class='dot'></span><div style='flex:1'><b>{e(label)}</b><br><span class='muted'>{e(desc)}</span></div><a href='{e(url)}'>Open →</a></li>" for label,desc,url in items)
        blocks.append(f"<section><h2>{e(title)}</h2><ul class='steps'>{rows}</ul></section>")
    return page("<h1>Set up ZERO HAWK</h1><p class='muted'>A guided checklist for connecting your channels, configuring your agent and preparing your sales workspace.</p>" + "".join(blocks))

@router.get("/suite", response_class=HTMLResponse)
def suite_page():
    features = [
      ("Prospecting","Discover businesses, save companies, enrich public website signals and organize contacts.","/discover"),
      ("People","Contact records, email verification, suppression checks and CSV import/export.","/contacts"),
      ("Campaigns","Create campaigns, draft outreach and review before sending.","/campaigns"),
      ("Email sending","SMTP setup, inbox connection, approval-first sending and sending limits.","/connections"),
      ("Email warmup","TrulyInbox mailbox warmup, status, pause/resume and deliverability checks.","/warmup"),
      ("Inbound","Inbox conversations, WhatsApp connection and inbound messages.","/inbox"),
      ("Calendar","Schedule meetings, view a weekly calendar and manage booking links.","/calendar"),
      ("Automation","Autopilot controls, run history and safety rules.","/controls"),
      ("Analytics","Pipeline, activity and usage reporting.","/activity")
    ]
    cards = "".join(f"<section><h2>{e(t)}</h2><p class='muted'>{e(d)}</p><a href='{e(u)}'>Open feature →</a></section>" for t,d,u in features)
    return page("<h1>Everything ZERO HAWK does</h1><p class='muted'>Feature directory. Some integrations require external accounts and API credentials.</p><div class='cols'>" + cards + "</div>")

@router.get("/calendar", response_class=HTMLResponse)
def calendar_page(week: str = ""):
    init_suite_db()
    try:
        anchor = datetime.fromisoformat(week).date() if week else datetime.now().date()
    except ValueError:
        anchor = datetime.now().date()
    monday = anchor - timedelta(days=anchor.weekday())
    sunday = monday + timedelta(days=6)
    start = datetime.combine(monday, datetime.min.time()).isoformat(timespec="minutes")
    end = datetime.combine(sunday + timedelta(days=1), datetime.min.time()).isoformat(timespec="minutes")
    with connect() as c:
        events = [dict(x) for x in c.execute("SELECT * FROM zh_calendar_events WHERE starts_at>=? AND starts_at<? ORDER BY starts_at", (start,end))]
        links = [dict(x) for x in c.execute("SELECT * FROM zh_booking_links WHERE active=1 ORDER BY id DESC")]
    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        day_events = [x for x in events if x["starts_at"][:10] == day.isoformat()]
        cells = "".join(f"<div class='card' style='padding:8px;margin:4px 0'><b>{e(x['title'])}</b><br><small>{e(x['starts_at'][11:16])} · {e(x['kind'])}</small></div>" for x in day_events)
        days.append(f"<section style='min-width:130px;flex:1'><b>{day.strftime('%a %d')}</b>{cells or '<p class=muted style=margin-top:12px>No events</p>'}</section>")
    event_rows = "".join(f"<tr><td>{e(x['title'])}</td><td>{e(x['starts_at'])}</td><td>{e(x['kind'])}</td><td>{e(x['status'])}</td></tr>" for x in events)
    link_rows = "".join(f"<li><a href='{e(x['url'])}' target='_blank' rel='noopener'>{e(x['label'])}</a></li>" for x in links)
    prev = (monday - timedelta(days=7)).isoformat()
    nxt = (monday + timedelta(days=7)).isoformat()
    body = f"""<h1>Calendar</h1><p class='muted'>{len(events)} scheduled events · {monday.strftime('%b %d')}–{sunday.strftime('%b %d, %Y')}</p>
    <section><div style='display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap'><a class='pill info' href='/calendar?week={prev}'>← Previous</a><a href='/calendar'>Today</a><a class='pill info' href='/calendar?week={nxt}'>Next →</a></div>
    <div style='display:flex;gap:8px;overflow-x:auto;margin-top:16px'>{''.join(days)}</div></section>
    <div class='cols'><section><h2>Add event or meeting</h2><form method='post' action='/calendar/events'><label>Title</label><input name='title' required placeholder='Discovery call with client'><label>Start time</label><input type='datetime-local' name='starts_at' required><label>End time</label><input type='datetime-local' name='ends_at'><label>Type</label><select name='kind'><option value='meeting'>Meeting</option><option value='call'>Call</option><option value='follow-up'>Follow-up</option><option value='task'>Task</option></select><label>Notes</label><textarea name='notes'></textarea><button>Save to calendar</button></form></section>
    <section><h2>Booking link</h2><p class='muted'>Save your external booking page so you can share it with prospects. This does not create a public booking service by itself.</p><form method='post' action='/calendar/booking'><input name='label' placeholder='Booking page name' required><input name='url' type='url' placeholder='https://cal.com/yourname' required><button>Save booking link</button></form><ul>{link_rows or '<li class=muted>No booking link saved yet.</li>'}</ul></section></div>
    <section><h2>Meetings this week</h2><table><tr><th>Meeting</th><th>Starts</th><th>Type</th><th>Status</th></tr>{event_rows or '<tr><td colspan=4>No meetings booked yet</td></tr>'}</table></section>"""
    return page(body, "/calendar")

@router.post("/calendar/events")
def add_calendar_event(title:str=Form(...), starts_at:str=Form(...), ends_at:str=Form(""), kind:str=Form("meeting"), notes:str=Form("")):
    init_suite_db()
    try:
        start = datetime.fromisoformat(starts_at)
        if ends_at and datetime.fromisoformat(ends_at) < start:
            raise ValueError("End time must be after start time.")
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    with connect() as c:
        c.execute("INSERT INTO zh_calendar_events(title,starts_at,ends_at,kind,notes) VALUES(?,?,?,?,?)", (title.strip(), starts_at, ends_at, kind, notes))
    log("calendar_event_created", title)
    return RedirectResponse("/calendar",303)

@router.post("/calendar/booking")
def save_booking_link(label:str=Form(...), url:str=Form(...)):
    init_suite_db()
    if not url.startswith(("https://","http://")):
        raise HTTPException(400,"Enter a valid booking URL.")
    with connect() as c:
        c.execute("INSERT INTO zh_booking_links(label,url) VALUES(?,?)", (label.strip(),url.strip()))
    log("booking_link_saved", label)
    return RedirectResponse("/calendar",303)

@router.get("/warmup", response_class=HTMLResponse)
def warmup_page():
    configured = bool(env_value("ZERO_HAWK_TRULYINBOX_API_KEY","") and env_value("ZERO_HAWK_TRULYINBOX_WORKSPACE_ID",""))
    if not configured:
        return page("""<h1>Email warmup · TrulyInbox</h1><p class='muted'>Connect your TrulyInbox workspace to manage mailbox warmup from ZERO HAWK.</p>
        <section><h2>Connect TrulyInbox</h2><p>Add these values to your local <code>.env</code> file, then restart ZERO HAWK.</p>
        <pre>ZERO_HAWK_TRULYINBOX_API_KEY=your_workspace_or_personal_api_key
ZERO_HAWK_TRULYINBOX_WORKSPACE_ID=your_numeric_workspace_id</pre>
        <p><a href='https://dev.trulyinbox.com/docs' target='_blank' rel='noopener'>TrulyInbox API documentation →</a></p>
        <p class='warning'>The API key is read only by the local backend. Never paste it into browser code or commit it to GitHub. TrulyInbox API access and warmup availability depend on your TrulyInbox plan.</p></section>""")
    try:
        data = ti_request("/accounts?page=1&limit=50")
        accounts = data if isinstance(data,list) else data.get("accounts", data.get("items", [])) if isinstance(data,dict) else []
        if isinstance(data,dict) and not accounts and isinstance(data.get("data"),list): accounts=data["data"]
    except Exception as exc:
        return page(f"<h1>Email warmup · TrulyInbox</h1><section><p class='warning'>Connection error: {e(exc)}</p><p>Check the API key, workspace ID, scopes and subscription.</p><a href='https://dev.trulyinbox.com/docs' target='_blank'>Open API docs →</a></section>")
    rows = ""
    for a in accounts:
        ident = a.get("id")
        status = a.get("warmupStatus","Unknown")
        rows += f"<tr><td>{e(a.get('emailAddress','Unknown mailbox'))}</td><td>{e(a.get('provider',''))}</td><td>{e(a.get('status',''))}</td><td>{e(status)}</td><td><form class='inline' method='post' action='/warmup/{ident}/enable'><button>Enable warmup</button></form> <form class='inline' method='post' action='/warmup/{ident}/pause'><button class='secondary'>Pause</button></form> <a href='/warmup/{ident}/health'>Health</a></td></tr>"
    return page(f"<h1>Email warmup · TrulyInbox</h1><p class='muted'>{len(accounts)} mailboxes returned by your workspace.</p><section><table><tr><th>Mailbox</th><th>Provider</th><th>Connection</th><th>Warmup</th><th>Actions</th></tr>{rows or '<tr><td colspan=5>No mailboxes found. Connect one in TrulyInbox first.</td></tr>'}</table></section><p class='muted'>Warmup status is reported by TrulyInbox. Start/resume and pause actions call the live API and may be subject to plan limits.</p>")

@router.post("/warmup/{account_id}/enable")
def warmup_enable(account_id:int):
    try:
        # First-time enable is the documented action; resume is used after pause.
        result = ti_request(f"/accounts/{account_id}/warmup/enable", "POST")
        log("trulyinbox_warmup_enable", str(account_id))
    except Exception as exc:
        raise HTTPException(502, str(exc))
    return RedirectResponse("/warmup",303)

@router.post("/warmup/{account_id}/pause")
def warmup_pause(account_id:int):
    try:
        ti_request(f"/accounts/{account_id}/warmup/pause", "POST")
        log("trulyinbox_warmup_pause", str(account_id))
    except Exception as exc:
        raise HTTPException(502, str(exc))
    return RedirectResponse("/warmup",303)

@router.get("/warmup/{account_id}/health", response_class=HTMLResponse)
def warmup_health(account_id:int):
    try:
        score = ti_request(f"/accounts/{account_id}/setup-score")
        deliverability = ti_request(f"/accounts/{account_id}/deliverability")
        stats = ti_request(f"/accounts/{account_id}/analytics/stats")
        body = f"<h1>Mailbox health</h1><section><h2>Setup score</h2><pre>{e(json.dumps(score,indent=2))}</pre></section><section><h2>Deliverability</h2><pre>{e(json.dumps(deliverability,indent=2))}</pre></section><section><h2>Warmup statistics</h2><pre>{e(json.dumps(stats,indent=2))}</pre></section><a href='/warmup'>Back to warmup</a>"
        return page(body)
    except Exception as exc:
        return page(f"<h1>Mailbox health</h1><p class='warning'>{e(exc)}</p><a href='/warmup'>Back</a>")
