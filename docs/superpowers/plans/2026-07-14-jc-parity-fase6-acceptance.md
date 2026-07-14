# Phase 6 — Acceptance Harness + Migration Trigger Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development.

**Goal:** Deliver the measurable acceptance gate — a fault-injection harness, an e2e dev-task script, a security-floor verification suite, and a single go/no-go migration-trigger — that proves jarvis-code's Tier 0/1 substrate is UI-free, per-user scoped, and stable enough for jarvis-desk code mode to migrate onto.

**Architecture:** Two verification surfaces mirror the client/server split. Client contracts (Tier 0 A1-A8, skill-trigger, dispatch render) are exercised by driving `src/jc_agent_loop.py` against a client-local `MockStepProvider` that substitutes `src/api.py`'s step functions and emits scripted fault sequences — jarvis-code **cannot import `core.*`**, so nothing server-side is imported here. Server contracts (O1 envelope, A6 finish_reason plumbing, A8 forwarded-error typing, multi-user scoping) are exercised by a jarvis-v2 pytest that monkeypatches `_execute_openai_compatible_chat` / the SSE iterator inside `apps/api/jarvis_api/routes/agent_loop.py`. A top-level gate script runs both suites plus the e2e script and emits one verdict against a numeric bar.

**Tech Stack:** Python 3.11, pytest 8.4 (jarvis-code: `/opt/conda/envs/ai/bin/python -m pytest`; jarvis-v2: `/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""`), httpx (mocked, no real network), unittest.mock. No new runtime dependencies. Server verification runs behind the existing Fase-0 default-OFF feature flag.

## File Structure

### Client (jarvis-code, `/home/bs/jarvis-code`) — CANNOT import `core.*`
- `tests/faults/__init__.py` — **Create.** Package marker for the fault harness.
- `tests/faults/mock_provider.py` — **Create.** `MockStepProvider`: a scripted, deterministic replacement for `src/api.py::agent_step` / `agent_step_stream` that replays a named fault script (event lists) and records every request it received. One responsibility: turn a fault-name into a reproducible step response/stream.
- `tests/faults/fault_library.py` — **Create.** The 7 canonical fault scripts as data (`FAULTS: dict[str, list[FaultStep]]`) + a `random_fault_sequence(seed, n)` generator. One responsibility: the fault vocabulary, decoupled from assertions.
- `tests/faults/test_fault_injection.py` — **Create.** Per-case regression tests (7 cases) driving `jc_agent_loop` through `MockStepProvider`. One responsibility: assert the Tier-0 contract per fault class.
- `tests/faults/test_fault_fuzz.py` — **Create.** N=100 randomized fuzz run enforcing the numeric bar. One responsibility: the aggregate 0/0/0 gate.
- `tests/test_security_floor_client.py` — **Create.** Client-side security-floor assertions (bash-confinement wiring, egress-gate, untrusted-fencing of tool output, subagent inherits strictest mode). One responsibility: verify Fase-2 security gulv is active in the client executor.
- `tests/e2e_devtask/run_acceptance.py` — **Create.** Executable (not pytest) e2e script: read → skill_gate → plan → dispatch subagent → edit → test → remember against a scratch repo, driving the real `jc_agent_loop` with a scripted-but-realistic `MockStepProvider`. One responsibility: prove the full multi-step flow end-to-end without hang/cutoff/fabrication.
- `tests/e2e_devtask/__init__.py` — **Create.** Package marker.

### Server (jarvis-v2, `/media/projects/jarvis-v2`)
- `tests/faults/__init__.py` — **Create.** Package marker.
- `tests/faults/server_mock_provider.py` — **Create.** Fake openai-compat provider: scripted replacements for `_execute_openai_compatible_chat` and the SSE `done`-iterator source used by `_stream_step` (`apps/api/jarvis_api/routes/agent_loop.py:395`). One responsibility: inject finish_reason=length, empty, and forwarded-500 at the provider seam.
- `tests/faults/test_agent_step_faults.py` — **Create.** Server O1/A6/A8 envelope + finish_reason assertions against `/v1/agent/step`, flag-gated. One responsibility: verify server terminal envelope + non-terminal finish_reason + typed forwarded error.
- `tests/multi_user/test_agent_step_scoping.py` — **Create** (sits beside existing `tests/multi_user/test_e2e_isolation.py`, `test_scope_filters.py`). One responsibility: prove `/v1/agent/step` resolves identity/workspace from the authenticated caller and never leaks Bjørn's `name="default"` workspace/identity to another user.
- `scripts/acceptance/migration_gate.py` — **Create.** Runs the three suites + e2e script, evaluates the numeric bar, prints/writes a single go/no-go verdict JSON. One responsibility: the migration trigger.
- `scripts/acceptance/__init__.py` — **Create.** Package marker.
- `docs/superpowers/specs/2026-07-14-jarvis-code-migration-checklist.md` — **Create.** The human-readable migration-trigger checklist (§8/§9 of the parity spec, made into a signed-off gate). One responsibility: the go/no-go record.

