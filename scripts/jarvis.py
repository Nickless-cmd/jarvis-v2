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

from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
from apps.api.jarvis_api.services.non_visible_lane_execution import (
    coding_lane_execution_truth,
    local_lane_execution_truth,
)
from apps.api.jarvis_api.services.visible_runs import (
    cancel_visible_run,
    get_active_visible_run,
    get_last_visible_capability_use,
    get_last_visible_run_outcome,
)
from core.costing.ledger import telemetry_summary
from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.cli.copilot_auth import (
    cmd_copilot_auth_status,
    cmd_intake_copilot_oauth_callback,
    cmd_launch_copilot_oauth_browser,
    cmd_reset_copilot_oauth_launch,
    cmd_set_copilot_auth_state,
    cmd_start_copilot_oauth_launch_intent,
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
    approve_capability_approval_request,
    connect,
    get_capability_approval_request,
    init_db,
)
from core.runtime.provider_router import (
    configure_provider_router_entry,
    provider_router_summary,
    select_main_agent_target,
)
from core.runtime.settings import load_settings
from core.tools.workspace_capabilities import (
    get_capability_invocation_truth,
    invoke_workspace_capability,
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
    capability_invocation, capability_invocation_source, capability_invocation_api_unavailable = (
        _capability_invocation_truth()
    )
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


def cmd_configure_provider(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider=args.provider,
        model=args.model,
        auth_mode=args.auth_mode,
        auth_profile=args.auth_profile,
        base_url=args.base_url,
        api_key=args.api_key,
        lane=args.lane,
        set_visible=args.set_visible,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_coding_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="openai",
        model=args.model,
        auth_mode="api-key",
        auth_profile=args.auth_profile,
        base_url=args.base_url,
        api_key=args.api_key,
        lane="coding",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "coding_lane": {
                    "provider": "openai",
                    "lane": "coding",
                    "auth_mode": "api-key",
                    "auth_profile": args.auth_profile,
                },
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_copilot_coding_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="github-copilot",
        model=args.model,
        auth_mode="oauth",
        auth_profile=args.auth_profile,
        base_url="",
        api_key="",
        lane="coding",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "coding_lane": {
                    "provider": "github-copilot",
                    "lane": "coding",
                    "auth_mode": "oauth",
                    "auth_profile": args.auth_profile,
                },
                "provider_router": provider_router_summary(),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_configure_local_lane(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = configure_provider_router_entry(
        provider="ollama",
        model=args.model,
        auth_mode="none",
        auth_profile="",
        base_url=args.base_url,
        api_key="",
        lane="local",
        set_visible=False,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "configured": result,
                "local_lane": {
                    "provider": "ollama",
                    "lane": "local",
                    "auth_mode": "none",
                    "base_url": args.base_url,
                    "model": args.model,
                },
                "local_lane_execution": local_lane_execution_truth(),
                "provider_router": provider_router_summary(),
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


def cmd_select_main_agent(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    result = select_main_agent_target(
        provider=args.provider,
        model=args.model,
        auth_profile=args.auth_profile,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "selected": result,
                "provider_router": provider_router_summary(),
            },
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


def cmd_invoke_capability(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    capability_id = args.capability_id.strip()
    result, source, api_unavailable = _invoke_capability_truth(
        capability_id, approved=bool(args.approve)
    )
    print(
        json.dumps(
            {
                "ok": result["status"] == "executed",
                "source": source,
                "api_unavailable": api_unavailable,
                **result,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_approve_capability_request(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    request_id = args.request_id.strip()
    result, source, api_unavailable = _approve_capability_request_truth(request_id)
    print(
        json.dumps(
            {
                "ok": bool(result),
                "source": source,
                "api_unavailable": api_unavailable,
                "request": result,
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def cmd_execute_capability_request(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    request_id = args.request_id.strip()
    result, source, api_unavailable = _execute_capability_request_truth(request_id)
    print(
        json.dumps(
            {
                "ok": bool(result.get("ok")) if result else False,
                "source": source,
                "api_unavailable": api_unavailable,
                **(result or {}),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


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
    configure_coding_lane.add_argument("--base-url", default="https://api.openai.com/v1")
    configure_coding_lane.set_defaults(func=cmd_configure_coding_lane)

    configure_copilot_coding_lane = sub.add_parser("configure-copilot-coding-lane")
    configure_copilot_coding_lane.add_argument("--model", required=True)
    configure_copilot_coding_lane.add_argument("--auth-profile", default="copilot")
    configure_copilot_coding_lane.set_defaults(func=cmd_configure_copilot_coding_lane)

    configure_local_lane = sub.add_parser("configure-local-lane")
    configure_local_lane.add_argument("--model", default="qwen3.5:9b")
    configure_local_lane.add_argument("--base-url", default="http://127.0.0.1:11434")
    configure_local_lane.set_defaults(func=cmd_configure_local_lane)

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

    start_copilot_oauth_launch_intent = sub.add_parser("start-copilot-oauth-launch-intent")
    start_copilot_oauth_launch_intent.add_argument("--auth-profile", default="copilot")
    start_copilot_oauth_launch_intent.set_defaults(func=cmd_start_copilot_oauth_launch_intent)

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

    coding_lane_status = sub.add_parser("coding-lane-status")
    coding_lane_status.set_defaults(func=cmd_coding_lane_status)

    local_lane_status = sub.add_parser("local-lane-status")
    local_lane_status.set_defaults(func=cmd_local_lane_status)

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
        return {
            "authority": response.get("authority"),
            "readiness": response.get("readiness"),
            "visible_identity": response.get("visible_identity"),
            "visible_work": response.get("visible_work"),
            "visible_work_surface": response.get("visible_work_surface"),
            "visible_selected_work_surface": response.get("visible_selected_work_surface"),
            "visible_selected_work_item": response.get("visible_selected_work_item"),
            "visible_session_continuity": response.get("visible_session_continuity"),
            "visible_continuity": response.get("visible_continuity"),
            "visible_capability_continuity": response.get("visible_capability_continuity"),
        }, "api", None
    return {
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
    }, "local-fallback", api_error


def _capability_invocation_truth() -> tuple[dict, str, str | None]:
    response, api_error = request_json("GET", "/mc/visible-execution")
    if response is not None:
        return response.get("capability_invocation") or {}, "api", None
    return {
        **get_capability_invocation_truth(),
        "persisted_recent_invocations": [],
        "recent_approval_requests": [],
    }, "local-fallback", api_error


def _invoke_capability_truth(
    capability_id: str, *, approved: bool = False
) -> tuple[dict, str, str | None]:
    response, api_error = request_json(
        "POST",
        (
            f"/mc/workspace-capabilities/{capability_id}/invoke?approved=true"
            if approved
            else f"/mc/workspace-capabilities/{capability_id}/invoke"
        ),
    )
    if response is not None:
        return response, "api", None
    return (
        invoke_workspace_capability(capability_id, approved=approved),
        "local-fallback",
        api_error,
    )


def _approve_capability_request_truth(
    request_id: str,
) -> tuple[dict | None, str, str | None]:
    response, api_error = request_json(
        "POST", f"/mc/capability-approval-requests/{request_id}/approve"
    )
    if response is not None:
        return response.get("request"), "api", None
    return (
        approve_capability_approval_request(
            request_id,
            approved_at=datetime.now(UTC).isoformat(),
        ),
        "local-fallback",
        api_error,
    )


def _execute_capability_request_truth(
    request_id: str,
) -> tuple[dict, str, str | None]:
    response, api_error = request_json(
        "POST", f"/mc/capability-approval-requests/{request_id}/execute"
    )
    if response is not None:
        return response, "api", None

    request = get_capability_approval_request(request_id)
    if request is None:
        return (
            {
                "ok": False,
                "request_id": request_id,
                "status": "not-found",
                "detail": "Capability approval request not found",
                "request": None,
                "invocation": None,
            },
            "local-fallback",
            api_error,
        )
    if request.get("status") != "approved":
        return (
            {
                "ok": False,
                "request_id": request_id,
                "status": "not-approved",
                "detail": "Capability approval request must be approved before execution",
                "request": request,
                "invocation": None,
            },
            "local-fallback",
            api_error,
        )
    invocation = invoke_workspace_capability(
        str(request.get("capability_id") or ""),
        approved=True,
        run_id=str(request.get("run_id") or "") or None,
    )
    return (
        {
            "ok": invocation["status"] == "executed",
            "request_id": request_id,
            "status": invocation["status"],
            "request": request,
            "invocation": invocation,
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
