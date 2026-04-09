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

CAPABILITY_FILES = {
    "tools": "TOOLS.md",
    "skills": "SKILLS.md",
}
RUNTIME_NOTE_PREFIX = "RUNTIME_NOTE:"
READ_FILE_PREFIX = "READ_FILE:"
SEARCH_FILE_PREFIX = "SEARCH_FILE:"
READ_EXTERNAL_FILE_PREFIX = "READ_EXTERNAL_FILE:"
LIST_EXTERNAL_DIR_PREFIX = "LIST_EXTERNAL_DIR:"
EXEC_COMMAND_PREFIX = "EXEC_COMMAND:"
WRITE_FILE_PREFIX = "WRITE_FILE:"
WRITE_MEMORY_FILE_PREFIX = "WRITE_MEMORY_FILE:"
REPLACE_MEMORY_LINE_PREFIX = "REPLACE_MEMORY_LINE:"
DELETE_MEMORY_LINE_PREFIX = "DELETE_MEMORY_LINE:"
REWRITE_MEMORY_FILE_PREFIX = "REWRITE_MEMORY_FILE:"
APPEND_DAILY_MEMORY_PREFIX = "APPEND_DAILY_MEMORY:"
PROPOSE_SOURCE_EDIT_PREFIX = "PROPOSE_SOURCE_EDIT:"
WRITE_EXTERNAL_FILE_PREFIX = "WRITE_EXTERNAL_FILE:"
RUNTIME_INSPECT_PREFIX = "RUNTIME_INSPECT:"
PROJECT_GREP_PREFIX = "PROJECT_GREP:"
MULTI_READ_PREFIX = "MULTI_READ:"
PROJECT_OUTLINE_PREFIX = "PROJECT_OUTLINE:"
MAX_FILE_OUTPUT_CHARS = 8000
MAX_SEARCH_MATCHES = 5
MAX_MATCH_EXCERPT_CHARS = 160
MAX_EXEC_OUTPUT_CHARS = 4000
MAX_EXEC_SECONDS = 8
MAX_MULTI_READ_FILES = 10
MAX_MULTI_READ_CHARS = 24000
MAX_GREP_MATCHES = 50
MAX_GREP_MATCH_CHARS = 200
_LAST_CAPABILITY_INVOCATION: dict[str, object] | None = None
NON_DESTRUCTIVE_EXEC_ALLOWLIST = {
    "cd",
    "pwd",
    "ls",
    "lsblk",
    "lscpu",
    "lshw",
    "lspci",
    "cat",
    "head",
    "tail",
    "wc",
    "stat",
    "file",
    "free",
    "whoami",
    "id",
    "hostnamectl",
    "nvidia-smi",
    "nproc",
    "uname",
    "uptime",
    "date",
    "df",
    "ps",
    "pgrep",
    "env",
    "printenv",
    "rg",
    "find",
    "tree",
}
GIT_READ_EXEC_ALLOWLIST = {
    ("status",),
    ("diff", "--stat"),
    ("diff", "--name-only"),
    ("branch", "--show-current"),
    ("rev-parse", "--show-toplevel"),
    ("show", "--stat", "-n", "1"),
}
GIT_MUTATING_SUBCOMMANDS = {
    "add",
    "commit",
    "reset",
    "checkout",
    "switch",
    "restore",
    "merge",
    "rebase",
    "pull",
    "push",
    "stash",
    "cherry-pick",
    "revert",
    "fetch",
}
GIT_BLOCKED_SUBCOMMANDS = {
    "clean",
    "gc",
    "filter-branch",
    "worktree",
    "submodule",
    "config",
}
APPROVED_MUTATING_EXEC_ALLOWLIST = {
    "mv",
    "cp",
    "chmod",
}
APPROVED_SUDO_EXEC_ALLOWLIST = {
    "chmod",
}
MUTATING_EXEC_PROPOSAL_TOKENS = {
    "sudo",
    "mv",
    "cp",
    "chmod",
    "chown",
    "tee",
    "sed",
    "npm",
    "pip",
    "pip3",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "brew",
    "git",
    "make",
    "cargo",
    "go",
    "docker",
    "kubectl",
}
HARD_BLOCKED_EXEC_TOKENS = {
    "rm",
    "awk",
    "perl",
    "python",
    "python3",
    "node",
}
NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS = (
    ">>",
    "<<",
    ">",
    "<",
)
NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS = (
    "&&",
    "||",
    "|",
    ";",
)


def _finalize_capability_result(result: dict[str, object]) -> dict[str, object]:
    normalized = dict(result)
    status = str(normalized.get("status") or "unknown")
    execution_mode = str(normalized.get("execution_mode") or "unsupported")
    detail = str(normalized.get("detail") or "").strip()
    status_family = _capability_status_family(status)

    if not detail:
        detail = _default_capability_detail(status=status, execution_mode=execution_mode)

    normalized["status_family"] = status_family
    normalized["ok"] = status == "executed"
    normalized["error"] = status_family in {"blocked", "unavailable", "missing", "error"}
    normalized["detail"] = detail
    normalized["message"] = detail
    return normalized


