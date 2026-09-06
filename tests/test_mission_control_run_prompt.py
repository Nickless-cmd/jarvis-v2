"""Run-detalje og prompt-sammensætning: scoping + ærlig tomhed."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.jarvis_api.routes import mission_control_dashboard as mcd
from core.identity import workspace_context as wc


@pytest.fixture
def klient(tmp_path, monkeypatch):
    import sqlite3

    sti = tmp_path / "t.db"
    # check_same_thread: TestClient kører requesten i en ANDEN tråd, og en
    # tråd-fejl ville give samme svar som «ingen adgang» — så scoping-testene
    # ville bestå af den forkerte grund.
    conn = sqlite3.connect(sti, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE visible_runs (run_id TEXT, lane TEXT, provider TEXT, model TEXT,
          status TEXT, started_at TEXT, finished_at TEXT, text_preview TEXT,
          error TEXT, capability_id TEXT, user_id TEXT DEFAULT '');
        CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT,
          payload_json TEXT, created_at TEXT);
        """
    )
    conn.execute("INSERT INTO visible_runs (run_id, lane, provider, model, status, user_id)"
                 " VALUES ('r-min','visible','p','m','completed','bjorn')")
    conn.execute("INSERT INTO visible_runs (run_id, lane, provider, model, status, user_id)"
                 " VALUES ('r-anden','visible','p','m','completed','anden')")
    conn.execute(
        "INSERT INTO events (kind, payload_json, created_at) VALUES (?,?,?)",
        ("prompt.section_answer_impact",
         json.dumps({"run_id": "r-min", "answer_chars": 765,
                     "sections": [{"label": "SOUL.md", "chars": 7705},
                                  {"label": "Regler", "chars": 2634}]}),
         "2026-09-06T12:00:00+00:00"),
    )
    conn.commit()

    class Forbindelse:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    monkeypatch.setattr("core.runtime.db.connect", lambda *a, **k: Forbindelse())
    app = FastAPI()
    app.include_router(mcd.router, prefix="/mc")
    return TestClient(app)


def test_ejeren_ser_sin_prompt_sammensaetning(klient, monkeypatch):
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    monkeypatch.setattr(wc, "current_user_id", lambda: "bjorn")
    d = klient.get("/mc/runs/r-min/prompt").json()
    assert d["found"] is True
    assert d["section_count"] == 2
    # Sorteret efter fylde, så det tungeste står øverst.
    assert d["sections"][0]["label"] == "SOUL.md"
    assert d["sections"][0]["pct"] == pytest.approx(74.5, abs=0.2)


def test_en_anden_bruger_faar_intet(klient, monkeypatch):
    """Listen var scopet; detaljen stod åben ved siden af med et kendt run_id."""
    monkeypatch.setattr(wc, "current_role", lambda: "member")
    monkeypatch.setattr(wc, "current_user_id", lambda: "mikkel")
    d = klient.get("/mc/runs/r-min/prompt").json()
    assert d["found"] is False
    assert "error" not in d, f"afvist af en FEJL, ikke af scoping: {d.get('error')}"
    assert klient.get("/mc/runs/r-min").json()["run"] is None


def test_manglende_post_siges_aabent(klient, monkeypatch):
    """13 af 200 runs mangler posten — tom liste må ikke ligne en tom prompt."""
    monkeypatch.setattr(wc, "current_role", lambda: "owner")
    monkeypatch.setattr(wc, "current_user_id", lambda: "bjorn")
    d = klient.get("/mc/runs/r-anden/prompt").json()
    assert d["found"] is False and d["sections"] == []
