"""thought_thread og open_loop_thread (core/tools/thread_lifecycle_tools.py).

Testene kalder ``execute_tool`` — den indgang Jarvis' modelkald går igennem — og
læser tilstanden direkte fra JSON-filen / SQLite-tabellen bagefter, ikke gennem
service-laget. Fjernes kaldet til service-funktionen i værktøjet, står tilstanden
uændret og testen fejler (mutationskørsel: se docs/notes/2026-11-07-dormant-triage.md).
"""
from __future__ import annotations

import json
import sqlite3

import pytest

import core.services.cross_session_threads as xthreads
from core.services.run_autonomy_context import set_run_identity
from core.tools.simple_tools import _TOOL_HANDLERS, execute_tool
from core.tools.simple_tools_definitions import TOOL_DEFINITIONS

def _file(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def threads_file(tmp_path, monkeypatch):
    path = tmp_path / "thought_threads.json"
    monkeypatch.setattr(xthreads, "_storage_path", lambda: path)
    return path


@pytest.fixture
def run_identity():
    """Kørslens identitet er en ContextVar; sæt og nulstil den pr. test."""
    def _set(run_id):
        set_run_identity(run_id, "")
    yield _set
    set_run_identity("", "")


_NEW_TOOLS = ('thought_thread', 'open_loop_thread')


def test_new_tools_are_registered_in_both_tables():
    defined = {d["function"]["name"] for d in TOOL_DEFINITIONS}
    for name in _NEW_TOOLS:
        assert name in defined, f"{name} has no schema in TOOL_DEFINITIONS"
        assert name in _TOOL_HANDLERS, f"{name} has no handler in the dispatch table"


# ── cross_session_threads.pause/resume/close ───────────────────────────────

def test_thread_pause_resume_close_each_land_in_the_file(threads_file):
    tid = xthreads.create_thread(topic="Havet", synopsis="s", status="active")["thread_id"]

    paused = execute_tool("thought_thread", {"action": "pause", "thread_id": tid, "note": "træt"})
    assert paused["status"] == "ok"
    row = _file(threads_file)[0]
    assert (row["status"], row["pause_note"]) == ("paused", "træt")
    assert "paused_at" in row

    resumed = execute_tool("thought_thread", {
        "action": "resume", "thread_id": tid, "new_synopsis": "ny vinkel",
    })
    assert resumed["status"] == "ok"
    row = _file(threads_file)[0]
    assert (row["status"], row["synopsis"], row["pickup_count"]) == ("active", "ny vinkel", 2)
    assert "paused_at" not in row

    closed = execute_tool("thought_thread", {"action": "close", "thread_id": tid, "reason": "færdig"})
    assert closed["status"] == "ok"
    row = _file(threads_file)[0]
    assert (row["status"], row["close_reason"]) == ("closed", "færdig")
    assert closed["thread"]["status"] == "closed"


@pytest.mark.parametrize(
    ("setup_status", "action", "fragment"),
    [
        ("paused", "pause", "is paused"),
        ("closed", "resume", "is closed"),
        ("closed", "close", "is closed"),
        ("closed", "pause", "is closed"),
    ],
)
def test_thread_action_in_the_wrong_state_is_an_error_that_names_the_state(
    threads_file, setup_status, action, fragment
):
    tid = xthreads.create_thread(topic="T", status="active")["thread_id"]
    if setup_status == "paused":
        xthreads.pause_thread(tid)
    else:
        xthreads.close_thread(tid)
    snapshot = threads_file.read_text(encoding="utf-8")

    result = execute_tool("thought_thread", {"action": action, "thread_id": tid})

    assert result["status"] == "error"
    assert fragment in result["error"]
    assert threads_file.read_text(encoding="utf-8") == snapshot


@pytest.mark.parametrize(
    ("args", "fragment"),
    [
        ({"action": "pause"}, "thread_id is required"),
        ({"action": "pause", "thread_id": "thr-ukendt"}, "not found"),
        ({"action": "reopen", "thread_id": "x"}, "action must be one of"),
    ],
)
def test_thread_errors_are_honest(threads_file, args, fragment):
    result = execute_tool("thought_thread", args)
    assert result["status"] == "error"
    assert fragment in result["error"]


def test_thread_list_returns_threads_with_ids(threads_file):
    tid = xthreads.create_thread(topic="T", status="active")["thread_id"]
    result = execute_tool("thought_thread", {"action": "list", "status": "active"})
    assert result["status"] == "ok"
    assert [t["thread_id"] for t in result["threads"]] == [tid]


# ── open_loop_signal_tracking.declare/touch/close ──────────────────────────

def _threads(db):
    with db.connect() as conn:
        try:
            rows = conn.execute(
                "SELECT thread_id, name, status, declared_by, opened_in_run_id, "
                "closure_evidence, closed_in_run_id FROM runtime_thread_registry ORDER BY rowid"
            ).fetchall()
        except sqlite3.OperationalError:  # tabellen oprettes først ved første skrivning: ingen tabel = ingen tråde
            return []
    return [dict(r) for r in rows]


def _loops(db, thread_id):
    with db.connect() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT status, run_id, source_run_id, thread_id FROM runtime_open_loop_signals "
            "WHERE thread_id = ? ORDER BY id", (thread_id,),
        ).fetchall()]


