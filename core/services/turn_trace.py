"""core/services/turn_trace.py

Gated ende-til-ende turn-tracer: fra request-in (Bjørns ENTER) til det øjeblik
prompten forlader huset mod deepseek. Timer HVER assembly-sektion, HVERT LLM/
embed-kald (med lane/model/varighed/tråd) og de daemons der fyrer under en
assembly — så vi kan se præcist hvor vores-side-sekunderne går (deepseek's egne
3-5s ligger EFTER prompt_leaves og trækkes fra).

INERT medmindre sentinel-filen findes:  touch /tmp/jarvis-turn-trace
Dumper hele tidslinjen til /tmp/jarvis-turn-trace-dumps/latest.json ved
prompt_leaves. Global (ikke contextvar) så den fanger kald i executor-/daemon-
tråde OGSÅ — brug til ÉN solo-tur ad gangen (samtidige ture interleaver).
Self-safe: kaster aldrig, tilføjer ~0 latency når slukket.
"""
from __future__ import annotations

import os
import threading
import time

_SENTINEL = "/tmp/jarvis-turn-trace"
_DUMP_DIR = "/tmp/jarvis-turn-trace-dumps"
_lock = threading.Lock()
_events: list[dict] = []
_t0: list[float | None] = [None]
_on: list[bool] = [False]


def _sentinel() -> bool:
    try:
        return os.path.exists(_SENTINEL)
    except Exception:
        return False


def active() -> bool:
    return _on[0]


def start(label: str = "") -> None:
    """Nulstil tidslinjen ved request-in. No-op uden sentinel."""
    if not _sentinel():
        _on[0] = False
        return
    try:
        with _lock:
            _on[0] = True
            _t0[0] = time.monotonic()
            _events.clear()
            _events.append({
                "off_ms": 0, "kind": "request_in", "label": label[:100],
                "dur_ms": None, "thread": threading.current_thread().name,
            })
    except Exception:
        pass


def mark(kind: str, label: str = "", dur_ms: int | None = None) -> None:
    """Tilføj ét event + print en LIVE-linje til stderr (så ruten kan følges i
    realtid via `journalctl -fu jarvis-api | grep TURN-LIVE`). No-op når slukket."""
    if not _on[0] or _t0[0] is None:
        return
    try:
        off = int((time.monotonic() - _t0[0]) * 1000)
        th = threading.current_thread().name
        with _lock:
            _events.append({
                "off_ms": off, "kind": kind, "label": str(label)[:100],
                "dur_ms": dur_ms, "thread": th,
            })
        import sys as _s
        _d = f" +{dur_ms}ms" if dur_ms is not None else ""
        print(f"TURN-LIVE @{off:>6}ms  {kind:<14} {str(label)[:60]}{_d}  [{th}]",
              file=_s.stderr, flush=True)
    except Exception:
        pass


def dump(reason: str = "") -> None:
    """Skriv hele tidslinjen til latest.json + kompakt stderr-resumé, og sluk."""
    if not _on[0]:
        return
    try:
        import json
        import sys
        with _lock:
            evs = list(_events)
            _on[0] = False
        os.makedirs(_DUMP_DIR, exist_ok=True)
        total = evs[-1]["off_ms"] if evs else 0
        n_llm = sum(1 for e in evs if e["kind"] == "llm")
        n_embed = sum(1 for e in evs if e["kind"] == "embed")
        with open(_DUMP_DIR + "/latest.json", "w", encoding="utf-8") as fh:
            json.dump({
                "reason": reason, "total_ms": total,
                "n_events": len(evs), "n_llm": n_llm, "n_embed": n_embed,
                "events": evs,
            }, fh, indent=2, ensure_ascii=False)
        print(f"TURN-TRACE dump ({reason}) total_ms={total} events={len(evs)} "
              f"llm={n_llm} embed={n_embed} -> {_DUMP_DIR}/latest.json",
              file=sys.stderr, flush=True)
    except Exception:
        pass
