"""HTTP-indgang til Nominatim-opslagene (PWA har ingen Electron-bro).

Ingen ny opslagslogik: ruterne kalder `_osm_reverse_geocode` / `_osm_geocode`
i `core.tools.geolocation_tools` (throttle + User-Agent). Bevidst IKKE et
`/geo/ip`-endpoint: ip-api uden klient-IP giver SERVERENS adresse.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from core.tools import geolocation_tools

router = APIRouter(prefix="/geo", tags=["geo"])


def _label(res: dict[str, Any], precise: bool) -> str:
    """Samme label som Electron-broen: «vej, by» (præcis) eller «by»."""
    city = str(res.get("city") or "")
    if not precise:
        return city
    return ", ".join(p for p in (str(res.get("road") or ""), city) if p)


@router.get("/reverse")
def geo_reverse(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    precise: bool = True,
) -> dict[str, Any]:
    res = geolocation_tools._osm_reverse_geocode(lat, lon)
    if res.get("status") != "ok":
        raise HTTPException(status_code=502, detail=res.get("error") or "reverse fejlede")
    label = _label(res, precise) or str(res.get("display_name") or "")
    return {"label": label, "display_name": res.get("display_name", "")}


@router.get("/search")
def geo_search(q: str = Query(..., min_length=1, max_length=300)) -> dict[str, Any]:
    addr = q.strip()
    if not addr:
        raise HTTPException(status_code=422, detail="tom adresse")
    res = geolocation_tools._osm_geocode(addr)
    if res.get("status") != "ok":
        raise HTTPException(status_code=404, detail=res.get("error") or "ingen match")
    return {"lat": res["lat"], "lon": res["lon"], "label": res.get("display_name", "")}
