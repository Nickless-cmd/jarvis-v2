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


def test_list_findings_laeser_parsede_fund_i_track_raekkefoelge(isolated_store):
    """Fase B2: findings gemmes struktureret i `finding_json` og læses tilbage.

    Uden denne læsning ville de par­sede fund kun leve i hukommelsen under runnet —
    og evidensblokken til syntesen kunne ikke bygges bagefter.
    """
    from core.services.research_contract import ResearchTask

    run = isolated_store.create_run(session_id="s1", original_query="q", tier="orchestrated")
    tasks = isolated_store.create_tasks(
        run["id"],
        [
            ResearchTask(ordinal=1, title="A", objective="om A"),
            ResearchTask(ordinal=2, title="B", objective="om B"),
        ],
    )
    isolated_store.start_task(tasks[0]["id"])
    isolated_store.complete_task(
        tasks[0]["id"],
        {"findings": [{"task_ordinal": 1, "claim": "A er dyr", "source_urls": ["https://a.dk"]}]},
    )
    # Rækkefølgen skal følge ordinal, ikke indsættelses-rækkefølgen.
    isolated_store.start_task(tasks[1]["id"])
    isolated_store.complete_task(
        tasks[1]["id"],
        {"findings": [{"task_ordinal": 2, "claim": "B er billig", "source_urls": []}]},
    )

    fund = isolated_store.list_findings(run["id"])
    assert [f["task_ordinal"] for f in fund] == [1, 2]
    assert fund[0]["claim"] == "A er dyr"


def test_list_findings_springer_ulæselig_json_over(isolated_store):
    """Et enkelt dårligt svar må ikke skjule resten af runnets fund."""
    from core.services.research_contract import ResearchTask

    run = isolated_store.create_run(session_id="s1", original_query="q", tier="orchestrated")
    tasks = isolated_store.create_tasks(
        run["id"],
        [
            ResearchTask(ordinal=1, title="A", objective="om A"),
            ResearchTask(ordinal=2, title="B", objective="om B"),
        ],
    )
    isolated_store.start_task(tasks[0]["id"])
    isolated_store.complete_task(tasks[0]["id"], {"findings": "ikke-en-liste"})
    isolated_store.start_task(tasks[1]["id"])
    isolated_store.complete_task(
        tasks[1]["id"], {"findings": [{"task_ordinal": 2, "claim": "B"}]}
    )

    fund = isolated_store.list_findings(run["id"])
    assert [f["claim"] for f in fund] == ["B"]


def test_list_findings_uden_fund_er_tom(isolated_store):
    run = isolated_store.create_run(session_id="s1", original_query="q", tier="orchestrated")
    assert isolated_store.list_findings(run["id"]) == []
