---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Harness Part C — Tool Concurrency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run independent read-only tool calls within one agentic round concurrently, cutting wall-clock, while preserving result order, cache byte-stability, and the existing mode/role/tier gating.

**Architecture:** A pure policy module (`tool_concurrency.py`) decides if a round is parallelizable (allowlist + all-or-nothing + kill-switch). The round executor is Boy-Scout-extracted from the 5700-line `visible_runs.py` into `simple_tool_executor.py`, then refactored into `_prepare_call`/`_finalize_call` helpers so a parallel branch can run only the tool invocation concurrently — each task inside its own `copy_context()` so mode/role/tier ContextVars propagate. Dedup/cache/gate/record stay single-threaded. Default off → byte-identical to today.

**Tech Stack:** Python 3.11, `concurrent.futures.ThreadPoolExecutor`, `contextvars`, pytest, `conda activate ai`.

**Execution note:** Task 1 (pure policy module) → fresh **haiku** subagent. Tasks 2–4 touch the extracted hot-path executor → **Claude inline**. Controller verifies between tasks.

---

## File Structure

- **New** `core/services/tool_concurrency.py` — allowlist + `is_parallelizable()` + `concurrency_mode()`. Pure, no execution.
- **New** `core/services/simple_tool_executor.py` — the extracted `_execute_simple_tool_calls` + `_prepare_call`/`_finalize_call` helpers + the parallel branch. Re-exported from `visible_runs`.
- **Modify** `core/services/visible_runs.py` — remove the executor body, add a re-export import.
- **New tests** `tests/test_tool_concurrency.py`, `tests/test_simple_tool_executor.py`.

---

## Task 1: `tool_concurrency.py` — policy module

**Files:**
- Create: `core/services/tool_concurrency.py`
- Test: `tests/test_tool_concurrency.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_tool_concurrency.py
from core.services.tool_concurrency import (
    is_parallelizable, concurrency_mode, _PARALLEL_SAFE, _MAX_CONCURRENCY,
)


def _call(name):
    return {"function": {"name": name, "arguments": {}}}


def test_allowlist_has_core_readers_not_writers():
    assert "read_file" in _PARALLEL_SAFE
    assert "search_memory" in _PARALLEL_SAFE
    assert "write_file" not in _PARALLEL_SAFE
    assert "operator_bash" not in _PARALLEL_SAFE
    assert "operator_write_file" not in _PARALLEL_SAFE


def test_all_safe_two_plus_on_is_parallelizable():
    calls = [_call("read_file"), _call("search_memory")]
    assert is_parallelizable(calls, mode="on") is True


def test_one_unsafe_present_blocks_whole_round():
    calls = [_call("read_file"), _call("write_file")]
    assert is_parallelizable(calls, mode="on") is False


def test_single_call_not_parallelizable():
    assert is_parallelizable([_call("read_file")], mode="on") is False


def test_mode_off_never_parallelizes():
    calls = [_call("read_file"), _call("search_memory")]
    assert is_parallelizable(calls, mode="off") is False


def test_unknown_tool_not_parallelizable():
    calls = [_call("read_file"), _call("some_new_tool_xyz")]
    assert is_parallelizable(calls, mode="on") is False


def test_empty_or_malformed_calls_safe():
    assert is_parallelizable([], mode="on") is False
    assert is_parallelizable([{"function": {}}, {"function": {}}], mode="on") is False


def test_concurrency_mode_defaults_off(monkeypatch):
    monkeypatch.delenv("JARVIS_TOOL_CONCURRENCY_MODE", raising=False)
    monkeypatch.setattr("core.runtime.settings.load_settings",
                        lambda: type("S", (), {"extra": {}})())
    assert concurrency_mode() == "off"


def test_concurrency_mode_env_wins(monkeypatch):
    monkeypatch.setenv("JARVIS_TOOL_CONCURRENCY_MODE", "on")
    assert concurrency_mode() == "on"


def test_max_concurrency_is_positive():
    assert _MAX_CONCURRENCY >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `conda run -n ai python -m pytest tests/test_tool_concurrency.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write the implementation**

