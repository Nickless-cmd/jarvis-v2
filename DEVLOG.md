# Development log
## 2026-11-26 (third pass) — The order of a turn is data, not a reconstruction

**Root cause.** `deriveChatFlow` collapsed the turn into two BUCKETS:
`workBlocks` and `finalBlocks`. The order «Answer A → Round 1 → Answer B» could
not be expressed — A and B landed in one bucket, the round in the other, and the
presentation layer had to rebuild the sequence from metadata. That is not a
rendering defect; the data was collapsed before rendering saw it.

**Fix.** `segmenter: FlowSegment[]` now carries the turn's order: each contiguous
run of blocks with the same role is one segment, and `id` is `role:index` of the
segment's FIRST block. Blocks are only ever appended (SSE addresses explicit
indices, and a replay re-sets the same indices), so the id is stable for the
whole turn. `workBlocks`/`finalBlocks` are now DERIVED from the segments with
identical content and order, so every existing reader (`useChatPacedBlocks`,
`harSlutblok`, `transcriptFilter`, `svarPacing`) keeps its contract unchanged.

The role comes from `block.phase` when the server stamped it; position is only
the fallback for persisted blocks without a phase. That fallback is the
documented open limitation: an unstamped text block can still change role when
`final_answer_start` arrives. Stamped blocks cannot — proven against the old
classification.

**The three invariants are now tests**, one each in
`chatFlowModel.segmenter.test.ts` (9 tests): a new block gives no existing
segment a new id; a new round does not reclassify a shown answer; no segment
disappears when another grows. Plus the case the buckets could never pass: the
ordered Answer A → Round 1 → Answer B.

**Three measurement defects, all real.** (a) `__intMaal` read
`document.body.textContent`, which also sees what the fold has hidden — it now
reports both `vistTegn` (the pace cursor, `textContent`) and `synligtTegn`
(what the user sees, `innerText`); they were identical through the whole run,
so nothing was hidden behind the fold. (b) `__intFold` read `aria-expanded`
synchronously after `.click()` — before React re-rendered — and returned the OLD
value; it now waits two frames and returns `skiftede`, and validity requires
that the head actually changed state at every toggle. (c) `process.exit(0)`
fired even when `GYLDIG` was false; both measurements now exit on validity.
Verified by running a copy with validity forced false: the measurement ran
through, reported `GYLDIG: false`, and exited 1. The first attempt at that
control was itself invalid — the copy sat in `/tmp` where `playwright` does not
resolve — so it failed on a module error, not on the condition.

**Measured:** integration 91 → 185 → 240 → 294 → 430 characters across three
fold toggles, 12 after the deliberate turn-id change; head state flipped
`false → true → false` at every toggle. 3716 desk tests green, `tsc` clean.

## 2026-11-26 (second pass) — The measurement was of a mechanism, not of its integration

GPT verified the two pushed commits against `main` and found three defects. All
three were real; one was a production bug, not a test gap.

**1. The turn id still changed in the turn's first frame.** `client_turn_start`
set a `turId` but bound no run: `activeRunId` was still `null`. The server's
first `message_start` then carried a run id the client did not know, so
`_sameRun` was false and `_bevar` fell back to false — and the turn got a NEW id
exactly when pacing began. Identity survived rounds, reconnects and follow-ups,
but not the one frame where it must be established first. Fixed with a third
`_bevar` branch: when the client opened the turn (`turId` set, no run bound,
status working) the identity is preserved; a foreign turn with `origin` still
turns the branch off. Side effect caught while fixing it: `arbejdeEfterSvar`
became true on the turn's first frame — there was no locked answer to come
*after* — which would have unfolded the head at every turn start. The condition
now requires `state.svarLaast`.

**2. The counter-test could pass on the key change alone.**
`efterNoegle.vistTegn < start.vistTegn || efterNoegle.key !== start.key`. The
key change is something the measurement did on purpose, so it can never be
evidence that the cursor resets; and `start` is the FIRST sample (5 chars), not
the last before the switch (39), so a fall from 39 to 18 passed unnoticed. Now
compared against the sample immediately before the switch. Fixing it exposed a
second error in the same line: `pace[pace.length - 1]` is `efterNoegle` itself,
because `laesPace` already pushed it — the comparison was `x < x`.

