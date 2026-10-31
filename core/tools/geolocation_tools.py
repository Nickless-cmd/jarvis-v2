"""Native geolocation-tools til Jarvis — geocode, reverse-geocode, routing,
nearby-søgning og bruger-lokations-opslag.

Alle kilder er gratis og kræver INGEN API-nøgle eller brugeroprettelse:
- Nominatim (OpenStreetMap): geocode + reverse-geocode. Kræver User-Agent.
- OSRM (project-osrm.org): vejbeskrivelser (driving/cycling/walking).
- Overpass (OSM): steder i nærheden.
- ip-api.com: IP-baseret by-niveau fallback.

Designprincip: best-effort, graceful fallback, aldrig crash ved API-fejl —
returnér altid et dict med "status": "ok" | "error".
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

logger = logging.getLogger(__name__)

_USER_AGENT = "Jarvis-Mobile-Companion/1.0 (jarvis-v2; contact onkeladolf@gmail.com)"
_NOMINATIM = "https://nominatim.openstreetmap.org"
_OSRM = "https://router.project-osrm.org"
_OVERPASS = "https://overpass-api.de/api/interpreter"
_IP_API = "http://ip-api.com/json/?fields=status,city,regionName,lat,lon,query"

# Nominatim-høflighed: max 1 req/sek. Vi serialiserer kald med en simpel throttle.
_last_nominatim_at = 0.0

# ── Google Routes (valgfri kilde ved siden af OSM — kræver nøgle) ──────────────
# Målt 31/10-2026: Routes og Geocoding er Essentials-tier med 10.000 gratis
# kald/md; først derefter koster en rute ~$5/1.000. Husets forbrug (15 ruter på
# en uge) er 0,2 % af kvoten — der er reelt ingen pris. Det man køber er
# adressekvaliteten: Nominatim gav to forskellige koordinater for samme adresse,
# og DAWA er nedlagt (410).
_GOOGLE_ROUTES = "https://routes.googleapis.com/directions/v2:computeRoutes"
_GOOGLE_FIELD_MASK = ",".join((
    "routes.distanceMeters",
    "routes.duration",
    "routes.legs.steps.navigationInstruction",
    "routes.legs.steps.distanceMeters",
))
_GOOGLE_TRAVEL_MODE = {"driving": "DRIVE", "cycling": "BICYCLE", "walking": "WALK"}


def _http_get_json(url: str, *, timeout: float = 12.0, data: bytes | None = None) -> Any:
    """GET (eller POST hvis data) JSON med Jarvis User-Agent. Kaster ved fejl."""
    req = urllib_request.Request(url, data=data, headers={"User-Agent": _USER_AGENT})
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _http_post_json(
    url: str, payload: dict[str, Any], headers: dict[str, str] | None = None,
    *, timeout: float = 15.0,
) -> Any:
    """POST JSON med ekstra headers (Google kræver X-Goog-Api-Key + field mask)."""
    hdrs = {"User-Agent": _USER_AGENT, "Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    req = urllib_request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=hdrs, method="POST"
    )
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _google_maps_key() -> str | None:
    """Nøglen, eller None når den ikke er sat.

    Manglende nøgle er en NORMAL tilstand, ikke en fejl: værktøjet skal kunne
    svare «ikke konfigureret» uden at vælte, og uden at lyve om at det har en
    rute. Derfor fanges kun RuntimeError (det read_runtime_key kaster), ikke alt.
    """
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key(
            "google_maps_api_key", env_override="JARVIS_GOOGLE_MAPS_API_KEY"
        ))
    except RuntimeError:  # noegle mangler = normal tilstand, ikke en fejl (se docstring)
        return None


def _google_seconds(value: object) -> float:
    """Google sender varighed som '144s' (protobuf-duration), ikke som tal."""
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip()
    if text.endswith("s"):
        text = text[:-1]
    try:
        return float(text)
    except ValueError:
        # Ukendt varighedsformat fra Google. 0.0 er en fallback der ser ud som
        # en gyldig rute paa nul minutter, saa den logges: et format-skift skal
        # kunne findes i loggen frem for at gemme sig som et pænt tal.
        logger.warning("Google-rute: ukendt varighedsformat %r - bruger 0.0", value)
        return 0.0


def _throttle_nominatim() -> None:
    global _last_nominatim_at
    elapsed = time.monotonic() - _last_nominatim_at
    if elapsed < 1.05:
        time.sleep(1.05 - elapsed)
    _last_nominatim_at = time.monotonic()


# ── Geocode (adresse → koordinater) ────────────────────────────────────────────
def geocode(address: str) -> dict[str, Any]:
    addr = (address or "").strip()
    if not addr:
        return {"status": "error", "error": "Ingen adresse angivet."}
    _throttle_nominatim()
    q = urllib_parse.urlencode({"q": addr, "format": "json", "limit": 1, "addressdetails": 1})
    try:
        rows = _http_get_json(f"{_NOMINATIM}/search?{q}")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError, ValueError) as exc:
        return {"status": "error", "error": f"Geocode fejlede: {exc}"}
    if not rows:
        return {"status": "error", "error": f"Ingen match for '{addr}'."}
    r = rows[0]
    return {
        "status": "ok",
        "lat": float(r.get("lat")),
        "lon": float(r.get("lon")),
        "display_name": r.get("display_name", ""),
    }


# ── Reverse-geocode (koordinater → adresse) ─────────────────────────────────────
def reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"status": "error", "error": "Ugyldige koordinater."}
    _throttle_nominatim()
    q = urllib_parse.urlencode({"lat": lat_f, "lon": lon_f, "format": "json", "addressdetails": 1})
    try:
        r = _http_get_json(f"{_NOMINATIM}/reverse?{q}")
    except (urllib_error.URLError, urllib_error.HTTPError, OSError, ValueError) as exc:
        return {"status": "error", "error": f"Reverse-geocode fejlede: {exc}"}
    if not r or r.get("error"):
        return {"status": "error", "error": "Ingen adresse fundet for koordinaterne."}
    a = r.get("address", {})
    return {
        "status": "ok",
        "display_name": r.get("display_name", ""),
        "road": a.get("road", ""),
        "city": a.get("city") or a.get("town") or a.get("village") or a.get("municipality", ""),
        "postcode": a.get("postcode", ""),
        "country": a.get("country", ""),
    }


# ── Route directions (A → B) ────────────────────────────────────────────────────
_PROFILE_MAP = {"driving": "driving", "cycling": "cycling", "walking": "walking",
                "bil": "driving", "cykel": "cycling", "gang": "walking", "gå": "walking"}


def _resolve_point(point: Any) -> tuple[float, float] | None:
    """Accepter enten 'adresse'-streng eller [lat, lon] / {lat,lon}."""
    if isinstance(point, dict) and "lat" in point and "lon" in point:
        try:
            return float(point["lat"]), float(point["lon"])
        except (TypeError, ValueError):
            return None
    if isinstance(point, (list, tuple)) and len(point) == 2:
        try:
            return float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
    if isinstance(point, str) and point.strip():
        g = geocode(point)
        if g.get("status") == "ok":
            return g["lat"], g["lon"]
    return None


def _osm_route(from_: Any, to: Any, profile: str = "driving") -> dict[str, Any]:
    prof = _PROFILE_MAP.get((profile or "driving").strip().lower(), "driving")
    a = _resolve_point(from_)
    b = _resolve_point(to)
    if not a:
        return {"status": "error", "error": f"Kunne ikke finde startpunkt: {from_!r}"}
    if not b:
        return {"status": "error", "error": f"Kunne ikke finde slutpunkt: {to!r}"}
    # OSRM forventer lon,lat;lon,lat
    coords = f"{a[1]},{a[0]};{b[1]},{b[0]}"
    url = f"{_OSRM}/route/v1/{prof}/{coords}?overview=false&steps=true"
    try:
        data = _http_get_json(url, timeout=15.0)
    except (urllib_error.URLError, urllib_error.HTTPError, OSError, ValueError) as exc:
        return {"status": "error", "error": f"Ruteberegning fejlede: {exc}"}
    routes = data.get("routes") or []
    if not routes:
        return {"status": "error", "error": "Ingen rute fundet."}
    route = routes[0]
    steps: list[str] = []
    for leg in route.get("legs", []):
        for s in leg.get("steps", []):
            man = s.get("maneuver", {})
            name = s.get("name", "")
            instr = man.get("type", "")
            if name or instr:
                steps.append(f"{instr} {name}".strip())
    dist_m = route.get("distance", 0)
    dur_s = route.get("duration", 0)
    return {
        "status": "ok",
        "profile": prof,
        "distance_km": round(dist_m / 1000.0, 2),
        "duration_min": round(dur_s / 60.0, 1),
        "steps": steps[:40],
    }


# ── Google Routes (kræver nøgle) ───────────────────────────────────────────────
def google_route(from_: Any, to: Any, profile: str = "driving") -> dict[str, Any]:
    """Rute via Google Routes API v2. Svarer ærligt hvis nøglen mangler."""
    key = _google_maps_key()
    if not key:
        return {
            "status": "error",
            "source": "google",
            "needs_key": True,
            "error": (
                "google_maps_api_key mangler — sæt den som top-level key i "
                "~/.jarvis-v2/config/runtime.json (eller JARVIS_GOOGLE_MAPS_API_KEY "
                "i .env). Google-kilden er valgfri; OSM virker uden nøgle."
            ),
        }
    prof = _PROFILE_MAP.get((profile or "driving").strip().lower(), "driving")
    a = _resolve_point(from_)
    b = _resolve_point(to)
    if not a:
        return {"status": "error", "error": f"Kunne ikke finde startpunkt: {from_!r}"}
    if not b:
        return {"status": "error", "error": f"Kunne ikke finde slutpunkt: {to!r}"}
    payload = {
        "origin": {"location": {"latLng": {"latitude": a[0], "longitude": a[1]}}},
        "destination": {"location": {"latLng": {"latitude": b[0], "longitude": b[1]}}},
        "travelMode": _GOOGLE_TRAVEL_MODE.get(prof, "DRIVE"),
        "computeAlternativeRoutes": False,
    }
    try:
        data = _http_post_json(
            _GOOGLE_ROUTES,
            payload,
            {"X-Goog-Api-Key": key, "X-Goog-FieldMask": _GOOGLE_FIELD_MASK},
        )
    except (urllib_error.URLError, urllib_error.HTTPError, OSError, ValueError) as exc:
        # Fejlen returneres i "error" til kalderen - den forsvinder ikke her.
        return {"status": "error", "source": "google", "error": f"Google-rute fejlede: {exc}"}
    routes = data.get("routes") or []
    if not routes:
        return {"status": "error", "source": "google", "error": "Ingen rute fundet."}
    route = routes[0]
    steps: list[str] = []
    for leg in route.get("legs", []):
        for s in leg.get("steps", []):
            instr = ((s.get("navigationInstruction") or {}).get("instructions") or "").strip()
            if instr:
                steps.append(instr)
    dist_m = route.get("distanceMeters", 0) or 0
    dur_s = _google_seconds(route.get("duration"))
    return {
        "status": "ok",
        "source": "google",
        "profile": prof,
        "distance_km": round(float(dist_m) / 1000.0, 2),
        "duration_min": round(dur_s / 60.0, 1),
        "steps": steps[:40],
    }


def compare_routes(from_: Any, to: Any, profile: str = "driving") -> dict[str, Any]:
    """Kør samme rute gennem begge kilder og vis hvor de er uenige.

    Formålet er ikke at vælge en vinder automatisk — det er at gøre
    uenigheden synlig, så et enkelt svar ikke får lov at se ud som en sandhed.
    """
    osm = _osm_route(from_, to, profile)
    google = google_route(from_, to, profile)
    ud: dict[str, Any] = {"status": "ok", "profile": profile, "osm": osm, "google": google}
    if osm.get("status") == "ok" and google.get("status") == "ok":
        ud["distance_delta_km"] = round(
            float(google["distance_km"]) - float(osm["distance_km"]), 2
        )
        ud["duration_delta_min"] = round(
            float(google["duration_min"]) - float(osm["duration_min"]), 1
        )
        ud["sources_agree"] = (
            abs(ud["distance_delta_km"]) < 0.2 and abs(ud["duration_delta_min"]) < 1.0
        )
    else:
        ud["sources_agree"] = None
        ud["note"] = (
            "Kunne ikke sammenligne — mindst én kilde fejlede. "
            "Se de to kilders egen 'error'."
        )
    return ud


# ── Rute (samlet indgang: osm | google | compare) ──────────────────────────────
def route_directions(
    from_: Any, to: Any, profile: str = "driving", source: str = "osm",
) -> dict[str, Any]:
    """Rute A → B. ``source``: 'osm' (standard, gratis), 'google' eller 'compare'."""
    valg = (source or "osm").strip().lower()
    if valg in ("google", "gmaps"):
        return google_route(from_, to, profile)
    if valg in ("compare", "sammenlign", "both"):
        return compare_routes(from_, to, profile)
    return _osm_route(from_, to, profile)


# ── Nearby search (steder i nærheden) ──────────────────────────────────────────
# Almindelige forespørgsler → Overpass amenity/shop-tags. Ukendte falder tilbage
# til et frit navne-match.
_AMENITY_MAP = {
    "tankstation": 'node["amenity"="fuel"]', "fuel": 'node["amenity"="fuel"]',
    "gas station": 'node["amenity"="fuel"]', "benzin": 'node["amenity"="fuel"]',
    "supermarked": 'node["shop"="supermarket"]', "supermarket": 'node["shop"="supermarket"]',
    "apotek": 'node["amenity"="pharmacy"]', "pharmacy": 'node["amenity"="pharmacy"]',
    "restaurant": 'node["amenity"="restaurant"]', "cafe": 'node["amenity"="cafe"]',
    "café": 'node["amenity"="cafe"]', "hospital": 'node["amenity"="hospital"]',
    "sygehus": 'node["amenity"="hospital"]', "atm": 'node["amenity"="atm"]',
    "hæveautomat": 'node["amenity"="atm"]', "bank": 'node["amenity"="bank"]',
    "parkering": 'node["amenity"="parking"]', "parking": 'node["amenity"="parking"]',
    "toilet": 'node["amenity"="toilets"]', "bibliotek": 'node["amenity"="library"]',
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt
    r = 6371000.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


def nearby_search(lat: float, lon: float, query: str, radius: int = 1500) -> dict[str, Any]:
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return {"status": "error", "error": "Ugyldige koordinater."}
    try:
        rad = max(50, min(int(radius), 20000))
    except (TypeError, ValueError):
        rad = 1500
    q = (query or "").strip().lower()
    selector = _AMENITY_MAP.get(q)
    if not selector and q:
        # Frit navne-match (case-insensitiv) på node/way name.
        safe = q.replace('"', "")
        selector = f'node["name"~"{safe}",i]'
    if not selector:
        return {"status": "error", "error": "Ingen søgeterm angivet."}
    ql = f"[out:json][timeout:20];({selector}(around:{rad},{lat_f},{lon_f}););out center 30;"
    try:
        data = _http_get_json(_OVERPASS, timeout=25.0, data=urllib_parse.urlencode({"data": ql}).encode())
    except (urllib_error.URLError, urllib_error.HTTPError, OSError, ValueError) as exc:
        return {"status": "error", "error": f"Nærheds-søgning fejlede: {exc}"}
    results = []
    for el in data.get("elements", []):
        elat = el.get("lat") or (el.get("center") or {}).get("lat")
        elon = el.get("lon") or (el.get("center") or {}).get("lon")
        if elat is None or elon is None:
            continue
        tags = el.get("tags", {})
        results.append({
            "name": tags.get("name", "(uden navn)"),
            "type": tags.get("amenity") or tags.get("shop") or "",
            "distance_m": round(_haversine_m(lat_f, lon_f, float(elat), float(elon))),
            "lat": float(elat), "lon": float(elon),
        })
    results.sort(key=lambda r: r["distance_m"])
    return {"status": "ok", "count": len(results), "results": results[:15]}


# ── IP-baseret lokation (fallback) ─────────────────────────────────────────────
def _ip_location() -> dict[str, Any] | None:
    try:
        d = _http_get_json(_IP_API, timeout=8.0)
    except (urllib_error.URLError, urllib_error.HTTPError, OSError, ValueError):
        return None
    if d.get("status") != "success":
        return None
    label = ", ".join([p for p in [d.get("city"), d.get("regionName")] if p])
    return {"lat": d.get("lat"), "lon": d.get("lon"), "label": label,
            "source": "ip", "precision": "city"}


# ── Bruger-lokations-opslag (presence først, IP-fallback) ──────────────────────
def geolocation_lookup(user_id: str = "") -> dict[str, Any]:
    """Find en brugers nuværende lokation. Læser delt presence-lokation først;
    falder tilbage til server-IP hvis ingen enhed deler. Respekterer toggle:
    returnerer 'ikke tilgængelig' hvis brugeren ikke deler OG IP fejler."""
    uid = (user_id or "").strip()
    try:
        from core.services import device_presence
        loc = device_presence.location_for(uid) if uid else None
    except Exception:
        loc = None
    if loc and loc.get("label"):
        kilde = loc.get("source", "presence")
        svar = {"status": "ok", "source": kilde,
                "label": loc["label"], "lat": loc.get("lat"), "lon": loc.get("lon"),
                "precision": loc.get("precision", "city"), "via": "presence"}
        # Et IP-opslag kan ikke finde byen (målt 7/10-2026): på mobildata går
        # trafikken gennem operatørens carrier-grade NAT, hvis udgang ligger i
        # København. Resultatet skal derfor sige hvad stedet ER — et gæt — så
        # en kalder ikke henter vejr for den forkerte by uden at vide det.
        if kilde == "ip":
            svar["note"] = ("Stedet er udledt af IP-adresse, ikke GPS. På "
                            "mobildata peger det typisk på operatørens "
                            "udgang, ikke på brugerens by.")
        return svar
    # Ingen delt lokation → IP-fallback (server-side; by-niveau).
    ip = _ip_location()
    if ip and ip.get("label"):
        return {"status": "ok", "source": "ip", "label": ip["label"],
                "lat": ip.get("lat"), "lon": ip.get("lon"),
                "precision": "city", "via": "ip_fallback",
                "note": "Brugeren deler ikke lokation — dette er server-IP (groft)."}
    return {"status": "ok", "available": False,
            "message": "Lokation ikke tilgængelig (deling slået fra)."}


# ── Tool-exec-wrappers (kaldes fra simple_tools._TOOL_HANDLERS) ─────────────────
def exec_geolocation_lookup(args: dict[str, Any]) -> dict[str, Any]:
    uid = str(args.get("user_id") or "").strip()
    if not uid:
        try:
            from core.identity.workspace_context import current_user_id
            uid = current_user_id() or ""
        except Exception:
            uid = ""
    return geolocation_lookup(uid)


def exec_geocode(args: dict[str, Any]) -> dict[str, Any]:
    return geocode(str(args.get("address") or ""))


def exec_reverse_geocode(args: dict[str, Any]) -> dict[str, Any]:
    return reverse_geocode(args.get("lat"), args.get("lon"))


def exec_route_directions(args: dict[str, Any]) -> dict[str, Any]:
    return route_directions(
        args.get("from"), args.get("to"),
        str(args.get("profile") or "driving"),
        str(args.get("source") or "osm"),
    )


def exec_nearby_search(args: dict[str, Any]) -> dict[str, Any]:
    return nearby_search(args.get("lat"), args.get("lon"), str(args.get("query") or ""),
                         args.get("radius") or 1500)
