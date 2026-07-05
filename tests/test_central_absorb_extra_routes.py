import asyncio
from unittest.mock import patch


# --- council -------------------------------------------------------------

def test_council_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake = {"sessions": [{"council_id": "a"}, {"council_id": "b"}], "summary": {}}
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.agent_runtime.build_council_surface", lambda limit=40: fake), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_council())
    assert out["count"] == 2
    assert len(out["sessions"]) == 2
    assert out["council"] == fake
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "council" and a[1] == "sessions"


def test_council_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.agent_runtime.build_council_surface", boom), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_council())
    assert isinstance(out, dict)
    assert out["sessions"] == [] and out["count"] == 0 and out["council"] == {}


# --- scheduled -----------------------------------------------------------

def test_scheduled_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake = [{"id": 1}, {"id": 2}, {"id": 3}]
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.scheduled_tasks.list_pending_for_current_user", lambda: fake), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_scheduled())
    assert out["count"] == 3
    assert out["tasks"] == fake
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "queue" and a[1] == "scheduled"


def test_scheduled_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.scheduled_tasks.list_pending_for_current_user", boom), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_scheduled())
    assert isinstance(out, dict)
    assert out["tasks"] == [] and out["count"] == 0


# --- autonomy ------------------------------------------------------------

def test_autonomy_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake = {
        "proposals": [
            {"id": "p1", "status": "pending"},
            {"id": "p2", "status": "approved"},
        ],
        "pending_count": 1,
    }
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.autonomy_proposal_queue.build_autonomy_proposal_surface", lambda limit=20: fake), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_autonomy())
    assert out["count"] == 2
    assert out["pending_count"] == 1
    assert out["autonomy"] == fake
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "autonomy" and a[1] == "proposal"


def test_autonomy_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.services.autonomy_proposal_queue.build_autonomy_proposal_surface", boom), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_autonomy())
    assert isinstance(out, dict)
    assert out["proposals"] == [] and out["count"] == 0 and out["pending_count"] == 0
    assert out["autonomy"] == {}
