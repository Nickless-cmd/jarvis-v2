# Development log

## 2026-11-15 — Code Mode round timeline: process while active, result when done

Code Mode round rows now carry the two phases of a round explicitly. While a
round is active its row shows what Jarvis is working on, followed by the round's
actual working steps — one per `tool_use`, each with its real state (done,
running, failed, or abandoned). When the round is left, the step list is replaced
by the existing result synthesis. The completed row carries no step count and no
fold hint: the row's own chevron already shows that it expands, and a count said
nothing about the outcome. What remains on the row is only what cannot be seen
from the synthesis itself — that a step failed or never received an answer
("1 fejlede", "2 uden resultat").

The steps are derived from the round's own blocks (`src/lib/rundeTrin.ts`); no
step exists unless the server sent the call, and no count is inferred. A call
whose `status` is still `running` once the round is no longer active is reported
as abandoned ("uden resultat") rather than as a success, and a failed round is
marked on the collapsed row so it can be seen without expanding it.

Visual hierarchy is now three levels: the active round heading uses normal text
contrast, completed round headings are dimmed, and tool details keep their
existing secondary treatment. No new animation, panel, or decoration was added;
the only motion is the existing ring, shimmer, and `.spin` glyph on the step that
is actually running. Steps are keyed by the server's call id, so a status change
updates the row instead of rebuilding the list.

Chat Mode is untouched: `ChatFlowPresentation` is a separate renderer, and only
`RaekkeTranskript` (Code Mode) changed.

Verification: 447 frontend test files passed, 3,480 tests passed and 1 skipped,
including 19 new tests covering the seven required scenarios. TypeScript build
clean. Rendering was verified in Chromium against the real component: the active
heading measured `rgb(240, 239, 236)` against `rgb(166, 165, 156)` for the
completed one, the step glyph column sits at the same x as the active heading
text, and the rendered reading order matches the specification.

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
