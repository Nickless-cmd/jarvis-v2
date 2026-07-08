"""Mission Control routes: agenter, watcher/agent-lineage, council/swarm-config og -runtime

Ruter flyttet uændret fra mission_control.py (god-fil-snit). Egen prefix-fri
APIRouter; samles i mission_control.py via include_router(prefix=/mc)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException  # noqa: F401 (HTTPException brugt i route-kroppe)

from .mission_control_common import *  # noqa: F401,F403 (delt flade + hjælpere)

router = APIRouter()

@router.get("/agents")
def mc_agents(limit: int = 100) -> dict:
    """Return live and persistent agent runtime state for Mission Control."""
    return build_agent_runtime_surface(limit=limit)


@router.get("/agents/{agent_id}")
def mc_agent_detail(agent_id: str) -> dict:
    """Return full detail-surface for one agent; 404 hvis agenten ikke findes."""
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return payload


@router.get("/agents/{agent_id}/messages")
def mc_agent_messages(agent_id: str) -> dict:
    """Return agentens beskeder og deres antal; 404 hvis agenten ikke findes."""
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return {
        "agent_id": agent_id,
        "messages": payload.get("messages") or [],
        "count": payload.get("message_count") or 0,
    }


@router.get("/agents/{agent_id}/runs")
def mc_agent_runs(agent_id: str) -> dict:
    """Return agentens runs; 404 hvis agenten ikke findes."""
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return {
        "agent_id": agent_id,
        "runs": payload.get("runs") or [],
    }


@router.get("/agents/{agent_id}/tool-calls")
def mc_agent_tool_calls(agent_id: str) -> dict:
    """Return agentens tool-calls og deres antal; 404 hvis agenten ikke findes."""
    payload = build_agent_detail_surface(agent_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="agent-not-found")
    return {
        "agent_id": agent_id,
        "tool_calls": payload.get("tool_calls") or [],
        "count": payload.get("tool_call_count") or 0,
    }


@router.get("/watcher-lineage")
def mc_watcher_lineage() -> dict:
    """Return persistent watcher history — agents with kind=persistent-watcher."""
    from core.services.agent_runtime import build_agent_runtime_surface, list_agent_runs
    surface = build_agent_runtime_surface(limit=200)
    all_agents = surface.get("agents") or []
    watchers = [a for a in all_agents if str(a.get("kind") or "") == "persistent-watcher"]
    result = []
    for w in watchers[:20]:
        agent_id = str(w.get("agent_id") or "")
        runs = list_agent_runs(agent_id=agent_id, limit=5)
        ctx = w.get("context") or {}
        result.append({
            "agent_id": agent_id,
            "name": str(w.get("name") or w.get("goal") or agent_id)[:80],
            "goal": str(w.get("goal") or "")[:200],
            "status": str(w.get("status") or ""),
            "spawn_depth": int((ctx or {}).get("spawn_depth") or 0),
            "next_wake_at": str(w.get("next_wake_at") or ""),
            "completed_at": str(w.get("completed_at") or ""),
            "tokens_burned": int(w.get("tokens_burned") or 0),
            "recent_runs": [
                {
                    "run_id": str(r.get("run_id") or ""),
                    "status": str(r.get("status") or ""),
                    "output_summary": str(r.get("output_summary") or "")[:300],
                    "finished_at": str(r.get("finished_at") or ""),
                }
                for r in runs
            ],
        })
    return {"watchers": result, "watcher_count": len(result)}


@router.get("/agent-lineage")
def mc_agent_lineage() -> dict:
    """Return full agent spawn lineage — parent→child chains with outcomes."""
    import json as _json
    from core.services.agent_runtime import build_agent_runtime_surface
    from core.services.agent_outcomes_log import get_recent_agent_outcomes

    surface = build_agent_runtime_surface(limit=200)
    all_agents = surface.get("agents") or []
    outcomes = get_recent_agent_outcomes(limit=50)
    outcome_by_id = {str(o.get("agent_id") or ""): o for o in outcomes}

    def _build_node(agent: dict) -> dict:
        agent_id = str(agent.get("agent_id") or "")
        ctx: dict = {}
        try:
            ctx = _json.loads(str(agent.get("context_json") or "{}"))
        except Exception:
            pass
        outcome = outcome_by_id.get(agent_id)
        children = [
            _build_node(a) for a in all_agents
            if str((lambda c: c.get("parent_agent_id") or "")(
                _json.loads(str(a.get("context_json") or "{}"))
            )) == agent_id
        ]
        return {
            "agent_id": agent_id,
            "name": str(agent.get("name") or agent.get("goal") or agent_id)[:80],
            "goal": str(agent.get("goal") or "")[:200],
            "status": str(agent.get("status") or ""),
            "kind": str(agent.get("kind") or "solo-task"),
            "spawn_depth": int(ctx.get("spawn_depth") or 0),
            "parent_agent_id": str(ctx.get("parent_agent_id") or "jarvis"),
            "tokens_burned": int(agent.get("tokens_burned") or 0),
            "created_at": str(agent.get("created_at") or ""),
            "completed_at": str(agent.get("completed_at") or ""),
            "outcome_summary": str(outcome.get("outcome") or "")[:200] if outcome else None,
            "children": children,
        }

    # Build forest: root nodes are those with parent = "jarvis" or no parent
    roots = [
        a for a in all_agents
        if str((_json.loads(str(a.get("context_json") or "{}")) or {}).get("parent_agent_id") or "jarvis") == "jarvis"
    ]
    tree = [_build_node(a) for a in roots[:30]]
    total_agents = len(all_agents)
    max_depth = max(
        (int((_json.loads(str(a.get("context_json") or "{}")) or {}).get("spawn_depth") or 0)
         for a in all_agents), default=0
    )
    return {
        "tree": tree,
        "total_agents": total_agents,
        "root_count": len(tree),
        "max_spawn_depth": max_depth,
    }


@router.get("/council-model-config")
def mc_get_council_model_config() -> dict:
    """Return persisted per-role model overrides."""
    import json
    from core.runtime.config import CONFIG_DIR
    path = CONFIG_DIR / "council_models.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"role_models": []}


@router.post("/council-model-config")
def mc_set_council_model_config(payload: dict) -> dict:
    """Persist per-role model overrides. payload: {role_models: [{role, provider, model}]}"""
    import json
    from core.runtime.config import CONFIG_DIR
    role_models = [
        {
            "role": str(item.get("role") or ""),
            "provider": str(item.get("provider") or ""),
            "model": str(item.get("model") or ""),
        }
        for item in (payload.get("role_models") or [])
        if item.get("role")
    ]
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = CONFIG_DIR / "council_models.json"
    path.write_text(json.dumps({"role_models": role_models}, indent=2))
    return {"role_models": role_models, "saved": True}


@router.get("/council-activation-config")
def mc_get_council_activation_config() -> dict:
    """Return council activation sensitivity config."""
    import json
    from core.runtime.config import CONFIG_DIR as _cfg_dir
    path = _cfg_dir / "council_activation.json"
    defaults: dict = {"sensitivity": "balanced", "auto_convene": True}
    if path.exists():
        try:
            saved = json.loads(path.read_text())
            return {**defaults, **saved}
        except Exception:
            pass
    return defaults


@router.post("/council-activation-config")
def mc_set_council_activation_config(payload: dict) -> dict:
    """Persist council activation sensitivity config."""
    import json
    from core.runtime.config import CONFIG_DIR as _cfg_dir
    allowed_sensitivities = {"conservative", "balanced", "minimal"}
    sensitivity = str(payload.get("sensitivity") or "balanced")
    if sensitivity not in allowed_sensitivities:
        sensitivity = "balanced"
    auto_convene = bool(payload.get("auto_convene", True))
    config = {"sensitivity": sensitivity, "auto_convene": auto_convene}
    _cfg_dir.mkdir(parents=True, exist_ok=True)
    (_cfg_dir / "council_activation.json").write_text(json.dumps(config, indent=2))
    return {**config, "saved": True}


@router.get("/council")
def mc_council(limit: int = 40) -> dict:
    """Return roster and council sessions for Mission Control."""
    return build_council_surface(limit=limit)


@router.get("/council/{council_id}")
def mc_council_detail(council_id: str) -> dict:
    """Return full detail-surface for én council-session; 404 hvis den ikke findes."""
    payload = build_council_detail_surface(council_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="council-not-found")
    return payload


@router.get("/council/{council_id}/messages")
def mc_council_messages(council_id: str) -> dict:
    """Return beskederne i én council-session; 404 hvis den ikke findes."""
    payload = build_council_detail_surface(council_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="council-not-found")
    return {
        "council_id": council_id,
        "messages": payload.get("messages") or [],
    }


@router.post("/runtime/agents/spawn")
def mc_spawn_agent(payload: dict) -> dict:
    """Spawn en ny agent-task ud fra payload (role, goal, tools, budget, provider/model osv.)."""
    return spawn_agent_task(
        role=str(payload.get("role") or "researcher"),
        goal=str(payload.get("goal") or ""),
        system_prompt=str(payload.get("system_prompt") or ""),
        tool_policy=str(payload.get("tool_policy") or ""),
        allowed_tools=list(payload.get("allowed_tools") or []),
        parent_agent_id=str(payload.get("parent_agent_id") or "jarvis"),
        persistent=bool(payload.get("persistent", False)),
        ttl_seconds=int(payload.get("ttl_seconds") or 0),
        budget_tokens=int(payload.get("budget_tokens") or 0),
        context=dict(payload.get("context") or {}),
        result_contract=dict(payload.get("result_contract") or {}),
        execution_mode=str(payload.get("execution_mode") or "solo-task"),
        auto_execute=bool(payload.get("auto_execute", True)),
        provider=str(payload.get("provider") or ""),
        model=str(payload.get("model") or ""),
    )


@router.post("/runtime/agents/{agent_id}/execute")
def mc_execute_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Kør agentens task nu (valgfrit thread_id og execution_mode fra payload)."""
    payload = payload or {}
    return execute_agent_task(
        agent_id=agent_id,
        thread_id=str(payload.get("thread_id") or ""),
        execution_mode=str(payload.get("execution_mode") or "solo-task"),
    )


