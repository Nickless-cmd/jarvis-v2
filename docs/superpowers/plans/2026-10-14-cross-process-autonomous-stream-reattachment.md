# Cross-Process Autonomous Stream Reattachment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every visible autonomous run discoverable, securely streamable, and resumable through the public API regardless of whether the API or runtime process owns execution.

**Architecture:** Keep each producer's bounded in-memory `run_event_log` as the frame authority and add a shared journal locator containing the producer process role. Public routes authorize the session, stream locally when possible, or byte-proxy an authenticated loopback SSE endpoint on the owner process; Desk and Mobile retain a global replay cursor and reconcile explicit non-stream states without inventing completion.

**Tech Stack:** Python 3.11, FastAPI/Starlette streaming responses, `httpx`, JSON-file state under `flock`, pytest with real subprocesses, React/TypeScript/Vitest, React Native/TypeScript/Jest.

**Spec:** `docs/superpowers/specs/2026-10-14-cross-process-autonomous-stream-reattachment-design.md`

## Global Constraints

- Evidence first; do not change behavior until the failing test for that behavior has been observed.
- Preserve real token-by-token SSE delivery and the existing bounded ring buffer.
- Do not synchronously persist individual frames to SQLite or add infrastructure.
- Public discovery and subscription must enforce the existing session ownership rule.
- HTTP failures must never be converted directly into successful `message_stop`.
- Use true subprocesses for cross-process claims.
- Preserve old imports when extracting code from `apps/api/jarvis_api/routes/chat.py`.
- Do not change notification routing without a separately reproduced routing defect.
- Update `DEVLOG.md` and `STATUS.md`.
- Create exactly one final commit through `scripts/commit_with_attribution.py`; do not commit between tasks.

## Review Focus

- A journal record whose owner PID is alive but whose process role is absent must produce retryable unavailability, not completion; covered in Task 2 and Task 4.
- An unauthorized caller who knows a valid run ID must receive 403 without learning frame or lifecycle content; covered in Task 4.
- Proxy keepalives must not advance client cursors or enter replay storage; covered in Tasks 4–6.
- An API restart during a runtime-owned run must preserve attachability while a runtime restart must produce explicit recovery; covered in Task 4.
- Two devices reconnecting from different cursors must not launch another model run or interfere with each other's offsets; covered in Tasks 4–6.

---

### Task 1: Extract the run-stream route unit before behavioral changes

**Files:**
- Create: `apps/api/jarvis_api/routes/chat_run_streams.py`
- Modify: `apps/api/jarvis_api/routes/chat.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_chat_run_stream_route_extraction.py`

**Interfaces:**
- Consumes: `chat_session_view.kraev_adgang(session_id: str) -> None`, `run_event_log`, `run_follow`, and existing visible-run cancellation functions.
- Produces: `chat_run_streams.router`; compatibility re-exports `chat_active_runs`, `chat_run_subscribe`, `chat_session_live`, and `chat_session_follow` from `routes.chat`.

- [ ] **Step 1: Add a route-inventory characterization test**

```python
from apps.api.jarvis_api.app import create_app


def test_run_stream_routes_exist_once_after_extraction():
    app = create_app()
    paths = [route.path for route in app.routes]
    for expected in (
        "/chat/active-runs",
        "/chat/runs/{run_id}/subscribe",
        "/chat/sessions/{session_id}/live",
        "/chat/sessions/{session_id}/follow",
    ):
        assert paths.count(expected) == 1


def test_old_chat_module_reexports_stream_handlers():
    from apps.api.jarvis_api.routes import chat, chat_run_streams
    assert chat.chat_active_runs is chat_run_streams.chat_active_runs
    assert chat.chat_run_subscribe is chat_run_streams.chat_run_subscribe
    assert chat.chat_session_live is chat_run_streams.chat_session_live
    assert chat.chat_session_follow is chat_run_streams.chat_session_follow
```

