"""`StreamSettlement` — ét sted der afgør hvad et udbyder-forsøg BLEV til.

Spec: Fase 2. Den normative afregningstabel i spec'ens §2 er denne fils
specifikation, og hver af dens 13 rækker har en test.

## Hvorfor det skal være ét sted

I dag er terminal-håndteringen spredt over otte filer: `visible_runs.py`,
`visible_followup_adapters.py`, `cheap_provider_runtime_streaming.py`,
`anthropic_translator.py` og flere. Hver af dem har sin egen mening om hvad et
tomt svar er, hvad `max_tokens` betyder, og hvornår en annullering skal gemme
det der allerede blev sendt.

Spredt logik af den slags har ikke ét svar; den har otte, og de er kun enige
indtil nogen retter det ene sted.

## Klassifikatoren er REN

`classify()` rører ingen database, ingen stream, ingen tilstand. Den tager en
beskrivelse af hvad udbyderen gjorde, og siger hvad det skal blive til. Det er
dét der gør 13 tabelrækker prøvbare uden at starte en eneste stream.

Hvad der SKER derefter — hændelsen der skrives, rammen der sendes — er en anden
sag, og hører ikke hjemme her.

## Den hårde invariant: tomt betyder INTET sendt

`core/services/visible_runs.py` bærer to advarsler om samme fejl (linje 2290 og
4644): en falsk `empty_completion` får fallback'en til at «wipe det streamede
svar». Altså — systemet konkluderede at der ikke kom noget svar, mens brugeren
sad og så på det.

Derfor kan `EMPTY_RESPONSE` kun nås når der hverken er blokke ELLER et sendt
præfiks. Er der sendt bytes, findes der et svar, og resten af klassifikationen
må finde ud af hvad det er. Reglen håndhæves med en assert i selve funktionen,
ikke kun i en test.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── terminale årsager fra udbyderen ──────────────────────────────────────
OK = "ok"
MAX_TOKENS = "max_tokens"
CANCELLED = "cancelled"
TRANSPORT_ERROR = "transport_error"

# ── afregnings-hændelser ─────────────────────────────────────────────────
ASSISTANT_MESSAGE = "assistant_message"
ASSISTANT_ATTEMPT = "assistant_attempt"

# ── årsager på et mislykket forsøg ───────────────────────────────────────
EMPTY_RESPONSE = "EMPTY_RESPONSE"
CANCELLED_REASON = "CANCELLED"
MALFORMED_TOOL_CALL = "MALFORMED_TOOL_CALL"
FAILURE = "FAILURE"

# ── hvad UI skal gøre ────────────────────────────────────────────────────
FINALIZE = "finalize"                    # gør de foreløbige rammer endelige
CLEAR = "clear_provisional"              # ryd dem — der kom aldrig noget
RESET = "reset_provisional"              # erstat dem før næste forsøg streamer
TERMINAL_STATUS = "terminal_status"      # kun en status, intet indhold
RETAIN_WITH_TOOL_ERROR = "retain_with_tool_error"

# ── hvad der bør ske bagefter ────────────────────────────────────────────
CONTINUE = "continue"
EXECUTE_TOOLS = "execute_tools"
RETRY_WITHIN_POLICY = "retry_within_policy"
END_INTERRUPTED = "end_interrupted"
STOP_OR_CONTINUATION = "stop_or_explicit_continuation"
NO_SIDE_EFFECT = "no_side_effect"
RECONCILE_INVOCATION = "reconcile_invocation"


@dataclass(frozen=True)
class Attempt:
    """Hvad udbyderen faktisk gjorde. Ren beskrivelse, ingen fortolkning."""

    terminal: str = OK

    #: Gyldige tekstblokke fra udbyderen.
    text_blocks: tuple[str, ...] = ()
    #: Gyldige værktøjskald.
    tool_calls: tuple[dict, ...] = ()
    #: Privat ræsonnement — aldrig i sig selv et svar.
    reasoning_blocks: tuple[str, ...] = ()
    #: Et `thinking`-svar der ER klassificeret som forfremmelses-egnet svar.
    promotable_answer: str = ""

    #: Det SERVER-EJEDE præfiks: den højeste sammenhængende rammesekvens der
    #: nåede den genoptagelige run-buffer før SSE-udsendelse. Spec'en er skarp:
    #: bytes en klient så, men som ikke er i denne buffer, er en transport-fejl
    #: — ikke en alternativ historik.
    emitted_prefix: str = ""

    malformed_tool_call: bool = False
    #: Var der ALLEREDE afregnet en gyldig assistent-besked for dette forsøg?
    message_committed: bool = False
    #: Blev et værktøjskald sendt afsted?
    tool_dispatched: bool = False
    #: Fejlteksten, hvis terminal er en fejl.
    failure: str = ""


@dataclass(frozen=True)
class Settlement:
    """Nøjagtig ÉN pr. forsøg."""

    event: str
    reason: str = ""
    ui: str = FINALIZE
    #: Skal indholdet med i den model-historik næste runde ser?
    in_model_surface: bool = False
    #: Blev turen afbrudt midt i — annulleret eller afkortet?
    interrupted: bool = False
    next_action: str = CONTINUE
    #: Hvilken tabelrække der afgjorde det. Gør en forkert klassifikation
    #: mulig at spore tilbage til reglen frem for at skulle genlæses.
    rule: str = ""


def har_indhold(a: Attempt) -> bool:
    """Findes der overhovedet noget der kunne være et svar?"""
    return bool(a.text_blocks or a.tool_calls or a.promotable_answer)


def classify(a: Attempt) -> Settlement:
    """Afgør hvad forsøget blev til. Ren funktion — rører ingenting.

    Rækkefølgen af reglerne ER betydningsbærende og følger tabellen nedefra og
    op: de tilstande hvor noget ALLEREDE er afregnet eller afsendt, afgøres
    først, fordi de ikke må kunne overskrives af en senere, mildere regel.
    """
    # Et sendt værktøjskald kan ikke gøres usket. Beskeden er afregnet, og det
    # der mangler, er at forlige kaldet — aldrig at prøve blindt igen.
    if a.tool_dispatched:
        return Settlement(ASSISTANT_MESSAGE, ui=RETAIN_WITH_TOOL_ERROR,
                          in_model_surface=True, next_action=RECONCILE_INVOCATION,
                          rule="fejl efter at et værktøjskald blev sendt")

    if a.malformed_tool_call:
        if a.message_committed or a.text_blocks:
            # De gyldige blokke er allerede accepteret. At kassere dem fordi et
            # kald var forkert, ville slette et svar brugeren har set.
            return Settlement(ASSISTANT_MESSAGE, ui=RETAIN_WITH_TOOL_ERROR,
                              in_model_surface=True, next_action=NO_SIDE_EFFECT,
                              rule="misdannet kald EFTER gyldig besked")
        return Settlement(ASSISTANT_ATTEMPT, reason=MALFORMED_TOOL_CALL,
                          ui=RESET, next_action=NO_SIDE_EFFECT,
                          rule="misdannet kald FØR beskeden blev accepteret")

    if a.terminal == TRANSPORT_ERROR:
        if a.emitted_prefix:
            # Delvist leveret, men ikke accepteret som flade. UI skal have en
            # erstatning FØR næste forsøg må streame, ellers ville to svar
            # blande sig i hinanden på skærmen.
            return Settlement(ASSISTANT_ATTEMPT, reason=FAILURE, ui=RESET,
                              next_action=RETRY_WITHIN_POLICY,
                              rule="transport-fejl EFTER delvis levering")
        return Settlement(ASSISTANT_ATTEMPT, reason=FAILURE, ui=TERMINAL_STATUS,
                          next_action=RETRY_WITHIN_POLICY,
                          rule="transport-fejl FØR nogen levering")

    if a.terminal == CANCELLED:
        if a.emitted_prefix:
            # Præfikset er sandheden om hvad der nåede ud. Det gemmes NØJAGTIGT,
            # så UI og model-historik ikke kan skilles ad.
            return Settlement(ASSISTANT_MESSAGE, ui=FINALIZE, in_model_surface=True,
                              interrupted=True, next_action=END_INTERRUPTED,
                              rule="annulleret EFTER at bytes nåede ud")
        return Settlement(ASSISTANT_ATTEMPT, reason=CANCELLED_REASON, ui=CLEAR,
                          next_action=END_INTERRUPTED,
                          rule="annulleret FØR nogen bytes nåede ud")

    if a.terminal == MAX_TOKENS and har_indhold(a):
        # ALDRIG stille genforsøg: svaret er ægte, bare afkortet. Et genforsøg
        # ville kaste et gyldigt svar væk og betale for det samme igen.
        return Settlement(ASSISTANT_MESSAGE, ui=FINALIZE, in_model_surface=True,
                          interrupted=True, next_action=STOP_OR_CONTINUATION,
                          rule="max_tokens med gyldige blokke")

    if a.promotable_answer and not a.text_blocks:
        return Settlement(ASSISTANT_MESSAGE, ui=FINALIZE, in_model_surface=True,
                          next_action=CONTINUE,
                          rule="svarbærende thinking forfremmet")

    if a.tool_calls:
        return Settlement(ASSISTANT_MESSAGE, ui=FINALIZE, in_model_surface=True,
                          next_action=EXECUTE_TOOLS,
                          rule="værktøjskald, med eller uden tekst")

    if a.text_blocks:
        return Settlement(ASSISTANT_MESSAGE, ui=FINALIZE, in_model_surface=True,
                          next_action=CONTINUE, rule="tekstsvar")

    # Herfra er der hverken tekst, kald eller forfremmet svar.
    #
    # DEN HÅRDE INVARIANT: er der sendt bytes, KAN det ikke være tomt. Netop den
    # fejl har brændt før — en falsk empty_completion fik fallback'en til at
    # slette det svar brugeren sad og så på.
    assert not a.emitted_prefix, (
        "EMPTY_RESPONSE med et sendt præfiks: der ER leveret bytes, så svaret "
        "findes. Klassificér det i stedet for at kalde det tomt."
    )

    if a.reasoning_blocks:
        # Privat ræsonnement er aldrig i sig selv et svar.
        return Settlement(ASSISTANT_ATTEMPT, reason=EMPTY_RESPONSE, ui=TERMINAL_STATUS,
                          next_action=RETRY_WITHIN_POLICY,
                          rule="kun privat ræsonnement")

    return Settlement(ASSISTANT_ATTEMPT, reason=EMPTY_RESPONSE, ui=TERMINAL_STATUS,
                      next_action=RETRY_WITHIN_POLICY,
                      rule="tomt svar")


# ── nøjagtig én afregning pr. forsøg ─────────────────────────────────────

class AlreadySettled(RuntimeError):
    """Forsøget er afregnet. En anden afregning ville være en anden historik."""


class StaleAttempt(RuntimeError):
    """En forsinket pumpe forsøgte at skrive efter afregningen."""


class AttemptLedger:
    """Holder styr på hvilke forsøg der er afregnet, og lukker dem for skrivning.

    Spec: «prevent stale provider pumps from appending after an attempt has
    settled» og «exactly one terminal frame ... per attempt».

    ## Hvorfor det ikke kan overlades til kaldestedet

    En udbyder-pumpe er en tråd eller en opgave der læser videre fra en
    forbindelse. Når et forsøg afregnes — fordi brugeren annullerede, fordi
    timeouten løb ud, eller fordi failover valgte en anden udbyder — ved den
    gamle pumpe det ikke. Den fortsætter, og dens næste delta ville skrive ind
    i en historik der allerede er afsluttet.

    Resultatet er ikke en fejl man ser: det er en samtale hvor der pludselig
    står to halve svar oven i hinanden, uden at noget har fejlet.

    Derfor er lukningen bundet til `attempt_id` og håndhævet HER, frem for at
    være noget hver pumpe skulle huske at tjekke.

    ## Pr. proces, ikke i databasen

    Et forsøg lever i én proces fra start til afregning. Var registret i
    databasen, ville det koste en skrivning pr. delta for at beskytte mod noget
    der kun kan ske inden for samme proces.
    """

    def __init__(self) -> None:
        self._afregnet: dict[str, Settlement] = {}
        self._rammer: dict[str, int] = {}

    # ── rammer ───────────────────────────────────────────────────────────
    def next_frame(self, attempt_id: str) -> int:
        """Næste rammesekvens. Kaster hvis forsøget er afregnet."""
        aid = str(attempt_id)
        if aid in self._afregnet:
            raise StaleAttempt(
                f"forsøg {aid!r} er afregnet som {self._afregnet[aid].event!r} — "
                "en forsinket pumpe kan ikke sende flere rammer"
            )
        n = self._rammer.get(aid, 0) + 1
        self._rammer[aid] = n
        return n

    def frames(self, attempt_id: str) -> int:
        return self._rammer.get(str(attempt_id), 0)

    # ── afregning ────────────────────────────────────────────────────────
    def settle(self, attempt_id: str, settlement: Settlement) -> Settlement:
        """Afregn ÉN gang. Et andet forsøg er en fejl, ikke en opdatering."""
        aid = str(attempt_id)
        if aid in self._afregnet:
            raise AlreadySettled(
                f"forsøg {aid!r} er allerede afregnet som "
                f"{self._afregnet[aid].event!r}/{self._afregnet[aid].reason!r}"
            )
        self._afregnet[aid] = settlement
        return settlement

    def settled(self, attempt_id: str) -> Settlement | None:
        return self._afregnet.get(str(attempt_id))

    def is_settled(self, attempt_id: str) -> bool:
        return str(attempt_id) in self._afregnet

    def guard(self, attempt_id: str) -> None:
        """Kaster hvis forsøget er afregnet. Til pumper der vil skrive."""
        if self.is_settled(attempt_id):
            raise StaleAttempt(f"forsøg {attempt_id!r} er afregnet")
