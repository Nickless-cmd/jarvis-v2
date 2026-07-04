from __future__ import annotations

_LEVEL_SCALE = {"low": 0.0, "medium": 0.5, "high": 1.0}


def _observe_private_growth_note(
    *, learning_kind: str, confidence: str, has_mistake: bool
) -> None:
    """Egress-fri puls til Centralen (§24.4) — cluster=cognition. KUN learning_kind/
    confidence-labels + mistake-flag (skalarer), ALDRIG lesson/helpful_signal-teksten.
    record_private = lokal trace + tidsserie, aldrig _emit. Self-safe."""
    try:
        from core.services.central_private_observe import record_private
        record_private(
            "cognition", "private_growth_note",
            value=_LEVEL_SCALE.get(str(confidence or "low"), 0.0),
            meta={
                "learning_kind": str(learning_kind or "observe"),
                "confidence": str(confidence or "low"),
                "has_mistake": bool(has_mistake),
            },
        )
    except Exception:
        pass


def build_private_growth_note_payload(
    *,
    run_id: str,
    work_id: str,
    status: str,
    work_preview: str | None,
    private_inner_note: dict[str, str],
    created_at: str,
) -> dict[str, str]:
    learning_kind = _learning_kind(status=status)
    focus = str(private_inner_note.get("focus") or "")
    work_signal = str(private_inner_note.get("work_signal") or "")
    lesson = _lesson(
        learning_kind=learning_kind,
        focus=focus,
        work_signal=work_signal,
    )
    mistake_signal = _mistake_signal(status=status)
    helpful_signal = _helpful_signal(
        status=status,
        focus=focus,
        work_signal=work_signal,
    )
    identity_signal = str(
        private_inner_note.get("identity_alignment") or "subordinate-to-visible"
    )[:48]
    confidence = _confidence(status=status, work_preview=work_preview)
    _observe_private_growth_note(
        learning_kind=learning_kind,
        confidence=confidence,
        has_mistake=bool(mistake_signal),
    )
    return {
        "record_id": f"private-growth-note:{run_id}",
        "source": "private-inner-note:private-runtime-grounded",
        "run_id": run_id,
        "work_id": work_id,
        "learning_kind": learning_kind,
        "lesson": lesson,
        "mistake_signal": mistake_signal,
        "helpful_signal": helpful_signal,
        "identity_signal": identity_signal,
        "confidence": confidence,
        "created_at": created_at,
    }


def _learning_kind(*, status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized == "completed":
        return "reinforce"
    if normalized in {"failed", "cancelled"}:
        return "adjust"
    return "observe"


def _lesson(*, learning_kind: str, focus: str, work_signal: str) -> str:
    focus_text = _topic_text(focus)
    signal_text = _signal_text(work_signal)
    if learning_kind == "reinforce":
        lead = f"I should keep carrying what helped around {focus_text}."
    elif learning_kind == "adjust":
        lead = f"I should stay careful around {focus_text}."
    else:
        lead = f"I should keep quietly watching {focus_text}."
    if signal_text:
        return f"{lead} {signal_text}"[:160].rstrip()
    return lead[:160].rstrip()


def _mistake_signal(*, status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"failed", "cancelled"}:
        return normalized[:48]
    return ""


def _helpful_signal(*, status: str, focus: str, work_signal: str) -> str:
    normalized = (status or "").strip().lower()
    focus_text = _topic_text(focus)
    signal_text = _signal_hint(work_signal)
    if normalized == "completed":
        base = f"Det virker værd at holde fast i det, der hjalp omkring {focus_text}."
        if signal_text:
            base = f"{base} Det peger stadig {signal_text}."
        template_output = base[:140].rstrip()
    elif normalized in {"failed", "cancelled"}:
        template_output = f"Det kræver en mere varsom hånd omkring {focus_text}."[:140].rstrip()
    elif normalized == "observe":
        template_output = f"Det er værd at blive ved med at følge tråden omkring {focus_text}."[:140].rstrip()
    else:
        template_output = normalized[:48]

    # 2026-05-25 (Claude): rollout from shadow to production.
    # After 109 shadow samples we have evidence that LLM output is
    # consistently better (60% useful + coherent Danish) than the
    # template (80% grammatical gibberish because focus inputs were
    # truncated user-message fragments). Call LLM synchronously with
    # 5s timeout; fall back to template on any failure. Continue
    # logging both outputs in inner_voice_shadow for ongoing tuning.
    try:
        from core.services.inner_voice_shadow import generate_helpful_signal_via_llm
        return generate_helpful_signal_via_llm(
            status=status, focus=focus, work_signal=work_signal,
            fallback=template_output,
        )
    except Exception:
        # If the LLM path imports fail, return the template — heartbeat
        # must never break because of this.
        return template_output


def _confidence(*, status: str, work_preview: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized == "completed":
        return "high" if (work_preview and len(work_preview.strip()) > 50) else "medium"
    if normalized in {"failed", "cancelled"}:
        return "low"
    return "low"


def _topic_text(value: str) -> str:
    normalized = (value or "").strip().replace("-", " ")
    return normalized or "this thread"


def _signal_text(value: str) -> str:
    hint = _signal_hint(value)
    if not hint:
        return ""
    return f"It still feels {hint.strip()}.".replace("  ", " ")


def _signal_hint(value: str) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""
    if ":" in normalized:
        status, capability = normalized.split(":", 1)
        capability_text = capability.replace("-", " ").strip() or "this area"
        if status == "completed":
            return f"mod {capability_text}"
        if status in {"failed", "cancelled"}:
            return f"uroligt omkring {capability_text}"
        return f"hen imod {capability_text}"
    if normalized == "completed":
        return "mere stabilt nu"
    if normalized in {"failed", "cancelled"}:
        return "uafklaret"
    return "til stede, men afgrænset"
