from core.services.visible_run_terminal_recovery import resolve_agentic_exit
from core.services.visible_terminal_policy import TerminalState


def test_forced_final_dsml_intent_becomes_recovery_event():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Nu samler jeg loggen.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=True,
    )
    assert result.exit_reason == "pending-tool-intent"
    assert result.decision.state is TerminalState.RECOVERING
    assert result.event_name == "run_recovery"
    assert result.event_payload["continuing"] is True


def test_forced_final_with_explicit_conclusion_can_complete():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Konklusionen er, at firewall-reglen blokerede trafikken.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=False,
    )
    assert result.exit_reason == "completed"
    assert result.decision.state is TerminalState.COMPLETED
    assert result.event_name == ""


def test_forced_final_answer_without_magic_completion_words_does_not_restart():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Her er resultatet: Firewall-reglen blokerede trafikken. Reglen er nu ændret.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=False,
    )
    assert result.decision.state is TerminalState.COMPLETED
    assert result.event_name == ""


def test_forced_final_with_explicit_continuing_action_recovers():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Jeg har undersøgt loggen og samler nu resultaterne.",
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=False,
    )
    assert result.exit_reason == "forced-finalize-unverified"
    assert result.decision.state is TerminalState.RECOVERING
    assert result.event_payload["continuing"] is True


def test_forced_final_without_an_answer_still_recovers():
    result = resolve_agentic_exit(
        exit_reason="completed", final_text=" ",
        finish_reason="stop", forced_finalize=True,
    )
    assert result.decision.state is TerminalState.RECOVERING


def test_negated_completion_claim_never_counts_as_evidence():
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text="Opgaven er ikke afsluttet; jeg mangler stadig verifikationen.",
        finish_reason="stop",
        forced_finalize=True,
    )
    assert result.exit_reason == "forced-finalize-unverified"
    assert result.decision.state is TerminalState.RECOVERING


def test_length_finish_recovers_even_with_partial_text():
    result = resolve_agentic_exit(
        exit_reason="completed", final_text="Et halvt svar",
        finish_reason="length", forced_finalize=False,
    )
    assert result.exit_reason == "completed-truncated"
    assert result.decision.state is TerminalState.RECOVERING


def test_exhausted_recovery_chain_never_promises_another_continuation():
    result = resolve_agentic_exit(
        exit_reason="early-exit-tool-only",
        final_text="",
        recovery_attempt=3,
        recovery_limit=3,
    )
    assert result.decision.state is TerminalState.FAILED_TERMINAL
    assert result.event_payload["continuing"] is False
    assert result.event_payload["state"] == "failed_terminal"


def test_visible_run_routes_exit_through_terminal_recovery():
    """Opgave 3 (17/9-2026): udgangen går gennem den durable afregning, som
    skriver posten FØR den terminale SSE. Klassifikationen er den samme —
    `resolve_agentic_exit` er stadig den rene funktion bag den.

    30/9-2026: selve afgoerelsen er udskilt til `visible_run_segment_exit`, saa
    soemmen ligger et led laengere ude. Vagten foelger den i stedet for at pege
    paa et kald der er flyttet — og tjekker koblingen paa modulet, ikke kun i
    teksten: en import der braekker ville ellers slippe igennem en
    streng-soegning.
    """
    import inspect
    from core.services import visible_run_segment_exit as vrse
    from core.services import visible_run_segment_settlement as vrss
    from core.services import visible_runs
    source = inspect.getsource(visible_runs)
    assert "afgoer_segment_udfald(" in source
    assert "settle_segment_exit(" not in source, (
        "afgoerelsen hoerer i `visible_run_segment_exit`, ikke i loekken")
    assert "settle_segment_exit(" in inspect.getsource(vrse)
    assert vrse.settle_segment_exit is vrss.settle_segment_exit
    assert '_agentic_loop_exit_reason = "early-exit-empty-text"' in source
    assert '_agentic_loop_exit_reason = "early-exit-tool-only"' in source
    assert '_agentic_loop_exit_reason = "early-exit-loop-gate-skip"' in source


# ── 26/10-2026: kun FØRSTEPERSON er et løfte om fortsat arbejde ──────────────
#
# Målt: 124 runs bar `forced-finalize-unverified`; 65 var terminalt opgivet i
# de sidste 14 dage — hver efter at brugeren havde fået sit svar. Årsagen var at
# verbet + «nu» matchede uden subjekt, så en beskrivelse af et værktøj der
# kører blev læst som mit eget løfte. Disse fire tests pinner grænsen.

def test_vaerktoej_der_koerer_er_ikke_et_loefte_om_fortsat_arbejde():
    """«bash kører nu» beskriver et kald — det er ikke uafsluttethed."""
    from core.services.visible_run_terminal_recovery import has_incompletion_evidence
    assert has_incompletion_evidence(
        "Kanalen er åben, så `bash` kører nu på CheifOne — derfor fejlede sti-opslaget."
    ) is False


def test_kommando_i_baggrunden_er_ikke_et_loefte():
    from core.services.visible_run_terminal_recovery import has_incompletion_evidence
    assert has_incompletion_evidence(
        "Kommandoen kører nu i baggrunden på din maskine."
    ) is False


def test_foerstepersons_loefte_er_stadig_uafsluttet():
    """Grænsen må ikke blive så bred at den ægte form slipper igennem."""
    from core.services.visible_run_terminal_recovery import has_incompletion_evidence
    assert has_incompletion_evidence(
        "Jeg har undersøgt loggen og samler nu resultaterne."
    ) is True
    assert has_incompletion_evidence("Jeg kører nu testen.") is True


def test_et_faerdigt_svar_der_naevner_en_begraensning_genstarter_ikke():
    """Et komplet svar må gerne sige hvad der IKKE virkede, uden at blive
    genstartet — ellers straffes ærlig rapportering."""
    from core.services.visible_run_terminal_recovery import resolve_agentic_exit
    from core.services.visible_terminal_policy import TerminalState
    result = resolve_agentic_exit(
        exit_reason="completed",
        final_text=(
            "Kanalen er åben, så `bash` kører nu på din maskine. "
            "Jeg fandt de tre lister og har rettet den første."
        ),
        finish_reason="stop",
        forced_finalize=True,
        pending_tool_intent=False,
    )
    assert result.exit_reason == "completed"
    assert result.decision.state is TerminalState.COMPLETED
