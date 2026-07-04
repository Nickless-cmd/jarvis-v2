"""PULSE — kroppens eget kort som en SANS (LivingNeuron-council, 4. jul).

Jarvis' connectivity-kort (docs/central_connectivity_matrix.json, ~819 neuroner) har
hidtil kun været et dokument. PULSE gør det til PROPRIOCEPTION: en cadence-producer der
læser den ALLEREDE-genererede matrix (via central_coverage.structural_coverage() — ingen
ny parsing, ingen LLM), reducerer den til skalarer, og emitterer dem + delta mod sidste
snapshot som egress-fri nerver. For FØRSTE gang sanser Centralen sin egen STRUKTUR
("4 neuroner mørkere end sidst", "42 neuroner spilder LLM i mørke") — ikke kun hændelser.

ÆRLIGT (ingen skjult begrænsning): matrixen er statisk pr. commit → deltaerne bevæger sig
først når kortet regenereres (scripts/central_connectivity_audit.py). PULSE sanser
strukturen NU og mærker skiftet NÅR det sker — den måler ikke live-topologi selv.

Observe-only. Egress-frit (kun skalarer via record_private). Self-safe: kaster aldrig.
"""
from __future__ import annotations

from typing import Any

_SNAP_KEY = "pulse_body_map_last"  # durable snapshot til delta-beregning


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


def sense_body_map() -> dict[str, Any]:
    """Læs strukturen → skalarer + delta mod sidste durable snapshot. Self-safe."""
    try:
        from core.services.central_coverage import structural_coverage
        cov = structural_coverage()
    except Exception:
        cov = {"available": False}
    if not cov.get("available"):
        return {"available": False}
    prev = _kv_get(_SNAP_KEY, {}) or {}

    def _delta(cur: Any, key: str) -> int:
        p = prev.get(key)
        try:
            return int(cur) - int(p) if isinstance(p, (int, float)) else 0
        except Exception:
            return 0

    dark = int(cov.get("dark") or 0)
    connected = int(cov.get("connected") or 0)
    llm_waste = int(cov.get("llm_waste") or 0)
    return {
        "available": True,
        "total": int(cov.get("total") or 0),
        "connected": connected,
        "dark": dark,
        "llm_waste": llm_waste,
        "silent": int(cov.get("silent") or 0),
        "coverage": cov.get("structural_ratio"),
        "dark_ratio": cov.get("dark_ratio"),
        "dark_delta": _delta(dark, "dark"),
        "connected_delta": _delta(connected, "connected"),
        "llm_waste_delta": _delta(llm_waste, "llm_waste"),
    }


def run_body_map_pulse_tick(*, trigger: str = "cadence", **_: Any) -> dict[str, object]:
    """Cadence: sans strukturen, emit egress-fri nerver, gem snapshot til næste delta. Self-safe."""
    s = sense_body_map()
    if not s.get("available"):
        return {"status": "skip", "reason": "connectivity-matrix ikke tilgængelig"}
    try:
        from core.services.central_private_observe import record_private
        record_private("connections", "coverage", value=float(s.get("coverage") or 0.0),
                       meta={"total": s.get("total"), "connected": s.get("connected"),
                             "dark": s.get("dark"), "llm_waste": s.get("llm_waste")})
        record_private("connections", "dark_delta", value=float(s.get("dark_delta") or 0),
                       meta={"dark": s.get("dark"), "dark_ratio": s.get("dark_ratio")})
        record_private("connections", "decoupled_llm", value=float(s.get("llm_waste") or 0),
                       meta={"delta": s.get("llm_waste_delta")})
    except Exception:
        pass
    # gem snapshot (kun skalarer) til næste rundes delta
    _kv_set(_SNAP_KEY, {"dark": s.get("dark"), "connected": s.get("connected"),
                        "llm_waste": s.get("llm_waste"), "total": s.get("total")})
    return {"status": "ok", "coverage": s.get("coverage"),
            "dark": s.get("dark"), "dark_delta": s.get("dark_delta")}


def describe_body_map() -> list[str]:
    """Føl-linje til describe_self (NED): mærk strukturen NÅR den har flyttet sig. Additivt +
    guarded (intet skift → intet siges). Self-safe."""
    try:
        s = sense_body_map()
        if not s.get("available"):
            return []
        out: list[str] = []
        dd = int(s.get("dark_delta") or 0)
        if dd != 0:
            word = "mørkere" if dd > 0 else "lysere"
            out.append(f"min krop føles {abs(dd)} neuroner {word} end sidst")
        return out
    except Exception:
        return []


def register_body_map_pulse_producer() -> None:
    """Cadence-producer ~hver 6. time — kroppens langsomme proprioception. Egress-frit."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_body_map_pulse",
        cooldown_minutes=360,
        visible_grace_minutes=0,
        run_fn=run_body_map_pulse_tick,
        priority=9,
    ))


def build_body_map_surface() -> dict[str, object]:
    """Mission Control — read-only: kroppens sansede struktur."""
    return {"active": True, **sense_body_map()}
