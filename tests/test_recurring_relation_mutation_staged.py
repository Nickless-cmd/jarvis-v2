from __future__ import annotations

import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from types import ModuleType


def _sqlite_connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def test_recurring_tasks_create_fire_cancel_and_state(tmp_path, monkeypatch):
    from core.runtime import db as runtime_db
    from core.services import recurring_tasks as recurring

    db_path = tmp_path / "jarvis.db"
    monkeypatch.setattr(runtime_db, "connect", lambda: _sqlite_connect(db_path))

    emitted: list[tuple[str, object]] = []
    visible_runs = ModuleType("core.services.visible_runs")
    visible_runs.start_autonomous_run = (
        lambda *, message, session_id=None: emitted.append((message, session_id))
    )
    monkeypatch.setitem(sys.modules, "core.services.visible_runs", visible_runs)

    task = recurring.create_recurring_task(
        focus="Send daily recap",
        interval_minutes=15,
        delay_minutes=0,
    )

    with runtime_db.connect() as conn:
        conn.execute(
            "UPDATE recurring_tasks SET next_fire_at = ? WHERE task_id = ?",
            ((datetime.now(UTC) - timedelta(minutes=1)).isoformat(), task["task_id"]),
        )
        conn.commit()

    state_before = recurring.get_recurring_tasks_state()
    recurring._fire_due()
    listed = recurring.list_recurring_tasks()
    cancelled = recurring.cancel_recurring_task(task["task_id"])

    assert task["status"] == "active"
    assert state_before["total"] == 1
    assert emitted == [("Send daily recap", None)]
    assert listed[0]["fire_count"] == 1
    assert cancelled is True
    assert recurring.get_recurring_tasks_state()["cancelled_count"] == 1


def test_relation_dynamics_reports_trend_and_prompt(monkeypatch):
    from core.services import relation_dynamics as dynamics

    now = datetime.now(UTC)
    runs = [
        {"started_at": (now - timedelta(days=1)).isoformat(), "text_preview": "hej relation one"},
        {"started_at": (now - timedelta(days=2)).isoformat(), "text_preview": "hej relation two"},
        {"started_at": (now - timedelta(days=3)).isoformat(), "text_preview": "hej relation three"},
        {"started_at": (now - timedelta(days=10)).isoformat(), "text_preview": "older relation"},
    ]
    monkeypatch.setattr(dynamics, "_recent_runs", lambda days=14, limit=500: [
        {**row, "_parsed_at": datetime.fromisoformat(row["started_at"])} for row in runs
    ])
    monkeypatch.setattr(dynamics, "_warmth_from_sources", lambda: 0.42)
    dynamics._cached = {}
    dynamics._last_computed_ts = 0.0

    state = dynamics.get_relation_dynamics()
    surface = dynamics.build_relation_dynamics_surface()
    prompt = dynamics.build_relation_dynamics_prompt_section()

    assert state["runs_considered"] == 4
    assert surface["active"] is True
    assert surface["engagement_trend"] == "rising"
    assert surface["warmth"] == 0.42
    assert prompt is not None
    assert "stigende engagement" in prompt


def test_self_mutation_lineage_records_and_surfaces(tmp_path, monkeypatch):
    from core.runtime import db as runtime_db
    from core.services import self_mutation_lineage as lineage

    db_path = tmp_path / "jarvis.db"
    monkeypatch.setattr(runtime_db, "connect", lambda: _sqlite_connect(db_path))
    monkeypatch.setattr(lineage, "connect", lambda: _sqlite_connect(db_path))
    lineage._table_initialized = False

    lineage.record_self_mutation(
        target_path="/media/projects/jarvis-v2/core/services/self_mutation_lineage.py",
        change_type="edit-staged",
        session_id="sess-1",
    )

    surface = lineage.build_self_mutation_lineage_surface(limit=5)
    lines = lineage.build_self_mutation_prompt_lines(limit=5)

    assert surface["mutation_count"] == 1
    assert surface["recent_mutations"][0]["category"] == "core-runtime"
    assert surface["recent_mutations"][0]["path"].endswith("core/services/self_mutation_lineage.py")
    assert lines and "edit-staged" in lines[0]


def test_staged_edits_stage_list_commit_and_discard(tmp_path, monkeypatch):
    from core.services import staged_edits as staged

    staged._STAGED_DIR = tmp_path / "staged_edits"
    staged._LOCK = staged.threading.Lock()

    target = tmp_path / "note.txt"
    target.write_text("hello world\n", encoding="utf-8")

    recorded: list[tuple[str, str]] = []
    lineage = ModuleType("core.services.self_mutation_lineage")
    lineage.record_self_mutation = lambda *, target_path, change_type, session_id=None: recorded.append((target_path, change_type))
    monkeypatch.setitem(sys.modules, "core.services.self_mutation_lineage", lineage)

    edit = staged.stage_edit(
        session_id="sess-1",
        path=str(target),
        old_text="world",
        new_text="jarvis",
        note="rename greeting",
    )
    new_path = tmp_path / "created.txt"
    write = staged.stage_write(
        session_id="sess-1",
        path=str(new_path),
        content="fresh content\n",
        note="create file",
    )
    staged_view = staged.list_staged("sess-1", full_diffs=True)
    committed = staged.commit_staged("sess-1")

    second = staged.stage_write(
        session_id="sess-1",
        path=str(tmp_path / "discarded.txt"),
        content="drop me",
    )
    discarded = staged.discard_staged("sess-1")

    assert edit["status"] == "staged"
    assert write["status"] == "staged"
    assert staged_view["count"] == 2
    assert committed["status"] == "ok"
    assert target.read_text(encoding="utf-8") == "hello jarvis\n"
    assert new_path.read_text(encoding="utf-8") == "fresh content\n"
    assert recorded and recorded[0][1] == "edit-staged"
    assert second["status"] == "staged"
    assert discarded["discarded_count"] == 1