def _capability_status_family(status: str) -> str:
    if status == "executed":
        return "success"
    if status == "approval-required":
        return "approval"
    if status in {"not-found", "blocked-missing-capability"}:
        return "missing"
    if status in {"unavailable", "not-runnable"}:
        return "unavailable"
    if status.startswith("blocked"):
        return "blocked"
    if status.endswith("error") or "error" in status:
        return "error"
    return "other"


def _default_capability_detail(*, status: str, execution_mode: str) -> str:
    if status == "executed":
        return f"Capability executed: {execution_mode}."
    if status == "approval-required":
        return f"Capability requires approval before execution: {execution_mode}."
    if status == "unavailable":
        return f"Capability is unavailable: {execution_mode}."
    if status == "not-runnable":
        return f"Capability is not runnable in this pass: {execution_mode}."
    if status == "not-found":
        return "Capability was not found in runtime truth."
    if status.startswith("blocked"):
        return f"Capability execution was blocked: {status}."
    return f"Capability finished with status {status}: {execution_mode}."

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


def _document_summary(path: Path, *, kind: str) -> dict[str, object]:
    if not path.exists():
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

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
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
    if not path.exists():
        return []

    sections: list[dict[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
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
        existing_content = (
            candidate.read_text(encoding="utf-8", errors="replace")
            if candidate.exists()
            else ""
        )
        existing_fingerprint = (
            _content_fingerprint(existing_content) if existing_content else ""
        )
        existing_bytes = len(existing_content.encode("utf-8"))
        merged_content = _merge_workspace_memory_content(
            existing_content=existing_content,
            incoming_content=write_content,
        )
        candidate.write_text(merged_content, encoding="utf-8")
        # Read-back verification: re-read the file from disk so we can
        # confirm the bytes Jarvis sees actually match what was written.
        # If the readback differs (filesystem race, encoding issue,
        # external mutation), we surface that explicitly so Jarvis is
        # not lied to about persistence success.
        try:
            readback_content = candidate.read_text(encoding="utf-8", errors="replace")
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
                f"readback={'verified' if readback_match else 'MISMATCH'}."
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
        if not candidate.exists():
            return {
                "capability": summary,
                "status": "blocked-missing-target-file",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"Memory replace target file does not exist: {candidate.resolve()}",
            }
        existing_content = candidate.read_text(encoding="utf-8", errors="replace")
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
        candidate.write_text(updated_content, encoding="utf-8")
        try:
            readback_content = candidate.read_text(encoding="utf-8", errors="replace")
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
        if not candidate.exists():
            return {
                "capability": summary,
                "status": "blocked-missing-target-file",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=True, granted=False),
                "result": None,
                "detail": f"Memory delete target file does not exist: {candidate.resolve()}",
            }
        existing_content = candidate.read_text(encoding="utf-8", errors="replace")
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
        candidate.write_text(updated_content, encoding="utf-8")
        try:
            readback_content = candidate.read_text(encoding="utf-8", errors="replace")
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
        existing_content = (
            candidate.read_text(encoding="utf-8", errors="replace")
            if candidate.exists()
            else ""
        )
        existing_fingerprint = _content_fingerprint(existing_content) if existing_content else ""
        existing_bytes = len(existing_content.encode("utf-8"))
        candidate.write_text(filtered_content, encoding="utf-8")
        try:
            readback_content = candidate.read_text(encoding="utf-8", errors="replace")
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
            from apps.api.jarvis_api.services.autonomy_proposal_queue import (
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
        candidate.write_text(write_content, encoding="utf-8")
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


def _requires_capability_approval(summary: dict[str, object]) -> bool:
    return bool(summary.get("approval_required"))


def _approval_result(
    summary: dict[str, object], *, approved: bool, granted: bool
) -> dict[str, object]:
    policy = str(summary.get("approval_policy") or "not-applicable")
    required = bool(summary.get("approval_required"))
    return {
        "policy": policy,
        "required": required,
        "approved": approved,
        "granted": granted,
    }


def _declared_read_file_path(body: str) -> str | None:
    return _declared_body_value(body, "path")


def _declared_search_file_spec(body: str) -> dict[str, str] | None:
    path = _declared_body_value(body, "path")
    query = _declared_body_value(body, "query", validate=False)
    if path is None or query is None:
        return None
    normalized_query = query.strip()
    if not normalized_query:
        return None
    return {
        "path": path,
        "query": normalized_query,
    }


def _declared_external_file_spec(body: str) -> dict[str, str] | None:
    path = _declared_body_value(body, "path", validate=False)
    if path is not None:
        return {
            "path": path,
            "path_source": "declared-path",
        }
    path_from = _declared_body_value(body, "path_from", validate=False)
    normalized_source = str(path_from or "").strip().lower()
    if normalized_source in {"user-message", "invocation-argument"}:
        return {
            "path": "",
            "path_source": "invocation-argument",
        }
    return None


def _declared_exec_spec(body: str) -> dict[str, str] | None:
    command = _declared_body_value(body, "command", validate=False)
    if command is not None:
        return {
            "command": command,
            "command_source": "declared-command",
        }
    command_from = _declared_body_value(body, "command_from", validate=False)
    normalized_source = str(command_from or "").strip().lower()
    if normalized_source in {"user-message", "invocation-argument"}:
        return {
            "command": "",
            "command_source": "invocation-argument",
        }
    return None


def _declared_write_target_path(body: str) -> str | None:
    return _declared_body_value(body, "path", validate=False)


def _declared_body_value(body: str, key: str, *, validate: bool = True) -> str | None:
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        prefix = f"{key}:"
        if not line.startswith(prefix):
            continue
        declared = line[len(prefix) :].strip()
        if not declared:
            return None
        if validate:
            return declared if _is_valid_workspace_relative_path(declared) else None
        return declared
    return None


def _is_valid_workspace_relative_path(value: str) -> bool:
    path = Path(value)
    if path.is_absolute():
        return False
    if not path.parts:
        return False
    if any(part in {"..", ""} for part in path.parts):
        return False
    return True


def _resolve_workspace_relative_path(workspace_dir: Path, value: str) -> Path | None:
    if not _is_valid_workspace_relative_path(value):
        return None
    root = workspace_dir.resolve()
    candidate = (workspace_dir / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    return candidate


def _resolve_external_path(workspace_dir: Path, value: str) -> Path | None:
    expanded = _expand_declared_path(value, workspace_dir=workspace_dir)
    if not expanded:
        return None
    if expanded.startswith("~"):
        expanded = str(Path(expanded).expanduser())
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = (workspace_dir / candidate).resolve()
    return candidate.resolve()


def _is_within_workspace_root(workspace_dir: Path, candidate: Path) -> bool:
    root = workspace_dir.resolve()
    try:
        candidate.resolve().relative_to(root)
        return True
    except ValueError:
        return False


def _expand_declared_path(value: str, *, workspace_dir: Path) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return ""
    return (
        normalized
        .replace("${PROJECT_ROOT}", str(PROJECT_ROOT))
        .replace("${WORKSPACE_ROOT}", str(workspace_dir.resolve()))
    )


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
            "core/eventbus/bus.py",
            "core/eventbus/events.py",
            "core/runtime/config.py",
            "core/runtime/bootstrap.py",
            "apps/api/jarvis_api/app.py",
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


def _classify_exec_command(command_text: str) -> dict[str, object]:
    normalized = str(command_text or "").strip()
    if not normalized:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    if any(pattern in normalized for pattern in NON_DESTRUCTIVE_EXEC_REDIRECTION_PATTERNS):
        return {
            "allowed": False,
            "status": "blocked-shell-redirection",
            "detail": "Shell redirection is not allowed in non-destructive exec.",
        }
    if "$(" in normalized or "`" in normalized:
        return {
            "allowed": False,
            "status": "blocked-shell-substitution",
            "detail": "Command substitution is not allowed in non-destructive exec.",
        }
    if any(separator in normalized for separator in NON_DESTRUCTIVE_EXEC_SEGMENT_SEPARATORS):
        return _classify_shell_composed_exec_command(normalized)
    try:
        argv = shlex.split(normalized, posix=True)
    except ValueError:
        return {
            "allowed": False,
            "status": "blocked-invalid-command",
            "detail": "Command could not be parsed safely.",
        }
    if not argv:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    normalized_argv, normalization_sources = _normalize_exec_argv(argv)
    command_name = normalized_argv[0]
    if "/" in command_name:
        return {
            "allowed": False,
            "status": "blocked-command-path",
            "detail": "Explicit binary paths are not allowed in non-destructive exec.",
        }
    lowered = [part.lower() for part in argv]
    if any(token in HARD_BLOCKED_EXEC_TOKENS for token in lowered):
        blocked = next(token for token in lowered if token in HARD_BLOCKED_EXEC_TOKENS)
        return {
            "allowed": False,
            "status": "blocked-destructive-command",
            "detail": f"Destructive or arbitrary-exec token is not allowed in this pass: {blocked}",
        }
    if command_name == "cd":
        return _classify_cd_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    if command_name == "git":
        return _classify_git_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    proposal_metadata = _mutating_exec_proposal_metadata(argv)
    if proposal_metadata is not None:
        return {
            "allowed": False,
            "proposal_required": True,
            **proposal_metadata,
        }
    if command_name not in NON_DESTRUCTIVE_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-command-not-allowlisted",
            "detail": f"Command is not in the bounded non-destructive allowlist: {command_name}",
        }
    return {
        "allowed": True,
        "argv": normalized_argv,
        "normalized_command_text": shlex.join(normalized_argv),
        "path_normalization_applied": bool(normalization_sources),
        "normalization_source": "+".join(normalization_sources) if normalization_sources else "none",
    }


def _classify_shell_composed_exec_command(command_text: str) -> dict[str, object]:
    segments = _split_shell_exec_segments(command_text)
    if not segments:
        return {
            "allowed": False,
            "status": "blocked-invalid-command",
            "detail": "Command could not be segmented safely.",
        }

    execution_scope = "filesystem"
    repo_scoped = False
    normalized_segments: list[str] = []
    normalization_sources: list[str] = []

    for segment in segments:
        verdict = _classify_exec_command_no_shell(segment)
        if verdict.get("proposal_required"):
            return {
                "allowed": False,
                "proposal_required": True,
                **{
                    key: value
                    for key, value in verdict.items()
                    if key != "allowed"
                },
            }
        if not verdict.get("allowed"):
            return verdict
        normalized_segments.append(
            str(verdict.get("normalized_command_text") or segment).strip()
        )
        if verdict.get("repo_scoped"):
            repo_scoped = True
        if str(verdict.get("execution_scope") or "") == "git-read":
            execution_scope = "git-read"
        for source in str(verdict.get("normalization_source") or "none").split("+"):
            normalized_source = source.strip()
            if (
                normalized_source
                and normalized_source != "none"
                and normalized_source not in normalization_sources
            ):
                normalization_sources.append(normalized_source)

    return {
        "allowed": True,
        "argv": ["/bin/bash", "-lc", command_text],
        "shell_mode": True,
        "normalized_command_text": " ".join(normalized_segments).strip(),
        "path_normalization_applied": bool(normalization_sources),
        "normalization_source": (
            "+".join(normalization_sources) if normalization_sources else "none"
        ),
        "execution_scope": execution_scope,
        "execution_classification": (
            "git-read-allowed"
            if execution_scope == "git-read"
            else "non-destructive-read-allowed"
        ),
        "repo_scoped": repo_scoped,
        "shell_segments": normalized_segments,
    }


def _classify_exec_command_no_shell(command_text: str) -> dict[str, object]:
    normalized = str(command_text or "").strip()
    if not normalized:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    try:
        argv = shlex.split(normalized, posix=True)
    except ValueError:
        return {
            "allowed": False,
            "status": "blocked-invalid-command",
            "detail": "Command could not be parsed safely.",
        }
    if not argv:
        return {
            "allowed": False,
            "status": "blocked-missing-command",
            "detail": "Non-destructive exec requires a non-empty command.",
        }
    normalized_argv, normalization_sources = _normalize_exec_argv(argv)
    command_name = normalized_argv[0]
    if "/" in command_name:
        return {
            "allowed": False,
            "status": "blocked-command-path",
            "detail": "Explicit binary paths are not allowed in non-destructive exec.",
        }
    lowered = [part.lower() for part in argv]
    if any(token in HARD_BLOCKED_EXEC_TOKENS for token in lowered):
        blocked = next(token for token in lowered if token in HARD_BLOCKED_EXEC_TOKENS)
        return {
            "allowed": False,
            "status": "blocked-destructive-command",
            "detail": f"Destructive or arbitrary-exec token is not allowed in this pass: {blocked}",
        }
    if command_name == "cd":
        return _classify_cd_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    if command_name == "git":
        return _classify_git_exec_command(
            normalized_argv,
            path_normalization_applied=bool(normalization_sources),
            normalization_source=(
                "+".join(normalization_sources) if normalization_sources else "none"
            ),
        )
    proposal_metadata = _mutating_exec_proposal_metadata(argv)
    if proposal_metadata is not None:
        return {
            "allowed": False,
            "proposal_required": True,
            **proposal_metadata,
        }
    if command_name not in NON_DESTRUCTIVE_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-command-not-allowlisted",
            "detail": f"Command is not in the bounded non-destructive allowlist: {command_name}",
        }
    return {
        "allowed": True,
        "argv": normalized_argv,
        "normalized_command_text": shlex.join(normalized_argv),
        "path_normalization_applied": bool(normalization_sources),
        "normalization_source": (
            "+".join(normalization_sources) if normalization_sources else "none"
        ),
    }


def _split_shell_exec_segments(command_text: str) -> list[str]:
    parts = re.split(r"\s*(?:\&\&|\|\||\||;)\s*", str(command_text or "").strip())
    return [part.strip() for part in parts if part.strip()]


def _normalize_exec_argv(argv: list[str]) -> tuple[list[str], list[str]]:
    if not argv:
        return [], []

    normalized = [str(argv[0])]
    normalization_sources: list[str] = []
    home = str(Path.home())

    for arg in argv[1:]:
        updated = str(arg)
        sources_for_arg: list[str] = []

        if "~" in updated:
            expanded = str(Path(updated).expanduser())
            if expanded != updated:
                updated = expanded
                sources_for_arg.append("tilde")

        if "$HOME" in updated:
            replaced = updated.replace("$HOME", home)
            if replaced != updated:
                updated = replaced
                sources_for_arg.append("home-env")

        normalized.append(updated)
        for source in sources_for_arg:
            if source not in normalization_sources:
                normalization_sources.append(source)

    return normalized, normalization_sources


def _classify_git_exec_command(
    argv: list[str],
    *,
    path_normalization_applied: bool = False,
    normalization_source: str = "none",
) -> dict[str, object]:
    subcommand_index, execution_cwd, option_error = _resolve_git_exec_context(argv)
    if option_error:
        return option_error
    if len(argv) <= subcommand_index:
        return {
            "allowed": False,
            "status": "blocked-git-command",
            "detail": "Git exec requires one explicit bounded git subcommand.",
        }

    subcommand = str(argv[subcommand_index]).strip().lower()
    shape = tuple(str(part) for part in argv[subcommand_index:])

    if shape in GIT_READ_EXEC_ALLOWLIST:
        return {
            "allowed": True,
            "argv": argv,
            "normalized_command_text": shlex.join(argv),
            "path_normalization_applied": path_normalization_applied,
            "normalization_source": normalization_source,
            "execution_scope": "git-read",
            "execution_classification": "git-read-allowed",
            "repo_scoped": True,
            "execution_cwd": execution_cwd,
        }

    if subcommand == "log":
        if _is_allowed_bounded_git_log_args(list(argv[subcommand_index + 1 :])):
            return {
                "allowed": True,
                "argv": argv,
                "normalized_command_text": shlex.join(argv),
                "path_normalization_applied": path_normalization_applied,
                "normalization_source": normalization_source,
                "execution_scope": "git-read",
                "execution_classification": "git-read-allowed",
                "repo_scoped": True,
                "execution_cwd": execution_cwd,
            }
        return {
            "allowed": False,
            "status": "blocked-git-command-shape",
            "detail": "Bounded git log allows only: git log --oneline -n N or git log -N --oneline",
        }

    if subcommand in GIT_MUTATING_SUBCOMMANDS:
        git_mutation_class = _classify_git_mutation_subcommand(subcommand)
        return {
            "allowed": False,
            "proposal_required": True,
            "matched_token": "git",
            "effective_token": "git",
            "requires_sudo": False,
            "proposal_scope": "git",
            "proposal_execution_mode": "mutating-exec-proposal",
            "criticality": "high",
            "git_mutation_class": git_mutation_class,
            "repo_stewardship_domain": "git",
            "argv": list(argv),
            "detail": (
                f"Git mutation subcommand {subcommand} was classified as {git_mutation_class} and captured as an approval-gated repo stewardship proposal only."
            ),
        }

    if subcommand == "clean":
        return {
            "allowed": False,
            "status": "blocked-git-destructive",
            "detail": "Git clean is destructive and stays blocked in this pass.",
        }

    if subcommand in GIT_BLOCKED_SUBCOMMANDS:
        return {
            "allowed": False,
            "status": "blocked-git-command",
            "detail": (
                f"Git subcommand {subcommand} is outside the bounded read/mutate model for this pass."
            ),
        }

    return {
        "allowed": False,
        "status": "blocked-git-command",
        "detail": (
            f"Git subcommand {subcommand or 'unknown'} is not in the bounded git read allowlist and is not opened for execution in this pass."
        ),
    }


def _resolve_git_exec_context(
    argv: list[str],
) -> tuple[int, Path, dict[str, object] | None]:
    execution_cwd = PROJECT_ROOT
    index = 1
    while index < len(argv):
        token = str(argv[index]).strip()
        if token != "-C":
            break
        if index + 1 >= len(argv):
            return index, execution_cwd, {
                "allowed": False,
                "status": "blocked-git-command",
                "detail": "Git -C requires one explicit directory path.",
            }
        candidate = Path(str(argv[index + 1])).expanduser()
        if not candidate.exists() or not candidate.is_dir():
            return index, execution_cwd, {
                "allowed": False,
                "status": "blocked-git-command",
                "detail": f"Git -C target is not an existing directory: {candidate}",
            }
        execution_cwd = candidate
        index += 2
    return index, execution_cwd, None


def _is_allowed_bounded_git_log_args(log_args: list[str]) -> bool:
    if len(log_args) == 3 and log_args[0] == "--oneline" and log_args[1] == "-n":
        return bool(re.fullmatch(r"[1-9][0-9]?", log_args[2]))
    if len(log_args) == 2 and re.fullmatch(r"-[1-9][0-9]?", log_args[0]) and log_args[1] == "--oneline":
        return True
    return False


def _classify_cd_exec_command(
    argv: list[str],
    *,
    path_normalization_applied: bool = False,
    normalization_source: str = "none",
) -> dict[str, object]:
    if len(argv) != 2:
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": "Bounded cd allows only one explicit target directory.",
        }
    candidate = Path(str(argv[1])).expanduser()
    if not candidate.exists() or not candidate.is_dir():
        return {
            "allowed": False,
            "status": "blocked-invalid-target-path",
            "detail": f"cd target is not an existing directory: {candidate}",
        }
    return {
        "allowed": True,
        "argv": argv,
        "normalized_command_text": shlex.join(argv),
        "path_normalization_applied": path_normalization_applied,
        "normalization_source": normalization_source,
        "execution_scope": "filesystem",
        "execution_classification": "non-destructive-navigation-allowed",
        "repo_scoped": str(candidate.resolve()).startswith(str(PROJECT_ROOT.resolve())),
    }


