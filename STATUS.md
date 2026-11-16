# Feature status

The repository-wide status source remains
[`docs/design-history/CURRENT_STATUS.md`](docs/design-history/CURRENT_STATUS.md).
This file records the status of the delivered Jarvis Desk changes requested for
implementation.

## A user stop leaves a findable trace — complete locally (2026-11-16)

- `stopped_for_session(session_id)` returns the run the user stopped, but only while that stop is still the last thing that happened in the session. A later `completed` turn makes it disappear; the rule is derived from state rather than a consumed flag.
- `stopped_prompt_section` puts it in the prompt with the opposite policy of the interruption block: state what was done, then **ask** — never resume on its own. `user-steer-stop` is excluded, since the new message is itself the continuation.
- The agentic checkpoint from a stopped run was already on disk (`phase="user-cancelled"`) but had zero readers: the only consumer, `interrupted_for_session`, requires `interrupted`. The auto-resume path is unchanged.
- Verified: 10 tests in `tests/test_in_flight_stopped.py`, including an end-to-end assertion that the block appears in the assembled prompt.

## `cancel-active` stops the conversation's work — complete locally (2026-11-16)

- `POST /chat/sessions/{id}/cancel-active` cancels **every** `running` run in the
  session via `active_locations()`, not only the newest. A wakeup running
  alongside the user's own turn no longer survives the stop button.
- The cross-process case is covered: `active_locations()` resolves runs owned by
  `jarvis-runtime` from `jarvis-api` through `in_flight_runs`.
- Response keeps `run_id` (newest) and adds `run_ids` (all cancelled). A run in
  another session is never touched.
- `stale_owner` is still refused — the owner process is dead, so there is
  nothing running to stop; that is journal cleanup, not a stop.
- Mutation-verified: collapsing the collection back to the single newest run
  fails both new tests.

## `cancel-active` lookup — complete locally (2026-11-16)

- `POST /chat/sessions/{id}/cancel-active` resolves the run per session
  (`live_run_for_session`) instead of reading the single global
  `visible_runs.active_run` slot. A run in another conversation can no longer
  make your own run unreachable by the stop button, and a foreign run is never
  touched.
- Only a `running` run is a stop target; a terminal one answers
  `{cancelled: false}` instead of claiming success.
- First test for the endpoint: `tests/test_chat_cancel_active.py`, driving real
  runs through `run_event_log.create`. Mutation-verified in both directions.

## CodeView stop and pending-approval projection — complete locally (2026-11-16)

- CodeView shows the stop button for all work in the conversation and stops it
  without a known run id (`cancelRun` when the id is known, otherwise
  `POST /chat/sessions/{id}/cancel-active`).
- A fetched pending approval is merged into the transcript as an
  `approval_request` row; a persisted row with the same id wins, so there is
  one card, and it disappears when decided.

## Session-bound background work — complete locally (2026-11-16)

- An explicit origin session is authoritative: an unusable one leaves the
  result pending with a visible block reason instead of redirecting to another
  session. Sessionless system initiatives keep their existing resolver home.
- Side tasks persist `owner_user_id`, `origin_session_id` and `parent_run_id`;
  `session_id` remains for backward compatibility.
- Twelve scenarios characterize origin isolation, idle wake, busy deferral,
  closed client, restart durability, coalescing, duplicate delivery, invalid
  origin, user stop, agent/side-task parity and the system-initiative home.

## Round row wording — complete locally (2026-11-15)

- `bash`, `search` and `find_files` have explicit present/past wording, so a
  call whose arguments cannot be read still names the action instead of falling
  back to "Brugte et værktøj".
- The completed round row carries only outcome wording ("uden resultat",
  "N fejlede") — no step count and no fold hint.

## Code Mode round timeline — complete locally (2026-11-15)

- An active round shows its heading plus its real working steps; a completed
  round shows the result synthesis. The completed row carries no step count and
  no fold hint — only a warning when a step failed or never answered.
- Steps are derived from actual `tool_use` blocks. None are invented, and no
  count is inferred from anything but the calls themselves.
- A call that never answered is reported as abandoned ("uden resultat"); a failed
  round is marked on the collapsed row so the failure is visible without
  expanding it.
- Completed rounds are frozen: later streaming does not rewrite them, and
  reopening a session renders the result rather than a process that is no longer
  running.
- Three-level visual hierarchy: active (normal contrast), completed (dimmed),
  tool details (secondary, unchanged).
- Chat Mode is unchanged; only the Code Mode row renderer was modified.
- Verification: 3,480 frontend tests passed (1 skipped, 447 files), TypeScript
  build clean, and the rendering measured in Chromium against the real component.

Release state: frontend-only change. No service restart is required, because the
API serves the built PWA from disk.

## Routine policy/presence routing — complete locally (2026-10-26)

- The persisted execution policy is connected to the Routine worker's actual
  dispatch decision.
- Adaptive routines do not interrupt active work; idle, owner-verified sessions
  receive a real contextual wakeup; offline users fall back only when isolated
  execution is permitted.
- Ambiguous ownership and unavailable runtime presence fail closed to a visible
  queued run.
- One idempotent occurrence and fenced lease is shared across both execution
  paths. Session completion stores durable visible-run evidence on the Routine
  run.
- Isolated successes reach the durable Routine inbox, with critical escalation
  preserved.
- Acceptance coverage includes busy Jarvis, idle Jarvis, offline Michelle,
  critical runtime findings, one-time execution and fail-closed sensor states.
- Verification: 191 relevant pytest tests passed; Python compilation and
  `git diff --check` passed.

## Adaptive Chat Flow — complete locally

- Chat Mode offers Living, Calm, and Adaptive without consulting the Code Mode
  row-view preference.
- Code Mode retains the existing row presentation and pacing.
- Active and historical Chat messages share content-preserving fallback rules.
- First-run comparison is live, single-run, per authenticated user, and is
  acknowledged only after render.
- Preference API, persistence, deterministic aggregates, suggestions, and the
  Jarvis preference tool are implemented without storing conversation text.
- Rich output, expandable work detail, Mission Control observability,
  accessibility, and existing scroll ownership remain available.
- Verification: 2,623 frontend tests passed (1 skipped); lint exited 0 with
  0 errors and 55 existing warnings; renderer build exited 0; 68 focused
  backend tests passed; Python compilation
  succeeded, and all five critical mutation checks failed and recovered as
  expected.

Release state: committed locally only. No automatic deployment, tag, push,
package publication, or service restart.
