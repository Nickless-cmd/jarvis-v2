"""The SQLite drift guard must reject schema and timestamp changes."""
import sqlite3

from scripts import verify_sqlite_schema as guard


def test_canonical_schema_ignores_creation_order_but_rejects_drift():
    first = sqlite3.connect(":memory:")
    second = sqlite3.connect(":memory:")
    first.executescript("""
        CREATE TABLE alpha (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL);
        CREATE INDEX ix_alpha_created ON alpha(created_at);
        CREATE TABLE beta (value TEXT DEFAULT 'x');
        INSERT INTO alpha VALUES (1, '2026-09-29T07:38:59.148486+00:00');
    """)
    second.executescript("""
        CREATE TABLE beta (value TEXT DEFAULT 'x');
        CREATE TABLE alpha (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL);
        CREATE INDEX ix_alpha_created ON alpha(created_at);
        INSERT INTO alpha VALUES (1, '2026-09-29T07:38:59.148486+00:00');
    """)
    expected = guard.inventory(first)
    assert guard.inventory(second) == expected
    second.execute("ALTER TABLE beta ADD COLUMN status TEXT NOT NULL DEFAULT 'new'")
    assert guard.compare(guard.inventory(second), expected) == [
        "CHANGED beta.digest: " + expected["tables"]["beta"]["digest"]
        + " -> " + guard.inventory(second)["tables"]["beta"]["digest"]
    ]


def test_timestamp_format_drift_is_separate_from_schema_digest():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, created_at TEXT)")
    conn.execute("INSERT INTO events VALUES (1, '2026-09-29T07:38:59.148486+00:00')")
    expected = guard.inventory(conn)
    conn.execute("INSERT INTO events VALUES (2, '2026-09-29 05:30:26')")
    actual = guard.inventory(conn)
    assert actual["tables"]["events"]["digest"] == expected["tables"]["events"]["digest"]
    assert guard.compare(actual, expected) == [
        "CHANGED events.created_at_formats: ['iso_utc_offset'] -> "
        "['iso_utc_offset', 'sqlite_utc_seconds']"
    ]


def test_new_table_and_third_format_are_visible():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (created_at TEXT)")
    expected = guard.inventory(conn)
    conn.execute("CREATE TABLE next_events (created_at TEXT)")
    conn.execute("INSERT INTO next_events VALUES ('2026-09-29T07:38:59Z')")
    actual = guard.inventory(conn)
    assert actual["tables"]["next_events"]["created_at_formats"] == ["iso_utc_z"]
    assert guard.compare(actual, expected) == ["NEW next_events"]


def test_partial_index_predicate_changes_digest():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE events (id INTEGER, status TEXT)")
    conn.execute("CREATE INDEX ix_events ON events(status) WHERE status = 'open'")
    expected = guard.inventory(conn)
    conn.execute("DROP INDEX ix_events")
    conn.execute("CREATE INDEX ix_events ON events(status) WHERE status = 'closed'")
    assert guard.inventory(conn)["tables"]["events"]["digest"] != expected["tables"]["events"]["digest"]


def test_precommit_skips_non_runtime_host(monkeypatch, tmp_path):
    monkeypatch.setattr(guard.socket, "gethostname", lambda: "developer-laptop")
    assert guard.main(["--only-host", "Jarvis", "--require-db",
                       "--db", str(tmp_path / "missing.db")]) == 0
