"""Gmail-connector — API-klient + tool-handlers (vertical: search + list).

Bruger BRUGERENS egen Google-token fra oauth_store (get_fresh_token → auto-refresh).
Google-pakken deler ÉN OAuth (provider="google"), så tokenet hentes under "google".
Intet token / manglende scope → {"status":"error","error":"gmail_not_connected"}.

`send_message` er bygget men IKKE registreret som tool endnu — afsendelse af mail
på brugerens vegne kræver approval-flow (følger separat). Kun læse-tools er live.
"""
from __future__ import annotations

from core.services.oauth_store import get_fresh_token

_API = "https://gmail.googleapis.com/gmail/v1/users/me"
_PROVIDER = "google"

GMAIL_CONNECTOR_TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "gmail_search",
            "description": (
                "Søg i brugerens Gmail via deres EGEN forbundne Google-konto (connector). "
                "Bruger Gmail-søgesyntaks (fx 'from:bank is:unread newer_than:7d'). "
                "Kræver at brugeren har forbundet Gmail i Marketplace. Returnerer "
                "afsender/emne/uddrag/dato — ikke fuld brødtekst."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Gmail-søgeudtryk, fx 'is:unread from:chef'"},
                    "max_results": {"type": "integer", "description": "Maks antal mails (1-25, standard 10)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_send",
            "description": (
                "Send en mail på brugerens vegne via deres EGEN forbundne Gmail. "
                "KRÆVER brugerens godkendelse (approval-kort) før afsendelse — kald bare "
                "værktøjet direkte, runtime håndterer godkendelsen. Kræver forbundet Gmail."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Modtagerens email-adresse"},
                    "subject": {"type": "string", "description": "Emnelinje"},
                    "body": {"type": "string", "description": "Mailens tekst (ren tekst)"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_modify",
            "description": (
                "Flyt, arkivér eller gendan EKSPLICITTE Gmail-beskeder via deres EGEN "
                "forbundne konto. Kræver message-id'er fra gmail_search/gmail_list — "
                "der er ingen søgestreng, så bred oprydning kræver at id'erne først er "
                "listet. dry_run er sand som standard og ændrer intet; kald igen med "
                "dry_run=false for at udføre. Maks 500 id'er pr. kald."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste af Gmail message-id'er (fra gmail_search)",
                    },
                    "action": {
                        "type": "string",
                        "enum": ["trash", "archive", "untrash"],
                        "description": "trash = Papirkurv, archive = fjern fra indbakke, untrash = tilbage",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Sand = vis kun hvad der ville ske (standard). Falsk = udfør.",
                    },
                },
                "required": ["message_ids"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_list",
            "description": (
                "List de nyeste mails i brugerens Gmail-indbakke via deres EGEN forbundne "
                "Google-konto (connector). Kræver forbundet Gmail i Marketplace."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Maks antal mails (1-25, standard 10)"},
                },
                "required": [],
            },
        },
    },
]


def _token(user_id: str) -> dict | None:
    tok = get_fresh_token(user_id, _PROVIDER)
    if not tok or not tok.get("access_token"):
        return None
    return tok


def _headers(token: dict) -> dict:
    return {"Authorization": f"Bearer {token.get('access_token')}"}


def _clamp(n, lo: int, hi: int, default: int) -> int:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, n))


def _fetch_messages(user_id: str, query: str | None, max_results: int) -> dict:
    """Fælles kerne for search/list: hent id-liste → berig med headers/snippet."""
    token = _token(user_id)
    if not token:
        return {"status": "error", "error": "gmail_not_connected"}
    n = _clamp(max_results, 1, 25, 10)
    try:
        import httpx
        params: dict = {"maxResults": n}
        if query:
            params["q"] = query
        r = httpx.get(f"{_API}/messages", headers=_headers(token), params=params, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "error": "gmail_not_connected"}
        if r.status_code == 403:
            return {"status": "error", "error": "gmail_scope_missing"}
        if r.status_code != 200:
            return {"status": "error", "error": f"gmail_http_{r.status_code}"}
        ids = [m.get("id") for m in (r.json().get("messages") or []) if isinstance(m, dict)]
        out = []
        for mid in ids:
            mr = httpx.get(
                f"{_API}/messages/{mid}",
                headers=_headers(token),
                params={"format": "metadata", "metadataHeaders": ["Subject", "From", "Date"]},
                timeout=20,
            )
            if mr.status_code != 200:
                continue
            md = mr.json()
            hdrs = {h.get("name", "").lower(): h.get("value", "")
                    for h in (md.get("payload", {}).get("headers") or []) if isinstance(h, dict)}
            out.append({
                "id": mid,
                "from": hdrs.get("from", ""),
                "subject": hdrs.get("subject", "(intet emne)"),
                "date": hdrs.get("date", ""),
                "snippet": md.get("snippet", ""),
                "unread": "UNREAD" in (md.get("labelIds") or []),
            })
        return {"status": "ok", "messages": out, "count": len(out)}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"gmail_request_failed: {e}"}


