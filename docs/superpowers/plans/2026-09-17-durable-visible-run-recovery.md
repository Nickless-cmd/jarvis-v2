# Durable Visible Run Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all six recoverable visible-run failure classes survive segment and process boundaries without silent completion, duplicate continuation, or lost checkpoints.

**Architecture:** Extend the existing disk-backed `in_flight_runs` record into a lease-owned recovery journal, then route every segment ending through one coordinator. A dispatcher in the API owner process claims due recovery records and starts detached continuation exactly once; research retains its own durable child state and resumes only unfinished tracks.

**Tech Stack:** Python 3.11, FastAPI, asyncio/threading, Linux `fcntl.flock`, atomic JSON state store, SQLite research store, pytest.

**Spec:** `docs/superpowers/specs/2026-09-17-durable-visible-run-recovery-design.md`

**Status 17/9-2026:** alle otte opgaver er bygget og flettet til main
(`183d46164`) og deployet. Opgave 1-2 af codex, 3-8 af opus efter at hans kvote
slap op. Afvigelser undervejs står i commit-beskederne; de to vigtigste: planens
opgave 3 trin 4 (fjern direkte fortsættelse fra detached-completion) blev
udført i opgave 4 i stedet, fordi dispatcheren skulle findes først, og
`recovery_mode: final_synthesis` blev først koblet på beskeden i slutrunden
efter en gennemgang af planens trin 5.

## Global Constraints

- Only explicit user Stop, recognized stop intent, or safety policy may produce terminal `cancelled`.
- `completed` requires positive completion evidence.
- A hard crash may lose an uncheckpointed token tail, but not the task, completed tools, latest checkpoint, or recovery reason.
- Claims and settlements are idempotent by `(task_id, recovery_generation, run_id)`.
- The API process owns visible recovery dispatch; the runtime process may reconcile but must not duplicate dispatch.
- Autonomous runs keep scheduler-owned recovery and are never auto-dispatched by this subsystem.
- Existing numerical provider, watchdog, retry, loop, and research budgets stay unchanged.
- Changes to `core/services/visible_runs.py` contain only narrow call-site wiring; recovery logic lives in focused modules in accordance with the Boy Scout rule.
- Run only focused affected tests, not the full suite.

---

### Task 1: Transactional Durable Recovery Journal

**Files:**
- Modify: `core/runtime/state_store.py`
- Modify: `core/services/in_flight_runs.py`
- Test: `tests/test_in_flight_runs.py`
- Create: `tests/test_in_flight_recovery_claims.py`

**Interfaces:**
- Produces: `save_json_strict(name: str, data: Any) -> None`
- Produces: `settle_recovering(run_id: str, *, reason: str, summary: str = "", checkpoint_ref: str = "", recovery_limit: int = 3, expected_generation: int | None = None, expected_owner: str = "") -> dict`
- Produces: `settle_terminal(run_id: str, *, status: str, reason: str = "", expected_generation: int | None = None, expected_owner: str = "") -> dict | None`
- Produces: `claim_due_recovery(*, owner: str, lease_seconds: float = 120.0, now: datetime | None = None) -> dict | None`
- Produces: `renew_recovery_lease(task_id: str, generation: int, *, owner: str, lease_seconds: float = 120.0) -> bool`
- Produces: `release_recovery_claim(task_id: str, generation: int, *, owner: str, reason: str, retry_after_s: float) -> bool`
- Existing `mark_started`, `mark_interrupted`, `mark_completed`, and readers remain source-compatible.

- [x] **Step 1: Write failing journal and claim tests**

