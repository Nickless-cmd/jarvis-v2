from __future__ import annotations

import queue
import sqlite3


def test_experience_correction_listener_handles_correction_event(monkeypatch):
    from core.services import experience_correction_listener as listener

    seen: list[str] = []
    monkeypatch.setattr(listener, "_mark_recent_episode_corrected", lambda session_id: seen.append(session_id))
    listener._listener_running = True

    q = queue.SimpleQueue()
    q.put({
        "kind": "channel.chat_message_appended",
        "payload": {
            "session_id": "sess-9",
            "message": {"role": "user", "content": "nej, det er forkert"},
        },
    })
    q.put(None)

    listener._listener_loop(q)

    assert seen == ["sess-9"]
    assert listener._looks_like_correction("nej, det er forkert") is True
    assert listener._extract_user_message(
        {"session_id": "sess-9", "message": {"role": "user", "content": "hej"}}
    ) == ("sess-9", "hej")


def test_subagent_digest_surfaces_completed_agents(monkeypatch):
    from core.services import subagent_digest as digest

    monkeypatch.setattr(digest, "_load_marks", lambda: {})
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(digest, "_mark_seen", lambda session_id, when_iso: seen.append((session_id, when_iso)))
    monkeypatch.setattr(
        "core.runtime.db.list_agent_registry_entries",
        lambda limit=80: [
            {
                "agent_id": "agent-1",
                "role": "researcher",
                "status": "completed",
                "completed_at": "2026-05-12T10:00:00+00:00",
                "goal": "map the repo",
            },
            {
                "agent_id": "agent-2",
                "role": "watcher",
                "status": "active",
                "completed_at": "",
                "goal": "watch logs",
            },
        ],
    )

    section = digest.subagent_digest_section("sess-4")

    assert section is not None
    assert "Subagenter der har afsluttet" in section
    assert seen == [("sess-4", "2026-05-12T10:00:00+00:00")]


def test_visible_self_state_summary_reads_real_counts(monkeypatch):
    from core.services import visible_self_state_summary as summary

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE behavioral_decisions (directive TEXT, adherence_score REAL, last_reviewed_at TEXT, status TEXT)"
    )
    conn.execute(
        "CREATE TABLE long_horizon_goals (title TEXT, progress_pct INTEGER, updated_at TEXT, status TEXT)"
    )
    conn.execute(
        "CREATE TABLE tick_quality_summary_signals (id INTEGER PRIMARY KEY, score INTEGER, summary TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO behavioral_decisions VALUES ('test', 0.6, NULL, 'active')"
    )
    conn.execute(
        "INSERT INTO long_horizon_goals VALUES ('goal', 40, '2026-05-11T00:00:00+00:00', 'active')"
    )
    conn.execute(
        "INSERT INTO tick_quality_summary_signals VALUES (1, 72, 'steady', '2026-05-12T09:00:00+00:00')"
    )
    conn.commit()

    monkeypatch.setattr(summary, "connect", lambda: conn)

    block = summary.build_self_state_block()

    assert "behavioral_decisions: 1 active" in block
    assert "long_horizon_goals: 1 active" in block
    assert "latest_tick_quality: 72/100" in block


def test_memory_resurfacing_picks_stale_heading(tmp_path, monkeypatch):
    from core.services import memory_resurfacing as resurfacing

    memory_file = tmp_path / "MEMORY.md"
    memory_file.write_text(
        "# Title\n\n## Old Thing\nRemember this.\n\n## New Thing\nFresh content.\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(resurfacing, "_memory_md", lambda: memory_file)
    monkeypatch.setattr(resurfacing, "_recently_touched_headings", lambda: set())
    monkeypatch.setattr(resurfacing, "_recently_resurfaced_headings", lambda: set())
    logged: list[str] = []
    monkeypatch.setattr(resurfacing, "_log_resurfacing", lambda heading, trigger="heartbeat": logged.append(heading))

    candidate = resurfacing.pick_resurfacing_candidate(seed=1)
    prompt = resurfacing.format_for_prompt(candidate)

    assert candidate is not None
    assert candidate["heading"] in {"Old Thing", "New Thing"}
    assert logged == [candidate["heading"]]
    assert prompt.startswith('You haven\'t thought about')


def test_memory_graph_records_edges_and_ingests_text(monkeypatch):
    from core.services import memory_graph as graph

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    monkeypatch.setattr(graph, "connect", lambda: conn)
    monkeypatch.setattr(graph, "extract_from_text", lambda text, max_chars=2000: [("Bjørn", "likes", "forest green")])

    added = graph.record_triple("Bjørn", "likes", "forest green", evidence="test")
    ingested = graph.ingest_text("anything long enough to trigger extraction")

    rows = conn.execute("SELECT relation, evidence FROM memory_edges").fetchall()

    assert added is True
    assert ingested == 1
    assert rows and rows[0]["relation"] == "likes"
