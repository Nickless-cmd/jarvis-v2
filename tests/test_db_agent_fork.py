"""G2: db_agent_fork - varig kontekstbeslutning pr. assignment, ejer-afgraenset. Rigtig sqlite."""
from __future__ import annotations

import pytest


@pytest.fixture
def db(isolated_runtime):
    import core.runtime.db_agent_contract as c
    import core.runtime.db_agent_fork as F
    return c, F


def _plan(**over):
    p = {"context_mode": "fork", "plan_path": "paid_switch", "parent_run_id": "pr", "parent_provider": "ollama",
         "parent_model": "x", "parent_effort": "think", "route_provider": "copilot-premium",
         "route_model": "m1", "reasoning_effort": "default", "effort_source": "model_default",
         "history_tokens": 120, "extra_context_tokens": 120, "estimated_extra_cost_usd": None,
         "cost_basis": "premium_request_uden_dollarpris", "cache_reuse_possible": False,
         "switch_accepted": True, "use_snapshot": True, "excerpt": "",
         "snapshot": {"text": "[user] hej", "turns": 1, "truncated": False, "cutoff_at": "t", "sha256": "ab"}}
    p.update(over)
    return p


def test_a_recorded_plan_reads_back_complete_and_only_for_its_owner(db):
    c, F = db
    row = F.record_fork(assignment_id="asg-1", agent_id="a1", owner_user_id="o1", origin_session_id="s1",
                        plan=_plan())
    assert (row["requested_mode"], row["plan_path"], row["switch_accepted"], row["cache_reuse_possible"],
            row["history_tokens"], row["extra_context_tokens"], row["estimated_extra_cost_usd"],
            row["snapshot_text"], row["snapshot_turns"], row["snapshot_sha256"]) == (
        "fork", "paid_switch", 1, 0, 120, 120, None, "[user] hej", 1, "ab")
    assert F.get_fork(assignment_id="asg-1", owner_user_id="o2") is None
    assert F.get_fork(assignment_id="findes-ikke", owner_user_id="o1") is None


def test_a_snapshot_that_was_not_used_is_not_stored(db):
    c, F = db
    row = F.record_fork(assignment_id="asg-2", agent_id="a1", owner_user_id="o1", origin_session_id="s1",
                        plan=_plan(plan_path="excerpt", use_snapshot=False, excerpt="kun dette"))
    assert (row["snapshot_text"], row["snapshot_turns"], row["snapshot_sha256"], row["excerpt_text"]) == (
        "", 0, "", "kun dette")


@pytest.mark.parametrize("over", [{"context_mode": "klon"}, {"plan_path": "gratis_frokost"}])
def test_an_unknown_mode_or_path_is_refused_and_nothing_is_written(db, over):
    c, F = db
    with pytest.raises(ValueError):
        F.record_fork(assignment_id="asg-3", agent_id="a1", owner_user_id="o1", origin_session_id="s1",
                      plan=_plan(**over))
    assert c._conn().execute("SELECT COUNT(*) FROM agent_fork_contexts").fetchone()[0] == 0


def test_one_row_per_assignment(db):
    c, F = db
    F.record_fork(assignment_id="asg-4", agent_id="a1", owner_user_id="o1", origin_session_id="s1", plan=_plan())
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        F.record_fork(assignment_id="asg-4", agent_id="a1", owner_user_id="o1", origin_session_id="s1",
                      plan=_plan())
