"""agent_wake_intentions: skriv og aflys den varige vaekke-intention."""
from __future__ import annotations

import pytest

from core.services import agent_wake_intentions as aw
from core.services import in_flight_runs as ifr


@pytest.fixture(autouse=True)
def _clean(isolated_runtime):
    ifr._mutate(lambda r: r.clear())
    yield
    ifr._mutate(lambda r: r.clear())


def test_wake_message_names_condition_and_is_system_marked():
    first = aw.wake_message(condition="first_terminal", assignment_ids=["a", "b"])
    allm = aw.wake_message(condition="all_terminal", assignment_ids=["a"])
    assert first.startswith("[SYSTEM — agentvækning, ikke en besked fra brugeren]\n")
    assert "mindst én af" in first and "a, b" in first
    assert "alle dem" in allm


def test_stage_wake_is_idempotent_on_task_id():
    first = aw.stage_wake(task_id="t1", session_id="s", owner_user_id="u", message="m")
    again = aw.stage_wake(task_id="t1", session_id="s", owner_user_id="u", message="m")
    assert first == {"task_id": "t1", "merged": False, "created": True}
    assert again == {"task_id": "t1", "merged": False, "created": False}
    assert len([r for r in ifr._load().values() if r.get("wake_kind")]) == 1


def test_stage_wake_in_another_session_is_not_merged():
    ifr.mark_started(run_id="r-old", session_id="s1", user_message="x")
    ifr.settle_recovering("r-old", reason="shutdown")
    out = aw.stage_wake(task_id="t2", session_id="s2", owner_user_id="u", message="m")
    assert out["created"] is True and out["merged"] is False


def test_cancel_pending_wake_only_touches_a_recovering_record():
    aw.stage_wake(task_id="t3", session_id="s", owner_user_id="u", message="m")
    assert aw.cancel_pending_wake("t3", reason="r") is True
    rec = ifr._load()["t3"]
    assert (rec["status"], rec["exit_reason"], rec["notice_pending"]) == ("cancelled", "r", False)
    assert aw.cancel_pending_wake("t3", reason="r") is False       # allerede afsluttet
    assert aw.cancel_pending_wake("findes-ikke", reason="r") is False


def test_a_claimed_running_wake_is_left_alone():
    aw.stage_wake(task_id="t4", session_id="s", owner_user_id="u", message="m")
    krav = ifr.claim_due_recovery(owner="api")
    assert krav["task_id"] == "t4" and krav["status"] == "running"
    assert aw.cancel_pending_wake("t4", reason="r") is False
    assert ifr._load()["t4"]["status"] == "running"
