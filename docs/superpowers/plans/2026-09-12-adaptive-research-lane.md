# Adaptive Research Lane Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mobile's prompt-prefix research mode with a durable, evidence-governed research lane that runs inline for small tasks and uses existing researcher agents for parallelizable tasks.

**Architecture:** An additive `research_mode` request enters a focused router and contract layer before the existing visible run. Inline mode augments the normal Jarvis prompt and observes structured web results; orchestrated mode persists a research run, delegates bounded read-only tasks through the existing agent runtime, verifies evidence, then lets Jarvis stream the final synthesis through SSE v2.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, SQLite runtime DB, existing Jarvis visible/agent runtimes, SSE v2, pytest.

**Spec:** `docs/superpowers/specs/2026-09-12-mobile-adaptive-research-implementation-spec.md`

## Global Constraints

- `research_mode` defaults false and cannot alter older clients.
- Persist and display the user's original message without a research prefix.
- Research agents are read-only with maximum three concurrent workers.
- Jarvis owns the final answer; workers never write directly to chat.
- Research progress contains no raw chain-of-thought.
- Avoid logic changes in oversized `core/services/visible_runs.py`; branch outside it.
- Do not run the full repository test suite; run only affected pytest files.
- Do not touch unrelated `docs/specs/2026-09-08-deepseek-harness-lessons-for-jarvis.md` changes.

---

### Task 1: Request and Research Contract Types

**Files:**
- Create: `core/services/research_contract.py`
- Create: `tests/test_research_contract.py`
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Modify: `tests/test_chat_stream_v2_override.py`

**Interfaces:**
- Produces: `ResearchDecision`, `ResearchPolicy`, `ResearchPlan`, `ResearchTask`, `ResearchFinding`, `ResearchSource`, `load_research_contract()`.
- Produces: `ChatStreamRequest.research_mode: bool = False`.

- [ ] **Step 1: Write failing normalization and request-default tests**

```py
assert ChatStreamRequest(message="x").research_mode is False
assert normalize_source({"url": "https://EXAMPLE.com/a#x"}).canonical_url == "https://example.com/a"
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_contract.py tests/test_chat_stream_v2_override.py -k 'research or request'`
Expected: FAIL because types/field do not exist.

- [ ] **Step 3: Implement immutable normalized contracts and skill load fallback**

Use dataclasses or typed dictionaries with explicit validators. Load the canonical `deep-research` skill through a public skill-engine service, record explicit mode usage, and return a built-in minimum contract on failure.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_contract.py tests/test_chat_stream_v2_override.py -k 'research or request'`
Expected: PASS.

### Task 2: Deterministic Adaptive Router

**Files:**
- Create: `core/services/research_router.py`
- Create: `tests/test_research_router.py`

**Interfaces:**
- Consumes: user message, attachment count, policy.
- Produces: `classify_research(...) -> ResearchDecision` with tier, signals, max workers/tasks/tool calls/wall time/source target.

- [ ] **Step 1: Write failing boundary tests**

```py
assert classify_research("Hvad er seneste WLED version?").tier == "inline"
assert classify_research("Sammenlign fem leverandører på pris, sikkerhed og drift i en grundig rapport").tier == "orchestrated"
assert classify_research("Forklar dette ene komplekse bevis grundigt").tier == "inline"
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_router.py`
Expected: FAIL because router does not exist.

- [ ] **Step 3: Implement explainable conservative scoring**

Require at least two independent-track signals plus one complexity signal for orchestration. Clamp workers to 3 and tasks to 6.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_router.py`
Expected: PASS.

### Task 3: Durable Research Store

**Files:**
- Create: `core/services/research_store.py`
- Create: `tests/test_research_store.py`

**Interfaces:**
- Produces: `create_run`, `transition_run`, `create_tasks`, `start_task`, `complete_task`, `add_source`, `add_steer`, `active_for_session`, `mark_stale_interrupted`.
- Consumes: existing runtime DB `connect()`.

- [ ] **Step 1: Write failing state, dedup, and stale tests**

