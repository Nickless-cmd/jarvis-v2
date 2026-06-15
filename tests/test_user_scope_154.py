"""SECURITY #154: streng per-bruger-isolation på de 4 private tabeller.

Beviser at bruger A ikke kan læse bruger B's rækker (nordstjerne: hverken owner
NOR et medlem kan læse en andens private data)."""
from __future__ import annotations

from core.identity.workspace_context import user_context


def test_sensory_isolation(isolated_runtime):
    from core.runtime.db_sensory import insert_sensory_memory, list_sensory_memories, count_sensory_memories
    with user_context(discord_id="userA"):
        insert_sensory_memory(modality="visual", content="A-hemmelighed")
    with user_context(discord_id="userB"):
        insert_sensory_memory(modality="visual", content="B-hemmelighed")
        b = list_sensory_memories()
        assert [m["content"] for m in b] == ["B-hemmelighed"]
        assert count_sensory_memories() == 1
    with user_context(discord_id="userA"):
        a = list_sensory_memories()
        assert [m["content"] for m in a] == ["A-hemmelighed"]


def test_recurring_isolation(isolated_runtime):
    from core.services.recurring_tasks import create_recurring_task, list_recurring_tasks, cancel_recurring_task
    with user_context(discord_id="userA"):
        ta = create_recurring_task(focus="A-task", interval_minutes=60)
    with user_context(discord_id="userB"):
        create_recurring_task(focus="B-task", interval_minutes=60)
        assert [t["focus"] for t in list_recurring_tasks()] == ["B-task"]
        # B kan IKKE annullere A's task (ser den ikke).
        assert cancel_recurring_task(ta["task_id"]) is False
    with user_context(discord_id="userA"):
        assert [t["focus"] for t in list_recurring_tasks()] == ["A-task"]


def test_private_brain_isolation(isolated_runtime):
    from core.runtime.db import insert_private_brain_record, list_private_brain_records
    common = dict(record_type="private-carry", layer="private_brain", session_id="",
                 run_id="", focus="", summary="", detail="", source_signals="",
                 confidence="medium", created_at="2026-06-15T00:00:00Z")
    with user_context(discord_id="userA"):
        insert_private_brain_record(record_id="ra", **common)
    with user_context(discord_id="userB"):
        insert_private_brain_record(record_id="rb", **common)
        assert {r["record_id"] for r in list_private_brain_records()} == {"rb"}
    with user_context(discord_id="userA"):
        assert {r["record_id"] for r in list_private_brain_records()} == {"ra"}


def test_autonomy_isolation(isolated_runtime):
    from core.runtime.db import create_autonomy_proposal, list_autonomy_proposals
    with user_context(discord_id="userA"):
        create_autonomy_proposal(proposal_id="pa", kind="memory", title="A-forslag")
    with user_context(discord_id="userB"):
        create_autonomy_proposal(proposal_id="pb", kind="memory", title="B-forslag")
        assert {p["proposal_id"] for p in list_autonomy_proposals()} == {"pb"}
    with user_context(discord_id="userA"):
        assert {p["proposal_id"] for p in list_autonomy_proposals()} == {"pa"}
