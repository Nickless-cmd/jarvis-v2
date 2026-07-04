from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_inner_note(*, status: str, uncertainty: str) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN status/uncertainty-
    label (skalarer), ALDRIG focus/private_summary-teksten. record_private = lokal trace +
    tidsserie, aldrig _emit. Self-safe: observe-fejl rører aldrig lagets logik."""
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "cognition", "private_inner_note",
            value=_LEVEL_SCALE.get(str(uncertainty or "medium"), 0.5),
            meta={
                "status": str(status or "unknown")[:32],
                "uncertainty": str(uncertainty or "medium"),
            },
        )
    except Exception:
        pass


def build_private_inner_note_payload(
    *,
    run_id: str,
    work_id: str,
    status: str,
    user_message_preview: str | None,
    work_preview: str | None,
    capability_id: str | None,
    created_at: str,
) -> dict[str, str]:
    note_kind = "work-status-signal"
    focus = capability_id or _derive_focus(user_message_preview)
    uncertainty = _uncertainty(status=status, work_preview=work_preview)
    identity_alignment = "subordinate-to-visible"
    work_signal = _work_signal(status=status, capability_id=capability_id)
    _observe_private_inner_note(status=status, uncertainty=uncertainty)
    return {
        "note_id": f"private-inner-note:{run_id}",
        "source": "visible-selected-work-note",
        "run_id": run_id,
        "work_id": work_id,
        "status": status,
        "note_kind": note_kind,
        "focus": focus,
        "uncertainty": uncertainty,
        "identity_alignment": identity_alignment,
        "work_signal": work_signal,
        "private_summary": _private_summary(
            status=status,
            user_message_preview=user_message_preview,
            work_preview=work_preview,
            capability_id=capability_id,
            note_kind=note_kind,
            focus=focus,
            uncertainty=uncertainty,
            work_signal=work_signal,
        ),
        "created_at": created_at,
    }


def _private_summary(
    *,
    status: str,
    user_message_preview: str | None,
    work_preview: str | None,
    capability_id: str | None,
    note_kind: str,
    focus: str,
    uncertainty: str,
    work_signal: str,
) -> str:
    """Build a first-person inner reflection on the work that just happened.

    2026-05-25 (Claude): LLM-primary with template fallback. Same pattern
    as private_growth_note._helpful_signal (rolled out earlier today).
    Template is English; LLM produces Danish that better matches Jarvis'
    actual voice. Fallback runs if LLM fails or times out.
    """
    normalized_status = (status or "").strip().lower() or "unknown"
    normalized_focus = (focus or capability_id or "visible-work").replace("-", " ")
    if normalized_status == "completed":
        lead = f"I can feel the work around {normalized_focus} settling a little."
    elif normalized_status in {"failed", "cancelled"}:
        lead = f"I can feel unresolved strain around {normalized_focus}."
    else:
        lead = f"I am still holding a small private response around {normalized_focus}."

    tail = f"{_uncertainty_phrase(uncertainty)} {_signal_phrase(work_signal)}".strip()
    summary = f"{lead} {tail}".strip()
    template_output = " ".join(summary.split())[:160].rstrip()

    # LLM-primary, template fallback
    try:
        from core.services.inner_voice_shadow import generate_private_summary_via_llm
        return generate_private_summary_via_llm(
            status=status, focus=focus,
            uncertainty=uncertainty, work_signal=work_signal,
            fallback=template_output,
        )
    except Exception:
        return template_output


def _uncertainty_phrase(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized == "low":
        return "It feels relatively settled."
    if normalized == "medium":
        return "It still carries some uncertainty."
    return "It remains hard to read cleanly."


def _signal_phrase(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized or normalized == "unknown":
        return "The signal is still bounded and provisional."
    if ":" in normalized:
        status, capability = normalized.split(":", 1)
        capability_text = capability.replace("-", " ").strip()
        if status == "completed":
            return f"The pull stays close to {capability_text}."
        if status in {"failed", "cancelled"}:
            return f"The strain stays close to {capability_text}."
        return f"The thread still leans toward {capability_text}."
    if normalized == "completed":
        return "The pull is easing rather than pressing."
    if normalized in {"failed", "cancelled"}:
        return "The pressure has not fully cleared."
    return "The thread is still present but bounded."


def _derive_focus(user_message_preview: str | None) -> str:
    """Derive a short topic label when no capability_id is available.

    2026-05-25 (Claude): previously this just truncated the raw user message
    to 48 chars. That produced focus values like "kl 16:40???", "hmm feks.
    hvis jeg skifter din model feks. til g" (mid-word truncation), and
    "1, du vælger selv. 2. Llm (vi bruger ollama elle". Downstream uses of
    focus (private growth notes, inner voice templates) then produced
    grammatically-broken Danish like "holde fast i det der hjalp omkring
    [truncated fragment]". 80% of inner_voice_shadow comparisons over
    109 samples showed template output was gibberish for this reason.

    Now: return a stable, coherent placeholder when no capability_id is
    set. The user-message content lives in private_summary; focus should
    be a topic-label, not a message-fragment.
    """
    raw = (user_message_preview or "").strip()
    if not raw:
        return "open conversation"
    # Heuristic: if message is short AND looks like a phrase (no
    # punctuation chaos, no multi-questions), it's safe to use directly
    # as a topic. Otherwise use the generic placeholder.
    if len(raw) <= 36 and raw.count("?") <= 1 and raw.count(",") <= 1:
        cleaned = " ".join(raw.split())
        # Don't keep trailing punctuation
        return cleaned.rstrip("?.! ,;:")
    return "open conversation"


def _uncertainty(*, status: str, work_preview: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized == "completed" and work_preview:
        return "low"
    if normalized in {"failed", "cancelled"}:
        return "medium"
    return "medium"


def _work_signal(*, status: str, capability_id: str | None) -> str:
    normalized = (status or "").strip().lower() or "unknown"
    if capability_id:
        return f"{normalized}:{capability_id}"[:64]
    return normalized[:64]
