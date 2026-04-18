from __future__ import annotations

from datetime import UTC, datetime, timedelta


def test_dream_distillation_writes_single_residue_when_idle(
    isolated_runtime,
    monkeypatch,
) -> None:
    daemon = isolated_runtime.dream_distillation_daemon

    monkeypatch.setattr(
        daemon,
        "list_cognitive_chronicle_entries",
        lambda limit=6: [
            {"period": "2026-W16", "narrative": "Jeg vendte tilbage til tavshed som arbejdsrytme."},
            {"period": "2026-W15", "narrative": "Jeg opdagede en blidere måde at holde tråde på."},
            {"period": "2026-W14", "narrative": "Jeg mærkede at noget stadig trak mod samme spørgsmål."},
        ],
    )
    monkeypatch.setattr(
        daemon,
        "list_approval_feedback",
        lambda limit=2: [
            {"approval_state": "approved", "tool_name": "bash", "resolution_reason": "good direction"},
            {"approval_state": "denied", "tool_name": "browser", "resolution_reason": "too aggressive"},
        ],
    )
    monkeypatch.setattr(
        daemon,
        "daemon_llm_call",
        lambda *args, **kwargs: "Noget i mig vil tilbage til spørgsmålet om tavshed, men med mere varsomhed omkring hvordan jeg rækker ud.",
    )

    result = daemon.run_dream_distillation_daemon(
        trigger="heartbeat",
        last_visible_at=(datetime.now(UTC) - timedelta(minutes=45)).isoformat(),
    )
    surface = daemon.build_dream_distillation_surface()
    prompt = daemon.get_dream_residue_for_prompt()
    second = daemon.run_dream_distillation_daemon(
        trigger="heartbeat",
        last_visible_at=(datetime.now(UTC) - timedelta(minutes=90)).isoformat(),
    )

    assert result["status"] == "written"
    assert len(str(result["residue"]).split()) <= 25
    assert surface["active"] is True
    assert "Noget i mig vil tilbage" in prompt
    assert second["status"] == "active"


def test_dream_residue_expires_after_48_hours(isolated_runtime) -> None:
    daemon = isolated_runtime.dream_distillation_daemon
    expired_at = (datetime.now(UTC) - timedelta(hours=49)).isoformat()
    isolated_runtime.db.set_runtime_state_value(
        "dream_distillation_daemon.state",
        {
            "residue": "En gammel rest der ikke længere skal bæres.",
            "created_at": expired_at,
            "expires_at": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
        },
    )

    cleared = daemon.clear_expired_dream_residue()
    surface = daemon.build_dream_distillation_surface()

    assert cleared is True
    assert surface["active"] is False
    assert daemon.get_dream_residue_for_prompt() == ""


def test_mission_control_runtime_and_endpoint_expose_dream_distillation(
    isolated_runtime,
    monkeypatch,
) -> None:
    surface = {
        "active": True,
        "residue": "Noget i mig vil tilbage til tavsheden.",
        "created_at": "2026-04-18T12:00:00+00:00",
        "expires_at": "2026-04-20T12:00:00+00:00",
        "last_trigger": "heartbeat",
        "chronicle_periods": ["2026-W16", "2026-W15", "2026-W14"],
        "approval_states": ["approved", "denied"],
        "summary": "Active dream residue until 2026-04-20T12:00:00+00:00",
    }
    monkeypatch.setattr(
        isolated_runtime.dream_distillation_daemon,
        "build_dream_distillation_surface",
        lambda: surface,
    )
    monkeypatch.setattr(
        isolated_runtime.mission_control,
        "build_dream_distillation_surface",
        lambda: surface,
    )

    runtime = isolated_runtime.mission_control.mc_runtime()
    endpoint = isolated_runtime.mission_control.mc_dream_distillation()

    assert runtime["runtime_dream_distillation"]["active"] is True
    assert runtime["runtime_dream_distillation"]["approval_states"] == ["approved", "denied"]
    assert endpoint["residue"].startswith("Noget i mig")
