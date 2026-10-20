"""Stillingtagen ved tur-afslutning (Bjørn 7/10-2026).

Vagten flytter `output_discipline`s regel — «before you finish a turn that
leaves a next step, call suggest_next_task» — ned til beslutningsøjeblikket.

Det der skal BEVISES her er ikke at noten findes, men at den TIER i de
tilfælde hvor den ville være støj: når forslaget allerede er lagt, når turen
ikke udførte arbejde, og når der ikke er noget svar at tage stilling efter.
En vagt der fyrer på et gæt fylder komponisten med forslag der ikke er
rigtigt arbejde — og slider værktøjets egen regel ned.
"""
from __future__ import annotations

import pytest

from core.services.suggest_standing_guard import (
    SUGGEST_TOOL_NAMES,
    build_nudge,
    mangler_stilling,
    suggest_standing_guard_enabled,
)


def _kald(navn: str) -> dict:
    return {"function": {"name": navn, "arguments": "{}"}}


# ── Den positive kant: arbejde udført, intet forslag lagt ──────────────────

def test_fyrer_naar_arbejde_er_udfoert_og_intet_forslag_blev_lagt():
    assert mangler_stilling(
        called_tool_names=["bash", "read_file", "edit_file"],
        final_text="Jeg rettede dedup-vaernet og pushede.",
    ) is True


# ── Tieren: forslaget ER lagt ──────────────────────────────────────────────

def test_tier_naar_suggest_next_task_allerede_blev_kaldt():
    """Stillingen er taget. En note mere ville være en gentagelse."""
    assert mangler_stilling(
        called_tool_names=["bash", *SUGGEST_TOOL_NAMES],
        final_text="Færdig.",
    ) is False


def test_tier_ogsaa_naar_suggest_er_kaldt_ad_en_indpakket_vej():
    """Navnene kommer udpakkede fra samle_kaldte_navne — også dér skal det ses."""
    from core.services.skill_gate_guard import samle_kaldte_navne
    from core.services.visible_followup_events import ToolExchange

    ex = ToolExchange(text="", tool_calls=[_kald("suggest_next_task")], results=[])
    navne = samle_kaldte_navne([ex], [])
    assert "suggest_next_task" in navne
    assert mangler_stilling(called_tool_names=navne, final_text="Færdig.") is False


# ── Tieren: ingen arbejde ──────────────────────────────────────────────────

def test_tier_naar_turen_ikke_kaldte_et_eneste_vaerktoej():
    """En ren samtale-tur har intet næste skridt at pege på."""
    assert mangler_stilling(called_tool_names=[], final_text="Ja, det passer.") is False


def test_tier_ved_none_og_tomme_navne():
    assert mangler_stilling(called_tool_names=None, final_text="x") is False
    assert mangler_stilling(called_tool_names=["", "  "], final_text="x") is False


# ── Tieren: loftet og den sidste runde ─────────────────────────────────────

def test_tier_naar_der_allerede_er_nudged():
    """Én stillingtagen pr. tur — ellers kunne noten holde turen i live."""
    assert mangler_stilling(
        called_tool_names=["bash"], nudged_already=True, final_text="x",
    ) is False


def test_tier_paa_den_tvungne_afslutningsrunde():
    """På _is_last_round er der ingen runde tilbage at svare i."""
    assert mangler_stilling(
        called_tool_names=["bash"], final_text="x", is_last_round=True,
    ) is False


def test_tier_i_et_autonomt_nat_run():
    """Et nat-run har ingen bruger til stede. Forslaget hoerer til samtalen
    med Bjorn — i en nat-session ville det koste en runde pr. nat uden at
    nogen kunne se det."""
    assert mangler_stilling(
        called_tool_names=["bash"], final_text="x", er_autonom=True,
    ) is False


# ── Tieren: intet svar at tage stilling efter ──────────────────────────────

def test_tier_ved_tom_final_text():
    """Tom completion er en anden vagts sag."""
    assert mangler_stilling(called_tool_names=["bash"], final_text="") is False
    assert mangler_stilling(called_tool_names=["bash"], final_text="   \n ") is False


# ── Fail-retningen: kaster aldrig ──────────────────────────────────────────

def test_kaster_aldrig_paa_skrald():
    """En vagt der kaster vælter hver tur den rører."""
    assert mangler_stilling(called_tool_names=object(), final_text=object()) is False
    assert mangler_stilling(called_tool_names=12345, final_text=None) is False


# ── Noten selv ─────────────────────────────────────────────────────────────

def test_noten_er_maerket_som_system_og_ikke_fra_bjoern():
    note = build_nudge()
    assert "IKKE FRA BJØRN" in note
    assert "suggest_next_task" in note


def test_noten_beder_om_stillingtagen_ikke_om_gentagelse():
    """Formen er Bjørns: et nej er et gyldigt svar — og svaret gentages ikke."""
    note = build_nudge().lower()
    assert "stilling" in note
    assert "gentage" in note


# ── Kontakten ──────────────────────────────────────────────────────────────

def test_tier_naar_pause_and_ask_blev_kaldt():
    """Et spoergsmaal ER en stillingtagen (Bjorn 11/10-2026).

    Foer denne dato talte kun `suggest_next_task`. Saa naar Jarvis havde et
    spoergsmaal, skubbede vagten ham mod komponisten — og spoergsmaalet endte
    i Bjorns skrivefelt som om det var hans egen besked. Det er praecis den
    fejl Bjorn bad om at faa rettet."""
    assert mangler_stilling(
        called_tool_names=["bash", "pause_and_ask"],
        final_text="Jeg har brug for dit valg.",
    ) is False


def test_noten_naevner_baade_naeste_skridt_og_spoergsmaal():
    """Noten skal pege paa den RIGTIGE vej for hvert tilfaelde: et spoergsmaal
    hoerer i pause_and_ask, ikke i komponisten."""
    note = build_nudge()
    assert "suggest_next_task" in note
    assert "pause_and_ask" in note
    assert "anbefalet" in note


def test_kontakten_er_slukket_som_standard():
    """Bjørn 19/10-2026: vagten genstarter turen for at få et forslag, og den
    ekstra runde skubber `done` — så slutsvaret teleporterer ud af folden mens
    det streamer. Reglen bor nu i `output_discipline` i stedet."""
    assert suggest_standing_guard_enabled() is False


@pytest.mark.parametrize("vaerdi", ["1", "true", "yes", "on", "TRUE", " on "])
def test_kontakten_kan_taendes_uden_genstart(monkeypatch, vaerdi):
    monkeypatch.setenv("JARVIS_SUGGEST_STANDING_GUARD", vaerdi)
    assert suggest_standing_guard_enabled() is True


def test_kontakten_forbliver_slukket_ved_enhver_anden_vaerdi(monkeypatch):
    monkeypatch.setenv("JARVIS_SUGGEST_STANDING_GUARD", "maybe")
    assert suggest_standing_guard_enabled() is False
