from __future__ import annotations

import json
from pathlib import Path

from core.services.chat_response_policy import CHAT_CLOSURES, surface_for_reading_task


def test_presentation_eval_cases_cover_thresholds_and_closures() -> None:
    cases = json.loads(
        (Path(__file__).parent / "fixtures" / "chat_response_policy_cases.json").read_text()
    )
    assert len(cases) >= 12
    for case in cases:
        assert case["closure"] in CHAT_CLOSURES, case["name"]
        assert surface_for_reading_task(
            case["task"], item_count=case["items"],
            shared_dimensions=case["dimensions"],
            already_rendered=case.get("rendered", False),
        ) == case["surface"], case["name"]



def test_beslutningen_skal_traeffes_foer_formuleringen() -> None:
    """Fælden: fladevalget blev truffet bagefter, ud fra hvad der allerede stod.

    Målt 24/10-2026: `vaelg_flade` blev bygget kl. 20:21 og første gang kaldt
    55 minutter senere — midt i et svar hvor jeg forklarede hvorfor jeg ikke
    bruger flader. Reglen fandtes, værktøjet virkede, men intet bandt dem
    sammen i tid. Derfor står kravet nu i selve beslutningsreglen.
    """
    from core.services.chat_response_policy import CHAT_PRESENTATION_DECISION

    tekst = " ".join(CHAT_PRESENTATION_DECISION.split())
    assert "vaelg_flade" in tekst
    assert "FØR formuleringen" in tekst
    assert "før du skriver den første sætning" in tekst
    # Kaldet må ikke lække ud i svaret til brugeren.
    assert "nævn det aldrig" in tekst


def test_kravet_naar_chat_halen_og_ikke_code_mode() -> None:
    """Kravet skal være i den prompt modellen faktisk får — ikke kun i kilden."""
    from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
    from core.tools.tool_scoping import reset_tool_scope, set_tool_scope

    token = set_tool_scope("chat")
    try:
        tail = build_chat_mode_dynamic_tail("", message="sammenlign de to", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "vaelg_flade" in tail
    assert "FØR formuleringen" in tail

    token = set_tool_scope("code")
    try:
        code_tail = build_chat_mode_dynamic_tail("", message="ret koden", session_id=None)
    finally:
        reset_tool_scope(token)
    assert "vaelg_flade" not in code_tail
