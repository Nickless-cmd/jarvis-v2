# Desk Live Tool and Background Job Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stream bounded tool and background-job output into Jarvis Desk for work on both the server and the operator machine, with replay-safe state and concrete terminal errors.

**Architecture:** Reuse the existing visible-tool `tool_output_delta` path, and add a process-local bounded job-event hub plus an authenticated SSE projection for background work. Desk consumes the job stream into a small keyed reducer; `/api/jobs` remains the canonical snapshot and reconnect fallback, while source adapters tail only incremental bytes for server and operator background logs.

**Tech Stack:** Python 3.11, FastAPI/StreamingResponse, asyncio, existing Jarvis event/tool telemetry, React 19, TypeScript, Vitest/Testing Library, SSE over authenticated `fetch`.

**Spec:** `docs/superpowers/specs/2026-10-11-desk-live-tool-and-job-output-design.md`

## Global Constraints

- Jarvis Desk only; do not modify `apps/mobile/` or produce an APK.
- `/api/jobs` and existing registries/log files remain sources of truth; the live hub is a lossy projection, not durable job state.
- Enforce owner authentication and server-side `session_id` filtering before emitting output.
- Bound replay queues, pending subscriber queues and each UI job tail; Desk's per-job output ceiling is exactly 65,536 characters.
- Never allow a slow subscriber to block a command or producer thread.
- Render streamed output inertly; no Markdown or HTML interpretation.
- Preserve explicit `bridge_ok=false`/unknown semantics for the operator machine.
- Use `scripts/commit_with_attribution.py`; do not call raw `git commit`.
- Enable `live_tool_output_enabled` in live runtime only after tests and E2E prove the complete path.

## Review Focus

- A remote bridge outage while server jobs continue: test that server rows remain and operator rows become stale/unknown rather than disappearing.
- A job that starts and exits before the former ten-second poll: test that start and terminal events remain visible in the finished projection.
- Reconnect with a replayed output event: test that per-job `seq` prevents duplicate text.
- Output faster than the client can consume: test bounded dropping, explicit truncation and preservation of the terminal event.
- Session-bound events with a mismatched `session_id`: test that neither metadata nor output crosses conversation boundaries.

---

### Task 1: Complete Live Output in the Desk Row Transcript

**Files:**
- Modify: `apps/jarvis-desk/src/components/rich/raekkeKroppe.tsx`
- Modify: `apps/jarvis-desk/src/components/rich/RaekkeTranskript.tsx`
- Modify: `apps/jarvis-desk/src/components/rich/RaekkeTranskript.test.tsx`
- Modify: `apps/jarvis-desk/src/components/rich/raekkeKroppe.test.tsx`

**Interfaces:**
- Consumes: `ContentBlock.liveOutput`, `ContentBlock.liveOutputTruncated`, `ContentBlock.status` from the existing `streamReducer`.
- Produces: `kropFor(..., live?: { partialJson?: string; running?: boolean; output?: string; truncated?: boolean; elapsedMs?: number })` and a terminal body that shows live output before the final result.

- [ ] **Step 1: Write failing row-transcript tests**

Add focused tests proving the existing reducer-owned live output reaches the expanded row body:

```tsx
it('viser live stdout i den åbne række før tool-resultatet findes', () => {
  const blocks: ContentBlock[] = [{
    type: 'tool_use', id: 'b1', name: 'operator_bash', input: { command: 'python slow.py' },
    status: 'running', liveOutput: 'trin 1\ntrin 2\n', liveOutputSeq: 2,
  }]
  const { container } = render(<RaekkeTranskript blocks={blocks} streaming />)
  fireEvent.click(container.querySelector('.rv-arbejdsknap')!)
  fireEvent.click(container.querySelector('.rv-r[data-foldbar]')!)
  expect(container.querySelector('.rv-term pre')?.textContent).toContain('trin 2')
  expect(container.querySelector('.rv-term pre')?.textContent).not.toContain('Kører…')
})

it('viser at den levende hale er afkortet', () => {
  const blocks: ContentBlock[] = [{
    type: 'tool_use', id: 'b1', name: 'bash', input: { command: 'yes' },
    status: 'running', liveOutput: 'seneste hale', liveOutputSeq: 99,
    liveOutputTruncated: true,
  }]
  const { container } = render(<RaekkeTranskript blocks={blocks} streaming />)
  fireEvent.click(container.querySelector('.rv-arbejdsknap')!)
  fireEvent.click(container.querySelector('.rv-r[data-foldbar]')!)
  expect(container.textContent).toContain('live output afkortet')
})
```

