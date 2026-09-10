"""Agent-fladerne — Fase 6.

Jarvis fandt at «latest_message» tog `messages[-1]` fra et vindue der var
sorteret AELDST-foerst. Fladen kaldte altsaa den 40. aeldste besked
«seneste» saa snart traaden voksede forbi loftet — tavst forkert.
"""
from __future__ import annotations


def _tal(db, aid, tekst):
    from uuid import uuid4
    db.create_agent_message(
        message_id=f"m-{uuid4().hex}", thread_id=f"agent-thread-{aid}",
        agent_id=aid, direction="agent->runtime", role="assistant",
        kind="message", content=tekst,
    )


def test_latest_message_er_den_NYESTE_naar_loftet_bider(isolated_runtime):
    import core.runtime.db_agent_runtime as db
    from core.services.agent_runtime_surfaces import build_agent_detail_surface

    aid = "a-flade"
    db.create_agent_registry_entry(agent_id=aid, role="r", goal="g")
    for i in range(45):
        _tal(db, aid, f"besked-{i:02d}")

    flade = build_agent_detail_surface(aid) or {}
    seneste = str((flade.get("latest_message") or {}).get("content") or "")
    assert seneste == "besked-44", (
        f"fladen kaldte den 40. AELDSTE besked «seneste» ({seneste!r})")
