from __future__ import annotations

from datetime import UTC, datetime, timedelta


def _facts(
    *,
    sampled_at: str | None = None,
    load_1m: float = 0.5,
    cpu_count: int = 4,
    memory_total_bytes: int = 100,
    memory_available_bytes: int = 40,
    disk_total_bytes: int = 100,
    disk_free_bytes: int = 40,
    temperature_celsius: float | None = 65.0,
) -> dict[str, object]:
    return {
        "sampled_at": sampled_at or datetime.now(UTC).isoformat(),
        "load_1m": load_1m,
        "cpu_count": cpu_count,
        "load_source": "test",
        "memory_total_bytes": memory_total_bytes,
        "memory_available_bytes": memory_available_bytes,
        "memory_source": "test",
        "disk_total_bytes": disk_total_bytes,
        "disk_free_bytes": disk_free_bytes,
        "disk_source": "test",
        "temperature_celsius": temperature_celsius,
        "thermal_source": "test",
    }


def test_embodied_state_builds_bounded_surface_from_host_facts(isolated_runtime) -> None:
    embodied = isolated_runtime.embodied_state
    surface = embodied.build_embodied_state_from_facts(
        _facts(
            load_1m=4.8,
            cpu_count=4,
            memory_available_bytes=20,
            disk_free_bytes=20,
            temperature_celsius=84.0,
        )
    )

    assert surface["state"] == "strained"
    assert surface["primary_state"] == "strained"
    assert surface["strain_level"] == "high"
    assert surface["authority"] == "authoritative"
    assert surface["visibility"] == "internal-only"
    assert surface["kind"] == "embodied-runtime-state"
    assert surface["facts"]["cpu"]["bucket"] == "strained"
    assert surface["facts"]["memory"]["bucket"] == "loaded"
    assert surface["facts"]["disk"]["bucket"] == "loaded"
    assert surface["facts"]["thermal"]["bucket"] == "strained"


def test_embodied_state_can_enter_recovering_without_memory_or_identity_mix(
    isolated_runtime,
) -> None:
    embodied = isolated_runtime.embodied_state
    previous = embodied.build_embodied_state_from_facts(
        _facts(
            load_1m=6.0,
            cpu_count=4,
            memory_available_bytes=5,
            disk_free_bytes=3,
            temperature_celsius=95.0,
        )
    )
    recovering = embodied.build_embodied_state_from_facts(
        _facts(
            load_1m=1.8,
            cpu_count=4,
            memory_available_bytes=30,
            disk_free_bytes=18,
            temperature_celsius=68.0,
        ),
        previous=previous,
    )

    assert recovering["state"] == "recovering"
    assert recovering["primary_state"] == "loaded"
    assert recovering["recovery_state"] == "recovering"
    assert "memory" not in recovering
    assert "identity" not in recovering


def test_embodied_state_marks_staleness_from_old_source_timestamp(isolated_runtime) -> None:
    embodied = isolated_runtime.embodied_state
    old_sample = (datetime.now(UTC) - timedelta(seconds=90)).isoformat()
    surface = embodied.build_embodied_state_from_facts(_facts(sampled_at=old_sample))

    assert surface["freshness"]["state"] == "stale"
    assert surface["freshness"]["age_seconds"] >= 90


def test_heartbeat_self_knowledge_section_includes_embodied_state_guidance(
    isolated_runtime,
    monkeypatch,
) -> None:
    prompt_contract = isolated_runtime.prompt_contract
    monkeypatch.setattr(
        isolated_runtime.embodied_state,
        "build_embodied_state_prompt_section",
        lambda surface=None: "\n".join(
            [
                "Embodied host state (authoritative runtime truth, internal-only):",
                "- state=strained | primary=strained | strain=high | recovery=steady | freshness=fresh",
                "- guidance=Prefer bounded noop/ping over extra internal work while host/body state is strained or degraded.",
            ]
        ),
    )

    section = prompt_contract._heartbeat_self_knowledge_section()
    assert section is not None
    assert "Embodied host state" in section
    assert "Prefer bounded noop/ping" in section


def test_embodied_state_prompt_section_includes_somatic_overlay(
    isolated_runtime,
    monkeypatch,
) -> None:
    embodied = isolated_runtime.embodied_state
    monkeypatch.setattr(
        "core.services.somatic_daemon.build_body_state_surface",
        lambda: {
            "energy_budget": 72,
            "circadian_preference": "morgen",
            "wake_state": "alert",
            "pressure": "low",
        },
    )

    section = embodied.build_embodied_state_prompt_section(
        {
            "state": "steady",
            "primary_state": "steady",
            "strain_level": "low",
            "recovery_state": "steady",
            "freshness": {"state": "fresh"},
            "facts": {
                "cpu": {"bucket": "steady"},
                "memory": {"bucket": "steady"},
                "disk": {"bucket": "steady"},
                "thermal": {"bucket": "steady"},
            },
        }
    )

    assert section is not None
    assert "somatic=energy_budget=72" in section
    assert "circadian_preference=morgen" in section
    assert "wake_state=alert" in section


def test_mission_control_runtime_and_embodied_endpoint_expose_state(
    isolated_runtime,
    monkeypatch,
) -> None:
    mission_control = isolated_runtime.mission_control
    embodied = {
        "state": "loaded",
        "primary_state": "loaded",
        "strain_level": "elevated",
        "recovery_state": "steady",
        "freshness": {"state": "fresh", "age_seconds": 0},
        "facts": {
            "cpu": {"bucket": "loaded"},
            "memory": {"bucket": "steady"},
            "disk": {"bucket": "steady"},
            "thermal": {"bucket": "unavailable"},
        },
        "seam_usage": {
            "runtime_self_model": True,
            "mission_control_runtime_truth": True,
            "heartbeat_context": True,
            "heartbeat_prompt_grounding": True,
        },
        "authority": "authoritative",
        "visibility": "internal-only",
        "kind": "embodied-runtime-state",
    }
    monkeypatch.setattr(
        isolated_runtime.embodied_state,
        "build_embodied_state_surface",
        lambda: embodied,
    )
    monkeypatch.setattr(mission_control, "build_embodied_state_surface", lambda: embodied)

    endpoint = mission_control.mc_embodied_state()
    runtime = mission_control.mc_runtime()

    assert endpoint["state"] == "loaded"
    assert runtime["runtime_embodied_state"]["state"] == "loaded"
    assert runtime["runtime_embodied_state"]["visibility"] == "internal-only"
