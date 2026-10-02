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
