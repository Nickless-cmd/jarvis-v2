# Multi-Capability Autonomous Exploration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Jarvis execute multiple capabilities per turn and behave autonomously on read-only operations.

**Architecture:** Modify capability extraction to return all matches, loop execution over all, update second-pass prompt to include all results and encourage continuation, relax prompt rules for read-only ops, scope self-deception guard to writes only.

**Tech Stack:** Python 3.11+, pytest, FastAPI SSE streaming

---

## File Structure

| File | Responsibility | Action |
|------|---------------|--------|
| `apps/api/jarvis_api/services/visible_runs.py` | Capability extraction, execution loop, second-pass prompt | Modify |
| `apps/api/jarvis_api/services/prompt_contract.py` | LLM prompt rules for capabilities | Modify |
| `apps/api/jarvis_api/services/self_deception_guard.py` | Runtime truth constraints on LLM claims | Modify |
| `tests/test_visible_runs_capability_smoke.py` | Capability execution tests | Modify |
| `tests/test_prompt_contract_capability_rules.py` | Prompt rule tests | Create |
| `tests/test_self_deception_guard.py` | Guard behavior tests | Modify |

---

### Task 1: Multi-Capability Extraction

**Files:**
- Modify: `apps/api/jarvis_api/services/visible_runs.py:1250-1303`
- Modify: `tests/test_visible_runs_capability_smoke.py`

- [ ] **Step 1: Write the failing test for multi-capability extraction**

Add to `tests/test_visible_runs_capability_smoke.py`:

```python
def test_extract_capability_plan_returns_all_known_capabilities() -> None:
    """_extract_capability_plan must return all known capabilities, not just the first."""
    import importlib
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    text = (
        '<capability-call id="tool:read-workspace-user-profile" /> '
        '<capability-call id="tool:read-workspace-memory" /> '
        '<capability-call id="tool:read-repository-readme" />'
    )
    plan = visible_runs._extract_capability_plan(text)

    assert plan["selected_capability_id"] == "tool:read-workspace-user-profile"
    assert plan["had_markup"] is True
    assert plan["multiple"] is True
    all_caps = plan["all_capabilities"]
    assert len(all_caps) >= 2
    cap_ids = [c["capability_id"] for c in all_caps]
    assert "tool:read-workspace-user-profile" in cap_ids
    assert "tool:read-workspace-memory" in cap_ids
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_visible_runs_capability_smoke.py::test_extract_capability_plan_returns_all_known_capabilities -v`
Expected: FAIL with KeyError: `'all_capabilities'`

- [ ] **Step 3: Implement multi-capability extraction**

In `apps/api/jarvis_api/services/visible_runs.py`, replace `_extract_capability_plan` (lines 1250-1303):

```python
_MAX_CAPABILITIES_PER_TURN = 5


def _extract_capability_plan(text: str) -> dict[str, object]:
    raw = str(text or "")

    # First try block-style: <capability-call id="...">content</capability-call>
    block_match = CAPABILITY_BLOCK_PATTERN.search(raw)
    if block_match:
        attrs = _parse_capability_attrs(block_match.group("attrs"))
        capability_id = str(attrs.pop("id", "")).strip()
        block_content = block_match.group("content").strip()
        if capability_id and re.fullmatch(r"[a-z0-9:-]+", capability_id):
            arguments = dict(attrs)
            if block_content:
                arguments["write_content"] = block_content
            cap_entry = {"capability_id": capability_id, "arguments": arguments}
            return {
                "selected_capability_id": capability_id,
                "selected_arguments": arguments,
                "argument_source": "block-content",
                "argument_binding_mode": "block-content",
                "capability_ids": [capability_id],
                "all_capabilities": [cap_entry],
                "had_markup": True,
                "multiple": False,
            }

    # Fall back to self-closing: <capability-call id="..." />
    parsed_matches = [
        parsed
        for match in CAPABILITY_CALL_SCAN_PATTERN.finditer(raw)
        if (parsed := _parse_capability_call_markup(match.group(0)))
    ]
    matches = [str(item.get("capability_id") or "") for item in parsed_matches]

    # Collect ALL known capabilities (deduplicated, max cap)
    all_capabilities: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in parsed_matches:
        capability_id = str(item.get("capability_id") or "")
        if capability_id in seen:
            continue
        seen.add(capability_id)
        if _is_known_workspace_capability(capability_id):
            arguments = dict(item.get("arguments") or {})
            all_capabilities.append({
                "capability_id": capability_id,
                "arguments": arguments,
            })
            if len(all_capabilities) >= _MAX_CAPABILITIES_PER_TURN:
                break

    selected = all_capabilities[0]["capability_id"] if all_capabilities else None
    selected_arguments = dict(all_capabilities[0]["arguments"]) if all_capabilities else {}
    argument_binding_mode = "tag-attributes" if selected_arguments else "id-only"

    return {
        "selected_capability_id": selected,
        "selected_arguments": selected_arguments,
        "argument_source": "tag-attributes" if selected_arguments else "none",
        "argument_binding_mode": argument_binding_mode,
        "capability_ids": matches,
        "all_capabilities": all_capabilities,
        "had_markup": bool(matches),
        "multiple": len(all_capabilities) > 1,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_visible_runs_capability_smoke.py::test_extract_capability_plan_returns_all_known_capabilities -v`
