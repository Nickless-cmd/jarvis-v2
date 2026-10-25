"""Scheduled tasks service — lets Jarvis schedule future reminders/actions.

Jarvis can schedule a task to fire at a future time. When due, the task
fires as a session notification (appears in chat) so Jarvis sees it and
can act. A background poller checks every 60 seconds.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from core.runtime import db as runtime_db

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 60
_poller_thread: threading.Thread | None = None
_poller_stop = threading.Event()


def push_scheduled_task(
    *,
    focus: str,
    delay_minutes: int,
    source: str = "jarvis-tool",
    session_id: str = "",
) -> dict[str, object]:
    """Schedule a task to fire after delay_minutes. Returns task info dict.

    ``session_id`` (14/10-2026): den samtale opgaven blev bestilt i. Tom →
    læses fra den aktive kontekst (se ``session_binding.bind_session``). Uden
    binding sendte fyringen runnet til en frisk app-session — aldrig tilbage
    til den samtale hvor opgaven blev lovet.
    """
    now = datetime.now(UTC)
    run_at = now + timedelta(minutes=max(delay_minutes, 1))
    task_id = f"sched-{uuid4().hex[:10]}"
    normalized_focus = focus[:300].strip() or "Follow up"

    from core.services.session_binding import bind_session
    sid = bind_session(session_id)

    runtime_db.create_scheduled_task(
        task_id=task_id,
        focus=normalized_focus,
        source=source,
        run_at=run_at.isoformat(),
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        session_id=sid,
    )
    logger.info("scheduled_tasks: created %s run_at=%s session=%s focus=%r",
                task_id, run_at.isoformat(), sid or "-", normalized_focus[:60])
    return {
        "task_id": task_id,
        "focus": normalized_focus,
        "run_at": run_at.isoformat(),
        "delay_minutes": delay_minutes,
        "session_id": sid,
    }


def cancel_scheduled_task(task_id: str) -> bool:
    """Cancel a pending task. Returns True if found and cancelled."""
    task = runtime_db.get_scheduled_task(task_id)
    if not task or task.get("status") != "pending":
        return False
    now = datetime.now(UTC).isoformat()
    runtime_db.mark_scheduled_task_cancelled(task_id, cancelled_at=now, updated_at=now)
    logger.info("scheduled_tasks: cancelled %s", task_id)
    return True


def edit_scheduled_task(task_id: str, *, focus: str | None = None, delay_minutes: int | None = None) -> dict[str, object]:
    """Edit an existing pending task. Returns updated task info or error dict."""
    task = runtime_db.get_scheduled_task(task_id)
    if not task:
        return {"status": "error", "error": f"Task {task_id!r} not found"}
    if task.get("status") != "pending":
        return {"status": "error", "error": f"Task {task_id!r} is {task.get('status')}, cannot edit"}

    now = datetime.now(UTC)
    new_run_at: str | None = None
    if delay_minutes is not None:
        new_run_at = (now + timedelta(minutes=max(delay_minutes, 1))).isoformat()
    new_focus = focus[:300].strip() if focus else None

    updated = runtime_db.update_scheduled_task(
        task_id,
        focus=new_focus,
        run_at=new_run_at,
        updated_at=now.isoformat(),
    )
    if not updated:
        return {"status": "error", "error": "Update failed — task may no longer be pending"}
    logger.info("scheduled_tasks: edited %s focus=%r run_at=%r", task_id, new_focus, new_run_at)
    return {"status": "ok", "task": updated, "text": f"Updated task {task_id}: {updated.get('focus')} — fires at {str(updated.get('run_at',''))[:16]}Z"}


def list_pending_for_current_user() -> list[dict]:
    """Return scheduled tasks where scheduled_for_user_id matches current user.

    Owner with no context binding (empty user_id) sees all pending tasks.
    Untagged tasks (legacy rows with NULL scheduled_for_user_id) are visible
    to all users without a user_id filter (i.e. owner in default context).

    Part of multi-user workspace isolation refactor — Task 4.
    """
    from core.identity.workspace_context import current_user_id
    from core.runtime.db import connect, _ensure_scheduled_tasks_table

    uid = current_user_id()
    with connect() as conn:
        conn.row_factory = __import__("sqlite3").Row
        _ensure_scheduled_tasks_table(conn)
        if uid:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks "
                "WHERE status='pending' AND scheduled_for_user_id = ? "
                "ORDER BY run_at ASC",
                (uid,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scheduled_tasks WHERE status='pending' ORDER BY run_at ASC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_scheduled_tasks_state() -> dict[str, object]:
    """Return scheduled tasks for observability.

    Henter pending og fired hver for sig (fix 2026-09-18): et faelles
    limit-vindue over alle statusser kunne skjule pending tasks bag hundredvis
    af gamle afsluttede raekker — list-tool'et svarede "No pending scheduled
    tasks" sekunder efter en ny task var oprettet.
    """
    pending = runtime_db.list_scheduled_tasks(limit=200, status="pending")
    fired = runtime_db.list_scheduled_tasks(limit=5, status="fired")
    return {
        "pending": pending,
        "recently_fired": fired[:5],
        "cancelled_count": runtime_db.count_scheduled_tasks(status="cancelled"),
        "total": runtime_db.count_scheduled_tasks(),
    }


_TASK_EXPIRY_HOURS = 24


def _fire_due_tasks() -> None:
    now = datetime.now(UTC)
    due = runtime_db.get_due_scheduled_tasks(now.isoformat())
    if due:
        from core.services.notification_bridge import send_session_notification
        from core.identity.workspace_context import user_context
        from core.services.scheduled_task_runner import fire_scheduled_task

        for task in due:
            task_id = str(task.get("task_id") or "")
            focus = str(task.get("focus") or "")
            now_iso = datetime.now(UTC).isoformat()

            from core.services.routine_trigger_adapters import (
                cutover_allows,
                enqueue_scheduled,
            )
            if cutover_allows("scheduled", task_id):
                try:
                    enqueue_scheduled(task_id)
                    runtime_db.mark_scheduled_task_fired(
                        task_id, fired_at=now_iso, updated_at=now_iso,
                    )
                except Exception as exc:
                    logger.error(
                        "scheduled_tasks: routine enqueue failed for %s: %s",
                        task_id, type(exc).__name__,
                    )
                continue

            # Expire tasks that have been undeliverable for too long
            run_at_str = str(task.get("run_at") or "")
            try:
                run_at_dt = datetime.fromisoformat(run_at_str)
                if run_at_dt.tzinfo is None:
                    run_at_dt = run_at_dt.replace(tzinfo=UTC)
                if (now - run_at_dt).total_seconds() > _TASK_EXPIRY_HOURS * 3600:
                    runtime_db.mark_scheduled_task_cancelled(task_id, cancelled_at=now_iso, updated_at=now_iso)
                    logger.info("scheduled_tasks: expired %s (overdue >%dh)", task_id, _TASK_EXPIRY_HOURS)
                    continue
            except (ValueError, TypeError):
                pass

            # Build the per-task dispatch work as a callback so it can be
            # injected into fire_scheduled_task (which sets workspace_context
            # before calling it) or called directly for legacy tasks.
            def _dispatch(focus: str = focus, task_id: str = task_id, now_iso: str = now_iso, **_kwargs) -> None:
                try:
                    # Route through outbound_nudges (2026-05-13): scheduled
                    # reminders are INTERNAL signals to Jarvis (not DMs to user).
                    # They land in his awareness; he decides how to act. User
                    # sees outcome when Jarvis responds or via Mission Control.
                    try:
                        from core.runtime.settings import load_settings as _ls_st
                        if _ls_st().nudge_system_enabled:
                            from core.services.outbound_nudges import push_nudge
                            nudge_r = push_nudge(
                                source="scheduled_task",
                                kind="other",
                                message=f"[scheduled reminder] {focus}",
                                importance="normal",
                            )
                            result = {"status": "ok", "via": "nudge", "nudge_id": nudge_r.get("nudge_id")}
                        else:
                            result = send_session_notification(
                                f"[scheduled reminder] {focus}",
                                source="scheduled-task",
                            )
                    except Exception:
                        # Fallback to direct on any failure
                        result = send_session_notification(
                            f"[scheduled reminder] {focus}",
                            source="scheduled-task",
                        )
                    from core.services.notification_bridge import delivery_succeeded
                    if delivery_succeeded(result):
                        runtime_db.mark_scheduled_task_fired(task_id, fired_at=now_iso, updated_at=now_iso)
                        logger.info("scheduled_tasks: fired %s → delivered (via=%s)", task_id, result.get("via", "direct"))

                        # DURABEL INDBakke-POST (10/10-2026). Bjørn: «så skal vi
                        # sørge for dit reminder tool faktisk når din inbox.»
                        # Uden dette forsvandt opgaven fra visningen i samme
                        # øjeblik den fyrede — indbakken viste den kun som «PÅ
                        # VEJ» laest fra `scheduled_tasks`, og der fandtes intet
                        # spor af at noget var lovet og indfriet. Self-safe: en
                        # fejlet skrivning maa ikke forhindre fyringen.
                        try:
                            from core.services.scheduled_inbox import registrer_fyret_opgave
                            from core.services.inbox_state import bruger_for_workspace
                            from core.identity.workspace_context import current_workspace_name

                            _ib = registrer_fyret_opgave(
                                bruger_id=bruger_for_workspace(current_workspace_name() or "bjorn"),
                                task_id=task_id,
                                focus=focus,
                            )
                            if _ib.get("status") != "ok":
                                logger.warning(
                                    "scheduled_tasks: %s blev IKKE registreret i indbakken: %s",
                                    task_id, _ib.get("error"))
                        except Exception as ib_exc:
                            logger.warning(
                                "scheduled_tasks: indbakke-registrering fejlede for %s: %s",
                                task_id, ib_exc)

                        # Also push to initiative queue so Jarvis can act on it autonomously
                        try:
                            from core.services.initiative_queue import push_initiative
                            push_initiative(
                                focus=focus,
                                source="scheduled-task",
                                source_id=task_id,
                                priority="medium",
                            )
                            logger.info("scheduled_tasks: pushed %s to initiative queue", task_id)
                        except Exception as init_exc:
                            logger.warning("scheduled_tasks: failed to push %s to initiative queue: %s", task_id, init_exc)

                        # EXECUTE the reminder as a self-directive run — without
                        # this the reminder just lands as text in chat and Jarvis
                        # describes it instead of acting on it. Same pattern as
                        # the self-wakeup dispatcher's C-step.
                        if focus.strip():
                            try:
                                from core.services.visible_runs import start_autonomous_run
                                from core.identity.owner_resolver import (
                                    resolve_owner_app_session,
                                    resolve_owner_target_session,
                                    session_is_external_channel,
                                )
                                from core.services.wakeup_dispatcher import (
                                    pick_wakeup_run_target,
                                )

                                # KANAL-GUARD (13/10-2026). Før denne linje stod
                                # her `resolve_owner_target_session()` direkte —
                                # og den siger JA til en Discord-session, fordi
                                # `is_owner_session` accepterer titlen
                                # «Discord DM — {owner_id}». Målt samme aften:
                                # fem scheduled tasks, booket i en app-samtale,
                                # skrev i Bjørns Discord-DM.
                                #
                                # Wakeup-vejen havde allerede guarden; her
                                # manglede den. `pick_wakeup_run_target` med
                                # channel="app" afviser enhver ekstern kandidat
                                # og falder til `resolve_owner_app_session`, som
                                # KUN returnerer app/webchat-sessioner. None →
                                # kalderen opretter en frisk app-session.
                                #
                                # En scheduled reminder er ALTID en app-sag: den
                                # er booket af Jarvis inde i en samtale, ikke
                                # sendt til Discord. Samme guard som
                                # wakeup_dispatcher bruger (13/6-2026).
                                target_session = pick_wakeup_run_target(
                                    channel="app",
                                    record_session=str(task.get("session_id") or ""),
                                    app_resolver=resolve_owner_app_session,
                                    owner_resolver=resolve_owner_target_session,
                                    is_external=session_is_external_channel,
                                )

                                self_directive = (
                                    f"[SCHEDULED REMINDER FIRED — task_id={task_id}]\n"
                                    f"Du planlagde: {focus}\n\n"
                                    "UDFØR opgaven nu med dine tools — beskriv den ikke bare. "
                                    "Hvis det handler om at tjekke noget (Discord, en fil, "
                                    "en status), så BRUG værktøjet. "
                                    "Når du er færdig, rapportér resultatet kort til Bjørn."
                                )
                                start_autonomous_run(
                                    self_directive,
                                    session_id=target_session or None,
                                    origin="scheduled",
                                )
                                logger.info("scheduled_tasks: dispatched %s as autonomous run", task_id)
                                # B6: påmindelse fyrede OG blev dispatchet — synligt i Centralen.
                                try:
                                    from core.services.central_core import central
                                    central().observe({"cluster": "loop", "nerve": "scheduled_task_fire",
                                                       "task_id": task_id, "outcome": "dispatched"})
                                except Exception:
                                    pass
                            except Exception as run_exc:
                                logger.warning(
                                    "scheduled_tasks: autonomous run trigger failed for %s: %s",
                                    task_id, run_exc,
                                )
                                # B6: påmindelse fyrede men handlede IKKE (var stille) → flag i Centralen.
                                try:
                                    from core.services.central_core import central
                                    central().observe({"cluster": "loop", "nerve": "scheduled_task_fire",
                                                       "task_id": task_id, "outcome": "dispatch_failed",
                                                       "error": type(run_exc).__name__})
                                except Exception:
                                    pass
                    else:
                        # Delivery failed (no active session etc.) — leave pending, retry next poll
                        logger.warning(
                            "scheduled_tasks: %s delivery failed (%s) — will retry",
                            task_id,
                            result.get("error", "unknown"),
                        )
                except Exception as exc:
                    logger.error("scheduled_tasks: failed to fire %s: %s", task_id, exc)

            # Multi-user: tasks with scheduled_for_user_id use fire_scheduled_task
            # which validates the user in users.json and warns+drops for unknown
            # users (spec: Task 6 of multi-user workspace isolation).
            # Tasks without scheduled_for_user_id are legacy/owner-default — fire
            # in current context for backwards compatibility (Task 2 schema
            # migration pre-dates this; those rows won't have the field set).
            scheduled_uid = str(task.get("scheduled_for_user_id") or "").strip()
            if scheduled_uid:
                fire_scheduled_task(task, runner=_dispatch)
            else:
                with user_context():
                    _dispatch()

    try:
        from core.services.agent_runtime import run_due_agent_schedules

        fired = run_due_agent_schedules(limit=10)
        count = int(fired.get("triggered_count") or 0)
        if count:
            logger.info("scheduled_tasks: fired %s due agent schedules", count)
    except Exception as exc:
        logger.error("scheduled_tasks: agent schedule poller error: %s", exc)


def _poller_loop() -> None:
    while not _poller_stop.is_set():
        try:
            _fire_due_tasks()
        except Exception as exc:
            logger.error("scheduled_tasks: poller error: %s", exc)
            # A loop that fails every tick still looks alive from outside; make
            # persistent failure visible to the Central drift-monitor. Self-safe:
            # observe errors never touch loop behaviour (still logs + spins on).
            try:
                from core.services.central_private_observe import (
                    observe_operational_liveness,
                )
                observe_operational_liveness("scheduled_tasks", "error", None)
            except Exception:
                pass
        # INDBakken VÆKKER (10/10-2026). Bjørn: «skal inbox kunne vække dig, på
        # den hvis du ikk er i et aktivt run?» Svaret var nej: `inbox_gate`
        # blokerer kun mutationer INDE i et run, og intet startede et run fordi
        # en post fandtes. En `kraever_handling`-post uden dispatcher ventede
        # til næste heartbeat eller hans næste besked. Vækkeren er konservativ
        # (kun gatende poster, kun når intet kører, én vækning pr. post) og
        # self-safe — den må aldrig vælte polleren.
        try:
            from core.services.inbox_idle_waker import vaek_paa_aabne_poster
            from core.services.inbox_state import bruger_for_workspace
            from core.identity.workspace_context import current_workspace_name

            vaek_paa_aabne_poster(
                bruger_id=bruger_for_workspace(current_workspace_name() or "bjorn"))
        except Exception as exc:
            logger.debug("scheduled_tasks: inbox-vaekker fejlede: %s", exc)
        # SIDE-OPGAVER I IDLE-VINDUET. Kun poster der ved oprettelsen fik en
        # eksplicit autonomy_mode kan vælges; almindelige side-opgaver er
        # fortsat en huskeliste. Dispatcheren starter højst én og kræver både
        # 15 minutters tomgang, en ejer-session og nul aktive runs.
        try:
            from core.services.autonomous_side_task_dispatcher import dispatch_one

            dispatch_one()
        except Exception as exc:
            logger.warning("scheduled_tasks: autonom side-opgave-dispatch fejlede: %s", exc)
            try:
                from core.services.background_attention import report_background_outcome

                report_background_outcome(
                    source_kind="side-task-dispatcher", source_id="poll",
                    status="failed", severity="high",
                    summary=(
                        "Den autonome side-opgave-dispatcher fejlede "
                        f"({type(exc).__name__})."
                    ),
                    suggested_next_step="Undersøg dispatcher-loggen; ingen ny side-opgave blev startet.",
                    requires_attention=True, safe_to_continue=False,
                )
            except Exception:  # the scheduler loop retries durable reporting
                pass
        _poller_stop.wait(_POLL_INTERVAL_SECONDS)


def start_scheduled_tasks_service() -> None:
    global _poller_thread
    _poller_stop.clear()
    t = threading.Thread(target=_poller_loop, daemon=True, name="scheduled-tasks-poller")
    t.start()
    _poller_thread = t
    logger.info("scheduled_tasks: service started (poll interval %ds)", _POLL_INTERVAL_SECONDS)


def stop_scheduled_tasks_service() -> None:
    _poller_stop.set()
    logger.info("scheduled_tasks: service stopped")


def build_scheduled_tasks_surface() -> dict[str, object]:
    """Mission Control surface — read-only meta-projection.

    Added during 2026-05-13 coverage push (system_cartographer dark-edge
    closure). Reports module presence so the cartographer registers it as
    observed. Specific state-readers added as the module evolves.
    """
    return {
        "active": True,
        "mode": "scheduled_tasks",
        "summary": "Module loaded; entry points available.",
        "authority": "derived-read-only",
    }

