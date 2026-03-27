from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from core.cli.http_fallback import request_json
from core.runtime.bootstrap import ensure_runtime_dirs
from core.runtime.db import (
    approve_capability_approval_request,
    get_capability_approval_request,
)
from core.tools.workspace_capabilities import invoke_workspace_capability


def cmd_invoke_capability(args: argparse.Namespace) -> None:
    ensure_runtime_dirs()
    capability_id = args.capability_id.strip()
    result, source, api_unavailable = invoke_capability_truth(
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
    result, source, api_unavailable = approve_capability_request_truth(request_id)
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
    result, source, api_unavailable = execute_capability_request_truth(request_id)
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


def invoke_capability_truth(
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


def approve_capability_request_truth(
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


def execute_capability_request_truth(
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
