"""Værnets stemme: hvad siger vi, når det tvungne forsøg OGSÅ gav nul kald?

Baggrund 7/9-2026: vagten opdagede løftet, tvang en runde med
tool_choice=required, fik stadig nul værktøjskald — og skrev det udelukkende
til eventbussen. Bjørn så fire løfter i træk og skrev «Kør» hver gang.
"""
from core.services.hollow_promise_round import (
    hollow_promise_note,
    note_outcome,
    _ser_ud_til_at_mangle_vaerktoejer,
)


def test_nul_kald_er_ikke_loest():
    assert note_outcome(run_id="r", provider="deepseek", model="m", round_index=1,
                        session_id="s", forced=True, tool_calls=0) is False


def test_et_kald_er_loest():
    assert note_outcome(run_id="r", provider="deepseek", model="m", round_index=1,
                        session_id="s", forced=True, tool_calls=1) is True


def test_beskeden_indroemmer_at_intet_blev_udfoert():
    n = hollow_promise_note("deepseek-v4-pro")
    assert "ingen værktøjer" in n
    assert "ikke udført" in n


def test_vision_modellen_naevnes_ved_navn_med_en_udvej():
    n = hollow_promise_note("deepseek-v4-flash-vision-exp")
    assert "deepseek-v4-flash-vision-exp" in n
    # Uden en udvej er det bare en undskyldning.
    assert "Skift model" in n


def test_en_almindelig_model_beskyldes_ikke_for_at_mangle_vaerktoejer():
    n = hollow_promise_note("deepseek-v4-pro")
    assert "ikke ud til at kunne bruge værktøjer" not in n


def test_uden_modelnavn_siger_vi_stadig_sandheden():
    n = hollow_promise_note("")
    assert "ikke udført" in n
    assert "`" not in n          # intet tomt navn i baktikker


def test_kun_maalte_modeller_flages():
    assert _ser_ud_til_at_mangle_vaerktoejer("deepseek-v4-flash-vision-exp")
    assert not _ser_ud_til_at_mangle_vaerktoejer("claude-sonnet-5")
    assert not _ser_ud_til_at_mangle_vaerktoejer("")
