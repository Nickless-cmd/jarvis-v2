# core/services/proactivity_bridge.py
"""Proaktivitets-broen — samler Jarvis' indre spørgsmål/initiativer/undren og overflader dem til
Bjørn gennem en presence-bevidst contact-gate + delte caps. Hybrid: urgent-item straks, ellers
'mens du var væk'-digest, ellers observe-suppressed (synlig, ikke sendt). Live-governed via
kill-switch; fail-closed for afsendelse. Self-safe — kaster aldrig i cadence-hot-path."""
from __future__ import annotations

from typing import Any

_DIGEST_MAX = 5           # højst så mange normale items i én digest
_PRESENT_WINDOW_S = 900   # owner regnes "til stede" hvis synlig < 15 min siden
_AWAY_MIN_S = 3600        # digest kræver ≥1t fravær (urgent kræver ikke)
_URGENT_PRIORITIES = {"high", "critical"}
_URGENT_KINDS = {"critical_impulse"}


def classify(candidate: dict[str, Any]) -> str:
    """'urgent' hvis høj/kritisk prioritet eller kritisk kind; ellers 'normal'. Ren."""
    if str(candidate.get("priority") or "").lower() in _URGENT_PRIORITIES:
        return "urgent"
    if str(candidate.get("kind") or "") in _URGENT_KINDS:
        return "urgent"
    return "normal"


