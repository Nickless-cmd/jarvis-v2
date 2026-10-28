"""Vaegt-loekken: vaegten skal LAESES foer valget og OPDATERES efter udfaldet.

MAALT 28/10-2026 (opgaven side-a8609eea89): `runtime_action_outcomes` havde
274.614 raekker, men `decision_score` havde kun 6 distinkte vaerdier for 257.027
ok-raekker — og negative vaerdier for fejl. En score skrevet EFTER udfaldet kan
ikke have paavirket det valg den beskriver. Det var et facit-notat, ikke en
forudsigelse.

Disse tests maaler det der skiller et facit-notat fra en laering:
  (c) udfaldet flytter vaegten, og læringsraten er AFledt af forloebet
  (d) vaegten HAR flyttet sig mellem to samples — ikke bare at den findes
"""
from __future__ import annotations

import sqlite3

import pytest

from core.runtime import db_runtime_signals as drs


@pytest.fixture()
def temp_db(tmp_path, monkeypatch):
    """Rigtig sqlite i en temp-fil — den aegte UPSERT-aritmetik, ikke en mock."""
    path = tmp_path / "weights.db"

    class _Conn:
        def __init__(self):
            self._c = sqlite3.connect(path)
            self._c.row_factory = sqlite3.Row

        def execute(self, *a, **k):
            return self._c.execute(*a, **k)

        def commit(self):
            self._c.commit()

        def close(self):
            self._c.close()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.close()
            return False

    monkeypatch.setattr(drs, "connect", lambda: _Conn())
    return path


def _update(term: str, status: str, ts: str = "2026-10-28T20:00:00+00:00") -> dict:
    return drs.apply_action_weight_update(
        term=term, outcome_status=status, recorded_at=ts
    )


def test_foerste_sample_saetter_vaegten_mod_udfaldet(temp_db):
    """Et 'executed' peger mod 1.0 — foerste sample skal naa halvvejs dertil."""
    got = _update("a", "executed")
    assert got["n_samples"] == 1
    # start 0.5, target 1.0, rate 1/(0+1)=1.0 → 1.0
    assert got["weight"] == pytest.approx(1.0)


def test_vaegten_har_FLYTTET_sig_mellem_to_samples(temp_db):
    """(d) Det afgoerende maal: to samples med modsat udfald skal give to
    FORSKELLIGE vaegte. En vaegt der ikke kan flytte sig er ikke en vaegt."""
    first = _update("a", "failed")          # → 0.0
    second = _update("a", "executed")       # rate 1/2 → 0.5
    assert first["weight"] == pytest.approx(0.0)
    assert second["weight"] == pytest.approx(0.5)
    assert second["weight"] != first["weight"]
    assert second["n_samples"] == 2


def test_laeringsraten_aftager_med_forloebet(temp_db):
    """(c) Raten er AFledt af forloebet, ikke valgt frit: 1/(n+1).

    MAALT 28/10-2026: den foerste udgave af denne test målte BEVAEGELSEN og
    fejlede — men koden var rigtig. Bevægelsen er ``rate * afstand_til_target``,
    og med alternerende udfald skifter afstanden fortegn hver gang, saa
    bevægelsen ikke kan aftage monotont. Det er RATEN der skal aftage, ikke
    skridtlaengden. Derfor maales ``bevaegelse / afstand`` — den er 1/(n+1)
    uanset hvor vaegten staar.
    """
    rates = []
    prev = 0.5
    for i in range(5):
        status = "executed" if i % 2 == 0 else "failed"
        target = drs.outcome_target(status)
        got = _update("a", status)
        afstand = abs(target - prev)
        assert afstand > 0, "afstand 0 giver ingen maalbar rate"
        rates.append(abs(got["weight"] - prev) / afstand)
        prev = got["weight"]
    assert all(rates[i] > rates[i + 1] for i in range(len(rates) - 1)), rates
    # og den er praecis 1/(n+1), ikke bare «aftagende»
    for n, rate in enumerate(rates, start=1):
        assert rate == pytest.approx(1.0 / n), (n, rate)


def test_ingen_raekke_er_ingen_viden_ikke_neutral_vaegt(temp_db):
    """En term der aldrig er set skal MANGLES — ikke vaere 0.5. Forskellen er
    hele pointen: 'ingen viden' maa ikke se ud som 'maalt neutral'."""
    weights = drs.load_action_weights(["aldrig_set"])
    assert "aldrig_set" not in weights


def test_load_returnerer_det_der_blev_skrevet(temp_db):
    _update("a", "executed", ts="2026-10-28T21:00:00+00:00")
    weights = drs.load_action_weights(["a"])
    assert weights["a"]["n_samples"] == 1
    assert weights["a"]["last_updated"] == "2026-10-28T21:00:00+00:00"


def test_ukendt_status_er_neutral_ikke_et_nej():
    assert drs.outcome_target("noget-ukendt") == 0.5
    assert drs.outcome_target("failed") == 0.0
    assert drs.outcome_target("executed") == 1.0


def test_laesevejen_flytter_scoren_foer_valget(temp_db):
    """(b) Læse-vejen: beslutningsmotoren skal konsultere vaegten FOER den
    vaelger. Et daarligt forloeb paa en handling skal tynge den handling."""
    from core.services.runtime_decision_engine import (
        RuntimeActionCandidate,
        _apply_persisted_weight,
    )

    for _ in range(5):
        _update("follow_open_loop", "failed")

    cand = RuntimeActionCandidate(
        action_id="follow_open_loop",
        score=0.85,
        reason="baseline",
        payload={},
        mode="execute",
    )
    score, reasons = _apply_persisted_weight(cand, score=0.85)
    assert score < 0.85, "et daarligt forloeb skal saenke scoren"
    assert reasons and "Persisted weight" in reasons[0]


def test_ukendt_handling_flyttes_ikke(temp_db):
    """Ingen raekke → ingen flytning. En term uden historik maa ikke straffes."""
    from core.services.runtime_decision_engine import (
        RuntimeActionCandidate,
        _apply_persisted_weight,
    )

    cand = RuntimeActionCandidate(
        action_id="aldrig_set",
        score=0.5,
        reason="baseline",
        payload={},
        mode="execute",
    )
    score, reasons = _apply_persisted_weight(cand, score=0.5)
    assert score == 0.5
    assert reasons == []
