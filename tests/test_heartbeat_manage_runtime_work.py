"""`manage_runtime_work` uden noget arbejde maa ikke kaste.

15/9-2026: med hverken koeede eller koerende flows ramte grenen
`running_flows[0]` og kastede IndexError i stedet for at falde videre til en
anden handling. Latent i drift (der laa altid koeede flows), men handlingen er
et hjerteslag, og et hjerteslag der kaster naar huset er tomt er forkert vej rundt.
"""
from __future__ import annotations

from pathlib import Path

import core.services.heartbeat_runtime as hr
import core.services.runtime_browser_body as rbb
import core.services.runtime_flows as rf
import core.services.runtime_hooks as rh
import core.services.runtime_tasks as rt
import core.services.self_experiments as se
from core.services.heartbeat_manage_runtime_work import execute_manage_runtime_work


def test_intet_arbejde_falder_videre_uden_at_kaste(monkeypatch):
    monkeypatch.setattr(rh, "dispatch_unhandled_hook_events", lambda limit=4: [])
    monkeypatch.setattr(rt, "list_tasks", lambda status="", limit=4: [])
    monkeypatch.setattr(rf, "list_flows", lambda status="", limit=4: [])
    set_body: dict = {}
    monkeypatch.setattr(rbb, "ensure_browser_body",
                        lambda **kw: set_body.update(kw) or {"body_id": "b"})
    monkeypatch.setattr(se, "observe_recent_visible_runs_for_self_experiments",
                        lambda limit=6: {"observed": 0})
    monkeypatch.setattr(se, "materialize_learning_curriculum_tasks",
                        lambda **kw: {"created": 0, "task_ids": []})
    monkeypatch.setattr(hr, "_heartbeat_runtime_bias_from_recent_work", lambda kind: False)
    videre: dict = {}
    monkeypatch.setattr(hr, "_execute_heartbeat_internal_action",
                        lambda **kw: videre.update(kw) or {"status": "executed"})

    ud = execute_manage_runtime_work(tick_id="t", workspace_dir=Path("/tmp"))

    assert ud == {"status": "executed"}
    assert set_body["active_flow_id"] == ""
    assert videre["action_type"] == "refresh_memory_context"


def test_hjerteslaget_delegerer_hertil(monkeypatch):
    import core.services.heartbeat_manage_runtime_work as m
    monkeypatch.setattr(m, "execute_manage_runtime_work",
                        lambda **kw: {"status": "fra-modulet", **kw})
    ud = hr._execute_heartbeat_internal_action(
        action_type="manage_runtime_work", tick_id="t", workspace_dir=Path("/tmp"))
    assert ud["status"] == "fra-modulet"
