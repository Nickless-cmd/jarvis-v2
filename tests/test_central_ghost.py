"""Spøgelset læser hans seneste svar — kun hans.

LÆKKEN, 26/9-2026: `chat_messages` er ÉN pulje for alle brugere, og denne
læser hentede uden `workspace_name`-filter — andres ord endte i Bjørns
signaler.

Testen måler hvad der faktisk NÅR databasen, ikke hvad funktionen ender med
at returnere. De fleste af disse læsere filtrerer videre bagefter (tærskler,
længder, mønstre), så et tomt slutresultat ville få testen til at bestå uden
at bevise noget. Det er selve forespørgslen der skal være afgrænset.

Strukturvagten mod hele kodebasen står i `tests/test_samtale_scope.py`.
"""
from __future__ import annotations

import sqlite3

import pytest

import core.services.central_ghost as M


class _Optager:
    """Rigtig SQLite, men hver `execute` mod chat_messages skrives ned."""

    def __init__(self, conn):
        self._c = conn
        self.kald: list[tuple[str, tuple]] = []
        self.raekker: list[str] = []

    def execute(self, sql, params=()):
        cur = self._c.execute(sql, params)
        if "chat_messages" in sql.lower():
            self.kald.append((" ".join(sql.split()), tuple(params)))
            rows = cur.fetchall()
            self.raekker += [str(v) for r in rows for v in tuple(r)]
            return _Svar(rows)
        return cur

    def __getattr__(self, n):
        return getattr(self._c, n)


class _Svar:
    def __init__(self, rows): self._r = rows
    def fetchall(self): return self._r
    def fetchone(self): return self._r[0] if self._r else None
    def __iter__(self): return iter(self._r)


@pytest.fixture()
def optager(tmp_path, monkeypatch):
    c = sqlite3.connect(tmp_path / "to.db")
    c.execute("CREATE TABLE chat_messages (id INTEGER PRIMARY KEY, session_id TEXT, "
              "role TEXT, content TEXT, created_at TEXT, workspace_name TEXT)")
    c.executemany(
        "INSERT INTO chat_messages (session_id, role, content, created_at, workspace_name) "
        "VALUES (?,?,?,?,?)",
        [("s1", "assistant", "bjoerns egen saetning her om noget", "2026-09-26T10:00:00+00:00", "bjorn"),
         ("s2", "assistant", "michelles private saetning om noget", "2026-09-26T10:01:00+00:00", "michelle")])
    c.commit()
    c.row_factory = sqlite3.Row
    opt = _Optager(c)

    class _C:
        def __enter__(self): return opt
        def __exit__(self, *a): return False

    monkeypatch.setattr(__import__('core.runtime.db_core', fromlist=['connect']), "connect", lambda *a, **k: _C(), raising=False)
    yield opt
    c.close()


def _kald():
    try:
        M._recent_texts(limit=10)
    except Exception:
        pass        # laeseren maa gerne fejle videre nede; vi maaler forespoergslen


def test_forespoergslen_er_bundet_til_EN_workspace(optager, monkeypatch):
    monkeypatch.setattr(M, "aktuel_samtale_workspace", lambda: "bjorn")
    _kald()
    assert optager.kald, "der blev slet ikke spurgt mod chat_messages"
    for sql, params in optager.kald:
        assert "workspace_name" in sql, sql
        assert "bjorn" in params, (sql, params)
    assert not any("michelles" in r for r in optager.raekker), \
        "en anden brugers raekke kom tilbage"


def test_ubestemmelig_workspace_giver_INTET(optager, monkeypatch):
    # Fail-closed. Et tomt signal er forkert på en måde man kan måle;
    # et signal bygget på en fremmeds ord er det ikke.
    monkeypatch.setattr(M, "aktuel_samtale_workspace", lambda: "")
    _kald()
    assert not optager.raekker, optager.raekker
