from __future__ import annotations

import re
import shlex
import subprocess
from hashlib import sha1
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.config import PROJECT_ROOT
from core.runtime.db import connect

# Delte konstanter (fil-navne, tekst-prefikser, output-grænser, exec-allowlists)
# er udskilt til workspace_capabilities_const.py (Boy Scout). Importér ind som
# den ene sandhed og re-eksportér for bagudkompatibilitet (blast 25).
from core.tools.workspace_capabilities_const import (  # noqa: F401
    APPEND_DAILY_MEMORY_PREFIX,
    APPROVED_MUTATING_EXEC_ALLOWLIST,
    APPROVED_SUDO_EXEC_ALLOWLIST,
    CAPABILITY_FILES,
    DELETE_MEMORY_LINE_PREFIX,
    EXEC_COMMAND_PREFIX,
    GIT_BLOCKED_SUBCOMMANDS,
    GIT_MUTATING_SUBCOMMANDS,
    GIT_READ_EXEC_ALLOWLIST,
    HARD_BLOCKED_EXEC_TOKENS,
    LIST_EXTERNAL_DIR_PREFIX,
    MAX_EXEC_OUTPUT_CHARS,
    MAX_EXEC_SECONDS,
    MAX_FILE_OUTPUT_CHARS,
    MAX_GREP_MATCH_CHARS,
    MAX_GREP_MATCHES,
    MAX_MATCH_EXCERPT_CHARS,
    MAX_MULTI_READ_CHARS,
    MAX_MULTI_READ_FILES,
    MAX_SEARCH_MATCHES,
    MULTI_READ_PREFIX,
    MUTATING_EXEC_PROPOSAL_TOKENS,
    NON_DESTRUCTIVE_EXEC_ALLOWLIST,
    NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS,
    NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS,
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

# Exec-kommando-klassifikation udskilt til workspace_capabilities_exec.py.
# Re-eksporteret for bagudkompatibilitet.
from core.tools.workspace_capabilities_exec import (  # noqa: F401
    _classify_cd_exec_command,
    _classify_exec_command,
    _classify_exec_command_no_shell,
    _classify_git_exec_command,
    _classify_git_mutation_subcommand,
    _classify_shell_composed_exec_command,
    _is_allowed_bounded_git_log_args,
    _mutating_exec_proposal_metadata,
    _normalize_exec_argv,
    _resolve_git_exec_context,
    _split_shell_exec_segments,
)

# Encryption-aware workspace-fil-I/O udskilt til workspace_capabilities_wsio.py.
from core.tools.workspace_capabilities_wsio import (  # noqa: F401
    _ws_path_exists,
    _ws_read_text,
    _ws_write_text,
)

# Workspace-dokument-parsing udskilt til workspace_capabilities_documents.py.
from core.tools.workspace_capabilities_documents import (  # noqa: F401
    _approval_policy_for_execution_mode,
    _document_section_by_id,
    _document_sections,
    _document_summary,
    _normalize_body,
    _runtime_capability_record,
    _section_summary,
    _slugify,
)

# Workspace-memory-fletning + støjfilter udskilt til
# workspace_capabilities_memory.py.
from core.tools.workspace_capabilities_memory import (  # noqa: F401
    _MEMORY_NOISE_LINE_PREFIXES,
    _MEMORY_NOISE_SUBSTRINGS,
    _is_durable_memory_line,
    _merge_workspace_memory_content,
)

# Rene result-/preview-helpers udskilt til workspace_capabilities_results.py.
from core.tools.workspace_capabilities_results import (  # noqa: F401
    _approval_result,
    _capability_status_family,
    _content_fingerprint,
    _default_capability_detail,
    _finalize_capability_result,
    _preview_text,
    _requires_capability_approval,
    _result_preview,
)

# Read-only capability-udførere udskilt til workspace_capabilities_execute.py.
from core.tools.workspace_capabilities_execute import (  # noqa: F401
    _execute_multi_file_read,
    _execute_project_grep,
    _execute_project_outline,
    _execute_runtime_event_read,
)

# Approval-verdicts + proposal/execution-content udskilt til
# workspace_capabilities_verdict.py.
from core.tools.workspace_capabilities_verdict import (  # noqa: F401
    _approved_mutating_exec_verdict,
    _approved_sudo_exec_verdict,
    _mutating_exec_execution_content,
    _mutating_exec_proposal_content,
    _resolve_target_path_for_sudo_exec,
    _sudo_exec_execution_content,
)

_LAST_CAPABILITY_INVOCATION: dict[str, object] | None = None


def load_workspace_capabilities(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    tools = _document_summary(workspace_dir / CAPABILITY_FILES["tools"], kind="tool")
    skills = _document_summary(workspace_dir / CAPABILITY_FILES["skills"], kind="skill")
    described_capabilities = [
        *tools["described_capabilities"],
        *skills["described_capabilities"],
    ]
    runtime_capabilities = [
        _runtime_capability_record(item)
        for item in described_capabilities
    ]
    available_now = [item for item in runtime_capabilities if item["available_now"]]
    approval_required = [
        item for item in runtime_capabilities if item["runtime_status"] == "approval-required"
    ]
    guidance_only = [
        item for item in runtime_capabilities if item["runtime_status"] == "guidance-only"
    ]
    unavailable = [
        item for item in runtime_capabilities if item["runtime_status"] == "unavailable"
    ]
    callable_capability_ids = [
        str(item.get("capability_id") or "")
        for item in available_now
        if str(item.get("capability_id") or "").strip()
    ]
    approval_gated_capability_ids = [
        str(item.get("capability_id") or "")
        for item in approval_required
        if str(item.get("capability_id") or "").strip()
    ]
    return {
        "workspace": str(workspace_dir),
        "name": name,
        "tools": tools,
        "skills": skills,
        "described_capabilities": described_capabilities,
        "declared_capabilities": described_capabilities,
        "runtime_capabilities": runtime_capabilities,
        "callable_capability_ids": callable_capability_ids,
        "approval_gated_capability_ids": approval_gated_capability_ids,
        "contract": {
            "mode": "text-capability-call",
            "visible_invocation_format": '<capability-call id="capability_id" />',
            "visible_invocation_with_args_format": (
                '<capability-call id="capability_id" arg_name="value" />'
            ),
            "visible_argument_binding": "in-tag-attributes",
            "visible_argument_fallback": "current-user-message-compatibility-only",
            "json_tool_call_supported": False,
            "provider_native_structured_tools": False,
            "summary": (
                "Visible lane uses text capability calls only. "
                "Arguments for arg-requiring capabilities bind in capability-call attributes. "
                "JSON tool-call payloads are not part of the contract."
            ),
        },
        "policy": {
            "workspace_read": "allowed",
            "workspace_write": "explicit-approval-required",
            "external_read": "allowed",
            "external_dir_list": "allowed",
            "non_destructive_exec": "allowed",
            "mutating_exec": "explicit-approval-required-bounded-non-sudo-only",
            "sudo_exec": "explicit-approval-required-bounded-allowlist-with-short-ttl-window",
            "external_write": "explicit-approval-required",
            "mutation_outside_workspace": "explicit-approval-required",
            "delete_exec": "not-executable-in-this-pass",
            "package_mutation_exec": "not-executable-in-this-pass",
            "principle": "Read freely. Inspect freely. Exec freely when non-destructive. Mutate only with explicit approval.",
        },
        "authority": {
            "authority_source": "runtime.workspace_capabilities",
            "guidance_sources": ["TOOLS.md", "SKILLS.md"],
            "runtime_authoritative": True,
            "guidance_only_docs": True,
            "summary": "Runtime capability truth is authoritative. TOOLS.md and SKILLS.md are workspace guidance only.",
            "described_count": len(described_capabilities),
            "runtime_count": len(runtime_capabilities),
            "available_now_count": len(available_now),
            "approval_required_count": len(approval_required),
            "guidance_only_count": len(guidance_only),
            "unavailable_count": len(unavailable),
        },
    }


_TOOL_PARAMETER_MAP: dict[str, dict[str, object]] = {
    "project-grep": {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Regex search pattern to find across all source files",
            },
        },
        "required": ["pattern"],
    },
    "multi-external-file-read": {
        "type": "object",
        "properties": {
            "paths": {
                "type": "string",
                "description": "Comma-separated absolute file paths to read",
            },
        },
    },
    "project-outline": {
        "type": "object",
        "properties": {
            "subdir": {
                "type": "string",
                "description": "Subdirectory relative to project root (e.g. core/ or apps/api/)",
            },
        },
    },
    "external-file-read": {
        "type": "object",
        "properties": {
            "target_path": {
                "type": "string",
                "description": "Absolute path to the file to read",
            },
        },
        "required": ["target_path"],
    },
    "external-dir-list": {
        "type": "object",
        "properties": {
            "target_path": {
                "type": "string",
                "description": "Absolute path to the directory to list",
            },
        },
        "required": ["target_path"],
    },
    "non-destructive-exec": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to run (read-only, non-destructive)",
            },
        },
        "required": ["command"],
    },
    "workspace-memory-write": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Full MEMORY.md content to write",
            },
        },
        "required": ["content"],
    },
    "workspace-memory-replace": {
        "type": "object",
        "properties": {
            "old_line": {
                "type": "string",
                "description": "Exact existing line to replace (starts with '- ')",
            },
            "new_line": {
                "type": "string",
                "description": "New line to replace it with (starts with '- ')",
            },
        },
        "required": ["old_line", "new_line"],
    },
    "workspace-memory-delete": {
        "type": "object",
        "properties": {
            "line": {
                "type": "string",
                "description": "Exact line to delete from MEMORY.md (starts with '- ')",
            },
        },
        "required": ["line"],
    },
}

