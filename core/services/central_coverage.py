"""core/services/central_coverage.py

Fase 1c (LivingNeuron v3 §4): gør surface-count + Central-DÆKNING RUNTIME-MÅLT — ikke hardcodede gæt.

Baggrund: drafts/råd var uenige om surface-antallet (35 vs 74 vs 78). Runtime-sandheden er 74
(`len(signal_surface_router._get_router())`). Netop derfor MÅ tallet måles, ikke skrives i en spec.
Og det gamle "~85-90% af signal-volumen synlig" var et gæt uden nævner. Her defineres en REPRODUCERBAR
dæknings-formel over et eksplicit event-vindue.

Alt read-only, self-safe, kaster ALDRIG. Dæknings-tal er operationelle (ikke privat inner-life) →
skrives til den normale tidsserie (cluster=system), ikke den egress-fri sti.

DÆKNINGS-DEFINITIONER (reproducerbare):
  * ``family_coverage_seen`` = |routed ∩ seen| / |seen| — af de familier der FAKTISK publicerer i
    vinduet, hvor stor en andel router Centralen? (ikke /alle-registrerede: mange af de 166 familier
    publicerer sjældent, og 37 er bevidst mørke §24.4 — så /166 ville understate groft.)
  * ``volume_coverage`` = routed-events / alle-events i vinduet — den ærlige erstatning for "% synlig".
"""
from __future__ import annotations

import os
from typing import Any

_DEFAULT_WINDOW = 2000

# ── STRUKTUREL DÆKNING (§11 #5) ──────────────────────────────────────────────────────
# Det committede connectivity-kort (811 filer, KOBLET/DARK/LLM-spild) lever i dag KUN i en
# manuel rapport → Centralen "ved" ikke den er strukturelt blind for ~219 DARK-filer.
# Her læses kortet ved runtime (cachet — det er stort/statisk) og dets summary eksponeres
# som et central-signal, så den strukturelle blindhed bliver RUNTIME-KENDT.
_MATRIX_REL = os.path.join("docs", "central_connectivity_matrix.json")
_matrix_cache: dict[str, Any] | None = None


def _repo_root() -> str:
    # core/services/central_coverage.py → repo-rod = tre niveauer op.
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_connectivity_matrix() -> dict[str, Any] | None:
    """Læs det committede connectivity-kort ved runtime (cachet). Self-safe → None ved fejl.

    Kortet er statisk pr. commit; vi cacher det efter første læsning så gentagne ticks ikke
    parser ~811 rækker igen. Sætter aldrig egress i gang selv."""
    global _matrix_cache
    if _matrix_cache is not None:
        return _matrix_cache
    try:
        import json
        path = os.path.join(_repo_root(), _MATRIX_REL)
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            _matrix_cache = data
            return data
    except Exception:
        pass
    return None


def _reset_matrix_cache_for_tests() -> None:
    global _matrix_cache
    _matrix_cache = None


def structural_coverage(*, top_dark: int = 8) -> dict[str, Any]:
    """Reducér connectivity-kortet til RUNTIME-signal-skalarer: total/koblet/dark/llm-spild +
    strukturel dæknings-ratio + top dark-families (efter hvor mange filer de bærer). Self-safe.

    Definitioner (fra kortets egne kvadranter):
      * connected = KOBLET (direkte/indirekte wired til Centralen)
      * dark = FRAKOBLET+DARK (bærer event-families Centralen IKKE ser)
      * llm_waste = FRAKOBLET+LLM (kalder LLM men er ukoblet — kognitivt spild i mørke)
      * structural_ratio = koblet / total  (den ærlige strukturelle dækning, IKKE volumen-vinduet)
    """
    out: dict[str, Any] = {"available": False}
    m = load_connectivity_matrix()
    if not m:
        return out
    try:
        counts = m.get("counts") or {}
        total = int(m.get("total") or 0)
        connected = int(counts.get("KOBLET", 0))
        dark = int(counts.get("FRAKOBLET+DARK", 0))
        llm_waste = int(counts.get("FRAKOBLET+LLM", 0))
        silent = int(counts.get("FRAKOBLET-STILLE", 0))
        # Top dark-families: hvilke event-families bærer flest DARK-filer (= største blinde pletter).
        fam_load: dict[str, int] = {}
        for row in (m.get("rows") or []):
            if row.get("quadrant") == "FRAKOBLET+DARK":
                for fam in (row.get("dark_families") or []):
                    fam_load[str(fam)] = fam_load.get(str(fam), 0) + 1
        top = sorted(fam_load.items(), key=lambda kv: kv[1], reverse=True)[: max(int(top_dark), 0)]
        out.update({
            "available": True,
            "total": total,
            "connected": connected,
            "dark": dark,
            "llm_waste": llm_waste,
            "silent": silent,
            "structural_ratio": (round(connected / total, 4) if total else None),
            "dark_ratio": (round(dark / total, 4) if total else None),
            "top_dark_families": [{"family": f, "files": n} for f, n in top],
        })
    except Exception:
        return {"available": False}
    return out


