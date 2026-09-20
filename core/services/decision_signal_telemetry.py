"""Decision-signal telemetry — track whether decision signals get heeded.

Parallel to verification_gate_telemetry. Decision signals fire when a
behavioral decision wants Jarvis to take action (loop_nudge_5_rounds,
backend_unresolved_3_calls, etc.). We've been recording the FIRES (289
since 7. May) but never tracked whether the model actually responded.

Same architectural pattern as r2-telemetry (DB-polling listener, atomic
state-file persistence):

1. **Surfaces** — every ``decision_signal.fired`` event recorded with
   timestamp + decision_id + trigger_name + session_id.

2. **Reactions** — DB-poller watches for ``tool.completed`` events
   within ``_REACTION_WINDOW_SECONDS`` after a surface. Any tool call
   counts as "Jarvis did something in response" → heeded.

3. **Sweep** — surfaces still unresolved after window+grace → ignored.

Heed proxy is intentionally broad: any tool call counts. We can't tell
from telemetry alone whether the call was the RIGHT action for that
decision, but we CAN tell whether the model engaged or ignored. That's
the same standard verification_gate_telemetry uses.

Promotion path mirrors R2 → R2.5: when heed-rate stays low over a
meaningful window AND signals keep firing, we have data to make the
signals more visible or blocking.

Retention (20/9-2026): the measuring window is a *time*
(``_RETENTION_DAYS``), not a record count. A count moves with activity —
500 records covered 79 days at ~6.3/day, but would have covered 1 day at
500/day, and the number would have looked just as right.

Added 2026-05-14.
"""
from __future__ import annotations

import json as _json
import logging
import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from core.runtime.state_store import load_json, save_json

logger = logging.getLogger(__name__)


_TELEMETRY_KEY = "decision_signal_telemetry"
_REACTION_WINDOW_SECONDS = 90
_GRACE_SECONDS = 30
#: Fast målevindue. Horisonten skal være en *tid*, ikke et *antal*: et antal
#: flytter målevinduet når aktiviteten gør. Målt 20/9-2026 dækkede de 500 poster
#: 79 døgn (3/7 → 20/9, ~6,3/døgn) — ved 500/døgn ville «7d» reelt være 1 døgn,
#: og tallet ville se lige så rigtigt ud.
#:
#: Bevidst længere end søstermodulet `verification_gate_telemetry` (30 dage).
#: Modulet beskriver selv sin pointe som et *langt* forløb («289 fires siden
#: 7. maj»), og ved ~6,3/døgn koster et kvartal kun ~570 poster. Et 30-dages
#: vindue ville kaste 49 døgn af den eneste langtidshistorik vi har, uden at
#: vinde noget: filen er 238 KB ved 500 poster.
_RETENTION_DAYS = 90
#: Sikkerhedsnet mod vækst, IKKE den effektive horisont. Ved ~6,3 poster/døgn
#: binder loftet først ved ~222/døgn — aldersvinduet rammer længe før.
_MAX_RECORDS = 20000
_POLL_INTERVAL_SECONDS = 5.0


def _load() -> dict[str, Any]:
    try:
        data = load_json(_TELEMETRY_KEY, {}) or {}
        if not isinstance(data, dict):
            return {}
        data.setdefault("surfaces", [])
        data.setdefault("reactions", [])
        return data
    except Exception:
        return {"surfaces": [], "reactions": []}


def _save(data: dict[str, Any]) -> None:
    try:
        # Beskaering der TAELLER, paa et fast tidsvindue.
        #
        # Foer stod her `list(...)[-_MAX_RECORDS:]`. 13/9-2026 fik tabet et tal
        # (`beskaer`), men loftet var stadig et *antal* — saa maalevinduet
        # flyttede sig naar aktiviteten gjorde. Maalt 20/9-2026: 500 poster
        # daekkede 79 doegn ved ~6,3/dogn; ved 500/dogn ville «7d» vaere 1
        # doegn, og tallet ville se lige saa rigtigt ud. Soestermodulet
        # `verification_gate_telemetry` fik samme rettelse samme dag.
        #
        # Fase 10, kriterium 2: «tolerate loss honestly». Ikke «undgaa tab» —
        # tab er i orden for telemetri, det er netop forskellen paa telemetri og
        # sandhed. Usynligt tab er ikke.
        try:
            from core.services.telemetry_gate import beskaer_efter_alder
            data["surfaces"] = beskaer_efter_alder(
                data.get("surfaces", []), _RETENTION_DAYS,
                navn="decision_signal_telemetry.surfaces", maks=_MAX_RECORDS)
            data["reactions"] = beskaer_efter_alder(
                data.get("reactions", []), _RETENTION_DAYS,
                navn="decision_signal_telemetry.reactions", maks=_MAX_RECORDS)
        except Exception:
            # Regnskabet maa aldrig koste os selve beskaeringen — en ring uden
            # loft ville vokse til den spiste state-filen.
            data["surfaces"] = list(data.get("surfaces", []))[-_MAX_RECORDS:]
            data["reactions"] = list(data.get("reactions", []))[-_MAX_RECORDS:]
        save_json(_TELEMETRY_KEY, data)
    except Exception as exc:
        logger.debug("decision_telemetry: persist failed: %s", exc)


