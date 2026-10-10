# Tool Latency and Live Shell Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure where every visible shell call waits, show bounded stdout/stderr in its existing Desk card while it runs, and settle the card before the next prompt is assembled.

**Architecture:** Extend the existing visible-tool lifecycle instead of adding a second job model: `working_step` still creates the card, an ephemeral `tool_output_delta` system event updates it, and the canonical capability result settles it. A focused execution trace joins timings across the persistent shell, operator bridge, and result-publication boundary; the existing prompt cache gains keyed hit/miss telemetry, while the existing bridge HTTP forwarder becomes optionally NDJSON-streaming so output survives the API/runtime process split.

**Tech Stack:** Python 3.11, asyncio/threading, Unix-domain newline JSON, FastAPI/HTTPX/WebSocket, Electron/Node child processes, React/TypeScript, Vitest, pytest, SQLite eventbus.

**Spec:** `docs/superpowers/specs/2026-10-10-tool-latency-and-live-output-design.md`

## Global Constraints

- The final tool result remains the canonical persisted result; live chunks are an ephemeral projection and are never written to SQLite or chat history.
- Emit at most one live frame per call per 75 ms or 8 KiB, whichever happens first.
- Desk retains at most the latest 64 KiB per running call and visibly marks truncation.
- `tool_execution_timing_enabled` defaults to `true`; `live_tool_output_enabled` defaults to `false` for the first deployment.
- Protocol readers accept legacy final-only responses and the new delta-plus-final framing during rollout.
- A stream failure or dropped delta never changes command success, failure, cancellation, or final-result delivery.
- Do not stream partial tool output into the model.
- Do not route foreground calls through the existing background-shell polling API; its lifecycle and persistence semantics remain unchanged.
- Use `core.services.terminal_sanitize` for terminal control-code removal; do not add a second sanitizer.
- Use `system_event(kind="tool_output_delta")` and the existing `tool_use` block; do not add a parallel progress/content model.
- Respect the Boy Scout rule before changing logic in `prompt_contract.py`, `visible_runs.py`, or Electron's `bridge.ts`.
- Stage only paths owned by the task. Do not stage the unrelated untracked `apps/jarvis-desk/src/styles/message-rail.css`.
- Commit through `python scripts/commit_with_attribution.py`, never raw `git commit`.

## Review Focus

- UTF-8 and ANSI sequences split across transport chunks must render without replacement glyphs, leaked escape fragments, or executable markup; Task 3 and Task 7 pin this.
- Output floods must not block the command or final result; Task 1 and Task 5 pin bounded lossy projection behavior.
- Duplicate, out-of-order, unknown, and post-terminal deltas must be ignored; Task 4 and Task 7 pin correlation and reducer behavior.
- Mixed bridge/runtime versions and API/runtime process separation must retain final-only compatibility and deliver deltas when both sides support them; Task 3 and Task 4 pin both paths.
- Concurrent persistent-shell calls and concurrent prompt-cache misses must be measured honestly without introducing a single-flight/cross-process cache change; Task 2, Task 3, and Task 8 pin/report this.

## Existing-surface reuse decisions

- Keep `progress` blocks for persisted semantic narration. Raw output is transient and uses the already-supported arbitrary `system_event` envelope.
- Keep `working_step` as the only card-creation event and capability/tool-result as the only terminal authority.
- Extend `prompt_assembly_telemetri.py`, `turn_trace.py`, `tool_call_telemetry.py`, `terminal_sanitize.py`, and `jarvisx_bridge.py`; do not create competing telemetry, trace, sanitizer, or bridge registries.
- Reuse `correlation_id` across Electron WebSocket dispatch and the existing internal HTTP forwarder.
- Keep `operator_background.py` unchanged: it remains the explicit detached-job API, not the foreground streaming implementation.

---

### Task 1: Execution timing and bounded live-output primitives

**Files:**
- Create: `core/services/tool_execution_trace.py`
- Modify: `core/runtime/settings.py`
- Modify: `core/tools/tool_call_telemetry.py`
- Test: `tests/test_tool_execution_trace.py`
- Test: `tests/test_settings.py`
- Test: `tests/test_tool_call_telemetry.py`

**Interfaces:**
- Consumes: existing `event_bus.publish`, `RuntimeSettings`, and root-level run/tool identifiers already stamped into tool arguments.
- Produces: `start_call(tool_use_id, *, tool, run_id, announced_at=None)`, `bind_execution(tool_use_id, output_buffer)`, `mark_dispatch(tool_use_id)`, `mark_execution_complete(tool_use_id)`, `note_executor_timing(tool_use_id, timing)`, `surface_result(tool_use_id, *, status, exit_code=None)`, `cancel_call(tool_use_id)`, `emit_current_output(stream, chunk, seq=None)`, and `BoundedOutputBuffer.drain()`.

- [ ] **Step 1: Write failing settings and trace tests**

