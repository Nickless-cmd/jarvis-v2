"""core/services/central_router_explore.py

DEN MODIGE DEL — Tråd 1 EKSPLORATIONS-ARM (spec §3): skab A/B-kontrast så model_meta kan resolvere.

Præference-læreren (central_router_adapt) kan kun lære af RESOLVEREDE model_meta-hypoteser, som
kræver at flere modeller faktisk køres og sammenlignes. Denne arm generer den kontrast: den sampler
occasionelt en ALTERNATIV model — men KUN på AUTONOME runs (Jarvis' egne heartbeat-runs), ALDRIG
på Bjørns interaktive ture. Det giver ægte målinger uden at røre kvaliteten af det Bjørn ser.

⚠️ SIKKERHED (spec §3, ikke-forhandlelige):
  * KUN autonome runs (ingen bruger venter på kvalitet). Interaktive ture rører den ALDRIG.
  * SHADOW default (`model_router_explore_live_enabled=False`) → sampler intet.
  * ALDRIG deep/reasoning-tier (samme token-værn som adapt).
  * Rate-boundet: kun hver K'te autonome run udforskes (ellers default/præference).
  * Kun KONFIGUREREDE modeller (set køre). fail-safe: tvivl → None (ingen eksploration).
  * Kaster ALDRIG.
"""
from __future__ import annotations

from typing import Any

_EXPLORE_FLAG = "model_router_explore_live_enabled"   # Bjørns switch (default OFF)
_COUNTER_KEY = "model_router_explore_counter"         # autonome-run-tæller (rate-gate)
_SAMPLE_EVERY = 5                # udforsk hver K'te autonome run
_MIN_SAMPLES_CONFIGURED = 1      # en model tæller som 'konfigureret' ved ≥ dette antal runs


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


def is_explore_live() -> bool:
    return bool(_kv_get(_EXPLORE_FLAG, False))


def _candidates(default_key: str) -> list[tuple[str, int]]:
    """Konfigurerede, ikke-deep-tier modeller forskellige fra default — sorteret efter FÆRREST samples
    (byg kontrast hvor den er tyndest). Returnerer [(model_key, samples)]. Self-safe."""
    try:
        from core.services.central_model_meta import aggregate_model_outcomes
        from core.services.central_router_adapt import _is_never_tier
        rows = []
        for k, d in aggregate_model_outcomes().items():
            n = int(d.get("samples") or 0)
            if n >= _MIN_SAMPLES_CONFIGURED and k != default_key and not _is_never_tier(k):
                rows.append((k, n))
        rows.sort(key=lambda kv: kv[1])   # færrest samples først
        return rows
    except Exception:
        return []


def pick_exploration_model(default_provider: str, default_model: str) -> tuple[str, str] | None:
    """Vælg en alternativ model at sample på DENNE autonome run — eller None (behold default/præference).
    Live + rate-gated + mindst-samplede kandidat. Self-safe."""
    if not is_explore_live():
        return None
    default_key = f"{default_provider}/{default_model}"
    cands = _candidates(default_key)
    if not cands:
        return None
    # rate-gate: kun hver K'te autonome run
    try:
        counter = int(_kv_get(_COUNTER_KEY, 0) or 0) + 1
    except Exception:
        counter = 1
    _kv_set(_COUNTER_KEY, counter)
    if counter % _SAMPLE_EVERY != 0:
        return None
    model_key = cands[0][0]        # mindst-samplede → mest værdifulde at måle
    if "/" not in model_key:
        return None
    p, m = model_key.split("/", 1)
    return (p, m) if p and m else None


def build_router_explore_surface() -> dict[str, object]:
    """Mission Control — read-only: eksplorations-status + kandidater der ville blive samplet."""
    from core.runtime.settings import load_settings
    try:
        s = load_settings()
        default_key = f"{s.visible_model_provider}/{s.visible_model_name}"
    except Exception:
        default_key = "?"
    return {"active": True, "explore_live": is_explore_live(),
            "sample_every_n_autonomous": _SAMPLE_EVERY,
            "counter": _kv_get(_COUNTER_KEY, 0),
            "candidates": [{"model": k, "samples": n} for k, n in _candidates(default_key)][:8]}