Add a `kropFor` test for a silent running command that expects
`Kører stadig · intet output endnu` rather than bare `Kører…`.

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
cd apps/jarvis-desk
npx vitest run src/components/rich/RaekkeTranskript.test.tsx src/components/rich/raekkeKroppe.test.tsx
```

Expected failures: live text is absent because `RaekkeTranskript` does not pass it to `kropFor`, and the silent-state copy is still `Kører…`.

- [ ] **Step 3: Implement the minimal transcript plumbing**

Extend the `live` argument in `kropFor`, select `live.output ?? ud` while running, pass `b.liveOutput` and `b.liveOutputTruncated` from `RaekkeTranskript`, and render the truncation note in the terminal body. Preserve the final normalized result as authoritative once `status` is terminal.

- [ ] **Step 4: Run focused and reducer tests GREEN**

Run:

```bash
cd apps/jarvis-desk
npx vitest run src/components/rich/RaekkeTranskript.test.tsx src/components/rich/raekkeKroppe.test.tsx src/lib/streamReducer.test.ts
```

Expected: all pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add -- apps/jarvis-desk/src/components/rich/raekkeKroppe.tsx apps/jarvis-desk/src/components/rich/RaekkeTranskript.tsx apps/jarvis-desk/src/components/rich/RaekkeTranskript.test.tsx apps/jarvis-desk/src/components/rich/raekkeKroppe.test.tsx
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'stream tool output in desk row transcript' --path apps/jarvis-desk/src/components/rich/raekkeKroppe.tsx --path apps/jarvis-desk/src/components/rich/RaekkeTranskript.tsx --path apps/jarvis-desk/src/components/rich/RaekkeTranskript.test.tsx --path apps/jarvis-desk/src/components/rich/raekkeKroppe.test.tsx
```

### Task 2: Build the Bounded Live Job Event Hub

**Files:**
- Create: `core/services/live_job_events.py`
- Create: `tests/test_live_job_events.py`

**Interfaces:**
- Produces: `publish(event_type: str, *, job_key: str, session_id: str, source: str, payload: dict) -> JobEvent`, `subscribe(*, session_id: str, after: int | None, queue_size: int = 128) -> JobSubscription`, `snapshot_cursor() -> int`, and `reset_for_tests() -> None`.
- `JobSubscription` exposes `initial_events: list[JobEvent]`, `queue: asyncio.Queue[JobEvent]`, `needs_snapshot: bool`, and `close() -> None`.

- [ ] **Step 1: Write failing event-hub tests**

Cover monotonic cursors, bounded replay, session filtering and backpressure:

Define `drain_nowait(queue)` in the test file as a loop over `get_nowait()`
until `asyncio.QueueEmpty`; it is test-only and does not enter production code.

```python
def test_replay_returns_only_events_after_cursor():
    first = hub.publish("job_started", job_key="tool:a", session_id="s1", source="tool", payload={})
    second = hub.publish("job_output", job_key="tool:a", session_id="s1", source="tool", payload={"seq": 1, "chunk": "a"})
    sub = hub.subscribe(session_id="s1", after=first.cursor)
    assert [event.cursor for event in sub.initial_events] == [second.cursor]

def test_mismatched_session_receives_no_event():
    sub = hub.subscribe(session_id="s2", after=None)
    hub.publish("job_output", job_key="tool:a", session_id="s1", source="tool", payload={"seq": 1, "chunk": "secret"})
    assert sub.queue.empty()

def test_slow_subscriber_drops_output_but_keeps_finish():
    sub = hub.subscribe(session_id="s1", after=None, queue_size=2)
    for seq in range(1, 5):
        hub.publish("job_output", job_key="tool:a", session_id="s1", source="tool",
                    payload={"seq": seq, "chunk": str(seq)})
    hub.publish("job_finished", job_key="tool:a", session_id="s1", source="tool",
                payload={"status": "exited", "exit_code": 0})
    delivered = drain_nowait(sub.queue)
    assert delivered[-1].event_type == "job_finished"
    assert delivered[-1].payload["output_truncated"] is True
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest -q tests/test_live_job_events.py`

