from __future__ import annotations
import csv,html,io,json,difflib,re
from contextlib import asynccontextmanager
from fastapi import FastAPI,Form,HTTPException,File,UploadFile
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse,Response
from .db import (add_company,list_companies,connect,add_contact,list_contacts,
 add_campaign,list_campaigns,add_draft,list_drafts,set_draft_status,
 add_suppression,list_activity,is_suppressed,log,find_company_duplicate,save_company_observations,set_contact_email_status,set_contact_email)
from .ai import ask_ai
from .discovery import discover_osm
from .profiling import profile_website
from .verification import verify_email,learn_email_pattern,guess_email
from urllib.parse import urlsplit, urlencode

import contextvars
_current_path=contextvars.ContextVar("zh_path",default="/")
@asynccontextmanager
async def _lifespan(app):
 from .automation import resume_saved_autopilot, stop_worker_for_shutdown
 resume_saved_autopilot()
 yield
 stop_worker_for_shutdown()

app=FastAPI(title="Zero Hawk",version="0.3.0",lifespan=_lifespan)

@app.middleware("http")
async def _track_path(request,call_next):
 tok=_current_path.set(request.url.path)
 try:return await call_next(request)
 finally:_current_path.reset(tok)





@app.get("/brand.svg", include_in_schema=False)
def brand_icon():
 return Response(content='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256"><rect width="256" height="256" rx="54" fill="#0b0f12"/><path fill="#B7F34A" d="M30 63 119 105 81 121 27 102 83 143 31 191 129 148 101 130 158 119 221 85 177 79 148 91 103 70Z"/><path fill="#F4F7EF" d="m101 130 47-39 32-8 34 5 20 15-23 7-18 25-30 20-39-4 25-17-31 2-36 27 19-33Z"/><path fill="#0b0f12" d="m190 94 24 8-18 5-14-7Z"/><path fill="#B7F34A" d="m177 111 34 7-25 12-20-6Z"/></svg>''', media_type="image/svg+xml")

def esc(v):return html.escape(str(v or ""),quote=True)
def shell(body):
 from .ui import render_shell
 try:
  pending=sum(1 for d in list_drafts() if d["status"]=="draft")
 except Exception:pending=0
 from .sendpolicy import is_paused
 status=("Sending paused","warn") if is_paused() else ("Approval-first · safe mode","")
 return render_shell(body,_current_path.get(),pending,status)

def company_table(items):
 if not items:return "<p class='muted'>No companies yet. Add one or use Discover.</p>"
 rows="".join(f"<tr><td><b>{esc(x['name'])}</b><br><small>#{x['id']} · {esc(x['source'])}</small></td><td>{esc(x['website']) or '—'}</td><td>{esc(x['industry'])}</td><td>{esc(x['location'])}</td><td>{esc(x.get('phone',''))}</td><td><a href='/company/{x['id']}'>Open</a></td></tr>" for x in items)
 return f"<table><tr><th>Company</th><th>Website</th><th>Industry</th><th>Location</th><th>Phone</th><th></th></tr>{rows}</table>"

