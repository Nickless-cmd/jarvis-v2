"""Mode-orienteringen: prompten skal vide hvilket rum den bygges i.

## Hvorfor testen findes

`set_tool_scope()` har ligget i `visible_runs.py` siden 24/9 og er kørt FØR
prompten blev bygget — men prompten læste den aldrig. Målt 22/10-2026: nul
forekomster af mode-bevidsthed i hele prompt-kæden. Resultatet var at modellen
gættede på hvilket rum den var i, og derfor måtte bedes om at lade være med at
kode i chat mode.

## Hvad testen vogter — og hvorfor netop det

Registreringen er FIRE steder, og tre af dem fejler i STILHED:

1. `prompt_contract.raw_sections` — uden den findes sektionen ikke.
2. `attention_budget.section_budgets` — `select_sections_under_budget`
   itererer over DENNE dict, ikke over input. Et navn der mangler her bliver
   droppet uden fejl og uden spor.
3. `AttentionBudget.mode_orientation` + de to visible-profiler — uden
   `must_include` kan budgettet fortrænge orienteringen.
4. `section_placement.PRAEFIKS_SEKTIONER` — et navn der ikke står i en af de
   to lister bliver heller ikke placeret.

Test 3 er den vigtigste: den kalder den ÆGTE budget-vælger. En test der kun
læser `raw_sections` ville være grøn selv om sektionen blev droppet.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.services.attention_budget import (  # noqa: E402
    get_attention_budget,
    select_sections_under_budget,
)
from core.services.prompt_contract import (  # noqa: E402
    _visible_mode_orientation_instruction,
)
from core.services.prompt_sections.section_placement import (  # noqa: E402
    HALE_SEKTIONER,
    PRAEFIKS_SEKTIONER,
    placer_sektioner,
)
from core.tools.tool_scoping import reset_tool_scope, set_tool_scope  # noqa: E402


def _section(scope: str, *, compact: bool = False) -> str:
    token = set_tool_scope(scope)
    try:
        text = _visible_mode_orientation_instruction(compact=compact)
    finally:
        reset_tool_scope(token)
    assert text, f"ingen sektion for scope={scope!r}"
    return text


def test_chat_scope_siger_chat_og_peger_paa_code():
    text = _section("chat")
    assert "CHAT MODE" in text
    # Udvejen skal stå der — «ikke her», ikke «det kan jeg ikke».
    assert "code mode" in text
    # Og den må ikke love shell i chat mode.
    assert "Du har fil- og shell-adgang" not in text


def test_code_scope_siger_code_og_kraever_verifikation():
    text = _section("code")
    assert "CODE MODE" in text
    assert "Verificér" in text


def test_tom_scope_gaetter_ikke_i_stilhed():
    """Ældre klienter og mobil uden mode-signal sender tom scope.

    Den må ikke give None — så ville præfikset skifte mellem to tilstande uden
    at nogen kunne se hvorfor — og den må ikke påstå en mode den ikke har.
    """
    text = _section("")
    assert "UDEN mode-signal" in text
    assert "CHAT MODE" not in text


def test_sektionen_er_deterministisk_for_samme_scope():
    """Cache-krav: samme scope skal give byte-identisk tekst.

    Præfikset er det DeepSeek cacher. En sektion der varierer mellem to ture i
    samme mode ville koste hele værktøjsarrayet plus samtalen.
    """
    assert _section("chat") == _section("chat")
    assert _section("code") == _section("code")


def test_kompakt_variant_er_kortere():
    fuld = _section("chat", compact=True)
    assert len(fuld) < len(_section("chat"))


def test_budgettet_slipper_sektionen_igennem():
    """Den ægte vagt: den faktiske budget-vælger, ikke bare dict-medlemskab."""
    for profil in ("visible_full", "visible_compact"):
        budget = get_attention_budget(profil)
        selected, trace = select_sections_under_budget(
            budget=budget,
            sections={"mode_orientation": "x" * 300},
        )
        assert selected.get("mode_orientation"), f"{profil} droppede orienteringen"
        row = [s for s in trace.sections if s.name == "mode_orientation"]
        assert row and row[0].included, f"{profil}: ingen spor-række"


def test_profilerne_kraever_sektionen():
    for profil in ("visible_full", "visible_compact"):
        sb = get_attention_budget(profil).mode_orientation
        assert sb.must_include, f"{profil} kan fortrænge orienteringen"
        assert sb.max_chars >= 400, f"{profil}: for lidt plads til sektionen"


def test_placeringen_er_praefiks_og_foerst():
    assert "mode_orientation" in PRAEFIKS_SEKTIONER
    assert "mode_orientation" not in HALE_SEKTIONER
    assert PRAEFIKS_SEKTIONER[0] == "mode_orientation", (
        "orienteringen skal stå først — står den sent, drukner den i telemetri"
    )
    parts: list[str] = []
    hale: list[str] = []
    placer_sektioner(
        selected={"mode_orientation": "MODE", "capability_truth": "CAP"},
        labels={},
        parts=parts,
        dyn_tail=hale,
        derived_inputs=[],
    )
    assert parts == ["MODE", "CAP"]
    assert hale == []


def test_ingen_levende_tal_i_sektionen():
    """Samme mønstre som `test_praefiks_uden_levende_tal` vogter imod."""
    import re

    for scope in ("chat", "code", ""):
        text = _section(scope)
        assert not re.search(r"\d+\s*min since last session", text)
        assert not re.search(r"\(\d+ dage siden\)", text)
        assert not re.search(r"(curiosity|fatigue|frustration|confidence)=\d", text)


@pytest.mark.parametrize("scope", ["chat", "code", ""])
def test_sektionen_er_ikke_tom_og_under_loftet(scope):
    text = _section(scope)
    assert 100 < len(text) < 900, f"scope={scope!r} gav {len(text)} tegn"
