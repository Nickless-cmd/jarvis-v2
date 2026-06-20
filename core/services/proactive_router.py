"""Ruter proaktive notifikationer til bedste enhed + eskalerer ved manglende ack.

Erstatter push_dispatcher's blanket-blast. Tom presence → fallback til blast (mister
aldrig et signal). Eskalering via per-pending threading.Timer; ack annullerer."""
from __future__ import annotations

import logging
import threading
from uuid import uuid4

import core.services.device_presence as device_presence

logger = logging.getLogger(__name__)

_ESCALATE_S = 180.0
_lock = threading.Lock()
_PENDING: dict[str, dict] = {}   # notif_id -> {user_id, payload, kind, remaining, timer}


def reset() -> None:
    with _lock:
        for p in _PENDING.values():
            t = p.get("timer")
            if t:
                t.cancel()
        _PENDING.clear()


def _new_id() -> str:
    return f"notif-{uuid4().hex}"


def _send_fcm(user_id: str, device_key: str, data: dict) -> None:
    from core.services import push_dispatcher as pd
    pd._fcm_send(device_key, data)  # device_key == FCM-token for mobil


def _send_desktop(user_id: str, item: dict) -> None:
    from core.services import desktop_notifications as dn
    dn.enqueue(user_id, item)


def _fallback_blast(user_id: str, data: dict) -> None:
    from core.services import push_dispatcher as pd
    pd._push_to_user(user_id, data)


def _deliver(user_id: str, target, notif_id: str, payload: dict) -> None:
    if target.reachable_via == "desktop_queue":
        _send_desktop(user_id, {
            "notif_id": notif_id,
            "kind": payload.get("kind", ""),
            "title": payload.get("title", "Jarvis"),
            "body": payload.get("preview", "") or payload.get("body", ""),
            "session_id": payload.get("session_id", ""),
        })
    else:
        _send_fcm(user_id, target.device_key, {**payload, "notif_id": notif_id})


def _arm_timer(notif_id: str) -> None:
    t = threading.Timer(_ESCALATE_S, _escalate, args=(notif_id,))
    t.daemon = True
    with _lock:
        if notif_id in _PENDING:
            _PENDING[notif_id]["timer"] = t
    t.start()


def route(user_id: str, payload: dict, kind: str) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    ranked = device_presence.rank(uid)
    logger.warning(
        "proactive_router.route: kind=%s rank=%s",
        kind, [(r.platform, round(r.score, 1), r.reachable_via) for r in ranked],
    )
    if not ranked:
        logger.warning("proactive_router.route: tom rank -> fallback FCM-blast")
        _fallback_blast(uid, payload)
        return
    # If best score is 0.0 there's no real presence — treat like empty rank
    # and blast via FCM so the notification actually reaches a device.
    if ranked[0].score <= 0.0:
        logger.warning("proactive_router.route: bedste score %.1f <= 0 -> fallback FCM-blast",
                        ranked[0].score)
        _fallback_blast(uid, payload)
        return
    notif_id = _new_id()
    with _lock:
        _PENDING[notif_id] = {
            "user_id": uid, "payload": payload, "kind": kind,
            "remaining": ranked[1:], "timer": None,
        }
    logger.warning("proactive_router.route: leverer %s til %s/%s",
                notif_id[:12], ranked[0].platform, ranked[0].reachable_via)
    _deliver(uid, ranked[0], notif_id, payload)
    _arm_timer(notif_id)


def _escalate(notif_id: str) -> None:
    with _lock:
        p = _PENDING.get(notif_id)
        if not p or not p["remaining"]:
            _PENDING.pop(notif_id, None)
            return
        nxt = p["remaining"].pop(0)
        uid, payload = p["user_id"], p["payload"]
    _deliver(uid, nxt, notif_id, payload)
    _arm_timer(notif_id)


def ack(notif_id: str) -> None:
    with _lock:
        p = _PENDING.pop(notif_id, None)
        if p and p.get("timer"):
            p["timer"].cancel()
