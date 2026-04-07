from __future__ import annotations


def build_cognitive_architecture_surface() -> dict[str, object]:
    """Build a shared cognitive architecture surface for MC and self-model."""
    from apps.api.jarvis_api.services.heartbeat_runtime import _build_cognitive_surfaces

    surfaces = _build_cognitive_surfaces()
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
        "active_count": active_count,
        "total_count": len(systems),
        "summary": f"{active_count}/{len(systems)} cognitive systems active",
    }