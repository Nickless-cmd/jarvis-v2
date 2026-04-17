from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime.config import STATE_DIR
from core.services.signal_noise_guard import is_noisy_signal_text

DB_PATH = STATE_DIR / "jarvis.db"
NOW_ISO = datetime.now(UTC).isoformat()

_TABLES = (
    ("runtime_development_focuses", "focus_id"),
    ("runtime_goal_signals", "goal_id"),
    ("runtime_reflection_signals", "signal_id"),
    ("runtime_dream_hypothesis_signals", "signal_id"),
    ("runtime_witness_signals", "signal_id"),
)
_RECENT_KEEP = {
    "runtime_reflection_signals": 24,
    "runtime_witness_signals": 40,
}


def _ensure_signal_archive_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS signal_archive (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_table TEXT NOT NULL,
            signal_id TEXT NOT NULL,
            signal_type TEXT NOT NULL DEFAULT '',
            canonical_key TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            status_reason TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            archived_at TEXT NOT NULL
        )
        """
    )


def _archive_row(
    conn: sqlite3.Connection,
    *,
    table: str,
    id_column: str,
    row: sqlite3.Row,
    reason: str,
) -> None:
    conn.execute(
        """
        INSERT INTO signal_archive
            (source_table, signal_id, signal_type, canonical_key, status,
             title, summary, status_reason, created_at, updated_at, archived_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            table,
            str(row[id_column]),
            str(row["signal_type"] if "signal_type" in row.keys() else ""),
            str(row["canonical_key"] if "canonical_key" in row.keys() else ""),
            "archived-noise",
            str(row["title"] if "title" in row.keys() else ""),
            str(row["summary"] if "summary" in row.keys() else ""),
            reason,
            str(row["created_at"] if "created_at" in row.keys() else ""),
            str(row["updated_at"] if "updated_at" in row.keys() else ""),
            NOW_ISO,
        ),
    )
    conn.execute(
        f"DELETE FROM {table} WHERE {id_column} = ?",  # noqa: S608
        (str(row[id_column]),),
    )


def _row_is_noise(row: sqlite3.Row) -> bool:
    human_text = " ".join(
        str(row[key] or "")
        for key in ("title", "summary")
        if key in row.keys()
    )
    if is_noisy_signal_text(human_text):
        return True
    supplemental = " ".join(
        str(row[key] or "")
        for key in ("evidence_summary", "support_summary")
        if key in row.keys()
    )
    return bool(supplemental) and is_noisy_signal_text(supplemental)


def cleanup_signal_noise(*, db_path: Path = DB_PATH) -> dict[str, object]:
    archived_counts: dict[str, int] = {}
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_signal_archive_table(conn)
        for table, id_column in _TABLES:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()  # noqa: S608
            archived = 0
            for row in rows:
                if not _row_is_noise(row):
                    continue
                _archive_row(
                    conn,
                    table=table,
                    id_column=id_column,
                    row=row,
                    reason="Signal noise cleanup archived low-signal conversational residue.",
                )
                archived += 1
            if table == "runtime_reflection_signals":
                archived += _archive_low_support_run_audit_rows(
                    conn,
                    table=table,
                    id_column=id_column,
                    keep_latest=_RECENT_KEEP[table],
                    where_clause=(
                        "signal_type = 'post_run_reflection' "
                        "AND source_kind = 'cadence_producer' "
                        "AND support_count <= 1 "
                        "AND session_count <= 1"
                    ),
                )
            if table == "runtime_witness_signals":
                archived += _archive_low_support_run_audit_rows(
                    conn,
                    table=table,
                    id_column=id_column,
                    keep_latest=_RECENT_KEEP[table],
                    where_clause=(
                        "signal_type = 'visible_run_observed' "
                        "AND source_kind = 'visible_run' "
                        "AND support_count <= 1 "
                        "AND session_count <= 1"
                    ),
                )
            archived_counts[table] = archived
        conn.commit()

        remaining = {
            table: int(
                conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
            )
            for table, _ in _TABLES
        }
    return {"db_path": str(db_path), "archived": archived_counts, "remaining": remaining}


def _archive_low_support_run_audit_rows(
    conn: sqlite3.Connection,
    *,
    table: str,
    id_column: str,
    keep_latest: int,
    where_clause: str,
) -> int:
    rows = conn.execute(
        f"""
        SELECT *
        FROM {table}
        WHERE {where_clause}
        ORDER BY updated_at DESC
        """,  # noqa: S608
    ).fetchall()
    if len(rows) <= keep_latest:
        return 0
    archived = 0
    for row in rows[keep_latest:]:
        _archive_row(
            conn,
            table=table,
            id_column=id_column,
            row=row,
            reason="Signal noise cleanup archived low-support run-audit residue.",
        )
        archived += 1
    return archived


def main() -> None:
    result = cleanup_signal_noise()
    print("Signal noise cleanup completed")
    print(f"DB: {result['db_path']}")
    print("Archived:")
    for table, count in result["archived"].items():
        print(f"  {table}: {count}")
    print("Remaining:")
    for table, count in result["remaining"].items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
