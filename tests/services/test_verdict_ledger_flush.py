"""Verdict-ledger flush-holdbarhed — verdicts må ALDRIG tabes ved en DB-skrive-fejl.

Baggrund: `central().decide` akkumulerer et verdict pr. kald in-memory (`record`), og
`flush()` batch-skriver vinduet til den persistente `gate_verdict_counts`-tabel. Tabellen
er ground-truth for shadow→enforce-flip (sample-count + non_green%).

ROD (denne fil dækker): `flush()` DRÆNEDE akkumulatoren FØR DB-skrivet var bekræftet.
Fejlede `apply_deltas` (DB låst ud over busy_timeout, WAL-kontention på den store live-DB,
disk-fejl) returnerede den 0 — men vinduets tællere var allerede ryddet fra `_ACC` og gik
TABT uden retry. På en travl live-DB (api-proces-flush ved run-slut konkurrerer med tung
visible-run-DB-trafik = det mest lås-udsatte øjeblik) eroderer det ledgeren stille og
gør flip-beslutningen ugrundbar. Fix: kun ryd akkumulatoren når skrivet er bekræftet;
ved fejl re-kø deltaerne så de forsøges igen ved næste flush.
"""
from __future__ import annotations

from unittest import mock

import core.services.gate_verdict_ledger as ledger


def _reset_acc():
    with ledger._LOCK:
        ledger._ACC.clear()


def test_flush_failure_does_not_lose_counts():
    """DB-skrivet fejler (apply_deltas → 0): vinduets tællere må IKKE forsvinde."""
    _reset_acc()
    for _ in range(5):
        ledger.record("fact_gate", "truth", "green", "ok")

    # Simulér total DB-skrive-fejl (connect låst / busy_timeout overskredet).
    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas", return_value=0):
        assert ledger.flush() == 0

    # Tællerne skal stadig være i live-akkumulatoren — ikke tabt.
    with ledger._LOCK:
        assert ledger._ACC[("fact_gate", "green")]["count"] == 5


def test_requeued_counts_flush_on_next_success():
    """Efter en fejlet flush skal et efterfølgende vellykket flush persistere HELE vinduet."""
    _reset_acc()
    for _ in range(5):
        ledger.record("fact_gate", "truth", "green", "ok")

    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas", return_value=0):
        ledger.flush()  # fejler → re-kø

    captured: dict = {}

    def _ok(deltas):
        captured["deltas"] = deltas
        return len(deltas)

    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas", side_effect=_ok):
        assert ledger.flush() == 1  # 1 række (fact_gate/green) skrevet

    counts = {d["decision"]: d["count"] for d in captured["deltas"]}
    assert counts == {"green": 5}  # HELE vinduet, ikke 1
    with ledger._LOCK:
        assert not ledger._ACC  # tømt efter bekræftet skriv


def test_records_during_failed_flush_merge_into_requeue():
    """Verdicts der ankommer MENS et flush fejler må lægges oveni de re-køede — ikke tabt."""
    _reset_acc()
    for _ in range(3):
        ledger.record("truth", "truth", "green", "ok")

    def _fail_then_record(_deltas):
        # Simulér at der ankommer et nyt verdict lige efter drain, mens skrivet fejler.
        ledger.record("truth", "truth", "green", "ny")
        return 0

    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas", side_effect=_fail_then_record):
        ledger.flush()

    with ledger._LOCK:
        # 3 re-køede + 1 der ankom under flush = 4, intet tabt.
        assert ledger._ACC[("truth", "green")]["count"] == 4


def test_flush_exception_also_requeues():
    """Hvis apply_deltas KASTER (ikke bare returnerer 0) skal vinduet stadig re-køes."""
    _reset_acc()
    for _ in range(4):
        ledger.record("loop_control", "loop", "green", "ok")

    with mock.patch.object(ledger.db_gate_verdicts, "apply_deltas",
                           side_effect=RuntimeError("db boom")):
        assert ledger.flush() == 0

    with ledger._LOCK:
        assert ledger._ACC[("loop_control", "green")]["count"] == 4


def test_summary_reflects_true_accumulated_counts_end_to_end(tmp_path, monkeypatch):
    """End-to-end mod en rigtig tabel: efter en forbigående fejl + retry afspejler summary
    de ÆGTE akkumulerede tællere (groundbar flip-data), ikke et undertalt vindue."""
    import importlib

    import core.runtime.db_core as db_core
    db_file = tmp_path / "verdicts.db"
    monkeypatch.setattr(db_core, "DB_PATH", db_file)
    monkeypatch.setattr(db_core, "_DB_WAL_INITIALIZED", False)
    import core.runtime.db_gate_verdicts as dbv
    importlib.reload(dbv)
    monkeypatch.setattr(ledger, "db_gate_verdicts", dbv)

    _reset_acc()
    for _ in range(10):
        ledger.record("verification", "proactivity", "green", "ok")
    ledger.record("verification", "proactivity", "yellow", "tvivl")

    # Første flush fejler (DB låst) — må ikke tabe noget.
    with mock.patch.object(dbv, "apply_deltas", return_value=0):
        ledger.flush()

    # Anden flush lykkes mod den rigtige tabel.
    ledger.flush()

    _reset_acc()  # "genstart": læs kun fra persistent tabel
    summ = ledger.summary()
    assert summ["verification"]["total"] == 11
    assert summ["verification"]["green"] == 10
    assert summ["verification"]["yellow"] == 1
    # 1 af 11 ikke-grøn
    assert summ["verification"]["non_green_pct"] == round(100.0 / 11, 2)