```python
def test_rollout_defaults_are_explicit():
    s = RuntimeSettings()
    assert s.tool_execution_timing_enabled is True
    assert s.live_tool_output_enabled is False

def test_surface_publishes_exactly_one_summary(monkeypatch):
    sent = []
    monkeypatch.setattr(bus.event_bus, "publish", lambda kind, payload: sent.append((kind, payload)))
    trace.start_call("t1", tool="bash", run_id="r1", announced_at=10.0)
    trace.mark_dispatch("t1", now=10.025)
    trace.note_executor_timing("t1", {"route": "server_persistent_shell", "dispatch_to_lock_ms": 40,
                                       "first_output_ms": 60, "process_ms": 90, "had_output": True})
    trace.surface_result("t1", status="ok", exit_code=0, now=10.150)
    trace.surface_result("t1", status="ok", exit_code=0, now=10.200)
    assert [kind for kind, _ in sent] == ["tool.execution_timing"]
    assert sent[0][1]["announced_to_dispatch_ms"] == 25
    assert sent[0][1]["total_visible_ms"] == 150
```

Also pin that a disabled timing flag emits nothing, unknown IDs fail soft, and `byg_completed_payload` remains byte-compatible for its existing keys.

- [ ] **Step 2: Run the tests and verify the new API is absent**

Run: `pytest -q tests/test_tool_execution_trace.py tests/test_settings.py tests/test_tool_call_telemetry.py`

Expected: failures for missing settings fields/module/functions; existing telemetry tests remain green.

- [ ] **Step 3: Implement the focused trace and output buffer**

```python
@dataclass(frozen=True, slots=True)
class OutputDelta:
    tool_use_id: str
    stream: str
    seq: int
    chunk: str
    truncated: bool = False

class BoundedOutputBuffer:
    def __init__(self, max_frames: int = 128, max_pending_chars: int = 64 * 1024): ...
    def put(self, delta: OutputDelta) -> None: ...   # non-blocking; coalesce or drop oldest
    def drain(self) -> list[OutputDelta]: ...

@contextmanager
def bind_execution(tool_use_id: str, output_buffer: BoundedOutputBuffer | None): ...

def emit_current_output(stream: str, chunk: str, seq: int | None = None) -> None: ...
```

Use a lock-protected process-local trace map keyed by `tool_use_id`, monotonic clocks only, and a ContextVar solely for the current execution binding. Publish the durable summary through a new self-safe `udgiv_execution_timing(payload)` in `tool_call_telemetry.py`, so all durable tool-event publication retains one owner.

`mark_execution_complete` records when the server-side executor receives the terminal result. `surface_result` derives `process_exit_to_result_emit_ms` from that point without subtracting clocks across machines; executor-local `process_ms`, spawn/lock wait, and first-output durations arrive through `note_executor_timing`.

The terminal payload contains `tool`, `run_id`, `tool_use_id`, `route`, `status`, `exit_code`, `had_output`, `announced_to_dispatch_ms`, `dispatch_to_lock_ms`, `dispatch_to_spawn_ms`, `first_output_ms`, `process_ms`, `process_exit_to_result_emit_ms`, and `total_visible_ms`; unavailable route-specific fields are `null`, never fabricated as zero.

- [ ] **Step 4: Pin lossy backpressure and thread safety**

```python
def test_output_flood_is_lossy_but_never_blocks():
    q = BoundedOutputBuffer(max_frames=2, max_pending_chars=12)
    for i in range(1000):
        q.put(OutputDelta("t1", "stdout", i, "abcdef"))
    drained = q.drain()
    assert len(drained) <= 2
    assert any(d.truncated for d in drained)
```

Add a two-thread producer test and assert final timing publication still succeeds after output drops.
Also assert `cancel_call` publishes one `status="cancelled"` summary and removes the trace so a worker's late completion cannot publish a second event.

- [ ] **Step 5: Run focused tests and commit**

Run: `pytest -q tests/test_tool_execution_trace.py tests/test_settings.py tests/test_settings_komplet.py tests/test_tool_call_telemetry.py`

```bash
git add -- core/services/tool_execution_trace.py core/runtime/settings.py core/tools/tool_call_telemetry.py tests/test_tool_execution_trace.py tests/test_settings.py tests/test_tool_call_telemetry.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat: add tool execution timing primitives' --path core/services/tool_execution_trace.py --path core/runtime/settings.py --path core/tools/tool_call_telemetry.py --path tests/test_tool_execution_trace.py --path tests/test_settings.py --path tests/test_tool_call_telemetry.py
```

### Task 2: Prompt-cache extraction and 6–33 second verification telemetry

**Files:**
- Create: `core/services/prompt_assembly_turn_cache.py`
- Modify: `core/services/prompt_contract.py:591-687`
- Modify: `core/services/prompt_assembly_telemetri.py`
- Modify: `core/services/visible_model.py:454-475,738-756`
- Modify: `core/services/turn_trace.py`
- Test: `tests/test_prompt_assembly_turn_cache.py`
- Test: `tests/test_prompt_assembly_telemetri.py`
- Test: `tests/test_prompt_contract_budget.py`

