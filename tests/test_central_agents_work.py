"""Subagent-arbejdskort: læser agent_runs, ikke den nerve der ikke fyrer."""
from __future__ import annotations

import pytest

from core.services import central_agents_surface as cas


@pytest.fixture
def db(monkeypatch):
    import sqlite3

    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE agent_registry (agent_id TEXT PRIMARY KEY, role TEXT,"
        " kind TEXT, goal TEXT)"
    )
    conn.execute(
        "INSERT INTO agent_registry VALUES ('a1','researcher','subagent','find kilder')"
    )
    conn.commit()

    class Forbindelse:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    monkeypatch.setattr("core.runtime.db.connect", lambda *a, **k: Forbindelse())
    return conn


def _run(**o):
    grund = {
        "run_id": "r1", "agent_id": "a1", "status": "completed",
        "execution_mode": "solo-task", "model": "m", "input_summary": "ind",
        "output_summary": "ud", "started_at": "", "finished_at": "",
        "input_tokens": 100, "output_tokens": 50, "cost_usd": 0.0123,
    }
    return {**grund, **o}


def test_haefter_rollen_paa_fra_registret(db, monkeypatch):
    monkeypatch.setattr(
        "core.runtime.db_agent_runtime.list_agent_runs", lambda **k: [_run()]
    )
    d = cas.build_recent_agent_work(limit=5)
    assert d["antal"] == 1
    kort = d["runs"][0]
    assert kort["role"] == "researcher"
    assert kort["goal"] == "find kilder"
    assert kort["tokens"] == 150          # ind + ud lagt sammen
    assert kort["cost_usd"] == 0.0123


def test_ukendt_agent_faar_tomt_rollefelt_ikke_et_gaet(db, monkeypatch):
    monkeypatch.setattr(
        "core.runtime.db_agent_runtime.list_agent_runs",
        lambda **k: [_run(agent_id="ukendt")],
    )
    assert cas.build_recent_agent_work()["runs"][0]["role"] == ""


def test_registret_maa_ikke_vaelte_listen(monkeypatch):
    """Kan registret ikke læses, skal kørslerne stadig vises."""
    def eksploder(*a, **k):
        raise RuntimeError("db nede")

    monkeypatch.setattr("core.runtime.db.connect", eksploder)
    monkeypatch.setattr(
        "core.runtime.db_agent_runtime.list_agent_runs", lambda **k: [_run()]
    )
    d = cas.build_recent_agent_work()
    assert d["antal"] == 1 and d["runs"][0]["role"] == ""


def test_tom_liste_naar_der_intet_er(monkeypatch):
    monkeypatch.setattr("core.runtime.db_agent_runtime.list_agent_runs", lambda **k: [])
    assert cas.build_recent_agent_work() == {"runs": [], "antal": 0}


def test_grænsen_holdes_indenfor_1_til_100(db, monkeypatch):
    set_limit = {}
    def fanget(**k):
        set_limit.update(k); return []
    monkeypatch.setattr("core.runtime.db_agent_runtime.list_agent_runs", fanget)
    cas.build_recent_agent_work(limit=9999)
    assert set_limit["limit"] == 100
    cas.build_recent_agent_work(limit=0)
    assert set_limit["limit"] == 1
