"""Tests for heartbeat_runtime daemon wiring."""


def test_associative_recall_daemon_registered():
    """Verify associative_recall is registered in daemon_manager registry."""
    from core.services.daemon_manager import _REGISTRY

    assert "associative_recall" in _REGISTRY
    entry = _REGISTRY["associative_recall"]
    assert entry["module"] == "core.services.associative_recall"
    assert entry["default_cadence_minutes"] == 2
    assert entry["default_enabled"] is True


def test_associative_recall_tick_function_exists():
    """Verify tick_associative_recall is importable from associative_recall module."""
    from core.services.associative_recall import tick_associative_recall

    assert callable(tick_associative_recall)


def test_safe_surface_observes_to_central(monkeypatch):
    """Bjørn 2026-06-23: hver cognitive-surface skal OGSÅ observeres til Centralen (indre liv,
    ikke kun gates). _safe_surface fyrer cognitive_surface; throttlet pr. surface."""
    import core.services.heartbeat_runtime as hr
    from core.services.central_core import central
    hr._SURFACE_OBSERVE_AT.clear()
    fired = []
    monkeypatch.setattr(central(), "observe",
                        lambda ev: fired.append(ev) if isinstance(ev, dict) else None)
    d = {}
    hr._safe_surface(d, "soul", lambda: {"active": True})
    hr._safe_surface(d, "soul", lambda: {"active": True})  # throttlet → ingen 2. fyring
    surface_fires = [e for e in fired if e.get("nerve") == "cognitive_surface"]
    assert len(surface_fires) == 1
    assert surface_fires[0]["surface"] == "soul" and surface_fires[0]["cluster"] == "cognition"
    assert surface_fires[0]["active"] is True


def test_safe_surface_reports_failed_surface(monkeypatch):
    import core.services.heartbeat_runtime as hr
    from core.services.central_core import central
    hr._SURFACE_OBSERVE_AT.clear()
    fired = []
    monkeypatch.setattr(central(), "observe",
                        lambda ev: fired.append(ev) if isinstance(ev, dict) else None)
    d = {}
    hr._safe_surface(d, "broken", lambda: (_ for _ in ()).throw(RuntimeError("nej")))
    sf = [e for e in fired if e.get("nerve") == "cognitive_surface"]
    assert sf and sf[0]["active"] is False  # fejlet surface markeres inaktiv
    assert d["broken"]["error"] == "surface-build-failed"  # surface-bygning stadig self-safe
