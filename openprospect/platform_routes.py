"""Dashboard surfaces for real mailbox, inbox, automation and compliance features."""
from .config import env_value
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from .db import connect, list_activity, log, is_suppressed, add_suppression
from .conversations import ensure_schema, list_conversations
from .messaging import email_status, imap_status, send_email, sync_imap
from .automation import run_once, start_loop, pause_loop, loop_status
from .compliance import dns_report, privacy_checklist
from .security import get_dashboard_token

router=APIRouter()
def page(title,body):
    from .app import shell
    return shell(f"<h1>{title}</h1>{body}")

@router.get("/inbox",response_class=HTMLResponse)
def inbox():
    ensure_schema(); rows=list_conversations()
    body="".join(f"<section><b>{r['channel'].upper()} · {r['contact_address']}</b><p>{r['subject']}</p><p>{r['last_message'][:800]}</p><small>{r['updated_at']} · {r['status']}</small></section>" for r in rows)
    s=email_status(); m=imap_status()
    body+=f"<section><h2>Mailbox connections</h2><p>SMTP: {'Configured' if s['configured'] else 'Not connected'} · IMAP: {'Configured' if m['configured'] else 'Not connected'}</p><p>Configure ZERO_HAWK_SMTP_* and ZERO_HAWK_IMAP_* environment variables, then restart.</p><form method='post' action='/inbox/sync'><button>Sync IMAP now</button></form></section>"
    return page("Unified conversations",body or "<p>No conversations yet. Connect IMAP or the WhatsApp sidecar to receive messages.</p>")

@router.post("/inbox/sync",response_class=HTMLResponse)
def inbox_sync():
    try: result=sync_imap()
    except Exception as exc: return page("IMAP sync",f"<p class='warning'>Sync failed: {exc}</p><a href='/inbox'>Back</a>")
    return page("IMAP sync",f"<p>New messages imported: {result['synced']}</p><a href='/inbox'>Open inbox</a>")

@router.get("/controls",response_class=HTMLResponse)
def controls():
    state=loop_status()
    enabled=state["enabled"]
    status="ACTIVE" if enabled else "OFF"
    color="var(--green)" if enabled else "var(--muted)"
    last=state.get("last_completed") or "Not run yet"
    body=f"""<section class='control-hero'>
      <div style='display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap'>
        <div><span class='pill' style='color:{color}'>● {status}</span><h2 style='margin:10px 0 2px'>Autopilot</h2>
        <p class='muted'>Runs a safe research cycle automatically. You remain in control of every message.</p></div>
        <form method='post' action='/controls/{'pause' if enabled else 'start'}'>
          <button style='min-width:150px;background:{'var(--red)' if enabled else 'var(--green)'}'>{'Turn Autopilot OFF' if enabled else 'Turn Autopilot ON'}</button>
        </form>
      </div>
      <div class='grid' style='margin-top:16px'>
        <div class='card'><div class='lbl'>Heartbeat</div><div class='number'>15 min</div><div class='sub'>Minimum interval</div></div>
        <div class='card'><div class='lbl'>Last cycle</div><div class='number' style='font-size:18px'>{state.get('last_processed',0)} profiled</div><div class='sub'>{last}</div></div>
        <div class='card'><div class='lbl'>Batch size</div><div class='number'>{state['batch_size']}</div><div class='sub'>Companies per cycle</div></div>
      </div>
      <form method='post' action='/controls/configure' style='margin-top:16px'>
        <label>Companies to profile per cycle</label><input type='number' name='batch_size' min='1' max='25' value='{state['batch_size']}'>
        <label>Heartbeat interval</label><select name='interval_seconds'><option value='900' {'selected' if state['interval_seconds']==900 else ''}>Every 15 minutes</option><option value='1800' {'selected' if state['interval_seconds']==1800 else ''}>Every 30 minutes</option><option value='3600' {'selected' if state['interval_seconds']==3600 else ''}>Every hour</option><option value='21600' {'selected' if state['interval_seconds']==21600 else ''}>Every 6 hours</option></select>
        <button class='secondary'>Save Autopilot settings</button>
      </form>
      <form method='post' action='/controls/run'><button class='secondary'>Run one cycle now</button></form>
    </section>
    <section><h2>What Autopilot does</h2><ul><li>Profiles saved public business websites</li><li>Captures evidence-backed website signals</li><li>Updates activity and research history</li><li>Respects the global send kill switch</li></ul><p class='warning'>Autopilot does not discover new prospects, generate campaigns, reply to inboxes, or send messages automatically. Outbound email and WhatsApp remain manual and approval-gated.</p></section>
    <section><h2>Global send kill switch</h2><p>Outbound email is <b>{'PAUSED' if __import__('openprospect.sendpolicy',fromlist=['x']).is_paused() else 'available (approval-first)'}</b>.</p><form method='post' action='/controls/kill' class='inline'><button style='background:var(--red)'>Pause all sending</button></form> <form method='post' action='/controls/resume' class='inline'><button class='secondary'>Resume sending</button></form></section>"""
    return page("Autonomous controls",body)