@app.get("/",response_class=HTMLResponse)
def home():
 import os
 from .extra_routes import funnel
 from .training import load_training
 from .messaging import email_status
 from .ai import provider_status
 companies=list_companies(10000);contacts=list_contacts(10000);drafts=list_drafts()
 pending=sum(1 for d in drafts if d["status"]=="draft");f=dict(funnel())
 try:ai_ok=provider_status().get("status")=="connected"
 except Exception:ai_ok=False
 steps=[("Connect an email provider","Add SMTP details to .env so approved messages can be sent.",email_status()["configured"],"/connections"),
  ("Train on your product","Teach Zero Hawk your offer, ideal customer and voice.",bool(load_training()),"/train"),
  ("Connect an AI provider","Ollama (free, local), Claude Code or Codex.",ai_ok,"/settings"),
  ("Discover businesses","Pull local businesses from free OpenStreetMap data.",len(companies)>0,"/discover"),
  ("Profile websites for signals","Score who looks ready to buy, with evidence.",f["Profiled"]>0,"/signals"),
  ("Review your first draft","Approve or fix drafts in the Outbox.",f["Approved"]>0,"/drafts")]
 done=sum(1 for x in steps if x[2])
 lis="".join(f"<li><span class='dot {'done' if ok else ''}'>{'✓' if ok else ''}</span><div style='flex:1'><b>{t}</b><br><span class='muted'>{d}</span></div>"+("" if ok else f"<a href='{u}'>Set up →</a>")+"</li>" for t,d,ok,u in steps)
 cards="".join(f"<div class='card'><div class='lbl'>{k}</div><div class='number'>{v}</div><div class='sub'>{sub}</div></div>" for k,v,sub in [("Companies",len(companies),f"{f['With website']} with a website"),("Contacts",len(contacts),f"{f['Verified emails']} verified emails"),("Needs your review",pending,"drafts awaiting approval"),("Emails sent",f["Emails sent"],"all time")])
 recent=company_table(companies[:8])
 return shell(f"<h1>Today</h1><p class='muted'>What is done and what still needs to happen.</p><div class='grid'>{cards}</div><div class='cols'><section><div style='display:flex;justify-content:space-between'><h2>Setup progress</h2><span class='pill {'' if done==len(steps) else 'info'}'>{done}/{len(steps)} done</span></div><div class='bar' style='margin:6px 0 10px'><i style='width:{done*100//len(steps)}%'></i></div><ul class='steps'>{lis}</ul></section><section><h2>Funnel</h2>{__import__('openprospect.extra_routes',fromlist=['x'])._bars(list(f.items()))}</section></div><section><h2>Recent companies</h2>{recent}</section><p class='muted'>Coverage depends on community map data. A published address is not consent to marketing.</p>")

@app.get("/discover",response_class=HTMLResponse)
def discover_page():
 return shell("""<h1>Discover businesses</h1><p class='muted'>Use community OpenStreetMap data or Google Maps Places. Both feed the same company register and cross-source duplicate checks.</p><div class='cols'><section><h2>OpenStreetMap</h2><p class='muted'>Free, no API key. Coverage varies by area.</p><form method='post' action='/discover'><label>City or place</label><input name='city' placeholder='Nairobi, Kenya' required><label>Business category</label><select name='category'><option>any business</option><option>restaurant</option><option>cafe</option><option>hotel</option><option>shop</option><option>beauty</option><option>clinic</option><option>dentist</option><option>school</option><option>gym</option><option>supermarket</option></select><label>Maximum results</label><input name='limit' type='number' min='1' max='200' value='50'><button>Search OpenStreetMap</button></form></section><section><h2>Google Maps · free search</h2><p class='muted'>No API key or bank card. Search Google Maps, choose a business, then save its public details to ZERO HAWK. Scout can research the saved business afterwards.</p><a href='/discover/google'>Open free Google Maps discovery →</a></section></div><p><a href='/research'>Scout AI: Google Search and website research →</a> · <a href='/companies'>View saved companies</a></p>""")

@app.post("/discover",response_class=HTMLResponse)
def discover_run(city:str=Form(...),category:str=Form("any business"),limit:int=Form(50)):
 try: results=discover_osm(city,category,limit)
 except Exception as e:return shell(f"<h1>Discovery issue</h1><p class='warning'>{esc(e)}</p><a href='/discover'>Try again</a>")
 saved=0
 for x in results:
  # Deduplicate against a normalized company domain or phone number.
  if find_company_duplicate(x["website"],x["phone"],x["name"]):continue
  add_company(x["name"],x["website"],x["category"],x["address"] or city,"", "openstreetmap",x["source_url"],x["phone"],x["email"],x["socials"]);saved+=1
 rows="".join(f"<tr><td>{esc(x['name'])}</td><td>{esc(x['category'])}</td><td>{esc(x['website']) or 'No website listed'}</td><td>{esc(x['phone'])}</td></tr>" for x in results)
 log("discovery_completed",f"{city}: {len(results)} found, {saved} new")
 return shell(f"<h1>Discovery complete</h1><p>Found {len(results)} map entries; saved {saved} new companies.</p><section><table><tr><th>Name</th><th>Category</th><th>Website</th><th>Phone</th></tr>{rows}</table></section><a href='/companies'>Open company register</a> · <a href='/discover'>Search again</a>")


