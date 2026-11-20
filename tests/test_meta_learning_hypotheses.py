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


@pytest.fixture(autouse=True)
def _ingen_net_til_domaene(monkeypatch):
    """Producenten kalder `domaene_for_tur` (en LLM-klassifikation) — aldrig nettet i test."""
    from core.services import dream_domains

    monkeypatch.setattr(dream_domains, "domaene_for_tur", lambda t, **k: "memory")


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
    assert kald[0]["domain"] == "memory", "producenten skal levere domæne"
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


def _e2e_setup(monkeypatch, *, dream_domain):
    from core.services import dream_carry_over as dco

    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", True)
    monkeypatch.setattr(dco, "_save", lambda: None)
    kw = {"domain": dream_domain} if dream_domain else {}
    dco.adopt_dream(
        dream_id="dream-e2e",
        content="HC-DREAM-TEST-E og HC-DREAM-TEST-F forudsagde at de tre ville overleve",
        confidence=0.5, **kw,
    )
    _indsæt_hypotese("HC-DREAM-TEST-E")
    _indsæt_hypotese("HC-DREAM-TEST-F")
    return dco


def _afgoer_begge(mlh):
    for h in ("HC-DREAM-TEST-E", "HC-DREAM-TEST-F"):
        mlh.record_hypothesis_sample(hypothesis_id=h, supports=True)
        mlh.record_hypothesis_sample(hypothesis_id=h, supports=True)


def test_ende_til_ende_confidence_loeftes_med_domaene_fra_producenten(isolated_runtime, monkeypatch):
    """ÆGTE vej: producent → domaene_for_tur → bro → record_dream_evidence → confirm_dream."""
    from core.services import dream_domains
    from core.services import meta_learning_hypotheses as mlh

    dco = _e2e_setup(monkeypatch, dream_domain="memory")
    monkeypatch.setattr(dream_domains, "domaene_for_tur", lambda t, **k: "memory")
    d = next(x for x in dco._ACTIVE_DREAMS if x["dream_id"] == "dream-e2e")
    assert d["confidence"] == 0.5  # før

    _afgoer_begge(mlh)

    assert len(d["evidence"]) == 2
    assert all(e["source"] == "meta_learning_hypotheses" for e in d["evidence"])
    assert d["confirmed"] is True
    assert d["confidence"] == 0.65  # efter: 0.5 + _CONFIRM_BOOST


def test_ende_til_ende_producent_uden_domaene_loefter_intet(isolated_runtime, monkeypatch):
    """domaene_for_tur → None: beviset afvises (husets fejlmodel), confidence uændret."""
    from core.services import dream_domains
    from core.services import meta_learning_hypotheses as mlh

    dco = _e2e_setup(monkeypatch, dream_domain="memory")
    monkeypatch.setattr(dream_domains, "domaene_for_tur", lambda t, **k: None)
    _afgoer_begge(mlh)
    d = next(x for x in dco._ACTIVE_DREAMS if x["dream_id"] == "dream-e2e")
    assert (d.get("evidence") or []) == []
    assert d["confidence"] == 0.5


def test_ende_til_ende_aeldre_droem_uden_domaene_kan_loeftes(isolated_runtime, monkeypatch):
    """En drøm fra DREAM_CARRY.json uden domæne får domæne af eget indhold — og kan løftes."""
    from core.services import dream_domains
    from core.services import meta_learning_hypotheses as mlh

    dco = _e2e_setup(monkeypatch, dream_domain=None)
    d = next(x for x in dco._ACTIVE_DREAMS if x["dream_id"] == "dream-e2e")
    assert "domain" not in d
    monkeypatch.setattr(dream_domains, "domaene_for_tur", lambda t, **k: "memory")
    _afgoer_begge(mlh)
    assert d["domain"] == "memory"
    assert d["confidence"] == 0.65