```py
run = create_run(session_id="s1", original_query="q", tier="inline")
assert transition_run(run["id"], "planning")["status"] == "planning"
with pytest.raises(ResearchStateError): transition_run(run["id"], "completed")
assert add_source(run["id"], source)["id"] == add_source(run["id"], source)["id"]
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_store.py`
Expected: FAIL because store does not exist.

- [ ] **Step 3: Implement focused tables and legal transitions**

Keep schema ownership in `research_store.py`; do not add research methods to `core/runtime/db.py`. Terminal states are immutable and task agents are single-flight.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_store.py`
Expected: PASS.

### Task 4: Request-Scoped Prompt Context

**Files:**
- Create: `core/services/research_prompt_context.py`
- Create: `tests/test_research_prompt_context.py`
- Modify: `core/services/skill_relevance_surface.py`
- Modify: `tests/test_skill_relevance_surface.py`

**Interfaces:**
- Produces: `research_context(policy, evidence="")` context manager and `research_prompt_section()`.
- Consumes: normalized contract, never user-visible message mutation.

- [ ] **Step 1: Write failing isolation tests**

```py
with research_context(policy):
    assert "RESEARCH CONTRACT" in research_prompt_section()
assert research_prompt_section() == ""
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_prompt_context.py tests/test_skill_relevance_surface.py -k research`
Expected: FAIL on missing context/section.

- [ ] **Step 3: Implement ContextVar section and focused skill-surface hook**

The section contains policy, source rules, budget, and compressed verified evidence only. `skill_relevance_surface.relevant_skills_section()` prepends it before ordinary suggestions. Reset in `finally`; rely on detached run's copied context. This avoids a logic edit to oversized `prompt_contract.py`, which already consumes the skill surface.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_prompt_context.py tests/test_skill_relevance_surface.py -k research`
Expected: PASS.

### Task 5: Structured Evidence Collector

**Files:**
- Create: `core/services/research_evidence_collector.py`
- Create: `tests/test_research_evidence_collector.py`
- Modify: `core/tools/simple_tools_web.py`
- Modify: focused web-tool tests.

**Interfaces:**
- Produces: no-op-safe `observe_web_result(tool_name, result)` bound to active research run.
- Consumes: structured web tool dictionaries and `research_store.add_source`.

- [ ] **Step 1: Write failing no-op and capture tests**

```py
assert observe_web_result("web_search", result) == 0
with collecting_for(run_id):
    assert observe_web_result("web_search", result) == 2
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_evidence_collector.py tests/test_simple_tools_web.py -k 'web_search or research'`
Expected: FAIL because collector hook is absent.

- [ ] **Step 3: Implement observer at successful structured tool exits**

Never regex URLs from model prose. Collector failures are observed but cannot break ordinary web calls; active orchestrated research treats store failure as terminal.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_evidence_collector.py tests/test_simple_tools_web.py -k 'web_search or research'`
Expected: PASS.

### Task 6: Research Orchestrator and Agent Bounds

**Files:**
- Create: `core/services/research_orchestrator.py`
- Create: `tests/test_research_orchestrator.py`
- Modify: `core/services/visible_runs_sections/detached_run.py`
- Modify: focused detached-run tests.

**Interfaces:**
- Produces: `stream_research_run(...)` legacy event iterator and `start_research_or_visible_run(...)` selector.
- Consumes: router, store, prompt context, existing `spawn_agent_task`, existing `start_visible_run`.

- [ ] **Step 1: Write failing inline/orchestrated/cancel tests**

```py
events = collect(stream_research_run(message="lookup", decision=inline))
assert spawned_agents == []
assert events[0]["kind"] == "research_started"
assert max_observed_concurrency <= 3
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_orchestrator.py tests/test_detached_run.py`
Expected: FAIL because selector/orchestrator do not exist.

- [ ] **Step 3: Implement inline delegation and bounded worker waves**

Inline wraps normal visible run in research context. Orchestrated planning yields 2-6 validated tasks, runs at most 3 read-only researcher agents concurrently, rejects provider-error output, records structured findings, performs one gap/repair pass, and invokes Jarvis visible synthesis.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_orchestrator.py tests/test_detached_run.py`
Expected: PASS.

