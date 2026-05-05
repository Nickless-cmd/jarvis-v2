"""Bridge tool execution outcomes into durable runtime action evidence."""
from __future__ import annotations

from typing import Any


def record_tool_outcome_memory(
    *,
    tool_name: str,
    arguments: dict[str, Any] | None,
    result: dict[str, Any] | None,
    mode: str = "tool",
) -> dict[str, Any] | None:
    """Persist a tool outcome as runtime action evidence.

    This gives the executive/memory layer a durable precedent trail for tool
    behavior instead of only transient eventbus facts.
    """
    name = str(tool_name or "").strip()
    if not name:
        return None
    result_dict = dict(result or {})
    status = str(result_dict.get("status") or "unknown")
    summary = _summary_for_result(name, result_dict)
    try:
        from core.services.runtime_action_outcome_tracking import (
            record_runtime_action_outcome,
        )
        return record_runtime_action_outcome(
            action_id=f"tool:{name}",
            mode=mode,
            reason="Tool execution completed; persisted as agency evidence.",
            score=_score_for_status(status),
            payload={
                "tool_name": name,
                "arguments_preview": _preview_arguments(arguments or {}),
            },
            result={
                **result_dict,
                "status": status,
                "summary": summary,
            },
        )
    except Exception:
        return None


def _summary_for_result(tool_name: str, result: dict[str, Any]) -> str:
    for key in ("summary", "message", "error", "result_text"):
        value = str(result.get(key) or "").strip()
        if value:
            return value[:300]
    return f"{tool_name} finished with status {result.get('status') or 'unknown'}"


def _score_for_status(status: str) -> float:
    normalized = str(status or "").lower()
    if normalized in {"ok", "success", "completed", "executed"}:
        return 0.8
    if normalized in {"approval_needed", "gated", "gate_blocked", "blocked"}:
        return 0.1
    if normalized in {"error", "failed", "timeout"}:
        return -0.6
    return 0.0


def _preview_arguments(arguments: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)[:160]
        for key, value in dict(arguments or {}).items()
        if not str(key).startswith("_runtime_")
    }
