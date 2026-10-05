"""Rotationen skal faktisk SKIFTE model — Fase-uafhaengigt, maalt 10/9-2026.

Jarvis koerte explore tre gange mod Bjoerns maskine. Alle tre runder ramte
samme provider og samme model, selvom `egnede_modeller(undtagen=...)` korrekt
udelukkede den.

AARSAGEN, maalt hele vejen ned:

    rotationens valg : mistral/ministral-3b-latest   capability 0,28
    vagten           : 0,28 < 0,6 -> kasser valget
    routeren svarer  : nvidia-nim/nemotron-3-ultra-550b-a55b
                       (0 vaerktoejskald paa 87 koersler)

Blokken fyrer KUN naar kalderen har valgt eksplicit — og den kasserer netop
det valg. Rotationen var koblet paa og uden virkning, og vagten der skal undgaa
svage modeller rutede TIL den model der fabrikerer.
"""
from __future__ import annotations

import inspect


def test_et_eksplicit_valg_respekteres():
    from core.services import agent_runtime_spawn as sp

    par = inspect.signature(sp.spawn_agent_task).parameters
    assert "respekter_model" in par
    kilde = inspect.getsource(sp.spawn_agent_task)
    assert "and not respekter_model:" in kilde, (
        "capability-vagten kasserer stadig et eksplicit valg")


def test_explore_beder_om_at_faa_sit_valg_respekteret():
    from core.tools import simple_tools_explore as e

    kilde = inspect.getsource(e._explore_spawn)
    assert "respekter_model=bool(provider and model)" in kilde, (
        "explores rotation faar stadig sit valg kasseret nedenstroems")


def test_en_omrutning_maa_ikke_lande_paa_en_der_FABRIKERER():
    """Selv naar vagten omruter: erstatningen skal kunne kalde vaerktoejer. En
    vagt der bytter en svag model for en der fabrikerer, goer det vaerre."""
    from core.services import agent_runtime_spawn as sp

    kilde = inspect.getsource(sp.spawn_agent_task)
    assert "kan_kalde_vaerktoejer(_rp, _rm)" in kilde
    assert "_duer" in kilde


def test_rotationen_vaelger_faktisk_noget_ANDET(isolated_runtime, monkeypatch):
    """Selve rotationen — at `undtagen` bider — er uroert og skal blive ved
    med at virke."""
    from core.services import agent_model_fitness as f

    poster = [
        {"provider": "p1", "model": "m1", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}, "kvalitets_score": 90},
        {"provider": "p2", "model": "m2", "enabled": True, "probe_score": 100,
         "probe_detail": {"follows": True}, "kvalitets_score": 80},
    ]
    monkeypatch.setattr(f, "_registret", lambda: poster)
    alle = f.egnede_modeller(maks=4)
    assert ("p1", "m1") in alle
    uden = f.egnede_modeller(undtagen=frozenset({("p1", "m1")}), maks=4)
    assert ("p1", "m1") not in uden, "undtagen-filteret bider ikke"
    assert ("p2", "m2") in uden


# ── Rotationen i BAGGRUNDEN — maalt 5/10-2026 ────────────────────────────────
#
# Med taalmodighed 0 (default) gaar runde 0 altid ud som en kvittering. Loekken
# i _exec_explore forlader derfor runde 0 uden nogensinde at se svaret — og den
# rotation der ligger i loekken, blev aldrig naaet. Maalt: to scout_agent-kald
# med breadth=thorough kom hjem efter 3,0 og 3,2 s med tool_calls=0 og én
# hensigtserklaering («Jeg starter med at undersoege hvad workspacet indeholder
# om emnet.»). Ingen anden model blev forsoegt, ud af en pool paa fire.
#
# Testene her driver baggrunds-vejen manuelt: facaden fanges, og den
# efterbehandling der foelger med spawnet kaldes med et tomt svar — praecis som
# receipt-laget goer det naar barnet lander for sent.

TOMT_SVAR = {
    "tool_calls": 0,
    "messages": [{"direction": "agent->jarvis", "kind": "result",
                  "content": "Jeg starter med at undersoege hvad workspacet "
                             "indeholder om emnet."}],
}


def _intet_at_efterproeve(svar, **kw):
    """Et svar uden paastande: vaernet finder intet at holde op mod kilden."""
    return {"holder": False, "kontrolleret": 0, "indhold_bekraeftet": 0,
            "fejl": [], "bevis": "intet-bevis"}


def _baggrund(monkeypatch, pool=("m1", "m2", "m3", "m4"), tjek=None):
    """Fake hele vejen ud til facaden og fang HVERT spawn."""
    import core.services.copilot_catalogue as cc
    import core.services.explore_claim_check as ecc
    import core.tools.simple_tools_native as nat

    kald: list[dict] = []

    def _spawn(**kw):
        kald.append(kw)
        return {"status": "accepted", "agent_id": f"a-{len(kald)}",
                "provider": kw.get("provider"), "model": kw.get("model")}

    monkeypatch.setattr(nat, "_explore_spawn", _spawn)
    monkeypatch.setattr(cc, "rangeret",
                        lambda opgave="research", *, maks=4: {
                            "fra_katalog": True,
                            "modeller": [{"model": m} for m in pool]})
    monkeypatch.setattr(ecc, "tjek_paastande", tjek or _intet_at_efterproeve)
    return kald


