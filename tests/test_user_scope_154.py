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


def test_recurring_fires_in_owner_context(isolated_runtime):
    """En gentagen opgave affyres i EJERENS indbakke, ikke i ejerens-ejer.

    ÉN VÆKKER (11/11-2026): `_legacy` kalder `anmod_om_vaekning`, ikke
    `start_autonomous_run`. Testen måler derfor hvor POSTEN lander: den skal
    ligge i ejerens indbakke (under den identitet indbakken normaliserer til),
    med `beskrivelse == focus`, og kvitteringen må ikke være `rejected`.
    """
    import core.services.recurring_tasks as rt
    from core.identity.user_db import add_user
    from core.runtime import db_inbox
    from core.services import wake_gateway
    from core.services.inbox_state import normaliser_indbakke_bruger

    # db_inbox husker i en modul-flag at skemaet er lavet; en tidligere test med
    # anden DB-sti ellers gør dette til en ordens-afhængig `no such table`.
    db_inbox._skema_klar = False
    u = add_user(email="rec@b.dk", name="R", password="hemmelig123",
                 role="member", workspace="recws")
    uid = u["user_id"]
    rt._ensure_table()
    with user_context(discord_id=uid):
        rt._create(task_id="t1", focus="g\u00f8r det", source="x", interval_minutes=60,
                   next_fire_at="2000-01-01T00:00:00", now="2026-01-01T00:00:00")
    kvitteringer = []
    ægte = wake_gateway.anmod_om_vaekning

    def spion(**kw):
        k = ægte(**kw)
        kvitteringer.append((kw, k))
        return k

    import pytest
    mp = pytest.MonkeyPatch()
    mp.setattr(wake_gateway, "anmod_om_vaekning", spion)
    try:
        rt._fire_due()
    finally:
        mp.undo()

    assert len(kvitteringer) == 1
    kw, kv = kvitteringer[0]
    assert kw["bruger_id"] == uid            # ejeren bæres med fra opgaven
    assert kv["status"] != "rejected", kv
    indbakke = normaliser_indbakke_bruger(uid)
    post = db_inbox.hent(bruger_id=indbakke, kilde_id=kv["kilde_id"])
    assert post is not None, "posten ligger ikke i ejerens indbakke"
    assert post["beskrivelse"] == "g\u00f8r det"
