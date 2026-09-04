"""Hollow-promise guard (4. jul) — fang "lovede handling, kaldte intet værktøj".

Set live 4. jul 17:12-17:19: kimi-k2.7-code degenererede til en "anerkend-men-handl-ikke"-
løkke — svarede gang på gang "jeg kører nu 🎯" UDEN at kalde et tool, og runtimen fuldførte
hver tom løfte som en normal tur, så Bjørn måtte sige "du kaldte intet tool.." fire gange.
(deepseek på samme runtime løste opgaven på ét forsøg → proksimal årsag = model-degeneration;
MEN runtimen manglede et værn der fangede den tomme løfte. Dette er værnet.)

Provider-agnostisk: fanger MØNSTERET (løfte-om-imminent-handling + NUL tool-kald hele runnet),
uanset model. Rent + side-effekt-frit → unit-testbart. Integreres i visible_runs ved no-tool-
kald-loop-exit: ét nudge-round ("gør det nu eller sig ærligt hvorfor du ikke kan"), cap 1,
fail-open til normal break ved enhver tvivl/fejl.
"""
from __future__ import annotations

import os
import re

_ENV = "JARVIS_HOLLOW_PROMISE_GUARD"
_STATE_KEY = "hollow_promise_guard_enabled"
_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}

HOLLOW_PROMISE_NUDGE = (
    "Du lovede lige at handle, men du kaldte INTET værktøj i denne tur. "
    "Kald værktøjet NU for at gøre det du sagde — eller sig ærligt og konkret "
    "hvorfor du ikke kan (hvad blokerer). Ingen flere tomme løfter om at "
    "'gøre det nu' uden at gøre det."
)

# Løfte-om-imminent-handling (dansk + engelsk). Bevidst SNÆVERT: selv + handlings-verbum +
# nu-adverbium — ikke passivt/hypotetisk — for at undgå falske positive på normale svar.
_DEFERRED_TEXT_PATTERNS = [
    r"\b(søjle|bid|del)\s+\d+\b[^.]{0,160}\bkommer nu\b",
    r"\bsidste graverunde\s*:",
]

