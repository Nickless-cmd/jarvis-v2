"""Adaptive research coordinator around the existing visible and agent runtimes."""

from __future__ import annotations

import asyncio
import inspect
import json
import re
from dataclasses import asdict
from typing import AsyncIterator, Callable

from core.services import research_store as store
from core.services.research_contract import (
    ResearchDecision,
    ResearchPolicy,
    ResearchTask,
    load_research_contract,
)
from core.services.research_evidence_collector import collecting_for
from core.services.research_prompt_context import research_context
from core.services.research_router import classify_research


def _event(kind: str, payload: dict) -> str:
    return f"event: {kind}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _setting(name: str, default: bool) -> bool:
    try:
        from core.runtime.settings import load_settings
        return bool(load_settings().extra.get(name, default))
    except Exception:
        return default


def _plan(message: str, max_tasks: int) -> list[ResearchTask]:
    facets = []
    for candidate in ("price", "pris", "security", "sikkerhed", "operations", "drift", "performance", "ydelse", "features", "funktioner"):
        if re.search(rf"\b{re.escape(candidate)}\b", message, re.I):
            facets.append(candidate)
    count = max(2, min(max_tasks or 2, max(2, len(facets))))
    if not facets:
        facets = ["authoritative facts", "independent verification"]
    return [
        ResearchTask(
            ordinal=index + 1,
            title=f"Research track {index + 1}: {facets[index % len(facets)]}",
            objective=f"Investigate {facets[index % len(facets)]} for: {message}",
        )
        for index in range(count)
    ]


def _default_worker_sync(*, task: dict, run_id: str, skill_instructions: str) -> dict:
    from core.runtime.db import list_agent_messages
    from core.services.agent_runtime_spawn import spawn_agent_task

    with collecting_for(run_id, task_id=str(task["id"])):
        surface = spawn_agent_task(
            role="researcher",
            goal=str(task["objective"]),
            system_prompt=(
                "You are a read-only research worker. Use web tools, preserve URLs, "
                "separate evidence from inference, and return concise findings to Jarvis.\n\n"
                + skill_instructions
            ),
            allowed_tools=["web_search", "web_fetch", "web_scrape"],
            tool_policy="read-only-runtime",
            parent_agent_id="jarvis",
            max_turns=8,
            context={"research_run_id": run_id, "research_task_id": task["id"]},
            result_contract={"findings": True, "sources": True, "confidence": True, "gaps": True},
            execution_mode="research-worker",
            auto_execute=True,
        )
    agent_id = str(surface.get("agent_id") or "")
    messages = list_agent_messages(agent_id=agent_id, limit=20, tail=True) if agent_id else []
    result_text = next((
        str(message.get("content") or "") for message in reversed(messages)
        if message.get("kind") == "result"
    ), "")
    return {"status": str(surface.get("status") or "completed"), "text": result_text, "agent_id": agent_id}


async def _run_worker(worker_factory, *, task: dict, run_id: str, skill_instructions: str):
    value = worker_factory(task=task, run_id=run_id, skill_instructions=skill_instructions)
    return await value if inspect.isawaitable(value) else value


