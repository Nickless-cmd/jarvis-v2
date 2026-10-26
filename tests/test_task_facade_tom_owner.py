"""Task-facaden: en TOM owner maa ikke goere vaerktoejet ubrugeligt (26/10-2026).

Maalt 26/10-2026 efter en genstart: `current_user_id()` er tom i runtime-processen,
fordi ContextVar'en saettes i API'ets middleware og ikke i runtime-turen. Facaden
sammenlignede `session_owner != owner` og afviste derfor HVERT `Task`-kald med
"sessionen tilhoerer en anden ejer" — ogsaa fra ejerens egen session.

Vaernet skal stadig lukke den vej der betyder noget: en IKKE-tom owner der afviger
fra sessionens ejer. Denne test er et par — begge sider maa vaere sande.

Testen bruger en RIGTIG sqlite-motor med egne raekker (in-memory), ikke en stub:
en fake der svarer ens uanset SQL kan ikke se om `WHERE session_id=?` rammer den
rige session. Det var praecis den fejl der gjorde den foerste udgave af denne test
groen af den forkerte grund — conftest's prod-DB-shield pegede `connect()` paa en
tom database, saa testen maalte shield'en og ikke logikken.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager

import pytest

from core.services.agent_task_facade import _session_scope

SESSION = "chat-test-session"
EJER = "1246415163603816499"
FREMMED = "999999999999999999"


def _conn_with(rows: list[tuple[str, str, str, str]]) -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE chat_sessions ("
        " session_id TEXT PRIMARY KEY, owner_user_id TEXT,"
        " workspace_kind TEXT, workspace_root TEXT)"
    )
    conn.executemany(
        "INSERT INTO chat_sessions VALUES (?,?,?,?)", rows
    )
    return conn


@contextmanager
def _patched(monkeypatch, rows):
    """Peg facadens `connect()` paa en in-memory base med praecis disse raekker."""
    conn = _conn_with(rows)

    @contextmanager
    def _fake_connect():
        yield conn

    import core.runtime.db as db_mod

    monkeypatch.setattr(db_mod, "connect", _fake_connect)
    monkeypatch.setattr(
        db_mod, "_ensure_chat_session_workspace_columns", lambda _c: None
    )
    yield conn
    conn.close()


def test_tom_owner_arver_sessionens_ejer(monkeypatch):
    """Regressionen: tom ContextVar gav 'sessionen tilhoerer en anden ejer'."""
    with _patched(monkeypatch, [(SESSION, EJER, "workstation", "/media/projects/jarvis-v2")]):
        kind, root = _session_scope("", SESSION)
    assert kind == "workstation"
    assert root == "/media/projects/jarvis-v2"


def test_rigtig_owner_virker_uændret(monkeypatch):
    with _patched(monkeypatch, [(SESSION, EJER, "workstation", "/media/projects/jarvis-v2")]):
        kind, root = _session_scope(EJER, SESSION)
    assert kind == "workstation"


def test_fremmed_owner_afvises_stadig(monkeypatch):
    """Den ene vej vaernet SKAL lukke: en anden bruger maa ikke laane sessionen."""
    with _patched(monkeypatch, [(SESSION, EJER, "workstation", "/media/projects/jarvis-v2")]):
        with pytest.raises(ValueError, match="anden ejer"):
            _session_scope(FREMMED, SESSION)


def test_ukendt_session_giver_tom_scope(monkeypatch):
    with _patched(monkeypatch, [(SESSION, EJER, "workstation", "/media/projects/jarvis-v2")]):
        assert _session_scope(EJER, "chat-findes-ikke") == ("", "")


def test_where_rammer_kun_den_rige_session(monkeypatch):
    """To sessioner i samme base: opslaget maa ikke laane den forkerte ejer."""
    with _patched(
        monkeypatch,
        [
            (SESSION, EJER, "workstation", "/media/projects/jarvis-v2"),
            ("chat-anden", FREMMED, "workstation", "/tmp/anden"),
        ],
    ):
        with pytest.raises(ValueError, match="anden ejer"):
            _session_scope(FREMMED, SESSION)
        kind, root = _session_scope(FREMMED, "chat-anden")
    assert (kind, root) == ("workstation", "/tmp/anden")


def test_repo_alias_oploses(monkeypatch):
    """Desk gemmer server-roden som 'repo'; facaden skal oplose den til en sti."""
    with _patched(monkeypatch, [(SESSION, EJER, "workstation", "repo")]):
        _kind, root = _session_scope(EJER, SESSION)
    assert root.endswith("jarvis-v2")
