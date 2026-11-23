"""Tests for pacing-måleren — de fire underdomæner der stod på 0.40 uden grundlag.

MÅLT 23/11-2026: `desk og ord-animation i chat og code`, `chat mode ord-rytme
pacing`, `code mode ord-rytme pacing` og `code mode foldemekanik` stod alle på
0.40 i alle vektorer. Der findes 23 `*.maaling.test.*`-filer / 87 tests der
måler præcis de flader. Denne fil vogter at de bliver læst.

Husets klassiske fejl er at koden skrives og ingen kalder den — derfor tjekker
disse tests både parseren OG at `record()` faktisk skriver til sporet.
"""

from __future__ import annotations

import json

import core.services.desk_pacing_capability as dpc


def _fil(navn: str, *statusser: str) -> dict:
    """Byg en vitest-fil-post som vitest selv skriver den."""
    return {
        "name": f"/x/apps/jarvis-desk/src/lib/{navn}",
        "status": "passed" if all(s == "passed" for s in statusser) else "failed",
        "assertionResults": [{"status": s} for s in statusser],
    }


def _rapport(*filer: dict) -> dict:
    return {"testResults": list(filer), "success": True}


# ─── parseren ──────────────────────────────────────────────────────────


def test_groen_koersel_giver_alle_fire_domaener():
    """De fire domæner skal alle have grundlag i samme kørsel."""
    data = _rapport(
        _fil("streamingTextTail.farve.maaling.test.ts", "passed", "passed"),
        _fil("paceRate.maaling.test.ts", "passed", "passed"),
        _fil("paceRate.fold.maaling.test.ts", "passed"),
    )
    r = dpc.parse_maalinger(data)
    assert set(r) == set(dpc.DOMAENER)
    assert all(d["measured"] for d in r.values()), r


def test_loftet_er_085_som_den_samlede_flade():
    """To målere må ikke melde forskelligt om samme flade."""
    data = _rapport(_fil("paceRate.maaling.test.ts", "passed"))
    r = dpc.parse_maalinger(data)
    d = r["chat mode ord-rytme pacing"]
    assert d["pass_rate"] == 1.0
    assert d["confidence"] == 0.85, "grøn kørsel er bevis for det målte, ikke 1.0"
    assert d["cap"] == 0.85


def test_en_fejlet_test_saenker_den_maalte_vaerdi():
    data = _rapport(_fil("paceRate.maaling.test.ts", "passed", "failed", "passed"))
    d = dpc.parse_maalinger(data)["chat mode ord-rytme pacing"]
    assert d["passed"] == 2 and d["failed"] == 1
    assert d["confidence"] == 0.667, d


def test_ingen_json_giver_ingen_maaling():
    """Tavshed må ikke blive til et tal."""
    r = dpc.parse_maalinger(None)
    assert all(not d["measured"] for d in r.values())
    assert all(d["reason"] for d in r.values()), "en manglende måling skal sige hvorfor"


def test_tom_kørsel_giver_ingen_maaling():
    r = dpc.parse_maalinger({"testResults": []})
    assert all(not d["measured"] for d in r.values())


def test_domaene_uden_matchende_filer_er_ikke_maalt():
    """Et domæne hvis filer forsvinder må ikke arve et andet domænes tal."""
    data = _rapport(_fil("paceRate.maaling.test.ts", "passed"))
    r = dpc.parse_maalinger(data)
    assert r["code mode foldemekanik"]["measured"] is False
    assert "ingen kørte tests" in r["code mode foldemekanik"]["reason"]


def test_springende_tests_taeller_hverken_op_eller_ned():
    """Skippede tests måler intet og må ikke trække raten ned."""
    data = _rapport(_fil("paceRate.fold.maaling.test.ts", "passed", "skipped", "todo"))
    d = dpc.parse_maalinger(data)["code mode foldemekanik"]
    assert d["total"] == 1, "kun den kørte test tæller"
    assert d["confidence"] == 0.85


def test_chat_og_code_faar_samme_vaerdi_og_siger_det():
    """De deler testgrundlag — så skal beviset sige det, ikke lade som om de er to."""
    data = _rapport(_fil("pacingModeller.maaling.test.ts", "passed"))
    r = dpc.parse_maalinger(data)
    assert r["chat mode ord-rytme pacing"]["measured"] is True
    assert r["chat mode ord-rytme pacing"]["confidence"] == (
        r["code mode ord-rytme pacing"]["confidence"]
    )
    assert dpc.FAELLES_MED["chat mode ord-rytme pacing"] == "code mode ord-rytme pacing"
    assert dpc.FAELLES_MED["code mode ord-rytme pacing"] == "chat mode ord-rytme pacing"


