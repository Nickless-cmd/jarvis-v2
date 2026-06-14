"""Security-headers + let-vægts rate-limiting middleware (spec §20).

`SecurityHeadersMiddleware` tilføjer hærdnings-headers til ALLE svar (§20.4).
De fleste er sikre at sætte ubetinget på et JSON/SSE-API; Content-Security-Policy
er env-gated (`JARVISX_CSP`) fordi en streng `default-src 'none'` ville brække
evt. HTML/JS som API'et serverer.

`SimpleRateLimitMiddleware` er en in-memory per-IP token-bucket (ingen ekstern
afhængighed som slowapi). Den er **slået FRA** medmindre `JARVISX_RATE_LIMIT` er
sat — så et deploy ikke pludselig 429'er live trafik før Bjørn er klar.
"""
from __future__ import annotations

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
        scheme = request.url.scheme
        xfp = request.headers.get("x-forwarded-proto", "")
        client = request.client.host if request.client else ""
        if enabled and _should_redirect_to_https(
            scheme=scheme, x_forwarded_proto=xfp, client=client, path=request.url.path,
        ):
            return RedirectResponse(str(request.url.replace(scheme="https")), status_code=301)
        resp = await call_next(request)
        if str(os.environ.get("JARVISX_HTTPS_REDIRECT_DEBUG", "")).strip() == "1":
            resp.headers["X-Redir-Debug"] = f"en={int(enabled)} sch={scheme} xfp={xfp or '-'} cli={client}"
        return resp


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
    """(enabled, max_requests, window_seconds) fra env. Default FRA."""
    enabled = str(os.environ.get("JARVISX_RATE_LIMIT", "")).strip().lower() in {"1", "true", "yes", "on"}
    try:
        max_req = int(os.environ.get("JARVISX_RATE_LIMIT_MAX", "120"))
    except ValueError:
        max_req = 120
    try:
        window = float(os.environ.get("JARVISX_RATE_LIMIT_WINDOW", "60"))
    except ValueError:
        window = 60.0
    return enabled, max_req, window


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory per-IP sliding-window rate limit. FRA medmindre env slår den til."""

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque] = {}

    async def dispatch(self, request: Request, call_next):
        enabled, max_req, window = _rate_limit_config()
        if not enabled:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        dq = self._hits.setdefault(ip, deque())
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= max_req:
            return JSONResponse(
                {"detail": "rate limit exceeded", "error": "too_many_requests"},
                status_code=429,
                headers={"Retry-After": str(int(window))},
            )
        dq.append(now)
        return await call_next(request)
