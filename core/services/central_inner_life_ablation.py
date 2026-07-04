"""Inner-life-ablation-kontakt — måling #2 (Bjørn 4. jul).

Det STÆRKESTE enkeltbevis for kontentions-hypotesen ("hans indre liv træder på hans
stemme"): sluk den kognitive/emergente inder-liv-cadence i et måle-vindue og se om
cutoff/tom-raten + loop-lag FALDER ved fast provider. Falder de → presset er ægte,
mekanisk, og fixet ærer livet (giv stemmen beskyttet vejrtrækning). Falder de ikke →
kontention er ikke synderen, og vi står med noget uforklaret.

Kun den HEAVY inder-liv-cadence gates (emergent-signaler, personlighed→selv-model,
lifecycle, adoption, frozen-detektorer emergence/contradiction, idle-thinking). Infra/
health/cost/heartbeat-kernen kører videre — så systemet lever, bare uden det tunge
kognitive lag der konkurrerer om CPU/DB.

Toggle via runtime-state (ingen redeploy): jc cmd sætter flaget, eller kald set_ablated.
Self-safe: ved tvivl → IKKE ablateret (livet kører normalt).
"""
from __future__ import annotations

_FLAG = "central_inner_life_ablation"


def is_ablated() -> bool:
    """True hvis den heavy inder-liv-cadence skal springes over lige nu. Self-safe →
    default False (livet kører)."""
    try:
        from core.runtime.db import get_runtime_state_value
        return bool(get_runtime_state_value(_FLAG, False))
    except Exception:
        return False


def set_ablated(on: bool) -> None:
    """Tænd/sluk ablationen (måle-vindue). Self-safe."""
    try:
        from core.runtime.db import set_runtime_state_value
        set_runtime_state_value(_FLAG, bool(on))
    except Exception:
        pass


def build_ablation_surface() -> dict[str, object]:
    """Mission Control — read-only status."""
    return {"inner_life_ablated": is_ablated(), "flag": _FLAG}