Expected failure: module does not exist.

- [ ] **Step 3: Implement the hub**

Use immutable `JobEvent` dataclasses, a locked `deque(maxlen=512)` replay ring and per-subscriber `asyncio.Queue(maxsize=128)`. Schedule queue writes with the subscriber's owning loop using `call_soon_threadsafe`. On pressure, evict only older `job_output` entries, mark the next event `output_truncated`, and preserve `job_started`, `job_finished` and `source_status`. A stale `after` cursor sets `needs_snapshot=True` rather than returning a partial replay.

- [ ] **Step 4: Run hub tests GREEN**

Run: `pytest -q tests/test_live_job_events.py`

Expected: all pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add -- core/services/live_job_events.py tests/test_live_job_events.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'add bounded live job event hub' --path core/services/live_job_events.py --path tests/test_live_job_events.py
```

### Task 3: Fan Out Tool Lifecycle, Output and Concrete Failures

**Files:**
- Create: `core/services/tool_failure_surface.py`
- Modify: `core/services/tool_execution_trace.py`
- Modify: `core/services/visible_tool_exec.py`
- Modify: `core/services/tool_chip_payload.py`
- Modify: `tests/test_tool_output_backpressure.py`
- Create: `tests/test_tool_failure_surface.py`

**Interfaces:**
- Consumes: real tool-use ID, run/session identity, source tool name, stdout/stderr deltas and raw tool result.
- Produces: `normalise_tool_failure(status: str, result_text: str, raw_result: object, *, timeout_s: float | None = None) -> str` and live-job events keyed by the real tool-use ID.

- [ ] **Step 1: Write failing tool fan-out tests**

Extend `test_tool_output_backpressure.py` so an emitted output delta appears both in the existing visible buffer and as `job_output` with the same `tool_use_id`, stream, sequence and session. Assert an `operator_bash` call maps to `tool_operator`, while `bash` maps to `tool`.

Create failure tests:

```python
def test_timeout_has_a_visible_cause():
    assert normalise_tool_failure("error", "", {"status": "error", "error": "timeout"}, timeout_s=120) == "Timeout efter 120 sekunder"