```python
# core/services/tool_concurrency.py
"""Tool-concurrency policy (harness Part C).

Decides whether a round's tool calls may execute concurrently. ALLOWLIST +
ALL-OR-NOTHING: a round parallelizes only if EVERY call is a known read-only,
side-effect-free tool. Anything unlisted/new/mutating → the whole round runs
sequentially (fail-safe). Default mode is off (byte-identical to today).

This module only CLASSIFIES — it never executes. The executor
(simple_tool_executor.py) enforces the safe-invocation mechanics.
"""
from __future__ import annotations

import os

_MAX_CONCURRENCY = 6  # IO-bound reads; fixed (model-tiering the cap is a later lever)

# Curated read-only allowlist. Every entry is side-effect-free (reads/searches/
# list/status/network-GET). Writes, operator_bash*, click/type/key, mutations,
# rollbacks, and approval-gated tools are DELIBERATELY excluded.
_PARALLEL_SAFE: frozenset[str] = frozenset({
    "read_file", "read_tool_result", "read_attachment", "read_self_docs",
    "read_model_config", "read_mood", "read_self_state", "read_chronicles",
    "read_dreams", "list_dir", "find_files", "search", "search_memory",
    "search_chat_history", "search_sessions", "list_initiatives",
    "list_proposals", "list_scheduled_tasks", "heartbeat_status",
    "operator_read_file", "operator_list_dir", "operator_list_windows",
    "operator_list_processes", "operator_process_status", "operator_process_list",
    "operator_scheduled_list", "operator_browser_get_text",
    "operator_browser_get_links", "operator_browser_status",
    "operator_clipboard_read", "operator_find_image", "web_fetch", "web_search",
    "operator_webfetch", "get_weather", "get_exchange_rate", "get_news",
    "github_list_issues", "github_list_prs", "gmail_search", "gmail_list",
    "calendar_list_events", "drive_search", "docs_read", "sheets_read",
    "slides_read", "pdf_read", "note_list", "note_search", "hf_search_models",
    "hf_model_info",
})

_MODE_ENV = "JARVIS_TOOL_CONCURRENCY_MODE"
_VALID_MODES = ("off", "on")


def concurrency_mode() -> str:
    """Current mode: 'off' | 'on'. Default 'off'. Env wins over config. Self-safe."""
    env = os.environ.get(_MODE_ENV)
    if env is not None:
        v = env.strip().lower()
        if v in _VALID_MODES:
            return v
    try:
        from core.runtime.settings import load_settings
        v = str(load_settings().extra.get("tool_concurrency_mode", "off")).strip().lower()
        return v if v in _VALID_MODES else "off"
    except Exception:
        return "off"


def _call_name(tc: dict) -> str:
    fn = tc.get("function") or {}
    return str(fn.get("name") or "")


def is_parallelizable(tool_calls: list[dict], *, mode: str) -> bool:
    """True iff mode=='on' AND >=2 calls AND every call name is in the allowlist.
    All-or-nothing: any unlisted/unnamed call → False. Never raises."""
    try:
        if mode != "on":
            return False
        if not tool_calls or len(tool_calls) < 2:
            return False
        for tc in tool_calls:
            name = _call_name(tc)
            if not name or name not in _PARALLEL_SAFE:
                return False
        return True
    except Exception:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `conda run -n ai python -m pytest tests/test_tool_concurrency.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add core/services/tool_concurrency.py tests/test_tool_concurrency.py
git commit -m "feat(harness): tool-concurrency policy module (Part C)"
```

---

## Task 2 (Claude inline): Boy-Scout extract executor → `simple_tool_executor.py`

Pure relocation of `_execute_simple_tool_calls` (visible_runs.py:5315-5494), verified by the 5 existing tests that import it (`test_streaming_fault_injection`, `test_agentic_tool_cache`, `test_gates`, `test_visible_runs_loop_not_blocked`, `test_visible_runs_capability_smoke`) plus a new baseline test.

**Files:**
- Create: `core/services/simple_tool_executor.py`
- Modify: `core/services/visible_runs.py:5315-5494` (remove body, add re-export)
- Test: `tests/test_simple_tool_executor.py`

- [ ] **Step 1: Create `simple_tool_executor.py` with the function moved verbatim**

Copy the exact body of `_execute_simple_tool_calls` from `visible_runs.py:5315-5494` into the new file. Module-top imports: `import json` and `from core.eventbus.bus import event_bus`. The three names the function reads from `visible_runs`' module scope (`get_visible_run_controller`, `_MAX_CAPABILITIES_PER_TURN`) are imported **lazily inside the function** to avoid the import cycle (visible_runs imports this module at load time):

```python
# core/services/simple_tool_executor.py
"""Native tool_calls executor (extracted from visible_runs.py, Boy-Scout 2026-07-08).

Executes a round's native tool_calls via simple_tools and returns result dicts.
Re-exported from visible_runs for backward compatibility. Part C adds an optional
concurrent path for read-only rounds (see _execute_simple_tool_calls)."""
from __future__ import annotations