- [ ] **Step 2: Run the characterization test before extraction**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_chat_run_stream_route_extraction.py -q`

Expected: the route inventory passes and the compatibility-import assertion fails because `chat_run_streams` does not exist.

- [ ] **Step 3: Move the cohesive route block mechanically**

Move `_AKTIVE_RUNS_ALDER_LOFT_S`, `_JOURNAL_STILSTAND_LOFT_S`, `_journal_sessions`, and the four GET handlers named above to a new `APIRouter(prefix="/chat", tags=["chat"])`. Do not change response semantics in this task. Import `kraev_adgang` directly rather than importing private helpers back from `chat.py`.

At the end of `chat.py`, re-export:

```python
from apps.api.jarvis_api.routes.chat_run_streams import (  # noqa: E402,F401
    chat_active_runs,
    chat_run_subscribe,
    chat_session_follow,
    chat_session_live,
)
```

Register the new router once in `create_app()`:

```python
from apps.api.jarvis_api.routes.chat_run_streams import router as chat_run_streams_router
# inside create_app(), immediately after the existing chat router
app.include_router(chat_router)
app.include_router(chat_run_streams_router)
```

- [ ] **Step 4: Verify the mechanical extraction**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_chat_run_stream_route_extraction.py \
  tests/test_run_event_log.py \
  tests/test_run_follow.py -q
```

Expected: all pass with each public route registered exactly once.

- [ ] **Step 5: Check the Boy Scout result**

Run: `wc -l apps/api/jarvis_api/routes/chat.py apps/api/jarvis_api/routes/chat_run_streams.py`

Expected: `chat.py` is below 2,000 lines and the extracted module has one primary responsibility.

### Task 2: Record and classify the stream owner across processes

**Files:**
- Create: `core/services/run_stream_locator.py`
- Modify: `core/services/in_flight_runs.py`
- Test: `tests/test_run_stream_locator.py`
- Test: `tests/test_in_flight_runs.py` or the existing nearest journal test module

**Interfaces:**
- Consumes: `in_flight_runs.get_record(identity)`, `in_flight_runs.levende_koersler(max_alder_s=1800.0)`, `in_flight_runs.owner_still_alive(owner)`, `central_xproc.process_role()`, and local `run_event_log` lookups.
- Produces:

`RunStreamLocation` is a frozen slotted dataclass with `run_id: str`,
`session_id: str`, `lifecycle: Literal["running", "terminal",
"stale_owner", "unknown"]`, `producer_process: Literal["api", "runtime",
"unknown"]`, `local_available: bool`, and `journal_status: str`.

The public functions are `locate_run(run_id: str) -> RunStreamLocation`,
`live_run_for_session(session_id: str) -> RunStreamLocation | None`, and
`active_locations(max_idle_s: float = 1800.0) -> list[RunStreamLocation]`.

- [ ] **Step 1: Write failing journal and locator tests**

Add `test_mark_started_records_current_process_role`, patching
`central_xproc.process_role` to `runtime`, calling `mark_started`, and asserting
the stored field is exactly `runtime`. Add
`test_locator_distinguishes_remote_running_from_unknown` with a live journal
record, no local log, and an owner-alive patch; assert `running`, `runtime`, and
`local_available is False`, while a missing ID returns `unknown`. Add
`test_locator_reports_terminal_pruned_stream` with a completed journal record
and no local log, and `test_locator_reports_dead_owner_as_stale` with a running
record whose owner-alive check returns false.

Also pin backward compatibility: a live older record without
`producer_process` resolves to `unknown`, never to the current process by
assumption.

- [ ] **Step 2: Verify the tests fail for missing metadata and locator**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_run_stream_locator.py -q`

Expected: collection/import fails for the missing locator or assertions fail because journal records lack `producer_process`.

- [ ] **Step 3: Add producer role to journal creation paths**

In `mark_started()` and the recovery-created fallback record, set:

```python
try:
    from core.services.central_xproc import process_role
    producer_process = process_role()
except Exception:
    producer_process = ""
```

Store only `api`, `runtime`, or an empty string. Preserve an existing valid role
when recovery updates an older record.

- [ ] **Step 4: Implement the pure locator**

Local state wins for availability and supplies the canonical session when it
exists. Shared journal state supplies lifecycle and owner role otherwise.
Terminal statuses are `completed`, `cancelled`, and `failed_terminal`.
`running`, `recovering`, and `waiting_for_user` remain non-terminal but only
`running` is advertised as actively streaming. A dead recorded owner maps to
`stale_owner`; absent data maps to `unknown`.

- [ ] **Step 5: Run locator and journal regressions**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_run_stream_locator.py \
  tests/test_in_flight_recovery_claims.py \
  tests/test_run_guard.py -q
```

