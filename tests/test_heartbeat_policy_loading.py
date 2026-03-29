from __future__ import annotations


def test_load_heartbeat_policy_reads_ping_fields_from_workspace_file(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    policy = heartbeat_runtime.load_heartbeat_policy()

    assert policy["present"] is True
    assert policy["enabled"] is True
    assert policy["allow_propose"] is True
    assert policy["allow_execute"] is True
    assert policy["allow_ping"] is True
    assert policy["ping_channel"] == "webchat"
    assert policy["kill_switch"] == "enabled"


def test_heartbeat_runtime_surface_exposes_loaded_ping_policy(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    surface = heartbeat_runtime.heartbeat_runtime_surface()

    assert surface["policy"]["allow_ping"] is True
    assert surface["policy"]["ping_channel"] == "webchat"
    assert surface["policy"]["kill_switch"] == "enabled"
    assert surface["policy"]["heartbeat_file"].endswith("/HEARTBEAT.md")
