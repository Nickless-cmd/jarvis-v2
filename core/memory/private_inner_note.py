from __future__ import annotations


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
    focus = capability_id or "visible-work"
    uncertainty = _uncertainty(status=status, work_preview=work_preview)
    identity_alignment = "subordinate-to-visible"
    work_signal = _work_signal(status=status, capability_id=capability_id)
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
    parts = [
        f"kind={note_kind}",
        f"status={status or 'unknown'}",
        f"focus={focus}",
        f"uncertainty={uncertainty}",
        f"signal={work_signal}",
    ]
    if capability_id:
        parts.append(f"capability={capability_id}")
    if user_message_preview:
        parts.append(f"user={user_message_preview}")
    elif work_preview:
        parts.append(f"work={work_preview}")
    return " | ".join(parts)[:160].rstrip()


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
