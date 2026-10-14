# Autonomous Execution, Inbox Ownership & Run Continuity

**Date:** 2026-10-14
**Author:** Jarvis (self-audit, read-only)
**Scope:** `core/services/*`, `core/runtime/db_inbox.py`, `apps/api/*`
**Mode:** READ-ONLY. No production behaviour was modified. No service was restarted. No autonomous work was triggered.

Evidence labels used throughout:

- **CONFIRMED** — read directly in current source, or measured in live runtime records.
- **SUPPORTED HYPOTHESIS** — consistent with code and observations, but not directly measured.
- **NOT VERIFIED** — plausible, no evidence either way.
- **WORKING AS DESIGNED** — behaves as the code intends; not a defect.

---

## 1. Executive summary

Jarvis has **nine independent producers** capable of starting a new autonomous model run. They do not share an execution policy. They share exactly one thing: a pre-flight guard inside `start_autonomous_run()` — and that guard is a **positive list** (`BESKYTTEDE_ORIGINS`, nine origins) that several producers never reach, because they pass an origin that is not on it, or because they call a different starter entirely.

The Inbox is **not** an execution coordinator. It is an awareness surface, a commitment tracker and a mutation gate. Exactly **one** component reads it as an execution source: `inbox_idle_waker`. Ten components write to it. There is no atomic claim of a commitment, and no shared answer to "is this task already being worked on?".

The most important discovery is not a race. It is an **identity defect**: the architecture has no single identity that represents the *work*. It has `run_id`, `session_id`, `wakeup_id`, `task_id`, `initiative_id`, `agent_id` and inbox item identity — and the one that is supposed to represent the obligation (`task_id`) is **overwritten with the run id at every new link in a recovery chain**. Measured in the live journal: `visible-aa6c3e7e` and `visible-22d2d866` share a `task_id` but both carry `recovery_attempt=1` — the same attempt number, twice. A counter that cannot see the chain cannot stop it.

---

## 2. Autonomous producer inventory

Every call site that can start a new autonomous model run, measured by `grep` over `core/` and `apps/`:

| # | Producer | Trigger | Process | Starter called | Origin passed | Guard? | Inbox write? | Inbox read? |
|---|---|---|---|---|---|---|---|---|
| 1 | `wakeup_dispatcher` | due wakeup row | runtime | `start_autonomous_stream_run` | `wakeup` | **yes** (`levende_run_i_session`, L114) | no | no |
| 2 | `inbox_idle_waker` | open gating inbox item | runtime | `start_autonomous_run` | `inbox` | **yes** (via starter) | no | **yes** (`kandidater`) |
| 3 | `scheduled_tasks` | due scheduled row | runtime | `start_autonomous_run` | `scheduled` | **yes** (via starter) | yes (`scheduled_inbox`) | no |
| 4 | `recurring_tasks` | due recurring row | runtime | `start_autonomous_run` | `recurring` | **yes** (via starter) | no | no |
| 5 | `routine_trigger_adapters.dispatch_heartbeat_initiative` | heartbeat initiative | runtime | `start_autonomous_run` | `heartbeat` | **yes** (via starter) | no | no |
| 6 | `dreaming_session` | dream material | runtime | `start_autonomous_run` | `dream` | **yes** (via starter) | no | no |
| 7 | `session_spawn.start_session` | explicit spawn request | api | `start_autonomous_run` | caller-supplied | **only if origin on list** | no | no |
| 8 | `agent_message_receipt` | child-agent completion | api | `start_autonomous_stream_run` | `agent-completion` | **NO** — not on list | no | no |
| 9 | `visible_runs_memory` | continuation after segment exit | api | `start_autonomous_run` | *(none)* | **NO** — empty origin | no | no |
| 10 | `discord_gateway` / `telegram_gateway` | user message | api | `start_autonomous_run` | *(none)* | **NO** — by design | no | no |
| 11 | `jarvisx_processes` | desk process request | api | `start_autonomous_run` | *(none)* | **NO** — by design | no | no |
| 12 | `visible_run_recovery_dispatcher` | due recovery claim | runtime | `start_user_run_detached` | *(n/a)* | **NO** — different starter | no | no |
| 13 | `living_executive.indhent_forsoemte_afbrydelser` | `runtime.visible_run_interrupted` event | runtime | via `process_event` → impulse | *(n/a)* | **NO** | no | **read-only** (`get_record`) |

