"""Hvorfor loopet stopper — de to huller fra Bjørns session 5/9 kl. 06:05.

Selve loopet er én lang generator der ikke kan instantieres i en unit-test uden
en hel model-lane. Disse tests læser kilden og hævder de to kontrakter der
faktisk gik i stykker, så de ikke kan fjernes uden at nogen opdager det.
Logikken bag dem er dækket af tests/test_tool_world_change.py.
"""
from __future__ import annotations

import inspect

from core.services import visible_runs


def _source() -> str:
    return inspect.getsource(visible_runs)


def test_a_round_that_changed_something_is_never_no_progress():
    """En skrivning efterfulgt af to afviste verifikationer blev læst som
    "modellen spinner" → tvungen afslutning midt i arbejdet."""
    src = _source()
    marker = "_no_new = bool(_round_sig) and ("
    block = src[src.index(marker): src.index(marker) + 1400]
    assert "round_changed_the_world(_a_results)" in block
    assert "_no_new = False" in block
    # Rækkefølgen betyder alt: nulstillingen skal ske EFTER _no_new er beregnet
    # og FØR den bruges til at taelle op.
    assert block.index("round_changed_the_world") < block.index("if _no_new:")


def test_hollow_promise_is_still_detected_on_the_forced_finalize_round():
    """Vagten var slaaet fra naar _is_last_round — praecis den runde hvor
    loopet har fjernet vaerktoejerne og bedt om et endeligt svar."""
    src = _source()
    idx = src.index("hollow_promise_on_forced_finalize")
    block = src[idx - 2600: idx + 400]
    assert "_is_last_round" in block and "is_hollow_promise(" in block
    # Ingen puf (der er ingen runde tilbage) — men runnet skal markeres,
    # udfaldet persisteres og svaret sige det aerligt.
    assert "_run_degenerated = True" in block
    assert '_agentic_loop_exit_reason = "pending-tool-intent"' in block
    assert "note_detected" in block
    # 3/10-2026: selve note-TEKSTEN bor nu i `visible_run_guard_notices`, fordi
    # den skal filtreres ud af model-input (klasse 3) og teksten derfor kun maa
    # staa ÉT sted — ellers kan skriveren og filteret drive fra hinanden.
    # Vagten foelger soemmen og hedder nu kaldet i stedet for prosaen.
    assert "loekken_tvang_en_afslutning()" in block


def test_the_honest_note_reaches_both_the_stream_and_the_persisted_answer():
    """Noten skal naa BEGGE veje: streamen (Bjoern ser den live) og `_a_parts`
    (den persisteres). At den siden filtreres ud af MODEL-input er en anden sag
    og pinnes i `test_visible_run_guard_notices`."""
    src = _source()
    anker = "loekken_tvang_en_afslutning()"
    assert anker in src, f"{anker} kaldes ikke laengere i visible_runs"
    block = src[src.index(anker):][:700]
    assert "_a_parts.append(_stop_note)" in block
    assert "_all_followup_parts.append(_stop_note)" in block
    assert '"delta": _stop_note' in block


def test_followup_rounds_resolve_their_own_thinking_mode():
    src = _source()
    assert "thinking_mode=_thinking_for_round(run, _followup_exchanges)" in src
    assert "thinking_mode=run.thinking_mode," in src, "foerste pas er uaendret"


def test_forced_finalize_uses_pending_tool_intent_not_completed_default():
    src = _source()
    import inspect

    from core.services import visible_run_segment_exit as vrse

    assert "_a_pending_tool_intent" in src
    # Opgave 3 (17/9-2026): udgangen går gennem den durable afregning, som
    # skriver posten før den terminale SSE og selv kalder klassifikationen bag
    # `resolve_agentic_exit`.
    #
    # 30/9-2026: selve afgørelsen er udskilt til `visible_run_segment_exit`, så
    # `settle_segment_exit(` og kæde-opslaget ikke længere står i `visible_runs`.
    # Vagten følger sømmen. SSE og tilstands-markering blev i løkken, fordi de
    # hænger på generatoren — og dét er stadig det denne test skal beskytte.
    assert "afgoer_segment_udfald(" in src
    assert 'yield _sse(_terminal.event_name, _terminal.event_payload)' in src
    enhed = inspect.getsource(vrse)
    assert "settle_segment_exit(" in enhed
    assert "recovery_attempt=" in enhed, "kæde-nummeret skal med til afregningen"