**3. The probe measured a sibling component.** `PaceProbe` called the real
`useChatPacedBlocks` but returned `null` and sat beside the transcript. It proved
that an isolated pacer keeps running while another component folds; not that the
pacer delivering the user's text does. The measurement surface now mounts the
real `ChatFlowPresentation` (`?flade=pace`) and reads the cursor out of the DOM
as the longest prefix of the final answer present on the page — independent of
CSS class names and of how the word animation splits text into spans. A remount
that reset the pacer would leave the hook's own state correct in the new
instance; only the rendered text reveals that it started over.

**Measured.** Integration: 91 → 140 → 191 → 240 chars across three fold toggles,
378 after 700 ms with no fold, and 12 when the turn id was changed on purpose.
Mechanism: 5 → 15 → 27 → 39, counter-test 18. Both valid.

**Tests.** `streamReducer.turId.test.ts` gained the first-frame case and its
counter-test (a foreign turn with `origin` still gets a new id). Verified against
the old gate: 1 of 12 fails there, 12 of 12 pass now. 3707 desk tests green,
`tsc --noEmit` clean.

## 2026-11-26 — The turn's identity is not its clock; the block's phase is not its position

**Root cause (measured, two distinct couplings).**

1. *Pace identity was time.* The pacing key in `ChatFlowPresentation` was
   `tur-${turStart}`, and five sites in `streamReducer` wrote
   `turStart: Date.now()` — two of them (`follow_start`, `client_turn_start`)
   unconditionally. Any frame that rewrote the key dropped
   `useChatPacedBlocks`' cursor to `''`, so the answer was re-paced from the
   beginning mid-turn. This is the "empty screen, then the final answer starts
   pacing outside the head" symptom.

2. *Block semantics were position.* `projektion()` derived a text block's phase
   solely from `i > sidsteKald`. When a new round arrived after the answer,
   `sidsteKald` moved and an already-rendered final answer flipped back into the
   work group — same block, new phase, new visual row. That is the
   "blink/hik" Bjørn described.

**Change.** New immutable `StreamState.turId` (`tur-<uuid>`), set once per turn
and preserved by every frame belonging to the same turn: `message_start` with a
new run id, `follow_start` of the same run, reconnects, follow-up runs. Only a
genuine new turn gets a new id. `ChatFlowPresentation` now paces on `turId`
(`turStart` kept only as fallback for persisted turns), and `confirmedRef` keys
on `turId` instead of `runId` — the latter changes on every follow-up run, so
confirmed texts were being reset mid-turn.

`projektion()` now reads `block.phase` first (`sse_v2_events.py` sets
`commentary`/`final_answer`) and falls back to the positional rule only for
blocks without `phase` (older persisted turns, providers that omit it). A block
that has received its phase from the server can no longer be reclassified by a
later block.

**Measured.** 10 new `streamReducer.turId.test.ts` tests and 7 new
`raekkeModel.semantik.test.ts` tests. The semantics test was run against the
old code via `git stash`: 4 of 7 fail there, 7 of 7 pass with the change — the
test carries weight. 2202 desk tests green, `tsc --noEmit` clean.

**Open, deliberately documented, not claimed solved.** `follow_start` is
client-local (`CodeView.tsx`), never emitted by the server. "A new run id is a
new turn" is therefore our own heuristic, not a server contract. It is right in
the cross-device case (2026-11-16: a passive client merged a new turn into the
previous message) but unproven when the new run continues the turn the client
already shows. Distinguishing the two needs a turn id in the `follow_start`
payload, which does not exist today. The test asserts current behaviour and is
annotated with what must change, not what to delete.

Not started: independent round containers in the document flow, coordinated
fade/collapse, the persisted-message handover, and frame-by-frame verification
in the existing Playwright harness (`apps/jarvis-desk/scripts/maaling.mjs`).

## 2026-11-24 — Coordination §8: measure through the path the turn actually takes

`scripts/koordinering_maaling.py` (`--hours N`, `--json`, read-only `mode=ro`)
answers the nine §8 measurements, each tagged with source *and* the function it
was measured through (decision `dec_9ba465a80a7b`). Path A =
`push_initiative → find_covering_work → record_decision("coordinated")`; path B =
`act_on_initiative → claim_initiative → claim_work → decline_initiative`.
Baseline: `docs/findings/koordinering-maaling-baseline-2026-11-24.{json,txt}`.

