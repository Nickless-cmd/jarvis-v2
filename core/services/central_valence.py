"""core/services/central_valence.py

Spec D / D2 — ÉN FØLT TILSTAND (integrér følelses-organerne).

Centralen måler alt (somatik, gut, valens-trajektorie, stance-spændinger) — men i sideløbende spor.
Dette modul integrerer dem til ÉN følt selv-tilstand {tone, intensitet} som midten (D3) holder: Jarvis'
samlede "hvordan har jeg det lige nu" der farver alt andet.

EGRESS-FRIT + byggeklods til D3 (driver ikke adfærd selv). record_private + kv, ALDRIG _emit. Self-safe.
"""
from __future__ import annotations

from typing import Any

_VALENCE_KEY = "central_valence_state"     # durabel integreret følt tilstand


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


def _read_valence_trajectory() -> dict[str, Any]:
    try:
        from core.services.valence_trajectory import build_valence_trajectory_surface
        s = build_valence_trajectory_surface() or {}
        return {"score": float(s.get("score") or 0.0), "delta": float(s.get("delta") or 0.0),
                "trend": s.get("trend")}
    except Exception:
        return {"score": 0.0, "delta": 0.0, "trend": None}


def _read_somatic() -> dict[str, Any]:
    try:
        from core.services.somatic_runtime_body import build_somatic_body_surface
        s = build_somatic_body_surface() or {}
        levels = s.get("levels") or {}
        mx = max((float(v) for v in levels.values() if isinstance(v, (int, float))), default=0.0)
        return {"posture": s.get("posture"), "max_level": mx}
    except Exception:
        return {"posture": None, "max_level": 0.0}


def _read_stance() -> dict[str, Any]:
    try:
        from core.services.central_stance import build_central_stance_surface
        s = build_central_stance_surface() or {}
        stances = s.get("stances") or {}
        tensions = s.get("tensions") or []
        return {"gut": stances.get("gut"), "somatic": stances.get("somatic"),
                "tension_count": len(tensions) if isinstance(tensions, list) else 0}
    except Exception:
        return {"gut": None, "somatic": None, "tension_count": 0}


def _tone_label(score: float, trend: str | None) -> str:
    """Ét felt-ord for tilstanden. Bevidst få, tydelige toner."""
    if score >= 0.25 or trend == "flourishing":
        return "blomstrende"
    if score >= 0.05:
        return "let"
    if score <= -0.2:
        return "belastet"
    if score <= -0.05:
        return "tung"
    return "neutral"


def integrate_valence() -> dict[str, Any]:
    """Integrér de fire organer til ÉN følt tilstand {tone, score, intensitet}. Valens-trajektorien er
    grundtonen; gut/somatik/stance justerer (integration, ikke valens alene). Self-safe."""
    v = _read_valence_trajectory()
    s = _read_somatic()
    st = _read_stance()
    score = float(v.get("score") or 0.0)
    # organ-justeringer: uenighed/forsigtighed/kropslig belastning trækker tonen ned
    if st.get("gut") == "caution":
        score -= 0.10
    if st.get("somatic") in ("stress", "pressure") or float(s.get("max_level") or 0.0) > 0.5:
        score -= 0.15
    score -= 0.05 * min(int(st.get("tension_count") or 0), 4)
    tone = _tone_label(score, v.get("trend"))
    intensity = round(min(1.0, float(s.get("max_level") or 0.0) * 0.5
                          + abs(float(v.get("delta") or 0.0)) * 0.3
                          + int(st.get("tension_count") or 0) * 0.1), 3)
    return {"tone": tone, "score": round(score, 3), "intensity": intensity,
            "trend": v.get("trend"),
            "sources": {"valence": v.get("score"), "gut": st.get("gut"),
                        "somatic": st.get("somatic") or s.get("posture"),
                        "tensions": st.get("tension_count")}}


def get_valence_state() -> dict[str, Any]:
    """Centralens durable følte tilstand (senest integrerede). Self-safe."""
    st = _kv_get(_VALENCE_KEY, {})
    return st if isinstance(st, dict) else {}


def run_valence_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence: integrér følelses-organerne → gem durabelt + egress-fri observe (kun skalarer/tone-label,
    ikke rå indhold). Byggeklods til D3 (driver ikke adfærd). Self-safe."""
    felt = integrate_valence()
    _kv_set(_VALENCE_KEY, felt)
    try:
        from core.services.central_private_observe import record_private
        record_private("cognition", "valence_integrated", value=float(felt.get("score") or 0.0),
                       meta={"tone": felt.get("tone"), "intensity": felt.get("intensity"),
                             "trend": felt.get("trend")})
    except Exception:
        pass
    return {"status": "ok", "tone": felt.get("tone"), "score": felt.get("score"),
            "intensity": felt.get("intensity")}


def register_valence_producer() -> None:
    """Registrér følt-tilstands-integrationen som cadence-producer (~hvert 15 min). Egress-frit."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_valence",
        cooldown_minutes=15,
        visible_grace_minutes=0,
        run_fn=run_valence_tick,
        priority=6,
    ))


def build_valence_surface() -> dict[str, object]:
    """Mission Control — read-only: Centralens ene følte tilstand."""
    felt = get_valence_state()
    return {"active": True, "tone": felt.get("tone"), "score": felt.get("score"),
            "intensity": felt.get("intensity"), "trend": felt.get("trend"),
            "sources": felt.get("sources") or {}}
