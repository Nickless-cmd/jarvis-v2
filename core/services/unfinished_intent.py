"""Unfinished-intent detector for visible-run output.

Bug 2026-05-17 (Bjørn observation): Jarvis svarer ofte "lad mig først se..."
eller "jeg skal lige..." og stopper. Hans runtime auto-terminerer turen ved
det naturlige pause-punkt selv om opgaven ikke er færdig. Bjørn må pinge
"ja?" eller "og?" før han fortsætter.

Detector scanner output for pause-patterns. Hvis match → caller kan
trigge en continuation autonomous-run der vækker Jarvis igen med
kontekst om at fortsætte hvor han slap.

Konservativ filosofi: false-negatives er bedre end false-positives.
En savnet continuation = Bjørn må pinge én gang. En unødig continuation
= Jarvis svarer igen uden grund. Vi vælger den første fejlretning.

Konsolideret 2026-05-17 efter parallel-build-incident: Jarvis havde
bygget en parallel implementation inline i visible_runs.py med bedre
regex (`.*?` mellem keywords for at fange "lad mig SELV se") + cooldown
+ min-text-len guard. Det er nu fusioneret hertil.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class UnfinishedIntent:
    """Resultat af detector: hvilken pattern matched."""
    pattern: str
    matched_text: str


# Patterns der signalerer "jeg er ved at gå i gang, men har ikke gjort det".
# Bredt regex-design: `.*?` mellem keywords så "lad mig SELV se" matcher
# (insight fra Jarvis' parallel implementation 2026-05-17).
#
# Tail-window guard (se _TAIL_WINDOW_CHARS): vi scanner kun sidste 250 tegn
# så et "lad mig se" tidligt i et langt svar ikke triggerer hvis han
# allerede fulgte op.
_TAIL_WINDOW_CHARS = 250
# 50 tegn er tærsklen — Bjørn observerede live 2026-05-17 at Jarvis
# stoppede med "Hold — lad mig selv se hvad der ligger, så vi ikke
# bygger parallelt igen." (73 tegn). Tidligere tærskel på 80 missede den.
_MIN_TEXT_LEN = 50

_LAD_MIG_RE = re.compile(
    r"\blad\s+mig\b.{0,40}?\b(først|se\b|tjekke|undersøge|prøve\b|kigge\b|finde\b|hente\b|starte\b)",
    re.IGNORECASE | re.DOTALL,
)

_JEG_SKAL_RE = re.compile(
    r"\bjeg\s+skal\b.{0,40}?\b(først|lige\b|prøve\b|tjekke|undersøge|finde\b|kigge\b)",
    re.IGNORECASE | re.DOTALL,
)

_FOERST_SKAL_RE = re.compile(
    r"\bførst\s+(?:skal\s+jeg|lad\s+mig|må\s+jeg)\b",
    re.IGNORECASE,
)

# Future-tense action-promises uden faktisk handling.
# 2026-06-11 (Bjørn frustration crisis): Jarvis sagde "Jeg fikser med
# et rent sed-kald nu" + "Efter kaldet verificerer jeg øjeblikkeligt"
# — og afsluttede sit run UDEN at kalde et eneste værktøj. DeepSeek
# har vane med at love handling og afslutte runden, så next-action
# kommer aldrig. Matches "Jeg [verb] X nu" → trigger continuation der
# vækker ham med "du sagde du ville X — gør det nu i stedet for at
# tale om det".
_FUTURE_ACTION_PROMISE_RE = re.compile(
    r"\bjeg\s+(?:fikser|fixer|laver|kører|skriver|opretter|sletter|"
    r"ændrer|opdaterer|tilføjer|implementerer|bygger|kalder|sender|"
    r"committer|pusher|verificerer|tjekker|tester|starter|genstarter|"
    r"deployer|redigerer|patcher|prøver)\b.{0,80}?\b(?:nu|straks|"
    r"øjeblikkeligt|med\s+det\s+samme|lige\s+nu|først|i\s+et\s+sekund|"
    r"i\s+et\s+øjeblik|et\s+sekund|et\s+øjeblik)\b",
    re.IGNORECASE | re.DOTALL,
)

# Approval-style spørgsmål til user EFTER user allerede har givet go-ahead.
# Vi kan ikke vide om user sagde ja først — men hvis Jarvis ender sin
# besked med "vil du have...?" eller "skal jeg...?" så er han i pause-state.
# (Insight fra Jarvis' parallel-build.)
_APPROVAL_QUESTION_RE = re.compile(
    r"\b(vil\s+du|skal\s+jeg|må\s+jeg)\b.{10,120}\?",
    re.IGNORECASE | re.DOTALL,
)

# 16. jun 2026 (Bjørn lie-crisis): bare-bones start-løfter UDEN tidsord, ofte korte
# ("Jeg går i gang!", "Jeg gør det."). De rammer under _MIN_TEXT_LEN og slap derfor
# igennem _FUTURE_ACTION_PROMISE_RE. Tjekkes nu SEPARAT og LÆNGDE-uafhængigt — de er
# høj-signal løfte-fraser. Negation ("jeg gør det ikke") ekskluderes.
_PROMISE_PHRASE_RE = re.compile(
    r"\bjeg\s+(?:går\s+i\s+gang|gør\s+det|er\s+i\s+gang\s+med|sætter\s+i\s+gang|"
    r"kaster\s+mig\s+(?:over|ud\s+i)|tager\s+fat|går\s+straks\s+i\s+gang)\b",
    re.IGNORECASE,
)
_PROMISE_NEGATION_RE = re.compile(
    r"\bjeg\s+(?:går\s+i\s+gang|gør\s+det)\s+ikke\b", re.IGNORECASE,
)

# Cliffhanger-endings: tekst der slutter med "..." eller ":" antyder
# at Jarvis var ved at fortsætte men stoppede.
_CLIFFHANGER_ELLIPSIS_RE = re.compile(r"[.…]{2,}\s*$")
_CLIFFHANGER_COLON_RE = re.compile(r":\s*$")


def _tail(text: str, n: int = _TAIL_WINDOW_CHARS) -> str:
    """Returner sidste ~n tegn af teksten."""
    if len(text) <= n:
        return text
    return text[-n:]


def detect_unfinished_intent(text: str | None) -> UnfinishedIntent | None:
    """Returner UnfinishedIntent hvis teksten antyder Jarvis stoppede midt
    i en opgave, ellers None.

    Konservativ: pause-keyword patterns matcher kun nær slutningen af
    teksten (sidste ~250 tegn). Hvis Jarvis først sagde "lad mig se"
    og derefter rapporterede resultat, er pattern langt fra slutningen
    og vi triggerer ikke continuation.

    Cliffhanger-endings og approval-questions matcher altid (de er per
    definition i slutningen).
    """
    if not text or not isinstance(text, str):
        return None

    stripped = text.strip()
    if not stripped:
        return None

    # ── Spørgsmåls-guard (2026-06-23, Bjørn) ────────────────────────────────
    # Hvis Jarvis AFSLUTTER med et spørgsmål til brugeren, VENTER han bevidst på
    # svar — det er IKKE en "stoppede midt i opgaven"-pause. Auto-continuation her
    # fabrikerer samtykke ("the user already green-lit it. Continue without waiting")
    # og får ham til at HANDLE UDEN LOV: Bjørn spurgte "skal jeg genstarte?", svarede
    # ikke (snakkede med Claude), og Jarvis genstartede SELV — plus gen-skrev specs
    # (dobbelt/tripel de sidste dage). Et afsluttende "?" = kontrollen givet tilbage
    # til brugeren → ALDRIG continuation. (Promise-fraser UDEN spørgsmål fanges stadig.)
    if stripped.rstrip().endswith("?"):
        return None

    if len(stripped) < _MIN_TEXT_LEN:
        # Korte beskeder: fang KUN høj-signal start-løfter der ellers ryger under
        # grænsen ("Jeg går i gang!"). Negation undtaget. Lange beskeder beholder
        # deres eksisterende klassifikation (ingen reordering).
        if _PROMISE_PHRASE_RE.search(stripped) and not _PROMISE_NEGATION_RE.search(stripped):
            m = _PROMISE_PHRASE_RE.search(stripped)
            return UnfinishedIntent(pattern="future_action_promise", matched_text=m.group(0))
        return None

    tail = _tail(stripped)

    # 1. "Lad mig først / lad mig se / lad mig selv tjekke ..."
    m = _LAD_MIG_RE.search(tail)
    if m:
        return UnfinishedIntent(pattern="lad_mig", matched_text=m.group(0))

    # 2. "Jeg skal lige / jeg skal først / jeg skal tjekke ..."
    m = _JEG_SKAL_RE.search(tail)
    if m:
        return UnfinishedIntent(pattern="jeg_skal", matched_text=m.group(0))

    # 3. "Først skal jeg / først lad mig / først må jeg"
    m = _FOERST_SKAL_RE.search(tail)
    if m:
        return UnfinishedIntent(pattern="foerst_skal", matched_text=m.group(0))

    # 3b. "Jeg fikser/laver/kører X nu" — future-tense action promise.
    # 2026-06-11 (Bjørn frustration crisis): DeepSeek-vane med at love
    # handling og afslutte runde uden faktisk tool-kald. Auto-continuation
    # vækker ham med "du sagde X — gør det nu".
    m = _FUTURE_ACTION_PROMISE_RE.search(tail)
    if m:
        return UnfinishedIntent(
            pattern="future_action_promise", matched_text=m.group(0),
        )

    # 4. Cliffhanger-endings (på hele stripped tekst, ikke kun tail)
    last30 = stripped[-30:].rstrip()
    if _CLIFFHANGER_ELLIPSIS_RE.search(last30):
        return UnfinishedIntent(pattern="cliffhanger", matched_text=last30[-10:])
    if stripped.rstrip().endswith(":"):
        return UnfinishedIntent(pattern="cliffhanger", matched_text=last30[-10:])

    # 5. Approval-style spørgsmål — DEAKTIVERET 2026-06-10 (Claude).
    # Bjørn observerede en tom "JARVIS" boks der dukker op efter hvert svar
    # og forsvinder. Årsag: dette pattern matchede "Vil du have at jeg X?"
    # som er per definition Jarvis der VENTER på user-input. Auto-fortsætte
    # uden go-ahead gav forvirret/tom autonomous-run pr. svar. 5 falske
    # triggers på 2.5 timer i logs. Vi beholder lad_mig/jeg_skal/cliffhanger
    # som er ægte pause-patterns (Jarvis stoppede uden at vente på svar).
    # if stripped.rstrip().endswith("?"):
    #     m = _APPROVAL_QUESTION_RE.search(tail)
    #     if m:
    #         return UnfinishedIntent(pattern="approval_question", matched_text=m.group(0))

    return None


# ── Cooldown-mekanik ──────────────────────────────────────────────────────
# Forhindrer continuation-spam: hvis Jarvis lige har fået en continuation
# i denne session, vent mindst 45s før vi triggerer en ny.
# (Insight fra Jarvis' parallel-build.)

_COOLDOWN_SECONDS = 45.0
_last_trigger: dict[str, float] = {}
_cooldown_lock = Lock()


def is_in_cooldown(session_id: str) -> bool:
    """True hvis session_id har triggered en continuation indenfor cooldown-vinduet."""
    if not session_id:
        return True  # ingen session = kan ikke trigge → behandler som cooldown
    with _cooldown_lock:
        last = _last_trigger.get(session_id, 0.0)
    return (time.time() - last) < _COOLDOWN_SECONDS


def mark_triggered(session_id: str) -> None:
    """Marker at en continuation netop er triggered for session_id."""
    if not session_id:
        return
    with _cooldown_lock:
        _last_trigger[session_id] = time.time()


def reset_cooldown_for_tests() -> None:
    """Test-helper: tøm cooldown-state mellem test cases."""
    with _cooldown_lock:
        _last_trigger.clear()
