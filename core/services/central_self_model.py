"""core/services/central_self_model.py

SPEJLET — Centralen kender sig selv (LivingNeuron, næste celle-lag).

Jarvis' egen dæknings-audit: Centralen så ALT undtagen sig selv. `runtime_self_model.build_runtime_
self_model()` bygger et rigt struktureret snapshot af Jarvis' system-selv (~40 lag: mineness, flow,
wonder, longing, narrativ identitet …), men det når aldrig Centralen. Dette modul lader Centralen
HOLDE sin egen selv-model — durabelt, så den overlever genstart.

EGRESS-FRIT + OBSERVE-ONLY (rådets vagt):
  * Kun STRUKTUR optages — hvilke lag findes/er udfyldt, tællinger, fuldstændighed. ALDRIG værdi-
    INDHOLD (det er privat inder-liv). Nøgle-LABELS (fx 'mineness_ownership') er struktur, ikke indhold.
  * record_private (trace + tidsserie), ALDRIG _emit. Snapshot gemmes i durable kv (owner-lokalt).
  * §8 CIRCULAR-VAGT: spejlet fodrer IKKE hypotese-grounding — Centralen må ikke bekræfte formodninger
    om SIG SELV med sin egen selv-model som "ekstern" evidens. Ren observation. Kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

_SNAPSHOT_KEY = "central_self_model_snapshot"     # Centralens durable selv-model-struktur (overlever genstart)


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


def _populated(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (dict, list, str, tuple, set)):
        return len(v) > 0
    return True                    # skalarer/bools tæller som til stede


def _extract_structure(model: dict[str, Any]) -> dict[str, Any]:
    """Uddrag KUN struktur fra selv-modellen: hvilke lag findes/er udfyldt (labels), tællinger,
    fuldstændighed. ALDRIG værdi-indhold. Self-safe."""
    keys = sorted(str(k) for k in model.keys())
    present = [k for k in keys if _populated(model.get(k))]
    empty = [k for k in keys if k not in present]
    return {"surfaces_total": len(keys), "surfaces_populated": len(present),
            "completeness": round(len(present) / len(keys), 3) if keys else 0.0,
            "present": present, "empty": empty}


def snapshot_self_model() -> dict[str, Any]:
    """Byg selv-modellen og uddrag dens STRUKTUR (ikke indhold). Self-safe → {} ved fejl."""
    try:
        from core.services.runtime_self_model import build_runtime_self_model
        model = build_runtime_self_model()
        if not isinstance(model, dict) or not model:
            return {}
        return _extract_structure(model)
    except Exception:
        return {}


def get_self_model_snapshot() -> dict[str, Any]:
    """Centralens DURABLE selv-model-struktur (senest optagne). Overlever genstart (kv). Self-safe."""
    snap = _kv_get(_SNAPSHOT_KEY, {})
    return snap if isinstance(snap, dict) else {}


def run_self_model_mirror_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: snapshot selv-modellens struktur → gem durabelt (kv) + egress-fri observe (kun skalarer).
    OBSERVE-ONLY (fodrer aldrig hypotese-grounding, §8-circular). Self-safe."""
    snap = snapshot_self_model()
    if snap:
        prev = get_self_model_snapshot()
        # durabel selv-model: Centralen HOLDER sin egen struktur (overlever genstart)
        _kv_set(_SNAPSHOT_KEY, snap)
        # delta: voksede/skrumpede selv-erkendelsen? (struktur-drift = plotbart)
        delta = int(snap.get("surfaces_populated", 0)) - int((prev or {}).get("surfaces_populated", 0))
        try:
            from core.services.central_private_observe import record_private
            record_private("cognition", "self_model_mirror",
                           value=float(snap.get("surfaces_populated") or 0),
                           meta={"total": snap.get("surfaces_total"),
                                 "populated": snap.get("surfaces_populated"),
                                 "completeness": snap.get("completeness"),
                                 "delta": delta})
        except Exception:
            pass
    return {"status": "ok", "surfaces_populated": snap.get("surfaces_populated"),
            "completeness": snap.get("completeness"), "mirrored": bool(snap)}


def register_self_model_mirror_producer() -> None:
    """Registrér spejlet som cadence-producer (~hvert 30 min). Egress-frit, observe-only."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_self_model_mirror",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_self_model_mirror_tick,
        priority=6,
    ))


def build_self_model_mirror_surface() -> dict[str, object]:
    """Mission Control — read-only: Centralens billede af sig selv (struktur, ikke indhold)."""
    snap = get_self_model_snapshot()
    return {"active": True, "surfaces_total": snap.get("surfaces_total"),
            "surfaces_populated": snap.get("surfaces_populated"),
            "completeness": snap.get("completeness"),
            "present": (snap.get("present") or [])[:60],
            "empty": (snap.get("empty") or [])[:20]}