_lock = threading.Lock()


def record_surface(
    *,
    decision_id: str,
    trigger_name: str,
    session_id: str = "",
    at: datetime | None = None,
) -> None:
    """Record a decision_signal.fired surface for later heed-tracking."""
    now = at or datetime.now(UTC)
    record = {
        "at": now.isoformat(),
        "decision_id": str(decision_id or ""),
        "trigger_name": str(trigger_name or ""),
        "session_id": str(session_id or ""),
        "resolved": False,
    }
    with _lock:
        data = _load()
        existing = data.get("surfaces", [])
        # Suppress duplicate within 5s for same (decision_id, session_id) —
        # decision_signals.evaluate may call multiple triggers per tick
        if existing:
            last = existing[-1]
            try:
                last_ts = datetime.fromisoformat(str(last.get("at", "")))
                if (
                    (now - last_ts).total_seconds() < 5
                    and last.get("decision_id") == record["decision_id"]
                    and last.get("session_id") == record["session_id"]
                ):
                    return
            except ValueError:
                pass
        existing.append(record)
        data["surfaces"] = existing
        _save(data)


def record_heed(
    *,
    tool: str,
    session_id: str = "",
    at: datetime | None = None,
) -> None:
    """Mark recent surfaces as heeded if they match the reaction window."""
    now = at or datetime.now(UTC)
    cutoff = now - timedelta(seconds=_REACTION_WINDOW_SECONDS)
    with _lock:
        data = _load()
        surfaces = data.get("surfaces", [])
        changed = False
        for s in reversed(surfaces):
            if s.get("resolved"):
                continue
            try:
                s_at = datetime.fromisoformat(str(s.get("at", "")))
            except ValueError:
                continue
            if s_at < cutoff:
                break
            # Match by session_id when present on both sides; otherwise
            # any tool call within the window counts (Jarvis took action).
            s_session = str(s.get("session_id") or "")
            if s_session and session_id and s_session != session_id:
                continue
            s["resolved"] = True
            s["heeded_by_tool"] = tool
            s["heeded_at"] = now.isoformat()
            changed = True
            data.setdefault("reactions", []).append({
                "at": now.isoformat(),
                "verdict": "heeded",
                "tool": tool,
                "surface_at": s.get("at"),
                "decision_id": s.get("decision_id"),
                "trigger_name": s.get("trigger_name"),
            })
            break  # resolve only the most recent unresolved surface
        if changed:
            _save(data)


def sweep_expired_surfaces() -> int:
    """Mark surfaces as ignored once they pass window+grace with no heed."""
    now = datetime.now(UTC)
    cutoff = now - timedelta(seconds=_REACTION_WINDOW_SECONDS + _GRACE_SECONDS)
    ignored = 0
    with _lock:
        data = _load()
        for s in data.get("surfaces", []):
            if s.get("resolved"):
                continue
            try:
                s_at = datetime.fromisoformat(str(s.get("at", "")))
            except ValueError:
                continue
            if s_at < cutoff:
                s["resolved"] = True
                s["ignored_at"] = now.isoformat()
                ignored += 1
                data.setdefault("reactions", []).append({
                    "at": now.isoformat(),
                    "verdict": "ignored",
                    "surface_at": s.get("at"),
                    "decision_id": s.get("decision_id"),
                    "trigger_name": s.get("trigger_name"),
                })
        if ignored:
            _save(data)
    return ignored


