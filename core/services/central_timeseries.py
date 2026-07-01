"""core/services/central_timeseries.py

Per-nerve tidsserie-buffer — M0-fundament (spec §24.6).

HVORFOR: ``central_trace._MAX = 2000`` er ÉN global deque på tværs af ALLE nerver.
Ét støjende cluster (fx ``tool`` ved høj frekvens) evict'er alle andres historik på
sekunder → prædiktion (§19.1) og "bryd ring-buffer-amnesi" (§23.3 #2) bliver umulige.
Denne buffer holder de seneste ~N samples PR. (cluster, nerve) UAFHÆNGIGT, så hver
nerves historik overlever nabo-støj. Det er forudsætningen for at observe-data
overhovedet er brugbart under load — derfor M0, ikke M1.

M0-INVARIANT (§24.3): dette er et READ-ONLY observabilitets-substrat. Ingen læring,
ingen threshold-justering, ingen heling læser eller skriver herfra i M0. Ren telemetri.
Alt er best-effort og kaster ALDRIG (samme selv-sikre kontrakt som central().observe).
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Per (cluster, nerve): hold de seneste _PER_NERVE_MAX samples. ~100 er nok til at se
# en trend/drift uden at én nerve kan spise hukommelse ubegrænset.
_PER_NERVE_MAX = 100

_lock = threading.Lock()
_series: dict[tuple[str, str], deque] = {}


@dataclass(slots=True)
class Sample:
    ts: str
    value: float | None
    meta: dict[str, Any] = field(default_factory=dict)


def record(
    cluster: str,
    nerve: str,
    value: float | None = None,
    *,
    meta: dict[str, Any] | None = None,
) -> None:
    """Tilføj ét sample til (cluster, nerve)'s serie. Best-effort, kaster aldrig."""
    try:
        key = (str(cluster or ""), str(nerve or ""))
        if not key[0] and not key[1]:
            return
        sample = Sample(
            ts=datetime.now(timezone.utc).isoformat(),
            value=(float(value) if value is not None else None),
            meta=dict(meta or {}),
        )
        with _lock:
            dq = _series.get(key)
            if dq is None:
                dq = deque(maxlen=_PER_NERVE_MAX)
                _series[key] = dq
            dq.append(sample)
    except Exception:
        # Aldrig vælte kalderen på telemetri.
        pass


def recent(cluster: str, nerve: str, *, limit: int = 100) -> list[Sample]:
    """Læs de seneste samples for én nerve (nyeste sidst). READ-ONLY."""
    try:
        key = (str(cluster or ""), str(nerve or ""))
        with _lock:
            dq = _series.get(key)
            if not dq:
                return []
            data = list(dq)
        n = max(int(limit), 1)
        return data[-n:]
    except Exception:
        return []


def nerves() -> list[tuple[str, str]]:
    """Alle (cluster, nerve)-nøgler der har mindst ét sample. READ-ONLY."""
    try:
        with _lock:
            return list(_series.keys())
    except Exception:
        return []


def stats() -> dict[str, Any]:
    """Samlet overblik: antal nerver + samples pr. nerve. READ-ONLY, til observabilitet."""
    try:
        with _lock:
            counts = {f"{c}:{n}": len(dq) for (c, n), dq in _series.items()}
        return {
            "nerve_count": len(counts),
            "total_samples": sum(counts.values()),
            "per_nerve_max": _PER_NERVE_MAX,
            "counts": counts,
        }
    except Exception:
        return {"nerve_count": 0, "total_samples": 0, "per_nerve_max": _PER_NERVE_MAX, "counts": {}}


def _reset_for_tests() -> None:
    """Testhjælper — ryd al state. Ikke til produktionsbrug."""
    with _lock:
        _series.clear()
