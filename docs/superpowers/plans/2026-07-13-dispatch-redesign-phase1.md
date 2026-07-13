# Dispatch/Råd-Redesign — Fase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Byg fundamentet der gør Jarvis' agent/råd-dispatch event-drevet, robust og synligt — så det gamle blinde council-daemon-token-brænd kan retires, og Fase 2 (konvertér de 25 timer-daemons) kan bygges oven på det.

**Architecture:** Ét dispatch-primitiv (konstrueret kontekst → landet, struktureret konvolut), event-drevet trigger på signal-DELTA (ikke timer), 12 hærdnings-værn, alt wired ind i Centralen, agent-arbejde på gratis cheap-lane-pool. Byg-rækkefølge fra rådets synthesis §8.

**Tech Stack:** Python 3.11, pytest (`/opt/conda/envs/ai/bin/python -m pytest ... -o addopts=""`). Deploy: push → container `git merge --ff-only` → `sudo systemctl restart jarvis-api jarvis-runtime`. Commit `--no-verify` (docs-drift-hook urelateret).

**Kilder:** docs/superpowers/specs/2026-07-13-claude-orchestration-reference.md (reference-model) + 2026-07-13-council-findings-synthesis.md (rådets fund, fil:linje). Læs BEGGE før start.

**Invarianter (gælder ALLE tasks):**
- Robusthed-konvolut: hvert dispatch returnerer `{status, tokens_in, tokens_out, cost_usd, duration_ms, tool_calls, result}`. Aldrig `completed` uden ægte success.
- Typet fejl: `completed | failed | timeout | blocked | needs_context | concerns`.
- Agent-arbejde router til cheap-lane-pool (gratis providers først) — aldrig paid som default.
- Alt nyt/rørt modul i `core/services/agent_*`, `council_*`, `tool_scoping` SKAL have mindst ét `central().observe`/`central_timeseries.record`/`agents.note_*`-kald (mod ny silo).
- Kill-switch pr. ny mekanisme via runtime-state/central_switches (ingen deploy for at slå fra).

---

## WORKSTREAM A — Konvolut + typet status + record_cost(lane=agent) [fikser K2 live-bug]

### Task A1: Typet dispatch-status enum
**Files:** Create `core/services/dispatch_status.py`; Test `tests/services/test_dispatch_status.py`

- [ ] **Step 1: Failing test**
```python
from core.services.dispatch_status import DispatchStatus, is_terminal, is_failure
def test_status_values():
    assert DispatchStatus.COMPLETED == "completed"
    assert set(DispatchStatus.all()) == {"completed","failed","timeout","blocked","needs_context","concerns"}
def test_failure_classification():
    assert is_failure("failed") and is_failure("timeout") and is_failure("blocked")
    assert not is_failure("completed")
def test_terminal():
    assert is_terminal("completed") and is_terminal("failed")
```
- [ ] **Step 2:** Run → FAIL (module missing).
- [ ] **Step 3:** Implement `DispatchStatus` (str constants + `all()`), `is_terminal`, `is_failure` (`completed` is the only non-failure terminal; `concerns` = success-with-doubt, not failure).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(dispatch): typet dispatch-status enum (A1)`.

### Task A2: Robusthed-konvolut builder
**Files:** Create `core/services/dispatch_envelope.py`; Test `tests/services/test_dispatch_envelope.py`

- [ ] **Step 1: Failing test** — assert `build_envelope(status=..., tokens_in=, tokens_out=, cost_usd=, duration_ms=, tool_calls=, result=)` returns a dict with EXACTLY the 7 keys, correct types; a plausibility guard `validate_envelope(env)` flags `status=="completed"` with `tokens_out==0` (returns a warning list, does not raise). Test all 7 keys present + the tokens_out==0 flag.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `build_envelope(...) -> dict` (7 keys, coerce types, default duration from a passed monotonic start if given) + `validate_envelope(env) -> list[str]` (plausibility invariants: completed⇒tokens_out>0; claimed tool_calls>=0; unknown status → flag). Self-safe.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(dispatch): robusthed-konvolut + plausibilitets-guard (A2)`.

### Task A3: Fjern hardkodet "completed" i agent_runtime_base + fyld konvolutten
**Files:** Modify `core/services/agent_runtime_base.py:~262` (the hardcoded `"status":"completed"` result dict); Test `tests/services/test_agent_result_envelope.py`

