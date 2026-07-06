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
    family = classify_tool_family(name)
    summary = _summary_for_result(name, result_dict)
    try:
        from core.services.runtime_action_outcome_tracking import (
            record_runtime_action_outcome,
        )
        return record_runtime_action_outcome(
            action_id=f"tool:{name}",
            mode=mode,
            reason="Tool execution completed; persisted as agency evidence.",
            score=_score_for_outcome(status=status, family=family, result=result_dict),
            payload={
                "tool_name": name,
                "tool_family": family,
                "arguments_preview": _preview_arguments(arguments or {}),
            },
            result={
                **result_dict,
                "status": status,
                "tool_family": family,
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


def classify_tool_family(tool_name: str) -> str:
    name = str(tool_name or "").lower().replace("_", "-")
    if any(part in name for part in ("read", "list", "grep", "search", "find", "inspect", "open")):
        return "read"
    if any(part in name for part in ("write", "edit", "patch", "replace", "delete", "move", "commit")):
        return "write"
    if any(part in name for part in ("bash", "shell", "exec", "command", "pytest", "npm", "test")):
        return "execution"
    if any(part in name for part in ("browser", "navigate", "click", "web", "http", "curl")):
        return "browser"
    if any(part in name for part in ("memory", "brain", "recall", "remember")):
        return "memory"
    return "general"


def _score_for_outcome(*, status: str, family: str, result: dict[str, Any]) -> float:
    normalized = str(status or "").lower()
    family_name = str(family or "general")
    if normalized in {"ok", "success", "completed", "executed"}:
        return {
            "read": 0.62,
            "write": 0.9,
            "execution": 0.82,
            "browser": 0.7,
            "memory": 0.78,
        }.get(family_name, 0.75)
    if normalized in {"approval_needed", "gated", "gate_blocked", "blocked"}:
        return 0.18 if family_name in {"write", "execution"} else 0.08
    if normalized in {"error", "failed", "timeout"}:
        if normalized == "timeout":
            return -0.45 if family_name in {"browser", "execution"} else -0.35
        if family_name == "write":
            return -0.75
        if family_name == "execution":
            return -0.65
        return -0.5
    return 0.0


def _preview_arguments(arguments: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): str(value)[:160]
        for key, value in dict(arguments or {}).items()
        if not str(key).startswith("_runtime_")
    }


