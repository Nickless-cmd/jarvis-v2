"""Tool-result lifecycle (visible-lane). Spec 2026-07-16.

cold_floor = persisted integer message-id. Tool-results with id < cold_floor
render as byte-stable stubs. cold_floor advances ONLY at run-end, in discrete
batches with hysteresis (hybrid: last N user-turns OR T warm-tokens). Pure
computation here; DB storage below. NO recency-relative logic (breaks the cache).
"""
from __future__ import annotations


def user_message_ids(messages: list[dict]) -> list[int]:
    """Ids for role=='user' messages, ascending (= run boundaries)."""
    out = []
    for m in messages:
        if str(m.get("role")) == "user":
            try:
                out.append(int(m["id"]))
            except (KeyError, TypeError, ValueError):
                continue
    return sorted(out)


def estimate_tool_tokens(messages: list[dict]) -> int:
    """Sum of tool-result tokens (heuristic len//4). Only role=='tool'."""
    total = 0
    for m in messages:
        if str(m.get("role")) == "tool":
            total += len(str(m.get("content") or "")) // 4
    return total
