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
    ResearchFinding,
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


# ── Fase C1 (13/9-2026): LLM-planlægger med regex-fallback ────────────────────
#
# `_plan` er stadig fallback. Planneren må fejle på alle måder — ingen provider,
# tomt svar, ulæselig JSON — uden at runnet dør. Er flaget slået fra, kaldes
# `_plan` direkte, og adfærden er byte-identisk med før C1.

_PLANNER_PROMPT = """You plan independent research tracks for one question.

Split the question into {count} tracks that can each be researched independently by one worker with web tools.

{topic_line}Reply with ONLY a JSON array (no prose, no code fence) in this shape:
[{{"title": "short track name", "objective": "one sentence: what this track must establish"}}]

The question: {message}"""


def _parse_plan(text: str, max_tasks: int) -> list[ResearchTask]:
    """Læs plannerens JSON til en ResearchTask-liste. Defensiv: [] ved mindste tvivl.

    Vi beder om en liste af {title, objective}, men modeller pakker den ind i
    kodeblokke eller et {"tasks": [...]}-objekt — begge accepteres. Er svaret
    ikke til at læse, eller giver det færre end to tracks, returnerer vi [] og
    kalderen falder tilbage til regex-planen.
    """
    candidate = _clean_text(text)
    fenced = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        parsed: object = json.loads(candidate)
    except Exception:
        bracket = re.search(r"\[.*\]", text, re.S)
        if not bracket:
            return []
        try:
            parsed = json.loads(bracket.group(0))
        except Exception:
            return []
    if isinstance(parsed, dict):
        for key in ("tasks", "tracks", "plan"):
            if isinstance(parsed.get(key), list):
                parsed = parsed[key]
                break
    if not isinstance(parsed, list):
        return []
    out: list[ResearchTask] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        title = _clean_text(item.get("title"))
        objective = _clean_text(item.get("objective") or item.get("goal") or title)
        if not title or not objective:
            continue
        out.append(ResearchTask(ordinal=len(out) + 1, title=title, objective=objective))
        if len(out) >= max(2, max_tasks):
            break
    return out if len(out) >= 2 else []


def _llm_plan(message: str, max_tasks: int, facets: list[str]) -> list[ResearchTask] | None:
    """Fase C1: bed en billig model om delopgaver. None = kunne ikke → regex.

    Blokerende (netværk) — kalderen kører den i en tråd. Alle fejl giver None,
    aldrig en exception: et run må ikke dø, fordi planneren ikke kunne svare.
    """
    from core.services.cheap_provider_runtime import execute_public_safe_cheap_lane

    count = max(2, max_tasks or 2)
    topic_line = ""
    if facets:
        # Facetterne er dem kvalitetsgaten måler dækning imod — planen skal dække
        # dem, ellers dømmer gaten planen ude for noget den ikke blev bedt om.
        topic_line = f"Together the tracks must cover: {', '.join(facets)}.\n\n"
    prompt = _PLANNER_PROMPT.format(count=count, topic_line=topic_line, message=message)
    try:
        result = execute_public_safe_cheap_lane(message=prompt)
    except Exception:
        return None
    text = str((result or {}).get("text") or "")
    if not text.strip():
        return None
    return _parse_plan(text, max_tasks) or None


async def _plan_tasks(message: str, max_tasks: int, *, planner_enabled: bool) -> list[ResearchTask]:
    """Fase C1: LLM-planlægger med regex-fallback.

    Slået fra eller fejlet → præcis `_plan()`. Netværkskaldet kører i en tråd,
    så et langsomt planner-svar ikke blokerer event-loopet.
    """
    if planner_enabled:
        try:
            planned = await asyncio.to_thread(_llm_plan, message, max_tasks, _facets(message))
        except Exception:
            planned = None
        if planned:
            return planned
    return _plan(message, max_tasks)


