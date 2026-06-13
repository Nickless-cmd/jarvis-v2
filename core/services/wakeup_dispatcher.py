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
import threading
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Serialiser adgang til dispatch-sektionen — forhindrer TOCTOU-race
# mellem _load() og _save() når dispatch_due_wakeups() kaldes
# samtidigt fra f.eks. periodic_jobs_scheduler + heartbeat poll.
_dispatch_lock = threading.Lock()


def pick_wakeup_run_target(
    *,
    channel: str,
    record_session: str,
    app_resolver,
    owner_resolver,
    is_external,
) -> str | None:
    """Beslut hvilken session et wakeup-run skal lande i — med Discord-guard.

    App/operator-wakeups (default, channel != "discord") må ALDRIG ende i en
    ekstern kanal (Discord/Telegram), heller ikke selv om en eksplicit
    session_id peger derhen, eller owner-resolveren ville vælge den. Kun
    eksplicit channel=="discord" tillader ekstern levering (Bjørn 2026-06-13).

    Ren funktion (injicerbare resolvers) → kan testes uden DB.
    Returnerer en session-id, eller None → kalderen opretter en frisk app-session.
    """
    ch = (channel or "app").strip().lower()
    if ch == "discord":
        return (record_session or "").strip() or owner_resolver() or None
    # app/webchat: guard mod eksterne kanaler
    cand = (record_session or "").strip()
    if cand and is_external(cand):
        logger.info("wakeup guard: eksplicit session %s er ekstern kanal — afvist for app-wakeup", cand)
        cand = ""
    if not cand:
        cand = app_resolver() or ""  # springer allerede eksterne over
    return cand or None


def dispatch_due_wakeups() -> dict[str, Any]:
    """Find newly-fired wakeups, push them out via webchat + heartbeat tick."""
    from core.services.self_wakeup import due_wakeups, _load, _save

    with _dispatch_lock:
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

            # A: route through outbound_nudges
            # Default "app" (jarvis-desk) — wakeups må ALDRIG default'e til
            # Discord. "webchat" behandles som app (samme in-app destination).
            wakeup_channel = str(record.get("channel") or "app").strip().lower()
            wakeup_session = record.get("session_id", "")
            nudge_message = (
                f"Self-wakeup fyrede ({reason or 'no reason'}): {prompt} "
                f"[wakeup_id={wid}, channel={wakeup_channel}]"
            )
            try:
                from core.runtime.settings import load_settings as _ls_w
                if _ls_w().nudge_system_enabled:
                    from core.services.outbound_nudges import push_nudge
                    push_nudge(
                        source="wakeup_dispatcher",
                        kind="other",
                        message=nudge_message,
                        importance="normal",
                        parent_session_id=wakeup_session,
                    )
                else:
                    if wakeup_channel == "discord":
                        from core.services.discord_gateway import send_dm_to_user, is_gateway_connected
                        from core.services.discord_identity import get_owner_discord_id
                        if is_gateway_connected():
                            owner_id = get_owner_discord_id()
                            if owner_id:
                                send_dm_to_user(owner_id, f"⏰ Self-wakeup: {prompt}\n_(wakeup_id: {wid})_")
                    else:
                        from core.services.notification_bridge import send_session_notification
                        send_session_notification(nudge_message, source="self-wakeup")
            except Exception as exc:
                logger.warning("wakeup nudge push failed: %s", exc)

            # B: trigger heartbeat phase tick
            try:
                from core.services.heartbeat_phases import tick_with_phases
                tick_with_phases(name="default", trigger="self-wakeup-fire")
            except Exception as exc:
                logger.debug("wakeup heartbeat trigger failed: %s", exc)

            # C: actually EXECUTE the wakeup prompt as a self-directive run
            if prompt.strip():
                try:
                    from core.services.visible_runs import start_autonomous_run
                    from core.identity.owner_resolver import (
                        resolve_owner_app_session,
                        resolve_owner_target_session,
                        session_is_external_channel,
                    )
                    # GUARD: app/operator-wakeups må ALDRIG re-engagere i en
                    # ekstern kanal (Discord/Telegram). Kun eksplicit
                    # channel=="discord" tillader det.
                    target_session = pick_wakeup_run_target(
                        channel=wakeup_channel,
                        record_session=str(wakeup_session or ""),
                        app_resolver=resolve_owner_app_session,
                        owner_resolver=resolve_owner_target_session,
                        is_external=session_is_external_channel,
                    )
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

            # Mark dispatched in record (inside lock — TOCTOU race fix)
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
