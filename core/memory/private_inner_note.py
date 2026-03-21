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
    return {
        "note_id": f"private-inner-note:{run_id}",
        "source": "visible-selected-work-note",
        "run_id": run_id,
        "work_id": work_id,
        "status": status,
        "private_summary": _private_summary(
            status=status,
            user_message_preview=user_message_preview,
            work_preview=work_preview,
            capability_id=capability_id,
        ),
        "created_at": created_at,
    }


def _private_summary(
    *,
    status: str,
    user_message_preview: str | None,
    work_preview: str | None,
    capability_id: str | None,
) -> str:
    parts = [f"status={status or 'unknown'}"]
    if capability_id:
        parts.append(f"capability={capability_id}")
    if user_message_preview:
        parts.append(f"user={user_message_preview}")
    elif work_preview:
        parts.append(f"work={work_preview}")
    return " | ".join(parts)[:160].rstrip()
