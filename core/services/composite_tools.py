"""Composite tools — safe self-extension through composition only.

Jarvis can propose new tools that are sequences of existing ones.
A proposal isn't callable until a human approves it. After approval,
Jarvis invokes it via the composite_invoke tool.

Step format:
    {"tool": "existing_tool_name", "args": {...}, "bind": "optional_name"}

Arg values can include {{templates}} that resolve to:
  - {{input.X}}         — parameter supplied at invocation time
  - {{step_N.path}}     — result of Nth step (N is 1-indexed)
  - {{bind_name.path}}  — named bind from a prior step

All other characters pass through unchanged. Templates inside nested
dicts/lists recurse. Only existing tool handlers can be called — no
arbitrary Python, no eval, no shell access.
"""
from __future__ import annotations

import logging
import re
from typing import Any

from core.eventbus.bus import event_bus
from core.runtime.db_composites import (
    approve_composite as _db_approve,
    count_composites,
    delete_composite as _db_delete,
    get_composite as _db_get,
    list_composites as _db_list,
    propose_composite as _db_propose,
    record_invocation,
    revoke_composite as _db_revoke,
)

logger = logging.getLogger(__name__)


_MAX_STEPS = 12
_TEMPLATE_RE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def propose(
    *,
    name: str,
    description: str,
    input_schema: dict[str, Any],
    steps: list[dict[str, Any]],
    created_by: str | None = None,
) -> dict[str, Any]:
    """Validate and store a proposal. Raises ValueError on invalid input."""
    name = str(name or "").strip()
    description = str(description or "").strip()
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,63}", name):
        raise ValueError(
            "name must be lowercase snake_case, 3-64 chars, starting with a letter"
        )
    if not description:
        raise ValueError("description is required")
    if not isinstance(input_schema, dict):
        raise ValueError("input_schema must be a dict (JSON object)")
    if not isinstance(steps, list) or not steps:
        raise ValueError("steps must be a non-empty list")
    if len(steps) > _MAX_STEPS:
        raise ValueError(f"composite cannot exceed {_MAX_STEPS} steps")

    if _db_get(name):
        raise ValueError(f"composite '{name}' already exists")

    # Validate each step references a known handler with a dict args
    from core.tools.simple_tools import _TOOL_HANDLERS

    for i, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ValueError(f"step {i} must be an object")
        tool = str(step.get("tool") or "").strip()
        if not tool:
            raise ValueError(f"step {i}: 'tool' is required")
        if tool == "composite_invoke":
            raise ValueError(
                f"step {i}: composites may not invoke composite_invoke (no recursion)"
            )
        if tool not in _TOOL_HANDLERS:
            raise ValueError(f"step {i}: unknown tool '{tool}'")
        args = step.get("args", {})
        if not isinstance(args, dict):
            raise ValueError(f"step {i}: 'args' must be an object")
        bind = step.get("bind")
        if bind is not None and not isinstance(bind, str):
            raise ValueError(f"step {i}: 'bind' must be a string when present")

    proposal = _db_propose(
        name=name,
        description=description,
        input_schema=input_schema,
        steps=steps,
        created_by=created_by,
    )
    try:
        event_bus.publish(
            "composite.proposed",
            {
                "name": proposal.get("name"),
                "description": proposal.get("description"),
                "step_count": len(proposal.get("steps") or []),
                "created_by": proposal.get("created_by"),
            },
        )
    except Exception:
        pass
    return proposal


def approve(name: str, *, approved_by: str | None = None) -> dict[str, Any] | None:
    result = _db_approve(name, approved_by=approved_by)
    if result:
        try:
            event_bus.publish(
                "composite.approved",
                {"name": name, "approved_by": approved_by},
            )
        except Exception:
            pass
    return result


def revoke(name: str) -> dict[str, Any] | None:
    result = _db_revoke(name)
    if result:
        try:
            event_bus.publish("composite.revoked", {"name": name})
        except Exception:
            pass
    return result


