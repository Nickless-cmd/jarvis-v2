"""Grounded capability follow-up — det andet pas efter en udført evne.

Når en evne (capability) er kørt, får modellen resultatet tilbage og skriver
svaret til Bjørn ud fra det, der FAKTISK skete. Det er dét, der gør svaret
grounded frem for en genfortælling af, hvad den havde tænkt sig.

Her ligger fire ting der hører sammen: at bygge follow-up-beskeden (én evne og
flere evner) og at køre selve passet. De to prædikater neden for hører med,
fordi de kun bruges til at farve netop denne besked — kode-gennemgang og
«husk dette» skal have hver sin instruktion.

Boy-Scout-udskillelse 2026-09-07: `visible_runs` var 7.352 linjer. Modulet
importerer `visible_runs` DOVENT (inde i funktionerne), så der opstår ingen
cyklus, og symbolerne re-eksporteres derfra af hensyn til eksisterende
kaldere og tests.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.services.visible_model_types import VisibleModelResult

if TYPE_CHECKING:  # kun til typer — ingen import i runtime, ingen cyklus
    from core.services.visible_runs import VisibleRun

logger = logging.getLogger(__name__)


def _visible_runs():
    """Doven import. På modulniveau ville det være en cyklus — visible_runs
    importerer os."""
    from core.services import visible_runs as _vr
    return _vr

def _run_grounded_capability_followup(
    run: "VisibleRun",
    *,
    capability_id: str,
    invocation: dict[str, object],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_capability_followup_message(
        run,
        capability_id=capability_id,
        invocation=invocation,
        initial_model_text=initial_model_text,
    )
    try:
        # Hentes gennem visible_runs ved KALDET, ikke ved import. En direkte
        # import bandt den rigtige funktion, og så ramte tests' monkeypatch af
        # `visible_runs.execute_visible_model` ikke længere — udskillelsen ville
        # have taget sømmen med sig.
        return _visible_runs().execute_visible_model(
            message=followup_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
        )
    except Exception as exc:
        _visible_runs()._update_visible_execution_trace(
            run,
            {
                "provider_second_pass_status": "failed",
                "provider_error_summary": str(exc) or "second-pass-provider-error",
            },
        )
        return None


def _build_grounded_capability_followup_message(
    run: "VisibleRun",
    *,
    capability_id: str,
    invocation: dict[str, object],
    initial_model_text: str,
) -> str:
    execution_mode = str(invocation.get("execution_mode") or "unknown")
    status = str(invocation.get("status") or "unknown")
    result = invocation.get("result") or {}
    detail = str(invocation.get("detail") or "").strip()
    result_text = ""
    if isinstance(result, dict):
        result_text = str(result.get("text") or "").strip()
    parts = [
        "Second-pass visible response task.",
        "You have already completed one bounded capability invocation for the current user turn.",
        "Respond to the user in ordinary prose only.",
        "Every substantive claim must be grounded in the capability result below.",
        "If runtime facts are thin, say what remains uncertain instead of smoothing it over.",
        "If documentation and code or command output conflict, prefer code and command output.",
        "README or file-structure summaries do not outrank direct code/file evidence.",
        "If the user asked for code analysis, do not call this a code analysis unless you have actually read concrete code files.",
        "If more read-only data is clearly needed and the task is still bounded, you may emit more <capability-call ... /> tags instead of asking the user for permission to continue.",
        "Only ask the user to continue when the next step needs approval or the goal is genuinely unclear.",
        f"Original user message: {run.user_message}",
        f"Capability used: {capability_id}",
        f"Capability status: {status}",
        f"Capability execution mode: {execution_mode}",
    ]
    if _is_memory_commit_request(run.user_message):
        parts.append(
            "If the user asked you to remember or save something and the write succeeded, state that it has been saved. Do not talk about syntax unless the runtime result explicitly failed."
        )
    if result_text:
        parts.append("Capability result text:")
        parts.append(result_text)
    elif detail:
        parts.append(f"Capability result detail: {detail}")
    return "\n".join(parts)


def _run_grounded_multi_capability_followup(
    run: "VisibleRun",
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_multi_capability_followup_message(
        run,
        capability_results=capability_results,
        initial_model_text=initial_model_text,
    )
    try:
        # Hentes gennem visible_runs ved KALDET, ikke ved import. En direkte
        # import bandt den rigtige funktion, og så ramte tests' monkeypatch af
        # `visible_runs.execute_visible_model` ikke længere — udskillelsen ville
        # have taget sømmen med sig.
        return _visible_runs().execute_visible_model(
            message=followup_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
        )
    except Exception as exc:
        _visible_runs()._update_visible_execution_trace(
            run,
            {
                "provider_second_pass_status": "failed",
                "provider_error_summary": str(exc) or "second-pass-provider-error",
            },
        )
        return None


def _build_grounded_multi_capability_followup_message(
    run: "VisibleRun",
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> str:
    n = len(capability_results)
    parts = [
        "Second-pass visible response task.",
        f"You executed {n} capabilit{'y' if n == 1 else 'ies'} this turn. Results are below.",
        "",
        "Respond to the user grounded in these results.",
        "Every substantive claim must be grounded in one or more concrete capability results below.",
        "If runtime facts are thin, stale, or conflicting, say that plainly.",
        "If docs and code disagree, prefer code and direct command/file output.",
        "README, pyproject, or directory names are not enough for a real code analysis by themselves.",
        "If the user asked for code analysis, do not stop at structure or documentation; read concrete code files before claiming analysis.",
        "If more read-only data is clearly needed and the task is still bounded, emit additional <capability-call ... /> tags now and continue autonomously.",
        "Only ask the user to continue when the next step needs approval or the goal is genuinely unclear.",
        "",
        f"Original user message: {run.user_message}",
    ]
    if _is_memory_commit_request(run.user_message):
        parts.append(
            "If the user asked you to remember or save something and the write succeeded, state that it has been saved. Do not describe block syntax or retry mechanics unless the runtime result explicitly failed."
        )
    if _is_code_analysis_request(run.user_message):
        parts.append(
            "Code-analysis mode: prioritize concrete files such as entrypoints, routes, services, core modules, and tests. Do not present README-only or tree-only summaries as code analysis."
        )
    for i, cr in enumerate(capability_results):
        parts.append("")
        parts.append(f"--- Capability {i + 1}: {cr['capability_id']} ---")
        parts.append(f"Status: {cr['status']}")
        parts.append(f"Execution mode: {cr['execution_mode']}")
        result_text = str(cr.get("result_text") or "").strip()
        detail = str(cr.get("detail") or "").strip()
        if result_text:
            parts.append("Result:")
            parts.append(result_text)
        elif detail:
            parts.append(f"Detail: {detail}")
    return "\n".join(parts)


def _is_code_analysis_request(user_message: str) -> bool:
    normalized = str(user_message or "").lower()
    return any(
        token in normalized
        for token in (
            "code analysis",
            "kode analyse",
            "kodeanalyse",
            "codeanalyse",
            "gennemgang",
            "walkthrough",
            "review koden",
            "analyse af koden",
            "analyse main repo",
            "analyser main repo",
        )
    )


def _is_memory_commit_request(user_message: str) -> bool:
    normalized = str(user_message or "").lower()
    return any(
        token in normalized
        for token in (
            "remember this",
            "remember that",
            "husk dette",
            "husk det",
            "gem dette",
            "gem det",
            "this is important",
            "det er vigtigt",
            "do not forget",
            "glem ikke",
        )
    )