# jarvis-code Migration Trigger — go/no-go checklist

**Purpose:** the human-readable record of the §8/§9 migration-trigger decision
(docs/superpowers/specs/2026-07-14-jarvis-code-parity.md) — whether jarvis-desk
code mode may migrate onto the jarvis-code Tier 0/1 substrate. Each §9
criterion links to the test that proves it and the actual run that recorded
the verdict below. Generated/verified by `scripts/acceptance/migration_gate.py`.

## §9 acceptance criteria

### 1. Fault-injection harness green + numeric bar 0/0/0 over N=100

- Client: `/home/bs/jarvis-code/tests/faults/test_fault_injection.py` — 7 named
  fault classes (empty_content, midstream_cutoff, length_truncation,
  tool_use_no_result, degenerate_repetition, invalid_tool_args,
  forwarded_tool_500), each proven to yield a recovered answer OR a typed
  `BLOCKED`, always a terminal `TurnResult`, and zero orphan tool pairs —
  driven through the REAL `src/jc_agent_loop.py::AgentLoop`.
- Client: `/home/bs/jarvis-code/tests/faults/test_fault_fuzz.py` — N=100
  randomized combinations (1-4 chained faults per turn), wall-clock-bounded
  (5s per turn on a worker thread, so a true hang fails the test instead of
  blocking CI), asserting `silent_empty == 0`, `hangs == 0`, `orphan_400 == 0`.
- Server: `/media/projects/jarvis-v2/tests/faults/test_agent_step_faults.py`
  — the O1 envelope, A6 `finish_reason` plumbing in the streaming `done`
  event, `note_empty_completion` on empty completions, and a forwarded
  provider exception proven to return a **typed 502** (`upstream_error`)
  instead of an unhandled crash. Flag-OFF path proven inert.
- **Status: PASS.** Numeric bar recorded by `migration_gate.py`'s real run:
  `{"silent_empty": 0, "hangs": 0, "orphan_400": 0, "n": 100}`.

### 2. Real multi-step dev-task e2e passes

- `/home/bs/jarvis-code/tests/e2e_devtask/run_acceptance.py` (+ pytest wrapper
  `test_devtask_smoke.py`) drives the REAL `AgentLoop` through
  read → skill_gate → plan (todo_write) → dispatch subagent → edit → test →
  remember against a scratch git repo. Only the model is scripted; every tool
  call runs through the real production routing code
  (`jc_agent_loop.execute_one_tool` → `src/tools.py`) against real files/
  subprocess — `read_file` returns real content, `edit_file` changes a real
  file on disk, `bash` runs a real subprocess with a real captured exit code,
  the `task` tool runs a real nested subagent via `jc_dispatch.run_subagent`,
  and the forwarded `jarvis_memory_write` call is recorded at the network
  seam (no real network).
- **Status: PASS.** 12/12 checkpoints passed on the last run (no hang within a
  30s wall-clock budget, terminal envelope, no fabricated tool effect).

### 3. Not-blind lane: every step visible in Central with status/usage/duration/nerves/user_id

- `apps/api/jarvis_api/routes/agent_loop.py::_emit_agent_nerve` publishes
  `{status, provider, model, tokens_in, tokens_out, cost_usd, duration_ms,
  tool_calls, finish_reason, user_id, session_id}` to Den Intelligente
  Central, flag-gated on `jc_agent_observability`.