def _classify_git_mutation_subcommand(subcommand: str) -> str:
    normalized = str(subcommand or "").strip().lower()
    if normalized == "add":
        return "git-stage"
    if normalized == "commit":
        return "git-commit"
    if normalized in {"push", "pull", "fetch", "merge"}:
        return "git-sync"
    if normalized in {"checkout", "switch", "restore"}:
        return "git-branch-switch"
    if normalized in {"reset", "rebase", "cherry-pick", "revert"}:
        return "git-history-rewrite"
    if normalized == "stash":
        return "git-stash"
    return "git-other-mutate"


def _mutating_exec_proposal_metadata(argv: list[str]) -> dict[str, object] | None:
    lowered = [part.lower() for part in argv]
    matched_token = next(
        (token for token in lowered if token in MUTATING_EXEC_PROPOSAL_TOKENS),
        None,
    )
    if matched_token is None:
        return None

    requires_sudo = "sudo" in lowered
    scope = "filesystem"
    criticality = "medium"
    proposal_execution_mode = "mutating-exec-proposal"
    effective_token = matched_token

    if matched_token == "sudo":
        effective_token = lowered[1] if len(lowered) > 1 else "sudo"
        scope = "system"
        criticality = "high"
        proposal_execution_mode = "sudo-exec-proposal"
    elif matched_token in {"git"}:
        scope = "git"
        criticality = "high"
    elif matched_token in {"npm", "pip", "pip3", "apt", "apt-get", "dnf", "yum", "brew"}:
        scope = "package"
        criticality = "high"
    elif matched_token in {"docker", "kubectl"}:
        scope = "system"
        criticality = "high"

    if requires_sudo and proposal_execution_mode != "sudo-exec-proposal":
        proposal_execution_mode = "sudo-exec-proposal"
        criticality = "high"

    return {
        "matched_token": matched_token,
        "effective_token": effective_token,
        "requires_sudo": requires_sudo,
        "proposal_scope": scope,
        "proposal_execution_mode": proposal_execution_mode,
        "criticality": criticality,
        "argv": list(argv),
        "detail": (
            "sudo-near command was captured as an approval-gated proposal only and was not executed."
            if requires_sudo
            else f"Mutating command token {matched_token} was captured as an approval-gated proposal only and was not executed."
        ),
    }