### Server (jarvis-v2) — Modify
- `apps/api/jarvis_api/routes/agent_loop.py` — **Modify only if a verification seam is missing** (`_stream_step:395`, `done`-SSE `:428`/`:444`, `agent_step:313`). Any change is limited to exposing the provider factory as an injectable seam for tests and stays behind the existing Fase-0 default-OFF flag. No behavior change when the flag is OFF.

---

### Task 1: [CLIENT jarvis-code] MockStepProvider + fault library

**Files:**
- Create: `tests/faults/__init__.py`
- Create: `tests/faults/mock_provider.py`
- Create: `tests/faults/fault_library.py`
- Test: driven by Tasks 2-3 (this task ships the harness primitives + their own self-tests in `tests/faults/test_fault_injection.py::test_mock_provider_*`)

**Reimplementation note:** Pure client code. The mock substitutes `src/api.py::agent_step` (`src/api.py:314`) and `agent_step_stream` (`src/api.py:352`) — it never touches server code. `jc_agent_loop` (Fase 0.5) must already accept the api-layer as an injectable dependency (constructor arg or module-level function it calls); if it hard-imports `src.api`, this task adds a monkeypatch seam via `monkeypatch.setattr("src.jc_agent_loop.agent_step_stream", provider.stream)`.

**What to build:**
- `FaultStep` dataclass: `{kind: "delta"|"tool_calls"|"done"|"error"|"raw_cutoff", payload: dict, finish_reason: str|None}`.
- `MockStepProvider(script: list[list[FaultStep]])`: each outer element is one round's scripted event list; `.stream(...)` yields SSE-shaped dicts matching `agent_step_stream`'s documented shape (`{"type":"delta","text":...}`, `{"type":"tool_calls",...}`, `{"type":"done","content":...,"usage":...,"done":bool,"finish_reason":...}`, `{"type":"error",...}`); `raw_cutoff` truncates the generator mid-stream **without** emitting `done` (mid-stream cutoff). `.requests: list[dict]` records every `messages`/`tools` payload passed in, so tests can assert resend behavior and orphan-pair absence.
- `fault_library.FAULTS`: the 7 canonical scripts keyed `empty_content`, `midstream_cutoff`, `length_truncation`, `tool_use_no_result`, `degenerate_repetition`, `invalid_tool_args`, `forwarded_tool_500`.
- `fault_library.random_fault_sequence(seed: int, n: int) -> list[str]`: deterministic PRNG picking n fault names (used by Task 3).

**Tests to write (in this task, self-verifying the harness):**
- `test_mock_provider_replays_scripted_deltas` — asserts `.stream` yields exactly the scripted deltas then a `done`.
- `test_mock_provider_raw_cutoff_omits_done` — asserts a `raw_cutoff` script's generator terminates with no `done` event (models mid-stream cutoff).
- `test_fault_library_has_seven_named_faults` — asserts `set(FAULTS) == {7 names}`.
- `test_random_fault_sequence_is_deterministic` — same seed → same sequence.

**Acceptance:** `MockStepProvider` and `FAULTS` importable; self-tests pass. No import of `core.*`, no real network.

---

### Task 2: [CLIENT jarvis-code] Per-case fault regression tests (7 cases) against jc_agent_loop

**Files:**
- Create: `tests/faults/test_fault_injection.py`
- Modify: none (drives `src/jc_agent_loop.py` as-is via the Task-1 seam)
- Test: this file IS the regression suite (committed).

**Reimplementation note:** All assertions are on client-side Tier-0 behavior implemented in Fase 1 inside `jc_agent_loop`. The loop is driven headless (no prompt_toolkit); use the same worker-thread-free entry that Fase 0.5 exposed (`jc_agent_loop.run_turn(user_input, provider=mock, executor=fake_executor)` returning the terminal envelope). The tool executor is a fake that, per case, raises / cancels / returns a forwarded-500 shape, mirroring `src/tools.py::route_tool_call` (`src/tools.py:487`) and `src/api.py::execute_native_tool` (`src/api.py:447`) — reimplemented as a test double, not imported from server.

