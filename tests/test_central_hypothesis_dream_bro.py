"""Den LEVENDE kaldevej: en afgjort central-hypotese skal nå drømmene.

Målt 29/10-2026: `meta_learning_hypotheses` er tom (0 rækker), så broen derfra
fyrer aldrig. Det maskineri der FAKTISK afgør hypoteser er
`central_hypotheses` (134.765 resolved). Derfor sidder broen nu i
`record_governed_sample`, hvor afgørelsen sker — ellers ville rettelsen være
endnu en kaldevej hvis indgangsbetingelse intet kan opfylde.
"""
from __future__ import annotations

import types

import pytest

from core.services import central_hypothesis_generator as gen
from core.services import dream_carry_over as dco


def _hyp(sample_size: int = 1) -> dict:
    return {
        "hyp_id": "clh-test-1",
        "statement": "testudsagn",
        "prediction": "testforudsigelse",
        "null_hypothesis": "testnul",
        "success_criterion": "testkriterium",
        "sample_size": sample_size,
        "ttl_seconds": 86400,
        "provenance_json": "{}",
        "confidence": 0.5,
        "created_at": "2026-10-29T00:00:00+00:00",
        "status": "active",
        "_samples": [],
    }


def _verdict(*, alive: bool, confidence: float, quarantined: bool = False):
    return types.SimpleNamespace(
        alive=alive,
        confidence=confidence,
        quarantined=quarantined,
        acts=[],
        reason="test",
    )


def _kobl(monkeypatch, *, grounded: bool = True):
    kald: list[dict] = []
    monkeypatch.setattr(
        dco,
        "record_evidence_for_hypothesis",
        lambda hid, **kw: kald.append({"hyp_id": hid, **kw}) or [],
    )
    monkeypatch.setattr(gen, "_load", lambda _hid: _hyp())
    # Uden grounded evidens kan hypotesen ikke resolve — så bliver outcome
    # korrekt None, og testen ville maale sin egen opsaetning i stedet.
    monkeypatch.setattr(gen, "_to_evidence", lambda _s: [{"supports": True}])
    monkeypatch.setattr(
        gen.gov, "is_externally_grounded", lambda _e, verifier=None: grounded
    )
    return kald


def test_supported_hypotese_foerer_evidens_videre(isolated_runtime, monkeypatch):
    """resolved + supported skal kalde drømme-broen med supports=True."""
    kald = _kobl(monkeypatch)
    monkeypatch.setattr(
        gen.gov, "evaluate", lambda *a, **kw: _verdict(alive=True, confidence=0.9)
    )

    ud = gen.record_governed_sample("clh-test-1", supports=True, source="test")

    assert ud["hyp_status"] == "resolved"
    assert ud["outcome"] == "supported"
    assert len(kald) == 1
    assert kald[0]["hyp_id"] == "clh-test-1"
    assert kald[0]["supports"] is True
    assert kald[0]["source"] == "central_hypothesis_generator"
    assert kald[0]["evidence_ref"].startswith("central-hypothesis:")


def test_falsificeret_hypotese_foeres_videre_som_imod(isolated_runtime, monkeypatch):
    """dead + falsified er evidens IMOD — ikke «afgjort» i løs vægt."""
    kald = _kobl(monkeypatch)
    monkeypatch.setattr(
        gen.gov, "evaluate", lambda *a, **kw: _verdict(alive=False, confidence=0.1)
    )

    ud = gen.record_governed_sample("clh-test-1", supports=False, falsifies=True, source="test")

    assert ud["hyp_status"] == "dead"
    assert ud["outcome"] == "falsified"
    assert len(kald) == 1
    assert kald[0]["supports"] is False


def test_aktiv_hypotese_foerer_intet_videre(isolated_runtime, monkeypatch):
    """En hypotese der stadig lever er ikke evidens for noget endnu."""
    kald = _kobl(monkeypatch, grounded=False)
    monkeypatch.setattr(
        gen.gov, "evaluate", lambda *a, **kw: _verdict(alive=True, confidence=0.5)
    )

    ud = gen.record_governed_sample("clh-test-1", supports=True, source="test")

    assert ud["hyp_status"] == "active"
    assert ud["outcome"] is None
    assert kald == []


def test_bro_fejl_vaelter_ikke_afgoerelsen(isolated_runtime, monkeypatch):
    """Modulet lover «kaster ALDRIG» — det skal også gælde når drømmene fejler."""
    def _braek(*_a, **_kw):
        raise RuntimeError("drømme-lageret er nede")

    # Opsætningen skal være den SAMME som i de grønne tests: uden grounded
    # evidens kan hypotesen ikke resolve, og så er der ingen afgørelse at
    # beskytte — testen ville måle sin egen opsætning. `_kobl` giver evidensen,
    # derefter ødelægger vi bevidst broen.
    _kobl(monkeypatch)
    monkeypatch.setattr(dco, "record_evidence_for_hypothesis", _braek)
    monkeypatch.setattr(
        gen.gov, "evaluate", lambda *a, **kw: _verdict(alive=True, confidence=0.9)
    )

    ud = gen.record_governed_sample("clh-test-1", supports=True, source="test")

    assert ud["status"] == "ok"
    assert ud["outcome"] == "supported"
