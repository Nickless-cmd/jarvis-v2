# Visible Task Terminal Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make recoverable visible-run endings checkpoint, notify, and continue instead of silently completing or cutting off.

**Architecture:** A pure terminal-policy module classifies run-segment outcomes. Existing runtime, detached-run, and SSE layers consume that decision and carry its state without independently inventing success. DeepSeek DSML normalization supplies pending-tool-intent evidence to the policy.

**Tech Stack:** Python 3.11, FastAPI SSE, pytest, SQLite-backed Jarvis runtime.

**Spec:** `docs/superpowers/specs/2026-09-17-visible-task-terminal-recovery-design.md`

## Global Constraints

- `message_stop` closes a stream segment, not the user task.
- Explicit user cancellation and safety approval boundaries remain authoritative.
- Recovery chains are bounded and never fabricate user consent.
- Only focused affected tests are run; the full suite is not required.
- Changes to `core/services/visible_runs.py` obey the Boy Scout extraction rule.

---

### Task 1: Terminal Policy and DeepSeek Intent

**Files:**
- Create: `core/services/visible_terminal_policy.py`
- Modify: `core/services/cheap_provider_runtime_adapters.py`
- Modify: `core/services/visible_followup_adapters.py`
- Test: `tests/test_visible_terminal_policy.py`
- Test: `tests/test_cheap_provider_runtime.py`

**Interfaces:**
- Produces: `classify_terminal(TerminalEvidence) -> TerminalDecision`
- Produces: DSML normalization/detection that recognizes both provider dialects.

- [x] Write failing tests for clean completion, forced-final pending intent, budget, shutdown, provider failure, cancellation, and both DSML wrappers.
- [x] Run those tests and confirm failures are caused by missing policy/dialect support.
- [x] Implement the pure classifier and DSML dialect support.
- [x] Re-run focused tests to green.

### Task 2: Runtime Recovery Integration

**Files:**
- Create: `core/services/visible_run_terminal_recovery.py`
- Modify: `core/services/visible_runs.py`
- Modify: `core/services/auto_continuation.py`
- Modify: `core/services/visible_runs_sections/detached_run.py`
- Test: `tests/test_loop_stop_reasons.py`
- Test: `tests/test_auto_continuation.py`
- Test: `tests/test_auto_continuation_e2e.py`

**Interfaces:**
- Consumes: `TerminalDecision` from Task 1.
- Produces: checkpoint/recovery event payload and continuation eligibility for every non-clean loop exit.

- [x] Write failing tests showing forced finalization and all recoverable loop exits cannot remain `completed`.
- [x] Run tests and confirm the old behavior fails them.
- [x] Extract terminal handling from the oversized visible-runs module into the recovery module.
- [x] Route loop exits through the classifier, persist the decision, and broaden bounded continuation beyond exact `budget-opbrugt`.
- [x] Re-run focused tests to green.

### Task 3: Truthful Stream and Chat Notification

**Files:**
- Modify: `core/services/visible_runs_sse_v2.py`
- Modify: `core/services/run_event_log.py`
- Modify: `core/services/visible_runs_sections/detached_run.py`
- Test: `tests/test_visible_runs_sse_v2.py`
- Test: `tests/test_relay_terminal_frame.py`
- Test: `tests/test_detached_run_tavs_sluger.py`

**Interfaces:**
- Consumes: structured `run_recovery`/terminal state payloads.
- Produces: status-bearing system event followed by truthful `message_delta` and guaranteed `message_stop`.

- [x] Write failing tests for fallback terminals, detached crashes, and recovery notices.
- [x] Verify the tests fail because synthetic stops currently imply clean completion.
- [x] Carry terminal reason/status through synthetic and translated SSE frames.
- [x] Verify all focused stream tests pass.

### Task 4: Verification and Deployment

**Files:**
- Review all files changed by Tasks 1-3.

- [x] Run the focused terminal, DSML, continuation, detached-run, and SSE test files.
- [x] Run `python -m compileall` for changed runtime/API packages.
- [x] Review the staged diff for false completion paths, secrets, and unrelated changes.
- [ ] Commit through `scripts/commit_with_attribution.py` with only intended paths.
- [ ] Push `main`, pull on `bs@10.0.0.39`, restart `jarvis-api` and `jarvis-runtime`, and verify service health and deployed revision.