def measure(*, window: int = _DEFAULT_WINDOW) -> dict[str, Any]:
    """Mål surface-count + dækning LIVE fra registry + routing-tabeller + event-vinduet. Self-safe."""
    out: dict[str, Any] = {"window": int(window)}

    # 1) Surfaces registreret (RUNTIME — erstatter hardcodet 35/74/78).
    try:
        from core.services.signal_surface_router import _get_router
        out["surfaces_registered"] = len(_get_router())
    except Exception:
        out["surfaces_registered"] = None

    # 2) Nerver Centralen FAKTISK har samples for (dens "øjne" — tæl dine egne øjne).
    #    CROSS-PROCES (api:8080 + runtime:8011): en frisk probe-proces har tom in-memory
    #    timeseries → brug xproc-merge (fixer 1c's misvisende 0), fald tilbage til lokal.
    try:
        from core.services.central_signal_health import nerves_observed_xproc
        out["nerves_observed"] = nerves_observed_xproc()
    except Exception:
        try:
            from core.services import central_timeseries
            out["nerves_observed"] = len(central_timeseries.nerves())
        except Exception:
            out["nerves_observed"] = None

    # 3) Routing-tabeller (hvad Centralen ER wired til at se).
    routed: set[str] = set()
    try:
        from core.services.eventbus_central_bridge import (FAMILY_ROUTES,
                                                           PRIVATE_FAMILIES_EXCLUDED_M0,
                                                           PRIVATE_NO_EGRESS_ROUTES)
        routed = set(FAMILY_ROUTES) | set(PRIVATE_NO_EGRESS_ROUTES)
        out["families_routed"] = len(routed)
        out["families_excluded_by_design"] = len(PRIVATE_FAMILIES_EXCLUDED_M0)
    except Exception:
        out["families_routed"] = None
    try:
        from core.eventbus.events import ALLOWED_EVENT_FAMILIES
        out["families_registered"] = len(ALLOWED_EVENT_FAMILIES)
    except Exception:
        out["families_registered"] = None

    # 4) Hvad flyder FAKTISK i vinduet → reproducerbar dækning.
    seen: dict[str, int] = {}
    try:
        from core.eventbus.bus import event_bus
        for ev in event_bus.recent(limit=int(window)):
            fam = str(ev.get("kind") or "").split(".", 1)[0]
            if fam:
                seen[fam] = seen.get(fam, 0) + 1
    except Exception:
        pass
    total_vol = sum(seen.values())
    routed_vol = sum(v for f, v in seen.items() if f in routed)
    out["families_seen"] = len(seen)
    out["events_in_window"] = total_vol
    out["family_coverage_seen"] = (round(len(set(seen) & routed) / len(seen), 4) if seen else None)
    out["volume_coverage"] = (round(routed_vol / total_vol, 4) if total_vol else None)
    return out


def record_coverage(*, window: int = _DEFAULT_WINDOW) -> dict[str, Any]:
    """Mål + skriv nøgletal til tidsserien (cluster=system) så dækning kan plottes over tid."""
    m = measure(window=window)
    try:
        from core.services import central_timeseries as ts
        if m.get("surfaces_registered") is not None:
            ts.record("system", "coverage_surfaces", value=float(m["surfaces_registered"]))
        if m.get("nerves_observed") is not None:
            ts.record("system", "coverage_nerves", value=float(m["nerves_observed"]))
        if m.get("volume_coverage") is not None:
            ts.record("system", "coverage_volume", value=float(m["volume_coverage"]),
                      meta={"window": m["window"], "events": m["events_in_window"]})
        if m.get("family_coverage_seen") is not None:
            ts.record("system", "coverage_family", value=float(m["family_coverage_seen"]))
    except Exception:
        pass

    # Strukturel dækning (§11 #5): gør Centralens STRUKTURELLE blindhed runtime-kendt. Observeres
    # egress-frit via record_private (kun skalarer i meta) → Centralen "kender" nu at den er blind
    # for ~219 DARK-filer, ikke bare hvad der tilfældigvis flød i event-vinduet.
    try:
        sc = structural_coverage()
        if sc.get("available") and sc.get("structural_ratio") is not None:
            from core.services.central_private_observe import record_private
            record_private(
                "system", "structural_coverage",
                value=float(sc["structural_ratio"]),
                meta={"total": sc["total"], "connected": sc["connected"],
                      "dark": sc["dark"], "llm_waste": sc["llm_waste"],
                      "dark_ratio": sc["dark_ratio"]},
            )
        m["structural"] = sc
    except Exception:
        pass
    return m


def run_coverage_tick(*, trigger: str = "cadence", last_visible_at: str = "") -> dict[str, object]:
    """Cadence-producer: mål + registrér dækning (~hvert 30 min). Self-safe."""
    m = record_coverage()
    return {"status": "ok", "surfaces_registered": m.get("surfaces_registered"),
            "nerves_observed": m.get("nerves_observed"),
            "volume_coverage": m.get("volume_coverage"),
            "family_coverage_seen": m.get("family_coverage_seen")}


def register_coverage_producer() -> None:
    """Registrér dæknings-målingen som cadence-producer (~hvert 30 min)."""
    from core.services.internal_cadence import ProducerSpec, register_producer
    register_producer(ProducerSpec(
        name="central_coverage",
        cooldown_minutes=30,
        visible_grace_minutes=0,
        run_fn=run_coverage_tick,
        priority=6,
    ))


def build_central_coverage_surface() -> dict[str, object]:
    """Mission Control surface — read-only, runtime-målt dæknings-projektion (volumen + struktur)."""
    return {"active": True, **measure(), "structural": structural_coverage()}