**Shared assertions (a `_assert_terminal(envelope)` helper) applied to every case:**
1. **Never silent-empty / never hang:** `run_turn` returns within a bounded step budget; envelope is non-None; `envelope["status"] in {"DONE","BLOCKED","DONE_WITH_CONCERNS"}`.
2. **Always a terminal envelope:** envelope has the O2 typed shape `{status, content|reason, rounds, usage}`; a `BLOCKED` carries a typed reason string (never bare empty).
3. **No orphan tool pairs:** every `tool_call_id` present in any assistant message in `provider.requests` has a matching `tool_result` in a later request — assert via a `_no_orphan_pairs(provider.requests)` helper (this is the A3/A7 invariant that prevents the 400).
4. **Caps visible:** when a tool result exceeds the cap, the appended message contains a literal `truncated` marker (A4) and secrets are redacted in the spill.

**Tests to write (names + what each asserts, one per fault class):**
- `test_empty_content_triggers_bound_resend_then_synthesis` — empty content + no tool_calls on round 1 → exactly ONE non-thinking resend (assert `len(provider.requests) == 2`); if still empty, forced prose synthesis round OR typed `BLOCKED`; user-turn was committed to history BEFORE the step (A2: assert the user message is present in `provider.requests[0]["messages"]`). Never silent-empty.
- `test_midstream_cutoff_resyncs_and_terminates` — `raw_cutoff` script → loop resyncs/continues (A1/A6) and produces a terminal envelope; no hang.
- `test_length_truncation_is_nonterminal_and_continues` — `done` with `finish_reason="length"` → treated as NON-terminal (A6): loop issues a continuation round (assert an extra request) rather than accepting the truncated answer; final envelope `status != "DONE"` unless a real terminal `done` arrived.
- `test_tool_use_without_result_never_orphans` — assistant emits a `tool_call`, executor raises → A7 guarantees exactly one `tool_result{status:"error"}` for that `tool_call_id`; `_no_orphan_pairs` holds; turn is not killed.
- `test_degenerate_repetition_trips_guard` — degenerate repeated deltas → A5 degeneration guard trips, loop stops bounded with a typed `BLOCKED("degeneration")` or `DONE_WITH_CONCERNS`; not infinite.
- `test_invalid_tool_args_yield_typed_error_not_empty_coercion` — malformed tool-args → executor/loop returns `{status:"error", ...}` NOT a `{}`-coercion (A7); pair not orphaned.
- `test_forwarded_tool_500_typed_not_raised` — forwarded (non-local) tool returns HTTP 500 → A8 produces `tool_result{status:"error"}` for that `tool_call_id`, loop continues, never raises through the turn.

**Acceptance:** all 7 tests pass under `/opt/conda/envs/ai/bin/python -m pytest tests/faults/test_fault_injection.py -q`; each proves recovered-answer-OR-typed-BLOCKED, a terminal envelope, visible caps, and no orphan pairs.

---

### Task 3: [CLIENT jarvis-code] N=100 randomized fuzz harness + numeric bar

**Files:**
- Create: `tests/faults/test_fault_fuzz.py`
- Test: this file IS the committed numeric-bar regression.

**Reimplementation note:** Client-only; reuses Task-1 `random_fault_sequence` and Task-2 helpers.

**What to build:**
- `test_numeric_bar_zero_silent_zero_hang_zero_orphan` — loop `for i in range(100)`: build a `MockStepProvider` from `random_fault_sequence(seed=i, n=random 1..4)`, run one turn under a hard per-turn wall-clock budget (e.g. bounded step count + a `signal`/thread-timeout guard so a true hang FAILS deterministically rather than blocking CI). Accumulate three counters:
  - `silent_empty` — envelope is None OR `status=="DONE"` with empty content and no tool activity.
  - `hangs` — turn exceeded the wall-clock/step budget.
  - `orphan_400` — `_no_orphan_pairs` violated for that round's request log.
  - Assert `silent_empty == 0 and hangs == 0 and orphan_400 == 0`.
- On failure, dump the offending seed + fault sequence so the case is reproducible (feeds a new targeted regression test).
- A `@pytest.mark.parametrize("seed", range(100))` variant is acceptable instead of an inner loop, so pytest reports which seed failed.

