"""Per-bruger krypteret OAuth-token-hvælv — plugin-fundamentets privatlivs-spine.

16. jun 2026 (Bjørn: "kritisk for privatlivet"). Hver connector-token krypteres med
BRUGERENS egen nøgle (keyring DEK, AES-256-GCM). Bruger A kan derfor ALDRIG læse
bruger B's token — heller ikke Bjørn eller Jarvis-handlende-for-en-anden. Privatlivet
er kryptografisk håndhævet (decrypt med forkert nøgle fejler), ikke kun policy.

Gemmes i runtime_state (cross-proces, DB-backed): {user_id: {provider: b64_ciphertext}}.
Genbruger encryption + keyring fra §16-arbejdet → ingen dobbelt-sandhed. Fail-soft.
"""
from __future__ import annotations

import base64
import json

from core.runtime.db_core import get_runtime_state_value, set_runtime_state_value
from core.services.encryption import decrypt, encrypt
from core.services.keyring_store import get_user_key

_KEY = "oauth_tokens"


def _norm(user_id: str, provider: str) -> tuple[str, str]:
    return (user_id or "").strip(), (provider or "").strip().lower()


def save_token(user_id: str, provider: str, token: dict) -> bool:
    """Krypter + gem `token` (fx {access_token, refresh_token, expires_at, scope})
    for (bruger, provider). Krypteret med brugerens egen nøgle. True ved succes."""
    uid, prov = _norm(user_id, provider)
    if not uid or not prov or not isinstance(token, dict):
        return False
    try:
        blob = encrypt(json.dumps(token).encode("utf-8"), get_user_key(uid))
        store = get_runtime_state_value(_KEY, {}) or {}
        if not isinstance(store, dict):
            store = {}
        bucket = store.get(uid)
        if not isinstance(bucket, dict):
            bucket = {}
        bucket[prov] = base64.b64encode(blob).decode("ascii")
        store[uid] = bucket
        set_runtime_state_value(_KEY, store)
        return True
    except Exception:
        return False


def get_token(user_id: str, provider: str) -> dict | None:
    """Hent + dekrypter token for (bruger, provider). None hvis intet/fejl. Kan KUN
    dekrypteres med brugerens egen nøgle (kryptografisk isolation)."""
    uid, prov = _norm(user_id, provider)
    if not uid or not prov:
        return None
    try:
        store = get_runtime_state_value(_KEY, {}) or {}
        if not isinstance(store, dict):
            return None
        b64 = (store.get(uid) or {}).get(prov)
        if not b64:
            return None
        raw = decrypt(base64.b64decode(b64), get_user_key(uid))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def has_token(user_id: str, provider: str) -> bool:
    """Er der en (dekrypterbar) token for brugeren hos provideren?"""
    return get_token(user_id, provider) is not None


def revoke_token(user_id: str, provider: str) -> bool:
    """Fjern token for (bruger, provider). True hvis udført (eller intet at fjerne)."""
    uid, prov = _norm(user_id, provider)
    if not uid or not prov:
        return False
    try:
        store = get_runtime_state_value(_KEY, {}) or {}
        bucket = store.get(uid) if isinstance(store, dict) else None
        if isinstance(bucket, dict) and prov in bucket:
            del bucket[prov]
            store[uid] = bucket
            set_runtime_state_value(_KEY, store)
        return True
    except Exception:
        return False


def get_fresh_token(user_id: str, provider: str, *, now: float | None = None) -> dict | None:
    """Som get_token, men auto-fornyer hvis udløbet (≤60s buffer) og refresh_token findes.

    Gemmer den fornyede token igen, så næste kald er hurtigt. Falder tilbage til den
    eksisterende token hvis fornyelse ikke er mulig (intet refresh_token / provider-fejl).
    """
    tok = get_token(user_id, provider)
    if not tok:
        return None
    import time as _time
    exp = tok.get("expires_at")
    refresh = tok.get("refresh_token")
    if exp and refresh:
        clock = float(now if now is not None else _time.time())
        if clock >= float(exp) - 60:
            try:
                from core.services.oauth_flow import refresh_token as _rt
                new = _rt(provider, refresh, now=now)
            except Exception:
                new = None
            if new and new.get("access_token"):
                save_token(user_id, provider, new)
                return new
    return tok


def list_providers(user_id: str) -> list[str]:
    """Providere brugeren har forbundet (har en gemt token for)."""
    uid, _ = _norm(user_id, "")
    if not uid:
        return []
    try:
        store = get_runtime_state_value(_KEY, {}) or {}
        bucket = store.get(uid) if isinstance(store, dict) else None
        return sorted(bucket.keys()) if isinstance(bucket, dict) else []
    except Exception:
        return []
