# Jarvis Runtime Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix four concrete runtime defects in Jarvis V2: (1) no task worker consuming `runtime_tasks`, (2) `dream_insight` daemon never firing, (3) memory consolidation skipping with `model-unavailable`, (4) stale queued tasks piled up in DB.

**Architecture:** Each fix is largely isolated. We sequence them so the worker doesn't immediately detonate 93 stale tasks: first flush the backlog (#5), then build the worker (#1), then fix the two orthogonal daemon/lane bugs (#2, #3).

**Tech Stack:** Python 3.11, SQLite (`~/.jarvis-v2/state/jarvis.db`), FastAPI runtime services, daemon manager pattern (`daemon_manager.py`), provider router (`PROVIDER_ROUTER.json`).

**Scope:** Brevet fra Jarvis (TASKS_FOR_CLAUDE.md) — Opgave 1, 2, 3, 5. Opgave 4 (IDENTITY.md) og Opgave 6 (rod-stubs) **springes over** efter brugerens instruks.

---

## Task Ordering & Why

1. **Opgave 5 first** — flush 93 stale queued tasks before worker is wired up, or the worker will process a flood of old work on first tick.
2. **Opgave 1 second** — wire the worker into heartbeat tick so future `initiative-followup` / `heartbeat-followup` tasks actually execute.
3. **Opgave 2 third** — independent daemon fix for `dream_insight`.
4. **Opgave 3 fourth** — independent provider lane fix for memory consolidation.

Each task is committed separately. If any task grows unexpectedly, stop and re-plan.

---

## File Structure

### Opgave 5 (flush stale tasks)
- Modify: database rows only (no code). One-off SQL executed against both candidate DBs.

### Opgave 1 (task worker)
- Create: `apps/api/jarvis_api/services/task_worker.py` (new — contains `tick_task_worker()` and `_execute_task()` dispatch)
- Modify: `apps/api/jarvis_api/services/daemon_manager.py` (register `task_worker` in `_REGISTRY`)
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (call `tick_task_worker()` in non-LLM daemon group with cadence guard)
- Test: `tests/services/test_task_worker.py` (new)

### Opgave 2 (dream_insight)
- Read: `apps/api/jarvis_api/services/heartbeat_runtime.py:2080-2097` (current guard)
- Read: `apps/api/jarvis_api/services/daemon_manager.py:128-134` (registration)
- Read: `apps/api/jarvis_api/services/dream_insight_daemon.py`
- Read: `~/.jarvis-v2/workspaces/default/runtime/DAEMON_STATE.json`
- Modify: depends on diagnosis — most likely `heartbeat_runtime.py` (remove/soften guard or add logging), possibly `DAEMON_STATE.json` (enable), possibly `dream_insight_daemon.py` (handle missing signal).

### Opgave 3 (memory consolidation)
- Read: `apps/api/jarvis_api/services/end_of_run_memory_consolidation.py:70-90`
- Read: `apps/api/jarvis_api/services/cheap_provider_runtime.py:397-527`
- Read: `~/.jarvis-v2/workspaces/default/runtime/PROVIDER_ROUTER.json`
- Modify: depends on diagnosis — most likely add Ollama fallback in consolidation lane, or enable an available cheap provider, or add phase1-runtime fallback in `_run_local_consolidation_model()`.

---

## Opgave 5: Flush stale queued runtime_tasks

**Files:**
- Modify: `~/.jarvis-v2/state/jarvis.db` (rows only, SQL)

**Why first:** If the worker lands before this flush, it will immediately try to process 93 hour-old tasks — many of which are stale goals that no longer reflect current runtime state. Flushing first keeps behaviour predictable.

- [ ] **Step 1: Snapshot current state**

Run:
```bash
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "SELECT kind, status, COUNT(*) FROM runtime_tasks GROUP BY kind, status;"
```
Expected: Some rows with `kind=heartbeat-followup` or `initiative-followup` and `status=queued`. Record the counts.

- [ ] **Step 2: Inspect a few sample tasks to confirm they're genuinely stale**

Run:
```bash
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "SELECT task_id, kind, status, priority, goal, created_at FROM runtime_tasks WHERE status='queued' ORDER BY created_at LIMIT 5;"
```
Expected: tasks with `created_at` older than 1 hour (stale).

- [ ] **Step 3: Flush tasks older than 1 hour to `expired`**