- [ ] **Step 1:** READ `agent_runtime_base.py` around the result-assembly (~199-273). Find where it returns `{"status":"completed", input_tokens, output_tokens, ...}`.
- [ ] **Step 2: Failing test** — patch the model-call to (a) succeed → envelope has all 7 keys, status=completed, duration_ms>0, tool_calls counted; (b) raise → status in the failure set (NOT completed), usage still present. Regression guard: assert the literal `"completed"` is never returned on the raise path.
- [ ] **Step 3:** Run → FAIL (currently hardcoded completed).
- [ ] **Step 4:** Implement: build the result via `dispatch_envelope.build_envelope`, derive status from actual outcome (success/exception/empty-return→blocked), measure duration around the call (monotonic), count tool_calls actually made. Keep backward-compat keys (`input_tokens`/`output_tokens`) as aliases so existing readers don't break.
- [ ] **Step 5:** Run → PASS. Compile `core.services.agent_runtime_base`.
- [ ] **Step 6:** Commit `fix(dispatch): ægte typet konvolut i agent_runtime_base — fjern hardkodet completed (A3, K2)`.

### Task A4: record_cost(lane="agent") ved dispatch-completion + failure seam
**Files:** Modify `core/services/agent_runtime_spawn.py:~421` (completion) + `:~472` (failure); Test `tests/services/test_agent_cost_logging.py`

