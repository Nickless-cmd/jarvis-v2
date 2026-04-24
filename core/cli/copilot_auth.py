from __future__ import annotations

import argparse
import json
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import uuid4

from core.services.non_visible_lane_execution import (
    coding_lane_execution_truth,
)
from core.auth.copilot_oauth import get_copilot_oauth_truth
from core.auth.profiles import (
    get_provider_state,
    get_provider_state_view,
    revoke_provider,
    save_provider_credentials,
)
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import init_db

_PROVIDER = "github-copilot"
_CREATED_BY = "jarvis-cli"

_GITHUB_OAUTH_DEVICE_CODE_URL = "https://github.com/login/device/code"
_GITHUB_OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"

# VSCode's public GitHub OAuth client_id. Registered as a Copilot-authorized app,
# so tokens obtained via this client_id can call /copilot_internal/v2/token and
# reach the full Copilot model catalog (Claude, GPT-5, Gemini, etc).
# Used by numerous community tools (aider, opencode, avante.nvim, continue.dev).
_VSCODE_COPILOT_CLIENT_ID = "01ab8ac9400c4e429b23"


def _get_github_copilot_client_id() -> str:
    import os
    from core.runtime.config import CONFIG_DIR

    provider_auth_config = CONFIG_DIR / "provider_auth_config.json"
    if provider_auth_config.exists():
        try:
            data = json.loads(provider_auth_config.read_text(encoding="utf-8"))
            client_id = data.get("github_copilot", {}).get("client_id", "").strip()
            if client_id:
                return client_id
        except Exception:
            pass

    env_client_id = str(os.environ.get("JARVIS_GITHUB_COPILOT_CLIENT_ID", "")).strip()
    if env_client_id:
        return env_client_id

    return _VSCODE_COPILOT_CLIENT_ID


