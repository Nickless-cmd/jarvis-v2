# Tool latency and live shell output

**Date:** 2026-10-10  
**Status:** Implemented behind rollout flags
**Scope:** Visible Jarvis runs in Desk, server-side `bash`, and Desk-side `operator_bash`

## Purpose

Make shell work feel truthful in Jarvis Desk and make latency diagnosable.

Success means:

1. Every model-originated shell call can be split into queue time, execution time, time to first output, and post-execution time.
2. A running shell card shows bounded live stdout/stderr while the command runs.
3. A completed command is shown as completed without waiting for prompt assembly for the next model round.
4. The final tool result remains the canonical persisted result. Live chunks are an ephemeral projection and never become a second source of truth.
5. Prompt assembly cache hits, misses, build time, process role, and post-tool wait are measurable separately.

## What exists today

The visible-run pump emits a `working_step` with `status=running`, tool id, and arguments before execution. Desk already turns that into a live `tool_use` card. While execution runs, the pump emits heartbeat events, but those events carry no stdout/stderr.

Both shell implementations buffer output until completion:

- Server `bash` runs in the separate persistent `bash_session` daemon. The daemon holds one lock per session, reads PTY chunks internally, and returns one JSON response after the end marker.
- Desk `operator_bash` uses Electron `spawn()`, appends `stdout` and `stderr` chunks to arrays, and sends one `tool_result` after process close.

The first-pass visible-run path waits for `_build_visible_input` before it emits the completed capability/result event. This couples a UI fact (the command is complete) to preparation for the next model request.

Prompt assembly already has a 180-second turn-scoped cache intended to make the post-tool rebuild a sub-millisecond cache hit. The current telemetry records builds but not hits or caller phase, so it cannot prove whether a slow post-tool window was a cache miss, a different process, or time outside assembly.

Read-only inspection of the production event database on 2026-10-10 found 64 recorded prompt builds in the previous 14 days:

- median: 2,593 ms
- p90: 5,106 ms
- p95: 14,862 ms
- maximum: 15,017 ms
- 7 builds above 5 seconds; 5 above 10 seconds

Five builds clustered within milliseconds around 15 seconds on 2026-10-04. That is evidence for concurrent misses or process-local cache separation, but the existing payload lacks session key, cache outcome, PID, and process role, so it is not enough to name the root cause.

Existing `tool.invoked` / `tool.completed` data is also insufficient for latency analysis. It does not store durations or execution phases, recent operator polling polluted invocation counts, and the currently stored data has no pairable recent bash completion set.

## Approaches considered

### A. Only add timers

Add duration fields to final events but keep output buffered. This is small and would diagnose waits, but it leaves the visible experience unchanged and does not satisfy live output.

### B. Poll background shells

Route commands through the existing background-shell API and let Desk poll `bash_output`. This reuses existing pieces, but changes foreground tool semantics, adds polling latency, and creates two lifecycle owners for one call.

### C. One ephemeral output-delta path with canonical final results

Extend the existing tool lifecycle with bounded output deltas. Both shell transports emit the same logical delta, the visible-run stream forwards it, and Desk appends it to the existing card. Final results and persistence stay unchanged.

**Decision:** C. It preserves current execution semantics and source-of-truth boundaries while making both latency and progress visible.

## Architecture

### 1. Tool timing trace

Create a focused `core/services/tool_execution_trace.py` unit. It owns an in-memory trace per `tool_use_id` and publishes one durable `tool.execution_timing` event when the result is surfaced.

The trace records monotonic durations, not cross-machine wall-clock differences:

- `announced_to_dispatch_ms`
- `dispatch_to_lock_ms` for the persistent server shell, when applicable
- `dispatch_to_spawn_ms` for the operator bridge, when applicable
- `first_output_ms`, measured from dispatch/spawn
- `process_ms`
- `process_exit_to_result_emit_ms`
- `total_visible_ms`, from running card announcement to completed result emission
- route: `server_persistent_shell`, `server_fallback`, or `operator_bridge`
- tool, run id, tool-use id, status, exit code, and whether any output arrived

Remote executors report durations they can measure locally in the final result metadata. The server never subtracts clocks from two machines.

Only the single summary event is persisted. Output chunks are not written to the event database.

### 2. Server bash streaming

Extend the newline-delimited Unix-socket protocol used by `bash_session`:

- zero or more `{type: "output_delta", stream: "combined", seq, chunk}` frames
- one terminal `{type: "result", ...}` frame

The daemon already receives PTY chunks in `_Session.run`; it emits them after marker filtering and before adding them to the bounded final buffer. The client reader accepts both the new framed protocol and the legacy one-result response during rollout.

Because the PTY combines stdout and stderr, the server route labels chunks `combined`. The final result shape remains unchanged.

The time spent waiting to acquire the per-session lock is measured separately. This exposes the case where a fast command waits behind an earlier command in the shared shell.