```python
def test_recoverable_settlement_survives_reload(tmp_state):
    mark_started(run_id="r1", session_id="s1", user_message="fix it")
    rec = settle_recovering("r1", reason="provider-timeout", checkpoint_ref="cp-r1")
    assert rec["status"] == "recovering"
    assert _load()["r1"]["checkpoint_ref"] == "cp-r1"


def test_only_one_owner_can_claim_same_recovery(tmp_state):
    mark_started(run_id="r1", session_id="s1", user_message="fix it")
    settle_recovering("r1", reason="shutdown")
    first = claim_due_recovery(owner="100:1")
    second = claim_due_recovery(owner="200:2")
    assert first and first["recovery_generation"] == 1
    assert second is None


def test_expired_lease_can_be_reclaimed_but_stale_generation_cannot_settle(tmp_state):
    t0 = datetime(2026, 9, 17, tzinfo=UTC)
    mark_started(run_id="r1", session_id="s1", user_message="fix it")
    settle_recovering("r1", reason="shutdown")
    first = claim_due_recovery(owner="100:1", lease_seconds=10, now=t0)
    second = claim_due_recovery(
        owner="200:2", lease_seconds=10, now=t0 + timedelta(seconds=11)
    )
    assert first["recovery_generation"] == 1
    assert second["recovery_generation"] == 2
    with pytest.raises(StaleRecoveryClaim):
        settle_terminal(
            "r1", status="completed", expected_generation=1, expected_owner="100:1"
        )


def test_failed_strict_save_does_not_report_success(tmp_state, monkeypatch):
    monkeypatch.setattr(os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk")))
    with pytest.raises(OSError):
        save_json_strict("in_flight_runs", {"r1": {}})
```

- [x] **Step 2: Run tests and verify RED**

Run:

```bash
python -m pytest tests/test_in_flight_runs.py tests/test_in_flight_recovery_claims.py -q
```

Expected: failures for missing strict persistence and recovery claim APIs.

- [x] **Step 3: Implement strict persistence and cross-process mutation**

Add `save_json_strict`; keep `save_json` as the self-safe wrapper. In
`in_flight_runs`, use one sidecar lock file under `~/.jarvis-v2/state/` and
`fcntl.flock(LOCK_EX)` around load/compare/save mutations. Upgrade legacy
records on write with `task_id=run_id`, generation `0`, and conservative
defaults. Claims compare status, due time, owner liveness, lease, and session
ownership while holding the lock.

- [x] **Step 4: Re-run focused tests to GREEN**

Run the command from Step 2 plus a multiprocessing claim race test. Exactly one
process must return a claim.

- [x] **Step 5: Commit Task 1 through the attribution wrapper**

Stage only the four Task 1 paths and commit `feat(runtime): add durable recovery claims`.

---

### Task 2: Single Recovery Settlement Coordinator

**Files:**
- Create: `core/services/visible_run_recovery_coordinator.py`
- Modify: `core/services/visible_terminal_policy.py`
- Modify: `core/services/visible_runs_sections/run_finalization.py`
- Test: `tests/test_visible_run_recovery_coordinator.py`
- Modify: `tests/test_visible_terminal_policy.py`
- Modify: `tests/services/test_visible_runs_lifecycle.py`

**Interfaces:**
- Produces: `FailureClass` enum with `PROCESS`, `CANCELLATION`, `PROVIDER`, `WATCHDOG`, `RESEARCH`, and `RUNTIME`.
- Produces: `RecoverySettlementRequest(task_id, run_id, session_id, evidence, failure_class, summary, checkpoint_ref, generation)`.
- Produces: `settle_segment(request) -> RecoverySettlement`.
- `RecoverySettlement` contains `decision`, `record`, `notice`, `dispatch_due`, and `final_synthesis_required`.

- [x] **Step 1: Write failing classification and idempotence tests**

```python
@pytest.mark.parametrize("reason,failure_class", [
    ("shutdown", FailureClass.PROCESS),
    ("provider-timeout", FailureClass.PROVIDER),
    ("round-silence-timeout", FailureClass.WATCHDOG),
    ("research-wall-time-exceeded", FailureClass.RESEARCH),
    ("unhandled:ValueError", FailureClass.RUNTIME),
])
def test_recoverable_failure_classes_never_complete(reason, failure_class, journal):
    out = settle_segment(request(reason, failure_class))
    assert out.decision.state is TerminalState.RECOVERING
    assert out.dispatch_due is True


def test_duplicate_settlement_is_idempotent(journal):
    first = settle_segment(request("provider-timeout", FailureClass.PROVIDER))
    second = settle_segment(request("provider-timeout", FailureClass.PROVIDER))
    assert second.record == first.record
    assert second.dispatch_due is False


def test_explicit_cancel_is_final_and_revokes_claim(journal):
    out = settle_segment(cancel_request(explicit=True))
    assert out.decision.state is TerminalState.CANCELLED
    assert out.dispatch_due is False
```