def test_nonzero_exit_keeps_stderr():
    text = normalise_tool_failure("error", "", {"exit_code": 2, "stderr": "fil mangler"})
    assert "exit code 2" in text and "fil mangler" in text
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
pytest -q tests/test_tool_output_backpressure.py tests/test_tool_failure_surface.py
```

Expected failures: no job fan-out and no failure normalizer.

- [ ] **Step 3: Implement tool lifecycle publishing**

Extend `_ExecutionBinding` with `run_id`, `session_id` and `tool_name`. Publish `job_started` when `visible_tool_exec` announces the call, publish `job_output` from `emit_current_output` after the existing bounded-buffer write, and publish exactly one `job_finished` from `surface_result`/`cancel_call`. Keep publisher calls non-blocking and fail-soft so observability cannot break execution.

Normalize empty error results in `build_tool_capability_payload` before SSE emission. Include status, exit code and concrete text in the terminal live-job payload. Do not alter successful result formatting.

- [ ] **Step 4: Run tool tests GREEN**

Run:

```bash
pytest -q tests/test_tool_output_backpressure.py tests/test_tool_failure_surface.py tests/test_visible_runs_sse_v2.py
```

Expected: all pass and existing visible-stream payloads remain compatible.

- [ ] **Step 5: Commit Task 3**

```bash
git add -- core/services/tool_failure_surface.py core/services/tool_execution_trace.py core/services/visible_tool_exec.py core/services/tool_chip_payload.py tests/test_tool_output_backpressure.py tests/test_tool_failure_surface.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'publish live tool lifecycle and concrete failures' --path core/services/tool_failure_surface.py --path core/services/tool_execution_trace.py --path core/services/visible_tool_exec.py --path core/services/tool_chip_payload.py --path tests/test_tool_output_backpressure.py --path tests/test_tool_failure_surface.py
```

### Task 4: Add Incremental Server and Operator Background Sources

**Files:**
- Create: `core/services/live_job_sources.py`
- Modify: `core/services/process_supervisor.py`
- Modify: `core/tools/operator_background.py`
- Create: `tests/test_live_job_sources.py`
- Modify: `tests/test_operator_background.py`

**Interfaces:**
- Produces: `read_process_log_since(name: str, offset: int, max_bytes: int = 32768) -> dict`, `read_many_async(*, offsets: dict[str, int], user_id: str, max_bytes_per_job: int = 32768) -> dict`, and `LiveJobSourcePump.sample_once() -> None`.
- Consumes: canonical `/api/jobs` snapshot rows for discovery, process-supervisor logs, and `/tmp/jarvis-bg/<id>.{log,pid,rc}` through one operator bridge call.

- [ ] **Step 1: Write failing incremental-source tests**

Test local log offsets, remote multi-job parsing, short completion and bridge outage:

```python
def test_process_log_since_returns_only_new_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(process_supervisor, "_PROC_DIR", tmp_path)
    (tmp_path / "worker.log").write_bytes(b"a\nb\n")
    first = process_supervisor.read_process_log_since("worker", 0)
    with (tmp_path / "worker.log").open("ab") as fh:
        fh.write(b"c\n")
    second = process_supervisor.read_process_log_since("worker", first["offset"])
    assert second["output"] == "c\n"

@pytest.mark.asyncio
async def test_operator_read_many_returns_output_and_exit(monkeypatch):
    async def fake_bash_async(**_kwargs):
        return {"stdout": "__JBG_META__ bg_aaaaaaaaaaaa 2 1 -\nYQ==\n__JBG_END__\n"
                          "__JBG_META__ bg_bbbbbbbbbbbb 4 0 3\nYm9vbQ==\n__JBG_END__\n"}
    monkeypatch.setattr("core.tools.operator_tools.operator_bash_async", fake_bash_async)
    result = await operator_background.read_many_async(
        offsets={"bg_aaaaaaaaaaaa": 1, "bg_bbbbbbbbbbbb": 0}, user_id="owner")
    assert result["jobs"]["bg_aaaaaaaaaaaa"]["output"] == "a"
    assert result["jobs"]["bg_bbbbbbbbbbbb"]["exit_code"] == 3

def test_short_job_emits_started_output_finished_in_one_sample():
    pump = pump_with_sample(job(status="exited", exit_code=0), output="done\n")
    pump.sample_once()
    assert [event.event_type for event in captured_events()] == [
        "job_started", "job_output", "job_finished",
    ]

def test_bridge_failure_marks_operator_unknown_and_keeps_server_events():
    pump = pump_with_server_job_and_broken_bridge()
    pump.sample_once()
    events = captured_events()
    assert any(event.source == "supervisor" for event in events)
    assert any(event.event_type == "source_status"
               and event.source == "operator"
               and event.payload["healthy"] is False for event in events)
```

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest -q tests/test_live_job_sources.py tests/test_operator_background.py`

Expected failures: incremental APIs and pump do not exist.

- [ ] **Step 3: Implement bounded source adapters**

Add byte-offset local reads to `process_supervisor` without changing `tail_process_log`. Add one framed/base64-safe `read_many_async` bridge command to `operator_background` so pipes, newlines and arbitrary UTF-8 cannot corrupt metadata parsing. Cap each sample and signal truncation.

Implement `LiveJobSourcePump` with per-job offsets and last-seen state. While at least one subscriber exists, sample local sources every 250 ms and operator sources every 750 ms; stop when the final subscriber closes. Emit start before output and finish before eviction. Reconcile with `background_jobs.liste` on startup and every 30 seconds, not every ten seconds. Use the job hub only as output; do not persist a parallel registry.

- [ ] **Step 4: Run source tests GREEN**

Run:

