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


def test_tonen_bliver_ikke_klippet_af_budgettet():
    """Sektionen skal komme HEL igennem — ikke bare komme igennem.

    Målt i drift 22/10-2026 efter samtale-reglerne blev lagt ind: sektionen
    var 2270 tegn, men `chat_tone` havde `max_chars=1400` og `remaining`
    kappede den yderligere til 1300. Den kom altså igennem den eksisterende
    vagt (`selected.get("chat_tone")` var sand) mens de sidste regler blev
    skåret af midt i en sætning. En grøn vagt der kun spørger «er den der?»
    kan ikke se det — derfor spørger denne vagt om den er HEL.

    Klippes den, lover overskriften mere end kroppen holder, og det er værre
    end ingen sektion: modellen læser en halv regel som en hel.
    """
    from core.services.attention_budget import BUDGET_VISIBLE_FULL, select_sections_under_budget

    tekst = _tone("chat")
    assert tekst

    selected, trace = select_sections_under_budget(
        budget=BUDGET_VISIBLE_FULL,
        sections={"chat_tone": tekst, "mode_orientation": "Du er i CHAT MODE."},
    )
    ud = selected.get("chat_tone") or ""
    detalje = next((s for s in trace.sections if s.name == "chat_tone"), None)

    assert detalje is not None, "chat_tone optræder slet ikke i budget-tracet"
    assert not detalje.trimmed, (
        f"chat_tone blev KLIPPET ({len(tekst)} → {len(ud)} tegn). Hæv "
        f"`chat_tone.max_chars` OG `total_char_target` i BUDGET_VISIBLE_FULL — "
        f"`remaining` kapper den også, så loftet alene er ikke nok."
    )
    assert ud == tekst, "sektionen kom igennem, men indholdet er ændret undervejs"


def test_sidste_samtale_regel_naar_prompten():
    """Den sidste regel er den der forsvinder først — så den måles eksplicit.

    Klippes sektionen, er det altid halen der forsvinder. Denne vagt kræver
    at den sidste linje i reglerne står i den FAKTISKE prompt, ikke bare i
    funktionens returværdi.
    """
    from unittest.mock import patch

    from core.services import prompt_contract as pc

    with patch("core.tools.tool_scoping.current_tool_scope", return_value="chat"):
        out = pc.build_visible_chat_prompt_assembly(
            provider="ollama",
            model="deepseek-v4.1-flash:cloud",
            user_message="test",
            session_id="test-chat-tone-hale",
        )
    tekst = out.prompt if hasattr(out, "prompt") else str(out)
    assert "Begejstring skal" in tekst, (
        "den sidste samtale-regel nåede ikke den faktiske prompt — sektionen "
        "bliver klippet et sted mellem funktionen og assembly"
    )
