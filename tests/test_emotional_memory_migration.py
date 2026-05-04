from __future__ import annotations


def test_migration_copies_legacy_rows(isolated_runtime) -> None:
    from core.runtime.db import connect, list_emotional_memory_anchors
    from scripts.migrate_emotional_memory import migrate

    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_emotional_context (
                heading_normalized TEXT PRIMARY KEY,
                heading_display    TEXT NOT NULL,
                mood               TEXT NOT NULL,
                intensity          REAL NOT NULL,
                captured_at        TEXT NOT NULL,
                source             TEXT,
                notes              TEXT
            )
            """
        )
        conn.execute(
            """INSERT INTO memory_emotional_context
               (heading_normalized, heading_display, mood, intensity,
                captured_at, source, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("h-1", "## H1", "calm", 0.3, "2026-05-01T10:00:00+00:00", "x", None),
        )
        conn.execute(
            """INSERT INTO memory_emotional_context VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("h-2", "## H2", "frustrated", 0.7, "2026-05-02T10:00:00+00:00", "y", "n"),
        )

    stats = migrate()
    assert stats["migrated"] == 2

    rows = list_emotional_memory_anchors(anchor_type="memory_heading", limit=10)
    assert len(rows) == 2
    moods = sorted(r["mood"] for r in rows)
    assert moods == ["calm", "frustrated"]


def test_migration_is_idempotent(isolated_runtime) -> None:
    from core.runtime.db import connect, list_emotional_memory_anchors
    from scripts.migrate_emotional_memory import migrate

    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_emotional_context (
                heading_normalized TEXT PRIMARY KEY,
                heading_display    TEXT NOT NULL,
                mood               TEXT NOT NULL,
                intensity          REAL NOT NULL,
                captured_at        TEXT NOT NULL,
                source             TEXT,
                notes              TEXT
            )
            """
        )
        conn.execute(
            """INSERT INTO memory_emotional_context VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("h-1", "## H1", "calm", 0.3, "2026-05-01T10:00:00+00:00", "x", None),
        )

    s1 = migrate()
    s2 = migrate()
    assert s1["migrated"] == 1
    assert s2["migrated"] == 0
    rows = list_emotional_memory_anchors(anchor_type="memory_heading")
    assert len(rows) == 1


def test_migration_handles_missing_legacy_table(isolated_runtime) -> None:
    from scripts.migrate_emotional_memory import migrate
    stats = migrate()
    assert stats["migrated"] == 0
    assert stats["skipped"] == 0