- Proven by Task 4's O1-envelope spies:
  `test_agent_step_envelope_has_o1_fields` (envelope fields present,
  `record_cost` called with the caller's `user_id`) and
  `test_empty_completion_emits_note_and_envelope` (`note_empty_completion`
  fires on an empty completion).
- **Caveat:** this criterion is proven at the SEAM (the nerve-emit and
  record_cost calls happen with the right shape/arguments) — it does not
  independently re-verify that a LIVE Central instance actually renders
  these events; that is Central's own responsibility and out of scope for
  this client/server-loop acceptance harness. `jc_agent_observability`
  remains default-OFF; this criterion is about the WIRING being correct and
  regression-guarded, not about flipping the flag.
- **Status: PASS** (wiring proven; live rendering not independently
  re-verified here — see caveat).

### 4. Security floor active: bash-confinement + untrusted-fencing + egress-gate + multi-user scoping

- `/home/bs/jarvis-code/tests/test_security_floor_client.py` — 6 named
  invariants: dangerous-command guard fires in every approval mode incl.
  bypass/plan; the `.env`→`curl`-exfil chain is blocked in every mode; bash
  confinement is ACTUALLY active (real bwrap write-outside-cwd block proven
  on the CI host, not just mocked) and fails OPEN (never blocks Jarvis) when
  the mechanism itself is unavailable; untrusted tool output is fenced AND
  the fencing call is proven wired into a real turn's `tool_fn` closure; a
  dispatched subagent's effective approval_mode is proven end-to-end through
  the real `jc_agent_loop._execute_task_tool` to never exceed the parent's
  ceiling; the web_fetch SSRF floor blocks loopback/RFC1918/metadata
  destinations with zero network calls made.
- `/media/projects/jarvis-v2/tests/multi_user/test_agent_step_scoping.py` —
  `/v1/agent/step` resolves identity/workspace/role from the AUTHENTICATED
  caller end-to-end (not just at the pure-helper unit level): workspace-
  scoped identity context reaches the model prompt, `full`-tier memory
  recall doesn't leak the owner's workspace tag to another caller,
  `record_cost` is tagged with the caller's `user_id`, and bypass/full-auto
  approval-timing modes are owner-only.
- **A real gap was found and fixed while writing this honestly:**
  `_SYSTEM_PROMPT`'s framing sentence unconditionally said "Bjørns terminal"/
  "HANS lokale maskine" regardless of caller, even with `jc_agent_user_scoping`
  ON and a correctly-resolved non-default workspace — the per-workspace
  identity/memory DATA was scoped correctly, but the top-level framing text
  wasn't. Fixed with `_SYSTEM_PROMPT_GENERIC` + `_system_prompt_intro(name)`,
  used only when the flag is ON and the resolved workspace isn't `default` —
  byte-identical `_SYSTEM_PROMPT` for the owner and for the flag-off baseline.
- **Status: PASS** (after the fix above).

## §8 migration preconditions

- **Substrate is UI-free:** `src/jc_agent_loop.py::AgentLoop` exists as a
  pure, dependency-injected class (`step_fn`/`tool_fn` callables in,
  `TurnResult` out) — driven headlessly by every test in this phase (no
  `prompt_toolkit`, no `core.*` import; `test_module_is_ui_free` in
  `tests/test_jc_agent_loop.py` asserts this statically).
- **Per-user scoped:** closed by criterion 4 above
  (`tests/multi_user/test_agent_step_scoping.py`) — the §8 blocker
  (identity/memory/quota leak) is regression-guarded.
- **Prove-then-migrate note:** jarvis-desk's code mode should WIRE this
  substrate + its own channels in, not rebuild it — `AgentLoop` +
  `execute_one_tool` + the server `/v1/agent/step` envelope are the
  contract surface to consume, not a reference to reimplement.

## Verdict

Run via `scripts/acceptance/migration_gate.py`:

```
migration_gate: running acceptance suites (client=jarvis-code, server=jarvis-v2)...
  [PASS] client fault-injection — 7 named fault classes
  [PASS] client fault-fuzz — N=100 numeric bar
  [PASS] server fault-injection — O1 envelope, A6, A8
  [PASS] multi-user scoping on /v1/agent/step
  [PASS] security floor (client) — 6 named §9.4 invariants
  [PASS] e2e multi-step dev-task (read→skill_gate→plan→dispatch→edit→test→remember)

GO: True
numeric_bar: {'silent_empty': 0, 'hangs': 0, 'orphan_400': 0, 'n': 100}
```

**GO.** All four §9 criteria pass. The jarvis-code Tier 0/1 substrate is
UI-free, per-user scoped, security-floored, and stable under fault injection
(0/0/0 over N=100) and a real multi-step dev-task e2e. jarvis-desk code mode
may migrate onto this substrate.

Recorded 2026-07-14 by the Fase 6 acceptance-harness implementation
(this document + `scripts/acceptance/migration_gate.py` + the test files
named above). Re-run the gate script before actually cutting the migration
over — this verdict is a snapshot, not a standing guarantee; regressions are
caught by the committed regression tests above, but the gate should be
re-run as part of the migration PR itself.