- [x] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_visible_run_recovery_coordinator.py tests/test_visible_terminal_policy.py tests/services/test_visible_runs_lifecycle.py -q
```

- [x] **Step 3: Implement coordinator and broaden the terminal taxonomy**

Map provider errors, relay timeouts, watchdog limits, shutdown, research
exhaustion, and `interrupted:*` to recovery. Preserve explicit cancellation as
the only normal cancelled path. `finalize_in_flight` delegates to the
coordinator and must no longer clear failed/recovering records through the
generic `mark_completed` branch.

- [x] **Step 4: Re-run focused tests to GREEN**

- [x] **Step 5: Commit Task 2**

Commit `feat(runtime): centralize visible run recovery settlement`.

---

### Task 3: Provider, Watchdog, Loop, and Exception Wiring

**Files:**
- Modify: `core/services/visible_run_terminal_recovery.py`
- Modify: `core/services/visible_runs_sse_v2.py`
- Modify: `core/services/visible_runs_sections/detached_run.py`
- Modify: `core/services/visible_runs.py` (call sites only)
- Test: `tests/test_visible_run_terminal_recovery.py`
- Modify: `tests/test_visible_runs_sse_v2.py`
- Modify: `tests/test_detached_run_tavs_sluger.py`
- Modify: `tests/test_loop_stop_reasons.py`
- Create: `tests/test_visible_run_failure_classes.py`

**Interfaces:**
- Consumes: `settle_segment` from Task 2.
- Produces: every abnormal segment exit with a durable recovery record before terminal SSE.

- [x] **Step 1: Write fault-injection tests for each hot-path ending**

Cover raised first-pass provider error, breaker-open with no fallback, round
silence timeout, round total timeout, turn retry exhaustion, turn wall clock,
relay idle timeout, max rounds, empty/tool-only/no-progress forced finalization,
ordinary exception, `GeneratorExit`, and detached spawn failure. Assert:

```python
assert durable_record["status"] == "recovering"
assert terminal_delta["delta"]["stop_reason"] == "recovering"
assert not any(event_claims_completed_without_evidence(events))
```

- [x] **Step 2: Run focused tests and verify RED**

```bash
python -m pytest tests/test_visible_run_terminal_recovery.py tests/test_visible_runs_sse_v2.py tests/test_detached_run_tavs_sluger.py tests/test_loop_stop_reasons.py tests/test_visible_run_failure_classes.py -q
```

- [x] **Step 3: Replace local abnormal finalization with coordinator calls**

Keep retry/failover and numeric limits unchanged. Before yielding terminal SSE,
save checkpoint evidence, settle durably, then emit the coordinator notice.
The outer exception branch uses `FailureClass.RUNTIME`; `finally` handles
abandoned non-`Exception` exits unless cancellation is already durable. A
durable-write failure must emit failed infrastructure state where possible and
must not clear the previous running record.

- [x] **Step 4: Remove direct continuation scheduling from detached completion**

`_fortsaet_hvis_budgettet_loeb_toert` becomes a compatibility adapter that
records/signal-wakes the dispatcher; it may not call
`start_user_run_detached` itself. This establishes one continuation owner.

- [x] **Step 5: Re-run focused tests to GREEN**

- [x] **Step 6: Commit Task 3**

Commit `fix(runtime): settle every abnormal visible run exit durably`.

---

### Task 4: Exactly-Once Recovery Dispatcher and Boot Resume

**Files:**
- Create: `core/services/visible_run_recovery_dispatcher.py`
- Modify: `core/services/session_boot_reconciler.py`
- Modify: `apps/api/jarvis_api/app.py`
- Modify: `core/services/visible_runs_sections/detached_run.py`
- Test: `tests/test_visible_run_recovery_dispatcher.py`
- Modify: `tests/test_session_boot_reconciler.py`
- Modify: `tests/test_drain_before_restart.py`

**Interfaces:**
- Produces: `recover_due_once(*, owner: str | None = None) -> dict`
- Produces: `start_recovery_dispatcher() -> bool` and `stop_recovery_dispatcher() -> None`.
- Produces: `signal_recovery_dispatcher() -> None` for immediate wake after live settlement.
- Consumes: `start_user_run_detached(*, message: str, session_id: str, run_id: str | None = None, recovery_task_id: str = "", recovery_generation: int = 0, recovery_attempt: int = 0, **visible_kwargs) -> str`.

- [x] **Step 1: Write failing dispatcher tests**

```python
def test_boot_orphan_is_resumed_once_after_readiness(fake_spawn, journal):
    orphan_owned_by_dead_process(journal)
    reconcile_on_boot()
    assert recover_due_once()["started"] == 1
    assert recover_due_once()["started"] == 0
    assert fake_spawn.call_count == 1


