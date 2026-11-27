from __future__ import annotations
import html, re, urllib.parse, urllib.request
from html.parser import HTMLParser
from urllib.parse import urlsplit

UA="Mozilla/5.0 (compatible; ZeroHawkResearch/0.3)"

class Links(HTMLParser):
 def __init__(self):
  super().__init__(); self.links=[]; self.title_text=""; self.in_title=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="a" and a.get("href"):self.links.append(a["href"])
  if tag=="title":self.in_title=True
 def handle_data(self,data):
  if self.in_title:self.title_text+=data
 def handle_endtag(self,tag):
  if tag=="title":self.in_title=False

def _get(url,limit=1200000):
 req=urllib.request.Request(url,headers={"User-Agent":UA,"Accept":"text/html,application/xhtml+xml"})
 with urllib.request.urlopen(req,timeout=18) as r:
  final=r.geturl(); raw=r.read(limit+1); charset=r.headers.get_content_charset() or "utf-8"
 return final,raw[:limit].decode(charset,errors="replace")

def google_search(query,limit=8):
 url="https://www.google.com/search?"+urllib.parse.urlencode({"q":query,"num":min(max(limit,1),10)})
 try: _,page=_get(url,900000)
 except Exception as e:return {"query":query,"results":[],"error":f"Google Search unavailable: {e}"}
 p=Links();p.feed(page); out=[];seen=set()
 for href in p.links:
  href=html.unescape(href)
  if href.startswith("/url?"):href=urllib.parse.parse_qs(urlsplit(href).query).get("q",[""])[0]
  u=urlsplit(href)
  if u.scheme not in ("http","https") or not u.hostname:continue
  host=u.hostname.lower()
  if host.endswith(("google.com","googleusercontent.com","gstatic.com")):continue
  clean=urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,"",""))
  if clean not in seen:seen.add(clean);out.append({"url":clean,"domain":host.removeprefix("www.")})
  if len(out)>=limit:break
 return {"query":query,"results":out,"error":""}

def research_business(name,location="",known_website=""):
 queries=[f'"{name}" {location} official website'.strip(),f'"{name}" {location} phone email contact'.strip(),f'"{name}" {location} Instagram Facebook'.strip()]
 if known_website:queries.insert(0,f'"{name}" {known_website}')
 searches=[google_search(q) for q in queries]; candidates=[];seen=set()
 for group in searches:
  for item in group["results"]:
   if item["domain"] not in seen:seen.add(item["domain"]);candidates.append(item)
 known=(urlsplit(known_website if "://" in known_website else "https://"+known_website).hostname or "").lower().removeprefix("www.")
 candidates.sort(key=lambda x:(x["domain"]==known,name.lower().replace(" ","") in x["domain"].replace("-","")),reverse=True)
 fields={"websites":[],"phones":[],"emails":[],"socials":[]}; evidence=[]
 for item in candidates[:12]:
  url=item["url"];host=item["domain"]
  if any(s in host for s in ("instagram.com","facebook.com","tiktok.com","linkedin.com","x.com")):
   fields["socials"].append({"value":url,"source_url":url,"confidence":"medium"});evidence.append({"url":url,"type":"social profile","confidence":"medium"});continue
  try:final,page=_get(url)
  except Exception:continue
  p=Links();p.feed(page); title=html.unescape(p.title_text.strip())
  text=html.unescape(re.sub(r"<[^>]+>"," ",page))
  evidence.append({"url":final,"title":title,"type":"website","confidence":"high" if known and host==known else "medium"})
  fields["websites"].append({"value":final,"source_url":final,"confidence":"high" if known and host==known else "medium","title":title})
  for value in sorted(set(re.findall(r"(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",text)))[:20]:
   fields["emails"].append({"value":value,"source_url":final,"confidence":"medium"})
  for value in sorted(set(re.findall(r"(?<!\w)(?:\+?\d[\d .()/-]{7,}\d)(?!\w)",text)))[:20]:
   fields["phones"].append({"value":value.strip(),"source_url":final,"confidence":"low"})
  for href in p.links:
   absolute=urllib.parse.urljoin(final,href);domain=(urlsplit(absolute).hostname or "").lower()
   if any(s in domain for s in ("instagram.com","facebook.com","linkedin.com","tiktok.com","x.com")):
    fields["socials"].append({"value":absolute,"source_url":final,"confidence":"medium"})
 for key,values in fields.items():
  unique={}
  for v in values:unique.setdefault(v["value"].lower(),v)
  fields[key]=list(unique.values())
 return {"business":name,"location":location,"fields":fields,"conflicts":{k:v for k,v in fields.items() if len(v)>1},
  "evidence":evidence,"searches":searches,
  "summary":"Extracted from public linked pages. Contact ownership is not verified; compare conflicting values and review sources before use."}