_EXECUTION_MODE_TO_TOOL_NAME: dict[str, str] = {
    "project-grep": "grep_project",
    "multi-external-file-read": "read_multiple_files",
    "project-outline": "project_outline",
    "external-file-read": "read_file",
    "external-dir-list": "list_directory",
    "non-destructive-exec": "run_command",
    "workspace-file-read": "read_workspace_file",
    "workspace-search-read": "search_workspace",
    "workspace-memory-write": "write_memory",
    "workspace-memory-replace": "replace_memory_line",
    "workspace-memory-delete": "delete_memory_line",
    "workspace-daily-memory-append": "append_daily_memory",
    "runtime-event-read": "read_runtime_events",
    "autonomy-proposal-source-edit": "propose_source_edit",
}

_TOOL_NAME_TO_CAPABILITY_ID: dict[str, str] = {}


def build_ollama_tool_definitions(name: str = "default") -> list[dict]:
    """Build Ollama-compatible tool definitions from workspace capabilities."""
    caps = load_workspace_capabilities(name)
    tools: list[dict] = []
    seen_tool_names: set[str] = set()
    _TOOL_NAME_TO_CAPABILITY_ID.clear()
    for cap in caps["runtime_capabilities"]:
        if cap["runtime_status"] != "available":
            continue
        execution_mode = str(cap.get("execution_mode") or "")
        tool_name = _EXECUTION_MODE_TO_TOOL_NAME.get(execution_mode)
        if not tool_name or tool_name in seen_tool_names:
            continue
        seen_tool_names.add(tool_name)
        capability_id = str(cap.get("capability_id") or "")
        description = str(cap.get("name") or tool_name).strip()
        parameters = _TOOL_PARAMETER_MAP.get(execution_mode, {
            "type": "object",
            "properties": {},
        })
        tools.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": parameters,
            },
        })
        _TOOL_NAME_TO_CAPABILITY_ID[tool_name] = capability_id
    return tools


def resolve_tool_call_to_capability(
    tool_name: str,
    arguments: dict[str, object],
) -> dict[str, object]:
    """Map an Ollama tool_call back to capability invocation parameters."""
    capability_id = _TOOL_NAME_TO_CAPABILITY_ID.get(tool_name, "")
    command_text = (
        str(arguments.get("pattern") or "")
        or str(arguments.get("command") or "")
        or str(arguments.get("paths") or "")
        or str(arguments.get("subdir") or "")
        or str(arguments.get("old_line") or "")
        or str(arguments.get("line") or "")
    ).strip() or None
    target_path = str(arguments.get("target_path") or "").strip() or None
    write_content = str(arguments.get("content") or "").strip() or None
    return {
        "capability_id": capability_id,
        "command_text": command_text,
        "target_path": target_path,
        "write_content": write_content,
    }


def invoke_workspace_capability(
    capability_id: str,
    *,
    name: str = "default",
    run_id: str | None = None,
    approved: bool = False,
    write_content: str | None = None,
    target_path: str | None = None,
    command_text: str | None = None,
) -> dict[str, object]:
    invoked_at = _now()
    event_bus.publish(
        "runtime.capability_invocation_started",
        {
            "capability_id": capability_id,
            "invoked_at": invoked_at,
        },
    )
    workspace_dir = ensure_default_workspace(name=name)
    capabilities = load_workspace_capabilities(name=name)
    runtime_capabilities = capabilities.get("runtime_capabilities", [])
    capability = next(
        (
            item
            for item in runtime_capabilities
            if item.get("capability_id") == capability_id
        ),
        None,
    )

    if capability is not None:
        summary = dict(capability)
        if summary["runtime_status"] == "guidance-only":
            result = _finalize_capability_result({
                "capability": summary,
                "status": "not-runnable",
                "execution_mode": "guidance-only",
                "approval": _approval_result(summary, approved=approved, granted=False),
                "result": None,
                "detail": "Capability is described in workspace guidance only and is not runtime-executable.",
            })
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        if summary["runtime_status"] == "unavailable":
            result = _finalize_capability_result({
                "capability": summary,
                "status": "unavailable",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=approved, granted=False),
                "result": None,
                "detail": "Capability is known to runtime but is not currently available.",
            })
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        if summary["runtime_status"] == "approval-required" and not approved:
            proposal_content = _workspace_write_proposal_content(
                summary=summary,
                write_content=write_content,
            )
            result = _finalize_capability_result({
                "capability": summary,
                "status": "approval-required",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": proposal_content,
                "proposal_content": proposal_content,
                "detail": f"Capability requires explicit approval: {summary['execution_mode']}",
            })
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _persist_capability_approval_request(
                result,
                requested_at=invoked_at,
                run_id=run_id,
            )
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        if summary["runtime_status"] != "approval-required" and not summary["available_now"]:
            result = _finalize_capability_result({
                "capability": summary,
                "status": "unavailable",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=approved, granted=False),
                "result": None,
                "detail": "Capability is not currently available for execution.",
            })
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        section = _document_section_by_id(
            workspace_dir / CAPABILITY_FILES[f"{summary['kind']}s"],
            kind=str(summary["kind"]),
            capability_id=capability_id,
        )
        if section is None:
            result = _finalize_capability_result({
                "capability": summary,
                "status": "unavailable",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=approved, granted=False),
                "result": None,
                "detail": "Runtime capability is missing its source guidance section.",
            })
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        result = _finalize_capability_result(_invoke_runnable_capability(
            workspace_dir=workspace_dir,
            section=section,
            summary=summary,
            approved=approved,
            write_content=write_content,
            target_path=target_path,
            command_text=command_text,
        ))
        _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
        if str(result.get("status") or "") == "approval-required" and not approved:
            _persist_capability_approval_request(
                result,
                requested_at=invoked_at,
                run_id=run_id,
            )
        _publish_capability_invocation_completed(result, invoked_at=invoked_at)
        return result

    result = _finalize_capability_result({
        "capability": None,
        "status": "not-found",
        "execution_mode": "unsupported",
        "approval": {
            "policy": "not-applicable",
            "required": False,
            "approved": approved,
            "granted": False,
        },
        "result": None,
    })
    _set_last_capability_invocation(
        result,
        invoked_at=invoked_at,
        capability_id=capability_id,
        run_id=run_id,
    )
    _publish_capability_invocation_completed(
        result,
        invoked_at=invoked_at,
        capability_id=capability_id,
    )
    return result


