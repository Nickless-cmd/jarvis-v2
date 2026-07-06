"""Gate-verdict-ledger — in-memory akkumulering + persistent flush + summary.

Invariant: record() rører aldrig DB (billig hot-path), flush() persisterer batchet, og
summary() læser den persistente tabel så data overlever "genstart" (ny proces-import).
"""
from __future__ import annotations

import importlib
from unittest import mock

import core.services.gate_verdict_ledger as ledger


def _reset_acc():
    with ledger._LOCK:
        ledger._ACC.clear()


def test_record_accumulates_in_memory_without_db():
    """record() øger kun in-memory-akkumulatoren — ingen DB-kald."""
    _reset_acc()
    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas") as apply:
        ledger.record("decision_gate", "commit", "green", "ok")
        ledger.record("decision_gate", "commit", "green", "ok igen")
        ledger.record("decision_gate", "commit", "yellow", "tvivl")
        apply.assert_not_called()  # record rører ALDRIG DB
    with ledger._LOCK:
        assert ledger._ACC[("decision_gate", "green")]["count"] == 2
        assert ledger._ACC[("decision_gate", "yellow")]["count"] == 1
        assert ledger._ACC[("decision_gate", "green")]["last_reason"] == "ok igen"


def test_record_never_raises_on_bad_input():
    """record() sluger alt — en tæller må aldrig vælte governance."""
    _reset_acc()
    ledger.record("", "c", "green")      # tom nerve → no-op
    ledger.record("n", "c", "")          # tom decision → no-op
    with ledger._LOCK:
        assert not ledger._ACC


def test_flush_drains_and_upserts_then_clears():
    """flush() sender akkumulerede deltas til apply_deltas og tømmer akkumulatoren."""
    _reset_acc()
    ledger.record("loop_control", "loop", "green", "fint")
    ledger.record("loop_control", "loop", "red", "loop!")
    captured = {}
    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas",
                           side_effect=lambda d: captured.update({"deltas": d}) or len(d)) as apply:
        n = ledger.flush()
    assert n == 2
    apply.assert_called_once()
    decisions = {d["decision"]: d["count"] for d in captured["deltas"]}
    assert decisions == {"green": 1, "red": 1}
    with ledger._LOCK:
        assert not ledger._ACC  # tømt efter flush


def test_flush_empty_is_noop():
    """Tom akkumulator → flush() rører ikke DB og returnerer 0."""
    _reset_acc()
    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas") as apply:
        assert ledger.flush() == 0
        apply.assert_not_called()


def test_persistence_survives_reimport(tmp_path, monkeypatch):
    """End-to-end mod en rigtig tabel: flush persisterer, summary læser efter re-import
    (simulerer at data overlever en proces-genstart)."""
    import core.runtime.db_core as db_core
    db_file = tmp_path / "verdicts.db"
    monkeypatch.setattr(db_core, "DB_PATH", db_file)
    monkeypatch.setattr(db_core, "_DB_WAL_INITIALIZED", False)
    import core.runtime.db_gate_verdicts as dbv
    importlib.reload(dbv)
    monkeypatch.setattr(ledger, "db_gate_verdicts", dbv)

    _reset_acc()
    for _ in range(7):
        ledger.record("cross_user_share", "privacy", "green", "clean")
    ledger.record("cross_user_share", "privacy", "red", "læk!")
    ledger.flush()

    # "genstart": ny akkumulator, læs KUN fra persistent tabel
    _reset_acc()
    summ = ledger.summary()
    assert summ["cross_user_share"]["total"] == 8
    assert summ["cross_user_share"]["green"] == 7
    assert summ["cross_user_share"]["red"] == 1
    assert summ["cross_user_share"]["cluster"] == "privacy"
    # 1 af 8 ikke-grøn → 12.5%
    assert summ["cross_user_share"]["non_green_pct"] == 12.5
