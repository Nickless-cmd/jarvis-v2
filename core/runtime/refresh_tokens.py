"""Refresh-token-rotation (spec §22.6).

Eksisterende JWT (jarvisx_auth) er access-token. Dette lag tilføjer:
- **Access token**: kortlivet (default 30 min) — udstedt via jarvisx_auth.issue_token
- **Refresh token**: 7 dages TTL, opaque (secrets), lagret KUN som sha256-hash i
  runtime_state (rå token forlader aldrig serveren efter udstedelse)
- **Rotation**: hvert refresh invaliderer den gamle refresh-token + udsteder en ny
- **Revocation**: revoke_all(user_id) invaliderer alle brugerens refresh-tokens

Additivt — rører ikke eksisterende issue_token/verify_token. Cross-proces via
runtime_state-DB. Token-tyveri giver derved kun kortvarig adgang.
"""
from __future__ import annotations

import hashlib
import json
import secrets
import time

_ACCESS_TTL_SECONDS = 30 * 60     # 30 minutter
_REFRESH_TTL_SECONDS = 7 * 24 * 3600
_DB_PREFIX = "refresh:"
_USER_INDEX_PREFIX = "refresh_user:"


def _hash(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _now() -> float:
    return time.time()


def _kv():
    from core.runtime.db import get_runtime_state_value, set_runtime_state_value
    return get_runtime_state_value, set_runtime_state_value


def _index_add(user_id: str, h: str) -> None:
    get, set_ = _kv()
    key = _USER_INDEX_PREFIX + user_id
    try:
        hashes = json.loads(get(key, "[]") or "[]")
    except Exception:
        hashes = []
    if h not in hashes:
        hashes.append(h)
    set_(key, json.dumps(hashes))


def issue_refresh_token(user_id: str) -> str:
    """Udsted en ny refresh-token til brugeren. Returnerer den RÅ token (vises kun
    her); kun hash'en lagres."""
    uid = str(user_id or "").strip()
    if not uid:
        raise ValueError("user_id påkrævet")
    token = secrets.token_urlsafe(32)
    h = _hash(token)
    _, set_ = _kv()
    set_(_DB_PREFIX + h, json.dumps({
        "user_id": uid, "expires_at": _now() + _REFRESH_TTL_SECONDS, "active": True,
    }))
    _index_add(uid, h)
    return token


def verify_refresh_token(token: str) -> str | None:
    """Returnér user_id hvis refresh-token er gyldig (aktiv + ikke udløbet), ellers None."""
    get, _ = _kv()
    try:
        rec = json.loads(get(_DB_PREFIX + _hash(token), "") or "{}")
    except Exception:
        return None
    if not rec or not rec.get("active"):
        return None
    if float(rec.get("expires_at") or 0) < _now():
        return None
    return str(rec.get("user_id") or "") or None


def _deactivate(h: str) -> None:
    get, set_ = _kv()
    try:
        rec = json.loads(get(_DB_PREFIX + h, "") or "{}")
    except Exception:
        rec = {}
    if rec:
        rec["active"] = False
        set_(_DB_PREFIX + h, json.dumps(rec))


def rotate_refresh_token(token: str, *, app_id: str = "") -> dict:
    """Veksl en refresh-token til et nyt access+refresh-par. Den gamle refresh-token
    invalideres (rotation, §22.6). Returnerer {ok, access_token, refresh_token} eller
    {ok: False, reason}."""
    uid = verify_refresh_token(token)
    if uid is None:
        return {"ok": False, "reason": "invalid_or_expired"}
    _deactivate(_hash(token))                     # rotation: gammel ugyldiggøres
    new_refresh = issue_refresh_token(uid)
    # Rollen følger brugeren (issue_token defaulter member); ukendt → member.
    role = "member"
    try:
        from core.identity.users import find_user_by_discord_id
        u = find_user_by_discord_id(uid)
        if u is not None and getattr(u, "role", "") in {"owner", "member", "guest"}:
            role = u.role
    except Exception:
        pass
    from core.runtime.jarvisx_auth import issue_token
    access = issue_token(user_id=uid, role=role, ttl_seconds=_ACCESS_TTL_SECONDS, app_id=app_id)
    return {"ok": True, "access_token": access.get("token", ""), "refresh_token": new_refresh}


def revoke_all(user_id: str) -> int:
    """Invalidér ALLE brugerens refresh-tokens (§22.6 + !revoke-override). Returnerer
    antal deaktiverede."""
    uid = str(user_id or "").strip()
    get, _ = _kv()
    try:
        hashes = json.loads(get(_USER_INDEX_PREFIX + uid, "[]") or "[]")
    except Exception:
        hashes = []
    n = 0
    for h in hashes:
        _deactivate(h)
        n += 1
    return n
