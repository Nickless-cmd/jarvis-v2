"""Slette-model — hvem må slette hvad, og hvor hårdt (spec §4.3).

| Rolle | Eget workspace | Andres workspace |
|-------|----------------|------------------|
| Owner | hard-delete, men **spørg 2 gange** (eller vetogate) | hard-delete, 2× |
| Member | **soft-delete** (grace-period-kopi beholdes) | **deny** |
| Guest | deny | deny |

Ren policy-funktion — beslutter mode + bekræftelses-krav. Selve sletningen
(hard rm vs. flyt-til-grace) udføres af kald-laget, der FØRST konsulterer denne
politik. Fail-closed: ukendt rolle → deny.

Owner-hard-delete kræver to eksplicitte bekræftelser (§4.3) ELLER en vetogate-
bekræftelse — en irreversibel handling skal aldrig kunne ske ved ét uheld.
"""
from __future__ import annotations

_OWNER_ROLES = ("", "owner")  # "" = unbound legacy → owner
_OWNER_CONFIRMATIONS = 2


def resolve_delete_action(
    *, role: str, is_own_workspace: bool, gdpr_erasure: bool = False,
) -> dict:
    """Afgør slette-mode for (rolle, om det er eget workspace).

    Returnerer {mode: hard|soft|deny, confirmations: int, reason}.

    `gdpr_erasure=True`: brugeren udøver eksplicit sin GDPR-sletningsret (§15.2)
    på SINE EGNE data → ægte hard-delete (ingen skjult grace-kopi), 1× bekræftelse
    af hensigt. Default (soft) er fortryd-venlig; GDPR-erasure er den bevidste,
    irreversible vej.
    """
    r = (role or "").strip().lower()

    if r in _OWNER_ROLES:
        return {"mode": "hard", "confirmations": _OWNER_CONFIRMATIONS,
                "reason": "owner: hard-delete kræver 2× bekræftelse (§4.3)"}

    if r == "member":
        if is_own_workspace:
            if gdpr_erasure:
                return {"mode": "hard", "confirmations": 1,
                        "reason": "member GDPR-sletningsret (§15.2): ægte sletning af egne data"}
            return {"mode": "soft", "confirmations": 0,
                    "reason": "member: soft-delete med grace-period-kopi"}
        return {"mode": "deny", "confirmations": 0,
                "reason": "member må ikke slette i andres workspace"}

    # guest + ukendt → fail-closed
    return {"mode": "deny", "confirmations": 0,
            "reason": f"rolle '{r or 'ukendt'}' har ingen slette-rettighed"}


def is_delete_confirmed(*, role: str, confirmations_received: int) -> bool:
    """True hvis sletningen må udføres givet antal modtagne bekræftelser.

    Owner hard-delete: kræver 2. Member soft-delete: 0 (ingen bekræftelse).
    Deny-roller: aldrig.
    """
    action = resolve_delete_action(role=role, is_own_workspace=True)
    if action["mode"] == "deny":
        return False
    return int(confirmations_received) >= int(action["confirmations"])
