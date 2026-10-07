"""D: rute-lageret - ét raekke pr. forsoeg, lukket kilde-saet, laesbart efter genstart."""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture
def rdb(isolated_runtime):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_route as R
    from core.runtime.db_agent_runtime import create_agent_registry_entry

    def task(name, owner="u1"):
        create_agent_registry_entry(agent_id=name, role="researcher", goal="g")
        c.bind_agent_owner(agent_id=name, owner_user_id=owner, owner_session_id="s1")
        return c.accept_assignment(agent_id=name, owner_user_id=owner, origin_session_id="s1", goal="g",
                                   parent_agent_id="jarvis", parent_run_id="pr")

    class H:
        R_, task_ = R, staticmethod(task)

        def rec(self, acc, name, attempt, source="agent_pool", model="m", **extra):
            return R.record_decision(
                assignment_id=acc["assignment_id"], agent_id=name, owner_user_id="u1", attempt=attempt,
                decision={"route_source": source, "provider": "p", "model": model, "candidates": [], **extra})
    return H()


def test_every_attempt_is_a_row_and_latest_is_the_highest_attempt_of_the_newest_assignment(rdb):
    a = rdb.task_("a1")
    rdb.rec(a, "a1", 1, model="m1")
    rdb.rec(a, "a1", 2, source="cheap_lane_fallback", model="m2", failover_reason="nede")
    rows = rdb.R_.attempts_for_assignment(a["assignment_id"])
    assert [(r["attempt"], r["route_source"], r["model"]) for r in rows] == [
        (1, "agent_pool", "m1"), (2, "cheap_lane_fallback", "m2")]
    assert rows[1]["decision"]["failover_reason"] == "nede" and rows[1]["owner_user_id"] == "u1"
    last = rdb.R_.latest_for_agent("a1")
    assert (last["attempt"], last["model"], last["decision"]["model"]) == (2, "m2", "m2")


def test_an_attempt_number_is_recorded_once_per_assignment(rdb):
    a = rdb.task_("a1")
    rdb.rec(a, "a1", 1)
    with pytest.raises(sqlite3.IntegrityError):
        rdb.rec(a, "a1", 1, model="andet")
    assert len(rdb.R_.attempts_for_assignment(a["assignment_id"])) == 1


@pytest.mark.parametrize("source", ["", "deepseek", "stjaalet", "AGENT_POOL"])
def test_only_the_four_documented_route_sources_are_stored(rdb, source):
    a = rdb.task_("a1")
    with pytest.raises(ValueError):
        rdb.rec(a, "a1", 1, source=source)
    assert rdb.R_.attempts_for_assignment(a["assignment_id"]) == []
    assert set(rdb.R_.SOURCES) == {"explicit", "agent_pool", "owner_deepseek_fallback", "cheap_lane_fallback"}


def test_a_legacy_agent_has_no_route_and_agents_do_not_see_each_others(rdb):
    a, b = rdb.task_("a1"), rdb.task_("a2")
    rdb.rec(a, "a1", 1, model="kun-a1")
    assert rdb.R_.latest_for_agent("ingen") is None
    assert rdb.R_.latest_for_agent("a2") is None
    assert rdb.R_.latest_for_agent("a1")["model"] == "kun-a1"
    assert rdb.R_.attempts_for_assignment(b["assignment_id"]) == []


def test_an_unreadable_decision_json_degrades_to_an_empty_decision(rdb):
    a = rdb.task_("a1")
    row = rdb.rec(a, "a1", 1)
    import core.runtime.db_agent_contract as c
    conn = c._conn()
    conn.execute("UPDATE agent_route_decisions SET decision_json='{ikke json' WHERE decision_id=?",
                 (row["decision_id"],))
    conn.commit()
    assert rdb.R_.attempts_for_assignment(a["assignment_id"])[0]["decision"] == {}
