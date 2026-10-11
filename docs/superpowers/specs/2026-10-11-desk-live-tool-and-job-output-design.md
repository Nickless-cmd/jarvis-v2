# Desk Live Tool and Background Job Output Design

**Date:** 2026-10-11  
**Status:** Approved in conversation; awaiting review of this written specification  
**Scope:** Jarvis Desk only. The mobile application is explicitly out of scope.

## Intent

Long-running commands must not leave the user staring at `Kører…` for several
minutes without evidence of what the command is doing. The Desk transcript and
the Background Jobs panel must show bounded, live stdout/stderr for work on both
the Jarvis server and the operator's machine. If work fails, the visible card
must explain why; a generic `The tool could not complete` without a concrete
cause is not an acceptable terminal state.

Success means:

- a running command's output appears incrementally in its expanded transcript
  card;
- the Background Jobs panel receives starts, output and terminal states without
  depending on a ten-second full-list poll;
- a job that starts and finishes between two snapshots is still observable;
- jobs on the server and the operator's machine follow the same visible state
  contract while retaining their correct source label;
- reconnecting produces a current snapshot plus missed events without duplicate
  output; and
- silent commands remain visibly alive through elapsed time and heartbeat state.

## Existing System and Measured Gaps

The visible-run path already has most of a live-output pipeline:

1. shell implementations can forward stdout/stderr through
   `tool_execution_trace`;
2. `visible_tool_exec` drains a bounded buffer and emits
   `tool_output_delta`;
3. SSE v2 carries that event as a `system_event`;
4. the Desk reducer stores it as `ContentBlock.liveOutput`; and
5. `ToolCard` renders that field while a call is running.

Two breaks prevent this from solving the observed problem:

- `live_tool_output_enabled` defaults to false and is not set in the live
  runtime configuration;
- the Desk row transcript calls `kropFor` without passing `liveOutput`, so its
  terminal body still displays only `Kører…` even when the reducer has received
  output.

The Background Jobs panel is a separate path. It requests a merged snapshot
from `/api/jobs` every ten seconds. The snapshot joins supervisor processes,
operator background processes, agents, shell sessions and currently open tool
calls. This is useful recovery state, but it cannot represent a short-lived job
that appears and disappears between polls, and it does not carry incremental
log content.

## Chosen Architecture

Add one authenticated, owner-visible SSE endpoint for Desk background work:

```text
GET /api/jobs/stream?session_id=<id>&after=<cursor>
```

The endpoint emits a canonical initial snapshot and then ordered job events. It
does not replace `/api/jobs`; the existing route remains the durable snapshot
and recovery source. The stream is a live projection over existing truths, not
a second job registry.

The Desk panel opens the stream only while mounted. It applies events to a
keyed local projection and performs a slow snapshot reconciliation after a
stream failure or visibility resume. The current unconditional ten-second poll
is removed.

SSE is preferred over WebSocket because the data flow is server-to-client and
the application already has a tested SSE transport. Reducing the existing poll
interval is rejected: it increases expensive bridge traffic and still cannot
guarantee observation of short jobs.

## Canonical Job Identity and Event Contract

Every event carries:

```json
{
  "cursor": 1842,
  "type": "job_output",
  "job_key": "tool_operator:call_abc",
  "session_id": "chat-7",
  "source": "tool_operator",
  "timestamp": "2026-10-11T14:00:00Z",
  "payload": {}
}
```

`job_key` is `<source>:<stable-id>`. Tool calls use the real tool-use/call ID,
not a name-plus-timestamp reconstruction. Process and shell jobs retain their
existing stable IDs. Events are monotonically ordered by `cursor` within the
server process.

The public event types are:

- `snapshot`: the complete visible `JobsSvar` projection and the current
  cursor;
- `job_started`: complete `BackgroundJob` data for a newly observed job;
- `job_updated`: changed metadata such as pause/resume, elapsed-state anchors,
  title or source availability;
- `job_output`: `stream`, `seq`, `chunk` and `truncated` for stdout/stderr;
- `job_finished`: terminal `status`, `exit_code`, `error`, `finished_at` and
  final output sequence;
- `source_status`: health for the server or operator bridge; and
- `heartbeat`: connection liveness when no job data is available.

`seq` is monotonic per job. The client ignores an output event whose sequence is
not greater than the last applied sequence for that job. This makes replay and
reconnect idempotent.

## Source Adapters

### Visible tool calls

The existing `tool_output_delta` remains the single producer for visible-run
tool output. The job stream receives the same bounded delta through a small
fan-out sink in `tool_execution_trace` or the nearest existing execution-trace
boundary. It does not execute the tool again and does not parse transcript UI
state.

`tool.invoked` establishes the job with its real tool-use ID, session ID,
source and command metadata. `tool.completed` produces the terminal state. Both
server tools and `operator_*` tools use this contract; their source value
determines the Desk label.

### Server background processes and shell sessions

Supervisor processes use their existing process metadata and combined log
files. The stream tails from a byte cursor, never rereads the whole file, and
emits terminal state when the supervisor records it.

Persistent server shell commands use the existing bash-session output callback
where available. An open but idle shell remains a snapshot row and produces no
fabricated output.

### Operator-machine background processes and shell sessions

Foreground operator tools use their existing bridge output callback, which
already transports stdout/stderr while the call is active.

Detached operator background jobs currently write `/tmp/jarvis-bg/<id>.log`,
`.pid` and `.rc` on the operator machine. There is no reverse push channel from
that machine. While at least one authorized job-stream subscriber exists, the
server therefore performs a cursor-based remote tail through the existing
bridge. The tail request returns only bytes after the stored cursor plus current
process/exit metadata. It is deliberately separate from the expensive full
job-list command.