def _approved_mutating_exec_verdict(
    classification: dict[str, object],
) -> dict[str, object]:
    matched_token = str(
        classification.get("effective_token")
        or classification.get("matched_token")
        or "unknown"
    )
    if bool(classification.get("requires_sudo", False)):
        return {
            "allowed": False,
            "status": "blocked-sudo-execution-disabled",
            "detail": "Sudo exec remains proposal-only and is not executable in this pass.",
        }
    scope = str(classification.get("proposal_scope") or "filesystem")
    if scope in {"git", "package", "system"}:
        return {
            "allowed": False,
            "status": "blocked-command-class",
            "detail": (
                f"Approved {scope} mutation remains proposal-only in this pass and is not executable."
            ),
        }
    if matched_token not in APPROVED_MUTATING_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-command-class",
            "detail": (
                f"Approved mutating exec token {matched_token} is outside the bounded non-sudo execution allowlist for this pass."
            ),
        }
    argv = list(classification.get("argv") or [])
    if len(argv) != 3 or any(part.startswith("-") for part in argv[1:]):
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": (
                "Approved bounded non-sudo mutating exec currently allows only simple three-part commands without flags."
            ),
        }
    return {
        "allowed": True,
    }


def _approved_sudo_exec_verdict(
    classification: dict[str, object],
    *,
    workspace_dir: Path,
) -> dict[str, object]:
    if not bool(classification.get("requires_sudo", False)):
        return {
            "allowed": False,
            "status": "blocked-sudo-classification-mismatch",
            "detail": "Approved sudo exec requires a sudo-classified proposal.",
        }
    argv = list(classification.get("argv") or [])
    sudo_subcommand = str(classification.get("effective_token") or "").strip().lower()
    if sudo_subcommand not in APPROVED_SUDO_EXEC_ALLOWLIST:
        return {
            "allowed": False,
            "status": "blocked-sudo-command-class",
            "detail": (
                f"Approved sudo exec token {sudo_subcommand or 'unknown'} is outside the bounded sudo allowlist for this pass."
            ),
        }
    if len(argv) != 4 or argv[0] != "sudo":
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": (
                "Approved bounded sudo exec currently allows only simple four-part sudo commands."
            ),
        }
    if argv[1] != sudo_subcommand:
        return {
            "allowed": False,
            "status": "blocked-sudo-command-shape",
            "detail": "Approved sudo exec must match the exact bounded subcommand shape.",
        }
    if any(part.startswith("-") for part in argv[2:]):
        return {
            "allowed": False,
            "status": "blocked-command-shape",
            "detail": "Approved bounded sudo exec does not allow flags in this pass.",
        }
    mode = argv[2]
    if sudo_subcommand == "chmod" and not re.fullmatch(r"[0-7]{3,4}", mode):
        return {
            "allowed": False,
            "status": "blocked-sudo-command-shape",
            "detail": "Approved bounded sudo chmod requires a simple octal mode.",
        }
    candidate = _resolve_target_path_for_sudo_exec(workspace_dir, argv[3])
    if candidate is None:
        return {
            "allowed": False,
            "status": "blocked-sudo-target-path",
            "detail": "Approved bounded sudo exec requires a valid target path within the active workspace root.",
        }
    if not candidate.exists():
        return {
            "allowed": False,
            "status": "blocked-sudo-target-missing",
            "detail": "Approved bounded sudo exec target does not exist within the active workspace root.",
        }
    return {
        "allowed": True,
        "argv": ["sudo", sudo_subcommand, mode, str(candidate)],
        "workspace_scoped": True,
        "external_mutation_permitted": False,
    }


