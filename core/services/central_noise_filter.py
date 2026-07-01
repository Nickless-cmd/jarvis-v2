"""core/services/central_noise_filter.py

Støjfangeren (Bjørn 1. jul: "den skal også have en støjfanger").

Rå observe-data er fuld af blips: én langsom decide, ét enkelt tomt daemon-tick, en
forbigående fejl. Hvis Centralen flagger/lærer af HVER udsving, drukner den i støj (og
et lærende system der lærer af støj bliver værre, ikke bedre — jf. §24.3 K1/K2).

Denne filter afgør om et signal er ÆGTE nok til at flagge/notificere/lære af. Et signal
slipper KUN igennem hvis det:
  1. PERSISTERER — bryder tærsklen ≥ min_persistence gange i træk (ét blip = støj, droppes).
  2. Ikke er en GENTAGELSE — samme tilstand er ikke allerede flagget inden for cooldown
     (så en vedvarende tilstand giver ÉT signal, ikke ét pr. tick = dedup).

Ren, deterministisk, per-nøgle-tilstand. Kaster aldrig.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass

_DEFAULT_MIN_PERSISTENCE = 2
_DEFAULT_COOLDOWN_S = 1800.0  # 30 min: samme vedvarende tilstand re-flagges højst hvert 30. min.


@dataclass
class _KeyState:
    consecutive: int = 0
    last_flag_monotonic: float | None = None  # None = aldrig flagget (0.0 er en gyldig tid)


_lock = threading.Lock()
_state: dict[str, _KeyState] = {}


def is_real_signal(
    key: str,
    breached: bool,
    *,
    min_persistence: int = _DEFAULT_MIN_PERSISTENCE,
    cooldown_s: float = _DEFAULT_COOLDOWN_S,
    now_monotonic: float | None = None,
) -> bool:
    """Returnér True KUN når ``breached`` har holdt i ≥min_persistence træk OG tilstanden
    ikke er flagget inden for cooldown. Ellers False (= støj eller allerede kendt).

    ``key`` identificerer signalet (fx "bridge_failures" el. "inner:witness_daemon").
    Best-effort — kaster aldrig; ved intern fejl fail-open til False (hellere tie end spamme).
    """
    try:
        now = now_monotonic if now_monotonic is not None else time.monotonic()
        with _lock:
            st = _state.get(key)
            if st is None:
                st = _KeyState()
                _state[key] = st
            if not breached:
                st.consecutive = 0
                return False
            st.consecutive += 1
            if st.consecutive < max(int(min_persistence), 1):
                return False  # endnu ikke vedvarende nok — kan være et blip
            if st.last_flag_monotonic is not None and (now - st.last_flag_monotonic) < cooldown_s:
                return False  # allerede flagget for nylig — dedup
            st.last_flag_monotonic = now
            return True
    except Exception:
        return False


def peek(key: str) -> dict:
    """Read-only indblik i en nøgles tilstand (til debug/observabilitet)."""
    try:
        with _lock:
            st = _state.get(key)
            if st is None:
                return {"key": key, "consecutive": 0, "flagged": False}
            return {"key": key, "consecutive": st.consecutive,
                    "flagged": st.last_flag_monotonic is not None}
    except Exception:
        return {"key": key, "consecutive": 0, "flagged": False}


def _reset_for_tests() -> None:
    with _lock:
        _state.clear()
