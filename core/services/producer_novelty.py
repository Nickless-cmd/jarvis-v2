"""core/services/producer_novelty.py

Observe-only instrumentering (Bjørn 3. jul): mål hvor NY hver cadence-producers LLM-output
er vs. dens EGNE seneste outputs. Lav nyhed = producer gentager sig selv (metronomen kører
tør) → kandidat til saliens-gating (tal når du er bevæget, ikke på et ur). Høj nyhed = ægte
nye tanker → lad den være.

FORMÅL: grundlag for at skifte indre liv fra TID-drevet → SALIENS-drevet UDEN at miste
stemmer/tanker. Vi MÅLER først (denne fase), gater bagefter bag reversible flags.

DESIGN: ren tekst-lighed (difflib) — INGEN ekstra LLM/embed-kald. Vi forsøger at REDUCERE
load (og kontention med Bjørns synlige svar), ikke øge den. Attribution sker via en thread-
local sat af cadence-scheduleren omkring hver producers run_fn; cheap-lane-kaldet (synkront
i samme tråd) læser den. Self-safe: kaster ALDRIG (samme kontrakt som central().observe).
"""
from __future__ import annotations

import threading
from collections import deque
from difflib import SequenceMatcher
from typing import Any

_current = threading.local()
_RECENT = 5                         # sammenlign mod de seneste N outputs pr. producer
_lock = threading.Lock()
_history: dict[str, deque] = {}     # producer → deque[str] (seneste normaliserede outputs)
_stats: dict[str, dict] = {}        # producer → {calls, novelty_sum}


def set_producer(name: str) -> None:
    """Sæt hvilken producer der kører NU (cadence-tråden). Self-safe."""
    try:
        _current.name = str(name or "")
    except Exception:
        pass


def clear_producer() -> None:
    try:
        _current.name = ""
    except Exception:
        pass


def get_producer() -> str:
    return getattr(_current, "name", "") or ""


def _similarity(a: str, b: str) -> float:
    try:
        return SequenceMatcher(None, a, b).ratio()
    except Exception:
        return 0.0


def record_output(producer: str, text: str) -> None:
    """Registrér en producers LLM-output + mål nyhed = 1 - (max-lighed vs dens seneste N).
    0.0 = identisk gentagelse (metronome), 1.0 = helt nyt. Records til central_timeseries
    (cluster='novelty', nerve=producer). Observe-only, self-safe."""
    try:
        p = (str(producer or "").strip() or "ukendt")
        t = " ".join(str(text or "").split())
        if not t:
            return
        with _lock:
            dq = _history.get(p)
            if dq is None:
                dq = deque(maxlen=_RECENT)
                _history[p] = dq
            max_sim = max((_similarity(t, prev) for prev in dq), default=0.0)
            dq.append(t)
            st = _stats.setdefault(p, {"calls": 0, "novelty_sum": 0.0})
            novelty = round(1.0 - max_sim, 3)
            st["calls"] += 1
            st["novelty_sum"] += novelty
            avg = round(st["novelty_sum"] / st["calls"], 3)
        try:
            from core.services import central_timeseries as ts
            ts.record("novelty", p, value=novelty,
                      meta={"calls": st["calls"], "avg_novelty": avg, "chars": len(t)})
        except Exception:
            pass
    except Exception:
        pass


def snapshot() -> dict[str, Any]:
    """Read-only overblik: pr. producer antal kald + gennemsnitlig nyhed. Lav avg = repetitiv
    (metronome kører tør) → saliens-gate-kandidat. Til Mission Control / analyse."""
    try:
        with _lock:
            return {p: {"calls": s["calls"],
                        "avg_novelty": round(s["novelty_sum"] / max(s["calls"], 1), 3)}
                    for p, s in sorted(_stats.items(), key=lambda kv: kv[1]["calls"], reverse=True)}
    except Exception:
        return {}


def _reset_for_tests() -> None:
    with _lock:
        _history.clear()
        _stats.clear()
    clear_producer()
