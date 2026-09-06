"""OAuth/bearer til remote MCP-servere.

Porteret fra jarvis-code 2026-09-06.

Tokens er hemmeligheder, så de ligger IKKE i state_store sammen med
allowliste og pins. De får deres egen fil under `~/.jarvis-v2/config/` med
0600 — samme sted og samme rettigheder som resten af runtimens
konfigurations-hemmeligheder. Repoet ser dem aldrig.

Et udløbet token på en remote server retter sig selv: `_send_http` kører
refresh-grantet én gang ved 401 og prøver igen, så en forbindelse der har
stået natten over ikke fejler ved første kald om morgenen.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

TOKENS_PATH = Path("~/.jarvis-v2/config/mcp_tokens.json").expanduser()
_ENV_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
# Foernyer lidt FOER udloeb — et token der udloeber mens requesten er i luften
# giver en 401 vi kunne have undgaaet.
_MARGIN_S = 60


def _expand_env(value: Any) -> str:
    """`${MIN_NOEGLE}` slaas op i miljoeet, saa en config kan deles uden token."""
    return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), ""), str(value or ""))


def _load() -> dict[str, Any]:
    try:
        return json.loads(TOKENS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict[str, Any]) -> None:
    try:
        TOKENS_PATH.parent.mkdir(parents=True, exist_ok=True)
        TOKENS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        os.chmod(TOKENS_PATH, 0o600)
    except Exception:
        logger.warning("mcp_auth: kunne ikke gemme tokens", exc_info=True)


def get_token(name: str) -> dict[str, Any] | None:
    rec = _load().get(str(name or ""))
    return dict(rec) if isinstance(rec, dict) else None


def set_token(name: str, *, access_token: str, refresh_token: str | None = None,
              expires_in: Any = None, token_url: str = "",
              client_id: str = "", client_secret: str = "") -> None:
    data = _load()
    rec: dict[str, Any] = dict(data.get(str(name)) or {})
    rec["access_token"] = str(access_token)
    if refresh_token:
        rec["refresh_token"] = str(refresh_token)
    if token_url:
        rec["token_url"] = str(token_url)
    if client_id:
        rec["client_id"] = str(client_id)
    if client_secret:
        rec["client_secret"] = str(client_secret)
    try:
        rec["expires_at"] = time.time() + float(expires_in) if expires_in else None
    except (TypeError, ValueError):
        rec["expires_at"] = None
    data[str(name)] = rec
    _save(data)


def needs_refresh(name: str) -> bool:
    rec = get_token(name)
    if not rec or not rec.get("expires_at"):
        return False
    try:
        return time.time() >= float(rec["expires_at"]) - _MARGIN_S
    except (TypeError, ValueError):
        return False


def refresh(name: str) -> bool:
    """Kør refresh_token-grantet. False = intet at fornye, eller det fejlede."""
    rec = get_token(name)
    if not rec or not rec.get("refresh_token") or not rec.get("token_url"):
        return False
    body = {"grant_type": "refresh_token", "refresh_token": rec["refresh_token"]}
    for felt in ("client_id", "client_secret"):
        if rec.get(felt):
            body[felt] = rec[felt]
    try:
        import httpx
        svar = httpx.post(rec["token_url"], data=body, timeout=20)
        svar.raise_for_status()
        payload = svar.json()
    except Exception:
        logger.info("mcp_auth: refresh fejlede for %s", name)
        return False
    access = payload.get("access_token")
    if not access:
        return False
    set_token(name, access_token=access,
              refresh_token=payload.get("refresh_token", rec["refresh_token"]),
              expires_in=payload.get("expires_in"))
    return True


def resolve_headers(name: str, config: dict[str, Any]) -> dict[str, str]:
    """Headers til en request mod *name*.

    Rækkefølge: eksplicitte `headers` i config vinder (med ${ENV} udfoldet);
    ellers `auth`-blokken eller token-lageret. Et udløbet token fornyes først.
    """
    headers: dict[str, str] = {}
    for k, v in (config.get("headers") or {}).items():
        headers[str(k)] = _expand_env(v)
    if any(h.lower() == "authorization" for h in headers):
        return headers

    auth = config.get("auth") or {}
    atype = str(auth.get("type") or "").lower()
    token = ""
    if atype == "bearer" and auth.get("token"):
        token = _expand_env(auth["token"])
    elif atype in ("oauth", "bearer", ""):
        if needs_refresh(name):
            refresh(name)
        rec = get_token(name)
        if rec and rec.get("access_token"):
            token = str(rec["access_token"])
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