def _tool_calls_used(run_id: str) -> int:
    """Observerede værktøjskald i runnet. Defensiv: 0 hvis tællingen ikke kan læses."""
    try:
        return int(store.tool_call_count(run_id))
    except Exception:
        return 0


_URL_RE = re.compile(r"https?://[^\s\)\]\"'<>]+")


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _confidence(value: object) -> str:
    word = _clean_text(value).lower()
    return word if word in {"low", "medium", "high"} else "medium"


def _finding_from_text(text: str, task_ordinal: int) -> ResearchFinding:
    """Sidste udkast: hele teksten bliver ét fund med de URLs den bærer.

    Bruges når worker'en svarer i prosa i stedet for den aftalte struktur. Vi
    kaster ikke svaret væk — men vi lover heller ikke mere, end teksten bærer:
    uden URL'er er tilliden `low`.
    """
    claim = _clean_text(text)
    urls = tuple(dict.fromkeys(_URL_RE.findall(claim)))
    return ResearchFinding(
        task_ordinal=task_ordinal,
        claim=claim[:2000],
        source_urls=urls,
        confidence="medium" if urls else "low",
    )


def _parse_findings(text: str, task_ordinal: int) -> list[ResearchFinding]:
    """Fase B2: worker-svaret → `ResearchFinding`.

    Worker'ens `result_contract` beder om `findings`/`sources`/`confidence`/
    `gaps`. Den struktur blev før aldrig læst — svaret gik videre som rå tekst,
    så claim→kilde-koblingen fandtes ingen steder, og syntesen kunne ikke vide
    hvilke kilder der bar hvilke påstande.

    Defensiv hele vejen: alt der ikke kan parses, falder tilbage til ét fund på
    hele teksten. Et svar må aldrig tabe sin evidens på vej ind.
    """
    raw = str(text or "").strip()
    if not raw:
        return []
    candidate = raw
    fenced = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
    if fenced:
        candidate = fenced.group(1).strip()
    parsed: object = None
    try:
        parsed = json.loads(candidate)
    except Exception:
        parsed = None

    items: list = []
    if isinstance(parsed, list):
        items = parsed
    elif isinstance(parsed, dict):
        for key in ("findings", "results", "claims"):
            if isinstance(parsed.get(key), list):
                items = parsed[key]
                break
        else:
            if any(k in parsed for k in ("claim", "finding", "text", "summary")):
                items = [parsed]

    findings: list[ResearchFinding] = []
    for item in items:
        if isinstance(item, str):
            if item.strip():
                findings.append(_finding_from_text(item, task_ordinal))
            continue
        if not isinstance(item, dict):
            continue
        claim = _clean_text(
            item.get("claim") or item.get("finding") or item.get("summary") or item.get("text")
        )
        if not claim:
            continue
        raw_urls = (
            item.get("source_urls") or item.get("sources") or item.get("urls") or item.get("url") or ()
        )
        if isinstance(raw_urls, str):
            raw_urls = (raw_urls,)
        urls = tuple(
            dict.fromkeys(
                str(entry).strip() for entry in raw_urls
                if str(entry).strip().startswith("http")
            )
        )
        if not urls:
            urls = tuple(dict.fromkeys(_URL_RE.findall(claim)))
        findings.append(
            ResearchFinding(
                task_ordinal=task_ordinal,
                claim=claim[:2000],
                source_urls=urls,
                confidence=_confidence(item.get("confidence")),
                caveat=_clean_text(item.get("caveat") or item.get("gap") or item.get("gaps"))[:500],
            )
        )
    return findings or [_finding_from_text(raw, task_ordinal)]


