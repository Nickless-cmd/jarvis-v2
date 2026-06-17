"""OAuth-flow-helper for plugin-connectors (16. jun 2026).

Provider-config + signeret `state` (anti-CSRF + binder bruger-id til callback'en, TTL)
+ authorize-URL + code→token-bytte. Client-secrets læses fra runtime.json
(read_runtime_key) — aldrig i repo. Tokens gemmes pr. bruger krypteret i oauth_store.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import urllib.parse

_PUBLIC_BASE = "https://api.srvlab.dk"
_STATE_TTL = 600  # 10 min

_PROVIDERS: dict[str, dict] = {
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "default_scopes": ["repo", "read:user"],
        "id_key": "github_oauth_client_id",
        "secret_key": "github_oauth_client_secret",  # pragma: allowlist secret  (runtime.json-nøglenavn, ikke et secret)
        "extra_authorize": {},
    },
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "default_scopes": ["openid", "email"],
        "id_key": "google_oauth_client_id",
        "secret_key": "google_oauth_client_secret",  # pragma: allowlist secret  (runtime.json-nøglenavn, ikke et secret)
        # access_type=offline + prompt=consent → vi får et refresh_token.
        # include_granted_scopes=true → nye scopes lægges OVENI tidligere givne
        # (Google-pakken deler ét token; tilføj Kalender uden at miste Gmail).
        "extra_authorize": {
            "access_type": "offline", "prompt": "consent",
            "include_granted_scopes": "true",
        },
    },
}


def is_known_provider(provider: str) -> bool:
    return (provider or "").strip().lower() in _PROVIDERS


def redirect_uri(provider: str) -> str:
    return f"{_PUBLIC_BASE}/api/oauth/{(provider or '').strip().lower()}/callback"


def _secret(key: str, default: str = "") -> str:
    try:
        from core.runtime.secrets import read_runtime_key
        return str(read_runtime_key(key) or default)
    except Exception:
        return default


def _state_key() -> bytes:
    base = _secret("user_email_pepper", "jarvis-oauth-state-v1") or "jarvis-oauth-state-v1"
    return hashlib.sha256(("oauth-state:" + base).encode("utf-8")).digest()


def sign_state(user_id: str, provider: str, *, now: float | None = None) -> str:
    """Signeret, selvstændigt state — binder bruger+provider, udløber, anti-CSRF."""
    payload = {
        "uid": user_id, "prov": (provider or "").strip().lower(),
        "exp": int((now if now is not None else time.time()) + _STATE_TTL),
        "n": base64.urlsafe_b64encode(os.urandom(6)).decode("ascii"),
    }
    body = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii").rstrip("=")
    sig = hmac.new(_state_key(), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def verify_state(state: str, *, now: float | None = None) -> tuple[str, str] | None:
    """→ (user_id, provider) hvis gyldig+ikke-udløbet, ellers None."""
    try:
        body, sig = (state or "").split(".", 1)
        exp_sig = hmac.new(_state_key(), body.encode("ascii"), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(sig, exp_sig):
            return None
        pad = "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(body + pad))
        if int(payload.get("exp", 0)) < int(now if now is not None else time.time()):
            return None
        uid = str(payload.get("uid") or "")
        prov = str(payload.get("prov") or "")
        return (uid, prov) if uid and prov else None
    except Exception:
        return None


def build_authorize_url(
    provider: str, user_id: str, *, scopes: list[str] | None = None, now: float | None = None,
) -> str | None:
    """Authorize-URL til at åbne i brugerens browser. None hvis ukendt/ukonfigureret."""
    prov = (provider or "").strip().lower()
    p = _PROVIDERS.get(prov)
    if not p or not (user_id or "").strip():
        return None
    cid = _secret(p["id_key"])
    if not cid:
        return None
    q = {
        "client_id": cid,
        "redirect_uri": redirect_uri(prov),
        "scope": " ".join(scopes or p["default_scopes"]),
        "state": sign_state(user_id, prov, now=now),
        "response_type": "code",
    }
    q.update(p.get("extra_authorize") or {})
    return p["authorize_url"] + "?" + urllib.parse.urlencode(q)


def revoke_remote(provider: str, token: dict) -> bool:
    """Tilbagekald token hos provideren (best-effort). True hvis bekræftet revokeret.

    Lokal wipe sker uanset i kalderen — denne returnerer kun om provideren bekræftede.
    """
    prov = (provider or "").strip().lower()
    p = _PROVIDERS.get(prov)
    if not p or not isinstance(token, dict):
        return False
    access = token.get("access_token") or ""
    if not access:
        return False
    try:
        import httpx
        if prov == "google":
            r = httpx.post("https://oauth2.googleapis.com/revoke",
                           data={"token": access}, timeout=15)
            return r.status_code == 200
        if prov == "github":
            cid = _secret(p["id_key"])
            csec = _secret(p["secret_key"])
            r = httpx.request(
                "DELETE", f"https://api.github.com/applications/{cid}/grant",
                auth=(cid, csec), json={"access_token": access}, timeout=15,
            )
            return r.status_code in (204, 404)  # 404 = allerede væk
        return False
    except Exception:
        return False


def refresh_token(provider: str, refresh: str, *, now: float | None = None) -> dict | None:
    """Forny adgangstoken via grant_type=refresh_token. None ved fejl/ukendt provider."""
    prov = (provider or "").strip().lower()
    p = _PROVIDERS.get(prov)
    if not p or not (refresh or "").strip():
        return None
    data = {
        "client_id": _secret(p["id_key"]), "client_secret": _secret(p["secret_key"]),
        "grant_type": "refresh_token", "refresh_token": refresh,
    }
    try:
        import httpx
        r = httpx.post(p["token_url"], data=data, headers={"Accept": "application/json"}, timeout=20)
        if r.status_code != 200:
            return None
        tok = r.json()
        if not (isinstance(tok, dict) and tok.get("access_token")):
            return None
        tok.setdefault("refresh_token", refresh)  # GitHub/Google sender ikke altid ny
        if tok.get("expires_in"):
            base = float(now if now is not None else time.time())
            tok["obtained_at"] = base
            tok["expires_at"] = base + float(tok["expires_in"])
        return tok
    except Exception:
        return None


def exchange_code(provider: str, code: str, *, now: float | None = None) -> dict | None:
    """Byt authorization code for token (BLOKERENDE netværk — kør i tråd). None ved fejl."""
    prov = (provider or "").strip().lower()
    p = _PROVIDERS.get(prov)
    if not p or not (code or "").strip():
        return None
    data = {
        "client_id": _secret(p["id_key"]), "client_secret": _secret(p["secret_key"]),
        "code": code, "redirect_uri": redirect_uri(prov),
        "grant_type": "authorization_code",
    }
    try:
        import httpx
        r = httpx.post(p["token_url"], data=data, headers={"Accept": "application/json"}, timeout=20)
        if r.status_code != 200:
            return None
        tok = r.json()
        if not (isinstance(tok, dict) and tok.get("access_token")):
            return None
        if tok.get("expires_in"):
            tok["obtained_at"] = float(now if now is not None else time.time())
            tok["expires_at"] = tok["obtained_at"] + float(tok["expires_in"])
        return tok
    except Exception:
        return None