@app.get("/discover/google",response_class=HTMLResponse)
def google_maps_discovery_page():
 return shell("""<h1>Google Maps discovery · free mode</h1><p class='muted'>No Google Cloud account, API key or bank card required. This opens Google's own Maps search in your browser. Google does not provide unrestricted free Places API access, so ZERO HAWK does not scrape Maps pages or pretend to import results automatically.</p>
 <section><h2>1. Search Google Maps</h2><form method='post' action='/discover/google'><label>City or place</label><input name='city' placeholder='Nairobi, Kenya' required><label>Business category or search phrase</label><input name='category' value='restaurant' placeholder='restaurant, cafe, salon...'><button>Open Google Maps search</button></form></section>
 <section><h2>2. Save a business you choose</h2><p class='muted'>Open a listing in Google Maps, copy the publicly displayed business details and save them here. Leave fields blank if the listing does not publish them. Do not guess.</p><form method='post' action='/discover/google/save'><label>Business name</label><input name='name' required placeholder='Business name as shown on Maps'><label>Website</label><input name='website' type='url' placeholder='https://...'><label>Public phone</label><input name='phone' placeholder='+254...'><label>Public email (only if published)</label><input name='email' type='email' placeholder='name@example.com'><label>Location / address</label><input name='location' placeholder='Address shown on Maps'><label>Google Maps listing or search URL</label><input name='source_url' type='url' placeholder='https://maps.google.com/...'><button>Save business to ZERO HAWK</button></form></section>
 <p><a href='/research'>Use Scout AI to research saved businesses →</a> · <a href='/companies'>View saved companies</a></p>""")

@app.post("/discover/google",response_class=HTMLResponse)
def google_maps_discovery_search(city:str=Form(...),category:str=Form("any business")):
 city=city.strip(); category=category.strip() or "any business"
 if not city:return shell("<h1>Google Maps discovery</h1><p class='warning'>Enter a city or place.</p><a href='/discover/google'>Try again</a>")
 query=f"{category} in {city}"
 maps_url="https://www.google.com/maps/search/?"+urlencode({"api":"1","query":query})
 search_url="https://www.google.com/search?"+urlencode({"q":query+" official website phone email"})
 return shell(f"<h1>Google Maps search ready</h1><p>Search for <b>{esc(query)}</b> using Google's own service.</p><section><p><a href='{esc(maps_url)}' target='_blank' rel='noopener'>Open Google Maps results →</a></p><p><a href='{esc(search_url)}' target='_blank' rel='noopener'>Search Google for official business websites and public contacts →</a></p><p class='muted'>Choose a listing, check that it is the right business, then return to <a href='/discover/google'>the save form</a>. Scout research can add source-linked evidence, but no contact details are invented.</p></section>")

