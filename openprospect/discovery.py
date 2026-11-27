from __future__ import annotations
import json, os, threading, time, urllib.parse, urllib.request
from functools import lru_cache

PRESETS = {
 "restaurant": 'node["amenity"="restaurant"];way["amenity"="restaurant"];relation["amenity"="restaurant"];',
 "cafe": 'node["amenity"="cafe"];way["amenity"="cafe"];relation["amenity"="cafe"];',
 "hotel": 'node["tourism"="hotel"];way["tourism"="hotel"];relation["tourism"="hotel"];',
 "shop": 'node["shop"];way["shop"];relation["shop"];',
 "beauty": 'node["shop"="beauty"];way["shop"="beauty"];node["amenity"="beauty"];way["amenity"="beauty"];',
 "clinic": 'node["amenity"="clinic"];way["amenity"="clinic"];node["healthcare"];way["healthcare"];',
 "dentist": 'node["amenity"="dentist"];way["amenity"="dentist"];',
 "school": 'node["amenity"="school"];way["amenity"="school"];node["amenity"="college"];way["amenity"="college"];',
 "gym": 'node["leisure"="fitness_centre"];way["leisure"="fitness_centre"];',
 "supermarket": 'node["shop"="supermarket"];way["shop"="supermarket"];',
 "any business": 'node["office"];way["office"];node["shop"];way["shop"];node["amenity"~"restaurant|cafe|bank|clinic|dentist|school|hospital"];way["amenity"~"restaurant|cafe|bank|clinic|dentist|school|hospital"];',
}
_LAST_REQUEST=0.0
_LOCK=threading.Lock()
USER_AGENT="Zero Hawk/0.3 (local-first business discovery)"

def _pause():
 global _LAST_REQUEST
 with _LOCK:
  elapsed=time.monotonic()-_LAST_REQUEST
  if elapsed<1: time.sleep(1-elapsed)
  _LAST_REQUEST=time.monotonic()

@lru_cache(maxsize=128)
def _geocode(city):
 q=urllib.parse.urlencode({"q":city,"format":"json","limit":1})
 req=urllib.request.Request("https://nominatim.openstreetmap.org/search?"+q,headers={"User-Agent":USER_AGENT})
 _pause()
 with urllib.request.urlopen(req,timeout=30) as r: places=json.loads(r.read())
 if not places: raise RuntimeError("Location not found by OpenStreetMap.")
 return float(places[0]["lat"]),float(places[0]["lon"])

def _osm_item(e,category):
 t=e.get("tags",{}); name=t.get("name")
 if not name:return None
 return {"name":name,"website":t.get("website") or t.get("contact:website") or "",
 "phone":t.get("phone") or t.get("contact:phone") or "","email":t.get("email") or t.get("contact:email") or "",
 "socials":"; ".join(v for v in (t.get("contact:instagram"),t.get("contact:facebook"),t.get("contact:twitter"),t.get("contact:whatsapp")) if v),
 "category":t.get("amenity") or t.get("shop") or t.get("tourism") or t.get("office") or category,
 "address":", ".join(v for v in (t.get("addr:housenumber"),t.get("addr:street"),t.get("addr:city")) if v),
 "source":"openstreetmap","source_url":f"https://www.openstreetmap.org/{e['type']}/{e['id']}"}

def discover_osm(city,category="any business",limit=50):
 if not city.strip():raise ValueError("Enter a city or place.")
 selector=PRESETS.get(category.lower().strip(),PRESETS["any business"])
 lat,lon=_geocode(city.strip()); clauses=[]
 for clause in selector.split(";"):
  clause=clause.strip()
  if clause:
   for kind in ("node","way","relation"):clause=clause.replace(kind+"[",kind+"(around:10000,%s,%s)["%(lat,lon))
   clauses.append(clause+";")
 query="[out:json][timeout:45];("+"".join(clauses)+");out center tags;"
 req=urllib.request.Request("https://overpass-api.de/api/interpreter",data=urllib.parse.urlencode({"data":query}).encode(),headers={"User-Agent":USER_AGENT,"Content-Type":"application/x-www-form-urlencoded"})
 _pause()
 with urllib.request.urlopen(req,timeout=60) as r:data=json.loads(r.read())
 return [x for x in (_osm_item(e,category) for e in data.get("elements",[])) if x][:max(1,min(int(limit),200))]

def discover_google_maps(city,category="any business",limit=20):
 key=os.getenv("ZERO_HAWK_GOOGLE_MAPS_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
 query=f"{category} in {city}".strip()
 maps_url="https://www.google.com/maps/search/?"+urllib.parse.urlencode({"api":"1","query":query})
 if not key:return {"results":[],"maps_url":maps_url,"configured":False,"message":"Google Maps search link is ready. Add ZERO_HAWK_GOOGLE_MAPS_API_KEY to .env to import Places results."}
 body=json.dumps({"textQuery":query,"pageSize":max(1,min(int(limit),20))}).encode()
 req=urllib.request.Request("https://places.googleapis.com/v1/places:searchText",data=body,method="POST",headers={"Content-Type":"application/json","X-Goog-Api-Key":key,"X-Goog-FieldMask":"places.id,places.displayName,places.formattedAddress,places.websiteUri,places.nationalPhoneNumber,places.primaryType,places.googleMapsUri"})
 with urllib.request.urlopen(req,timeout=30) as r:data=json.loads(r.read())
 results=[]
 for p in data.get("places",[]):
  name=(p.get("displayName") or {}).get("text","")
  if name:results.append({"name":name,"website":p.get("websiteUri",""),"phone":p.get("nationalPhoneNumber",""),"email":"","socials":"","category":p.get("primaryType",category),"address":p.get("formattedAddress",city),"source":"google_maps","source_url":p.get("googleMapsUri",maps_url)})
 return {"results":results,"maps_url":maps_url,"configured":True,"message":""}
