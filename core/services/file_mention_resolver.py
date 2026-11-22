"""Resolve desk-style ``@relative/path`` mentions to real file contents."""
from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from core.runtime import db_core

_MENTION = re.compile(r"(?<!\S)@([^\s]+)")
_TRAILING_PUNCTUATION = ".,;:!?)]}"
_MAX_FILE_BYTES = 1024 * 1024


class FileMentionNotFound(FileNotFoundError):
    pass


class FileMentionAmbiguous(ValueError):
    pass


class FileMentionTooLarge(ValueError):
    pass


def _session_workspace_root(session_id: str) -> str:
    try:
        with db_core.connect() as conn:
            row = conn.execute(
                "SELECT workspace_root FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc):
            return ""
        raise
    return str(row["workspace_root"] or "") if row is not None else ""


def _project_file_paths(session_id: str, reference: str) -> list[Path]:
    from core.services.project_context import get_project_for_session

    project = get_project_for_session(session_id)
    if project is None:
        return []
    matches: list[Path] = []
    for item in project.get("materials") or []:
        if item.get("kind") != "file":
            continue
        path = Path(str(item.get("path") or "")).resolve()
        normalized = reference.replace("\\", "/")
        as_posix = path.as_posix()
        if (
            normalized == path.name
            or as_posix == normalized
            or as_posix.endswith("/" + normalized)
        ):
            matches.append(path)
    return matches


def _workspace_file_path(root: str, reference: str) -> Path | None:
    if not root:
        return None
    base = Path(root).expanduser()
    if not base.is_absolute():
        return None
    base = base.resolve()
    candidate = (base / reference).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:  # candidate ligger uden for base — afvis sti-escape
        return None
    return candidate if candidate.is_file() else None


def _resolve_path(session_id: str, workspace_root: str, reference: str) -> Path:
    matches = _project_file_paths(session_id, reference)
    workspace_match = _workspace_file_path(workspace_root, reference)
    if workspace_match is not None and workspace_match not in matches:
        matches.insert(0, workspace_match)
    existing = [path for path in matches if path.is_file()]
    if not existing:
        raise FileMentionNotFound(reference)
    if len(existing) > 1:
        raise FileMentionAmbiguous(reference)
    return existing[0]


def _read_text(path: Path) -> str:
    size = path.stat().st_size
    if size > _MAX_FILE_BYTES:
        raise FileMentionTooLarge(f"{path} is {size} bytes; limit is {_MAX_FILE_BYTES}")
    return path.read_bytes().decode("utf-8", errors="replace")


def resolve_file_mentions(
    message: str, *, session_id: str, workspace_root: str = ""
) -> str:
    """Replace file mentions and append the bytes read from their resolved paths.

    Unknown and ambiguous references raise instead of letting raw mention text reach
    the model, where it could be mistaken for file content that was never read.
    """
    text = str(message or "")
    sid = str(session_id or "").strip()
    matches = list(_MENTION.finditer(text))
    if not matches:
        return text
    if not sid:
        raise ValueError("session_id is required when resolving file mentions")
    root = str(workspace_root or "").strip() or _session_workspace_root(sid)
    contents: list[str] = []

    def replace(match: re.Match[str]) -> str:
        raw = match.group(1)
        reference = raw
        suffix = ""
        try:
            path = _resolve_path(sid, root, reference)
        except FileMentionNotFound:
            trimmed = raw.rstrip(_TRAILING_PUNCTUATION)
            if trimmed == raw:
                raise
            reference = trimmed
            suffix = raw[len(trimmed):]
            path = _resolve_path(sid, root, reference)
        content = _read_text(path)
        contents.append(
            f"<resolved_file path={json.dumps(reference, ensure_ascii=False)}>\n"
            f"{content}\n</resolved_file>"
        )
        return f"[resolved file: {reference}]{suffix}"

    rewritten = _MENTION.sub(replace, text)
    return (
        rewritten
        + "\n\n[Server-resolved file contents; these bytes were read from disk.]\n"
        + "\n\n".join(contents)
    )
