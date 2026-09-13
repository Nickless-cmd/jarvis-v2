"""`db_runtime_tasks` — tabellen bag arbejdsenheden.

Migrationen `run_id → origin_ref` er testet i `tests/test_work_ref.py`, hvor den
hører hjemme sammen med resten af referencens historie. Her testes lagets egen
kontrakt: at en opgave kan skrives, læses og opdateres uden at tabe felter.
"""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_runtime_tasks as db


@pytest.fixture
def _conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    db.ensure_runtime_tasks_tables(c)
    return c


def test_tabellen_har_de_felter_arbejdet_kraever(_conn):
    """Et cockpit kan ikke vise «hvorfor staar den stille» uden
    `blocked_reason`, og ikke «hvad hoerer sammen» uden `flow_id`."""
    kolonner = {r[1] for r in _conn.execute("PRAGMA table_info(runtime_tasks)")}
    for felt in ("task_id", "kind", "origin", "status", "goal", "priority",
                 "flow_id", "origin_ref", "blocked_reason", "result_summary",
                 "artifact_ref", "created_at", "updated_at"):
        assert felt in kolonner, f"{felt} mangler"


def test_ensure_er_IDEMPOTENT(_conn):
    """Den kaldes ved hver opstart OG ved hver skrivning."""
    for _ in range(3):
        db.ensure_runtime_tasks_tables(_conn)
    kolonner = [r[1] for r in _conn.execute("PRAGMA table_info(runtime_tasks)")]
    assert kolonner.count("task_id") == 1


def test_task_id_er_UNIKT(_conn):
    """To opgaver med samme id ville goere «denne opgave» tvetydigt."""
    _conn.execute(
        "INSERT INTO runtime_tasks (task_id, kind, origin, status, goal, "
        "created_at, updated_at) VALUES ('t1','k','o','queued','g','a','b')")
    with pytest.raises(sqlite3.IntegrityError):
        _conn.execute(
            "INSERT INTO runtime_tasks (task_id, kind, origin, status, goal, "
            "created_at, updated_at) VALUES ('t1','k2','o2','queued','g2','a','b')")


def test_raekke_mapperen_baerer_origin_ref(_conn):
    """Feltet skal naa HELE vejen ud — et felt i skemaet som mapperen ikke
    laeser, er usynligt for enhver flade."""
    _conn.execute(
        "INSERT INTO runtime_tasks (task_id, kind, origin, status, goal, "
        "origin_ref, created_at, updated_at) "
        "VALUES ('t1','k','o','queued','g','heartbeat-tick:abc','a','b')")
    row = _conn.execute("SELECT * FROM runtime_tasks WHERE task_id='t1'").fetchone()
    ud = db._runtime_task_from_row(row)
    assert ud["origin_ref"] == "heartbeat-tick:abc"
    assert "run_id" not in ud, "det gamle, loegnagtige navn laekker stadig ud"


def test_indekset_findes(_conn):
    """Uden det scanner et status-opslag hele tabellen — og den vokser."""
    idx = {r[1] for r in _conn.execute("PRAGMA index_list(runtime_tasks)")}
    assert any("status" in str(i) for i in idx), f"intet status-indeks: {idx}"