Expected: all pass.

### Task 3: Give every visible autonomous run an authoritative frame log

**Files:**
- Create: `core/services/autonomous_frame_relay.py`
- Modify: `core/services/visible_autonomous_run.py`
- Modify: `core/services/autonomous_stream_run.py`
- Test: `tests/test_autonomous_visible_runs.py`
- Test: `tests/test_autonomous_stream_run.py`
- Test: `tests/test_autonomous_entrypoint_streaming.py`

**Interfaces:**
- Consumes: `visible_runs_sse_v2.translate_to_v2`, `run_event_log.create/append/mark_done/prune`, and optional `run_follow.begin_follow/publish_follow_frame/end_follow`.
- Produces:

`AutonomousFrameRelay` is a slotted dataclass with `run_id`, `session_id`, and
`legacy_follow=False`. `register()` creates the run-keyed log and conditionally
starts legacy follow; `publish(frame)` appends to the run-keyed log and
conditionally tees the same frame to legacy follow; `finish()` marks the log
done, conditionally ends legacy follow, and prunes old completed logs. An
internal boolean makes `finish()` idempotent.

`finish()` is idempotent. `publish()` always appends to the run-keyed log and
tees to `run_follow` only when `legacy_follow=True`.

- [ ] **Step 1: Write failing entrypoint tests**

Add parameterized
`test_start_autonomous_run_always_registers_run_keyed_relay[False|True]`. Replace
the visible generator with a controlled async iterator, use a threading event
to wait for daemon completion, capture relay calls, and assert: `create` uses
the `VisibleRun.run_id`; appended v2 frames include start, delta, and stop;
`mark_done` occurs once; and the legacy follow tee is used exactly when
`follow=True`.

Add source-level or behavior-level coverage showing inbox, scheduled/recurring,
operator wakeup, and detached autonomous callers reach one of the two supported
starters without launching a second run for follow.

- [ ] **Step 2: Verify `follow=False` fails**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_autonomous_entrypoint_streaming.py \
  tests/test_autonomous_stream_run.py -q
```

Expected: `follow=False` has no run-keyed frames in current code.

- [ ] **Step 3: Implement the relay helper and use it in both starters**

Register before starting the worker thread. Wrap `_stream_visible_run(run)` in
`translate_to_v2(_stream_visible_run(run), run_id=run.run_id, model=run.model,
provider=run.provider, lane=run.lane, session_id=session_id)` for every visible autonomous run, publish each returned
frame once, and call `finish()` from `finally`. Keep lifecycle/outcome events and
model execution unchanged. `follow` now means only “also feed legacy
session-keyed follow.”

- [ ] **Step 4: Verify stable identity and terminal behavior**

Tests must assert the same `run.run_id` appears in the shared journal, local
event log, emitted `system_event(kind=run)`, and client subscription key. A
normal run produces one logical `message_stop`; an exception still marks the
relay done and follows existing recovery policy.

- [ ] **Step 5: Run autonomous regressions**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_autonomous_visible_runs.py \
  tests/test_autonomous_stream_run.py \
  tests/test_autonomous_entrypoint_streaming.py \
  tests/test_auto_continuation_e2e.py -q
```

Expected: all pass without duplicate model invocation.

### Task 4: Add secure owner-process proxying and authoritative HTTP states

**Files:**
- Create: `apps/api/jarvis_api/routes/internal_run_stream.py`
- Create: `core/services/run_stream_proxy.py`
- Modify: `apps/api/jarvis_api/routes/chat_run_streams.py`
- Modify: `apps/api/jarvis_api/app.py`
- Test: `tests/test_chat_run_stream_routes.py`
- Test: `tests/test_cross_process_run_stream.py`
- Test: `tests/test_run_stream_authorization.py`

**Interfaces:**
- Consumes: `run_stream_locator`, `run_event_log.read_from/is_open`,
  `jarvisx_bridge.internal_dispatch_token()`, `_INTERNAL_TOKEN_HEADER`,
  `_port_for_process(role)`, and `chat_session_view.kraev_adgang`.