**CONFIRMED.** Producers 8–13 start runs without passing through `blokeringsgrund`. Producers 8, 9, 10, 11 are **WORKING AS DESIGNED** — they are responses to something Bjørn did, and blocking them would drop a reply he is waiting for (the exclusion is documented in `run_guard.py:38-46`). Producers 12 and 13 are **not** designed exclusions; they are separate execution paths that were never wired to the guard.

### Legitimate internal cognitive activity (does NOT start a model run)

`heartbeat_runtime` ticks, `mood_oscillator`, `central_*` nerves, `dream_hypothesis_judge`, `opmaerksomhed`, `affect` — these write state and observations. They are not run producers. `heartbeat_runtime` appears in the brief's list but starts runs only indirectly, through `routine_trigger_adapters.dispatch_heartbeat_initiative` (producer 5).

---

## 3. Execution flow diagrams

### 3.1 The guarded path (producers 1–7)

```
trigger (wakeup / inbox / scheduled / recurring / heartbeat / dream)
        │
        ▼
start_autonomous_run(message, session_id, origin)
        │
        ├─ routine_cutover_enabled()?  ── NO (measured: flag unset) ──┐
        │                                                             │
        ▼                                                             │
resolve session:  session_id  OR  auto-{origin}-{YYYYMMDD}            │
        │                                                             │
        ▼                                                             │
blokeringsgrund(origin, session)                                      │
        │                                                             │
        ├─ origin NOT in BESKYTTEDE_ORIGINS → "" (free) ──────────────┤
        ├─ levende_run_i_session(session) → reason ──┐                │
        │                                            ▼                │
        │                              parker_forpligtelse()          │
        │                              (inbox item, bloker=True)      │
        │                              → return (no run)              │
        ▼                                                             │
run starts in background thread ◄─────────────────────────────────────┘
```

### 3.2 The unguarded paths (producers 8–13)

```
agent_message_receipt ──► start_autonomous_stream_run(origin="agent-completion")
                              └─ no guard call at all

visible_runs_memory ─────► start_autonomous_run(origin=None)
                              └─ blokeringsgrund("") → "" → free

visible_run_recovery_dispatcher ──► start_user_run_detached(recovery_task_id=…)
                              └─ different starter; no guard

living_executive ──► process_event → execute_impulse → run
                              └─ reads journal (get_record) but never writes it
```

### 3.3 The recovery chain (where continuity breaks)

```
run A reaches round limit (18) → forced-finalize-unverified
        │
        ▼
in_flight_runs: task released back (release_recovery_claim, retry_after_s=30)
        │
        ▼
recovery dispatcher: claim_due_recovery → picks OLDEST candidate
        │
        ▼
stempl_genoptagelse(run_id=<new>, task_id=<old>)   ← only call site: detached_run.py:213
        │
        ▼
start_visible_run → mark_started(run_id=<new>, task_id=<old>)
        │
        ▼
run B born. Run A stamped 'interrupted'.
        │
        └──► 'interrupted' is exactly what made step 2 release the task. Loop closes.
```

---

## 4. Inbox integration matrix

Ten writers, one execution reader.

| Writer | Source type | Gating? | Executable? |
|---|---|---|---|
| `self_wakeup` | `wakeup` | yes (owner=jarvis) | yes (via `wakeup_dispatcher`) |
| `scheduled_inbox` | `scheduled` | **no** (`IKKE_GATENDE_KILDETYPER`) | no |
| `routine_inbox` | `recurring` | **no** | no |
| `run_closure_gate` | `job` | no (owner=huset) | no |
| `run_guard.parker_forpligtelse` | `afvist_run` | **yes** (`bloker=True`) | yes (added to `KAN_DISPATCHES_KILDETYPER`) |
| `decision_adherence_gate` | `decision` | no | no |
| `ci_status_watch` | `ci` | no | no |
| `scout_inbox_delivery` | `scout` | no | no |
| `routine_diagnostics` | `diagnostic` | no | no |
| `restart_self_tools` | `restart` | no | no |