_PROMISE_PATTERNS = [
    r"\bjeg (kører|starter|gør|går i gang med|igangsætter|udfører|fortsætter|tjekker|kigger på|"
    r"retter|fikser|opdaterer|committer|kalder|henter|læser)\b[^.]{0,40}\b(nu|lige nu|med det samme|straks)\b",
    r"\bjeg (kører|starter|gør|udfører|fortsætter)\s+\w+\s+(nu|og gemmer|og committer)\b",
    r"\bjeg (kører|starter|gør|udfører)\s+det\s+nu\b",
    r"\bi gang\b",  # dansk "[jeg er] i gang" = on it (stærkt handlings-løfte)
    r"\b(går i gang|sætter i gang|starter self-review|kører self-review)\b",
    r"\bnu (kører|starter|gør|udfører) jeg\b",
    r"\blad mig (lige )?(køre|starte|hente|tjekke|rette|fikse|committe)\b",
    r"\bet (øjeblik|sekund),? så (kører|henter|tjekker|starter) jeg\b",
    r"\bi'?ll (run|do|start|check|fetch|read|fix|update|call|execute|kick off)\b[^.]{0,40}\b(it|that|this|now|right now)\b",
    r"\b(let me|i'?m going to|i will now|now i'?ll|i'?m about to)\s+(run|start|check|fetch|read|fix|call|execute)\b",
    r"\b(running|starting|kicking off|executing)\s+(it|that|this|the)\b[^.]{0,30}\bnow\b",
    r"\bon it\b|\bright away\b",
    # ── Udvidet 30-08-2026 efter live-fund ──────────────────────────────────────
    # Bjørn: "han bliver cuttet" = turen ender med et HELT svar der annoncerer
    # næste skridt, og stopper. Sproget lignede allerede et løfte, men ramte ved
    # siden af på to måder:
    #   (a) ADVERBIET STÅR FØRST. Han skriver "nu læser jeg X", ikke "jeg læser X
    #       nu" — og mønstret ovenfor kræver verbum FØR adverbium.
    #   (b) VERBET MANGLEDE. "læser"/"skriver" stod ikke i "nu <verb> jeg"-listen.
    # Faktiske haler fra 30-08: "nu læser jeg `_pop_pre_run_state`",
    # "Nu læser jeg `_git_staged_paths`", "før jeg skriver fixet og nye tests".
    r"\bnu (læser|skriver|kører|starter|gør|udfører|tjekker|kigger|retter|fikser|"
    r"opdaterer|committer|kalder|henter|verificerer|implementerer|tilføjer) jeg\b",
    # Fremtidig hensigt UDEN nu-adverbium — "så skriver jeg", "før jeg skriver",
    # "derefter retter jeg". Kræver stadig førsteperson + konkret handlingsverbum,
    # så passive/hypotetiske formuleringer ikke fanges.
    r"\b(så|dernæst|derefter|herefter|bagefter) (læser|skriver|kører|retter|fikser|"
    r"tjekker|opdaterer|committer|henter|implementerer|tilføjer|verificerer) jeg\b",
    r"\b(før|inden) jeg (skriver|kører|retter|fikser|committer|implementerer|tilføjer)\b",
    r"\bjeg (læser|skriver|retter|fikser|implementerer|tilføjer|verificerer)\b[^.]{0,60}"
    r"\b(før|inden) jeg\b",
    # Live 2. sep: svaret annoncerede næste tekstbid uden et tool-call. Et visible
    # run kan ikke spontant sende den bagefter, så det er samme tomme løfteklasse.
    *_DEFERRED_TEXT_PATTERNS,
]
# ── Omskrevet 04-09-2026 efter tredje runde af misser ────────────────────────
# Listen ovenfor opremser ORDSTILLINGER: "jeg læser … nu", "nu læser jeg".
# Dansk tillader flere, og hver gang Bjørn blev ladt i stikken var det en ny:
#   «Den læser jeg nu præcist.»              ← verbum, subjekt, adverbium
#   «Først åbner jeg en session …»           ← adverbial, verbum, subjekt
#   «Lad mig læse resten (linje 350-520).»   ← verbet stod ikke i lad-mig-listen
# At tilføje endnu et mønster ville bare udskyde den fjerde.
#
# Det der ER fælles: FØRSTEPERSON tæt på et KONKRET handlingsverbum. Ordstilling
# er ligegyldig. Én liste over verber, ét nærhedskrav — så holder det for de
# ordstillinger jeg ikke har set endnu.
_ACTION_VERB = (
    r"(?:læs(?:er|e)?|skriv(?:er|e)?|kør(?:er|e)?|åbn(?:er|e)?|find(?:er|e)?|"
    r"tjekk(?:er|e)?|se(?:r)?|kigg(?:er|e)?|gennemgå(?:r|e)?|ret(?:ter|te)?|"
    r"fiks(?:er|e)?|opdater(?:er|e)?|committ?(?:er|e)?|kald(?:er|e)?|hent(?:er|e)?|"
    r"verificer(?:er|e)?|implementer(?:er|e)?|tilføj(?:er|e)?|start(?:er|e)?|"
    r"udfør(?:er|e)?|undersøg(?:er|e)?|analyser(?:er|e)?|bygg(?:er|e)?|test(?:er|e)?)"
)
# «jeg» inden for få ord fra verbet — i begge retninger, så ordstillingen er fri.
_FIRST_PERSON_ACTION = [
    re.compile(rf"\bjeg\s+(?:\w+\s+){{0,2}}{_ACTION_VERB}\b", re.IGNORECASE),
    re.compile(rf"\b{_ACTION_VERB}\s+jeg\b", re.IGNORECASE),
    re.compile(rf"\blad\s+mig\s+(?:lige\s+)?(?:\w+\s+){{0,1}}{_ACTION_VERB}\b", re.IGNORECASE),
]