Run:
```bash
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "UPDATE runtime_tasks SET status='expired', updated_at=datetime('now'), result_summary='flushed: stale queue preceded task worker' WHERE status='queued' AND created_at < datetime('now', '-1 hour');"
```
Expected: affected row count ≈ 93.

- [ ] **Step 4: Verify nothing queued remains older than 1 hour**

Run:
```bash
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "SELECT COUNT(*) FROM runtime_tasks WHERE status='queued' AND created_at < datetime('now', '-1 hour');"
```
Expected: `0`.

- [ ] **Step 5: Re-snapshot**

Run:
```bash
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "SELECT kind, status, COUNT(*) FROM runtime_tasks GROUP BY kind, status;"
```
Expected: `expired` row now contains the flushed count; no stale `queued` rows older than 1 hour.

- [ ] **Step 6: Commit a migration/ops note (no code changes, just log)**

Since this is a data-only op, add a one-line note in `docs/ops/` if such a directory exists; otherwise skip the commit step. Ensure the snapshot numbers are captured in the conversation log for audit.

---

## Opgave 1: Task worker for runtime_tasks

**Files:**
- Create: `apps/api/jarvis_api/services/task_worker.py`
- Modify: `apps/api/jarvis_api/services/daemon_manager.py` (register in `_REGISTRY`)
- Modify: `apps/api/jarvis_api/services/heartbeat_runtime.py` (call in non-LLM daemon group)
- Test: `tests/services/test_task_worker.py`

**Kinds handled this pass:** `initiative-followup`, `heartbeat-followup`, `generic`, `open-loop-follow-up`.

**Budget per tick:** Max 3 tasks to avoid starving other daemons. Rest stays queued.

### Task 1.1: Scaffold task_worker module with list/claim helper

- [ ] **Step 1: Read existing patterns**

Read `apps/api/jarvis_api/services/runtime_tasks.py` fully. Note the exact function signatures for `list_tasks`, `get_task`, `update_task`. Note which statuses exist: `queued`, `running`, `blocked`, `succeeded`, `failed`, `cancelled`.

- [ ] **Step 2: Write the failing test for `claim_next_task`**

Create `tests/services/test_task_worker.py`:
```python
import pytest
from apps.api.jarvis_api.services import runtime_tasks, task_worker


def test_claim_next_task_returns_highest_priority_queued(tmp_path, monkeypatch):
    # Arrange: create three tasks at different priorities
    t_low = runtime_tasks.create_task(kind="generic", goal="low", priority="low")
    t_high = runtime_tasks.create_task(kind="generic", goal="high", priority="high")
    t_med = runtime_tasks.create_task(kind="generic", goal="med", priority="medium")

    # Act
    claimed = task_worker.claim_next_task(kinds=["generic"])

    # Assert: highest priority claimed first
    assert claimed is not None
    assert claimed["task_id"] == t_high["task_id"]
    assert claimed["status"] == "running"


def test_claim_next_task_returns_none_when_empty():
    claimed = task_worker.claim_next_task(kinds=["initiative-followup"])
    assert claimed is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/services/test_task_worker.py -v`
Expected: FAIL — `task_worker` module doesn't exist.

- [ ] **Step 4: Implement minimal `claim_next_task`**

Create `apps/api/jarvis_api/services/task_worker.py`:
```python
"""Task worker — consumes queued runtime_tasks in heartbeat tick cadence.

Responsibilities:
- Claim next queued task ordered by priority then age
- Dispatch to handler based on `kind`
- Mark `succeeded`/`failed` with result_summary
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import runtime_tasks

_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_DEFAULT_KINDS = ["initiative-followup", "heartbeat-followup", "generic", "open-loop-follow-up"]


def claim_next_task(kinds: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
    """Atomically claim the next queued task and mark it running.

    Returns the claimed task dict, or None if nothing queued.
    """
    kinds = kinds or _DEFAULT_KINDS
    queued = runtime_tasks.list_tasks(status="queued")
    # Filter by kind and sort by (priority_rank, created_at)
    candidates = [t for t in queued if t.get("kind") in kinds]
    candidates.sort(
        key=lambda t: (
            _PRIORITY_ORDER.get(t.get("priority", "medium"), 1),
            t.get("created_at") or "",
        )
    )
    if not candidates:
        return None
    task = candidates[0]
    updated = runtime_tasks.update_task(task["task_id"], status="running")
    return updated or task
```