def _save_github_copilot_client_id(client_id: str) -> None:
    from pathlib import Path
    import json
    from datetime import UTC, datetime
    from core.runtime.config import CONFIG_DIR

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    provider_auth_config = CONFIG_DIR / "provider_auth_config.json"

    data = {}
    if provider_auth_config.exists():
        try:
            data = json.loads(provider_auth_config.read_text(encoding="utf-8"))
        except Exception:
            pass

    if "github_copilot" not in data:
        data["github_copilot"] = {}
    data["github_copilot"]["client_id"] = client_id
    data["github_copilot"]["updated_at"] = datetime.now(UTC).isoformat()

    provider_auth_config.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def cmd_copilot_auth_status(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    coding_lane = coding_lane_execution_truth()
    oauth_truth = get_copilot_oauth_truth(profile=args.auth_profile)
    provider_state = get_provider_state(
        profile=args.auth_profile,
        provider=_PROVIDER,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "auth_material_kind": oauth_truth["auth_material_kind"],
                "oauth_state": oauth_truth["oauth_state"],
                "oauth_truth": oauth_truth,
                "coding_lane": coding_lane,
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if provider_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_copilot_client_id(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    client_id = str(args.client_id or "").strip()
    if not client_id:
        raise ValueError("client_id is required")

    _save_github_copilot_client_id(client_id)

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "action": "configure-client-id",
                "client_id_configured": True,
                "source": "cli-argument",
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_start_copilot_device_flow(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    device_code_response = _request_github_device_code()
    device_code = str(device_code_response.get("device_code", ""))
    user_code = str(device_code_response.get("user_code", ""))
    verification_uri = str(device_code_response.get("verification_uri", ""))
    verification_uri_complete = str(
        device_code_response.get("verification_uri_complete", verification_uri)
    )
    expires_in = int(device_code_response.get("expires_in", 600))
    interval = int(device_code_response.get("interval", 5))

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "action": "start-device-flow",
                "user_code": user_code,
                "verification_uri": verification_uri,
                "verification_uri_complete": verification_uri_complete,
                "expires_in_seconds": expires_in,
                "poll_interval_seconds": interval,
                "instruction": f"Visit {verification_uri_complete} and enter code: {user_code}",
            },
            indent=2,
            ensure_ascii=False,
        ),
    )

    started_at = datetime.now(UTC).isoformat()
    profile_state = save_provider_credentials(
        profile=args.auth_profile,
        provider=_PROVIDER,
        credentials={
            "kind": "github-copilot-oauth-device-flow",
            "oauth_state": "device-flow-started",
            "device_code": device_code,
            "user_code": user_code,
            "verification_uri": verification_uri,
            "verification_uri_complete": verification_uri_complete,
            "expires_in": expires_in,
            "interval": interval,
            "device_flow_started_at": started_at,
            "device_authorization_completed": False,
            "token_exchange_completed": False,
            "real_oauth": False,
            "created_by": _CREATED_BY,
        },
    )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "start-device-flow",
                "credentials_saved": True,
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if profile_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_poll_copilot_token_exchange(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    credentials = _load_provider_credentials_for_action(
        profile=args.auth_profile,
        action="poll-token",
    )

    device_code = str(credentials.get("device_code", ""))
    if not device_code:
        raise ValueError("No device_code found. Start device flow first.")

    expires_in = int(credentials.get("expires_in", 600))
    started_at_str = str(credentials.get("device_flow_started_at", ""))
    if started_at_str:
        try:
            started_at = datetime.fromisoformat(started_at_str)
            elapsed = (datetime.now(UTC) - started_at).total_seconds()
            if elapsed > expires_in:
                raise ValueError(
                    f"Device code expired. Elapsed {elapsed}s > {expires_in}s. Start new flow."
                )
        except ValueError:
            pass

    interval = int(credentials.get("interval", 5))

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "action": "poll-token-exchange",
                "polling": True,
                "interval_seconds": interval,
                "instruction": "Polling GitHub for authorization...",
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    token_response = _poll_github_token_exchange(
        device_code=device_code, interval=interval
    )

    if "error" in token_response:
        error = str(token_response.get("error", "unknown"))
        error_description = str(token_response.get("error_description", ""))
        print(
            json.dumps(
                {
                    "ok": False,
                    "provider": _PROVIDER,
                    "auth_profile": args.auth_profile,
                    "action": "poll-token-exchange",
                    "error": error,
                    "error_description": error_description,
                    "auth_status": f"poll-failed-{error}",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        credentials.update(
            {
                "oauth_state": "device-flow-poll-failed",
                "token_exchange_error": error,
                "token_exchange_error_description": error_description,
                "token_exchange_completed": False,
                "real_oauth": False,
            }
        )
        save_provider_credentials(
            profile=args.auth_profile,
            provider=_PROVIDER,
            credentials=credentials,
        )
        return

    access_token = str(token_response.get("access_token", ""))
    token_type = str(token_response.get("token_type", "bearer"))
    expires_in_token = token_response.get("expires_in")
    refresh_token = str(token_response.get("refresh_token", ""))
    refresh_token_expires_in = token_response.get("refresh_token_expires_in")

    if not access_token:
        raise RuntimeError("No access_token in token response")

    completed_at = datetime.now(UTC).isoformat()
    credentials.update(
        {
            "kind": "github-copilot-oauth-device-flow-complete",
            "oauth_state": "real-stored",
            "access_token": access_token,
            "token_type": token_type,
            "expires_in": expires_in_token,
            "refresh_token": refresh_token,
            "refresh_token_expires_in": refresh_token_expires_in,
            "device_authorization_completed": True,
            "token_exchange_completed": True,
            "token_exchange_completed_at": completed_at,
            "real_oauth": True,
        }
    )
    profile_state = save_provider_credentials(
        profile=args.auth_profile,
        provider=_PROVIDER,
        credentials=credentials,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "action": "poll-token-exchange",
                "success": True,
                "token_received": True,
                "token_type": token_type,
                "expires_in": expires_in_token,
                "has_refresh_token": bool(refresh_token),
                "auth_status": "exchange-complete",
                "coding_lane": coding_lane_execution_truth(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _request_github_device_code() -> dict:
    client_id = _get_github_copilot_client_id()
    data = urllib_parse.urlencode(
        {
            "client_id": client_id,
            "scope": "read:user",
        }
    ).encode("utf-8")

    req = urllib_request.Request(
        _GITHUB_OAUTH_DEVICE_CODE_URL,
        data=data,
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
        raise RuntimeError(
            f"GitHub device code request failed: HTTP {exc.code}: {body}"
        )
    except Exception as exc:
        raise RuntimeError(f"GitHub device code request failed: {exc}")


def _poll_github_token_exchange(*, device_code: str, interval: int) -> dict:
    client_id = _get_github_copilot_client_id()
    data = urllib_parse.urlencode(
        {
            "client_id": client_id,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }
    ).encode("utf-8")

    req = urllib_request.Request(
        _GITHUB_OAUTH_TOKEN_URL,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )

    max_attempts = 120
    for attempt in range(max_attempts):
        try:
            with urllib_request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if exc.code == 400:
                error_data = json.loads(body)
                error = str(error_data.get("error", ""))
                if error == "authorization_pending":
                    continue
                if error == "slow_down":
                    interval += 1
                    continue
                if error == "expired_token":
                    return {
                        "error": "expired_token",
                        "error_description": "Device code expired",
                    }
                if error == "incorrect_device_code":
                    return {
                        "error": "incorrect_device_code",
                        "error_description": "Device code mismatch",
                    }
                return error_data
            raise RuntimeError(f"Token exchange HTTP error: {exc.code}: {body}")
        except Exception as exc:
            raise RuntimeError(f"Token exchange request failed: {exc}")

        if "access_token" in result:
            return result

        import time

        time.sleep(interval)

    return {
        "error": "timeout",
        "error_description": f"Polling timed out after {max_attempts * interval}s",
    }


def cmd_set_copilot_auth_state(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    profile_state = None
    if args.state == "prepared":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider=_PROVIDER,
            credentials={
                "placeholder": True,
                "kind": "github-copilot-oauth-prepared",
                "oauth_state": "prepared",
                "real_oauth": False,
                "created_by": _CREATED_BY,
            },
        )
    elif args.state == "handshake-started":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider=_PROVIDER,
            credentials={
                "placeholder": True,
                "kind": "github-copilot-oauth-handshake-placeholder",
                "oauth_state": "handshake-started",
                "real_oauth": False,
                "created_by": _CREATED_BY,
            },
        )
    elif args.state == "handshake-stubbed":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider=_PROVIDER,
            credentials={
                "oauth_stub": True,
                "kind": "github-copilot-oauth-handshake-stub",
                "oauth_state": "handshake-stubbed",
                "oauth_stub_id": f"copilot-oauth-stub:{uuid4()}",
                "oauth_started_at": datetime.now(UTC).isoformat(),
                "browser_launched": False,
                "token_exchange_completed": False,
                "real_oauth": False,
                "created_by": _CREATED_BY,
            },
        )
    elif args.state == "launch-stubbed":
        stub_id = f"copilot-oauth-launch:{uuid4()}"
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider=_PROVIDER,
            credentials={
                "oauth_launch_stub": True,
                "kind": "github-copilot-oauth-launch-stub",
                "oauth_state": "launch-stubbed",
                "oauth_stub_id": stub_id,
                "oauth_started_at": datetime.now(UTC).isoformat(),
                "oauth_launch_mode": "browser-device-future",
                "oauth_launch_url": f"https://github.com/login/device?jarvis_oauth_stub={stub_id}",
                "oauth_launch_started_at": datetime.now(UTC).isoformat(),
                "browser_launched": False,
                "token_exchange_completed": False,
                "real_oauth": False,
                "created_by": _CREATED_BY,
            },
        )
    elif args.state == "stored":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider=_PROVIDER,
            credentials={
                "placeholder": True,
                "kind": "github-copilot-oauth-placeholder",
                "oauth_state": "placeholder-stored",
                "real_oauth": False,
                "created_by": _CREATED_BY,
            },
        )
    elif args.state == "revoked":
        profile_state = revoke_provider(
            profile=args.auth_profile,
            provider=_PROVIDER,
        )
    else:
        raise ValueError(
            "state must be one of: prepared, handshake-started, handshake-stubbed, launch-stubbed, stored, revoked"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_state": args.state,
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if profile_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_start_copilot_oauth_launch_intent(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    intent_id = f"copilot-oauth-intent:{uuid4()}"
    launch_started_at = datetime.now(UTC).isoformat()
    profile_state = save_provider_credentials(
        profile=args.auth_profile,
        provider=_PROVIDER,
        credentials={
            "oauth_launch_intent": True,
            "kind": "github-copilot-oauth-launch-intent",
            "oauth_state": "launch-intent-created",
            "oauth_intent_id": intent_id,
            "oauth_launch_mode": "browser-device-future",
            "oauth_launch_url": f"https://github.com/login/device?jarvis_oauth_intent={intent_id}",
            "oauth_launch_started_at": launch_started_at,
            "browser_launch_requested": True,
            "browser_launched": False,
            "token_exchange_completed": False,
            "real_oauth": False,
            "created_by": _CREATED_BY,
        },
    )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "start-oauth-launch-intent",
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if profile_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_launch_copilot_oauth_browser(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    credentials = _load_provider_credentials_for_action(
        profile=args.auth_profile,
        action="launch",
    )
    launch_url = str(credentials.get("oauth_launch_url") or "").strip()
    if not launch_url:
        raise ValueError("No oauth launch URL found; create a launch intent first")

    attempted_at = datetime.now(UTC).isoformat()
    launch_result = "failed"
    browser_launched = False
    try:
        browser_launched = bool(webbrowser.open(launch_url, new=2))
        launch_result = "opened" if browser_launched else "not-opened"
    except Exception:
        browser_launched = False
        launch_result = "failed"

    credentials.update(
        {
            "oauth_launch_intent": True,
            "kind": "github-copilot-oauth-browser-launch-stub",
            "oauth_state": "browser-launch-attempted",
            "browser_launch_requested": True,
            "browser_launch_attempted_at": attempted_at,
            "browser_launch_method": "python-webbrowser",
            "browser_launch_result": launch_result,
            "browser_launched": browser_launched,
            "real_oauth": False,
            "created_by": str(credentials.get("created_by") or _CREATED_BY),
        }
    )
    profile_state = save_provider_credentials(
        profile=args.auth_profile,
        provider=_PROVIDER,
        credentials=credentials,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "launch-oauth-browser",
                "launch_url": launch_url,
                "browser_launch_result": launch_result,
                "browser_launched": browser_launched,
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if profile_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_reset_copilot_oauth_launch(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    credentials = _load_provider_credentials_for_action(
        profile=args.auth_profile,
        action="reset",
    )
    launch_url = str(credentials.get("oauth_launch_url") or "").strip()
    if not launch_url:
        raise ValueError("No oauth launch URL found; create a launch intent first")

    reset_at = datetime.now(UTC).isoformat()
    credentials.update(
        {
            "oauth_launch_intent": True,
            "kind": "github-copilot-oauth-launch-intent",
            "oauth_state": "launch-intent-created",
            "oauth_launch_started_at": reset_at,
            "browser_launch_requested": True,
            "browser_launched": False,
            "real_oauth": False,
            "created_by": str(credentials.get("created_by") or _CREATED_BY),
        }
    )
    credentials.pop("browser_launch_attempted_at", None)
    credentials.pop("browser_launch_method", None)
    credentials.pop("browser_launch_result", None)

    profile_state = save_provider_credentials(
        profile=args.auth_profile,
        provider=_PROVIDER,
        credentials=credentials,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "reset-oauth-launch",
                "launch_url": launch_url,
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if profile_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_intake_copilot_oauth_callback(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()

    credentials = _load_provider_credentials_for_action(
        profile=args.auth_profile,
        action="callback intake",
    )

    callback_input = str(args.callback or "").strip()
    if not callback_input:
        raise ValueError("Callback URL/string is required")

    parsed = urllib_parse.urlsplit(callback_input)
    params = urllib_parse.parse_qs(parsed.query, keep_blank_values=True)
    callback_keys = sorted(params.keys())
    received_at = datetime.now(UTC).isoformat()

    credentials.update(
        {
            "oauth_callback_stub": True,
            "kind": "github-copilot-oauth-callback-stub",
            "oauth_state": "callback-received",
            "oauth_callback_received_at": received_at,
            "oauth_callback_url": callback_input,
            "oauth_callback_has_code": "code" in params,
            "oauth_callback_has_state": "state" in params,
            "oauth_callback_param_keys": callback_keys,
            "token_exchange_completed": False,
            "real_oauth": False,
            "created_by": str(credentials.get("created_by") or _CREATED_BY),
        }
    )

    profile_state = save_provider_credentials(
        profile=args.auth_profile,
        provider=_PROVIDER,
        credentials=credentials,
    )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "intake-oauth-callback",
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider=_PROVIDER,
                    )
                    if profile_state
                    else None
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _load_provider_credentials_for_action(
    *, profile: str, action: str
) -> dict[str, object]:
    provider_state = get_provider_state(
        profile=profile,
        provider=_PROVIDER,
    )
    if provider_state is None:
        raise ValueError(f"No github-copilot auth profile state found for {action}")

    credentials_path = Path(str(provider_state.get("credentials_path") or ""))
    if not credentials_path.exists():
        raise ValueError(f"No github-copilot credentials found for {action}")

    return json.loads(credentials_path.read_text(encoding="utf-8"))
