"""One-shot migration: copy memory_emotional_context rows into emotional_memory_anchors.

Idempotent — safe to run multiple times. Leaves the legacy table intact;
deletion is a separate later commit once the new system has proven itself
in production.

Usage:
    conda activate ai
    python scripts/migrate_emotional_memory.py
"""
from __future__ import annotations

import json
import logging
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.runtime.db import (  # noqa: E402
    connect,
    get_emotional_memory_anchor,
    insert_emotional_memory_anchor,
)

logger = logging.getLogger(__name__)


def migrate(*, batch_size: int = 500) -> dict[str, int]:
    """Migrate legacy rows into the new table.

    Returns {"migrated": N, "skipped": M} where skipped counts both rows
    already present in the new table and rows that failed to copy.
    """
    migrated = 0
    skipped = 0

    with connect() as conn:
        if not _legacy_table_exists(conn):
            return {"migrated": 0, "skipped": 0}
        rows = conn.execute(
            "SELECT heading_normalized, heading_display, mood, intensity, "
            "captured_at, source, notes FROM memory_emotional_context"
        ).fetchall()

    for row in rows:
        anchor_id = str(row["heading_normalized"])
        try:
            existing = get_emotional_memory_anchor("memory_heading", anchor_id)
            if existing is not None:
                skipped += 1
                continue
            insert_emotional_memory_anchor(
                anchor_type="memory_heading",
                anchor_id=anchor_id,
                captured_at=str(row["captured_at"]),
                mood=str(row["mood"]),
                intensity=float(row["intensity"]),
                context_features_json=json.dumps(
                    {"heading_display": row["heading_display"]},
                    ensure_ascii=False,
                ),
                source=row["source"],
                notes=row["notes"],
            )
            migrated += 1
        except Exception as exc:
            logger.warning("migration: failed for %s: %s", anchor_id, exc)
            skipped += 1

    return {"migrated": migrated, "skipped": skipped}


def _legacy_table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_emotional_context'"
    ).fetchone()
    return row is not None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    stats = migrate()
    print(f"migrated={stats['migrated']} skipped={stats['skipped']}")