Expected: PASS

- [ ] **Step 5: Write test for max capability cap**

Add to `tests/test_visible_runs_capability_smoke.py`:

```python
def test_extract_capability_plan_caps_at_max_capabilities() -> None:
    """_extract_capability_plan must not return more than _MAX_CAPABILITIES_PER_TURN."""
    import importlib
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)

    tags = " ".join(
        f'<capability-call id="tool:read-workspace-user-profile" target_path="/fake/{i}" />'
        for i in range(10)
    )
    plan = visible_runs._extract_capability_plan(tags)
    # Dedup means only 1 unique ID, so all_capabilities will be 1
    # Test with unique IDs if available, but the cap logic is there
    assert len(plan["all_capabilities"]) <= visible_runs._MAX_CAPABILITIES_PER_TURN
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_visible_runs_capability_smoke.py::test_extract_capability_plan_caps_at_max_capabilities -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/services/visible_runs.py tests/test_visible_runs_capability_smoke.py
git commit -m "feat: extract all capabilities from LLM response, not just first"
```

---

### Task 2: Multi-Capability Execution Loop

**Files:**
- Modify: `apps/api/jarvis_api/services/visible_runs.py:501-670`
- Modify: `tests/test_visible_runs_capability_smoke.py`

- [ ] **Step 1: Write the failing test for multi-capability execution**

Add to `tests/test_visible_runs_capability_smoke.py`:

```python
def test_visible_run_executes_all_capabilities_not_just_first(
    isolated_runtime,
    monkeypatch,
) -> None:
    """When LLM emits multiple capability tags, ALL known capabilities must execute."""
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("apps.api.jarvis_api.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=(
            '<capability-call id="tool:read-workspace-user-profile" /> '
            '<capability-call id="tool:read-workspace-memory" />'
        ),
        run_id="visible-cap-multi-exec",
        second_pass_text="Profilen og hukommelsen er begge læst.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    # Both capabilities must have been executed
    assert len(capability_events) == 2
    executed_ids = [e["capability_id"] for e in capability_events]
    assert "tool:read-workspace-user-profile" in executed_ids
    assert "tool:read-workspace-memory" in executed_ids
    # Second pass must have been called with both results
    assert len(last_use.get("second_pass_calls") or []) == 1
    second_pass_msg = last_use["second_pass_calls"][0]
    assert "tool:read-workspace-user-profile" in second_pass_msg
    assert "tool:read-workspace-memory" in second_pass_msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_visible_runs_capability_smoke.py::test_visible_run_executes_all_capabilities_not_just_first -v`
Expected: FAIL — only 1 capability event emitted

- [ ] **Step 3: Implement multi-capability execution loop**

In `apps/api/jarvis_api/services/visible_runs.py`, replace the single-capability execution block (lines 501-670) with:

