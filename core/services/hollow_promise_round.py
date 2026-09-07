"""Hollow-promise follow-through (redesign 2026-09-04).

Before, the guard appended a text nudge ("kald værktøjet NU …") and hoped the
model would act. Measured: on DeepSeek every nudge round died with HTTP 400
before the model saw it (empty tool_calls array — fixed 179f0018a), and even
when it reaches the model a plea is not deterministic.

Now the next round is FORCED: ``tool_choice="required"`` on OpenAI-compatible
providers (DeepSeek, OpenCode, Groq, …), so the model must call a tool or the
provider errors. The outcome is persisted as events so the effect is
measurable:

* ``runtime.hollow_promise_detected`` — when the guard fires
* ``runtime.hollow_promise_outcome`` — after the forced round, with
  ``resolved`` (a tool was called) and ``forced`` (tool_choice was required)

Pure helpers; visible_runs only calls in.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Providers whose follow-up adapter honours ``tool_choice`` (OpenAICompatFollowupAdapter).
_TOOL_CHOICE_PROVIDERS = frozenset({
    "deepseek", "opencode", "groq", "openrouter", "mistral", "nvidia-nim", "sambanova",
    "openai", "github-copilot", "aihubmix", "kilo", "kilocode",
})


def supports_forced_tool_choice(provider: str) -> bool:
    return str(provider or "").strip().lower() in _TOOL_CHOICE_PROVIDERS


def next_round_tool_choice(*, force_summary: bool, hollow_force: bool, provider: str) -> str | None:
    """Sampling param for the next follow-up round.

    force_summary wins (last round / synth pause must produce prose). Otherwise a
    hollow promise forces a tool call when the provider supports it.
    """
    if force_summary:
        return "none"
    if hollow_force and supports_forced_tool_choice(provider):
        return "required"
    return None


def _publish(kind: str, payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(kind, payload)
    except Exception as exc:
        logger.debug("hollow_promise_round: publish %s failed: %s", kind, exc)


def note_detected(*, run_id: str, provider: str, model: str, round_index: int, session_id: str, forced: bool) -> None:
    _publish("runtime.hollow_promise_detected", {
        "run_id": str(run_id or ""), "provider": str(provider or ""), "model": str(model or ""),
        "round": int(round_index or 0), "session_id": str(session_id or ""), "forced": bool(forced),
    })


def note_outcome(*, run_id: str, provider: str, model: str, round_index: int, session_id: str,
                 forced: bool, tool_calls: int) -> bool:
    """Persist the outcome of the round after a hollow promise. Returns resolved."""
    resolved = int(tool_calls or 0) > 0
    _publish("runtime.hollow_promise_outcome", {
        "run_id": str(run_id or ""), "provider": str(provider or ""), "model": str(model or ""),
        "round": int(round_index or 0), "session_id": str(session_id or ""),
        "forced": bool(forced), "tool_calls": int(tool_calls or 0), "resolved": resolved,
    })
    try:
        from core.services import followup_observer as _fo
        _fo.note_hollow_promise(run_id, provider=provider, model=model, round_index=round_index,
                                session_id=session_id, resolved=resolved)
    except Exception:
        pass
    return resolved


def hollow_promise_note(model: str = "") -> str:
    """Sætningen der siges højt når BEGGE tvungne forsøg gav nul værktøjskald.

    Den skal indrømme at der ikke blev udført noget — ellers står Bjørn med et
    løfte og aner ikke at det er tomt; 7/9 skrev han «Kør» fire gange i træk.

    Den peger IKKE på modellen. Første udgave gjorde, og det var forkert:
    målt på 36 tvungne runder løser vision-modellen 11 af 15 og flash uden syn
    13 af 16. Fejlen er tilfældig pr. forsøg, ikke en egenskab ved modellen, og
    en forkert beskyldning ville sende Bjørn ud at skifte model uden grund.
    """
    return (
        "\n\n_(Jeg sagde hvad jeg ville gøre og kaldte så ingen værktøjer — "
        "heller ikke da jeg blev tvunget til det, to gange. Der blev altså "
        "ikke udført noget. Sig til, så tager jeg den forfra.)_"
    )
