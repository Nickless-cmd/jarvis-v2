"""Hvor længe tænkte han? — målt ét sted, læst ét sted.

Ræsonneringens TEKST er allerede persisteret (`chat_messages.reasoning_content`).
Det der manglede, var VARIGHEDEN — og uden den kan klienten ikke vise ChatGPT's
sammenfoldede «Tænkte i 14 s ›», kun en linje uden tal.

Målingen hører hjemme dér hvor tænkningen faktisk åbner og lukker
(`visible_runs_sse_v2._open_thinking_block` / `_close_thinking_block_if_open`),
men skal LÆSES et helt andet sted (ved persistering af turen). Derfor dette
lille mellemled frem for at trække en ny parameter gennem hele run-løkken:
`visible_runs.py` er 6.956 linjer, og en ekstra gennemgående parameter dér ville
koste mere end den er værd.

Kortet er bevidst i hukommelsen og bevidst lille. Går api'en ned mellem åbning
og persistering, mister vi ét varighedstal — ikke ræsonneringen selv. Det er en
acceptabel pris for ikke at skulle skrive til DB'en midt i en stream.
"""
from __future__ import annotations

import threading
import time

# Nok til de runs der kan være i luften samtidig, med rigelig margen.
_MAX_ENTRIES = 256

_lock = threading.Lock()
# run_id -> (start_monotonic, end_monotonic | None)
_marks: "dict[str, tuple[float, float | None]]" = {}


def _evict_if_needed() -> None:
    """Hold kortet lille. Ældste post ryger — kaldes altid under _lock."""
    while len(_marks) > _MAX_ENTRIES:
        oldest = min(_marks, key=lambda k: _marks[k][0])
        _marks.pop(oldest, None)


def mark_start(run_id: str) -> None:
    """Første tænke-blok i turen. Senere kald ignoreres.

    En tur kan åbne flere tænke-blokke (én pr. runde). Bjørn skal se ÉN linje
    for turen, ikke én pr. runde — derfor vinder det første starttidspunkt.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return
    with _lock:
        if rid in _marks:
            return
        _marks[rid] = (time.monotonic(), None)
        _evict_if_needed()


def mark_end(run_id: str) -> None:
    """Seneste tænke-blok lukkede. Sidste lukning vinder — se mark_start."""
    rid = str(run_id or "").strip()
    if not rid:
        return
    with _lock:
        entry = _marks.get(rid)
        if entry is None:
            return
        _marks[rid] = (entry[0], time.monotonic())


def take_seconds(run_id: str) -> float | None:
    """Varigheden i sekunder, og RYD posten. None hvis der ikke blev tænkt.

    Ryddes fordi tallet hører til ÉN persisteret tur; bliver det liggende, ville
    en senere tur i samme run kunne arve en fremmed varighed.
    """
    rid = str(run_id or "").strip()
    if not rid:
        return None
    with _lock:
        entry = _marks.pop(rid, None)
    if entry is None:
        return None
    start, end = entry
    # Blev blokken aldrig lukket (afbrudt stream), måler vi frem til nu — det er
    # sandere end at kaste tallet væk: han tænkte faktisk i den tid.
    stop = end if end is not None else time.monotonic()
    # Afrund FØR vi vurderer om der blev tænkt. Gør man det omvendt, slipper en
    # måling på 20 ms igennem som «0,0 s» — og «Tænkte i 0 s» er ikke en
    # oplysning, det er støj. Runder tallet til nul, blev der ikke tænkt.
    seconds = round(stop - start, 1)
    return seconds if seconds > 0 else None


def peek_seconds(run_id: str) -> float | None:
    """Som take_seconds, men uden at rydde. Til observation/test."""
    rid = str(run_id or "").strip()
    with _lock:
        entry = _marks.get(rid)
    if entry is None:
        return None
    start, end = entry
    stop = end if end is not None else time.monotonic()
    seconds = round(stop - start, 1)
    return seconds if seconds > 0 else None
