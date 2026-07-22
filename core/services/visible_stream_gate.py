"""In-process real-time gate: is a VISIBLE turn actively assembling/streaming right now?

ROD (bevist 2026-07-22): DeepSeek svarer på ~600ms, MEN når private baggrunds-LLM-lag
(inner_voice_shadow spawner 7 fire-and-forget tråde, cheap-lane-ticks, post-process)
kører SAMTIDIG med en synlig tur på samme proces, sulter Pythons GIL den synlige turs
SSE-læser → TTFT hopper fra 600ms til 8-9s (målt: isoleret 621ms → under 7 tråde 9052ms).

CLAUDE.md: de private lag må ALDRIG udrangere den beskyttede kerne — og den synlige
chat-lane ER kernen. Denne gate håndhæver det: mens en synlig tur assembler/streamer,
udskyder de private LLM-lag deres arbejde (de er observe-only/eksperimentelle og fyrer
igen næste cadence — intet tabes).

In-process (ikke DB): signalet skal være real-time og gratis at læse tusindvis af gange.
Tæller (ikke bool) så samtidige synlige ture nestes korrekt. Fail-open: enhver fejl →
``visible_streaming()`` returnerer False (privat arbejde kører hellere end at fryse).
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import Iterator

_lock = threading.Lock()
_active = 0


def visible_streaming() -> bool:
    """True hvis mindst én synlig tur i øjeblikket assembler/streamer i denne proces.

    Baggrunds-LLM-lag tjekker dette FØR de fyrer et LLM-kald og udskyder hvis True.
    Fail-open (aldrig kast)."""
    try:
        return _active > 0
    except Exception:
        return False


def enter_visible_stream() -> None:
    global _active
    with _lock:
        _active += 1


def exit_visible_stream() -> None:
    global _active
    with _lock:
        if _active > 0:
            _active -= 1


@contextmanager
def visible_stream() -> Iterator[None]:
    """Context manager: markér at en synlig tur er aktiv i dens levetid. Self-safe —
    tælleren dekrementeres altid i finally, også ved exception/abort."""
    enter_visible_stream()
    try:
        yield
    finally:
        exit_visible_stream()