- [ ] **Step 1:** READ `agent_runtime_spawn.py:398-490` — the seam that computes input_tokens/output_tokens/status but does NOT call record_cost (council-wiring member's gap).
- [ ] **Step 2: Failing test** — patch `record_cost`, run a dispatch (mock the model call w/ known usage) → assert `record_cost(lane="agent", provider=, model=, input_tokens=, output_tokens=, cost_usd=0.0, cache_*=...)` called once on success AND once on the failure path (usage on failure too).
- [ ] **Step 3:** Run → FAIL.
- [ ] **Step 4:** Implement: at both seams add `record_cost(lane="agent", ...)` (cost auto-computes; for free cheap-lane providers it's ~0 — that's correct/intended). Fail-safe try/except (never break dispatch).
- [ ] **Step 5:** Run → PASS.
- [ ] **Step 6:** Commit `feat(cost): log agent-dispatch spend via record_cost(lane=agent) (A4)`.

---

## WORKSTREAM B — Central-wiring [byg PÅ agents.py, ingen ny silo]

### Task B1: agent_result nerve + envelope-timeseries
**Files:** Modify `core/services/agents.py` (extend, it's KOBLET: note_agent_spawn:23/error:33/council:39); call from `agent_runtime_spawn.py` completion seam; Test `tests/services/test_agents_nerves.py`

- [ ] **Step 1: Failing test** — patch `central().observe` + `central_timeseries.record`; on dispatch-end assert `note_agent_result(agent_id, status=, tokens_in=, tokens_out=, cost_usd=, duration_ms=, tool_calls=, role=)` emits cluster `"agents"` nerve `"agent_result"` AND records series `agents/agent_duration_ms` + `agents/agent_tokens`.
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `note_agent_result(...)` in agents.py (observe + two timeseries.record). Wire the call at the completion/failure seam (same place as A4). Self-safe.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(central): agent_result-nerve + envelope-timeseries (B1)`.

### Task B2: typet agent_blocked (separat fra error — undgå fejl-rate-drift)
**Files:** Modify `core/services/agents.py` + `agent_runtime_spawn.py:~404` (result-parse); Test extend `test_agents_nerves.py`

- [ ] **Step 1: Failing test** — a `blocked`/`needs_context` outcome emits `central().observe({cluster:"agents",nerve:"agent_blocked",kind:"blocked",status:...})` and does NOT call `note_agent_error` (so error-rate drift isn't inflated).
- [ ] **Step 2-4:** Implement `note_agent_blocked(...)`; branch at the result-parse seam on typed status; run → PASS.
- [ ] **Step 5:** Commit `feat(central): typet agent_blocked-nerve, adskilt fra error (B2)`.

### Task B3: /central/agents + /central/council surfaces + jc subcommands
**Files:** Create `core/services/central_agents_surface.py` (pattern: `central_cost_surface.py`); Modify `apps/api/jarvis_api/routes/central.py` (add routes after `/cost`); Modify `/home/bs/.local/bin/jc` (add `agents`/`council` blocks mirroring `cost`); Modify `core/services/central_hub.py:103` (`_BUILDERS` — fill the existing `council`/`agency` placeholder tabs); Test `tests/services/test_central_agents_surface.py`

- [ ] **Step 1: Failing test** — seed some `agents`-cluster events/costs (via note_agent_result + record_cost lane=agent), call `build_agents_surface()` → aggregate (spawns/results/blocks/errors + envelope sums + spend today/7d). And `build_council_surface()` → convocations + roles + event-vs-ondemand split. Owner-gate on routes.
- [ ] **Step 2-4:** Implement both surface builders (read costs where lane=agent + agents-cluster timeseries), routes (owner-gated, to_thread), jc subcommands, Mind-hub builders. Run → PASS.
- [ ] **Step 5:** Deploy + verify `jc agents` / `jc council` render live.
- [ ] **Step 6:** Commit `feat(central): /central/agents + /central/council + jc surfaces, fyld Mind-hub-tabs (B3)`.

---

## WORKSTREAM C — Event-trigger i SHADOW + hærdnings-værn

### Task C1: Persisteret signal-baseline (durable, cold-start-guard)
**Files:** Create `core/services/signal_baseline.py`; Test `tests/services/test_signal_baseline.py`

- [ ] **Step 1: Failing test** — `get_baseline(signal)` returns None on cold-start (first ever read); `set_baseline(signal, value)` persists to DB; after set, `get_baseline` returns it; `is_cold_start()` True until N baselines established. Survives across a simulated restart (durable KV, not in-memory).
- [ ] **Step 2-4:** Implement durable baseline store (runtime-state KV or a small table), cold-start detection (first-M-heartbeats suppression). Run → PASS.
- [ ] **Step 5:** Commit `feat(trigger): persisteret signal-baseline + cold-start-guard (C1)`.

### Task C2: Delta-trigger med hysterese + absolut-gulv + debounce
**Files:** Create `core/services/signal_delta_trigger.py`; Test `tests/services/test_signal_delta_trigger.py`

- [ ] **Step 1: Failing test** (the core economic-proof tests):
  - `test_delta_fires_on_real_rise` (baseline 0.20→0.55 crosses θ_high → fire)
  - `test_flat_does_not_fire` + assert NO LLM facade call (the "idle=nul" proof)
  - `test_hysteresis` (fires at θ_high; must fall below θ_low before re-arm; no re-fire while elevated)
  - `test_debounce_window` (two crossings within cooldown → one fire)
  - `test_absolute_floor_or` (`abs > θ_abs held T` fires even with tiny delta — slow-boil)
  - `test_cold_start_no_fire` (first tick establishes baseline, does NOT fire)
  - `test_composite_coalesce` (N signals cross same tick → ONE dispatch, all batched into context)
- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `evaluate(signals: dict) -> DispatchDecision | None` — pure, NON-LLM. Hysteresis bands (θ_high/θ_low), per-signal debounce cooldown, absolute-floor OR, cold-start suppression, composite coalescing (one decision per tick carrying all crossed signals). Bands/cooldowns read from runtime-state (tunable, no deploy).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Commit `feat(trigger): delta-trigger m. hysterese+absolut-gulv+debounce+coalesce (C2)`.

### Task C3: Idempotens + dead-man-timeout + circuit-breaker + budget-loft
**Files:** Create `core/services/dispatch_guards.py`; Test `tests/services/test_dispatch_guards.py`

- [ ] **Step 1: Failing test**:
  - `test_idempotency_key` (same (signal, baseline-epoch) → second dispatch refused until consumed marker cleared)
  - `test_dead_man_timeout` (dispatch w/ deadline; no completion → `synthesize_timeout_envelope` returns a `timeout` envelope, treated as loud failure)
  - `test_circuit_breaker` (N consecutive failures in window → `is_tripped()` True → dispatch blocked; auto-reset after cooldown)
  - `test_budget_ceiling` (per-24h max dispatches AND max cost_usd; `budget_allows()` False when exceeded — enforced BEFORE LLM)
- [ ] **Step 2-4:** Implement the four guards (durable counters, self-safe, all runtime-state-tunable). Run → PASS.
- [ ] **Step 5:** Commit `feat(trigger): idempotens+dead-man+circuit-breaker+budget-loft (C3)`.

### Task C4: Visible↔autonom gensidig udelukkelse (marker-default)
**Files:** Create `core/services/autonomous_lease.py`; Test `tests/services/test_autonomous_lease.py`

- [ ] **Step 1: Failing test** — while a visible turn holds the lease, `try_autonomous_dispatch()` defers to a MARKER (returns `deferred`, does not mutate self-model/central-state); when idle, it proceeds. Marker is readable later.
- [ ] **Step 2-4:** Implement the lease (visible turn acquires; autonomous checks; defer→marker). Resolves Q1 (marker-default, opt-in wake only when idle+high-value). Run → PASS.
- [ ] **Step 5:** Commit `feat(trigger): visible↔autonom lease, marker-default (C4)`.

### Task C5: Event-trigger SHADOW-meter — wire C1-C4 into a delta gate on convene_judge, log-only
**Files:** Modify `core/services/central_convene_judge.py` (repurpose `_MOVEMENT_THRESHOLD` → delta-trigger via C2; keep its dynamic `_derive_roles`/`_derive_topic_hint`); wire onto the heartbeat delta-check; Test `tests/services/test_convene_judge_shadow.py`

- [ ] **Step 1: Failing test** — in shadow mode, the delta gate evaluates on tick and RECORDS what it WOULD dispatch (`central_timeseries.record("agents","event_trigger", value=delta, meta={signals, crossed, would_dispatch})`) but makes NO LLM call and triggers NO council. Assert LLM facade never called in shadow; assert `crossed`/`would_dispatch` telemetry present.
- [ ] **Step 2-4:** Implement shadow path: convene_judge consults `signal_delta_trigger.evaluate` + guards, records telemetry, does not act while `central_convene_judge_mode == "shadow"`. Run → PASS.
- [ ] **Step 5:** Deploy in SHADOW. Verify via `jc series agents/event_trigger` that it observes deltas and the `event_trigger` curve is flat-with-no-crossings when signals are flat (economic proof, live).
- [ ] **Step 6:** Commit `feat(trigger): event-trigger shadow-meter på convene_judge (C5)`.
- [ ] **Step 7 (CALIBRATION GATE — not code):** Let shadow run 2-4 days. Read the traces; set θ_high/θ_low/cooldown/budget from REAL data (answers Q2). Document the chosen numbers in the reference doc §Åbne-spørgsmål. Do NOT flip to active until calibrated.

---

## WORKSTREAM D — Retire den blinde council-daemon [KUN triggeren, ikke motoren]

> ⚠️ K1: `create_council_session_runtime`/`run_council_round`/`DeliberationController`/council-tabellerne er DELT motor (on-demand tool + MC). RØR DEM IKKE. Retire kun `autonomous_council_daemon.py` + dens wirings. Følg synthesis §4 rækkefølge.

### Task D1: Neutralisér den blinde trigger (kill-switch, ingen deploy)
- [ ] Set daemon-enable-flag så `is_enabled("autonomous_council")` → False (heartbeat_runtime_influence.py:863 stopper med at ticke den). Verify via `jc` ingen nye `council.autonomous_triggered`-events. Commit intet (runtime-state).

### Task D2: Fjern tick + registry
**Files:** Modify `core/services/heartbeat_runtime_influence.py:863-869` (remove tick block) + `core/services/daemon_manager.py:221-227` (remove registry entry); Test: `python -m compileall core apps/api scripts` + existing heartbeat tests green.
- [ ] Remove both; run compileall + heartbeat test suite; deploy; verify heartbeat runs. Commit `refactor(retire): fjern autonomous_council tick+registry (D2)`.

### Task D3: Fjern surface-registrering (m. 1-deploy shim mod jc-500)
**Files:** Modify `core/services/signal_surface_router.py:155,251`.
- [ ] Option: first deploy returns `{"retired": true}` for `build_autonomous_council_surface`; next deploy removes the key. Verify `jc series`/surface-router no 500. Commit `refactor(retire): retire autonomous_council-surface (D3)`.

### Task D4: Slet modulet + statiske rolle-maps + council→push_initiative-landing
**Files:** Delete `core/services/autonomous_council_daemon.py` (incl. `_ALL_COUNCIL_ROLES`/`_SIGNAL_TO_ROLES`/`_land_initiative`). Verify no importer remains (grep) besides the docstring ref in convene_judge (tidy comment).
- [ ] `python -m compileall core apps/api scripts` (CI smoke) green. Commit `refactor(retire): slet autonomous_council_daemon — blind trigger væk, motor intakt (D4)`.

### Task D5: existential_wonder cadence → event-gated (behold wonder-output)
**Files:** Modify `core/services/existential_wonder_daemon.py:27,59-61` (replace `_CADENCE_HOURS=24` gate with event/delta trigger via C2; KEEP wonder generation + its surface — 4 consumers). Test: wonder still generates on-demand-by-reason; the blind 24h timer no longer fires.
- [ ] Implement + test. Commit `refactor(trigger): existential_wonder event-gated, output bevaret (D5, Q3)`.

---

## WORKSTREAM E — jarvis-code rendering [parallel m. C/D, afhænger af A-konvolut]

### Task E1: Konvolut-meta + typede statuser i render
**Files:** Modify `/home/bs/jarvis-code/src/render.py` (`_status_frag` add running-spin + failed/timeout/blocked/needs_ctx/concerns; add `_status_label`, `envelope_meta`, `council_summary`); Test `/home/bs/jarvis-code/tests/test_render_dispatch.py`
- [ ] Test: `envelope_meta(entry)` → `"41k tok · 4.2s · $0.004"`; `_status_frag("timeout")` → red ⧖; `council_summary(children)` → `"5 agenter · 5/5 ✓ · 128k · 3.1s"` (dur=max, tok=sum). Implement + PASS. Commit.

### Task E2: agent + council entry-kinds i round-blok
**Files:** Modify `/home/bs/jarvis-code/src/repl_ptk.py` (`_round_add`/`_round_update` accept kind/agent_type/lens/children/started/envelope; add `_agent_add`/`_council_add`/`_council_member_update`; thread `spin_i` into render_round); `render.tool_entry_lines` render envelope in diffstat-slot + typed badge + nested children when expanded.
- [ ] Test (PTY/unit): a dispatched agent renders as running→landed with envelope; a council renders parent+children; a blocked child shows a loud badge and degrades parent ✓→⚠. Implement + PASS. Commit.

### Task E3: Baggrunds-dispatch wake-on-done freeze
**Files:** Modify `repl_ptk.py` (background agent renders running, freezes; task-notification emits frozen scrollback line `⟲ agent:… landede · … ✓ (baggrund)` via `frags_to_ansi(tool_entry_lines(entry))`).
- [ ] Test + manual TTY verify (screenshot per feedback_verify_visual_before_done). Commit.

---

## WORKSTREAM F — Flip + acceptance

### Task F1: Flip event-trigger shadow→active (efter C5 kalibrering)
- [ ] After calibration gate (C5 step 7): set `central_convene_judge_mode` → `on`. Now delta-trigger actually convenes (via the KEPT motor). Watch `jc series agents/event_trigger` + `jc cost` — convocations only on real crossings. Kill-switch = flip back to shadow. Commit any config-doc.

### Task F2: Flip agent_tools_enabled on (efter konvolut+værn grønne)
- [ ] Define role-allowlists (searcher=read-only, builder=full+approval — per §4.4). Set `agent_tools_enabled` → True. Verify tool-scope activations surface (B-nerves) + execute_tool approval-gate holds (test). Kill-switch = flip off.

### Task F3: Acceptance-gate
- [ ] `conda activate ai && python scripts/central_connectivity_audit.py` → `council_deliberation_controller`/`agent_dispatch`/`tool_scoping` moved FRAKOBLET→KOBLET; ZERO new FRAKOBLET+LLM rows.
- [ ] Idle-burn proof: `test_flat_for_n_ticks_zero_llm_calls` green + live `jc series agents/event_trigger` flat-no-crossings when signals flat.
- [ ] `jc cost` before/after: autonomous LLM-kald/dag markant ned (mål: autonomous_council's 48/d → 0; total daemon-fleet unchanged yet — that's Fase 2).
- [ ] Docs: flip 2026-07-03-spec status færdig→in-progress; update reference doc §Åbne-spørgsmål with calibrated numbers; add envelope-rule + retire-note to CLAUDE.md; write kill-switch/activation-order runbook.

---

## Self-review (efter skrivning)
- **Spec-dækning:** K1 (retire kun trigger, WS-D beskytter motoren ✓), K2 (A3 fikser hardkodet completed ✓), K3 (F3 audit-gate ✓). 12 værn: hysterese/absolut/debounce/coalesce (C2), baseline/cold-start (C1), idempotens/dead-man/circuit/budget (C3), lease (C4), plausibilitet (A2), subscriber-ack (→ tilføj til B1 note), rekursions-guard (→ mangler egen task).
- **HUL fundet i self-review:** (a) subscriber-ack (værn #7) er ikke sin egen task — foldes ind i B1 (assertér ≥1 konsument når agent_result emitteres). (b) rekursions-guard (værn #11, can-spawn dybde) mangler — TILFØJ som C6. (c) shadow-mode nice-to-have #2 (per-signal effektivitets-feedback) er Fase-2-værktøj, korrekt udeladt her.

### Task C6: Rekursions-guard (spawn-dybde + fan-out-loft)
**Files:** Modify `core/services/agent_runtime_spawn.py` (carry depth-budget in dispatch context; `can-spawn` decrements; refuse at max-depth/max-concurrent/max-fanout); Test `tests/services/test_recursion_guard.py`
- [ ] Test: agent at depth=max cannot spawn; total-concurrent cap enforced; fan-out cap per dispatch. Implement + PASS. Commit `feat(trigger): rekursions-guard — spawn-dybde+fan-out-loft (C6)`.