def _gap_objective(query: str, findings: list[ResearchFinding]) -> str:
    """Fase B3: critic-opgaven — hvad MANGLER der, givet de fundne påstande.

    Critic'en skal ikke forske videre; den skal pege på hullerne. Derfor står
    påstandene i selve opgaven: worker-stien sender kun `objective` videre som
    goal, så konteksten skal ligge i teksten.
    """
    claims = "\n".join(f"- {finding.claim}" for finding in findings) or "(ingen påstande endnu)"
    return (
        "You are a gap-checker, not a researcher. Given the original task and the "
        "claims already gathered, list ONLY what is missing, unsupported, stale, or "
        "contradictory. Be specific and terse; do not repeat the claims. "
        'Reply with JSON: {"gaps": ["..."]}.\n\n'
        f"Original task: {query}\n\nClaims so far:\n{claims}"
    )


def _parse_gaps(text: str) -> list[str]:
    """Fase B3: critic-svaret → korte gap-linjer. Defensiv hele vejen.

    Kan svaret ikke læses som JSON, bruges linjerne som de står — et svar må
    ikke tabe sine huller på vej ind, og et tomt svar giver ingen huller.
    """
    raw = str(text or "").strip()
    if not raw:
        return []
    candidate = raw
    fenced = re.search(r"```(?:json)?\s*(.+?)```", raw, re.S)
    if fenced:
        candidate = fenced.group(1).strip()
    parsed: object = None
    try:
        parsed = json.loads(candidate)
    except Exception:
        parsed = None
    out: list[str] = []
    if isinstance(parsed, dict):
        for key in ("gaps", "missing", "unsupported", "issues"):
            value = parsed.get(key)
            if isinstance(value, list):
                out = [_clean_text(item) for item in value if _clean_text(item)]
                break
    elif isinstance(parsed, list):
        out = [_clean_text(item) for item in parsed if _clean_text(item)]
    if not out and parsed is None:
        # Kun når svaret SLET IKKE var JSON: brug linjerne som de står. Et gyldigt
        # svar uden huller skal give nul huller — ikke hele svaret som ét hul.
        out = [_clean_text(line) for line in raw.splitlines() if _clean_text(line)]
    return out[:20]


def _evidence_block(
    texts: list[str],
    sources: list[dict],
    findings: list[ResearchFinding],
    gaps: list[str] | None = None,
) -> str:
    """Evidens til syntesen — med en KANONISK nummereret kilde-liste.

    Uden nummereringen opdigter syntesen sin egen, og `citation_validity`-gaten
    måler citationer mod et kildesæt modellen aldrig fik at se. Med den peger
    `[3]` på præcis den kilde gaten kontrollerer imod.
    """
    parts: list[str] = []
    if sources:
        lines = []
        for index, source in enumerate(sources, 1):
            url = str(source.get("canonical_url") or source.get("url") or "")
            title = _clean_text(source.get("title"))
            lines.append(f"[{index}] {url}" + (f" — {title}" if title else ""))
        parts.append("Canonical sources (cite these numbers):\n" + "\n".join(lines))
    if findings:
        lines = []
        for finding in findings:
            marker = " ".join(finding.source_urls) if finding.source_urls else "(no source)"
            line = f"- (track {finding.task_ordinal}, {finding.confidence}) {finding.claim} — {marker}"
            if finding.caveat:
                line += f" [caveat: {finding.caveat}]"
            lines.append(line)
        parts.append("Findings:\n" + "\n".join(lines))
    if gaps:
        # Fase B3: hullerne skal med til syntesen — ellers ved den ikke hvad den
        # skal være forsigtig med. Den skal adressere dem eller flagge dem.
        parts.append("Known gaps (address or flag these):\n" + "\n".join(f"- {gap}" for gap in gaps))
    if texts:
        parts.append("Raw worker notes:\n" + "\n\n".join(texts))
    return "\n\n".join(parts)


