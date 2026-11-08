"""Tool-handlere for lokale planlagte opgaver og deres eksterne spejl.

Udskilt samlet fra ``simple_tools_native`` efter Boy Scout-reglen: schedule,
list, cancel og edit er én sammenhængende livscyklus og skal ikke drive fra
hinanden. ``simple_tools_native`` re-eksporterer navnene for bagudkompatibilitet.
"""
from __future__ import annotations

from collections.abc import Callable
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _operator_user_id(args: dict[str, Any]) -> str:
    """Brug simple_tools-facaden, så eksisterende test-patches stadig rammer."""
    import core.tools.simple_tools as simple_tools
    return simple_tools._operator_user_id(args)


def _mirror_text(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "error")
    if status == "mirrored":
        return " Google Tasks: mirrored."
    if status == "mirrored_untracked":
        return " Google Tasks: mirrored, but later edits and cancellation may not sync."
    if status == "cancelled":
        return " Google Tasks mirror cancelled."
    if status == "not_mirrored":
        return " No Google Tasks mirror existed."
    detail = str(result.get("error") or status)
    return f" Google Tasks mirror unavailable ({detail}); the local operation succeeded."


def _safe_mirror(
    call: Callable[..., dict[str, Any]],
    tool_args: dict[str, Any],
    *args: Any,
) -> dict[str, Any]:
    """Et spejl må aldrig ændre udfaldet af den allerede udførte lokale handling."""
    try:
        return call(_operator_user_id(tool_args), *args)
    except Exception as exc:  # noqa: BLE001 — fail-open er selve kontrakten her
        logger.warning("scheduled_tasks: Google-spejlet fejlede efter lokal succes", exc_info=True)
        return {"status": "error", "error": f"google_tasks_internal_error: {exc}"}


def _exec_schedule_task(args: dict[str, Any]) -> dict[str, Any]:
    """Planlæg en lokal opgave efter ``delay_minutes``."""
    focus = str(args.get("focus") or "").strip()
    if not focus:
        return {"status": "error", "error": "focus is required"}
    try:
        delay_minutes = int(args.get("delay_minutes") or 0)
    except (TypeError, ValueError):  # Ugyldigt tool-input returneres struktureret til modellen.
        return {"status": "error", "error": "delay_minutes must be an integer"}
    if delay_minutes < 1:
        return {"status": "error", "error": "delay_minutes must be at least 1"}
    try:
        from core.services.scheduled_tasks import push_scheduled_task
        task = push_scheduled_task(focus=focus, delay_minutes=delay_minutes)
        run_at = task.get("run_at", "")
        from core.services.google_tasks_mirror import create_task_mirror
        mirror = _safe_mirror(create_task_mirror, args, task)
        from core.services.peak_hours import tilfoej_booking_varsel
        from core.util.timezone import dk_label
        return tilfoej_booking_varsel({
            "status": "ok",
            "task_id": task.get("task_id"),
            "focus": focus,
            "delay_minutes": delay_minutes,
            "run_at": run_at,
            "google_tasks": mirror,
            "text": (
                f"Scheduled in {delay_minutes} min: {focus} (fires {dk_label(run_at)})"
                f"{_mirror_text(mirror)}"
            ),
        }, run_at)
    except Exception as exc:
        logger.warning("scheduled_tasks: kunne ikke planlaegge lokal opgave", exc_info=True)
        return {"status": "error", "error": str(exc)}


def _exec_list_scheduled_tasks(_args: dict[str, Any]) -> dict[str, Any]:
    """List lokale planlagte opgaver (ventende og nyligt fyrede)."""
    try:
        from core.services.scheduled_tasks import get_scheduled_tasks_state
        state = get_scheduled_tasks_state()
    except Exception as exc:
        logger.warning("scheduled_tasks: kunne ikke liste lokale opgaver", exc_info=True)
        return {"status": "error", "error": str(exc)}

    pending = state.get("pending") or []
    fired = state.get("recently_fired") or []
    from core.util.timezone import dk_label
    lines = []
    if pending:
        lines.append(f"Pending ({len(pending)}):")
        for task in pending:
            lines.append(
                f"  [{task.get('task_id','')}] {task.get('focus','')} — "
                f"fires {dk_label(str(task.get('run_at','')))}"
            )
    else:
        lines.append("No pending scheduled tasks.")
    if fired:
        lines.append(f"Recently fired ({len(fired)}):")
        for task in fired:
            lines.append(
                f"  [{task.get('task_id','')}] {task.get('focus','')} — "
                f"fired {dk_label(str(task.get('fired_at','')))}"
            )
    return {
        "status": "ok",
        "pending_count": len(pending),
        "pending": pending,
        "recently_fired": fired,
        "text": "\n".join(lines),
    }


def _exec_cancel_task(args: dict[str, Any]) -> dict[str, Any]:
    """Annullér en ventende lokal opgave."""
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    try:
        from core.services.scheduled_tasks import cancel_scheduled_task
        cancelled = cancel_scheduled_task(task_id)
    except Exception as exc:
        logger.warning("scheduled_tasks: kunne ikke annullere lokal opgave", exc_info=True)
        return {"status": "error", "error": str(exc)}
    if cancelled:
        from core.services.google_tasks_mirror import cancel_task_mirror
        mirror = _safe_mirror(cancel_task_mirror, args, task_id)
        return {
            "status": "ok",
            "task_id": task_id,
            "google_tasks": mirror,
            "text": f"Task {task_id} cancelled.{_mirror_text(mirror)}",
        }
    return {"status": "error", "error": f"Task {task_id!r} not found or not pending"}


def _exec_edit_task(args: dict[str, Any]) -> dict[str, Any]:
    """Redigér fokus og/eller tidspunkt på en ventende lokal opgave."""
    task_id = str(args.get("task_id") or "").strip()
    if not task_id:
        return {"status": "error", "error": "task_id is required"}
    focus = args.get("focus")
    delay_minutes = args.get("delay_minutes")
    if focus is None and delay_minutes is None:
        return {"status": "error", "error": "Provide at least one of: focus, delay_minutes"}
    try:
        from core.services.scheduled_tasks import edit_scheduled_task
        result = edit_scheduled_task(
            task_id,
            focus=str(focus).strip() if focus is not None else None,
            delay_minutes=int(delay_minutes) if delay_minutes is not None else None,
        )
        if result.get("status") != "ok" or not isinstance(result.get("task"), dict):
            return result
        from core.services.google_tasks_mirror import update_task_mirror
        mirror = _safe_mirror(update_task_mirror, args, result["task"])
        result["google_tasks"] = mirror
        result["text"] = f"{result.get('text', '')}{_mirror_text(mirror)}"
        return result
    except Exception as exc:
        logger.warning("scheduled_tasks: kunne ikke redigere lokal opgave", exc_info=True)
        return {"status": "error", "error": str(exc)}


__all__ = [
    "_exec_schedule_task",
    "_exec_list_scheduled_tasks",
    "_exec_cancel_task",
    "_exec_edit_task",
]
