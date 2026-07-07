"""Read-only capability-udførere (runtime-event-read, grep, multi-read, outline).

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som den sammenhængende
enhed af bundne, approval-frie read-only tools: inspektion af egne runtime-events,
projekt-grep, multi-fil-læsning og projekt-outline.

Afhænger af delte konstanter (const), result-helpers (results) og
external-path-resolution (workspace_capability_decl). Kaldes af
_invoke_runnable_capability i hoved-modulet.

Alle funktioner re-eksporteres fra core.tools.workspace_capabilities for
bagudkompatibilitet.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from core.runtime.config import PROJECT_ROOT

from core.tools.workspace_capabilities_const import (
    MAX_EXEC_SECONDS,
    MAX_FILE_OUTPUT_CHARS,
    MAX_GREP_MATCH_CHARS,
    MAX_GREP_MATCHES,
    MAX_MULTI_READ_CHARS,
    MAX_MULTI_READ_FILES,
)
from core.tools.workspace_capabilities_results import _approval_result
from core.tools.workspace_capability_decl import _resolve_external_path


def _execute_runtime_event_read(summary: dict[str, object]) -> dict[str, object]:
    """Execute the runtime-event-read tool: surface recent eventbus events.

    Lets Jarvis inspect his own recent runtime activity (eventbus events)
    so internal logging is no longer a blind spot. Read-only and bounded
    to the most recent 30 events.
    """
    try:
        from core.eventbus.bus import event_bus
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "capability": summary,
            "status": "blocked-runtime-unavailable",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=False),
            "result": None,
            "detail": f"Eventbus unavailable: {exc}",
        }
    try:
        events = event_bus.recent(limit=30)
    except Exception as exc:
        return {
            "capability": summary,
            "status": "blocked-runtime-error",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=False),
            "result": None,
            "detail": f"Failed to read runtime events: {exc}",
        }
    lines: list[str] = []
    for event in events:
        kind = str(event.get("kind") or "").strip()
        created_at = str(event.get("created_at") or "").strip()
        payload_json = str(event.get("payload_json") or "").strip()
        if not kind:
            continue
        payload_preview = payload_json
        if len(payload_preview) > 160:
            payload_preview = payload_preview[:159] + "…"
        lines.append(f"{created_at} | {kind} | {payload_preview}")
    text_body = "\n".join(lines) if lines else "[no recent runtime events]"
    if len(text_body) > MAX_FILE_OUTPUT_CHARS:
        text_body = text_body[: MAX_FILE_OUTPUT_CHARS - 1].rstrip() + "…"
    return {
        "capability": summary,
        "status": "executed",
        "execution_mode": summary["execution_mode"],
        "approval": _approval_result(summary, approved=True, granted=True),
        "result": {
            "type": "runtime-event-read",
            "event_count": len(lines),
            "text": text_body,
        },
        "detail": f"Read {len(lines)} recent runtime events.",
    }


def _execute_project_grep(
    summary: dict[str, object],
    command_text: str | None,
) -> dict[str, object]:
    """Grep across PROJECT_ROOT for a pattern. Read-only, no approval."""
    pattern = str(command_text or "").strip()
    if not pattern:
        return {
            "capability": summary,
            "status": "blocked-missing-pattern",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=False),
            "result": None,
            "detail": "Project grep requires a search pattern in command_text.",
        }
    argv = [
        "grep", "-rn", "--color=never",
        "--include=*.py", "--include=*.md", "--include=*.json",
        "--include=*.yaml", "--include=*.yml", "--include=*.toml",
        "--include=*.ts", "--include=*.tsx", "--include=*.jsx",
        "--include=*.js", "--include=*.css", "--include=*.html",
        "--exclude-dir=.git", "--exclude-dir=node_modules",
        "--exclude-dir=__pycache__", "--exclude-dir=.claude",
        "--exclude-dir=dist", "--exclude-dir=build",
        "-m", str(MAX_GREP_MATCHES),
        pattern,
        ".",
    ]
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_EXEC_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {
            "capability": summary,
            "status": "blocked-timeout",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": None,
            "detail": f"Grep timed out after {MAX_EXEC_SECONDS}s.",
        }
    output = str(completed.stdout or "").strip()
    lines = output.splitlines()[:MAX_GREP_MATCHES]
    bounded_lines: list[str] = []
    for line in lines:
        if len(line) > MAX_GREP_MATCH_CHARS:
            line = line[: MAX_GREP_MATCH_CHARS - 1] + "…"
        bounded_lines.append(line)
    text_body = "\n".join(bounded_lines) if bounded_lines else "[no matches]"
    if len(text_body) > MAX_FILE_OUTPUT_CHARS:
        text_body = text_body[: MAX_FILE_OUTPUT_CHARS - 1].rstrip() + "…"
    return {
        "capability": summary,
        "status": "executed",
        "execution_mode": summary["execution_mode"],
        "approval": _approval_result(summary, approved=False, granted=True),
        "result": {
            "type": "project-grep",
            "pattern": pattern,
            "match_count": len(bounded_lines),
            "text": text_body,
        },
        "detail": f"Grep found {len(bounded_lines)} matches for '{pattern}'.",
    }


def _execute_multi_file_read(
    summary: dict[str, object],
    command_text: str | None,
    workspace_dir: Path,
) -> dict[str, object]:
    """Read multiple project files in one call. Read-only, no approval."""
    raw_paths = str(command_text or "").strip()
    if not raw_paths:
        raw_paths = ", ".join([
            str(Path(PROJECT_ROOT) / "core/eventbus/bus.py"),
            str(Path(PROJECT_ROOT) / "core/eventbus/events.py"),
            str(Path(PROJECT_ROOT) / "core/runtime/config.py"),
            str(Path(PROJECT_ROOT) / "core/runtime/bootstrap.py"),
            str(Path(PROJECT_ROOT) / "apps/api/jarvis_api/app.py"),
        ])
    path_list = [p.strip() for p in raw_paths.split(",") if p.strip()]
    if len(path_list) > MAX_MULTI_READ_FILES:
        path_list = path_list[:MAX_MULTI_READ_FILES]
    parts: list[str] = []
    files_read = 0
    total_chars = 0
    per_file_limit = MAX_MULTI_READ_CHARS // max(len(path_list), 1)
    for raw_path in path_list:
        candidate = _resolve_external_path(workspace_dir, raw_path)
        if candidate is None or not candidate.exists() or not candidate.is_file():
            parts.append(f"--- file: {raw_path} ---\n[not found]")
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except (PermissionError, OSError):
            parts.append(f"--- file: {raw_path} ---\n[permission denied]")
            continue
        if len(text) > per_file_limit:
            text = text[: per_file_limit - 1].rstrip() + "…"
        parts.append(f"--- file: {candidate} ---\n{text}")
        files_read += 1
        total_chars += len(text)
        if total_chars >= MAX_MULTI_READ_CHARS:
            break
    text_body = "\n\n".join(parts)
    if len(text_body) > MAX_MULTI_READ_CHARS:
        text_body = text_body[: MAX_MULTI_READ_CHARS - 1].rstrip() + "…"
    return {
        "capability": summary,
        "status": "executed",
        "execution_mode": summary["execution_mode"],
        "approval": _approval_result(summary, approved=False, granted=True),
        "result": {
            "type": "multi-external-file-read",
            "files_requested": len(path_list),
            "files_read": files_read,
            "text": text_body,
        },
        "detail": f"Read {files_read} of {len(path_list)} requested files.",
    }


def _execute_project_outline(
    summary: dict[str, object],
    command_text: str | None,
) -> dict[str, object]:
    """List project files with line counts. Read-only, no approval."""
    subdir = str(command_text or "").strip() or "."
    target_dir = Path(PROJECT_ROOT) / subdir
    if not target_dir.exists() or not target_dir.is_dir():
        return {
            "capability": summary,
            "status": "blocked-invalid-path",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=False),
            "result": None,
            "detail": f"Directory not found: {subdir}",
        }
    try:
        resolved = target_dir.resolve()
        project_resolved = Path(PROJECT_ROOT).resolve()
        resolved.relative_to(project_resolved)
    except ValueError:
        return {
            "capability": summary,
            "status": "blocked-scope-violation",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=False),
            "result": None,
            "detail": "Path must be within project root.",
        }
    argv = [
        "find", str(resolved),
        "-type", "f",
        "(", "-name", "*.py", "-o", "-name", "*.md", "-o", "-name", "*.json",
        "-o", "-name", "*.yaml", "-o", "-name", "*.yml", "-o", "-name", "*.toml",
        "-o", "-name", "*.ts", "-o", "-name", "*.tsx", "-o", "-name", "*.js",
        "-o", "-name", "*.css", "-o", "-name", "*.html", ")",
        "-not", "-path", "*/.git/*",
        "-not", "-path", "*/node_modules/*",
        "-not", "-path", "*/__pycache__/*",
        "-not", "-path", "*/.claude/*",
        "-not", "-path", "*/workspace/*",
        "-not", "-path", "*/tests/*",
    ]
    try:
        find_result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=MAX_EXEC_SECONDS,
            cwd=str(PROJECT_ROOT),
        )
    except subprocess.TimeoutExpired:
        return {
            "capability": summary,
            "status": "blocked-timeout",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": None,
            "detail": f"Outline timed out after {MAX_EXEC_SECONDS}s.",
        }
    file_paths = [
        p.strip() for p in find_result.stdout.strip().splitlines() if p.strip()
    ][:100]
    entries: list[tuple[str, int]] = []
    for fp in file_paths:
        try:
            line_count = sum(1 for _ in open(fp, encoding="utf-8", errors="replace"))
            rel = str(Path(fp).relative_to(project_resolved))
            entries.append((rel, line_count))
        except (OSError, ValueError):
            continue
    entries.sort(key=lambda e: -e[1])
    lines = [f"{count:>6} lines  {path}" for path, count in entries]
    total = sum(c for _, c in entries)
    lines.append(f"\n{total:>6} lines  TOTAL ({len(entries)} files)")
    text_body = "\n".join(lines)
    if len(text_body) > MAX_FILE_OUTPUT_CHARS:
        text_body = text_body[: MAX_FILE_OUTPUT_CHARS - 1].rstrip() + "…"
    return {
        "capability": summary,
        "status": "executed",
        "execution_mode": summary["execution_mode"],
        "approval": _approval_result(summary, approved=False, granted=True),
        "result": {
            "type": "project-outline",
            "subdir": subdir,
            "file_count": len(entries),
            "total_lines": total,
            "text": text_body,
        },
        "detail": f"Outlined {len(entries)} files ({total} lines) in {subdir}.",
    }
