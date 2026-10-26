"""Build a bounded Routine prompt directly from its immutable execution context."""
from __future__ import annotations

import json

from core.services.routine_types import RoutineExecutionContext


def build_routine_prompt(
    context: RoutineExecutionContext, *, instruction: bytes
) -> str:
    """Return the execution prompt without consulting conversation state."""
    try:
        task = instruction.decode("utf-8")
    except UnicodeDecodeError:
        task = instruction.decode("utf-8", errors="replace")
    trigger = json.dumps(
        context.trigger_inputs,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    permissions = json.dumps(
        context.permission_policy,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    workspace = "none"
    if context.workspace_kind or context.workspace_root:
        workspace = json.dumps(
            {
                "kind": context.workspace_kind,
                "name": context.workspace_name,
                "root": context.workspace_root,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return "\n".join((
        "You are Jarvis executing one isolated Routine run.",
        "Use only the declared capabilities and observable tool results.",
        "Do not infer or address any conversation destination.",
        f"Routine version: {context.routine_version}",
        f"Capability scope: {context.capability_scope}",
        f"Workspace: {workspace}",
        f"Permissions: {permissions}",
        f"Trigger inputs: {trigger}",
        "Task:",
        task,
    ))


def build_session_routine_prompt(
    context: RoutineExecutionContext, *, instruction: bytes,
) -> str:
    """Build a wakeup instruction; the visible lane supplies chat context."""
    try:
        task = instruction.decode("utf-8")
    except UnicodeDecodeError:
        task = instruction.decode("utf-8", errors="replace")
    return "\n".join((
        "[ROUTINE WAKEUP]",
        "Resume this owner-verified conversation and EXECUTE the routine now.",
        "Use relevant conversation context, but obey the routine's capability scope.",
        "Do not describe an isolated result as if it were executed here.",
        f"Routine id: {context.routine_id}",
        f"Routine version: {context.routine_version}",
        f"Capability scope: {context.capability_scope}",
        "Task:",
        task,
    ))
