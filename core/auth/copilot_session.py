"""GitHub Copilot session-token exchange.

The long-lived OAuth access_token stored in credentials.json is NOT what
api.githubcopilot.com accepts. Before calling any Copilot API, that OAuth
token must be exchanged at GET api.github.com/copilot_internal/v2/token
for a short-lived session bearer (TTL ~25 minutes). The session token's
`expires_at` field is a unix timestamp we cache against.

This exchange only succeeds if the OAuth token was obtained via a
Copilot-authorized client_id (VSCode's 01ab8ac9400c4e429b23 works) AND
the authenticated GitHub user has an active Copilot subscription.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from core.auth.profiles import get_provider_state

_PROVIDER = "github-copilot"
_EXCHANGE_URL = "https://api.github.com/copilot_internal/v2/token"
_EXPIRY_SAFETY_SECONDS = 60

_cache_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}


def _load_oauth_access_token(*, profile: str) -> str:
    state = get_provider_state(profile=profile, provider=_PROVIDER)
    if state is None:
        raise RuntimeError("copilot session: no profile state — run device flow first")
    credentials_path = Path(str(state.get("credentials_path", "")))
    if not credentials_path.exists():
        raise RuntimeError("copilot session: credentials.json missing")
    credentials = json.loads(credentials_path.read_text(encoding="utf-8"))
    token = str(credentials.get("access_token") or "")
    if not token:
        raise RuntimeError("copilot session: no access_token in credentials.json")
    return token


def _exchange_for_session(oauth_token: str) -> dict[str, Any]:
    req = urllib_request.Request(
        _EXCHANGE_URL,
        headers={
            "Authorization": f"token {oauth_token}",
            "Accept": "application/json",
            "Editor-Version": "vscode/1.95.0",
            "Editor-Plugin-Version": "copilot-chat/0.23.0",
            "User-Agent": "GitHubCopilotChat/0.23.0",
        },
        method="GET",
    )
    try:
        with urllib_request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        if exc.code == 401 or exc.code == 403:
            raise RuntimeError(
                f"copilot session exchange denied (HTTP {exc.code}): "
                f"token is not Copilot-authorized — re-run device flow with VSCode client_id. "
                f"Response: {body[:200]}"
            )
        if exc.code == 404:
            raise RuntimeError(
                "copilot session exchange 404: OAuth client_id is not registered "
                "as a Copilot app — check provider_auth_config.json uses VSCode client_id "
                "(01ab8ac9400c4e429b23) and re-run device flow"
            )
        raise RuntimeError(f"copilot session exchange HTTP {exc.code}: {body[:200]}")
    except Exception as exc:
        raise RuntimeError(f"copilot session exchange failed: {exc}")


def get_copilot_session_token(*, profile: str) -> str:
    """Return a valid Copilot session bearer token, exchanging & caching as needed."""
    now = time.time()
    with _cache_lock:
        cached = _cache.get(profile)
        if cached:
            expires_at = float(cached.get("expires_at", 0))
            if expires_at - _EXPIRY_SAFETY_SECONDS > now:
                return str(cached["token"])

        oauth_token = _load_oauth_access_token(profile=profile)
        response = _exchange_for_session(oauth_token)
        session_token = str(response.get("token") or "")
        if not session_token:
            raise RuntimeError(
                f"copilot session exchange returned no token: {response}"
            )
        expires_at = float(response.get("expires_at") or (now + 1500))
        _cache[profile] = {
            "token": session_token,
            "expires_at": expires_at,
            "endpoints": response.get("endpoints") or {},
        }
        return session_token


def get_cached_session_endpoints(*, profile: str) -> dict[str, Any]:
    with _cache_lock:
        cached = _cache.get(profile)
        if cached:
            return dict(cached.get("endpoints") or {})
    return {}


def invalidate_session_cache(*, profile: str | None = None) -> None:
    with _cache_lock:
        if profile is None:
            _cache.clear()
        else:
            _cache.pop(profile, None)
