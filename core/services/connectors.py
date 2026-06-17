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
    # ── Google-pakken (P1) — deler ÉN Google-OAuth (provider="google").
    #    status="coming_soon" indtil per-app tools er wired (fase 2). ──
    {
        "id": "gmail", "name": "Gmail", "kind": "oauth", "provider": "google",
        "category": "Google", "icon": "mail", "status": "available",
        "desc": "Læs, søg og send mails",
        "scopes": ["gmail.readonly", "gmail.send"],
        "oauth_scopes": [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.send",
        ],
        "post_connect_hint": "Nu kan jeg kigge i din Gmail — skal jeg tjekke din indbakke?",
    },
    {
        "id": "google-calendar", "name": "Google Calendar", "kind": "oauth", "provider": "google",
        "category": "Google", "icon": "calendar", "status": "available",
        "desc": "Læs kommende aftaler",
        "scopes": ["calendar.events"],
        "oauth_scopes": ["https://www.googleapis.com/auth/calendar.events"],
        "post_connect_hint": "Nu kan jeg se din kalender — skal jeg tjekke hvad du har i denne uge?",
    },
    {
        "id": "google-drive", "name": "Google Drive", "kind": "oauth", "provider": "google",
        "category": "Google", "icon": "hard-drive", "status": "available",
        "desc": "Søg og læs filer",
        "scopes": ["drive.readonly"],
        "oauth_scopes": ["https://www.googleapis.com/auth/drive.readonly"],
    },
    {
        "id": "google-docs", "name": "Google Docs", "kind": "oauth", "provider": "google",
        "category": "Google", "icon": "file-text", "status": "available",
        "desc": "Læs dokumenter",
        "scopes": ["documents"],
        "oauth_scopes": ["https://www.googleapis.com/auth/documents"],
    },
    {
        "id": "google-sheets", "name": "Google Sheets", "kind": "oauth", "provider": "google",
        "category": "Google", "icon": "table", "status": "available",
        "desc": "Læs regneark",
        "scopes": ["spreadsheets"],
        "oauth_scopes": ["https://www.googleapis.com/auth/spreadsheets"],
    },
    {
        "id": "google-slides", "name": "Google Slides", "kind": "oauth", "provider": "google",
        "category": "Google", "icon": "presentation", "status": "available",
        "desc": "Læs præsentationer",
        "scopes": ["presentations"],
        "oauth_scopes": ["https://www.googleapis.com/auth/presentations"],
    },
    # ── Udvidede (P2) ──
    {
        "id": "build-web-apps", "name": "Build Web Apps", "kind": "local",
        "category": "Udvikling", "icon": "code", "status": "coming_soon",
        "desc": "Prototype og deploy små webapps", "scopes": [],
    },
    {
        "id": "huggingface", "name": "Hugging Face", "kind": "oauth", "provider": "huggingface",
        "category": "AI", "icon": "cpu", "status": "coming_soon",
        "desc": "Adgang til Hugging Face-modeller", "scopes": ["read"],
    },
    {
        "id": "openai-models", "name": "OpenAI / Andre", "kind": "oauth", "provider": "openai",
        "category": "AI", "icon": "brain", "status": "coming_soon",
        "desc": "Adgang til eksterne model-API'er", "scopes": [],
    },
    {
        "id": "pdf", "name": "PDF", "kind": "local",
        "category": "Dokumenter", "icon": "file", "status": "coming_soon",
        "desc": "Læs, analysér og ekstraher PDF", "scopes": [],
    },
    # ── Langsigtet (P3) ──
    {
        "id": "spotify", "name": "Spotify", "kind": "oauth", "provider": "spotify",
        "category": "Medier", "icon": "music", "status": "coming_soon",
        "desc": "Musikstyring", "scopes": ["user-read-playback-state", "user-modify-playback-state"],
    },
    {
        "id": "slack", "name": "Slack", "kind": "oauth", "provider": "slack",
        "category": "Kommunikation", "icon": "message-square", "status": "coming_soon",
        "desc": "Læs og skriv i Slack", "scopes": ["chat:write", "channels:read"],
    },
    {
        "id": "notion", "name": "Notion / Obsidian", "kind": "oauth", "provider": "notion",
        "category": "Noter", "icon": "book-open", "status": "coming_soon",
        "desc": "Note-synkronisering", "scopes": [],
    },
    {
        "id": "notes", "name": "Huskesedler", "kind": "local",
        "category": "Noter", "icon": "sticky-note", "status": "coming_soon",
        "desc": "Simple notater", "scopes": [],
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


def _provider_of(c: dict) -> str:
    """OAuth-provider for en connector. Google-pakken deler provider='google'."""
    return str(c.get("provider") or c["id"])


def _connected(user_id: str, c: dict) -> bool:
    if c["kind"] == "local":
        return True
    return bool(has_token(user_id, _provider_of(c)))


def oauth_request_for(connector_id: str) -> tuple[str, list[str]] | None:
    """Map et connector-id → (oauth_provider, scopes) til /api/oauth/{id}/start.

    Fx 'gmail' → ('google', [gmail-scope-URLs]). Tom scope-liste = brug providerens
    default. None hvis id'et ikke er en (oauth-)connector.
    """
    c = _BY_ID.get((connector_id or "").strip())
    if not c or c.get("kind") != "oauth":
        return None
    return _provider_of(c), list(c.get("oauth_scopes") or [])


def list_for_user(user_id: str) -> list[dict]:
    """Hele kataloget beriget med per-bruger `connected` + `enabled`."""
    uid = (user_id or "").strip()
    out: list[dict] = []
    for c in _CATALOG:
        status = c.get("status", "available")
        out.append({
            "id": c["id"], "name": c["name"], "kind": c["kind"],
            "category": c["category"], "icon": c["icon"], "desc": c["desc"],
            "scopes": list(c.get("scopes") or []),
            "post_connect_hint": c.get("post_connect_hint"),
            "status": status,
            # coming_soon kan ikke forbindes endnu → aldrig "connected".
            "connected": False if status == "coming_soon" else _connected(uid, c),
            "enabled": is_enabled(uid, c["id"]),
        })
    return out


def _audit(event: str, user_id: str, connector_id: str) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish("connector." + event, {"user_id": user_id, "connector": connector_id})
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
        provider = _provider_of(c)
        try:
            token = get_fresh_token(uid, provider)
            if token:
                oauth_flow.revoke_remote(provider, token)
        except Exception:
            pass
        oauth_store.revoke_token(uid, provider)
    # ryd enabled-flag
    store = _enabled_store()
    bucket = store.get(uid)
    if isinstance(bucket, dict) and connector_id in bucket:
        del bucket[connector_id]
        store[uid] = bucket
        dbc.set_runtime_state_value(_ENABLED_KEY, store)
    _audit("deleted", uid, connector_id)
    return True
