"""Workspace-dokument-parsing (TOOLS.md / SKILLS.md → capability-sektioner).

Udskilt fra workspace_capabilities.py (Boy Scout-reglen) som den sammenhængende
enhed, der læser workspace-guidance-dokumenter og udleder capability-sektioner,
summaries og runtime-records — inkl. execution-mode + approval-policy pr. sektion.

Ren læsning/parsing: ingen udførelse, ingen persistering. Afhænger af delte
konstanter (const), encryption-aware fil-I/O (wsio) og declaration-parserne
(workspace_capability_decl).

Alle funktioner re-eksporteres fra core.tools.workspace_capabilities for
bagudkompatibilitet.
"""
from __future__ import annotations

import re
from pathlib import Path

from core.tools.workspace_capabilities_const import (
    APPEND_DAILY_MEMORY_PREFIX,
    DELETE_MEMORY_LINE_PREFIX,
    EXEC_COMMAND_PREFIX,
    LIST_EXTERNAL_DIR_PREFIX,
    MULTI_READ_PREFIX,
    PROJECT_GREP_PREFIX,
    PROJECT_OUTLINE_PREFIX,
    PROPOSE_SOURCE_EDIT_PREFIX,
    READ_EXTERNAL_FILE_PREFIX,
    READ_FILE_PREFIX,
    REPLACE_MEMORY_LINE_PREFIX,
    REWRITE_MEMORY_FILE_PREFIX,
    RUNTIME_INSPECT_PREFIX,
    RUNTIME_NOTE_PREFIX,
    SEARCH_FILE_PREFIX,
    WRITE_EXTERNAL_FILE_PREFIX,
    WRITE_FILE_PREFIX,
    WRITE_MEMORY_FILE_PREFIX,
)
from core.tools.workspace_capabilities_wsio import _ws_path_exists, _ws_read_text
from core.tools.workspace_capability_decl import (
    _declared_exec_spec,
    _declared_external_file_spec,
    _declared_read_file_path,
    _declared_search_file_spec,
    _declared_write_target_path,
)


def _approval_policy_for_execution_mode(execution_mode: str) -> str:
    if execution_mode in {
        "inline-text",
        "workspace-file-read",
        "workspace-search-read",
        "external-file-read",
        "external-dir-list",
        "non-destructive-exec",
        "workspace-memory-write",
        "workspace-memory-replace",
        "workspace-memory-delete",
        "workspace-daily-memory-append",
        "autonomy-proposal-source-edit",
        "runtime-event-read",
        "project-grep",
        "multi-external-file-read",
        "project-outline",
    }:
        return "not-needed"
    if execution_mode in {
        "workspace-file-write",
        "workspace-memory-replace",
        "workspace-memory-delete",
        "workspace-memory-rewrite",
        "external-file-write",
        "workspace-file-delete",
        "delete-file",
        "git-mutate",
        "mutating-exec",
        "sudo-exec",
        "repo-update-check",
        "system-mutate",
        "package-mutate",
    }:
        return "required"
    return "not-applicable"


def _document_summary(path: Path, *, kind: str) -> dict[str, object]:
    if not _ws_path_exists(path):
        return {
            "path": str(path),
            "exists": False,
            "title": None,
            "has_text": False,
            "headings": [],
            "guidance_only": True,
            "authority": "workspace-guidance-only",
            "described_capabilities": [],
            "declared_capabilities": [],
        }

    lines = [line.strip() for line in (_ws_read_text(path) or "").splitlines()]
    headings = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    content_lines = [line for line in lines if line and not line.startswith("#")]
    # Bumped from 20 to 30 — 20 was hiding the new code-exploration
    # capabilities (grep-project, read-project-files, project-outline).
    described_capabilities = [
        _section_summary(section)
        for section in _document_sections(path, kind=kind)[:30]
    ]

    return {
        "path": str(path),
        "exists": True,
        "title": headings[0] if headings else None,
        "has_text": bool(content_lines),
        "headings": headings[1:8],
        "guidance_only": True,
        "authority": "workspace-guidance-only",
        "described_capabilities": described_capabilities,
        "declared_capabilities": described_capabilities,
    }


