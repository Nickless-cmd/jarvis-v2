# Development log

## 2026-11-16 — Real process restarts and a real claim race, and the bug they found

The session-bound continuation above was characterized through the durable store and the lease/generation semantics — not through an actual restart. That gap is now closed, and closing it exposed a genuine defect.

**`tests/test_session_bound_process_restart.py` launches fresh interpreters as subprocesses.** The workers share an isolated on-disk SQLite database and an isolated recovery journal but no Python module state. One worker writes a wake intention and is killed with `os._exit`; a second claims it and is killed the same way; a third must then collect the intention and dispatch it. The race test runs twelve rounds with four simultaneous workers released through a file gate and requires exactly one winner per round. Both patch `db_core.DB_PATH` explicitly in every worker, because patching `core.runtime.db.DB_PATH` alone does not affect `connect()`.

**The defect it found.** With `recovery_limit = 1`, an expired lease became permanently unclaimable: the single attempt had been spent by the dispatcher that died, so the reclaim the lease exists to enable could never happen. The limit is now 2 — one normal dispatch attempt plus one reclaim. The proof is the mutation: set back to 1, the restart test fails with `'started': 0` where it expects `1`; restored, it passes. The whole wake/recovery surface is green with the change (212 passed).

**A note on the measurement itself.** `tests/test_a*.py` and `tests/test_b*.py`–`test_e*.py` were run to completion for the first time: 38 failures and 9,905 passes across 915 files. Thirty-eight failures across a file set this large is not a number to trust at face value, so the failing files were re-run on the base commit `2a51a9234`: 25 of them fail identically there, and the remaining 13 — in `test_brain_index_orphans`, `test_causal_graph` and `test_central_brain_link` — pass 42/42 when run in isolation on the same tree. Those 13 were contention artifacts from `--timeout=30` on a single core with 694 files in one process, not regressions. The earlier appearance of large `F` blocks in these files was a different cause entirely: `/tmp` is a 16 GB tmpfs and had filled with `pytest-of-bs` directories from killed runs, so tests could not write their temp files.

## 2026-11-16 — Session-bound background work: origin is authoritative, continuation is characterized

An initiative that starts in a conversation now keeps that conversation as its authoritative origin through the whole lifecycle. Two layers were missing; the rest of the chain already existed and was reused, not replaced.

**Routing (`wakeup_dispatcher.pick_wakeup_run_target`).** An explicit origin that is an external or unusable channel previously fell back to *any* app session, which is exactly the silent redirection the contract forbids. It now returns `None`, so the caller leaves the row pending with a visible block reason. The resolver fallback is used only when the origin is empty — i.e. for sessionless system initiatives, which keep their own home.

**Lineage (`side_tasks.flag`).** A flagged task now persists `owner_user_id`, `origin_session_id` and `parent_run_id` explicitly, derived from the running context when not supplied. `session_id` is retained for older readers.

**Characterization (`tests/test_session_bound_background_continuation.py`).** The twelve requested scenarios run against the real chain — `stage_wake` → `in_flight_runs.claim_due_recovery` → `recover_due_once` → `claim_for_model_step` — and against the real `agent_result_outbox` table in an isolated DB, not mocks of the functions under test.

Measured, not assumed: six deliberate mutations each failed exactly their protected scenario — routing restored to the old redirect (scenario 9), coalescing removed (scenario 7), lineage fields emptied (scenarios 1 and 11), session scoping dropped from the claim query (scenario 2), the active-turn guard made blind (scenario 4), and `cancel_pending_wake` made a no-op (scenario 10). Every mutation was reverted and verified gone before the next one; the tree was clean at each step. Restored: 12 passed, and the affected wake/recovery/side-task surface green. The repository's own e2e suite (`tests/e2e/`, `test_auto_continuation_e2e.py`) passes on the same tree, so the new contract does not disturb the queue-and-inbox path it sits on.

Not covered: no test drives a real process restart or a real multi-worker race; both are characterized through the durable store and the lease/generation semantics, not through an actual restart. That limitation is stated here rather than implied by a green run.

## 2026-11-16 — Docs-drift gate: scoped by file type, and regenerates once instead of blocking

Two fixes to the pre-commit docs-drift gate, both measured against real inbox evidence rather than assumed.

**Scoping was by directory name, not file type.** `_staged_under` matched `apps/` for `api_docs_gen`, but that generator reads only `*.py`. A `.tsx` change under `apps/jarvis-desk` therefore started a Python docs check that could not possibly go stale from that file — and when older drift existed anywhere, the commit was refused for a run that never touched Python. Measured 15/11-2026: 3 of 5 docs-drift blockages were exactly this false trigger (inbox posts 521216, 514347, 351824). Each generator now declares its `source_suffixes`, and scoping counts only staged files of those types.

**Genuine drift now regenerates once.** The remaining 2 of 5 were real: a run touching `core/` could not be sealed unless someone ran the generators by hand. When — and only when — the commit fails with docs-drift text, the gate now runs the three generators and retries the commit once with the generators' own output added. Any other commit failure (attribution, secrets) still abstains honestly. The added paths are restricted to `_GENERATED_DOCS_PREFIXES`, read from the generators themselves, so a regeneration cannot sweep unrelated files into the commit.

Proof is the mutation, not the green run. Removing the file-type filter fails the two false-trigger tests; making drift detection always-true fails the "other failures must not regenerate" test; removing the "any new docs?" gate fails the no-op-retry test. End-to-end: with only a `.tsx` staged and stale docs in `core/`, the old code exits 1 and the new code exits 0.


## 2026-11-15 — A call without a readable subject still says what it was

`describeTool` falls back to a generic phrase when it cannot read a subject out
of the call's arguments. That fallback was reached more often than it should
have been: `bash` with an empty command, `search` and `find_files` had no entry
in the `NO_SUBJECT` table, so the round row reported "Brugte et værktøj" — which
says no more than that *something* was used.

Each of the three now has a present/past pair, so the row can answer what was
done even when the argument itself cannot be read. The fallback still exists for
tools that genuinely have nothing to name; it is no longer the answer for the
common ones.

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
