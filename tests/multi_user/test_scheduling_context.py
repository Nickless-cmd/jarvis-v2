"""When a scheduled task fires, the dispatcher must set workspace_context
to the task's scheduled_for_user_id BEFORE calling the run function.
Otherwise Jarvis wakes up in default/owner context and operator tools
route to the wrong bridge.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

BJORN_ID = "1246415163603816499"
MIKKEL_ID = "238975101381378048"


@pytest.fixture
def mu_env(tmp_path, monkeypatch):
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    cfg = tmp_path / "config"; cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "users.json").write_text(json.dumps({
        "users": [
            {"discord_id": BJORN_ID, "name": "Bjørn", "role": "owner", "workspace": "bjorn", "created_at": "2026-01-01"},
            {"discord_id": MIKKEL_ID, "name": "Mikkel", "role": "member", "workspace": "mikkel", "created_at": "2026-01-01"},
        ]
    }))
    # Match the same fixture pattern used by other multi_user tests
    import core.runtime.config as cfgmod
    monkeypatch.setattr(cfgmod, "CONFIG_DIR", cfg, raising=False)
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    import importlib
    import core.runtime.db as dbmod
    importlib.reload(dbmod)
    yield tmp_path


def test_dispatch_sets_user_context_from_scheduled_for_user_id(mu_env):
    """When a task tagged for Mikkel fires, the dispatcher sets context
    to Mikkel's user_id before invoking the run callback."""
    from core.identity.workspace_context import current_user_id
    from core.services.scheduled_task_runner import fire_scheduled_task

    seen_user_id = {}

    def fake_runner(focus: str, **kwargs):
        seen_user_id["uid"] = current_user_id()

    task = {
        "task_id": "test-1",
        "focus": "remind mikkel",
        "scheduled_for_user_id": MIKKEL_ID,
    }
    fire_scheduled_task(task, runner=fake_runner)
    assert seen_user_id["uid"] == MIKKEL_ID


def test_dispatch_without_user_id_falls_back_loudly(mu_env, caplog):
    """A task with no scheduled_for_user_id must log a warning and
    skip rather than firing in random context."""
    import logging
    caplog.set_level(logging.WARNING)
    from core.services.scheduled_task_runner import fire_scheduled_task

    fired = []
    def fake_runner(focus: str, **kwargs):
        fired.append(focus)

    task = {
        "task_id": "test-2",
        "focus": "untagged task",
        "scheduled_for_user_id": None,
    }
    fire_scheduled_task(task, runner=fake_runner)
    assert fired == [], "untagged task should not fire"
    assert any("scheduled_for_user_id" in r.message for r in caplog.records)


def test_dispatch_missing_user_logs_and_drops(mu_env, caplog):
    """If scheduled_for_user_id no longer exists in users.json, log and drop."""
    import logging
    caplog.set_level(logging.WARNING)
    from core.services.scheduled_task_runner import fire_scheduled_task

    fired = []
    def fake_runner(focus: str, **kwargs):
        fired.append(focus)

    task = {
        "task_id": "test-3",
        "focus": "ghost user task",
        "scheduled_for_user_id": "9999999999999999999",  # not in users.json
    }
    fire_scheduled_task(task, runner=fake_runner)
    assert fired == []
    assert any("not found in users.json" in r.message or "unknown user" in r.message.lower() for r in caplog.records)
