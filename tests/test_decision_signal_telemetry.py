"""`decision_signal_telemetry._save` — ringen der tabte i tavshed.

Målt på runtime 13/9-2026:

    decision_signal_telemetry.surfaces   500 poster  <-- paa loftet
    decision_signal_telemetry.reactions  500 poster  <-- paa loftet

At begge står *præcis* på loftet betyder at de har kastet væk, og der fandtes
ikke ét tal for hvor meget. `_save()` gjorde `list(...)[-500:]`.

20/9-2026: tabet havde fået et tal (`beskaer`), men loftet var stadig et
*antal* — så målevinduet flyttede sig når aktiviteten gjorde. Målt samme dag
dækkede de 500 poster 79 døgn (3/7 → 20/9, ~6,3/døgn); ved 500/døgn ville
«7d» reelt være 1 døgn, og tallet ville se lige så rigtigt ud. Horisonten er
nu en tid (`beskaer_efter_alder`), loftet et rent sikkerhedsnet.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


def _p(dage_siden: float, tag: str = "") -> dict:
    """En post med tidsstempel `dage_siden` døgn tilbage."""
    return {"at": (datetime.now(UTC) - timedelta(days=dage_siden)).isoformat(),
            "tag": tag}


# ── horisonten: en tid, ikke et antal (20/9-2026) ────────────────────────────


def test_horisonten_er_en_TID_ikke_et_antal(_rent):
    """Kernen i rettelsen.

    Før bestemte *antallet* vinduet. Nu skal 10 friske poster overleve uanset
    hvor mange gamle der ligger bag dem — ellers flytter vinduet sig med
    aktiviteten, og tallet ser rigtigt ud imens.
    """
    dst._save({"surfaces": [_p(200) for _ in range(500)]
                          + [_p(1, "ny") for _ in range(10)],
               "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == 10, "antallet bestemte stadig vinduet"


def test_save_beskaerer_BEGGE_ringe(_rent):
    dst._save({"surfaces": [_p(200), _p(1, "ny")],
               "reactions": [_p(200)]})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == 1
    assert len(gemt["reactions"]) == 0


def test_save_beholder_de_NYESTE(_rent):
    """Beholdt den de ældste, ville telemetrien fryse ved første vindue og
    aldrig vise hvad der skete siden."""
    dst._save({"surfaces": [_p(200, "gammel"), _p(100, "gammel"), _p(1, "ny")],
               "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert [s["tag"] for s in gemt["surfaces"]] == ["ny"]


def test_uden_tidsstempel_beholdes(_rent):
    """Alder ukendt → behold. Et gæt ville kaste rigtige poster væk."""
    dst._save({"surfaces": [{"tag": "uden-at"}, _p(1, "ny")], "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == 2


def test_naiv_tidsstempel_kaster_ikke(_rent):
    """Et naivt tidsstempel (uden tz) må ikke vælte sammenligningen."""
    naiv = datetime.now(UTC).replace(tzinfo=None).isoformat()
    dst._save({"surfaces": [{"at": naiv, "tag": "naiv"}], "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == 1


def test_save_TAELLER_det_der_ryger(_rent):
    """Kriterium 2: «tolerate loss honestly». Tab er i orden for telemetri —
    det er netop forskellen på telemetri og sandhed. Usynligt tab er ikke."""
    dst._save({"surfaces": [_p(200) for _ in range(600)],
               "reactions": [_p(200) for _ in range(700)]})
    assert tg.tabt("decision_signal_telemetry.surfaces") == 600
    assert tg.tabt("decision_signal_telemetry.reactions") == 700


def test_save_taeller_paa_tvaers_af_kald(_rent):
    dst._save({"surfaces": [_p(200) for _ in range(600)], "reactions": []})
    dst._save({"surfaces": [_p(200) for _ in range(520)], "reactions": []})
    assert tg.tabt("decision_signal_telemetry.surfaces") == 1120


def test_ingen_beskaering_naar_der_er_plads(_rent):
    dst._save({"surfaces": [_p(1, "a"), _p(2, "b")], "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert [s["tag"] for s in gemt["surfaces"]] == ["a", "b"]
    assert tg.tabt("decision_signal_telemetry.surfaces") == 0


def test_loftet_er_et_sikkerhedsnet_ikke_horisonten():
    """Et loft paa 500 poster *var* den effektive horisont. Det maa det ikke
    vaere: ved 500/dogn ville det vaere eet doegn, ikke 90."""
    assert dst._MAX_RECORDS > 500, "loftet er stadig den effektive horisont"
    assert dst._RETENTION_DAYS >= 30


def test_loftet_holder_selv_om_TAELLEREN_braekker(monkeypatch, _rent):
    """Regnskabet må aldrig koste os selve beskæringen.

    En ring uden loft ville vokse til den spiste state-filen — og en
    observabilitets-funktion der brækker det den observerer, er den samme fejl
    som `snapshot()` i `effective_policy` næsten lavede.
    """
    monkeypatch.setattr(
        tg, "beskaer_efter_alder",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("nede")),
    )
    dst._save({"surfaces": list(range(dst._MAX_RECORDS + 500)), "reactions": []})
    gemt = _rent[dst._TELEMETRY_KEY]
    assert len(gemt["surfaces"]) == dst._MAX_RECORDS, "loftet forsvandt med taelleren"


def test_save_kaster_aldrig(monkeypatch):
    """Telemetri maa aldrig braekke det den maaler — modulet siger det selv:
    «telemetry must never break the caller»."""
    monkeypatch.setattr(dst, "save_json",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk fuld")))
    dst._save({"surfaces": [1], "reactions": []})   # maa ikke kaste