def _mutating_exec_proposal_content(
    *,
    command_text: str,
    command_source: str,
    classification: dict[str, object],
) -> dict[str, object]:
    matched_token = str(classification.get("matched_token") or "unknown")
    requires_sudo = bool(classification.get("requires_sudo", False))
    scope = str(classification.get("proposal_scope") or "filesystem")
    criticality = str(classification.get("criticality") or "medium")
    proposal_type = (
        "sudo-exec-proposal" if requires_sudo else "mutating-exec-proposal"
    )
    git_mutation_class = str(classification.get("git_mutation_class") or "none")
    repo_stewardship_domain = str(
        classification.get("repo_stewardship_domain")
        or ("git" if scope == "git" else "none")
    )
    return {
        "state": "approval-required-proposal",
        "type": proposal_type,
        "command": command_text,
        "content": command_text,
        "summary": _preview_text(command_text, limit=160),
        "fingerprint": _content_fingerprint(command_text),
        "source": command_source or "invocation-argument",
        "target": matched_token,
        "reason": str(
            classification.get("detail")
            or "Mutating exec proposal was captured but not executed."
        ),
        "scope": scope,
        "explicit_approval_required": True,
        "approval_scope": "sudo-exec" if requires_sudo else "mutating-exec",
        "requires_sudo": requires_sudo,
        "criticality": criticality,
        "git_mutation_class": git_mutation_class,
        "repo_stewardship_domain": repo_stewardship_domain,
        "confidence": "high",
        "proposal_only": True,
        "not_executed": True,
        "workspace_scoped": False,
        "target_identity": False,
        "target_memory": False,
        "source_contributors": [
            "workspace-capability-runtime",
            "exec-command-classifier",
        ],
    }