def select(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Dedup på source_id, split i urgent/normal, sortér (urgent først/friskest), cap normal-listen."""
    seen: set[str] = set()
    urgent: list[dict[str, Any]] = []
    normal: list[dict[str, Any]] = []
    for c in candidates or []:
        sid = str(c.get("source_id") or "")
        if sid and sid in seen:
            continue
        if sid:
            seen.add(sid)
        (urgent if classify(c) == "urgent" else normal).append(c)
    normal.sort(key=lambda c: str(c.get("ts") or ""), reverse=True)
    return {"urgent": urgent, "normal": normal[:_DIGEST_MAX]}


def should_reach_owner(*, owner_present: bool, is_quiet: bool, sent_today: int, cap: int,
                       within_cooldown: bool, urgent: bool) -> tuple[bool, str]:
    """Ren contact-gate (kalderen injicerer signalerne). Rækkefølge = spam-værn:
    owner til stede → aldrig afbryd; quiet-hours blokerer normal (urgent må bryde); daily-cap;
    cooldown. Returnér (ok, reason) — reason bruges til observe ved suppression."""
    if owner_present:
        return (False, "owner_present")
    if is_quiet and not urgent:
        return (False, "quiet_hours")
    if sent_today >= cap:
        return (False, "daily_cap")
    if within_cooldown:
        return (False, "cooldown")
    return (True, "ok")


def build_urgent(item: dict[str, Any]) -> str:
    """Enkelt-item besked (urgent-gren)."""
    text = str(item.get("text") or "").strip()
    kind = str(item.get("kind") or "note")
    return f"💭 Jarvis ({kind}): {text}"


def build_digest(normal: list[dict[str, Any]]) -> str:
    """'Mens du var væk'-digest af normale items (kort, prioriteret)."""
    lines = ["💭 Mens du var væk tænkte jeg på:"]
    for c in (normal or [])[:_DIGEST_MAX]:
        text = str(c.get("text") or "").strip()
        if text:
            lines.append(f"  • {text}")
    return "\n".join(lines)


# ── I/O layer ────────────────────────────────────────────────────────────
import logging as _logging
from datetime import UTC, datetime

logger = _logging.getLogger(__name__)
_KILL_SCOPE, _KILL_NAME = "autonomy", "proactivity_bridge"   # central_switches kill-switch


def _owner_uid() -> str:
    try:
        from core.runtime.settings import load_settings
        return str(load_settings().extra.get("owner_user_id") or "").strip()
    except Exception:
        return ""


def _owner_presence(uid: str) -> tuple[bool, float]:
    """(present, away_seconds) fra ÆGTE owner-signaler — IKKE runs (som inkluderer autonome →
    den gamle outreach-bug). present = owner's app-enhed pinger aktivt. away = tid siden owner's
    SIDSTE user-turn-besked (role='user' i chat_messages — ikke assistant/tool/autonom)."""
    now = datetime.now(UTC)
    try:
        from core.services.notification_router import _app_device_live
        if uid and _app_device_live(uid):
            return (True, 0.0)
    except Exception:
        pass
    last_seen = None
    try:
        from core.runtime.db import connect
        with connect() as conn:
            row = conn.execute("SELECT MAX(created_at) AS t FROM chat_messages WHERE role='user'").fetchone()
        ts = row["t"] if row else None
        if ts:
            last_seen = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=UTC)
    except Exception:
        last_seen = None
    if last_seen is None:
        return (False, float(_AWAY_MIN_S * 2))       # ukendt → antag væk (cooldown+cap værner mod spam)
    away = max(0.0, (now - last_seen).total_seconds())
    return (away < _PRESENT_WINDOW_S, away)


def collect_candidates() -> list[dict[str, Any]]:
    """Læs de EKSISTERENDE kilder (egress-frit, skriver intet). Self-safe → []."""
    out: list[dict[str, Any]] = []
    try:
        from core.services.initiative_queue import get_pending_initiatives
        for it in get_pending_initiatives() or []:
            out.append({"kind": "initiative", "text": str(it.get("focus") or "").strip(),
                        "priority": str(it.get("priority") or "medium"),
                        "source": "initiative_queue", "source_id": str(it.get("initiative_id") or ""),
                        "ts": str(it.get("detected_at") or "")})
    except Exception:
        pass
    try:
        from core.services.existential_wonder_daemon import get_latest_wonder
        w = (get_latest_wonder() or "").strip()
        if w:
            out.append({"kind": "wonder", "text": w, "priority": "medium",
                        "source": "existential_wonder", "source_id": f"wonder:{hash(w) & 0xffff}",
                        "ts": datetime.now(UTC).isoformat()})
    except Exception:
        pass
    return [c for c in out if c.get("text")]


def _route(uid: str, text: str, importance: str) -> dict[str, Any]:
    """Send direkte via den eksisterende notifikations-router (springer nudge-brønden over — broen
    ER beslutnings-laget) og LOG i action_routers delte cap-ledger. Self-safe."""
    from core.services.notification_router import route_proactive_notification
    res = route_proactive_notification(uid, "reach_out", {"preview": text, "body": text}, importance)
    try:
        from core.services.action_router import _append_proactive
        _append_proactive({"at": datetime.now(UTC).isoformat(), "outcome": "sent",
                           "reason": "proactivity_bridge", "channel": str(res.get("channel") or ""),
                           "message": text[:240], "importance": importance, "source": "proactivity_bridge"})
    except Exception:
        pass
    return res


def _observe(nerve: str, meta: dict[str, Any]) -> None:
    try:
        from core.services.central_core import central
        central().observe({"cluster": "proactivity", "nerve": nerve, **meta})
    except Exception:
        pass


def run_proactivity_bridge_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence run_fn. Hybrid: urgent straks / ellers digest / ellers observe suppressed.
    Fail-CLOSED for afsendelse (kill-switch-fejl → suppress). Self-safe."""
    try:
        from core.services import central_switches
        enabled = central_switches.is_enabled(_KILL_SCOPE, _KILL_NAME)
    except Exception:
        _observe("bridge_suppressed", {"reason": "switch_read_error"})
        return {"status": "ok", "action": "suppressed", "reason": "switch_read_error"}
    if not enabled:
        _observe("bridge_suppressed", {"reason": "disabled"})
        return {"status": "ok", "action": "suppressed", "reason": "disabled"}
    try:
        uid = _owner_uid()
        if not uid:
            _observe("bridge_suppressed", {"reason": "no_owner_uid"})
            return {"status": "ok", "action": "suppressed", "reason": "no_owner_uid"}
        sel = select(collect_candidates())
        if not sel["urgent"] and not sel["normal"]:
            _observe("bridge_suppressed", {"reason": "no_candidates"})
            return {"status": "ok", "action": "suppressed", "reason": "no_candidates"}
        present, away = _owner_presence(uid)
        from core.services.action_router import (_proactive_messages_today, _within_cooldown,
                                                 _max_proactive_per_day)
        sent_today, cap, cooldown = _proactive_messages_today(), _max_proactive_per_day(), _within_cooldown()
        try:
            from core.services.notification_router import is_quiet_hours, get_preferences
            is_quiet = is_quiet_hours(get_preferences(uid))
        except Exception:
            is_quiet = False
        if sel["urgent"]:
            ok, reason = should_reach_owner(owner_present=present, is_quiet=is_quiet, sent_today=sent_today,
                                            cap=cap, within_cooldown=cooldown, urgent=True)
            if ok:
                item = sel["urgent"][0]
                res = _route(uid, build_urgent(item), "high")
                _observe("bridge_surfaced", {"kind": "urgent", "delivered": bool(res.get("delivered")),
                                             "source_id": item.get("source_id")})
                return {"status": "ok", "action": "surfaced_urgent"}
            _observe("bridge_suppressed", {"reason": reason, "branch": "urgent"})
        if sel["normal"] and away >= _AWAY_MIN_S:
            ok, reason = should_reach_owner(owner_present=present, is_quiet=is_quiet, sent_today=sent_today,
                                            cap=cap, within_cooldown=cooldown, urgent=False)
            if ok:
                res = _route(uid, build_digest(sel["normal"]), "normal")
                _observe("bridge_surfaced", {"kind": "digest", "n": len(sel["normal"]),
                                             "delivered": bool(res.get("delivered"))})
                return {"status": "ok", "action": "surfaced_digest"}
            _observe("bridge_suppressed", {"reason": reason, "branch": "digest"})
            return {"status": "ok", "action": "suppressed", "reason": reason}
        _observe("bridge_suppressed", {"reason": "not_away_enough" if sel["normal"] else "urgent_gated",
                                       "away_s": int(away)})
        return {"status": "ok", "action": "suppressed"}
    except Exception as exc:
        logger.debug("proactivity_bridge tick failed: %s", exc)
        _observe("bridge_error", {"error": str(exc)[:160]})
        return {"status": "error"}


def register_proactivity_bridge_producer() -> None:
    """Registrér broen som cadence-producer (~10 min, visible_grace 15 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(name="proactivity_bridge", cooldown_minutes=10,
                                   visible_grace_minutes=15, run_fn=run_proactivity_bridge_tick, priority=12))


def build_proactivity_bridge_surface() -> dict[str, Any]:
    """Read-only surface til /central/proactivity + jc. Self-safe."""
    try:
        from core.services import central_switches
        enabled = central_switches.is_enabled(_KILL_SCOPE, _KILL_NAME)
    except Exception:
        enabled = None
    try:
        sel = select(collect_candidates())
        return {"status": "ok", "enabled": enabled,
                "pending_urgent": len(sel["urgent"]), "pending_normal": len(sel["normal"]),
                "candidates": (sel["urgent"] + sel["normal"])[:8]}
    except Exception:
        return {"status": "unavailable", "enabled": enabled}