def get_capability_invocation_truth() -> dict[str, object]:
    return {
        "active": False,
        "last_invocation": dict(_LAST_CAPABILITY_INVOCATION)
        if _LAST_CAPABILITY_INVOCATION
        else None,
    }


def _invoke_runnable_capability(
    *,
    workspace_dir: Path,
    section: dict[str, str],
    summary: dict[str, object],
    approved: bool = False,
    write_content: str | None = None,
    target_path: str | None = None,
    command_text: str | None = None,
) -> dict[str, object]:
    if summary["execution_mode"] == "inline-text":
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": {
                "type": "inline-text",
                "text": section["body"],
            },
        }

    if summary["execution_mode"] == "runtime-event-read":
        return _execute_runtime_event_read(summary)

    if summary["execution_mode"] == "project-grep":
        return _execute_project_grep(summary, command_text)

    if summary["execution_mode"] == "multi-external-file-read":
        return _execute_multi_file_read(summary, command_text, workspace_dir)

    if summary["execution_mode"] == "project-outline":
        return _execute_project_outline(summary, command_text)

    if summary["execution_mode"] == "workspace-file-read":
        target_path = str(summary.get("target_path") or "").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None or not candidate.exists() or not candidate.is_file():
            return {
                "capability": summary,
                "status": "executed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=True),
                "result": None,
                "detail": f"Declared workspace file missing: {target_path or 'unknown'}",
            }
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-file-read",
                "path": target_path,
                "text": _read_bounded_text(candidate),
            },
        }

    if summary["execution_mode"] == "workspace-search-read":
        target_path = str(summary.get("target_path") or "").strip()
        target_query = str(summary.get("target_query") or "").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None or not candidate.exists() or not candidate.is_file():
            return {
                "capability": summary,
                "status": "executed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=True),
                "result": None,
                "detail": f"Declared workspace file missing: {target_path or 'unknown'}",
            }
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": {
                "type": "workspace-search-read",
                "path": target_path,
                "query": target_query,
                "matches": _search_file_matches(candidate, target_query),
            },
        }

    if summary["execution_mode"] == "external-file-read":
        declared_target_path = str(summary.get("target_path") or "").strip()
        target_path_source = str(summary.get("target_path_source") or "").strip()
        resolved_target_path = (
            str(target_path or "").strip()
            if target_path_source == "invocation-argument"
            else declared_target_path
        )
        if not resolved_target_path:
            return {
                "capability": summary,
                "status": "blocked-missing-target-path",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": "External file read requires an explicit target_path.",
            }
        candidate = _resolve_external_path(workspace_dir, resolved_target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-invalid-target-path",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": f"Declared external file path is invalid: {resolved_target_path}",
            }
        if _is_within_workspace_root(workspace_dir, candidate):
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": (
                    "External file read is bounded to paths outside the active workspace root."
                ),
            }
        target_path = resolved_target_path
        if candidate is None or not candidate.exists() or not candidate.is_file():
            return {
                "capability": summary,
                "status": "executed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=True),
                "result": None,
                "detail": f"Declared external file missing: {target_path or 'unknown'}",
            }
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": {
                "type": "external-file-read",
                "path": str(candidate),
                "text": _read_bounded_text(candidate),
                "target_source": target_path_source or "declared-path",
                "workspace_scoped": False,
            },
        }

    if summary["execution_mode"] == "external-dir-list":
        declared_target_path = str(summary.get("target_path") or "").strip()
        target_path_source = str(summary.get("target_path_source") or "").strip()
        resolved_target_path = (
            str(target_path or "").strip()
            if target_path_source == "invocation-argument"
            else declared_target_path
        )
        if not resolved_target_path:
            return {
                "capability": summary,
                "status": "blocked-missing-target-path",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": "External directory list requires an explicit target_path.",
            }
        candidate = _resolve_external_path(workspace_dir, resolved_target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-invalid-target-path",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": f"Declared external directory path is invalid: {resolved_target_path}",
            }
        if not candidate.exists() or not candidate.is_dir():
            return {
                "capability": summary,
                "status": "executed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=True),
                "result": None,
                "detail": f"External directory not found or not a directory: {resolved_target_path}",
            }
        try:
            entries = sorted(candidate.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            lines: list[str] = []
            for entry in entries[:100]:
                kind = "d" if entry.is_dir() else "f"
                lines.append(f"[{kind}] {entry.name}")
            listing = "\n".join(lines)
            if len(listing) > MAX_FILE_OUTPUT_CHARS:
                listing = listing[:MAX_FILE_OUTPUT_CHARS] + "\n…"
        except PermissionError:
            return {
                "capability": summary,
                "status": "blocked-permission-denied",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": f"Permission denied listing directory: {resolved_target_path}",
            }
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": {
                "type": "external-dir-list",
                "path": str(candidate),
                "text": listing,
                "entry_count": len(entries),
                "target_source": target_path_source or "declared-path",
                "workspace_scoped": False,
            },
        }

    if summary["execution_mode"] == "non-destructive-exec":
        declared_command = str(summary.get("command_text") or "").strip()
        command_source = str(summary.get("command_source") or "").strip()
        resolved_command = (
            str(command_text or "").strip()
            if command_source == "invocation-argument"
            else declared_command
        )
        if not resolved_command:
            return {
                "capability": summary,
                "status": "blocked-missing-command",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": "Non-destructive exec requires one explicit command_text.",
            }
        command_verdict = _classify_exec_command(resolved_command)
        if command_verdict.get("proposal_required"):
            if approved:
                execution_mode = (
                    "sudo-exec"
                    if bool(command_verdict.get("requires_sudo", False))
                    else "mutating-exec"
                )
                approved_verdict = (
                    _approved_sudo_exec_verdict(
                        command_verdict,
                        workspace_dir=workspace_dir,
                    )
                    if execution_mode == "sudo-exec"
                    else _approved_mutating_exec_verdict(command_verdict)
                )
                if not approved_verdict.get("allowed"):
                    return {
                        "capability": summary,
                        "status": str(
                            approved_verdict.get("status")
                            or "blocked-approved-mutating-exec"
                        ),
                        "execution_mode": str(
                            command_verdict.get("proposal_execution_mode")
                            or "mutating-exec-proposal"
                        ),
                        "approval": {
                            "policy": "required",
                            "required": True,
                            "approved": True,
                            "granted": False,
                        },
                        "result": None,
                        "proposal_content": _mutating_exec_proposal_content(
                            command_text=resolved_command,
                            command_source=command_source or "declared-command",
                            classification=command_verdict,
                        ),
                        "detail": str(
                            approved_verdict.get("detail")
                            or "Approved mutating exec remains blocked in this pass."
                        ),
                    }
                argv = list(
                    approved_verdict.get("argv")
                    or command_verdict.get("argv")
                    or []
                )
                execution_cwd = Path(
                    approved_verdict.get("execution_cwd")
                    or command_verdict.get("execution_cwd")
                    or workspace_dir
                )
                completed, timeout_detail = _run_bounded_command(
                    argv=argv,
                    workspace_dir=execution_cwd,
                )
                if completed is None:
                    execution_content = (
                        _sudo_exec_execution_content(
                            command_text=resolved_command,
                            command_source=command_source or "declared-command",
                            classification=command_verdict,
                            exit_code=None,
                            output_text="",
                        )
                        if execution_mode == "sudo-exec"
                        else _mutating_exec_execution_content(
                            command_text=resolved_command,
                            command_source=command_source or "declared-command",
                            classification=command_verdict,
                            exit_code=None,
                            output_text="",
                        )
                    )
                    return {
                        "capability": summary,
                        "status": "blocked-timeout",
                        "execution_mode": execution_mode,
                        "approval": {
                            "policy": "required",
                            "required": True,
                            "approved": True,
                            "granted": False,
                        },
                        "result": None,
                        "proposal_content": execution_content,
                        "detail": timeout_detail,
                    }
                output_text = _bounded_exec_output(
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                )
                execution_content = (
                    _sudo_exec_execution_content(
                        command_text=resolved_command,
                        command_source=command_source or "declared-command",
                        classification=command_verdict,
                        exit_code=completed.returncode,
                        output_text=output_text,
                    )
                    if execution_mode == "sudo-exec"
                    else _mutating_exec_execution_content(
                        command_text=resolved_command,
                        command_source=command_source or "declared-command",
                        classification=command_verdict,
                        exit_code=completed.returncode,
                        output_text=output_text,
                    )
                )
                return {
                    "capability": summary,
                    "status": "executed",
                    "execution_mode": execution_mode,
                    "approval": {
                        "policy": "required",
                        "required": True,
                        "approved": True,
                        "granted": True,
                    },
                    "result": {
                        "type": execution_mode,
                        "command_text": resolved_command,
                        "normalized_command_text": str(
                            command_verdict.get("normalized_command_text")
                            or resolved_command
                        ),
                        "argv": argv,
                        "exit_code": completed.returncode,
                        "text": output_text,
                        "command_source": command_source or "declared-command",
                        "path_normalization_applied": bool(
                            command_verdict.get("path_normalization_applied", False)
                        ),
                        "normalization_source": str(
                            command_verdict.get("normalization_source") or "none"
                        ),
                        "execution_scope": str(
                            command_verdict.get("execution_scope") or "filesystem"
                        ),
                        "execution_classification": str(
                            command_verdict.get("execution_classification")
                            or execution_mode
                        ),
                        "workspace_scoped": bool(
                            approved_verdict.get("workspace_scoped", False)
                        ),
                        "repo_scoped": bool(
                            approved_verdict.get("repo_scoped", False)
                            or command_verdict.get("repo_scoped", False)
                        ),
                        "mutation_permitted": True,
                        "sudo_permitted": execution_mode == "sudo-exec",
                        "external_mutation_permitted": bool(
                            approved_verdict.get("external_mutation_permitted", True)
                        ),
                        "delete_permitted": False,
                        "scope": str(
                            command_verdict.get("proposal_scope") or "filesystem"
                        ),
                        "matched_token": str(
                            command_verdict.get("matched_token") or "unknown"
                        ),
                        "command_fingerprint": execution_content.get("fingerprint") or "",
                        "proposal_only": False,
                        "not_executed": False,
                    },
                    "proposal_content": execution_content,
                    "detail": (
                        (
                            "Approved bounded sudo exec completed."
                            if execution_mode == "sudo-exec"
                            else "Approved bounded non-sudo mutating exec completed."
                        )
                        if completed.returncode == 0
                        else (
                            "Approved bounded sudo exec exited non-zero."
                            if execution_mode == "sudo-exec"
                            else "Approved bounded non-sudo mutating exec exited non-zero."
                        )
                    ),
                }
            proposal_content = _mutating_exec_proposal_content(
                command_text=resolved_command,
                command_source=command_source or "declared-command",
                classification=command_verdict,
            )
            return {
                "capability": summary,
                "status": "approval-required",
                "execution_mode": str(
                    command_verdict.get("proposal_execution_mode")
                    or "mutating-exec-proposal"
                ),
                "approval": {
                    "policy": "required",
                    "required": True,
                    "approved": approved,
                    "granted": False,
                },
                "result": proposal_content,
                "proposal_content": proposal_content,
                "detail": str(
                    command_verdict.get("detail")
                    or "Mutating exec remains proposal-only until explicitly approved."
                ),
            }
        if not command_verdict["allowed"]:
            return {
                "capability": summary,
                "status": str(command_verdict.get("status") or "blocked-command"),
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": str(command_verdict.get("detail") or "Command is not allowed."),
            }
        argv = list(command_verdict.get("argv") or [])
        execution_cwd = Path(command_verdict.get("execution_cwd") or workspace_dir)
        if bool(command_verdict.get("shell_mode")):
            completed, timeout_detail = _run_bounded_shell_command(
                command_text=resolved_command,
                workspace_dir=execution_cwd,
            )
        else:
            completed, timeout_detail = _run_bounded_command(
                argv=argv,
                workspace_dir=execution_cwd,
            )
        if completed is None:
            return {
                "capability": summary,
                "status": "blocked-timeout",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": timeout_detail,
            }
        output_text = _bounded_exec_output(
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=False, granted=True),
            "result": {
                "type": "non-destructive-exec",
                "command_text": resolved_command,
                "normalized_command_text": str(
                    command_verdict.get("normalized_command_text")
                    or resolved_command
                ),
                "argv": argv,
                "shell_mode": bool(command_verdict.get("shell_mode")),
                "shell_segments": list(command_verdict.get("shell_segments") or []),
                "exit_code": completed.returncode,
                "text": output_text,
                "command_source": command_source or "declared-command",
                "path_normalization_applied": bool(
                    command_verdict.get("path_normalization_applied", False)
                ),
                "normalization_source": str(
                    command_verdict.get("normalization_source") or "none"
                ),
                "execution_scope": str(
                    command_verdict.get("execution_scope") or "filesystem"
                ),
                "execution_classification": str(
                    command_verdict.get("execution_classification")
                    or "non-destructive-read-allowed"
                ),
                "workspace_scoped": False,
                "repo_scoped": bool(command_verdict.get("repo_scoped", False)),
                "mutation_permitted": False,
                "sudo_permitted": False,
            },
        }

    if summary["execution_mode"] == "workspace-memory-write":
        target_path = str(summary.get("target_path") or "MEMORY.md").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Memory write target is outside workspace scope: {target_path}. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        _MEMORY_WRITE_ALLOWED_FILES = {"MEMORY.md", "USER.md"}
        if candidate.name not in _MEMORY_WRITE_ALLOWED_FILES:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"workspace-memory-write is only allowed for {', '.join(sorted(_MEMORY_WRITE_ALLOWED_FILES))}. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        if write_content is None:
            return {
                "capability": summary,
                "status": "blocked-missing-write-content",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory write requires explicit write_content. Use block syntax: <capability-call id=\"tool:write-workspace-memory\">\\n# MEMORY\\n(full content)\\n</capability-call>",
            }
        candidate.parent.mkdir(parents=True, exist_ok=True)
        existing_content = _ws_read_text(candidate) or ""
        existing_fingerprint = (
            _content_fingerprint(existing_content) if existing_content else ""
        )
        existing_bytes = len(existing_content.encode("utf-8"))
        merged_content = _merge_workspace_memory_content(
            existing_content=existing_content,
            incoming_content=write_content,
        )
        _ws_write_text(candidate, merged_content)
        # Read-back verification: re-read the file from disk so we can
        # confirm the bytes Jarvis sees actually match what was written.
        # If the readback differs (filesystem race, encoding issue,
        # external mutation), we surface that explicitly so Jarvis is
        # not lied to about persistence success.
        try:
            readback_content = _ws_read_text(candidate) or ""
        except Exception:
            readback_content = ""
        readback_fingerprint = (
            _content_fingerprint(readback_content) if readback_content else ""
        )
        merged_fingerprint = _content_fingerprint(merged_content)
        readback_match = bool(
            readback_fingerprint
            and readback_fingerprint == merged_fingerprint
        )
        merged_bytes = len(merged_content.encode("utf-8"))
        bytes_delta = merged_bytes - existing_bytes
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-memory-write",
                "path": target_path,
                "resolved_path": str(candidate.resolve()),
                "workspace_relative_path": target_path,
                "workspace_root": str(workspace_dir.resolve()),
                "bytes_written": merged_bytes,
                "bytes_before": existing_bytes,
                "bytes_delta": bytes_delta,
                "text": _preview_text(
                    merged_content,
                    limit=min(MAX_FILE_OUTPUT_CHARS, 400),
                ),
                "content_after": merged_content,
                "content_before": existing_content,
                "content_fingerprint": merged_fingerprint,
                "content_fingerprint_before": existing_fingerprint,
                "readback_fingerprint": readback_fingerprint,
                "readback_match": readback_match,
                "content_source": "explicit-write-content-merged",
                "workspace_scoped": True,
            },
            "detail": (
                f"Memory write executed for {target_path} at {candidate.resolve()}. "
                f"{bytes_delta:+d} bytes, "
                f"readback={'verified' if readback_match else 'MISMATCH'}. "
                f"Review 'content_before' to see what existed before this write — "
                f"check for semantic duplicates and use workspace-memory-rewrite if cleanup is needed."
            ),
        }

    if summary["execution_mode"] == "workspace-daily-memory-append":
        # Daily memory is Jarvis' own territory — no approval needed.
        # The note comes from either write_content (block syntax) or
        # from an inline user_message arg.
        note_text = ""
        if write_content is not None:
            note_text = str(write_content).strip()
        if not note_text:
            raw_args = summary.get("arguments") or {}
            if isinstance(raw_args, dict):
                note_text = str(raw_args.get("note") or raw_args.get("text") or "").strip()
        if not note_text:
            return {
                "capability": summary,
                "status": "blocked-missing-note",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    "Daily memory append requires explicit note text in the capability body. "
                    f"Active workspace root: {workspace_dir.resolve()}. "
                    f"Expected daily target: {(workspace_dir / 'memory' / 'daily' / (datetime.now(UTC).date().isoformat() + '.md')).resolve()}"
                ),
            }
        # Bounded: one line, ~240 chars max
        note_text = " ".join(note_text.split())
        if len(note_text) > 240:
            note_text = note_text[:239].rstrip() + "…"
        expected_daily_path = (
            workspace_dir / "memory" / "daily" / f"{datetime.now(UTC).date().isoformat()}.md"
        )
        daily_path: Path | None = None
        recent_lines: list[str] = []
        try:
            from core.identity.workspace_bootstrap import (
                append_daily_memory_note,
                read_daily_memory_lines,
            )
            daily_path = append_daily_memory_note(note_text, source="jarvis")
            recent_lines = read_daily_memory_lines(limit=6)
        except Exception as exc:
            return {
                "capability": summary,
                "status": "executed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=True),
                "result": {
                    "type": "workspace-daily-memory-append",
                    "path": str(expected_daily_path),
                    "resolved_path": str(expected_daily_path.resolve()),
                    "workspace_relative_path": str(expected_daily_path.relative_to(workspace_dir)),
                    "workspace_root": str(workspace_dir.resolve()),
                    "note": note_text,
                    "recent_lines": [],
                    "workspace_scoped": True,
                    "persisted": False,
                    "degraded_reason": str(exc),
                },
                "detail": (
                    f"Daily memory note could not be persisted to {expected_daily_path.resolve()}: {exc}"
                ),
            }
        if daily_path is None:
            return {
                "capability": summary,
                "status": "executed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=True),
                "result": {
                    "type": "workspace-daily-memory-append",
                    "path": str(expected_daily_path),
                    "resolved_path": str(expected_daily_path.resolve()),
                    "workspace_relative_path": str(expected_daily_path.relative_to(workspace_dir)),
                    "workspace_root": str(workspace_dir.resolve()),
                    "note": note_text,
                    "recent_lines": recent_lines[-6:],
                    "workspace_scoped": True,
                    "persisted": False,
                    "degraded_reason": "append-returned-no-path",
                },
                "detail": (
                    f"Daily memory note was accepted but could not be persisted to {expected_daily_path.resolve()}."
                ),
            }
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-daily-memory-append",
                "path": str(daily_path) if daily_path else "",
                "resolved_path": str(Path(daily_path).resolve()) if daily_path else "",
                "workspace_relative_path": (
                    str(Path(daily_path).resolve().relative_to(workspace_dir.resolve()))
                    if daily_path else ""
                ),
                "workspace_root": str(workspace_dir.resolve()),
                "note": note_text,
                "recent_lines": recent_lines[-6:],
                "workspace_scoped": True,
                "persisted": True,
            },
            "detail": (
                f"Daily memory note appended ({len(note_text)} chars) to "
                f"{Path(daily_path).resolve() if daily_path else (workspace_dir / 'memory' / 'daily').resolve()}."
            ),
        }

    if summary["execution_mode"] == "workspace-memory-replace":
        target_path = str(summary.get("target_path") or "MEMORY.md").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Memory replace target is outside workspace scope: {target_path}. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        if candidate.name != "MEMORY.md":
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    "workspace-memory-replace is only allowed for MEMORY.md. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        old_line = " ".join(str(command_text or "").split()).strip()
        new_line = " ".join(str(write_content or "").split()).strip()
        if not old_line or not new_line:
            return {
                "capability": summary,
                "status": "blocked-missing-replace-content",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    "Memory replace requires command_text with the exact old durable line "
                    "and write_content with the exact new durable line."
                ),
            }
        if old_line == new_line:
            return {
                "capability": summary,
                "status": "blocked-noop",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory replace old and new lines are identical.",
            }
        if not old_line.startswith("- ") or not _is_durable_memory_line(old_line):
            return {
                "capability": summary,
                "status": "blocked-invalid-replace-old-line",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory replace only supports exact durable bullet lines from MEMORY.md.",
            }
        if not new_line.startswith("- ") or not _is_durable_memory_line(new_line):
            return {
                "capability": summary,
                "status": "blocked-invalid-replace-new-line",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory replace new line must be a single durable bullet line.",
            }
        if not _ws_path_exists(candidate):
            return {
                "capability": summary,
                "status": "blocked-missing-target-file",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"Memory replace target file does not exist: {candidate.resolve()}",
            }
        existing_content = _ws_read_text(candidate) or ""
        existing_lines = existing_content.splitlines()
        match_indexes = [
            index
            for index, line in enumerate(existing_lines)
            if line.strip() == old_line
        ]
        if not match_indexes:
            return {
                "capability": summary,
                "status": "blocked-no-match",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Memory replace could not find the exact line in {candidate.resolve()}: {old_line}"
                ),
            }
        updated_lines = [
            new_line if line.strip() == old_line else line
            for line in existing_lines
        ]
        updated_content = "\n".join(updated_lines).rstrip() + "\n"
        existing_bytes = len(existing_content.encode("utf-8"))
        _ws_write_text(candidate, updated_content)
        try:
            readback_content = _ws_read_text(candidate) or ""
        except Exception:
            readback_content = ""
        new_fingerprint = _content_fingerprint(updated_content)
        readback_fingerprint = _content_fingerprint(readback_content) if readback_content else ""
        readback_match = bool(readback_fingerprint and readback_fingerprint == new_fingerprint)
        new_bytes = len(updated_content.encode("utf-8"))
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-memory-replace",
                "path": target_path,
                "resolved_path": str(candidate.resolve()),
                "workspace_relative_path": target_path,
                "workspace_root": str(workspace_dir.resolve()),
                "match_count": len(match_indexes),
                "old_line": _preview_text(old_line, limit=160),
                "new_line": _preview_text(new_line, limit=160),
                "bytes_written": new_bytes,
                "bytes_before": existing_bytes,
                "bytes_delta": new_bytes - existing_bytes,
                "readback_match": readback_match,
                "content_fingerprint": new_fingerprint,
            },
            "detail": (
                f"Memory replace executed for {len(match_indexes)} exact line(s) in {candidate.resolve()}."
            ),
        }

    if summary["execution_mode"] == "workspace-memory-delete":
        target_path = str(summary.get("target_path") or "MEMORY.md").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Memory delete target is outside workspace scope: {target_path}. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        if candidate.name != "MEMORY.md":
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    "workspace-memory-delete is only allowed for MEMORY.md. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        delete_line = " ".join(str(command_text or "").split()).strip()
        if not delete_line:
            return {
                "capability": summary,
                "status": "blocked-missing-delete-line",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory delete requires command_text with the exact durable line to remove.",
            }
        if not delete_line.startswith("- ") or not _is_durable_memory_line(delete_line):
            return {
                "capability": summary,
                "status": "blocked-invalid-delete-line",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory delete only supports exact durable bullet lines from MEMORY.md.",
            }
        if not _ws_path_exists(candidate):
            return {
                "capability": summary,
                "status": "blocked-missing-target-file",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"Memory delete target file does not exist: {candidate.resolve()}",
            }
        existing_content = _ws_read_text(candidate) or ""
        existing_lines = existing_content.splitlines()
        kept_lines = [line for line in existing_lines if line.strip() != delete_line]
        match_count = len(existing_lines) - len(kept_lines)
        if match_count <= 0:
            return {
                "capability": summary,
                "status": "blocked-no-match",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Memory delete could not find the exact line in {candidate.resolve()}: {delete_line}"
                ),
            }
        updated_content = "\n".join(kept_lines).rstrip() + "\n"
        existing_bytes = len(existing_content.encode("utf-8"))
        _ws_write_text(candidate, updated_content)
        try:
            readback_content = _ws_read_text(candidate) or ""
        except Exception:
            readback_content = ""
        new_fingerprint = _content_fingerprint(updated_content)
        readback_fingerprint = _content_fingerprint(readback_content) if readback_content else ""
        readback_match = bool(readback_fingerprint and readback_fingerprint == new_fingerprint)
        new_bytes = len(updated_content.encode("utf-8"))
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-memory-delete",
                "path": target_path,
                "resolved_path": str(candidate.resolve()),
                "workspace_relative_path": target_path,
                "workspace_root": str(workspace_dir.resolve()),
                "match_count": match_count,
                "deleted_line": _preview_text(delete_line, limit=160),
                "bytes_written": new_bytes,
                "bytes_before": existing_bytes,
                "bytes_delta": new_bytes - existing_bytes,
                "readback_match": readback_match,
                "content_fingerprint": new_fingerprint,
            },
            "detail": (
                f"Memory delete executed for {match_count} exact line(s) in {candidate.resolve()}."
            ),
        }

    if summary["execution_mode"] == "workspace-memory-rewrite":
        target_path = str(summary.get("target_path") or "MEMORY.md").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Memory rewrite target is outside workspace scope: {target_path}. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        _MEMORY_REWRITE_ALLOWED_FILES = {"MEMORY.md", "USER.md"}
        if candidate.name not in _MEMORY_REWRITE_ALLOWED_FILES:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"workspace-memory-rewrite is only allowed for {', '.join(sorted(_MEMORY_REWRITE_ALLOWED_FILES))}. "
                    f"Active workspace root: {workspace_dir.resolve()}"
                ),
            }
        if not approved:
            return {
                "capability": summary,
                "status": "blocked-needs-approval",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": "Memory rewrite requires explicit Bjørn approval — call again with approved=True.",
            }
        if write_content is None:
            return {
                "capability": summary,
                "status": "blocked-missing-write-content",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Memory rewrite requires explicit write_content with the FULL new file contents.",
            }
        # Filter the incoming content through the durable-only line
        # filter so even an approved rewrite cannot inject session
        # noise into long-term memory.
        filtered_lines: list[str] = []
        rejected_lines: list[str] = []
        for line in str(write_content).splitlines():
            if _is_durable_memory_line(line):
                filtered_lines.append(line)
            else:
                rejected_lines.append(line)
        filtered_content = "\n".join(filtered_lines).rstrip() + "\n"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        existing_content = _ws_read_text(candidate) or ""
        existing_fingerprint = _content_fingerprint(existing_content) if existing_content else ""
        existing_bytes = len(existing_content.encode("utf-8"))
        _ws_write_text(candidate, filtered_content)
        try:
            readback_content = _ws_read_text(candidate) or ""
        except Exception:
            readback_content = ""
        new_fingerprint = _content_fingerprint(filtered_content)
        readback_fingerprint = _content_fingerprint(readback_content) if readback_content else ""
        readback_match = bool(readback_fingerprint and readback_fingerprint == new_fingerprint)
        new_bytes = len(filtered_content.encode("utf-8"))
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-memory-rewrite",
                "path": target_path,
                "resolved_path": str(candidate.resolve()),
                "workspace_relative_path": target_path,
                "workspace_root": str(workspace_dir.resolve()),
                "bytes_written": new_bytes,
                "bytes_before": existing_bytes,
                "bytes_delta": new_bytes - existing_bytes,
                "lines_kept": len(filtered_lines),
                "lines_rejected": len(rejected_lines),
                "rejected_sample": [line[:120] for line in rejected_lines[:5]],
                "text": _preview_text(
                    filtered_content,
                    limit=min(MAX_FILE_OUTPUT_CHARS, 600),
                ),
                "content_fingerprint": new_fingerprint,
                "content_fingerprint_before": existing_fingerprint,
                "readback_fingerprint": readback_fingerprint,
                "readback_match": readback_match,
                "content_source": "explicit-rewrite-content-filtered",
                "workspace_scoped": True,
            },
            "detail": (
                f"Memory rewrite executed for {target_path} at {candidate.resolve()}. "
                f"{new_bytes - existing_bytes:+d} bytes, "
                f"{len(filtered_lines)} lines kept, "
                f"{len(rejected_lines)} noise lines rejected, "
                f"readback={'verified' if readback_match else 'MISMATCH'}."
            ),
        }

    if summary["execution_mode"] == "autonomy-proposal-source-edit":
        # Niveau 2 autonomy: Jarvis files a source-edit proposal that
        # waits for Bjørn approval. The capability itself does NOT
        # mutate any source — it just enqueues the request. Approval
        # + execution happen via the autonomy_proposal_queue service.
        raw_args = summary.get("arguments") or {}
        if not isinstance(raw_args, dict):
            raw_args = {}
        target_path_arg = str(
            target_path
            or raw_args.get("target_path")
            or raw_args.get("path")
            or ""
        ).strip()
        base_fingerprint = str(raw_args.get("base_fingerprint") or "").strip()
        rationale = str(raw_args.get("rationale") or "").strip()
        new_content = str(write_content or "")
        if not target_path_arg:
            return {
                "capability": summary,
                "status": "blocked-missing-target",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "tool:propose-source-edit requires target_path attribute on the capability call.",
            }
        if not new_content:
            return {
                "capability": summary,
                "status": "blocked-missing-write-content",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "tool:propose-source-edit requires the FULL new file contents in the capability body.",
            }
        # Path safety: must exist, must be under PROJECT_ROOT, must
        # have an allowed extension, must not be in a forbidden path.
        from pathlib import Path as _Path
        try:
            resolved = _Path(target_path_arg).resolve()
            project_root = _Path(PROJECT_ROOT).resolve()
            resolved.relative_to(project_root)
        except (ValueError, OSError):
            return {
                "capability": summary,
                "status": "blocked-out-of-scope",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"target_path must be inside the repo: {target_path_arg}",
            }
        forbidden_segments = {".git", ".claude", "node_modules", "__pycache__"}
        forbidden_subpaths = ("workspace/default/runtime",)
        rel_str = str(resolved.relative_to(project_root))
        if any(seg in resolved.parts for seg in forbidden_segments):
            return {
                "capability": summary,
                "status": "blocked-forbidden-path",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"target_path is in a forbidden directory: {rel_str}",
            }
        if any(rel_str.startswith(sub) for sub in forbidden_subpaths):
            return {
                "capability": summary,
                "status": "blocked-forbidden-path",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"target_path is in a forbidden subpath: {rel_str}",
            }
        allowed_exts = {
            ".py", ".md", ".json", ".yaml", ".yml",
            ".ts", ".tsx", ".jsx", ".js",
            ".css", ".html", ".toml", ".txt",
        }
        if resolved.suffix.lower() not in allowed_exts:
            return {
                "capability": summary,
                "status": "blocked-extension",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"target_path extension {resolved.suffix} not in allowed set",
            }
        if not resolved.exists() or not resolved.is_file():
            return {
                "capability": summary,
                "status": "blocked-not-found",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"target_path does not exist: {rel_str}",
            }
        # Compute current disk fingerprint and the new fingerprint;
        # we surface both so MC can render a diff later. We do NOT
        # require base_fingerprint to match here — that check happens
        # at execute time so the proposal can survive Bjørn pondering
        # for a while. We just record the base.
        try:
            current_content = resolved.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return {
                "capability": summary,
                "status": "blocked-read-failed",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"Could not read target file: {exc}",
            }
        current_fingerprint = _content_fingerprint(current_content)
        new_fingerprint = _content_fingerprint(new_content)
        if new_fingerprint == current_fingerprint:
            return {
                "capability": summary,
                "status": "blocked-no-op",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Proposed content is identical to current file content — no edit needed.",
            }
        # File the proposal
        try:
            from core.services.autonomy_proposal_queue import (
                file_proposal,
            )
            proposal = file_proposal(
                kind="source-edit",
                title=f"Edit {rel_str}",
                rationale=rationale or "(no rationale provided)",
                payload={
                    "target_path": str(resolved),
                    "relative_path": rel_str,
                    "base_fingerprint": base_fingerprint or current_fingerprint,
                    "current_fingerprint_at_filing": current_fingerprint,
                    "new_fingerprint": new_fingerprint,
                    "new_content": new_content,
                    "bytes_before": len(current_content.encode("utf-8")),
                    "bytes_after": len(new_content.encode("utf-8")),
                    "bytes_delta": len(new_content.encode("utf-8")) - len(current_content.encode("utf-8")),
                },
                created_by="visible-capability",
            )
        except Exception as exc:
            return {
                "capability": summary,
                "status": "error",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"Failed to file source-edit proposal: {exc}",
            }
        proposal_id = str(proposal.get("proposal_id") or "")
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "autonomy-proposal-source-edit",
                "proposal_id": proposal_id,
                "kind": "source-edit",
                "target_path": rel_str,
                "current_fingerprint": current_fingerprint,
                "new_fingerprint": new_fingerprint,
                "bytes_delta": len(new_content.encode("utf-8")) - len(current_content.encode("utf-8")),
                "status": "pending",
                "workspace_scoped": False,
            },
            "detail": (
                f"Source-edit proposal filed: {proposal_id} for {rel_str} "
                f"({len(new_content.encode('utf-8')) - len(current_content.encode('utf-8')):+d} bytes). "
                "Awaiting Bjørn approval."
            ),
        }

    if summary["execution_mode"] == "workspace-file-write":
        target_path = str(summary.get("target_path") or "").strip()
        candidate = _resolve_workspace_relative_path(workspace_dir, target_path)
        if candidate is None:
            return {
                "capability": summary,
                "status": "blocked-scope-mismatch",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": (
                    f"Declared workspace write target is outside workspace scope: {target_path or 'unknown'}"
                ),
            }
        if write_content is None:
            return {
                "capability": summary,
                "status": "blocked-missing-write-content",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": "Approved workspace write execution requires explicit write_content.",
            }
        candidate.parent.mkdir(parents=True, exist_ok=True)
        _ws_write_text(candidate, write_content)
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "approval": _approval_result(summary, approved=True, granted=True),
            "result": {
                "type": "workspace-file-write",
                "path": target_path,
                "bytes_written": len(write_content.encode("utf-8")),
                "text": _preview_text(
                    write_content,
                    limit=min(MAX_FILE_OUTPUT_CHARS, 400),
                ),
                "content_fingerprint": _content_fingerprint(write_content),
                "content_source": "explicit-write-content",
                "workspace_scoped": True,
            },
            "proposal_content": _workspace_write_proposal_content(
                summary=summary,
                write_content=write_content,
            ),
            "detail": f"Approved workspace write executed for {target_path}.",
        }

    return {
        "capability": summary,
        "status": "not-runnable",
        "execution_mode": str(summary.get("execution_mode", "declared-only")),
        "approval": _approval_result(summary, approved=False, granted=False),
        "result": None,
    }


