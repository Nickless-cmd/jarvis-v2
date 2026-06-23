"""Tests for cognitive-architecture-surfacen + dens TTL-cache (load-fix 2026-06-23)."""
from __future__ import annotations

import core.services.cognitive_architecture_surface as cas


def test_surface_shape():
    s = cas._build_cognitive_architecture_surface_uncached()
    for k in ("systems", "surfaces", "active_count", "total_count", "summary"):
        assert k in s
    assert isinstance(s["systems"], list) and s["total_count"] == len(s["systems"])


def test_cache_collapses_repeat_builds(monkeypatch):
    # MC poller hyppigt → inden for TTL skal build_uncached kun køre ÉN gang
    calls = {"n": 0}
    real = cas._build_cognitive_architecture_surface_uncached

    def _counted():
        calls["n"] += 1
        return real()
    monkeypatch.setattr(cas, "_build_cognitive_architecture_surface_uncached", _counted)
    # ryd evt. cache-rest fra andre tests
    try:
        from core.services import runtime_surface_cache as rsc
        rsc._TIMED_CACHE.pop("cognitive_architecture_surface", None)
    except Exception:
        pass
    a = cas.build_cognitive_architecture_surface()
    b = cas.build_cognitive_architecture_surface()
    c = cas.build_cognitive_architecture_surface()
    assert calls["n"] == 1            # kun ét reelt build trods 3 kald
    assert a is b is c               # samme cachede objekt (no-mutate-kontrakt)


def test_self_safe_falls_back_when_cache_unavailable(monkeypatch):
    # hvis cache-modulet fejler → stadig et fersk surface, aldrig en exception
    import core.services.runtime_surface_cache as rsc
    monkeypatch.setattr(rsc, "get_timed_runtime_surface",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("cache nede")))
    s = cas.build_cognitive_architecture_surface()
    assert "systems" in s and s["total_count"] >= 1