def get_telemetry_summary(*, hours: int = 24) -> dict[str, Any]:
    """Aggregate counts + heed-rate over the lookback window."""
    sweep_expired_surfaces()
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    data = _load()
    in_window = 0
    heeded = 0
    ignored = 0
    by_trigger: dict[str, dict[str, int]] = {}
    for s in data.get("surfaces", []):
        try:
            s_at = datetime.fromisoformat(str(s.get("at", "")))
        except ValueError:
            continue
        if s_at < cutoff:
            continue
        in_window += 1
        trig = str(s.get("trigger_name") or "unknown")
        by_trigger.setdefault(trig, {"surfaced": 0, "heeded": 0, "ignored": 0})
        by_trigger[trig]["surfaced"] += 1
        if s.get("heeded_by_tool"):
            heeded += 1
            by_trigger[trig]["heeded"] += 1
        elif s.get("ignored_at"):
            ignored += 1
            by_trigger[trig]["ignored"] += 1
    rate = round(heeded / in_window, 3) if in_window > 0 else None
    return {
        "window_hours": hours,
        "surfaced_total": in_window,
        "heeded_total": heeded,
        "ignored_total": ignored,
        "heed_rate": rate,
        "by_trigger": by_trigger,
    }


# ── DB-polling listener — same cross-process pattern as r2_telemetry ──


_subscribed = False


def _poll_db_for_events() -> None:
    """Poll events table for decision_signal.fired and tool.completed.

    Cross-process safe: SQLite events table is shared, so we see events
    emitted in any worker. Initializes cursor to current MAX(id) so we
    don't replay history.
    """
    import time as _time
    try:
        from core.runtime.db import connect
    except Exception:
        return

    last_id = 0
    try:
        with connect() as conn:
            row = conn.execute("SELECT COALESCE(MAX(id), 0) FROM events").fetchone()
            last_id = int(row[0] or 0) if row else 0
    except Exception as exc:
        logger.debug("decision_telemetry: cursor init failed: %s", exc)

    while True:
        _time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            with connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, kind, payload_json, created_at
                    FROM events
                    WHERE id > ?
                      AND kind IN ('decision_signal.fired', 'tool.completed')
                    ORDER BY id ASC
                    LIMIT 500
                    """,
                    (last_id,),
                ).fetchall()
            for row in rows:
                eid = int(row[0])
                last_id = max(last_id, eid)
                kind = str(row[1] or "")
                try:
                    payload = _json.loads(row[2] or "{}")
                except (ValueError, TypeError):
                    continue
                if not isinstance(payload, dict):
                    continue
                created_at_raw = str(row[3] or "")
                try:
                    event_at = datetime.fromisoformat(created_at_raw)
                except ValueError:
                    event_at = datetime.now(UTC)

                if kind == "decision_signal.fired":
                    record_surface(
                        decision_id=str(payload.get("decision_id") or ""),
                        trigger_name=str(payload.get("trigger_name") or ""),
                        session_id=str(payload.get("session_id") or ""),
                        at=event_at,
                    )
                elif kind == "tool.completed":
                    tool = str(payload.get("tool") or "")
                    status = str(payload.get("status") or "")
                    if status == "ok" and tool:
                        record_heed(tool=tool, at=event_at)
        except Exception as exc:
            logger.debug("decision_telemetry: poll cycle failed: %s", exc)
            continue


def subscribe() -> None:
    """Start the DB-polling telemetry listener. Idempotent per process."""
    global _subscribed
    if _subscribed:
        return
    _subscribed = True
    threading.Thread(
        target=_poll_db_for_events,
        name="decision-signal-telemetry-poll",
        daemon=True,
    ).start()


def telemetry_section() -> str | None:
    """Render telemetry as awareness section. Only when >= 5 surfaces/24h."""
    s = get_telemetry_summary(hours=24)
    if s.get("surfaced_total", 0) < 5:
        return None
    rate = s.get("heed_rate")
    rate_str = f"{int(rate * 100)}%" if rate is not None else "n/a"
    flag = ""
    if rate is not None and rate < 0.4:
        flag = " ⚠ under 40% — decisions firing but ignored"
    return (
        f"Decision-signal telemetry (24t): surfaced={s['surfaced_total']} "
        f"heeded={s['heeded_total']} ignored={s['ignored_total']} "
        f"heed_rate={rate_str}{flag}"
    )


def build_decision_signal_telemetry_surface() -> dict[str, object]:
    """MC surface — read-only meta-projection."""
    s = get_telemetry_summary(hours=24)
    return {
        "active": True,
        "mode": "decision_signal_telemetry",
        "summary": (
            f"24h: surfaced={s['surfaced_total']} heeded={s['heeded_total']} "
            f"ignored={s['ignored_total']} rate={s.get('heed_rate')}"
        ),
        "stats": s,
        "authority": "derived-read-only",
    }


def _emit_decision_signal_telemetry_event(
    kind: str, payload: dict[str, object] | None = None
) -> None:
    """Defensive scoped event emitter."""
    try:
        from core.eventbus.bus import event_bus
        event_bus.publish(f"decision_signal_telemetry.{kind}", payload or {})
    except Exception:
        pass
