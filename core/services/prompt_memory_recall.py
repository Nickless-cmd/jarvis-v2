"""Supplementary non-blocking recall during visible prompt assembly."""
from __future__ import annotations

import threading


# Compatibility exports for prompt_contract and older diagnostics. Previous-query
# cache delivery was retired on 2026-10-14 because it could cross query boundaries;
# keep the symbols until their importers migrate, but never populate or consume them.
_RBA_CACHE: dict = {}
_RBA_INFLIGHT: set = set()
_RBA_LOCK = threading.Lock()
_RBA_TTL_S = 300.0
_MSR_CACHE: dict = {}
_MSR_INFLIGHT: set = set()


def append_background_recall(user_message, session_id, _dyn_memory_recall, derived_inputs, _sec_err):
    """Surface prepared associations only when they match the current message.

    Expensive associative scoring remains post-turn, outside TTFT.  The next
    turn may use a prepared association only when the current query still
    matches it; unrelated previous-query results are never injected.
    """
    try:
        from core.services.associative_recall import build_recall_prompt_section

        section = build_recall_prompt_section(str(user_message or ""))
        if section:
            _dyn_memory_recall.append(section)
            derived_inputs.append("associative recall (prepared, query-matched)")
    except Exception as exc:
        _sec_err("associative recall", exc)
    return None
