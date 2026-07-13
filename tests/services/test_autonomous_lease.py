from __future__ import annotations

import importlib

import core.services.autonomous_lease as lease


def _reload():
    return importlib.reload(lease)


def test_visible_active_false_by_default(isolated_runtime):
    mod = _reload()
    assert mod.visible_active() is False


def test_visible_active_toggles_with_acquire_release(isolated_runtime):
    mod = _reload()
    mod.acquire_visible(ttl_s=120, now_ts=1000.0)
    assert mod.visible_active(now_ts=1000.0) is True
    mod.release_visible()
    assert mod.visible_active(now_ts=1000.0) is False


def test_visible_active_false_after_ttl_expiry(isolated_runtime):
    mod = _reload()
    mod.acquire_visible(ttl_s=120, now_ts=1000.0)
    assert mod.visible_active(now_ts=1050.0) is True
    # now past expiry (1000 + 120 = 1120)
    assert mod.visible_active(now_ts=1200.0) is False


def test_dispatch_proceeds_when_idle(isolated_runtime):
    mod = _reload()
    result = mod.try_autonomous_dispatch({"kind": "nudge"}, now_ts=1000.0)
    assert result["action"] == "proceed"
    assert mod.pending_markers() == []


def test_dispatch_deferred_while_visible_and_marker_stored(isolated_runtime):
    mod = _reload()
    mod.acquire_visible(ttl_s=120, now_ts=1000.0)
    result = mod.try_autonomous_dispatch({"kind": "nudge", "id": 7}, now_ts=1000.0)
    assert result["action"] == "deferred"
    assert result["reason"] == "visible-active"
    markers = mod.pending_markers()
    assert len(markers) == 1
    assert markers[0]["kind"] == "nudge"
    assert markers[0]["id"] == 7


def test_consume_markers_drains(isolated_runtime):
    mod = _reload()
    mod.acquire_visible(ttl_s=120, now_ts=1000.0)
    mod.try_autonomous_dispatch({"kind": "a"}, now_ts=1000.0)
    mod.try_autonomous_dispatch({"kind": "b"}, now_ts=1000.0)
    drained = mod.consume_markers()
    assert [m["kind"] for m in drained] == ["a", "b"]
    # second call is empty
    assert mod.consume_markers() == []
    assert mod.pending_markers() == []


def test_markers_list_is_bounded(isolated_runtime):
    mod = _reload()
    mod.acquire_visible(ttl_s=10_000, now_ts=1000.0)
    total = mod.MAX_MARKERS + 20
    for i in range(total):
        mod.try_autonomous_dispatch({"seq": i}, now_ts=1000.0)
    markers = mod.pending_markers()
    assert len(markers) == mod.MAX_MARKERS
    # oldest dropped: first retained seq is total - MAX_MARKERS
    assert markers[0]["seq"] == total - mod.MAX_MARKERS
    assert markers[-1]["seq"] == total - 1
