"""`lokal_groen` — fast-path for en optjent gate, og det bevis den skal BEVARE.

Baggrund maalt 6/10-2026: moenstret stod inline i `commit_gate_arbiter` og
talte IKKE verdiktet. Da veto-noeglen blev godkendt 13:19:15, stoppede `veto`s
groenne taelling i `gate_verdict_counts` 13:18:46, mens `decision_gate` i SAMME
funktionskald taellede videre til 13:27:54. Baade
`central_decentralization.analyze_chokepoint` og
`central_keymaker.evaluate_keys` laeser praecis den ledger, saa
decentraliseringen slukkede det bevis der optjener og fornyer noeglen.

Derfor er `test_groent_verdikt_TAELLES_lokalt` den vigtigste test her: uden den
kan fejlen komme tilbage uden at noget andet faanger den.
"""

from __future__ import annotations

import pytest

from core.services import central_decentralization as D
from core.services.gate_kernel import Decision, Verdict


def _gate(decision: Decision, *, kald: list | None = None):
    def fn(ctx):
        if kald is not None:
            kald.append(ctx)
        return Verdict("prøve", decision, reason="r")
    return fn


@pytest.fixture
def noegle_ja(monkeypatch):
    monkeypatch.setattr("core.services.central_keymaker.is_decentralized", lambda n: True)


@pytest.fixture
def fanget_ledger(monkeypatch):
    poster: list[tuple] = []
    monkeypatch.setattr("core.services.gate_verdict_ledger.record",
                        lambda n, c, d, reason="": poster.append((n, c, d, reason)))
    return poster


def test_uden_noegle_koeres_gaten_slet_ikke(monkeypatch, fanget_ledger):
    """Ingen noegle → None, OG gaten maa ikke vaere kaldt: ellers betalte vi for
    baade den lokale koersel og Centralens."""
    monkeypatch.setattr("core.services.central_keymaker.is_decentralized", lambda n: False)
    kald: list = []
    assert D.lokal_groen("x", "c", _gate(Decision.GREEN, kald=kald), {}) is None
    assert kald == []
    assert fanget_ledger == []


def test_groent_verdikt_TAELLES_lokalt(noegle_ja, fanget_ledger):
    v = D.lokal_groen("veto", "commit", _gate(Decision.GREEN), {"a": 1})
    assert v is not None and v.decision is Decision.GREEN
    assert fanget_ledger == [("veto", "commit", "green", "r")], (
        "det groenne verdikt skal i ledgeren — den er kilden der optjener noeglen"
    )


@pytest.mark.parametrize("d", [Decision.RED, Decision.YELLOW, Decision.SKIP])
def test_ikke_groent_eskalerer_og_taelles_IKKE_lokalt(noegle_ja, fanget_ledger, d):
    """None = «brug Centralen». Den optager selv verdiktet, saa en lokal
    taelling her ville vaere dobbelt."""
    assert D.lokal_groen("x", "c", _gate(d), {}) is None
    assert fanget_ledger == []


def test_gate_der_kaster_eskalerer(noegle_ja, fanget_ledger):
    def sprael(ctx):
        raise RuntimeError("gate nede")
    assert D.lokal_groen("x", "c", sprael, {}) is None
    assert fanget_ledger == []


def test_gate_der_returnerer_None_eskalerer(noegle_ja, fanget_ledger):
    assert D.lokal_groen("x", "c", lambda ctx: None, {}) is None
    assert fanget_ledger == []


def test_noegle_opslag_der_kaster_eskalerer(monkeypatch, fanget_ledger):
    def sprael(n):
        raise RuntimeError("tabel nede")
    monkeypatch.setattr("core.services.central_keymaker.is_decentralized", sprael)
    assert D.lokal_groen("x", "c", _gate(Decision.GREEN), {}) is None
    assert fanget_ledger == []


def test_en_taeller_maa_ikke_paavirke_governance(noegle_ja, monkeypatch):
    """Falder ledgeren, skal verdiktet stadig komme igennem — ellers kunne en
    statistik-fejl aendre en gates udfald."""
    def sprael(*a, **k):
        raise RuntimeError("ledger nede")
    monkeypatch.setattr("core.services.gate_verdict_ledger.record", sprael)
    v = D.lokal_groen("x", "c", _gate(Decision.GREEN), {})
    assert v is not None and v.decision is Decision.GREEN


def test_konteksten_gives_videre_uaendret(noegle_ja, fanget_ledger):
    kald: list = []
    ctx = {"tool_name": "bash", "run_id": "r1"}
    D.lokal_groen("x", "c", _gate(Decision.GREEN, kald=kald), ctx)
    assert kald == [ctx]