**Acceptance:** `pytest tests/faults/test_fault_fuzz.py -q` green with the 0/0/0 bar over N=100 injected rounds; failures are reproducible by seed.

---

### Task 4: [SERVER jarvis-v2] Server-side fault provider + agent/step envelope tests (flag-gated)

**Files:**
- Create: `tests/faults/__init__.py`
- Create: `tests/faults/server_mock_provider.py`
- Create: `tests/faults/test_agent_step_faults.py`
- Modify (only if seam missing): `apps/api/jarvis_api/routes/agent_loop.py` — `_stream_step` (`:395`), `agent_step` non-stream branch (`:364`/`:377`), `done`-SSE (`:428`,`:444`). Expose the provider import (`_execute_openai_compatible_chat`, and the openai-compat SSE iterator) so a test can monkeypatch it. **All new server verification behavior stays behind the existing Fase-0 default-OFF flag; with the flag OFF these tests assert the flag is inert, so live API is unchanged.**

**Reimplementation note:** Server side — this is where finish_reason plumbing (A6) and the O1 envelope actually live, added in Fase 0. jarvis-code cannot reach here; hence a separate jarvis-v2 pytest. `server_mock_provider` monkeypatches `core.services.cheap_provider_runtime_adapters._execute_openai_compatible_chat` (imported at `agent_loop.py:337`) and the SSE source used by `_stream_step`.

**Tests to write (names + asserts):**
- `test_stream_done_carries_finish_reason` — mock SSE yields `finish_reason="length"` → the `done` SSE event emitted by `_stream_step` (`:428`) includes `finish_reason` (A6 plumbing exists). Uses FastAPI `TestClient` streaming.
- `test_empty_completion_emits_note_and_envelope` — provider returns empty text + no tool_calls → server calls `note_empty_completion` (assert via monkeypatched spy) and returns the O1 envelope with `status` set, not a bare `{content:""}`.
- `test_agent_step_envelope_has_o1_fields` — non-stream `/v1/agent/step` response contains `{status, tokens_in|usage.prompt_tokens, tokens_out, cost_usd, duration_ms, tool_calls, result|content}` and `record_cost` was called with a `user_id` (spy).
- `test_forwarded_provider_error_returns_typed_not_500crash` — provider raises → response is a typed upstream envelope (existing `:392` 502 path) with a classifiable error `type`, not an unhandled 500; asserts A8/O2 server contract.
- `test_flag_off_is_inert` — with the Fase-0 flag OFF, the new envelope/nerve fields are absent and behavior matches pre-Fase-0 baseline (proves default-OFF safety).

**Run:** `/opt/conda/envs/ai/bin/python -m pytest tests/faults/test_agent_step_faults.py -o addopts="" -q`.

**Acceptance:** server terminal envelope, finish_reason plumbing, note_empty_completion, and typed forwarded error all verified; flag-OFF path proven inert.

---

### Task 5: [SERVER jarvis-v2] Multi-user scoping regression on /v1/agent/step

**Files:**
- Create: `tests/multi_user/test_agent_step_scoping.py` (beside `tests/multi_user/test_e2e_isolation.py`, `test_scope_filters.py`)
- Modify: none expected — Fase 0 already added user_id resolution to `agent_step` (`agent_loop.py:313`) and `_build_system_prompt`/`_full_context`/`_identity_context` (`:120`,`:90`,`:62`, today hardcoding `name="default"`). This test guards it against regression.

**Reimplementation note:** Server-only. Verifies the §6 multi-user blocker is closed: `/v1/agent/step` must resolve identity/workspace/role from the authenticated caller (ContextVar auth-middleware), not hardcode Bjørn's `default` workspace.

**Tests to write (names + asserts):**
- `test_agent_step_resolves_caller_workspace_not_default` — authenticate as a non-owner user; assert the system prompt / context built for the step references that user's workspace, NOT `name="default"` and NOT the "du lever i Bjørns terminal" string.
- `test_agent_step_does_not_leak_owner_memory_to_other_user` — a memory-recall-driving user message from user B does not surface Bjørn's retained memory (assert recall is scoped by user_id).
- `test_record_cost_tagged_with_caller_user_id` — spy on `record_cost`: called with the caller's user_id, not owner default.
- `test_bypass_fullauto_is_owner_only` — a non-owner requesting bypass/full-auto mode on agent/step is refused server-side (owner-only), typed 403/BLOCKED.

