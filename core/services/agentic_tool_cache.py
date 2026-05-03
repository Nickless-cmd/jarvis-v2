"""Small durable cache for read-only agentic tool results.

Interrupted runs often resume by asking for the same files/searches again.
This cache lets retry-intent turns reuse deterministic read-only tool
results without redoing the same work immediately.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.runtime.state_store import load_json, save_json

_STATE_KEY = "agentic_tool_result_cache"
_MAX_RECORDS = 200
_RESULT_LIMIT = 12000
_CACHEABLE_TOOLS = frozenset({
    "read_file",
    "read_tool_result",
    "search_memory",
    "recall_memories",
    "find_files",
    "list_plans",
    "todo_list",
    "decision_list",
})


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save(records: dict[str, dict[str, Any]]) -> None:
    if len(records) > _MAX_RECORDS:
        ordered = sorted(records.items(), key=lambda i: str(i[1].get("stored_at") or ""), reverse=True)
        records = dict(ordered[:_MAX_RECORDS])
    save_json(_STATE_KEY, records)


def _file_fingerprint(arguments: dict[str, Any]) -> dict[str, Any] | None:
    path = str(arguments.get("path") or "").strip()
    if not path:
        return None
    try:
        p = Path(path)
        stat = p.stat()
        return {"path": str(p), "mtime_ns": stat.st_mtime_ns, "size": stat.st_size}
    except Exception:
        return {"path": path, "missing": True}


def _signature(tool_name: str, arguments: dict[str, Any]) -> str:
    clean_args = {
        str(k): v for k, v in dict(arguments or {}).items()
        if not str(k).startswith("_runtime_")
    }
    payload = {"tool_name": str(tool_name), "arguments": clean_args}
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def get_cached_result(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
    if tool_name not in _CACHEABLE_TOOLS:
        return None
    records = _load()
    rec = records.get(_signature(tool_name, arguments))
    if not rec:
        return None
    if tool_name == "read_file" and rec.get("file_fingerprint") != _file_fingerprint(arguments):
        return None
    return dict(rec)


def store_result(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    result_text: str,
    status: str,
) -> None:
    if tool_name not in _CACHEABLE_TOOLS or status != "ok" or not result_text:
        return
    records = _load()
    records[_signature(tool_name, arguments)] = {
        "tool_name": str(tool_name),
        "arguments": {
            str(k): v for k, v in dict(arguments or {}).items()
            if not str(k).startswith("_runtime_")
        },
        "result_text": str(result_text)[:_RESULT_LIMIT],
        "status": "ok",
        "file_fingerprint": _file_fingerprint(arguments) if tool_name == "read_file" else None,
        "stored_at": datetime.now(UTC).isoformat(),
    }
    _save(records)
