"""TEMP diagnostic (2026-07-18): process-wide stall sampler.

Formål: nail hvad prompt-assembly'ens ~4s baseline + intermitterende multi-sekund-
spikes FAKTISK er — CPU/GIL (tråd fast i numpy/BM25/parse), ollama-I/O (fast i
httpx-embed), eller DB-lås (tråde fast i sqlite). Sampler alle tråde hvert 200ms;
når en tråd sidder i SAMME app-frame >1,5s, logger den den tråds frame + ALLE
tråde's top-app-frames i det øjeblik → et øjebliksbillede af hvem der holder hvad.

Self-safe, idempotent start, daemon-tråd. FJERNES efter diagnosen.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time

logger = logging.getLogger(__name__)

_started = False
_lock = threading.Lock()
_STUCK_S = 1.5          # sektion regnes "fast" efter dette
_REDUMP_S = 4.0         # rate-limit pr. tråd
_SAMPLE_S = 0.2


def _top_app_frame(frame) -> str:
    """Dybeste core/apps-frame i stakken (det der reelt kører/venter)."""
    picked = ""
    f = frame
    while f is not None:
        fn = f.f_code.co_filename
        if ("/core/" in fn or "/apps/" in fn) and "_assembly_stall_probe" not in fn:
            picked = f"{os.path.basename(fn)}:{f.f_code.co_name}:{f.f_lineno}"
        f = f.f_back
    return picked or "(non-app)"


def _sampler() -> None:
    last: dict[int, tuple[str, float]] = {}
    dumped: dict[int, float] = {}
    while True:
        try:
            now = time.monotonic()
            snap = {tid: _top_app_frame(fr) for tid, fr in sys._current_frames().items()}
            for tid, fs in snap.items():
                prev = last.get(tid)
                if prev and prev[0] == fs and fs != "(non-app)":
                    stuck = now - prev[1]
                    if stuck > _STUCK_S and (now - dumped.get(tid, 0.0)) > _REDUMP_S:
                        dumped[tid] = now
                        allf = " || ".join(
                            f"{s}" for t, s in snap.items() if s != "(non-app)")
                        print(
                            f"[STALL-PROBE] stuck={stuck:.1f}s in {fs} "
                            f"| n_app_threads={sum(1 for s in snap.values() if s!='(non-app)')} "
                            f"| ALL=[{allf[:700]}]",
                            file=sys.stderr, flush=True,
                        )
                elif not prev or prev[0] != fs:
                    last[tid] = (fs, now)
        except Exception:
            pass
        time.sleep(_SAMPLE_S)


def ensure_started() -> None:
    """Idempotent — starter sampler-daemonen første gang. Self-safe."""
    global _started
    try:
        with _lock:
            if _started:
                return
            _started = True
            threading.Thread(
                target=_sampler, name="assembly-stall-probe", daemon=True
            ).start()
    except Exception:
        pass
