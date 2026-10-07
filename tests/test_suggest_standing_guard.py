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

def test_kontakten_er_taendt_som_standard():
    assert suggest_standing_guard_enabled() is True


@pytest.mark.parametrize("vaerdi", ["0", "false", "no", "off", "FALSE", " off "])
def test_kontakten_kan_slaas_fra_uden_genstart(monkeypatch, vaerdi):
    monkeypatch.setenv("JARVIS_SUGGEST_STANDING_GUARD", vaerdi)
    assert suggest_standing_guard_enabled() is False


def test_kontakten_forbliver_taendt_ved_enhver_anden_vaerdi(monkeypatch):
    monkeypatch.setenv("JARVIS_SUGGEST_STANDING_GUARD", "yes")
    assert suggest_standing_guard_enabled() is True
