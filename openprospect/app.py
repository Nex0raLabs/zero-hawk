from __future__ import annotations
import csv,html,io
from fastapi import FastAPI,Form,HTTPException,File,UploadFile
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse,Response
from .db import (add_company,list_companies,connect,add_contact,list_contacts,
 add_campaign,list_campaigns,add_draft,list_drafts,set_draft_status,
 add_suppression,list_activity,is_suppressed,log,find_company_duplicate,save_company_observations,set_contact_email_status,set_contact_email)
from .ai import ask_ai
from .discovery import discover_osm
from .profiling import profile_website
from .verification import verify_email,learn_email_pattern,guess_email
from urllib.parse import urlsplit

app=FastAPI(title="Zero Hawk",version="0.2.0")
CSS="""<style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#121b2b;--line:#27364b;--muted:#91a0b7;--accent:#6ea8fe;--green:#42d392}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#17243a 0,#0b1020 55%);color:#e8eef8;font:15px Inter,ui-sans-serif,system-ui,sans-serif}header{position:sticky;top:0;z-index:5;padding:17px 4%;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);background:#0b1020ef;backdrop-filter:blur(16px)}.brand{font-size:23px;font-weight:850;letter-spacing:-.8px}small,.muted{color:var(--muted)}nav{position:sticky;top:70px;z-index:4;padding:12px 4%;display:flex;gap:8px;flex-wrap:wrap;border-bottom:1px solid var(--line);background:#0b1020ef;backdrop-filter:blur(16px)}nav a{padding:8px 12px;border:1px solid var(--line);border-radius:999px;font-size:13px}a{color:var(--accent);text-decoration:none}a:hover{color:#c2dcff}main{max-width:1440px;margin:30px auto;padding:0 26px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}.card,section{background:linear-gradient(145deg,#172337,#111a29);border:1px solid var(--line);border-radius:16px;padding:20px;margin-bottom:16px;box-shadow:0 12px 36px #0003}h1{font-size:clamp(27px,4vw,38px);letter-spacing:-1.1px;margin:0 0 10px}.number{font-size:36px;font-weight:850;letter-spacing:-1px;margin-top:8px}input,textarea,select,button{font:inherit;padding:11px 12px;border-radius:9px;border:1px solid #34445d;background:#0b1321;color:#e8eef8;width:100%;margin:5px 0}textarea{min-height:100px}button{width:auto;background:#2563eb;border:0;font-weight:700;cursor:pointer;padding:11px 17px}button:hover{filter:brightness(1.12)}button.secondary{background:#334155}table{width:100%;border-collapse:collapse;display:block;overflow-x:auto;font-size:14px}td,th{text-align:left;padding:11px;border-bottom:1px solid var(--line);vertical-align:top}form.inline{display:inline}.tag{color:var(--green)}.warning{color:#fbbf24}.muted{line-height:1.55}@media(max-width:650px){header{align-items:flex-start;flex-direction:column;gap:7px}nav{top:83px;overflow-x:auto;flex-wrap:nowrap}nav a{white-space:nowrap}main{padding:0 14px;margin:20px auto}.card,section{padding:16px}}
</style>"""



@app.get("/brand.svg", include_in_schema=False)
def brand_icon():
 return Response(content='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect width="256" height="256" rx="54" fill="#0b0f12"/><path fill="#B7F34A" d="M30 63 119 105 81 121 27 102 83 143 31 191 129 148 101 130 158 119 221 85 177 79 148 91 103 70Z"/><path fill="#F4F7EF" d="m101 130 47-39 32-8 34 5 20 15-23 7-18 25-30 20-39-4 25-17-31 2-36 27 19-33Z"/><path fill="#0b0f12" d="m190 94 24 8-18 5-14-7Z"/><path fill="#B7F34A" d="m177 111 34 7-25 12-20-6Z"/></svg>''', media_type="image/svg+xml")

