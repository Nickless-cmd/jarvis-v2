"""Durable working conclusions for interrupted agentic runs."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.runtime.state_store import load_json, save_json

_STATE_KEY = "agentic_working_conclusions"
_MAX_RECORDS = 80


def _load() -> dict[str, dict[str, Any]]:
    raw = load_json(_STATE_KEY, {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _save(records: dict[str, dict[str, Any]]) -> None:
    if len(records) > _MAX_RECORDS:
        ordered = sorted(records.items(), key=lambda item: str(item[1].get("updated_at") or ""), reverse=True)
        records = dict(ordered[:_MAX_RECORDS])
    save_json(_STATE_KEY, records)


def update_working_conclusion(
    *,
    run_id: str,
    session_id: str | None,
    user_message: str,
    round_index: int,
    observation: str = "",
    next_step: str = "",
) -> None:
    if not run_id:
        return
    observation = " ".join(str(observation or "").split())[:1000]
    next_step = " ".join(str(next_step or "").split())[:500]
    if not observation and not next_step:
        return
    records = _load()
    records[str(run_id)] = {
        "run_id": str(run_id),
        "session_id": str(session_id or ""),
        "user_message": str(user_message or "")[:500],
        "round_index": int(round_index),
        "observation": observation,
        "next_step": next_step,
        "updated_at": datetime.now(UTC).isoformat(),
    }
    _save(records)


def latest_for_session(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    sid = str(session_id)
    records = [r for r in _load().values() if str(r.get("session_id") or "") == sid]
    if not records:
        return None
    records.sort(key=lambda r: str(r.get("updated_at") or ""), reverse=True)
    return records[0]


def clear_run(run_id: str) -> None:
    records = _load()
    if str(run_id) in records:
        records.pop(str(run_id), None)
        _save(records)


def working_conclusion_prompt_section(session_id: str | None) -> str | None:
    rec = latest_for_session(session_id)
    if not rec:
        return None
    parts = [
        "Durable working conclusion fra afbrudt agentic run:",
        f"- round: {rec.get('round_index')}",
    ]
    observation = str(rec.get("observation") or "").strip()
    next_step = str(rec.get("next_step") or "").strip()
    if observation:
        parts.append(f"- nåede hertil: {observation}")
    if next_step:
        parts.append(f"- næste skridt: {next_step}")
    return "\n".join(parts)


def build_round_observation(*, text: str, tool_names: list[str], result_texts: list[str]) -> str:
    text = " ".join(str(text or "").split())
    if text:
        return text[:1000]
    if result_texts:
        joined = " | ".join(" ".join(str(item or "").split())[:240] for item in result_texts[:3])
        return joined[:1000]
    if tool_names:
        return f"Udførte tools: {', '.join(tool_names[:8])}"
    return ""