**Reader:** `inbox_idle_waker.kandidater()` → `vaek_paa_aabne_poster()`. That is the only execution consumer.

### Which responsibility is actually implemented?

| Responsibility | Implemented? | Evidence |
|---|---|---|
| A. Awareness surface | **yes** | `inbox_prompt_section()` puts open items in the prompt tail every turn |
| B. Commitment tracker | **yes** | `inbox_items` with status, expiry, `afgjort_at` |
| C. Mutation gate | **yes** | `inbox_gate.evaluer_inbox_mutation` blocks tools inside a run |
| D. Wakeup mechanism | **yes, partially** | `inbox_idle_waker`, but only for `kraever_handling=1` + verified owner |
| E. Execution coordinator | **NO** | no atomic claim; no "is this already running?" query; no cross-producer registration |

**CONFIRMED.** Inbox is A+B+C+D. It is not E.

### Specific questions from the brief

- **Which sources bypass Inbox entirely?** All of them except `inbox_idle_waker` itself. Producers 1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13 never read Inbox before starting.
- **Which write AND start directly?** `scheduled_tasks` (writes via `scheduled_inbox`, starts via `start_autonomous_run`) and `run_guard.parker_forpligtelse` (writes, then the waker starts later). The first is the dangerous one: the item is informational, the run is direct, and the two are not linked by any id.
- **Can an item exist while its task executes elsewhere?** **Yes.** `scheduled_tasks` writes an inbox item and starts a run in the same breath; nothing marks the item as "executing".
- **Can an item be marked awakened without execution?** **Yes — and this was a real bug, now fixed.** `start_autonomous_run` returned `None` on guard rejection while the caller believed it started. Fixed 14/10 (`b43796a9b`): the rejection now writes a parked commitment. **But the fix is incomplete**: `inbox_idle_waker` still calls `noter_vaekning` *before* `_start_run`, and `_start_run` returns `None` on rejection — so the item is marked awakened even when the run was refused. The rollback (`nulstil_vaekning`) only fires on an *exception*, not on a silent rejection.
- **Can execution finish without closing the item?** **Yes.** No producer closes its own inbox item; closure is manual (`inbox_done`) or by the run itself.
- **Can multiple items initiate competing runs?** **Yes.** `MAKS_PR_RUNDE = 2` — the loop starts up to two runs per round, and `_noget_koerer()` is checked **once, before the loop**, not between iterations.
- **Wrong session?** **Not anymore** for the waker (fixed 14/10: `_maal_session`). Still possible for producers that pass `session_id=None` → `auto-{origin}-{date}` silo.
- **Intended session unavailable?** The waker skips the item (`continue`) and leaves it open. Correct behaviour.

---

## 5. Cross-process and session ownership

`run_guard.levende_run_i_session` reads two sources in order:

1. `run_event_log.active_run_for_session` — **in-memory, per process**.
2. `in_flight_runs.levende_koersler` — **shared file + flock**.

Source 2 is the cross-process one and is why the guard works at all. **CONFIRMED** in `run_guard.py:60-88`.

**The gap:** `inbox_idle_waker._noget_koerer()` does **not** use `run_guard`. It calls `wakeup_dispatcher._active_turn_blocks(session)`, which reads `run_event_log` — **in-memory, per process** (`inbox_idle_waker.py:131-147`). The daemons run in `jarvis-runtime`; Bjørn's turn runs in `jarvis-api`. So the waker's own pre-check is blind to a live api-process run. It is saved only because `start_autonomous_run` re-checks with the cross-process guard — but only for origins on the positive list, and `inbox` is on it, so this path is covered. **The blindness is real but currently masked.**

**Session continuity is best-effort, not an invariant.** `session_id` survives through: scheduled tasks (column added 14/10), recurring tasks (column added 14/10), inbox items (column added 14/10), `parker_forpligtelse`. It does **not** survive through: `dreaming_session` (hardcoded `session_id=None`), `agent_message_receipt` (resolves the *current* app session, not the session that delegated), `visible_runs_memory` continuation (passes `run.session_id`, which is correct).

---

## 6. Task identity and duplicate execution

**The architecture cannot reliably answer "is this task already being worked on?"**

