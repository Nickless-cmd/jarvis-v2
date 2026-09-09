"""`OutcomeProjector` — ét terminalt udfald pr. run, uden at opfinde sandhed.

Spec: Fase 2, §10.

## Reglen der bærer det hele

    «Never manufactures a successful assistant message to hide a failed
     attempt.»

Det er ikke en teoretisk regel her i huset. Det er sket: en aihubmix-kvotefejl
blev gemt som en ASSISTENT-besked og endte i `[SELF]`-ankeret, hvor Jarvis
læste sin egen udbyder-regning som noget han havde sagt om sig selv. Og
`visible_runs.py` bærer to advarsler om at en falsk tom-svar-konklusion «wiper
det streamede svar».

Fælles for begge: et mislykket forsøg blev til noget der lignede et svar.

Derfor: en besked til brugeren om at noget gik galt, er en EGEN slags
overflade-hændelse med sin egen herkomst — ikke en assistent-besked med et
venligt indhold. Forskellen kan ses i data, ikke kun i tonen.

## Nøjagtig ét terminalt udfald

`completed`, `interrupted`, `failed` eller `abandoned`. Ét. Et run med to
udfald er et run ingen kan rapportere på: to tællere, to grafer, to svar på
«gik det godt».

## Projektionen opfinder ikke noget

Den læser afregnede forsøg og siger hvad de tilsammen betyder. Den kalder ingen
udbyder, gætter ikke på hvad der «nok» skete, og skriver ikke en besked ingen
har sagt.

## Idempotent, nøglet på den terminale hændelse

En projektion der fejler, skal kunne køres igen — uafhængigt af model- og
værktøjskørsel, som spec'en kræver. Derfor er nøglen den terminale hændelses
id, og en gentagelse giver samme svar frem for et nyt udfald.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.services import stream_settlement as S

# ── terminale run-udfald ─────────────────────────────────────────────────
COMPLETED = "completed"
INTERRUPTED = "interrupted"
FAILED = "failed"
ABANDONED = "abandoned"

TERMINALE = (COMPLETED, INTERRUPTED, FAILED, ABANDONED)

# ── overflade-hændelser til brugeren ─────────────────────────────────────
#: En besked OM at noget gik galt. Aldrig forklædt som et svar.
SURFACE_NOTICE = "surface_notice"


@dataclass(frozen=True)
class SurfaceEvent:
    """En besked til brugeren med sin EGEN herkomst.

    `kind` er `surface_notice`, ikke `assistant_message`. Det er hele pointen:
    forskellen skal kunne ses i data, ikke kun i tonen.
    """

    kind: str
    text: str
    #: Hvor beskeden kommer fra — «runtime», aldrig «modellen».
    provenance: str = "runtime"
    reason: str = ""


@dataclass(frozen=True)
class RunOutcome:
    outcome: str
    #: Den hændelse der gjorde det terminalt. Projektionens nøgle.
    terminal_event_id: str = ""
    attempts: int = 0
    #: Sat når brugeren skal have besked om at noget gik galt.
    surface: SurfaceEvent | None = None
    rule: str = ""


class DoubleTerminal(RuntimeError):
    """Et run fik to terminale udfald. Så kan ingen rapportere på det."""


def project(settlements: list[S.Settlement], *, terminal_event_id: str = "",
            recovered: bool = False, stop_reason: str = "") -> RunOutcome:
    """Ét udfald ud af de afregnede forsøg. Ren funktion.

    `recovered` betyder at runnet blev fundet forladt og lukket af
    genopretningen — dét er `abandoned`, og det er en anden ting end at fejle.
    """
    n = len(settlements)

    if recovered:
        return RunOutcome(ABANDONED, terminal_event_id, n,
                          surface=SurfaceEvent(
                              SURFACE_NOTICE,
                              "Kørslen blev afbrudt og er lukket bagefter.",
                              reason="abandoned"),
                          rule="fundet forladt og lukket af genopretningen")

    if n == 0:
        return RunOutcome(FAILED, terminal_event_id, 0,
                          surface=SurfaceEvent(
                              SURFACE_NOTICE, "Der kom aldrig et svar.",
                              reason="ingen forsøg"),
                          rule="ingen forsøg overhovedet")

    sidste = settlements[-1]

    if sidste.event == S.ASSISTANT_MESSAGE:
        if sidste.interrupted:
            # Der ER et svar, og det er afkortet. Brugeren skal vide det, men
            # svaret står — det må ikke skjules bag en fejlbesked.
            return RunOutcome(INTERRUPTED, terminal_event_id, n,
                              surface=SurfaceEvent(
                                  SURFACE_NOTICE,
                                  "Svaret blev afbrudt undervejs.",
                                  reason="interrupted"),
                              rule="afregnet besked, afbrudt")
        return RunOutcome(COMPLETED, terminal_event_id, n,
                          rule="afregnet besked, hel")

    if sidste.reason == S.CANCELLED_REASON:
        # Et AFBRUDT run er ikke et fejlet run.
        #
        # Fundet 9/9-2026 af afregnings-skyggens anden uenighed: den gamle kode
        # kaldte en kørsel afbrudt midt i flugten `interrupted`, min kontrakt
        # kaldte den `failed`. Den gamle havde ret. Spec'en har fire udfald
        # netop for at skelne — «det gik i stykker» og «det blev stoppet» er
        # ikke det samme, hverken for brugeren eller for en optælling.
        #
        # Intet svar at vise, men heller ingen fejl at melde: derfor en
        # overflade-note der siger hvad der skete, ikke en fejlbesked.
        return RunOutcome(INTERRUPTED, terminal_event_id, n,
                          surface=SurfaceEvent(
                              SURFACE_NOTICE, "Kørslen blev afbrudt.",
                              reason=S.CANCELLED_REASON),
                          rule="afbrudt før der kom et svar")

    # Sidste forsøg mislykkedes. HER er fristelsen til at lave et svar der
    # dækker over det — og præcis dét gøres ikke.
    return RunOutcome(FAILED, terminal_event_id, n,
                      surface=SurfaceEvent(
                          SURFACE_NOTICE,
                          _fejltekst(sidste, stop_reason),
                          reason=sidste.reason or "failure"),
                      rule="sidste forsøg mislykkedes")


def _fejltekst(s: S.Settlement, stop_reason: str) -> str:
    """Sig hvad der skete. Ingen undskyldninger, ingen opdigtet forklaring."""
    hvad = {
        S.EMPTY_RESPONSE: "Modellen svarede ikke.",
        S.CANCELLED_REASON: "Kørslen blev afbrudt.",
        S.MALFORMED_TOOL_CALL: "Modellen lavede et ugyldigt værktøjskald.",
        S.FAILURE: "Forbindelsen til udbyderen fejlede.",
    }.get(s.reason, "Kørslen fejlede.")
    return f"{hvad} {stop_reason}".strip() if stop_reason else hvad


# ── idempotent projektion ────────────────────────────────────────────────

class OutcomeLedger:
    """Nøjagtig ét terminalt udfald pr. run, nøglet på den terminale hændelse.

    En gentagelse giver SAMME svar tilbage. En projektion der fejler, skal
    kunne køres igen uafhængigt af model- og værktøjskørsel — så et
    genforsøg må ikke kunne lave et nyt udfald.
    """

    def __init__(self) -> None:
        self._ud: dict[str, RunOutcome] = {}

    def record(self, run_id: str, outcome: RunOutcome) -> RunOutcome:
        rid = str(run_id)
        findes = self._ud.get(rid)
        if findes is not None:
            if (findes.outcome != outcome.outcome
                    or findes.terminal_event_id != outcome.terminal_event_id):
                raise DoubleTerminal(
                    f"run {rid!r} er allerede {findes.outcome!r} "
                    f"(hændelse {findes.terminal_event_id!r}); kan ikke også være "
                    f"{outcome.outcome!r} ({outcome.terminal_event_id!r})"
                )
            # Samme udfald igen: en gentaget projektion, ikke et nyt udfald.
            return findes
        self._ud[rid] = outcome
        return outcome

    def outcome(self, run_id: str) -> RunOutcome | None:
        return self._ud.get(str(run_id))

    def is_terminal(self, run_id: str) -> bool:
        return str(run_id) in self._ud