**Interfaces:**
- Consumes: `central_xproc.process_role()`, `os.getpid()`, existing `prompt.assembly_size`, and the current 180-second key `(session_id, latest_user_message_id, provider, model, name)`.
- Produces: `lookup(key, now) -> CacheLookup`, `store(key, value, now)`, `clear()`, `rapporter_cache_lookup(...)`, and optional `caller_phase` arguments defaulting to `"initial"` through `_build_visible_input` to `build_visible_chat_prompt_assembly`.

- [ ] **Step 1: Write failing cache outcome tests**

```python
def test_hit_miss_expired_and_unsafe_key_are_distinct(monkeypatch):
    cache.clear()
    assert cache.lookup(None, now=1).outcome == "unsafe_no_key"
    key = ("s", 7, "deepseek", "m", "default")
    assert cache.lookup(key, now=1).outcome == "miss"
    cache.store(key, "value", now=1)
    assert cache.lookup(key, now=2).outcome == "hit"
    assert cache.lookup(key, now=182).outcome == "expired"
```

Test that the emitted `prompt.assembly_cache` payload contains only an opaque `key_hash`, `cache_outcome`, `cache_age_ms`, `lookup_ms`, `build_ms`, `caller_phase`, `pid`, and `process_role`; it must not contain message text or a raw session ID.

- [ ] **Step 2: Run prompt tests and verify failure**

Run: `pytest -q tests/test_prompt_assembly_turn_cache.py tests/test_prompt_assembly_telemetri.py tests/test_prompt_contract_budget.py`

Expected: the extracted cache and `prompt.assembly_cache` publisher do not exist.

- [ ] **Step 3: Extract the turn cache before changing its behavior**

```python
@dataclass(frozen=True, slots=True)
class CacheLookup:
    outcome: Literal["hit", "miss", "unsafe_no_key", "expired"]
    value: Any = None
    age_ms: int | None = None

def lookup(key: tuple | None, *, now: float | None = None) -> CacheLookup: ...
def store(key: tuple, value: Any, *, now: float | None = None) -> None: ...
```

Move the cache dictionary, 180-second TTL, and 64-entry pruning policy into the new module without adding locking, single-flight, or cross-process state. Keep `_latest_user_msg_id` in `prompt_contract.py` because it owns chat-history key construction.

- [ ] **Step 4: Add telemetry around lookup/build and propagate caller phase**

```python
def rapporter_cache_lookup(*, key: tuple | None, outcome: str, cache_age_ms: int | None,
                           lookup_ms: float, build_ms: float | None,
                           caller_phase: str) -> None: ...

def build_visible_chat_prompt_assembly(..., caller_phase: str = "initial") -> PromptAssembly: ...
def _build_visible_input(..., caller_phase: str = "initial") -> list[dict]: ...
```

Emit one cache event for every wrapper call. Reuse `turn_trace.mark("prompt_cache", ...)` when tracing is active. Preserve `prompt.assembly_size` as the detailed miss/build event.

- [ ] **Step 5: Prove clustered calls remain measurable, not serialized**

Use two threads with a barrier and a deliberately slow builder. Assert both may report `miss` and both carry the same `key_hash`, distinct `pid/process_role` metadata as patched, and no single-flight behavior.

- [ ] **Step 6: Run focused tests and commit**

Run: `pytest -q tests/test_prompt_assembly_turn_cache.py tests/test_prompt_assembly_telemetri.py tests/test_prompt_contract_budget.py tests/test_prompt_contract.py`

```bash
git add -- core/services/prompt_assembly_turn_cache.py core/services/prompt_contract.py core/services/prompt_assembly_telemetri.py core/services/visible_model.py core/services/turn_trace.py tests/test_prompt_assembly_turn_cache.py tests/test_prompt_assembly_telemetri.py tests/test_prompt_contract_budget.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat: measure prompt assembly cache outcomes' --path core/services/prompt_assembly_turn_cache.py --path core/services/prompt_contract.py --path core/services/prompt_assembly_telemetri.py --path core/services/visible_model.py --path core/services/turn_trace.py --path tests/test_prompt_assembly_turn_cache.py --path tests/test_prompt_assembly_telemetri.py --path tests/test_prompt_contract_budget.py
```

### Task 3: Persistent server-shell and fallback streaming

**Files:**
- Modify: `core/tools/bash_session.py:199-285,463-577,728-770,810-834`
- Create: `core/tools/streaming_subprocess.py`
- Modify: `core/tools/simple_tools_web.py:533-727`
- Modify: `core/services/terminal_sanitize.py`
- Test: `tests/test_bash_session_streaming.py`
- Test: `tests/test_streaming_subprocess.py`
- Test: `tests/test_terminal_sanitize.py`
- Test: `tests/test_bash_session_selvhelbredelse.py`

**Interfaces:**
- Consumes: Task 1 `emit_current_output()` / `note_executor_timing()` and existing shell result shapes.
- Produces: framed daemon messages `{type:"output_delta",stream:"combined",seq,chunk}` followed by `{type:"result",...}`, while `_client_call_once(payload, timeout, on_output=None)` also accepts legacy terminal JSON.

- [ ] **Step 1: Write protocol, queue-wait, and split-encoding tests**

