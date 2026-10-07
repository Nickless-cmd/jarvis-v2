"""Varig kontekstbeslutning for et assignment: fresh/fork, valgt vej og omkostning (agent-contract-v1 G, spec 7.1).

En raekke pr. assignment (``dispatch``): hvilken kontekst agenten fik, hvorfor, hvad den ekstra kontekst
koster, og - for en fork - tidspunktssnapshottet af parentens AFSLUTTEDE ture. Beslutningen traeffes af
``agent_fork_policy`` FOER agenten oprettes; her gemmes den, ejer-afgraenset. Inde i en BEGIN IMMEDIATE
bruges kun den medgivne conn (``connect()`` ruller en aaben transaktion tilbage).
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from core.runtime.db_agent_contract import _conn, _now_iso, _row

CONTEXT_MODES = ("fresh", "fork")
PLAN_PATHS = ("fresh", "excerpt", "same_route", "same_model_route", "paid_switch")


def ensure_fork_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_fork_contexts (
            assignment_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            owner_user_id TEXT NOT NULL,
            origin_session_id TEXT NOT NULL,
            parent_run_id TEXT NOT NULL DEFAULT '',
            requested_mode TEXT NOT NULL,
            plan_path TEXT NOT NULL,
            parent_provider TEXT NOT NULL DEFAULT '',
            parent_model TEXT NOT NULL DEFAULT '',
            parent_effort TEXT NOT NULL DEFAULT '',
            route_provider TEXT NOT NULL,
            route_model TEXT NOT NULL,
            reasoning_effort TEXT NOT NULL DEFAULT 'default',
            effort_source TEXT NOT NULL DEFAULT 'model_default',
            history_tokens INTEGER NOT NULL DEFAULT 0,
            extra_context_tokens INTEGER NOT NULL DEFAULT 0,
            estimated_extra_cost_usd REAL,
            cost_basis TEXT NOT NULL DEFAULT '',
            cache_reuse_possible INTEGER NOT NULL DEFAULT 0,
            switch_accepted INTEGER NOT NULL DEFAULT 0,
            snapshot_turns INTEGER NOT NULL DEFAULT 0,
            snapshot_truncated INTEGER NOT NULL DEFAULT 0,
            snapshot_cutoff_at TEXT NOT NULL DEFAULT '',
            snapshot_sha256 TEXT NOT NULL DEFAULT '',
            snapshot_text TEXT NOT NULL DEFAULT '',
            excerpt_text TEXT NOT NULL DEFAULT '',
            plan_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """)


def record_fork(*, assignment_id: str, agent_id: str, owner_user_id: str, origin_session_id: str,
                plan: dict[str, Any], conn: sqlite3.Connection | None = None) -> dict[str, Any]:
    """Gem planen (``agent_fork_policy.plan_context``) for assignmentet."""
    if plan["context_mode"] not in CONTEXT_MODES or plan["plan_path"] not in PLAN_PATHS:
        raise ValueError(f"ukendt plan {plan['context_mode']!r}/{plan['plan_path']!r}")
    own = conn is None
    c = conn or _conn()
    snap = (plan.get("snapshot") or {}) if plan.get("use_snapshot") else {}   # kun et BRUGT snapshot bogfoeres
    summary = {k: v for k, v in plan.items() if k not in ("snapshot", "excerpt")}
    c.execute(
        "INSERT INTO agent_fork_contexts (assignment_id, agent_id, owner_user_id, origin_session_id, "
        "parent_run_id, requested_mode, plan_path, parent_provider, parent_model, parent_effort, "
        "route_provider, route_model, reasoning_effort, effort_source, history_tokens, "
        "extra_context_tokens, estimated_extra_cost_usd, cost_basis, cache_reuse_possible, "
        "switch_accepted, snapshot_turns, snapshot_truncated, snapshot_cutoff_at, snapshot_sha256, "
        "snapshot_text, excerpt_text, plan_json, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (assignment_id, agent_id, owner_user_id, origin_session_id, plan.get("parent_run_id", ""),
         plan["context_mode"], plan["plan_path"], plan.get("parent_provider", ""),
         plan.get("parent_model", ""), plan.get("parent_effort", ""), plan["route_provider"],
         plan["route_model"], plan["reasoning_effort"], plan["effort_source"],
         int(plan.get("history_tokens", 0)), int(plan.get("extra_context_tokens", 0)),
         plan.get("estimated_extra_cost_usd"), plan.get("cost_basis", ""),
         int(bool(plan.get("cache_reuse_possible"))), int(bool(plan.get("switch_accepted"))),
         int(snap.get("turns", 0)), int(bool(snap.get("truncated"))), snap.get("cutoff_at", ""),
         snap.get("sha256", ""), snap.get("text", ""),
         plan.get("excerpt", ""), json.dumps(summary, ensure_ascii=False, default=str), _now_iso()))
    if own:
        c.commit()
    return get_fork(assignment_id=assignment_id, owner_user_id=owner_user_id, conn=c) or {}


def get_fork(*, assignment_id: str, owner_user_id: str,
             conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    """Ejer-afgraenset opslag; en andens assignment er ``None``."""
    return _row((conn or _conn()).execute(
        "SELECT * FROM agent_fork_contexts WHERE assignment_id=? AND owner_user_id=?",
        (assignment_id, owner_user_id)).fetchone())
