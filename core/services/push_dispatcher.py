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


def _dispatch_run_done(run_id: str) -> None:
    from core.services import run_event_log as rel
    if rel.was_consumed_or_active(run_id):
        return  # nogen saa det live
    sid = rel.session_for_run(run_id)
    owner = _owner_of_run(run_id)
    if not owner:
        return
    _push_to_user(owner, {"kind": "answer_ready", "session_id": sid or "", "run_id": run_id})


def on_run_done(run_id: str) -> None:
    """Kaldes fra detached_run finally. Planlaegger suppression-tjek efter grace."""
    try:
        threading.Timer(PUSH_GRACE_S, _dispatch_run_done, args=(run_id,)).start()
    except Exception as e:
        logger.warning("push: kunne ikke planlaegge run-done-tjek: %s", e)


def on_initiative(user_id: str, text: str) -> None:
    if not user_id:
        return
    _push_to_user(user_id, {"kind": "initiative", "preview": (text or "")[:80]})


def on_reminder(user_id: str, text: str) -> None:
    if not user_id:
        return
    _push_to_user(user_id, {"kind": "reminder", "preview": (text or "")[:80]})