```python
def test_client_accepts_delta_frames_then_terminal_result(fake_socket):
    fake_socket.feed(b'{"type":"output_delta","stream":"combined","seq":1,"chunk":"hej"}\n'
                     b'{"type":"result","status":"ok","exit_code":0,"output":"hej"}\n')
    seen = []
    result = bs._client_call_once({"op": "run"}, on_output=lambda **d: seen.append(d))
    assert seen == [{"stream": "combined", "seq": 1, "chunk": "hej"}]
    assert result["exit_code"] == 0
```

Add tests for legacy one-line JSON, a marker split across reads, a multi-byte `æ` split across byte chunks, an ANSI sequence split across frames, and a second fast call whose measured `dispatch_to_lock_ms` is non-zero while the first holds the session lock.

- [ ] **Step 2: Run tests and verify framing is absent**

Run: `pytest -q tests/test_bash_session_streaming.py tests/test_streaming_subprocess.py tests/test_terminal_sanitize.py`

- [ ] **Step 3: Add marker-safe daemon streaming and timing**

Change `_Session.run` to accept `on_output: Callable[[str], None] | None`, time lock acquisition explicitly, use an incremental UTF-8 decoder, and retain enough trailing bytes to prove the end marker is not output before emitting a safe prefix. The daemon sends deltas only when the request has `"stream": true`; its last frame is always `type=result`.

```python
def _client_call_once(payload: dict[str, Any], timeout: float = 310.0,
                      on_output: Callable[..., None] | None = None) -> dict[str, Any]:
    # read newline frames until type=result; a frame without type is legacy final
    ...
```

Attach local monotonic metadata (`route`, `dispatch_to_lock_ms`, `first_output_ms`, `process_ms`, `had_output`) to the internal result, feed it to Task 1, and remove it before building the model-visible shell result.

- [ ] **Step 4: Extract and use a streaming one-shot subprocess helper**

```python
@dataclass(frozen=True, slots=True)
class StreamingProcessResult:
    stdout: str
    stderr: str
    exit_code: int | None
    timed_out: bool
    first_output_ms: int | None
    process_ms: int

def run_streaming(argv: list[str], *, cwd: str, timeout_s: float,
                  on_output: Callable[[str, str], None] | None) -> StreamingProcessResult: ...
```

Use `subprocess.Popen`, concurrently drain stdout/stderr, preserve the existing final composition (`stdout`, then `[stderr]`), and label the route `server_fallback`. Output callbacks are best-effort and never allowed to stop the child or final collection.

- [ ] **Step 5: Extend the existing sanitizer for chunk boundaries**

```python
class TerminalStreamSanitizer:
    def feed(self, chunk: str) -> str: ...
    def flush(self) -> str: ...
```

Reuse the existing regex/constants and retain only an incomplete escape suffix between calls. Do not interpret markdown/HTML.

- [ ] **Step 6: Run server-shell regression tests and commit**

Run: `pytest -q tests/test_bash_session_streaming.py tests/test_streaming_subprocess.py tests/test_terminal_sanitize.py tests/test_bash_session_selvhelbredelse.py tests/test_shell_policy_parity.py`

```bash
git add -- core/tools/bash_session.py core/tools/streaming_subprocess.py core/tools/simple_tools_web.py core/services/terminal_sanitize.py tests/test_bash_session_streaming.py tests/test_streaming_subprocess.py tests/test_terminal_sanitize.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat: stream server shell output' --path core/tools/bash_session.py --path core/tools/streaming_subprocess.py --path core/tools/simple_tools_web.py --path core/services/terminal_sanitize.py --path tests/test_bash_session_streaming.py --path tests/test_streaming_subprocess.py --path tests/test_terminal_sanitize.py
```

### Task 4: Operator bridge streaming across both processes

**Files:**
- Create: `apps/jarvis-desk/electron/asyncSpawn.ts`
- Create: `apps/jarvis-desk/electron/asyncSpawn.test.ts`
- Modify: `apps/jarvis-desk/electron/bridge.ts:430-483,679-703,2571-2715`
- Modify: `core/services/jarvisx_bridge.py:160-320,595-850`
- Modify: `apps/api/jarvis_api/routes/jarvisx_bridge.py:34-110,221-290`
- Modify: `core/tools/operator_tools.py:28-48,356-390`
- Modify: `core/tools/simple_tools_operator.py:680-715`
- Test: `tests/test_jarvisx_bridge.py`
- Test: `tests/test_bridge_cross_process.py`
- Test: `tests/test_jarvisx_bridge_streaming.py`

**Interfaces:**
- Consumes: Task 1 current output sink/timing merge and the existing bridge `correlation_id`.
- Produces: `asyncSpawn(..., onOutput?)`, WebSocket `tool_output_delta`, `BridgeRegistry.dispatch(..., on_output=None)`, `BridgeConnection.deliver_output(...)`, and optional NDJSON internal dispatch when request body has `stream_output: true`.

- [ ] **Step 1: Extract `asyncSpawn` before changing the 2,700-line bridge**