def classify_workspace_execution_mode(execution_mode: str) -> dict[str, object]:
    normalized = str(execution_mode or "declared-only").strip().lower()
    if normalized in {
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
        "guidance-only",
        "declared-only",
        "unsupported",
    }:
        return {
            "classification": "read-only",
            "mutation_near": False,
            "sudo_required": False,
            "mutation_critical": False,
        }
    if normalized in {
        "workspace-file-write",
        "workspace-memory-rewrite",
        "workspace-file-edit",
        "workspace-file-create",
        "modify-file",
        "mutating-exec",
        "external-file-write",
        "mutating-exec-proposal",
    } or normalized.startswith("workspace-file-write"):
        return {
            "classification": "modify-file",
            "mutation_near": True,
            "sudo_required": False,
            "mutation_critical": False,
        }
    if normalized in {"sudo-exec-proposal", "sudo-exec"}:
        return {
            "classification": "system-mutate",
            "mutation_near": True,
            "sudo_required": True,
            "mutation_critical": True,
        }
    if normalized in {"workspace-file-delete", "delete-file"}:
        return {
            "classification": "delete-file",
            "mutation_near": True,
            "sudo_required": False,
            "mutation_critical": True,
        }
    if normalized.startswith("git-") or normalized in {"repo-update-check", "git-mutate"}:
        return {
            "classification": "git-mutate",
            "mutation_near": True,
            "sudo_required": False,
            "mutation_critical": True,
        }
    if normalized.startswith(("system-", "package-", "sudo-")) or normalized in {
        "system-mutate",
        "package-mutate",
    }:
        return {
            "classification": "system-mutate",
            "mutation_near": True,
            "sudo_required": normalized.startswith("sudo-") or "sudo" in normalized,
            "mutation_critical": True,
        }
    return {
        "classification": "unknown",
        "mutation_near": False,
        "sudo_required": False,
        "mutation_critical": False,
    }


