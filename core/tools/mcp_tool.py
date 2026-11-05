"""Jarvis-toolindgangen til MCP-register, tillid og MCP Apps."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def exec_mcp(args: dict[str, Any]) -> dict[str, Any]:
    """Se, godkend, list og kald MCP-tools gennem én kompakt toolindgang."""
    from core.services import mcp_manager, mcp_trust

    handling = str(args.get("action") or "status").strip().lower()
    server = str(args.get("server") or "").strip()

    if handling == "status":
        return mcp_manager.status()
    if handling == "allow":
        if not server:
            return {"status": "error", "error": "server mangler"}
        from core.services.operator_channel import current_is_owner
        if not current_is_owner():
            return {"status": "error", "error": "kun Bjørn kan godkende en MCP-server"}
        return mcp_trust.allow(server)
    if handling == "revoke":
        from core.services.operator_channel import current_is_owner
        if not current_is_owner():
            return {"status": "error", "error": "kun Bjørn kan tilbagekalde en MCP-server"}
        return mcp_trust.revoke(server)
    if handling == "tools":
        if not server:
            return {"status": "error", "error": "server mangler"}
        return mcp_manager.list_tools(server)
    if handling == "call":
        vaerktoej = str(args.get("tool") or "").strip()
        if not server or not vaerktoej:
            return {"status": "error", "error": "server og tool er påkrævet"}
        tool_args = args.get("arguments") or {}
        if not isinstance(tool_args, dict):
            return {"status": "error", "error": "arguments skal være et objekt"}
        result, app = mcp_manager.call_with_app(server, vaerktoej, tool_args)
        if app:
            try:
                from core.services.mcp_apps import publish
                publish(
                    server=server,
                    tool_name=vaerktoej,
                    arguments=tool_args,
                    result=app["result"],
                    html=app["html"],
                    run_id=str(args.get("_runtime_turn_id")
                               or args.get("_runtime_run_id") or ""),
                    tool_use_id=str(args.get("_runtime_tool_use_id") or ""),
                )
            except Exception as exc:
                # Tool-resultatet er stadig sandt og brugbart, selv hvis den
                # valgfrie UI-resource er defekt.
                logger.warning("MCP App kunne ikke publiceres", exc_info=True)
                result = dict(result)
                result["ui_warning"] = f"MCP App-fladen kunne ikke vises: {str(exc)[:160]}"
        return result
    return {"status": "error", "error": f"ukendt action: {handling!r}"}


# Samme offentlige navn som den gamle placering.
_exec_mcp = exec_mcp