Move the existing helper unchanged into `asyncSpawn.ts`, export its existing result type/function, import it from `bridge.ts`, and prove the final stdout/stderr/status behavior is byte-equivalent with a child-process test.

- [ ] **Step 2: Write failing Electron streaming tests**

```ts
it('emits decoded ordered chunks and preserves the final buffers', async () => {
  const seen: Array<{ stream: string; seq: number; chunk: string }> = []
  const r = await asyncSpawn(process.execPath, ['-e',
    "process.stdout.write(Buffer.from([0xc3]));setTimeout(()=>process.stdout.write(Buffer.from([0xa6,10])),20)"
  ], {}, (d) => seen.push(d))
  expect(seen.map((d) => d.seq)).toEqual([...seen.keys()].map((i) => i + 1))
  expect(seen.map((d) => d.chunk).join('')).toBe('æ\n')
  expect(r.stdout).toBe('æ\n')
})
```

Add a flood test proving WebSocket emissions are batched at 75 ms/8 KiB while the complete bounded final buffer remains available.

- [ ] **Step 3: Add bridge correlation and terminal guards**

Replace pending tuples with a small `PendingBridgeCall(future, owning_loop, on_output, terminal)` record. `deliver_output` schedules the callback on its owning loop, accepts only increasing sequences, and ignores unknown, duplicate, late, timed-out, or terminal correlations. `deliver_result` marks terminal before removing the entry.

Extend Electron's handler type without changing non-shell handlers:

```ts
interface ToolExecutionContext {
  emitOutput: (delta: { stream: 'stdout' | 'stderr'; seq: number; chunk: string }) => void
}
type ToolHandler = (args: Record<string, unknown>, context?: ToolExecutionContext) => unknown | Promise<unknown>
```

Use Node's `StringDecoder` independently for stdout and stderr so a Buffer boundary cannot create replacement characters.

- [ ] **Step 4: Carry output through local and cross-process dispatch**

The Electron handler sends:

```ts
this.send({ type: 'tool_output_delta', correlation_id, stream, seq, chunk })
```

`BridgeConnection.send_invoke` includes `stream_output: boolean`; Electron creates/passes `ToolExecutionContext` only when it is true. Thus `live_tool_output_enabled=false` retains final-only bridge traffic even when both sides contain the new code.

The FastAPI WebSocket route calls `conn.deliver_output(...)`. For a local bridge, `dispatch(on_output=...)` invokes the callback directly. For a remote bridge process, request `stream_output: true`; the internal endpoint returns newline-delimited objects:

```json
{"type":"output_delta","stream":"stdout","seq":1,"chunk":"linje\n"}
{"type":"result","status":"ok","result":{},"error":null}
```

Use `httpx.AsyncClient.stream(...).aiter_lines()` in `_forward_cross_process`. Preserve the existing JSONResponse path when `stream_output` is false, so old callers and mixed versions retain final-only behavior.

When a new caller reaches an old endpoint and receives one unframed JSON object, treat that line as the legacy terminal result. When an old caller reaches a new endpoint it omits `stream_output`, so it still receives the existing JSONResponse.

- [ ] **Step 5: Pass the current sink only for operator bash and merge remote timings**

```python
async def _bridge_call(..., on_output: Callable[..., None] | None = None) -> Any: ...
async def operator_bash_async(..., on_output: Callable[..., None] | None = None) -> dict[str, Any]: ...
```

Electron reports its locally measured `dispatch_to_spawn_ms`, `first_output_ms`, `process_ms`, and `had_output` beside the terminal envelope. `_bridge_call` merges timing into Task 1 and returns only the existing `result` to callers.

- [ ] **Step 6: Run bridge tests and commit**

Run: `pytest -q tests/test_jarvisx_bridge.py tests/test_bridge_cross_process.py tests/test_jarvisx_bridge_streaming.py tests/test_operator_tools.py tests/test_bro_frister.py`

Run: `cd apps/jarvis-desk && npm test -- --run electron/asyncSpawn.test.ts && npm run build:electron`

```bash
git add -- apps/jarvis-desk/electron/asyncSpawn.ts apps/jarvis-desk/electron/asyncSpawn.test.ts apps/jarvis-desk/electron/bridge.ts core/services/jarvisx_bridge.py apps/api/jarvis_api/routes/jarvisx_bridge.py core/tools/operator_tools.py core/tools/simple_tools_operator.py tests/test_jarvisx_bridge.py tests/test_bridge_cross_process.py tests/test_jarvisx_bridge_streaming.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat: stream operator shell output across bridge' --path apps/jarvis-desk/electron/asyncSpawn.ts --path apps/jarvis-desk/electron/asyncSpawn.test.ts --path apps/jarvis-desk/electron/bridge.ts --path core/services/jarvisx_bridge.py --path apps/api/jarvis_api/routes/jarvisx_bridge.py --path core/tools/operator_tools.py --path core/tools/simple_tools_operator.py --path tests/test_jarvisx_bridge.py --path tests/test_bridge_cross_process.py --path tests/test_jarvisx_bridge_streaming.py
```

### Task 5: Visible-run output queue and SSE translation

