"""Tools for project-scoped persistent notes.

Stored at <project_root>/.jarvisx/notes.md. Persists across sessions —
when Jarvis is anchored to the same project later, prompt_contract reads
this file and injects it as awareness so he "remembers" lessons learned
about THIS codebase even after the chat history is /compact'ed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.identity.project_context import current_project_root


_NOTES_RELATIVE = ".jarvisx/notes.md"
_GITIGNORE_BODY = "# JarvisX local-only notes — do not commit\n*\n!.gitignore\n"
_MAX_NOTES_BYTES = 64 * 1024  # 64 KB ceiling — enough for project-specific lessons


def _resolve_notes_path() -> Path | None:
    root = current_project_root().strip()
    if not root:
        return None
    p = Path(root).expanduser().resolve()
    if not p.is_dir():
        return None
    return p / _NOTES_RELATIVE


def _exec_read_project_notes(_args: dict[str, Any]) -> dict[str, Any]:
    p = _resolve_notes_path()
    if p is None:
        return {
            "status": "no-anchor",
            "message": "No project anchored — cannot resolve notes path. Bjørn must anchor JarvisX to a project first.",
        }
    if not p.is_file():
        return {
            "status": "ok",
            "exists": False,
            "path": str(p),
            "content": "",
        }
    raw = p.read_bytes()
    truncated = len(raw) > _MAX_NOTES_BYTES
    if truncated:
        raw = raw[:_MAX_NOTES_BYTES]
    return {
        "status": "ok",
        "exists": True,
        "path": str(p),
        "content": raw.decode("utf-8", errors="replace"),
        "truncated": truncated,
    }


def _exec_update_project_notes(args: dict[str, Any]) -> dict[str, Any]:
    p = _resolve_notes_path()
    if p is None:
        return {
            "status": "no-anchor",
            "message": "No project anchored — set X-JarvisX-Project (e.g. via JarvisX desktop app's project picker) before writing notes.",
        }
    content = str(args.get("content") or "")
    mode = str(args.get("mode") or "overwrite").lower()
    if mode not in ("overwrite", "append"):
        return {"status": "error", "error": "mode must be 'overwrite' or 'append'"}

    p.parent.mkdir(parents=True, exist_ok=True)

    # Drop a .gitignore if missing so notes never accidentally get
    # committed. Notes are local-to-this-machine project memory by design.
    gi = p.parent / ".gitignore"
    if not gi.is_file():
        gi.write_text(_GITIGNORE_BODY, encoding="utf-8")

    if mode == "append" and p.is_file():
        existing = p.read_text(encoding="utf-8", errors="replace")
        new_content = existing.rstrip() + "\n\n" + content.lstrip()
    else:
        new_content = content

    if len(new_content.encode("utf-8")) > _MAX_NOTES_BYTES:
        return {
            "status": "error",
            "error": f"notes exceed {_MAX_NOTES_BYTES} bytes — please prune. "
                     f"Project notes are short by design; large state belongs in workspace MEMORY.md.",
        }

    p.write_text(new_content, encoding="utf-8")
    return {
        "status": "ok",
        "path": str(p),
        "size_bytes": len(new_content.encode("utf-8")),
        "mode": mode,
    }


PROJECT_NOTES_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_project_notes",
            "description": (
                "Read the project-specific notes file (.jarvisx/notes.md inside "
                "the currently anchored project root). Use to recall what you "
                "learned about THIS codebase from previous sessions — "
                "architectural quirks, gotchas, conventions, the user's "
                "preferences for THIS project. Returns exists=false if no "
                "notes exist yet. Returns no-anchor if no project is anchored."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_project_notes",
            "description": (
                "Write or append to the project-specific notes file. Use SPARINGLY — "
                "only for genuinely useful lessons that will help on future sessions "
                "in this same project: architectural surprises, conventions Bjørn "
                "uses HERE specifically, recurring pitfalls. Don't dump session "
                "transcripts; this is for distilled takeaways. Cap is 64 KB. "
                "mode='overwrite' replaces, mode='append' adds with a blank line."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Markdown content"},
                    "mode": {
                        "type": "string",
                        "enum": ["overwrite", "append"],
                        "description": "overwrite (default) or append",
                    },
                },
                "required": ["content"],
            },
        },
    },
]


PROJECT_NOTES_TOOL_HANDLERS: dict[str, Any] = {
    "read_project_notes": _exec_read_project_notes,
    "update_project_notes": _exec_update_project_notes,
}
