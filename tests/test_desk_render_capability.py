"""Desk render capabilities skal MÅLES, ikke gættes.

MÅLT 20/11-2026: domænet stod på 0.32 i alle 1.000 versioner af
personlighedsvektoren — et LLM-gæt. Den ægte browser-måling fandtes hele
tiden (`*.maaling.test.ts` i rigtig Chromium, CI-jobbet `desk-browser`), men
nul Python-kode refererede den. Fakta i den ene ende, ingen læser i den anden.

Testene her holder fire ting fast:
 1. parseren læser vitest' EGEN opsummering (grøn og rød)
 2. en kørsel uden resultat skriver INTET — tavshed er ikke 0.32
 3. en målt værdi kræver et bevis
 4. domænenøglen er den SAMME som læringsplanen læser

Punkt 4 er det vigtigste: skrev vi til en nøgle planen ikke læser, ville
målingen være lige så død som build-id'et der blev sendt i 26 dage.
"""

from __future__ import annotations

import json

import core.services.desk_render_capability as drc

GROEN = """
 Test Files  4 passed (4)
      Tests  9 passed (9)
   Duration  8.58s
"""

ROED = """
 Test Files  1 failed | 3 passed (4)
      Tests  2 failed | 7 passed (9)
   Duration  9.10s
"""


def _pv_domaener() -> dict:
    from core.runtime.db_cognitive import get_latest_cognitive_personality_vector

    pv = get_latest_cognitive_personality_vector() or {}
    return json.loads(str(pv.get("confidence_by_domain") or "{}"))


def _seed(domains: dict) -> None:
    from core.runtime.db_cognitive import upsert_cognitive_personality_vector

    upsert_cognitive_personality_vector(
        confidence_by_domain=json.dumps(domains),
        communication_style="{}",
        learned_preferences="[]",
        recurring_mistakes="[]",
        strengths_discovered="[]",
        current_bearing="test",
        emotional_baseline="{}",
    )


# --- 1. parseren ---------------------------------------------------------


def test_parser_laeser_groen_opsummering():
    p = drc.parse_vitest(GROEN)
    assert p["measured"] is True
    assert (p["passed"], p["failed"], p["total"]) == (9, 0, 9)


def test_parser_laeser_roed_opsummering():
    p = drc.parse_vitest(ROED)
    assert p["measured"] is True
    assert (p["passed"], p["failed"], p["total"]) == (7, 2, 9)


def test_parser_afviser_no_tests():
    """En suite der kører men måler intet er ikke en grøn måling."""
    p = drc.parse_vitest(" Test Files  no tests\n      Tests  no tests\n")
    assert p["measured"] is False
    assert "no tests" in p["reason"]


def test_parser_afviser_output_uden_opsummering():
    p = drc.parse_vitest("npx: command not found\n")
    assert p["measured"] is False
    assert p["total"] == 0


def test_parser_laeser_springende_tests():
    """MÅLT 20/11-2026: den ægte linje er `3625 passed | 1 skipped (3626)`.

    Formen knækkede den første regex, og parseren meldte «kunne ikke læse
    opsummeringen» om en grøn kørsel. Skippede tests måler intet og skal
    derfor ikke trække raten ned.
    """
    p = drc.parse_vitest("      Tests  3625 passed | 1 skipped (3626)\n")
    assert p["measured"] is True
    assert (p["passed"], p["failed"], p["skipped"], p["total"]) == (3625, 0, 1, 3626)


def test_parser_bruger_den_sidste_opsummering():
    """Vitest skriver opsummeringen til sidst; en tidlig linje må ikke vinde."""
    tekst = "Tests  3 passed (3)\n...mere output...\n      Tests  9 passed (9)\n"
    p = drc.parse_vitest(tekst)
    assert p["total"] == 9


# --- 2. intet målt -> intet skrevet -------------------------------------


def test_maaling_uden_resultat_skriver_intet(isolated_runtime):
    _seed({"desk render capabilities": 0.32})
    result = drc.record(runner=lambda _t: (1, "npx: command not found"))
    assert result["measured"] is False
    assert _pv_domaener()["desk render capabilities"] == 0.32, (
        "en måling der ikke kunne læses må ikke røre tallet"
    )