def esc(v):return html.escape(str(v or ""),quote=True)
def shell(body):
 return f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Zero Hawk — Prospecting Workspace</title>{CSS}</head><body><header><div><div class="brand"><span style="display:inline-flex;align-items:center;gap:10px"><img src="/brand.svg" width="34" height="34" alt="" style="vertical-align:middle"><span>ZERO HAWK</span></span></div><small>Local-first prospecting command centre</small></div><small>Private workspace · Human approval · No automatic campaign sending</small></header><nav><a href="/">Today</a><a href="/train">Train</a><a href="/discover">Discover</a><a href="/signals">Signals</a><a href="/companies">Companies</a><a href="/contacts">Contacts</a><a href="/campaigns">Campaigns</a><a href="/drafts">Outbox</a><a href="/inbox">Inbox</a><a href="/controls">Controls</a><a href="/compliance">Compliance</a><a href="/connections">Connections</a><a href="/whatsapp">WhatsApp</a><a href="/activity">Activity</a><a href="/settings">Settings</a></nav><main>{body}</main></body></html>'

def company_table(items):
 if not items:return "<p class='muted'>No companies yet. Add one or use Discover.</p>"
 rows="".join(f"<tr><td><b>{esc(x['name'])}</b><br><small>#{x['id']} · {esc(x['source'])}</small></td><td>{esc(x['website']) or '—'}</td><td>{esc(x['industry'])}</td><td>{esc(x['location'])}</td><td>{esc(x.get('phone',''))}</td><td><a href='/company/{x['id']}'>Open</a></td></tr>" for x in items)
 return f"<table><tr><th>Company</th><th>Website</th><th>Industry</th><th>Location</th><th>Phone</th><th></th></tr>{rows}</table>"

@app.get("/",response_class=HTMLResponse)
def home():
 companies=list_companies(10000);contacts=list_contacts(10000);drafts=list_drafts();campaigns=list_campaigns()
 pending=sum(1 for d in drafts if d["status"]=="draft")
 return shell(f"<h1>Today</h1><p class='muted'>Your local prospecting workspace. Review evidence, organise contacts and send only explicitly approved, verified messages.</p><div class='grid'><div class='card'>Companies<div class='number'>{len(companies)}</div></div><div class='card'>Contacts<div class='number'>{len(contacts)}</div></div><div class='card'>Campaigns<div class='number'>{len(campaigns)}</div></div><div class='card'>Drafts awaiting review<div class='number'>{pending}</div></div></div><section><h2>Get started</h2><p><a href='/discover'>Discover businesses</a> using free OpenStreetMap data, or <a href='/companies'>add a company manually</a>.</p><p class='muted'>Coverage depends on community map data. Businesses with websites can still be found; a website is not evidence of consent to marketing.</p></section><section><h2>Recent companies</h2>{company_table(companies[:12])}</section><section><h2>Safety</h2><p class='warning'>Outbound email requires SMTP configuration, verified recipients, explicit draft approval and a public HTTPS unsubscribe URL.</p></section>")

@app.get("/discover",response_class=HTMLResponse)
def discover_page():
 return shell("""<h1>Discover businesses</h1><p class='muted'>Free OpenStreetMap discovery. Searches a 10 km radius around the place you enter. Results depend on OpenStreetMap coverage and are not a complete business directory.</p><section><form method='post' action='/discover'><label>City or place</label><input name='city' placeholder='Nairobi, Kenya' required><label>Business category</label><select name='category'><option>any business</option><option>restaurant</option><option>cafe</option><option>hotel</option><option>shop</option><option>beauty</option><option>clinic</option><option>dentist</option><option>school</option><option>gym</option><option>supermarket</option></select><label>Maximum results</label><input name='limit' type='number' min='1' max='200' value='50'><button>Search free map data</button></form></section><p><a href='/companies'>View saved companies</a></p>""")

