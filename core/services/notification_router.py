"""Unified proactive notification routing (spec docs/specs/2026-06-20-...).

ÉT indgangspunkt — `route_proactive_notification()` — som ALLE proaktive kilder
(morgenbriefing, reminders, reach_out, team-invites, wakeups) kalder i stedet for
hver sin hardcodede sti. Lag-ansvar:

  notification_router  =  POLICY (per-bruger-præference, quiet hours, kanal-resolve,
                           fallback) + MEKANIK (device-aware levering + eskalering,
                           inlined fra det tidligere proactive_router i Phase 5)
  push_dispatcher / desktop_notifications / gateways  =  lavniveau-transport

Kanalværdier: auto | mobile | desktop | push | discord | telegram.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from core.runtime.db import connect

_log = logging.getLogger(__name__)

VALID_CHANNELS = {"auto", "mobile", "desktop", "push", "discord", "telegram"}
# Kolonner i notification_preferences der er per-type-overrides:
_TYPE_KEYS = ("briefing", "reminder", "reach_out", "team_invite", "wakeup")
_PREF_KEYS = ("global", *_TYPE_KEYS, "quiet_start", "quiet_end")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Preferences CRUD ───────────────────────────────────────────────────────────
def get_preferences(user_id: str) -> dict:
    """Returnér brugerens præferencer (defaults hvis ingen række)."""
    uid = (user_id or "").strip()
    with connect() as conn:
        r = conn.execute(
            "SELECT pref_global, briefing, reminder, reach_out, team_invite, wakeup, "
            "quiet_start, quiet_end FROM notification_preferences WHERE user_id = ?",
            (uid,),
        ).fetchone()
    if not r:
        return {"global": "auto", "briefing": None, "reminder": None, "reach_out": None,
                "team_invite": None, "wakeup": None, "quiet_start": "23:00", "quiet_end": "07:00"}
    return {"global": r[0], "briefing": r[1], "reminder": r[2], "reach_out": r[3],
            "team_invite": r[4], "wakeup": r[5], "quiet_start": r[6], "quiet_end": r[7]}


def set_preferences(user_id: str, **kwargs) -> dict:
    """Upsert. Kun kendte nøgler ('global' + per-type + quiet_start/end). Validerer
    kanalværdier. Returnerer den nye fulde præference."""
    uid = (user_id or "").strip()
    cur = get_preferences(uid)
    for k in _PREF_KEYS:
        if k in kwargs and kwargs[k] is not None:
            v = str(kwargs[k]).strip()
            if k in ("global", *_TYPE_KEYS) and v and v not in VALID_CHANNELS:
                raise ValueError(f"ugyldig kanal '{v}' for '{k}' (skal være {sorted(VALID_CHANNELS)})")
            cur[k] = v
    with connect() as conn:
        conn.execute(
            "INSERT INTO notification_preferences "
            "(user_id, pref_global, briefing, reminder, reach_out, team_invite, wakeup, "
            " quiet_start, quiet_end, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET pref_global=excluded.pref_global, "
            "briefing=excluded.briefing, reminder=excluded.reminder, reach_out=excluded.reach_out, "
            "team_invite=excluded.team_invite, wakeup=excluded.wakeup, "
            "quiet_start=excluded.quiet_start, quiet_end=excluded.quiet_end, "
            "updated_at=excluded.updated_at",
            (uid, cur["global"], cur["briefing"], cur["reminder"], cur["reach_out"],
             cur["team_invite"], cur["wakeup"], cur["quiet_start"], cur["quiet_end"], _now_iso()),
        )
    return cur


# ── Pure policy-logik (let at teste) ───────────────────────────────────────────
def resolve_channel(prefs: dict, notification_type: str) -> str:
    """Prioritet: type-specifik override → global → 'auto'."""
    t = (notification_type or "").strip()
    if t in _TYPE_KEYS and prefs.get(t):
        return prefs[t]
    return prefs.get("global") or "auto"


def is_quiet_hours(prefs: dict, now_hm: str | None = None) -> bool:
    """Er vi i quiet hours? now_hm = 'HH:MM' (server-lokal hvis None). Håndterer
    midnats-wrap (fx 23:00–07:00). start==end → ingen quiet hours."""
    start = (prefs.get("quiet_start") or "23:00").strip()
    end = (prefs.get("quiet_end") or "07:00").strip()
    if start == end:
        return False
    now = now_hm or datetime.now().strftime("%H:%M")
    if start < end:
        return start <= now < end
    return now >= start or now < end  # wrapper over midnat


# ── Quiet-hours-kø ─────────────────────────────────────────────────────────────
def _enqueue_delayed(user_id: str, ntype: str, payload: dict, importance: str, deliver_after_hm: str) -> None:
    """Gem en notifikation til levering efter quiet_end. deliver_after_hm = 'HH:MM'."""
    with connect() as conn:
        conn.execute(
            "INSERT INTO delayed_notifications "
            "(user_id, notif_type, payload_json, importance, deliver_after, created_at, delivered) "
            "VALUES (?,?,?,?,?,?,0)",
            (user_id, ntype, json.dumps(payload, ensure_ascii=False), importance,
             deliver_after_hm, _now_iso()),
        )


def fire_due_delayed(now_hm: str | None = None) -> int:
    """Lever forfaldne udskudte notifikationer (kaldes af scheduler). Returnerer antal."""
    now = now_hm or datetime.now().strftime("%H:%M")
    fired = 0
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, user_id, notif_type, payload_json, importance FROM delayed_notifications "
            "WHERE delivered = 0",
        ).fetchall()
    for rid, uid, ntype, pj, imp in rows:
        # Quiet hours er overstået når now >= deliver_after ELLER vi er ude af vinduet.
        try:
            payload = json.loads(pj)
        except Exception:
            payload = {}
        prefs = get_preferences(uid)
        if is_quiet_hours(prefs, now):
            continue  # stadig stille — vent
        if str(ntype).startswith("msg:"):
            deliver_message(uid, payload.get("body") or "", ntype[4:], importance=imp)
        else:
            route_proactive_notification(uid, ntype, payload, importance=imp, _skip_quiet=True)
        with connect() as conn:
            conn.execute("UPDATE delayed_notifications SET delivered = 1 WHERE id = ?", (rid,))
        fired += 1
    return fired


# ── Levering (mekanik — delegerer til eksisterende primitiver) ─────────────────
def _deliver_ntfy(payload: dict) -> bool:
    try:
        from core.services.ntfy_gateway import send_notification
        send_notification(payload.get("preview") or payload.get("body") or "Jarvis",
                          title=payload.get("title"))
        return True
    except Exception:
        return False


def _deliver_to_channel(uid: str, channel: str, payload: dict, ntype: str) -> bool:
    """Lever til én konkret kanal. Returnerer True ved succes."""
    kind = payload.get("kind") or ntype
    try:
        if channel in ("auto",):
            route_device_aware(uid, payload, kind)  # inlined device-aware (Phase 5)
            return True
        if channel in ("mobile", "push"):
            from core.services import push_dispatcher as pd
            pd._push_to_user(uid, {**payload, "kind": kind})
            return True
        if channel == "desktop":
            from core.services import desktop_notifications as dn
            dn.enqueue(uid, {"kind": kind, "title": payload.get("title", "Jarvis"),
                             "body": payload.get("preview") or payload.get("body", ""),
                             "session_id": payload.get("session_id", "")})
            return True
        if channel == "discord":
            from core.services.discord_gateway import send_dm_to_user
            r = send_dm_to_user(uid, payload.get("preview") or payload.get("body") or "Jarvis")
            return bool(isinstance(r, dict) and r.get("ok", True))
        if channel == "telegram":
            from core.services.telegram_gateway import send_message  # type: ignore
            return bool(send_message(uid, payload.get("preview") or payload.get("body") or "Jarvis"))
    except Exception as e:
        _log.warning("notification_router: levering til %s fejlede: %s", channel, e)
    return False


def route_proactive_notification(
    user_id: str,
    notification_type: str,
    payload: dict,
    importance: str = "normal",
    *,
    _skip_quiet: bool = False,
) -> dict:
    """Samlet routing for alle proaktive notifikationer.

    Returnerer {delivered, channel, target, fallback_used}.
    importance: low | normal | high | critical (critical omgår quiet hours).
    """
    uid = (user_id or "").strip()
    if not uid:
        return {"delivered": False, "channel": "none", "target": "", "fallback_used": False}
    prefs = get_preferences(uid)
    channel = resolve_channel(prefs, notification_type)

    # Quiet hours (kø, medmindre critical eller allerede afkøet)
    if not _skip_quiet and importance != "critical" and is_quiet_hours(prefs):
        _enqueue_delayed(uid, notification_type, payload, importance, prefs.get("quiet_end") or "07:00")
        return {"delivered": False, "channel": "queued", "target": uid, "fallback_used": False}

    # Primær levering
    if _deliver_to_channel(uid, channel, payload, notification_type):
        return {"delivered": True, "channel": channel, "target": uid, "fallback_used": False}

    # Fallback: prøv device-aware auto, så ntfy som sidste udvej
    if channel != "auto" and _deliver_to_channel(uid, "auto", payload, notification_type):
        return {"delivered": True, "channel": "auto", "target": uid, "fallback_used": True}
    if _deliver_ntfy(payload):
        return {"delivered": True, "channel": "ntfy", "target": uid, "fallback_used": True}
    return {"delivered": False, "channel": "failed", "target": uid, "fallback_used": True}


# ── Device-aware levering + eskalering (inlined fra proactive_router, Phase 5) ──
# Den "auto"-kanal: ranger brugerens enheder, lever til den bedste, og eskalér til
# næste hvis ingen ack inden _ESCALATE_S. Tom/0-rank → FCM-blast (mister aldrig et
# signal). ack(notif_id) annullerer eskalering.
import threading as _threading  # noqa: E402
from uuid import uuid4 as _uuid4  # noqa: E402
import core.services.device_presence as _device_presence  # noqa: E402

_ESCALATE_S = 180.0
_deliv_lock = _threading.Lock()
_PENDING: dict[str, dict] = {}   # notif_id -> {user_id, payload, kind, remaining, timer}


def reset_delivery() -> None:
    with _deliv_lock:
        for p in _PENDING.values():
            t = p.get("timer")
            if t:
                t.cancel()
        _PENDING.clear()


def _new_id() -> str:
    return f"notif-{_uuid4().hex}"


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
    t = _threading.Timer(_ESCALATE_S, _escalate, args=(notif_id,))
    t.daemon = True
    with _deliv_lock:
        if notif_id in _PENDING:
            _PENDING[notif_id]["timer"] = t
    t.start()


def route_device_aware(user_id: str, payload: dict, kind: str) -> None:
    """Lever en notifikation til brugerens bedste enhed + arm eskalering."""
    uid = (user_id or "").strip()
    if not uid:
        return
    ranked = _device_presence.rank(uid)
    _log.warning("notification_router.route_device_aware: kind=%s rank=%s",
                 kind, [(r.platform, round(r.score, 1), r.reachable_via) for r in ranked])
    if not ranked:
        _log.warning("notification_router: tom rank -> fallback FCM-blast")
        _fallback_blast(uid, payload)
        return
    if ranked[0].score <= 0.0:
        _log.warning("notification_router: bedste score %.1f <= 0 -> fallback FCM-blast",
                     ranked[0].score)
        _fallback_blast(uid, payload)
        return
    notif_id = _new_id()
    with _deliv_lock:
        _PENDING[notif_id] = {"user_id": uid, "payload": payload, "kind": kind,
                              "remaining": ranked[1:], "timer": None}
    _deliver(uid, ranked[0], notif_id, payload)
    _arm_timer(notif_id)


def _escalate(notif_id: str) -> None:
    with _deliv_lock:
        p = _PENDING.get(notif_id)
        if not p or not p["remaining"]:
            _PENDING.pop(notif_id, None)
            return
        nxt = p["remaining"].pop(0)
        uid, payload = p["user_id"], p["payload"]
    _deliver(uid, nxt, notif_id, payload)
    _arm_timer(notif_id)


def ack(notif_id: str) -> None:
    """Annullér eskalering for en leveret notifikation (kaldt af /notifications/ack)."""
    with _deliv_lock:
        p = _PENDING.pop(notif_id, None)
        if p and p.get("timer"):
            p["timer"].cancel()


# ── Proaktiv INDHOLD-levering (morgenbriefing, reach_out) ──────────────────────
# Til forskel fra route_device_aware (korte notifikationer) leverer dette selve
# TEKSTEN dér hvor brugeren ser den: i app-samtalen (webchat, delt mobil↔desktop)
# hvis han er online på en app — ellers Discord — efter hans præference.
# Erstatter den hardcodede discord/webchat-hint i outreach_composer (Bjørn 2026-06-21).
def _discord_connected() -> bool:
    try:
        from core.services.discord_gateway import get_discord_status
        return bool(get_discord_status().get("connected"))
    except Exception:
        return False


def _app_device_live(uid: str) -> bool:
    """Er en app-enhed AKTIVT online (frisk ping), ikke bare en registreret token?"""
    try:
        for r in _device_presence.rank(uid):
            if r.score > _REGISTERED_FCM_SCORE:  # aktivt ping slår en bar registreret token
                return True
    except Exception:
        pass
    return False


def _deliver_content(uid: str, channel: str, text: str) -> dict:
    if channel in ("webchat", "mobile", "desktop"):
        ok = False
        try:
            from core.services.notification_bridge import send_session_notification
            ok = send_session_notification(text, source="notification-router").get("status") == "ok"
        except Exception:
            ok = False
        try:  # best-effort surface-notifikation så han kigger
            route_device_aware(uid, {"kind": "proactive", "preview": text[:120], "body": text})
        except Exception:
            pass
        return {"sent": ok, "channel": "webchat"}
    if channel == "discord":
        try:
            from core.services.discord_config import load_discord_config
            from core.services.discord_gateway import send_discord_message, get_discord_status
            cfg = load_discord_config() or {}
            if not get_discord_status().get("connected"):
                return {"sent": False, "channel": "discord", "reason": "not connected"}
            send_discord_message(int(cfg.get("default_user_id") or cfg.get("notify_user_id") or 0), text)
            return {"sent": True, "channel": "discord"}
        except Exception as e:
            return {"sent": False, "channel": "discord", "reason": str(e)}
    if channel in ("push", "telegram"):
        ok = _deliver_to_channel(uid, channel, {"body": text, "preview": text[:200]}, "reach_out")
        return {"sent": ok, "channel": channel}
    return {"sent": False, "channel": channel}


def deliver_message(user_id: str, text: str, ntype: str = "reach_out", importance: str = "normal") -> dict:
    """Lever proaktivt INDHOLD efter brugerens kanal-præference.

    auto = app hvis du er online der (mobil/desktop) → vises i samtalen; ellers
    Discord; ellers post i webchat-sessionen (ses næste gang app åbnes). Returnerer
    {sent, channel}."""
    uid = (user_id or "").strip()
    text = (text or "").strip()
    if not uid or not text:
        return {"sent": False, "channel": "none"}
    prefs = get_preferences(uid)
    channel = resolve_channel(prefs, ntype)
    if importance != "critical" and is_quiet_hours(prefs):
        _enqueue_delayed(uid, f"msg:{ntype}", {"body": text}, importance, prefs.get("quiet_end") or "07:00")
        return {"sent": False, "channel": "queued"}
    if channel == "auto":
        if _app_device_live(uid):
            channel = "webchat"
        elif _discord_connected():
            channel = "discord"
        else:
            channel = "webchat"
    return _deliver_content(uid, channel, text)
