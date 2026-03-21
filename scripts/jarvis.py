#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from uuid import uuid4
from urllib import error as urllib_error
from urllib import request as urllib_request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
from apps.api.jarvis_api.services.non_visible_lane_execution import (
    coding_lane_execution_truth,
)
from core.auth.profiles import (
    get_provider_auth_material_kind,
    get_provider_oauth_state,
    get_provider_state,
    get_provider_state_view,
    revoke_provider,
    save_provider_credentials,
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
                "visible_execution": _visible_execution_section(
                    visible_execution,
                    visible_execution_source,
                    visible_execution_api_unavailable,
                ),
                "visible_run": _visible_run_section(
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
                "visible_execution": _visible_execution_section(
                    visible_execution,
                    visible_execution_source,
                    visible_execution_api_unavailable,
                ),
                "workspace_capabilities": load_workspace_capabilities(),
                "capability_invocation": _capability_invocation_section(
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


def cmd_copilot_auth_status(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    init_db()
    coding_lane = coding_lane_execution_truth()
    auth_material_kind = get_provider_auth_material_kind(
        profile=args.auth_profile,
        provider="github-copilot",
    )
    oauth_state = get_provider_oauth_state(
        profile=args.auth_profile,
        provider="github-copilot",
    )
    provider_state = get_provider_state(
        profile=args.auth_profile,
        provider="github-copilot",
    )
    provider_state_view = get_provider_state_view(
        profile=args.auth_profile,
        provider="github-copilot",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "provider": "github-copilot",
                "auth_profile": args.auth_profile,
                "auth_material_kind": auth_material_kind,
                "oauth_state": oauth_state,
                "coding_lane": coding_lane,
                "profile_state": provider_state_view if provider_state else None,
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
            provider="github-copilot",
            credentials={
                "placeholder": True,
                "kind": "github-copilot-oauth-prepared",
                "oauth_state": "prepared",
                "real_oauth": False,
                "created_by": "jarvis-cli",
            },
        )
    elif args.state == "handshake-started":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider="github-copilot",
            credentials={
                "placeholder": True,
                "kind": "github-copilot-oauth-handshake-placeholder",
                "oauth_state": "handshake-started",
                "real_oauth": False,
                "created_by": "jarvis-cli",
            },
        )
    elif args.state == "handshake-stubbed":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider="github-copilot",
            credentials={
                "oauth_stub": True,
                "kind": "github-copilot-oauth-handshake-stub",
                "oauth_state": "handshake-stubbed",
                "oauth_stub_id": f"copilot-oauth-stub:{uuid4()}",
                "oauth_started_at": datetime.now(UTC).isoformat(),
                "browser_launched": False,
                "token_exchange_completed": False,
                "real_oauth": False,
                "created_by": "jarvis-cli",
            },
        )
    elif args.state == "stored":
        profile_state = save_provider_credentials(
            profile=args.auth_profile,
            provider="github-copilot",
            credentials={
                "placeholder": True,
                "kind": "github-copilot-oauth-placeholder",
                "oauth_state": "placeholder-stored",
                "real_oauth": False,
                "created_by": "jarvis-cli",
            },
        )
    elif args.state == "revoked":
        profile_state = revoke_provider(
            profile=args.auth_profile,
            provider="github-copilot",
        )
    else:
        raise ValueError(
            "state must be one of: prepared, handshake-started, handshake-stubbed, stored, revoked"
        )

    print(
        json.dumps(
            {
                "ok": True,
                "provider": "github-copilot",
                "auth_profile": args.auth_profile,
                "requested_state": args.state,
                "coding_lane": coding_lane_execution_truth(),
                "profile_state": (
                    get_provider_state_view(
                        profile=args.auth_profile,
                        provider="github-copilot",
                    )
                    if profile_state
                    else None
                ),
            },
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

    api_cancelled, api_error = _cancel_visible_run_via_api(run_id)
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
        choices=("prepared", "handshake-started", "handshake-stubbed", "stored", "revoked"),
    )
    set_copilot_auth_state.set_defaults(func=cmd_set_copilot_auth_state)

    coding_lane_status = sub.add_parser("coding-lane-status")
    coding_lane_status.set_defaults(func=cmd_coding_lane_status)

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
    api_payload, api_error = _fetch_visible_run_via_api()
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
    response, api_error = _request_json("GET", "/mc/visible-execution")
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
    response, api_error = _request_json("GET", "/mc/visible-execution")
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
    response, api_error = _request_json(
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
    response, api_error = _request_json(
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
    response, api_error = _request_json(
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


def _fetch_visible_run_via_api() -> tuple[dict | None, str | None]:
    response, api_error = _request_json("GET", "/mc/visible-execution")
    if response is None:
        return None, api_error
    return response.get("visible_run"), None


def _cancel_visible_run_via_api(run_id: str) -> tuple[bool, str | None]:
    response, api_error = _request_json("POST", f"/chat/runs/{run_id}/cancel")
    if response is None:
        return False, api_error
    return bool(response.get("ok")), None


def _request_json(
    method: str, path: str, payload: dict | None = None
) -> tuple[dict | None, str | None]:
    settings = load_settings()
    url = f"http://{settings.host}:{settings.port}{path}"
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib_request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib_request.urlopen(request, timeout=0.75) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}, None
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        detail = _http_error_detail(body)
        if exc.code == 404:
            return None, "not-found"
        return None, detail or f"http-{exc.code}"
    except urllib_error.URLError as exc:
        reason = getattr(exc, "reason", exc)
        return None, f"api-unavailable: {reason}"
    except TimeoutError:
        return None, "api-unavailable: timeout"
    except Exception as exc:
        return None, f"api-unavailable: {exc}"


def _http_error_detail(body: str) -> str | None:
    try:
        data = json.loads(body)
    except Exception:
        return None
    detail = data.get("detail")
    return str(detail) if detail else None


def _visible_execution_section(
    visible_execution: dict, source: str, api_unavailable: str | None
) -> dict:
    return {
        "visible_execution_source": source,
        "visible_execution_api_unavailable": api_unavailable,
        "authority": _normalize_visible_authority(visible_execution.get("authority")),
        "readiness": _normalize_visible_readiness(visible_execution.get("readiness")),
        "visible_identity": _normalize_visible_identity(
            visible_execution.get("visible_identity")
        ),
        "visible_work": _normalize_visible_work(visible_execution.get("visible_work")),
        "visible_work_surface": _normalize_visible_work_surface(
            visible_execution.get("visible_work_surface")
        ),
        "visible_selected_work_surface": _normalize_visible_selected_work_surface(
            visible_execution.get("visible_selected_work_surface")
        ),
        "visible_selected_work_item": _normalize_visible_selected_work_item(
            visible_execution.get("visible_selected_work_item")
        ),
        "visible_session_continuity": _normalize_visible_session_continuity(
            visible_execution.get("visible_session_continuity")
        ),
        "visible_continuity": _normalize_visible_continuity(
            visible_execution.get("visible_continuity")
        ),
        "visible_capability_continuity": _normalize_visible_capability_continuity(
            visible_execution.get("visible_capability_continuity")
        ),
    }


def _visible_run_section(
    visible_run: dict, source: str, api_unavailable: str | None
) -> dict:
    return {
        "visible_run_source": source,
        "visible_run_api_unavailable": api_unavailable,
        "active": bool(visible_run.get("active")),
        "active_run": _normalize_active_run(visible_run.get("active_run")),
        "last_outcome": _normalize_last_outcome(visible_run.get("last_outcome")),
        "last_capability_use": _normalize_visible_capability_use(
            visible_run.get("last_capability_use")
        ),
        "persisted_recent_runs": _normalize_persisted_recent_runs(
            visible_run.get("persisted_recent_runs")
        ),
        "recent_events": visible_run.get("recent_events", []),
    }


def _capability_invocation_section(
    capability_invocation: dict, source: str, api_unavailable: str | None
) -> dict:
    return {
        "capability_invocation_source": source,
        "capability_invocation_api_unavailable": api_unavailable,
        "active": bool(capability_invocation.get("active")),
        "last_invocation": _normalize_capability_invocation(
            capability_invocation.get("last_invocation")
        ),
        "persisted_recent_invocations": _normalize_persisted_capability_invocations(
            capability_invocation.get("persisted_recent_invocations")
        ),
        "recent_approval_requests": _normalize_approval_requests(
            capability_invocation.get("recent_approval_requests")
        ),
        "recent_events": capability_invocation.get("recent_events", []),
    }


def _normalize_visible_authority(authority: dict | None) -> dict:
    authority = authority or {}
    return {
        "visible_model_provider": authority.get("visible_model_provider"),
        "visible_model_name": authority.get("visible_model_name"),
        "visible_auth_profile": authority.get("visible_auth_profile"),
    }


def _normalize_visible_readiness(readiness: dict | None) -> dict:
    readiness = readiness or {}
    return {
        "provider": readiness.get("provider"),
        "model": readiness.get("model"),
        "mode": readiness.get("mode"),
        "auth_ready": readiness.get("auth_ready"),
        "auth_status": readiness.get("auth_status"),
        "auth_profile": readiness.get("auth_profile"),
        "provider_reachable": readiness.get("provider_reachable"),
        "live_verified": readiness.get("live_verified"),
        "provider_status": readiness.get("provider_status"),
        "probe_cache": readiness.get("probe_cache"),
        "checked_at": readiness.get("checked_at"),
    }


def _normalize_visible_identity(visible_identity: dict | None) -> dict:
    visible_identity = visible_identity or {}
    return {
        "workspace": visible_identity.get("workspace"),
        "name": visible_identity.get("name"),
        "active": bool(visible_identity.get("active")),
        "source_files": list(visible_identity.get("source_files") or []),
        "extracted_line_count": visible_identity.get("extracted_line_count"),
        "prompt_chars": visible_identity.get("prompt_chars"),
        "fingerprint": visible_identity.get("fingerprint"),
    }


def _normalize_visible_work(visible_work: dict | None) -> dict:
    visible_work = visible_work or {}
    return {
        "active": bool(visible_work.get("active")),
        "run_id": visible_work.get("run_id"),
        "status": visible_work.get("status"),
        "lane": visible_work.get("lane"),
        "provider": visible_work.get("provider"),
        "model": visible_work.get("model"),
        "started_at": visible_work.get("started_at"),
        "current_user_message_preview": visible_work.get("current_user_message_preview"),
        "capability_id": visible_work.get("capability_id"),
        "persisted_recent_units": _normalize_visible_work_units(
            visible_work.get("persisted_recent_units")
        ),
        "persisted_recent_notes": _normalize_visible_work_notes(
            visible_work.get("persisted_recent_notes")
        ),
    }


def _normalize_visible_work_units(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "work_id": item.get("work_id"),
                "run_id": item.get("run_id"),
                "status": item.get("status"),
                "finished_at": item.get("finished_at"),
                "user_message_preview": item.get("user_message_preview"),
                "capability_id": item.get("capability_id"),
                "work_preview": item.get("work_preview"),
            }
        )
    return normalized


def _normalize_visible_work_notes(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "note_id": item.get("note_id"),
                "work_id": item.get("work_id"),
                "run_id": item.get("run_id"),
                "status": item.get("status"),
                "user_message_preview": item.get("user_message_preview"),
                "capability_id": item.get("capability_id"),
                "work_preview": item.get("work_preview"),
                "projection_source": item.get("projection_source"),
                "finished_at": item.get("finished_at"),
            }
        )
    return normalized


def _normalize_visible_work_surface(visible_work_surface: dict | None) -> dict:
    visible_work_surface = visible_work_surface or {}
    return {
        "active": bool(visible_work_surface.get("active")),
        "current_work_id": visible_work_surface.get("current_work_id"),
        "current_run_id": visible_work_surface.get("current_run_id"),
        "status": visible_work_surface.get("status"),
        "lane": visible_work_surface.get("lane"),
        "provider": visible_work_surface.get("provider"),
        "model": visible_work_surface.get("model"),
        "started_at": visible_work_surface.get("started_at"),
        "finished_at": visible_work_surface.get("finished_at"),
        "current_user_message_preview": visible_work_surface.get(
            "current_user_message_preview"
        ),
        "capability_id": visible_work_surface.get("capability_id"),
        "recent_work_ids": list(visible_work_surface.get("recent_work_ids") or []),
        "latest_work_preview": visible_work_surface.get("latest_work_preview"),
    }


def _normalize_visible_selected_work_surface(
    visible_selected_work_surface: dict | None,
) -> dict:
    visible_selected_work_surface = visible_selected_work_surface or {}
    return {
        "active": bool(visible_selected_work_surface.get("active")),
        "selected_work_id": visible_selected_work_surface.get("selected_work_id"),
        "selected_run_id": visible_selected_work_surface.get("selected_run_id"),
        "status": visible_selected_work_surface.get("status"),
        "lane": visible_selected_work_surface.get("lane"),
        "provider": visible_selected_work_surface.get("provider"),
        "model": visible_selected_work_surface.get("model"),
        "selected_user_message_preview": visible_selected_work_surface.get(
            "selected_user_message_preview"
        ),
        "selected_capability_id": visible_selected_work_surface.get(
            "selected_capability_id"
        ),
        "selected_work_preview": visible_selected_work_surface.get(
            "selected_work_preview"
        ),
        "recent_work_ids": list(
            visible_selected_work_surface.get("recent_work_ids") or []
        ),
    }


def _normalize_visible_selected_work_item(
    visible_selected_work_item: dict | None,
) -> dict:
    visible_selected_work_item = visible_selected_work_item or {}
    return {
        "active": bool(visible_selected_work_item.get("active")),
        "selected_work_id": visible_selected_work_item.get("selected_work_id"),
        "selected_run_id": visible_selected_work_item.get("selected_run_id"),
        "selected_status": visible_selected_work_item.get("selected_status"),
        "selected_lane": visible_selected_work_item.get("selected_lane"),
        "selected_provider": visible_selected_work_item.get("selected_provider"),
        "selected_model": visible_selected_work_item.get("selected_model"),
        "selected_user_message_preview": visible_selected_work_item.get(
            "selected_user_message_preview"
        ),
        "selected_capability_id": visible_selected_work_item.get(
            "selected_capability_id"
        ),
        "selected_work_preview": visible_selected_work_item.get(
            "selected_work_preview"
        ),
        "recent_work_ids": list(visible_selected_work_item.get("recent_work_ids") or []),
        "selection_source": visible_selected_work_item.get("selection_source"),
        "recent_count": visible_selected_work_item.get("recent_count"),
    }


def _normalize_visible_continuity(visible_continuity: dict | None) -> dict:
    visible_continuity = visible_continuity or {}
    return {
        "active": bool(visible_continuity.get("active")),
        "source": visible_continuity.get("source"),
        "included_rows": visible_continuity.get("included_rows"),
        "included_run_ids": list(visible_continuity.get("included_run_ids") or []),
        "statuses": list(visible_continuity.get("statuses") or []),
        "preview_count": visible_continuity.get("preview_count"),
        "error_count": visible_continuity.get("error_count"),
        "capability_count": visible_continuity.get("capability_count"),
        "chars": visible_continuity.get("chars"),
    }


def _normalize_visible_session_continuity(
    visible_session_continuity: dict | None,
) -> dict:
    visible_session_continuity = visible_session_continuity or {}
    return {
        "active": bool(visible_session_continuity.get("active")),
        "source": visible_session_continuity.get("source"),
        "latest_run_id": visible_session_continuity.get("latest_run_id"),
        "latest_status": visible_session_continuity.get("latest_status"),
        "latest_finished_at": visible_session_continuity.get("latest_finished_at"),
        "latest_text_preview": visible_session_continuity.get("latest_text_preview"),
        "latest_capability_id": visible_session_continuity.get("latest_capability_id"),
        "recent_capability_ids": list(
            visible_session_continuity.get("recent_capability_ids") or []
        ),
        "included_run_rows": visible_session_continuity.get("included_run_rows"),
        "included_capability_rows": visible_session_continuity.get(
            "included_capability_rows"
        ),
        "chars": visible_session_continuity.get("chars"),
    }


def _normalize_visible_capability_continuity(
    visible_capability_continuity: dict | None,
) -> dict:
    visible_capability_continuity = visible_capability_continuity or {}
    return {
        "active": bool(visible_capability_continuity.get("active")),
        "source": visible_capability_continuity.get("source"),
        "included_rows": visible_capability_continuity.get("included_rows"),
        "included_capability_ids": list(
            visible_capability_continuity.get("included_capability_ids") or []
        ),
        "statuses": list(visible_capability_continuity.get("statuses") or []),
        "preview_count": visible_capability_continuity.get("preview_count"),
        "detail_count": visible_capability_continuity.get("detail_count"),
        "chars": visible_capability_continuity.get("chars"),
    }


def _normalize_active_run(active_run: dict | None) -> dict | None:
    if not active_run:
        return None
    return {
        "run_id": active_run.get("run_id"),
        "lane": active_run.get("lane"),
        "provider": active_run.get("provider"),
        "model": active_run.get("model"),
        "started_at": active_run.get("started_at"),
        "cancelled": active_run.get("cancelled"),
    }


def _normalize_last_outcome(last_outcome: dict | None) -> dict | None:
    if not last_outcome:
        return None
    return {
        "run_id": last_outcome.get("run_id"),
        "lane": last_outcome.get("lane"),
        "provider": last_outcome.get("provider"),
        "model": last_outcome.get("model"),
        "status": last_outcome.get("status"),
        "finished_at": last_outcome.get("finished_at"),
        "error": last_outcome.get("error"),
        "text_preview": last_outcome.get("text_preview"),
    }


def _normalize_capability_invocation(last_invocation: dict | None) -> dict | None:
    if not last_invocation:
        return None
    return {
        "capability_id": last_invocation.get("capability_id"),
        "capability": last_invocation.get("capability"),
        "status": last_invocation.get("status"),
        "execution_mode": last_invocation.get("execution_mode"),
        "approval": _normalize_approval(last_invocation.get("approval")),
        "invoked_at": last_invocation.get("invoked_at"),
        "finished_at": last_invocation.get("finished_at"),
        "result_preview": last_invocation.get("result_preview"),
        "detail": last_invocation.get("detail"),
        "run_id": last_invocation.get("run_id"),
    }


def _normalize_persisted_capability_invocations(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "capability_id": item.get("capability_id"),
                "capability_name": item.get("capability_name"),
                "capability_kind": item.get("capability_kind"),
                "status": item.get("status"),
                "execution_mode": item.get("execution_mode"),
                "approval": _normalize_approval(item.get("approval")),
                "invoked_at": item.get("invoked_at"),
                "finished_at": item.get("finished_at"),
                "result_preview": item.get("result_preview"),
                "detail": item.get("detail"),
                "run_id": item.get("run_id"),
            }
        )
    return normalized


def _normalize_approval_requests(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "request_id": item.get("request_id"),
                "capability_id": item.get("capability_id"),
                "capability_name": item.get("capability_name"),
                "capability_kind": item.get("capability_kind"),
                "execution_mode": item.get("execution_mode"),
                "approval_policy": item.get("approval_policy"),
                "run_id": item.get("run_id"),
                "requested_at": item.get("requested_at"),
                "status": item.get("status"),
                "approved_at": item.get("approved_at"),
                "executed": bool(item.get("executed")),
                "executed_at": item.get("executed_at"),
                "invocation_status": item.get("invocation_status"),
                "invocation_execution_mode": item.get("invocation_execution_mode"),
            }
        )
    return normalized


def _normalize_approval(approval: dict | None) -> dict | None:
    if not approval:
        return None
    return {
        "policy": approval.get("policy"),
        "required": bool(approval.get("required")),
        "approved": bool(approval.get("approved")),
        "granted": bool(approval.get("granted")),
    }


def _normalize_visible_capability_use(last_capability_use: dict | None) -> dict | None:
    if not last_capability_use:
        return None
    return {
        "run_id": last_capability_use.get("run_id"),
        "lane": last_capability_use.get("lane"),
        "provider": last_capability_use.get("provider"),
        "model": last_capability_use.get("model"),
        "capability_id": last_capability_use.get("capability_id"),
        "capability": last_capability_use.get("capability"),
        "status": last_capability_use.get("status"),
        "execution_mode": last_capability_use.get("execution_mode"),
        "used_at": last_capability_use.get("used_at"),
        "result_preview": last_capability_use.get("result_preview"),
        "detail": last_capability_use.get("detail"),
    }


def _normalize_persisted_recent_runs(items: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for item in items or []:
        normalized.append(
            {
                "run_id": item.get("run_id"),
                "lane": item.get("lane"),
                "provider": item.get("provider"),
                "model": item.get("model"),
                "status": item.get("status"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "text_preview": item.get("text_preview"),
                "error": item.get("error"),
                "capability_id": item.get("capability_id"),
            }
        )
    return normalized


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
