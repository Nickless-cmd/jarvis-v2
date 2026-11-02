"""Forslag skal kunne SES og AFGOERES fra notifikations-feedet (2/11-2026).

ROD (Bjørn 2/11-2026): 57 `pending` forslag laa i `autonomy_proposals`, og
der var INGEN flade hvor de kunne ses. De raadnede op — det aeldste var fra
22/10. Maalt samme dag: 0 af 14 source-edit matchede deres `base_fingerprint`,
og fire af dem ville slette 69-152 linjer inklusive `_MAX_ATTEMPTS`-loftet i
`initiative_queue.py` — altsaa rulle fixet fra 1/11 tilbage.

Det er praecis den fejlform Bjørn kalder teater: en mekanisme der ser ud som
om den virker, men hvis indgangsbetingelse intet kan opfylde. Forslagene blev
GENERERET korrekt; de blev bare aldrig leveret.

Disse tests laaser de tre led der manglede:
  1. `afstem_forslag` foeder ventende forslag ind i notifikations-lageret.
  2. `proposal` er afgoerbart — ellers afviser ruten ethvert svar.
  3. En foraeldet source-edit markeres, saa den ikke godkendes blindt.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from core.services import notifikationer_hydrering as hyd
from core.services import notifikations_emittere as emit


def test_proposal_er_afgoerbart():
    """Uden dette svarer afgoer-ruten «Den slags kan ikke godkendes eller
    afvises» — og knapperne i toasten ville vaere attrap."""
    assert "proposal" in hyd.AFGOERBARE


def test_source_edit_med_forkert_fingerprint_er_foraeldet(tmp_path: Path):
    fil = tmp_path / "ting.py"
    fil.write_text("x = 1\n")
    forslag = {
        "kind": "source-edit",
        "payload": {"target_path": str(fil), "base_fingerprint": "deadbeefdeadbeef"},
    }
    assert emit._forslag_er_foraeldet(forslag) is True


def test_source_edit_med_korrekt_fingerprint_er_ikke_foraeldet(tmp_path: Path):
    fil = tmp_path / "ting.py"
    fil.write_text("x = 1\n")
    korrekt = hashlib.sha256(fil.read_bytes()).hexdigest()[:16]
    forslag = {
        "kind": "source-edit",
        "payload": {"target_path": str(fil), "base_fingerprint": korrekt},
    }
    assert emit._forslag_er_foraeldet(forslag) is False


def test_utilgaengelig_fil_regnes_som_foraeldet(tmp_path: Path):
    """Kan ankeret ikke laeses, er det ikke BEVIST frisk. Vi siger foraeldet
    frem for at paastaa det modsatte — en forkert «godkendelsesklar» er den
    dyre fejl."""
    forslag = {
        "kind": "source-edit",
        "payload": {"target_path": str(tmp_path / "findes-ikke.py"),
                    "base_fingerprint": "deadbeefdeadbeef"},
    }
    assert emit._forslag_er_foraeldet(forslag) is True


def test_andre_kinds_har_intet_anker_og_er_ikke_foraeldede():
    """instrument_fix/git-commit baerer ingen fingerprint. De skal ikke
    skjules — blot ikke paastaa en friskhed de ikke har."""
    for kind in ("instrument_fix", "git-commit", "memory-rewrite"):
        assert emit._forslag_er_foraeldet({"kind": kind, "payload": {}}) is False


def test_afstem_forslag_foeder_ventende_forslag(monkeypatch):
    """Kernen: et ventende forslag skal give en raekke i lageret."""
    oprettede: list[dict] = []

    class FalskLager:
        @staticmethod
        def aabne(user_id, *, er_owner):
            return []

        @staticmethod
        def genaabn(slags, ref):
            return False

        @staticmethod
        def opret(**kw):
            oprettede.append(kw)
            return "nid"

    monkeypatch.setattr(emit, "_lager", FalskLager)
    monkeypatch.setattr(emit, "_maaske_push", lambda *a, **k: None)

    import core.services.autonomy_proposal_queue as ko
    monkeypatch.setattr(ko, "list_pending_proposals", lambda limit=200: [{
        "proposal_id": "prop-test123",
        "kind": "instrument_fix",
        "title": "Ret en tavs except",
        "payload": {},
    }])

    antal = emit.afstem_forslag("owner")

    assert antal == 1
    assert oprettede[0]["slags"] == "proposal"
    assert oprettede[0]["ref"] == "prop-test123"
    assert oprettede[0]["kilde"] == "proposal"


def test_afstem_forslag_springer_allerede_aabne_over(monkeypatch):
    """Idempotens: en raekke der allerede staar aaben maa ikke dubleres."""
    oprettede: list[dict] = []

    class FalskLager:
        @staticmethod
        def aabne(user_id, *, er_owner):
            return [{"ref": "prop-test123", "slags": "proposal"}]

        @staticmethod
        def genaabn(slags, ref):
            return False

        @staticmethod
        def opret(**kw):
            oprettede.append(kw)
            return "nid"

    monkeypatch.setattr(emit, "_lager", FalskLager)
    monkeypatch.setattr(emit, "_maaske_push", lambda *a, **k: None)

    import core.services.autonomy_proposal_queue as ko
    monkeypatch.setattr(ko, "list_pending_proposals", lambda limit=200: [{
        "proposal_id": "prop-test123", "kind": "instrument_fix",
        "title": "Ret en tavs except", "payload": {},
    }])

    assert emit.afstem_forslag("owner") == 0
    assert oprettede == []
