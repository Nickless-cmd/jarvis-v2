"""Central-governed EARNED model-trust (harness refactor Part 1 foundation).

Every model starts WEAK (all safety nets on). The Central earns each one's trust from evidence:
20 consecutive CLEAN runs -> auto-promote to STRONG; a SINGLE degeneration run -> auto-revert to weak
+ reset the streak. No owner classification (the Central remembers). model_strength() is the single
downstream reader and FAILS OPEN to weak. Owner may pin a model (weak/strong/auto=default) but never
has to. Durable (survives restart). Self-safe throughout."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from core.runtime.db_core import connect

_PROMOTE_THRESHOLD = 20  # consecutive clean runs to earn strong


def _ensure(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS model_trust (
            model TEXT PRIMARY KEY,
            strength TEXT NOT NULL DEFAULT 'weak',
            clean_streak INTEGER NOT NULL DEFAULT 0,
            pin TEXT NOT NULL DEFAULT 'auto',
            last_degeneration_at TEXT NOT NULL DEFAULT '',
            promoted_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )"""
    )


def _row(conn: sqlite3.Connection, model: str) -> dict[str, Any]:
    r = conn.execute(
        "SELECT model, strength, clean_streak, pin, last_degeneration_at, promoted_at "
        "FROM model_trust WHERE model = ?", (model,)).fetchone()
    if r is None:
        return {"model": model, "strength": "weak", "clean_streak": 0, "pin": "auto",
                "last_degeneration_at": "", "promoted_at": ""}
    return dict(r)


def record_run_outcome(model: str, *, degenerated: bool) -> None:
    """Record one run's outcome. Clean -> +1 streak (promote at threshold); degeneration -> reset
    streak + revert to weak. Self-safe (never affects the run)."""
    model = str(model or "").strip()
    if not model:
        return
    try:
        now = datetime.now(UTC).isoformat()
        with connect() as conn:
            _ensure(conn)
            row = _row(conn, model)
            strength, streak = row["strength"], int(row["clean_streak"])
            promoted_at, last_deg = row["promoted_at"], row["last_degeneration_at"]
            if degenerated:
                strength, streak, last_deg = "weak", 0, now
            else:
                streak += 1
                if streak >= _PROMOTE_THRESHOLD and strength != "strong":
                    strength, promoted_at = "strong", now
            conn.execute(
                """INSERT INTO model_trust (model, strength, clean_streak, pin, last_degeneration_at, promoted_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(model) DO UPDATE SET
                     strength=excluded.strength, clean_streak=excluded.clean_streak,
                     last_degeneration_at=excluded.last_degeneration_at,
                     promoted_at=excluded.promoted_at, updated_at=excluded.updated_at""",
                (model, strength, streak, row["pin"], last_deg, promoted_at, now))
            conn.commit()
    except Exception:
        pass


def set_pin(model: str, pin: str) -> None:
    """Owner override: 'weak' | 'strong' | 'auto' (default). Self-safe."""
    if pin not in ("weak", "strong", "auto"):
        return
    try:
        with connect() as conn:
            _ensure(conn)
            conn.execute(
                "INSERT INTO model_trust (model, pin, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(model) DO UPDATE SET pin=excluded.pin, updated_at=excluded.updated_at",
                (str(model), pin, datetime.now(UTC).isoformat()))
            conn.commit()
    except Exception:
        pass


def model_strength(model: str) -> str:
    """'strong' | 'weak'. Pin wins; else earned strength. FAILS OPEN to 'weak'."""
    try:
        with connect() as conn:
            _ensure(conn)
            row = _row(conn, str(model or ""))
        pin = row.get("pin") or "auto"
        if pin in ("weak", "strong"):
            return pin
        return "strong" if row.get("strength") == "strong" else "weak"
    except Exception:
        return "weak"


def build_model_trust_surface() -> dict[str, object]:
    """Central-CLI view: per-model trust state. Self-safe."""
    try:
        with connect() as conn:
            _ensure(conn)
            rows = conn.execute(
                "SELECT model, strength, clean_streak, pin, last_degeneration_at, promoted_at "
                "FROM model_trust ORDER BY strength DESC, clean_streak DESC").fetchall()
        return {"active": True, "threshold": _PROMOTE_THRESHOLD, "models": [dict(r) for r in rows]}
    except Exception:
        return {"active": True, "threshold": _PROMOTE_THRESHOLD, "models": []}