@app.post("/discover",response_class=HTMLResponse)
def discover_run(city:str=Form(...),category:str=Form("any business"),limit:int=Form(50)):
 try: results=discover_osm(city,category,limit)
 except Exception as e:return shell(f"<h1>Discovery issue</h1><p class='warning'>{esc(e)}</p><a href='/discover'>Try again</a>")
 saved=0
 for x in results:
  # Deduplicate against a normalized company domain or phone number.
  if find_company_duplicate(x["website"],x["phone"]):continue
  add_company(x["name"],x["website"],x["category"],x["address"] or city,"", "openstreetmap",x["source_url"],x["phone"],x["email"],x["socials"]);saved+=1
 rows="".join(f"<tr><td>{esc(x['name'])}</td><td>{esc(x['category'])}</td><td>{esc(x['website']) or 'No website listed'}</td><td>{esc(x['phone'])}</td></tr>" for x in results)
 log("discovery_completed",f"{city}: {len(results)} found, {saved} new")
 return shell(f"<h1>Discovery complete</h1><p>Found {len(results)} map entries; saved {saved} new companies.</p><section><table><tr><th>Name</th><th>Category</th><th>Website</th><th>Phone</th></tr>{rows}</table></section><a href='/companies'>Open company register</a> · <a href='/discover'>Search again</a>")

@app.get("/companies",response_class=HTMLResponse)
def companies_page():return shell("<h1>Companies</h1>"+company_table(list_companies(10000))+"""<section><h2>Add company manually</h2><form method='post' action='/companies'><input name='name' placeholder='Business name' required><input name='website' placeholder='https://example.com'><input name='industry' placeholder='Industry'><input name='location' placeholder='City, country'><input name='phone' placeholder='Public business phone'><input name='email' placeholder='Published business email'><input name='socials' placeholder='Public social links'><textarea name='notes' placeholder='Notes and source context'></textarea><button>Add company</button></form><p><a href='/export/companies.csv'>Export companies as CSV</a></p><form method='post' action='/import/companies.csv' enctype='multipart/form-data'><label>Import companies CSV</label><input type='file' name='file' accept='.csv,text/csv' required><button>Import CSV</button></form></section>""")

@app.post("/companies")
def create_company(name:str=Form(...),website:str=Form(""),industry:str=Form(""),location:str=Form(""),notes:str=Form(""),phone:str=Form(""),email:str=Form(""),socials:str=Form("")):
 add_company(name,website,industry,location,notes,"manual","",phone,email,socials);return RedirectResponse("/companies",303)

@app.get("/company/{company_id}",response_class=HTMLResponse)
def company_detail(company_id:int):
 with connect() as c:
  row=c.execute("SELECT * FROM companies WHERE id=?",(company_id,)).fetchone()
  contacts=[dict(x) for x in c.execute("SELECT * FROM contacts WHERE company_id=? ORDER BY id DESC",(company_id,))]
 if not row:raise HTTPException(404,"Company not found")
 x=dict(row)
 profile=f"<section><h2>Website profile</h2><form method='post' action='/company/{company_id}/profile'><button>Read public website</button></form><p class='muted'>Fetches the public homepage only. Respect robots.txt, site terms and rate limits; this is not a verification of contact consent.</p></section>" if x["website"] else ""
 cs="".join(f"<tr><td>{esc(c['name'])}</td><td>{esc(c['title'])}</td><td>{esc(c['email'])}</td><td>{esc(c['email_status'])}</td></tr>" for c in contacts)
 website_link=('<a href="'+esc(x["website"])+'" rel="noreferrer">'+esc(x["website"])+'</a>') if x["website"].startswith(("http://","https://")) else esc(x["website"]) or "Not recorded"
 return shell(f"<h1>{esc(x['name'])}</h1><p class='muted'>{esc(x['industry'])} · {esc(x['location'])} · Source: {esc(x['source'])}</p><section><p>Website: {website_link}</p><p>Public phone: {esc(x.get('phone','')) or 'Not recorded'} · Public email: {esc(x.get('email','')) or 'Not recorded'}</p><p>Socials: {esc(x.get('socials','')) or 'Not recorded'}</p><p>{esc(x['notes'])}</p><small>Source record: {esc(x['source_url'])}</small></section>{profile}<section><h2>Add contact</h2><form method='post' action='/company/{company_id}/contacts'><input name='name' placeholder='Contact name'><input name='title' placeholder='Role / title'><input name='email' placeholder='Email (only if lawfully obtained)'><input name='phone' placeholder='Phone'><input name='source_url' placeholder='Public source URL'><select name='email_status'><option>unknown</option><option>unverified</option><option>verified</option><option>risky</option><option>guess</option><option>invalid</option></select><textarea name='notes' placeholder='Notes'></textarea><button>Save contact</button></form></section><section><h2>Contacts</h2><table><tr><th>Name</th><th>Role</th><th>Email</th><th>Status</th></tr>{cs}</table></section><section><h2>Create an outreach draft</h2><form method='post' action='/company/{company_id}/draft'><input name='contact_id' type='number' placeholder='Contact ID (optional)'><input name='subject' placeholder='Subject'><textarea name='context' placeholder='Your offer and relevant context'></textarea><button>Create AI draft</button></form></section>")

