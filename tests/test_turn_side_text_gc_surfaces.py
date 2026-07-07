from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


def test_turn_changelog_reconstructs_ground_truth(monkeypatch):
    from core.services import turn_changelog as changelog

    events = [
        {
            "kind": "tool.completed",
            "created_at": "2026-05-12T10:05:00+00:00",
            "payload": {"run_id": "run-1", "tool": "edit_file", "status": "ok"},
        },
        {
            "kind": "tool.completed",
            "created_at": "2026-05-12T10:06:00+00:00",
            "payload": {"run_id": "run-1", "tool": "edit_file", "status": "ok"},
        },
    ]
    monkeypatch.setattr(
        "core.eventbus.bus.event_bus",
        SimpleNamespace(recent=lambda limit=200: events),
    )

    class FakeRun:
        stdout = " M tests/test_x.py\nA  core/services/y.py\n"

    monkeypatch.setattr(changelog.subprocess, "run", lambda *args, **kwargs: FakeRun())

    data = changelog.build_turn_changelog(
        run_id="run-1",
        started_at="2026-05-12T10:00:00+00:00",
        repo_root=Path("/tmp"),
    )
    section = changelog.format_changelog(data)

    assert data["tool_call_total"] == 2
    assert "tests/test_x.py" in data["files_changed"]
    assert section is not None
    assert "Denne tur" in section


def test_side_tasks_flag_list_and_resolve(monkeypatch):
    from core.services import side_tasks as tasks

    state: list[dict[str, object]] = []

    def load_json(_key, default):
        return list(state) if state else list(default)

    def save_json(_key, items):
        state[:] = list(items)

    monkeypatch.setattr(tasks, "load_json", load_json)
    monkeypatch.setattr(tasks, "save_json", save_json)

    created = tasks.flag(title="Fix docs", prompt="Update docs", tldr="Docs are stale", session_id="sess-1")
    prompt = tasks.side_tasks_prompt_section()
    resolved = tasks.resolve(created["side_task_id"], decision="dismissed")

    assert created["status"] == "ok"
    assert prompt is not None
    assert "side-tasks" in prompt  # header: "Flaggede side-tasks (deferred):"
    assert resolved["new_status"] == "dismissed"


def test_text_resonance_tracks_warm_and_cold_text():
    from core.services import text_resonance as resonance

    resonance.reset_text_resonance()
    warm = resonance.resonate("tak, det er dejligt og varmt ❤", source="chat")
    cold = resonance.resonate("det er forkert, fejl og kritisk", source="chat")
    surface = resonance.build_text_resonance_surface()
    prompt = resonance.build_text_resonance_prompt_section()

    assert warm["emotional_tone"] == "warm"
    assert cold["emotional_tone"] == "cold"
    assert surface["active"] is True
    assert surface["total_signals"] == 2
    assert prompt is None


def test_nudge_broend_persists_pending_nudges(tmp_path, monkeypatch):
    from core.services import nudge_broend as broend

    monkeypatch.setattr(broend, "_STORAGE_PATH", tmp_path / "nudge_broend.json")

    nudge_id = broend.push(source="daemon", kind="info", message="look later", importance="normal")
    pending = broend.list_pending()
    marked = broend.mark_sent(nudge_id)

    assert nudge_id.startswith("nudge-")
    assert pending and pending[0]["nudge_id"] == nudge_id
    assert marked is True


def test_signal_surface_gc_force_archives_old_items():
    from datetime import UTC, datetime, timedelta

    from core.services import signal_surface_gc as gc

    archived: list[tuple[str, dict[str, object]]] = []

    def update_fn(item_id, **kwargs):
        archived.append((item_id, kwargs))

    # _force_archive uses a cutoff of now - _FORCE_ARCHIVE_AFTER_DAYS (14d), so
    # timestamps must be relative to now — hardcoded calendar dates eventually
    # fall on the same side of the cutoff and both get archived.
    now = datetime.now(UTC)
    old_dt = (now - timedelta(days=gc._FORCE_ARCHIVE_AFTER_DAYS + 5)).isoformat()
    new_dt = (now - timedelta(days=1)).isoformat()
    items = [
        {"snapshot_id": "old-1", "status": "active", "created_at": old_dt},
        {"snapshot_id": "new-1", "status": "active", "created_at": new_dt},
    ]

    count = gc._force_archive(items=items, id_field="snapshot_id", update_fn=update_fn, label="private_state")

    assert count == 1
    assert archived and archived[0][0] == "old-1"
    assert archived[0][1]["status"] == "archived"
