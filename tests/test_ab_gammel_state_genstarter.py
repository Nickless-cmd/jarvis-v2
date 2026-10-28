"""En A/B-state der er uforenelig med flag-tilstanden skal erstattes (28/10-2026).

BAGGRUND — målt i produktion, ikke gættet:

`prompt_ablation_state` blev skrevet 17/8-2026 med `arm: "absent"` mens
`prompt_relevance_explore_live_enabled` var `false`. I shadow udelades ingen sektion, så
`record_trial` returnerer straks i absent-grenen. Staten kunne derfor ALDRIG tælle.

`maybe_start_ablation` havde en guard: «findes der en state med `tt`, returnér den». Den
gjorde derfor det modsatte af sit formål — den værgede om et forsøg der var dødt fra
fødslen og blokerede ethvert nyt.

Målt konsekvens: `prompt_section_freq` blev opdateret hver tur (20:11:34), mens
`present_total` stod på 0 siden 17/8. Kæden kørte halvt, og intet sted stod der at den
gjorde det.

Disse tests værner den modsatte adfærd: en død state skal erstattes, en levende skal
bevares — og en state med ægte ABSENT-data må ikke smides væk fordi flaget tilfældigvis
er slukket nu.
"""

from __future__ import annotations

import pytest

from core.services import central_prompt_explore as cpe


@pytest.fixture()
def butik(monkeypatch):
    """In-memory kv-store + styrbart flag + fast kandidat. Rører hverken DB eller levende state."""
    lager: dict[str, object] = {}
    flag = {"live": False}

    monkeypatch.setattr(cpe, "_kv_get", lambda k, d=None: lager.get(k, d))
    monkeypatch.setattr(cpe, "_kv_set", lambda k, v: lager.__setitem__(k, v))
    monkeypatch.setattr(cpe, "is_explore_live", lambda: flag["live"])
    # Kandidat-kilden læser produktions-hyppigheder. Uden denne patch måler testen
    # hvorvidt der findes data i basen — ikke min logik. Den skal være deterministisk.
    monkeypatch.setattr(cpe, "_is_frozen", lambda section: False)
    import core.services.central_prompt_composer as _cpc

    monkeypatch.setattr(
        _cpc,
        "build_relevance_candidates",
        lambda: [{"turn_type": "opgave", "section": "kerne-selv (Centralens midte)"}],
    )
    return lager, flag


def _doed_state() -> dict:
    """Præcis den form der lå i produktionen 17/8."""
    return {
        "tt": "opgave",
        "sec": "kerne-selv (Centralens midte)",
        "arm": "absent",
        "left": 15,
        "absent_good": 0,
        "absent_total": 0,
        "present_good": 0,
        "present_total": 0,
    }


def test_doed_absent_state_i_shadow_erstattes(butik):
    """MODPRØVEN: uden fixet ville denne state blive returneret og aldrig tælle."""
    lager, flag = butik
    lager[cpe._STATE_KEY] = _doed_state()
    flag["live"] = False

    st = cpe.maybe_start_ablation()

    assert st is not None, "der skal startes et nyt forsøg"
    assert st["arm"] == "present", (
        "i shadow er PRESENT den eneste arm der kan tælle — en ny state skal starte der"
    )


def test_doed_state_kan_faktisk_taelle_efter_genstart(butik):
    """Kernen i sagen: efter genstart skal et udfald ende i present_total, ikke forsvinde."""
    lager, flag = butik
    lager[cpe._STATE_KEY] = _doed_state()
    flag["live"] = False

    st = cpe.maybe_start_ablation()
    cpe.record_trial(st["tt"], [st["sec"]], "completed")

    efter = lager[cpe._STATE_KEY]
    assert efter["present_total"] == 1, "udfaldet skal tælles ind i PRESENT-armen"
    assert efter["present_good"] == 1


def test_gyldig_absent_state_bevares_naar_flaget_er_taendt(butik):
    """MODPRØVE: med flaget TÆNDT er absent-armen gyldig. Dens data må ikke smides væk."""
    lager, flag = butik
    levende = _doed_state()
    levende["absent_total"] = 7
    levende["absent_good"] = 5
    lager[cpe._STATE_KEY] = levende
    flag["live"] = True

    st = cpe.maybe_start_ablation()

    assert st["absent_total"] == 7, "ægte ABSENT-data skal bevares"
    assert st["arm"] == "absent"


def test_present_state_i_shadow_bevares(butik):
    """En state der allerede står på PRESENT er forenelig — den skal fortsætte, ikke nulstilles."""
    lager, flag = butik
    igang = _doed_state()
    igang["arm"] = "present"
    igang["present_total"] = 9
    igang["present_good"] = 8
    lager[cpe._STATE_KEY] = igang
    flag["live"] = False

    st = cpe.maybe_start_ablation()

    assert st["present_total"] == 9, "baseline skal akkumulere videre, ikke starte forfra"
    assert st["arm"] == "present"
