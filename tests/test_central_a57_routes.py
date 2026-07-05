import asyncio
from unittest.mock import patch


# ── Route 1: /central/events (A7) ──────────────────────────────────────────

def test_events_no_family_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_items = [{"id": 1, "family": "runtime"}, {"id": 2, "family": "tool"}]
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.eventbus.bus.event_bus.recent", lambda limit=50: fake_items), \
         patch("core.eventbus.bus.event_bus.recent_by_family",
               lambda family, limit=50: (_ for _ in ()).throw(AssertionError("må ikke kaldes"))), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_events())
    assert out["items"] == fake_items
    assert out["count"] == 2
    assert out["family"] is None
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "events" and a[1] == "feed"
    assert a[2]["count"] == 2 and a[2]["family"] == "all"


def test_events_with_family_uses_by_family():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_items = [{"id": 9, "family": "tool"}]
    seen = {}
    calls = {"absorb": []}

    def _by_family(family, limit=50):
        seen["family"] = family
        return fake_items

    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.eventbus.bus.event_bus.recent_by_family", _by_family), \
         patch("core.eventbus.bus.event_bus.recent",
               lambda limit=50: (_ for _ in ()).throw(AssertionError("må ikke kaldes"))), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_events(family="tool"))
    assert seen["family"] == "tool"
    assert out["items"] == fake_items
    assert out["family"] == "tool"
    a, k = calls["absorb"][0]
    assert a[2]["family"] == "tool"


def test_events_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.eventbus.bus.event_bus.recent", boom), \
         patch("core.eventbus.bus.event_bus.recent_by_family", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_events())
    assert out["items"] == []
    assert out["count"] == 0
    assert isinstance(out, dict)
    assert calls["absorb"], "absorb skal stadig kaldes ved fejl"


# ── Route 2: /central/memory-health (A5) ───────────────────────────────────

def test_memory_health_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_surface = {
        "jarvis_brain": {"added_today": 42},
        "daily_journal": {"today_exists": True},
    }
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("apps.api.jarvis_api.routes.mission_control.mc_memory_pipeline",
               lambda limit=10: fake_surface), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_memory_health())
    assert out["memory"] == fake_surface
    assert out["added_today"] == 42
    assert out["journal_today"] is True
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "memory" and a[1] == "pipeline"
    assert a[2]["added_today"] == 42 and a[2]["journal_today"] is True


def test_memory_health_flags_when_no_journal():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_surface = {
        "jarvis_brain": {"added_today": 0},
        "daily_journal": {"today_exists": False},
    }
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("apps.api.jarvis_api.routes.mission_control.mc_memory_pipeline",
               lambda limit=10: fake_surface), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_memory_health())
    assert out["journal_today"] is False
    a, k = calls["absorb"][0]
    flag_if = k.get("flag_if")
    assert flag_if is not None
    assert flag_if(a[2]) is True  # journal mangler → flag


def test_memory_health_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("apps.api.jarvis_api.routes.mission_control.mc_memory_pipeline", boom), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_memory_health())
    assert out["memory"] == {}
    assert out["added_today"] == 0
    assert out["journal_today"] is False
    assert isinstance(out, dict)
    assert calls["absorb"], "absorb skal stadig kaldes ved fejl"
