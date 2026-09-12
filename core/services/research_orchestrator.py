"""Adaptive research coordinator around the existing visible and agent runtimes."""

from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
from dataclasses import asdict
from typing import AsyncIterator, Callable

from core.services import research_ledger, research_store as store
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


_FACET_WORDS = (
    "price", "pris", "security", "sikkerhed", "operations", "drift",
    "performance", "ydelse", "features", "funktioner",
)


def _facets(message: str) -> list[str]:
    """De emneord planlægningen deler beskeden i — og som gaten måler dækning imod.

    Delt mellem `_plan` og `_evaluate_quality`, så de to altid måler det samme.
    """
    return [c for c in _FACET_WORDS if re.search(rf"\b{re.escape(c)}\b", message, re.I)]


def _delta_text(frame: str) -> str:
    """Træk syntese-teksten ud af en `delta`-frame. Andre frames giver ''."""
    if not frame.startswith("event: delta"):
        return ""
    for line in frame.splitlines():
        if line.startswith("data: "):
            try:
                payload = json.loads(line[6:])
            except Exception:
                return ""
            return str(payload.get("text") or "")
    return ""


def _plan(message: str, max_tasks: int) -> list[ResearchTask]:
    facets = _facets(message)
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


def _tool_calls_used(run_id: str) -> int:
    """Observerede værktøjskald i runnet. Defensiv: 0 hvis tællingen ikke kan læses."""
    try:
        return int(store.tool_call_count(run_id))
    except Exception:
        return 0


def _evaluate_quality(run_id: str, query: str, report: str, policy: ResearchPolicy) -> dict:
    """Fase A1: kobl kvalitetsgaten på den faktiske rapport.

    **Markerer — blokerer aldrig** (spec §4 A1): en gate må ikke fjerne et svar
    brugeren venter på. Fejler gaten selv, rapporteres `not_evaluated` frem for
    at lade runnet dø.
    """
    blank = {"status": "not_evaluated", "gates": {}, "failures": [], "tool_calls": None}
    try:
        from core.services.research_contract import normalize_source
        from core.services.research_quality import evaluate_research_report
        sources = [normalize_source(row) for row in store.list_sources(run_id)]
        used = _tool_calls_used(run_id)
        result = evaluate_research_report(
            report,
            sources,
            _facets(query),
            tool_calls=used,
            max_tool_calls=policy.max_tool_calls,
        )
    except Exception:
        return blank
    return {
        "status": "passed" if result.passed else "failed",
        "gates": dict(result.gates),
        "failures": list(result.failures),
        "tool_calls": used,
    }


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
    # Fase A2: hård vagt. Et run må ikke kunne hænge på en worker der aldrig svarer —
    # wall_time_seconds stod før kun i prompt-teksten.
    deadline = time.monotonic() + policy.wall_time_seconds
    timed_out = False
    yield _event("research_started", {"research_run_id": run_id, "tier": decision.tier})
    # Fase A4: gør runnet synligt i sessionens egen historik. Defensiv — en
    # manglende metadatalinje må aldrig vælte et run.
    research_ledger.record_run_started(
        session_id, run_id=run_id, tier=decision.tier, query=query,
    )
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
                # Fase A3: loftet over værktøjskald. Tjekkes når semaphore'en er vundet,
                # så et run der har brændt sit budget ikke starter flere workers.
                if _tool_calls_used(run_id) >= policy.max_tool_calls:
                    store.complete_task(
                        str(task["id"]), {"error": "tool budget exhausted"}, status="failed",
                    )
                    return f"Track {task['ordinal']} skipped: tool budget exhausted"
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
        pending = {asyncio.create_task(one(task)) for task in tasks}
        completed = 0
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            done, pending = await asyncio.wait(
                pending, timeout=remaining, return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                timed_out = True
                break
            for future in done:
                completed += 1
                try:
                    findings.append(future.result())
                except Exception as exc:
                    findings.append(f"Track failed: {exc}")
                yield _event("research_progress", {
                    "research_run_id": run_id,
                    "phase": "researching",
                    "completed_tasks": completed,
                    "total_tasks": len(tasks),
                    "sources": store.source_count(run_id),
                })
        if timed_out:
            for future in pending:
                future.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
            # Spec §4 A2: markér — men syntetisér på det der nåede ind, så brugeren
            # ikke står uden svar fordi én worker hang.
            yield _event("research_warning", {
                "research_run_id": run_id,
                "warning": "wall_time_exceeded",
                "wall_time_seconds": policy.wall_time_seconds,
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
    report_chunks: list[str] = []
    try:
        with research_context(policy, skill_instructions=contract.instructions, evidence=evidence), collecting_for(run_id):
            legacy = visible_factory(message=message, session_id=session_id, **visible_kwargs)
            async for frame in legacy:
                if frame.startswith("event: delta"):
                    report_chunks.append(_delta_text(frame))
                if frame.startswith("event: done"):
                    saw_done = True
                    store.transition_run(run_id, "verifying")
                    # Fase A1: gaten kører nu på den faktiske rapport + de indsamlede
                    # kilder. Den MARKERER — den blokerer ikke (spec §4 A1).
                    quality = _evaluate_quality(run_id, query, "".join(report_chunks), policy)
                    store.transition_run(run_id, "synthesizing")
                    store.transition_run(run_id, "completed")
                    research_ledger.record_run_completed(
                        session_id,
                        run_id=run_id,
                        sources=store.source_count(run_id),
                        quality=quality["status"],
                        timed_out=timed_out,
                        tool_calls=quality["tool_calls"],
                    )
                    yield _event("research_completed", {
                        "research_run_id": run_id,
                        "sources": store.source_count(run_id),
                        "quality": quality["status"],
                        "quality_gates": quality["gates"],
                        "quality_failures": quality["failures"],
                        "tool_calls": quality["tool_calls"],
                        "timed_out": timed_out,
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
