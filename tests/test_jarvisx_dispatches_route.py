"""`GET /api/dispatches` skal svare med LISTEN — ikke med en kolonne-hjaelper.

13/9-2026 blev `_felt` indsat mellem `@router.get("/dispatches")` og
`list_dispatches`. Python bandt dekoratoren til det foerste `def` under den,
saa FastAPI eksponerede kolonne-opslaget `_felt(row, navn)` som ruten.
`list_dispatches` stod udekoreret og kunne ikke naas.

Intet fejlede hoejt: mobilens artefakt-skaerm fik en fejl, slugte den i en
`catch { return [] }` og viste «Ingen artifacts endnu» i fem dage — det samme
som en tom database. Fundet 18/9 da desk skulle have en artefakt-menu bygget
paa samme endpoint.
"""
from __future__ import annotations

import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _rute(sti: str):
    from apps.api.jarvis_api.routes.jarvisx_dispatches import router
    return next(
        r for r in router.routes
        if getattr(r, "path", "").endswith(sti) and "GET" in getattr(r, "methods", set())
    )


def test_listen_er_bundet_til_list_dispatches() -> None:
    # Den strukturelle fejl selv: HVILKEN funktion sidder ruten paa?
    assert _rute("/dispatches").endpoint.__name__ == "list_dispatches"


def test_hjaelperen_er_ikke_en_rute() -> None:
    from apps.api.jarvis_api.routes.jarvisx_dispatches import router
    navne = {getattr(r, "endpoint", None).__name__ for r in router.routes if getattr(r, "endpoint", None)}
    assert "_felt" not in navne


@pytest.fixture
def klient(monkeypatch):
    conn = sqlite3.connect(":memory:", check_same_thread=False)
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
    conn.execute(
        "INSERT INTO claude_dispatch_audit (task_id, started_at, ended_at, spec_json, status, diff_summary)"
        " VALUES ('abc123', '2026-09-18T10:00:00Z', '2026-09-18T10:05:00Z',"
        " '{\"prompt\": \"ret login\"}', 'done', ' 1 file changed, 3 insertions(+)')"
    )

    class _Wrap:
        def __enter__(self): return conn
        def __exit__(self, *a): return False

    import core.runtime.db as db
    monkeypatch.setattr(db, "connect", lambda *a, **k: _Wrap())

    from apps.api.jarvis_api.routes import jarvisx_dispatches as mod
    from core.runtime.jarvisx_auth import require_owner

    app = FastAPI()
    app.include_router(mod.router)
    app.dependency_overrides[require_owner] = lambda: None
    return TestClient(app)


def test_svarer_med_listen_og_dens_raekker(klient) -> None:
    sti = _rute("/dispatches").path
    r = klient.get(sti)

    assert r.status_code == 200, r.text
    krop = r.json()
    # Foer rettelsen var svaret en STRENG (kolonne-hjaelperens returvaerdi).
    assert isinstance(krop, dict)
    assert krop["count"] == 1
    d = krop["dispatches"][0]
    assert d["task_id"] == "abc123"
    assert "insertions" in d["diff_summary"]