def _topup_plan(run_id: str, tasks: list[dict], policy: ResearchPolicy) -> list[ResearchTask]:
    """Fase B1: hvilke tracks skal styrkes — og med hvad?

    Stop på EVIDENS frem for på «bølgen blev færdig»: er kilderne for få OG er
    der råd, kører én ekstra bølge på de TYNDESTE tracks. Returnerer [] når
    evidensen er nok, budgettet er brugt, eller der ikke er noget at styrke.

    Defensiv hele vejen: kan tællingen ikke læses, kører vi ingen ekstra bølge.
    En top-up der ikke kan begrundes, er en udgift uden dækning.
    """
    if not tasks:
        return []
    try:
        if store.source_count(run_id) >= policy.source_target:
            return []
    except Exception:
        return []
    if _tool_calls_used(run_id) >= policy.max_tool_calls:
        return []
    per_task: dict[str, int] = {}
    try:
        for row in store.list_sources(run_id):
            tid = str((row or {}).get("task_id") or "")
            per_task[tid] = per_task.get(tid, 0) + 1
    except Exception:
        per_task = {}
    ranked = sorted(
        tasks,
        key=lambda t: (per_task.get(str(t.get("id")), 0), int(t.get("ordinal") or 0)),
    )
    thin = ranked[: max(1, min(int(policy.max_workers or 1), len(ranked)))]
    base = max(int(t.get("ordinal") or 0) for t in tasks)
    return [
        ResearchTask(
            ordinal=base + index + 1,
            title=f"Top-up track {t.get('ordinal')}: {t.get('title') or ''}".strip(),
            objective=(
                "Find ADDITIONAL independent sources for: "
                f"{t.get('objective') or ''} Prefer sources that are not already "
                "cited, and preserve their URLs."
            ),
        )
        for index, t in enumerate(thin)
    ]


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


def _default_worker_sync(
    *,
    task: dict,
    run_id: str,
    skill_instructions: str,
    max_turns: int = 8,
    budget_tokens: int = 0,
) -> dict:
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
            # Fase C2: budgettet følger med herfra. Uden det er
            # `_check_budget_and_expire` inert for research-workers.
            max_turns=max_turns,
            budget_tokens=budget_tokens,
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