### Task 7: SSE Progress, Snapshot, and Steering

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat_stream_v2.py`
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Modify: route tests.
- Modify: `apps/mobile/src/lib/sseProtocol.ts`
- Modify: `apps/mobile/src/lib/streamReducer.ts`
- Modify: `apps/mobile/src/lib/streamReducer.test.ts`
- Create: `apps/mobile/src/components/ResearchStatus.tsx`
- Create: `apps/mobile/src/components/ResearchStatus.test.tsx`

**Interfaces:**
- Produces: additive `research_*` system events and active-run snapshot metadata.
- Consumes: research store snapshots; unknown clients remain compatible.

- [ ] **Step 1: Write failing route and reducer tests**

```py
assert active["sessions"][0]["research_status"] == "researching"
assert persisted_user_message == original_message
```

```ts
expect(reduce(event).research).toMatchObject({ phase: 'researching', sources: 4 })
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_chat_stream_v2.py -k research && cd apps/mobile && npm test -- --runInBand src/lib/streamReducer.test.ts src/components/ResearchStatus.test.tsx`
Expected: FAIL on missing metadata/events/UI.

- [ ] **Step 3: Wire route selector, snapshots, steering, and mobile status**

Persist original user text. A message arriving during active research becomes a durable steer applied at the next phase boundary. Render status above composer, outside `MessageList`, and use existing cancel-run.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_chat_stream_v2.py -k research && cd apps/mobile && npm test -- --runInBand src/lib/streamReducer.test.ts src/components/ResearchStatus.test.tsx`
Expected: PASS.

### Task 8: Quality Gates and Focused Evaluation

**Files:**
- Create: `core/services/research_quality.py`
- Create: `tests/test_research_quality.py`
- Create: `tests/fixtures/research_eval_cases.json`
- Create: `scripts/eval_research_lane.py`
- Create: `tests/test_eval_research_lane.py`

**Interfaces:**
- Produces: `evaluate_research_report(report, sources, requested_facets)` and a deterministic local eval summary.
- Consumes: normalized findings/source ledger, no live network in unit tests.

- [ ] **Step 1: Write failing citation/coverage/contradiction tests**

```py
result = evaluate_research_report("Claim [1]", sources=[], requested_facets=["price"])
assert result.passed is False
assert "citation_validity" in result.failures
```

- [ ] **Step 2: Run and confirm RED**

Run: `pytest -q tests/test_research_quality.py tests/test_eval_research_lane.py`
Expected: FAIL because quality layer does not exist.

- [ ] **Step 3: Implement deterministic gates and 20-case fixture harness**

Measure coverage, citation validity, source quality, contradictions, freshness, calibration, tool efficiency, and tier correctness. Do not use one opaque aggregate score to hide a failed critical gate.

- [ ] **Step 4: Run and confirm GREEN**

Run: `pytest -q tests/test_research_quality.py tests/test_eval_research_lane.py`
Expected: PASS.

### Task 9: Research Verification

**Files:**
- No production changes unless verification exposes a defect.

**Interfaces:**
- Consumes: Tasks 1-8.
- Produces: verified backend and mobile research integration.

- [ ] **Step 1: Run affected Python tests**

Run: `pytest -q tests/test_research_contract.py tests/test_research_router.py tests/test_research_store.py tests/test_research_prompt_context.py tests/test_research_evidence_collector.py tests/test_research_orchestrator.py tests/test_research_quality.py tests/test_eval_research_lane.py tests/test_detached_run.py tests/test_chat_stream_v2.py -k 'research or detached or stream'`
Expected: PASS.

- [ ] **Step 2: Run syntax smoke**

Run: `python -m compileall core/services/research_contract.py core/services/research_router.py core/services/research_store.py core/services/research_prompt_context.py core/services/research_evidence_collector.py core/services/research_orchestrator.py core/services/research_quality.py apps/api/jarvis_api/routes/chat.py apps/api/jarvis_api/routes/chat_stream_v2.py`
Expected: exit 0.

- [ ] **Step 3: Run affected mobile research tests and typecheck**

Run: `cd apps/mobile && npm test -- --runInBand src/lib/chatSettings.test.ts src/lib/streamClient.test.ts src/state/StreamContext.test.tsx src/lib/streamReducer.test.ts src/components/ResearchStatus.test.tsx && npm run typecheck`
Expected: PASS and exit 0.