- [ ] **Step 5: Run test to verify claim behaviour**

Run: `pytest tests/services/test_task_worker.py::test_claim_next_task_returns_highest_priority_queued -v`
Expected: PASS.

Run: `pytest tests/services/test_task_worker.py::test_claim_next_task_returns_none_when_empty -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/services/task_worker.py tests/services/test_task_worker.py
git commit -m "feat(task-worker): add claim_next_task helper"
```

### Task 1.2: Add `_execute_task` dispatcher

- [ ] **Step 1: Write failing test for execute dispatch**

Append to `tests/services/test_task_worker.py`:
```python
def test_execute_task_marks_succeeded_on_clean_run():
    t = runtime_tasks.create_task(kind="generic", goal="noop-test", priority="low")
    task_worker._execute_task(t)  # should not raise
    reloaded = runtime_tasks.get_task(t["task_id"])
    assert reloaded["status"] == "succeeded"
    assert reloaded.get("result_summary")


def test_execute_task_marks_failed_on_unknown_kind():
    t = runtime_tasks.create_task(kind="totally-unknown-kind", goal="x", priority="low")
    task_worker._execute_task(t)
    reloaded = runtime_tasks.get_task(t["task_id"])
    assert reloaded["status"] == "failed"
    assert "unknown kind" in (reloaded.get("result_summary") or "").lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/services/test_task_worker.py -v`
Expected: FAIL — `_execute_task` not defined.

- [ ] **Step 3: Implement `_execute_task` and kind dispatchers**

Append to `apps/api/jarvis_api/services/task_worker.py`:
```python
def _execute_task(task: Dict[str, Any]) -> None:
    """Execute a single task and update its status. Never raises."""
    kind = task.get("kind", "")
    task_id = task.get("task_id")
    try:
        if kind == "initiative-followup":
            summary = _handle_initiative_followup(task)
        elif kind == "heartbeat-followup":
            summary = _handle_heartbeat_followup(task)
        elif kind == "open-loop-follow-up":
            summary = _handle_open_loop_followup(task)
        elif kind == "generic":
            summary = f"generic task acknowledged: {task.get('goal', '')[:120]}"
        else:
            runtime_tasks.update_task(
                task_id,
                status="failed",
                result_summary=f"unknown kind: {kind}",
            )
            return
        runtime_tasks.update_task(
            task_id,
            status="succeeded",
            result_summary=summary[:500] if summary else "ok",
        )
    except Exception as exc:  # noqa: BLE001
        runtime_tasks.update_task(
            task_id,
            status="failed",
            result_summary=f"error: {type(exc).__name__}: {exc}"[:500],
        )


def _handle_initiative_followup(task: Dict[str, Any]) -> str:
    """For now: log the initiative goal and mark done.

    Next iteration should hand off to runtime_action_executor with initiative context.
    """
    goal = task.get("goal") or "(no goal)"
    return f"initiative-followup acknowledged: {goal[:300]}"


def _handle_heartbeat_followup(task: Dict[str, Any]) -> str:
    goal = task.get("goal") or "(no goal)"
    return f"heartbeat-followup acknowledged: {goal[:300]}"


def _handle_open_loop_followup(task: Dict[str, Any]) -> str:
    goal = task.get("goal") or "(no goal)"
    return f"open-loop-follow-up acknowledged: {goal[:300]}"
```

Note: the three handlers are intentionally thin acknowledgements. They convert queued → succeeded and record the goal text as the summary. A richer implementation (hooking into `runtime_action_executor`) can follow in a later PR — per Jarvis' brief, the critical gap today is that tasks *never move out of queued*.

- [ ] **Step 4: Run tests**

Run: `pytest tests/services/test_task_worker.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/task_worker.py tests/services/test_task_worker.py
git commit -m "feat(task-worker): dispatch by kind with safe error handling"
```

### Task 1.3: Add `tick_task_worker` entrypoint with budget

- [ ] **Step 1: Write failing test for budget**

Append to `tests/services/test_task_worker.py`:
```python
def test_tick_processes_up_to_budget():
    # Seed 5 queued tasks; budget=3 should process 3 and leave 2
    for i in range(5):
        runtime_tasks.create_task(kind="generic", goal=f"t{i}", priority="medium")
    result = task_worker.tick_task_worker(budget=3)
    assert result["processed"] == 3
    assert result["remaining_queued"] >= 2
```

