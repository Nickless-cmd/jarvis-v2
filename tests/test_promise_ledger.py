"""Promise-ledger (Bjørn-gate) — record/pending/clear + TTL + cap."""
from __future__ import annotations

import core.services.promise_ledger as pl


def _mem_store(monkeypatch):
    """In-memory erstatning for runtime_state (ingen DB i unit-test)."""
    store: dict = {}
    import core.runtime.db_core as dbc
    monkeypatch.setattr(dbc, "get_runtime_state_value", lambda k, d=None: store.get(k, d))
    def _set(k, v, **kw):
        store[k] = v
    monkeypatch.setattr(dbc, "set_runtime_state_value", _set)
    return store


def test_record_and_list(monkeypatch):
    _mem_store(monkeypatch)
    pl.record_promise("s1", "Jeg committer claim-scanner-fixet nu", now=1000.0)
    pend = pl.pending_promises("s1", now=1000.0)
    assert len(pend) == 1 and "claim-scanner" in pend[0]["text"]


def test_ttl_expiry(monkeypatch):
    _mem_store(monkeypatch)
    pl.record_promise("s1", "gammelt løfte", now=1000.0)
    # 31 min senere → forældet
    assert pl.pending_promises("s1", now=1000.0 + 1860) == []
    # inden for vinduet → stadig der
    assert len(pl.pending_promises("s1", now=1000.0 + 600)) == 1


def test_cap_per_session(monkeypatch):
    _mem_store(monkeypatch)
    for i in range(8):
        pl.record_promise("s1", f"løfte {i}", now=1000.0 + i)
    pend = pl.pending_promises("s1", now=1010.0)
    assert len(pend) == 5  # _MAX_PER_SESSION
    assert pend[-1]["text"] == "løfte 7"  # nyeste bevaret


def test_sessions_isolated(monkeypatch):
    _mem_store(monkeypatch)
    pl.record_promise("s1", "a", now=1000.0)
    pl.record_promise("s2", "b", now=1000.0)
    assert len(pl.pending_promises("s1", now=1000.0)) == 1
    assert pl.pending_promises("s2", now=1000.0)[0]["text"] == "b"


def test_clear(monkeypatch):
    _mem_store(monkeypatch)
    pl.record_promise("s1", "x", now=1000.0)
    pl.clear_promises("s1")
    assert pl.pending_promises("s1", now=1000.0) == []


def test_empty_and_blank_are_safe(monkeypatch):
    _mem_store(monkeypatch)
    pl.record_promise("", "x")
    pl.record_promise("s1", "   ")
    assert pl.pending_promises("s1") == []
    assert pl.pending_promises("") == []
