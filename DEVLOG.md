# Development log

## 2026-10-26 — Routine execution policy now controls the real path

Routine occurrences are now routed once, at the existing worker claim point,
from their persisted `execution_mode` and shared runtime presence. `background`
stays isolated, `session` waits for an owner-verified idle app conversation,
and `adaptive` wakes that conversation when idle but falls back to the isolated
runner while Jarvis is busy or the owner is offline. Unknown ownership or
presence remains visibly queued.

Session execution uses the existing visible autonomous-run path with real chat
context, the routine's tool scope and owner identity. The Routine run is leased
before wakeup, and a completion callback stores the visible-run/session evidence
on that same occurrence, preventing scheduler/runner/wakeup duplication.
Background success now projects to the durable Routine inbox; critical results
carry the existing blocking escalation flag.

Verification: 191 Routine, wakeup, guard and autonomous-run tests passed. Python
compilation and `git diff --check` also passed. Full final checks are recorded in
`STATUS.md`.

## 2026-10-15 — Adaptive Chat Flow for Jarvis Desk

Jarvis Desk Chat Mode now has a dedicated conversational presentation layer with
Living, Calm, and opt-in Adaptive modes. Living keeps at most the latest three
real synthesis lines; Calm keeps only the latest meaningful status; Adaptive
chooses deterministically from prior per-user aggregate observations and locks
that choice for the duration of a run. No additional model call or thought
summary is requested.

The first real Chat run can claim and render a live side-by-side Living/Calm
demonstration from the same run. The server marks onboarding seen only after the
rendered comparison acknowledges its short-lived atomic claim. Preferences,
claims, bounded observations, and suggestion outcomes are self-scoped to the
verified authenticated principal. The new `set_chat_flow_preference` Jarvis
tool uses the same service and exposes no user-id argument.

Chat and Code presentation are now explicitly separated at `MessageRow`.
Code Mode retains its existing row renderer, preference key, and pacing. Chat
Mode uses bounded animation-frame pacing for final text, preserves files,
images, video, widgets, tool details, and errors, and promotes retained text
exactly once when an older, failed, or interrupted stream lacks
`finalAnswerStarted`. Work disclosures use honest completed/interrupted/failed
copy, one polite live status, keyboard controls, and reduced-motion CSS.

Verification on 2026-10-15:

- Frontend: 344 Vitest files passed; 2,623 tests passed and 1 skipped.
- ESLint exited successfully with 0 errors and 55 existing warnings.
- Renderer TypeScript/Vite build completed successfully.
- Backend focused suite: 68 pytest tests passed.
- Python `compileall` and `git diff --check` completed successfully.
- Five critical contracts were mutation-tested: Chat/Code isolation, the
  three-line cap, authoritative final transition, authenticated ownership, and
  onboarding acknowledgement timing.

No deployment, push, tag, package publication, or service restart was performed.
