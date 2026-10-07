"""Test af skill-beslutnings-vagten (2/10-2026).

Bjørn spurgte hvorfor skill-fladen aldrig blev brugt, når han kunne se den
ramme. Målt samme dag: i de agentiske runder overlevede INTET skill-værktøj
router+pin, så tilbuddet tabte til bash hver gang. Vagten gør tilbuddet til et
krav der ikke kan ties ihjel.

Husets regel: en vagt skal have en test der ser den **afvise**. Den ligger i
`test_ignoreret_match_afvises`.
"""
from __future__ import annotations

from core.services import skill_gate_guard as g


# ────────────────────────────────────────────── det positive (vagten fyrer)

def test_ignoreret_match_afvises():
    """Kernen: et stærkt match, ingen skill kaldt, navnet ikke nævnt → fyr."""
    assert g.is_unanswered_skill_match(
        primary_matches=["code-review"],
        called_tool_names=["bash", "read_file", "write_file"],
        final_text="Jeg har gennemgået koden og rettet tre ting.",
    ) is True


# ────────────────────────────────────────────── det negative (vagten tier)

def test_uden_match_fyrer_den_ikke():
    """Uden et primært match er der intet at svare på."""
    assert g.is_unanswered_skill_match(
        primary_matches=[],
        called_tool_names=["bash"],
        final_text="Færdig.",
    ) is False


def test_invokeret_skill_godkendes():
    """Blev skillet brugt, er valget truffet."""
    assert g.is_unanswered_skill_match(
        primary_matches=["code-review"],
        called_tool_names=["skill_invoke"],
        final_text="Jeg gennemgik koden.",
    ) is False


def test_naevnt_ved_navn_godkendes():
    """Én linje om hvorfor ikke er nok — navnet i svaret er sporet på det."""
    assert g.is_unanswered_skill_match(
        primary_matches=["code-review"],
        called_tool_names=["bash"],
        final_text="Jeg springer code-review over her; opgaven er en enkelt linje.",
    ) is False


def test_kun_én_nudge_pr_tur():
    """Cap 1. Uden den ville en tur kunne puffes i det uendelige."""
    assert g.is_unanswered_skill_match(
        primary_matches=["code-review"],
        called_tool_names=[],
        final_text="Færdig.",
        nudged_already=True,
    ) is False


def test_tomt_svar_er_en_anden_vagts_sag():
    """Intet svar at vurdere — empty-completion håndteres andetsteds."""
    assert g.is_unanswered_skill_match(
        primary_matches=["code-review"],
        called_tool_names=[],
        final_text="   ",
    ) is False


def test_killswitch_uden_genstart(monkeypatch):
    monkeypatch.setenv("JARVIS_SKILL_GATE_GUARD", "0")
    assert g.skill_gate_guard_enabled() is False
    monkeypatch.setenv("JARVIS_SKILL_GATE_GUARD", "1")
    assert g.skill_gate_guard_enabled() is True
    monkeypatch.delenv("JARVIS_SKILL_GATE_GUARD", raising=False)
    assert g.skill_gate_guard_enabled() is True


def test_kaster_aldrig_paa_skrald():
    """Fail-open: en vagt der kaster ville vælte hver tur den rører."""
    assert g.is_unanswered_skill_match(
        primary_matches=None, called_tool_names=None, final_text=None) is False
    assert g.is_unanswered_skill_match(
        primary_matches=[""], called_tool_names=[], final_text="x") is False
    assert g.build_nudge([]) == ""


def test_nudgen_navngiver_skillet_og_begge_veje():
    tekst = g.build_nudge(["code-review"])
    assert "code-review" in tekst
    assert "skill_invoke" in tekst
    assert "én linje" in tekst


# ── samle_kaldte_navne: de to huller og deres kanter (3/10-2026) ───────────
#
# Begge huller blev fundet i PRODUKTION, ikke af en test, fordi koden sad
# inline i en 7.600-linjers async-generator. Den er nu udskilt, og hver kant
# har sin egen test — inklusive de fire veje et argument kan være ubrugeligt.

import json as _json

from core.services.skill_gate_guard import samle_kaldte_navne
from core.tools.kaldt_vaerktoej import KALD_NAVN


class _Ex:
    """Minimal ToolExchange — kun det feltet funktionen læser."""

    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


def _kald(navn: str, argumenter=None):
    """Et kald som en udbyder sender det: arguments er en JSON-STRENG."""
    fn = {"name": navn}
    if argumenter is not None:
        fn["arguments"] = _json.dumps(argumenter)
    return {"function": fn}


def test_direkte_kald_gaar_uaendret_igennem():
    assert samle_kaldte_navne([], [_kald("skill_invoke", {"name": "code-review"})]) == [
        "skill_invoke"
    ]


