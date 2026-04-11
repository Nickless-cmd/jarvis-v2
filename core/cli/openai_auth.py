from __future__ import annotations

import argparse
import json
import webbrowser
from datetime import UTC, datetime
from urllib import parse as urllib_parse

from core.auth.openai_oauth import (
    build_openai_launch_intent,
    exchange_openai_callback_code,
    get_openai_callback_url,
    get_openai_oauth_truth,
    load_openai_oauth_config,
    refresh_openai_access_token,
    save_openai_callback,
    save_openai_oauth_config,
)
from core.auth.profiles import (
    get_provider_credentials,
    get_provider_state_view,
    revoke_provider,
    save_provider_credentials,
)
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import init_db

_PROVIDER = "openai"
_CREATED_BY = "jarvis-cli"


def cmd_openai_auth_status(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "oauth_truth": get_openai_oauth_truth(profile=args.auth_profile),
                "oauth_config": load_openai_oauth_config(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_openai_oauth_client(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    config = save_openai_oauth_config(
        client_id=str(args.client_id or "").strip(),
        authorize_url=str(args.authorize_url or "").strip(),
        token_url=str(args.token_url or "").strip(),
        scopes=str(args.scopes or "").strip(),
        audience=str(args.audience or "").strip(),
        redirect_base_url=str(args.redirect_base_url or "").strip(),
    )
    print(json.dumps({"ok": True, "provider": _PROVIDER, "oauth_config": config}, indent=2, ensure_ascii=False))


def cmd_start_openai_oauth_launch_intent(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    intent = build_openai_launch_intent(profile=args.auth_profile)
    credentials = get_provider_credentials(profile=args.auth_profile, provider=_PROVIDER) or {}
    credentials["created_by"] = _CREATED_BY
    save_provider_credentials(profile=args.auth_profile, provider=_PROVIDER, credentials=credentials)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "start-oauth-launch-intent",
                "launch": intent,
                "profile_state": get_provider_state_view(profile=args.auth_profile, provider=_PROVIDER),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_launch_openai_oauth_browser(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    credentials = get_provider_credentials(profile=args.auth_profile, provider=_PROVIDER) or {}
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
    save_provider_credentials(profile=args.auth_profile, provider=_PROVIDER, credentials=credentials)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "launch_url": launch_url,
                "browser_launch_result": launch_result,
                "browser_launched": browser_launched,
                "profile_state": get_provider_state_view(profile=args.auth_profile, provider=_PROVIDER),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_reset_openai_oauth_launch(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    intent = build_openai_launch_intent(profile=args.auth_profile)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "reset-oauth-launch",
                "launch": intent,
                "profile_state": get_provider_state_view(profile=args.auth_profile, provider=_PROVIDER),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_intake_openai_oauth_callback(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    callback = str(args.callback or "").strip()
    if not callback:
        raise ValueError("Callback URL/string is required")
    stored = save_openai_callback(profile=args.auth_profile, callback_url=callback)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "intake-oauth-callback",
                "callback_keys": list(stored.get("oauth_callback_param_keys") or []),
                "profile_state": get_provider_state_view(profile=args.auth_profile, provider=_PROVIDER),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_exchange_openai_oauth_code(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    credentials = exchange_openai_callback_code(profile=args.auth_profile)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "exchange-oauth-code",
                "has_access_token": bool(str(credentials.get("access_token") or "").strip()),
                "has_refresh_token": bool(str(credentials.get("refresh_token") or "").strip()),
                "expires_at": str(credentials.get("expires_at") or ""),
                "profile_state": get_provider_state_view(profile=args.auth_profile, provider=_PROVIDER),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_refresh_openai_oauth_token(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    credentials = refresh_openai_access_token(profile=args.auth_profile)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "refresh-oauth-token",
                "expires_at": str(credentials.get("expires_at") or ""),
                "profile_state": get_provider_state_view(profile=args.auth_profile, provider=_PROVIDER),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_revoke_openai_oauth(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    profile_state = revoke_provider(profile=args.auth_profile, provider=_PROVIDER)
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "requested_action": "revoke-oauth",
                "profile_state": profile_state,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_print_openai_callback_url(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            {
                "ok": True,
                "provider": _PROVIDER,
                "auth_profile": args.auth_profile,
                "callback_url": get_openai_callback_url(profile=args.auth_profile),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
