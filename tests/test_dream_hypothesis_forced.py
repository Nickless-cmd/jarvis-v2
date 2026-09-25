"""Den tvungne hypotese er den eneste producent der taler kaedens sprog.

`maybe_force_dream_hypothesis` skriver `dream-hypothesis:forced:{domaene}` med
et navn fra det faelles ordforraad. Maalt 25/9-2026: fire saadanne raekker fra
24/9 baerer `capability`, `creativity`, `memory` og `identity` — og de er de
eneste i tabellen der overhovedet KAN moede et maal eller et fokus.

De 42 andre baerer `dream:topic:<slug af en besked>` og fylder alle tolv
pladser i overfladen, saa disse fire ikke kan ses.
"""
from __future__ import annotations

import core.services.dream_hypothesis_forced as F
from core.services.dream_domains import DOMAENER, er_gyldigt_domaene


def test_noeglen_baerer_altid_et_kendt_domaene(monkeypatch):
    """Emnet maa aldrig vaere fri tekst — kaeden foejer paa netop de navne."""
    fanget: list[dict] = []
    monkeypatch.setattr("core.runtime.db.upsert_runtime_dream_hypothesis_signal",
                        lambda **kw: fanget.append(kw) or kw)
    monkeypatch.setattr(F.random, "random", lambda: 0.0)  # tvinger den til at fyre
    for _ in range(12):
        F.maybe_force_dream_hypothesis()
    assert fanget, "den fyrede aldrig"
    for kw in fanget:
        ck = str(kw["canonical_key"])
        assert ck.startswith("dream-hypothesis:forced:"), ck
        assert er_gyldigt_domaene(ck.split(":")[-1]), ck


def test_den_fyrer_ikke_hver_gang(monkeypatch):
    """10 % pr. tick. Fyrede den altid, ville de otte domaener druknes i sig selv."""
    monkeypatch.setattr(F.random, "random", lambda: 0.99)
    assert F.maybe_force_dream_hypothesis() is None


def test_ordforraadet_er_det_faelles():
    assert dict(F._DOMAINS) == DOMAENER


def test_en_fejl_i_skrivningen_vaelter_ikke_hjerteslaget(monkeypatch):
    """Den kaldes fra et hjerteslags-tick; en droem maa aldrig kunne standse det."""
    def _braekker(**kw):
        raise RuntimeError("basen er vaek")
    monkeypatch.setattr("core.runtime.db.upsert_runtime_dream_hypothesis_signal", _braekker)
    monkeypatch.setattr(F.random, "random", lambda: 0.0)
    assert F.maybe_force_dream_hypothesis() is None
