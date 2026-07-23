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


_V6BIND_FLAG_KEY = "egress_v6bind_enabled"          # master switch, default OFF
_V6BIND_SOURCE_KEY = "egress_v6bind_source"         # account2 v6 source addr in the /64
_V6BIND_PROVIDERS_KEY = "egress_v6bind_providers"   # comma-sep provider allowlist


def resolve_v6bind_source(provider: str, auth_profile: str) -> str | None:
    """Native-IPv6 account2 egress: bind the outbound socket to a distinct v6
    SOURCE address in our HE /64 instead of routing account2 through the he6 HTTP
    proxy. Returns the source address for an eligible slot, else None (unchanged —
    the existing proxy path still applies).

    Gated by ``egress_v6bind_enabled`` (default False → always None → byte-identical
    to today). Only non-default (account2) profiles, and only providers on the
    ``egress_v6bind_providers`` allowlist (start: just ``groq``). Self-safe: any
    error → None → falls back to the proxy path (never silently leaks account2 over
    the home IP, because the proxy leak-guard still runs when this returns None).
    """
    if (auth_profile or "default") == "default":
        return None
    try:
        from core.runtime.db_core import get_runtime_state_value
        if not bool(get_runtime_state_value(_V6BIND_FLAG_KEY, False)):
            return None
        allow = str(get_runtime_state_value(_V6BIND_PROVIDERS_KEY, "groq") or "")
        if provider not in {p.strip() for p in allow.split(",") if p.strip()}:
            return None
        src = str(get_runtime_state_value(_V6BIND_SOURCE_KEY, "") or "").strip()
        if not src:
            return None
        # Fail-safe: only bind if the address actually exists on this host. If it
        # ever vanishes (e.g. a reboot before the persistence unit ran), fall back
        # to None → the proxy path — so groq degrades gracefully instead of erroring
        # with "cannot assign requested address".
        if not _source_addr_usable(src):
            return None
        return src
    except Exception:
        return None


def _source_addr_usable(addr: str) -> bool:
    """True if ``addr`` can be bound as an IPv6 source on this host (cheap check)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            s.bind((addr, 0))
            return True
        finally:
            s.close()
    except OSError:
        return False


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
