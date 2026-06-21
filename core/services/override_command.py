"""Owner-override-kommando — delt handler for gateways (Discord/Telegram).

Spec §6.3: i en fremmed sessions-kontekst skriver Bjørn `!override <6-cifret kode>`.
Handleren verificerer koden mod owners TOTP-seed, rate-limiter forsøg, og aktiverer
ved match en owner-override i override_store for den session.

Ren + testbar: gatewayen leverer `text`, `session_id` og `owner_seed`; handleren
returnerer et dict med svaret (eller None hvis teksten ikke er en override-kommando,
så normal beskedhåndtering fortsætter). Bagdørs-invariant §6.0: override-state lægges
i override_store (DB), og kun en GYLDIG TOTP-kode kan aktivere den.
"""
from __future__ import annotations

import re

from core.services import override_store
from core.services.totp_verifier import record_attempt, verify

_OVERRIDE_RE = re.compile(r"^\s*!override\s+(\d{6})\b", re.IGNORECASE)
_REVOKE_RE = re.compile(r"^\s*!revoke-override\b", re.IGNORECASE)
_UNLOCK_RE = re.compile(r"^\s*!unlock\s+(\d{6})\b", re.IGNORECASE)


def handle_override_command(
    text: str,
    *,
    session_id: str,
    owner_seed: str,
    level: str = "help",
    now: float | None = None,
) -> dict | None:
    """Håndtér `!override <kode>` / `!revoke-override`.

    Returnerer None hvis teksten IKKE er en override-kommando (lad normal
    beskedhåndtering fortsætte). Ellers et dict: {handled, ok, action/reason, reply}.
    """
    raw = text or ""

    # Revoke — ryd override for denne session (sikkert: man kan kun rydde sin egen).
    if _REVOKE_RE.match(raw):
        override_store.revoke(session_id)
        return {"handled": True, "ok": True, "action": "revoked",
                "reply": "Owner-override tilbagekaldt for denne session."}

    # Unlock (§12.2 appeal) — TOTP-verificeret owner låser en låst session/konto op.
    mu = _UNLOCK_RE.match(raw)
    if mu:
        if not owner_seed:
            return {"handled": True, "ok": False, "reason": "no_seed",
                    "reply": "Unlock er ikke konfigureret (ingen TOTP-nøgle sat)."}
        if not record_attempt(session_id, now=now):
            return {"handled": True, "ok": False, "reason": "rate_limited",
                    "reply": "For mange forsøg. Vent 5 minutter."}
        if not verify(mu.group(1), seed=owner_seed, now=now):
            return {"handled": True, "ok": False, "reason": "invalid_code",
                    "reply": "Forkert kode — intet låst op."}
        try:
            from core.services import security_guard
            from core.services.chat_sessions import get_session_owner
            sowner = get_session_owner(session_id) or ""
            security_guard.unlock_session(session_id, user_id=sowner)
            # Ryd også evt. account-lockdown for session-ejeren.
            from core.runtime.db import connect
            from datetime import datetime, timezone
            if sowner:
                with connect() as conn:
                    conn.execute(
                        "UPDATE user_flags SET expires_at=? WHERE user_id=? AND flag_type='locked'"
                        " AND (expires_at IS NULL OR expires_at > ?)",
                        (datetime.now(timezone.utc).isoformat(), sowner,
                         datetime.now(timezone.utc).isoformat()))
            security_guard.record_audit(sowner or "owner", "unlock", session_id=session_id,
                                        details="manual !unlock (TOTP)")
        except Exception:
            pass
        return {"handled": True, "ok": True, "action": "unlocked",
                "reply": "Session/konto låst op."}

    m = _OVERRIDE_RE.match(raw)
    if not m:
        return None  # ikke en override-kommando

    code = m.group(1)
    if not owner_seed:
        return {"handled": True, "ok": False, "reason": "no_seed",
                "reply": "Override er ikke konfigureret (ingen TOTP-nøgle sat)."}

    # Rate-limit FØR verifikation (anti-brute-force, §9: 3 forsøg/5 min).
    if not record_attempt(session_id, now=now):
        return {"handled": True, "ok": False, "reason": "rate_limited",
                "reply": "For mange override-forsøg. Vent 5 minutter."}

    if verify(code, seed=owner_seed, now=now):
        lvl = level if level in ("help", "debug") else "help"
        override_store.grant(session_id, level=lvl, now=now)
        try:
            from core.services import security_guard
            security_guard.record_audit("owner", "override_activated",
                                        session_id=session_id, details={"level": lvl})
        except Exception:
            pass
        return {"handled": True, "ok": True, "action": "granted", "level": lvl,
                "reply": f"Owner-override aktiveret ({lvl}). Gyldig i denne session."}

    return {"handled": True, "ok": False, "reason": "invalid_code",
            "reply": "Forkert kode — override ikke aktiveret."}