Available identities:

| Identity | Represents | Survives a new run? |
|---|---|---|
| `session_id` | the conversation | yes |
| `run_id` | one execution | **no — new id per run** |
| `task_id` | the obligation | **should, but is overwritten** |
| `wakeup_id` | one wakeup row | n/a |
| `initiative_id` | one heartbeat initiative | n/a |
| `agent_id` | one delegated agent | yes |
| inbox `kilde_id` | one inbox item | yes |

**CONFIRMED defect.** `in_flight_runs.mark_started` wrote `"task_id": str(task_id or run_id)` at two sites (L315, L378). `start_visible_run` calls `mark_started` **without** recovery parameters, so every new link in a chain overwrote the inherited `task_id` with its own `run_id`. Fixed 14/10 (`31f64fe8a`): the value is now inherited from the existing record when the caller supplies none.

**Measured in the live journal** (`~/.jarvis-v2/state/in_flight_runs.json`, 27 records):

```
task_id visible-aa6c3e7e7b914385b7d999a9e9 → 2 runs
    visible-aa6c3e7e7b914385b7d999  completed        a=1 g=1
    visible-22d2d866d56142989bb139  failed_terminal  a=1 g=1
```

Two runs, one obligation, **both at attempt 1**. The chain counter never advanced. This is the identity break, measured.

**Second defect, same effect.** `claim_due_recovery` selects the **oldest** candidate (`min` on `settled_at`). Both `settle_recovering` and `release_recovery_claim` write a **fresh** `settled_at`. So a task that was just released goes to the back of the queue, and a different, older task is picked instead. Measured in the log:

```
18:26:58  resumed visible-b6aae6e8 as run visible-ca873886 (generation 1)
18:31:39  task visible-b6aae6e8 released after forced-finalize-unverified
18:31:43  continuing task visible-f7f0ada2 (generation 1, attempt 1)
```

The chain does not continue — it hops. **No task is ever claimed three times in a row**, so a limit of three can never be reached.

**Third path.** `living_executive.indhent_forsoemte_afbrydelser()` runs every minute, reads `runtime.visible_run_interrupted` events, and starts runs through `process_event` → `execute_impulse`. It touches the journal exactly once — a **read** (`get_record`, L322). It never writes `task_id`, never writes `recovery_attempt`, never calls `stempl_genoptagelse`. `stempl_genoptagelse` has **one** call site in the whole repository (`detached_run.py:213`), reachable only via `claim_due_recovery` → `start_user_run_detached(recovery_task_id=…)`. **CONFIRMED: only the dispatcher path stamps the chain.**

---

## 7. Confirmed bugs (file/line evidence)

| # | Bug | Evidence | Status |
|---|---|---|---|
| B1 | `task_id` overwritten by `run_id` at every chain link | `in_flight_runs.py:315,378` | **FIXED** `31f64fe8a` |
| B2 | Guard rejection was logged but wrote nothing | `visible_autonomous_run.py:153`, `autonomous_stream_run.py:44` | **FIXED** `b43796a9b` |
| B3 | `living_executive` starts runs without stamping the chain | `living_executive.py:894`, `:322` (read-only) | **OPEN** |
| B4 | `claim_due_recovery` picks oldest; release resets `settled_at` → chain hops | `in_flight_runs.py:885-906` | **OPEN** |
| B5 | `inbox_idle_waker` marks awakened before start; silent rejection not rolled back | `inbox_idle_waker.py:280-296` | **OPEN** |
| B6 | `MAKS_PR_RUNDE=2` with `_noget_koerer()` checked once, before the loop | `inbox_idle_waker.py:52,262,264` | **OPEN** |
| B7 | `_noget_koerer` reads per-process `run_event_log`, not the shared journal | `inbox_idle_waker.py:139-144` | **OPEN** (masked) |
| B8 | `agent-completion` and continuation origins are not guarded | `run_guard.py:48-51`, `agent_message_receipt.py:135` | **WORKING AS DESIGNED** for agent-completion; **OPEN** for continuation |
| B9 | `dreaming_session` hardcodes `session_id=None` → auto-silo | `dreaming_session.py:368` | **OPEN** (low impact) |

---

