"""Hypotese-maskineriet skal faktisk føre sine afgørelser videre.

Målt 29/10-2026: `record_hypothesis_sample` afgjorde hypoteser korrekt, men
afgørelsen gik i jorden — `confirm_dream` havde nul kaldere, så en drøm kunne
kun blive gammel, aldrig sand. Broen her er den manglende kaldevej: en
AFGJORT hypotese (supported/contradicted) føres videre til de drømme der
nævner den. En uafgjort hypotese (uncertain) må ikke føre noget videre.

Testene bruger `isolated_runtime`, så SQL'en er ægte og tabellerne rigtige —
ikke en attrap der svarer det samme uanset forespørgsel.
"""
from __future__ import annotations

import pytest


def _indsæt_hypotese(hyp_id: str, *, sample_size: int = 2) -> None:
    from core.runtime.db import connect
    from core.services import meta_learning_hypotheses as mlh

    # `_SCHEMA_INITIALIZED` er en modul-global der overlever at isolated_runtime
    # peger DB'en paa en frisk tmp-fil. Uden nulstilling svarer ensure_schema
    # «allerede kørt» og tabellerne findes ikke i den nye base.
    mlh._SCHEMA_INITIALIZED = False
    mlh.ensure_schema()
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta_learning_hypotheses (hypothesis_id, source_memo_id, "
            "candidate_idx, statement, observation, hypothesis_text, "
            "success_criterion, sample_size_needed, status, outcome, "
            "created_at, resolved_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', NULL, "
            "'2026-10-29T00:00:00+00:00', NULL)",
            (
                hyp_id,
                "memo-test",
                0,
                "testudsagn",
                "testobservation",
                "testhypotese",
                "testsucceskriterium",
                sample_size,
            ),
        )
        conn.commit()


def test_afgjort_hypotese_foeres_videre_til_droemmene(isolated_runtime, monkeypatch):
    """Kernen: en supported-afgørelse SKAL kalde drømme-broen."""
    from core.services import dream_carry_over as dco
    from core.services import meta_learning_hypotheses as mlh

    kald: list[dict] = []

    def _fang(hypothesis_id, **kwargs):
        kald.append({"hypothesis_id": hypothesis_id, **kwargs})
        return []

    monkeypatch.setattr(dco, "record_evidence_for_hypothesis", _fang)
    _indsæt_hypotese("HC-DREAM-TEST-A")

    mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-A", supports=True)
    ud = mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-A", supports=True)

    assert ud["auto_resolved"]["outcome"] == "supported"
    assert len(kald) == 1, "broen skal kaldes præcis én gang — ved afgørelsen"
    assert kald[0]["hypothesis_id"] == "HC-DREAM-TEST-A"
    assert kald[0]["supports"] is True
    assert kald[0]["source"] == "meta_learning_hypotheses"
    assert kald[0]["evidence_ref"].startswith("meta-learning-sample:")


def test_modstridt_hypotese_foeres_videre_som_imod(isolated_runtime, monkeypatch):
    """Contradicted skal give supports=False — ikke bare «afgjort»."""
    from core.services import dream_carry_over as dco
    from core.services import meta_learning_hypotheses as mlh

    kald: list[dict] = []
    monkeypatch.setattr(
        dco, "record_evidence_for_hypothesis", lambda hid, **kw: kald.append(kw) or []
    )
    _indsæt_hypotese("HC-DREAM-TEST-B")

    mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-B", supports=False)
    ud = mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-B", supports=False)

    assert ud["auto_resolved"]["outcome"] == "contradicted"
    assert len(kald) == 1
    assert kald[0]["supports"] is False


def test_uafgjort_hypotese_foerer_intet_videre(isolated_runtime, monkeypatch):
    """50/50 er ikke evidens. En uncertain afgørelse må ikke røre drømmene."""
    from core.services import dream_carry_over as dco
    from core.services import meta_learning_hypotheses as mlh

    kald: list[dict] = []
    monkeypatch.setattr(
        dco, "record_evidence_for_hypothesis", lambda hid, **kw: kald.append(kw) or []
    )
    _indsæt_hypotese("HC-DREAM-TEST-C")

    mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-C", supports=True)
    ud = mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-C", supports=False)

    assert ud["auto_resolved"]["outcome"] == "uncertain"
    assert kald == [], "en uafgjort hypotese er ikke evidens for noget"


def test_bro_fejl_vaelter_ikke_afgoerelsen(isolated_runtime, monkeypatch):
    """En drøm der ikke kan opdateres må ikke ødelægge en gennemført måling."""
    from core.services import dream_carry_over as dco
    from core.services import meta_learning_hypotheses as mlh

    def _braek(*_a, **_kw):
        raise RuntimeError("drømme-lageret er nede")

    monkeypatch.setattr(dco, "record_evidence_for_hypothesis", _braek)
    _indsæt_hypotese("HC-DREAM-TEST-D")

    mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-D", supports=True)
    ud = mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-D", supports=True)

    assert ud["status"] == "ok"
    assert ud["auto_resolved"]["outcome"] == "supported"


def test_ende_til_ende_droem_faar_evidens(isolated_runtime, monkeypatch):
    """Hele kæden: afgjort hypotese → drøm der nævner den får ekstern evidens."""
    from core.services import dream_carry_over as dco
    from core.services import meta_learning_hypotheses as mlh

    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", True)
    monkeypatch.setattr(dco, "_save", lambda: None)
    dco.adopt_dream(
        dream_id="dream-e2e",
        content="HC-DREAM-TEST-E forudsagde at de tre ville overleve",
        confidence=0.8,
    )
    _indsæt_hypotese("HC-DREAM-TEST-E")

    mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-E", supports=True)
    mlh.record_hypothesis_sample(hypothesis_id="HC-DREAM-TEST-E", supports=True)

    d = next(x for x in dco._ACTIVE_DREAMS if x["dream_id"] == "dream-e2e")
    evidens = d.get("evidence") or []
    assert len(evidens) == 1
    assert evidens[0]["source"] == "meta_learning_hypotheses"
    assert evidens[0]["supports"] is True
