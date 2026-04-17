#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.services.visible_model import visible_execution_readiness
from core.services.non_visible_lane_execution import (
    cheap_lane_execution_truth,
    coding_lane_execution_truth,
    local_lane_execution_truth,
)
from core.services.visible_runs import (
    cancel_visible_run,
    get_active_visible_run,
    get_last_visible_capability_use,
    get_last_visible_run_outcome,
)
from core.costing.ledger import telemetry_summary
from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.cli.capability_commands import (
    cmd_approve_capability_request,
    cmd_execute_capability_request,
    cmd_invoke_capability,
)
from core.cli.copilot_auth import (
    cmd_configure_copilot_client_id,
    cmd_copilot_auth_status,
    cmd_intake_copilot_oauth_callback,
    cmd_launch_copilot_oauth_browser,
    cmd_poll_copilot_token_exchange,
    cmd_reset_copilot_oauth_launch,
    cmd_set_copilot_auth_state,
    cmd_start_copilot_device_flow,
    cmd_start_copilot_oauth_launch_intent,
)
from core.cli.openai_auth import (
    cmd_await_openai_oauth_callback,
    cmd_configure_openai_oauth_client,
    cmd_exchange_openai_oauth_code,
    cmd_import_openai_codex_session,
    cmd_intake_openai_oauth_callback,
    cmd_launch_openai_oauth_browser,
    cmd_openai_auth_status,
    cmd_print_openai_callback_url,
    cmd_refresh_openai_oauth_token,
    cmd_reset_openai_oauth_launch,
    cmd_revoke_openai_oauth,
    cmd_start_openai_oauth_launch_intent,
)
from core.cli.provider_config import (
    cmd_cheap_lane_status,
    cmd_cheap_lane_smoke,
    cmd_configure_cheap_provider,
    cmd_configure_coding_lane,
    cmd_configure_copilot_coding_lane,
    cmd_configure_codex_cli_coding_lane,
    cmd_configure_local_lane,
    cmd_configure_openai_oauth_coding_lane,
    cmd_configure_provider,
    cmd_list_cheap_providers,
    cmd_list_provider_models,
    cmd_select_main_agent,
    cmd_test_provider,
)
from core.cli.http_fallback import (
    cancel_visible_run_via_api,
    fetch_visible_run_via_api,
    request_json,
)
from core.cli.visible_output import (
    capability_invocation_section,
    visible_execution_section,
    visible_run_section,
)
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.config import SETTINGS_FILE
from core.runtime.db import (
    connect,
    init_db,
)
from core.runtime.provider_router import provider_router_summary
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import (
    get_capability_invocation_truth,
    load_workspace_capabilities,
)


