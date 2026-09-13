"""Index-connection lifecycle (fix 2026-09-13).

Rod-årsag målt 13. sep 2026: 98 "database is locked" på 36 timer på tværs af
b4_catchup_infer (72), reindex_loop (15) og memory_pruning (9).

connect_index() havde tre problemer:
  1. journal_mode=delete — én skrive-lock pr. commit, mens mange samtidige
     daemons skrev til den samme 505 MB-fil.
  2. busy_timeout=0 — ingen venten ved lock; fejl i det øjeblik den var taget.
  3. executescript(_INDEX_SCHEMA) + migrations + commit ved HVERT kald, så selv
     rene læsninger tog en skrive-lock og kolliderede med skriverne.

Disse tests låser fixen fast.
"""
from __future__ import annotations

import threading
from pathlib import Path

import pytest


@pytest.fixture
def brain(tmp_path, monkeypatch):
    from core.services import jarvis_brain

    monkeypatch.setattr(jarvis_brain, "_workspace_root", lambda: tmp_path / "ws")
    monkeypatch.setattr(jarvis_brain, "_state_root", lambda: tmp_path / "state")
    return jarvis_brain


def test_connect_index_enables_wal(brain):
    conn = brain.connect_index()
    try:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    assert str(mode).lower() == "wal"


def test_connect_index_sets_busy_timeout(brain):
    conn = brain.connect_index()
    try:
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    finally:
        conn.close()
    assert int(timeout) == 30000


def test_schema_migration_runs_once_not_per_call(brain, monkeypatch):
    """Regression: DDL må ikke køre ved hvert connect — det var lock-kilden."""
    calls: list[int] = []
    original = brain._ensure_index_schema_migrations

    def spy(conn):
        calls.append(1)
        return original(conn)

    monkeypatch.setattr(brain, "_ensure_index_schema_migrations", spy)
    brain._SCHEMA_READY.clear()

    for _ in range(3):
        conn = brain.connect_index()
        conn.close()

    assert len(calls) == 1, f"schema-DDL kørte {len(calls)} gange, forventet 1"


def test_schema_is_recreated_if_db_file_replaced(brain):
    """Hvis filen skiftes eller nulstilles under os, skal schemaet genskabes."""
    conn = brain.connect_index()
    conn.close()
    assert str(brain.index_db_path()) in brain._SCHEMA_READY

    for suffix in ("", "-wal", "-shm"):
        Path(str(brain.index_db_path()) + suffix).unlink(missing_ok=True)

    conn = brain.connect_index()
    try:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='brain_index'"
        ).fetchone()
    finally:
        conn.close()
    assert row, "brain_index blev ikke genskabt efter filen forsvandt"


def test_concurrent_writers_do_not_lock(brain):
    """Regression for de 98 lock-fejl: samtidige skrivere må ikke fejle."""
    brain.connect_index().close()  # sæt WAL + schema op først

    errors: list[Exception] = []

    def worker(i: int) -> None:
        try:
            conn = brain.connect_index()
            conn.execute(
                "INSERT INTO brain_proposals(id, path, reason, created_at, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"p{i}", "x", "r", "2026-01-01T00:00:00+00:00", "pending"),
            )
            conn.commit()
            conn.close()
        except Exception as exc:  # noqa: BLE001 — vi vil se præcis hvad der fejler
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"lock-fejl under samtidige skrivere: {errors}"

    conn = brain.connect_index()
    try:
        count = conn.execute("SELECT COUNT(*) FROM brain_proposals").fetchone()[0]
    finally:
        conn.close()
    assert count == 12
