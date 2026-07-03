"""Beslutter HVORNAAR og HVEM der skal pushes. Bygger paa run_event_log-suppression."""
from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

PUSH_GRACE_S = 5.0  # giv en levende klient tid til at draene sidste frames foer vi tjekker


def _fcm_send(token: str, data: dict):
    from core.services.fcm_gateway import send
    return send(token, data)


def _owner_of_run(run_id: str):
    from core.services import run_event_log as rel
    from core.services.chat_sessions import get_session_owner
    sid = rel.session_for_run(run_id)
    return get_session_owner(sid) if sid else None


def _push_to_user(user_id: str, data: dict) -> None:
    from core.services import device_tokens as dt
    for token in dt.list_for_user(user_id):
        try:
            ok, code = _fcm_send(token, data)
            if not ok and code == "invalid":
                dt.delete(token)
        except Exception as e:
            logger.warning("push: send-fejl for token: %s", e)


def _route_or_blast(user_id: str, data: dict, kind: str) -> None:
    """Flag ON → intelligent device-routing; OFF → gammel FCM-blast (bagudkompat)."""
    try:
        from core.runtime.settings import load_settings
        if load_settings().device_awareness_enabled:
            from core.services import notification_router
            notification_router.route_device_aware(user_id, data, kind)
            return
    except Exception as e:
        logger.warning("push: routing-fejl, falder tilbage til blast: %s", e)
    _push_to_user(user_id, data)


def _last_assistant_preview(session_id: str, *, width: int = 160) -> str:
    """Sidste assistant-beskeds tekst (trunkeret) til notifikations-preview. "" hvis ingen.
    Bruges så pushet VISER hvad Jarvis sagde — ikke bare et tomt 'Jarvis har svaret'."""
    try:
        if not (session_id or "").strip():
            return ""
        from core.services.chat_sessions import recent_chat_session_messages
        msgs = recent_chat_session_messages(session_id, limit=6) or []
        for m in reversed(msgs):  # nyeste først → find seneste assistant-svar
            if str(m.get("role") or "") == "assistant":
                txt = " ".join(str(m.get("content") or "").split()).strip()
                if txt:
                    return txt[:width] + ("…" if len(txt) > width else "")
        return ""
    except Exception:
        return ""


def _dispatch_run_done(run_id: str) -> None:
    from core.services import run_event_log as rel
    if rel.was_consumed_or_active(run_id):
        logger.warning("push: answer_ready UNDERTRYKT (run %s set live)", run_id[:12])
        return  # nogen saa det live
    sid = rel.session_for_run(run_id)
    owner = _owner_of_run(run_id)
    if not owner:
        return
    # SPRING pushet over hvis runnet ikke producerede et synligt assistant-svar (rent
    # autonomt internt arbejde) → ingen tomme spam-notifikationer (Bjørn 3. jul).
    #
    # VIGTIGT: answer_ready sendes DATA-ONLY (ingen title/preview) MED VILJE. Mobil-appen
    # renderer den selv via notifee (henter svaret over HTTPS + Direct Reply + tap→åbn-
    # session). Sætter vi title+preview, bygger fcm_gateway en 'notification'-blok →
    # Android viser den via system-baren UDEN OM notifee → tap-navigation (notifee.
    # getInitialNotification) + fetchLatest brydes = "tap viser intet". Hold den data-only.
    if not _last_assistant_preview(sid):
        logger.warning("push: answer_ready SPRUNGET OVER (run %s uden svar-tekst)", run_id[:12])
        return
    logger.warning("push: answer_ready DISPATCH for run %s", run_id[:12])
    _route_or_blast(owner, {"kind": "answer_ready", "session_id": sid or "", "run_id": run_id},
                    "answer_ready")


def on_run_done(run_id: str) -> None:
    """Kaldes fra detached_run finally. Planlaegger suppression-tjek efter grace."""
    try:
        threading.Timer(PUSH_GRACE_S, _dispatch_run_done, args=(run_id,)).start()
    except Exception as e:
        logger.warning("push: kunne ikke planlaegge run-done-tjek: %s", e)


def send_companion_push(user_id: str, message: str, title: str = "Jarvis") -> bool:
    """Proaktiv push til brugerens companion-enheder (mobil + desktop) via
    device-routing. Bruges af send_push_notification-tool'et så Jarvis selv kan
    naa brugeren naar de er vaek fra chatten. Returnerer True hvis afsendt."""
    uid = (user_id or "").strip()
    text = (message or "").strip()
    if not uid or not text:
        return False
    logger.warning("push: send_companion_push (tool) uid=%s msg=%r", uid[:8], text[:40])
    _route_or_blast(uid, {"kind": "initiative", "preview": text[:140], "title": title}, "initiative")
    return True


def on_initiative(user_id: str, text: str) -> None:
    if not user_id:
        return
    _route_or_blast(user_id, {"kind": "initiative", "preview": (text or "")[:80]}, "initiative")


def on_reminder(user_id: str, text: str) -> None:
    if not user_id:
        return
    _route_or_blast(user_id, {"kind": "reminder", "preview": (text or "")[:80]}, "reminder")
