# Cross-Process Autonomous Stream Reattachment Design

## Implementation evidence (2026-10-14)

Implemented on `codex/autonomous-stream-reconnect` with these observed proofs:

- The pre-fix two-process reproduction showed a runtime-owned run in the shared
  journal while API `/active-runs` could discover it but `/subscribe` returned
  404 and `/sessions/{id}/live` returned 204.
- Every autonomous visible entrypoint now registers the same stable run ID in a
  process-local, bounded v2 frame log before its worker thread starts.
- The shared journal records the producer role. Public routes authorize the
  resolved session first, then stream locally or proxy raw SSE bytes through an
  authenticated loopback-only owner endpoint.
- A real subprocess integration test proves discovery, two simultaneous
  subscribers, reconnect from a saved cursor without old deltas, API routing
  recreation during the run, explicit state after producer termination, and a
  single producer invocation.
- Desk and Mobile keep global log offsets; pings do not advance them and
  `relay_gap.resume_idx` resets the cursor base. HTTP 404/410 reconcile, 503
  retries, and 401/403 fail without synthesizing `message_stop`.

The intentional boundary remains unchanged: frames are not persisted per
token. Producer death loses the in-memory replay window, so recovery uses the
persisted session transcript and an explicit pruned/unavailable state.

**Date:** 2026-10-14
**Status:** Proposed for implementation
**Repository:** `jarvis-v2`

## Goal

Desk and Mobile must be able to discover, attach to, disconnect from, and
resume the same autonomous visible run regardless of whether `jarvis-api` or
`jarvis-runtime` owns execution. A missing process-local stream must never be
reported as successful completion, and every discovery or subscription path
must preserve session isolation.

## Verified Current Failure

The failure was reproduced with two separate Python processes sharing one
isolated runtime home:

1. Producer PID `2204594` registered `autonomous-xproc-proof` in
   `in_flight_runs` and published a frame to its own `run_event_log`.
2. API PID `2204593` read the shared journal.
3. `GET /chat/active-runs` semantics returned the run as `working`.
4. `GET /chat/runs/autonomous-xproc-proof/subscribe` semantics returned
   `404 run not found`.
5. `GET /chat/sessions/chat-xproc-proof/live` semantics returned `204`.

The exact contract break is therefore verified:

- `core/services/in_flight_runs.py` is shared across processes and is now used
  by `/chat/active-runs`.
- `core/services/run_event_log.py` is process-local.
- Both live SSE endpoints in `apps/api/jarvis_api/routes/chat.py` read only the
  API process's event log.
- A runtime-owned run can consequently be advertised by API while its frames
  remain unreachable through API.

Two client-side amplifiers are also verified:

- Desk `followRun()` turns subscription HTTP 404 into a synthetic
  `message_stop`.
- Mobile `startStream()` does the same when reconnect receives HTTP 404.

This falsely converts “the requested process has no local stream” into “the
run completed successfully.”

## Additional Verified Defects

### Authorization

`GET /chat/sessions/{session_id}/live` invokes `_kraev_adgang(session_id)`.
`GET /chat/runs/{run_id}/subscribe` does not resolve the session and invoke the
same guard. Knowing a run ID is therefore sufficient to reach its local SSE
frames once the caller has passed general API authentication.

`GET /chat/active-runs` merges every live record from the shared journal
without filtering the associated session through the session access rule.
Authentication middleware alone does not provide per-session isolation.

### Autonomous producer coverage

`start_autonomous_stream_run()` translates visible output to v2 SSE and writes
both `run_event_log` and the legacy `run_follow` buffer.

`start_autonomous_run()` only performs that translation when `follow=True`.
With `follow=False`, it consumes the underlying visible generator without
publishing replayable SSE frames. Inbox, scheduled, recurring, dream, session
spawn, and other legacy call sites can therefore produce a durable answer but
no attachable live stream.

### Cursor behavior

Mobile's primary stream path maintains a global log-frame cursor, excludes
ephemeral pings, understands `relay_gap.resume_idx`, and fences callbacks from
superseded EventSource generations.

Desk's passive `followRun()` always requests `from_idx=0` and has no reconnect
cursor. A new passive follow can replay already reduced frames and relies on
higher layers to avoid visible duplication.

