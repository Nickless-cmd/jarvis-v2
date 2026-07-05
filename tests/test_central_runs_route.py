import asyncio

from unittest.mock import patch


def test_runs_list_shapes_and_absorbs():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_runs = [
        {"run_id": "r-1", "lane": "primary", "status": "completed", "model": "deepseek"},
        {"run_id": "r-2", "lane": "primary", "status": "failed", "model": "glm"},
        {"run_id": "r-3", "lane": "cheap", "status": "cancelled", "model": "kimi"},
    ]
    calls = {"absorb": []}
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.db.recent_visible_runs", lambda limit=5: fake_runs), \
         patch.object(m, "absorb", lambda *a, **k: calls["absorb"].append((a, k))):
        out = asyncio.new_event_loop().run_until_complete(m.get_runs())
    assert out["runs"] == fake_runs
    assert out["count"] == 3
    assert out["failed_count"] == 2  # failed + cancelled
    assert calls["absorb"], "absorb skal kaldes"
    a, k = calls["absorb"][0]
    assert a[0] == "run" and a[1] == "list"


def test_runs_detail_found():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_runs = [
        {"run_id": "r-1", "lane": "primary", "status": "completed", "model": "deepseek"},
        {"run_id": "r-2", "lane": "primary", "status": "failed", "model": "glm"},
    ]
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.db.recent_visible_runs", lambda limit=50: fake_runs), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_run_detail("r-2"))
    assert out["found"] is True
    assert out["run"]["run_id"] == "r-2"


def test_runs_detail_not_found():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    fake_runs = [
        {"run_id": "r-1", "lane": "primary", "status": "completed", "model": "deepseek"},
    ]
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.db.recent_visible_runs", lambda limit=50: fake_runs), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_run_detail("nope"))
    assert out["found"] is False
    assert out["run"] is None


def test_runs_list_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.db.recent_visible_runs", boom), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_runs())
    assert out["runs"] == [] and out["count"] == 0 and out["failed_count"] == 0


def test_runs_detail_self_safe_on_producer_error():
    from apps.api.jarvis_api.routes import central_absorb_routes as m
    def boom(*a, **k): raise RuntimeError("nej")
    with patch.object(m, "require_central_owner", lambda: None), \
         patch("core.runtime.db.recent_visible_runs", boom), \
         patch.object(m, "absorb", lambda *a, **k: None):
        out = asyncio.new_event_loop().run_until_complete(m.get_run_detail("r-1"))
    assert out["found"] is False and out["run"] is None
