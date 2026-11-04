"""Exit 1 kan ikke skelne et dødt token fra en opbrugt kvote. Teksten kan."""
from __future__ import annotations

from core.tools.claude_dispatch.failure import (
    NONE, OTHER, QUOTA_EXHAUSTED, TOKEN_DEAD, classify_dispatch_failure,
)

# Begge strenge er målt 4/11-2026 på ægte kald — begge med exit code 1.
DEAD_TOKEN_STDERR = (
    "Error: 401 OAuth access token is invalid. "
    "Your session may have expired; run /login."
)
QUOTA_STDOUT = "You've hit your 5-hour limit · resets 11:30pm"


def test_doedt_token_klassificeres_som_token_dead():
    result = classify_dispatch_failure(
        stdout="", stderr=DEAD_TOKEN_STDERR, exit_code=1,
    )

    assert result.kind == TOKEN_DEAD
    assert "token" in result.action.lower()
    assert result.needs_human is True


def test_opbrugt_kvote_klassificeres_som_quota_exhausted():
    result = classify_dispatch_failure(
        stdout=QUOTA_STDOUT, stderr="", exit_code=1,
    )

    assert result.kind == QUOTA_EXHAUSTED
    assert result.reset_hint == "11:30pm"
    assert "11:30pm" in result.action
    assert result.needs_human is False


def test_kvote_paa_stderr_klassificeres_ogsaa():
    result = classify_dispatch_failure(
        stdout="", stderr=QUOTA_STDOUT, exit_code=1,
    )

    assert result.kind == QUOTA_EXHAUSTED


def test_groen_koersel_er_aldrig_en_fejl():
    """En vellykket opgave kan omtale en kvote-grænse i sit svar."""
    result = classify_dispatch_failure(
        stdout="Jeg har ryddet op. PS: man rammer let 'usage limit' her.",
        stderr="",
        exit_code=0,
    )

    assert result.kind == NONE
    assert result.is_failure is False


def test_ukendt_fejl_er_other_med_sidste_linje():
    result = classify_dispatch_failure(
        stdout="", stderr="Traceback...\nModuleNotFoundError: No module named 'x'",
        exit_code=1,
    )

    assert result.kind == OTHER
    assert "ModuleNotFoundError" in result.detail
    assert result.needs_human is True


def test_doedt_token_vinder_over_kvote_naar_begge_matcher():
    """En kombineret fejlbesked skal ikke sendes videre som «vent på reset».

    Teksten er KONSTRUERET som worst case — ikke målt. Den er her, fordi
    rækkefølgen mellem de to grene ellers ikke kan efterprøves: uden en tekst
    der matcher begge mønstre, ville testen være grøn uanset hvilken gren der
    stod først. De to målte strenge testes hver for sig ovenfor.

    Et dødt token venter ikke på et reset — det skal fornys.
    """
    result = classify_dispatch_failure(
        stdout="",
        stderr="401 OAuth access token is invalid — usage limit reached",
        exit_code=1,
    )

    assert result.kind == TOKEN_DEAD