def test_en_tom_runde_i_baggrunden_roterer_til_naeste_model(monkeypatch):
    """Kravet: svarer foerste model tool_calls=0, skal en ANDEN model faktisk
    blive forsoegt. Foer blev advarslen givet i stedet for forsoegt igen."""
    from core.tools.simple_tools_native import _exec_explore

    kald = _baggrund(monkeypatch)
    r = _exec_explore({"query": "hvad indeholder workspacet om emnet?",
                       "breadth": "thorough"})

    assert r["status"] == "accepted"
    assert len(kald) == 1, "kalderens tur roterede selv — den skal kun kvittere"
    assert kald[0]["model"] == "m1"

    efter = kald[0]["efterbehandling"]
    assert callable(efter), "et sent svar ville slippe uden om baade vaern og rotation"
    besked = efter(TOMT_SVAR)

    assert len(kald) == 2, "en tom runde blev aldrig proevet igen"
    assert kald[1]["model"] == "m2", "rotationen landede ikke paa naeste model"
    assert "m2" in besked, "vaekningen siger ikke hvilken model der blev forsoegt"


def test_rotationen_i_baggrunden_blokerer_ikke_kalderen(monkeypatch):
    """Rotationen hoerer i baggrundstraaden. Bliver den sendt afsted med
    taalmodigheden 60, holder den receipt-traaden — og et nyt forsoeg maa ikke
    koste den traad noget."""
    from core.tools.simple_tools_native import _exec_explore

    kald = _baggrund(monkeypatch)
    _exec_explore({"query": "x"})
    kald[0]["efterbehandling"](TOMT_SVAR)

    assert kald[1]["taalmodighed_s"] == 0.0, (
        "rotationen ventede — den skal vaere baggrund fra start til slut")


def test_rotationen_i_baggrunden_er_bundet_af_maks_runder(monkeypatch):
    """Kaeden maa ikke loebe frit. Tre tomme runder i traek = tre forsoeg, ikke
    et fjerde."""
    from core.tools.simple_tools_explore import _EXPLORE_MAKS_RUNDER
    from core.tools.simple_tools_native import _exec_explore

    kald = _baggrund(monkeypatch)
    _exec_explore({"query": "x"})

    for _ in range(_EXPLORE_MAKS_RUNDER + 1):
        efter = kald[-1].get("efterbehandling")
        if not callable(efter):
            break
        efter(TOMT_SVAR)

    assert len(kald) == _EXPLORE_MAKS_RUNDER, (
        f"kaeden loeb til {len(kald)} forsoeg — loftet er {_EXPLORE_MAKS_RUNDER}")
    assert [k["model"] for k in kald] == ["m1", "m2", "m3"]


def test_et_fabrikeret_svar_dommes_frem_for_at_rotere(monkeypatch):
    """0 vaerktoejskald er ikke i sig selv nok til at rotere. Rejste svaret en
    paastand der FALDT i kilden, er det fabrikeret — det skal have en dom, ikke
    skjules bag et nyt forsoeg."""
    from core.tools.simple_tools_native import _exec_explore

    kald = _baggrund(monkeypatch, tjek=lambda svar, **kw: {
        "holder": False, "kontrolleret": 1, "indhold_bekraeftet": 0,
        "fejl": ["stien findes ikke: core/findes_ikke.py"], "bevis": "uenig"})
    _exec_explore({"query": "x"})

    besked = kald[0]["efterbehandling"]({
        "tool_call_count": 0,
        "messages": [{"direction": "agent->jarvis", "kind": "result",
                      "content": "Det staar i core/findes_ikke.py:42"}]})

    assert len(kald) == 1, "et fabrikeret svar blev skjult bag en ny model"
    assert besked.startswith("ADVARSEL")


def test_vaelg_kandidat_runde_0_maa_bruge_default_men_roterer_ikke():
    """En tom pool maa ikke vaelte runde 0 — den skal falde til
    default-modellen. Til gengaeld maa den ikke give en ROTATION: der er intet
    at rotere til, og et nyt spawn paa den samme model er ikke et forsoeg mere."""
    from core.tools import simple_tools_explore as ex

    assert ex._vaelg_kandidat([], set(), 0, None) == ("", "")
    assert ex._vaelg_kandidat([], set(), 1, None) is None
    assert ex._vaelg_kandidat([("p", "m")], set(), 1, None) == ("p", "m")
    assert ex._vaelg_kandidat([("p", "m")], {("p", "m")}, 1, None) is None