def _mutating_exec_execution_content(
    *,
    command_text: str,
    command_source: str,
    classification: dict[str, object],
    exit_code: int | None,
    output_text: str,
) -> dict[str, object]:
    proposal = _mutating_exec_proposal_content(
        command_text=command_text,
        command_source=command_source,
        classification=classification,
    )
    execution_state = "mutating-exec-completed"
    reason = "Approved bounded non-sudo mutating exec completed."
    if exit_code is None:
        execution_state = "mutating-exec-blocked"
        reason = "Approved bounded non-sudo mutating exec timed out before completion."
    elif exit_code != 0:
        execution_state = "mutating-exec-failed"
        reason = "Approved bounded non-sudo mutating exec exited non-zero."
    return {
        **proposal,
        "state": "executed" if exit_code is not None else "blocked",
        "type": "mutating-exec",
        "reason": reason,
        "proposal_only": exit_code is None,
        "not_executed": exit_code is None,
        "execution_state": execution_state,
        "exit_code": exit_code,
        "text": output_text,
    }


def _sudo_exec_execution_content(
    *,
    command_text: str,
    command_source: str,
    classification: dict[str, object],
    exit_code: int | None,
    output_text: str,
) -> dict[str, object]:
    proposal = _mutating_exec_proposal_content(
        command_text=command_text,
        command_source=command_source,
        classification=classification,
    )
    execution_state = "sudo-exec-completed"
    reason = "Approved bounded sudo exec completed."
    if exit_code is None:
        execution_state = "sudo-exec-blocked"
        reason = "Approved bounded sudo exec timed out before completion."
    elif exit_code != 0:
        execution_state = "sudo-exec-failed"
        reason = "Approved bounded sudo exec exited non-zero."
    return {
        **proposal,
        "state": "executed" if exit_code is not None else "blocked",
        "type": "sudo-exec",
        "reason": reason,
        "proposal_only": exit_code is None,
        "not_executed": exit_code is None,
        "execution_state": execution_state,
        "workspace_scoped": True,
        "exit_code": exit_code,
        "text": output_text,
    }


