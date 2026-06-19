"""Per-bruger in-memory kø af proaktive desktop-notifikationer. Desktop poller
GET /notifications/pending → drain. Efemær; TTL-prune for udrainede items."""
from __future__ import annotations

import threading
import time

_now = time.monotonic
_DESKTOP_NOTIF_TTL_S = 300.0

_lock = threading.Lock()
_QUEUE: dict[str, list[dict]] = {}


def reset() -> None:
    with _lock:
        _QUEUE.clear()


def enqueue(user_id: str, item: dict) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    rec = dict(item)
    rec["_ts"] = _now()
    with _lock:
        _QUEUE.setdefault(uid, []).append(rec)


def drain(user_id: str) -> list[dict]:
    uid = (user_id or "").strip()
    with _lock:
        items = _QUEUE.pop(uid, [])
    return [{k: v for k, v in it.items() if k != "_ts"} for it in items]


def prune() -> None:
    now = _now()
    with _lock:
        for uid in list(_QUEUE.keys()):
            kept = [it for it in _QUEUE[uid] if (now - it.get("_ts", now)) <= _DESKTOP_NOTIF_TTL_S]
            if kept:
                _QUEUE[uid] = kept
            else:
                _QUEUE.pop(uid, None)
