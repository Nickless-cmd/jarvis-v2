"""Plugin-regelsæt — brugerdefinerede kanal-regler der IKKE kan tilsidesættes.

Spec §5.3: hvert kanal-plugin har et regelsæt brugeren definerer, som Jarvis
**ikke kan bryde — uanset hvem der spørger, selv owner med gyldig override**.
Derfor ignorerer `is_allowed` `override_active` fuldstændigt (hardblock for alle).

Regelsæt-felter (alle valgfrie):
- `allowed_channels: list[str]`  — kun disse kanaler; alle andre ignoreres.
- `blocked_roles: list[str]`     — beskeder fra disse afsender-roller når aldrig Jarvis.
- `quiet_hours: [start, end]`    — stilletid (timer 0-23), wrap-around understøttet.
- `rate_limits: {channel: max}`  — maks svar pr. rullende time pr. kanal.

`is_allowed(msg_ctx, ruleset)` returnerer (allow, grund). Et tilladt svar
optælles mod rate-grænsen (ét kald = ét potentielt svar).
"""
from __future__ import annotations

import time
from collections import deque

_RATE_WINDOW = 3600  # sekunder (1 time)

# In-memory svar-log pr. kanal til rate-limiting. Lokal misbrugs-bremse, ikke
# autoritet — behøver ikke cross-proces.
_RESPONSES: dict[str, deque[float]] = {}


def _quiet_now(hour: int, quiet: list[int] | tuple[int, int]) -> bool:
    """True hvis `hour` er inden for stilletids-vinduet (wrap-around understøttet)."""
    try:
        start, end = int(quiet[0]), int(quiet[1])
    except (TypeError, ValueError, IndexError):
        return False
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    # Wrap-around, fx 22→8: blokeret hvis hour>=22 ELLER hour<8
    return hour >= start or hour < end


def is_allowed(
    msg_ctx: dict,
    ruleset: dict | None,
    *,
    override_active: bool = False,
) -> tuple[bool, str]:
    """Afgør om Jarvis må svare på en indkommende kanal-besked.

    `override_active` er bevidst UBRUGT — plugin-regelsæt er hardblock for alle,
    inkl. owner (§5.3). Parameteren findes kun for kald-symmetri med andre gates.
    """
    rs = ruleset or {}
    channel = str(msg_ctx.get("channel") or "")
    role = str(msg_ctx.get("role") or "")
    hour = int(msg_ctx.get("hour", -1))
    now = msg_ctx.get("now")
    now = time.time() if now is None else float(now)

    # 1. Kanal-allowlist
    allowed = rs.get("allowed_channels")
    if allowed is not None and channel not in allowed:
        return False, f"kanal '{channel}' ikke i tilladte kanaler"

    # 2. Rolle-blocklist
    if role and role in (rs.get("blocked_roles") or []):
        return False, f"afsender-rolle '{role}' er blokeret"

    # 3. Stilletid
    quiet = rs.get("quiet_hours")
    if quiet and 0 <= hour <= 23 and _quiet_now(hour, quiet):
        return False, f"stilletid ({quiet[0]}-{quiet[1]}), time {hour}"

    # 4. Rate-limit pr. kanal (optæl kun når alt andet er tilladt)
    limit = (rs.get("rate_limits") or {}).get(channel)
    if limit is not None:
        dq = _RESPONSES.setdefault(channel, deque())
        cutoff = now - _RATE_WINDOW
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= int(limit):
            return False, f"rate-grænse nået i '{channel}' ({limit}/time)"
        dq.append(now)

    return True, "ok"