def test_domaenenavnene_er_dem_planen_peger_paa():
    """Skriver vi til en nøgle curriculum ikke læser, er målingen usynlig.

    Samme vagt som `test_desk_render_capability.py` har for sit domæne: navnet
    skal være præcis det der står i `confidence_by_domain`.
    """
    fra_planen = {
        "desk og ord-animation i chat og code",
        "chat mode ord-rytme pacing",
        "code mode ord-rytme pacing",
        "code mode foldemekanik",
    }
    assert set(dpc.DOMAENER) == fra_planen


# ─── skrivevejen ───────────────────────────────────────────────────────


def test_record_skriver_intet_naar_intet_er_maalt(isolated_runtime):
    """Uden grundlag skrives intet — tavshed er ikke 0.40."""
    fra_core = dpc.record

    def tom_runner(timeout_s: int):
        return 0, {"testResults": []}, ""

    r = fra_core(runner=tom_runner)
    assert r["domaener"]
    for navn, udfald in r["skrevet"].items():
        assert udfald["recorded"] is False, f"{navn} blev skrevet uden grundlag"


def test_record_skriver_den_maalte_vaerdi(isolated_runtime):
    """Den ægte kæde: parser -> set_domain_confidence -> sporet."""
    from core.services.capability_measurement import maalte_vaerdier

    def groen_runner(timeout_s: int):
        return 0, _rapport(
            _fil("streamingTextTail.farve.maaling.test.ts", "passed"),
            _fil("paceRate.maaling.test.ts", "passed"),
            _fil("paceRate.fold.maaling.test.ts", "passed"),
        ), ""

    r = dpc.record(runner=groen_runner)
    skrevet = {k: v for k, v in r["skrevet"].items() if v.get("recorded")}
    assert skrevet, "en grøn kørsel skal skrive mindst ét domæne"
    maalt = maalte_vaerdier()
    for navn in skrevet:
        assert navn in maalt, f"{navn} mangler i målingssporet"
        assert maalt[navn] == 0.85


def test_record_skriver_bevis_der_navngiver_filerne(isolated_runtime):
    """Et tal uden bevis er en selvrapport med finere navn."""

    def groen_runner(timeout_s: int):
        return 0, _rapport(_fil("pacingModeller.maaling.test.ts", "passed")), ""

    r = dpc.record(runner=groen_runner)
    udfald = r["skrevet"]["chat mode ord-rytme pacing"]
    assert udfald.get("recorded") is True
    assert "pacingModeller" in udfald["evidence"]
    assert "FÆLLES" in udfald["evidence"], (
        "chat/code deler grundlag — beviset skal sige det"
    )


def test_maaling_der_timer_ud_skriver_intet(isolated_runtime):
    import subprocess

    def timeout_runner(timeout_s: int):
        raise subprocess.TimeoutExpired(cmd="npx vitest", timeout=timeout_s)

    r = dpc.record(runner=timeout_runner)
    assert r["ok"] is False
    assert r["domaener"] == {}
    assert "timede ud" in r["reason"]


def test_json_rapporten_kan_laeses_selv_naar_den_mangler():
    """En manglende JSON må ikke kaste — den skal give en ærlig tom måling."""

    def ingen_json(timeout_s: int):
        return 0, None, "noget output"

    r = dpc.measure(runner=ingen_json)
    assert all(not d["measured"] for d in r["domaener"].values())


def test_koersel_bruges_uden_at_koere_vitest():
    """Den delte kørsel må ikke udløse endnu en vitest-kørsel her.

    MÅLT 23/11-2026: hele suiten giver de samme fire tal som den isolerede
    målekørsel (11/11, 20/20, 20/20, 17/17), så underdomænerne kan læses fra
    samme svar som den samlede flade — 44 s sparet pr. kadence-kørsel.
    """
    kaldt: list[int] = []

    def _runner(_t: int):
        kaldt.append(1)
        return 1, None, "skal ikke bruges"

    r = dpc.measure(
        runner=_runner,
        koersel=(
            0,
            "noget output",
            _rapport(_fil("paceRate.maaling.test.ts", "passed")),
        ),
    )
    assert r["ok"] is True
    assert r["domaener"]["chat mode ord-rytme pacing"]["measured"] is True
    assert kaldt == [], "koerslen blev ignoreret og vitest kørt igen"
