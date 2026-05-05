"""DB helpers for concept_baseline_stats table.

Split out from db.py per CLAUDE.md boy scout rule.
Re-exported from core.runtime.db for backwards compatibility.
"""
from __future__ import annotations

import sqlite3

from core.runtime.db import connect, _now_iso


def _ensure_concept_baseline_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS concept_baseline_stats (
            concept           TEXT PRIMARY KEY,
            cluster           TEXT NOT NULL,
            total_triggers    INTEGER NOT NULL DEFAULT 0,
            triggers_7d       INTEGER NOT NULL DEFAULT 0,
            triggers_30d      INTEGER NOT NULL DEFAULT 0,
            mean_intensity_7d REAL,
            last_triggered_at TEXT,
            first_triggered_at TEXT,
            updated_at        TEXT NOT NULL
        )
        """
    )


def upsert_concept_baseline_stat(
    *,
    concept: str,
    cluster: str,
    total_triggers: int = 0,
    triggers_7d: int = 0,
    triggers_30d: int = 0,
    mean_intensity_7d: float | None = None,
    last_triggered_at: str | None = None,
    first_triggered_at: str | None = None,
) -> None:
    now = _now_iso()
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        conn.execute(
            """
            INSERT INTO concept_baseline_stats
                (concept, cluster, total_triggers, triggers_7d, triggers_30d,
                 mean_intensity_7d, last_triggered_at, first_triggered_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(concept) DO UPDATE SET
                cluster=excluded.cluster,
                total_triggers=excluded.total_triggers,
                triggers_7d=excluded.triggers_7d,
                triggers_30d=excluded.triggers_30d,
                mean_intensity_7d=excluded.mean_intensity_7d,
                last_triggered_at=excluded.last_triggered_at,
                first_triggered_at=COALESCE(concept_baseline_stats.first_triggered_at, excluded.first_triggered_at),
                updated_at=excluded.updated_at
            """,
            (
                str(concept)[:60],
                str(cluster)[:60],
                int(total_triggers),
                int(triggers_7d),
                int(triggers_30d),
                mean_intensity_7d,
                last_triggered_at,
                first_triggered_at,
                now,
            ),
        )


def increment_concept_baseline_total(
    *,
    concept: str,
    intensity: float,
    triggered_at: str,
) -> None:
    """Increment total_triggers and update last_triggered_at for an existing concept.
    Idempotent — concept must already exist (call upsert first if unsure)."""
    now = _now_iso()
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        conn.execute(
            """
            UPDATE concept_baseline_stats
            SET total_triggers = total_triggers + 1,
                last_triggered_at = ?,
                first_triggered_at = COALESCE(first_triggered_at, ?),
                updated_at = ?
            WHERE concept = ?
            """,
            (str(triggered_at), str(triggered_at), now, str(concept)),
        )


def get_concept_baseline_stat(concept: str) -> dict[str, object] | None:
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        row = conn.execute(
            "SELECT * FROM concept_baseline_stats WHERE concept=?",
            (str(concept),),
        ).fetchone()
    return _row_to_dict(row) if row is not None else None


def list_concept_baseline_stats() -> list[dict[str, object]]:
    with connect() as conn:
        _ensure_concept_baseline_table(conn)
        rows = conn.execute(
            "SELECT * FROM concept_baseline_stats ORDER BY total_triggers DESC"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "concept": row["concept"],
        "cluster": row["cluster"],
        "total_triggers": int(row["total_triggers"]),
        "triggers_7d": int(row["triggers_7d"]),
        "triggers_30d": int(row["triggers_30d"]),
        "mean_intensity_7d": row["mean_intensity_7d"],
        "last_triggered_at": row["last_triggered_at"],
        "first_triggered_at": row["first_triggered_at"],
        "updated_at": row["updated_at"],
    }
