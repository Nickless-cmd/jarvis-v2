"""Gentagelses-vagt (5/11-2026) — fang "sagde det samme igen, intet er ændret".

Bjørn, 5/11: «din gentagelser uden ændring er en anden sag». Målt samme aften tre
gange: tre batch-instrukser i prompten, en beslutning, to rundebudget-varsler. Alle
er SÆTNINGER i konteksten og ingen flyttede adfærd — en regel man beder om, er en
regel man kan overhøre.

Hollow-promise-vagten flytter adfærd fordi den ikke BEDER: den LÆSER det endelige
svar og indlægger en korrektion midt i turen. Dette er samme form, anden fejl.

Rent + side-effekt-frit → unit-testbart. Integreres i visible_runs lige efter
hollow-promise-blokken: ét nudge-round, cap 1 pr. run, fail-open til normal break
ved enhver tvivl/fejl.

Lighed måles med de shingle/Jaccard-hjælpere der allerede findes i
`sensory_perception_bridge` — de er ikke duplikeret her.
"""
from __future__ import annotations

import os
import re

from core.services.sensory_perception_bridge import _jaccard, _shingle

_ENV = "JARVIS_REPETITION_GUARD"
_STATE_KEY = "repetition_guard_enabled"
_TRUTHY = {"1", "true", "yes", "on"}
_FALSY = {"0", "false", "no", "off"}

REPETITION_NUDGE = (
    "Dit sidste svar gentager et tidligere svar i denne session uden at noget er "
    "ændret. Gør nu ét af tre: (a) gør noget der ændrer tilstanden — kald et "
    "værktøj eller ret noget; (b) eskalér tydeligt til Bjørn, så det fremgår hvad "
    "der blokerer; eller (c) tie, hvis der ikke er mere at sige."
)

# Hvor mange af de seneste svar vi sammenligner med, og hvor ens svaret skal være.
# Bevidst højt: en falsk positiv bryder en tur, en misset gentagelse koster en sætning.
DEFAULT_WINDOW = 5
DEFAULT_THRESHOLD = 0.8
# Under dette antal ord er ligheden meningsløs («Ja.», «Kører.») — korte svar
# gentages legitimt.
MIN_WORDS = 12

# NY INFORMATION: tal, filnavne, commit-hashes. Har svaret ét sådant som ingen af de
# tidligere svar har, ER noget ændret — uanset hvor ens resten er.
_NUMBER = re.compile(r"\d+(?:[.,:]\d+)*")
_FILENAME = re.compile(r"[\w./-]*\w\.(?:py|md|json|jsonl|txt|ts|tsx|js|jsx|css|html|yml|yaml|toml|sh|sql|db|log|cfg|ini)\b", re.IGNORECASE)
_HASH = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b", re.IGNORECASE)
_PUNCT = re.compile(r"[^\w\s]")


def _fact_tokens(text: str) -> set[str]:
    """Konkrete fakta i teksten: tal, filnavne, hashes (lowercased)."""
    t = text or ""
    ud: set[str] = set()
    for rx in (_NUMBER, _FILENAME, _HASH):
        ud.update(m.group(0).lower() for m in rx.finditer(t))
    return ud


def _normaliser(text: str) -> str:
    """Tegnsætning væk, så «færdig.» og «færdig» ikke tæller som forskellige ord."""
    return _PUNCT.sub(" ", (text or "").lower())


def is_repetition(
    final_text: str,
    previous_texts: list[str] | tuple[str, ...],
    nudged_already: bool = False,
    window: int = DEFAULT_WINDOW,
    threshold: float = DEFAULT_THRESHOLD,
    min_words: int = MIN_WORDS,
) -> bool:
    """Gentagelse = svaret ligner et af de seneste svar + ingen ny information.

    `previous_texts` er tidligere Jarvis-svar i SAMME session, ældste først. Kun de
    seneste `window` sammenlignes. Konservativ: enhver tvivl → False (→ nuværende
    adfærd). Self-safe."""
    try:
        if nudged_already:
            return False
        text = (final_text or "").strip()
        if not text:
            return False
        if len(_normaliser(text).split()) < min_words:
            return False
        prev = [str(p) for p in list(previous_texts or [])[-max(int(window), 1):] if p and str(p).strip()]
        if not prev:
            return False
        # Ny information trumfer lighed: nyt filnavn/tal/hash = noget er ændret.
        kendte: set[str] = set()
        for p in prev:
            kendte |= _fact_tokens(p)
        if _fact_tokens(text) - kendte:
            return False
        mine = _shingle(_normaliser(text))
        return any(_jaccard(mine, _shingle(_normaliser(p))) >= threshold for p in prev)
    except Exception:  # noqa: BLE001 — enhver tvivl skal give NUVÆRENDE adfærd (False), aldrig bryde turen
        return False


def previous_assistant_texts(session_id: str, limit: int = 12) -> list[str]:
    """Jarvis' seneste svar i sessionen, ældste først. Self-safe → [] ved fejl."""
    try:
        from core.services.chat_sessions import recent_chat_session_messages
        rows = recent_chat_session_messages(str(session_id or ""), limit=limit)
        return [str(r.get("content") or "") for r in rows if r.get("role") == "assistant"]
    except Exception:  # noqa: BLE001 — uden historik er der intet at sammenligne; vagten maa ikke vaelte turen
        return []


def should_nudge(final_text: str, session_id: str | None) -> bool:
    """Produktions-indgangen: flag + sessionens seneste svar + is_repetition."""
    return repetition_guard_enabled() and is_repetition(
        final_text, previous_assistant_texts(session_id or ""))


def repetition_guard_enabled() -> bool:
    """Default TRUE. Env `JARVIS_REPETITION_GUARD` vinder; ellers runtime-state
    `repetition_guard_enabled`. Fail-safe: tvivl → True. Selve guard-BLOKKEN i
    visible_runs er try/except → fail-open til normal break, så 'on' aldrig kan
    brække runtimen — flaget styrer kun OM vagten forsøger."""
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
    except Exception:  # noqa: BLE001 — kan flaget ikke laeses, behandles det som TIL; blokken selv er fail-open
        return True