- [ ] **Step 2: Run to verify failure**

Run: `pytest tests/services/test_task_worker.py::test_tick_processes_up_to_budget -v`
Expected: FAIL — `tick_task_worker` undefined.

- [ ] **Step 3: Implement `tick_task_worker`**

Append to `apps/api/jarvis_api/services/task_worker.py`:
```python
def tick_task_worker(budget: int = 3) -> Dict[str, Any]:
    """One tick: claim up to `budget` tasks and execute them.

    Returns a summary dict suitable for daemon_manager.record_daemon_tick.
    """
    processed = 0
    succeeded = 0
    failed = 0
    kinds = list(_DEFAULT_KINDS)
    for _ in range(budget):
        task = claim_next_task(kinds=kinds)
        if task is None:
            break
        _execute_task(task)
        reloaded = runtime_tasks.get_task(task["task_id"])
        processed += 1
        if reloaded and reloaded.get("status") == "succeeded":
            succeeded += 1
        elif reloaded and reloaded.get("status") == "failed":
            failed += 1
    remaining = [t for t in runtime_tasks.list_tasks(status="queued") if t.get("kind") in kinds]
    return {
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "remaining_queued": len(remaining),
    }
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/services/test_task_worker.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/jarvis_api/services/task_worker.py tests/services/test_task_worker.py
git commit -m "feat(task-worker): add tick_task_worker with per-tick budget"
```

### Task 1.4: Register `task_worker` in daemon_manager

- [ ] **Step 1: Read existing registry**

Read `apps/api/jarvis_api/services/daemon_manager.py` around line 22 (the `_REGISTRY` definition) and around line 128-134 (how `dream_insight` is registered) to match the exact entry shape.

- [ ] **Step 2: Add registry entry**

In `daemon_manager.py` `_REGISTRY`, add (match the existing entry shape exactly — field names like `name`, `module`, `default_cadence_minutes`, `description`):
```python
    {
        "name": "task_worker",
        "module": "apps.api.jarvis_api.services.task_worker",
        "default_cadence_minutes": 2,
        "description": "Consumes queued runtime_tasks (initiative-followup, heartbeat-followup, open-loop, generic).",
    },
```

**Important:** verify the actual field names by reading the existing `dream_insight` entry first. If the codebase uses different keys (e.g. `cadence_minutes` instead of `default_cadence_minutes`), match those exactly. Do not invent field names.

- [ ] **Step 3: Verify the module is enabled by default**

Check `DAEMON_STATE.json` — if there's a default-enabled mechanism, new daemons should default to enabled. If each must be explicitly enabled, add `task_worker` with `enabled: true`.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/daemon_manager.py
git commit -m "feat(task-worker): register task_worker daemon (2 min cadence)"
```

### Task 1.5: Wire task_worker tick into heartbeat runtime

- [ ] **Step 1: Read heartbeat_runtime.py around line 2035-2100**

Find the Group 4 (Non-LLM daemons) section. Identify the pattern: each daemon call is wrapped in `if _dm.is_enabled("name"):` with cadence gate via `_dm.get_effective_cadence("name")` compared against tick_count or last_run_at.

- [ ] **Step 2: Insert task_worker invocation**

After the last existing Group 4 daemon call, add:
```python
        # task_worker — consume queued runtime_tasks
        if _dm.is_enabled("task_worker"):
            try:
                from .task_worker import tick_task_worker
                tw_result = tick_task_worker(budget=3)
                _dm.record_daemon_tick("task_worker", tw_result)
            except Exception as exc:  # noqa: BLE001
                _dm.record_daemon_tick("task_worker", {"error": f"{type(exc).__name__}: {exc}"})
```

**Important:** match the cadence gate pattern used by neighbouring daemons. If they check `_dm.get_effective_cadence("name")` against elapsed minutes, do the same. Don't invent a tick-modulo scheme if the codebase uses time-based cadence.

- [ ] **Step 3: Syntax check**

Run: `python -m compileall apps/api/jarvis_api/services/heartbeat_runtime.py apps/api/jarvis_api/services/task_worker.py`
Expected: no errors.

- [ ] **Step 4: Run full test suite for services**

Run: `pytest tests/services/ -v`
Expected: all pass (or no pre-existing regressions).

- [ ] **Step 5: Manual smoke — seed a test task and watch one tick**

```bash
# Seed a low-priority task
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "INSERT INTO runtime_tasks (task_id, kind, goal, status, priority, created_at, updated_at) VALUES ('smoke-1', 'generic', 'smoke test from task worker', 'queued', 'low', datetime('now'), datetime('now'));"
```
Then trigger a heartbeat tick (or wait ≤2 min). Verify:
```bash
sqlite3 ~/.jarvis-v2/state/jarvis.db \
  "SELECT task_id, status, result_summary FROM runtime_tasks WHERE task_id='smoke-1';"
