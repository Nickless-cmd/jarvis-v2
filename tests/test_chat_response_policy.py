from __future__ import annotations

import json
from pathlib import Path

from core.services.chat_response_policy import (
    CHAT_CLOSURES,
    CHAT_ENGAGEMENT_CORE,
    CHAT_FORMAT_CORE,
    CHAT_RESPONSE_DECISION,
    surface_for_reading_task,
)
from core.services.visible_chat_pragmatics import build_chat_mode_dynamic_tail
from core.tools.tool_scoping import tool_scope


def _chat_prompt(message: str = "", session_id: str | None = None) -> str:
    """Stabil prefix + per-tur hale — den chat-prompt modellen faktisk ser.

    Målt 5/11-2026: i v2-layoutet ligger CHAT_MODE_HOW_I_TALK i den cachebare
    prefix, ikke i halen (`test_prompt_mode_layout.py` ejer placeringen).
    Vagterne her målte kun halen og var derfor røde på en prompt der
    fungerede. De skal måle den samlede vej.
    """
    from core.services.prompt_sections.chat_mode import _visible_mode_orientation_instruction

    with tool_scope("chat"):
        prefix = _visible_mode_orientation_instruction(compact=False) or ""
        rest = build_chat_mode_dynamic_tail("", message=message, session_id=session_id)
    return "\n\n".join(part for part in (prefix, rest) if part)


def _code_prompt(message: str = "", session_id: str | None = None) -> str:
    """Samme for code mode, så «når ikke code mode» måles på den vej der kører."""
    from core.services.prompt_sections.chat_mode import _visible_mode_orientation_instruction

    with tool_scope("code"):
        prefix = _visible_mode_orientation_instruction(compact=False) or ""
        rest = build_chat_mode_dynamic_tail("", message=message, session_id=session_id)
    return "\n\n".join(part for part in (prefix, rest) if part)


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


def test_kravet_naar_chatten_og_ikke_code_mode() -> None:
    """Kravet skal være i den prompt modellen faktisk får — ikke kun i kilden."""
    chat = _chat_prompt(message="sammenlign de to")
    assert "vaelg_flade" in chat
    assert "FØR formuleringen" in chat
    assert "vaelg_flade" not in _code_prompt(message="ret koden")


def test_chat_core_har_proportionalitet_uden_psykoanalyse() -> None:
    engagement = " ".join(CHAT_ENGAGEMENT_CORE.lower().split())
    format_core = " ".join(CHAT_FORMAT_CORE.lower().split())

    assert "kompetent voksen" in engagement
    assert "opfind ikke en diagnose" in engagement
    assert "psykologisk årsag" in engagement
    assert "moraliser ikke" in engagement
    assert "konsekvens for andre" in engagement
    assert "ét præcist spørgsmål" in engagement
    assert "én ændring" in format_core
    assert "ikke hele materialet igen" in format_core
    assert "al tænkelig information" in format_core


def test_chat_core_kraever_et_reelt_svar_efter_vaerktoejer() -> None:
    decision = " ".join(CHAT_RESPONSE_DECISION.lower().split())

    assert "efter sidste værktøjskald" in decision
    assert "aldrig kun en status som 'færdig'" in decision
    assert "gentag ikke statusopdateringer" in decision


def test_nye_regler_naar_chatten_men_ikke_code_mode() -> None:
    chat = _chat_prompt(message="ret kun overskriften")
    code = _code_prompt(message="ret kun overskriften")

    assert "kompetent voksen" in chat
    assert "Efter sidste værktøjskald" in chat
    assert "ikke hele materialet igen" in chat
    assert "kompetent voksen" not in code
    assert "Efter sidste værktøjskald" not in code
