from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from core.services import automation_dsl
from core.services import cross_session_threads
from core.services import outcome_learning
from core.services import scheduled_job_windows
from core.services import skill_contract_registry as skills


@pytest.fixture()
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))


def test_automation_dsl_registers_and_expires(isolated_storage):
    dsl = automation_dsl.validate_automation(
        {
            "name": "daily-summary",
            "description": "Send a daily summary to internal lane.",
            "channel": "internal",
            "trigger": {"type": "schedule", "config": {"cron": "0 8 * * *"}},
            "action": {
                "type": "llm_prompt",
                "prompt_template": "Summarize the day.",
                "vars": {"tone": "concise"},
            },
            "expires_in_hours": 1,
        }
    )
    automation_id = automation_dsl.register_automation(dsl)

    surface = automation_dsl.build_automation_dsl_surface()
    assert surface["active"] is True
    assert surface["total"] == 1
    assert surface["recent_active"][0]["automation_id"] == automation_id

    assert automation_dsl.tick()["expired"] == 0
    items = automation_dsl.list_automations()
    items[0]["expires_at"] = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    automation_dsl._save(items)
    assert automation_dsl.tick()["expired"] == 1


def test_scheduled_job_windows_fire_once_per_day(isolated_storage):
    window_id = scheduled_job_windows.register_window(
        name="overnight-batch",
        start_hour=22,
        end_hour=6,
        allowed_providers=["local"],
        prefer_free_first=True,
    )

    fires = []
    first = scheduled_job_windows.tick_windows(
        now=datetime(2026, 5, 12, 23, 0, tzinfo=UTC),
        callback=lambda window, day_key: fires.append((window["window_id"], day_key)),
    )
    second = scheduled_job_windows.tick_windows(
        now=datetime(2026, 5, 12, 23, 30, tzinfo=UTC),
        callback=lambda window, day_key: fires.append((window["window_id"], day_key)),
    )

    surface = scheduled_job_windows.build_scheduled_job_windows_surface()
    assert surface["active"] is True
    assert surface["total_windows"] == 1
    assert surface["inside_window_now"] in ([], ["overnight-batch"])
    assert len(first) == 1
    assert second == []
    assert fires == [(window_id, "2026-05-12-22")]


def test_skill_contract_registry_exposes_registered_contracts(monkeypatch):
    monkeypatch.setattr(skills, "_registry", {})

    manifest = skills.SkillManifest(
        spec=skills.SkillSpec(
            name="test_skill",
            version="1.0",
            description="Test skill contract.",
        ),
        permissions=skills.SkillPermissionSpec(
            scopes=("memory:read", "session:read"),
            requires_approval=True,
        ),
        tags=("memory", "test"),
    )
    skills.register_skill(manifest)

    result = skills.check_permissions("test_skill", {"memory:read"})
    surface = skills.build_skill_contract_registry_surface()

    assert result["found"] is True
    assert result["ok"] is False
    assert result["missing"] == ["session:read"]
    assert surface["active"] is True
    assert surface["total_skills"] == 1
    assert surface["approval_gated"] == 1
    assert surface["skills"][0]["name"] == "test_skill"


def test_outcome_learning_decays_and_surfaces_best_context(isolated_storage):
    outcome_learning.record_outcome(
        context="prompt:status",
        outcome="success",
        weight=2.0,
        metadata={"source": "test"},
    )
    outcome_learning.record_outcome(
        context="prompt:status",
        outcome="error",
        weight=1.0,
    )

    strength = outcome_learning.pattern_strength("prompt:status")
    surface = outcome_learning.build_outcome_learning_surface()

    assert strength["context"] == "prompt:status"
    assert strength["raw_count"] == 2
    assert strength["strength"] > 0
    assert surface["active"] is True
    assert surface["total_records"] == 2
    assert surface["summary"].startswith("2 observationer")


def test_cross_session_threads_surface_tracks_resume_state(isolated_storage):
    thread = cross_session_threads.create_thread(
        topic="Partial triage",
        synopsis="Continue the next batch.",
        opened_in_session="session-1",
    )
    assert cross_session_threads.pause_thread(thread["thread_id"], note="waiting")
    assert cross_session_threads.resume_thread(
        thread["thread_id"], new_synopsis="Continue with autonomy batch."
    )
    assert cross_session_threads.close_thread(thread["thread_id"], reason="done")

    surface = cross_session_threads.build_cross_session_threads_surface()
    assert surface["total"] == 1
    assert surface["counts"] == {"active": 0, "paused": 0, "closed": 1}
    assert surface["summary"] == "Tråde: 1 lukkede"
    assert surface["active"] is False