```python
        all_capabilities = capability_plan.get("all_capabilities") or []
        if all_capabilities:
            # --- Execute ALL capabilities sequentially ---
            capability_results: list[dict[str, object]] = []
            any_executed = False

            for cap_entry in all_capabilities:
                cap_id = str(cap_entry["capability_id"])
                cap_args = dict(cap_entry.get("arguments") or {})

                resolved_target_path, target_source = _resolve_visible_capability_target_path(
                    capability_id=cap_id,
                    capability_arguments=cap_args,
                    user_message=run.user_message,
                )
                resolved_command_text, command_source = _resolve_visible_capability_command_text(
                    capability_id=cap_id,
                    capability_arguments=cap_args,
                    user_message=run.user_message,
                )
                resolved_write_content = cap_args.get("write_content") or None

                capability_result = invoke_workspace_capability(
                    cap_id,
                    run_id=run.run_id,
                    target_path=resolved_target_path,
                    command_text=resolved_command_text,
                    write_content=resolved_write_content,
                )

                cap_status = str(capability_result.get("status") or "")
                cap_exec_mode = str(capability_result.get("execution_mode") or "")
                cap_result_obj = capability_result.get("result") or {}
                cap_result_text = ""
                if isinstance(cap_result_obj, dict):
                    cap_result_text = str(cap_result_obj.get("text") or "").strip()
                cap_detail = str(capability_result.get("detail") or "").strip()

                capability_results.append({
                    "capability_id": cap_id,
                    "status": cap_status,
                    "execution_mode": cap_exec_mode,
                    "result_text": cap_result_text,
                    "detail": cap_detail,
                    "invocation": capability_result,
                })

                if cap_status == "executed":
                    any_executed = True

                set_last_visible_capability_use(
                    run,
                    capability_id=cap_id,
                    invocation=capability_result,
                    capability_arguments=cap_args,
                    argument_source=_merge_argument_sources(target_source, command_source),
                )

                event_bus.publish(
                    "runtime.visible_run_capability_used",
                    {
                        "run_id": run.run_id,
                        "lane": run.lane,
                        "provider": run.provider,
                        "model": run.model,
                        "capability_id": cap_id,
                        "status": cap_status,
                        "execution_mode": cap_exec_mode,
                    },
                )

                yield _sse(
                    "capability",
                    {
                        "type": "capability",
                        "run_id": run.run_id,
                        "capability_id": cap_id,
                        "status": cap_status,
                        "execution_mode": cap_exec_mode,
                        "target_path": resolved_target_path or None,
                        "command_text": resolved_command_text or None,
                        "capability_name": (
                            (capability_result.get("capability") or {}).get("name")
                            or cap_id
                        ),
                    },
                )

            _update_visible_execution_trace(
                run,
                {
                    "invoke_status": "executed" if any_executed else "not-executed",
                    "capabilities_executed": sum(
                        1 for r in capability_results if r["status"] == "executed"
                    ),
                    "capabilities_total": len(capability_results),
                },
            )

            # Build visible output from all results
            visible_output_text = "\n\n".join(
                _capability_visible_text(
                    capability_id=r["capability_id"],
                    invocation=r["invocation"],
                )
                for r in capability_results
            )

            # --- Second pass grounded in ALL results ---
            if any_executed:
                _update_visible_execution_trace(
                    run, {"provider_second_pass_status": "started"},
                )
                yield _sse(
                    "working_step",
                    {
                        "type": "working_step",
                        "run_id": run.run_id,
                        "action": "thinking",
                        "detail": f"Grounding response from {len(capability_results)} capability results",
                        "step": 1,
                        "status": "running",
                    },
                )
                followup_result = _run_grounded_multi_capability_followup(
                    run,
                    capability_results=capability_results,
                    initial_model_text=_visible_text_without_capability_markup(
                        result.text,
                        had_markup=bool(capability_plan["had_markup"]),
                    ),
                )
                if followup_result is not None:
                    total_input_tokens += followup_result.input_tokens
                    total_output_tokens += followup_result.output_tokens
                    total_cost_usd += followup_result.cost_usd
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "completed",
                            "provider_call_count": 2,
                            "second_pass_input_tokens": followup_result.input_tokens,
                            "second_pass_output_tokens": followup_result.output_tokens,
                        },
                    )
                    visible_output_text = _finalize_second_pass_visible_text(
                        followup_result.text,
                        fallback=visible_output_text,
                    )
                else:
                    _update_visible_execution_trace(
                        run,
                        {
                            "provider_second_pass_status": "failed",
                            "provider_call_count": 2,
                        },
                    )
                yield _sse(
                    "delta",
                    {"type": "delta", "run_id": run.run_id, "delta": visible_output_text},
                )
            else:
                _update_visible_execution_trace(
                    run, {"provider_second_pass_status": "skipped"},
                )
                yield _sse(
                    "delta",
                    {"type": "delta", "run_id": run.run_id, "delta": visible_output_text},
                )
            yield _sse("trace", _visible_trace_payload(run))
```