### 3. Operator bash streaming

Electron's `asyncSpawn` gains an optional output callback. `stdout` and `stderr` listeners continue filling the final bounded buffers and also emit throttled bridge messages:

```json
{
  "type": "tool_output_delta",
  "correlation_id": "...",
  "stream": "stdout",
  "seq": 4,
  "chunk": "..."
}
```

The bridge registry maps `correlation_id` to the pending call's `tool_use_id` and forwards the delta to the visible-run trace/output sink. Unknown, late, duplicated, or already-terminal correlations are ignored.

The final `tool_result` message is unchanged and remains authoritative.

### 4. Visible-run output channel

`run_tool_batch` owns a thread-safe output queue for the active batch. While it awaits the executor task, it drains this queue and emits an SSE event:

```json
{
  "type": "tool_output_delta",
  "run_id": "...",
  "tool_use_id": "...",
  "stream": "stdout|stderr|combined",
  "seq": 4,
  "chunk": "..."
}
```

The queue is bound through a ContextVar for in-process handlers. The bash-session and operator transports explicitly bridge their process boundaries into that sink.

Per call, emission is throttled to at most one frame per 75 ms or 8 KiB, whichever happens first. Desk retains at most the latest 64 KiB of live output. The existing final-result store retains the canonical complete/clipped result according to current policy.

Backpressure is lossy only for the live projection: if the queue is full, adjacent chunks are coalesced or the oldest live chunk is dropped and the card displays an explicit `live output truncated` marker. Execution and final result delivery must never block on the UI stream.

ANSI/control-code sanitization is applied before browser rendering. Raw HTML and markdown are never interpreted.

### 5. Desk state and rendering

Add `liveOutput`, `liveOutputTruncated`, and the latest sequence number to the rendered `tool_use` block state. `streamReducer` applies deltas only when the tool id exists and the sequence is newer than the last applied sequence.

The existing terminal body renders live output while status is `running`. When the canonical result arrives, it replaces the ephemeral live buffer and the status changes to `done` or `error`.

Reconnect/replay does not persist all deltas. A reconnected client may initially see only the running command and elapsed time; the final canonical result restores complete state. A later bounded snapshot can be added if real usage shows this gap matters.

### 6. Decouple completion from prompt assembly

The first-pass result publication and approval request flow currently lives inside `visible_runs.py`, which is far above the repository's size limit. Before changing that logic, extract the coherent first-pass result-resolution/publication unit into a new module and re-export any required seam for compatibility, satisfying the Boy Scout rule.

After extraction, split the post-tool flow into two ordered concerns:

1. Publish the tool's terminal UI state immediately after execution (or publish the approval request immediately when approval is required).
2. Prepare/persist the transcript and build the next model request.

SSE publication does not mutate the chat transcript, so a completed result can be shown before the base-message snapshot is built. Transcript persistence and the follow-up model call keep their existing ordering and still await a valid base-message snapshot.

The timing trace closes at terminal result publication, making any remaining prompt work visible as a separate next-round phase instead of fake shell runtime.

### 7. Prompt assembly verification

Instrument the turn-scoped assembly cache itself:

- `cache_outcome`: `hit`, `miss`, `unsafe_no_key`, or `expired`
- opaque hash of the cache key; never the message text
- cache age
- caller phase: `initial`, `post_tool`, `followup`, or `other`
- PID and configured process role
- build duration on misses and lookup duration on hits

Add a dedicated span around the post-tool `_build_visible_input` await. This distinguishes:

- an actual prompt build
- a cache lookup
- executor scheduling delay
- time after tool completion but outside prompt assembly

Do not add single-flight or a cross-process cache in the first change. First collect enough keyed evidence to decide whether the five-way 15-second cluster was same-process stampede, multiple processes, or independent sessions. If same-process duplicate misses are confirmed, add per-key single-flight. If cross-process duplication dominates, decide separately whether the added invalidation complexity is justified.

Replace the stale unconditional “6–33s” comment with the measured contract: post-tool should normally hit the turn cache, misses are bounded and observable, and UI completion does not wait for either.

## Error and lifecycle rules

- A stream failure never changes command success or failure.
- Missing deltas are not a tool error; the final result settles the card.
- Deltas after a terminal result are ignored.
- Duplicate sequence numbers are ignored.
- Cancellation stops forwarding immediately. The existing executor cancellation semantics remain unchanged.
- Approval-needed commands emit no execution output until the approved execution actually begins.
- Secrets are not newly persisted. Live shell output has the same sensitivity as the final tool result and remains scoped to the existing authenticated run stream.

## Verification

### Runtime tests

