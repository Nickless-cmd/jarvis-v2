"""Tool registry entries for staged edits.

Wires the core/services/staged_edits.py primitives as 5 tools Jarvis can
call inline:

  stage_edit_file        — like edit_file but doesn't write to disk
  stage_write_file       — like write_file but doesn't write to disk
  list_staged_edits      — show what's currently staged
  commit_staged_edits    — apply all (or named) staged edits atomically
  discard_staged_edits   — drop staged edits without applying

Session resolution: the visible-run loop binds a session_id ContextVar
before executing tools. We pull it from there so each chat session has
its own staging area. Falls back to "_default" if not bound.
"""
from __future__ import annotations

from typing import Any

from core.services.staged_edits import (
    commit_staged,
    discard_staged,
    list_staged,
    stage_edit,
    stage_write,
)


def _current_session_id() -> str:
    """Resolve the session_id for staging scope.

    Tries multiple ContextVars in order — visible run loop sets one,
    chat session machinery may set another. Falls back to "_default".
    """
    try:
        from core.services.visible_run_context import current_session_id
        sid = current_session_id() or ""
        if sid:
            return sid
    except Exception:
        pass
    try:
        from core.services.chat_sessions import current_session_id_ctx
        sid = current_session_id_ctx() or ""
        if sid:
            return sid
    except Exception:
        pass
    return "_default"


# ── Tool exec wrappers ────────────────────────────────────────────


def _exec_stage_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    return stage_edit(
        session_id=_current_session_id(),
        path=str(args.get("path") or "").strip(),
        old_text=str(args.get("old_text") or ""),
        new_text=str(args.get("new_text") or ""),
        replace_all=bool(args.get("replace_all", False)),
        note=str(args.get("note") or ""),
    )


def _exec_stage_write_file(args: dict[str, Any]) -> dict[str, Any]:
    return stage_write(
        session_id=_current_session_id(),
        path=str(args.get("path") or "").strip(),
        content=str(args.get("content") or ""),
        note=str(args.get("note") or ""),
    )


def _exec_list_staged_edits(args: dict[str, Any]) -> dict[str, Any]:
    return list_staged(
        _current_session_id(),
        full_diffs=bool(args.get("full_diffs", False)),
    )


def _exec_commit_staged_edits(args: dict[str, Any]) -> dict[str, Any]:
    raw = args.get("stage_ids")
    stage_ids = None
    if isinstance(raw, list) and raw:
        stage_ids = [str(x) for x in raw if x]
    return commit_staged(_current_session_id(), stage_ids=stage_ids)


def _exec_discard_staged_edits(args: dict[str, Any]) -> dict[str, Any]:
    raw = args.get("stage_ids")
    stage_ids = None
    if isinstance(raw, list) and raw:
        stage_ids = [str(x) for x in raw if x]
    return discard_staged(_current_session_id(), stage_ids=stage_ids)


# ── Tool definitions (OpenAI-style schema) ───────────────────────


STAGED_EDITS_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "stage_edit_file",
            "description": (
                "Stage an edit to a file WITHOUT writing to disk. Use when you're "
                "composing a multi-file refactor or larger change and want to review "
                "the full diff together before applying. Same matching semantics as "
                "edit_file: old_text must be a unique substring (or pass replace_all). "
                "After staging all edits, call list_staged_edits to review, then "
                "commit_staged_edits to apply atomically (rolls back on failure) or "
                "discard_staged_edits to throw the batch away."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to edit"},
                    "old_text": {"type": "string", "description": "Substring to replace"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                    "replace_all": {
                        "type": "boolean",
                        "description": "Replace every occurrence (default false)",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional human-readable note (e.g. 'rename foo to bar')",
                    },
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stage_write_file",
            "description": (
                "Stage a full-file write/create WITHOUT touching disk. Pairs with "
                "stage_edit_file for batches that mix edits and new files. The "
                "current file content (if it exists) is captured at stage time so "
                "the diff is meaningful and rollback can restore it."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Absolute path to write"},
                    "content": {"type": "string", "description": "Full file content"},
                    "note": {"type": "string", "description": "Optional note"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_staged_edits",
            "description": (
                "List all currently staged edits for this session — paths, "
                "+/- counts, optional full diffs. Use to review before committing. "
                "Returns count=0 if nothing is staged."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "full_diffs": {
                        "type": "boolean",
                        "description": "Include full unified diff text per edit (default false — saves tokens)",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "commit_staged_edits",
            "description": (
                "Apply staged edits to disk atomically. On the first failure, "
                "already-applied edits are rolled back using their captured "
                "old_content. With no arguments: commits ALL staged edits. With "
                "stage_ids: commits only the listed ones. Detects out-of-band file "
                "changes between stage time and commit and refuses to overwrite "
                "(safer than silently discarding parallel edits)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stage_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional subset of stage_ids to commit. Omit to commit all.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "discard_staged_edits",
            "description": (
                "Drop staged edits without applying. With no arguments: discards "
                "the whole batch. With stage_ids: drops only those. Returns count "
                "of edits removed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "stage_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional subset to discard. Omit for all.",
                    },
                },
                "required": [],
            },
        },
    },
]


STAGED_EDITS_TOOL_HANDLERS: dict[str, Any] = {
    "stage_edit_file": _exec_stage_edit_file,
    "stage_write_file": _exec_stage_write_file,
    "list_staged_edits": _exec_list_staged_edits,
    "commit_staged_edits": _exec_commit_staged_edits,
    "discard_staged_edits": _exec_discard_staged_edits,
}