@app.post("/company/{company_id}/contacts")
def create_contact(company_id:int,name:str=Form(""),title:str=Form(""),email:str=Form(""),phone:str=Form(""),source_url:str=Form(""),email_status:str=Form("unknown"),notes:str=Form("")):
 with connect() as c:
  if not c.execute("SELECT id FROM companies WHERE id=?",(company_id,)).fetchone():raise HTTPException(404,"Company not found")
  if email and is_suppressed(email):raise HTTPException(400,"This address is on your suppression list.")
 add_contact(company_id,name,title,email,phone,source_url,email_status,notes);return RedirectResponse(f"/company/{company_id}",303)

@app.post("/company/{company_id}/profile",response_class=HTMLResponse)
def profile_company(company_id:int):
 with connect() as c:row=c.execute("SELECT * FROM companies WHERE id=?",(company_id,)).fetchone()
 if not row:raise HTTPException(404,"Company not found")
 data=profile_website(row["website"])
 if data.get("error"):return shell(f"<h1>Website profile</h1><p class='warning'>{esc(data['error'])}</p><a href='/company/{company_id}'>Back</a>")
 save_company_observations(company_id,data.get("signals",[]))
 signal_rows="".join(f"<tr><td>{esc(s['label'])}</td><td>{s['weight']}</td><td>{s['confidence']:.0%}</td><td><a href='{esc(s['evidence_url'])}'>Evidence</a></td></tr>" for s in data.get("signals",[]))
 return shell(f"<h1>Website profile: {esc(row['name'])}</h1><section><p><b>{esc(data['title'])}</b></p><p>{esc(data['description'])}</p><p>Fetched: <a href='{esc(data['url'])}'>{esc(data['url'])}</a></p><p>Opportunity score: <b>{data['score']}/100</b> · Pages read: {len(data['pages'])} · Load: {data['load_seconds']}s</p><h3>Buying signals</h3><table><tr><th>Signal</th><th>Weight</th><th>Confidence</th><th>Evidence</th></tr>{signal_rows or '<tr><td colspan=4>No enabled signals found</td></tr>'}</table><h3>Public email strings found (unverified)</h3><ul>{''.join('<li>'+esc(e)+'</li>' for e in data['emails']) or '<li>None found</li>'}</ul><h3>Possible phone strings (unverified)</h3><ul>{''.join('<li>'+esc(p)+'</li>' for p in data['phones']) or '<li>None found</li>'}</ul><h3>Page text excerpt</h3><p>{esc(data['text'][:5000])}</p></section><a href='/company/{company_id}'>Back to company</a>")

