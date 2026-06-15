"""Fil-tool executors (read_file / write_file / edit_file / read_tool_result /
read_self_docs) — udskilt fra simple_tools.py (Boy Scout-reglen, 2026-06-14).

Den naturlige sammenhængende enhed: de generiske fil-læse/skrive/redigér-tools.
Samtidig gjort encryption-aware (§16 Task 3.2) via workspace_crypto, så en members
egen workspace-fil læses/skrives korrekt når den er krypteret (.enc).

Deps der bor i simple_tools (MAX_READ_CHARS, _canonicalize_workspace_target,
classify_file_write) importeres LAZY inde i funktionerne (kald-tid), så der ikke
opstår import-cyklus ved modul-load. Re-eksporteres fra simple_tools for bagudkompat
(dispatch-dict + tests bruger simple_tools._exec_*).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.services.tool_result_store import get_tool_result
from core.services.self_critique_runtime import read_self_docs


def _ws_read_text(path: Path) -> str | None:
    """Læs encryption-aware (member .enc transparent). None hvis intet findes."""
    from core.services.workspace_crypto import read_text_for_path
    return read_text_for_path(path)


def _ws_write_text(path: Path, content: str) -> None:
    """Skriv encryption-aware (member → .enc når ENCRYPT_ON_WRITE on)."""
    from core.services.workspace_crypto import write_text_for_path
    write_text_for_path(path, content)


def _ws_path_exists(path: Path) -> bool:
    """Eksistens encryption-aware: plaintext eller member .enc."""
    if path.exists():
        return True
    from core.services.workspace_crypto import member_user_id_for_path
    return bool(member_user_id_for_path(path)) and Path(str(path) + ".enc").exists()


def _record_active_file(path: str, op: str, args: dict[str, Any]) -> None:
    """Live-highlight: notér at Jarvis (i brugerens kontekst) rører `path`, så
    desk-fil-træet kan markere filen live. Fail-open — må aldrig vælte tool-kaldet."""
    try:
        from core.services.active_file_store import set_active_file
        uid = str(args.get("_runtime_user_id") or args.get("_user_id") or "owner")
        set_active_file(uid, str(path), op)
    except Exception:
        pass


def _exec_read_file(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import MAX_READ_CHARS

    path = str(args.get("path") or "").strip()
    if not path:
        return {"error": "path is required", "status": "error"}

    target = Path(path).expanduser().resolve()
    if not _ws_path_exists(target):
        return {"error": f"File not found: {path}", "status": "error"}
    if target.exists() and not target.is_file():
        return {"error": f"Not a file: {path}", "status": "error"}

    try:
        text = _ws_read_text(target)
    except PermissionError:
        return {"error": f"Permission denied: {path}", "status": "error"}
    if text is None:
        return {"error": f"File not found: {path}", "status": "error"}

    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS - 1] + "…"

    # Record read for read-before-write guard
    # Note: tools receive _runtime_session_id (not _session_id) — fall back
    # through both keys so the guard tracks reads correctly regardless of
    # caller convention.
    try:
        from core.services.read_before_write_guard import record_read
        _session_id = (
            args.get("_runtime_session_id")
            or args.get("_session_id")
            or "default"
        )
        record_read(str(target), session_id=str(_session_id))
    except Exception:
        pass

    _record_active_file(str(target), "read", args)
    return {"text": text, "path": str(target), "size": len(text), "status": "ok"}


def _exec_read_tool_result(args: dict[str, Any]) -> dict[str, Any]:
    result_id = str(args.get("result_id") or "").strip()
    if not result_id:
        return {"error": "result_id is required", "status": "error"}

    record = get_tool_result(result_id)
    if not record:
        return {"error": f"Tool result not found: {result_id}", "status": "error"}

    return {
        "status": "ok",
        "text": str(record.get("result") or "") or "[empty tool result]",
        "result_id": result_id,
        "tool_name": str(record.get("tool_name") or ""),
        "arguments": dict(record.get("arguments") or {}),
        "summary": str(record.get("summary") or ""),
        "created_at": str(record.get("created_at") or ""),
    }


def _exec_read_self_docs(args: dict[str, Any]) -> dict[str, Any]:
    doc_id = str(args.get("doc_id") or "").strip()
    include_history = bool(args.get("include_history") or False)
    max_chars_per_doc_raw = args.get("max_chars_per_doc")
    kwargs: dict[str, Any] = {
        "doc_id": doc_id,
        "include_history": include_history,
    }
    if max_chars_per_doc_raw is not None:
        kwargs["max_chars_per_doc"] = max(500, int(max_chars_per_doc_raw))
    try:
        return read_self_docs(**kwargs)
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _exec_write_file(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _canonicalize_workspace_target, classify_file_write

    path = str(args.get("path") or "").strip()
    content = str(args.get("content") or "")
    if not path:
        return {"error": "path is required", "status": "error"}

    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)
    classification = classify_file_write(str(target))

    if classification == "blocked":
        return {"error": f"Write blocked for safety: {path}", "status": "blocked"}

    if classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"Writing to {path} requires your approval. Please confirm in chat.",
            "path": str(target),
            "content_preview": content[:200] + ("…" if len(content) > 200 else ""),
        }

    # Read-before-write guard: block overwriting protected files without reading first
    try:
        from core.services.read_before_write_guard import check_read_before_write
        _session_id = (
            args.get("_runtime_session_id")
            or args.get("_session_id")
            or "default"
        )
        _guard_allowed, _guard_reason = check_read_before_write(
            str(target), session_id=str(_session_id)
        )
        if not _guard_allowed:
            return {"status": "guard_blocked", "error": _guard_reason}
    except Exception:
        pass  # guard failure → allow (fail-open)

    # Auto-approved (workspace files)
    target.parent.mkdir(parents=True, exist_ok=True)
    _ws_write_text(target, content)
    result = {"status": "ok", "path": str(target), "bytes_written": len(content.encode("utf-8"))}
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    try:
        from core.services.self_mutation_lineage import record_self_mutation
        record_self_mutation(target_path=str(target), change_type="write")
    except Exception:
        pass
    _record_active_file(str(target), "write", args)
    return result


def _exec_edit_file(args: dict[str, Any]) -> dict[str, Any]:
    from core.tools.simple_tools import _canonicalize_workspace_target, classify_file_write

    path = str(args.get("path") or "").strip()
    old_text = str(args.get("old_text") or "")
    new_text = str(args.get("new_text") or "")
    replace_all = bool(args.get("replace_all", False))
    expected_replacements = args.get("expected_replacements")
    if not path or not old_text:
        return {"error": "path and old_text are required", "status": "error"}

    target = Path(path).expanduser().resolve()
    target, redirected_from = _canonicalize_workspace_target(target)
    classification = classify_file_write(str(target))

    if classification == "blocked":
        return {"error": f"Edit blocked for safety: {path}", "status": "blocked"}

    if classification == "approval":
        return {
            "status": "approval_needed",
            "message": f"Editing {path} requires your approval. Please confirm in chat.",
            "path": str(target),
            "old_text_preview": old_text[:100],
            "new_text_preview": new_text[:100],
        }

    if not _ws_path_exists(target):
        return {"error": f"File not found: {path}", "status": "error"}

    content = _ws_read_text(target) or ""
    if old_text not in content:
        return {"error": "old_text not found in file", "status": "error"}

    count = content.count(old_text)
    if count > 1 and not replace_all:
        return {
            "error": f"old_text matches {count} locations — be more specific, "
                     f"or pass replace_all=true to rename every occurrence",
            "status": "error",
            "match_count": count,
        }

    if expected_replacements is not None:
        try:
            expected = int(expected_replacements)
        except Exception:
            return {"error": "expected_replacements must be an integer", "status": "error"}
        if count != expected:
            return {
                "error": f"expected {expected} matches but found {count}",
                "status": "error",
                "match_count": count,
            }

    replacements = count if replace_all else 1
    new_content = content.replace(old_text, new_text, -1 if replace_all else 1)
    _ws_write_text(target, new_content)
    try:
        from core.services.self_mutation_lineage import record_self_mutation
        record_self_mutation(target_path=str(target), change_type="edit")
    except Exception:
        pass
    result = {"status": "ok", "path": str(target), "replacements": replacements}
    if redirected_from:
        result["redirected_from"] = redirected_from
        result["note"] = f"Path redirected to canonical workspace location: {target}"
    _record_active_file(str(target), "write", args)
    return result