@app.post("/discover/google/save",response_class=HTMLResponse)
def google_maps_save_business(name:str=Form(...),website:str=Form(""),phone:str=Form(""),email:str=Form(""),location:str=Form(""),source_url:str=Form("")):
 name=name.strip()
 if not name:raise HTTPException(400,"Business name is required.")
 existing=find_company_duplicate(website,phone,name)
 if existing:
  return shell(f"<h1>Already saved</h1><p><b>{esc(name)}</b> matches an existing company record. ZERO HAWK skipped the duplicate.</p><a href='/company/{existing['id']}'>Open existing company →</a> · <a href='/discover/google'>Back to Google Maps discovery</a>")
 ident=add_company(name,website,"",location,"","google_maps",source_url,phone,email,"")
 log("google_maps_business_saved",name)
 return shell(f"<h1>Business saved</h1><p><b>{esc(name)}</b> has been added to your company register.</p><p>Website: {esc(website) or 'Not provided'} · Phone: {esc(phone) or 'Not provided'} · Email: {esc(email) or 'Not provided'}</p><a href='/company/{ident}'>Open company →</a> · <a href='/research'>Research with Scout AI →</a>")

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
 if data.get("title"):
  save_company_observations(company_id,[{
   "code":"WEBSITE_IDENTITY","label":f"Homepage identifies this business as: {data['title']}",
   "weight":0,"confidence":1.0,"evidence_url":data.get("url","")
  }])
 site_label=(data.get("title") or "").split("|")[0].split("—")[0].strip()
 norm=lambda value: re.sub(r"[^a-z0-9]+","",value.lower())
 identity_mismatch=bool(site_label and len(norm(site_label))>3 and difflib.SequenceMatcher(None,norm(row["name"]),norm(site_label)).ratio()<0.35)
 identity_warning=(f"<p class='warning'><b>Possible business identity mismatch:</b> your saved record says {esc(row['name'])}, but the homepage title says {esc(site_label)}. Confirm the correct business before drafting outreach.</p>" if identity_mismatch else "")
 signal_rows="".join(f"<tr><td>{esc(s['label'])}</td><td>{s['weight']}</td><td>{s['confidence']:.0%}</td><td><a href='{esc(s['evidence_url'])}'>Evidence</a></td></tr>" for s in data.get("signals",[]))
 return shell(f"<h1>Website profile: {esc(row['name'])}</h1><section>{identity_warning}<p><b>{esc(data['title'])}</b></p><p>{esc(data['description'])}</p><p>Fetched: <a href='{esc(data['url'])}'>{esc(data['url'])}</a></p><p>Opportunity score: <b>{data['score']}/100</b> · Pages read: {len(data['pages'])} · Load: {data['load_seconds']}s</p><h3>Buying signals</h3><table><tr><th>Signal</th><th>Weight</th><th>Confidence</th><th>Evidence</th></tr>{signal_rows or '<tr><td colspan=4>No enabled signals found</td></tr>'}</table><h3>Public email strings found (unverified)</h3><ul>{''.join('<li>'+esc(e)+'</li>' for e in data['emails']) or '<li>None found</li>'}</ul><h3>Possible phone strings (unverified)</h3><ul>{''.join('<li>'+esc(p)+'</li>' for p in data['phones']) or '<li>None found</li>'}</ul><h3>Page text excerpt</h3><p>{esc(data['text'][:5000])}</p></section><a href='/company/{company_id}'>Back to company</a>")

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
  observations=[dict(item) for item in c.execute(
   "SELECT label,weight,confidence,evidence_url FROM observations WHERE company_id=? ORDER BY id DESC LIMIT 12",
   (company_id,)
  ).fetchall()]
 try:
  from .training import load_training
  training=load_training()
 except Exception:
  training={}
 sender_offer=training.get("offer") or "ARTCRAFT STUDIO provides website design, logo design, brand identity and graphic design for businesses."
 sender_icp=training.get("icp") or "Restaurants and other local businesses that could benefit from a stronger online presence."
 sender_signature=training.get("signature") or "ARTCRAFT STUDIO"
 sender_voice=training.get("tone_of_voice") or "Professional, warm, concise and specific."
 sender_cta=training.get("default_cta") or "Would you be open to a short conversation?"
 prompt=(
  "Write a concise, genuinely personalised first-contact email for a business prospect. "
  "Use only the facts supplied below. Never invent a website defect, missing feature, result, relationship, "
  "decision-maker, consent or prior interaction. Treat website observations as clues, not proof; only mention "
  "a finding when its evidence supports it. If there are no useful evidence-backed opportunities, write a "
  "polite introductory email without pretending to have found a problem. Do not use generic filler such as "
  "'I am reaching out to introduce myself and learn whether there may be a fit'. "
  "Do not use merge tags or placeholders such as [Your name]. Use the supplied sender signature exactly. "
  "Include a brief, respectful opt-out sentence. Return the subject on the first line, a blank line, then the body.\n\n"
  f"Prospect name in CRM (may be outdated; compare with website identity): {company['name']}\n"
  f"Website: {company['website']}\nIndustry: {company['industry']}\nLocation: {company['location']}\n"
  f"CRM notes: {company['notes']}\nWebsite observations (newest first): {json.dumps(observations, ensure_ascii=False)}\n"
  f"Contact: {dict(contact) if contact else 'No contact linked'}\n"
  f"Sender: ARTCRAFT STUDIO\nServices / offer: {sender_offer}\nIdeal customers: {sender_icp}\n"
  f"Brand voice: {sender_voice}\nPreferred CTA: {sender_cta}\nSignature: {sender_signature}\n"
  f"Additional user context for this draft: {context or 'Use the sender offer and verified website observations above.'}"
 )
 try:
  answer=ask_ai(prompt,system="You are the careful sales copywriter for ARTCRAFT STUDIO. Follow the requested output format exactly. Be specific, evidence-led, concise and natural. Never invent facts or include placeholders.")
 except Exception as e:raise HTTPException(400,f"AI draft unavailable: {e}")
 lines=answer.splitlines();sub=subject or (lines[0].replace("Subject:","").strip() if lines else "Introduction")
 body="\n".join(lines[2:] if len(lines)>2 and not lines[1].strip() else lines[1:]).strip()
 add_draft(body,company_id,int(contact_id) if contact_id.strip() and contact else None,subject=sub)
 return RedirectResponse("/drafts",303)