This operator tail is the only polling retained in the live path. It is bounded,
incremental and active only with a subscriber. A terminal `.rc` observation is
emitted before the job may disappear from the live projection, which prevents
short jobs from being missed.

If the operator bridge is unavailable, the server emits `source_status` with a
concrete cause and keeps the last known rows marked stale. It does not turn an
unknown remote state into an empty list.

## Retention, Replay and Backpressure

The stream keeps a bounded in-memory replay ring of job events. Reconnect uses
the last cursor through the `after` query parameter or SSE `Last-Event-ID`.

- If the cursor is still in the ring, missed events are replayed in order.
- If it has expired, the server sends a fresh `snapshot` and continues live.
- Terminal jobs remain in the projection long enough to be delivered and are
  also available through the existing `include_done=true` snapshot.

Output is bounded at every layer:

- each emitted chunk has a fixed maximum size;
- each job keeps only a bounded live tail for replay;
- the Desk keeps at most 65,536 characters of live output per job, matching the
  existing transcript reducer policy; and
- truncation is explicit through `truncated: true` and visible UI text.

A slow subscriber cannot block a tool process. Its queue drops older output
chunks for that subscriber, marks the next event truncated and preserves state
and terminal events.

## Desk Transcript Behavior

The row transcript passes `ContentBlock.liveOutput` and
`liveOutputTruncated` into `kropFor`. An expanded terminal card displays the
live tail while status is running and the final normalized result when it
finishes.

The compact row remains calm: it shows the command description, running shimmer
and elapsed time rather than dumping output into the collapsed transcript.
Opening the row reveals the live terminal content.

For a silent command, the body reads `Kører stadig · intet output endnu` and
updates elapsed time. Live output replaces that sentence as soon as the first
chunk arrives.

## Background Jobs Panel Behavior

Each job remains a compact row by default. Expanding it reveals a terminal-like
body containing the live tail, source (`Server` or `Din maskine`), current
state and elapsed time.

Visible states are:

- `I kø` when known but not dispatched;
- `Kører · <elapsed>`;
- `Pauset`;
- `Færdig · exit 0`;
- `Fejlede · <concrete cause>`;
- `Timeout efter <duration>`;
- `Afbrudt`; and
- `Ukendt — forbindelsen til <source> er væk` for stale source state.

The panel does not auto-scroll an expanded log if the user has scrolled away
from the bottom. A small “nyt output” affordance returns to the tail. This
prevents streaming content from fighting the user.

## Error Contract

A terminal failure must contain at least one non-empty human-readable field:
`error`, `message`, stderr tail or synthesized typed cause. The backend
normalizes failures before emitting `tool_result` or `job_finished`.

Typed causes include at minimum:

- non-zero process exit with exit code and stderr tail;
- timeout with configured duration;
- cancellation/interruption;
- bridge unavailable;
- spawn/dispatch failure; and
- output transport failure where execution outcome is unknown.

The primary card surface renders the concrete cause. Raw data remains available
as secondary diagnostic detail. The English fallback string may remain as a
last defensive guard for corrupt historical data, but new terminal events must
never rely on it.

## Runtime Rollout

`live_tool_output_enabled` remains the rollout gate during development. The
production runtime value is changed to true only after backend, Desk transcript
and Background Jobs tests pass together. No API keys or unrelated runtime
settings are changed.

The rollout sequence is:

1. land event-contract and bounded replay tests;
2. connect existing visible tool output to the Desk row transcript;
3. add job-stream sources and endpoint;
4. connect the Desk Background Jobs projection and recovery behavior;
5. verify server and operator-machine commands end to end;
6. enable the live runtime flag; and
7. retain the snapshot endpoint as recovery and operational fallback.

## Security and Privacy

The endpoint uses the same authenticated ownership rules as the current Jobs
panel. Session filtering is enforced on the server for session-bound tools and
agents. Machine-global supervisor/shell rows preserve the current
`uspecificeret` semantics.

Output is rendered inertly in `<pre>`-style components; it is never interpreted
as HTML or Markdown. Arguments and output retain current clipping and secret
handling. The stream does not introduce a new persisted output database or a
second source of truth.

## Testing and Acceptance

Automated tests must cover:

- row transcript renders successive live chunks before tool completion;
- final tool result replaces live-only state without duplication;
- concrete error text is visible when a tool fails;
- server and operator jobs both emit start, output and finish events;
- a job that completes faster than ten seconds still appears as finished;
- reconnect replays only unseen sequences;
- an expired replay cursor falls back to a canonical snapshot;
- a slow consumer receives truncation rather than blocking execution;
- a bridge outage marks remote state unknown and preserves server jobs;
- session filtering prevents another conversation's tool jobs from appearing;
- silent jobs show heartbeat/elapsed state; and
- mounting and unmounting the panel opens and closes live observation without
  leaving background polling behind.

End-to-end verification uses one server command and one operator-machine
command that each print at least three delayed lines, followed by one failing
command. For both sources, Desk must show each line before completion and the
correct terminal result afterward. A short detached job must remain visible in
the finished section even if it starts and ends between former poll intervals.

## Out of Scope

- Mobile UI or APK changes.
- A general WebSocket transport.
- Persisting unlimited terminal logs in the chat database.
- Making in-run tool calls independently stoppable from the Jobs panel.
- Replacing the process supervisor, operator bridge or shell-session daemon.
- Streaming internal model reasoning.