def test_open_loop_declare_touch_close_land_in_the_tables(isolated_runtime, run_identity):
    db = isolated_runtime.db
    run_identity("run-A")
    declared = execute_tool("open_loop_thread", {
        "action": "declare", "name": "Hvorfor driver loops?", "summary": "Åbent",
    })
    assert declared["status"] == "ok"
    tid = declared["thread"]["thread_id"]
    assert _threads(db) == [{
        "thread_id": tid, "name": "Hvorfor driver loops?", "status": "open",
        "declared_by": "jarvis", "opened_in_run_id": "run-A",
        "closure_evidence": "", "closed_in_run_id": "",
    }]
    assert [(r["status"], r["run_id"]) for r in _loops(db, tid)] == [("open", "run-A")]

    run_identity("run-B")
    touched = execute_tool("open_loop_thread", {"action": "touch", "thread_id": tid})
    assert touched["status"] == "ok"
    rows = _loops(db, tid)
    assert [r["run_id"] for r in rows if r["status"] == "open"] == ["run-B"]
    assert {r["source_run_id"] for r in rows if r["status"] == "open"} == {"run-A"}

    closed = execute_tool("open_loop_thread", {
        "action": "close", "thread_id": tid, "evidence": "Svaret stod i run-B",
    })
    assert closed["status"] == "ok"
    thread = _threads(db)[0]
    assert thread["status"] == "closed"
    assert thread["closure_evidence"] == "Svaret stod i run-B"
    assert thread["closed_in_run_id"] == "run-B"
    assert all(r["status"] == "closed" for r in _loops(db, tid))


@pytest.mark.parametrize(
    ("args", "fragment"),
    [
        ({"action": "declare", "name": ""}, "name set on purpose"),
        ({"action": "touch", "thread_id": "thread-ukendt"}, "unknown thread_id"),
        ({"action": "close", "thread_id": "thread-ukendt", "evidence": "x"}, "unknown thread_id"),
        ({"action": "close", "thread_id": "thread-ukendt"}, "evidence"),
        ({"action": "reopen"}, "action must be one of"),
    ],
)
def test_open_loop_service_refusals_are_returned_as_errors(
    isolated_runtime, run_identity, args, fragment
):
    run_identity("run-A")
    result = execute_tool("open_loop_thread", args)
    assert result["status"] == "error"
    assert fragment in result["error"]
    assert _threads(isolated_runtime.db) == []


def test_open_loop_cannot_be_closed_by_the_run_that_opened_it(isolated_runtime, run_identity):
    db = isolated_runtime.db
    run_identity("run-A")
    tid = execute_tool("open_loop_thread", {"action": "declare", "name": "Selvlukning"})["thread"]["thread_id"]

    result = execute_tool("open_loop_thread", {"action": "close", "thread_id": tid, "evidence": "mig selv"})

    assert result["status"] == "error"
    assert "cannot be the run that answers" in result["error"]
    assert _threads(db)[0]["status"] == "open"


@pytest.mark.parametrize("action", ["declare", "touch", "close"])
def test_open_loop_without_a_run_identity_is_refused_not_defaulted(
    isolated_runtime, run_identity, action
):
    run_identity("")
    result = execute_tool("open_loop_thread", {
        "action": action, "name": "N", "thread_id": "thread-x", "evidence": "e",
    })
    assert result["status"] == "error"
    assert "identity of the current run" in result["error"]
    assert _threads(isolated_runtime.db) == []


def test_open_loop_list_shows_declared_threads(isolated_runtime, run_identity):
    run_identity("run-A")
    tid = execute_tool("open_loop_thread", {"action": "declare", "name": "Liste"})["thread"]["thread_id"]
    result = execute_tool("open_loop_thread", {"action": "list", "status": "open"})
    assert result["status"] == "ok"
    assert [t["thread_id"] for t in result["threads"]] == [tid]