**Files:**
- Modify: `core/services/visible_tool_exec.py:100-437`
- Modify: `core/services/simple_tool_executor.py:359-470`
- Modify: `core/services/visible_runs_sse_v2.py:50-65,780-920`
- Test: `tests/test_visible_tool_exec.py`
- Test: `tests/test_visible_runs_sse_v2.py`
- Test: `tests/test_tool_output_backpressure.py`

**Interfaces:**
- Consumes: Task 1 `BoundedOutputBuffer`, `bind_execution`, trace start/dispatch APIs; Task 3/4 producers.
- Produces: legacy SSE `tool_output_delta`, translated as existing v2 `system_event(kind="tool_output_delta")` with `{run_id, tool_use_id, stream, seq, chunk, truncated}`.

- [ ] **Step 1: Write failing pump and translator tests**

Create a fake executor that emits two chunks, waits, and returns a final result. Assert the async generator yields `working_step`, then both `tool_output_delta` events, before the executor completes. Add a disabled-flag test with no delta events and unchanged result.

- [ ] **Step 2: Bind the output buffer per executable call**

Extend `_execute_simple_tool_calls(..., output_buffer=None)` and bind each prepared call's real `tc["id"]` around `_exec`, including each parallel worker's copied ContextVar. Cached, duplicate, blocked, and approval-needed results bind nothing because no command executes.

Call Task 1 `mark_dispatch` immediately before `_exec` and `mark_execution_complete` immediately after it returns or raises. This separates executor/gate queue time from the post-execution wait without changing `tool.invoked` / `tool.completed` consumers.

- [ ] **Step 3: Drain while awaiting without blocking final execution**

Refactor the wait loop to wake every 75 ms when live output is enabled, drain all available frames, sanitize via one `TerminalStreamSanitizer` per `(tool_use_id, stream)`, and yield `_sse("tool_output_delta", payload)`. Heartbeats retain their current 5/15-second cadence and cancellation remains checked at least once per second. Drain once more before returning results.

When cancellation wins, call Task 1 `cancel_call` for each still-active call before returning; the bounded buffer may receive late worker chunks but no further SSE or durable duplicate timing event is emitted.

- [ ] **Step 4: Add the explicit v2 pass-through case**

```python
elif event_name == "tool_output_delta":
    await _emit_message_start_if_needed()
    await queue.put(SystemEvent(kind="tool_output_delta", payload=payload).to_sse_line())
```

Although unknown events already pass through, an explicit branch and `_KNOWN_SYSTEM_EVENT_KINDS` entry make this supported protocol rather than accidental behavior.

- [ ] **Step 5: Run pump/SSE tests and commit**

Run: `pytest -q tests/test_visible_tool_exec.py tests/test_visible_runs_sse_v2.py tests/test_tool_output_backpressure.py tests/test_visible_runs_loop_not_blocked.py`

```bash
git add -- core/services/visible_tool_exec.py core/services/simple_tool_executor.py core/services/visible_runs_sse_v2.py tests/test_visible_tool_exec.py tests/test_visible_runs_sse_v2.py tests/test_tool_output_backpressure.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat: forward live tool output through visible runs' --path core/services/visible_tool_exec.py --path core/services/simple_tool_executor.py --path core/services/visible_runs_sse_v2.py --path tests/test_visible_tool_exec.py --path tests/test_visible_runs_sse_v2.py --path tests/test_tool_output_backpressure.py
```

### Task 6: Settle first-pass results before prompt assembly

**Files:**
- Create: `core/services/visible_first_pass_results.py`
- Modify: `core/services/visible_runs.py:1830-2135,4600-4765`
- Test: `tests/test_visible_first_pass_results.py`
- Test: `tests/test_visible_result_before_prompt.py`
- Test: `tests/test_visible_runs_capability_smoke.py`

**Interfaces:**
- Consumes: existing approval state/wait helpers, `_sse`, `build_tool_capability_payload`, Task 1 `surface_result`, and Task 2 `_build_visible_input(..., caller_phase="post_tool")`.
- Produces: `publish_first_pass_results(results, *, run, step_counter, out) -> AsyncIterator[str]`, where `out["resolved_result_texts"]` preserves the current persistence/follow-up input.

- [ ] **Step 1: Characterize the existing publication behavior before extraction**

Write fixture cases for normal success, error, gate-blocked, autonomous denial, trust-all non-destructive approval, explicit approval success/denial, working-step settlement, and app-action event. Assert exact event order and resolved text for each.

- [ ] **Step 2: Extract the coherent first-pass result unit unchanged**

```python
async def publish_first_pass_results(results: list[dict], *, run, step_counter: int,
                                     out: dict) -> AsyncIterator[str]:
    """Resolve approvals and publish terminal UI facts; do not persist transcript."""
    ...
```

Keep imports from `visible_runs` lazy to avoid a cycle, as `visible_tool_exec.py` already does. Re-export the helper from `visible_runs.py` if current tests patch the old seam.

- [ ] **Step 3: Run characterization tests before reordering**

Run: `pytest -q tests/test_visible_first_pass_results.py tests/test_visible_runs_capability_smoke.py`

