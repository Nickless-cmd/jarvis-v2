"""`decision_signal_telemetry._save` — ringen der tabte i tavshed.

Målt på runtime 13/9-2026:

    decision_signal_telemetry.surfaces   500 poster  <-- paa loftet
    decision_signal_telemetry.reactions  500 poster  <-- paa loftet

At begge står *præcis* på loftet betyder at de har kastet væk, og der fandtes
ikke ét tal for hvor meget. `_save()` gjorde `list(...)[-500:]`.
"""
from __future__ import annotations

import pytest

from core.services import decision_signal_telemetry as dst
from core.services import telemetry_gate as tg


@pytest.fixture(autouse=True)
def _rent(monkeypatch):
    tg.nulstil_tab()
    gemt: dict = {}
    monkeypatch.setattr(dst, "save_json", lambda k, v: gemt.update({k: v}))
    yield gemt
    tg.nulstil_tab()


def test_save_beskaerer_BEGGE_ringe(_rent):
    dst._save({"surfaces": list(range(600)), "reactions": list(range(700))})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == dst._MAX_RECORDS
    assert len(gemt["reactions"]) == dst._MAX_RECORDS


def test_save_beholder_de_NYESTE(_rent):
    """Beholdt den de aeldste, ville telemetrien fryse ved foerste 500 og
    aldrig vise hvad der skete siden."""
    dst._save({"surfaces": list(range(600)), "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert gemt["surfaces"][-1] == 599 and gemt["surfaces"][0] == 100


def test_save_TAELLER_det_der_ryger(_rent):
    """Kriterium 2: «tolerate loss honestly». Tab er i orden for telemetri —
    det er netop forskellen paa telemetri og sandhed. Usynligt tab er ikke."""
    dst._save({"surfaces": list(range(600)), "reactions": list(range(700))})
    assert tg.tabt("decision_signal_telemetry.surfaces") == 100
    assert tg.tabt("decision_signal_telemetry.reactions") == 200


def test_save_taeller_paa_tvaers_af_kald(_rent):
    dst._save({"surfaces": list(range(600)), "reactions": []})
    dst._save({"surfaces": list(range(520)), "reactions": []})
    assert tg.tabt("decision_signal_telemetry.surfaces") == 120


def test_ingen_beskaering_naar_der_er_plads(_rent):
    dst._save({"surfaces": [1, 2, 3], "reactions": []})
    assert _rent[dst._TELEMETRY_KEY]["surfaces"] == [1, 2, 3]
    assert tg.tabt("decision_signal_telemetry.surfaces") == 0


def test_loftet_holder_selv_om_TAELLEREN_braekker(monkeypatch, _rent):
    """Regnskabet maa aldrig koste os selve beskaeringen.

    En ring uden loft ville vokse til den spiste state-filen — og en
    observabilitets-funktion der braekker det den observerer, er den samme fejl
    som `snapshot()` i `effective_policy` naesten lavede.
    """
    monkeypatch.setattr(tg, "beskaer",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")))
    dst._save({"surfaces": list(range(900)), "reactions": list(range(900))})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == dst._MAX_RECORDS, "loftet forsvandt med taelleren"
    assert len(gemt["reactions"]) == dst._MAX_RECORDS


def test_save_kaster_aldrig(monkeypatch):
    """Telemetri maa aldrig braekke det den maaler — modulet siger det selv:
    «telemetry must never break the caller»."""
    monkeypatch.setattr(dst, "save_json",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk fuld")))
    dst._save({"surfaces": [1], "reactions": []})   # maa ikke kaste