## Constraints

- Preserve real incremental SSE delivery.
- Do not persist every token or frame synchronously to SQLite.
- Do not introduce Redis, Kafka, Docker, or another infrastructure service.
- Keep one stable client-visible run ID.
- Permit multiple simultaneous authorized subscribers.
- Producer execution must not depend on subscribers.
- Persisted session state remains the final reconciliation source.
- Keep the existing bounded ring buffer and explicit replay-gap behavior.
- Preserve the existing API/runtime deployment: the same FastAPI app on ports
  8080 and 8011, distinguished by `JARVIS_ENABLE_RUNTIME_SERVICES`.
- Produce one final commit, including documentation and tests.

## Considered Approaches

### 1. Proxy SSE to the owner process — selected

The shared run journal records which process role owns the stream. Public API
routes authorize the session and either subscribe locally or proxy the byte
stream from an authenticated loopback-only endpoint on the owner process.

Advantages:

- Preserves the existing in-memory ring buffer and token cadence.
- Avoids a disk write for every token.
- Supports many readers because each reader has an independent offset.
- Reuses the repository's established API/runtime localhost forwarding model,
  port helpers, process roles, and internal shared secret.
- Allows API restart during a runtime-owned run: the restarted API can read the
  journal and reconnect to the still-running owner.

Limitations:

- If the producer process itself dies, its in-memory replay window is gone.
  The journal and persisted session still provide an explicit interrupted or
  reconciliation path; the design does not pretend the lost live frames exist.

### 2. Shared bounded append-only files

Each run could write framed records to a bounded file that both processes read.
This would survive an API restart and could retain frames after producer exit,
but it introduces per-frame filesystem traffic, rotation, partial-record crash
handling, ownership cleanup, and another lifecycle authority.

This is disproportionate while the owner process is already reachable through
localhost HTTP.

### 3. SQLite frame journal

Frames could be rows in the operational database. This provides querying and
restart persistence but adds write amplification and contention on an already
significant SQLite workload. Batching would also weaken true incremental
delivery. This approach is rejected without performance evidence requiring it.

## Selected Architecture

### 1. Shared run locator

Extend each `in_flight_runs` record with a non-secret `producer_process` field:

- `api` when `JARVIS_ENABLE_RUNTIME_SERVICES` is false;
- `runtime` otherwise.

The value comes from the existing `central_xproc.process_role()` helper. Older
records without the field remain readable. For an old running record, routing
may conservatively try the known runtime port after confirming the owner PID is
alive; it must never classify a failed lookup as successful completion.

The shared locator exposes focused read operations:

- resolve a run ID to its journal record;
- resolve the newest live run for a session;
- classify lifecycle as running, terminal, stale-owner, or unknown.

The journal remains lifecycle truth. It does not store stream content or
subscriber cursors.

### 2. Uniform autonomous publication

Every visible autonomous execution path must create one `run_event_log` entry
under the same stable run ID before its worker thread begins. Its visible output
is translated once through `translate_to_v2()` and appended to that log.

`start_autonomous_run()` retains its public signature and caller behavior, but
`follow` controls only whether the legacy session-keyed `run_follow` tee also
receives frames. It no longer controls whether the authoritative run-keyed log
exists.

`start_autonomous_stream_run()` uses the same publication lifecycle instead of
maintaining a divergent contract. Execution and persistence remain detached
from subscribers.

Publication ordering is:

1. construct the stable run ID;
2. register lifecycle and producer role in the shared journal;
3. create the local run event log;
4. start execution;
5. append non-ephemeral v2 frames to the bounded ring;
6. settle authoritative lifecycle;
7. mark the local log done and retain the current replay window according to
   existing pruning rules.

### 3. Route extraction required by the Boy Scout rule

`apps/api/jarvis_api/routes/chat.py` is over 2,000 lines. Before changing its
run-streaming behavior, extract the cohesive active-run and follow/subscribe
route group into a focused route module. The old module re-exports public
symbols used by tests or callers so existing imports remain compatible.

The extraction is mechanical first and must pass existing tests before the
behavioral change begins.

### 4. Internal owner endpoint

Add an internal SSE endpoint served by both process instances. It reads only
the current process's `run_event_log` and accepts:

- stable run ID;
- global `from_idx` cursor.