# Capability body declaration-parsere + sti-resolution udskilt til
# workspace_capability_decl.py (Boy Scout). Re-eksporteret for bagudkompat.
from core.tools.workspace_capability_decl import (  # noqa: E402
    _declared_body_value,
    _declared_exec_spec,
    _declared_external_file_spec,
    _declared_read_file_path,
    _declared_search_file_spec,
    _declared_write_target_path,
    _expand_declared_path,
    _is_valid_workspace_relative_path,
    _is_within_workspace_root,
    _resolve_external_path,
    _resolve_workspace_relative_path,
)


def _read_bounded_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= MAX_FILE_OUTPUT_CHARS:
        return text
    return text[: MAX_FILE_OUTPUT_CHARS - 1].rstrip() + "…"


def _bounded_exec_output(*, stdout: str, stderr: str) -> str:
    parts: list[str] = []
    normalized_stdout = str(stdout or "").strip()
    normalized_stderr = str(stderr or "").strip()
    if normalized_stdout:
        parts.append(normalized_stdout)
    if normalized_stderr:
        parts.append(f"[stderr]\n{normalized_stderr}")
    joined = "\n".join(parts).strip()
    if not joined:
        joined = "[no output]"
    if len(joined) <= MAX_EXEC_OUTPUT_CHARS:
        return joined
    return joined[: MAX_EXEC_OUTPUT_CHARS - 1].rstrip() + "…"