```bash
pytest -q tests/test_live_job_sources.py tests/test_operator_background.py tests/test_background_jobs.py tests/test_background_jobs_tool_kilde.py
```

Expected: all pass.

- [ ] **Step 5: Commit Task 4**

```bash
git add -- core/services/live_job_sources.py core/services/process_supervisor.py core/tools/operator_background.py tests/test_live_job_sources.py tests/test_operator_background.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'stream incremental server and operator job logs' --path core/services/live_job_sources.py --path core/services/process_supervisor.py --path core/tools/operator_background.py --path tests/test_live_job_sources.py --path tests/test_operator_background.py
```

### Task 5: Expose the Authenticated Replayable Jobs SSE Route

**Files:**
- Modify: `apps/api/jarvis_api/routes/jarvisx_processes.py`
- Create: `tests/test_jarvisx_jobs_stream.py`

**Interfaces:**
- Produces: `GET /api/jobs/stream?session_id=<id>&after=<cursor>` as `text/event-stream` with `id`, `event` and JSON `data` lines.
- Consumes: `live_job_events.subscribe`, `background_jobs.liste` for canonical snapshot and `LiveJobSourcePump` subscriber lifetime.

- [ ] **Step 1: Write failing route tests**

Build a small FastAPI app containing the route and override owner auth. Assert:

Define test-local `publish_test_event(...)` through `live_job_events.publish`
and `read_sse_frames(...)` as a bounded parser over `TestClient.stream`; neither
helper is a production interface.

```python
def test_stream_starts_with_snapshot_and_cursor(client, monkeypatch):
    # first frame event == "snapshot" and contains jobs, bridge_ok and cursor

def test_after_cursor_replays_only_missed_events(client, monkeypatch):
    first = publish_test_event("job_started", cursor=None)
    second = publish_test_event("job_output", cursor=None)
    frames = read_sse_frames(client, f"/api/jobs/stream?after={first.cursor}", count=1)
    assert frames[0]["id"] == str(second.cursor)

def test_session_filter_hides_other_conversation(client, monkeypatch):
    publish_test_event("job_output", session_id="s-other")
    frames = read_sse_frames(client, "/api/jobs/stream?session_id=s-current", count=1)
    assert frames[0]["event"] == "snapshot"
    assert "s-other" not in frames[0]["data"]

def test_unauthenticated_stream_is_rejected(client):
    # expect 401/403 before StreamingResponse begins
```

- [ ] **Step 2: Run route tests and verify RED**

Run: `pytest -q tests/test_jarvisx_jobs_stream.py`

Expected: 404 or missing route.

- [ ] **Step 3: Implement the route**

Authorize before creating the generator. Resolve resume cursor from `after` first, then `Last-Event-ID`. Emit a canonical snapshot if requested or if replay expired, replay ordered events, send heartbeat every 15 seconds, and close the subscription/pump in `finally`. Set `Cache-Control: no-cache`, `X-Accel-Buffering: no` and `Connection: keep-alive`.

- [ ] **Step 4: Run route and security tests GREEN**

Run:

```bash
pytest -q tests/test_jarvisx_jobs_stream.py tests/test_api_security.py tests/test_files_signed_link.py
```

Expected: all pass.

- [ ] **Step 5: Commit Task 5**

```bash
git add -- apps/api/jarvis_api/routes/jarvisx_processes.py tests/test_jarvisx_jobs_stream.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'expose replayable background jobs stream' --path apps/api/jarvis_api/routes/jarvisx_processes.py --path tests/test_jarvisx_jobs_stream.py
```

### Task 6: Replace Desk Job Polling with a Live Projection

**Files:**
- Create: `apps/jarvis-desk/src/lib/jobsStream.ts`
- Create: `apps/jarvis-desk/src/lib/liveJobs.ts`
- Create: `apps/jarvis-desk/src/lib/liveJobs.test.ts`
- Modify: `apps/jarvis-desk/src/lib/jobsApi.ts`
- Modify: `apps/jarvis-desk/src/components/shell/JobsPanel.tsx`
- Modify: `apps/jarvis-desk/src/components/shell/JobsPanel.test.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css`

