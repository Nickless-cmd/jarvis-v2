"""Security-headers + let-vægts rate-limiting middleware (spec §20).

`SecurityHeadersMiddleware` tilføjer hærdnings-headers til ALLE svar (§20.4).
De fleste er sikre at sætte ubetinget på et JSON/SSE-API; Content-Security-Policy
er env-gated (`JARVISX_CSP`) fordi en streng `default-src 'none'` ville brække
evt. HTML/JS som API'et serverer.

`SimpleRateLimitMiddleware` er en in-memory sliding-window-grænse (ingen ekstern
afhængighed som slowapi): offentlig trafik tælles pr. IP, mens verificerede
app-klienter tælles pr. bruger+IP med et højere polling-loft. Den er **slået
TIL** som standard (ændret 22/10-2026) og kan slås fra med
`JARVISX_RATE_LIMIT=0`.

Hvorfor standarden blev vendt: målt i drift 22/10-2026 svarede det offentlige
`api.srvlab.dk` (185.107.14.241:443) på `/api/auth/login` og
`/api/auth/register` uden nogen grænse — `JARVISX_RATE_LIMIT` var ikke sat, så
der var nul beskyttelse mod brute force. En sikkerhedsgrænse skal være tændt når
ingen har taget stilling, ikke slukket.
"""
from __future__ import annotations

import ipaddress
import os
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