async def _run_worker(
    worker_factory,
    *,
    task: dict,
    run_id: str,
    skill_instructions: str,
    max_turns: int = 8,
    budget_tokens: int = 0,
):
    """Kør én worker gennem factory'en.

    Fase C2: `max_turns` og `budget_tokens` følger med hele vejen ned til
    `spawn_agent_task`. Uden dem er `_check_budget_and_expire` inert — den
    læser `budget_tokens` fra agent-registry'en og returnerer straks når den
    er 0 (målt 13/9-2026: 113 af 138 researcher-kørsler havde intet budget).
    """
    value = worker_factory(
        task=task,
        run_id=run_id,
        skill_instructions=skill_instructions,
        max_turns=max_turns,
        budget_tokens=budget_tokens,
    )
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
        # Fase C2: indsatsen pr. worker følger beslutningen. 0 budget = ubegrænset,
        # så en kalder der ikke sætter et loft får nøjagtig den gamle adfærd.
        worker_max_turns=max(2, decision.worker_max_turns or 8),
        worker_token_budget=max(0, decision.worker_token_budget or 0),
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
    findings: list[str] = []
    parsed_findings: list[ResearchFinding] = []
    gaps: list[str] = []
    if decision.tier == "orchestrated":
        tasks = store.create_tasks(
            run_id,
            await _plan_tasks(
                query,
                policy.max_tasks,
                planner_enabled=_setting("research_llm_planner_enabled", False),
            ),
        )
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
                        max_turns=policy.worker_max_turns,
                        budget_tokens=policy.worker_token_budget,
                    )
                    text = str((result or {}).get("text") or "").strip()
                    provider_status = str((result or {}).get("status") or "")
                    if not text or provider_status in {"error", "failed", "provider_error"}:
                        raise RuntimeError("research worker returned no usable evidence")
                    # Fase B2: læs den struktur worker'en faktisk blev bedt om.
                    # Defensivt — kan svaret ikke parses, bliver hele teksten ét
                    # fund frem for at forsvinde.
                    track = _parse_findings(text, int(task.get("ordinal") or 0))
                    parsed_findings.extend(track)
                    payload = dict(result) if isinstance(result, dict) else {"text": text}
                    payload["findings"] = [asdict(item) for item in track]
                    store.complete_task(str(task["id"]), payload)
                    return text
                except Exception as exc:
                    store.complete_task(str(task["id"]), {"error": str(exc)}, status="failed")
                    return f"Track {task['ordinal']} failed: {exc}"

        async def _wave(wave_tasks: list, *, total: int):
            """Kør én bølge workers og yield fremskridt. Sætter `timed_out`."""
            nonlocal timed_out
            pending = {asyncio.create_task(one(task)) for task in wave_tasks}
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
                        "total_tasks": total,
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

        async for event in _wave(tasks, total=len(tasks)):
            yield event

        # Fase B1: stop på EVIDENS, ikke på «bølgen blev færdig». Er kilderne for
        # få OG er der råd, kører ÉN ekstra bølge på de tyndeste tracks. Den kaldes
        # her — ikke i en løkke — så et run kan strukturelt ikke loope her.
        known_ids = {str(t["id"]) for t in tasks}
        if not timed_out:
            plan = _topup_plan(run_id, tasks, policy)
            if plan:
                fresh = [t for t in store.create_tasks(run_id, plan)
                         if str(t["id"]) not in known_ids]
                if fresh:
                    known_ids |= {str(t["id"]) for t in fresh}
                    yield _event("research_progress", {
                        "research_run_id": run_id,
                        "phase": "topping_up",
                        "reason": "source_target",
                        "source_target": policy.source_target,
                        "sources": store.source_count(run_id),
                        "tracks": [int(t["ordinal"]) for t in fresh],
                    })
                    async for event in _wave(fresh, total=len(tasks) + len(fresh)):
                        yield event

        # Fase B3: ÉN critic-runde — hvad mangler der? (spec princip 5: ét
        # gennemløb). Kun når der er påstande at kritisere, tid tilbage og
        # budget tilbage. Defensiv: en critic der fejler må ikke koste svaret.
        if not timed_out and parsed_findings and _tool_calls_used(run_id) < policy.max_tool_calls:
            try:
                fresh_critic = [
                    t for t in store.create_tasks(
                        run_id,
                        [ResearchTask(
                            ordinal=0,
                            title="Gap check",
                            objective=_gap_objective(query, parsed_findings),
                        )],
                    )
                    if str(t["id"]) not in known_ids
                ]
                if fresh_critic:
                    critic_task = fresh_critic[0]
                    store.start_task(str(critic_task["id"]))
                    yield _event("research_progress", {
                        "research_run_id": run_id,
                        "phase": "gap_check",
                        "sources": store.source_count(run_id),
                    })
                    critic_result = await _run_worker(
                        worker_factory,
                        task=critic_task,
                        run_id=run_id,
                        skill_instructions=contract.instructions,
                        # Critic'en researcher ikke — den læser og peger. Derfor
                        # færre ture og et lavere loft end research-workerne
                        # (målt: critic brænder i snit 7.382 tokens mod
                        # researcher'ens 14.561).
                        max_turns=min(4, policy.worker_max_turns),
                        budget_tokens=min(20_000, policy.worker_token_budget)
                        if policy.worker_token_budget
                        else 0,
                    )
                    critic_text = str((critic_result or {}).get("text") or "").strip()
                    gaps = _parse_gaps(critic_text)
                    store.complete_task(str(critic_task["id"]), {"text": critic_text, "gaps": gaps})
            except Exception:
                # Critic'en er et supplement, ikke et krav. Fejler den, kører
                # runnet videre uden huller — men det bliver ikke skjult.
                gaps = []

        try:
            canonical = store.list_sources(run_id)
        except Exception:
            canonical = []
        evidence = _evidence_block(findings, canonical, parsed_findings, gaps)
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
                        "findings": len(parsed_findings),
                        "gaps": len(gaps),
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