def test_runtime_process_does_not_dispatch_visible_recovery(monkeypatch):
    monkeypatch.setenv("JARVIS_ENABLE_RUNTIME_SERVICES", "1")
    assert start_recovery_dispatcher() is False


def test_failed_spawn_releases_claim_with_backoff(fake_spawn_raises, journal):
    result = recover_due_once()
    assert result["released"] == 1
    assert journal_record()["status"] == "recovering"
```

- [x] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_visible_run_recovery_dispatcher.py tests/test_session_boot_reconciler.py tests/test_drain_before_restart.py -q
```

- [x] **Step 3: Implement boot reconciliation and dispatcher**

Boot reconciliation changes confirmed dead-owner visible records to
`recovering` while preserving task metadata. The API process starts one daemon
dispatcher only after normal startup initialization. Claims carry stable task
identity, incremented generation, original request, checkpoint context, and
unfinished intent into the detached run. Progress renews the lease. Graceful
shutdown settles but never dispatches new work.

- [x] **Step 4: Re-run focused tests to GREEN**

- [x] **Step 5: Commit Task 4**

Commit `feat(runtime): resume orphaned visible tasks exactly once`.

---

### Task 5: Correct Cancellation and Supersession Semantics

**Files:**
- Modify: `core/services/visible_runs_sections/detached_run.py`
- Modify: `core/services/visible_runs.py` (call sites only)
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Test: `tests/test_server_authoritative_runs.py`
- Modify: `tests/test_auto_continuation.py`
- Create: `tests/test_visible_run_supersession.py`

**Interfaces:**
- Explicit Stop builds `RecoverySettlementRequest` with the active task/run/session identifiers, `FailureClass.CANCELLATION`, and `TerminalEvidence(explicit_user_cancel=True)`, then calls `settle_segment(request)` before cancelling execution.
- New user input calls `steer_visible_run`; if steering is unavailable, it is durably queued rather than clearing the active task.
- Explicit restart/forget intent calls `settle_terminal(run_id, status="cancelled", reason="user-restart")` and clears the prior task by authorization.

- [x] **Step 1: Write failing cancellation/supersession tests**

```python
def test_stop_is_terminal_and_never_recovered(active_run):
    response = cancel_active(active_run.session_id)
    assert response["cancelled"] is True
    assert record(active_run.task_id)["status"] == "cancelled"
    assert claim_due_recovery(owner="other") is None


def test_new_message_steers_without_erasing_active_recovery(active_run):
    start_or_attach_user_run(message="also check tests", session_id=active_run.session_id)
    assert active_run.controller.steers == ["also check tests"]
    assert record(active_run.task_id)["status"] == "running"
```

- [x] **Step 2: Run tests and verify RED**

- [x] **Step 3: Wire explicit cancel and preserve non-cancelling supersession**

Remove any generic “new run implies prior finished” deletion from
`mark_started`. Preserve terminal history until the coordinator prunes it.
Session single-flight remains authoritative.

- [x] **Step 4: Re-run focused tests to GREEN**

- [x] **Step 5: Commit Task 5**

Commit `fix(runtime): separate user stop from run supersession`.

---

### Task 6: Resumable Research Deadlines and Budgets

**Files:**
- Modify: `core/services/research_store.py`
- Modify: `core/services/research_orchestrator.py`
- Modify: `core/services/research_ledger.py`
- Modify: `core/services/visible_run_recovery_coordinator.py`
- Modify: `tests/test_research_orchestrator.py`
- Modify: `tests/test_research_store.py`
- Create: `tests/test_research_recovery.py`

**Interfaces:**
- Produces: `prepare_recovery(run_id: str, *, warning: str) -> dict`.
- Produces: `unfinished_tasks(run_id: str) -> list[dict]`.
- Produces: `list_tasks(run_id: str) -> list[dict]` for deterministic recovery inspection.
- Produces: `resume_research_run(run_id: str, *, visible_run_id: str, worker_factory=None) -> AsyncIterator[str]`.
- Produces: `ResearchRecoverableError(run_id, reason, evidence_count)` when no synthesis is possible.