## 8. Suspected problems, not confirmed

- **SUPPORTED HYPOTHESIS:** the six-link chain measured on 14/10 (17:29 → 17:34 → 18:01 → 18:03 → 18:26 → 18:31) was driven by B3 and B4 together. In the minutes measured, `living_executive` logged `indhentede 1 afbrydelser, genoptog 0, sprang 1 over` — its own gates stopped it. The engine and its blind spot are confirmed; the finger on the trigger in each individual link is not.
- **NOT VERIFIED:** whether B7 has ever caused a real duplicate. The cross-process guard in the starter covers the `inbox` origin, so the blindness is currently masked.
- **NOT VERIFIED:** whether `session_spawn` has ever been called with an origin outside the positive list.
- **NOT VERIFIED:** the impact of B9 in production.

---

## 9. Existing safeguards that work

- **`run_guard.blokeringsgrund`** — cross-process, reads the shared journal, covers nine origins. **CONFIRMED working** (measured 14/10: a recurring run was correctly refused while a session run was live).
- **`parker_forpligtelse`** — a refused commitment is now written to the Inbox with `bloker=True` and a 30-day expiry, bound to its session. **CONFIRMED** (8 tests, `tests/test_afvist_forpligtelse.py`).
- **`_foedselsvagt`** — a run announced but never born is closed after 120 s with `run-never-born`. **CONFIRMED** (5 tests, `tests/test_run_birth_watchdog.py`).
- **`settle_terminal` sibling sweep** — closing a task closes its siblings sharing `task_id`. **CONFIRMED** (measured 14/10: a ghost run closed itself).
- **`inbox_gate`** — blocks mutations inside a run while a gating item is open. **CONFIRMED.**
- **`_maal_session`** — the waker wakes the session the item belongs to, not an auto-silo. **CONFIRMED** (measured 14/10).
- **`run_closure_gate`** — closes the loop when a run completes. **CONFIRMED.**

---

## 10. Ranked findings

### P0

1. **B3 + B4 — the recovery chain cannot terminate.** Two independent mechanisms (an unstamped producer, and a queue that hops) both defeat the attempt limit. Measured: a chain of six links in one day, every link at attempt 1.
2. **B1 — no identity represents the work.** Without it, no counter, limit or dedup can work. (Fixed, but the fix is one line and the class of bug is architectural.)

### P1

3. **B5 — a commitment can be marked awakened without execution.** Silent rejection is not rolled back.
4. **B6 — two runs per round with a single pre-loop check.**
5. **B7 — the waker's own pre-check is per-process.** Masked today, fragile tomorrow.

### P2

6. **B9 — `dreaming_session` writes to an auto-silo.**
7. **B8 (continuation) — continuation runs carry no origin and are therefore unguarded.**

---

## 11. Proposed smallest viable correction

**Do not build a new coordinator.** The infrastructure already exists; it is not wired.

**Step 1 (smallest, highest value): make the chain stampable from every producer.**
Move the chain stamp out of `detached_run.py:213` and into `start_autonomous_run` / `start_autonomous_stream_run`, so *any* producer that starts a run for an existing obligation stamps it. One function, two call sites.

**Step 2: make the queue continue instead of hop.**
`claim_due_recovery` must prefer the task that was most recently released, not the oldest. One sort key.

**Step 3: make the waker's claim honest.**
`noter_vaekning` must be written *after* a confirmed start, or `_start_run` must return a status the waker can roll back on. One return value.

**Step 4: make the waker's pre-check cross-process.**
Replace `_active_turn_blocks` with `run_guard.levende_run_i_session` — the function that already exists for exactly this. One import.

**Step 5: re-check `_noget_koerer()` between iterations**, not only before the loop. One line.

Steps 1–5 are each a handful of lines. None changes Inbox semantics. None reduces autonomy.

---

## 12. Non-goals and regression risks

**Non-goals:**

- No new identity system. `task_id` already exists; it must be *preserved*, not replaced.
- No reduction of autonomy or proactive behaviour.
- No change to Inbox gating semantics.
- No blocking of user-requested continuations (Discord, Telegram, agent-completion, desk processes).
- No removal of legitimate parallel work or deliberate agent delegation.

