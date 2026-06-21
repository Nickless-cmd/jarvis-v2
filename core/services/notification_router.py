"""Unified proactive notification routing (spec docs/specs/2026-06-20-...).

ÉT indgangspunkt — `route_proactive_notification()` — som ALLE proaktive kilder
(morgenbriefing, reminders, reach_out, team-invites, wakeups) kalder i stedet for
hver sin hardcodede sti. Lag-ansvar:

  notification_router  =  POLICY  (per-bruger-præference, quiet hours, kanal-resolve,
                                    fallback) — DETTE modul
  proactive_router / push_dispatcher / gateways  =  MEKANIK (faktisk levering)

Kanalværdier: auto | mobile | desktop | push | discord | telegram.
(Phase 5 inliner proactive_router's leverings-mekanik herind og fjerner det.)
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
            import core.services.proactive_router as pr
            pr.route(uid, payload, kind)  # device-aware (bruger udvidet rank())
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
