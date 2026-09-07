"""Explore skal EFTERPRØVE sine påstande, ikke gætte på modellen.

Bjørn 7/9-2026: «burde der ikke være et værn i explore der kan checke
påstande, og rotere model hvis en påstand ikke holder?»

Baggrunden: en hel dag med forsøg på at FORUDSIGE om en model ville lyve —
syntetiske prøver, gentagne kørsler, opdigt-detektor. copilot-free/gpt-4.1
bestod dem alle og gav på SAMME spørgsmål både det rigtige svar og tre
opdigtede funktionsnavne med «Confidence: høj».
"""
from unittest.mock import patch

from core.services.explore_claim_check import tjek_paastande
from core.tools.simple_tools_native import _exec_explore

FALSK_STI = "Se src/jarvis/providers/provider_router.py linje 20"
FALSK_LINJE = "core/runtime/provider_router.py:12:def route_provider_request"
SANDT = "core/runtime/provider_router.py:18:def load_provider_router_registry"


# ── selve tjekket ───────────────────────────────────────────────────────────

def test_en_opdigtet_filsti_fanges():
    d = tjek_paastande(FALSK_STI)
    assert d["holder"] is False and "findes ikke" in d["fejl"][0]


def test_et_forkert_linjenummer_fanges():
    d = tjek_paastande(FALSK_LINJE)
    assert d["holder"] is False and "indeholder ikke" in d["fejl"][0]


def test_en_sand_paastand_holder():
    assert tjek_paastande(SANDT)["holder"] is True


def test_ren_prosa_doemmes_ikke():
    """En påstand som «nøglerne læses dynamisk» kan ikke slås op. Et værn der
    afviste den ville afvise gyldige svar."""
    d = tjek_paastande("Nøglerne læses dynamisk via read_runtime_key.")
    assert d["kontrolleret"] == 0 and d["holder"] is True


def test_tomt_svar_doemmes_ikke():
    assert tjek_paastande("")["holder"] is True


def test_vaernet_vaelter_aldrig():
    for x in (None, 12345, {"a": 1}):
        assert tjek_paastande(x)["holder"] is True


# ── rotationen ──────────────────────────────────────────────────────────────

def _spawn(indhold, provider="p1", model="m1"):
    return {"agent_id": "a1", "provider": provider, "model": model,
            "messages": [{"direction": "agent->jarvis", "kind": "result",
                          "content": indhold}]}


def test_holder_paastanden_roteres_der_ikke():
    with patch("core.tools.simple_tools_native._explore_spawn",
               return_value=_spawn(SANDT)) as sp:
        r = _exec_explore({"query": "q"})
    assert r["status"] == "ok" and sp.call_count == 1
    assert r["paastande_kontrolleret"] == 1


def test_holder_den_ikke_proeves_en_anden_model():
    svar = [_spawn(FALSK_LINJE, "p1", "m1"), _spawn(SANDT, "p2", "m2")]
    with patch("core.tools.simple_tools_native._explore_spawn",
               side_effect=svar) as sp, \
         patch("core.services.agent_model_fitness.egnede_modeller",
               return_value=[("p2", "m2")]):
        r = _exec_explore({"query": "q"})
    assert sp.call_count == 2, "roterede ikke da påstanden faldt"
    assert r["status"] == "ok" and "advarsel" not in r


def test_den_fejlende_model_proeves_ikke_igen():
    set_undtagne = {}

    def falsk_egnede(*, undtagen=frozenset(), maks=4):
        set_undtagne["v"] = set(undtagen)
        return [("p2", "m2")]

    with patch("core.tools.simple_tools_native._explore_spawn",
               side_effect=[_spawn(FALSK_LINJE, "p1", "m1"), _spawn(SANDT, "p2", "m2")]), \
         patch("core.services.agent_model_fitness.egnede_modeller", falsk_egnede):
        _exec_explore({"query": "q"})
    assert ("p1", "m1") in set_undtagne["v"]


def test_holder_INGEN_af_forsoegene_afleveres_svaret_med_en_ADVARSEL():
    """At skjule det ville være samme fejl som at tro på det."""
    with patch("core.tools.simple_tools_native._explore_spawn",
               return_value=_spawn(FALSK_STI)), \
         patch("core.services.agent_model_fitness.egnede_modeller",
               return_value=[("p2", "m2")]):
        r = _exec_explore({"query": "q"})
    assert r["status"] == "ok"
    assert "advarsel" in r and "findes ikke" in r["advarsel"]
    assert r["findings"]


def test_ingen_andre_maalte_modeller_stopper_rotationen():
    with patch("core.tools.simple_tools_native._explore_spawn",
               return_value=_spawn(FALSK_STI)) as sp, \
         patch("core.services.agent_model_fitness.egnede_modeller", return_value=[]):
        r = _exec_explore({"query": "q"})
    assert sp.call_count == 1
    assert "advarsel" in r
