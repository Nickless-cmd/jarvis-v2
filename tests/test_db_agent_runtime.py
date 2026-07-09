"""Smoke tests for db_agent_runtime.py — exercise the read/write paths against an isolated DB."""
from __future__ import annotations


def test_db_agent_runtime_read_paths_are_callable(isolated_runtime):
    import core.runtime.db_agent_runtime as m

    # Every LIST function returns an empty list on a fresh DB (schema is created
    # lazily by the first call, so this also proves the CREATE TABLE runs).
    assert m.list_agent_registry_entries() == []
    assert m.list_agent_runs() == []
    assert m.list_agent_messages() == []
    assert m.list_agent_tool_calls() == []
    assert m.list_agent_schedules() == []
    assert m.list_council_sessions() == []
    assert m.list_council_members(council_id="nope") == []

    # Every GET function returns None for an unknown id.
    assert m.get_agent_registry_entry("nope") is None
    assert m.get_agent_run("nope") is None
    assert m.get_agent_message("nope") is None
    assert m.get_agent_tool_call("nope") is None
    assert m.get_agent_schedule("nope") is None
    assert m.get_council_session("nope") is None
    assert m.get_council_member(council_id="nope", agent_id="nope") is None


def test_db_agent_runtime_registry_round_trip(isolated_runtime):
    import core.runtime.db_agent_runtime as m

    created = m.create_agent_registry_entry(
        agent_id="agent-1",
        role="researcher",
        goal="find the truth",
    )
    assert created["agent_id"] == "agent-1"
    assert created["role"] == "researcher"

    # The row is now readable via get and appears in the list.
    fetched = m.get_agent_registry_entry("agent-1")
    assert fetched is not None
    assert fetched["goal"] == "find the truth"

    ids = [row["agent_id"] for row in m.list_agent_registry_entries()]
    assert "agent-1" in ids

    # update patches a column and returns the updated row.
    updated = m.update_agent_registry_entry("agent-1", status="running")
    assert updated is not None
    assert updated["status"] == "running"


def test_db_agent_runtime_council_round_trip(isolated_runtime):
    import core.runtime.db_agent_runtime as m

    session = m.create_council_session(council_id="c-1", topic="what to build")
    assert session["council_id"] == "c-1"
    assert session["members"] == []

    member = m.add_council_member(council_id="c-1", agent_id="agent-1", role="voter")
    assert member["agent_id"] == "agent-1"

    # The session read-back now carries the member.
    got = m.get_council_session("c-1")
    assert got is not None
    assert [mem["agent_id"] for mem in got["members"]] == ["agent-1"]

    members = m.list_council_members(council_id="c-1")
    assert len(members) == 1
    assert members[0]["role"] == "voter"
