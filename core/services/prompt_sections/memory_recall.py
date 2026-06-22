"""Memory recall section builder — udskilt fra prompt_contract.py (Boy Scout).

Fem tightly coupled funktioner til at bygge [MEMORY-RECALL]-sektionen:
  - _visible_memory_recall_bundle_section: hovedfunktion, bygger sektionen
  - _private_brain_recall_lines: henter private brain continuity
  - _recent_tool_recall_lines: henter seneste tool observationer
  - _memory_candidate_recall_lines: henter pending memory candidates
  - _clip_line: hjælper til at klippe lange linjer

Re-eksporteres fra prompt_contract.py så eksisterende imports + monkeypatches
i tests ikke knækker.
"""
from __future__ import annotations

from core.services.chat_sessions import recent_chat_tool_messages
from core.services.tool_result_store import render_tool_result_for_prompt
from core.runtime.db import list_runtime_contract_candidates


def _visible_memory_recall_bundle_section(
    *,
    session_id: str | None,
    user_message: str,
    compact: bool,
) -> str | None:
    lines: list[str] = ["Memory recall bundle:"]

    private_brain = _private_brain_recall_lines(limit=3 if compact else 4)
    if private_brain:
        lines.append("- Private continuity:")
        lines.extend(f"  - {line}" for line in private_brain)

    tool_lines = _recent_tool_recall_lines(session_id, limit=3 if compact else 5)
    if tool_lines:
        lines.append("- Internal tool observations (Jarvis-only, not user-visible chat):")
        lines.extend(f"  - {line}" for line in tool_lines)

    candidate_lines = _memory_candidate_recall_lines(limit=2 if compact else 3)
    if candidate_lines:
        lines.append("- Pending memory candidates:")
        lines.extend(f"  - {line}" for line in candidate_lines)

    if len(lines) == 1:
        return None
    lines.append(
        "Use this only as bounded continuity support. Workspace files and the user's latest message outrank it."
    )
    return "\n".join(lines)


def _private_brain_recall_lines(*, limit: int) -> list[str]:
    try:
        from core.services.session_distillation import (
            build_private_brain_context,
        )

        brain = build_private_brain_context(limit=limit)
    except Exception:
        return []
    if not brain.get("active"):
        return []
    result: list[str] = []
    summary = " ".join(str(brain.get("continuity_summary") or "").split()).strip()
    if summary:
        result.append(_clip_line(summary, limit=180))
    for excerpt in list(brain.get("excerpts") or [])[:limit]:
        text = " ".join(str(excerpt.get("summary") or "").split()).strip()
        if not text:
            continue
        focus = " ".join(str(excerpt.get("focus") or "").split()).strip()
        prefix = f"{focus}: " if focus else ""
        result.append(_clip_line(prefix + text, limit=180))
    return result[:limit]


def _recent_tool_recall_lines(session_id: str | None, *, limit: int) -> list[str]:
    if not session_id:
        return []
    try:
        messages = recent_chat_tool_messages(session_id, limit=limit)
    except Exception:
        return []
    # 2026-06-22 (Jarvis' review): tool observations are historical bash-output
    # noise from earlier debugging. Only surface ones from the last 30 minutes,
    # and condense hard to a one-line summary (was 220 chars). Old runs drop out.
    from datetime import datetime, timezone, timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    result: list[str] = []
    for item in messages[-limit:]:
        ts_raw = str(item.get("created_at") or "").strip()
        if ts_raw:
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue  # older than 30 min — historical, not "now"
            except Exception:
                pass
        content = render_tool_result_for_prompt(
            str(item.get("content") or ""),
            expand=False,
            max_chars=100,
        )
        if not content:
            continue
        result.append(_clip_line(content, limit=100))
    return result


def _memory_candidate_recall_lines(*, limit: int) -> list[str]:
    try:
        candidates = list_runtime_contract_candidates(
            candidate_type="memory_promotion",
            target_file="MEMORY.md",
            status="proposed",
            limit=limit,
        )
    except Exception:
        return []
    lines: list[str] = []
    for candidate in candidates[:limit]:
        summary = " ".join(str(candidate.get("summary") or "").split()).strip()
        confidence = str(candidate.get("confidence") or "unknown").strip()
        if summary:
            lines.append(_clip_line(f"{summary} (confidence={confidence})", limit=180))
    return lines


def _clip_line(value: str, *, limit: int) -> str:
    text = " ".join(str(value or "").split()).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"