@router.post("/controls/start")
def controls_start():
    state=loop_status();start_loop(state['interval_seconds'],state['batch_size']);return RedirectResponse("/controls",303)
@router.post("/controls/pause")
def controls_pause():
    pause_loop();return RedirectResponse("/controls",303)
@router.post("/controls/configure")
def controls_configure(batch_size:int=Form(5),interval_seconds:int=Form(900)):
    state=loop_status()
    if state['enabled']:
        pause_loop();start_loop(interval_seconds,batch_size)
    else:
        from .automation import _write_settings
        _write_settings(interval_seconds=max(900,min(interval_seconds,86400)),batch_size=max(1,min(batch_size,25)))
    return RedirectResponse("/controls",303)
@router.post("/controls/run",response_class=HTMLResponse)
def controls_run():
    result=run_once()
    return page("Pipeline run",f"<p>Companies profiled: {result.get('processed',0)}</p><pre>{result.get('errors',[])}</pre><a href='/controls'>Back</a>")

@router.get("/compliance",response_class=HTMLResponse)
def compliance():
    items="".join(f"<li>{x['item']}</li>" for x in privacy_checklist())
    return page("Compliance & DNS",f"<section><h2>DNS checks</h2><form method='post' action='/compliance/dns'><input name='domain' placeholder='example.com' required><button>Check SPF, DMARC and MX</button></form><p>DKIM requires your provider's selector and is not guessed.</p></section><section><h2>Privacy readiness checklist</h2><ul>{items}</ul><p class='muted'>Operational checklist only, not legal advice. Review Kenya's Data Protection Act and ODPC guidance with qualified counsel.</p></section>")

@router.post("/compliance/dns",response_class=HTMLResponse)
def compliance_dns(domain:str=Form(...)):
    try: data=dns_report(domain)
    except Exception as exc: return page("DNS report",f"<p class='warning'>{exc}</p><a href='/compliance'>Back</a>")
    rows="".join(f"<tr><td>{k.upper()}</td><td>{v['status']}</td><td>{', '.join(v['records']) or 'No record returned'}</td></tr>" for k,v in data.items() if isinstance(v,dict))
    return page("DNS report",f"<section><p>Domain: {data['domain']}</p><table><tr><th>Record</th><th>Status</th><th>Evidence</th></tr>{rows}</table><p>{data['notes']}</p></section><a href='/compliance'>Check another domain</a>")

@router.get("/connections",response_class=HTMLResponse)
def connections():
    from .messaging import email_status,imap_status
    smtp=email_status();imap=imap_status()
    return page("Connections",f"<section><h2>Email</h2><p>SMTP: {'Configured' if smtp['configured'] else 'Not connected'}</p><p>IMAP: {'Configured' if imap['configured'] else 'Not connected'}</p><p>Missing SMTP variables: {', '.join(smtp['missing']) or 'None'}</p><p>Missing IMAP variables: {', '.join(imap['missing']) or 'None'}</p><p>Credentials are read from environment variables; never paste them into the dashboard.</p></section><section><h2>WhatsApp</h2><p>Baileys sidecar: not connected until separately installed, paired and health-checked.</p><p>Cloud API: not connected until access token, phone-number ID and webhook are configured.</p></section>")

@router.post("/drafts/{draft_id}/send",response_class=HTMLResponse)
def send_approved_draft(draft_id:int):
    import os
    from urllib.parse import quote
    from .db import set_draft_status
    from .messaging import send_email
    with connect() as c:
        row=c.execute("SELECT drafts.*,contacts.email,contacts.email_status,contacts.verified_at FROM drafts JOIN contacts ON contacts.id=drafts.contact_id WHERE drafts.id=?",(draft_id,)).fetchone()
    if not row: raise HTTPException(404,"Draft or linked contact not found.")
    if row["status"]!="approved": raise HTTPException(400,"Approve the draft before sending.")
    if row["email_status"]!="verified" or not row["verified_at"]: raise HTTPException(400,"Recipient must be verified in Zero Hawk first.")
    base=env_value("ZERO_HAWK_PUBLIC_BASE_URL","").rstrip("/")
    if not base.startswith("https://"): raise HTTPException(400,"Set ZERO_HAWK_PUBLIC_BASE_URL to a public HTTPS unsubscribe endpoint before sending.")
    url=base+"/unsubscribe?email="+quote(row["email"])
    try:
        result=send_email(to=row["email"],subject=row["subject"],body=row["body"],unsubscribe_url=url,verification={"address":row["email"],"status":"verified","catch_all":False},approved=True)
    except Exception as exc: return page("Email send",f"<p class='warning'>Not sent: {exc}</p><a href='/drafts'>Back</a>")
    set_draft_status(draft_id,"sent")
    return page("Email sent",f"<p>SMTP accepted the message to {row['email']}.</p><p>Message ID: {result['message_id']}</p><a href='/drafts'>Back</a>")