Expected: all extraction characterization tests pass with event payloads unchanged.

- [ ] **Step 4: Move publication ahead of the post-tool prompt build**

The first-pass order becomes:

```python
async for frame in publish_first_pass_results(simple_results, run=run,
                                               step_counter=_step_counter, out=_published):
    yield frame
_resolved_result_texts = _published["resolved_result_texts"]
_bvi_task = asyncio.create_task(asyncio.to_thread(
    _build_visible_input, run.user_message, session_id=run.session_id,
    provider=run.provider, model=run.model, caller_phase="post_tool",
))
visible_input_pre = await _bvi_task  # existing heartbeat loop remains around this await
# only now persist tool rows and construct follow-up exchanges
```

Close Task 1 traces immediately before each terminal capability/denial event. Approval requests are emitted before prompt work; an approved execution closes only when its actual result is surfaced. Replace the stale unconditional “6–33s” comment with the measured cache contract.

Apply the same `surface_result` call immediately before terminal capability/denial emission in the agentic-round result loop. That path already publishes before its next model round, so only instrumentation changes there; add a test proving one timing summary per first-pass and per agentic call.

- [ ] **Step 5: Prove result/approval events win a blocked prompt race**

Use a prompt builder held on a `threading.Event`. Advance the visible generator until the terminal capability (and separately approval request), assert it arrived while the builder is still blocked, release the event, then assert transcript/follow-up order equals the pre-change fixture.

- [ ] **Step 6: Run visible-run tests and commit**

Run: `pytest -q tests/test_visible_first_pass_results.py tests/test_visible_result_before_prompt.py tests/test_visible_runs_capability_smoke.py tests/test_visible_runs_loop_not_blocked.py tests/test_visible_runs_approvals.py`

```bash
git add -- core/services/visible_first_pass_results.py core/services/visible_runs.py tests/test_visible_first_pass_results.py tests/test_visible_result_before_prompt.py tests/test_visible_runs_capability_smoke.py
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix: settle tool cards before prompt assembly' --path core/services/visible_first_pass_results.py --path core/services/visible_runs.py --path tests/test_visible_first_pass_results.py --path tests/test_visible_result_before_prompt.py --path tests/test_visible_runs_capability_smoke.py
```

### Task 7: Desk live terminal state and inert rendering

**Files:**
- Modify: `apps/jarvis-desk/src/lib/sseProtocol.ts:150-205`
- Modify: `apps/jarvis-desk/src/lib/streamReducer.ts:220-430`
- Modify: `apps/jarvis-desk/src/lib/streamReducer.test.ts`
- Modify: `apps/jarvis-desk/src/components/rich/ToolCard.tsx:20-180`
- Modify: `apps/jarvis-desk/src/components/rich/ToolCard.test.tsx`
- Modify: `apps/jarvis-desk/src/styles/app.css:2209-2211`

**Interfaces:**
- Consumes: Task 5 `system_event(kind="tool_output_delta")` payload.
- Produces: optional `liveOutput`, `liveOutputSeq`, and `liveOutputTruncated` fields on the existing rendered `tool_use` block.

- [ ] **Step 1: Write failing reducer tests**

```ts
const start: StreamEvent = { type: 'message_start', message: {
  id: 'r1', model: 'm', provider: 'p', lane: 'primary', session_id: 's',
  usage: { input_tokens: 0, output_tokens: 0 },
} }
const toolStart: StreamEvent = { type: 'content_block_start', index: 0,
  content_block: { type: 'tool_use', id: 't1', name: 'bash', input: {} } }
const delta = (seq: number, chunk: string): StreamEvent => ({
  type: 'system_event', kind: 'tool_output_delta',
  payload: { run_id: 'r1', tool_use_id: 't1', stream: 'stdout', seq, chunk },
})

it('appends only increasing deltas to a running matching card', () => {
  const s = reduce([start, toolStart, delta(2, 'B'), delta(2, 'dup'), delta(1, 'old')])
  const card = s.blocks[0]
  expect(card.type === 'tool_use' ? card.liveOutput : '').toBe('B')
})
```

Also test unknown ID, wrong run, post-terminal delta, 64-KiB rolling cap, explicit truncation marker, and final canonical result replacing/clearing live state.

- [ ] **Step 2: Implement reducer state without a new block type**

Handle `tool_output_delta` before the generic unknown-system-event return. Apply only to a matching `status === "running"` card and a strictly newer sequence. Keep the newest 65,536 characters and set `liveOutputTruncated` when either the server says so or client trimming occurs.

- [ ] **Step 3: Render live output in the existing terminal body**

```tsx
const terminalText = status === 'running' ? (block.liveOutput ?? resultat) : resultat
...
{terminalText && <pre className="tc-term-out">{terminalText}</pre>}
{block.liveOutputTruncated && <div className="toolcard-afkortet">live output truncated</div>}
```

Keep React text interpolation inside `<pre>`; do not use markdown parsing or `dangerouslySetInnerHTML`. The card remains collapsed unless the user opens it, and updates while open.