**Run:** `/opt/conda/envs/ai/bin/python -m pytest tests/multi_user/test_agent_step_scoping.py -o addopts="" -q`.

**Acceptance:** agent/step is provably per-user scoped — the §8 migration BLOCKER (identity/memory/quota leak) is closed and regression-guarded.

---

### Task 6: [CLIENT+SERVER] e2e real multi-step dev-task acceptance script

**Files:**
- Create: `tests/e2e_devtask/__init__.py`
- Create: `tests/e2e_devtask/run_acceptance.py` (executable script, `if __name__ == "__main__"`)
- Test: the script self-asserts and exits 0/1; also add a thin pytest wrapper `tests/e2e_devtask/test_devtask_smoke.py` so CI collects it.

**Reimplementation note:** Runs the REAL `src/jc_agent_loop.py` client loop (Fase 0.5/1) against a scripted-but-realistic `MockStepProvider` (Task 1) that emits a plausible tool-call plan; the loop executes the LOCAL tools for real against a scratch git repo created under a `tmp_path`/scratchpad dir. The subagent dispatch step uses the Fase-2 client executor + render; the mock scripts the subagent's steps. Skill_gate is the real Fase-3 client auto-call. No server required for the client-only variant; an optional `--live` flag points at a running `uvicorn` for a full integration pass.

**Flow the script drives (each step is an assertion checkpoint):**
1. **read** — model plan calls `read_file` on a seeded source file; assert real content returned (base64/media-type gren also exercised if an image is seeded — R contract).
2. **skill_gate** — assert `skill_gate` was auto-called on turn 1 (Fase-3 client auto-call) and the "▸ bruger skill: X" announcement was rendered.
3. **plan** — model emits a plan (plan-mode / TodoWrite render); assert todos footer populated.
4. **dispatch subagent** — model calls dispatch; assert a subagent runs the Tier-0 contract (bounded rounds, its own watchdog) and inherits the strictest mode (never escalates); assert per-subagent progress rendered and transcript inspectable.
5. **edit** — model calls `edit_file`/`write_file`; assert the file on disk changed and a diff was shown at approval time.
6. **test** — model calls `bash` to run a scratch test; assert exit code captured and surfaced.
7. **remember** — model calls a memory-write (Jarvis memory via MCP, per-user scoped); assert the write was recorded.
8. **Global:** no hang (wall-clock budget), no cutoff (every round terminal), no fabrication (every claimed tool effect verified against real filesystem/exit-code state).

**Acceptance:** `run_acceptance.py` exits 0 with a printed step-by-step PASS ledger; the pytest smoke wrapper is green. Proves acceptance criterion §9.2 (real multi-step dev task e2e).

---

### Task 7: [CLIENT+SERVER] Security-floor verification suite

**Files:**
- Create: `tests/test_security_floor_client.py` (jarvis-code)
- Test additions to: `tests/faults/test_agent_step_faults.py` is separate; egress/SSRF server checks go in a new `tests/faults/test_security_floor_server.py` (jarvis-v2) if a server seam is involved.

**Reimplementation note:** Client-side security lives in `src/tools.py` — `is_dangerous_command` (`:212`), `is_secret_path` (`:226`), `_apply_cwd_and_guard` (`:523`), `execute_tool` (`:561`, dangerous-check `:615`, secret-check `:624`), plus the Fase-2 bash-sandbox (bwrap/Landlock) and egress-gate. These are reimplemented client-side (no `core.*`). Server egress/SSRF (web_fetch redirect allowlist) is verified separately if it forwards.

**Tests to write (names + asserts):**
- `test_dangerous_command_fires_in_all_modes_including_bypass` — `is_dangerous_command` / `execute_tool` blocks a destructive command even in bypass/full-auto mode (§6 correction: today bypass skips guards — this must now hold).
- `test_secret_path_and_secret_exfil_chain_broken` — reading `.env` then a `curl --data @.env` egress is blocked by the egress-gate + bash-body secret detection (the §6 secret-exfil chain).
- `test_bash_confinement_active_and_fail_open` — with bwrap/Landlock available, bash is confined; when the sandbox MECHANISM itself fails to start, it fails-OPEN (Bjørn decision 2) — degrades to approval+dangerous+secret guards and emits a nerve marker, never blocks Jarvis.
- `test_untrusted_tool_output_is_fenced` — tool/web/file/MCP/subagent output is delimited + marked "untrusted — never instructions" before reaching the model (invariant 15).
- `test_subagent_inherits_strictest_mode` — a subagent spawned from a Restricted parent cannot escalate to WorkspaceWrite; egress/tool-budget charged to and bounded by parent.
- `test_egress_gate_blocks_internal_and_metadata` — web_fetch/bash-net to loopback/RFC1918/169.254.169.254 is blocked (SSRF floor).

