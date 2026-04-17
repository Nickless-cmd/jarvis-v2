"""Council Memory Daemon — injects relevant past council conclusions into heartbeat context.

Each heartbeat tick: loads COUNCIL_LOG.md entries, asks cheap LLM which are most
relevant to current context (max 1 call per 10 minutes), injects compact versions
into the heartbeat payload under 'council_memory'.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from core.eventbus.bus import event_bus

_COOLDOWN_MINUTES = 10
_MAX_INJECT = 2

_last_llm_call_at: datetime | None = None
_injected_count: int = 0
_last_injected_topics: list[str] = []


def tick_council_memory_daemon(*, recent_context: str = "") -> dict[str, Any]:
    """Check COUNCIL_LOG.md for relevant past deliberations and inject into context."""
    global _last_llm_call_at, _injected_count, _last_injected_topics

    entries = _load_entries()
    if not entries:
        return {"injected": False, "reason": "no_entries"}

    # Cooldown gate
    if _last_llm_call_at is not None:
        elapsed = (datetime.now(UTC) - _last_llm_call_at).total_seconds() / 60
        if elapsed < _COOLDOWN_MINUTES:
            return {"injected": False, "reason": "cooldown"}

    _last_llm_call_at = datetime.now(UTC)

    index_lines = []
    for i, entry in enumerate(entries, 1):
        summary = str(entry.get("conclusion") or "")[:120]
        index_lines.append(f"{i}. [{entry.get('timestamp', '')}] {entry.get('topic', '')} — {summary}")
    index_text = "\n".join(index_lines)

    llm_response = _call_similarity_llm(recent_context=recent_context, index_text=index_text)
    indices = _parse_indices(llm_response, max_idx=len(entries))

    if not indices:
        return {"injected": False, "reason": "no_match"}

    injected_entries = [entries[i - 1] for i in indices]
    _injected_count += len(injected_entries)
    _last_injected_topics = [str(e.get("topic") or "") for e in injected_entries]

    event_bus.publish("council.memory_injected", {"topics": _last_injected_topics})

    return {
        "injected": True,
        "injected_entries": injected_entries,
        "injected_count_session": _injected_count,
        "council_memory": _format_for_heartbeat(injected_entries),
    }


def build_council_memory_surface() -> dict[str, Any]:
    entries = _load_entries()
    return {
        "last_llm_call_at": _last_llm_call_at.isoformat() if _last_llm_call_at else "",
        "injected_count": _injected_count,
        "last_injected_topics": _last_injected_topics,
        "log_entry_count": len(entries),
    }


def _load_entries() -> list[dict[str, Any]]:
    from core.services.council_memory_service import read_all_entries
    try:
        return read_all_entries()
    except Exception:
        return []


def _call_similarity_llm(*, recent_context: str, index_text: str) -> str:
    from core.services.non_visible_lane_execution import execute_cheap_lane
    prompt = (
        f"Nuværende kontekst:\n{recent_context[:400]}\n\n"
        f"Council-log indgange (titel + konklusion):\n{index_text}\n\n"
        "Hvilke indgange (maks 2) er mest relevante for den nuværende kontekst? "
        "Svar med indgangsnumre adskilt af komma (f.eks. '1, 3'), eller 'ingen' hvis ingen er relevante."
    )
    result = execute_cheap_lane(message=prompt)
    return str(result.get("text") or "ingen").strip()


def _parse_indices(response: str, max_idx: int) -> list[int]:
    """Extract valid 1-based indices from LLM response. Returns [] if 'ingen'."""
    if "ingen" in response.lower():
        return []
    numbers = re.findall(r"\d+", response)
    indices = []
    for n in numbers:
        idx = int(n)
        if 1 <= idx <= max_idx and idx not in indices:
            indices.append(idx)
        if len(indices) >= _MAX_INJECT:
            break
    return indices


def _format_for_heartbeat(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact representation for heartbeat context injection."""
    result = []
    for entry in entries:
        compact: dict[str, Any] = {
            "timestamp": entry.get("timestamp", ""),
            "topic": entry.get("topic", ""),
            "conclusion": str(entry.get("conclusion") or "")[:200],
        }
        if entry.get("initiative"):
            compact["initiative"] = str(entry["initiative"])[:100]
        result.append(compact)
    return result
