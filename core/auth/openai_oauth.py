from __future__ import annotations

import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from core.auth.profiles import (
    get_provider_auth_material_kind,
    get_provider_callback_intent_consistency,
    get_provider_callback_validation_state,
    get_provider_credentials,
    get_provider_exchange_readiness,
    get_provider_launch_freshness,
    get_provider_launch_result_state,
    get_provider_oauth_state,
    get_provider_state_view,
    provider_has_real_credentials,
    save_provider_credentials,
)
from core.runtime.config import CONFIG_DIR

PROVIDER_ID = "openai-codex"
_CONFIG_PATH = CONFIG_DIR / "provider_auth_config.json"
_DEFAULT_AUTHORIZE_URL = "https://auth.openai.com/oauth/authorize"
_DEFAULT_TOKEN_URL = "https://auth.openai.com/oauth/token"
_DEFAULT_SCOPES = "openid profile email offline_access"
_DEFAULT_AUDIENCE = "https://api.openai.com/v1"
_DEFAULT_REDIRECT_BASE_URL = "http://localhost:1455"
_DEFAULT_CALLBACK_PATH = "/auth/callback"


def get_openai_oauth_truth(*, profile: str) -> dict[str, Any]:
    oauth_state = get_provider_oauth_state(profile=profile, provider=PROVIDER_ID)
    auth_material_kind = get_provider_auth_material_kind(
        profile=profile,
        provider=PROVIDER_ID,
    )
    exchange_readiness = get_provider_exchange_readiness(
        profile=profile,
        provider=PROVIDER_ID,
    )
    return {
        "provider": PROVIDER_ID,
        "profile": profile,
        "oauth_state": oauth_state,
        "auth_material_kind": auth_material_kind,
        "has_real_credentials": provider_has_real_credentials(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "launch_result_state": get_provider_launch_result_state(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "launch_freshness": get_provider_launch_freshness(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "callback_validation_state": get_provider_callback_validation_state(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "exchange_readiness": exchange_readiness,
        "callback_intent_consistency": get_provider_callback_intent_consistency(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "profile_state": get_provider_state_view(
            profile=profile,
            provider=PROVIDER_ID,
        ),
        "oauth_client_configured": bool(str(load_openai_oauth_config().get("client_id") or "").strip()),
    }


def load_openai_oauth_config() -> dict[str, Any]:
    data: dict[str, Any] = {}
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    section = dict(data.get("openai_oauth") or {})
    env = __import__("os").environ
    client_id = str(section.get("client_id") or env.get("JARVIS_OPENAI_OAUTH_CLIENT_ID", "")).strip()
    authorize_url = str(section.get("authorize_url") or env.get("JARVIS_OPENAI_OAUTH_AUTHORIZE_URL", _DEFAULT_AUTHORIZE_URL)).strip()
    token_url = str(section.get("token_url") or env.get("JARVIS_OPENAI_OAUTH_TOKEN_URL", _DEFAULT_TOKEN_URL)).strip()
    scopes = str(section.get("scopes") or env.get("JARVIS_OPENAI_OAUTH_SCOPES", _DEFAULT_SCOPES)).strip()
    audience = str(section.get("audience") or env.get("JARVIS_OPENAI_OAUTH_AUDIENCE", _DEFAULT_AUDIENCE)).strip()
    redirect_base_url = str(section.get("redirect_base_url") or env.get("JARVIS_OPENAI_OAUTH_REDIRECT_BASE_URL", _DEFAULT_REDIRECT_BASE_URL)).strip()
    callback_path = str(section.get("callback_path") or env.get("JARVIS_OPENAI_OAUTH_CALLBACK_PATH", _DEFAULT_CALLBACK_PATH)).strip()
    return {
        "client_id": client_id,
        "authorize_url": authorize_url,
        "token_url": token_url,
        "scopes": scopes,
        "audience": audience,
        "redirect_base_url": redirect_base_url.rstrip("/"),
        "callback_path": "/" + callback_path.lstrip("/"),
    }


def save_openai_oauth_config(
    *,
    client_id: str,
    authorize_url: str = _DEFAULT_AUTHORIZE_URL,
    token_url: str = _DEFAULT_TOKEN_URL,
    scopes: str = _DEFAULT_SCOPES,
    audience: str = _DEFAULT_AUDIENCE,
    redirect_base_url: str = _DEFAULT_REDIRECT_BASE_URL,
    callback_path: str = _DEFAULT_CALLBACK_PATH,
) -> dict[str, Any]:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = {}
    if _CONFIG_PATH.exists():
        try:
            data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    data["openai_oauth"] = {
        "client_id": str(client_id).strip(),
        "authorize_url": str(authorize_url).strip(),
        "token_url": str(token_url).strip(),
        "scopes": str(scopes).strip(),
        "audience": str(audience).strip(),
        "redirect_base_url": str(redirect_base_url).strip().rstrip("/"),
        "callback_path": "/" + str(callback_path).strip().lstrip("/"),
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return load_openai_oauth_config()


def get_openai_callback_url(*, profile: str) -> str:
    config = load_openai_oauth_config()
    return f"{config['redirect_base_url']}{config['callback_path']}"


def build_openai_launch_intent(*, profile: str) -> dict[str, Any]:
    config = load_openai_oauth_config()
    client_id = str(config.get("client_id") or "").strip()
    if not client_id:
        raise ValueError("OpenAI OAuth client_id is not configured")
    verifier = _generate_code_verifier()
    challenge = _pkce_code_challenge(verifier)
    state_token = secrets.token_urlsafe(24)
    intent_id = f"openai-oauth-intent:{secrets.token_hex(8)}"
    redirect_uri = get_openai_callback_url(profile=profile)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": str(config.get("scopes") or _DEFAULT_SCOPES),
        "state": state_token,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "audience": str(config.get("audience") or _DEFAULT_AUDIENCE),
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "jarvis",
    }
    launch_url = f"{str(config['authorize_url']).rstrip('?')}?{urllib_parse.urlencode(params)}"
    launched_at = datetime.now(UTC).isoformat()
    credentials = {
        "oauth_launch_intent": True,
        "kind": "openai-oauth-launch-intent",
        "oauth_state": "launch-intent-created",
        "oauth_intent_id": intent_id,
        "oauth_launch_mode": "browser-pkce",
        "oauth_launch_url": launch_url,
        "oauth_launch_started_at": launched_at,
        "oauth_pkce_code_verifier": verifier,
        "oauth_pkce_code_challenge": challenge,
        "oauth_expected_state": state_token,
        "oauth_redirect_uri": redirect_uri,
        "browser_launch_requested": True,
        "browser_launched": False,
        "token_exchange_completed": False,
        "real_oauth": False,
        "created_by": "jarvis-openai-oauth",
    }
    save_provider_credentials(
        profile=profile,
        provider=PROVIDER_ID,
        credentials=credentials,
    )
    return {
        "intent_id": intent_id,
        "launch_url": launch_url,
        "redirect_uri": redirect_uri,
        "state": state_token,
        "code_challenge_method": "S256",
    }


def save_openai_callback(
    *,
    profile: str,
    callback_url: str,
) -> dict[str, Any]:
    credentials = get_provider_credentials(profile=profile, provider=PROVIDER_ID) or {}
    parsed = urllib_parse.urlsplit(str(callback_url).strip())
    params = urllib_parse.parse_qs(parsed.query, keep_blank_values=True)
    callback_keys = sorted(params.keys())
    credentials.update(
        {
            "oauth_callback_stub": True,
            "kind": "openai-oauth-callback",
            "oauth_state": "callback-received",
            "oauth_callback_received_at": datetime.now(UTC).isoformat(),
            "oauth_callback_url": callback_url,
            "oauth_callback_has_code": bool(params.get("code")),
            "oauth_callback_has_state": bool(params.get("state")),
            "oauth_callback_param_keys": callback_keys,
            "oauth_callback_code": str((params.get("code") or [""])[0]).strip(),
            "oauth_callback_state": str((params.get("state") or [""])[0]).strip(),
            "real_oauth": False,
        }
    )
    save_provider_credentials(
        profile=profile,
        provider=PROVIDER_ID,
        credentials=credentials,
    )
    return credentials


def exchange_openai_callback_code(*, profile: str) -> dict[str, Any]:
    credentials = get_provider_credentials(profile=profile, provider=PROVIDER_ID) or {}
    config = load_openai_oauth_config()
    client_id = str(config.get("client_id") or "").strip()
    if not client_id:
        raise ValueError("OpenAI OAuth client_id is not configured")
    code = str(credentials.get("oauth_callback_code") or "").strip()
    code_verifier = str(credentials.get("oauth_pkce_code_verifier") or "").strip()
    redirect_uri = str(credentials.get("oauth_redirect_uri") or get_openai_callback_url(profile=profile)).strip()
    expected_state = str(credentials.get("oauth_expected_state") or "").strip()
    callback_state = str(credentials.get("oauth_callback_state") or "").strip()
    if not code:
        raise ValueError("No OAuth code stored for profile")
    if expected_state and callback_state and expected_state != callback_state:
        raise ValueError("OAuth callback state mismatch")
    token_data = _post_openai_token_request(
        token_url=str(config.get("token_url") or _DEFAULT_TOKEN_URL),
        payload={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    stored = _store_openai_token_response(
        profile=profile,
        credentials=credentials,
        token_data=token_data,
    )
    return stored


def refresh_openai_access_token(*, profile: str) -> dict[str, Any]:
    credentials = get_provider_credentials(profile=profile, provider=PROVIDER_ID) or {}
    config = load_openai_oauth_config()
    client_id = str(config.get("client_id") or "").strip()
    refresh_token = str(credentials.get("refresh_token") or "").strip()
    if not client_id:
        raise ValueError("OpenAI OAuth client_id is not configured")
    if not refresh_token:
        raise ValueError("No refresh_token stored for profile")
    token_data = _post_openai_token_request(
        token_url=str(config.get("token_url") or _DEFAULT_TOKEN_URL),
        payload={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
        },
    )
    stored = _store_openai_token_response(
        profile=profile,
        credentials=credentials,
        token_data=token_data,
    )
    return stored


def get_openai_bearer_token(*, profile: str) -> str:
    credentials = get_provider_credentials(profile=profile, provider=PROVIDER_ID) or {}
    api_key = str(credentials.get("api_key") or "").strip()
    if api_key:
        return api_key
    access_token = str(credentials.get("access_token") or "").strip()
    expires_at_raw = str(credentials.get("expires_at") or "").strip()
    if access_token and not _is_expired(expires_at_raw):
        return access_token
    refreshed = refresh_openai_access_token(profile=profile)
    refreshed_token = str(refreshed.get("access_token") or "").strip()
    if refreshed_token:
        return refreshed_token
    raise RuntimeError("OpenAI credentials missing usable api_key or oauth access_token")


def _post_openai_token_request(*, token_url: str, payload: dict[str, str]) -> dict[str, Any]:
    encoded = urllib_parse.urlencode(payload).encode("utf-8")
    req = urllib_request.Request(
        token_url,
        data=encoded,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI OAuth token request failed: HTTP {exc.code}: {body}")
    except Exception as exc:
        raise RuntimeError(f"OpenAI OAuth token request failed: {exc}")


def _store_openai_token_response(
    *,
    profile: str,
    credentials: dict[str, Any],
    token_data: dict[str, Any],
) -> dict[str, Any]:
    access_token = str(token_data.get("access_token") or "").strip()
    if not access_token:
        raise RuntimeError("OpenAI OAuth token response missing access_token")
    expires_in = int(token_data.get("expires_in") or 3600)
    refreshed_at = datetime.now(UTC)
    refresh_token = str(token_data.get("refresh_token") or credentials.get("refresh_token") or "").strip()
    credentials.update(
        {
            "kind": "openai-oauth-real",
            "oauth_state": "real-stored",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": str(token_data.get("token_type") or "Bearer"),
            "scope": str(token_data.get("scope") or credentials.get("scope") or ""),
            "expires_in": expires_in,
            "expires_at": (refreshed_at + timedelta(seconds=max(0, expires_in - 60))).isoformat(),
            "refreshed_at": refreshed_at.isoformat(),
            "token_exchange_completed": True,
            "token_exchange_completed_at": refreshed_at.isoformat(),
            "real_oauth": True,
        }
    )
    save_provider_credentials(
        profile=profile,
        provider=PROVIDER_ID,
        credentials=credentials,
    )
    return credentials


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(64)


def _pkce_code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def _is_expired(expires_at_raw: str) -> bool:
    if not expires_at_raw:
        return False
    try:
        return datetime.now(UTC) >= datetime.fromisoformat(expires_at_raw)
    except ValueError:
        return False