# §20.4 — altid sikre at sætte på et API.
_BASE_HEADERS = {
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Referrer-Policy": "no-referrer",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}
# CSP kun hvis eksplicit slået til (kan brække serveret HTML).
_CSP = "default-src 'none'; frame-ancestors 'none'"


def _should_redirect_to_https(*, scheme: str, x_forwarded_proto: str, client: str, path: str) -> bool:
    """Ren beslutning: skal denne request 301'es til HTTPS? (§20.1)

    Nej hvis: allerede HTTPS (scheme eller X-Forwarded-Proto=https, dvs. Caddy-
    proxied), loopback-klient (intern localhost-HTTP), eller /health-probe."""
    if scheme == "https" or x_forwarded_proto.lower() == "https":
        return False
    if client in ("127.0.0.1", "::1", "localhost"):
        return False
    if path in ("/health",):
        return False
    return True


class HttpsRedirectMiddleware(BaseHTTPMiddleware):
    """HTTP→HTTPS-redirect i-app (§20.1, lag 1) — uden at binde :80 (det ejer uvicorn).

    En request er "allerede HTTPS" hvis Caddy proxy'ede den (X-Forwarded-Proto: https)
    eller scheme==https. Ellers (direkte plain HTTP til uvicorn :80) → 301 til https.
    **FRA** medmindre JARVISX_HTTPS_REDIRECT er sat — så plain-HTTP-klienter ikke
    pludselig 301'es før Bjørn har bekræftet at alle bruger HTTPS.
    """
    async def dispatch(self, request: Request, call_next):
        enabled = str(os.environ.get("JARVISX_HTTPS_REDIRECT", "")).strip().lower() in {"1", "true", "yes", "on"}
        if enabled and _should_redirect_to_https(
            scheme=request.url.scheme,
            x_forwarded_proto=request.headers.get("x-forwarded-proto", ""),
            client=request.client.host if request.client else "",
            path=request.url.path,
        ):
            return RedirectResponse(str(request.url.replace(scheme="https")), status_code=301)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        for k, v in _BASE_HEADERS.items():
            response.headers.setdefault(k, v)
        if str(os.environ.get("JARVISX_CSP", "")).strip().lower() in {"1", "true", "yes", "on"}:
            response.headers.setdefault("Content-Security-Policy", _CSP)
        return response


def cors_allowed_origins() -> list[str]:
    """CORS-origins fra env (§20.3). `JARVISX_CORS_ORIGINS` = komma-sepereret
    whitelist; tom (default) → ["*"] (nuværende adfærd, behold desk-adgang).
    Behavior-neutral indtil Bjørn sætter env'en."""
    raw = str(os.environ.get("JARVISX_CORS_ORIGINS", "")).strip()
    if not raw:
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


def _rate_limit_config() -> tuple[bool, int, float]:
    """(enabled, max_requests, window_seconds) fra env. Default TIL.

    Stod som «Default FRA» indtil 22/10-2026. Det betød at en sikkerhedsgrænse
    var slukket indtil nogen tog stilling — og ingen havde. Kun en eksplicit
    fra-valg slår den fra nu.
    """
    raw = str(os.environ.get("JARVISX_RATE_LIMIT", "")).strip().lower()
    enabled = raw not in {"0", "false", "no", "off"}
    try:
        max_req = int(os.environ.get("JARVISX_RATE_LIMIT_MAX", "120"))
    except ValueError:
        max_req = 120
    try:
        window = float(os.environ.get("JARVISX_RATE_LIMIT_WINDOW", "60"))
    except ValueError:
        window = 60.0
    return enabled, max_req, window


def _authenticated_rate_limit_max() -> int:
    """Loft for en gyldigt autentificeret app-klient.

    Desk/PWA holder flere lette statusflader levende samtidig. Det er legitim
    trafik, men overstiger let den offentlige brute-force-grænse på 120/min.
    """
    try:
        return int(os.environ.get("JARVISX_AUTH_RATE_LIMIT_MAX", "600"))
    except ValueError:  # Fejlkonfiguration falder sikkert tilbage til standardloftet.
        return 600


def _authenticated_subject(request: Request) -> str:
    """Verificeret token-subjekt, ellers tom streng (aldrig header-tillid)."""
    raw = str(request.headers.get("authorization") or "").strip()
    if not raw.lower().startswith("bearer "):
        return ""
    token = raw.split(None, 1)[1].strip()
    if not token:
        return ""
    try:
        from core.runtime.jarvisx_auth import verify_token
    except Exception:  # Manglende auth-runtime må aldrig åbne det højere loft.
        return ""
    try:
        claims = verify_token(token)
    except Exception:  # Ugyldigt/udløbet token skal blive på det stramme offentlige loft.
        return ""
    return str((claims or {}).get("sub") or "").strip()


def _effektiv_klient_ip(request: Request) -> str:
    """Den IP der skal tælles på — ikke den socket uvicorn ser.

    Caddy ejer :443 og proxyer til `127.0.0.1:8080`, og uvicorn kører UDEN
    `--proxy-headers` (målt i `/etc/caddy/Caddyfile` og
    `/etc/systemd/system/jarvis-api.service`, 22/10-2026). Derfor er
    `request.client.host` **127.0.0.1 for alle kald, også dem fra internettet**.

    Uden denne funktion ville én grænse ramme alle klienter som én IP: den
    første der hamrede på login ville lukke for alle andre, og angriberen selv
    ville slippe igen så snart vinduet gled.

    X-Forwarded-For sættes af Caddy. Vi læser det **sidste** håb og ikke det
    første: Caddy tilføjer den ægte klient-adresse, så uanset om den overskriver
    eller appender en medbragt liste, er det sidste element den adresse Caddy
    selv målte. Et spoofet første-håb kan derfor ikke bruges til at vælge sin
    egen nøgle — eller til at udgive sig for at være på husets net.
    """
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        sidste = xff.split(",")[-1].strip()
        if sidste:
            return sidste
    return request.client.host if request.client else "unknown"


def _er_lokal_adresse(ip: str) -> bool:
    """Loopback/privat/link-local = husets egne klienter.

    Desk, runtime-processen og Caddy selv kalder API'et indefra. De skal ikke
    rammes af en grænse der findes for at bremse internettet — ellers ville
    Bjørns egen klient blive 429'et af sin egen polling.
    """
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:  # ikke en IP-streng (fx TestClient's "testclient") — kan ikke vaere husets net
        return False
    return bool(a.is_loopback or a.is_private or a.is_link_local)


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory sliding-window limit for public IPs and verified app users."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque] = {}

    async def dispatch(self, request: Request, call_next):
        enabled, max_req, window = _rate_limit_config()
        if not enabled:
            return await call_next(request)
        ip = _effektiv_klient_ip(request)
        if _er_lokal_adresse(ip):
            return await call_next(request)
        subject = _authenticated_subject(request)
        limit = _authenticated_rate_limit_max() if subject else max_req
        bucket = f"user:{subject}:{ip}" if subject else f"ip:{ip}"
        now = time.monotonic()
        dq = self._hits.setdefault(bucket, deque())
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= limit:
            return JSONResponse(
                {"detail": "rate limit exceeded", "error": "too_many_requests"},
                status_code=429,
                headers={"Retry-After": str(int(window))},
            )
        dq.append(now)
        return await call_next(request)
