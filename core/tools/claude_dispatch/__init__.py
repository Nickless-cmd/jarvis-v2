from core.tools.claude_dispatch.tool import (
    _exec_dispatch_to_claude_code,
    _exec_dispatch_status,
    _exec_dispatch_cancel,
)

CLAUDE_DISPATCH_TOOL_DEFINITIONS = [
    {
        "name": "dispatch_to_claude_code",
        "description": (
            "Hand off a coding task to a sandboxed Claude Code subprocess "
            "running in a fresh git worktree of this repo. Spec is frozen "
            "for the duration of the run; you cannot reinstruct mid-flight. "
            "Use for code edits scoped to specific files. Always supply "
            "scope_files and allowed_tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "goal": {"type": "string"},
                "scope_files": {"type": "array", "items": {"type": "string"}},
                "allowed_tools": {"type": "array", "items": {"type": "string"}},
                "max_tokens": {"type": "integer"},
                "max_wall_seconds": {"type": "integer"},
                "permission_mode": {"type": "string"},
                "forbidden_paths": {"type": "array", "items": {"type": "string"}},
                "success_criteria": {"type": "string"},
            },
            "required": ["goal", "scope_files", "allowed_tools"],
        },
    },
    {
        "name": "dispatch_status",
        "description": (
            "Look up the audit row for a previously-dispatched Claude Code "
            "task by task_id."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
    {
        "name": "dispatch_cancel",
        "description": (
            "Kill a running Claude Code dispatch by task_id. Best-effort."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    },
]

__all__ = [
    "_exec_dispatch_to_claude_code",
    "_exec_dispatch_status",
    "_exec_dispatch_cancel",
    "CLAUDE_DISPATCH_TOOL_DEFINITIONS",
]
