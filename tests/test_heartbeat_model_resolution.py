from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace


def _settings(
    *,
    heartbeat_model_provider: str = "",
    heartbeat_model_name: str = "",
    heartbeat_auth_profile: str = "",
    cheap_model_lane: str = "cheap",
) -> SimpleNamespace:
    return SimpleNamespace(
        heartbeat_model_provider=heartbeat_model_provider,
        heartbeat_model_name=heartbeat_model_name,
        heartbeat_auth_profile=heartbeat_auth_profile,
        cheap_model_lane=cheap_model_lane,
    )


def test_select_heartbeat_target_prefers_heartbeat_specific_settings(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "load_settings",
        lambda: _settings(
            heartbeat_model_provider="ollama",
            heartbeat_model_name="llama3.1:8b",
        ),
    )
    monkeypatch.setattr(
        heartbeat_runtime,
        "resolve_provider_router_target",
        lambda lane: {
            "provider": "ollama",
            "model": "qwen3.5:9b",
            "auth_profile": "",
            "base_url": "http://127.0.0.1:11434",
        },
    )

    target = heartbeat_runtime._select_heartbeat_target()

    assert target["provider"] == "ollama"
    assert target["model"] == "llama3.1:8b"
    assert target["lane"] == "heartbeat"
    assert target["model_source"] == "runtime.settings.heartbeat_model"
    assert target["resolution_status"] == "heartbeat-configured"
    assert target["fallback_used"] is False


def test_select_heartbeat_target_falls_back_to_runtime_local_lane(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "load_settings",
        lambda: _settings(),
    )

    def _target(lane: str) -> dict[str, str]:
        if lane == "local":
            return {
                "provider": "ollama",
                "model": "qwen3.5:9b",
                "auth_profile": "",
                "base_url": "http://127.0.0.1:11434",
            }
        if lane == "visible":
            return {"provider": "openai", "model": "gpt-5-mini", "auth_profile": "default", "base_url": ""}
        return {"provider": "", "model": "", "auth_profile": "", "base_url": ""}

    monkeypatch.setattr(heartbeat_runtime, "resolve_provider_router_target", _target)

    target = heartbeat_runtime._select_heartbeat_target()

    assert target["lane"] == "local"
    assert target["provider"] == "ollama"
    assert target["model"] == "qwen3.5:9b"
    assert target["model_source"] == "provider-router.local-lane"
    assert target["resolution_status"] == "runtime-local"
    assert target["fallback_used"] is False


def test_select_heartbeat_target_uses_bounded_fallback_only_when_needed(
    isolated_runtime,
    monkeypatch,
) -> None:
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    monkeypatch.setattr(
        heartbeat_runtime,
        "load_settings",
        lambda: _settings(cheap_model_lane="cheap"),
    )

    def _target(lane: str) -> dict[str, str]:
        if lane == "visible":
            return {
                "provider": "ollama",
                "model": "llama3.1:8b-instruct",
                "auth_profile": "",
                "base_url": "http://127.0.0.1:11434",
            }
        return {"provider": "", "model": "", "auth_profile": "", "base_url": ""}

    monkeypatch.setattr(heartbeat_runtime, "resolve_provider_router_target", _target)

    target = heartbeat_runtime._select_heartbeat_target()

    assert target["lane"] == "visible"
    assert target["model"] == "llama3.1:8b-instruct"
    assert target["model_source"] == "provider-router.visible-lane-fallback"
    assert target["resolution_status"] == "bounded-fallback"
    assert target["fallback_used"] is True


def test_heartbeat_runtime_surface_exposes_model_resolution_observability(
    isolated_runtime,
) -> None:
    db = isolated_runtime.db
    heartbeat_runtime = isolated_runtime.heartbeat_runtime

    now = datetime.now(UTC).isoformat()
    db.upsert_heartbeat_runtime_state(
        state_id="default",
        last_tick_id="heartbeat-tick:test",
        last_tick_at=now,
        next_tick_at=now,
        schedule_state="scheduled",
        due=False,
        last_decision_type="noop",
        last_result="Heartbeat is idle.",
        blocked_reason="",
        currently_ticking=False,
        last_trigger_source="manual",
        scheduler_active=False,
        scheduler_started_at="",
        scheduler_stopped_at="",
        scheduler_health="manual-only",
        recovery_status="idle",
        last_recovery_at="",
        provider="ollama",
        model="qwen3.5:9b",
        lane="local",
        model_source="provider-router.local-lane",
        resolution_status="runtime-local",
        fallback_used=False,
        budget_status="bounded-internal-only",
        last_ping_eligible=False,
        last_ping_result="not-checked",
        last_action_type="",
        last_action_status="noop",
        last_action_summary="Heartbeat is idle.",
        last_action_artifact="",
        updated_at=now,
    )

    surface = heartbeat_runtime.heartbeat_runtime_surface()
    state = surface["state"]

    assert state["provider"] == "ollama"
    assert state["model"] == "qwen3.5:9b"
    assert state["lane"] == "local"
    assert state["model_source"] == "provider-router.local-lane"
    assert state["resolution_status"] == "runtime-local"
    assert state["fallback_used"] is False