def _resolve_target_path_for_sudo_exec(workspace_dir: Path, target: str) -> Path | None:
    normalized = str(target or "").strip()
    if not normalized:
        return None
    expanded = Path(normalized).expanduser()
    candidate = (
        expanded.resolve()
        if expanded.is_absolute()
        else (workspace_dir / expanded).resolve()
    )
    if not _is_within_workspace_root(workspace_dir, candidate):
        return None
    return candidate


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
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        conn.commit()


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


_MEMORY_NOISE_SUBSTRINGS = (
    # Session/time-bound phrases that should never live in long-term memory
    "vi ses",
    "god nat",
    "god aften",
    "god morgen",
    "pas på dig",
    "kør forsigtigt",
    "hav en god",
    "ses senere",
    "i mellemtiden",
    "i aften",
    "i morgen",
    "lige nu",
    # First-person inner state narration — belongs in INNER_VOICE
    "jeg mærker",
    "jeg føler",
    "jeg oplever",
    "jeg holder stillingen",
    "jeg venter",
    "jeg fortsætter selv",
    "næste skridt",
    "jeg dykker ned",
    # Direct address to user — conversation, not memory
    "hej bjørn",
    "hi bjørn",
    "hvordan har du",
    # Question-to-user phrasing — same
    "vil du have jeg",
    "vil du have mig til",
    "skal jeg",
    "hvad foretrækker du",
    "er der noget",
    # English session-bound equivalents
    "see you soon",
    "let me know",
    "how are you",
    "should i review",
    "should i look",
    "is there anything",
)