import json

from core.eventbus.bus import event_bus


def _execute_simple_tool_calls(
    tool_calls: list[dict],
    *,
    force: bool = False,
    run_id: str | None = None,
    session_id: str | None = None,
    user_message: str = "",
) -> list[dict[str, object]]:
    """Execute native tool_calls directly via simple_tools. Returns results.

    When *force* is True (autonomous runs), use ``execute_tool_force`` which
    bypasses the approval gate (blocked commands are still blocked).
    """
    from core.services.visible_runs import get_visible_run_controller, _MAX_CAPABILITIES_PER_TURN
    from core.tools.simple_tools import execute_tool, execute_tool_force, format_tool_result_for_model

    _exec = execute_tool_force if force else execute_tool

    results: list[dict[str, object]] = []
    controller = get_visible_run_controller(run_id) if run_id else None
    for tc in tool_calls[:_MAX_CAPABILITIES_PER_TURN]:
        # ... EXACT body from visible_runs.py:5338-5493, unchanged ...
        # (copy lines 5338 through 5493 verbatim: arg-parse, stamping, signature,
        #  dedup, cache, commit-gate, _exec, finalize, results.append)
    return results
```

(The `...` is filled by copying visible_runs.py:5338-5493 verbatim — no logic change. The only edits vs the original are: `json`/`event_bus` now module-top imports here, and the `get_visible_run_controller`/`_MAX_CAPABILITIES_PER_TURN` import moved to the top of the function body.)

- [ ] **Step 2: Replace the body in `visible_runs.py` with a re-export**

Delete lines 5315-5494 (the whole `def _execute_simple_tool_calls...return results`) and replace with:

```python
# _execute_simple_tool_calls extracted to core/services/simple_tool_executor.py
# (Boy-Scout, 2026-07-08). Re-exported for backward compatibility — existing
# callers (`_ctx_for_agentic_exec.run(_execute_simple_tool_calls, ...)`) and the
# 5 tests importing it from visible_runs keep working unchanged.
from core.services.simple_tool_executor import _execute_simple_tool_calls  # noqa: E402,F401
```

Place this import near the other late module-level imports (it must be module-level so `_execute_simple_tool_calls` resolves at the call site ~3567). Because `simple_tool_executor` only touches `visible_runs` lazily (inside the function), importing it at `visible_runs` load time does not cycle.

- [ ] **Step 3: Write a baseline behaviour test**

```python
# tests/test_simple_tool_executor.py
from core.services import simple_tool_executor as ste


def test_reexported_from_visible_runs():
    from core.services.visible_runs import _execute_simple_tool_calls as via_vr
    assert via_vr is ste._execute_simple_tool_calls


def test_basic_sequential_execution(monkeypatch):
    # No run_id → controller None → no dedup/cache state; pure pass-through.
    calls = [{"function": {"name": "read_file", "arguments": {"path": "/x"}}}]

    def fake_execute_tool(name, arguments):
        return {"status": "ok", "output": f"ran {name}"}

    monkeypatch.setattr("core.tools.simple_tools.execute_tool", fake_execute_tool)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result: str(result.get("output") or ""))
    # Neutralise the commit-gate so the tool runs.
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    out = ste._execute_simple_tool_calls(calls, force=False)
    assert len(out) == 1
    assert out[0]["tool_name"] == "read_file"
    assert out[0]["status"] == "ok"
    assert out[0]["result_text"] == "ran read_file"