@app.get("/contacts",response_class=HTMLResponse)
def contacts_page():
 rows=list_contacts()
 def actions(x):
  verify=f"<form method='post' action='/contact/{x['id']}/verify'><button>Verify</button></form>" if x.get("email") else ""
  guess=f"<form method='post' action='/contact/{x['id']}/guess'><button>Guess email</button></form>" if not x.get("email") else ""
  return verify+guess
 body="".join(f"<tr><td>{esc(x['name'])}</td><td>{esc(x['company_name'])}</td><td>{esc(x['title'])}</td><td>{esc(x['email'])}</td><td>{esc(x['email_status'])}<br><small>{esc(x.get('email_verification_reason',''))}</small></td><td>{actions(x)}</td><td><a href='/company/{x['company_id']}'>Company</a></td></tr>" for x in rows)
 return shell("<h1>Contacts</h1><p class='muted'>Use Verify for syntax, disposable-domain, MX and (where network policy allows) SMTP RCPT checks. Only verified non-catch-all addresses are deliverable.</p><table><tr><th>Name</th><th>Company</th><th>Role</th><th>Email</th><th>Status / reason</th><th>Check</th><th></th></tr>"+body+"</table><p><a href='/export/contacts.csv'>Export contacts CSV</a></p><section><h2>Import contacts CSV</h2><form method='post' action='/import/contacts.csv' enctype='multipart/form-data'><input type='file' name='file' accept='.csv,text/csv' required><button>Import contacts</button></form></section>")

@app.post("/contact/{contact_id}/verify",response_class=HTMLResponse)
def verify_contact(contact_id:int):
 with connect() as conn: row=conn.execute("SELECT * FROM contacts WHERE id=?",(contact_id,)).fetchone()
 if not row: raise HTTPException(404,"Contact not found.")
 if not row["email"]: raise HTTPException(400,"This contact has no email address.")
 result=verify_email(row["email"],is_guess=row["email_status"]=="guess")
 set_contact_email_status(contact_id,result["status"],result["reason"])
 return shell(f"<h1>Email verification</h1><p><b>{esc(result['address'])}</b></p><p>Status: <b>{esc(result['status'])}</b></p><p>{esc(result['reason'])}</p><p>MX found: {result['mx_found']} · Role account: {result['role_account']} · Catch-all: {result['catch_all']}</p><a href='/contacts'>Back to contacts</a>")

@app.post("/contact/{contact_id}/guess",response_class=HTMLResponse)
def guess_contact_email(contact_id:int):
 with connect() as conn:
  contact=conn.execute("SELECT contacts.*,companies.website FROM contacts JOIN companies ON companies.id=contacts.company_id WHERE contacts.id=?",(contact_id,)).fetchone()
  samples=[dict(x) for x in conn.execute("SELECT name,email FROM contacts WHERE company_id=? AND email<>'' AND email_status<>'guess'",(contact["company_id"],)).fetchall()] if contact else []
 if not contact: raise HTTPException(404,"Contact not found.")
 if contact["email"]: raise HTTPException(400,"This contact already has an email address.")
 website=contact["website"] or ""
 if not website: raise HTTPException(400,"A company website is required to generate an email guess.")
 domain=urlsplit(website if "://" in website else "https://"+website).hostname or ""
 name=(contact["name"] or "").split()
 if not name: raise HTTPException(400,"A contact name is required.")
 pattern=learn_email_pattern(samples)
 guess=guess_email(name[0],name[-1] if len(name)>1 else "",domain,pattern)
 reason=f"Generated guess using {guess['pattern']} pattern. Verify before use."
 set_contact_email(contact_id,guess["address"],"guess",reason)
 return shell(f"<h1>Email guess created</h1><p>{esc(guess['address'])}</p><p>Status: guess — not deliverable until verified.</p><p>{esc(reason)}</p><a href='/contacts'>Back to contacts</a>")

