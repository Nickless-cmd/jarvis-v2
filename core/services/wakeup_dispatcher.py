"""Wakeup dispatcher — autonomous fire of self-wakeups.

Self-wakeups land in awareness when Jarvis has a turn. Without this
dispatcher, a wakeup that fires when no user is talking just sits in
state forever — the prompt is never built, awareness never renders.

Three actions per fired wakeup (matches user's A+B+C plan):

A) Push to webchat — actively notify the user (wakeup is "loud")
B) Trigger heartbeat phase tick — wakes Jarvis' inner loop
C) Send webchat message FROM Jarvis — quote the wakeup prompt
   so when the user sees it they can engage

Idempotent: each wakeup is only dispatched once. After dispatch, the
wakeup stays in 'fired' status until Jarvis calls mark_wakeup_consumed.
We track dispatched-already in the wakeup record itself.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def dispatch_due_wakeups() -> dict[str, Any]:
    """Find newly-fired wakeups, push them out via webchat + heartbeat tick."""
    from core.services.self_wakeup import due_wakeups, _load, _save

    fired = due_wakeups(include_fired_unconsumed=True)
    if not fired:
        return {"status": "ok", "dispatched": 0}

    # Load full records to check + mutate dispatched flag
    all_records = _load()
    by_id = {r.get("wakeup_id"): r for r in all_records}

    dispatched: list[str] = []
    for w in fired:
        wid = w.get("wakeup_id")
        record = by_id.get(wid)
        if record is None or record.get("dispatched"):
            continue
        prompt = str(record.get("prompt", ""))
        reason = str(record.get("reason", ""))

        # A: push to webchat + Discord DM (dual-channel — user sees it
        # regardless of which channel they're active on)
        try:
            from core.services.notification_bridge import send_session_notification
            msg = (
                f"⏰ Self-wakeup fyrede ({reason or 'no reason'}):\n"
                f"  {prompt}\n"
                f"_(wakeup_id: {wid})_"
            )
            send_session_notification(msg, source="self-wakeup")
        except Exception as exc:
            logger.warning("wakeup webchat push failed: %s", exc)

        # Discord DM fallback — ensures the user sees the wakeup even when
        # they're talking on Discord instead of webchat
        try:
            from core.services.discord_gateway import send_dm_to_user, is_gateway_connected
            from core.services.discord_identity import get_owner_discord_id
            if is_gateway_connected():
                owner_id = get_owner_discord_id()
                if owner_id:
                    send_dm_to_user(
                        owner_id,
                        f"⏰ Self-wakeup: {prompt}\n_(wakeup_id: {wid})_",
                    )
        except Exception as exc:
            logger.debug("wakeup Discord DM failed: %s", exc)

        # B: trigger heartbeat phase tick (lets Jarvis' inner loop see it)
        try:
            from core.services.heartbeat_phases import tick_with_phases
            tick_with_phases(name="default", trigger="self-wakeup-fire")
        except Exception as exc:
            logger.debug("wakeup heartbeat trigger failed: %s", exc)

        # C: actually EXECUTE the wakeup prompt as a self-directive run.
        # Without this step the wakeup just sits in awareness — Jarvis sees
        # it but never picks up the prompt and acts. start_autonomous_run
        # spawns a fire-and-forget visible run on the active session so the
        # tools fire, the answer streams to chat, and the user sees Jarvis
        # actually doing the thing he asked himself to do.
        if prompt.strip():
            try:
                from core.services.visible_runs import start_autonomous_run
                from core.services.notification_bridge import get_pinned_session_id
                from core.services.chat_sessions import (
                    get_chat_session,
                    list_chat_sessions,
                )

                # Resolve the same session the A-step delivered to so the
                # autonomous reply lands in the user's view, not in a hidden
                # autonomous-only session.
                target_session = get_pinned_session_id() or ""
                if not target_session:
                    for s in list_chat_sessions():
                        sid = str((s or {}).get("id") or "").strip()
                        if not sid:
                            continue
                        full = get_chat_session(sid)
                        if full and any(
                            m.get("role") == "user" for m in (full.get("messages") or [])
                        ):
                            target_session = sid
                            break

                self_directive = (
                    f"[SELF-WAKEUP FIRED — wakeup_id={wid}]\n"
                    f"Du bad dig selv: {prompt}\n"
                    f"Kontekst: {reason or '(ingen begrundelse angivet)'}\n\n"
                    "UDFØR opgaven nu med dine tools — beskriv den ikke bare. "
                    "Hvis prompten siger 'tjek Discord', så BRUG discord_channel-værktøjet. "
                    "Hvis den siger 'læs filen X', så BRUG read_file. "
                    "Når du er færdig, kald `mark_wakeup_consumed` med wakeup_id="
                    f"\"{wid}\" og rapportér resultatet kort til Bjørn."
                )
                start_autonomous_run(
                    self_directive,
                    session_id=target_session or None,
                )
            except Exception as exc:
                logger.warning("wakeup autonomous run trigger failed: %s", exc)

        # Mark dispatched in record
        record["dispatched"] = True
        record["dispatched_at"] = datetime.now(UTC).isoformat()
        dispatched.append(str(wid))

        # Eventbus
        try:
            from core.eventbus.bus import event_bus
            event_bus.publish(
                "self_wakeup.dispatched",
                {"wakeup_id": wid, "reason": reason[:80]},
            )
        except Exception:
            pass

    if dispatched:
        _save(all_records)

    return {"status": "ok", "dispatched": len(dispatched), "dispatched_ids": dispatched}


def _exec_dispatch_due_wakeups(args: dict[str, Any]) -> dict[str, Any]:
    return dispatch_due_wakeups()


WAKEUP_DISPATCHER_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "dispatch_due_wakeups",
            "description": (
                "Manually run the wakeup dispatcher (normally automatic via "
                "periodic_jobs_scheduler every 60s). Pushes any fired-but-undispatched "
                "wakeups to webchat + triggers heartbeat tick."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