- Produces:

The route constant is
`_INTERNAL_RUN_STREAM_PATH = "/api/internal/run-stream/{run_id}"`. The service
exports `local_frame_generator(run_id: str, from_idx: int) ->
AsyncIterator[str]`, `proxy_owner_stream(location: RunStreamLocation,
from_idx: int) -> StreamingResponse`, and `stream_error(status: int, code: str,
retry_after: int | None = None) -> HTTPException`.

Public status payloads use `{ "detail": { "code": "stream_unavailable", "run_id": "run-123" } }`
without session transcript content.

- [ ] **Step 1: Write failing public-state and authorization tests**

Add these exact cases:

- `test_subscribe_checks_session_access_before_stream_lookup`: a valid foreign
  run ID raises 403 and `run_event_log.read_from` is never called.
- `test_active_runs_omits_foreign_journal_session`: one allowed and one denied
  journal record returns only the allowed item.
- `test_running_remote_stream_failure_is_503_not_404_or_200`: a live remote
  record with a failed owner connection raises 503.
- `test_terminal_pruned_stream_is_410`: a terminal journal record without a
  retained log raises 410.
- `test_unknown_run_is_404`: an ID absent from both authorities raises 404.
- `test_session_live_remote_running_never_returns_204`: a live remote session
  either attaches or returns 503, never 204.

- [ ] **Step 2: Write failing internal-endpoint security tests**

Assert non-loopback, forwarded requests, missing token, and bad token are
rejected; a loopback request with the correct token reaches only a local log.
The internal endpoint must return 404 for a non-local stream instead of
proxying again.

- [ ] **Step 3: Verify all new backend route tests fail**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_chat_run_stream_routes.py \
  tests/test_run_stream_authorization.py -q
```

Expected: failures demonstrate missing guard, missing status distinctions, and
missing internal route.

- [ ] **Step 4: Implement the local generator once**

Move the duplicate subscribe/live polling loop into
`local_frame_generator(run_id, from_idx)`. Preserve:

- global `read_from` cursor;
- five-second ephemeral ping;
- open-run tolerance through long tool silence;
- ring-gap forwarding;
- synthetic recovery terminal only when the local authoritative log is marked
  done without `message_stop`;
- subscriber open/close accounting in `try/finally`.

Emit structured metadata-only logs on attach, detach, resume, replay gap, proxy
failure, and terminal delivery.

- [ ] **Step 5: Implement internal streaming and byte proxying**

The internal route performs loopback, forwarded-header, and constant-time token
checks before returning
`StreamingResponse(local_frame_generator(run_id, from_idx), media_type="text/event-stream")`.

`proxy_owner_stream()` uses `httpx.AsyncClient.stream()` against
`127.0.0.1:_port_for_process(location.producer_process)`, forwards the cursor,
requires `text/event-stream`, and yields `response.aiter_raw()` chunks directly.
Client disconnect closes the upstream context. It never stores or renumbers
frames.

- [ ] **Step 6: Implement public resolution and explicit statuses**

Both public handlers use one resolver:

```python
async def subscribe_authorized(location: RunStreamLocation, from_idx: int):
    kraev_adgang(location.session_id)
    if location.local_available:
        return StreamingResponse(
            local_frame_generator(location.run_id, from_idx),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Run-Id": location.run_id},
        )
    if location.lifecycle == "running" and location.producer_process in {"api", "runtime"}:
        return await proxy_owner_stream(location, from_idx)
    if location.lifecycle == "running":
        raise stream_error(503, "stream_unavailable", retry_after=1)
    if location.lifecycle in {"terminal", "stale_owner"}:
        raise stream_error(410, "stream_pruned")
    raise stream_error(404, "run_unknown")
