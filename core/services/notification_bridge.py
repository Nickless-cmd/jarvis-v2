"""Notification bridge — lets Jarvis push messages to the active session.

Two entry points:
  1. send_session_notification(content, source) — called directly (tool, tick, etc.)
  2. Boredom subscriber — auto-fires when boredom reaches "productive" threshold.
"""
from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

from core.eventbus.bus import event_bus
from core.runtime.db import get_runtime_state_value, set_runtime_state_value

logger = logging.getLogger(__name__)

_boredom_sub: object | None = None
_boredom_thread: threading.Thread | None = None
_boredom_stop = threading.Event()

# Guard: only one boredom notification per productive episode
_last_boredom_notification_level: str = "none"

# The session currently active in the user's browser. When set, proactive
# notifications are delivered here instead of guessing from list_chat_sessions().
_PINNED_SESSION_STATE_KEY = "notification_bridge.pinned_session_id"


def pin_session(session_id: str) -> None:
    """Record which session the user is currently viewing. Call on every user message."""
    normalized = (session_id or "").strip()
    if not normalized:
        return
    set_runtime_state_value(
        _PINNED_SESSION_STATE_KEY,
        {
            "session_id": normalized,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    )


def get_pinned_session_id() -> str:
    """Return the currently pinned session ID, or empty string if none.

    17/9-2026: pin'en blev sat én gang og pegede derefter på en session der
    ikke længere findes (`chat-8d36a224…`). Alle kaldere — wakeup-resolveren
    og heartbeat — troede derfor de havde et gyldigt mål og sprang deres egne
    fallbacks over. Vi validerer nu at sessionen faktisk findes; gør den ikke,
    rydder vi pin'en og svarer "" så kalderen må vælge på ny.
    """
    payload = get_runtime_state_value(_PINNED_SESSION_STATE_KEY, default={})
    if not isinstance(payload, dict):
        return ""
    sid = str(payload.get("session_id") or "").strip()
    if not sid:
        return ""
    try:
        from core.services.chat_sessions import get_chat_session
        if get_chat_session(sid) is None:
            logger.warning(
                "notification_bridge: pinnet session %s findes ikke — rydder pin", sid
            )
            set_runtime_state_value(_PINNED_SESSION_STATE_KEY, {})
            return ""
    except Exception:
        # Kan vi ikke slå op, lader vi pin'en stå: en DB-hikke må ikke smide et
        # gyldigt mål væk (fail-open, samme valg som session_is_external_channel).
        pass
    return sid


def _push_proactive(session_id: str, text: str) -> None:
    """Spejl en proaktiv session-notifikation som mobil-push til sessionens ejer."""
    try:
        from core.services.chat_sessions import get_session_owner
        from core.services.push_dispatcher import on_initiative
        owner = get_session_owner(session_id)
        if owner:
            on_initiative(owner, text)
    except Exception:
        pass


# 23/9-2026: send_session_notification har TRE udfald, ikke to — men hvert
# kaldested tjekkede `status == "ok"` og behandlede dermed "queued" som fejl.
# Det kostede en dobbelt-levering: morgenbriefen blev køet (Bjørn sad aktivt i
# chatten), run'et læste "queued" som "webchat nede" og tog Discord-nødplanen.
# Kontrakten bor nu her, ét sted, så ingen læser skal gætte den igen.
_DELIVERY_OK_STATUSES = frozenset({"ok", "queued"})


def delivery_succeeded(result: object) -> bool:
    """True når notifikationen er ANTAGET til levering.

    "ok"     — skrevet direkte ind i sessionen nu.
    "queued" — sessionen var aktiv; beskeden ligger i session_inbox og
               flushes efter den igangværende tur. Stadig en succes.
    Alt andet ("blocked", "error", manglende status) er en reel fejl.
    """
    if not isinstance(result, dict):
        return False
    return str(result.get("status") or "") in _DELIVERY_OK_STATUSES


def _koe_afsender(user_id: str | None, workspace_name: str | None) -> dict[str, str]:
    """Kun de afsender-felter der faktisk er sat — se begrundelsen ved
    `_afsender` i `send_session_notification`. Holder kaldet til `enqueue`
    uaendret for kaldere der ikke saetter dem."""
    ud: dict[str, str] = {}
    if (user_id or "").strip():
        ud["user_id"] = str(user_id)
    if (workspace_name or "").strip():
        ud["workspace_name"] = str(workspace_name)
    return ud


def send_session_notification(
    content: str,
    *,
    source: str = "jarvis-notify",
    urgent: bool = False,
    session_id: str | None = None,
    user_id: str | None = None,
    workspace_name: str | None = None,
    push: bool = True,
) -> dict[str, object]:
    """Append a proactive message to the most recently active chat session.

    Returns a status dict. Never raises — returns error dict on failure.

    2/10-2026: fire moduler skrev direkte med `append_chat_message` og var
    derfor HELT uden daemon-vagten nedenfor — de kunne banke paa midt i en
    saetning. De er flyttet herind, og de fire parametre er hvad flytningen
    kraevede for at vaere adfaerds-bevarende:

    * `session_id` — de kender selv deres maal (fx heartbeat'ens webchat-
      session). Uden den ville de skifte til den session DENNE funktion
      udvaelger, altsaa en anden samtale end i dag.
    * `user_id`/`workspace_name` — `append_chat_message` falder tilbage paa
      kontekst-variabler naar de er tomme, og en daemon-traad har ingen
      kontekst. De sendes derfor videre baade paa den direkte OG den koeede
      vej (se `session_inbox.enqueue`).
    * `push=False` — ingen af de fire sendte mobil-push i dag. At flytte dem
      ind maa ikke give Bjoern fire NYE push-kilder; det var det modsatte af
      formaalet.

    Resultatet baerer `message` paa "ok"-vejen, saa kaldere der skal have et
    message_id (heartbeat-ledgeren, execution-piloten) kan faa det.

    **Laes status med `delivery_succeeded()`, ikke `== "ok"`.** "queued" er
    ogsaa en succes; den fejl kostede en dobbelt-levering 23/9 — se noten ved
    `_DELIVERY_OK_STATUSES`.

    2026-05-24 (Claude): when the target session is active (chat-stream
    activity within last 5 min) AND urgent=False, the notification is
    queued in session_inbox instead of appended directly. It will be
    flushed after Jarvis' next turn completes — preventing the "knock at
    the door mid-sentence" effect Jarvis flagged in inner-voice and
    Bjørn observed externally. urgent=True bypasses the queue for
    emergencies (errors, security alerts, etc.).
    """
    from core.services.chat_sessions import (
        append_chat_message,
        get_chat_session,
        list_chat_sessions,
    )

    content = content.strip()
    if not content:
        return {"status": "error", "error": "empty content"}

    # Communication guard — backstop: scrub hård afslutnings-fraser fra
    # proaktive notifikationer (godnat/sov godt). Bløde fraser røres ikke.
    try:
        from core.services.communication_guard import guard_channel_text
        content = guard_channel_text(content, "notification").strip()
        if not content:
            return {"status": "blocked", "error": "communication-guard-blocked"}
    except Exception:
        pass

    # Use the pinned session if set (e.g. the session currently active in the user's browser),
    # otherwise fall back to the most recently updated session that has user messages
    # (to avoid sending to autonomous-run-only sessions which the user may not be watching).
    session_id = (session_id or "").strip() or get_pinned_session_id()
    if not session_id:
        sessions = list_chat_sessions()
        for s in sessions:
            sid = str((s or {}).get("id") or "").strip()
            if not sid:
                continue
            full = get_chat_session(sid)
            if full and any(m.get("role") == "user" for m in (full.get("messages") or [])):
                session_id = sid
                break
        if not session_id:
            session_id = str((sessions[0] or {}).get("id") or "").strip() if sessions else ""
    if not session_id:
        return {"status": "blocked", "error": "no active session"}
    if get_chat_session(session_id) is None:
        # Skelnes fra «ingen aktiv session»: her HAVDE vi en session — den
        # findes bare ikke (slettet, eller en kalder gav et id vi ikke kender).
        # Teksten betoed foer begge ting, og det sendte fejlsoegningen forkert
        # vej 2/10-2026 da fire kaldesteder begyndte at sende deres egen.
        return {"status": "blocked", "error": f"unknown session: {session_id}"}

    # Daemon-interruption gate: queue if session is active and not urgent.
    if not urgent:
        try:
            from core.services.session_inbox import (
                is_session_active, enqueue as inbox_enqueue,
            )
            if is_session_active(session_id):
                result = inbox_enqueue(
                    session_id=session_id,
                    content=content,
                    source=source,
                    urgent=False,
                    **_koe_afsender(user_id, workspace_name),
                )
                if result.get("status") == "queued":
                    logger.info(
                        "notification_bridge: queued [%s] for session %s "
                        "(active session — will flush after next turn)",
                        source, session_id,
                    )
                    return {
                        "status": "queued",
                        "session_id": session_id,
                        "source": source,
                        "inbox_id": result.get("id"),
                    }
        except Exception:
            # If inbox path fails, fall through to direct delivery
            logger.exception("notification_bridge: inbox gate failed; delivering directly")

    try:
        # Kun de felter afsenderen FAKTISK satte. `user_id=None` er semantisk
        # identisk med at udelade det (append_chat_message falder tilbage paa
        # kontekst-variabler), men at sende dem ubetinget aendrer kaldets FORM —
        # og fire test-stubs med en smal signatur braekkede paa det 2/10. Et
        # kald fra en kalder der ikke saetter dem er nu byte-identisk med foer.
        _afsender: dict[str, str] = {}
        if (user_id or "").strip():
            _afsender["user_id"] = str(user_id)
        if (workspace_name or "").strip():
            _afsender["workspace_name"] = str(workspace_name)
        message = append_chat_message(
            session_id=session_id,
            role="assistant",
            content=content,
            **_afsender,
        )
        event_bus.publish(
            "channel.chat_message_appended",
            {
                "session_id": session_id,
                "message": message,
                "source": source,
            },
        )
        logger.info("notification_bridge: delivered [%s] to session %s", source, session_id)
        if push:
            _push_proactive(session_id, content)
        return {"status": "ok", "session_id": session_id, "source": source,
                "message": message}
    except Exception as exc:
        logger.error("notification_bridge: delivery failed: %s", exc, exc_info=True)
        return {"status": "error", "error": str(exc)}


def _boredom_listener_loop() -> None:
    """Background thread that listens for boredom_productive events."""
    global _last_boredom_notification_level
    from core.eventbus.bus import event_bus as bus
    sub = bus.subscribe()
    try:
        while not _boredom_stop.is_set():
            import queue as _q
            try:
                item = sub.get(timeout=1.0)
            except _q.Empty:
                continue
            if item is None:
                break
            kind = item.get("kind", "") if isinstance(item, dict) else ""
            if kind != "cognitive_state.boredom_productive":
                continue
            # Only notify once per productive episode (reset when level drops)
            if _last_boredom_notification_level == "productive":
                continue
            _last_boredom_notification_level = "productive"
            try:
                from core.services.boredom_engine import get_boredom_state
                state = get_boredom_state()
                restlessness = state.get("restlessness", 0)
                desire = state.get("desire", "")
                msg = f"[boredom] Restlessness {restlessness:.0%} — {desire}" if desire else f"[boredom] Restlessness {restlessness:.0%}"
                # Route through nudge ledger (Path 6 of spejlsal-audit).
                try:
                    from core.runtime.settings import load_settings as _ls_b
                    if _ls_b().nudge_system_enabled:
                        from core.services.outbound_nudges import push_nudge
                        push_nudge(
                            source="boredom_bridge",
                            kind="boredom",
                            message=msg,
                            importance="low",
                        )
                    else:
                        send_session_notification(msg, source="boredom-bridge")
                except Exception:
                    send_session_notification(msg, source="boredom-bridge")
            except Exception as exc:
                logger.error("notification_bridge: boredom notify failed: %s", exc)
    finally:
        bus.unsubscribe(sub)


def _reset_boredom_level_listener_loop() -> None:
    """Background thread that resets the boredom notification guard when level drops."""
    global _last_boredom_notification_level
    from core.eventbus.bus import event_bus as bus
    sub = bus.subscribe()
    try:
        while not _boredom_stop.is_set():
            import queue as _q
            try:
                item = sub.get(timeout=1.0)
            except _q.Empty:
                continue
            if item is None:
                break
            if not isinstance(item, dict):
                continue
            kind = item.get("kind", "")
            payload = item.get("payload") or {}
            if kind == "cognitive_state.boredom_productive":
                continue
            # Any heartbeat tick completion resets guard so next productive episode fires again
            if kind in ("heartbeat.tick_completed", "heartbeat.tick_blocked"):
                _last_boredom_notification_level = "none"
    finally:
        bus.unsubscribe(sub)


def start_notification_bridge() -> None:
    """Start the boredom notification listener threads."""
    global _boredom_thread, _boredom_stop
    _boredom_stop.clear()
    t = threading.Thread(target=_boredom_listener_loop, daemon=True, name="boredom-notify")
    t.start()
    _boredom_thread = t
    t2 = threading.Thread(target=_reset_boredom_level_listener_loop, daemon=True, name="boredom-reset")
    t2.start()
    logger.info("notification_bridge: started")


def stop_notification_bridge() -> None:
    """Stop the boredom notification listener."""
    _boredom_stop.set()
    logger.info("notification_bridge: stopped")
