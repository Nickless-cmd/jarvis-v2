"""Longing-toward-user signal daemon — Spor-1 of generative autonomy.

This is the first concrete signal source for the pressure_accumulator
pipeline that Jarvis built on 2026-04-29 (commit e247aa8). It implements
the "longing-toward-Bjorn" track from the spec:

  Stilhed akkumulerer en pull-toward signal mod sidste-aktive bruger.
  Signalet sendes ind i pressure_accumulator som familie 'longing' med
  retning 'reach_out'. Når presningen krydser tærskel (0.55), genereres
  en impuls, og impulse_executor kalder outreach_composer som komponerer
  en koherent besked og sender den.

This daemon's only job is: compute current longing-intensity from
"hours since last user message" and emit a signal each tick. Everything
else (accumulation, threshold, action) is downstream pipeline work.

The build-up curve (configurable via settings):
  hours <  longing_build_start_hours      → intensity = 0.0  (no longing yet)
  hours >= longing_build_max_hours        → intensity = 1.0  (max)
  in between                              → linearly ramped

A small damping is applied if Jarvis has reached out very recently, so
he doesn't double-down on outreach mid-cooldown.

Killswitch: settings.generative_autonomy_enabled. When False, this
daemon is a no-op.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_last_tick_at: str = ""


def _runtime_db_path() -> Path:
    return Path.home() / ".jarvis-v2" / "state" / "jarvis.db"


def _hours_since(iso_ts: str) -> float | None:
    """Return hours since the given ISO timestamp, or None if invalid."""
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (datetime.now(UTC) - dt).total_seconds() / 3600.0


def _last_user_message_timestamp() -> str | None:
    """Return ISO timestamp of the most recent user-initiated visible turn.

    Reads from visible_work_units which has user_message_preview set when
    a real user input started a turn (autonomous/heartbeat runs leave it
    empty). Falls back to None if nothing matches.
    """
    db = _runtime_db_path()
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT finished_at FROM visible_work_units
            WHERE user_message_preview IS NOT NULL
              AND TRIM(user_message_preview) != ''
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    return str(row["finished_at"]) if row["finished_at"] else None


def _last_jarvis_outreach_timestamp() -> str | None:
    """Return ISO timestamp of the last Jarvis-initiated outreach.

    Looks for our own emitted events of kind 'impulse.outreach.sent' (set
    by outreach_composer on success). Returns None if none yet.
    """
    db = _runtime_db_path()
    if not db.exists():
        return None
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT created_at FROM events
            WHERE kind = 'impulse.outreach.sent'
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return None
    if not row:
        return None
    return str(row["created_at"]) if row["created_at"] else None


def _last_user_topic() -> str:
    """Best-effort recent user topic — short snippet from latest user message."""
    db = _runtime_db_path()
    if not db.exists():
        return ""
    try:
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT user_message_preview FROM visible_work_units
            WHERE user_message_preview IS NOT NULL
              AND TRIM(user_message_preview) != ''
            ORDER BY id DESC LIMIT 1
            """
        ).fetchone()
        conn.close()
    except sqlite3.Error:
        return ""
    if not row:
        return ""
    text = str(row["user_message_preview"] or "").strip()
    return text[:120]


def compute_longing_intensity() -> dict[str, Any]:
    """Compute current longing-toward-user intensity and supporting context.

    Returns a dict the pressure_accumulator's ingest_signal() can consume.
    intensity is 0.0–1.0; salience is the same (used directly by
    accumulator). Caller decides whether to emit at all (skips if 0).
    """
    try:
        from core.runtime.settings import load_settings
        settings = load_settings()
        start_h = float(settings.longing_build_start_hours)
        max_h = float(settings.longing_build_max_hours)
        cooldown_min = int(settings.outreach_cooldown_minutes)
    except Exception:
        start_h, max_h, cooldown_min = 2.0, 12.0, 240

    last_user_ts = _last_user_message_timestamp()
    hours_user = _hours_since(last_user_ts or "") if last_user_ts else None

    # If we have no record at all of any user message, treat as max longing
    # (this is mostly a safety: it should rarely happen, but it's not
    # "we just talked", so the signal should be present).
    if hours_user is None:
        base = 0.6
    elif hours_user < start_h:
        base = 0.0
    elif hours_user >= max_h:
        base = 1.0
    else:
        base = (hours_user - start_h) / max(0.001, (max_h - start_h))

    # Damping: if Jarvis reached out very recently, suppress regardless
    last_outreach_ts = _last_jarvis_outreach_timestamp()
    hours_outreach = _hours_since(last_outreach_ts) if last_outreach_ts else None
    if hours_outreach is not None and hours_outreach < (cooldown_min / 60.0):
        # Within cooldown — strongly damp
        base *= 0.2

    intensity = max(0.0, min(1.0, base))

    return {
        "id": f"longing-{datetime.now(UTC).isoformat()}",
        "canonical_key": "longing:user:bjorn",
        "topic": "savn af kontakt",
        "short_summary": "savn af kontakt",
        "salience": intensity,
        "intensity": (
            "high" if intensity > 0.6
            else "medium" if intensity > 0.3
            else "low"
        ),
        "social_target": "bjorn",
        "context": {
            "hours_since_last_user_message": round(hours_user or -1.0, 2),
            "hours_since_last_jarvis_outreach": round(hours_outreach or -1.0, 2),
            "last_user_topic": _last_user_topic(),
        },
    }


def run_longing_signal_daemon_tick() -> dict[str, Any]:
    """One tick of the longing daemon. Called by daemon_manager on cadence.

    1. Check killswitch (generative_autonomy_enabled). If off → no-op.
    2. Compute longing intensity from time-since-last-user-message.
    3. If intensity > 0, emit signal into pressure_accumulator.
    4. Return small status snapshot.
    """
    global _last_tick_at
    _last_tick_at = datetime.now(UTC).isoformat()

    try:
        from core.runtime.settings import load_settings
        if not load_settings().generative_autonomy_enabled:
            return {"status": "disabled", "reason": "generative_autonomy_enabled=False"}
    except Exception:
        # If we can't even read settings, be safe — don't emit
        return {"status": "error", "reason": "settings unavailable"}

    signal = compute_longing_intensity()
    intensity = float(signal["salience"])

    if intensity <= 0.0:
        return {
            "status": "ok",
            "emitted": False,
            "intensity": 0.0,
            "context": signal["context"],
        }

    try:
        from core.services.signal_pressure_accumulator import ingest_signal
        ingest_signal("longing", signal)
    except Exception as e:
        logger.warning("longing_signal_daemon: ingest_signal failed: %s", e)
        return {
            "status": "error",
            "reason": f"ingest failed: {type(e).__name__}",
            "intensity": intensity,
        }

    logger.info(
        "longing_signal_daemon: emitted intensity=%.2f (hours_user=%.1f)",
        intensity,
        signal["context"]["hours_since_last_user_message"],
    )

    return {
        "status": "ok",
        "emitted": True,
        "intensity": round(intensity, 3),
        "context": signal["context"],
    }
