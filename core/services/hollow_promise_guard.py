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
]
_PROMISE_RE = [re.compile(p, re.IGNORECASE) for p in _PROMISE_PATTERNS]

# Billig negativ-guard: slutter svaret på et spørgsmål → afventer brugeren (ikke tom løfte).
_QUESTION_TAIL = re.compile(r"[?]\s*$")


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
        return any(rx.search(t) for rx in _PROMISE_RE)
    except Exception:
        return False


def is_hollow_promise(
    final_text: str,
    total_tool_calls: int,
    user_message: str = "",
    nudged_already: bool = False,
) -> bool:
    """Tom løfte = lovede handling + NUL tool-kald hele runnet + ikke allerede nudget.

    Konservativ: enhver tvivl → False (→ nuværende adfærd). `user_message` accepteres til
    fremtidig request-intent-gating men KRÆVES ikke (løfte+nul-tool er allerede stærkt +
    provider-agnostisk). Self-safe."""
    try:
        if nudged_already:
            return False
        if int(total_tool_calls) != 0:       # et tool KØRTE → ikke tomt
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