Security follows the established JarvisX internal dispatch pattern:

- loopback clients only;
- reject `Forwarded` and `X-Forwarded-For`;
- require the shared internal token using constant-time comparison;
- do not accept a user identity or make an independent user authorization
  decision.

The public API is solely responsible for user authorization before invoking
this endpoint. The internal response forwards the existing SSE bytes without
re-parsing or renumbering them.

The endpoint returns explicit machine-readable failure classes for local
unknown/pruned streams. It never proxies again, preventing loops.

### 5. Public discovery and subscription

#### `GET /chat/active-runs`

Merge local event-log records and shared journal records by stable run ID.
Before returning an item, apply the existing session access predicate to its
session. Unauthorized sessions are omitted rather than revealed through an
error, since this is a collection endpoint.

#### `GET /chat/runs/{run_id}/subscribe?from_idx=N`

Resolution order:

1. Resolve the run locally or from the shared journal.
2. If no record exists, return 404 `run_unknown`.
3. Resolve its session and run `_kraev_adgang(session_id)` before returning
   lifecycle information or SSE data.
4. If the local event log exists, stream from it.
5. If another live process owns it, proxy the internal owner stream from the
   requested global cursor.
6. If lifecycle is running but the owner or stream is temporarily unavailable,
   return 503 `stream_unavailable` with `Retry-After`.
7. If lifecycle is terminal and the replay window is gone, return 410
   `stream_pruned` with a reconciliation instruction.

#### `GET /chat/sessions/{session_id}/live`

Authorize the session first. Resolve its newest live run across local state and
the shared journal, then use the same local-or-owner subscription function.
Return 204 only when authoritative state says the session has no active run.
Never return 204 merely because the API process lacks local frames.

### 6. Stream status contract

| HTTP status | Meaning | Client action |
|---|---|---|
| 200 | SSE attached locally or through owner proxy | Reduce frames and retain cursor |
| 204 | Session has no authoritative active run | Reconcile persisted session, then become idle |
| 401 | Authentication missing or expired | Enter authentication flow; never complete run |
| 403 | Session not authorized | Show authorization failure; never expose state |
| 404 | Run ID has no known lifecycle record | Reconcile session; do not synthesize success |
| 410 | Run is terminal but replay was pruned | Fetch persisted session, then complete from authoritative state |
| 503 | Run is active but stream owner is unavailable | Retry with cursor and backoff |

SSE `message_stop` remains the only live-stream evidence of normal terminal
delivery. An HTTP error is never converted directly into `message_stop`.

### 7. Desk reconnect

Replace the one-shot passive `followRun()` behavior with a run-aware controller
that maintains:

- stable run ID;
- global non-ping frame cursor;
- current connection generation;
- reconnect attempt count;
- whether a logical `message_stop` was observed.

It uses the same cursor rules already proven on Mobile:

- pings do not increment the cursor;
- normal replayable frames increment it once;
- `relay_gap.resume_idx` resets the cursor to the server-provided base before
  following frames advance it;
- callbacks from a replaced connection are ignored.

Network failures and 503 retry from the saved cursor. A 404 or 410 triggers
session reconciliation; only persisted terminal state or a received
`message_stop` ends the logical run. Authentication and authorization failures
surface as errors.

### 8. Mobile reconnect and lifecycle

Keep the existing offset and generation fencing in `startStream()`. Change its
HTTP error policy:

- remove 404-to-`message_stop` synthesis;
- retry 503 with the current cursor;
- reconcile on 404/410;
- propagate 401/403 as non-success errors;
- invoke `onComplete` only after `message_stop` or successful persisted-state
  reconciliation.

Foreground reattachment uses the run ID returned by `/active-runs` and never
POSTs the original message. Backgrounding stores the current run ID and cursor
before closing the socket. Switching sessions fences the old stream generation.

### 9. Terminal and replay-gap behavior

The producer owns terminal generation. A correctly completed translated stream
contains one logical `message_stop`. Existing server protection may synthesize
a recovery terminal only when authoritative local state is done without a
terminal frame; it must not do so because a remote lookup failed.

Ring-buffer overflow keeps the existing explicit `relay_gap` marker. The proxy
does not count its own keepalive traffic, modify offsets, or buffer the entire
upstream response. A long tool call remains active according to journal state;
subscriber keepalives do not become replayable frames.

