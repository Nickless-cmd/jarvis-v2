#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from urllib import error as urllib_error
from urllib import request as urllib_request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.jarvis_api.services.visible_model import visible_execution_readiness
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
from core.runtime.db import connect, init_db
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
                "path": str(SETTINGS_FILE),
                "settings": settings.to_dict(),
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
    result, source, api_unavailable = _invoke_capability_truth(capability_id)
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

    workspace = sub.add_parser("workspace")
    workspace.add_argument("--name", default="default")
    workspace.set_defaults(func=cmd_workspace)

    cancel_visible = sub.add_parser("cancel-visible-run")
    cancel_visible.add_argument("--run-id", default="")
    cancel_visible.set_defaults(func=cmd_cancel_visible_run)

    invoke_capability = sub.add_parser("invoke-capability")
    invoke_capability.add_argument("capability_id")
    invoke_capability.set_defaults(func=cmd_invoke_capability)

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
        }, "api", None
    return {
        "authority": {
            "visible_model_provider": load_settings().visible_model_provider,
            "visible_model_name": load_settings().visible_model_name,
            "visible_auth_profile": load_settings().visible_auth_profile,
        },
        "readiness": visible_execution_readiness(),
    }, "local-fallback", api_error


def _capability_invocation_truth() -> tuple[dict, str, str | None]:
    response, api_error = _request_json("GET", "/mc/visible-execution")
    if response is not None:
        return response.get("capability_invocation") or {}, "api", None
    return get_capability_invocation_truth(), "local-fallback", api_error


def _invoke_capability_truth(capability_id: str) -> tuple[dict, str, str | None]:
    response, api_error = _request_json(
        "POST", f"/mc/workspace-capabilities/{capability_id}/invoke"
    )
    if response is not None:
        return response, "api", None
    return invoke_workspace_capability(capability_id), "local-fallback", api_error


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
        "invoked_at": last_invocation.get("invoked_at"),
        "finished_at": last_invocation.get("finished_at"),
        "result_preview": last_invocation.get("result_preview"),
        "detail": last_invocation.get("detail"),
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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
