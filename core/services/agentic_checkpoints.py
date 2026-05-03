"""Durable checkpoints for visible agentic loops.

The in-flight tracker records that a run was interrupted. This module
records enough round state to let the next turn continue with concrete
context instead of only a vague "you were interrupted" hint.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.runtime.state_store import load_json, save_json

_STATE_KEY = "agentic_run_checkpoints"
_MAX_RECORDS = 80
_MAX_EXCHANGES = 20
_TEXT_LIMIT = 4000
_RESULT_LIMIT = 4000


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save(records: dict[str, dict[str, Any]]) -> None:
    if len(records) > _MAX_RECORDS:
        ordered = sorted(
            records.items(),
            key=lambda item: str(item[1].get("updated_at") or item[1].get("started_at") or ""),
            reverse=True,
        )
        records = dict(ordered[:_MAX_RECORDS])
    save_json(_STATE_KEY, records)


def _tool_name(tool_call: dict[str, Any]) -> str:
    function = tool_call.get("function") if isinstance(tool_call, dict) else {}
    if isinstance(function, dict):
        return str(function.get("name") or tool_call.get("name") or "tool")
    return str(tool_call.get("name") or "tool")


def _compact_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
    function = tool_call.get("function") if isinstance(tool_call, dict) else {}
    args = function.get("arguments") if isinstance(function, dict) else tool_call.get("arguments")
    return {
        "id": str(tool_call.get("id") or "")[:120],
        "name": _tool_name(tool_call)[:120],
        "arguments": args if isinstance(args, dict) else str(args or "")[:1000],
    }


def _compact_result(result: Any) -> dict[str, str]:
    return {
        "tool_call_id": str(getattr(result, "tool_call_id", "") or "")[:120],
        "tool_name": str(getattr(result, "tool_name", "") or "tool")[:120],
        "content": str(getattr(result, "content", "") or "")[:_RESULT_LIMIT],
    }


def compact_exchange(exchange: Any) -> dict[str, Any]:
    tool_calls = list(getattr(exchange, "tool_calls", []) or [])
    results = list(getattr(exchange, "results", []) or [])
    return {
        "text": str(getattr(exchange, "text", "") or "")[:_TEXT_LIMIT],
        "tool_calls": [_compact_tool_call(tc) for tc in tool_calls if isinstance(tc, dict)],
        "results": [_compact_result(result) for result in results],
    }


def save_checkpoint(
    *,
    run_id: str,
    session_id: str | None,
    user_message: str,
    provider: str,
    model: str,
    round_index: int,
    phase: str,
    exchanges: list[Any],
    partial_text: str = "",
    exit_reason: str = "",
) -> None:
    if not run_id:
        return
    records = _load()
    now = _now()
    existing = records.get(str(run_id), {})
    records[str(run_id)] = {
        "run_id": str(run_id),
        "session_id": str(session_id or ""),
        "user_message": str(user_message or "")[:500],
        "provider": str(provider or ""),
        "model": str(model or ""),
        "round_index": int(round_index),
        "phase": str(phase or "")[:80],
        "partial_text": str(partial_text or "")[:_TEXT_LIMIT],
        "exit_reason": str(exit_reason or "")[:200],
        "exchanges": [compact_exchange(ex) for ex in list(exchanges)[-_MAX_EXCHANGES:]],
        "started_at": str(existing.get("started_at") or now),
        "updated_at": now,
    }
    _save(records)


def latest_for_session(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    sid = str(session_id)
    records = [r for r in _load().values() if str(r.get("session_id") or "") == sid]
    if not records:
        return None
    records.sort(key=lambda r: str(r.get("updated_at") or r.get("started_at") or ""), reverse=True)
    return records[0]


def clear_run(run_id: str) -> None:
    if not run_id:
        return
    records = _load()
    if str(run_id) in records:
        records.pop(str(run_id), None)
        _save(records)


def clear_session(session_id: str | None) -> int:
    if not session_id:
        return 0
    sid = str(session_id)
    records = _load()
    keys = [k for k, v in records.items() if str(v.get("session_id") or "") == sid]
    for key in keys:
        records.pop(key, None)
    if keys:
        _save(records)
    return len(keys)


def checkpoint_prompt_section(session_id: str | None) -> str | None:
    rec = latest_for_session(session_id)
    if not rec:
        return None
    exchanges = list(rec.get("exchanges") or [])
    last = exchanges[-1] if exchanges and isinstance(exchanges[-1], dict) else {}
    calls = [str(tc.get("name") or "tool") for tc in list(last.get("tool_calls") or []) if isinstance(tc, dict)]
    results = list(last.get("results") or [])
    parts = [
        "Seneste agentic checkpoint:",
        f"- run_id: {rec.get('run_id')}",
        f"- round: {rec.get('round_index')} phase={rec.get('phase')}",
        f"- original opgave: {rec.get('user_message')}",
    ]
    if calls:
        parts.append(f"- sidste tools: {', '.join(calls[:8])}")
    if results:
        result_preview = " | ".join(
            str(r.get("content") or "")[:240] for r in results[:3] if isinstance(r, dict)
        )
        if result_preview:
            parts.append(f"- sidste tool-resultater: {result_preview}")
    partial = str(rec.get("partial_text") or "").strip()
    if partial:
        parts.append(f"- partial answer: {partial[:800]}")
    parts.append("Brug dette som konkret resume-state, hvis brugeren beder dig fortsætte.")
    return "\n".join(parts)