def delete(name: str) -> bool:
    ok = _db_delete(name)
    if ok:
        try:
            event_bus.publish("composite.deleted", {"name": name})
        except Exception:
            pass
    return ok


def get(name: str) -> dict[str, Any] | None:
    return _db_get(name)


def list_available(*, status: str | None = None) -> list[dict[str, Any]]:
    return _db_list(status=status)


def invoke(name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Execute an approved composite. Returns {status, steps, result}."""
    composite = _db_get(name)
    if composite is None:
        return {"status": "error", "error": f"composite '{name}' not found"}
    if composite.get("status") != "approved":
        return {
            "status": "error",
            "error": f"composite '{name}' is not approved (status={composite.get('status')})",
        }

    from core.tools.simple_tools import _TOOL_HANDLERS

    steps = composite.get("steps") or []
    context: dict[str, Any] = {"input": dict(args or {})}
    step_results: list[dict[str, Any]] = []

    for i, step in enumerate(steps, start=1):
        tool_name = str(step.get("tool"))
        raw_args = step.get("args") or {}
        bind = step.get("bind")

        try:
            resolved = _substitute(raw_args, context)
        except Exception as exc:
            return {
                "status": "error",
                "error": f"step {i} ({tool_name}): template error: {exc}",
                "steps": step_results,
            }

        handler = _TOOL_HANDLERS.get(tool_name)
        if handler is None:
            return {
                "status": "error",
                "error": f"step {i}: handler '{tool_name}' missing at runtime",
                "steps": step_results,
            }
        try:
            result = handler(resolved)
        except Exception as exc:
            return {
                "status": "error",
                "error": f"step {i} ({tool_name}): {exc}",
                "steps": step_results,
            }
        step_results.append({"step": i, "tool": tool_name, "result": result})
        context[f"step_{i}"] = result
        if bind:
            context[bind] = result
        # abort cascade on explicit per-step failure
        if isinstance(result, dict) and result.get("status") == "error":
            return {
                "status": "error",
                "error": f"step {i} ({tool_name}) returned error",
                "steps": step_results,
            }

    try:
        record_invocation(name)
        event_bus.publish("composite.invoked", {"name": name})
    except Exception:
        pass

    final = step_results[-1]["result"] if step_results else None
    return {"status": "ok", "steps": step_results, "result": final}


def get_stats() -> dict[str, Any]:
    return {
        "proposed": count_composites(status="proposed"),
        "approved": count_composites(status="approved"),
        "revoked": count_composites(status="revoked"),
        "total": count_composites(),
    }


# ---------------------------------------------------------------------------
# Template resolution
# ---------------------------------------------------------------------------

def _substitute(value: Any, context: dict[str, Any]) -> Any:
    if isinstance(value, str):
        return _resolve_string(value, context)
    if isinstance(value, list):
        return [_substitute(v, context) for v in value]
    if isinstance(value, dict):
        return {k: _substitute(v, context) for k, v in value.items()}
    return value


def _resolve_string(s: str, context: dict[str, Any]) -> Any:
    """Resolve {{...}} templates.

    If the string is *exactly* one template, return the raw value
    (preserves types — e.g. lists, dicts, ints). If the string has
    surrounding text, interpolate as strings.
    """
    matches = list(_TEMPLATE_RE.finditer(s))
    if not matches:
        return s
    if len(matches) == 1 and matches[0].group(0) == s:
        return _lookup(matches[0].group(1), context)

    def _replace(m: re.Match[str]) -> str:
        val = _lookup(m.group(1), context)
        return "" if val is None else str(val)

    return _TEMPLATE_RE.sub(_replace, s)


def _lookup(path: str, context: dict[str, Any]) -> Any:
    parts = [p for p in path.strip().split(".") if p]
    if not parts:
        return None
    current: Any = context.get(parts[0])
    for key in parts[1:]:
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, list):
            try:
                idx = int(key)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        else:
            return None
    return current
