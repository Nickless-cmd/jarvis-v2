# Feature status

The repository-wide status source remains
[`docs/design-history/CURRENT_STATUS.md`](docs/design-history/CURRENT_STATUS.md).
This file records the status of the delivered Jarvis Desk changes requested for
implementation.

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