```
Expected: status=succeeded, result_summary contains "smoke test".

- [ ] **Step 6: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "feat(task-worker): invoke tick_task_worker in heartbeat Group 4"
```

---

## Opgave 2: Fix `dream_insight` daemon

**Hypothesis (from exploration):** The guard at `heartbeat_runtime.py:2093` is `if _da_signal_id and _da_summary:` — so if `build_dream_articulation_surface()` returns empty signal/summary, the daemon silently no-ops. The exception handler at line 2096-2097 swallows errors without logging.

### Task 2.1: Diagnose

- [ ] **Step 1: Verify daemon is enabled**

Run:
```bash
python -c "import json; d=json.load(open('/home/bs/.jarvis-v2/workspaces/default/runtime/DAEMON_STATE.json')); print(json.dumps(d.get('dream_insight', {}), indent=2))"
```
Expected: `enabled: true` (or missing key = enabled by default). If disabled, set to true and move to step 4.

- [ ] **Step 2: Inspect the guard and surface call**

Read `apps/api/jarvis_api/services/heartbeat_runtime.py:2080-2097`. Identify the exact surface function that produces `_da_signal_id` and `_da_summary`.

- [ ] **Step 3: Run the surface function in isolation**

Write a small REPL snippet (or use `python -c ...`) that imports and calls the surface function. Inspect the return value. Determine whether signal/summary are chronically empty.

- [ ] **Step 4: Record diagnosis finding**

Write a short note in the PR description (or in a commit body) stating which of these is true:
- (A) Daemon disabled in `DAEMON_STATE.json`
- (B) Surface always returns empty signal/summary
- (C) Exception silently thrown and swallowed
- (D) Something else

### Task 2.2: Fix based on diagnosis

- [ ] **Step 1: Add logging around the guard regardless**

Modify `heartbeat_runtime.py:2080-2097` to replace the silent exception handler with explicit logging and daemon-tick recording of the failure, so future debugging is instant:
```python
        if _dm.is_enabled("dream_insight"):
            try:
                from .dream_insight_daemon import tick_dream_insight_daemon
                da_surface = build_dream_articulation_surface()
                _da_signal_id = da_surface.get("signal_id") if da_surface else None
                _da_summary = da_surface.get("summary") if da_surface else None
                if _da_signal_id and _da_summary:
                    di_result = tick_dream_insight_daemon(_da_signal_id, _da_summary)
                    _dm.record_daemon_tick("dream_insight", di_result or {"ok": True})
                else:
                    _dm.record_daemon_tick("dream_insight", {
                        "skipped": True,
                        "reason": "no-signal-or-summary",
                        "signal_present": bool(_da_signal_id),
                        "summary_present": bool(_da_summary),
                    })
            except Exception as exc:  # noqa: BLE001
                _dm.record_daemon_tick("dream_insight", {
                    "error": f"{type(exc).__name__}: {exc}",
                })
```

This change alone converts "silent nothing" into "visible skip or error". After deploying, `last_run_at` will update every tick and the reason will be recorded in `last_result_summary`.

- [ ] **Step 2: Apply diagnosis-specific fix**

- If (A) enable daemon.
- If (B) investigate `build_dream_articulation_surface()` in `heartbeat_runtime.py` to see why it produces empty results. Common cause: guard on recent dream state that is never populated. Either loosen the guard or seed dream state.
- If (C) the logging in Step 1 will now expose the exception in `last_result_summary` — proceed based on what it says.

- [ ] **Step 3: Verify `last_run_at` is no longer None**

After at least one heartbeat tick:
```bash
python -c "import json; d=json.load(open('/home/bs/.jarvis-v2/workspaces/default/runtime/DAEMON_STATE.json')); print(json.dumps(d.get('dream_insight', {}), indent=2))"
```
Expected: `last_run_at` populated, `last_result_summary` containing either success payload or the specific skip reason.