def cmd_bootstrap(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    workspace = ensure_default_workspace()
    event_bus.publish("runtime.bootstrap", {"workspace": str(workspace)})
    print(f"Bootstrapped workspace: {workspace}")


def cmd_events(args: argparse.Namespace) -> None:
    items = event_bus.recent(limit=args.limit)
    print(json.dumps(items, indent=2, ensure_ascii=False))


def cmd_health(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    settings = load_settings()
    print(
        json.dumps(
            {
                "ok": True,
                "app": settings.app_name,
                "environment": settings.environment,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_overview(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    costs = telemetry_summary()
    items = event_bus.recent(limit=1)
    visible_run, visible_run_source, api_unavailable = _visible_run_truth()
    visible_execution, visible_execution_source, visible_execution_api_unavailable = (
        _visible_execution_truth()
    )
    print(
        json.dumps(
            {
                "ok": True,
                "visible_execution": visible_execution_section(
                    visible_execution,
                    visible_execution_source,
                    visible_execution_api_unavailable,
                ),
                "visible_run": visible_run_section(
                    visible_run,
                    visible_run_source,
                    api_unavailable,
                ),
                "events": _event_count(),
                "cost_rows": costs["cost_rows"],
                "input_tokens": costs["input_tokens"],
                "output_tokens": costs["output_tokens"],
                "total_cost_usd": costs["total_cost_usd"],
                "latest_event": items[0] if items else None,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_config(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    settings = load_settings()
    visible_execution, visible_execution_source, visible_execution_api_unavailable = (
        _visible_execution_truth()
    )
    (
        capability_invocation,
        capability_invocation_source,
        capability_invocation_api_unavailable,
    ) = _capability_invocation_truth()
    print(
        json.dumps(
            {
                "visible_execution": visible_execution_section(
                    visible_execution,
                    visible_execution_source,
                    visible_execution_api_unavailable,
                ),
                "workspace_capabilities": load_workspace_capabilities(),
                "capability_invocation": capability_invocation_section(
                    capability_invocation,
                    capability_invocation_source,
                    capability_invocation_api_unavailable,
                ),
                "provider_router": provider_router_summary(),
                "path": str(SETTINGS_FILE),
                "settings": settings.to_dict(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_coding_lane_status(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            coding_lane_execution_truth(),
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_local_lane_status(_: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    print(
        json.dumps(
            local_lane_execution_truth(),
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_workspace(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    workspace = ensure_default_workspace(name=args.name)
    files = sorted(path.name for path in workspace.iterdir() if path.is_file())
    print(
        json.dumps(
            {
                "workspace": str(workspace),
                "exists": workspace.exists(),
                "files": files,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_cancel_visible_run(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    requested_run_id = (args.run_id or "").strip()
    run_id = requested_run_id
    api_unavailable = None

    if not run_id:
        visible_run, visible_run_source, api_unavailable = _visible_run_truth()
        active_run = visible_run.get("active_run")
        if not active_run:
            print(
                json.dumps(
                    {
                        "ok": False,
                        "status": "not-found",
                        "detail": "No active visible run",
                        "source": visible_run_source,
                        "api_unavailable": api_unavailable,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return
        run_id = str(active_run["run_id"])

    api_cancelled, api_error = cancel_visible_run_via_api(run_id)
    if api_cancelled:
        print(
            json.dumps(
                {
                    "ok": True,
                    "run_id": run_id,
                    "status": "cancelled",
                    "source": "api",
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if api_error != "not-found":
        api_unavailable = api_error

    if not cancel_visible_run(run_id):
        print(
            json.dumps(
                {
                    "ok": False,
                    "run_id": run_id,
                    "status": "not-found",
                    "detail": "Visible run not active",
                    "source": "api" if api_error == "not-found" else "local-fallback",
                    "api_unavailable": api_unavailable,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    print(
        json.dumps(
            {
                "ok": True,
                "run_id": run_id,
                "status": "cancelled",
                "source": "local-fallback",
                "api_unavailable": api_unavailable,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_discord_setup(_: argparse.Namespace) -> None:
    """Interactive wizard to configure the Discord gateway."""
    ensure_runtime_dirs()
    init_db()

    from core.services.discord_config import (
        load_discord_config,
        save_discord_config,
    )

    print("Discord Gateway Setup")
    print("=" * 40)

    existing = load_discord_config()
    if existing:
        print("Existing config found. Values in [brackets] are current — press Enter to keep.")
    print()

    def _prompt(label: str, current: str = "", secret: bool = False) -> str:
        suffix = f" [{current}]" if current and not secret else (" [set]" if current and secret else "")
        val = input(f"{label}{suffix}: ").strip()
        return val if val else current

    current_token = (existing or {}).get("bot_token", "")
    bot_token = _prompt("Bot token", current_token, secret=True)
    if not bot_token:
        print("Error: bot token is required.")
        sys.exit(1)

    import urllib.request
    import urllib.error
    try:
        req = urllib.request.Request(
            "https://discord.com/api/v10/users/@me",
            headers={
                "Authorization": f"Bot {bot_token}",
                "User-Agent": "DiscordBot (https://github.com/Rapptz/discord.py, 2.6.4)",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            bot_info = json.loads(resp.read())
        print(f"Token valid — bot username: {bot_info.get('username', '?')}#{bot_info.get('discriminator', '0')}")
    except urllib.error.HTTPError as exc:
        print(f"Token validation failed: HTTP {exc.code}. Check your bot token.")
        sys.exit(1)
    except Exception as exc:
        print(f"Token validation failed: {exc}")
        sys.exit(1)

    current_guild = (existing or {}).get("guild_id", "")
    guild_id = _prompt("Guild ID", current_guild)
    if not guild_id:
        print("Error: guild ID is required.")
        sys.exit(1)

    current_channels = ",".join((existing or {}).get("allowed_channel_ids", []))
    channels_input = _prompt("Allowed channel IDs (comma-separated)", current_channels)
    allowed_channel_ids = [c.strip() for c in channels_input.split(",") if c.strip()]
    if not allowed_channel_ids:
        print("Error: at least one channel ID is required.")
        sys.exit(1)

    current_owner = (existing or {}).get("owner_discord_id", "")
    owner_discord_id = _prompt("Owner Discord user ID", current_owner)
    if not owner_discord_id:
        print("Error: owner Discord user ID is required.")
        sys.exit(1)

    config = {
        "bot_token": bot_token,
        "guild_id": guild_id,
        "allowed_channel_ids": allowed_channel_ids,
        "owner_discord_id": owner_discord_id,
        "enabled": True,
    }
    save_discord_config(config)
    print()
    print("Config saved to ~/.jarvis-v2/config/discord.json (chmod 600)")
    print("Restart the API to activate: uvicorn apps.api.jarvis_api.app:app --reload")


def cmd_discord_status(_: argparse.Namespace) -> None:
    """Show Discord gateway config and connection status."""
    ensure_runtime_dirs()
    from core.services.discord_config import is_discord_configured, load_discord_config

    if not is_discord_configured():
        print("Discord is not configured. Run: python scripts/jarvis.py discord-setup")
        return

    cfg = load_discord_config()
    print(json.dumps({
        "configured": True,
        "guild_id": cfg.get("guild_id"),
        "allowed_channel_ids": cfg.get("allowed_channel_ids"),
        "owner_discord_id": cfg.get("owner_discord_id"),
        "enabled": cfg.get("enabled", True),
        "bot_token": "[set]",
    }, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jarvis")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap")
    bootstrap.set_defaults(func=cmd_bootstrap)

    events = sub.add_parser("events")
    events.add_argument("--limit", type=int, default=20)
    events.set_defaults(func=cmd_events)

    health = sub.add_parser("health")
    health.set_defaults(func=cmd_health)

    overview = sub.add_parser("overview")
    overview.set_defaults(func=cmd_overview)

    config = sub.add_parser("config")
    config.set_defaults(func=cmd_config)

    configure_provider = sub.add_parser("configure-provider")
    configure_provider.add_argument("--provider", required=True)
    configure_provider.add_argument("--model", required=True)
    configure_provider.add_argument("--auth-mode", default="none")
    configure_provider.add_argument("--auth-profile", default="")
    configure_provider.add_argument("--base-url", default="")
    configure_provider.add_argument("--api-key", default="")
    configure_provider.add_argument("--lane", default="visible")
    configure_provider.add_argument("--set-visible", action="store_true")
    configure_provider.set_defaults(func=cmd_configure_provider)

    configure_coding_lane = sub.add_parser("configure-coding-lane")
    configure_coding_lane.add_argument("--model", required=True)
    configure_coding_lane.add_argument("--auth-profile", default="codex")
    configure_coding_lane.add_argument("--api-key", default="")
    configure_coding_lane.add_argument(
        "--base-url", default="https://api.openai.com/v1"
    )
    configure_coding_lane.set_defaults(func=cmd_configure_coding_lane)

    configure_copilot_coding_lane = sub.add_parser("configure-copilot-coding-lane")
    configure_copilot_coding_lane.add_argument("--model", required=True)
    configure_copilot_coding_lane.add_argument("--auth-profile", default="copilot")
    configure_copilot_coding_lane.set_defaults(func=cmd_configure_copilot_coding_lane)

    configure_openai_oauth_coding_lane = sub.add_parser("configure-openai-oauth-coding-lane")
    configure_openai_oauth_coding_lane.add_argument("--model", required=True)
    configure_openai_oauth_coding_lane.add_argument("--auth-profile", default="codex")
    configure_openai_oauth_coding_lane.add_argument("--base-url", default="https://api.openai.com/v1")
    configure_openai_oauth_coding_lane.set_defaults(func=cmd_configure_openai_oauth_coding_lane)

    configure_codex_cli_coding_lane = sub.add_parser("configure-codex-cli-coding-lane")
    configure_codex_cli_coding_lane.add_argument("--model", default="gpt-5.4")
    configure_codex_cli_coding_lane.set_defaults(func=cmd_configure_codex_cli_coding_lane)

    configure_local_lane = sub.add_parser("configure-local-lane")
    configure_local_lane.add_argument("--model", default="qwen3.5:9b")
    configure_local_lane.add_argument("--base-url", default="http://127.0.0.1:11434")
    configure_local_lane.set_defaults(func=cmd_configure_local_lane)

    configure_cheap_provider = sub.add_parser("configure-cheap-provider")
    configure_cheap_provider.add_argument("--provider", required=True)
    configure_cheap_provider.add_argument("--model", required=True)
    configure_cheap_provider.add_argument("--auth-profile", default="")
    configure_cheap_provider.add_argument("--api-key", default="")
    configure_cheap_provider.add_argument("--base-url", default="")
    configure_cheap_provider.add_argument("--account-id", default="")
    configure_cheap_provider.set_defaults(func=cmd_configure_cheap_provider)

    list_provider_models = sub.add_parser("list-provider-models")
    list_provider_models.add_argument("--provider", required=True)
    list_provider_models.add_argument("--auth-profile", default="")
    list_provider_models.add_argument("--base-url", default="")
    list_provider_models.set_defaults(func=cmd_list_provider_models)

    test_provider = sub.add_parser("test-provider")
    test_provider.add_argument("--provider", required=True)
    test_provider.add_argument("--model", required=True)
    test_provider.add_argument("--auth-profile", required=True)
    test_provider.add_argument("--base-url", default="")
    test_provider.add_argument("--message", default="Return exactly: cheap-lane-ok")
    test_provider.set_defaults(func=cmd_test_provider)

    cheap_providers = sub.add_parser("list-cheap-providers")
    cheap_providers.set_defaults(func=cmd_list_cheap_providers)

    select_main_agent = sub.add_parser("select-main-agent")
    select_main_agent.add_argument("--provider", required=True)
    select_main_agent.add_argument("--model", required=True)
    select_main_agent.add_argument("--auth-profile", default="")
    select_main_agent.set_defaults(func=cmd_select_main_agent)

    copilot_auth_status = sub.add_parser("copilot-auth-status")
    copilot_auth_status.add_argument("--auth-profile", default="copilot")
    copilot_auth_status.set_defaults(func=cmd_copilot_auth_status)

    set_copilot_auth_state = sub.add_parser("set-copilot-auth-state")
    set_copilot_auth_state.add_argument("--auth-profile", default="copilot")
    set_copilot_auth_state.add_argument(
        "--state",
        required=True,
        choices=(
            "prepared",
            "handshake-started",
            "handshake-stubbed",
            "launch-stubbed",
            "stored",
            "revoked",
        ),
    )
    set_copilot_auth_state.set_defaults(func=cmd_set_copilot_auth_state)

    start_copilot_oauth_launch_intent = sub.add_parser(
        "start-copilot-oauth-launch-intent"
    )
    start_copilot_oauth_launch_intent.add_argument("--auth-profile", default="copilot")
    start_copilot_oauth_launch_intent.set_defaults(
        func=cmd_start_copilot_oauth_launch_intent
    )

    launch_copilot_oauth_browser = sub.add_parser("launch-copilot-oauth-browser")
    launch_copilot_oauth_browser.add_argument("--auth-profile", default="copilot")
    launch_copilot_oauth_browser.set_defaults(func=cmd_launch_copilot_oauth_browser)

    reset_copilot_oauth_launch = sub.add_parser("reset-copilot-oauth-launch")
    reset_copilot_oauth_launch.add_argument("--auth-profile", default="copilot")
    reset_copilot_oauth_launch.set_defaults(func=cmd_reset_copilot_oauth_launch)

    intake_copilot_oauth_callback = sub.add_parser("intake-copilot-oauth-callback")
    intake_copilot_oauth_callback.add_argument("--auth-profile", default="copilot")
    intake_copilot_oauth_callback.add_argument("--callback", required=True)
    intake_copilot_oauth_callback.set_defaults(func=cmd_intake_copilot_oauth_callback)

    configure_copilot_client_id = sub.add_parser("configure-copilot-client-id")
    configure_copilot_client_id.add_argument("--client-id", required=True)
    configure_copilot_client_id.set_defaults(func=cmd_configure_copilot_client_id)

    configure_openai_oauth_client = sub.add_parser("configure-openai-oauth-client")
    configure_openai_oauth_client.add_argument("--client-id", required=True)
    configure_openai_oauth_client.add_argument("--authorize-url", default="")
    configure_openai_oauth_client.add_argument("--token-url", default="")
    configure_openai_oauth_client.add_argument("--scopes", default="")
    configure_openai_oauth_client.add_argument("--audience", default="")
    configure_openai_oauth_client.add_argument("--redirect-base-url", default="")
    configure_openai_oauth_client.add_argument("--callback-path", default="")
    configure_openai_oauth_client.set_defaults(func=cmd_configure_openai_oauth_client)

    openai_auth_status = sub.add_parser("openai-auth-status")
    openai_auth_status.add_argument("--auth-profile", default="codex")
    openai_auth_status.set_defaults(func=cmd_openai_auth_status)

    import_openai_codex_session = sub.add_parser("import-openai-codex-session")
    import_openai_codex_session.add_argument("--auth-profile", default="codex")
    import_openai_codex_session.set_defaults(func=cmd_import_openai_codex_session)

    start_openai_oauth_launch_intent = sub.add_parser("start-openai-oauth-launch-intent")
    start_openai_oauth_launch_intent.add_argument("--auth-profile", default="codex")
    start_openai_oauth_launch_intent.set_defaults(func=cmd_start_openai_oauth_launch_intent)

    launch_openai_oauth_browser = sub.add_parser("launch-openai-oauth-browser")
    launch_openai_oauth_browser.add_argument("--auth-profile", default="codex")
    launch_openai_oauth_browser.set_defaults(func=cmd_launch_openai_oauth_browser)

    await_openai_oauth_callback = sub.add_parser("await-openai-oauth-callback")
    await_openai_oauth_callback.add_argument("--auth-profile", default="codex")
    await_openai_oauth_callback.add_argument("--timeout-seconds", type=int, default=180)
    await_openai_oauth_callback.set_defaults(func=cmd_await_openai_oauth_callback)

    reset_openai_oauth_launch = sub.add_parser("reset-openai-oauth-launch")
    reset_openai_oauth_launch.add_argument("--auth-profile", default="codex")
    reset_openai_oauth_launch.set_defaults(func=cmd_reset_openai_oauth_launch)

    intake_openai_oauth_callback = sub.add_parser("intake-openai-oauth-callback")
    intake_openai_oauth_callback.add_argument("--auth-profile", default="codex")
    intake_openai_oauth_callback.add_argument("--callback", required=True)
    intake_openai_oauth_callback.set_defaults(func=cmd_intake_openai_oauth_callback)

    exchange_openai_oauth_code = sub.add_parser("exchange-openai-oauth-code")
    exchange_openai_oauth_code.add_argument("--auth-profile", default="codex")
    exchange_openai_oauth_code.set_defaults(func=cmd_exchange_openai_oauth_code)

    refresh_openai_oauth_token = sub.add_parser("refresh-openai-oauth-token")
    refresh_openai_oauth_token.add_argument("--auth-profile", default="codex")
    refresh_openai_oauth_token.set_defaults(func=cmd_refresh_openai_oauth_token)

    revoke_openai_oauth = sub.add_parser("revoke-openai-oauth")
    revoke_openai_oauth.add_argument("--auth-profile", default="codex")
    revoke_openai_oauth.set_defaults(func=cmd_revoke_openai_oauth)

    print_openai_callback_url = sub.add_parser("print-openai-callback-url")
    print_openai_callback_url.add_argument("--auth-profile", default="codex")
    print_openai_callback_url.set_defaults(func=cmd_print_openai_callback_url)

    start_copilot_device_flow = sub.add_parser("start-copilot-device-flow")
    start_copilot_device_flow.add_argument("--auth-profile", default="copilot")
    start_copilot_device_flow.set_defaults(func=cmd_start_copilot_device_flow)

    poll_copilot_token_exchange = sub.add_parser("poll-copilot-token-exchange")
    poll_copilot_token_exchange.add_argument("--auth-profile", default="copilot")
    poll_copilot_token_exchange.set_defaults(func=cmd_poll_copilot_token_exchange)

    coding_lane_status = sub.add_parser("coding-lane-status")
    coding_lane_status.set_defaults(func=cmd_coding_lane_status)

    local_lane_status = sub.add_parser("local-lane-status")
    local_lane_status.set_defaults(func=cmd_local_lane_status)

    cheap_lane_status = sub.add_parser("cheap-lane-status")
    cheap_lane_status.set_defaults(func=cmd_cheap_lane_status)

    cheap_lane_smoke = sub.add_parser("cheap-lane-smoke")
    cheap_lane_smoke.add_argument("--message", default="Return exactly: cheap-lane-ok")
    cheap_lane_smoke.set_defaults(func=cmd_cheap_lane_smoke)

    workspace = sub.add_parser("workspace")
    workspace.add_argument("--name", default="default")
    workspace.set_defaults(func=cmd_workspace)

    cancel_visible = sub.add_parser("cancel-visible-run")
    cancel_visible.add_argument("--run-id", default="")
    cancel_visible.set_defaults(func=cmd_cancel_visible_run)

    invoke_capability = sub.add_parser("invoke-capability")
    invoke_capability.add_argument("capability_id")
    invoke_capability.add_argument("--approve", action="store_true")
    invoke_capability.set_defaults(func=cmd_invoke_capability)

    approve_capability_request = sub.add_parser("approve-capability-request")
    approve_capability_request.add_argument("request_id")
    approve_capability_request.set_defaults(func=cmd_approve_capability_request)

    execute_capability_request = sub.add_parser("execute-capability-request")
    execute_capability_request.add_argument("request_id")
    execute_capability_request.set_defaults(func=cmd_execute_capability_request)

    discord_setup = sub.add_parser("discord-setup", help="Configure the Discord gateway interactively")
    discord_setup.set_defaults(func=cmd_discord_setup)

    discord_status = sub.add_parser("discord-status", help="Show Discord gateway config and status")
    discord_status.set_defaults(func=cmd_discord_status)

    return parser


def _event_count() -> int:
    with connect() as conn:
        return int(conn.execute("SELECT COUNT(*) AS n FROM events").fetchone()["n"])


def _visible_run_truth() -> tuple[dict, str, str | None]:
    api_payload, api_error = fetch_visible_run_via_api()
    if api_payload is not None:
        return api_payload, "api", None
    return (
        {
            "active": bool(get_active_visible_run()),
            "active_run": get_active_visible_run(),
            "last_outcome": get_last_visible_run_outcome(),
            "last_capability_use": get_last_visible_capability_use(),
            "persisted_recent_runs": [],
            "recent_events": [],
        },
        "local-fallback",
        api_error,
    )


def _visible_execution_truth() -> tuple[dict, str, str | None]:
    response, api_error = request_json("GET", "/mc/visible-execution")
    if response is not None:
        return (
            {
                "authority": response.get("authority"),
                "readiness": response.get("readiness"),
                "visible_identity": response.get("visible_identity"),
                "visible_work": response.get("visible_work"),
                "visible_work_surface": response.get("visible_work_surface"),
                "visible_selected_work_surface": response.get(
                    "visible_selected_work_surface"
                ),
                "visible_selected_work_item": response.get(
                    "visible_selected_work_item"
                ),
                "visible_session_continuity": response.get(
                    "visible_session_continuity"
                ),
                "visible_continuity": response.get("visible_continuity"),
                "visible_capability_continuity": response.get(
                    "visible_capability_continuity"
                ),
            },
            "api",
            None,
        )
    return (
        {
            "authority": {
                "visible_model_provider": load_settings().visible_model_provider,
                "visible_model_name": load_settings().visible_model_name,
                "visible_auth_profile": load_settings().visible_auth_profile,
            },
            "readiness": visible_execution_readiness(),
            "visible_identity": {},
            "visible_work": {},
            "visible_work_surface": {},
            "visible_selected_work_surface": {},
            "visible_selected_work_item": {},
            "visible_session_continuity": {},
            "visible_continuity": {},
            "visible_capability_continuity": {},
        },
        "local-fallback",
        api_error,
    )


def _capability_invocation_truth() -> tuple[dict, str, str | None]:
    response, api_error = request_json("GET", "/mc/visible-execution")
    if response is not None:
        return response.get("capability_invocation") or {}, "api", None
    return (
        {
            **get_capability_invocation_truth(),
            "persisted_recent_invocations": [],
            "recent_approval_requests": [],
        },
        "local-fallback",
        api_error,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
