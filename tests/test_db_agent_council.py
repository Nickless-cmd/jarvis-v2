"""F5: raadets sammenhaeng i DB. Rigtig sqlite."""
from __future__ import annotations

import pytest

O, S = "u1", "s1"


@pytest.fixture
def cdb(isolated_runtime):
    import core.runtime.db_agent_council as C

    class H:
        C_ = C

        def make(self, owner=O, key="", topic="t"):
            return C.create(owner_user_id=owner, origin_session_id=S, parent_run_id="pr", parent_agent_id="jarvis",
                            topic=topic, facts="f", synthesis_role="synthesizer", budget_tokens=0,
                            idempotency_key=key)
    return H()


def test_a_council_starts_gathering_with_no_members_and_is_owner_scoped(cdb):
    c = cdb.make()
    assert (c["status"], c["members"], c["synthesis_assignment_id"], c["topic"]) == ("gathering", [], "", "t")
    assert cdb.C_.get(c["council_id"], O)["council_id"] == c["council_id"]
    assert cdb.C_.get(c["council_id"], "u2") is None
    with pytest.raises(cdb.C_.ContractError):
        cdb.C_.require(c["council_id"], "u2")


def test_members_roundtrip_and_the_idempotency_key_is_unique_per_owner_and_session(cdb):
    c = cdb.make(key="k1")
    cdb.C_.set_members(c["council_id"], [{"index": 1, "role": "critic", "task": "x", "assignment_id": "a", "agent_id": "g"}])
    assert cdb.C_.get(c["council_id"], O)["members"][0]["role"] == "critic"
    assert cdb.C_.find_by_key(O, S, "k1")["council_id"] == c["council_id"]
    assert cdb.C_.find_by_key("u2", S, "k1") is None and cdb.C_.find_by_key(O, S, "") is None
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        cdb.make(key="k1")
    assert cdb.make(owner="u2", key="k1")["owner_user_id"] == "u2"


def test_transitions_are_compare_and_swap_and_only_open_councils_are_listed(cdb):
    c = cdb.make()
    cid = c["council_id"]
    assert cdb.C_.transition(cid, frm="synthesizing", to="done") is False          # forkert udgangspunkt
    assert cdb.C_.transition(cid, frm="gathering", to="synthesizing", synthesis_assignment_id="asg-9") is True
    assert cdb.C_.transition(cid, frm="gathering", to="synthesizing", synthesis_assignment_id="asg-X") is False
    assert cdb.C_.get(cid, O)["synthesis_assignment_id"] == "asg-9"
    assert [x["council_id"] for x in cdb.C_.open_councils()] == [cid]
    assert cdb.C_.transition(cid, frm="synthesizing", to="done") is True
    assert cdb.C_.open_councils() == [] and cdb.C_.get(cid, O)["synthesis_assignment_id"] == "asg-9"
