"""`RetryRuntime` — genforsøg som en BEGRÆNSET beslutning, ikke en refleks.

Spec: Fase 2, §9.

## Hvad der er galt med genforsøg der «bare virker»

Et genforsøg uden loft er en løkke der koster penge. Værre: hvis loftet
nulstilles når man skifter udbyder, findes loftet ikke — det udsætter bare
regningen. Spec'en siger det direkte: «Provider failover does not reset them.»

Derfor er budgettet knyttet til TUREN, ikke til udbyderen. Fem forsøg er fem
forsøg, uanset hvor mange udbydere de fordeler sig på.

## Beslutningen ændrer ingenting

`decide()` er en ren funktion: den får en afregnet fejl, de tidligere forsøg og
det resterende budget, og svarer `retry(...)` eller `stop(...)`. Den skriver
ikke i historikken, starter ikke en timer og kalder ikke en udbyder.

Det er ikke pedanteri. En beslutningsfunktion der også handler, kan ikke prøves
uden at der sker noget — og så bliver den ikke prøvet grundigt.

## Ikke alt skal prøves igen

Nogle fejl er forbigående: tomt svar, rate limit, timeout, transport, server.
Andre er en tilstand der ikke ændrer sig af at man spørger igen —
autentificering, ugyldig anmodning, politik-afvisning. At prøve igen dér er at
lave den samme fejl hurtigere.

Og én kategori er farlig frem for nytteløs: `outcome_unknown` og fejl efter en
værktøjs-bivirkning. Vi ved ikke om det virkede. Et genforsøg kunne udføre
handlingen to gange, og det er værre end at fejle.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

# ── strukturerede fejlårsager ────────────────────────────────────────────
EMPTY_RESPONSE = "EMPTY_RESPONSE"
RATE_LIMIT = "RATE_LIMIT"
TIMEOUT = "TIMEOUT"
TRANSPORT = "TRANSPORT"
SERVER_ERROR = "SERVER_ERROR"

AUTH = "AUTH"
INVALID_REQUEST = "INVALID_REQUEST"
POLICY_DENIED = "POLICY_DENIED"
TOOL_SIDE_EFFECT = "TOOL_SIDE_EFFECT"
OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"

#: Fejl der kan gå over af sig selv.
FORBIGAAENDE = (EMPTY_RESPONSE, RATE_LIMIT, TIMEOUT, TRANSPORT, SERVER_ERROR)

#: Fejl hvor et genforsøg er den samme fejl, bare hurtigere.
UAENDRET_AF_AT_SPOERGE_IGEN = (AUTH, INVALID_REQUEST, POLICY_DENIED)

#: Fejl hvor et genforsøg kan gøre SKADE, ikke bare spilde tid.
FARLIGT_AT_GENTAGE = (TOOL_SIDE_EFFECT, OUTCOME_UNKNOWN)

RETRY = "retry"
STOP = "stop"


@dataclass(frozen=True)
class Budget:
    """Lofter for HELE turen. Failover nulstiller intet af det."""

    max_attempts: int = 3
    max_failovers: int = 2
    max_wall_s: float = 300.0
    max_generated_tokens: int = 60_000
    max_cost_usd: float = 1.0


@dataclass(frozen=True)
class Spent:
    """Hvad turen allerede har brugt — på tværs af alle udbydere."""

    attempts: int = 0
    failovers: int = 0
    wall_s: float = 0.0
    generated_tokens: int = 0
    cost_usd: float = 0.0

    def plus_attempt(self, *, wall_s: float = 0.0, tokens: int = 0,
                     cost_usd: float = 0.0, failover: bool = False) -> "Spent":
        return replace(
            self, attempts=self.attempts + 1,
            failovers=self.failovers + (1 if failover else 0),
            wall_s=self.wall_s + wall_s,
            generated_tokens=self.generated_tokens + tokens,
            cost_usd=self.cost_usd + cost_usd,
        )


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str = ""
    delay_s: float = 0.0
    route_override: str = ""
    #: Hvilken regel der afgjorde det — så en forkert beslutning kan spores
    #: til reglen frem for at skulle genlæses.
    rule: str = ""


def _udtoemt(b: Budget, s: Spent) -> str:
    """Hvilket loft er nået? Tom streng hvis der er plads.

    Rækkefølgen er den mest sigende først: har man brugt alle forsøg, er det
    den forklaring der hjælper, selv om tiden også var ved at løbe ud.
    """
    if s.attempts >= b.max_attempts:
        return f"alle {b.max_attempts} forsøg brugt"
    if s.failovers >= b.max_failovers:
        return f"alle {b.max_failovers} udbyder-skift brugt"
    if s.wall_s >= b.max_wall_s:
        return f"tidsloftet nået ({s.wall_s:.0f}s af {b.max_wall_s:.0f}s)"
    if s.generated_tokens >= b.max_generated_tokens:
        return f"token-loftet nået ({s.generated_tokens} af {b.max_generated_tokens})"
    if s.cost_usd >= b.max_cost_usd:
        return f"pris-loftet nået ({s.cost_usd:.3f} af {b.max_cost_usd:.3f} USD)"
    return ""


def backoff(forsoeg: int, *, provider_hint_s: float = 0.0,
            mindst: float = 0.5, hoejst: float = 30.0) -> float:
    """Ventetid før næste forsøg.

    Udbyderens eget hint vinder når det findes — den ved bedre end os hvornår
    en rate limit går væk — men klippes til vores grænser, så en udbyder ikke
    kan bede os vente i en time.
    """
    if provider_hint_s > 0:
        return max(mindst, min(float(provider_hint_s), hoejst))
    return max(mindst, min(mindst * (2 ** max(0, forsoeg - 1)), hoejst))


def decide(*, failure: str, budget: Budget, spent: Spent,
           cancelled: bool = False, provider_hint_s: float = 0.0,
           route_override: str = "") -> Decision:
    """Skal der prøves igen? Ren funktion — ændrer ingenting.

    Rækkefølgen er: annullering, så det farlige, så det uændrede, så budgettet,
    og først derefter det forbigående. Et loft må aldrig kunne åbne for noget
    der ikke skulle prøves igen overhovedet.
    """
    if cancelled:
        # Brugeren har sagt stop. Intet loft og ingen fejlklasse gør det til
        # noget andet.
        return Decision(STOP, reason="annulleret", rule="brugeren annullerede")

    if failure in FARLIGT_AT_GENTAGE:
        # Vi ved ikke om det virkede. Et genforsøg kunne udføre handlingen to
        # gange, og det er værre end at fejle.
        return Decision(STOP, reason=f"{failure}: udfaldet er ukendt",
                        rule="farligt at gentage")

    if failure in UAENDRET_AF_AT_SPOERGE_IGEN:
        return Decision(STOP, reason=f"{failure}: ændrer sig ikke af et genforsøg",
                        rule="uændret af at spørge igen")

    if failure not in FORBIGAAENDE:
        # Ukendt fejlklasse. Standarden er at LADE VÆRE: en fejl vi ikke har
        # taget stilling til, skal ikke arve «prøv igen» ved et tilfælde.
        return Decision(STOP, reason=f"{failure}: ukendt fejlklasse",
                        rule="ukendt fejl prøves ikke igen")

    udtoemt = _udtoemt(budget, spent)
    if udtoemt:
        return Decision(STOP, reason=udtoemt, rule="budget udtømt")

    return Decision(RETRY, reason=failure,
                    delay_s=backoff(spent.attempts + 1,
                                    provider_hint_s=provider_hint_s),
                    route_override=str(route_override or ""),
                    rule="forbigående fejl inden for budget")