@app.get("/campaigns",response_class=HTMLResponse)
def campaigns_page():
 rows="".join(f"<tr><td>{esc(x['name'])}</td><td>{esc(x['description'])}</td><td>{esc(x['status'])}</td></tr>" for x in list_campaigns())
 return shell("<h1>Campaigns</h1><section><form method='post' action='/campaigns'><input name='name' placeholder='Campaign name' required><textarea name='description' placeholder='Goal, target audience and offer'></textarea><button>Create campaign</button></form></section><table><tr><th>Name</th><th>Description</th><th>Status</th></tr>"+rows+"</table>")
@app.post("/campaigns")
def create_campaign_route(name:str=Form(...),description:str=Form("")):
 add_campaign(name,description);return RedirectResponse("/campaigns",303)

@app.post("/company/{company_id}/draft")
def create_company_draft(company_id:int,contact_id:str=Form(""),subject:str=Form(""),context:str=Form("")):
 with connect() as c:
  company=c.execute("SELECT * FROM companies WHERE id=?",(company_id,)).fetchone()
  if not company:raise HTTPException(404,"Company not found")
  contact=None
  if contact_id.strip():contact=c.execute("SELECT * FROM contacts WHERE id=? AND company_id=?",(int(contact_id),company_id)).fetchone()
  if contact and contact["email"] and is_suppressed(contact["email"]):raise HTTPException(400,"Address is suppressed.")
 prompt=f"Write a concise, truthful first-contact email draft. Do not invent facts or claim prior contact. Business: {company['name']}. Website: {company['website']}. Industry: {company['industry']}. Location: {company['location']}. Notes: {company['notes']}. Contact: {dict(contact) if contact else 'not specified'}. Sender offer/context: {context}. Include a clear opt-out line. Return subject on first line, then a blank line, then body."
 try:
  answer=ask_ai(prompt,system="You draft compliant, truthful business correspondence. Never fabricate facts, personal relationships, or consent.")
 except Exception as e:raise HTTPException(400,f"AI draft unavailable: {e}")
 lines=answer.splitlines();sub=subject or (lines[0].replace("Subject:","").strip() if lines else "Introduction")
 body="\n".join(lines[2:] if len(lines)>2 and not lines[1].strip() else lines[1:]).strip()
 add_draft(body,company_id,int(contact_id) if contact_id.strip() and contact else None,subject=sub)
 return RedirectResponse("/drafts",303)

@app.get("/drafts",response_class=HTMLResponse)
def drafts_page():
 rows=list_drafts();body=""
 for r in rows:
  body+=f"<section><b>{esc(r['subject'] or 'Message draft')}</b><p class='muted'>To: {esc(r['contact_email'] or 'No contact linked')} · {esc(r['company_name'] or 'No company')} · Status: {esc(r['status'])}</p><pre style='white-space:pre-wrap;font:inherit'>{esc(r['body'])}</pre>"
  if r["status"]=="draft":body+=f"<form class='inline' method='post' action='/drafts/{r['id']}/approve'><button>Approve draft</button></form><form class='inline' method='post' action='/drafts/{r['id']}/reject'><button class='secondary'>Reject</button></form>"
  if r["status"]=="approved" and r.get("contact_email"):body+=f"<form class='inline' method='post' action='/drafts/{r['id']}/send' onsubmit='return confirm(\"Send this email now?\")'><button>Send approved email now</button></form>"
  body+="</section>"
 return shell("<h1>Outbox / Drafts</h1><p class='warning'>Send only after reviewing the recipient and message. Sending requires configured SMTP, a verified non-catch-all recipient and a public HTTPS unsubscribe URL.</p>"+(body or "<p class='muted'>No drafts yet. Open a company to create one.</p>"))
@app.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id:int):
 set_draft_status(draft_id,"approved");return RedirectResponse("/drafts",303)