def _document_sections(path: Path, *, kind: str) -> list[dict[str, str]]:
    text = _ws_read_text(path)
    if text is None:
        return []

    sections: list[dict[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            if current_heading:
                sections.append(
                    {
                        "kind": kind,
                        "heading": current_heading,
                        "body": _normalize_body(current_lines),
                        "source_doc": path.name,
                    }
                )
            current_heading = line[3:].strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading:
        sections.append(
            {
                "kind": kind,
                "heading": current_heading,
                "body": _normalize_body(current_lines),
                "source_doc": path.name,
            }
        )
    return sections


def _document_section_by_id(path: Path, *, kind: str, capability_id: str) -> dict[str, str] | None:
    for section in _document_sections(path, kind=kind):
        if _section_summary(section)["capability_id"] == capability_id:
            return section
    return None


def _section_summary(section: dict[str, str]) -> dict[str, object]:
    heading = section["heading"]
    read_file_path = _declared_read_file_path(section["body"])
    search_spec = _declared_search_file_spec(section["body"])
    external_read_spec = _declared_external_file_spec(section["body"])
    external_read_path = external_read_spec["path"] if external_read_spec else None
    exec_spec = _declared_exec_spec(section["body"])
    write_target_path = _declared_write_target_path(section["body"])
    if heading.startswith(RUNTIME_NOTE_PREFIX):
        name = heading[len(RUNTIME_NOTE_PREFIX) :].strip()
        execution_mode = "inline-text"
        runnable = True
    elif heading.startswith(READ_FILE_PREFIX):
        name = heading[len(READ_FILE_PREFIX) :].strip()
        execution_mode = "workspace-file-read"
        runnable = read_file_path is not None
    elif heading.startswith(SEARCH_FILE_PREFIX):
        name = heading[len(SEARCH_FILE_PREFIX) :].strip()
        execution_mode = "workspace-search-read"
        runnable = search_spec is not None
    elif heading.startswith(READ_EXTERNAL_FILE_PREFIX):
        name = heading[len(READ_EXTERNAL_FILE_PREFIX) :].strip()
        execution_mode = "external-file-read"
        runnable = external_read_spec is not None
    elif heading.startswith(LIST_EXTERNAL_DIR_PREFIX):
        name = heading[len(LIST_EXTERNAL_DIR_PREFIX) :].strip()
        execution_mode = "external-dir-list"
        runnable = external_read_spec is not None
    elif heading.startswith(EXEC_COMMAND_PREFIX):
        name = heading[len(EXEC_COMMAND_PREFIX) :].strip()
        execution_mode = "non-destructive-exec"
        runnable = exec_spec is not None
    elif heading.startswith(WRITE_MEMORY_FILE_PREFIX):
        name = heading[len(WRITE_MEMORY_FILE_PREFIX) :].strip()
        execution_mode = "workspace-memory-write"
        runnable = write_target_path is not None
    elif heading.startswith(REPLACE_MEMORY_LINE_PREFIX):
        name = heading[len(REPLACE_MEMORY_LINE_PREFIX) :].strip()
        execution_mode = "workspace-memory-replace"
        runnable = write_target_path is not None
    elif heading.startswith(DELETE_MEMORY_LINE_PREFIX):
        name = heading[len(DELETE_MEMORY_LINE_PREFIX) :].strip()
        execution_mode = "workspace-memory-delete"
        runnable = write_target_path is not None
    elif heading.startswith(REWRITE_MEMORY_FILE_PREFIX):
        name = heading[len(REWRITE_MEMORY_FILE_PREFIX) :].strip()
        execution_mode = "workspace-memory-rewrite"
        runnable = write_target_path is not None
    elif heading.startswith(APPEND_DAILY_MEMORY_PREFIX):
        name = heading[len(APPEND_DAILY_MEMORY_PREFIX) :].strip()
        execution_mode = "workspace-daily-memory-append"
        runnable = True
    elif heading.startswith(PROPOSE_SOURCE_EDIT_PREFIX):
        name = heading[len(PROPOSE_SOURCE_EDIT_PREFIX) :].strip()
        execution_mode = "autonomy-proposal-source-edit"
        runnable = True
    elif heading.startswith(WRITE_FILE_PREFIX):
        name = heading[len(WRITE_FILE_PREFIX) :].strip()
        execution_mode = "workspace-file-write"
        runnable = False
    elif heading.startswith(WRITE_EXTERNAL_FILE_PREFIX):
        name = heading[len(WRITE_EXTERNAL_FILE_PREFIX) :].strip()
        execution_mode = "external-file-write"
        runnable = False
    elif heading.startswith(RUNTIME_INSPECT_PREFIX):
        name = heading[len(RUNTIME_INSPECT_PREFIX) :].strip()
        execution_mode = "runtime-event-read"
        runnable = True
    elif heading.startswith(PROJECT_GREP_PREFIX):
        name = heading[len(PROJECT_GREP_PREFIX) :].strip()
        execution_mode = "project-grep"
        runnable = True
    elif heading.startswith(MULTI_READ_PREFIX):
        name = heading[len(MULTI_READ_PREFIX) :].strip()
        execution_mode = "multi-external-file-read"
        runnable = True
    elif heading.startswith(PROJECT_OUTLINE_PREFIX):
        name = heading[len(PROJECT_OUTLINE_PREFIX) :].strip()
        execution_mode = "project-outline"
        runnable = True
    else:
        name = heading
        execution_mode = "declared-only"
        runnable = False
    return {
        "capability_id": f"{section['kind']}:{_slugify(name)}",
        "kind": section["kind"],
        "name": name,
        "source_doc": section["source_doc"],
        "guidance_only": True,
        "authority_source": "workspace-guidance",
        "runtime_authoritative": False,
        "runnable": runnable,
        "execution_mode": execution_mode,
        "status": "runnable" if runnable else "declared-only",
        "approval_policy": _approval_policy_for_execution_mode(
            execution_mode
        ),
        "approval_required": _approval_policy_for_execution_mode(
            execution_mode
        )
        == "required"
        or _approval_policy_for_execution_mode(execution_mode) == "required",
        "target_path": read_file_path or external_read_path or write_target_path,
        "target_path_source": (
            (external_read_spec or {}).get("path_source")
            if execution_mode in {"external-file-read", "external-dir-list"}
            else "declared-path"
        ),
        "command_text": (exec_spec or {}).get("command"),
        "command_source": (
            (exec_spec or {}).get("command_source")
            if execution_mode == "non-destructive-exec"
            else "declared-command"
        ),
        "target_query": search_spec["query"] if search_spec else None,
    }


def _runtime_capability_record(item: dict[str, object]) -> dict[str, object]:
    runnable = bool(item.get("runnable"))
    approval_required = bool(item.get("approval_required"))
    if runnable and not approval_required:
        runtime_status = "available"
    elif approval_required:
        runtime_status = "approval-required"
    elif str(item.get("execution_mode") or "") == "declared-only":
        runtime_status = "guidance-only"
    else:
        runtime_status = "unavailable"
    return {
        **item,
        "guidance_only": runtime_status == "guidance-only",
        "described_in_guidance": True,
        "authority_source": "runtime.workspace_capabilities",
        "runtime_authoritative": True,
        "runtime_status": runtime_status,
        "available_now": runtime_status == "available",
        "callable_now": runtime_status == "available",
    }


def _normalize_body(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    return text


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "unnamed"