async def stream_research_run(
    *,
    message: str,
    original_query: str | None = None,
    session_id: str,
    visible_run_id: str = "",
    decision: ResearchDecision | None = None,
    visible_factory: Callable[..., AsyncIterator[str]] | None = None,
    worker_factory=None,
    orchestrator_enabled: bool | None = None,
    **visible_kwargs,
) -> AsyncIterator[str]:
    query = str(original_query if original_query is not None else message)
    contract = load_research_contract(query)
    decision = decision or classify_research(query, policy=contract.policy)
    if orchestrator_enabled is None:
        orchestrator_enabled = _setting("research_orchestrator_enabled", False)
    if decision.tier == "orchestrated" and not orchestrator_enabled:
        decision = ResearchDecision(
            tier="inline",
            signals=decision.signals + ("orchestrator_rollout_disabled",),
            max_workers=1,
            max_tasks=1,
            max_tool_calls=min(10, decision.max_tool_calls),
            wall_time_seconds=min(240, decision.wall_time_seconds),
            source_target=min(6, decision.source_target),
        )
    policy = ResearchPolicy(
        max_workers=max(1, min(3, decision.max_workers or 1)),
        max_tasks=max(1, min(6, decision.max_tasks or 1)),
        max_tool_calls=max(1, decision.max_tool_calls or 8),
        wall_time_seconds=max(30, decision.wall_time_seconds or 180),
        source_target=max(2, decision.source_target or 3),
    )
    run = store.create_run(
        session_id=session_id,
        original_query=query,
        tier=decision.tier,
        decision=asdict(decision),
    )
    run_id = str(run["id"])
    if visible_run_id:
        store.bind_visible_run(run_id, visible_run_id)
    yield _event("research_started", {"research_run_id": run_id, "tier": decision.tier})
    if contract.warnings:
        yield _event("research_warning", {"research_run_id": run_id, "warnings": list(contract.warnings)})
    store.transition_run(run_id, "planning")

    evidence = ""
    if decision.tier == "orchestrated":
        tasks = store.create_tasks(run_id, _plan(query, policy.max_tasks))
        yield _event("research_plan", {
            "research_run_id": run_id,
            "tasks": [{"ordinal": task["ordinal"], "title": task["title"]} for task in tasks],
        })
        store.transition_run(run_id, "researching")
        semaphore = asyncio.Semaphore(policy.max_workers)
        worker_factory = worker_factory or (
            lambda **kwargs: asyncio.to_thread(_default_worker_sync, **kwargs)
        )

        async def one(task):
            async with semaphore:
                store.start_task(str(task["id"]))
                try:
                    result = await _run_worker(
                        worker_factory, task=task, run_id=run_id,
                        skill_instructions=contract.instructions,
                    )
                    text = str((result or {}).get("text") or "").strip()
                    provider_status = str((result or {}).get("status") or "")
                    if not text or provider_status in {"error", "failed", "provider_error"}:
                        raise RuntimeError("research worker returned no usable evidence")
                    store.complete_task(str(task["id"]), result)
                    return text
                except Exception as exc:
                    store.complete_task(str(task["id"]), {"error": str(exc)}, status="failed")
                    return f"Track {task['ordinal']} failed: {exc}"

        findings = []
        futures = [asyncio.create_task(one(task)) for task in tasks]
        for completed, future in enumerate(asyncio.as_completed(futures), 1):
            findings.append(await future)
            yield _event("research_progress", {
                "research_run_id": run_id,
                "phase": "researching",
                "completed_tasks": completed,
                "total_tasks": len(tasks),
                "sources": store.source_count(run_id),
            })
        evidence = "\n\n".join(findings)
    else:
        store.transition_run(run_id, "researching")

    steers = store.consume_pending_steers(run_id)
    if steers:
        evidence = f"{evidence}\n\nUser steering received at phase boundary:\n" + "\n".join(steers)
        yield _event("research_progress", {
            "research_run_id": run_id, "phase": "synthesizing",
            "completed_tasks": len(steers), "total_tasks": len(steers),
            "sources": store.source_count(run_id), "steers_applied": len(steers),
        })

    if visible_factory is None:
        from core.services.visible_runs import start_visible_run
        visible_factory = start_visible_run

    saw_done = False
    try:
        with research_context(policy, skill_instructions=contract.instructions, evidence=evidence), collecting_for(run_id):
            legacy = visible_factory(message=message, session_id=session_id, **visible_kwargs)
            async for frame in legacy:
                if frame.startswith("event: done"):
                    saw_done = True
                    store.transition_run(run_id, "verifying")
                    store.transition_run(run_id, "synthesizing")
                    store.transition_run(run_id, "completed")
                    yield _event("research_completed", {
                        "research_run_id": run_id,
                        "sources": store.source_count(run_id),
                        "quality": "evidence_collected",
                    })
                yield frame
    except Exception as exc:
        try:
            store.transition_run(run_id, "failed", warning=str(exc))
        except Exception:
            pass
        yield _event("research_warning", {"research_run_id": run_id, "error": str(exc)})
        if not saw_done:
            yield _event("done", {})


def research_enabled() -> bool:
    return _setting("research_request_metadata_enabled", True) and _setting("research_inline_contract_enabled", True)