@router.post("/runtime/agents/{agent_id}/message")
def mc_message_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Send en besked til agenten (content/role/kind); auto-eksekverer som standard."""
    payload = payload or {}
    return send_message_to_agent(
        agent_id=agent_id,
        content=str(payload.get("content") or ""),
        role=str(payload.get("role") or "user"),
        kind=str(payload.get("kind") or "jarvis-message"),
        execution_mode=str(payload.get("execution_mode") or "solo-task"),
        auto_execute=bool(payload.get("auto_execute", True)),
    )


@router.post("/runtime/agents/{agent_id}/peer-message")
def mc_peer_message_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Send en peer-besked fra denne agent til en anden agent (to_agent_id fra payload)."""
    payload = payload or {}
    return send_peer_message(
        from_agent_id=agent_id,
        to_agent_id=str(payload.get("to_agent_id") or ""),
        content=str(payload.get("content") or ""),
        kind=str(payload.get("kind") or "peer-message"),
    )


@router.post("/runtime/agents/{agent_id}/schedule")
def mc_schedule_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Planlæg agentens task (schedule_kind, delay_seconds, schedule_expr, activate)."""
    payload = payload or {}
    return schedule_agent_task(
        agent_id=agent_id,
        schedule_kind=str(payload.get("schedule_kind") or "interval-seconds"),
        delay_seconds=int(payload.get("delay_seconds") or 900),
        schedule_expr=str(payload.get("schedule_expr") or ""),
        activate=bool(payload.get("activate", True)),
    )


@router.post("/runtime/agents/run-due")
def mc_run_due_agents(payload: dict | None = None) -> dict:
    """Kør de agent-schedules der er forfaldne nu (op til limit, default 10)."""
    payload = payload or {}
    return run_due_agent_schedules(limit=int(payload.get("limit") or 10))


@router.post("/runtime/agents/{agent_id}/cancel")
def mc_cancel_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Annullér agenten (valgfri note fra payload)."""
    payload = payload or {}
    return cancel_agent(agent_id, note=str(payload.get("note") or ""))


