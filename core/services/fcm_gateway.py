"""FCM HTTP v1 gateway — data-only push. Google ser kun et vaekke-signal.

Parallel til ntfy_gateway. OAuth via google-auth (allerede i ai-miljoeet).
Config i runtime.json: fcm_project_id + fcm_service_account_path.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def _runtime() -> dict:
    try:
        return json.loads((Path.home() / ".jarvis-v2" / "config" / "runtime.json").read_text())
    except Exception:
        return {}


def _project_id() -> str | None:
    return _runtime().get("fcm_project_id")


def _sa_path() -> str | None:
    return _runtime().get("fcm_service_account_path")


def is_configured() -> bool:
    return bool(_project_id()) and bool(_sa_path()) and Path(_sa_path() or "").exists()


def _access_token() -> str | None:
    """Mint en OAuth-access-token fra service-account via google-auth."""
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
        creds = service_account.Credentials.from_service_account_file(_sa_path(), scopes=[_SCOPE])
        creds.refresh(Request())
        return creds.token
    except Exception as e:
        logger.warning("fcm: kunne ikke minte access-token: %s", e)
        return None


def _build_message(token: str, data: dict) -> dict:
    # ALLE data-vaerdier skal vaere strenge i FCM v1.
    str_data = {k: str(v) for k, v in (data or {}).items()}
    msg: dict = {
        "token": token,
        "data": str_data,
        "android": {"priority": "high"},
    }
    # Hvis payload har title+preview, tilføj en notification-blok så OS'et
    # viser en synlig notifikation selv hvis app'en ikke er åben.
    title = str_data.get("title") or ""
    body = str_data.get("preview") or str_data.get("body") or ""
    if title and body:
        msg["notification"] = {"title": title, "body": body}
    return {"message": msg}


def send(token: str, data: dict) -> tuple[bool, str]:
    """Send data-only push. Returnerer (ok, code). code='invalid' => slet token."""
    if not is_configured():
        return (False, "unconfigured")
    tok = _access_token()
    pid = _project_id()
    if not tok or not pid:
        return (False, "auth")
    url = f"https://fcm.googleapis.com/v1/projects/{pid}/messages:send"
    payload = json.dumps(_build_message(token, data)).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            r.read()
        return (True, "ok")
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode()
        except Exception:
            pass
        if e.code in (404, 400) and ("NOT_FOUND" in body or "UNREGISTERED" in body or "INVALID_ARGUMENT" in body):
            return (False, "invalid")
        logger.warning("fcm: HTTP %s: %s", e.code, body[:200])
        return (False, "http")
    except Exception as e:
        logger.warning("fcm: send-fejl: %s", e)
        return (False, "net")