def search(user_id: str, query: str, *, max_results: int = 10) -> dict:
    if not (query or "").strip():
        return {"status": "error", "error": "query_required"}
    return _fetch_messages(user_id, query, max_results)


def list_inbox(user_id: str, *, max_results: int = 10) -> dict:
    return _fetch_messages(user_id, None, max_results)


_AKTIONER: dict[str, dict] = {
    "trash": {"add": ["TRASH"], "remove": ["INBOX"]},
    "archive": {"add": [], "remove": ["INBOX"]},
    "untrash": {"add": ["INBOX"], "remove": ["TRASH"]},
}

# Gmail batchModify tager op til 1000 id'er. Vi holder os under og kræver
# eksplicitte id'er — aldrig en søgestreng — så et kald ikke kan ramme bredt
# ved et uheld i en formulering.
_MAX_BATCH = 500


def modify_messages(
    user_id: str,
    message_ids: list[str],
    *,
    action: str = "trash",
    dry_run: bool = True,
) -> dict:
    """Flyt/arkivér/fortryd på EKSPLICITTE message-id'er.

    `dry_run` er default: et kald uden `dry_run=false` ændrer intet, men viser
    hvad der ville ske. Det er med vilje — den her funktion kan flytte tusinder
    af mails, og et forkert argument må ikke kunne gøre det i ét hug.

    Id'erne skal komme fra `search()`/`list_inbox()`. Der er ingen søgestreng i
    signaturen, så bred sletning kræver at kalderen selv har listet dem.
    """
    token = _token(user_id)
    if not token:
        return {"status": "error", "error": "gmail_not_connected"}
    plan = _AKTIONER.get((action or "").strip().lower())
    if not plan:
        return {"status": "error", "error": f"ukendt_handling: {action}",
                "gyldige": sorted(_AKTIONER)}
    ids = [str(i).strip() for i in (message_ids or []) if str(i).strip()]
    if not ids:
        return {"status": "error", "error": "message_ids_required"}
    if len(ids) > _MAX_BATCH:
        return {"status": "error",
                "error": f"for_mange_ids: {len(ids)} > {_MAX_BATCH}",
                "hint": "del op i flere kald"}
    if dry_run:
        return {
            "status": "ok",
            "dry_run": True,
            "action": action,
            "count": len(ids),
            "would_add": plan["add"],
            "would_remove": plan["remove"],
            "sample_ids": ids[:5],
            "note": "Intet ændret. Kald igen med dry_run=false for at udføre.",
        }
    try:
        import httpx
        r = httpx.post(
            f"{_API}/messages/batchModify",
            headers=_headers(token),
            json={"ids": ids, "addLabelIds": plan["add"], "removeLabelIds": plan["remove"]},
            timeout=60,
        )
        if r.status_code == 401:
            return {"status": "error", "error": "gmail_not_connected"}
        if r.status_code == 403:
            return {"status": "error", "error": "gmail_scope_missing",
                    "hint": "tokenet mangler gmail.modify — forbind Gmail igen"}
        if r.status_code not in (200, 204):
            return {"status": "error", "error": f"gmail_http_{r.status_code}"}
        return {"status": "ok", "dry_run": False, "action": action, "modified": len(ids)}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"gmail_request_failed: {e}"}


def send_message(user_id: str, to: str, subject: str, body: str) -> dict:
    """Send en mail på brugerens vegne. KRÆVER approval-flow før den eksponeres som tool."""
    token = _token(user_id)
    if not token:
        return {"status": "error", "error": "gmail_not_connected"}
    if not (to or "").strip():
        return {"status": "error", "error": "to_required"}
    try:
        import base64
        from email.message import EmailMessage
        import httpx
        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject or ""
        msg.set_content(body or "")
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        r = httpx.post(f"{_API}/messages/send", headers=_headers(token),
                       json={"raw": raw}, timeout=20)
        if r.status_code == 401:
            return {"status": "error", "error": "gmail_not_connected"}
        if r.status_code == 403:
            return {"status": "error", "error": "gmail_scope_missing"}
        if r.status_code not in (200, 202):
            return {"status": "error", "error": f"gmail_http_{r.status_code}"}
        return {"status": "ok", "id": r.json().get("id")}
    except Exception as e:  # noqa: BLE001
        return {"status": "error", "error": f"gmail_request_failed: {e}"}
