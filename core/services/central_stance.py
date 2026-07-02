"""core/services/central_stance.py

Lag 3 v3 (LivingNeuron): tvær-modal STANCE-divergens — "organer uenige i NUET".

Rådets dybeste indsigt: intelligens/refleksion opstår ikke fra at organer er ENIGE, men fra at
skulle ARBITRERE mellem UENIGE indre stemmer. Cross-thread run-scoping af de indre observes er
arkitektonisk dyb (somatik kører på heartbeat-tråden, ikke run-tråden), SÅ i stedet PULL'er vi:
læs hvert organs NUVÆRENDE stance fra dets eksisterende surface (read-only, egress-frit) og
detektér når to organer holder MODSATTE holdninger samtidig.

Grounded i faktiske surfaces (verificeret 2. jul):
  * gut (`build_gut_surface`): last_hunch "proceed"/"caution"
  * somatik (`build_somatic_body_surface`): levels pressure/startle/frustration → stress/calm
  * contradiction (`build_contradiction_engine_surface`): active/finding_count → conflicted/consistent

En tension der GENTAGER sig (≥N snapshots) bliver en divergens-hypotese hos generatoren:
"når gut siger 'proceed' men kroppen er i 'stress' — hvad afgør udfaldet?" Alt read-only, self-safe.
"""
from __future__ import annotations

from typing import Any

# Kuraterede MODSAT-holdning-par på tværs af modaliteter (tension = begge tokens aktive samtidig).
_TENSION_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("gut:proceed", "somatic:stress", "gut vil frem, men kroppen bremser"),
    ("gut:caution", "somatic:calm", "gut tøver, selvom kroppen er rolig"),
    ("contradiction:conflicted", "somatic:calm", "tanken er i konflikt, men kroppen upåvirket"),
    ("gut:proceed", "contradiction:conflicted", "gut vil frem trods indre inkonsistens"),
)
_STRESS_THRESHOLD = 0.6


def _classify_gut() -> str | None:
    try:
        from core.services.gut_engine import build_gut_surface
        s = build_gut_surface() or {}
        hunch = str(((s.get("state") or {}).get("last_hunch")) or "").lower()
        if "proceed" in hunch:
            return "proceed"
        if "caution" in hunch or "hold" in hunch or "wait" in hunch:
            return "caution"
    except Exception:
        pass
    return None


def _classify_somatic() -> str | None:
    try:
        from core.services.somatic_runtime_body import build_somatic_body_surface
        lv = (build_somatic_body_surface() or {}).get("levels") or {}
        arousal = max(float(lv.get("pressure", 0) or 0), float(lv.get("startle", 0) or 0),
                      float(lv.get("frustration", 0) or 0))
        return "stress" if arousal >= _STRESS_THRESHOLD else "calm"
    except Exception:
        return None


def _classify_contradiction() -> str | None:
    try:
        from core.services.contradiction_engine import build_contradiction_engine_surface
        s = build_contradiction_engine_surface() or {}
        n = int(((s.get("summary") or {}).get("finding_count")) or 0)
        return "conflicted" if (bool(s.get("active")) and n > 0) else "consistent"
    except Exception:
        return None


def read_current_stances() -> dict[str, str]:
    """Læs hvert organs NUVÆRENDE stance (read-only fra surfaces). Udelader organer uden klar stance."""
    out: dict[str, str] = {}
    for mod, fn in (("gut", _classify_gut), ("somatic", _classify_somatic),
                    ("contradiction", _classify_contradiction)):
        v = fn()
        if v:
            out[mod] = v
    return out


def current_tensions(stances: dict[str, str] | None = None) -> list[dict[str, str]]:
    """Hvilke MODSAT-holdning-par er aktive lige NU? (to organer uenige samtidig)."""
    s = stances if stances is not None else read_current_stances()
    tokens = {f"{k}:{v}" for k, v in s.items()}
    out = []
    for a, b, desc in _TENSION_PAIRS:
        if a in tokens and b in tokens:
            out.append({"a": a, "b": b, "desc": desc, "key": f"{a}|{b}"})
    return out


def run_stance_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer (~10 min): læs stances, registrér aktive tensions egress-frit i tidsserien
    (så gentagne tensions kan tælles → divergens-hypotese hos generatoren). Self-safe."""
    stances = read_current_stances()
    tensions = current_tensions(stances)
    try:
        from core.services.central_private_observe import record_private
        for t in tensions:
            # egress-fri: kun tension-NØGLEN (modalitet:holdning — ikke indhold) i tidsserien
            record_private("cognition", f"tension:{t['key']}", value=1.0, meta={"desc": t["desc"]})
        record_private("cognition", "stance_snapshot", value=float(len(tensions)),
                       meta={k: v for k, v in stances.items()})
    except Exception:
        pass
    return {"status": "ok", "stances": stances, "tensions": [t["key"] for t in tensions]}


def recurring_tensions(*, min_count: int = 3, window: int = 100) -> list[dict[str, Any]]:
    """Tensions der har GENTAGET sig ≥ min_count gange i det seneste tidsserie-vindue → stabile
    nok til en divergens-hypotese (ikke ét støj-øjeblik). Self-safe."""
    out = []
    try:
        from core.services import central_timeseries
        for (cluster, nerve) in central_timeseries.nerves():
            if cluster != "cognition" or not nerve.startswith("tension:"):
                continue
            samples = central_timeseries.recent(cluster, nerve, limit=window)
            if len(samples) >= int(min_count):
                key = nerve[len("tension:"):]
                desc = ""
                if samples and isinstance(samples[-1].meta, dict):
                    desc = str(samples[-1].meta.get("desc") or "")
                out.append({"key": key, "count": len(samples), "desc": desc})
    except Exception:
        pass
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


def register_stance_producer() -> None:
    """Registrér stance-aflæsningen som cadence-producer (~hvert 10 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_stance",
        cooldown_minutes=10,
        visible_grace_minutes=0,
        run_fn=run_stance_tick,
        priority=6,
    ))


def build_central_stance_surface() -> dict[str, object]:
    """Mission Control surface — read-only NUVÆRENDE stances + aktive tensions."""
    stances = read_current_stances()
    return {"active": True, "stances": stances,
            "tensions": current_tensions(stances),
            "recurring": recurring_tensions()}