```

- [ ] **Step 4: Verify — compile, import, existing + new tests**

Run: `conda run -n ai python -m compileall core/services/visible_runs.py core/services/simple_tool_executor.py -q`
Expected: no output.

Run: `conda run -n ai python -c "from core.services.visible_runs import _execute_simple_tool_calls; from core.services.simple_tool_executor import _execute_simple_tool_calls as x; print('reexport ok', _execute_simple_tool_calls is x)"`
Expected: `reexport ok True`.

Run: `conda run -n ai python -m pytest tests/test_simple_tool_executor.py tests/test_agentic_tool_cache.py tests/test_gates.py tests/test_visible_runs_capability_smoke.py tests/test_visible_runs_loop_not_blocked.py tests/test_streaming_fault_injection.py -q`
Expected: PASS (the 5 pre-existing suites confirm the relocation preserved behaviour).

- [ ] **Step 5: Commit**

```bash
git add core/services/simple_tool_executor.py core/services/visible_runs.py tests/test_simple_tool_executor.py
git commit -m "refactor(harness): Boy-Scout extract _execute_simple_tool_calls → simple_tool_executor (Part C)"
```

---

## Task 3 (Claude inline): refactor into helpers + add the parallel branch

Refactor the sequential loop into `_prepare_call`/`_finalize_call` (behaviour-preserving), then add a concurrent branch gated by `is_parallelizable`. Parallelize only `_exec`; keep dedup/cache/gate/record single-threaded; propagate ContextVars per task.

**Files:**
- Modify: `core/services/simple_tool_executor.py`
- Test: `tests/test_simple_tool_executor.py`

- [ ] **Step 1: Add the helpers + branch to `simple_tool_executor.py`**

Add module-top imports:
```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextvars import copy_context
```

Add the two helpers (they encapsulate the per-call logic, lifted verbatim from the loop body):

```python
def _prepare_call(tc, *, force, run_id, session_id, user_message, controller, round_seen):
    """Single-thread prep for one call: parse/stamp args, signature, dedup, cache,
    commit-gate. Returns ("result", result_dict) for a short-circuit (duplicate/
    cached/gate-blocked), or ("run", token) where token carries name/arguments/
    signature/soft_warn for the invoke+finalize phases. Never runs the tool."""
    fn = tc.get("function") or {}
    name = str(fn.get("name") or "")
    arguments = fn.get("arguments") or {}
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except (ValueError, TypeError):
            arguments = {}
    if not isinstance(arguments, dict):
        arguments = {}
    if not name:
        return ("skip", None)
    try:
        from core.services.in_flight_runs import mark_tool
        mark_tool(run_id or "", name)
    except Exception:
        pass
    arguments = dict(arguments)
    if session_id:
        arguments["_runtime_session_id"] = session_id
    if run_id:
        arguments["_runtime_turn_id"] = run_id
    try:
        from core.identity.workspace_context import current_user_id
        uid = current_user_id()
        if uid:
            arguments["_runtime_user_id"] = uid
    except Exception:
        pass
    if force or (controller and controller.trust_all):
        arguments["_runtime_trust_all"] = True
    signature = json.dumps({"tool_name": name, "arguments": arguments},
                           ensure_ascii=False, sort_keys=True)
    seen = (controller.seen_simple_tool_call_signatures if controller else set())
    if signature in seen or signature in round_seen:
        return ("result", {
            "tool_name": name, "arguments": arguments,
            "result": {"status": "duplicate_suppressed",
                       "message": "Skipped duplicate tool call in the same visible run."},
            "result_text": "[Duplicate tool call skipped in same visible run]",
            "status": "duplicate_suppressed"})
    try:
        from core.services.agentic_tool_cache import get_cached_result
        _cached = get_cached_result(name, arguments)
    except Exception:
        _cached = None
    if _cached:
        return ("result", {
            "tool_name": name, "arguments": arguments,
            "result": {"status": "ok", "cached": True, "stored_at": _cached.get("stored_at")},
            "result_text": str(_cached.get("result_text") or ""),
            "status": "ok", "cached": True})
    from core.services.commit_gate_arbiter import evaluate_commit_gates
    _cg = evaluate_commit_gates(name=name, arguments=arguments,
                                user_message=user_message,
                                session_id=session_id or "", run_id=run_id or "")
    if _cg.blocked:
        _gate_reason = _cg.reason or "Ukendt gate-blokering"
        _gate_type = _cg.gate_type or "decision_gate"
        try:
            event_bus.publish(f"{_gate_type}.blocked",
                              {"tool_name": name, "reason": _gate_reason[:500], "run_id": run_id})
        except Exception:
            pass
        return ("result", {
            "tool_name": name, "arguments": arguments,
            "result": {"status": "gate_blocked", "gate_type": _gate_type, "message": _gate_reason},
            "result_text": f"[{_gate_type}] {_gate_reason}", "status": "gate_blocked"})
    # Reserve the signature for within-round dedup (parallel: success unknown yet;
    # a same-round exact duplicate read is suppressed — benign for idempotent reads).
    round_seen.add(signature)
    return ("run", {"name": name, "arguments": arguments,
                    "signature": signature, "soft_warn": _cg.soft_warn})