**Interfaces:**
- Produces: `startJobsStream(config, { sessionId, after, onEvent, onError }): { abort(): void }`, pure `applyJobEvent(state, event)`, and expandable live-output job rows.
- Consumes: snapshot and delta events from `/api/jobs/stream`; `listJobs` only for initial/recovery reconciliation after stream failure or visibility resume.

- [ ] **Step 1: Write failing pure reducer tests**

In `liveJobs.test.ts`, assert start/upsert, output append, duplicate-sequence rejection, 65,536-character tail cap, finish retention and snapshot replacement:

```ts
it('ignorerer replayet output med samme seq', () => {
  let s = fromSnapshot({ jobs: [running], bridge_ok: true }, 10)
  s = applyJobEvent(s, output('tool:x', 1, 'a'))
  s = applyJobEvent(s, output('tool:x', 1, 'a'))
  expect(s.byKey['tool:x'].liveOutput).toBe('a')
})

it('beholder et kort job som færdigt', () => {
  let s = emptyLiveJobs()
  s = applyJobEvent(s, started(fast))
  s = applyJobEvent(s, finished('tool:x', { status: 'exited', exit_code: 0 }))
  expect(s.byKey['tool:x'].status).toBe('exited')
})
```

- [ ] **Step 2: Write failing JobsPanel behavior tests**

Mock `startJobsStream`. Prove that mounting opens one stream, an event updates output without advancing timers, unmount aborts it, a stream error performs one snapshot recovery, and the former ten-second recurring poll no longer runs. Add UI tests for expand/collapse, live stdout, `nyt output`, concrete failure and `Din maskine`/`Server` labels.

- [ ] **Step 3: Run Desk tests and verify RED**

Run:

```bash
cd apps/jarvis-desk
npx vitest run src/lib/liveJobs.test.ts src/components/shell/JobsPanel.test.tsx
```

Expected failures: modules and live behavior do not exist; polling expectations still describe the old behavior.

- [ ] **Step 4: Implement authenticated fetch-SSE client and projection**

Reuse the bounded frame parsing rules from `streamClient.ts`, but keep the job protocol in `jobsStream.ts`. Send the bearer token in headers, persist the latest cursor in memory, reconnect with backoff and pass `after`. Reject oversized/malformed frames with a typed error and abort cleanly.

Keep state mechanics in `liveJobs.ts`, not `JobsPanel.tsx`. Update `BackgroundJob` with optional `job_key`, `error`, `finished_at`, `liveOutput`, `liveOutputSeq`, `liveOutputTruncated` and `stale`. In `JobsPanel`, remove the ten-second interval, open/close the stream with component lifetime and reconcile through `listJobs` only on initial load, visibility resume and terminal stream failure.

Render output in an inert `<pre>`. Auto-follow only when already at the bottom; otherwise show a `Nyt output` button. Show `Kører stadig · intet output endnu` for silent jobs and concrete terminal cause for failures.

- [ ] **Step 5: Run focused Desk tests GREEN**

Run:

```bash
cd apps/jarvis-desk
npx vitest run src/lib/liveJobs.test.ts src/components/shell/JobsPanel.test.tsx src/components/rich/RaekkeTranskript.test.tsx src/lib/streamReducer.test.ts
npm run build:renderer
```

Expected: all tests and TypeScript build pass.

- [ ] **Step 6: Commit Task 6**

```bash
git add -- apps/jarvis-desk/src/lib/jobsStream.ts apps/jarvis-desk/src/lib/liveJobs.ts apps/jarvis-desk/src/lib/liveJobs.test.ts apps/jarvis-desk/src/lib/jobsApi.ts apps/jarvis-desk/src/components/shell/JobsPanel.tsx apps/jarvis-desk/src/components/shell/JobsPanel.test.tsx apps/jarvis-desk/src/styles/app.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'stream live background jobs in desk' --path apps/jarvis-desk/src/lib/jobsStream.ts --path apps/jarvis-desk/src/lib/liveJobs.ts --path apps/jarvis-desk/src/lib/liveJobs.test.ts --path apps/jarvis-desk/src/lib/jobsApi.ts --path apps/jarvis-desk/src/components/shell/JobsPanel.tsx --path apps/jarvis-desk/src/components/shell/JobsPanel.test.tsx --path apps/jarvis-desk/src/styles/app.css
```