def test_maaling_der_timer_ud_skriver_intet(isolated_runtime):
    _seed({"desk render capabilities": 0.32})

    def _boom(_t):
        raise drc.subprocess.TimeoutExpired(cmd="npx", timeout=1)

    result = drc.record(runner=_boom)
    assert result["measured"] is False
    assert _pv_domaener()["desk render capabilities"] == 0.32


# --- 3. målt værdi kræver bevis ----------------------------------------


def test_maalt_vaerdi_kraever_bevis(isolated_runtime):
    _seed({"desk render capabilities": 0.32})
    out = drc.set_domain_confidence("desk render capabilities", 0.85, evidence="  ")
    assert out["recorded"] is False
    assert _pv_domaener()["desk render capabilities"] == 0.32


# --- 4. den målte værdi lander i domænet -------------------------------


def test_groen_koersel_skriver_den_maalte_vaerdi(isolated_runtime):
    _seed({"desk render capabilities": 0.32})
    result = drc.record(runner=lambda _t: (0, GROEN))
    assert result["measured"] is True
    assert result["passed"] == 9
    d = _pv_domaener()
    # Loftet: et grønt run beviser det målte, ikke det umålte.
    assert d["desk render capabilities"] == 0.85
    assert result["record"]["before"] == 0.32
    assert "9/9" in result["record"]["evidence"]


def test_roed_koersel_saenker_til_det_maalte(isolated_runtime):
    _seed({"desk render capabilities": 0.85})
    result = drc.record(runner=lambda _t: (1, ROED))
    d = _pv_domaener()
    assert d["desk render capabilities"] == 0.778, (
        "7 af 9 grønne skal give 7/9 — ikke et trinvis fradrag"
    )
    assert result["ok"] is False


# --- 5. nøglen er den planen læser -------------------------------------


def test_domaenet_er_det_samme_som_planen_peger_paa(isolated_runtime):
    """Skrev vi til en anden nøgle end planen læser, var målingen død.

    Samme fejlklasse som build-id'et: en header der blev sendt, men aldrig
    læst. Her er det omvendte krav — læseren skal ramme skriverens nøgle.
    """
    from core.services.self_experiments import generate_learning_curriculum

    _seed({drc.DOMAIN: 0.2})
    plan = generate_learning_curriculum()
    navne = [str(c.get("focus") or "").lower() for c in plan.get("curriculum") or []]
    assert drc.DOMAIN in navne, (
        f"planen peger ikke på {drc.DOMAIN!r} — så læser ingen den målte værdi. "
        f"Planen indeholdt: {navne}"
    )


def test_maalt_tal_fjerner_domaenet_fra_planen(isolated_runtime):
    """Den ægte sammenkobling — og den kan fejle.

    Min første udgave af denne kontrol påstod at en nær-på-stavning ikke måtte
    stå i planen. Den fejlede med rette: planen lister ALLE domæner under 0,5,
    så påstanden kunne aldrig være falsk. En vagt der ikke kan fejle er teater.

    Her er kravet det omvendte og efterprøveligt: står domænet som svaghed på
    0.32, kører en grøn måling, og står det STADIG i planen bagefter, så skrev
    `record()` til en anden nøgle end planen læser — samme skæbne som
    build-id'et der blev sendt i 26 dage uden en læser.
    """
    from core.services.self_experiments import generate_learning_curriculum

    def plan_navne() -> list[str]:
        plan = generate_learning_curriculum()
        return [str(c.get("focus") or "").lower() for c in plan.get("curriculum") or []]

    _seed({drc.DOMAIN: 0.32})
    assert drc.DOMAIN in plan_navne(), "udgangspunktet er ikke svagt — testen måler intet"

    drc.record(runner=lambda _t: (0, GROEN))
    assert drc.DOMAIN not in plan_navne(), (
        "domænet står stadig som svaghed efter en grøn måling — "
        "så skrev record() til en nøgle planen ikke læser"
    )