def _run_bounded_command(
    *,
    argv: list[str],
    workspace_dir: Path,
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    try:
        completed = subprocess.run(
            argv,
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=MAX_EXEC_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, f"Bounded exec exceeded {MAX_EXEC_SECONDS} seconds."
    return completed, None


def _run_bounded_shell_command(
    *,
    command_text: str,
    workspace_dir: Path,
) -> tuple[subprocess.CompletedProcess[str] | None, str | None]:
    try:
        completed = subprocess.run(
            ["/bin/bash", "-lc", str(command_text)],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=MAX_EXEC_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, f"Bounded exec exceeded {MAX_EXEC_SECONDS} seconds."
    return completed, None


def _search_file_matches(path: Path, query: str) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    needle = query.casefold()
    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        if needle not in raw_line.casefold():
            continue
        results.append(
            {
                "line": line_number,
                "excerpt": _bounded_excerpt(raw_line),
            }
        )
        if len(results) >= MAX_SEARCH_MATCHES:
            break
    return results


def _bounded_excerpt(text: str, limit: int = MAX_MATCH_EXCERPT_CHARS) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _set_last_capability_invocation(
    invocation: dict[str, object],
    *,
    invoked_at: str,
    capability_id: str | None = None,
    run_id: str | None = None,
) -> None:
    global _LAST_CAPABILITY_INVOCATION
    capability = invocation.get("capability")
    result = invocation.get("result") or {}
    detail = invocation.get("detail")
    result_preview = _result_preview(result)
    proposal_content = invocation.get("proposal_content") or {}
    finished_at = _now()

    _LAST_CAPABILITY_INVOCATION = {
        "active": False,
        "capability_id": capability_id or (capability or {}).get("capability_id"),
        "capability": capability,
        "status": invocation.get("status"),
        "execution_mode": invocation.get("execution_mode"),
        "approval": invocation.get("approval"),
        "invoked_at": invoked_at,
        "finished_at": finished_at,
        "result_preview": result_preview,
        "proposal_content": proposal_content,
        "detail": detail,
        "run_id": run_id,
    }
    _persist_capability_invocation(
        invocation,
        invoked_at=invoked_at,
        finished_at=finished_at,
        capability_id=capability_id,
        run_id=run_id,
    )


def _publish_capability_invocation_completed(
    invocation: dict[str, object],
    *,
    invoked_at: str,
    capability_id: str | None = None,
) -> None:
    capability = invocation.get("capability")
    result = invocation.get("result") or {}
    detail = invocation.get("detail")
    result_preview = _result_preview(result)
    proposal_content = invocation.get("proposal_content") or {}

    event_bus.publish(
        "runtime.capability_invocation_completed",
        {
            "capability_id": capability_id or (capability or {}).get("capability_id"),
            "capability": capability,
            "status": invocation.get("status"),
            "execution_mode": invocation.get("execution_mode"),
            "approval": invocation.get("approval"),
            "invoked_at": invoked_at,
            "finished_at": _now(),
            "result_preview": result_preview,
            "proposal_content": proposal_content,
            "detail": detail,
        },
    )


def _persist_capability_invocation(
    invocation: dict[str, object],
    *,
    invoked_at: str,
    finished_at: str,
    capability_id: str | None = None,
    run_id: str | None = None,
) -> None:
    capability = invocation.get("capability") or {}
    result = invocation.get("result") or {}
    detail = invocation.get("detail")
    result_preview = _result_preview(result)
    approval = invocation.get("approval") or {}
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_invocations (
                capability_id,
                capability_name,
                capability_kind,
                status,
                execution_mode,
                invoked_at,
                finished_at,
                result_preview,
                detail,
                approval_policy,
                approval_required,
                approved,
                granted,
                run_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                capability_id or capability.get("capability_id") or "unknown",
                capability.get("name"),
                capability.get("kind"),
                invocation.get("status"),
                invocation.get("execution_mode"),
                invoked_at,
                finished_at,
                result_preview,
                detail,
                approval.get("policy"),
                1 if approval.get("required") else 0,
                1 if approval.get("approved") else 0,
                1 if approval.get("granted") else 0,
                run_id,
            ),
        )
        conn.commit()


def _persist_capability_approval_request(
    invocation: dict[str, object],
    *,
    requested_at: str,
    run_id: str | None = None,
) -> None:
    capability = invocation.get("capability") or {}
    approval = invocation.get("approval") or {}
    proposal_content = invocation.get("proposal_content") or {}
    # Stamp from workspace_context so capability approval rows carry the requesting user.
    scheduled_for_user_id: str | None = None
    initiated_by: str | None = None
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id() or None
        scheduled_for_user_id = uid
        initiated_by = f"user:{uid}" if uid else "jarvis-self"
    except Exception:
        pass
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO capability_approval_requests (
                request_id,
                capability_id,
                capability_name,
                capability_kind,
                execution_mode,
                approval_policy,
                run_id,
                proposal_target_path,
                proposal_content,
                proposal_content_summary,
                proposal_content_fingerprint,
                proposal_content_source,
                proposal_reason,
                requested_at,
                status,
                scheduled_for_user_id,
                initiated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"cap-approval-{uuid4().hex}",
                capability.get("capability_id") or "unknown",
                capability.get("name"),
                capability.get("kind"),
                invocation.get("execution_mode") or "unknown",
                approval.get("policy"),
                run_id,
                proposal_content.get("target"),
                proposal_content.get("content"),
                proposal_content.get("summary"),
                proposal_content.get("fingerprint"),
                proposal_content.get("source"),
                proposal_content.get("reason"),
                requested_at,
                "pending",
                scheduled_for_user_id,
                initiated_by,
            ),
        )
        conn.commit()


def _workspace_write_proposal_content(
    *,
    summary: dict[str, object],
    write_content: str | None,
) -> dict[str, object] | None:
    if str(summary.get("execution_mode") or "") != "workspace-file-write":
        return None
    content = str(write_content or "")
    if not content:
        return {
            "state": "content-missing",
            "type": "workspace-file-write-proposal",
            "target": str(summary.get("target_path") or ""),
            "content": "",
            "summary": "",
            "fingerprint": "",
            "source": "explicit-write-content",
            "reason": (
                "Workspace write proposal exists, but no explicit write_content has been attached yet."
            ),
            "explicit_approval_required": True,
            "approval_scope": "workspace-write",
            "confidence": "low",
            "target_identity": False,
            "target_memory": False,
            "workspace_scoped": True,
        }
    return {
        "state": "bounded-content-ready",
        "type": "workspace-file-write-proposal",
        "target": str(summary.get("target_path") or ""),
        "content": content,
        "summary": _preview_text(content, limit=160),
        "fingerprint": _content_fingerprint(content),
        "source": "explicit-write-content",
        "reason": (
            f"Scoped workspace write proposal prepared for {summary.get('target_path') or 'workspace'}."
        ),
        "explicit_approval_required": True,
        "approval_scope": "workspace-write",
        "confidence": "high",
        "target_identity": False,
        "target_memory": False,
        "workspace_scoped": True,
    }


def _now() -> str:
    return datetime.now(UTC).isoformat()
