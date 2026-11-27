from __future__ import annotations
import html
from fastapi import APIRouter, Form, HTTPException
from .db import add_company, find_company_duplicate, list_companies, log
from .discovery import discover_google_maps
from .research import research_business

router=APIRouter()
def _page(title,body):
 from .app import shell
 return shell(f"<h1>{html.escape(title)}</h1>{body}")
def _e(v):return html.escape(str(v or ""),quote=True)

@router.get("/research",response_class=__import__("fastapi.responses",fromlist=["HTMLResponse"]).HTMLResponse)
def research_page():
 rows="".join(f"<option value='{x['id']}'>{_e(x['name'])} — #{x['id']}</option>" for x in list_companies(10000))
 return _page("Scout research",f"""<p class='muted'>Search Google for official websites and public contact channels. Every extracted value keeps its source link and confidence label.</p><section><form method='post' action='/research'><label>Saved business</label><select name='company_id' required>{rows}</select><button>Research with Scout</button></form></section>""")

@router.post("/research",response_class=__import__("fastapi.responses",fromlist=["HTMLResponse"]).HTMLResponse)
def research_run(company_id:int=Form(...)):
 from .db import connect
 with connect() as c:row=c.execute("SELECT * FROM companies WHERE id=?",(company_id,)).fetchone()
 if not row:raise HTTPException(404,"Company not found")
 result=research_business(row["name"],row["location"],row["website"])
 try:
  from .ai import ask_ai
  prompt=("Analyse only the evidence below. Never infer or invent a phone, email, URL, identity or fact. Distinguish official-site evidence from search results and social profiles. Flag conflicting values, cite exact source URLs, and say unknown when absent.\n\n"+repr(result))
  result["scout_analysis"]=ask_ai(prompt,system="You are Scout, a cautious evidence-based business researcher. Never fabricate.")
 except Exception as exc:result["scout_analysis"]="AI analysis unavailable: "+str(exc)
 fields=result["fields"]
 def table(label,key):
  cells="".join(f"<tr><td>{_e(v['value'])}</td><td>{_e(v['confidence'])}</td><td><a href='{_e(v['source_url'])}' target='_blank' rel='noreferrer'>Open source</a></td></tr>" for v in fields[key])
  return f"<h3>{label}</h3><table><tr><th>Found value</th><th>Confidence</th><th>Evidence</th></tr>{cells or '<tr><td colspan=3>Not found — leave blank rather than guess</td></tr>'}</table>"
 conflict="".join(f"<li><b>{_e(k)}</b>: {', '.join(_e(v['value']) for v in vals)} — compare source links</li>" for k,vals in result["conflicts"].items())
 evidence="".join(f"<li><a href='{_e(v['url'])}' target='_blank' rel='noreferrer'>{_e(v.get('title') or v['url'])}</a> <small>{_e(v['type'])} · {_e(v['confidence'])}</small></li>" for v in result["evidence"])
 log("scout_research_completed",f"{row['name']}: {len(result['evidence'])} sources")
 return _page("Scout research report",f"<p>Research for <b>{_e(row['name'])}</b>. Results are not automatically saved to contact details.</p><section><h2>Scout analysis</h2><pre>{_e(result.get('scout_analysis',''))}</pre></section><section>{table('Official websites','websites')}{table('Public phone numbers','phones')}{table('Public emails','emails')}{table('Social profiles','socials')}</section><section><h2>Conflicting details</h2><ul>{conflict or '<li>No conflicting values found in pages reviewed.</li>'}</ul><h2>Evidence sources</h2><ul>{evidence or '<li>No accessible sources returned.</li>'}</ul></section>")

@router.get("/discover/google",response_class=__import__("fastapi.responses",fromlist=["HTMLResponse"]).HTMLResponse)
def google_page():
 return _page("Google Maps discovery","""<p class='muted'>Google Maps Places import requires a Google Maps Platform API key. Without one, open the live Maps search link.</p><section><form method='post' action='/discover/google'><label>City or place</label><input name='city' placeholder='Nairobi, Kenya' required><label>Business category</label><input name='category' value='restaurant'><label>Maximum results</label><input name='limit' type='number' min='1' max='20' value='20'><button>Search Google Maps</button></form></section><p><a href='/discover'>Back to discovery</a></p>""")

@router.post("/discover/google",response_class=__import__("fastapi.responses",fromlist=["HTMLResponse"]).HTMLResponse)
def google_run(city:str=Form(...),category:str=Form("any business"),limit:int=Form(20)):
 try:payload=discover_google_maps(city,category,limit)
 except Exception as exc:return _page("Google Maps discovery",f"<p class='warning'>Google Places search failed: {_e(exc)}</p><a href='/discover/google'>Try again</a>")
 saved=0
 for x in payload["results"]:
  if find_company_duplicate(x["website"],x["phone"],x["name"]):continue
  add_company(x["name"],x["website"],x["category"],x["address"],"","google_maps",x["source_url"],x["phone"],x["email"],x["socials"]);saved+=1
 rows="".join(f"<tr><td>{_e(x['name'])}</td><td>{_e(x['address'])}</td><td>{_e(x['phone'])}</td><td><a href='{_e(x['source_url'])}' target='_blank' rel='noreferrer'>Maps</a></td></tr>" for x in payload["results"])
 setup=f"<p class='warning'>{_e(payload['message'])}</p>" if not payload["configured"] else ""
 return _page("Google Maps discovery",f"{setup}<p>Found {len(payload['results'])}; saved {saved} new businesses. Existing matches are skipped across sources.</p><p><a href='{_e(payload['maps_url'])}' target='_blank' rel='noreferrer'>Open live Google Maps search</a></p><section><table><tr><th>Business</th><th>Address</th><th>Phone</th><th>Source</th></tr>{rows}</table></section><a href='/companies'>Company register</a>")
