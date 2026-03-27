from __future__ import annotations

import argparse
import json
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from urllib import parse as urllib_parse
from uuid import uuid4

from apps.api.jarvis_api.services.non_visible_lane_execution import (
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