@app.get("/drafts",response_class=HTMLResponse)
def drafts_page():
 rows=list_drafts();body=""
 for r in rows:
  from .drafting import lint_for_draft
  lr=lint_for_draft(r["id"]) or {"ok":True,"errors":[],"warnings":[]}
  badge="<span class='pill'>Lint passed</span>" if lr["ok"] else "<span class='pill bad'>Needs fixes</span>"
  notes="".join(f"<li class='warning'>{esc(x)}</li>" for x in lr["errors"])+"".join(f"<li class='muted'>{esc(x)}</li>" for x in lr["warnings"])
  body+=f"<section><div style='display:flex;justify-content:space-between;gap:10px'><b>{esc(r['subject'] or 'Message draft')}</b>{badge}</div><ul style='margin:6px 0 0;padding-left:18px'>{notes}</ul><p class='muted'>To: {esc(r['contact_email'] or 'No contact linked')} · {esc(r['company_name'] or 'No company')} · Status: {esc(r['status'])}</p><pre style='white-space:pre-wrap;font:inherit'>{esc(r['body'])}</pre>"
  if r["status"]=="draft":body+=f"<form class='inline' method='post' action='/drafts/{r['id']}/approve'><button>Approve draft</button></form><form class='inline' method='post' action='/drafts/{r['id']}/reject'><button class='secondary'>Reject</button></form>"
  if r["status"]=="approved" and r.get("contact_email"):body+=f"<form class='inline' method='post' action='/drafts/{r['id']}/send' onsubmit='return confirm(\"Send this email now?\")'><button>Send approved email now</button></form>"
  body+="</section>"
 return shell("<h1>Outbox / Drafts</h1><p class='warning'>Send only after reviewing the recipient and message. Sending requires configured SMTP, a verified non-catch-all recipient and a public HTTPS unsubscribe URL.</p>"+(body or "<p class='muted'>No drafts yet. Open a company to create one.</p>"))
@app.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id:int):
 from .drafting import lint_for_draft
 r=lint_for_draft(draft_id)
 if r is None:raise HTTPException(404,"Draft not found")
 if not r["ok"]:raise HTTPException(400,"Cannot approve: "+" ".join(r["errors"]))
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
 <p>API keys stay in your private .env file and are never stored by this form. Variables: ZERO_HAWK_AI_API_KEY.</p></section>
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
  if find_company_duplicate(website,phone,name): skipped+=1; continue
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
 return StreamingResponse(iter([buf.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=zero-hawk-companies.csv"})
@app.get("/export/contacts.csv")
def export_contacts():
 rows=list_contacts(100000);buf=io.StringIO();fields=["id","company_id","company_name","name","title","email","phone","source_url","email_status","email_verification_reason","verified_at","notes"];w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
 for r in rows:w.writerow({k:r.get(k,"") for k in fields})
 return StreamingResponse(iter([buf.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=zero-hawk-contacts.csv"})

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
from .platform_routes import router as platform_router
app.include_router(platform_router)
from .extra_routes import router as extra_router
app.include_router(extra_router)



from .suite_routes import router as suite_router
app.include_router(suite_router)
from .research_routes import router as research_router
app.include_router(research_router)