_MEMORY_NOISE_LINE_PREFIXES = (
    "### ",
    "#### ",
    "##### ",
    "✅",
    "🚀",
    "🧠",
    "📋",
    "🌙",
    "❓",
    "🎮",
    "🤖",
    "🎬",
    "🖥️",
)


def _is_durable_memory_line(line: str) -> bool:
    """True if a line looks like a durable fact, not session noise.

    Used by _merge_workspace_memory_content to reject conversation
    fragments, inner-state narration, and emoji-headed proposals from
    leaking into MEMORY.md. Durable facts are short, start with `- `
    or a `## H2` header, and don't contain first-person reflection.
    """
    stripped = line.strip()
    if not stripped:
        return True  # blank lines are structural, not noise
    # Allowed structural lines
    if stripped.startswith("# ") or stripped.startswith("## "):
        return True
    if stripped == "---":
        return True
    # Bullet facts or continuation-indented body lines
    if not (stripped.startswith("- ") or stripped.startswith("  ")):
        # Anything else (free-form prose, headings, etc.) is noise
        return False
    # Reject emoji-headed or H3+ pseudo-sections even inside bullets
    for prefix in _MEMORY_NOISE_LINE_PREFIXES:
        if stripped.startswith(prefix):
            return False
    # Too long to be a concise fact — likely narrative
    if len(stripped) > 400:
        return False
    lowered = stripped.lower()
    for substring in _MEMORY_NOISE_SUBSTRINGS:
        if substring in lowered:
            return False
    return True


def _merge_workspace_memory_content(*, existing_content: str, incoming_content: str) -> str:
    existing_lines = existing_content.splitlines()
    incoming_lines = incoming_content.splitlines()
    if not existing_lines:
        return incoming_content if incoming_content.endswith("\n") else incoming_content + "\n"

    seen = {
        " ".join(str(line).split()).strip()
        for line in existing_lines
        if " ".join(str(line).split()).strip()
    }
    appended: list[str] = []
    rejected: list[str] = []
    for line in incoming_lines:
        normalized = " ".join(str(line).split()).strip()
        if not normalized or normalized in seen:
            continue
        if not _is_durable_memory_line(line):
            rejected.append(line)
            continue
        seen.add(normalized)
        appended.append(line)

    # Surface rejected noise so we have observability into what the
    # filter catches — not raised as an error because we still want
    # the caller to get a successful write for the durable lines.
    if rejected:
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "workspace_memory.noise_filtered",
                {
                    "rejected_count": len(rejected),
                    "sample": [line[:120] for line in rejected[:5]],
                },
            )
        except Exception:
            pass

    if not appended:
        return existing_content if existing_content.endswith("\n") else existing_content + "\n"

    return f"{existing_content.rstrip()}\n" + "\n".join(appended).rstrip() + "\n"


def _result_preview(result: object) -> str | None:
    if not isinstance(result, dict):
        return None
    text = str(result.get("text", "")).strip()
    if text:
        return _preview_text(text)
    matches = result.get("matches")
    if isinstance(matches, list) and matches:
        excerpt = str((matches[0] or {}).get("excerpt", "")).strip()
        if excerpt:
            return _preview_text(excerpt)
    return None


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


def _content_fingerprint(text: str) -> str:
    return sha1((text or "").encode("utf-8")).hexdigest()[:16]


def _now() -> str:
    return datetime.now(UTC).isoformat()