Baseline, 24 h to 2026-11-24 22:06Z (this is the *before* side — the coordination
code went live ~21:56Z, minutes earlier):

- 1: 15 initiatives entered the queue (`runtime_initiatives`); 89 more were turned
  away at the gate (`heartbeat.initiative_rejected`, shared by several reasons).
- 2: 0/15 became a `claim_work` task — measured zero, but all pre-deploy.
- 4: 0 (lower bound: extra acted initiatives with identical `work_fingerprint`).
- 9: 843 — all from stale `initiative-followup` tasks (`blocked`, standing stock
  since 2026-11-01), 0 pending/leased initiatives stuck; 1 expired in-window.
- 3, 7, 8: **cannot be measured yet** — zero `coordination.decision` events exist,
  so `0` would be indistinguishable from "not instrumented". The tool says so.
- 5: cannot be measured — "legitimate" is a judgement; no function persists a
  verdict (upper bound shown: 1 declined, 89 gate rejections).
- 6: cannot be measured — `costs.run_id` has no link to initiative/task;
  `claim_work` persists no run id.

Implemented and tested (`tests/test_koordinering_maaling.py`); the baseline was
run against the live DB. Not verified in operation: 3/7/8 need a post-deploy run.

## 2026-11-24 — Coordinate on concrete work relations, not on topic words or a clock