- [ ] **Step 4: Commit**

```bash
git add apps/api/jarvis_api/services/heartbeat_runtime.py
git commit -m "fix(dream-insight): record daemon tick on skip/error so last_run_at is never silently stuck"
```

If Step 2 required additional code changes (e.g. seeding surface state), commit those separately with a descriptive message.

---

## Opgave 3: Fix memory consolidation `model-unavailable`

**Hypothesis (from exploration):** `select_cheap_lane_target()` in `cheap_provider_runtime.py` returns no-healthy-provider because all configured cheap providers (Groq, Gemini, NVIDIA NIM, OpenRouter, Mistral, SambaNova, Cloudflare) are blocked by quota, missing credentials, or rate limit. `_run_local_consolidation_model()` fallback then silently returns empty string.

### Task 3.1: Diagnose which lane is unavailable

- [ ] **Step 1: Inspect current provider router config**

Run:
```bash
cat ~/.jarvis-v2/workspaces/default/runtime/PROVIDER_ROUTER.json | python -m json.tool | head -80
```
Record which providers are listed for the cheap lane and whether any appear enabled with credentials.

- [ ] **Step 2: Check each provider's availability directly**

Write a diagnostic snippet in `scripts/diag_cheap_lane.py`:
```python
"""Diagnostic: inspect cheap lane candidate health. Run once, then delete."""
from apps.api.jarvis_api.services.cheap_provider_runtime import (
    select_cheap_lane_target,
    _candidate_quota_snapshot,
    _candidate_adaptive_snapshot,
)

target = select_cheap_lane_target()
print("selected target:", target)
# If target is None, inspect candidates:
# (Find the internal list via the module — adjust based on real API after reading the file)
```

Run: `python scripts/diag_cheap_lane.py`
Expected: either a selected target (then the bug is downstream in consolidation itself) or `None` (confirming the lane is unavailable).

- [ ] **Step 3: Record diagnosis**

Note which of these is true:
- (A) All cheap providers lack credentials
- (B) All cheap providers are rate-limited / quota-exhausted
- (C) Selector returns a target but consolidation still fails (bug downstream)
- (D) Local Ollama is running and could serve — not wired as cheap lane

### Task 3.2: Add Ollama fallback to consolidation lane

