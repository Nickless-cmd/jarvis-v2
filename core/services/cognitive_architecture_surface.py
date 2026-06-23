from __future__ import annotations

# MC poller cognitive-arkitekturen (~70 surfaces) hvert 60s, og DEN byggede FØR friskt hver
# gang (ingen cache) → stor backend-load (Bjørn 2026-06-23). TTL-cache (75s) collapser
# samtidige pollere til ÉN build og capper rebuild-raten uanset poll-frekvens. Surfaces
# afspejler indre tilstand der ændrer sig på minut-kadence → 75s staleness er fint.
# Kontrakt (get_timed_runtime_surface): callers MÅ IKKE mutere returværdien (kun læse).
_SURFACE_TTL_SECONDS = 75.0


def build_cognitive_architecture_surface() -> dict[str, object]:
    """Cached MC/self-model cognitive-architecture-surface. Self-safe → falder til fersk build."""
    try:
        from core.services.runtime_surface_cache import get_timed_runtime_surface
        return get_timed_runtime_surface(
            "cognitive_architecture_surface", _SURFACE_TTL_SECONDS,
            _build_cognitive_architecture_surface_uncached,
        )
    except Exception:
        return _build_cognitive_architecture_surface_uncached()


def _build_cognitive_architecture_surface_uncached() -> dict[str, object]:
    """Build a shared cognitive architecture surface for MC and self-model."""
    from core.services.heartbeat_runtime import _build_cognitive_surfaces
    from core.services.cognitive_core_experiments import (
        build_cognitive_core_experiments_surface,
    )

    surfaces = _build_cognitive_surfaces()
    cognitive_core_experiments = build_cognitive_core_experiments_surface()
    surfaces["cognitive_core_experiments"] = cognitive_core_experiments
    systems: list[dict[str, object]] = []

    for name, result in surfaces.items():
        active = bool(result) and (
            result.get("active", False)
            if isinstance(result, dict)
            else bool(result)
        )
        summary = (
            str(result.get("summary") or "")[:80]
            if isinstance(result, dict)
            else str(result or "")[:80]
        )
        systems.append({"system": name, "active": active, "summary": summary})

    active_count = sum(1 for item in systems if item.get("active"))
    return {
        "systems": systems,
        "surfaces": surfaces,
        "cognitive_core_experiments": cognitive_core_experiments,
        "active_count": active_count,
        "total_count": len(systems),
        "summary": f"{active_count}/{len(systems)} cognitive systems active",
    }
