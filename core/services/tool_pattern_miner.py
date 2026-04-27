"""Tool pattern miner — discover repeating tool sequences as composite candidates.

Composite tools (composite_propose/invoke) are powerful but require Jarvis
to spot the pattern manually. This module reads eventbus tool.invoked
history, finds N-grams of tool calls that repeat ≥K times, and surfaces
them as candidate composites.

Heuristic only — no LLM. Output: ranked list of (sequence, count) that
the user (or Jarvis) can review and promote to a real composite via
composite_propose.

Doesn't auto-create anything. Just observes and suggests.
"""
from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


_MIN_SEQUENCE_LENGTH = 2
_MAX_SEQUENCE_LENGTH = 5
_MIN_REPEAT_COUNT = 3
_LOOKBACK_HOURS = 168  # 1 week


def _recent_tool_invocations(*, hours: int = _LOOKBACK_HOURS, limit: int = 1000) -> list[dict[str, Any]]:
    try:
        from core.eventbus.bus import event_bus
        events = event_bus.recent(limit=limit * 3)
    except Exception:
        return []
    cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
    out: list[dict[str, Any]] = []
    for e in events:
        if str(e.get("kind", "")) != "tool.invoked":
            continue
        if str(e.get("created_at", "")) < cutoff:
            continue
        payload = e.get("payload") or {}
        tool = str(payload.get("tool", ""))
        if tool:
            out.append({
                "tool": tool,
                "ts": str(e.get("created_at", "")),
                "session_id": str(payload.get("session_id") or payload.get("run_id") or ""),
            })
        if len(out) >= limit:
            break
    out.reverse()  # oldest first
    return out


def _extract_sequences(
    invocations: list[dict[str, Any]],
    *,
    min_len: int,
    max_len: int,
) -> Counter:
    """Slide window over tool calls, count N-gram occurrences."""
    counter: Counter = Counter()
    # Group by session/run so we don't merge across unrelated streams
    by_session: dict[str, list[str]] = {}
    for inv in invocations:
        by_session.setdefault(inv["session_id"], []).append(inv["tool"])
    for tools in by_session.values():
        if len(tools) < min_len:
            continue
        for n in range(min_len, min(max_len, len(tools)) + 1):
            for i in range(len(tools) - n + 1):
                seq = tuple(tools[i:i + n])
                # Skip degenerate sequences (all same tool — that's looping, not pattern)
                if len(set(seq)) <= 1:
                    continue
                counter[seq] += 1
    return counter


def find_candidate_composites(
    *,
    hours: int = _LOOKBACK_HOURS,
    min_repeat: int = _MIN_REPEAT_COUNT,
    max_results: int = 10,
) -> dict[str, Any]:
    """Mine tool history for repeating sequences worth composing."""
    invocations = _recent_tool_invocations(hours=hours)
    if not invocations:
        return {
            "status": "ok",
            "candidates": [],
            "total_invocations": 0,
            "lookback_hours": hours,
        }
    sequences = _extract_sequences(
        invocations, min_len=_MIN_SEQUENCE_LENGTH, max_len=_MAX_SEQUENCE_LENGTH,
    )
    candidates: list[dict[str, Any]] = []
    for seq, count in sequences.most_common(max_results * 3):
        if count < min_repeat:
            continue
        # Penalty: longer sequences are more interesting; prefer ones that aren't
        # subsumed by a longer sequence at the same count
        score = count * len(seq)
        candidates.append({
            "sequence": list(seq),
            "count": count,
            "score": score,
            "suggested_name": "_then_".join(seq[:3]) + ("_etc" if len(seq) > 3 else ""),
        })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return {
        "status": "ok",
        "candidates": candidates[:max_results],
        "total_invocations": len(invocations),
        "unique_sequences_seen": len(sequences),
        "lookback_hours": hours,
        "min_repeat": min_repeat,
    }


def composite_candidates_section() -> str | None:
    """Awareness section listing top 3 candidate composites."""
    result = find_candidate_composites(max_results=3)
    candidates = result.get("candidates") or []
    if not candidates:
        return None
    lines = ["💡 Tool-mønstre observeret (kandidater til composite_propose):"]
    for c in candidates:
        seq_str = " → ".join(c["sequence"])
        lines.append(f"  • {c['count']}× : {seq_str}")
    return "\n".join(lines)


def _exec_mine_tool_patterns(args: dict[str, Any]) -> dict[str, Any]:
    return find_candidate_composites(
        hours=int(args.get("hours") or _LOOKBACK_HOURS),
        min_repeat=int(args.get("min_repeat") or _MIN_REPEAT_COUNT),
        max_results=int(args.get("max_results") or 10),
    )


TOOL_PATTERN_MINER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "mine_tool_patterns",
            "description": (
                "Analyze recent tool-invocation history (eventbus) to find "
                "repeating sequences that could be promoted to composite tools. "
                "Returns ranked candidates with count + suggested name. "
                "Cheap heuristic — no LLM call. Use composite_propose to "
                "actually create one."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hours": {"type": "integer", "description": "Lookback window (default 168 = 1 week)."},
                    "min_repeat": {"type": "integer", "description": "Minimum repetitions to qualify (default 3)."},
                    "max_results": {"type": "integer"},
                },
                "required": [],
            },
        },
    },
]