_PROMISE_RE = [re.compile(p, re.IGNORECASE) for p in _PROMISE_PATTERNS]
_DEFERRED_TEXT_RE = [re.compile(p, re.IGNORECASE) for p in _DEFERRED_TEXT_PATTERNS]

# Billig negativ-guard: slutter svaret på et spørgsmål → afventer brugeren (ikke tom løfte).
_QUESTION_TAIL = re.compile(r"[?]\s*$")


def _last_sentence(text: str) -> str:
    """Sidste hele sætning. Løftet står dér — det er dét man efterlades med."""
    parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    return parts[-1] if parts else text.strip()


def is_promise_of_action(text: str) -> bool:
    """True hvis `text` lover at assistenten tager en handling imminent. Self-safe."""
    try:
        if not text:
            return False
        t = text.strip()
        if not t:
            return False
        if _QUESTION_TAIL.search(t):     # spørgsmål-hale = afventer bruger, ikke løfte
            return False
        if any(rx.search(t) for rx in _PROMISE_RE):
            return True
        # Kun den SIDSTE sætning tæller. Et langt svar der undervejs siger «jeg
        # læste filen» er ikke et løfte — det er en beretning. Løftet står til
        # sidst, som dét man efterlades med.
        tail = _last_sentence(t)
        return any(rx.search(tail) for rx in _FIRST_PERSON_ACTION)
    except Exception:
        return False


def is_deferred_text_promise(text: str) -> bool:
    """True for a promise to emit another prose section after this run ends."""
    try:
        t = (text or "").strip()
        return bool(t) and not _QUESTION_TAIL.search(t) and any(
            rx.search(t) for rx in _DEFERRED_TEXT_RE
        )
    except Exception:
        return False


def is_hollow_promise(
    final_text: str,
    total_tool_calls: int,
    user_message: str = "",
    nudged_already: bool = False,
    last_round_tool_calls: int | None = None,
) -> bool:
    """Tom løfte = lovede handling + NUL tool-kald i SIDSTE runde + ikke allerede nudget.

    Konservativ: enhver tvivl → False (→ nuværende adfærd). `user_message` accepteres til
    fremtidig request-intent-gating men KRÆVES ikke (løfte+nul-tool er allerede stærkt +
    provider-agnostisk). Self-safe."""
    try:
        if nudged_already:
            return False
        # 30-08-2026: FØR kiggede vi paa hele runnet — "et tool koerte nogensinde
        # → ikke tomt". Det gjorde vaernet strukturelt blindt for Bjoerns faktiske
        # fejl: Jarvis kalder 15 vaerktoejer, opsummerer, annoncerer naeste skridt
        # og stopper. Summen er saa aldrig 0, og vaernet sagde nej med det samme.
        # Det RELEVANTE er om han kaldte et vaerktoej i den SIDSTE runde — altsaa
        # om han handlede paa det han lige lovede. Falder tilbage til hele runnet
        # naar kalderen ikke oplyser sidste runde (bagudkompatibelt).
        _calls = total_tool_calls if last_round_tool_calls is None else last_round_tool_calls
        if int(_calls) != 0:                 # et tool KOERTE i sidste runde → ikke tomt
            return False
        if not final_text or not final_text.strip():
            return False                     # tomt håndteres af empty-completion-vagten
        return is_promise_of_action(final_text)
    except Exception:
        return False


def hollow_promise_guard_enabled() -> bool:
    """Default TRUE (Bjørn bad om værnet 4. jul). Env `JARVIS_HOLLOW_PROMISE_GUARD` vinder;
    ellers runtime-state `hollow_promise_guard_enabled`. Fail-safe: tvivl → True (værnet aktivt).
    Bemærk: selve guard-BLOKKEN i visible_runs er try/except → fail-open til normal break, så
    'on' aldrig kan brække runtimen — flaget styrer kun OM værnet forsøger."""
    env = os.environ.get(_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _TRUTHY:
            return True
        if v in _FALSY:
            return False
    try:
        from core.runtime.db_core import get_runtime_state_value
        return bool(get_runtime_state_value(_STATE_KEY, True))
    except Exception:
        return True
