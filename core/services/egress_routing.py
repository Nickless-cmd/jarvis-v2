"""Egress routing — which network egress a (provider, auth_profile) slot uses.

Two egress proxies route account2 traffic so it looks different from the
default (home-IP) profile, removing multi-account ban risk:

- VPN proxy (``vpn``)  — for 12 of 13 account2 providers.
- IPv6 proxy (``he6``) — for ``groq`` ONLY (Cloudflare blocks groq's VPN IP
  but accepts our Hurricane-Electric IPv6).
- ``home`` — no proxy; used by the default profile (home IP).

Resolution is per-(provider, auth_profile): default -> home; any other
profile -> per-provider override (EGRESS_ROUTES) or 'vpn'.
"""
from __future__ import annotations

# EGRESS_ROUTES: per-provider override of which egress a NON-default profile uses.
EGRESS_ROUTES = {"groq": "he6"}   # groq's VPN IP is Cloudflare-blocked -> use IPv6 proxy
_DEFAULT_NONDEFAULT_EGRESS = "vpn"
# proxy endpoints (overridable via runtime config; these are the real proven defaults)
_DEFAULT_PROXY_ENDPOINTS = {
    "vpn": "http://10.0.0.45:8888",
    "he6": "http://10.0.0.46:8888",
    "home": None,
}


def resolve_egress(provider: str, auth_profile: str) -> str:
    """Which egress a slot uses. default profile -> 'home'; other profiles ->
    per-provider override or 'vpn'."""
    if (auth_profile or "default") == "default":
        return "home"
    return EGRESS_ROUTES.get(provider, _DEFAULT_NONDEFAULT_EGRESS)


def proxy_endpoints() -> dict:
    """Return {egress: url|None}. Reads runtime config override if present, else
    the defaults. Self-safe: any error -> the hardcoded defaults."""
    try:
        from core.runtime.db_core import get_runtime_state_value
        raw = get_runtime_state_value("egress_proxy_endpoints")
        if isinstance(raw, str) and raw.strip():
            import json
            raw = json.loads(raw)
        if isinstance(raw, dict) and raw:
            merged = dict(_DEFAULT_PROXY_ENDPOINTS)
            merged.update(raw)
            return merged
    except Exception:
        pass
    return dict(_DEFAULT_PROXY_ENDPOINTS)