- Timing trace calculates each phase and publishes one terminal summary.
- A queued persistent-shell call reports lock wait separately from process time.
- Bash-session socket client accepts legacy final-only responses and new delta-plus-final frames.
- Output backpressure cannot block or fail tool execution.
- First-pass result SSE appears before a deliberately blocked prompt rebuild.
- Transcript and follow-up message order remains byte-equivalent after extraction.
- Approval request appears before a deliberately blocked prompt rebuild.
- Prompt cache telemetry distinguishes hit, miss, unsafe key, and expiry.

### Bridge tests

- Electron forwards stdout and stderr chunks with correlation id and increasing sequence.
- Final result is unchanged.
- Late chunks after timeout/completion are ignored.
- Large output is throttled and bounded without losing the final buffered result.

### Desk tests

- A running bash card updates as deltas arrive.
- Out-of-order and duplicate deltas do not corrupt output.
- Final result replaces the live buffer and settles status.
- The rolling 64 KiB cap displays a truncation marker.
- Output remains inert text.

### End-to-end acceptance

Run commands that cover four cases:

1. immediate silent success (`true`)
2. immediate output (`printf`)
3. delayed multi-line output (three lines one second apart)
4. a quick command queued behind a longer command in the shared shell

For each call, verify the card appears immediately, output arrives while running where applicable, the final state settles without waiting for post-tool prompt assembly, and the timing event explains the observed delay.

Then run at least one real Desk turn with turn tracing enabled and compare the new post-tool/cache fields with the existing production baseline.

## Implementation verification — 2026-10-10

The implementation is complete behind the two rollout flags and was verified in an isolated worktree. The focused Python suites, Desk reducer/component/bridge suites, Python compilation, and the production Desk build passed. The final result is published before post-tool prompt construction, while live deltas remain an ephemeral bounded projection and the terminal result remains canonical.

The four native persistent-shell acceptance cases produced these observations:

| Case | First output | Process | Lock wait | Result |
| --- | ---: | ---: | ---: | --- |
| `true` | none | 50 ms | 0 ms | completed silently |
| immediate `printf` | 50 ms | 50 ms | 0 ms | delta arrived before the result |
| three lines one second apart | 50 ms | 3,055 ms | 0 ms | deltas arrived at 0.05, 1.05, and 2.05 seconds |
| quick command queued behind `sleep 2` | 50 ms | 50 ms | 1,952 ms | queue wait was separated from execution |

The production database did not yet contain `tool.execution_timing` or `prompt.assembly_cache` events because this code was not deployed. The report therefore correctly returned zero new-format calls/cache events while still summarising the old `prompt.assembly_size` baseline. A wider read-only scan found 841 historical assembly events from 2026-09-05 through 2026-10-08. Its maximum was 15,922 ms; 717 were at least 6 seconds and none were at least 20 seconds. The stored evidence therefore does not support a 33-second prompt-assembly span. A perceived 33-second wait must include scheduling, support futures, model latency, or another phase outside the old assembly event; the old event shape cannot attribute it more precisely.

A real owner Desk turn against the existing production build completed normally and the live turn log measured:

- prompt assembly start at +20 ms and end at +12,627 ms (`12,606 ms` duration)
- skill relevance at 5,697 ms, including one embedding call taking 4,908 ms
- the inner-life section at 8,225 ms
- memory selection at 825 ms and visible-session continuity at 2,852 ms
- prompt hand-off at +14,760 ms, first token at +15,623 ms, and completion at +15,814 ms

An adjacent traced production turn measured about 12,009 ms of assembly and 13,800 ms total. These traces confirm that prompt construction itself can dominate a turn, while the remaining gap is outside assembly. They do not identify the five-way 15-second historical cluster's cause.

The production trace dump did not yield a reliable cache outcome or process role: the existing tracer is process-global, and overlapping runtime traffic can reset or interleave it before the dump is written. The journal timings above are valid, but attributing them to a cache hit/miss would be guesswork. The implemented cache event records opaque key hash, caller phase, PID, and process role per event after deployment, which removes that ambiguity.

Separately, host inspection found the approximately 60 named daemon threads are created together at startup and remain stable rather than accumulating. Most were blocked in futex, sleep, or event waits. This rules out a thread leak in the observed window, but a futex wait alone does not prove GIL starvation; scheduler/contention remains a hypothesis to test against the new per-call timing data.

## Rollout

Ship behind two independent runtime flags:

- `tool_execution_timing_enabled` — default on after tests, because it emits one small event per completed call.
- `live_tool_output_enabled` — default off for the first deployed observation, then on for owner Desk sessions after bridge/runtime compatibility is verified.

Protocol readers remain backward compatible during the rollout. The flag controls production, not divergent implementations; there is one code path with optional emission.

## Non-goals

- Streaming partial tool output into the model before process completion.
- Persisting every output chunk in SQLite.
- Making every atomic tool stream artificial progress.
- Replacing final tool-result storage or transcript persistence.
- Solving cross-process prompt caching without evidence from the new cache telemetry.
