from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path

from core.eventbus.bus import event_bus
from core.identity.workspace_bootstrap import ensure_default_workspace

CAPABILITY_FILES = {
    "tools": "TOOLS.md",
    "skills": "SKILLS.md",
}
RUNTIME_NOTE_PREFIX = "RUNTIME_NOTE:"
READ_FILE_PREFIX = "READ_FILE:"
MAX_FILE_OUTPUT_CHARS = 4000
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
    capability_id: str, *, name: str = "default"
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
                "result": None,
            }
            _set_last_capability_invocation(result, invoked_at=invoked_at)
            _publish_capability_invocation_completed(result, invoked_at=invoked_at)
            return result
        result = _invoke_runnable_capability(
            workspace_dir=workspace_dir,
            section=section,
            summary=summary,
        )
        _set_last_capability_invocation(result, invoked_at=invoked_at)
        _publish_capability_invocation_completed(result, invoked_at=invoked_at)
        return result

    result = {
        "capability": None,
        "status": "not-found",
        "execution_mode": "unsupported",
        "result": None,
    }
    _set_last_capability_invocation(
        result,
        invoked_at=invoked_at,
        capability_id=capability_id,
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
    if heading.startswith(RUNTIME_NOTE_PREFIX):
        name = heading[len(RUNTIME_NOTE_PREFIX) :].strip()
        execution_mode = "inline-text"
        runnable = True
    elif heading.startswith(READ_FILE_PREFIX):
        name = heading[len(READ_FILE_PREFIX) :].strip()
        execution_mode = "workspace-file-read"
        runnable = read_file_path is not None
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
        "target_path": read_file_path,
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
                "result": None,
                "detail": f"Declared workspace file missing: {target_path or 'unknown'}",
            }
        return {
            "capability": summary,
            "status": "executed",
            "execution_mode": summary["execution_mode"],
            "result": {
                "type": "workspace-file-read",
                "path": target_path,
                "text": _read_bounded_text(candidate),
            },
        }

    return {
        "capability": summary,
        "status": "not-runnable",
        "execution_mode": str(summary.get("execution_mode", "declared-only")),
        "result": None,
    }


def _declared_read_file_path(body: str) -> str | None:
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not line.startswith("path:"):
            continue
        declared = line[5:].strip()
        if not declared:
            return None
        return declared if _is_valid_workspace_relative_path(declared) else None
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


def _set_last_capability_invocation(
    invocation: dict[str, object],
    *,
    invoked_at: str,
    capability_id: str | None = None,
) -> None:
    global _LAST_CAPABILITY_INVOCATION
    capability = invocation.get("capability")
    result = invocation.get("result") or {}
    detail = invocation.get("detail")
    result_preview = None
    if isinstance(result, dict):
        text = str(result.get("text", "")).strip()
        if text:
            result_preview = _preview_text(text)

    _LAST_CAPABILITY_INVOCATION = {
        "active": False,
        "capability_id": capability_id or (capability or {}).get("capability_id"),
        "capability": capability,
        "status": invocation.get("status"),
        "execution_mode": invocation.get("execution_mode"),
        "invoked_at": invoked_at,
        "finished_at": _now(),
        "result_preview": result_preview,
        "detail": detail,
    }


def _publish_capability_invocation_completed(
    invocation: dict[str, object],
    *,
    invoked_at: str,
    capability_id: str | None = None,
) -> None:
    capability = invocation.get("capability")
    result = invocation.get("result") or {}
    detail = invocation.get("detail")
    result_preview = None
    if isinstance(result, dict):
        text = str(result.get("text", "")).strip()
        if text:
            result_preview = _preview_text(text)

    event_bus.publish(
        "runtime.capability_invocation_completed",
        {
            "capability_id": capability_id or (capability or {}).get("capability_id"),
            "capability": capability,
            "status": invocation.get("status"),
            "execution_mode": invocation.get("execution_mode"),
            "invoked_at": invoked_at,
            "finished_at": _now(),
            "result_preview": result_preview,
            "detail": detail,
        },
    )


def _preview_text(text: str, limit: int = 120) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def _now() -> str:
    return datetime.now(UTC).isoformat()