@app.post("/drafts/{draft_id}/reject")
def reject_draft(draft_id:int):
 set_draft_status(draft_id,"rejected");return RedirectResponse("/drafts",303)

@app.get("/activity",response_class=HTMLResponse)
def activity_page():
 rows=list_activity();body="".join(f"<tr><td>{esc(x['created_at'])}</td><td>{esc(x['event'])}</td><td>{esc(x['details'])}</td></tr>" for x in rows)
 return shell("<h1>Activity</h1><table><tr><th>Time</th><th>Event</th><th>Details</th></tr>"+body+"</table>")

@app.get("/settings",response_class=HTMLResponse)
def settings_page():
 from .ai import provider_name, provider_status
 selected=provider_name()
 status=provider_status()
 options="".join(f"<option value='{p}' {'selected' if selected==p else ''}>{label}</option>" for p,label in [("ollama","Ollama (local)"),("claude-code","Claude Code CLI"),("codex","Codex CLI"),("openai-compatible","OpenAI-compatible endpoint"),("anthropic","Anthropic API")])
 return shell(f"""<h1>Settings</h1><section><h2>AI provider</h2>
 <p>Status: <b>{esc(status['status'])}</b> · Selected: {esc(selected)}</p><p class='muted'>{esc(status['fix'])}</p>
 <form method='post' action='/settings/ai'><label>Provider</label><select name='provider'>{options}</select>
 <label>Model (Ollama / API providers)</label><input name='model' placeholder='llama3.2 or model name'>
 <label>Base URL (API providers)</label><input name='base_url' placeholder='http://localhost:11434/v1'>
 <button>Save provider selection</button></form>
 <form method='post' action='/settings/test-ai'><button class='secondary'>Test connection</button></form>
 <p>Claude Code and Codex use your existing signed-in CLI subscription. Ollama runs locally. API-compatible and Anthropic providers may incur usage charges.</p>
 <p>API keys stay in your private .env file and are never stored by this form. Variables: OPENPROSPECT_AI_API_KEY.</p></section>
 <section><h2>Suppression list</h2><form method='post' action='/settings/suppressions'><input name='value' placeholder='Email address or domain' required><input name='reason' placeholder='Reason'><button>Add suppression</button></form><p class='muted'>The app checks exact email suppressions before draft creation. No delivery is enabled.</p></section>
 <section><h2>Privacy and compliance</h2><p>Use only data you are lawfully allowed to process. Record the source of contact information, respect opt-outs and applicable marketing laws, and check provider terms. A public email address is not automatically consent to marketing.</p></section>""")

@app.post("/settings/ai")
def save_ai_settings(provider:str=Form(...),model:str=Form(""),base_url:str=Form("")):
 from .ai import save_provider_settings
 try: save_provider_settings(provider,model,base_url)
 except ValueError as exc: raise HTTPException(400,str(exc))
 return RedirectResponse("/settings",303)

@app.post("/settings/test-ai",response_class=HTMLResponse)
def test_ai_provider():
 from .ai import test_ai_connection
 try:
  result=test_ai_connection()
  return shell(f"<h1>AI connection test</h1><p class='tag'>Connected: {esc(result['provider'])}</p><pre>{esc(result['response'])}</pre><a href='/settings'>Back to settings</a>")
 except Exception as exc:
  return shell(f"<h1>AI connection test</h1><p class='warning'>Not connected</p><p>{esc(exc)}</p><a href='/settings'>Back to settings</a>")

@app.post("/settings/suppressions")
def suppress_route(value:str=Form(...),reason:str=Form("")):
 add_suppression(value,reason);return RedirectResponse("/settings",303)