def _finalize_call(token, raw_result, *, controller, exec_fmt):
    """Single-thread finalize for one executed call: soft-warn wrap, mark-seen on
    ok, cache-store, assemble the result dict. exec_fmt = format_tool_result_for_model."""
    name = token["name"]; arguments = token["arguments"]
    signature = token["signature"]; soft_warn = token["soft_warn"]
    result_text = exec_fmt(name, raw_result)
    if soft_warn:
        result_text = f"⚠ {soft_warn}\n\n{result_text}"
    if controller and raw_result.get("status") == "ok":
        controller.seen_simple_tool_call_signatures.add(signature)
    try:
        from core.services.agentic_tool_cache import store_result
        store_result(tool_name=name, arguments=arguments, result_text=result_text,
                     status=str(raw_result.get("status", "ok")))
    except Exception:
        pass
    return {"tool_name": name, "arguments": arguments, "result": raw_result,
            "result_text": result_text, "status": raw_result.get("status", "ok")}
```

Replace the `for tc in tool_calls[...]:` loop body in `_execute_simple_tool_calls` with a dispatcher that chooses sequential or parallel:

```python
    from core.tools.simple_tools import execute_tool, execute_tool_force, format_tool_result_for_model
    from core.services.tool_concurrency import is_parallelizable, concurrency_mode, _MAX_CONCURRENCY
    _exec = execute_tool_force if force else execute_tool

    results: list[dict[str, object]] = []
    controller = get_visible_run_controller(run_id) if run_id else None
    calls = tool_calls[:_MAX_CAPABILITIES_PER_TURN]
    round_seen: set[str] = set()

    _parallel = False
    try:
        _parallel = is_parallelizable(calls, mode=concurrency_mode())
    except Exception:
        _parallel = False

    if not _parallel:
        # ── Sequential path (default; behaviour-identical to pre-Part-C) ──
        for tc in calls:
            kind, payload = _prepare_call(
                tc, force=force, run_id=run_id, session_id=session_id,
                user_message=user_message, controller=controller, round_seen=round_seen)
            if kind == "skip":
                continue
            if kind == "result":
                results.append(payload)
                continue
            raw = _exec(payload["name"], payload["arguments"])
            results.append(_finalize_call(payload, raw, controller=controller,
                                          exec_fmt=format_tool_result_for_model))
        return results

    # ── Parallel path (read-only rounds only) ──
    # Prepare all (single-thread, in order) → plan of (idx, kind, payload).
    plan: list[tuple[int, str, object]] = []
    for idx, tc in enumerate(calls):
        kind, payload = _prepare_call(
            tc, force=force, run_id=run_id, session_id=session_id,
            user_message=user_message, controller=controller, round_seen=round_seen)
        plan.append((idx, kind, payload))
    run_items = [(idx, p) for (idx, kind, p) in plan if kind == "run"]
    raw_by_idx: dict[int, dict] = {}
    if run_items:
        with ThreadPoolExecutor(max_workers=min(_MAX_CONCURRENCY, len(run_items))) as pool:
            fut_to_idx = {}
            for idx, p in run_items:
                # Per-task ContextVar snapshot: this thread already runs inside
                # _ctx_for_agentic_exec (correct role/scope/override). copy_context()
                # per task so each worker re-enters its OWN copy — a single Context
                # cannot be .run() concurrently from multiple threads.
                ctx_i = copy_context()
                fut = pool.submit(ctx_i.run, _exec, p["name"], p["arguments"])
                fut_to_idx[fut] = idx
            for fut in as_completed(fut_to_idx):
                idx = fut_to_idx[fut]
                try:
                    raw_by_idx[idx] = fut.result()
                except Exception as exc:
                    raw_by_idx[idx] = {"status": "error", "message": str(exc)}
    # Finalize in emission order (single-thread) → deterministic result list.
    for (idx, kind, payload) in plan:
        if kind == "skip":
            continue
        if kind == "result":
            results.append(payload)
            continue
        raw = raw_by_idx.get(idx) or {"status": "error", "message": "no result"}
        results.append(_finalize_call(payload, raw, controller=controller,
                                      exec_fmt=format_tool_result_for_model))
    # Observability: how often / how wide concurrency fired.
    try:
        from core.services import central_timeseries as _cts_conc
        _cts_conc.record("tool", "concurrency", float(len(run_items)),
                         meta={"run_id": run_id, "n": len(run_items),
                               "cap": _MAX_CONCURRENCY})
    except Exception:
        pass
    return results