@router.post("/runtime/agents/{agent_id}/suspend")
def mc_suspend_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Suspendér agenten (valgfri note fra payload)."""
    payload = payload or {}
    return suspend_agent(agent_id, note=str(payload.get("note") or ""))


@router.post("/runtime/agents/{agent_id}/resume")
def mc_resume_agent(agent_id: str) -> dict:
    """Genoptag en suspenderet agent."""
    return resume_agent(agent_id)


@router.post("/runtime/agents/{agent_id}/expire")
def mc_expire_agent(agent_id: str, payload: dict | None = None) -> dict:
    """Lad agenten udløbe (valgfri reason fra payload)."""
    payload = payload or {}
    return expire_agent(agent_id, reason=str(payload.get("reason") or ""))


@router.post("/runtime/agents/{agent_id}/promote")
def mc_promote_agent_result(agent_id: str, payload: dict | None = None) -> dict:
    """Promovér agentens resultat (valgfri note fra payload)."""
    payload = payload or {}
    return promote_agent_result(agent_id, note=str(payload.get("note") or ""))


@router.post("/runtime/council/spawn")
def mc_spawn_council(payload: dict) -> dict:
    """Opret en ny council-session runtime (topic, roles, owner_agent_id, member_models)."""
    return create_council_session_runtime(
        topic=str(payload.get("topic") or ""),
        roles=list(payload.get("roles") or []),
        owner_agent_id=str(payload.get("owner_agent_id") or "jarvis"),
        member_models=list(payload.get("member_models") or []),
    )


@router.post("/runtime/swarm/spawn")
def mc_spawn_swarm(payload: dict) -> dict:
    """Opret en ny swarm-session runtime (topic, roles, owner_agent_id, member_models)."""
    return create_swarm_session_runtime(
        topic=str(payload.get("topic") or ""),
        roles=list(payload.get("roles") or []),
        owner_agent_id=str(payload.get("owner_agent_id") or "jarvis"),
        member_models=list(payload.get("member_models") or []),
    )


@router.post("/runtime/council/{council_id}/message")
def mc_message_council(council_id: str, payload: dict | None = None) -> dict:
    """Post en besked til en council-session (content/kind/role fra payload)."""
    payload = payload or {}
    return post_council_message(
        council_id=council_id,
        content=str(payload.get("content") or ""),
        kind=str(payload.get("kind") or "jarvis-note"),
        role=str(payload.get("role") or "user"),
    )


@router.post("/runtime/council/{council_id}/run-round")
def mc_run_council_round(council_id: str) -> dict:
    """Kør én runde i den angivne council-session."""
    return run_council_round(council_id)


@router.post("/runtime/swarm/{council_id}/run-round")
def mc_run_swarm_round(council_id: str) -> dict:
    """Kør én runde i den angivne swarm-session."""
    return run_swarm_round(council_id)


