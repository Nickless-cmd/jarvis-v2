from __future__ import annotations

import sqlite3
import threading

from core.runtime import db as runtime_db
import core.runtime.db_core as db_core


def test_connection_pool_reconnects_on_db_path_change(monkeypatch, tmp_path) -> None:
    # Regression (2026-07-24): the thread-local connection pool must not reuse a
    # connection after DB_PATH is repointed. Tests repoint DB_PATH per-test; a stale
    # pooled conn to a PRIOR db leaked state across tests ("no such table" / bled-over
    # rows) and was the root cause of ~70 full-suite failures.
    db_core.close_pooled_connection()
    a, b = tmp_path / "a.db", tmp_path / "b.db"
    monkeypatch.setattr(db_core, "DB_PATH", a)
    with runtime_db.connect() as conn:
        conn.execute("CREATE TABLE marker(x)")
        conn.commit()
    monkeypatch.setattr(db_core, "DB_PATH", b)
    with runtime_db.connect() as conn:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "marker" not in names  # fresh DB b, not the stale pooled conn to a.db
    db_core.close_pooled_connection()  # don't leak pool state into the next test


def test_connect_context_manager_closes_connection(monkeypatch, tmp_path) -> None:
    # With pooling DISABLED, connect() returns a ClosingConnection that closes on
    # context exit. (Pooled connections deliberately stay open for reuse — the perf
    # optimisation added 2026-07-12 — so this closing invariant is the NOPOOL path.)
    monkeypatch.setattr(db_core, "_POOL_DISABLED", True)
    db_path = tmp_path / "jarvis.db"
    monkeypatch.setattr(db_core, "DB_PATH", db_path)

    with runtime_db.connect() as conn:
        conn.execute("SELECT 1")

    try:
        conn.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        pass
    else:
        raise AssertionError("connect() should close sqlite connection on context exit (NOPOOL)")


# ── Pool-attribution (15/10-2026) ────────────────────────────────────────────
# Sporet fra side-fbe495ba3c. Det åbne spørgsmål: findes der pool-forbindelser
# hvis EJER-TRÅD er død? /proc kan ikke svare — fd-tabellen er delt mellem tråde
# (målt 15/10: alle TIDs viste samme 105 fds), og lsof -K kan ikke læse
# tråd-niveau på denne host. Svaret bygges derfor ved FØDSEL og DØD i db_core.


def _ren_pool(monkeypatch, tmp_path) -> None:
    """Ren pool + rene tællere, så testene ikke måler hinandens rester."""
    db_core.close_pooled_connection()
    monkeypatch.setattr(db_core, "_pool_births", {})
    monkeypatch.setattr(db_core, "_POOL_BIRTH_SEQ", 0)
    monkeypatch.setattr(db_core, "_POOL_DEATH_SEQ", 0)
    monkeypatch.setattr(db_core, "DB_PATH", tmp_path / "jarvis.db")


def test_pool_foedsel_henfoeres_til_den_levene_traad(monkeypatch, tmp_path) -> None:
    _ren_pool(monkeypatch, tmp_path)
    ident: dict = {}
    klar, slip = threading.Event(), threading.Event()

    def _arbejde():
        ident["vaerdi"] = threading.get_ident()
        with runtime_db.connect() as conn:
            conn.execute("SELECT 1")
        klar.set()
        slip.wait(5)

    t = threading.Thread(target=_arbejde, name="probe-traad")
    t.start()
    assert klar.wait(5), "arbejdstraaden naaede ikke at aabne en forbindelse"
    try:
        stats = db_core.pool_connection_stats()
        assert stats["pooled"] == 1
        assert stats["orphaned"] == {}  # tråden lever — intet forældreløst
        assert stats["births_total"] == 1
    finally:
        slip.set()
        t.join()


def test_doed_traads_forbindelse_meldes_som_foraeldreloes(monkeypatch, tmp_path) -> None:
    """KERNE-MÅLINGEN: en forbindelse hvis ejer-tråd er død, er den klasse der
    kan vokse monotont og ende i fd-udmattelse. Den skal kunne SES."""
    _ren_pool(monkeypatch, tmp_path)
    ident: dict = {}

    def _arbejde():
        ident["vaerdi"] = threading.get_ident()
        with runtime_db.connect() as conn:
            conn.execute("SELECT 1")

    t = threading.Thread(target=_arbejde, name="doed-probe")
    t.start()
    t.join()  # tråden er nu død — dens pool-forbindelse lever videre

    stats = db_core.pool_connection_stats()
    assert ident["vaerdi"] in stats["orphaned"], (
        "en forbindelse hvis traad er doed skal kunne ses — ellers er den "
        "klasse der vokser over dage usynlig"
    )
    assert stats["orphaned"][ident["vaerdi"]]["thread_name"] == "doed-probe"


def test_genbrug_taeller_ikke_som_ny_foedsel(monkeypatch, tmp_path) -> None:
    """Tre kald i SAMME tråd = ÉN fødsel. Uden dette målte vi genbrug som vækst."""
    _ren_pool(monkeypatch, tmp_path)
    for _ in range(3):
        with runtime_db.connect() as conn:
            conn.execute("SELECT 1")

    stats = db_core.pool_connection_stats()
    assert stats["births_total"] == 1
    assert stats["pooled"] == 1

    db_core.close_pooled_connection()
    efter = db_core.pool_connection_stats()
    assert efter["deaths_total"] == 1
    assert efter["pooled"] == 0
    assert efter["orphaned"] == {}
