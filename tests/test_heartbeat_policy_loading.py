from __future__ import annotations

from datetime import UTC, datetime


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


def test_merge_runtime_state_recomputes_next_tick_at_from_current_policy_interval(
    isolated_runtime,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime
    last_tick_at = "2026-04-01T17:52:52.146944+00:00"
    stale_next_tick_at = "2026-04-01T20:52:52.146944+00:00"

    merged = heartbeat_runtime._merge_runtime_state(
        policy={
            "enabled": True,
            "kill_switch": "enabled",
            "interval_minutes": 15,
            "budget_status": "bounded-internal-only",
            "summary": "interval=15m",
            "workspace": "/tmp/test-heartbeat-workspace",
        },
        persisted={
            **heartbeat_runtime._default_persisted_state(),
            "last_tick_at": last_tick_at,
            "next_tick_at": stale_next_tick_at,
        },
        now=datetime(2026, 4, 1, 18, 0, tzinfo=UTC),
    )

    assert merged["last_tick_at"] == last_tick_at
    assert merged["next_tick_at"] == "2026-04-01T18:07:52.146944+00:00"
    assert merged["due"] is False
