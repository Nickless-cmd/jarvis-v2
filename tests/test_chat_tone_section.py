"""Tone-sektionen: kun chat mode, og den skal faktisk nå prompten.

## Hvorfor testen findes

Målt 22/10-2026: `VISIBLE_CHAT_RULES.md` er 38 linjer og 8.919 tegn, og nul
af dem handler om tone. Alle handler om ærlighed og teknisk adfærd. Modellen
blev derfor ikke løgnagtig — den blev rapporterende: korrekt, tør og uden
puls, fordi forsigtighed var det eneste prompten belønnede.

Tonen er derfor en EGEN sektion, ikke linje 39 i regelfilen: 80 tegn
stemning taber på vægt mod 8.919 tegn forsigtighed, præcis som
`mode_orientation` tabte da den lå 97,6 % inde i præfikset.

## Hvad testen vogter — og hvorfor netop det

To ting, og de fejler på hver sin måde:

1. **Grænsen.** Tonen må ikke lække til code mode. Code mode skal fortsætte
   uændret (Bjørn 22/10-2026), og en påtvunget emoji i et teknisk svar er
   støj. Testen måler det gennem den ægte funktion, ikke ved at grep'e kilden.

2. **At den når frem.** Registreringen er FEM steder: funktionen,
   `raw_sections`, `_section_labels`, `FORREST_SEKTIONER` og budget-linjen i
   `attention_budget.py`. Glemmer man budget-linjen, droppes sektionen i
   stilhed — det skete for `mode_orientation` den 22/10. Derfor kører testen
   den ægte budget-vælger og kræver at sektionen kommer ud med indhold.
"""
from __future__ import annotations

import pytest


def _tone(scope: str, *, compact: bool = False) -> str | None:
    from core.services.prompt_contract import _visible_chat_tone_instruction
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    token = set_tool_scope(scope)
    try:
        return _visible_chat_tone_instruction(compact=compact)
    finally:
        reset_tool_scope(token)


def test_chat_mode_faar_tonen():
    tekst = _tone("chat")
    assert tekst, "chat mode fik ingen tone-sektion"
    assert "Tone (chat)" in tekst
    # Rækkefølgen er hele pointen: reaktionen kommer før analysen.
    assert "Reager først" in tekst


def test_code_mode_faar_intet():
    """Code mode skal fortsætte uændret — det er et valg, ikke en forglemmelse."""
    assert _tone("code") is None


def test_tom_scope_faar_intet():
    """Ældre klient uden mode-signal: ingen tone, samme adfærd som i dag."""
    assert _tone("") is None


def test_compact_er_kortere_men_ikke_tom():
    fuld = _tone("chat", compact=True)
    assert fuld, "compact-lanen mistede tonen helt"
    assert len(fuld) < len(_tone("chat") or "")


def test_tonen_naar_faktisk_gennem_budgettet():
    """Den ægte søm: sektionen skal overleve budget-vælgeren med indhold.

    Uden budget-linjen i `attention_budget.py` ville sektionen blive droppet
    i stilhed — løkken itererer kun over budget-dicten, ikke over input.
    """
    from core.services.attention_budget import BUDGET_VISIBLE_FULL, select_sections_under_budget

    tekst = _tone("chat")
    assert tekst

    selected, _trace = select_sections_under_budget(
        budget=BUDGET_VISIBLE_FULL,
        sections={"chat_tone": tekst, "mode_orientation": "Du er i CHAT MODE."},
    )
    assert selected.get("chat_tone"), (
        "chat_tone blev droppet af budgettet — så når den aldrig prompten, "
        "uanset hvor rigtig funktionen er"
    )


def test_tonen_staar_efter_orienteringen_i_praefikset():
    """Først «hvor er du», så «hvordan taler du her».

    LISTEN LÆSES NEDEFRA OG OP: `placer_sektioner` kalder `parts.insert(0, …)`
    for hvert navn, så det sidste navn ender forrest i prompten. Målt
    22/10-2026: med `chat_tone` sidst indledtes live-prompten med
    «## Tone (chat)» og orienteringen kom bagefter — og warmer-prefikset
    matchede ikke. Derfor skal `mode_orientation` stå SIDST i listen.
    """
    from core.services.prompt_sections.section_placement import FORREST_SEKTIONER

    assert "mode_orientation" in FORREST_SEKTIONER
    assert "chat_tone" in FORREST_SEKTIONER
    assert FORREST_SEKTIONER.index("mode_orientation") > FORREST_SEKTIONER.index("chat_tone"), (
        "mode_orientation skal stå SIDST i FORREST_SEKTIONER — listen indsættes "
        "forrest ét ad gangen, så sidste navn bliver det første modellen læser"
    )