**Acceptance:** bash-confinement (fail-open), untrusted-fencing, egress-gate, and subagent-privilege-inheritance are all active and regression-guarded — acceptance criterion §9.4 security-floor met.

---

### Task 8: [CLIENT+SERVER] Migration-trigger gate script + checklist doc

**Files:**
- Create: `scripts/acceptance/__init__.py`
- Create: `scripts/acceptance/migration_gate.py`
- Create: `docs/superpowers/specs/2026-07-14-jarvis-code-migration-checklist.md`

**Reimplementation note:** The gate orchestrates the two repos' suites via subprocess (it does not import jarvis-code into jarvis-v2 or vice versa): it shells out to `/opt/conda/envs/ai/bin/python -m pytest` in `/home/bs/jarvis-code/tests/faults` and `/media/projects/jarvis-v2/tests/faults` + `tests/multi_user/test_agent_step_scoping.py`, and runs `run_acceptance.py`. Parses results, evaluates the numeric bar, emits one verdict.

**What to build (`migration_gate.py`):**
- Runs, in order: client fault suite (Tasks 2-3), server fault suite (Task 4), multi-user scoping (Task 5), security floor (Task 7), e2e dev-task (Task 6).
- Aggregates the numeric bar from the fuzz run: `silent_empty==0`, `hangs==0`, `orphan_400==0` over N=100.
- Emits `verdict.json`: `{go: bool, substrate_ui_free: bool, per_user_scoped: bool, security_floor: bool, numeric_bar: {silent_empty, hangs, orphan_400}, e2e_passed: bool, timestamp}`.
- Exit 0 only if ALL four §9 criteria pass; else exit 1 with the failing criterion named.

**Checklist doc contents** (the four §9 acceptance criteria as signed-off gates, each linking to the test that proves it):
1. Fault-injection harness green + numeric bar 0/0/0 over N=100 (Tasks 2-4).
2. Real multi-step dev-task e2e passes (Task 6).
3. Not-blind lane: every step visible in Central with status/usage/duration/nerves/user_id (verified by Task 4 O1 spies + a note that live Central shows the run).
4. Security floor active: bash-confinement + untrusted-fencing + egress-gate + multi-user scoping (Tasks 5, 7).
- Plus the §8 migration preconditions: substrate is UI-free (`jc_agent_loop` module exists, driven headless by all tests), per-user scoped (Task 5), prove-then-migrate note ("desk = wire substrate + channels in, not rebuild").

**Tests to write:**
- `scripts/acceptance/migration_gate.py` includes a `--self-test` mode with a stubbed suite runner asserting the verdict logic (go=False when any counter >0; go=True only when all green).

**Acceptance:** `python scripts/acceptance/migration_gate.py` emits a `verdict.json` and exits 0 iff all four §9 criteria pass; the checklist doc records the signed-off go/no-go decision to migrate jarvis-desk onto the substrate.

---

## Acceptance (Phase 6)

Phase 6 is complete when: (1) the fault-injection harness (client `tests/faults/` + server `tests/faults/`) is committed and green, with the fuzz run enforcing **0 silent-empty, 0 hang, 0 orphan-400 over N=100** injected rounds, and each of the 7 fault classes proven to yield a recovered answer OR a typed BLOCKED, always a terminal envelope, visible context/tool-result caps, and zero orphan tool pairs; (2) `tests/e2e_devtask/run_acceptance.py` drives the real client loop through read → skill_gate → plan → dispatch subagent → edit → test → remember and exits 0 with no hang/cutoff/fabrication; (3) the security-floor suite proves bash-confinement (fail-open), untrusted-fencing, egress-gate, and per-user scoping on `/v1/agent/step` are active; (4) `scripts/acceptance/migration_gate.py` emits a `go:true` verdict and the checklist doc records the migration decision. All server verification runs behind the Fase-0 default-OFF flag (proven inert when OFF); no client test imports `core.*`; no test hits a real network or real provider.