**Regression risks:**

- **Step 1** touches the hot path of every autonomous run. A stamping failure must be self-safe (log and continue), never fatal.
- **Step 2** changes which task is picked. A wrong sort key could starve a task. Needs a test that a released task is picked next.
- **Step 3** changes when the wakeup trace is written. If written too late, a crash between start and trace causes a double wakeup. The current order was chosen deliberately; the fix must keep the rollback path.
- **Step 4** makes the waker stricter. A false positive would suppress a legitimate wakeup. `levende_run_i_session` is fail-open, which is the correct direction.

---

## 13. Staged implementation plan

| Stage | Change | Test |
|---|---|---|
| 1 | Chain stamp in both starters | a chain of 3 links keeps one `task_id` and increments `recovery_attempt` |
| 2 | `claim_due_recovery` prefers most-recently-released | released task is claimed next, not an older one |
| 3 | Waker rolls back on silent rejection | a refused start leaves the item unawakened |
| 4 | Waker uses the cross-process guard | a live api-process run blocks the waker |
| 5 | `_noget_koerer()` re-checked per iteration | two eligible items produce one run, not two |
| 6 | `dreaming_session` carries a session | dream run lands in a named session |

Each stage is independently revertible. Stage 1 is the prerequisite for 2–3 to have any effect.

---

## 14. Test coverage gaps

Measured by counting test files referencing each producer:

| Producer | Test files | Gap |
|---|---|---|
| `run_guard` | 6 | good |
| `scheduled_tasks` | 13 | good |
| `recurring_tasks` | 9 | good |
| `wakeup_dispatcher` | 9 | good |
| `dreaming_session` | 5 | no test for session selection |
| `routine_trigger_adapters` | 5 | no test for the cutover-off path |
| `inbox_idle_waker` | 3 | **no test for two eligible items in one round** |
| `session_spawn` | 1 | thin |
| `agent_message_receipt` | 1 | thin |
| `living_executive` | 0 | **no test at all for the recovery path** |

**Missing regression scenarios:**

1. Two producers start the same obligation → one run, one chain.
2. A chain of N links increments `recovery_attempt` monotonically.
3. A refused start does not mark the inbox item awakened.
4. Two eligible inbox items in one round produce one run.
5. A released task is claimed before an older one.
6. `living_executive` stamps the chain when it starts a continuation.

---

## 15. Evidence and reproduction

**Sources inspected (read-only):**

- `core/services/run_guard.py` (full)
- `core/services/visible_autonomous_run.py:79-175`
- `core/services/inbox_idle_waker.py` (full)
- `core/services/recurring_tasks.py:495-545`
- `core/services/scheduled_tasks.py:300-340`
- `core/services/routine_trigger_adapters.py:180-225`
- `core/services/dreaming_session.py:350-380`
- `core/services/session_spawn.py:100-130`
- `core/services/agent_message_receipt.py:120-145`
- `core/services/wakeup_dispatcher.py:300-320`
- `core/services/in_flight_runs.py` (mark_started, claim_due_recovery, release_recovery_claim)
- `core/services/living_executive.py:780-900`
- `core/runtime/db_inbox.py` (noter_vaekning, opret_eller_hent)
- `core/services/inbox_gate.py:266+`

**Runtime records:**

- `~/.jarvis-v2/state/in_flight_runs.json` — 27 records; one `task_id` with two runs, both `a=1`.
- `journalctl -u jarvis-api` — the six-link chain on 14/10, all at `generation 1, attempt 1`.
- `journalctl -u jarvis-runtime` — `living_executive: indhentede 1 afbrydelser, genoptog 0, sprang 1 over`.

**Environment measured:**

- `JARVIS_ROUTINES_CUTOVER` — **not set**. Production uses the legacy path everywhere.
- `BESKYTTEDE_ORIGINS` — nine origins; `agent-completion` and continuation are deliberately outside.

**No autonomous work was triggered. No service was restarted. No production behaviour was modified.**

---

## 16. Note on requested deliverables

`DEVLOG.md` and `STATUS.md` do not exist anywhere in the repository (verified by `find`). They were not created, because their intended location and format are unknown and inventing them would add documentation that no process reads. This audit is the single documentation change.