```

`session_live` returns 204 only when `live_run_for_session()` returns `None`.
`active-runs` filters every local or journal item through
`maa_tilgaa_session()` before including it.

- [ ] **Step 7: Add the true two-process integration test**

`tests/test_cross_process_run_stream.py` must launch a subprocess with a fresh
`HOME`, `JARVIS_ENABLE_RUNTIME_SERVICES=1`, and an ephemeral localhost port. The
child registers a stable run, publishes controlled SSE frames over time, and
serves the internal route. The parent uses a separate interpreter/process role
and public route app.

Assert:

- discovery returns the runtime run;
- two concurrent public subscribers receive the same deltas and one terminal;
- one subscriber reconnects from a saved cursor without replaying earlier
  deltas;
- API-side app recreation during the child run still attaches;
- child termination changes the result to explicit recovery/unavailability;
- a counter shared by the producer proves exactly one model-run surrogate was
  launched.

- [ ] **Step 8: Run backend streaming tests**

Run:

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_chat_run_stream_routes.py \
  tests/test_run_stream_authorization.py \
  tests/test_cross_process_run_stream.py \
  tests/test_run_event_log.py \
  tests/test_run_follow.py -q
```

Expected: all pass, including the subprocess proof.

### Task 5: Make Desk passive follow cursor-safe and state-aware

**Files:**
- Modify: `apps/jarvis-desk/src/lib/api.ts`
- Modify: `apps/jarvis-desk/src/lib/api.test.ts`
- Modify: `apps/jarvis-desk/src/contexts/StreamContext.tsx`
- Modify: `apps/jarvis-desk/src/contexts/StreamContext.test.tsx`
- Modify if required by existing passive-follow ownership: `apps/jarvis-desk/src/views/ChatView.tsx`

**Interfaces:**
- Consumes: SSE `StreamEvent`, `relay_gap.resume_idx`, public stream status contract, and existing `getSession()`/active-run reads.
- Produces:

```typescript
export type FollowEndReason = 'terminal' | 'idle' | 'reconcile' | 'error'

export interface FollowRunControl {
  abort(): void
  getOffset(): number
  getRunId(): string | null
}

export function followRun(
  config: ApiConfig,
  sessionId: string,
  onEvent: (ev: StreamEvent) => void,
  onDone: (reason: FollowEndReason) => void,
  runId?: string | null,
): FollowRunControl
```

- [ ] **Step 1: Replace the old 404-success test with failing contract tests**

Tests assert:

- 404 and 410 emit no `message_stop` and finish as `reconcile`;
- 401/403 finish as `error` and emit no terminal;
- 503 reconnects with backoff from the current cursor;
- a dropped response reconnects from the current cursor;
- pings do not advance the cursor;
- `relay_gap.resume_idx` updates the cursor base;
- callbacks from an aborted generation do not dispatch or increment cursor;
- a real `message_stop` produces exactly one `terminal` completion.

- [ ] **Step 2: Run Desk tests and observe the old behavior fail**

Run:

```bash
cd apps/jarvis-desk
npm test -- --run src/lib/api.test.ts src/contexts/StreamContext.test.tsx
```

Expected: current code fails because it emits synthetic `message_stop`, always
uses `from_idx=0`, and cannot report an end reason.

- [ ] **Step 3: Implement cursor accounting and reconnect generations**

Add a local `nextFollowOffset()` matching Mobile's proven rules. Track `offset`,
`generation`, `attempt`, `sawStop`, and the current abort controller. Parse each
SSE event once, ignore superseded generations, and reconnect with
`from_idx=${offset}`. Retry network failures and 503 with bounded exponential
backoff. Never POST from passive follow.

- [ ] **Step 4: Update StreamContext terminal decisions**

Only dispatch a terminal transition for `reason === 'terminal'`. For
`reconcile`, refresh the persisted session and active-run state before clearing
working UI. For `error`, retain the existing retryable error UI. Abort the old
controller before session switches or a new follow generation.

- [ ] **Step 5: Run Desk targeted tests and type build**

Run:

```bash
cd apps/jarvis-desk
npm test -- --run src/lib/api.test.ts src/contexts/StreamContext.test.tsx
npm run build:renderer
```

Expected: tests and TypeScript build pass.

### Task 6: Make Mobile lifecycle recovery honor authoritative states

**Files:**
- Modify: `apps/mobile/src/lib/streamClient.ts`
- Modify: `apps/mobile/src/lib/streamClient.test.ts`
- Modify: `apps/mobile/src/state/StreamContext.tsx`
- Modify: `apps/mobile/src/screens/ChatScreen.tsx`
- Modify or create nearest lifecycle test: `apps/mobile/src/state/StreamContext.test.tsx`