```

- [ ] **Step 2: Add tests (equivalence, ordering, ContextVar propagation, dedup)**

```python
# append to tests/test_simple_tool_executor.py
import contextvars
import time
from core.services import tool_concurrency


_SCOPE = contextvars.ContextVar("_test_scope", default="DEFAULT")


def _mk_calls(names):
    return [{"function": {"name": n, "arguments": {"i": i}}} for i, n in enumerate(names)]


def _patch_reads(monkeypatch, record=None, sleep_map=None):
    def fake_execute_tool(name, arguments):
        if sleep_map:
            time.sleep(sleep_map.get(arguments.get("i"), 0))
        if record is not None:
            record.append((name, arguments.get("i"), _SCOPE.get()))
        return {"status": "ok", "output": f"{name}:{arguments.get('i')}"}
    monkeypatch.setattr("core.tools.simple_tools.execute_tool", fake_execute_tool)
    monkeypatch.setattr("core.tools.simple_tools.format_tool_result_for_model",
                        lambda name, result: str(result.get("output") or ""))
    monkeypatch.setattr("core.services.commit_gate_arbiter.evaluate_commit_gates",
                        lambda **kw: type("CG", (), {"blocked": False, "soft_warn": "",
                                                     "reason": "", "gate_type": ""})())
    monkeypatch.setattr("core.services.agentic_tool_cache.get_cached_result",
                        lambda name, arguments: None)
    monkeypatch.setattr("core.services.agentic_tool_cache.store_result", lambda **kw: None)


def test_parallel_equals_sequential(monkeypatch):
    names = ["read_file", "search_memory", "list_dir"]
    _patch_reads(monkeypatch)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "off")
    seq = ste._execute_simple_tool_calls(_mk_calls(names))
    _patch_reads(monkeypatch)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    par = ste._execute_simple_tool_calls(_mk_calls(names))
    assert [r["result_text"] for r in seq] == [r["result_text"] for r in par]
    assert [r["tool_name"] for r in par] == names  # emission order preserved


def test_parallel_preserves_order_under_out_of_order_completion(monkeypatch):
    names = ["read_file", "search_memory", "list_dir"]
    # First call sleeps longest → finishes last, but must still be index 0 in output.
    _patch_reads(monkeypatch, sleep_map={0: 0.15, 1: 0.05, 2: 0.0})
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    out = ste._execute_simple_tool_calls(_mk_calls(names))
    assert [r["result_text"] for r in out] == ["read_file:0", "search_memory:1", "list_dir:2"]


def test_parallel_propagates_contextvars_to_workers(monkeypatch):
    # SECURITY-CRITICAL: mode/role/tier gating reads ContextVars inside execute_tool.
    # A raw worker thread would see DEFAULT. Each task must run in a copied context.
    record: list = []
    _patch_reads(monkeypatch, record=record)
    monkeypatch.setattr(tool_concurrency, "concurrency_mode", lambda: "on")
    token = _SCOPE.set("OWNER_SCOPE")
    try:
        ste._execute_simple_tool_calls(_mk_calls(["read_file", "search_memory"]))
    finally:
        _SCOPE.reset(token)
    observed = {scope for (_n, _i, scope) in record}
    assert observed == {"OWNER_SCOPE"}, f"worker context not propagated: {observed}"
