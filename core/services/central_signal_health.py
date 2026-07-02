"""core/services/central_signal_health.py

Fase 1e (LivingNeuron v3 §8): signal-KORREKTHED + hub META-LIVENESS.

To huller rådet fandt:
  1. observe_liveness sætter ok=(status=='ran') — en daemon der kører men producerer SKRALD
     tæller som "ok". Signal-TILSTEDEVÆRELSE ≠ signal-KORREKTHED. → verificér mindst én sansning
     mod en uafhængig DB-sandhed.
  2. Hele observabiliteten hviler på 4 hub-observe-punkter (~50 engines). Falder ét tavst, bliver
     en hel population usynlig UDEN at nogen ser det — Centralen bliver blind for sin egen blindhed.
     → meta-liveness der overvåger hub'ene SELV, cross-proces (api:8080 + runtime:8011).

Alt read-only, self-safe, kaster ALDRIG.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# De 4 load-bearing hubs (cluster:nerve) — fanger ~50 engines. Se v3 §GROUND TRUTH.
_HUB_NERVES = (
    ("cognition", "cognitive_conductor"),
    ("cognition", "cognitive_state_assembly"),
    ("cognition", "signal_surface_router"),
    ("cognition", "visible_turn_tracking"),
)
# KRITISK skel (undgå false-positive-flag-storm, jf. Centralen-rød-regression): en hub der er
# TAVS fordi systemet er IDLE er IKKE en fejl. Kun HEARTBEAT-gatede hubs (fyrer uafhængigt af
# bruger-aktivitet) er ægte blindzoner hvis de går tavse. TUR-gatede hubs fyrer kun på faktiske
# ture/prompt-builds → "missing/stale når idle" er NORMALT og må ALDRIG flagge.
_HUB_GATING = {
    "cognitive_conductor": "heartbeat",       # bygger cognitive frame på heartbeat → bør altid være frisk
    "cognitive_state_assembly": "turn",       # bygges ved prompt-build (kun ved ture)
    "signal_surface_router": "turn",          # læses ved prompt-build
    "visible_turn_tracking": "turn",          # kun på ægte visible-ture
}
_HUB_STALE_S = 7200  # heartbeat-hub: >2t uden sample = mistænkeligt tavs (heartbeat kører hvert par min).


def _parse_ts(s: Any) -> datetime | None:
    try:
        t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _merged() -> dict[str, Any]:
    try:
        from core.services.central_xproc import merged_timeseries
        return merged_timeseries()
    except Exception:
        return {}


def _freshest_ts(by_role: dict[str, Any]) -> datetime | None:
    freshest: datetime | None = None
    for _role, data in (by_role or {}).items():
        t = _parse_ts((data or {}).get("ts"))
        if t and (freshest is None or t > freshest):
            freshest = t
    return freshest


def hub_liveness(*, max_age_s: int = _HUB_STALE_S, merged: dict[str, Any] | None = None) -> dict[str, Any]:
    """Meta-liveness: for hver af de 4 hubs, find friskeste sample på tværs af processer og
    klassificér live / stale / missing. Så Centralen KAN se hvis en hub går tavs. Self-safe."""
    m = merged if merged is not None else _merged()
    now = datetime.now(timezone.utc)
    hubs: dict[str, Any] = {}
    live = stale = missing = 0
    for cluster, nerve in _HUB_NERVES:
        freshest = _freshest_ts(m.get(f"{cluster}:{nerve}") or {})
        if freshest is None:
            state, age = "missing", None
            missing += 1
        else:
            age = (now - freshest).total_seconds()
            if age <= max_age_s:
                state = "live"; live += 1
            else:
                state = "stale"; stale += 1
        hubs[nerve] = {"state": state, "age_s": (round(age) if age is not None else None),
                       "gated_by": _HUB_GATING.get(nerve, "turn")}
    # Ægte blindzone = KUN en heartbeat-gatet hub der ikke er live (tur-gatede er idle-afhængige).
    heartbeat_blind = [n for n, h in hubs.items()
                       if h["gated_by"] == "heartbeat" and h["state"] != "live"]
    return {"hubs": hubs, "live": live, "stale": stale, "missing": missing,
            "all_live": (live == len(_HUB_NERVES)),
            "heartbeat_blind": heartbeat_blind,
            "heartbeat_healthy": (len(heartbeat_blind) == 0)}


def nerves_observed_xproc(*, merged: dict[str, Any] | None = None) -> int:
    """Distinkte nerver Centralen FAKTISK har samples for PÅ TVÆRS af processer (fikser 1c's
    per-proces 0 i frisk probe). Self-safe."""
    m = merged if merged is not None else _merged()
    return len(m)


def signal_correctness(*, merged: dict[str, Any] | None = None) -> dict[str, Any]:
    """Verificér at mindst én sansning rapporterer VIRKELIGHEDEN, ikke bare fyrer. Sansernes Arkiv:
    den observerede 'total' krydstjekkes mod DB-sandheden (count_sensory_memories). Korrekt = observeret
    er et gyldigt snapshot (0 ≤ obs ≤ db) OG ikke fastlåst på 0 mens DB har data. Self-safe."""
    out: dict[str, Any] = {"nerve": "sensory:archive", "observed_total": None,
                           "db_total": None, "correct": None}
    try:
        from core.runtime.db_sensory import count_sensory_memories
        out["db_total"] = int(count_sensory_memories())
    except Exception:
        return out
    m = merged if merged is not None else _merged()
    by_role = m.get("sensory:archive") or {}
    newest_ts: datetime | None = None
    newest: dict[str, Any] | None = None
    for _role, data in by_role.items():
        t = _parse_ts((data or {}).get("ts"))
        if t and (newest_ts is None or t > newest_ts):
            newest_ts, newest = t, data
    if newest:
        meta = newest.get("meta") or {}
        if isinstance(meta.get("total"), (int, float)) and not isinstance(meta.get("total"), bool):
            out["observed_total"] = int(meta["total"])
    obs, db = out["observed_total"], out["db_total"]
    if obs is None:
        out["correct"] = None  # ingen observation endnu — hverken rigtig eller forkert
    else:
        out["correct"] = (0 <= obs <= db) and not (obs == 0 and db > 0)
    return out


def measure() -> dict[str, Any]:
    """Fuldt signal-sundheds-billede: hub-meta-liveness + cross-proces-nerver + signal-korrekthed."""
    m = _merged()
    hubs = hub_liveness(merged=m)
    return {**hubs, "nerves_observed_xproc": nerves_observed_xproc(merged=m),
            "signal_correctness": signal_correctness(merged=m)}


def record_signal_health() -> dict[str, Any]:
    """Mål + skriv nøgletal til tidsserien (cluster=system) + flag tavse hubs via central_watch."""
    r = measure()
    try:
        from core.services import central_timeseries as ts
        ts.record("system", "hubs_live", value=float(r.get("live") or 0),
                  meta={"stale": r.get("stale"), "missing": r.get("missing")})
        ts.record("system", "nerves_observed_xproc", value=float(r.get("nerves_observed_xproc") or 0))
        sc = r.get("signal_correctness") or {}
        if sc.get("correct") is not None:
            ts.record("system", "signal_correct", value=(1.0 if sc["correct"] else 0.0),
                      meta={"nerve": sc.get("nerve")})
    except Exception:
        pass
    # Flag KUN ægte blindzoner (heartbeat-gatet hub tavs) — ALDRIG idle-tavse tur-gatede hubs
    # (det ville være en false-positive-flag-storm der farvede Centralen rød uden grund).
    try:
        blind = r.get("heartbeat_blind") or []
        if blind:
            from core.services.central_core import central
            central().observe({"cluster": "system", "nerve": "hub_blindzone", "kind": "flag",
                               "silent_hubs": ",".join(blind), "count": len(blind)})
    except Exception:
        pass
    return r


def run_signal_health_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: mål + registrér signal-sundhed (~hvert 15 min). Self-safe."""
    r = record_signal_health()
    sc = r.get("signal_correctness") or {}
    return {"status": "ok", "hubs_live": r.get("live"), "hubs_missing": r.get("missing"),
            "nerves_observed_xproc": r.get("nerves_observed_xproc"), "signal_correct": sc.get("correct")}


def register_signal_health_producer() -> None:
    """Registrér signal-sundheds-målingen som cadence-producer (~hvert 15 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_signal_health",
        cooldown_minutes=15,
        visible_grace_minutes=0,
        run_fn=run_signal_health_tick,
        priority=6,
    ))


def build_central_signal_health_surface() -> dict[str, object]:
    """Mission Control surface — read-only hub-meta-liveness + signal-korrekthed."""
    return {"active": True, **measure()}