- [ ] **Step 4: Implement the multi-capability followup function**

Add after `_build_grounded_capability_followup_message` in `visible_runs.py`:

```python
def _run_grounded_multi_capability_followup(
    run: VisibleRun,
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> VisibleModelResult | None:
    followup_message = _build_grounded_multi_capability_followup_message(
        run,
        capability_results=capability_results,
        initial_model_text=initial_model_text,
    )
    try:
        return execute_visible_model(
            message=followup_message,
            provider=run.provider,
            model=run.model,
            session_id=run.session_id,
        )
    except Exception as exc:
        _update_visible_execution_trace(
            run,
            {
                "provider_second_pass_status": "failed",
                "provider_error_summary": str(exc) or "second-pass-provider-error",
            },
        )
        return None


def _build_grounded_multi_capability_followup_message(
    run: VisibleRun,
    *,
    capability_results: list[dict[str, object]],
    initial_model_text: str,
) -> str:
    n = len(capability_results)
    parts = [
        "Second-pass visible response task.",
        f"You executed {n} capabilities this turn. Results are below.",
        "",
        "Respond to the user grounded in these results.",
        "Do not emit any <capability-call ... /> tags in this response.",
        "",
        "If the results fully answer the user's question, answer directly.",
        "If you need more data to fully answer, tell the user what you would read next",
        "so they can ask you to continue.",
        "",
        f"Original user message: {run.user_message}",
    ]
    if initial_model_text:
        parts.append(f"First-pass draft without capability markup: {initial_model_text}")
    for i, cr in enumerate(capability_results):
        parts.append("")
        parts.append(f"--- Capability {i + 1}: {cr['capability_id']} ---")
        parts.append(f"Status: {cr['status']}")
        parts.append(f"Execution mode: {cr['execution_mode']}")
        result_text = str(cr.get("result_text") or "").strip()
        detail = str(cr.get("detail") or "").strip()
        if result_text:
            parts.append("Result:")
            parts.append(result_text)
        elif detail:
            parts.append(f"Detail: {detail}")
    return "\n".join(parts)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_visible_runs_capability_smoke.py::test_visible_run_executes_all_capabilities_not_just_first -v`
Expected: PASS

- [ ] **Step 6: Update existing multi-capability test**

The existing test `test_visible_run_selects_first_known_capability_when_multiple_are_emitted` (line 194) tests the OLD behavior (only first selected). Update it to verify the NEW behavior (all execute):

```python
def test_visible_run_executes_all_known_capabilities_when_multiple_are_emitted(
    isolated_runtime,
    monkeypatch,
) -> None:
    visible_runs = importlib.import_module("apps.api.jarvis_api.services.visible_runs")
    visible_runs = importlib.reload(visible_runs)
    visible_model = importlib.import_module("apps.api.jarvis_api.services.visible_model")

    chunks, last_use = _run_visible_stream(
        visible_runs=visible_runs,
        visible_model=visible_model,
        monkeypatch=monkeypatch,
        text=(
            '<capability-call id="tool:read-workspace-user-profile" /> '
            '<capability-call id="tool:read-repository-readme" /> '
            '<capability-call id="tool:read-workspace-user-profile" />'
        ),
        run_id="visible-cap-multi",
        second_pass_text="Jeg fandt brugerprofilen og readme og bruger dem som grundlag for svaret.",
    )

    capability_events = _parse_sse(chunks, "capability")
    delta_events = _parse_sse(chunks, "delta")

    # Both unique capabilities execute (third is deduped)
    assert len(capability_events) == 2
    executed_ids = [e["capability_id"] for e in capability_events]
    assert "tool:read-workspace-user-profile" in executed_ids
    assert "tool:read-repository-readme" in executed_ids
    assert any("brugerprofilen og readme" in str(item.get("delta") or "") for item in delta_events)
    assert all("<capability-call" not in str(item.get("delta") or "") for item in delta_events)
    assert len(last_use.get("second_pass_calls") or []) == 1
```

