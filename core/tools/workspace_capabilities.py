from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace
from core.runtime.db import connect

CAPABILITY_FILES = {
    "tools": "TOOLS.md",
    "skills": "SKILLS.md",
}
RUNTIME_NOTE_PREFIX = "RUNTIME_NOTE:"
READ_FILE_PREFIX = "READ_FILE:"
SEARCH_FILE_PREFIX = "SEARCH_FILE:"
MAX_FILE_OUTPUT_CHARS = 4000
MAX_SEARCH_MATCHES = 5
MAX_MATCH_EXCERPT_CHARS = 160
_LAST_CAPABILITY_INVOCATION: dict[str, object] | None = None


def load_workspace_capabilities(name: str = "default") -> dict[str, object]:
    workspace_dir = ensure_default_workspace(name=name)
    tools = _document_summary(workspace_dir / CAPABILITY_FILES["tools"], kind="tool")
    skills = _document_summary(workspace_dir / CAPABILITY_FILES["skills"], kind="skill")
    return {
        "workspace": str(workspace_dir),
        "name": name,
        "tools": tools,
        "skills": skills,
        "declared_capabilities": [
            *tools["declared_capabilities"],
            *skills["declared_capabilities"],
        ],
    }


def invoke_workspace_capability(
    capability_id: str,
    *,
    name: str = "default",
    run_id: str | None = None,
    approved: bool = False,
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
    sections = [
        *_document_sections(workspace_dir / CAPABILITY_FILES["tools"], kind="tool"),
        *_document_sections(workspace_dir / CAPABILITY_FILES["skills"], kind="skill"),
    ]

    for section in sections:
        summary = _section_summary(section)
        if summary["capability_id"] != capability_id:
            continue
        if not summary["runnable"]:
            result = {
                "capability": summary,
                "status": "not-runnable",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=approved, granted=False),
                "result": None,
            }
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        if _requires_capability_approval(summary) and not approved:
            result = {
                "capability": summary,
                "status": "approval-required",
                "execution_mode": summary["execution_mode"],
                "approval": _approval_result(summary, approved=False, granted=False),
                "result": None,
                "detail": f"Capability requires explicit approval: {summary['execution_mode']}",
            }
            _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
            _persist_capability_approval_request(
                result,
                requested_at=invoked_at,
                run_id=run_id,
            )
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        result = _invoke_runnable_capability(
            workspace_dir=workspace_dir,
            section=section,
            summary=summary,
        )
        _set_last_capability_invocation(result, invoked_at=invoked_at, run_id=run_id)
        _publish_capability_invocation_completed(result, invoked_at=invoked_at)
        return result

    result = {
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
    }
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
            "declared_capabilities": [],
        }

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    headings = [line.lstrip("#").strip() for line in lines if line.startswith("#")]
    content_lines = [line for line in lines if line and not line.startswith("#")]
    declared_capabilities = [
        _section_summary(section)
        for section in _document_sections(path, kind=kind)[:8]
    ]

    return {
        "path": str(path),
        "exists": True,
        "title": headings[0] if headings else None,
        "has_text": bool(content_lines),
        "headings": headings[1:8],
        "declared_capabilities": declared_capabilities,
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


def _section_summary(section: dict[str, str]) -> dict[str, object]:
    heading = section["heading"]
    read_file_path = _declared_read_file_path(section["body"])
    search_spec = _declared_search_file_spec(section["body"])
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
    else:
        name = heading
        execution_mode = "declared-only"
        runnable = False
    return {
        "capability_id": f"{section['kind']}:{_slugify(name)}",
        "kind": section["kind"],
        "name": name,
        "source_doc": section["source_doc"],
        "runnable": runnable,
        "execution_mode": execution_mode if runnable else "declared-only",
        "status": "runnable" if runnable else "declared-only",
        "approval_policy": _approval_policy_for_execution_mode(
            execution_mode if runnable else "declared-only"
        ),
        "approval_required": _approval_policy_for_execution_mode(
            execution_mode if runnable else "declared-only"
        )
        == "required",
        "target_path": read_file_path,
        "target_query": search_spec["query"] if search_spec else None,
    }


def _normalize_body(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    return text


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "unnamed"


def _invoke_runnable_capability(
    *, workspace_dir: Path, section: dict[str, str], summary: dict[str, object]
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

    return {
        "capability": summary,
        "status": "not-runnable",
        "execution_mode": str(summary.get("execution_mode", "declared-only")),
        "approval": _approval_result(summary, approved=False, granted=False),
        "result": None,
    }


def _approval_policy_for_execution_mode(execution_mode: str) -> str:
    if execution_mode == "workspace-file-read":
        return "required"
    if execution_mode in {"inline-text", "workspace-search-read"}:
        return "not-needed"
    return "not-applicable"


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


def _read_bounded_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= MAX_FILE_OUTPUT_CHARS:
        return text
    return text[: MAX_FILE_OUTPUT_CHARS - 1].rstrip() + "…"


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
                requested_at,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"cap-approval-{uuid4().hex}",
                capability.get("capability_id") or "unknown",
                capability.get("name"),
                capability.get("kind"),
                invocation.get("execution_mode") or "unknown",
                approval.get("policy"),
                run_id,
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


def _now() -> str:
    return datetime.now(UTC).isoformat()