def test_transportnavnet_pakkes_ud_til_det_aegte_navn():
    """HUL 1: et skill hentet med `call_loaded_tool` stod med transport-navnet,
    saa vagten konkluderede «intet skill kaldt» og fyrede falskt."""
    kald = _kald(KALD_NAVN, {"navn": "skill_invoke", "argumenter": {"name": "docx"}})
    assert samle_kaldte_navne([], [kald]) == ["skill_invoke"]


def test_den_AKTUELLE_rundes_kald_er_med():
    """HUL 2: `_a_tool_calls` er per-runde, mens rundens exchange foerst lægges
    i `_followup_exchanges` EFTER gaten. Maalt 3/10: nudgen fyrede 66 sekunder
    efter `skill_invoke` i samme run, fordi kun exchangene blev laest."""
    tidligere = [_Ex([_kald("read_file", {"path": "/x"})])]
    nu = [_kald("skill_invoke", {"name": "code-review"})]
    assert samle_kaldte_navne(tidligere, nu) == ["read_file", "skill_invoke"]


def test_begge_kilder_laeses_selv_naar_den_ene_er_tom():
    nu = [_kald("skill_invoke")]
    assert samle_kaldte_navne(None, nu) == ["skill_invoke"]
    assert samle_kaldte_navne([_Ex([_kald("skill_chain")])], None) == ["skill_chain"]
    assert samle_kaldte_navne(None, None) == []


def test_ugyldig_json_lader_transportnavnet_staa():
    """Fail-retningen: kan det indre navn ikke laeses, er svaret «ukendt
    vaerktoej» (status quo) og ikke «et skill blev brugt». Et falsk «skill
    kaldt» ville slaa vagten fra i TAVSHED, og det er den dyre retning."""
    kald = {"function": {"name": KALD_NAVN, "arguments": "{ikke json"}}
    assert samle_kaldte_navne([], [kald]) == [KALD_NAVN]


def test_gyldig_json_der_ikke_er_et_objekt_rammer_samme_retning():
    for raa in ("[1, 2]", '"tekst"', "null", "7"):
        kald = {"function": {"name": KALD_NAVN, "arguments": raa}}
        assert samle_kaldte_navne([], [kald]) == [KALD_NAVN], raa


def test_dispatcher_uden_indre_navn_fejler_HOEJLYDT():
    """`pak_ud`s egen kontrakt: uden brugbart navn returneres dispatcher-navnet,
    saa det fejler som et ukendt vaerktoej frem for at udfoere ingenting."""
    for args in ({}, {"navn": ""}, {"navn": "   "}, {"navn": KALD_NAVN}):
        assert samle_kaldte_navne([], [_kald(KALD_NAVN, args)]) == [KALD_NAVN], args


def test_argumenter_som_dict_virker_ogsaa():
    """Nogle veje giver arguments som et objekt frem for en streng."""
    kald = {"function": {"name": KALD_NAVN,
                         "arguments": {"navn": "skill_gate", "argumenter": {}}}}
    assert samle_kaldte_navne([], [kald]) == ["skill_gate"]


def test_skrald_springes_over_uden_at_kaste():
    """En vagt der kaster vaelter hver tur den roerer."""
    skrald = [None, "streng", 7, {}, {"function": None}, {"function": "nej"},
              {"function": {}}, {"ingen": "function"}]
    assert samle_kaldte_navne([_Ex(None), _Ex("nej"), None], skrald) == [""]


def test_raekkefoelgen_er_exchanges_FOER_den_aktuelle_runde():
    """Ordenen er ikke kosmetik: den oprindelige inline-kode havde den, og
    `is_unanswered_skill_match` laeser listen som turens forloeb."""
    ud = samle_kaldte_navne(
        [_Ex([_kald("a")]), _Ex([_kald("b")])], [_kald("c")])
    assert ud == ["a", "b", "c"]


def test_vagten_i_visible_runs_kalder_den_UDSKILTE_funktion():
    """En vagt ingen kalder er doed kode — husets hyppigste moenster. Her er
    risikoen konkret: stod indsamlingen igen inline, ville kanterne ovenfor
    maale et modul produktionen ikke bruger."""
    import ast
    import pathlib

    src = pathlib.Path("core/services/visible_runs.py").read_text()
    assert "samle_kaldte_navne as _sg_navne" in src, "importen mangler"
    assert "_sg_navne(" in src, "den udskilte funktion kaldes ikke"
    # Og indsamlingen maa ikke vaere gentaget inline ved siden af.
    assert "_sg_pak_ud" not in src, (
        "udpakningen staar igen inline i visible_runs — den hoerer i "
        "skill_gate_guard.samle_kaldte_navne, saa der er EN definition")
    ast.parse(src)