**Root cause (measured).** An initiative carried only text. `initiative_queue._gentaget_paastand`
(topic-word overlap, own queue only) was too loose — it merged different actions on one topic —
and `_aktiv_synlig_tur` (30-minute clock) was too coarse — it treated all activity as conflict
(48 % of a week's 133 inner-voice initiatives fell inside the window). Neither could answer
"is this exact action already covered?". Further causes found in the code:
`heartbeat_runtime` `act_on_initiative` took `pending[0]` with no cross-process claim (`_QUEUE_LOCK`
is a thread lock), stored `origin_ref=tick_id` (initiative→task relation lost), and its completion
callback wrote status `completed`, which `runtime_tasks.update_task` silently normalises to `queued`.

**Change.** New `core/services/work_coordination.py`: a work fingerprint = user scope + action class
+ concrete anchors (ids, files, code identifiers). `find_covering_work` checks tasks, agent
assignments and recent visible runs (same user only; references, never content); finished work is
covered for 24 h unless `new_evidence=True`. Atomic accept: unique partial index
`runtime_tasks.work_fingerprint` (queued/running only — never locks a topic, reaper takeover reused)
and CAS `claim_initiative` (lease in `next_attempt_at`). The 30-min gate is now a fallback only for
initiatives with no anchor+action; the "Jeg …" state rule no longer rejects a sentence that has
anchor+action. Every decision publishes `coordination.decision` with a reason.

**Status:** implemented + committed in worktree; not deployed, not verified in production.
Not done: Mission Control panel for `coordination.decision`; before/after metrics beyond the baseline
in the commit message; visible-turn → task registration (visible runs are matched by preview text).
## 2026-11-20 — `done` is not "the pacer is finished"

Desk Chat Mode dumped the tail of an answer at `message_stop`. `ChatView` passed
`flushFinalAnswer={stream.status === 'done'}`, and `useChatPacedBlocks` returns
the full target whenever `options.flush` is set. The flush was added in
54fa0d850 when the live row was unmounted before the pacer drained; the row is
now held mounted by `paceFinalAnswer` until `onAnswerPaced`, so the flush had
become redundant and only caused the dump.

Measured in `ChatView.test.tsx` (real pacer, 1,680-char answer, samples every
8 ms after `message_stop`): visible text went 14 → 27 → 1679 characters, i.e.
27 → 1679 in one step. After removing the flush: it rolls out monotonically and
completes in ~6.9 s (the existing catch-up curve, `PACE_CATCH_UP_SECONDS = 2`,
unchanged). `flushFinalAnswer` stays as an explicit, documented escape hatch.

Not reproduced / not done: text streaming inside the turn-header fold
(hypothesis B), and the word-animation tuning. No change was made for those.

## 2026-11-16 — A prune function nobody called, and a guard that cried wolf

Bjørn asked whether the database needed a different solution as it grows. The
measurement said no — 6.03 GB with 320 GB free is not a fire — but it turned up
two defects worth fixing, and both are the same shape: a mechanism that looks
alive because it exists.

`prune_cadence_decisions` was written, tested, and correct. It was called from
exactly one place: `tests/test_db_cadence_journal.py`. Zero production callers.
The table held 231,645 rows growing ~19,000/day. That is the same figure as
`cheap_lane_route_decisions`, which became 45 % of the entire database in
September because nobody had put it on the list — except this time the function
already existed. It just never ran.

The retention guard had the opposite problem. `tabeller_uden_politik()` reported
`signal_archive` and `cadence_decisions` as having no agreed cleanup, while both
had a prune function. The guard looked for a `created_at` column; `signal_archive`
uses `archived_at`, `cadence_decisions` uses `closed_at`/`last_seen_at`. A guard
that cries wolf about tables that are in order is worse than no guard, because
you learn to ignore it.

Both are now placed in `_EGEN_OPRYDNING` with their actual time column written
into the reason, and `prune_cadence_decisions` runs from
`cache_maintenance_daemon` alongside the other retention calls. Measured after:
the guard reports four tables instead of six, and still catches a genuinely
uncovered table.

The test that matters is not that the function works — it already did. It is
that the call exists in the production path. Removing the call fails
`test_prune_cadence_decisions_kaldes_fra_produktionsstien`; that mutation was
measured, not assumed.

## 2026-11-16 — A stale wakeup is marked, never cancelled

Bjørn: *"det var det her jeg mente [...] Ikke afbestil. Mærk. En post der får et
flag: «muligvis forældet — sagen blev lukket 15/11 kl. 17:44». Så fyrer den som
den skal, men med beviset foran mig i stedet for gætteriet."*

The occasion was measured the same day: a wakeup booked 15/11 16:40 with a
24-hour delay fired on 16/11 17:40 about a matter that had been settled a few
hours after the booking. The post was perfectly healthy. It pointed at a world
that no longer existed.

Every guard in the wakeup system turned out to be **mechanical**: `er_stadig_fyret`
asks "is it receipted", `dispatch_skipped` asks "was it already forwarded",
`cleanup_old_wakeups` asks "is it too old", and `booking_dedup.find_dublet`
compares text and time. Not one of them asks *is the premise still true*. The
system knows whether a booking is **alive**. It never knows whether it is
**true**.

The obvious fix — a scanner that cancels what has already happened — was
rejected, and the reason is the same one that shaped the stop fix earlier the
same day. A scanner that decides "this is done" is making a judgement about the
world. When it is wrong it removes work **without a trace**, which is exactly
the hole the stop fix was built to close: a stop must not vanish silently, but
it must not raise itself either. Cancelling automatically recreates the hole
from the other side.

So `core/services/wakeup_staleness.py` reads and marks. It has no write path at
all — the test patches `_save`, `cancel_wakeup` and `mark_wakeup_consumed` to
raise, so any future "helpful" auto-cancel fails the suite. It gathers three
facts, each with a timestamp the reader can check: how long before firing the
post was booked; whether a side task the post points at has been closed; and how
many turns have completed in the conversation since. The third is the same rule
as `stopped_for_session` — *the conversation moved on* is derived from state,
not from a consumption flag.

It fails towards keeping. A post that cannot be dated, or whose sources cannot
be read, gets no marking and fires exactly as before. And under an hour old it
is left alone: 65 of 69 posts in the live store had a delay under an hour, and a
warning on every short check is a warning nobody reads.

Marking lives in `direktiv_for`, which is the single entry point for **both** the
dispatcher and the inbox waker — so one hook covers both paths.

Measured against the actual post from yesterday: the text now reads *"booket
15/11 17:40 — 24 timer før den fyrede. Der er afsluttet 86 ture i denne samtale
siden posten blev booket."* The premise is put in front of the reader instead of
being assumed.

One test was green for the wrong reason and had to be fixed: the first version
of the no-write guard ran with all sources stubbed to `None`, so `fakta` was
empty and an inserted auto-cancel was never reached. A guard that cannot reach
the branch it protects proves nothing about it.

## 2026-11-16 — The round line carries the life, so it must exist before the work does

Bjørn: *"den aktive rundelinje skal være synlig fra starten for det er den der bærer livet... sådan er det os i chat mode"*.

He was right, and the measurement is blunt: `senesteRunde` requires at least one `tool_use` element, and `visTurhoved` requires `arbejde.length > 0`. From the moment a turn starts until the first tool call lands, code mode rendered **nothing** — no ring, no word. The one window where the user is waiting for a sign of life was the one window with no face on it.

Chat mode never had this hole. `rundeTekst` falls back to `model.hovedTekst` when there is no work yet, so the presence ring and the word "Tænker" are there from the first frame. Code mode had the fallback removed somewhere along the way, or never received it.

The waiting line reuses the round line's wrapper, icon and text style, so the real round takes over the same slot without moving anything. It has no fold arrow — there is nothing to fold yet — and `cursor: default` says the same thing to the mouse. The text is the server's reported `working_step` when it passes the same `isMeaningfulStatus` guard the round line uses (so a raw tool name cannot leak through), otherwise "Tænker".

The gate is `arbejdeKoerer && arbejde.length === 0` — the same `arbejdeKoerer` the rest of the surface uses, so the line disappears when the answer begins and returns if work arrives after the answer lock.

Verified: six new tests. Mutation measured — removing the gate drops the three that require the line to be visible; the three "it disappears" tests pass by design, because they guard the opposite direction. 767 green across the rich and view suites, `tsc` clean, both bundles built, and `rv-venter` verified present in `dist/` **and** `dist-web/` rather than assumed.

## 2026-11-16 — A stop leaves a trace you can find, and does not resume itself

Bjørn asked the question the mechanism could not answer: *"de burde ikk dø, men endten lande i din inbox eller i en kø … eller risikere vi jo noget kunne gå tabt"*.

The stop itself was already durable. Since 17/9 a user stop is settled **before** the run is aborted, precisely so it does not look like an interrupted turn — an interrupted turn resumes itself, so the user's own stop would start again. `settle_terminal` wrote the record as `cancelled`.

The defect sat one level up. The only reader, `interrupted_for_session`, requires `status == "interrupted"`, so a `cancelled` record was invisible to every consumer — and the agentic checkpoint written by the stopped run (full exchanges, partial text, `phase="user-cancelled"`) sat on disk with **zero readers**. The trace existed; the entry condition could never be satisfied. Same shape as the defects above: a mechanism that looks alive because it writes something.

`stopped_for_session` closes it without touching the auto-resume path. It returns the most recent `user-cancelled` run for the session, and only while that stop is still the last thing that happened there — as soon as a later turn settles `completed`, the notice disappears on its own. The rule is derived from state, not from a consumed flag: a flag would require trusting that the exact prompt that was built also reached the model.

`stopped_prompt_section` renders it with the **opposite** policy of the interruption block: do not resume; say what was done and ask. Deliberately not a queue entry — a post that waits for the user is not a run that starts itself.

`user-steer-stop` is excluded on purpose: there the new message *is* the continuation, and a "you stopped me" notice on top of it would make Jarvis ask about something the user had just answered.

Verified: 10 tests, including one end-to-end that asserts the block is present in the actually assembled prompt (the two `_awareness_add` gates could otherwise discard it silently). Mutations: removing the "conversation moved on" rule, and admitting `user-steer-stop`, each fell exactly their own test.

## 2026-11-16 — The stop button stops the conversation's work, not just the newest run

The entry below closed with its own limitation: *"two runs in the same session resolve to the newest ... the older one is not reachable by this endpoint"*. That was true, and it is the case the user actually hits — a wakeup starts while he is sending, two runs live in one session, and pressing stop left the older one running.

`live_run_for_session` returns `candidates[-1]`; that is right for "which stream do I attach to" and wrong for "stop what I am looking at". `chat_cancel_active` now collects every `running` location in the session from `active_locations()` — which covers both the process-local journal and runs owned by the other process through `in_flight_runs` — and cancels each, keeping the newest as `run_id` for compatibility and adding `run_ids` for the full list. A foreign session's runs are filtered out by `session_id`, so "all" means all of *this* conversation.

`stale_owner` is deliberately still refused. It is not a stop target: `_from_record` sets it when `owner_still_alive(owner)` is false, so nothing is running. Cancelling it would report success for stopping something already gone; closing that journal row is cleanup, not a stop.

`tests/test_chat_cancel_active.py` grew two tests: two runs in one session both get cancelled (replacing the test that asserted the opposite), and a run in another session is not touched while two in the target session are. Mutation-verified: replacing the collection with `alle = [rid]` fails both, restored 6 passed. Broader: 51 passed across the cancel-active, run-stream-route, run-event-log and supersession suites; import smoke confirms the endpoint uses both lookups.

## 2026-11-16 — `cancel-active` looks up the run per session, not in the global slot

The stop button's server-side fallback had a lookup defect that the entry above named as its own limitation: *"backend `cancel-active` only matches the single globally active visible run"*.

`visible_runs.active_run` is **one key without a session suffix**, and `register_visible_run` overwrites it. So when a run registered last in another conversation, the slot pointed at that conversation. `chat_cancel_active` compared the slot's `session_id` with the requested one, found no match, and answered `cancelled: false` while the user's own run kept going. It never killed a foreign run — the comparison made that safe — but it could not stop the right one, which is the worse failure for a stop button.

The per-session lookup already existed: `live_run_for_session` in `core.services.run_stream_locator`, used by `/sessions/{id}/live`. It reads the process-local journal first and falls back to `active_locations()`, which resolves cross-process runs through `in_flight_runs` — so a run owned by `jarvis-runtime` is found from `jarvis-api`. The endpoint now uses it and cancels only when `lifecycle == "running"`; a terminal run is not a stop target and no longer reports success.

`cancel_visible_run(run_id)` was already correct per run: it checks the controller dict *and* `visible_runs.control.<run_id>`, and `is_cancelled()` falls back to the DB flag, so a cancellation set in `jarvis-api` is read by `jarvis-runtime`.

`tests/test_chat_cancel_active.py` is the first test for this endpoint — there was none. It registers real runs through `run_event_log.create` and drives the real `live_run_for_session`, so it measures the lookup rather than mocking it. Mutation-verified: replacing the per-session lookup with "globally newest" fails both cross-session tests, one in each direction (A stopping B's run, and B stopping A's). Reverted, 5 passed.

Not covered: a `stale_owner` run is refused rather than cancelled. Two runs in the *same* session originally resolved to the newest only — the entry above fixes that.

## 2026-11-16 — CodeView stop for all work, and the pending approval card goes into the transcript

Two client defects in Jarvis Desk, both fixed in `apps/jarvis-desk/src/**` (so installed Desk and PWA move together).

**Stop button.** `CodeView` was a forgotten copy of `ChatView` from before 12/11: `streaming` was only the client's own run and stop called `stream.abort()`, a no-op for a run this client never started. It now shows stop for any work in the conversation (`stream.status === 'working' || bgActive || followState.status === 'working'`), keeps the run id the active-runs poll already found (`bgRunId`), and stop calls `cancelRun(runId)` when an id is known, falling back to the new `cancelActiveRun(sessionId)` (`POST /chat/sessions/{id}/cancel-active`, which no client called before). A run the client streams itself still goes through `stream.abort()`.

**Approval projection.** The fetched `pendingApproval` lived only in state, so with no persisted `approval_request` row (persistence is fail-open; `refreshMessages` lags up to 1.5 s after a restart) both views drew it in `.composer-notices`, "on top of the turn". `medVentendeGodkendelse` now merges it into the message list as a synthetic `approval_request` row before `fletGodkendelser`, so it stands where a persisted row would. A persisted row with the same `approval_id` wins (one card, never two); a card for another session is left alone; once decided, `pendingApproval` is null and the row is gone.

Mutation-verified: stop — reverting the `streaming` condition fails all three new tests, removing the fallback fails the cancel-active test, removing the cancelRun branch or the stored `bgRunId` fails the cancelRun test. Approval — a no-op projection fails (a), (c) and both view tests, removing the dedupe fails (b), removing the null guard fails (c), removing the session guard fails its test, un-wiring either view fails that view's test.

Not covered: the real server endpoint is only called through a mocked client (the backend lookup defect behind that mock — `cancel-active` matching only the single globally active visible run — is fixed in the entry above); the synthetic row's `created_at` is client time; a session with no user/assistant message still shows the empty state instead of the card.

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