### Task 7: Full Verification, Live Rollout, Deploy and E2E

**Files:**
- Runtime-only change after green verification: `~/.jarvis-v2/config/runtime.json` on `bs@10.0.0.39`
- Build output (not committed): `apps/jarvis-desk/dist-web/` on `bs@10.0.0.39`

**Interfaces:**
- Consumes: complete backend/Desk implementation and live operator bridge.
- Produces: verified deployment with `live_tool_output_enabled=true`; no repository secret/config artifact.

- [ ] **Step 1: Run the complete relevant backend suite**

Run:

```bash
pytest -q tests/test_live_job_events.py tests/test_tool_output_backpressure.py tests/test_tool_failure_surface.py tests/test_live_job_sources.py tests/test_operator_background.py tests/test_background_jobs.py tests/test_background_jobs_tool_kilde.py tests/test_jarvisx_jobs_stream.py tests/test_visible_runs_sse_v2.py
python -m compileall core apps/api scripts
```

Expected: all pass; compileall exits 0.

- [ ] **Step 2: Run the complete Desk suite and build**

Run:

```bash
cd apps/jarvis-desk
npm test
npm run lint
npm run build
```

Expected: all tests pass, lint exits 0 and renderer/electron builds complete.

- [ ] **Step 3: Inspect diff and run repository guards**

Run:

```bash
git status --short
git diff --check HEAD~6..HEAD
/opt/conda/envs/ai/bin/python scripts/install_git_hooks.py --check
```

Expected: only intended files changed, no whitespace errors, hooks valid.

- [ ] **Step 4: Push and deploy with the repository's safe procedures**

First run `git status --short`, `git branch --show-current` and
`git fetch origin`; require a clean tree and resolve upstream divergence without
rewriting committed attribution. Then run:

```bash
git push origin main
ssh bs@10.0.0.39 'cd /media/projects/jarvis-v2 && git status --short && git pull --ff-only origin main && scripts/build_desk_web.sh'
scripts/genstart_sikkert.sh jarvis-api jarvis-runtime
ssh bs@10.0.0.39 'systemctl is-active jarvis-api jarvis-runtime && journalctl -u jarvis-api -u jarvis-runtime --since "5 minutes ago" --no-pager -n 200'
```

Do not pull over a dirty live checkout. The safe restart script must report no
active visible run before restarting; do not set `VENT=0`.

- [ ] **Step 5: Enable the live-output rollout flag without exposing runtime secrets**

Use a small Python JSON update on the live host that changes only:

```json
{"live_tool_output_enabled": true}
```

Read back only that boolean, never the full runtime configuration. If `load_settings()` does not hot-reload this field, perform the same bounded service restart and recheck health.

- [ ] **Step 6: Run live server and operator E2E**

From an owner Desk session, run one server command and one operator command that each emit three delayed lines, followed by a failing command. Verify through the actual `/api/jobs/stream` and Desk UI that:

1. every delayed line appears before process completion;
2. source labels are `Server` and `Din maskine` respectively;
3. terminal exit state replaces running state without duplicating output;
4. the failing command shows its concrete exit/error cause; and
5. a detached sub-ten-second job remains under `Færdige`.

Capture event timestamps and compare first-output time with finish time; first output must precede finish for both machines.

- [ ] **Step 7: Run reconnect and bridge-loss E2E**

Disconnect and reconnect the Desk job stream mid-command by aborting only the
browser request and allowing its normal reconnect path to run. Verify cursor
replay adds no duplicate line. For bridge loss, invoke the source adapter's
tested fail-soft path against an intentionally unreachable test bridge target;
do not stop the live operator bridge or unrelated services. Confirm server jobs
remain visible while the operator source reads unknown/stale.

- [ ] **Step 8: Final repository and deployment audit**

Run `git status --short`, confirm the remote deployed commit equals local `HEAD`, verify services active, and record test counts plus E2E timings in the final user report. Do not claim completion if any required suite, build, service health check or either-machine E2E is red.