**Interfaces:**
- Consumes: existing `StreamControl.getOffset()`, active-run discovery, persisted-session fetch, and public HTTP state contract.
- Produces: an additive handler `onReconcile?: (reason: 'unknown' | 'pruned') => void`; existing callers that omit it remain valid.

- [ ] **Step 1: Write failing status and lifecycle tests**

Tests assert:

- HTTP 404 invokes `onReconcile('unknown')` without `message_stop`;
- HTTP 410 invokes `onReconcile('pruned')` without `message_stop`;
- HTTP 503 retries the same run from the saved cursor;
- HTTP 401/403 invokes `onError` and never `onComplete`;
- background captures run ID and cursor before abort;
- foreground reattaches with GET subscribe, not POST stream creation;
- session switching fences old callbacks;
- two passive device controls do not share cursors or start execution.

- [ ] **Step 2: Run Mobile tests and observe synthetic completion fail**

Run:

```bash
cd apps/mobile
npm test -- --runInBand src/lib/streamClient.test.ts src/state/StreamContext.test.tsx
```

Expected: the 404 assertions fail because current code emits synthetic
`message_stop` and completes.

- [ ] **Step 3: Implement explicit error classification**

In `disconnect()`, branch by `xhrStatus`:

```typescript
if (status === 401 || status === 403) failAuthorization()
else if (status === 404) reconcile('unknown')
else if (status === 410) reconcile('pruned')
else if (status === 503) scheduleReconnect()
else scheduleReconnectOrInterrupt()
```

No HTTP branch calls `handlers.onEvent({type: 'message_stop'})`. Only parsed SSE
terminal frames call `onComplete` directly.

- [ ] **Step 4: Wire foreground reconciliation**

`StreamContext`/`ChatScreen` responds to `onReconcile` by fetching the session
snapshot and current active-run list. If the run is still active, follow the
returned stable run ID. If not active, accept the persisted transcript as
terminal UI state. Never resend the original message.

- [ ] **Step 5: Run Mobile targeted tests and typecheck**

Run:

```bash
cd apps/mobile
npm test -- --runInBand src/lib/streamClient.test.ts src/state/StreamContext.test.tsx
npm run typecheck
```

Expected: all pass.

### Task 7: Verify notification routing remains independent

**Files:**
- Test: `tests/test_stream_presence_independence.py`
- Modify only if a new failing test proves a defect: `core/services/device_presence.py`
- Modify only if a new failing test proves a defect: `core/services/notification_router.py`

**Interfaces:**
- Consumes: presence/routing decisions and the new authorized subscription path.
- Produces: regression proof that notification destination does not change stream ownership or subscription permission.

- [ ] **Step 1: Add the independence test**

Set Mobile as the selected notification destination and Desk presence as stale,
then assert both authorized user contexts can independently resolve and
subscribe to the same run. Assert notification choice never mutates the journal
record, local subscriber count except during attachment, or producer process.

- [ ] **Step 2: Run the test before changing routing**

Run: `/opt/conda/envs/ai/bin/python -m pytest tests/test_stream_presence_independence.py -q`

Expected: if it passes, make no production changes to presence/routing. If it
fails, stop and document the independently reproduced routing defect before a
minimal TDD fix in the owning module.

### Task 8: Documentation, full verification, review, and one attributed commit

**Files:**
- Modify: `DEVLOG.md`
- Modify: `STATUS.md`
- Modify: `docs/superpowers/specs/2026-10-14-cross-process-autonomous-stream-reattachment-design.md` only if implementation evidence requires a factual correction
- Modify: this plan only to check completed boxes if desired

**Interfaces:**
- Consumes: exact test output and final diff.
- Produces: evidence-backed delivery report and one attributed Git commit.

- [ ] **Step 1: Update project truth documents**

Record the two-process reproduction, root cause, owner-proxy mechanism, status
contract, authorization fix, client cursor behavior, tests run, and the
remaining limitation: producer-process death loses the in-memory replay window
and requires persisted-session recovery.

- [ ] **Step 2: Run backend targeted and syntax gates**

