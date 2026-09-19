"""Et færdigt HTTP-svar pr. version — serialiseret og komprimeret ÉN gang.

## Hvorfor (målt 19/9-2026 på CT105)

`GET /chat/sessions/{id}` for Bjørns aktive session: 2.672 beskeder og
**21,5 MB JSON**, heraf 13 MB værktøjs-output. Desk får 304 via ETag'en, men
telefonen har ingen HTTP-cache, så den hentede hele samtalen ved hver
forbindelse og hver poll-resync: 67 fulde svar på 10 minutter fra én telefon.
Hvert af dem serialiserede de 21,5 MB forfra (~0,3 s CPU), og intet blev
komprimeret — hverken af API'et eller af Caddy.

Løsningen her ændrer ikke hvad klienten får, kun hvordan det kommer frem:

- Bytes caches pr. version, så en uændret samtale serialiseres én gang, ikke
  én gang pr. kald.
- Beder klienten om gzip (Androids HTTP-klient gør det selv og pakker
  transparent ud), sendes den komprimerede udgave: 21,5 → 6,5 MB. Niveau 1,
  fordi det koster 0,18 s mod 0,44 s ved niveau 6 for næsten samme størrelse,
  og fordi det sker én gang pr. version.

Rører ikke streaming: kun svar der bygges her, komprimeres.
"""
from __future__ import annotations

import gzip
from typing import Any, Callable

from fastapi.responses import JSONResponse, Response

from core.services.central_projection_cache import cached_by_version

GZIP_NIVEAU = 1


def _vil_have_gzip(accept_encoding: str | None) -> bool:
    for del_ in (accept_encoding or "").lower().split(","):
        navn, _, param = del_.strip().partition(";")
        if navn.strip() == "gzip":
            # «gzip;q=0» betyder udtrykkeligt nej.
            return param.replace(" ", "") not in ("q=0", "q=0.0", "q=0.00", "q=0.000")
    return False


def versioneret_json_svar(
    *,
    noegle: str,
    version: str,
    etag: str,
    accept_encoding: str | None,
    indhold: Callable[[], Any],
) -> Response:
    """Byg (eller genbrug) svaret for `version`. `indhold` kaldes kun ved ny version."""
    raa, _ = cached_by_version(f"{noegle}:raa", version, lambda: JSONResponse(indhold()).body)
    hoveder = {"ETag": etag, "Cache-Control": "no-cache", "Vary": "Accept-Encoding"}
    if _vil_have_gzip(accept_encoding):
        pakket, _ = cached_by_version(
            f"{noegle}:gzip", version, lambda: gzip.compress(raa, compresslevel=GZIP_NIVEAU))
        return Response(content=pakket, media_type="application/json",
                        headers={**hoveder, "Content-Encoding": "gzip"})
    return Response(content=raa, media_type="application/json", headers=hoveder)
