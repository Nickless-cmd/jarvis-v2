"""Capability body declaration-parsere + workspace-sti-resolution.

Udskilt fra workspace_capabilities.py (Boy Scout-reglen, 2026-06-14) som den
nærmeste naturlige sammenhængende enhed: rene funktioner der (a) parser
`key: value`-deklarationer ud af en capability-sektions body og (b) validerer/
resolver workspace-relative og eksterne stier sikkert (path-jail mod traversal).

Re-eksporteres fra workspace_capabilities.py så eksisterende imports +
test-monkeypatches ikke knækker.
"""
from __future__ import annotations

from pathlib import Path

from core.runtime.config import PROJECT_ROOT


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
