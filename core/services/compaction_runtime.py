"""`CompactionRuntime` — kontekst-pres lettes ved ERSTATNING, aldrig ved sletning.

Spec: Fase 2, §12.

## Den ene regel der forhindrer en uendelig løkke

    «Retry after context overflow is allowed only when pruning or summary
     commitment advances `surface_generation`; otherwise the original overflow
     remains terminal.»

Uden den regel er overløb en løkke: prompten er for stor → kompaktér →
kompakteringen frigav ingenting → prøv igen → prompten er stadig for stor.
Systemet ville arbejde uendeligt uden at komme nogen vegne, og hvert omløb
koster et modelkald.

Derfor er `surface_generation` ikke bogholderi. Den er beviset for at der
faktisk skete noget. Rykkede den ikke, må der ikke prøves igen.

## Atomisk eller slet ikke

Enten committes erstatningen OG den nye generation sammen, eller også står
generationen uændret og fejlen bevaret. En halv kompaktering — en generation
der rykkede uden en erstatning, eller omvendt — ville betyde at prompten
hverken er den gamle eller den nye.

## Hvad der ALDRIG må erstattes

Identitet og systemknuder, uafsluttede værktøjskald, brugerens aktuelle input,
og den konfigurerede hale. De tre første af hensyn til korrekthed; den sidste
fordi en samtale uden nyere kontekst er en samtale der har glemt hvad den
handlede om.

Et uafsluttet værktøjspar er værst: erstattes kaldet men ikke resultatet,
refererer historikken til noget der ikke findes.

## Beskæring før opsummering

Beskæring er deterministisk og gratis; opsummering koster et modelkald og kan
tage fejl. Rækkefølgen er ikke en optimering, men et spørgsmål om hvor meget
man risikerer for at spare plads.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

# ── knude-typer der ikke må erstattes ────────────────────────────────────
PROTECTED_KINDS = ("system", "identity")

STARTED = "compaction_started"
ENDED = "compaction_ended"
FAILED = "compaction_failed"


class NotAdvancing(RuntimeError):
    """Kompakteringen frigav ingenting. Et genforsøg ville være en løkke."""


@dataclass(frozen=True)
class Node:
    """En knude i den overflade der kan erstattes."""

    node_id: str
    kind: str            # system | identity | user | assistant | tool_call | tool_result
    tokens: int = 0
    #: For et `tool_call`: id'et på det resultat der hører til, hvis det findes.
    pair_id: str = ""


@dataclass(frozen=True)
class Policy:
    threshold_tokens: int = 100_000
    #: Hvor mange knuder i halen der ALTID bevares.
    retained_tail: int = 20
    max_attempts: int = 2
    prune_tool_results_over: int = 2_000


@dataclass(frozen=True)
class Surface:
    nodes: tuple[Node, ...]
    generation: int = 0

    def tokens(self) -> int:
        return sum(n.tokens for n in self.nodes)


@dataclass(frozen=True)
class Result:
    surface: Surface
    advanced: bool
    events: tuple[str, ...] = ()
    freed_tokens: int = 0
    rule: str = ""
    error: str = ""


def _uafsluttede_par(nodes: tuple[Node, ...]) -> set[str]:
    """Værktøjskald hvis resultat mangler — og resultaterne selv.

    Erstattes kaldet men ikke resultatet, refererer historikken til noget der
    ikke findes.
    """
    resultater = {n.node_id for n in nodes if n.kind == "tool_result"}
    ud: set[str] = set()
    for n in nodes:
        if n.kind == "tool_call":
            if n.pair_id and n.pair_id in resultater:
                ud.add(n.node_id)
                ud.add(n.pair_id)
            else:
                ud.add(n.node_id)          # kald uden resultat: rør det ikke
    return ud


def protected_ids(s: Surface, p: Policy, *, current_user_input: str = "") -> set[str]:
    """Alt der ikke må erstattes."""
    beskyttet = {n.node_id for n in s.nodes if n.kind in PROTECTED_KINDS}
    beskyttet |= _uafsluttede_par(s.nodes)
    if p.retained_tail > 0:
        beskyttet |= {n.node_id for n in s.nodes[-p.retained_tail:]}
    if current_user_input:
        beskyttet.add(current_user_input)
    return beskyttet


def prune_tool_results(s: Surface, p: Policy, *,
                       current_user_input: str = "") -> Result:
    """Deterministisk beskæring. Ingen model, ingen risiko for at tage fejl."""
    fredet = protected_ids(s, p, current_user_input=current_user_input)
    frigivet = 0
    nye: list[Node] = []
    for n in s.nodes:
        if (n.kind == "tool_result" and n.node_id not in fredet
                and n.tokens > p.prune_tool_results_over):
            frigivet += n.tokens - p.prune_tool_results_over
            nye.append(replace(n, tokens=p.prune_tool_results_over))
        else:
            nye.append(n)

    if frigivet == 0:
        # Generationen rykker IKKE. Der skete ingenting.
        return Result(s, advanced=False, freed_tokens=0,
                      rule="intet at beskære")
    return Result(Surface(tuple(nye), s.generation + 1), advanced=True,
                  events=(STARTED, ENDED), freed_tokens=frigivet,
                  rule="værktøjsresultater beskåret")


def replaceable_range(s: Surface, p: Policy, *,
                      current_user_input: str = "") -> tuple[int, int]:
    """Ét SAMMENHÆNGENDE spænd der må erstattes. `(0, 0)` hvis intet kan.

    Sammenhængende, fordi en opsummering af spredte stumper ikke er en
    opsummering af en samtale — den er en liste over hvad der tilfældigvis
    ikke var fredet.
    """
    fredet = protected_ids(s, p, current_user_input=current_user_input)
    start = None
    for i, n in enumerate(s.nodes):
        if n.node_id in fredet:
            if start is not None:
                return (start, i)
            continue
        if start is None:
            start = i
    if start is not None and start < len(s.nodes):
        return (start, len(s.nodes))
    return (0, 0)


def summarize(s: Surface, p: Policy, *, summary_text: str, summary_tokens: int,
              current_user_input: str = "") -> Result:
    """Erstat ét spænd med en opsummering. Atomisk eller slet ikke.

    `summary_text` kommer udefra med vilje: opsummeringen laves af en
    bivirkningsfri model-rute, og dén hører ikke hjemme i den funktion der
    afgør HVAD der må erstattes.
    """
    i, j = replaceable_range(s, p, current_user_input=current_user_input)
    if i == j:
        return Result(s, advanced=False, rule="intet spænd kan erstattes")

    frigivet = sum(n.tokens for n in s.nodes[i:j]) - summary_tokens
    if frigivet <= 0:
        # Opsummeringen er ikke mindre end det den erstatter. Generationen
        # rykker ikke — ellers ville et genforsøg være tilladt uden at der var
        # frigivet noget.
        return Result(s, advanced=False, freed_tokens=0,
                      rule="opsummeringen frigav ingenting")

    ny = Node(node_id=f"summary-gen{s.generation + 1}", kind="assistant",
              tokens=summary_tokens)
    nodes = s.nodes[:i] + (ny,) + s.nodes[j:]
    return Result(Surface(nodes, s.generation + 1), advanced=True,
                  events=(STARTED, ENDED), freed_tokens=frigivet,
                  rule="spænd erstattet af opsummering")


def failed(s: Surface, error: str) -> Result:
    """En mislykket kompaktering. Generationen står UÆNDRET.

    Og den oprindelige fejl bevares: erstattes den med «kompakteringen
    fejlede», mister man hvorfor der skulle kompakteres.
    """
    return Result(s, advanced=False, events=(STARTED, FAILED), error=str(error),
                  rule="kompakteringen fejlede — generationen uændret")


def may_retry_after_overflow(before: Surface, after: Result) -> bool:
    """Må overløbet prøves igen?

    KUN hvis generationen rykkede. Ellers er prompten stadig for stor, og et
    genforsøg ville være samme kald med samme udfald — i en løkke der koster et
    modelkald pr. omgang.
    """
    return bool(after.advanced) and after.surface.generation > before.generation


def require_advance(before: Surface, after: Result) -> Result:
    """Som ovenfor, men kaster. Til kaldesteder der ellers ville løkke."""
    if not may_retry_after_overflow(before, after):
        raise NotAdvancing(
            f"generationen står stadig på {before.generation}: "
            f"{after.rule or 'ingenting blev frigivet'} — "
            "et genforsøg ville være det samme kald med samme udfald"
        )
    return after
