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

import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

# Per (cluster, nerve): hold de seneste _PER_NERVE_MAX samples. ~100 er nok til at se
# en trend/drift uden at én nerve kan spise hukommelse ubegrænset.
_PER_NERVE_MAX = 100

_lock = threading.Lock()
_series: dict[tuple[str, str], deque] = {}

# ── DURABILITET (Bjørn 3. jul): nervesystemet skal OVERLEVE genstart (§6.2). Tidsserien var
# ren in-memory (M0-valg for performance) → hver deploy/restart nulstillede al nervøs aktivitet +
# ethvert shadow-måле-vindue. Fix: periodisk snapshot-flush til durabel kv (i baggrundstråd, aldrig
# hot-path) + restore ved første adgang. Vi mister højst de sidste _PERSIST_INTERVAL_S ved et crash.
_DURABLE_KEY = "central_timeseries_durable"
_PERSIST_PER_NERVE = 40          # sidste N pr. nerve i snapshottet (bounded blob-størrelse)
_PERSIST_INTERVAL_S = 180.0      # flush højst hvert ~3 min (throttlet på record-aktivitet)
_SEP = "\x1f"                    # unit-separator: sikker (cluster/nerve indeholder den aldrig)
_restore_lock = threading.Lock()
_restored = False
_last_persist = 0.0


def _kv_get(key: str, default: Any) -> Any:
    try:
        from core.runtime.db_core import get_runtime_state_value
        v = get_runtime_state_value(key, default)
        return v if v is not None else default
    except Exception:
        return default


def _kv_set(key: str, value: Any) -> None:
    try:
        from core.runtime.db_core import set_runtime_state_value
        set_runtime_state_value(key, value)
    except Exception:
        pass


def _durability_on() -> bool:
    """Hot-path-durabilitet (auto-restore/persist i record/recent) er AKTIV i produktion, men
    slås fra under pytest så ingen test utilsigtet rører den rigtige runtime-DB. Funktionerne
    (persist_snapshot/_maybe_restore/_load_durable) er stadig direkte kaldbare i tests."""
    return "PYTEST_CURRENT_TEST" not in os.environ


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
        if _durability_on():
            _maybe_restore()  # første adgang efter genstart → genindlæs durabelt snapshot
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
        _maybe_persist()  # throttlet baggrunds-flush (aldrig hot-path-blokerende)
    except Exception:
        # Aldrig vælte kalderen på telemetri.
        pass


def recent(cluster: str, nerve: str, *, limit: int = 100) -> list[Sample]:
    """Læs de seneste samples for én nerve (nyeste sidst). READ-ONLY."""
    try:
        if _durability_on():
            _maybe_restore()  # læsning efter genstart ser det durable snapshot
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


def snapshot(*, recent: int = 3) -> dict[str, Any]:
    """Kompakt cross-proces-snapshot: pr. nerve seneste værdi(er) + count. Read-only, self-safe.
    Bruges af central_xproc til at tee tidsserien til shared_cache (cross-proces-læsbarhed)."""
    try:
        with _lock:
            items = list(_series.items())
        out: dict[str, Any] = {}
        n = max(int(recent), 1)
        for (c, nv), dq in items:
            data = list(dq)[-n:]
            if not data:
                continue
            out[f"{c}:{nv}"] = {
                "count": len(dq),
                "latest": data[-1].value,
                "meta": dict(data[-1].meta or {}),
                "ts": data[-1].ts,
                "recent": [s.value for s in data],
            }
        return out
    except Exception:
        return {}


def persist_snapshot() -> dict[str, Any]:
    """Flush de bounded per-nerve-serier til durabel kv, så nervesystemet OVERLEVER genstart.
    Bounded (_PERSIST_PER_NERVE pr. nerve). Self-safe. Kaldes throttlet fra baggrundstråd + kan
    kaldes eksplicit ved graceful shutdown."""
    try:
        with _lock:
            items = [((c, nv), list(dq)[-_PERSIST_PER_NERVE:]) for (c, nv), dq in _series.items()]
        blob: dict[str, Any] = {}
        for (c, nv), data in items:
            if not data:
                continue
            blob[f"{c}{_SEP}{nv}"] = [[s.ts, s.value, s.meta] for s in data]
        _kv_set(_DURABLE_KEY, blob)
        return {"status": "ok", "nerves": len(blob)}
    except Exception:
        return {"status": "error"}


def _load_durable() -> None:
    """Genindlæs det durable snapshot ind i _series (merge-append). Self-safe."""
    blob = _kv_get(_DURABLE_KEY, {})
    if not isinstance(blob, dict) or not blob:
        return
    with _lock:
        for key, samples in blob.items():
            if not isinstance(key, str) or _SEP not in key or not isinstance(samples, list):
                continue
            c, nv = key.split(_SEP, 1)
            dq = _series.get((c, nv))
            if dq is None:
                dq = deque(maxlen=_PER_NERVE_MAX)
                _series[(c, nv)] = dq
            for item in samples:
                try:
                    ts, value, meta = item
                    dq.append(Sample(ts=str(ts), value=value,
                                     meta=dict(meta) if isinstance(meta, dict) else {}))
                except Exception:
                    continue


def _maybe_restore() -> None:
    """Restore-on-first-access (dobbelt-tjekket): genindlæs durabelt snapshot ÉN gang efter boot."""
    global _restored
    if _restored:
        return
    with _restore_lock:
        if _restored:
            return
        try:
            _load_durable()
        finally:
            _restored = True


def _maybe_persist() -> None:
    """Throttlet flush i baggrundstråd (hot-path stalles ALDRIG af DB-skrivning)."""
    global _last_persist
    now = time.time()
    if now - _last_persist < _PERSIST_INTERVAL_S:
        return
    _last_persist = now
    try:
        threading.Thread(target=persist_snapshot, name="cts-persist", daemon=True).start()
    except Exception:
        pass


def _reset_for_tests() -> None:
    """Testhjælper — ryd al state. Ikke til produktionsbrug."""
    global _restored, _last_persist
    with _lock:
        _series.clear()
    _restored = False
    _last_persist = 0.0
