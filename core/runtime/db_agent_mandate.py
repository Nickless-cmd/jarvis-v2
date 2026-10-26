"""Durable, mechanically enforceable mandate for one agent assignment.

The mandate is data, not prose: exact tools, target, workspace roots, resource
limits and ordered side-effect classes.  The approval gate compares a concrete
invocation with this row; no model is asked to interpret whether an action fits.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from core.runtime.db_core import _now_iso


SIDE_EFFECT_LEVELS = {
    "none": 0,
    "read": 1,
    "worktree-write": 2,
    "external-write": 3,
    "host-write": 4,
    "destructive": 5,
}


def ensure_mandate_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_assignment_mandates (
            mandate_id TEXT PRIMARY KEY,
            assignment_id TEXT NOT NULL UNIQUE,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_run_id TEXT NOT NULL DEFAULT '',
            original_mandate_id TEXT NOT NULL DEFAULT '',
            target TEXT NOT NULL,
            workspace_roots_json TEXT NOT NULL DEFAULT '[]',
            allowed_tools_json TEXT NOT NULL DEFAULT '[]',
            tool_policy TEXT NOT NULL,
            granted_side_effect TEXT NOT NULL,
            original_side_effect TEXT NOT NULL,
            budget_tokens INTEGER NOT NULL,
            max_turns INTEGER NOT NULL,
            max_depth INTEGER NOT NULL,
            max_fanout INTEGER NOT NULL,
            deadline_at TEXT NOT NULL,
            expected_result TEXT NOT NULL,
            return_address TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_mandate_owner "
        "ON agent_assignment_mandates(owner_user_id, origin_session_id)"
    )


def _conn():
    from core.runtime.db_agent_contract import _conn as contract_conn

    conn = contract_conn()
    ensure_mandate_tables(conn)
    return conn


def record(*, assignment_id: str, mandate: dict[str, Any]) -> dict[str, Any]:
    """Persist one immutable mandate. A conflicting second value is refused."""
    required = {
        "mandate_id", "owner_user_id", "origin_session_id", "target", "tool_policy",
        "granted_side_effect", "original_side_effect", "budget_tokens", "max_turns",
        "max_depth", "max_fanout", "deadline_at", "expected_result", "return_address",
    }
    missing = sorted(k for k in required if mandate.get(k) in (None, ""))
    if missing:
        raise ValueError(f"mandate mangler: {', '.join(missing)}")
    for key in ("granted_side_effect", "original_side_effect"):
        if mandate[key] not in SIDE_EFFECT_LEVELS:
            raise ValueError(f"ukendt side-effect-klasse: {mandate[key]}")
    conn = _conn()
    payload = (
        str(mandate["mandate_id"]), assignment_id, str(mandate["owner_user_id"]),
        str(mandate["origin_session_id"]), str(mandate.get("parent_run_id") or ""),
        str(mandate.get("original_mandate_id") or ""), str(mandate["target"]),
        json.dumps(sorted(set(mandate.get("workspace_roots") or []))),
        json.dumps(sorted(set(mandate.get("allowed_tools") or []))), str(mandate["tool_policy"]),
        str(mandate["granted_side_effect"]), str(mandate["original_side_effect"]),
        int(mandate["budget_tokens"]), int(mandate["max_turns"]), int(mandate["max_depth"]),
        int(mandate["max_fanout"]), str(mandate["deadline_at"]),
        str(mandate["expected_result"]), str(mandate["return_address"]), _now_iso(),
    )
    conn.execute("BEGIN IMMEDIATE")
    try:
        existing = conn.execute(
            "SELECT * FROM agent_assignment_mandates WHERE assignment_id=?", (assignment_id,),
        ).fetchone()
        if existing is not None:
            old = _decode(existing)
            comparable = {k: old[k] for k in mandate if k in old and k != "created_at"}
            wanted = {k: mandate[k] for k in comparable}
            if comparable != wanted:
                raise ValueError("assignmentet har allerede et andet mandat")
            conn.rollback()
            return old
        conn.execute(
            "INSERT INTO agent_assignment_mandates (mandate_id, assignment_id, owner_user_id, "
            "origin_session_id, parent_run_id, original_mandate_id, target, workspace_roots_json, "
            "allowed_tools_json, tool_policy, granted_side_effect, original_side_effect, "
            "budget_tokens, max_turns, max_depth, max_fanout, deadline_at, expected_result, "
            "return_address, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            payload,
        )
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return get(assignment_id=assignment_id) or {}


def _decode(row) -> dict[str, Any]:
    out = {k: row[k] for k in row.keys()}
    out["workspace_roots"] = json.loads(out.pop("workspace_roots_json") or "[]")
    out["allowed_tools"] = json.loads(out.pop("allowed_tools_json") or "[]")
    return out


def get(*, assignment_id: str) -> dict[str, Any] | None:
    row = _conn().execute(
        "SELECT * FROM agent_assignment_mandates WHERE assignment_id=?", (assignment_id,),
    ).fetchone()
    return None if row is None else _decode(row)


def side_effect_exceeds(actual: str, ceiling: str) -> bool:
    return SIDE_EFFECT_LEVELS.get(actual, SIDE_EFFECT_LEVELS["destructive"]) > SIDE_EFFECT_LEVELS.get(
        ceiling, -1
    )