```

- [ ] **Step 3: Run the executor tests**

Run: `conda run -n ai python -m pytest tests/test_simple_tool_executor.py -q`
Expected: PASS (all).

- [ ] **Step 4: Re-run the pre-existing executor suites (no regression)**

Run: `conda run -n ai python -m pytest tests/test_agentic_tool_cache.py tests/test_gates.py tests/test_visible_runs_capability_smoke.py tests/test_visible_runs_loop_not_blocked.py tests/test_streaming_fault_injection.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add core/services/simple_tool_executor.py tests/test_simple_tool_executor.py
git commit -m "feat(harness): concurrent read-only tool execution, ctx-safe, default off (Part C)"
```

---

## Task 4: full-suite gate + deploy

**Files:** none (verification + deploy)

- [ ] **Step 1: Module tests together**

Run: `conda run -n ai python -m pytest tests/test_tool_concurrency.py tests/test_simple_tool_executor.py -q`
Expected: PASS.

- [ ] **Step 2: Full-suite gate (~20 min)**

Run: `conda run -n ai python -m pytest -q -p no:cacheprovider --timeout=45 --timeout-method=signal`
Expected: PASS. Known rotating isolation flakes (re-run alone to confirm): meta_learning, forgetting_engine, subagent_ecology, heartbeat_self_knowledge, workspace_bootstrap, causal_quality, db_user_temperature.

- [ ] **Step 3: Push**

```bash
git push
```
Expected: pre-push smoke passes (allow ≥300 s).

- [ ] **Step 4: Deploy on container (ff-pull + verify HEAD + restart both)**

```bash
R=/media/projects/jarvis-v2
ssh bs@10.0.0.39 "git -C $R pull --ff-only && git -C $R rev-parse --short HEAD"
```
Confirm HEAD matches the pushed commit. If the container has local commits blocking ff-only, MERGE (never overwrite/rebase), then re-verify.

```bash
ssh bs@10.0.0.39 'sudo systemctl restart jarvis-runtime jarvis-api && sleep 4 && systemctl is-active jarvis-runtime jarvis-api'
```
Expected: `active` / `active`.

- [ ] **Step 5: Verify live (default off → zero behaviour change)**

```bash
ssh bs@10.0.0.39 'PYTHONPATH=/media/projects/jarvis-v2 /opt/conda/envs/ai/bin/python -c "from core.services.tool_concurrency import concurrency_mode; from core.services.simple_tool_executor import _execute_simple_tool_calls; from core.services.visible_runs import _execute_simple_tool_calls as x; print(\"mode:\", concurrency_mode(), \"| reexport ok:\", _execute_simple_tool_calls is x)"'
```
Expected: `mode: off | reexport ok: True`. Send one visible chat turn; confirm it still answers normally. To later enable: set `tool_concurrency_mode=on` in runtime config (or `JARVIS_TOOL_CONCURRENCY_MODE=on`), watch `jc series tool:concurrency`.

- [ ] **Step 6: Update memory** `project_harness_refactor_spec` with Part C shipped.

---

## Self-Review

**Spec coverage:** allowlist + all-or-nothing (Task 1 `is_parallelizable` + tests) ✓; kill-switch default off (Task 1 `concurrency_mode` + Task 3 dispatcher) ✓; Boy-Scout extraction (Task 2) ✓; parallelize-invocation-serialize-bookkeeping (Task 3 `_prepare_call`/`_finalize_call` + branch) ✓; deterministic ordering (Task 3 finalize-in-plan-order + test) ✓; **ContextVar propagation** (Task 3 per-task `copy_context()` + security-critical test) ✓; dedup single-threaded + within-round (Task 3 `round_seen`) ✓; fixed cap 6 / no tiering (Task 1 `_MAX_CONCURRENCY`) ✓; observability nerve — NOTE: the spec mentions a `tool/concurrency` nerve; add it as a one-line `central_timeseries.record("tool","concurrency",len(run_items),...)` at the end of the parallel branch in Task 3 Step 1 (already fits, folded into the branch).

**Placeholder scan:** the only `...` is Task 2 Step 1's "copy verbatim from named lines" — that is an explicit copy instruction with exact source line numbers, not a vague placeholder. All other code is complete.

**Type consistency:** `_prepare_call(...) -> (kind, payload)` with kind in {"skip","result","run"} used identically in both branches; `_finalize_call(token, raw_result, *, controller, exec_fmt)` signature consistent; `is_parallelizable(calls, *, mode)` / `concurrency_mode()` / `_MAX_CONCURRENCY` match Task 1 definitions; token keys (`name`/`arguments`/`signature`/`soft_warn`) consistent between `_prepare_call` and `_finalize_call`.
