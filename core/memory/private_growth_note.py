from __future__ import annotations


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
    lesson = _lesson(
        learning_kind=learning_kind,
        focus=str(private_inner_note.get("focus") or ""),
        work_signal=str(private_inner_note.get("work_signal") or ""),
    )
    mistake_signal = _mistake_signal(status=status)
    helpful_signal = _helpful_signal(status=status, work_preview=work_preview)
    identity_signal = str(
        private_inner_note.get("identity_alignment") or "subordinate-to-visible"
    )[:48]
    confidence = _confidence(str(private_inner_note.get("uncertainty") or "medium"))
    return {
        "record_id": f"private-growth-note:{run_id}",
        "source": "private-inner-note",
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
    parts = [learning_kind]
    if focus:
        parts.append(f"focus={focus}")
    if work_signal:
        parts.append(f"signal={work_signal}")
    return " | ".join(parts)[:160].rstrip()


def _mistake_signal(*, status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"failed", "cancelled"}:
        return normalized[:48]
    return ""


def _helpful_signal(*, status: str, work_preview: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized == "completed":
        return (work_preview or "completed")[:96].rstrip()
    return normalized[:48]


def _confidence(uncertainty: str) -> str:
    normalized = (uncertainty or "").strip().lower()
    if normalized == "low":
        return "medium"
    if normalized == "medium":
        return "low"
    return "low"
