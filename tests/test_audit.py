"""`claude_dispatch.audit` — revisionsrækken for én dispatch.

Filen findes fordi dæknings-gaten (med rette) kræver en test ved siden af
modulet. Men den er ikke formalia: `finalize_audit_row` har en betingelse i sin
`WHERE` der er let at overse, og som er hele grunden til at en færdig dispatch
ikke kan få sit udfald overskrevet bagefter.

Kanten «hvilken tur startede denne dispatch» testes i
`tests/test_dispatch_ophav.py`.
"""
from __future__ import annotations

import json
import sqlite3

import pytest

from core.tools.claude_dispatch import audit


@pytest.fixture
def _db(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE claude_dispatch_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            started_at TEXT NOT NULL, ended_at TEXT,
            spec_json TEXT NOT NULL, status TEXT NOT NULL,
            tokens_used INTEGER NOT NULL DEFAULT 0,
            exit_code INTEGER, diff_summary TEXT, error TEXT)"""
    )

    class _Wrap:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    monkeypatch.setattr(audit, "connect", lambda: _Wrap())
    monkeypatch.setattr(audit, "_ophav", lambda: ("", ""))
    return conn


def _spec():
    from core.tools.claude_dispatch.spec import parse_spec
    return parse_spec({"goal": "goer noget", "scope_files": ["core/x.py"],
                       "allowed_tools": ["Read"]})


def _raekke(conn, task_id="t1"):
    return conn.execute(
        "SELECT * FROM claude_dispatch_audit WHERE task_id=?", (task_id,)).fetchone()


def test_start_skriver_en_raekke_som_KOERENDE(_db):
    audit.start_audit_row("t1", _spec())
    r = _raekke(_db)
    assert r["status"] == "running"
    assert r["tokens_used"] == 0
    assert r["ended_at"] is None


def test_start_gemmer_HELE_spec_en(_db):
    """Uden spec'en kan man ikke bagefter se hvad dispatchen fik lov til —
    og et revisionsspor uden mandatet er ikke et revisionsspor."""
    audit.start_audit_row("t1", _spec())
    spec = json.loads(_raekke(_db)["spec_json"])
    assert spec["goal"] == "goer noget"
    assert spec["scope_files"] == ["core/x.py"]
    assert spec["allowed_tools"] == ["Read"]


def test_finalize_saetter_udfaldet(_db):
    audit.start_audit_row("t1", _spec())
    audit.finalize_audit_row("t1", status="completed", tokens_used=1234,
                             exit_code=0, diff_summary="2 filer", error=None)
    r = _raekke(_db)
    assert r["status"] == "completed"
    assert r["tokens_used"] == 1234
    assert r["exit_code"] == 0
    assert r["diff_summary"] == "2 filer"
    assert r["ended_at"]


def test_finalize_roerer_KUN_en_koerende_raekke(_db):
    """`WHERE ... AND status='running'` er ikke pynt.

    Uden den kunne et sent svar fra en opgivet proces overskrive udfaldet paa
    en dispatch der allerede var gjort op — samme familie som de
    generations-hegn klienterne fik i dag.
    """
    audit.start_audit_row("t1", _spec())
    audit.finalize_audit_row("t1", status="completed", tokens_used=100,
                             exit_code=0, diff_summary="foerste", error=None)
    audit.finalize_audit_row("t1", status="failed", tokens_used=999,
                             exit_code=1, diff_summary="sent svar", error="hov")
    r = _raekke(_db)
    assert r["status"] == "completed", "et sent svar overskrev et faerdigt udfald"
    assert r["tokens_used"] == 100
    assert r["diff_summary"] == "foerste"


def test_finalize_paa_et_ukendt_task_id_er_en_no_op(_db):
    audit.finalize_audit_row("findes-ikke", status="completed", tokens_used=1,
                             exit_code=0, diff_summary=None, error=None)
    assert _raekke(_db, "findes-ikke") is None


def test_fejlede_dispatches_beholder_deres_fejl(_db):
    audit.start_audit_row("t1", _spec())
    audit.finalize_audit_row("t1", status="failed", tokens_used=7,
                             exit_code=2, diff_summary=None, error="kvote opbrugt")
    r = _raekke(_db)
    assert r["status"] == "failed" and r["error"] == "kvote opbrugt"
