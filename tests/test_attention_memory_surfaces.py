from __future__ import annotations

import pytest


@pytest.fixture()
def isolated_storage(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("JARVIS_WORKSPACES_DIR", str(tmp_path / "workspaces"))
    ws = tmp_path / "workspaces" / "default"
    ws.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("core.runtime.workspace_paths.workspace_dir", lambda user_id=None: ws)


def test_memory_write_policy_queues_low_confidence_inferred_writes(isolated_storage):
    from core.services import memory_write_policy as policy

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(policy, "_write_timestamps", [])
    monkeypatch.setattr(policy, "_last_write_per_key", {})
    try:
        decision = policy.evaluate_write(
            key="note:triage",
            content="Review the next partial batch.",
            confidence=0.2,
            write_reason="inferred",
            metadata={"source": "test"},
        )

        surface = policy.build_memory_write_policy_surface()

        assert decision.decision == "queued"
        assert decision.allowed is False
        assert decision.queue_id is not None
        assert surface["pending_reviews"] == 1
        assert surface["review_queue_enabled"] is True
        assert policy.build_memory_write_policy_prompt_section() is not None
    finally:
        monkeypatch.undo()


def test_memory_breathing_records_access_and_surface_tracks_recent_window(monkeypatch):
    from core.services import memory_breathing as breathing

    breathing.reset_memory_breathing()
    monkeypatch.setattr(breathing, "_get_record_salience", lambda record_id: 0.4)
    monkeypatch.setattr(
        "core.runtime.db.update_private_brain_record_salience",
        lambda record_id, salience: None,
    )

    updated = breathing.record_access(["r-1", "r-2"], context="test")
    surface = breathing.build_memory_breathing_surface()

    assert updated == {"r-1": 0.45, "r-2": 0.45}
    assert surface["active"] is True
    assert surface["recent_accesses"] == 2
    assert surface["unique_records_touched"] == 2
    breathing.reset_memory_breathing()


def test_spaced_repetition_schedules_and_completes_reviews(isolated_storage):
    from core.services import spaced_repetition as sr

    review_ids = sr.schedule_reviews_on_completion(
        topic="partial batch",
        plan_id="plan-1",
        intervals_days=(1, 3, 7),
    )
    assert len(review_ids) == 3

    due = sr.list_due_reviews(now=sr.datetime.now(sr.UTC) + sr.timedelta(days=4))
    assert due

    result = sr.complete_review(review_ids[0], score=0.9)
    assert result is not None
    assert result["profile"]["completed_count"] == 1

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        sr,
        "list_due_reviews",
        lambda now=None, limit=20: [{"topic": "partial batch"}],
    )
    surface = sr.build_spaced_repetition_surface()
    try:
        assert surface["active"] is True
        assert surface["profile_count"] == 1
        assert sr.build_spaced_repetition_prompt_section() is not None
    finally:
        monkeypatch.undo()


def test_thought_thread_surface_and_prompt_section_use_recent_thoughts(monkeypatch):
    from core.services import thought_thread as thread

    thread.reset_thought_thread()
    now = thread.datetime.now(thread.UTC)
    monkeypatch.setattr(
        "core.runtime.db.list_private_brain_records",
        lambda limit=200, status="active": [
                {
                    "record_id": "t-1",
                    "record_type": "thought-stream-fragment",
                    "focus": "partial batch planning",
                    "summary": "Partial batch planning for next steps.",
                    "created_at": (now - thread.timedelta(minutes=12)).isoformat(),
                },
                {
                    "record_id": "t-2",
                    "record_type": "meta-reflection",
                    "focus": "partial batch progress",
                    "summary": "Partial batch progress remains in focus.",
                    "created_at": (now - thread.timedelta(minutes=4)).isoformat(),
                },
            ],
        )

    surface = thread.build_thought_thread_surface()
    prompt = thread.build_thought_thread_prompt_section()

    assert surface["active"] is True
    assert surface["carrying_count"] == 2
    assert "partial" in surface["theme"]
    assert "batch" in surface["theme"]
    assert prompt is not None
    assert "Du holdt tråden" in prompt
    thread.reset_thought_thread()


def test_sustained_attention_surface_and_prompt_section_reflect_projects(isolated_storage):
    from core.services import sustained_attention as sa

    project = sa.create_project(
        name="Batch triage",
        description="Carry the next capability batch.",
        why="Keep partial services honest.",
        priority="high",
        autonomy_level="own",
    )
    assert sa.add_progress(project["id"], "Initial review landed.")

    surface = sa.build_sustained_attention_surface()
    prompt = sa.build_sustained_attention_prompt_section()

    assert surface["active"] is True
    assert surface["active_count"] == 1
    assert surface["by_autonomy"] == {"own": 1}
    assert surface["summary"].startswith("Fokus:")
    assert prompt is not None
    assert "Batch triage" in prompt
    assert "own" in prompt
