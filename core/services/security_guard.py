"""Identity-verification-guard & abuse-monitoring — kerne (spec 2026-06-21).

Ansvar:
- Revisionsspor (`audit_log`): override/sudo/lock/abuse — uudsletteligt.
- Abuse-hændelser (`abuse_events`): spoofing/injection/manipulation/rate.
- Session-lås (mute): en låst session ignorerer indgående beskeder.
- Account-lockdown: 3 session-locks (samme user_id, 24h) → alle sessioner låst 24h.
  OWNER er exempt (kan aldrig låse sig selv ude, §12.3).
- Strikes: progressiv eskalering, nulstilles efter 7 dage uden nye events (§12.1).

Fail-open-princip (§11.4): hvis guard'en selv kaster, må den ALDRIG låse en
session — log fejlen og lad beskeden passere. Sikkerhed må ikke blive en
selvmål-DoS.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

from core.runtime.db import connect

# ── tærskler (spec §4, §12) ─────────────────────────────────────────────
PUSHBACK_LIMIT = 3            # 3x ignoreret pushback i samme session → session-lock
SESSION_LOCKS_FOR_LOCKDOWN = 3  # 3 session-locks (samme uid, 24h) → account-lockdown
LOCKDOWN_HOURS = 24
STRIKE_RESET_DAYS = 7        # strikes nulstilles efter 7 dage uden nye events
RATE_LIMIT_PER_MIN = 20      # §10/§5.1 — beskeder/min pr. user_id


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None = None) -> str:
    return (dt or _now()).isoformat()


# ── owner-check (owner er exempt fra account-lockdown) ──────────────────
def is_owner(user_id: str) -> bool:
    """True hvis user_id er ejeren (Bjørn). Owner kan få session-lock men
    ALDRIG account-lockdown (§12.3 — anti-self-lockout)."""
    uid = (user_id or "").strip()
    if not uid:
        return False
    try:
        from core.identity.users import get_owner
        owner = get_owner()
        return bool(owner and str(getattr(owner, "discord_id", "")).strip() == uid)
    except Exception:
        return False


# ── audit-log (uudsletteligt revisionsspor, §9) ─────────────────────────
def record_audit(
    user_id: str, action: str, *, session_id: str | None = None,
    details: str | dict | None = None, device_info: str | None = None,
) -> None:
    """Append-only. Aktioner: override_activated, sudo_executed, session_locked,
    account_lockdown, abuse_detected, unlock, identity_pushback."""
    try:
        d = json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else (details or None)
        with connect() as conn:
            conn.execute(
                "INSERT INTO audit_log (user_id, action, session_id, details, device_info, created_at)"
                " VALUES (?,?,?,?,?,?)",
                ((user_id or "").strip(), action, session_id, d, device_info, _iso()),
            )
    except Exception:
        pass  # revision må aldrig spærre runtime


# ── abuse-hændelser ─────────────────────────────────────────────────────
def record_abuse(
    user_id: str, session_id: str, event_type: str, severity: str,
    *, details: str | dict | None = None,
) -> None:
    """severity ∈ {low, medium, high}. Kun high eskalerer til lock (§11.4)."""
    try:
        d = json.dumps(details, ensure_ascii=False) if isinstance(details, dict) else (details or None)
        with connect() as conn:
            conn.execute(
                "INSERT INTO abuse_events (user_id, session_id, event_type, severity, details, created_at)"
                " VALUES (?,?,?,?,?,?)",
                ((user_id or "").strip(), (session_id or "").strip(), event_type, severity, d, _iso()),
            )
        record_audit(user_id, "abuse_detected", session_id=session_id,
                     details={"type": event_type, "severity": severity})
    except Exception:
        pass


# ── session-lås (mute) ──────────────────────────────────────────────────
def lock_session(session_id: str, reason: str, *, user_id: str = "") -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        with connect() as conn:
            conn.execute(
                "UPDATE chat_sessions SET locked=1, locked_reason=?, locked_at=? WHERE session_id=?",
                (reason, _iso(), sid),
            )
        record_audit(user_id, "session_locked", session_id=sid, details=reason)
    except Exception:
        pass


def unlock_session(session_id: str, *, user_id: str = "") -> None:
    sid = (session_id or "").strip()
    if not sid:
        return
    try:
        with connect() as conn:
            conn.execute(
                "UPDATE chat_sessions SET locked=0, locked_reason=NULL, locked_at=NULL WHERE session_id=?",
                (sid,),
            )
        record_audit(user_id, "unlock", session_id=sid)
    except Exception:
        pass


def is_session_locked(session_id: str) -> bool:
    sid = (session_id or "").strip()
    if not sid:
        return False
    try:
        with connect() as conn:
            row = conn.execute(
                "SELECT locked FROM chat_sessions WHERE session_id=?", (sid,)
            ).fetchone()
        return bool(row and int(row[0] or 0) == 1)
    except Exception:
        return False  # fail-open


# ── account-lockdown (per user_id) ──────────────────────────────────────
def is_account_locked(user_id: str) -> bool:
    """True hvis brugeren har en AKTIV (ikke-udløbet) 'locked'-flag."""
    uid = (user_id or "").strip()
    if not uid:
        return False
    try:
        now = _iso()
        with connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM user_flags WHERE user_id=? AND flag_type='locked'"
                " AND (expires_at IS NULL OR expires_at > ?) LIMIT 1",
                (uid, now),
            ).fetchone()
        return bool(row)
    except Exception:
        return False  # fail-open


def _lock_account(user_id: str, *, hours: int = LOCKDOWN_HOURS) -> None:
    """Lås ALLE brugerens sessioner + sæt 'locked'-flag (udløber om `hours`)."""
    uid = (user_id or "").strip()
    if not uid or is_owner(uid):
        return  # owner-exempt
    try:
        exp = _iso(_now() + timedelta(hours=hours))
        with connect() as conn:
            conn.execute(
                "UPDATE chat_sessions SET locked=1, locked_reason='account-lockdown', locked_at=?"
                " WHERE session_id IN (SELECT session_id FROM chat_messages WHERE user_id=?)",
                (_iso(), uid),
            )
            conn.execute(
                "INSERT INTO user_flags (user_id, flag_type, reason, flagged_at, expires_at, strike_count)"
                " VALUES (?,?,?,?,?,?)",
                (uid, "locked", "account-lockdown", _iso(), exp, 0),
            )
        record_audit(uid, "account_lockdown", details={"hours": hours})
    except Exception:
        pass


# ── strikes / eskalering ────────────────────────────────────────────────
def _recent_session_lock_count(user_id: str, *, hours: int = 24) -> int:
    """Antal session-lock-audit-entries for user_id i de sidste `hours`."""
    uid = (user_id or "").strip()
    if not uid:
        return 0
    try:
        since = _iso(_now() - timedelta(hours=hours))
        with connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM audit_log WHERE user_id=? AND action='session_locked'"
                " AND created_at > ?",
                (uid, since),
            ).fetchone()
        return int(row[0] or 0) if row else 0
    except Exception:
        return 0


def escalate_session_lock(user_id: str, session_id: str, reason: str) -> str:
    """Lås sessionen, og afgør om det også udløser account-lockdown.

    Returnerer 'session_lock' eller 'account_lockdown'. Owner får aldrig
    account-lockdown (§12.3)."""
    lock_session(session_id, reason, user_id=user_id)
    if is_owner(user_id):
        return "session_lock"
    # +1 fordi den netop loggede lock også tæller
    if _recent_session_lock_count(user_id, hours=24) >= SESSION_LOCKS_FOR_LOCKDOWN:
        _lock_account(user_id)
        return "account_lockdown"
    return "session_lock"