- [ ] **Step 4: Run Desk tests/build and commit**

Run: `cd apps/jarvis-desk && npm test -- --run src/lib/streamReducer.test.ts src/components/rich/ToolCard.test.tsx && npm run build:renderer`

```bash
git add -- apps/jarvis-desk/src/lib/sseProtocol.ts apps/jarvis-desk/src/lib/streamReducer.ts apps/jarvis-desk/src/lib/streamReducer.test.ts apps/jarvis-desk/src/components/rich/ToolCard.tsx apps/jarvis-desk/src/components/rich/ToolCard.test.tsx apps/jarvis-desk/src/styles/app.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat: render live shell output in tool cards' --path apps/jarvis-desk/src/lib/sseProtocol.ts --path apps/jarvis-desk/src/lib/streamReducer.ts --path apps/jarvis-desk/src/lib/streamReducer.test.ts --path apps/jarvis-desk/src/components/rich/ToolCard.tsx --path apps/jarvis-desk/src/components/rich/ToolCard.test.tsx --path apps/jarvis-desk/src/styles/app.css
```

### Task 8: Read-only latency report and end-to-end verification

**Files:**
- Create: `scripts/tool_latency_report.py`
- Create: `tests/test_tool_latency_report.py`
- Modify: `docs/superpowers/specs/2026-10-10-tool-latency-and-live-output-design.md`

**Interfaces:**
- Consumes: durable `tool.execution_timing`, `prompt.assembly_cache`, and existing `prompt.assembly_size` events.
- Produces: a read-only CLI summary for a configurable full-day window with counts, p50/p90/p95/max, route, wait-stage attribution, and prompt cache outcomes.

- [ ] **Step 1: Write failing report aggregation tests**

```python
def test_report_counts_where_calls_waited():
    def timing(**values):
        return {"kind": "tool.execution_timing", "payload": {
            "tool": "bash", "route": "server_persistent_shell", **values}}
    rows = [timing(total_visible_ms=900, dispatch_to_lock_ms=700, process_ms=40),
            timing(total_visible_ms=120, dispatch_to_lock_ms=0, process_ms=80)]
    report = aggregate(rows, slow_ms=500)
    assert report["calls"] == 2
    assert report["slow_calls"] == 1
    assert report["dominant_wait_stage"]["shell_lock"] == 1
```

Pin empty windows, malformed old events, mixed routes, and cache-outcome counts. The script must not mutate DB/state.

- [ ] **Step 2: Implement the report**

```python
def aggregate(events: Iterable[dict], *, slow_ms: int = 500) -> dict[str, Any]: ...

def main() -> int:
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--slow-ms", type=int, default=500)
    parser.add_argument("--json", action="store_true")
    ...
```

Classify the dominant measured wait as `shell_lock`, `bridge_or_spawn`, `process`, `result_surface`, or `unattributed`; never force phase durations to sum when a route cannot measure one.

- [ ] **Step 3: Run automated verification**

Run: `pytest -q tests/test_tool_execution_trace.py tests/test_prompt_assembly_turn_cache.py tests/test_prompt_assembly_telemetri.py tests/test_bash_session_streaming.py tests/test_streaming_subprocess.py tests/test_jarvisx_bridge_streaming.py tests/test_visible_tool_exec.py tests/test_visible_runs_sse_v2.py tests/test_visible_first_pass_results.py tests/test_visible_result_before_prompt.py tests/test_tool_latency_report.py`

Run: `python -m compileall core apps/api scripts`

Run: `cd apps/jarvis-desk && npm test -- --run electron/asyncSpawn.test.ts src/lib/streamReducer.test.ts src/components/rich/ToolCard.test.tsx && npm run build`

- [ ] **Step 4: Exercise the four acceptance commands with output enabled**

In an isolated test runtime set `live_tool_output_enabled=true` and run: `true`; `printf 'nu\n'`; `for n in 1 2 3; do echo "$n"; sleep 1; done`; and two calls sharing one persistent session where the first runs `sleep 2` and the second runs `printf 'queued\n'`. Verify card creation, in-flight output, terminal settlement before post-tool prompt work, and non-zero lock wait for the queued call.

- [ ] **Step 5: Capture one real traced Desk turn and update measured status**

Create `/tmp/jarvis-turn-trace`, run one owner Desk turn with delayed output, inspect `/tmp/jarvis-turn-trace-dumps/latest.json`, then run:

```bash
python scripts/tool_latency_report.py --days 1
```

Update the spec status from `Proposed design` to `Implemented behind rollout flags` and append the verification date plus observed cache outcome/process role. Do not claim the five-way 15-second cluster's cause unless the new key hashes and process metadata prove it.

- [ ] **Step 6: Commit report and verification note**

```bash
git add -- scripts/tool_latency_report.py tests/test_tool_latency_report.py docs/superpowers/specs/2026-10-10-tool-latency-and-live-output-design.md
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'docs: add tool latency verification report' --path scripts/tool_latency_report.py --path tests/test_tool_latency_report.py --path docs/superpowers/specs/2026-10-10-tool-latency-and-live-output-design.md
```
