"""Hvor længe skal et cheap-lane-slot i karantæne? Afhænger af HVORFOR det fejlede.

**Problemet, målt 18. aug 2026 på hele poolen (106 slots).** Balanceren behandlede
enhver ikke-429-fejl ens: tre fortløbende fejl før breakeren overhovedet reagerer, og
derefter en gradueret cooldown på 5 min → 15 min → maks 1 time. Det er rigtigt for et
flakkende netværk. Det er forkert for en model providerne har pensioneret: et slot med
``model-not-found`` eller ``http-410`` (HTTP *Gone*) fejler på 66 ms, venter en time og
kommer så tilbage i lodtrækningen — for evigt, for en model der aldrig vender tilbage.

Målt fordeling:

===================  ====  ====================================================
ok                     71  67% — median 858 ms. Lanen er ikke tør.
credits-exhausted      10  betalings-/kvotecyklus
model-not-found         6  config-drift: modellen findes ikke længere
http-410                5  endpointet er permanent fjernet
unreachable             4  ægte transient
rate-limited            3  ægte transient
quota-exhausted         2  kvotecyklus
request-failed          2  ægte transient
auth-rejected           2  nøglen afvises — vender ikke tilbage af sig selv
http-400                1  ægte transient
===================  ====  ====================================================

25 af 106 slots (24%) burde slet ikke være i lodtrækningen, men cyklede tilbage hver
time. Med ``max_retries=3`` betød det at et kald rutinemæssigt kunne trække tre døde
slots og erklære "hele bunden tør" — mens 71 sunde slots stod ubrugte.

**Karantænen er tidsbegrænset, ikke permanent.** En rettet konfiguration skal hele sig
selv uden at nogen husker at fjerne et flag. Derfor 24 timer, ikke "for evigt".
"""
from __future__ import annotations

# Config-drift: modellen/endpointet findes ikke, eller nøglen afvises. Ingen mængde
# gentagelser inden for det næste døgn ændrer det — det kræver en config-ændring.
PERMANENT_CODES: frozenset[str] = frozenset({
    "model-not-found",
    "not-found",
    "http-404",
    "http-410",
    "auth-rejected",
    "unauthorized",
    "forbidden",
    "http-401",
    "http-403",
})

# Budgettet er brugt. Kommer tilbage på en daglig eller månedlig cyklus — men ikke
# inden for de næste minutter, som breaker-trappen ellers ville antage.
DEPLETED_CODES: frozenset[str] = frozenset({
    "credits-exhausted",
    "quota-exhausted",
    "insufficient-credits",
    "billing",
})

PERMANENT_QUARANTINE_S = 24 * 3600
DEPLETED_QUARANTINE_S = 6 * 3600


# Udbyderne er ikke enige om hvilken HTTP-kode en pensioneret model giver. Målt 19. aug:
# opencode svarede ``auth-rejected`` på "Model … is not supported" (sendte fejlsøgningen
# efter NØGLER), og aionlabs svarede ``http-400`` på "Unknown model" (klassificeret
# transient → slottet kom tilbage i lodtrækningen igen og igen). Beskeden er sandere end
# koden, så vi læser den når vi har den.
_RETIRED_PHRASES = (
    "is not supported",
    "unknown model",
    "does not exist",
    "no longer available",
    "model_archived",
    "is archived",
    "has been retired",
    "retirement",
    "decommissioned",
)


def classify(error_kind: str, message: str = "") -> str:
    """``'permanent'`` | ``'depleted'`` | ``'transient'``.

    ``message`` er serverens egen fejltekst, når vi har den. Den vejer TUNGERE end koden:
    en udbyder der skriver "Unknown model" bag en 400'er fortæller os noget koden skjuler.

    Ukendte koder uden sigende besked bliver ``transient``: en fejl vi ikke forstår må
    aldrig føre til at et sundt slot forsvinder i et døgn. Mild ved tvivl.
    """
    body = str(message or "").strip().lower()
    if body and any(p in body for p in _RETIRED_PHRASES):
        return "permanent"

    kind = str(error_kind or "").strip().lower()
    if not kind:
        return "transient"
    if kind in PERMANENT_CODES:
        return "permanent"
    if kind in DEPLETED_CODES:
        return "depleted"
    return "transient"


def quarantine_seconds(error_kind: str, *, retry_after_s: int = 0, message: str = "") -> int:
    """Karantæne-længde, eller ``0`` når slottet skal følge den normale breaker-trappe.

    Et ``retry-after`` fra serveren er altid autoritativt — providerens eget svar om
    hvornår den er klar igen skal aldrig overskrives af vores klassifikation.
    """
    if retry_after_s and retry_after_s > 0:
        return 0
    kind = classify(error_kind, message)
    if kind == "permanent":
        return PERMANENT_QUARANTINE_S
    if kind == "depleted":
        return DEPLETED_QUARANTINE_S
    return 0
