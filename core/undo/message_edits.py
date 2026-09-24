"""Undo file writes belonging to one saved assistant message.

Each supported file tool stores its exact before/after bytes under its tool-call id.
Undo reads one message's call ids, checks every current file against the last
after-image, then restores the first before-image for each path. A later edit
therefore blocks the whole undo instead of being silently overwritten.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import stat
import tempfile
import zlib
from pathlib import Path
from typing import Any

_SUPPORTED = frozenset({"write_file", "edit_file", "multi_edit", "fuzzy_edit"})
_REMOTE = frozenset({"operator_write_file", "operator_edit_file", "operator_multi_edit"})
_WRITING = _SUPPORTED | _REMOTE | {"apply_patch", "create_file",
                         "notebook_edit", "phone_write_file"}
_MAX_BYTES = 2_000_000
_MAX_RECORDS_PER_SESSION = 60


def _key(session_id: str, call_id: str) -> str:
    digest = hashlib.sha256(f"{session_id}\0{call_id}".encode()).hexdigest()
    return f"edit_message_undo:{digest}"


def _index_key(session_id: str) -> str:
    return f"edit_message_undo_index:{hashlib.sha256(session_id.encode()).hexdigest()}"


def _load(key: str) -> Any:
    from core.runtime.db_core import get_runtime_state_value
    return get_runtime_state_value(key, None)


def _save(key: str, value: Any) -> None:
    from core.runtime.db_core import set_runtime_state_value
    set_runtime_state_value(key, value)


def _snapshot(path: Path) -> dict[str, Any] | None:
    if path.is_symlink():
        return None
    try:
        if not path.exists():
            return {"exists": False, "sha": None, "data": None, "mode": None}
        if not path.is_file() or path.stat().st_size > _MAX_BYTES:
            return None
        data = path.read_bytes()
        if len(data) > _MAX_BYTES:
            return None
        return {
            "exists": True,
            "sha": hashlib.sha256(data).hexdigest(),
            "data": base64.b64encode(zlib.compress(data)).decode("ascii"),
            "mode": stat.S_IMODE(path.stat().st_mode),
        }
    except OSError:  # Filen kan forsvinde under læsning; uden et sikkert billede må den ikke fortrydes.
        return None


def _target(name: str, arguments: dict[str, Any]) -> Path | None:
    if name not in _SUPPORTED:
        return None
    raw = arguments.get("path") or arguments.get("file_path")
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw).expanduser().absolute()
    if path.is_symlink():
        return None
    try:
        from core.tools.simple_tools import _canonicalize_workspace_target
        path, _ = _canonicalize_workspace_target(path.resolve())
        return Path(path)
    except Exception:  # Kanonisk stiresolution skal være sikker; kan den ikke afgøres, gemmes intet billede.
        return None


def _remote_read(path: str, user_id: str) -> str:
    from core.tools.operator_tools import operator_read_file_async
    from core.tools.simple_tools_operator import _run_operator_async_impl
    result = _run_operator_async_impl(
        lambda: operator_read_file_async(path=path, user_id=user_id),
        tool_name="operator_read_file", timeout_s=35.0,
    )
    if result.get("status") != "ok":
        raise RuntimeError(str(result.get("error") or "kunne ikke læse filen"))
    return str(result.get("result") or "")


def _remote_write(path: str, user_id: str, content: str) -> None:
    from core.tools.operator_tools import operator_write_file_async
    from core.tools.simple_tools_operator import _run_operator_async_impl
    result = _run_operator_async_impl(
        lambda: operator_write_file_async(path=path, content=content, user_id=user_id),
        tool_name="operator_write_file", timeout_s=35.0,
    )
    if result.get("status") != "ok":
        raise RuntimeError(str(result.get("error") or "kunne ikke skrive filen"))


def _remote_snapshot(path: str, user_id: str) -> dict[str, Any] | None:
    try:
        data = _remote_read(path, user_id).encode("utf-8")
        if len(data) > _MAX_BYTES:
            return None
        return {"exists": True, "sha": hashlib.sha256(data).hexdigest(),
                "data": base64.b64encode(zlib.compress(data)).decode("ascii"),
                "mode": None}
    except Exception:  # En frakoblet operatørbro giver intet sikkert før/efter-billede.
        return None


def capture_before(session_id: str | None, call_id: str, name: str,
                   arguments: dict[str, Any]) -> dict[str, Any] | None:
    """Take a bounded snapshot immediately before a supported file tool executes."""
    if not session_id or not call_id:
        return None
    if name in _REMOTE:
        path = str(arguments.get("path") or "").strip()
        user_id = str(arguments.get("_runtime_user_id") or "").strip()
        if not user_id:
            from core.tools.simple_tools_operator import _operator_user_id
            user_id = _operator_user_id(arguments)
        if not path or not user_id:
            return None
        before = _remote_snapshot(path, user_id)
        if before is None:
            return None
        return {"key": _key(session_id, call_id), "session_id": session_id,
                "path": path, "before": before,
                "remote_user_id": user_id}
    path = _target(name, arguments)
    before = _snapshot(path) if path else None
    if before is None:
        return None
    return {"key": _key(session_id, call_id), "session_id": session_id,
            "path": str(path), "before": before}


def capture_after(token: dict[str, Any] | None, result: dict[str, Any]) -> None:
    if not token or result.get("status") not in {"ok", "done"}:
        return
    remote_user_id = token.get("remote_user_id")
    after = (_remote_snapshot(token["path"], remote_user_id) if remote_user_id
             else _snapshot(Path(token["path"])))
    if after is None or after["sha"] == token["before"]["sha"]:
        return
    _save(token["key"], {"path": token["path"], "before": token["before"],
                         "after": after, "remote_user_id": remote_user_id})
    index_key = _index_key(token["session_id"])
    previous = _load(index_key)
    keys = [k for k in previous if isinstance(k, str)] if isinstance(previous, list) else []
    keys = [k for k in keys if k != token["key"]] + [token["key"]]
    for expired in keys[:-_MAX_RECORDS_PER_SESSION]:
        _save(expired, None)
    _save(index_key, keys[-_MAX_RECORDS_PER_SESSION:])


def _message_blocks(session_id: str, message_id: str) -> list[dict[str, Any]] | None:
    from core.runtime.db_core import connect
    with connect() as conn:
        row = conn.execute(
            "SELECT role, content_json FROM chat_messages WHERE session_id = ? AND message_id = ?",
            (session_id, message_id),
        ).fetchone()
    if not row or row["role"] != "assistant" or not row["content_json"]:
        return None
    try:
        blocks = json.loads(str(row["content_json"]))
        return blocks if isinstance(blocks, list) else None
    except (TypeError, ValueError):  # Gamle eller beskadigede beskeder må ikke udløse filskrivning.
        return None


def _records(session_id: str, message_id: str) -> tuple[list[dict[str, Any]], str | None]:
    blocks = _message_blocks(session_id, message_id)
    if blocks is None:
        return [], "Beskeden findes ikke i denne session."
    records: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != "tool_use":
            continue
        name = str(block.get("name") or "")
        if name not in _WRITING or block.get("status") == "error":
            continue
        call_id = str(block.get("id") or "")
        record = _load(_key(session_id, call_id)) if call_id else None
        if not isinstance(record, dict):
            return [], "Denne beskeds filændringer har ikke sikre fortrydelsesdata."
        records.append(record)
    if not records:
        return [], "Beskeden har ingen filændringer, der kan fortrydes."
    return records, None


def _decode(snapshot: dict[str, Any]) -> bytes | None:
    if not snapshot["exists"]:
        return None
    data = zlib.decompress(base64.b64decode(snapshot["data"]))
    if len(data) > _MAX_BYTES or hashlib.sha256(data).hexdigest() != snapshot["sha"]:
        raise ValueError("Fortrydelsesdata er beskadiget")
    return data


def _restore(path: str, snapshot: dict[str, Any], remote_user_id: str | None,
             data: bytes | None) -> None:
    if remote_user_id:
        if data is None:
            raise ValueError("En ny fil på operatørens maskine kan ikke slettes sikkert endnu")
        _remote_write(path, remote_user_id, data.decode("utf-8"))
        return
    target = Path(path)
    if data is None:
        target.unlink()
        return
    fd, temporary = tempfile.mkstemp(prefix=".jarvis-undo-", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
        os.chmod(temporary, snapshot["mode"])
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _matches(current: dict[str, Any] | None, expected: dict[str, Any]) -> bool:
    return (current is not None and current["exists"] == expected["exists"]
            and current["sha"] == expected["sha"]
            and current["mode"] == expected["mode"])


def undo_message(session_id: str, message_id: str) -> dict[str, Any]:
    """Restore exact files only if all still equal this message's after-image."""
    records, error = _records(session_id, message_id)
    if error:
        return {"status": "unavailable", "error": error}
    by_path: dict[str, dict[str, Any]] = {}
    for record in records:
        path = str(record["path"])
        if path not in by_path:
            by_path[path] = {"before": record["before"], "after": record["after"],
                             "remote_user_id": record.get("remote_user_id")}
        else:
            if (by_path[path]["remote_user_id"] != record.get("remote_user_id")
                    or not _matches(record["before"], by_path[path]["after"])):
                return {"status": "conflict", "error": f"{path} blev ændret mellem Jarvis’ filkald. Ingen filer blev fortrudt."}
            by_path[path]["after"] = record["after"]
    for path, pair in by_path.items():
        remote_user_id = pair["remote_user_id"]
        current = (_remote_snapshot(path, remote_user_id) if remote_user_id
                   else _snapshot(Path(path)))
        if not _matches(current, pair["after"]):
            return {"status": "conflict", "error": f"{path} er ændret siden beskeden. Ingen filer blev fortrudt."}
    try:
        for pair in by_path.values():
            pair["before_data"] = _decode(pair["before"])
            pair["after_data"] = _decode(pair["after"])
    except (ValueError, KeyError, TypeError, zlib.error) as exc:  # Afvis før nogen fil ændres.
        return {"status": "unavailable", "error": str(exc)}
    applied: list[str] = []
    try:
        for path, pair in by_path.items():
            current = (_remote_snapshot(path, pair["remote_user_id"]) if pair["remote_user_id"]
                       else _snapshot(Path(path)))
            if not _matches(current, pair["after"]):
                raise RuntimeError(f"{path} er ændret under fortrydelsen")
            applied.append(path)
            _restore(path, pair["before"], pair["remote_user_id"], pair["before_data"])
    except Exception as exc:
        for path in reversed(applied):
            pair = by_path[path]
            try:
                _restore(path, pair["after"], pair["remote_user_id"], pair["after_data"])
            except Exception:  # Kompensation kan selv fejle; rapportér mulig delvis ændring tydeligt.
                return {"status": "error", "error": "Fortrydelsen stoppede, og nogle filer kunne ikke gendannes automatisk."}
        return {"status": "error", "error": f"Kunne ikke fortryde alle filer: {exc}"}
    for block in (_message_blocks(session_id, message_id) or []):
        if (isinstance(block, dict) and block.get("type") == "tool_use"
                and block.get("name") in _WRITING):
            _save(_key(session_id, str(block.get("id") or "")), None)
    return {"status": "ok", "files": len(by_path)}
