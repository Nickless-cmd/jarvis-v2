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

Aktiv-guard (12/9-2026): fyrer et wakeup mens en visible-tur ALLEREDE kører
i samme session, starter vi ikke et konkurrerende autonomt run. Recorden får
`dispatch_skipped_reason="user_active"`, og awareness-vejen bærer
instruktionerne inde i den aktive tur. Målt på wake-d07eaea13d (16:57:35),
der fyrede 26 s efter Bjørn selv skrev — uden spor og uden forklaring.
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

# Hvor frisk en aktiv visible-tur skal være for at blokere et wakeup-run.
# Samme tærskel som visible_runs bruger for «same-session stale» (120 s): et
# run der ikke har rørt sig i to minutter er ikke længere «nogen taler nu».
_ACTIVE_TURN_FRESH_S = 120.0


def _active_turn_blocks(session_id: str) -> str:
    """Returnér en skip-årsag hvis en FERSK visible-tur kører i sessionen.

    12/9-2026: wake-d07eaea13d fyrede 16:57:35 mens Bjørn skrev (16:58:01).
    Dispatcheren startede alligevel sit eget run oveni turen. Målt: intet
    `dispatched`-flag, intet autonomt run — den faldt stille tilbage, og
    koden kunne ikke fortælle hvorfor.

    Nu spørger vi FØRST om nogen taler i den session wakeup'en hører til.
    Er svaret ja, starter vi IKKE et konkurrerende run: awareness-vejen bærer
    instruktionerne inde i den aktive tur, og recorden får et spor så Jarvis
    kan se at den blev afvist med vilje — ikke glemt.

    Self-safe: enhver fejl → "" (ingen blokering). Et wakeup må aldrig
    forsvinde fordi aktiv-tilstanden ikke kunne læses.
    """
    try:
        from core.services.visible_runs import _get_active_visible_run_state

        state = _get_active_visible_run_state() or {}
    except Exception:
        return ""
    if not state or not bool(state.get("active", True)):
        return ""
    active_sid = str(state.get("session_id") or "")
    # Anden session taler → wakeup'en hører ikke til der. Kun når vi ikke kan
    # afgøre det (wakeup uden session, eller aktiv uden session) blokerer vi.
    if session_id and active_sid and active_sid != session_id:
        return ""
    ts = str(state.get("last_activity_at") or state.get("started_at") or "")
    if not ts:
        return "user_active"
    try:
        started = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        age_s = (datetime.now(UTC) - started).total_seconds()
    except Exception:
        return "user_active"
    if age_s > _ACTIVE_TURN_FRESH_S:
        return ""
    return "user_active"


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
        skipped: list[str] = []
        for w in fired:
            wid = w.get("wakeup_id")
            record = by_id.get(wid)
            if record is None or record.get("dispatched"):
                continue
            # 12/9-2026: en wakeup der blev afvist fordi en tur VAR aktiv, prøves
            # ikke igen. Awareness bærer den (status forbliver 'fired' indtil
            # mark_wakeup_consumed), så instruktionerne går ikke tabt — og vi
            # undgår at dispatche et autonomt run oveni en tur der er i gang.
            if str(record.get("dispatch_skipped_reason") or "").startswith("user_active"):
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
            run_started = False
            skip_reason = ""
            if not prompt.strip():
                skip_reason = "empty_prompt"
            else:
                try:
                    from core.services.autonomous_stream_run import (
                        start_autonomous_stream_run,
                    )
                    from core.identity.workspace_context import reset_context, set_context
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
                    # 12/9-2026: aktiv-guard. Fyrede wakeup'en midt i en tur, må
                    # dispatcheren IKKE starte sit eget run oveni — så taler to
                    # runs i samme session. Vi afviser med et spor; awareness
                    # bærer instruktionerne inde i den aktive tur i stedet.
                    blocked = _active_turn_blocks(str(target_session or ""))
                    if blocked:
                        skip_reason = blocked
                    else:
                        extra = str(record.get("extra") or "").strip()
                        self_directive = (
                            f"[SELF-WAKEUP FIRED — wakeup_id={wid}]\n"
                            f"Du bad dig selv: {prompt}\n"
                            f"Kontekst: {reason or '(ingen begrundelse angivet)'}\n"
                            + (f"Tilføjelse: {extra}\n" if extra else "")
                            + "\nUDFØR opgaven nu med dine tools — beskriv den ikke bare. "
                            "Hvis prompten siger 'tjek Discord', så BRUG discord_channel-værktøjet. "
                            "Hvis den siger 'læs filen X', så BRUG read_file. "
                            "Når du er færdig, kald `mark_wakeup_consumed` med wakeup_id="
                            f"\"{wid}\" og rapportér resultatet kort til Bjørn."
                        )
                        context_token = set_context(
                            workspace_name=str(record.get("workspace_name") or "bjorn"),
                            user_id=str(record.get("user_id") or ""),
                            user_display_name=str(record.get("user_display_name") or ""),
                            role=str(record.get("role") or ""),
                            channel=str(record.get("context_channel") or ""),
                            session_id=target_session or "",
                        )
                        try:
                            start_autonomous_stream_run(
                                self_directive,
                                session_id=target_session,
                                origin="wakeup",
                            )
                            run_started = True
                        finally:
                            reset_context(context_token)
                except Exception as exc:
                    logger.warning("wakeup autonomous run trigger failed: %s", exc)
                    skip_reason = f"run_start_failed: {str(exc)[:160]}"

            if not run_started:
                # 12/9-2026: efterlad spor. Uden dette står recorden som 'fired'
                # uden forklaring, og awareness-vejen kan ikke skelne «kørte
                # planlagt» fra «faldt tilbage fordi du var aktiv». Målt på
                # wake-d07eaea13d (intet flag) vs wake-bc9c4ebdbc (flag sat,
                # +0,76 s efter fired_at, med autonomt run).
                record["dispatch_skipped"] = True
                record["dispatch_skipped_at"] = datetime.now(UTC).isoformat()
                record["dispatch_skipped_reason"] = skip_reason or "unknown"
                skipped.append(str(wid))
                continue

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

        if dispatched or skipped:
            _save(all_records)

        return {
            "status": "ok",
            "dispatched": len(dispatched),
            "dispatched_ids": dispatched,
            "skipped": len(skipped),
            "skipped_ids": skipped,
        }


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
