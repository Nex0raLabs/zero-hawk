from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from functools import lru_cache

# OpenStreetMap tags are intentionally broad. Results depend on local mapping coverage.
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

_LAST_REQUEST = 0.0
_REQUEST_LOCK = threading.Lock()
USER_AGENT = "Zero Hawk/0.2 (free local-first business discovery)"


def _polite_pause() -> None:
    """Keep public OSM requests at least one second apart per process."""
    global _LAST_REQUEST
    with _REQUEST_LOCK:
        elapsed = time.monotonic() - _LAST_REQUEST
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _LAST_REQUEST = time.monotonic()


@lru_cache(maxsize=128)
def _geocode(city: str) -> tuple[float, float]:
    query = urllib.parse.urlencode({"q": city, "format": "json", "limit": 1})
    request = urllib.request.Request(
        "https://nominatim.openstreetmap.org/search?" + query,
        headers={"User-Agent": USER_AGENT},
    )
    _polite_pause()
    with urllib.request.urlopen(request, timeout=30) as response:
        places = json.loads(response.read())
    if not places:
        raise RuntimeError("Location not found by OpenStreetMap. Try a more specific city name.")
    return float(places[0]["lat"]), float(places[0]["lon"])


def discover_osm(city: str, category: str = "any business", limit: int = 50):
    if not city.strip():
        raise ValueError("Enter a city or place.")
    key = category.lower().strip()
    selector = PRESETS.get(key, PRESETS["any business"])
    lat, lon = _geocode(city.strip())
    clauses = []
    for clause in selector.split(";"):
        clause = clause.strip()
        if clause:
            clause = clause.replace("node[", "node(around:10000,%s,%s)[" % (lat, lon))
            clause = clause.replace("way[", "way(around:10000,%s,%s)[" % (lat, lon))
            clause = clause.replace("relation[", "relation(around:10000,%s,%s)[" % (lat, lon))
            clauses.append(clause + ";")
    overpass = "[out:json][timeout:45];(" + "".join(clauses) + ");out center tags;"
    data = urllib.parse.urlencode({"data": overpass}).encode()
    request = urllib.request.Request(
        "https://overpass-api.de/api/interpreter",
        data=data,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    _polite_pause()
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read())
    results = []
    for element in payload.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        website = tags.get("website") or tags.get("contact:website") or ""
        phone = tags.get("phone") or tags.get("contact:phone") or ""
        email = tags.get("email") or tags.get("contact:email") or ""
        socials = "; ".join(
            value for value in (
                tags.get("contact:instagram"), tags.get("contact:facebook"),
                tags.get("contact:twitter"), tags.get("contact:whatsapp"),
            ) if value
        )
        address = ", ".join(
            value for value in (
                tags.get("addr:housenumber"), tags.get("addr:street"), tags.get("addr:city")
            ) if value
        )
        results.append({
            "name": name, "website": website, "phone": phone, "email": email,
            "socials": socials,
            "category": tags.get("amenity") or tags.get("shop") or tags.get("tourism") or tags.get("office") or category,
            "address": address,
            "source_url": f"https://www.openstreetmap.org/{element['type']}/{element['id']}",
        })
    return results[:max(1, min(int(limit), 200))]
