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
        return {"handled": True, "ok": True, "action": "granted", "level": lvl,
                "reply": f"Owner-override aktiveret ({lvl}). Gyldig i denne session."}

    return {"handled": True, "ok": False, "reason": "invalid_code",
            "reply": "Forkert kode — override ikke aktiveret."}
