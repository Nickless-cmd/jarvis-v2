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


def _candidate_by_runs(user_ids: list[int], run_window: int) -> int:
    """Floor so exactly the last `run_window` user-turns stay warm."""
    if len(user_ids) <= run_window:
        return 0
    keep_from = user_ids[-run_window]  # oldest user-turn we KEEP warm
    return keep_from - 1               # warm = id > floor  <=>  id >= keep_from


def _candidate_by_tokens(messages: list[dict], token_ceiling: int) -> int:
    """Floor so warm tool-tokens <= ceiling. Walks newest->oldest."""
    cum = 0
    floor = 0
    for m in reversed(messages):
        if str(m.get("role")) == "tool":
            cum += len(str(m.get("content") or "")) // 4
            if cum > token_ceiling:
                floor = int(m["id"])  # this msg (and older) goes cold
                break
    return floor


def compute_new_floor(
    messages: list[dict],
    *,
    current_floor: int,
    run_window: int,
    token_ceiling: int,
    hysteresis: float,
) -> int:
    """New cold_floor. Monotonic (>= current_floor). 0 = nothing cold yet.

    Warm = messages with id > current_floor. Advance only if warm EXCEEDS the
    limit by the hysteresis margin. On advance, trim warm to the BASE limits.
    """
    warm = [m for m in messages if int(m.get("id", 0)) > current_floor]
    user_ids_warm = user_message_ids(warm)
    tokens_warm = estimate_tool_tokens(warm)

    # >= so warm reaching exactly the hysteresis threshold advances (the margin
    # is inclusive); strict > would stall at the exact boundary (e.g. 50k vs 40k*1.25).
    over_runs = len(user_ids_warm) >= run_window * (1 + hysteresis)
    over_tokens = tokens_warm >= token_ceiling * (1 + hysteresis)
    if not (over_runs or over_tokens):
        return current_floor

    all_user_ids = user_message_ids(messages)
    cand_runs = _candidate_by_runs(all_user_ids, run_window)
    cand_tokens = _candidate_by_tokens(messages, token_ceiling)
    return max(current_floor, cand_runs, cand_tokens)


from core.runtime.db import connect

_TABLE = "tool_result_cold_floor"


def _ensure_table(conn) -> None:
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {_TABLE} ("
        "session_id TEXT PRIMARY KEY, floor_id INTEGER NOT NULL, "
        "updated_at TEXT NOT NULL)"
    )


def get_cold_floor(session_id: str) -> int:
    sid = (session_id or "").strip()
    if not sid:
        return 0
    with connect() as conn:
        _ensure_table(conn)
        row = conn.execute(
            f"SELECT floor_id FROM {_TABLE} WHERE session_id = ?", (sid,)
        ).fetchone()
    if row is None:
        return 0
    try:
        return int(row["floor_id"])
    except (KeyError, TypeError, ValueError):
        return int(row[0])


def set_cold_floor(session_id: str, floor_id: int) -> None:
    """Monotonic: writes only if floor_id > existing."""
    sid = (session_id or "").strip()
    if not sid:
        return
    from datetime import datetime, UTC
    now = datetime.now(UTC).isoformat()
    with connect() as conn:
        _ensure_table(conn)
        conn.execute(
            f"INSERT INTO {_TABLE} (session_id, floor_id, updated_at) "
            "VALUES (?, ?, ?) ON CONFLICT(session_id) DO UPDATE SET "
            "floor_id = excluded.floor_id, updated_at = excluded.updated_at "
            "WHERE excluded.floor_id > tool_result_cold_floor.floor_id",
            (sid, int(floor_id), now),
        )