@router.get("/unsubscribe",response_class=HTMLResponse)
def unsubscribe(email:str):
    add_suppression(email,"Recipient used unsubscribe link")
    return HTMLResponse("<h1>Unsubscribed</h1><p>This address has been added to the Zero Hawk suppression list.</p>")

@router.post("/unsubscribe",response_class=HTMLResponse)
def unsubscribe_one_click(email:str=Form(...)):
    add_suppression(email,"Recipient used one-click email unsubscribe")
    return HTMLResponse("<h1>Unsubscribed</h1><p>This address has been added to the Zero Hawk suppression list.</p>")

@router.post("/api/whatsapp/inbound")
def whatsapp_inbound(payload:dict):
    import os, hmac
    # The security middleware checks the sidecar bearer token before this route.
    from .conversations import add_message
    add_message("whatsapp",str(payload.get("external_id","")),str(payload.get("address","")),str(payload.get("subject","WhatsApp")),str(payload.get("body","")),"inbound")
    return {"ok":True}

def _wa_request(path, payload=None):
    import os, json, urllib.request
    base=os.getenv("WA_SIDECAR_URL","http://127.0.0.1:8787").rstrip("/")
    token=os.getenv("WA_SIDECAR_TOKEN","")
    if not token: raise RuntimeError("WA_SIDECAR_TOKEN is not configured.")
    req=urllib.request.Request(base+path,data=json.dumps(payload or {}).encode() if payload is not None else None,headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"},method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req,timeout=15) as response:return json.loads(response.read().decode())
@router.get("/whatsapp",response_class=HTMLResponse)
def whatsapp_page():
    import os
    configured=bool(os.getenv("WA_SIDECAR_TOKEN"))
    try: state=_wa_request("/status") if configured else {"state":"not_configured"}
    except Exception as exc: state={"state":"unreachable","error":str(exc)}
    return page("WhatsApp connection",f"<section><p>Bridge status: <b>{state.get('state')}</b></p><p>{state.get('error',state.get('lastError',''))}</p><p>Pairing code: {state.get('pairingCode','not issued')}</p><form method='post' action='/whatsapp/pair'><input name='phone' placeholder='2547XXXXXXXX' required><button>Request pairing code</button></form><p class='warning'>Baileys is an unofficial WhatsApp Web client. Use at your own risk; WhatsApp may restrict accounts. Prefer the official Cloud API for production.</p></section><section><h2>Send an approved message</h2><form method='post' action='/whatsapp/send'><input name='to' placeholder='2547XXXXXXXX' required><textarea name='message' placeholder='Message text' required></textarea><label><input type='checkbox' name='approved' value='yes' required style='width:auto'> I approve sending this message now</label><button>Send WhatsApp message</button></form></section>")
@router.post("/whatsapp/pair",response_class=HTMLResponse)
def whatsapp_pair(phone:str=Form(...)):
    try: result=_wa_request("/pair",{"phone":phone})
    except Exception as exc: return page("WhatsApp pairing",f"<p class='warning'>Pairing unavailable: {exc}</p><a href='/whatsapp'>Back</a>")
    return page("WhatsApp pairing code",f"<h2>{result.get('pairingCode','')}</h2><p>On your phone: WhatsApp → Linked devices → Link a device → Link with phone number.</p><a href='/whatsapp'>Back</a>")
@router.post("/whatsapp/send",response_class=HTMLResponse)
def whatsapp_send(to:str=Form(...),message:str=Form(...),approved:str=Form("")):
    if approved!="yes": raise HTTPException(400,"Explicit approval is required.")
    try: result=_wa_request("/send",{"to":to,"text":message,"approved":True})
    except Exception as exc: return page("WhatsApp send",f"<p class='warning'>Not sent: {exc}</p><a href='/whatsapp'>Back</a>")
    return page("WhatsApp send",f"<p>Sidecar accepted message ID: {result.get('id')}</p><a href='/inbox'>Open inbox</a>")
