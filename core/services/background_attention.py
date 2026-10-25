"""One durable exit path for findings from unattended runtime work.

Background producers may log as much telemetry as they need.  A finding that
needs a decision, however, must also acquire an owner-facing address.  This
module is that small boundary: it emits one structured event, updates one
deduplicated inbox item, and optionally creates one explicitly bounded side
task.  It never executes the task itself.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Final


STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "finding", "blocked", "failed", "critical"}
)
SEVERITIES: Final[frozenset[str]] = frozenset(
    {"info", "low", "normal", "high", "critical"}
)
AUTONOMY_MODES: Final[frozenset[str]] = frozenset(
    {"none", "inspect", "local_write"}
)
_TOKEN = re.compile(r"[^a-z0-9_.-]+")


def _token(value: object, fallback: str) -> str:
    text = _TOKEN.sub("-", str(value or "").strip().lower()).strip("-")
    return (text or fallback)[:120]


def _owner_user_id() -> str:
    try:
        from core.identity.owner_resolver import owner_user_id

        return str(owner_user_id() or "").strip()
    except Exception:  # missing owner prevents unsafe cross-user delivery
        return ""


def _publish(payload: dict[str, Any]) -> None:
    try:
        from core.eventbus.bus import event_bus

        event_bus.publish("background.attention", payload)
    except Exception:  # telemetry is best-effort beside durable persistence
        # Telemetry must not become a new failure mode for the producer.
        pass


def _write_inbox(**kwargs: Any) -> dict[str, Any]:
    from core.services.inbox_state import registrer_kilde

    return registrer_kilde(**kwargs)


def _existing_inbox(*, owner: str, inbox_id: str) -> dict[str, Any] | None:
    try:
        from core.runtime import db_inbox

        return db_inbox.hent(bruger_id=owner, kilde_id=inbox_id)
    except Exception:  # lookup failure falls through to durable upsert
        return None


def _write_side_task(**kwargs: Any) -> dict[str, Any]:
    from core.services.side_tasks import flag

    return flag(**kwargs)


def report_background_outcome(
    *,
    source_kind: str,
    source_id: str,
    status: str,
    summary: str,
    severity: str = "normal",
    run_id: str = "",
    session_id: str = "",
    evidence_ref: str = "",
    suggested_next_step: str = "",
    requires_attention: bool = False,
    create_side_task: bool = False,
    autonomy_mode: str = "none",
    safe_to_continue: bool = True,
    max_minutes: int = 20,
    max_tool_calls: int = 12,
) -> dict[str, Any]:
    """Project one background outcome without granting it extra authority.

    ``autonomy_mode`` applies only to an optional side task.  ``inspect`` may
    gather evidence; ``local_write`` may use the existing local-write tools.
    Unknown values fail closed instead of silently becoming executable.
    """
    source_kind_n = _token(source_kind, "background")
    source_id_n = _token(source_id or run_id, "unknown")
    status_n = str(status or "").strip().lower()
    severity_n = str(severity or "normal").strip().lower()
    autonomy_n = str(autonomy_mode or "none").strip().lower()
    summary_n = " ".join(str(summary or "").split())[:1000]
    next_step_n = " ".join(str(suggested_next_step or "").split())[:1200]

    if status_n not in STATUSES:
        return {"status": "error", "error": f"unknown background status {status_n!r}"}
    if severity_n not in SEVERITIES:
        return {"status": "error", "error": f"unknown severity {severity_n!r}"}
    if autonomy_n not in AUTONOMY_MODES:
        return {"status": "error", "error": f"unknown autonomy_mode {autonomy_n!r}"}
    if not summary_n:
        return {"status": "error", "error": "summary is required"}
    if create_side_task and not next_step_n:
        return {"status": "error", "error": "a side task requires suggested_next_step"}

    attention = bool(requires_attention or status_n in {"blocked", "failed", "critical"})
    dedupe_key = f"background:{source_kind_n}:{source_id_n}"
    payload = {
        "source_kind": source_kind_n,
        "source_id": source_id_n,
        "run_id": str(run_id or "")[:160],
        "session_id": str(session_id or "")[:160],
        "status": status_n,
        "severity": severity_n,
        "summary": summary_n,
        "requires_attention": attention,
        "safe_to_continue": bool(safe_to_continue),
        "dedupe_key": dedupe_key,
        "evidence_ref": str(evidence_ref or "")[:500],
    }
    _publish(payload)

    result: dict[str, Any] = {
        "status": "recorded", "inbox": "skipped", "side_task": "skipped",
        "dedupe_key": dedupe_key,
    }
    if not attention:
        return result

    owner = _owner_user_id()
    if not owner:
        return {**result, "status": "partial", "inbox": "no-owner"}

    inbox_id = f"background-{source_kind_n}-{source_id_n}"[:220]
    existing = _existing_inbox(owner=owner, inbox_id=inbox_id)
    # An open incident is updated.  A resolved incident is history and must
    # not swallow a genuine recurrence, so a new generation gets its own id.
    if existing and str(existing.get("status") or "") in {
        "done", "afsluttet_af_kilde",
    }:
        generation = _token(run_id, "") or datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        inbox_id = f"{inbox_id}-{generation}"[:240]
        dedupe_key = f"{dedupe_key}:{generation}"
        result["dedupe_key"] = dedupe_key
    inbox_result = _write_inbox(
        bruger_id=owner,
        kildetype="background_attention",
        kilde_id=inbox_id,
        oprettende_run_id=str(run_id or ""),
        paastaaet_ejer="huset",
        beskrivelse=(
            f"[{severity_n}/{status_n}] {summary_n}"
            + (f" Næste skridt: {next_step_n}" if next_step_n else "")
            + (f" Evidens: {str(evidence_ref)[:300]}" if evidence_ref else "")
        )[:1600],
        session_id=str(session_id or ""),
    )
    result["inbox"] = str(inbox_result.get("status") or "error")

    if create_side_task:
        task_result = _write_side_task(
            title=f"Følg op: {summary_n[:140]}",
            prompt=(
                f"{next_step_n}\n\nKilde: {source_kind_n}/{source_id_n}. "
                f"Status: {status_n}. Alvor: {severity_n}. Fund: {summary_n}"
                + (f" Evidens: {evidence_ref}" if evidence_ref else "")
            )[:12000],
            tldr=summary_n[:600],
            session_id=str(session_id or "") or None,
            finding_key=dedupe_key,
            source_run_id=str(run_id or ""),
            evidence=summary_n,
            autonomy_mode=autonomy_n,
            max_minutes=max_minutes,
            max_tool_calls=max_tool_calls,
        )
        result["side_task"] = str(task_result.get("status") or "error")
        result["side_task_id"] = str(task_result.get("side_task_id") or "")
        result["deduplicated"] = bool(task_result.get("deduplicated"))
    return result


__all__ = ["report_background_outcome"]
