"""Connector-katalog + per-bruger status (v1).

Privatlivs-først: hver connector-status er pr. bruger. OAuth-connectors er kun
"connected" hvis brugeren har en (dekrypterbar) token i oauth_store — den er
krypteret med brugerens egen nøgle. Lokale connectors (computer-use, browser …)
"findes-allerede" og er altid connected.

Truth: enabled-flag i runtime_state under `connector_enabled` = {uid: {id: bool}}.
Default ON. Delete = revoke hos provider (best-effort) + lokal token-wipe (GDPR).
"""
from __future__ import annotations

import core.runtime.db_core as dbc
from core.services import oauth_flow, oauth_store
from core.services.oauth_store import get_fresh_token, has_token

_ENABLED_KEY = "connector_enabled"

# v1-katalog. `kind`: "oauth" (kræver browser-flow) | "local" (findes-allerede).
_CATALOG: list[dict] = [
    {
        "id": "github", "name": "GitHub", "kind": "oauth",
        "category": "Udvikling", "icon": "github",
        "desc": "Issues, PRs, kode", "scopes": ["repo", "read:user"],
        "post_connect_hint": "Nu kan jeg kigge i dine GitHub-issues — skal jeg?",
    },
    {
        "id": "computer-use", "name": "Computer Use", "kind": "local",
        "category": "System", "icon": "command",
        "desc": "Styr skærm, mus og tastatur", "scopes": [],
    },
    {
        "id": "browser", "name": "Browser", "kind": "local",
        "category": "System", "icon": "globe",
        "desc": "Hent og læs websider", "scopes": [],
    },
    {
        "id": "read-aloud", "name": "Læs op", "kind": "local",
        "category": "System", "icon": "volume-2",
        "desc": "Tale-syntese (TTS)", "scopes": [],
    },
    {
        "id": "superpowers", "name": "Superpowers", "kind": "local",
        "category": "System", "icon": "sparkles",
        "desc": "Skills til struktureret arbejde", "scopes": [],
    },
]

_BY_ID = {c["id"]: c for c in _CATALOG}


def _enabled_store() -> dict:
    store = dbc.get_runtime_state_value(_ENABLED_KEY, {}) or {}
    return store if isinstance(store, dict) else {}


def is_enabled(user_id: str, connector_id: str) -> bool:
    """Default ON; kun False hvis brugeren eksplicit har slået den fra."""
    uid = (user_id or "").strip()
    bucket = _enabled_store().get(uid)
    if isinstance(bucket, dict) and connector_id in bucket:
        return bool(bucket[connector_id])
    return True


def set_enabled(user_id: str, connector_id: str, enabled: bool) -> bool:
    uid = (user_id or "").strip()
    if not uid or connector_id not in _BY_ID:
        return False
    store = _enabled_store()
    bucket = store.get(uid)
    if not isinstance(bucket, dict):
        bucket = {}
    bucket[connector_id] = bool(enabled)
    store[uid] = bucket
    dbc.set_runtime_state_value(_ENABLED_KEY, store)
    return True


def _connected(user_id: str, c: dict) -> bool:
    if c["kind"] == "local":
        return True
    return bool(has_token(user_id, c["id"]))


def list_for_user(user_id: str) -> list[dict]:
    """Hele kataloget beriget med per-bruger `connected` + `enabled`."""
    uid = (user_id or "").strip()
    out: list[dict] = []
    for c in _CATALOG:
        out.append({
            "id": c["id"], "name": c["name"], "kind": c["kind"],
            "category": c["category"], "icon": c["icon"], "desc": c["desc"],
            "scopes": list(c.get("scopes") or []),
            "post_connect_hint": c.get("post_connect_hint"),
            "connected": _connected(uid, c),
            "enabled": is_enabled(uid, c["id"]),
        })
    return out


def _audit(event: str, user_id: str, connector_id: str) -> None:
    try:
        from core.eventbus import publish
        publish("connector." + event, {"user_id": user_id, "connector": connector_id})
    except Exception:
        pass


def delete_for_user(user_id: str, connector_id: str) -> bool:
    """Afbryd & slet: revoke hos provider (best-effort) + lokal token-wipe + ryd flag.

    GDPR: token forsvinder uanset om provideren bekræfter revoke.
    """
    uid = (user_id or "").strip()
    c = _BY_ID.get(connector_id)
    if not uid or not c:
        return False
    if c["kind"] == "oauth":
        try:
            token = get_fresh_token(uid, connector_id)
            if token:
                oauth_flow.revoke_remote(connector_id, token)
        except Exception:
            pass
        oauth_store.revoke_token(uid, connector_id)
    # ryd enabled-flag
    store = _enabled_store()
    bucket = store.get(uid)
    if isinstance(bucket, dict) and connector_id in bucket:
        del bucket[connector_id]
        store[uid] = bucket
        dbc.set_runtime_state_value(_ENABLED_KEY, store)
    _audit("deleted", uid, connector_id)
    return True