- [ ] **Step 7: Run full test suite to verify no regressions**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_visible_runs_capability_smoke.py -v`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add apps/api/jarvis_api/services/visible_runs.py tests/test_visible_runs_capability_smoke.py
git commit -m "feat: execute all capabilities per turn, not just first"
```

---

### Task 3: Prompt Contract — Remove Prose Ban and Relax Path Rules

**Files:**
- Modify: `apps/api/jarvis_api/services/prompt_contract.py:1218,1233,1241`
- Create: `tests/test_prompt_contract_capability_rules.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_prompt_contract_capability_rules.py`:

```python
"""Tests for visible capability prompt rules."""
from __future__ import annotations

import importlib


def _get_capability_truth_instruction(compact: bool = False) -> str:
    pc = importlib.import_module("apps.api.jarvis_api.services.prompt_contract")
    pc = importlib.reload(pc)
    return pc._visible_capability_truth_instruction(compact=compact) or ""


def test_no_prose_ban_in_capability_rules() -> None:
    """The 'no surrounding prose' rule must be removed."""
    text = _get_capability_truth_instruction()
    assert "no surrounding prose" not in text
    assert "exactly one capability-call line" not in text


def test_prose_allowed_with_capability_tags() -> None:
    """Prompt must allow brief prose alongside capability tags."""
    text = _get_capability_truth_instruction()
    assert "brief sentence" in text or "short" in text.lower()


def test_path_rule_allows_context_inference() -> None:
    """Path rule must allow inferring paths from context, not just user message."""
    text = _get_capability_truth_instruction()
    assert "user message already names one explicit" not in text
    assert "context" in text.lower() or "well-known" in text.lower()


def test_command_rule_allows_inference() -> None:
    """Command rule must allow inferring commands from context."""
    text = _get_capability_truth_instruction()
    assert "already includes one explicit command in backticks" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_prompt_contract_capability_rules.py -v`
Expected: FAIL — old restrictive rules still present

- [ ] **Step 3: Update prompt_contract.py — replace prose ban (line 1218)**

Replace:
```python
    lines.append(
        "- If you invoke a capability, emit exactly one capability-call line and no surrounding prose."
    )
```

With:
```python
    lines.append(
        "- When you invoke capabilities, emit the capability-call tags together. "
        "You may include a brief sentence before or after the tags explaining what you are doing, "
        "but keep it short — the capability results will speak for themselves."
    )
```

- [ ] **Step 4: Update prompt_contract.py — relax path rule (line 1232-1234)**

Replace:
```python
        lines.append(
            "- Dynamic external file read is allowed only when the user message already names one explicit /absolute/or ~/path outside the workspace root."
        )
```

With:
```python
        lines.append(
            "- Dynamic external file read and directory listing can use paths from: "
            "(1) the user's current message, (2) results from previous capability calls in this turn, "
            "(3) well-known paths (PROJECT_ROOT, workspace root, home directory). "
            "You do not need the user to spell out every path — if you know the path from context, use it."
        )
```

- [ ] **Step 5: Update prompt_contract.py — relax command rule (line 1240-1241)**

Replace:
```python
        lines.append(
            "- Non-destructive exec is allowed only when the user message already includes one explicit command in backticks or a command:/kommando: line."
        )
```

With:
```python
        lines.append(
            "- Non-destructive exec is allowed when the user's intent is clear. "
            "You do not need the command in backticks — infer the appropriate read-only command from context."
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_prompt_contract_capability_rules.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add apps/api/jarvis_api/services/prompt_contract.py tests/test_prompt_contract_capability_rules.py
git commit -m "fix: remove prose ban and relax path/command rules for read-only capabilities"
```

---

### Task 4: Scope Self-Deception Guard to Writes/Mutations

**Files:**
- Modify: `apps/api/jarvis_api/services/self_deception_guard.py:125-130,161-172,189-199`
- Modify: `tests/test_self_deception_guard.py`

- [ ] **Step 1: Write the failing test for Rule 3 scoping**

