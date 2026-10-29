"""Drømme kan bekræftes af ekstern evidens — ikke kun blive gamle.

Målt 29/10-2026: `confirm_dream` (linje 348) og `reject_dream` (linje 385) var
defineret men havde NUL produktionskaldere (grep over core/, tools/, apps/ gav
kun de to definitioner; tre test-filer rørte dem). `_maybe_fade_old_dreams`
freder `confirmed`-drømme — men intet kunne sætte flaget, så fredningen var
død kode og hver drøm døde på carry 5 uanset evidens. Samme nat faldt aktive
drømme 7→5, og HC-DREAM-111's egen forudsigelse blev fældet af målingen.

Disse tests værner BEGGE retninger: at evidens nu kan afgøre en drøm, og at en
drøm ikke kan bekræfte sig selv med sin egen formulering.
"""
from __future__ import annotations

import pytest

from core.services import dream_carry_over as dco


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(dco, "_ACTIVE_DREAMS", [])
    monkeypatch.setattr(dco, "_DREAM_ARCHIVE", [])
    monkeypatch.setattr(dco, "_LOADED", True)
    monkeypatch.setattr(dco, "_persist_file", lambda: tmp_path / "DREAM_CARRY.json")
    monkeypatch.setattr(dco, "_save", lambda: None)
    yield


def _droem(dream_id: str = "HC-DREAM-TEST", *, carry: int = 0, confidence: float = 0.8):
    dco.adopt_dream(dream_id=dream_id, content="Testdrøm om carry-mekanikken", confidence=confidence)
    d = next(x for x in dco._ACTIVE_DREAMS if x["dream_id"] == dream_id)
    d["session_carry_count"] = carry
    return d


def _evidens(dream_id: str, *, supports: bool, ref: str, source: str = "meta_learning_hypotheses"):
    return dco.record_dream_evidence(
        dream_id,
        supports=supports,
        source=source,
        evidence="målt i en ekstern kørsel",
        evidence_ref=ref,
    )


# ── (a) ekstern evidens kan bekræfte ──────────────────────────────────────
def test_droem_med_ekstern_evidens_bliver_bekraeftet():
    """To uafhængige målinger FOR drømmen skal gøre den `confirmed`."""
    d = _droem()
    assert not d.get("confirmed")

    foerste = _evidens("HC-DREAM-TEST", supports=True, ref="sample:1")
    assert foerste["status"] == "ok"
    assert foerste["decision"] is None, "ét sample må ikke afgøre alene"
    assert not d.get("confirmed")

    andet = _evidens("HC-DREAM-TEST", supports=True, ref="sample:2")
    assert andet["status"] == "ok"
    assert andet["decision"] == "confirmed"
    assert d.get("confirmed") is True
    assert int(d.get("confirmed_sessions") or 0) >= 1
    assert d.get("status") == "active"


# ── (b) bekræftet drøm fader IKKE ─────────────────────────────────────────
def test_bekraeftet_droem_fader_ikke_ved_carry_5():
    """Fredningen i `_maybe_fade_old_dreams` skal nu ramme noget virkeligt."""
    d = _droem(carry=0)
    _evidens("HC-DREAM-TEST", supports=True, ref="sample:1")
    _evidens("HC-DREAM-TEST", supports=True, ref="sample:2")
    assert d.get("confirmed") is True

    d["session_carry_count"] = dco._FADE_AFTER_SESSIONS
    dco._maybe_fade_old_dreams()

    ids = {x["dream_id"] for x in dco._ACTIVE_DREAMS}
    assert "HC-DREAM-TEST" in ids, "en bekræftet drøm må ikke fade på carry"


# ── (c) uden evidens: uafgjort, fader som før ─────────────────────────────
def test_droem_uden_evidens_forbliver_uafgjort_og_fader():
    """Ingen evidens = ingen bekræftelse. Glemslen skal være uændret."""
    d = _droem(carry=0)
    d["session_carry_count"] = dco._FADE_AFTER_SESSIONS
    dco._maybe_fade_old_dreams()

    ids = {x["dream_id"] for x in dco._ACTIVE_DREAMS}
    assert "HC-DREAM-TEST" not in ids
    arkiveret = next(x for x in dco._DREAM_ARCHIVE if x["dream_id"] == "HC-DREAM-TEST")
    assert arkiveret["status"] == "faded"


def test_et_enkelt_sample_er_ikke_nok():
    """Tærsklen skal være reel — ikke pyntet med et enkelt kald."""
    d = _droem()
    ud = _evidens("HC-DREAM-TEST", supports=True, ref="sample:1")
    assert ud["decision"] is None
    assert not d.get("confirmed")
    assert d.get("status") == "active"


# ── værn mod den modsatte fejl ────────────────────────────────────────────
def test_droem_kan_ikke_bekraefte_sig_selv():
    """En drøm må ikke kunne bekræftes af drømmemaskineriets egen formulering."""
    d = _droem()
    for i in range(3):
        ud = _evidens("HC-DREAM-TEST", supports=True, ref=f"egen:{i}", source="dream")
        assert ud["status"] == "rejected"
        assert "selv" in str(ud["reason"])
    assert not d.get("confirmed")
    assert d.get("evidence") in (None, [])


def test_tom_pegepind_afvises():
    """Uden en pegepind til målingen er der ingen evidens — kun en påstand."""
    d = _droem()
    ud = dco.record_dream_evidence(
        "HC-DREAM-TEST",
        supports=True,
        source="meta_learning_hypotheses",
        evidence="noget blev målt",
        evidence_ref="   ",
    )
    assert ud["status"] == "rejected"
    assert not d.get("confirmed")


def test_samme_pegepind_taeller_kun_engang():
    """Ét kald gentaget er ikke to uafhængige målinger."""
    d = _droem()
    _evidens("HC-DREAM-TEST", supports=True, ref="sample:1")
    igen = _evidens("HC-DREAM-TEST", supports=True, ref="sample:1")
    assert igen["status"] == "duplicate"
    assert not d.get("confirmed")


def test_evidens_imod_arkiverer_som_was_wrong():
    """Modstridende evidens skal kunne fælde drømmen — ikke kun lade den ældes."""
    d = _droem()
    _evidens("HC-DREAM-TEST", supports=False, ref="sample:1")
    ud = _evidens("HC-DREAM-TEST", supports=False, ref="sample:2")

    assert ud["decision"] == "was_wrong"
    ids = {x["dream_id"] for x in dco._ACTIVE_DREAMS}
    assert "HC-DREAM-TEST" not in ids
    arkiveret = next(x for x in dco._DREAM_ARCHIVE if x["dream_id"] == "HC-DREAM-TEST")
    assert arkiveret["status"] == "was_wrong"


def test_hypotese_broen_rammer_droemmen_der_naevner_den(monkeypatch):
    """Broen fra hypotese-maskineriet skal finde drømmen via id eller indhold."""
    dco.adopt_dream(
        dream_id="dream-x",
        content="HC-DREAM-111 forudsagde at de tre ville overleve",
        confidence=0.8,
    )
    ramte = dco.record_evidence_for_hypothesis(
        "HC-DREAM-111",
        supports=True,
        source="meta_learning_hypotheses",
        evidence="hypotese afgjort som supported",
        evidence_ref="meta-learning-sample:hsamp-1",
    )
    assert ramte == ["dream-x"]
    d = next(x for x in dco._ACTIVE_DREAMS if x["dream_id"] == "dream-x")
    assert len(d.get("evidence") or []) == 1
