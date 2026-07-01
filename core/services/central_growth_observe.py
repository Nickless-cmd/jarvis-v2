"""core/services/central_growth_observe.py

C — vækst-kapacitets-observation (Bjørn 1. jul: "data til LivingNeuron-teorien").

To signaler §23.3 #11 + biggest-gap #3-rest kortlagde som dark:
  1. INNER-DRIVES (impulse/pressure/emergent_signal) — Jarvis' intrinsiske motivation og
     autonomi-pres. Afgørende for at se om VÆKST-KAPACITETEN lever eller ossificerer — præcis
     det LivingNeuron-teorien skal måle. Men det er inner-drives = PRIVAT → observeres
     EGRESS-FRIT (§24.4): direkte til lokal trace + tidsserie, ALDRIG via central().observe
     (som _emit'er til eventbus), ALDRIG fodrer læring. Ren owner-observabilitet + data.
  2. SEMANTIC-INDEXER — operationel indeks-aktivitet (ikke privat) → NORMAL observe.

Aktivitets-niveau = antal events i det seneste vindue pr. tick (samplet trend, ikke delta).
Nok til at se "lever inner-drive-laget eller er det gået i stå". Self-safe, kaster aldrig.
"""
from __future__ import annotations

from typing import Any

from core.services import central_timeseries, central_trace

# Private inner-drive-families — observeres EGRESS-FRIT (cluster=autonomy).
_INNER_DRIVE_FAMILIES = ("impulse", "pressure", "emergent_signal")


def observe_inner_drive_activity() -> dict[str, int]:
    """Sampl inner-drive-aktivitet EGRESS-FRIT → lokal trace + tidsserie (cluster=autonomy).
    LivingNeuron-data: lever vækst-kapaciteten? Ingen egress, ingen læring. Self-safe."""
    counts: dict[str, int] = {}
    try:
        from core.eventbus.bus import event_bus
        for fam in _INNER_DRIVE_FAMILIES:
            try:
                counts[fam] = len(event_bus.recent_by_family(fam, limit=50))
            except Exception:
                counts[fam] = 0
    except Exception:
        return counts
    for fam, n in counts.items():
        # EGRESS-FRI: direkte til sinken (owner-only), ALDRIG central().observe (→ _emit).
        try:
            central_trace.sink().record(central_trace.TraceRecord(
                run_id="", session_id="", cluster="autonomy", nerve=fam,
                kind="observe", payload={"activity": int(n)}))
        except Exception:
            pass
        try:
            central_timeseries.record("autonomy", fam, value=float(n))
        except Exception:
            pass
    return counts


def observe_index_activity() -> int:
    """Sampl semantic-indexer-aktivitet (operationel, ikke privat) → NORMAL observe. Self-safe."""
    n = 0
    active = False
    try:
        from core.eventbus.bus import event_bus
        n = len(event_bus.recent_by_family("semantic_indexer", limit=50))
    except Exception:
        pass
    try:
        from core.services.semantic_indexer import build_semantic_indexer_surface
        active = bool((build_semantic_indexer_surface() or {}).get("active"))
    except Exception:
        pass
    try:
        from core.services.central_core import central
        central().observe({"cluster": "system", "nerve": "semantic_indexer",
                           "kind": "observe", "active": active, "activity": int(n)})
    except Exception:
        pass
    try:
        central_timeseries.record("system", "semantic_indexer", value=float(n),
                                  meta={"active": active})
    except Exception:
        pass
    return n


_SENSORY_MODALITIES = ("visual", "audio", "atmosphere", "mixed")


def observe_sensory_activity() -> dict[str, Any]:
    """Sansernes Arkiv → Centralen EGRESS-FRIT (§24.4): sansnings-AKTIVITET (rate + modalitet +
    total), ALDRIG indhold. Kerne LivingNeuron-modalitet: ser om Jarvis SANSER, og hvad.
    Sansning er privat perception → lokal trace + tidsserie (cluster=sensory), ingen egress/læring."""
    out: dict[str, Any] = {}
    try:
        from core.runtime.db_sensory import count_sensory_memories
        total = count_sensory_memories()
        by_mod = {m: count_sensory_memories(modality=m) for m in _SENSORY_MODALITIES}
        # rate: sansninger seneste time (er perceptionen levende?)
        recent_1h = 0
        try:
            from datetime import datetime, timedelta, timezone
            from core.services import sensory_archive
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            for r in sensory_archive.list_recent(limit=100):
                ts = str(r.get("timestamp") or "")
                try:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if t.tzinfo is None:
                        t = t.replace(tzinfo=timezone.utc)
                    if t >= cutoff:
                        recent_1h += 1
                except Exception:
                    pass
        except Exception:
            pass
        out = {"total": total, "recent_1h": recent_1h, **{f"mod_{m}": by_mod[m] for m in _SENSORY_MODALITIES}}
        # EGRESS-FRI: direkte til sinken (owner-only), ALDRIG central().observe (→ _emit).
        try:
            central_trace.sink().record(central_trace.TraceRecord(
                run_id="", session_id="", cluster="sensory", nerve="archive",
                kind="observe", payload=dict(out)))
        except Exception:
            pass
        central_timeseries.record("sensory", "archive", value=float(recent_1h),
                                  meta={"total": total, **by_mod})
    except Exception:
        pass
    return out


def run_growth_observe_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: sampl vækst-kapacitet (inner-drives + indexer + Sansernes Arkiv). Self-safe."""
    drives = observe_inner_drive_activity()
    idx = observe_index_activity()
    sensory = observe_sensory_activity()
    return {"status": "ok", "inner_drives": drives, "index_activity": idx,
            "sensory_recent_1h": sensory.get("recent_1h"), "sensory_total": sensory.get("total")}


def register_growth_observe_producer() -> None:
    """Registrér vækst-observationen som cadence-producer (~hvert 5 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_growth_observe",
        cooldown_minutes=5,
        visible_grace_minutes=0,
        run_fn=run_growth_observe_tick,
        priority=5,
    ))