@app.post("/import/companies.csv",response_class=HTMLResponse)
async def import_companies_csv(file:UploadFile=File(...)):
 raw=await file.read(5_000_001)
 if len(raw)>5_000_000: raise HTTPException(413,"CSV file is too large (5 MB maximum).")
 try: rows=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
 except UnicodeDecodeError: raise HTTPException(400,"Upload a UTF-8 CSV file.")
 saved=0; skipped=0
 for row in rows:
  name=(row.get("name") or "").strip()
  if not name: skipped+=1; continue
  phone=(row.get("phone") or "").strip(); website=(row.get("website") or "").strip()
  if find_company_duplicate(website,phone): skipped+=1; continue
  add_company(name,website,row.get("industry",""),row.get("location",""),row.get("notes",""),"csv_import",row.get("source_url",""),phone,row.get("email",""),row.get("socials","")); saved+=1
 return shell(f"<h1>Company CSV import</h1><p>Imported {saved}; skipped {skipped} empty or duplicate rows.</p><a href='/companies'>Back to companies</a>")

@app.post("/import/contacts.csv",response_class=HTMLResponse)
async def import_contacts_csv(file:UploadFile=File(...)):
 raw=await file.read(5_000_001)
 if len(raw)>5_000_000: raise HTTPException(413,"CSV file is too large (5 MB maximum).")
 try: rows=csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
 except UnicodeDecodeError: raise HTTPException(400,"Upload a UTF-8 CSV file.")
 saved=0; skipped=0
 with connect() as conn: companies=[dict(x) for x in conn.execute("SELECT id,name FROM companies")]
 by_name={x["name"].strip().lower():x["id"] for x in companies}
 valid_ids={x["id"] for x in companies}
 for row in rows:
  try: company_id=int(row.get("company_id") or 0)
  except ValueError: company_id=0
  if company_id not in valid_ids: company_id=by_name.get((row.get("company_name") or "").strip().lower(),0)
  email=(row.get("email") or "").strip()
  if not company_id or (email and is_suppressed(email)): skipped+=1; continue
  add_contact(company_id,row.get("name",""),row.get("title",""),email,row.get("phone",""),row.get("source_url",""),row.get("email_status","unknown"),row.get("notes","")); saved+=1
 return shell(f"<h1>Contact CSV import</h1><p>Imported {saved}; skipped {skipped} missing-company or suppressed rows.</p><a href='/contacts'>Back to contacts</a>")

@app.get("/export/companies.csv")
def export_companies():
 rows=list_companies(100000);buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=["id","name","website","industry","location","notes","phone","email","socials","source","source_url"]);w.writeheader()
 for r in rows:w.writerow({k:r.get(k,"") for k in w.fieldnames})
 return StreamingResponse(iter([buf.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=openprospect-companies.csv"})
@app.get("/export/contacts.csv")
def export_contacts():
 rows=list_contacts(100000);buf=io.StringIO();fields=["id","company_id","company_name","name","title","email","phone","source_url","email_status","email_verification_reason","verified_at","notes"];w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
 for r in rows:w.writerow({k:r.get(k,"") for k in fields})
 return StreamingResponse(iter([buf.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=openprospect-contacts.csv"})

@app.get("/api/companies")
def api_companies():return {"companies":list_companies(1000)}
@app.post("/api/companies")
def api_add_company(payload:dict):
 if not payload.get("name"):raise HTTPException(400,"name is required")
 return {"id":add_company(payload["name"],payload.get("website",""),payload.get("industry",""),payload.get("location",""),payload.get("notes",""),"api","",payload.get("phone",""),payload.get("email",""),payload.get("socials","")),"ok":True}
@app.post("/api/ai")
def ai_chat(payload:dict):
 prompt=str(payload.get("prompt","")).strip()
 if not prompt:raise HTTPException(400,"prompt is required")
 try:return {"response":ask_ai(prompt)}
 except Exception as e:raise HTTPException(400,str(e))


# Keep the local dashboard private even when bound to loopback.
from .security import install_security
from .training_routes import router as training_router
app.include_router(training_router)
install_security(app)


from .signals_routes import router as signals_router
app.include_router(signals_router)