```bash
/opt/conda/envs/ai/bin/python -m pytest \
  tests/test_chat_run_stream_route_extraction.py \
  tests/test_run_stream_locator.py \
  tests/test_autonomous_visible_runs.py \
  tests/test_autonomous_stream_run.py \
  tests/test_autonomous_entrypoint_streaming.py \
  tests/test_chat_run_stream_routes.py \
  tests/test_run_stream_authorization.py \
  tests/test_cross_process_run_stream.py \
  tests/test_run_event_log.py \
  tests/test_run_follow.py \
  tests/test_stream_presence_independence.py -q
/opt/conda/envs/ai/bin/python -m compileall core apps/api scripts
```

- [ ] **Step 3: Run complete client suites**

```bash
cd apps/jarvis-desk && npm test -- --run && npm run build:renderer
cd /media/projects/jarvis-v2/apps/mobile && npm test -- --runInBand && npm run typecheck
```

Report every failure by name, including failures determined to predate this
change.

- [ ] **Step 4: Run the broad backend suite**

Run: `/opt/conda/envs/ai/bin/python -m pytest -q`

If runtime makes the full suite impractical, run the largest relevant subsets
and state exactly what was and was not executed; do not replace the true
cross-process test with same-process coverage.

- [ ] **Step 5: Invoke verification-before-completion and inspect the final diff**

Check:

```bash
git diff --check
git status --short
git diff --stat
git diff -- apps/api/jarvis_api/routes core/services \
  apps/jarvis-desk/src apps/mobile/src tests DEVLOG.md STATUS.md docs/superpowers
```

Confirm no secrets, message contents, generated build outputs, unrelated user
changes, or per-token persistent writes entered the diff.

- [ ] **Step 6: Request a code review and address only verified findings**

Use the requesting-code-review workflow on the complete uncommitted diff. For
each finding, use receiving-code-review before changing code. Re-run the owning
test after every accepted fix and the targeted suite after all fixes.

- [ ] **Step 7: Create the single attributed commit**

Stage only the intended paths, listing each explicit path, then run:

```bash
/opt/conda/envs/ai/bin/python scripts/install_git_hooks.py --check
python scripts/commit_with_attribution.py --repo . --actor codex \
  --origin interactive --approved-by bjorn \
  --message 'fix(streaming): restore cross-process autonomous run reattachment' \
  --path apps/api/jarvis_api/app.py \
  --path apps/api/jarvis_api/routes/chat.py \
  --path apps/api/jarvis_api/routes/chat_run_streams.py \
  --path apps/api/jarvis_api/routes/internal_run_stream.py \
  --path core/services/in_flight_runs.py \
  --path core/services/run_stream_locator.py \
  --path core/services/run_stream_proxy.py \
  --path core/services/autonomous_frame_relay.py \
  --path core/services/visible_autonomous_run.py \
  --path core/services/autonomous_stream_run.py \
  --path apps/jarvis-desk/src/lib/api.ts \
  --path apps/jarvis-desk/src/lib/api.test.ts \
  --path apps/jarvis-desk/src/contexts/StreamContext.tsx \
  --path apps/jarvis-desk/src/contexts/StreamContext.test.tsx \
  --path apps/mobile/src/lib/streamClient.ts \
  --path apps/mobile/src/lib/streamClient.test.ts \
  --path apps/mobile/src/state/StreamContext.tsx \
  --path apps/mobile/src/state/StreamContext.test.tsx \
  --path apps/mobile/src/screens/ChatScreen.tsx \
  --path tests/test_chat_run_stream_route_extraction.py \
  --path tests/test_run_stream_locator.py \
  --path tests/test_autonomous_entrypoint_streaming.py \
  --path tests/test_chat_run_stream_routes.py \
  --path tests/test_run_stream_authorization.py \
  --path tests/test_cross_process_run_stream.py \
  --path tests/test_stream_presence_independence.py \
  --path DEVLOG.md --path STATUS.md \
  --path docs/superpowers/specs/2026-10-14-cross-process-autonomous-stream-reattachment-design.md \
  --path docs/superpowers/plans/2026-10-14-cross-process-autonomous-stream-reattachment.md
```

Do not use raw `git commit`, `--no-verify`, rebase, or a second commit.
