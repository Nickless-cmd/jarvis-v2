"""Delt loopback-vagt for /api/internal-ruterne — som DEPENDENCY, ikke som kropskode.

BAGGRUND (målt 28/10-2026, side-opgave side-eeb268d69d).

`/api/internal` er undtaget Bearer-token-kravet i `_PUBLIC_PATHS`, fordi
runtime-processen (port 8011) ikke kan bære et bruger-token. Hver rute under
præfikset håndhævede derfor loopback-only **inde i funktionskroppen**.

MÅLT FEJL: den placering betyder at FastAPI's body-validering kører FØRST.
Et kald med `X-Forwarded-For: 8.8.8.8` og `X-Forwarded-Proto: https` (præcis
hvad Caddy sender, jf. Caddyfile:15) gav **422 med feltnavne** — ikke 403.
Vagten blev aldrig evalueret, fordi Pydantic afviste body'en før funktionen
blev kaldt. Med en GYLDIG body gav samme kald korrekt 403, så der var ingen
reel eksponering — men den uautoriserede klient kunne probe rutens skema.

Det er samme fejlklasse som `/api/auth/register` (22/10-2026): kommentaren
påstod en grænse som koden ikke håndhævede der hvor den blev afprøvet.

LØSNINGEN: en `Depends()` evalueres FØR body-validering. Sat på router-niveau
svarer vagten derfor 403 med det samme, uanset om body'en er gyldig.

De oprindelige vagter i funktionskroppen er BEVARET med vilje — forsvar i
dybden. Denne dependency er den der svarer først; de er stadig sande hvis
nogen kalder rute-funktionen ad en anden vej.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

# Vært-navne der betyder "denne maskine". `testclient` er IKKE med: den
# repræsenterer en fremmed klient i tests, og en vagt der accepterer den
# accepterer alt.
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

# Proxy-headere der afslører at kaldet kom udefra. Caddy sætter altid
# X-Forwarded-For på reverse_proxy, så et ægte eksternt kald kan ikke
# skjule sig bag loopback-bindet.
_PROXY_HEADERS = ("x-forwarded-for", "forwarded")


def require_loopback(request: Request) -> None:
    """Rejs 403 hvis kaldet ikke er et ægte, lokalt IPC-kald.

    Bruges som `dependencies=[Depends(require_loopback)]` på routeren, så den
    kører før body-validering. Rejser `HTTPException` — FastAPI omsætter det
    til et 403-svar.
    """
    client_host = request.client.host if request.client else ""
    if client_host not in _LOOPBACK_HOSTS:
        raise HTTPException(status_code=403, detail="loopback-only")
    for header in _PROXY_HEADERS:
        if request.headers.get(header):
            raise HTTPException(
                status_code=403,
                detail="loopback-only (proxy-forwarded)",
            )