- [x] **Step 1: Write failing research recovery tests**

```python
async def test_timeout_synthesizes_completed_evidence_without_repeating_tracks(store):
    run = store.create_run(
        session_id="s1", original_query="compare", tier="orchestrated"
    )
    tasks = store.create_tasks(run["id"], [
        ResearchTask("done", "completed evidence", 1),
        ResearchTask("missing", "unfinished evidence", 2),
    ])
    store.start_task(tasks[0]["id"])
    store.complete_task(tasks[0]["id"], {"text": "fact", "findings": []})
    store.start_task(tasks[1]["id"])
    store.prepare_recovery(run["id"], warning="research-wall-time-exceeded")
    called = []

    async def worker_factory(**kwargs):
        called.append(int(kwargs["task"]["ordinal"]))
        return {"text": "recovered evidence", "status": "completed"}

    events = [event async for event in resume_research_run(
        run["id"], visible_run_id="v1", worker_factory=worker_factory
    )]
    assert called == [2]
    assert any("research_completed" in event for event in events)


async def test_timeout_without_evidence_requests_parent_recovery(store, monkeypatch):
    async def hanging_worker(**kwargs):
        await asyncio.Event().wait()

    async def immediate_deadline(pending, **kwargs):
        return set(), pending

    monkeypatch.setattr(research_orchestrator.asyncio, "wait", immediate_deadline)

    with pytest.raises(ResearchRecoverableError) as exc:
        await collect(run_research(
            message="investigate",
            original_query="investigate",
            session_id="s1",
            decision=ResearchDecision(
                tier="orchestrated", max_workers=1, max_tasks=2,
                max_tool_calls=2, wall_time_seconds=30, source_target=2,
            ),
            worker_factory=hanging_worker,
            orchestrator_enabled=True,
        ))
    assert exc.value.reason == "research-wall-time-exceeded"


def test_prepare_recovery_keeps_completed_tasks_and_resets_only_running(store):
    run = store.create_run(session_id="s1", original_query="q", tier="orchestrated")
    tasks = store.create_tasks(run["id"], [
        ResearchTask("done", "done", 1), ResearchTask("live", "live", 2),
    ])
    store.start_task(tasks[0]["id"])
    store.complete_task(tasks[0]["id"], {"text": "kept"})
    store.start_task(tasks[1]["id"])
    store.prepare_recovery(run["id"], warning="runtime restart")
    states = {task["ordinal"]: task["status"] for task in store.list_tasks(run["id"])}
    assert states == {1: "completed", 2: "pending"}
```

- [x] **Step 2: Run tests and verify RED**

```bash
python -m pytest tests/test_research_store.py tests/test_research_orchestrator.py tests/test_research_recovery.py -q
```

- [x] **Step 3: Implement resumable research state**

Add `recovering` as a nonterminal research status. `prepare_recovery` keeps
completed findings and sources, resets interrupted `running` tasks to pending,
and records an idempotent ledger event. Timeout still synthesizes partial
evidence when usable; only absent/failed synthesis escalates parent recovery.
Explicit cancellation remains terminal.

- [x] **Step 4: Connect research recovery metadata to visible recovery records**

Store `research_run_id` and unfinished ordinals in the parent checkpoint. The
dispatcher calls `resume_research_run` rather than creating a new research run.

- [x] **Step 5: Re-run focused tests to GREEN**

- [x] **Step 6: Commit Task 6**

Commit `feat(research): resume timed out research without duplicate work`.

---

### Task 7: Durable Reconnect Snapshot and Recovery Notices

**Files:**
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Modify: `core/services/run_event_log.py`
- Modify: `core/services/visible_terminal_policy.py`
- Test: `tests/test_server_authoritative_runs.py`
- Modify: `tests/test_run_event_log.py`
- Create: `tests/test_recovery_snapshot_api.py`

**Interfaces:**
- Produces: `GET /chat/sessions/{session_id}/recovery` returning `204` or `{task_id, run_id, state, reason, recovery_attempt, checkpoint_summary, notice}`.
- Existing `/active-runs`, `/live`, and `/subscribe` consult durable recovery state when the process-local event log is absent.