### 10. Reconciliation after restart or pruning

- API restart while runtime owns the run: read shared locator and proxy to the
  surviving runtime buffer from the client's cursor.
- Client reconnect after completion while owner retains replay: replay through
  `message_stop`.
- Client reconnect after terminal replay pruning: return 410 and fetch the
  persisted session transcript.
- Producer process death: classify the owner as dead, expose interrupted
  recovery rather than an active but empty stream, and reconcile persisted
  content. No component claims lost frames were delivered.

## Observability

Reuse structured logging and Central where available. Emit metadata-only events
at lifecycle boundaries:

- `run_created`
- `run_registered`
- `stream_published` (first frame and optional aggregate count, not every token)
- `subscriber_attached`
- `subscriber_detached`
- `resume_requested`
- `resume_succeeded`
- `resume_failed`
- `replay_gap`
- `terminal_delivered`

Fields are limited to run ID, session ID, producer/subscriber process roles,
cursor, reason, frame count, and timestamp. Message content, tokens, secrets,
authorization headers, and private transcript data are forbidden.

## Test Strategy

### Backend unit and route tests

- local API-owned subscription and cursor replay;
- session access required for run-ID subscription;
- unauthorized sessions omitted from active-run discovery;
- unknown, pruned, unavailable, and unauthorized states remain distinct;
- terminal frame delivered once logically;
- ping exclusion and replay-gap cursor behavior;
- long silent tool interval does not terminate an open run;
- multiple subscribers read independently;
- legacy autonomous call paths publish to the run-keyed log;
- duplicate execution is not launched by any follow endpoint.

### True multi-process integration tests

Use subprocesses, not two Python objects in one interpreter:

1. Start an isolated runtime-owner process with a local event log and shared
   journal record.
2. Start or exercise a separate API process.
3. Discover the run through public API state.
4. Subscribe through API and confirm frames originate from runtime.
5. Attach two independent subscribers and confirm both reach terminal state.
6. Disconnect one subscriber and resume from its cursor without duplicate
   execution or duplicate reduced frames.
7. Restart only API while runtime continues, then resume successfully.
8. Stop the producer and verify explicit unavailable/interrupted recovery.

The inverse API-owned path is covered as well so proxy selection does not break
local streams.

### Client tests

Desk and Mobile tests cover:

- no synthetic completion on 404, 401, 403, or 503;
- cursor resumes after a mid-stream disconnect;
- pings do not advance cursor;
- replay gaps reset cursor correctly;
- replaced connections cannot mutate reducer state;
- background/foreground and session switching;
- 410 reconciliation after completion;
- two devices following one run without launching another model run;
- exactly one logical terminal transition.

### Quality gates

- targeted backend pytest suites;
- new true multi-process test suite;
- Desk Vitest suite for touched streaming modules;
- Mobile Jest suite for touched streaming modules;
- `python -m compileall core apps/api scripts`;
- broader existing test suites where runtime is practical, with every unrelated
  pre-existing failure reported explicitly.

## Documentation and Delivery

Update `DEVLOG.md` and `STATUS.md` with:

- verified two-process root cause;
- chosen owner-proxy architecture;
- status and authorization contract;
- tests executed and their results;
- remaining limitation that producer-process death loses its in-memory replay
  window and requires persisted-session reconciliation.

Stage only intended paths and create one commit through
`scripts/commit_with_attribution.py` with message:

`fix(streaming): restore cross-process autonomous run reattachment`

## Acceptance Criteria

The change is complete only when all of the following are demonstrated:

1. A runtime-owned autonomous run is discoverable and streamable through API.
2. Desk and Mobile can simultaneously follow the same stable run ID.
3. Reconnection resumes from a correct global cursor without duplicate model
   execution or silent frame loss.
4. API restart does not sever a runtime-owned run.
5. Active but unreachable streams are not presented as completed.
6. Terminal/pruned streams reconcile from persisted session state.
7. Unauthorized users cannot discover or subscribe to another user's run.
8. True multi-process tests, client tests, and relevant quality gates pass.
9. Production verification is reported separately from automated evidence; no
   claim of a production fix rests solely on unit tests.
