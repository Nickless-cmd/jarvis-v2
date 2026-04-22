"""User attribution migrations — add user_id/workspace_name columns.

Adds ALTER TABLE ... ADD COLUMN IF NOT EXISTS patterns to existing tables
so multi-user can attribute data without losing historical records.

SQLite does not support native "ADD COLUMN IF NOT EXISTS" so we do an
information_schema-style check first and ALTER only when missing.

Run idempotently at startup via core.services.governance_bootstrap or
called explicitly from CLI/tests.

Tables scoped:
- chat_messages: per-user (always)
- visible_runs: per-user (always)
- cognitive_regrets: global + attributable_user_id (who triggered)
- cognitive_ruptures: same
- cognitive_blind_spots: same
- cognitive_trade_outcomes: same
- cognitive_personal_project_journal: same (journal entries carry user context)
- cognitive_reflective_plans: same
- cognitive_decisions: same

NOT scoped (intentionally global, no attribution):
- cognitive_personal_projects (the project itself is Jarvis')
- cognitive_dream_hypotheses (his dreams)
- cognitive_morning_threads (one per sleep period)
- cognitive_paradoxes (his meta-observations)
- cognitive_self_reviews (his self-audit)
- cognitive_epistemic_claims / cognitive_wrongness (his epistemics)
"""
from __future__ import annotations

import logging
from typing import Iterable

from core.runtime.db import connect

logger = logging.getLogger(__name__)


# (table_name, column_name, column_type, default_value_sql)
_USER_ATTRIBUTION_COLUMNS: list[tuple[str, str, str, str]] = [
    # Chat messages: per-user scoping (strongest privacy)
    ("chat_messages", "user_id", "TEXT", "''"),
    ("chat_messages", "workspace_name", "TEXT", "''"),

    # Visible runs: per-user scoping
    ("visible_runs", "user_id", "TEXT", "''"),
    ("visible_runs", "workspace_name", "TEXT", "''"),

    # Cognitive tables: global + attribution for filtering
    ("cognitive_regrets", "attributable_user_id", "TEXT", "''"),
    ("cognitive_ruptures", "attributable_user_id", "TEXT", "''"),
    ("cognitive_blind_spots", "attributable_user_id", "TEXT", "''"),
    ("cognitive_trade_outcomes", "attributable_user_id", "TEXT", "''"),
    ("cognitive_reflective_plans", "attributable_user_id", "TEXT", "''"),
    ("cognitive_decisions", "attributable_user_id", "TEXT", "''"),
    ("cognitive_personal_project_journal", "attributable_user_id", "TEXT", "''"),
]


def _table_has_column(conn, table: str, column: str) -> bool:
    try:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    except Exception:
        return False
    for row in rows:
        # PRAGMA table_info returns (cid, name, type, notnull, dflt_value, pk)
        try:
            name = row[1] if isinstance(row, tuple) else row["name"]
        except Exception:
            name = None
        if name == column:
            return True
    return False


def _table_exists(conn, table: str) -> bool:
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return row is not None
    except Exception:
        return False


def run_user_attribution_migrations() -> dict[str, list[str]]:
    """Add user_id / attributable_user_id columns to all listed tables.

    Idempotent — safe to call repeatedly. Returns summary dict with:
    - 'added': list of 'table.column' strings where column was added
    - 'already_present': list of 'table.column' strings already there
    - 'table_missing': list of tables that didn't exist yet (not an error
      — they'll be created by their owning service on first use, and the
      CREATE TABLE statements in those services will include the columns
      going forward via their own definition)
    """
    added: list[str] = []
    present: list[str] = []
    table_missing: list[str] = []

    with connect() as conn:
        for table, column, col_type, default_sql in _USER_ATTRIBUTION_COLUMNS:
            if not _table_exists(conn, table):
                table_missing.append(table)
                continue
            if _table_has_column(conn, table, column):
                present.append(f"{table}.{column}")
                continue
            try:
                conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {col_type} "
                    f"NOT NULL DEFAULT {default_sql}"
                )
                added.append(f"{table}.{column}")
                logger.info("user_attribution: added %s.%s", table, column)
            except Exception as exc:
                logger.warning(
                    "user_attribution: failed to add %s.%s: %s",
                    table, column, exc,
                )
        conn.commit()

    return {
        "added": added,
        "already_present": present,
        "table_missing": sorted(set(table_missing)),
    }


def list_user_attribution_schema() -> list[dict[str, str]]:
    """Return current status of all attribution columns for admin/debug."""
    out: list[dict[str, str]] = []
    with connect() as conn:
        for table, column, col_type, _default in _USER_ATTRIBUTION_COLUMNS:
            if not _table_exists(conn, table):
                status = "table_missing"
            elif _table_has_column(conn, table, column):
                status = "present"
            else:
                status = "missing"
            out.append({
                "table": table,
                "column": column,
                "type": col_type,
                "status": status,
            })
    return out