- [x] **Step 1: Write failing reconnect tests**

```python
def test_reconnect_after_process_log_loss_returns_recovery_snapshot(client, journal):
    recovering_record_without_event_log(journal)
    response = client.get("/chat/sessions/s1/recovery")
    assert response.status_code == 200
    assert response.json()["state"] == "recovering"


def test_synthetic_stop_for_recovery_never_claims_end_turn():
    frame = synthetic_terminal_frame("r1", "s1", reason="provider-timeout")
    assert '"stop_reason": "recovering"' in frame
    assert '"stop_reason": "end_turn"' not in frame
```

- [x] **Step 2: Run tests and verify RED**

- [x] **Step 3: Implement recovery snapshot and durable fallback**

Return redacted user-facing notice text only. A missing in-memory log is no
longer equivalent to a completed run when a durable recovering record exists.

- [x] **Step 4: Re-run focused tests to GREEN**

- [x] **Step 5: Commit Task 7**

Commit `feat(api): expose durable visible run recovery state`.

---

### Task 8: Fault Matrix, Documentation, and Release Verification

**Files:**
- Create: `tests/test_visible_recovery_fault_matrix.py`
- Modify generated API references required by repository checks.
- Review all paths changed by Tasks 1-7.

**Interfaces:**
- Verifies all six failure classes against the same lifecycle assertions.

- [x] **Step 1: Add the parameterized end-to-end fault matrix**

```python
@pytest.mark.parametrize("fault", [
    "process_owner_dead",
    "provider_failure",
    "watchdog_timeout",
    "research_timeout",
    "runtime_exception",
])
def test_recoverable_fault_never_silently_completes(fault, harness):
    result = harness.inject(fault)
    assert result.initial_terminal_state == "recovering"
    assert result.continuations == 1
    assert result.final_state in {"completed", "failed_terminal"}
    assert result.visible_notice_count >= 1


def test_explicit_user_cancel_is_the_nonrecovering_control(harness):
    result = harness.inject("explicit_cancel")
    assert result.final_state == "cancelled"
    assert result.continuations == 0
```

- [x] **Step 2: Run all affected tests, not the full suite**

```bash
python -m pytest \
  tests/test_in_flight_runs.py \
  tests/test_in_flight_recovery_claims.py \
  tests/test_visible_terminal_policy.py \
  tests/test_visible_run_recovery_coordinator.py \
  tests/services/test_visible_runs_lifecycle.py \
  tests/test_visible_run_terminal_recovery.py \
  tests/test_visible_runs_sse_v2.py \
  tests/test_detached_run_tavs_sluger.py \
  tests/test_loop_stop_reasons.py \
  tests/test_visible_run_failure_classes.py \
  tests/test_visible_run_recovery_dispatcher.py \
  tests/test_session_boot_reconciler.py \
  tests/test_drain_before_restart.py \
  tests/test_server_authoritative_runs.py \
  tests/test_visible_run_supersession.py \
  tests/test_research_store.py \
  tests/test_research_orchestrator.py \
  tests/test_research_recovery.py \
  tests/test_run_event_log.py \
  tests/test_recovery_snapshot_api.py \
  tests/test_visible_recovery_fault_matrix.py -q
```

- [x] **Step 3: Run syntax and repository checks**

```bash
python -m compileall -q core apps/api
git diff --check
python scripts/install_git_hooks.py --check
```

- [x] **Step 4: Regenerate only required API documentation**

Use the repository's existing docs generator for changed public modules, then
inspect generated diffs and exclude unrelated churn.

- [x] **Step 5: Review invariants before final commit**

Confirm no recoverable path calls `mark_completed`, every dispatcher claim has
a lease and generation check, explicit cancel cannot be reclaimed, completed
research tracks are immutable during recovery, and no secret or runtime state
file is staged.

- [x] **Step 6: Commit final integration through attribution wrapper**

Commit `test(runtime): verify durable recovery across run failure classes`.

- [x] **Step 7: Push, deploy, and verify focused production behavior when requested**

Drain active work before restart, pull the exact pushed revision on the Jarvis
container, restart only affected services, verify both health endpoints and
service revision, then perform one controlled recoverable interruption without
running the full suite.
