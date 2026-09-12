import sqlite3

import pytest

from core.services import research_store as store
from core.services.research_contract import normalize_source


@pytest.fixture()
def isolated_store(tmp_path, monkeypatch):
    path = tmp_path / "research.db"

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(store, "connect", connect)
    return store


def test_run_transitions_are_ordered_and_terminal(isolated_store):
    run = isolated_store.create_run(session_id="s1", original_query="q", tier="inline")
    assert isolated_store.transition_run(run["id"], "planning")["status"] == "planning"
    with pytest.raises(isolated_store.ResearchStateError):
        isolated_store.transition_run(run["id"], "completed")

    for status in ("researching", "verifying", "synthesizing", "completed"):
        run = isolated_store.transition_run(run["id"], status)
    with pytest.raises(isolated_store.ResearchStateError):
        isolated_store.transition_run(run["id"], "researching")


def test_sources_deduplicate_and_active_snapshot_disappears_on_completion(isolated_store):
    run = isolated_store.create_run(session_id="s1", original_query="q", tier="inline")
    source = normalize_source({"url": "https://example.com/a#x", "title": "A"})
    first = isolated_store.add_source(run["id"], source)
    second = isolated_store.add_source(run["id"], source)
    assert first["id"] == second["id"]
    assert isolated_store.active_for_session("s1")["id"] == run["id"]

    for status in ("planning", "researching", "verifying", "synthesizing", "completed"):
        isolated_store.transition_run(run["id"], status)
    assert isolated_store.active_for_session("s1") is None


def test_stale_runs_become_interrupted(isolated_store):
    run = isolated_store.create_run(session_id="s1", original_query="q", tier="orchestrated")
    changed = isolated_store.mark_stale_interrupted(older_than_seconds=0)
    assert changed == 1
    assert isolated_store.get_run(run["id"])["status"] == "interrupted"