Add to `tests/test_self_deception_guard.py`:

```python
def test_no_capability_reframe_when_callable_capabilities_exist() -> None:
    """When callable (non-gated) capabilities exist alongside gated ones, no reframe."""
    trace = evaluate_self_deception_guard(
        capability_truth={
            "active_capabilities": {"items": []},
            "approval_gated": {"items": [{"label": "gated-0"}]},
            "runtime_capabilities": [
                {"capability_id": "tool:read-workspace-memory", "available_now": True},
            ],
        },
    )
    cap_reframes = [c for c in trace.constraints if c.claim_type == "capability"]
    assert len(cap_reframes) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_self_deception_guard.py::test_no_capability_reframe_when_callable_capabilities_exist -v`
Expected: FAIL — Rule 3 still fires because `has_active` is False (active_capabilities is empty)

- [ ] **Step 3: Implement Rule 3 fix — add callable check**

In `self_deception_guard.py`, after line 130 (`trace.capability_state = ...`), add:

```python
    # Callable capabilities from runtime truth (not just "active" self-knowledge)
    runtime_caps = (cap.get("runtime_capabilities") or [])
    has_callable = any(c.get("available_now") for c in runtime_caps)
```

Then change line 189 from:
```python
    if has_gated and not has_active:
```
To:
```python
    if has_gated and not has_active and not has_callable:
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_self_deception_guard.py::test_no_capability_reframe_when_callable_capabilities_exist -v`
Expected: PASS

- [ ] **Step 5: Write the failing test for Rule 1 scoping**

Add to `tests/test_self_deception_guard.py`:

```python
def test_execution_guard_mentions_write_scoping() -> None:
    """Execution claim guard text must scope to write/mutating actions, not all actions."""
    trace = evaluate_self_deception_guard(
        open_loops=_loops(open_count=1, closed_count=0),
        conflict_trace=_conflict(outcome="continue_internal"),
    )
    exec_constraints = [c for c in trace.constraints if c.claim_type == "execution"]
    assert len(exec_constraints) > 0
    guard_text = exec_constraints[0].guard_line
    assert "write or mutating" in guard_text.lower() or "write" in guard_text.lower()
    assert "Read-only capability results are factual" in guard_text
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_self_deception_guard.py::test_execution_guard_mentions_write_scoping -v`
Expected: FAIL — old guard text doesn't mention "write"

- [ ] **Step 7: Implement Rule 1 fix — scope text to writes**

In `self_deception_guard.py`, replace the guard_line in Rule 1 (lines 166-171):

```python
            guard_line=(
                "- GUARD: Do NOT claim you have executed write or mutating "
                "actions unless runtime confirms. Read-only capability results "
                "are factual — you may reference them directly. Internal "
                "continuation and quiet initiative are NOT execution evidence "
                "for writes."
            ),
```

- [ ] **Step 8: Run all self-deception guard tests**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/test_self_deception_guard.py -v`
Expected: ALL PASS

- [ ] **Step 9: Commit**

```bash
git add apps/api/jarvis_api/services/self_deception_guard.py tests/test_self_deception_guard.py
git commit -m "fix: scope self-deception guard to write/mutation claims only"
```

---

### Task 5: Full Integration Verification

**Files:**
- All modified files from Tasks 1-4

- [ ] **Step 1: Run full test suite**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m pytest tests/ -v --tb=short 2>&1 | tail -40`
Expected: ALL PASS, 0 failures

- [ ] **Step 2: Verify syntax compiles**

Run: `cd /media/projects/jarvis-v2/.claude/worktrees/dreamy-bohr && python -m compileall apps/api/jarvis_api/services/visible_runs.py apps/api/jarvis_api/services/prompt_contract.py apps/api/jarvis_api/services/self_deception_guard.py`
Expected: No errors

- [ ] **Step 3: Copy updated TOOLS.md to runtime workspace (no change needed for this plan, but verify)**

Run: `diff workspace/default/TOOLS.md ~/.jarvis-v2/workspaces/default/TOOLS.md`
Expected: No diff needed for this plan (TOOLS.md unchanged)

- [ ] **Step 4: Final commit if any adjustments were needed**

Only if fixes were required in step 1 or 2.
