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


# --------------------------------------------------------------------------- #
# Bilag 2 — role- AND session-gated nudge projection
# --------------------------------------------------------------------------- #
def test_dispatch_default_marker_unchanged(isolated_runtime):
    """(1) Omitting the projection tags leaves the marker exactly as before."""
    mod = _reload()
    mod.acquire_visible(ttl_s=120, now_ts=1000.0)
    mod.try_autonomous_dispatch({"kind": "nudge"}, now_ts=1000.0)
    m = mod.pending_markers()[0]
    assert m["kind"] == "nudge"
    assert "scope" not in m and "session_id" not in m and "control_plane" not in m


def test_global_nudge_visible_to_everyone(isolated_runtime):
    mod = _reload()
    marker = {"kind": "creative-drift"}  # no scope → global self-signal
    assert mod.nudge_allowed_for(marker, user_id="owner1", role="owner") is True
    assert mod.nudge_allowed_for(marker, user_id="member1", role="member") is True


def test_control_plane_nudge_is_owner_only(isolated_runtime):
    mod = _reload()
    marker = {"kind": "council-convene", "control_plane": True}
    assert mod.nudge_allowed_for(marker, role="owner") is True
    assert mod.nudge_allowed_for(marker, role="member") is False
    # unknown role also denied (fails toward less exposure)
    assert mod.nudge_allowed_for(marker, role=None) is False


def test_user_scoped_nudge_does_not_leak_across_users(isolated_runtime):
    """(3) A user-scoped nudge surfaces only for the matching user."""
    mod = _reload()
    marker = {"kind": "tension", "scope": "userA"}
    assert mod.nudge_allowed_for(marker, user_id="userA", role="member") is True
    assert mod.nudge_allowed_for(marker, user_id="userB", role="member") is False
    # even the owner does not see another user's relational nudge
    assert mod.nudge_allowed_for(marker, user_id="userB", role="owner") is False


def test_session_gating_within_a_user(isolated_runtime):
    """(4) A session-scoped nudge is narrowed to its own conversation."""
    mod = _reload()
    marker = {"kind": "thread", "scope": "userA", "session_id": "s1"}
    assert (
        mod.nudge_allowed_for(marker, user_id="userA", session_id="s1") is True
    )
    assert (
        mod.nudge_allowed_for(marker, user_id="userA", session_id="s2") is False
    )
    # no session filter given → any session of the right user is allowed
    assert mod.nudge_allowed_for(marker, user_id="userA") is True


def test_markers_for_filters_and_drains_without_dropping_others(isolated_runtime):
    mod = _reload()
    mod.acquire_visible(ttl_s=10_000, now_ts=1000.0)
    mod.try_autonomous_dispatch({"kind": "global"}, now_ts=1000.0)
    mod.try_autonomous_dispatch({"kind": "a"}, now_ts=1000.0, scope="userA")
    mod.try_autonomous_dispatch({"kind": "b"}, now_ts=1000.0, scope="userB")
    mod.try_autonomous_dispatch(
        {"kind": "ctrl"}, now_ts=1000.0, control_plane=True
    )

    # userA (member) sees the global + its own scoped nudge, not userB's, not ctrl.
    got = mod.markers_for(user_id="userA", role="member", drain=True)
    kinds = sorted(m["kind"] for m in got)
    assert kinds == ["a", "global"]

    # draining userA's allowed markers left userB's and the control-plane one.
    remaining = sorted(m["kind"] for m in mod.pending_markers())
    assert remaining == ["b", "ctrl"]


def test_role_resolved_from_user_registry(isolated_runtime, monkeypatch):
    """Role falls back to the existing user registry when not passed."""
    mod = _reload()
    import core.identity.users as users

    def _fake_lookup(discord_id):
        if discord_id == "owner-did":
            return users.User(
                discord_id="owner-did",
                name="Bjørn",
                role="owner",
                workspace="bjorn",
                created_at="2026-01-01T00:00:00Z",
            )
        return None

    monkeypatch.setattr(users, "find_user_by_discord_id", _fake_lookup)

    ctrl = {"kind": "telemetry", "control_plane": True}
    # role resolved as owner from the registry → allowed
    assert mod.nudge_allowed_for(ctrl, user_id="owner-did") is True
    # unknown discord_id → role None → control-plane denied
    assert mod.nudge_allowed_for(ctrl, user_id="stranger-did") is False