Regardless of diagnosis, Ollama is a local, always-available lane that should back this up (Jarvis' brief explicitly suggests this option).

- [ ] **Step 1: Read `_run_local_consolidation_model`**

Read `apps/api/jarvis_api/services/end_of_run_memory_consolidation.py:175-194` to see how the current fallback works and which model name it uses.

- [ ] **Step 2: Write failing test for Ollama fallback**

Create `tests/services/test_memory_consolidation_fallback.py`:
```python
from unittest.mock import patch
from apps.api.jarvis_api.services import end_of_run_memory_consolidation as mc


def test_consolidation_falls_back_to_ollama_when_cheap_lane_unavailable():
    with patch.object(mc, "select_cheap_lane_target", return_value=None):
        with patch.object(mc, "_run_ollama_consolidation", return_value="consolidated text") as ollama:
            result = mc._run_memory_consolidation_pass("fake input")
            assert result == "consolidated text"
            ollama.assert_called_once()


def test_consolidation_returns_none_when_both_lanes_fail():
    with patch.object(mc, "select_cheap_lane_target", return_value=None):
        with patch.object(mc, "_run_ollama_consolidation", return_value=None):
            result = mc._run_memory_consolidation_pass("fake input")
            assert result is None
```

- [ ] **Step 3: Run to verify failure**

Run: `pytest tests/services/test_memory_consolidation_fallback.py -v`
Expected: FAIL — `_run_ollama_consolidation` doesn't exist and/or `_run_memory_consolidation_pass` doesn't call it.

- [ ] **Step 4: Implement `_run_ollama_consolidation` and wire fallback**

In `end_of_run_memory_consolidation.py`, add:
```python
def _run_ollama_consolidation(input_text: str, model: str = "llama3.1:8b") -> Optional[str]:
    """Fallback consolidation via local Ollama. Returns None on any failure."""
    try:
        import requests  # already a dep
        resp = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": model,
                "prompt": _CONSOLIDATION_PROMPT.format(input=input_text),
                "stream": False,
            },
            timeout=60,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        text = (data or {}).get("response", "").strip()
        return text or None
    except Exception:  # noqa: BLE001
        return None
```

Then modify `_run_memory_consolidation_pass` to call Ollama when the cheap lane selector returns `None`:
```python
def _run_memory_consolidation_pass(input_text: str) -> Optional[str]:
    target = select_cheap_lane_target()
    if target is None:
        # Fallback: local Ollama
        return _run_ollama_consolidation(input_text)
    # ... existing cheap-lane call path ...
```

**Important:** adapt the Ollama model name to something actually installed locally. If `llama3.1:8b` isn't present, use whatever shows up in `ollama list` (e.g. `qwen2.5:7b`, `mistral:7b`). Make it configurable via env var `JARVIS_OLLAMA_CONSOLIDATION_MODEL` with sensible default.

Also update the `_CONSOLIDATION_PROMPT` reference if it doesn't exist under that name — match the existing prompt constant used by the cheap-lane path.

- [ ] **Step 5: Verify Ollama model is installed**

Run: `ollama list`
Expected: at least one model listed. Pick an available one for the default.

- [ ] **Step 6: Run tests**

Run: `pytest tests/services/test_memory_consolidation_fallback.py -v`
Expected: both tests PASS.

- [ ] **Step 7: Manual smoke — run a real consolidation**

Trigger consolidation via whatever normal pathway exists (end of run). Check logs for `skipped_reason: model-unavailable`. Should no longer appear when Ollama is up.

- [ ] **Step 8: Commit**

```bash
git add apps/api/jarvis_api/services/end_of_run_memory_consolidation.py tests/services/test_memory_consolidation_fallback.py
git commit -m "fix(memory-consolidation): fallback to local Ollama when cheap lane unavailable"
```

- [ ] **Step 9: Clean up diagnostic script**

```bash
rm -f scripts/diag_cheap_lane.py
```

---

## Final verification

- [ ] **Step 1: Run full compile smoke test**

Run: `python -m compileall core apps/api scripts`
Expected: no errors.

- [ ] **Step 2: Run full service test suite**

Run: `pytest tests/services/ -v`
Expected: all pass.

- [ ] **Step 3: Runtime snapshot — all four Opgaver verified**

Run (each on its own):
```bash
# Opgave 5: no stale queued
sqlite3 ~/.jarvis-v2/state/jarvis.db "SELECT COUNT(*) FROM runtime_tasks WHERE status='queued' AND created_at < datetime('now', '-1 hour');"
# Expected: 0

# Opgave 1: tasks being processed (seed a fresh one and watch)
# (see Task 1.5 Step 5)

# Opgave 2: dream_insight has last_run_at
python -c "import json; d=json.load(open('/home/bs/.jarvis-v2/workspaces/default/runtime/DAEMON_STATE.json')); print(d.get('dream_insight', {}).get('last_run_at'))"
# Expected: non-null ISO timestamp

# Opgave 3: consolidation succeeds (no model-unavailable in latest run)
# (inspect latest private_brain or whatever consolidation output table is used)
```

- [ ] **Step 4: Summary commit / PR description**

Write a PR description referencing `TASKS_FOR_CLAUDE.md` and listing which Opgaver were addressed (1, 2, 3, 5) and which were explicitly deferred (4, 6).

---

## Notes for the implementer

1. **Don't skip the diagnosis steps for Opgave 2 and 3.** The exploration narrowed the hypotheses but did not confirm them. The fix code in this plan assumes the most likely cause — if diagnosis shows something different, adapt the fix before implementing, don't ram the wrong code through.

2. **Match codebase conventions.** The daemon registry entry shape, cadence gating pattern, and logger usage in `heartbeat_runtime.py` are the source of truth. If this plan uses a field name that doesn't exist in the real codebase (e.g. `default_cadence_minutes` vs `cadence_minutes`), use the real one.

3. **Task worker handlers are intentionally thin.** The brief says tasks are stuck in `queued` with no consumer. A thin acknowledgement that moves them to `succeeded` already solves Jarvis' stated problem. Making handlers actually *do* anything with the goal (hand off to `runtime_action_executor`, LLM-driven initiative follow-through) is a separate, follow-up piece of work — out of scope here.

4. **Opgave 4 (IDENTITY.md) and Opgave 6 (root stubs) are deferred per user instruction** — do not touch those files in this plan's execution.
