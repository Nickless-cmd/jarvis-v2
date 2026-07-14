# jarvis-code Fase 4 — Input/interaction layer Implementation Plan

> For agentic workers: use superpowers:subagent-driven-development.

**Goal:** Give the client-owned jarvis-code loop the full Claude-Code *interaction* surface — reasoning replay, environment awareness, mid-run steering, caching contract, budget ceilings, session fork, and the harness behavioural contract — so Jarvis works like Claude, not just calls the same tools.

**Architecture:** Two repos, no shared imports. The SERVER (`jarvis-v2`) owns the model turn on `POST /v1/agent/step` — it injects the system prompt, so `<env>` (T), the harness contract (Y), the caching-prefix contract (V) and reasoning-replay normalization (S) are server-side, every prompt/payload change gated behind a new `RuntimeSettings` boolean defaulting **False** (inert until flipped). The CLIENT (`jarvis-code`) owns the loop, the composer, the session store and the budget accounting; because it **cannot import `core.*`**, all client-side logic (env gathering, budget math, reasoning pairing on replay, fork, pagination, MultiEdit) is reimplemented locally. Post-Fase-0.5 the loop lives in `src/jc_agent_loop.py` (extracted from `repl_ptk._turn_worker`/`_run_one_step`); CLIENT loop tasks edit that module — the line anchors below point at the current `repl_ptk.py` pre-extraction locations.

**Tech Stack:** Python 3.11+, FastAPI (server route), `prompt_toolkit` (client shell), `httpx` (client transport), pytest in `/opt/conda/envs/ai` for both repos. Server tests: `/opt/conda/envs/ai/bin/python -m pytest <path> -o addopts=""` (bypasses repo `addopts` timeout/marker filter). Client tests: `cd /home/bs/jarvis-code && /opt/conda/envs/ai/bin/python -m pytest tests/<file> -o addopts=""`.

## File Structure

**SERVER (`/media/projects/jarvis-v2`)**
- `apps/api/jarvis_api/routes/agent_loop.py` (modify) — the one place the system prompt is assembled and the model turn runs; hosts env-block injection (T), harness contract (Y), reasoning plumbing+normalization (S), caching-prefix contract + telemetry (V). One responsibility: the `/v1/agent/step` turn.
- `core/runtime/settings.py` (modify) — add the Fase-4 feature-flag booleans (default False).
- `apps/api/jarvis_api/routes/jc_env.py` (create) — pure helper: validate + render the client-sent `env` dict into the `<env>` block. One responsibility: env rendering (kept out of the route file so it is unit-testable without FastAPI).
- `tests/test_agent_step_fase4.py` (create) — server-side Fase-4 tests.

**CLIENT (`/home/bs/jarvis-code`)**
- `src/jc_agent_loop.py` (modify; created in Fase 0.5) — the UI-free turn loop; hosts reasoning capture+replay (S), budget accounting (W), steering boundary (U), 429 handling wiring (13).
- `src/api.py` (modify) — transport: send `env`/`reasoning`/model params; parse reasoning + Retry-After.
- `src/repl_ptk.py` (modify) — composer/keybindings: Esc steering + input queue (U), `@`-mention completer (8), `/clear` + `/session fork` slash (9, 6).
- `src/jc_env.py` (create) — client-side env gatherer (cwd/git/OS/date/commits). One responsibility: collect env; no core import.
- `src/tools.py` (modify) — `local_read_file` pagination (10), `local_multi_edit` (11), schema/registry updates.
- `src/session.py` (modify) — `fork_session` on the client JSONL store (6).
- `src/main.py` (modify) — `--fork` CLI + resume/continue reconciliation (6).
- `src/config.py` (modify) — Fase-4 default config keys (budget caps, env toggle).
- Client tests (create): `tests/test_reasoning_replay.py`, `tests/test_env_block_client.py`, `tests/test_steering.py`, `tests/test_budget.py`, `tests/test_fork.py`, `tests/test_read_pagination.py`, `tests/test_multiedit.py`, `tests/test_subagent_model.py`, `tests/test_retry_after.py`, `tests/test_clear_and_mentions.py`.

---

### Task 1: Extended-thinking / reasoning-replay across tool rounds (S)

Preserve `reasoning_content` across tool rounds with a hard **pairing invariant**, and support a think-budget directive. Reasoning must stay attached to the assistant message that also carries the `tool_calls`, and must never be replayed orphaned (reasoning without its tool_calls, or with the tool_results dropped) — orphaning is the documented 400 root cause ([[reference_copilot_followup_thinking_bug]] "400=ollama-felter", [[reference_gemini_ollama_toolcall_400]]).

**Files:**
- Modify [SERVER]: `apps/api/jarvis_api/routes/agent_loop.py`
  - Non-stream response builder (currently `agent_loop.py:381-392`) — add `"reasoning_content"` to the returned JSON. The underlying `_execute_openai_compatible_chat` (`core/services/cheap_provider_runtime_adapters.py:543-559`) does **not** return reasoning today; add a thin re-extraction in the route from `raw` (deepseek exposes it on `choices[0].message.reasoning_content`) OR extend the adapter return dict — prefer the route-local extraction so the shared adapter stays untouched.
  - Stream done SSE (`agent_loop.py:425-435` and the fallback at `:442-444`) — forward `reasoning_content` from the iterator's done event (the iterator already yields it: `core/services/cheap_provider_runtime_streaming.py:303-312`).
  - Inbound normalization: before `chat_messages.extend(client_messages)` (`agent_loop.py:360`), run a provider-aware pass that keeps `reasoning_content` on assistant-with-tool_calls messages for providers that accept it (deepseek) and **strips** it for providers that 400 on it (ollama/copilot-compat). Add helper `_normalize_reasoning_for_provider(messages, provider)`.
  - Think-budget directive: read `body.get("thinking_mode")` in `agent_step` (`agent_loop.py:324-328`) and map to the provider extra_body via the existing `deepseek_request_for_thinking_mode` (`adapters.py:562`); thread through `_execute_openai_compatible_chat(..., extra_body=...)` and the stream path.
  - Gate everything behind `settings.agent_step_reasoning_replay_enabled` (default False): when off, behave exactly as today (no reasoning in payload, no normalization).
- Modify [SERVER]: `core/runtime/settings.py` — add `agent_step_reasoning_replay_enabled: bool = False`.
- Modify [CLIENT]: `src/api.py` — `agent_step` (`:314`) and `agent_step_stream` (`:352`): add `thinking_mode` to the request body (`:332`, `:371`); parse `reasoning_content` from the non-stream JSON and from the stream done event (`:399-400`) and surface it in the returned dict / a `{"type":"reasoning","text":...}` event.
- Modify [CLIENT]: `src/jc_agent_loop.py` (loop from `repl_ptk._turn_worker:811-864`, step from `_run_one_step:979-1036`). Reimplement client-side (no core import): when a step returns `tool_calls`, attach the captured `reasoning_content` to the assistant message pushed to `api_messages` (`repl_ptk.py:849-850`): `{"role":"assistant","content":content,"reasoning_content":reasoning,"tool_calls":tool_calls}`. Enforce the invariant in one guard `_pair_reasoning(msg)`: reasoning is dropped iff the message has no `tool_calls` OR its tool_results were dropped by the Fase-1 A3 round-atomic fit. A think/`+Nk` composer directive sets `self.thinking_mode` for the turn.
- **Test:** `tests/test_agent_step_fase4.py` (server), `tests/test_reasoning_replay.py` (client).

- [ ] Step: Write failing server test `test_reasoning_forwarded_when_flag_on` — monkeypatch `_execute_openai_compatible_chat` to return `{"text":"","tool_calls":[{...}],"reasoning_content":"because X",...}`, set flag on, POST `/v1/agent/step`; assert response JSON has `reasoning_content == "because X"`. And `test_reasoning_absent_when_flag_off` — flag off → key absent/empty.
- [ ] Step: Write failing server test `test_reasoning_stripped_for_ollama_replay` — send client_messages containing an assistant msg with `reasoning_content` + `tool_calls`, provider forced to an ollama-compat one; assert the outbound messages passed to the adapter have `reasoning_content` removed (captured via monkeypatched adapter), while for `deepseek` it is retained.
- [ ] Step: Write failing client test `test_reasoning_paired_across_three_rounds` — drive `jc_agent_loop` with a stub `agent_step_stream` that yields reasoning+tool_calls for rounds 1–2 then a final text; assert each replayed assistant message carrying `tool_calls` also carries `reasoning_content`, and the final text-only message carries none. `test_reasoning_dropped_when_tool_results_evicted` — simulate A3 eviction; assert `_pair_reasoning` strips the now-orphaned reasoning.
- [ ] Step: Implement server (extraction + normalization + flag + thinking_mode plumb), run server tests to PASS.
- [ ] Step: Implement client (`api.py` parse + body, `jc_agent_loop` attach + `_pair_reasoning`), run client tests to PASS.
- [ ] Step: Commit `feat(fase4): reasoning replay across tool rounds with pairing invariant (flag-gated)`.

**Acceptance:** A 3+ round deepseek loop replays reasoning paired to every tool_calls turn with zero 400s; an ollama-compat loop strips reasoning on replay and also does not 400; flag off = byte-identical to today.

---

### Task 2: Environment `<env>` block in system prompt (T)

Client gathers environment facts and sends them; server injects a fenced `<env>` block into the system prompt (mirrors Claude Code's env block).

**Files:**
- Create [CLIENT]: `src/jc_env.py` — `collect_env(cwd: str) -> dict` returning `{cwd, git_branch, git_status, os, platform, date, recent_commits}`. Reimplemented client-side (no core import): shell out to `git -C cwd rev-parse --abbrev-ref HEAD`, `git status --porcelain` (summarised to counts + first N paths), `git log -5 --oneline`; `platform.platform()`, `platform.system()`; `datetime.now().date().isoformat()`. All subprocesses time-boxed (5s) and fail-safe to `""`.
- Modify [CLIENT]: `src/api.py` — `agent_step`/`agent_step_stream` add `env` to the request body.
- Modify [CLIENT]: `src/jc_agent_loop.py` — call `collect_env(self.cwd)` once per turn (not per round) and pass it down; cache for the turn.
- Create [SERVER]: `apps/api/jarvis_api/routes/jc_env.py` — `render_env_block(env: dict) -> str` producing the `<env>` fenced block with a fixed key order (stable for caching, see Task 4); validates/clamps each field length (git_status capped, commits capped to 5). Pure, no FastAPI import.
- Modify [SERVER]: `agent_loop.py` — in `agent_step` read `body.get("env")`; in `_build_system_prompt` (`:120`) append `render_env_block(env)` when `settings.agent_step_env_block_enabled` (default False) and env is present. Injected AFTER identity/full context so it is the last, most-volatile section (keeps the cacheable prefix stable — Task 4).
- Modify [SERVER]: `core/runtime/settings.py` — add `agent_step_env_block_enabled: bool = False`.
- **Test:** `tests/test_env_block_client.py` (client), `tests/test_agent_step_fase4.py` (server).

- [ ] Step: Write failing client test `test_collect_env_shape` (tmp git repo) — assert keys present, `git_branch` matches created branch, `recent_commits` non-empty; `test_collect_env_no_git_is_safe` (non-git tmp dir) — git fields `""`, no raise.
- [ ] Step: Write failing server test `test_env_block_injected_when_flag_on` — POST with `env={...}`, flag on; capture assembled system prompt (monkeypatch `_execute...` to echo messages); assert `<env>` present with cwd + branch. `test_env_block_absent_when_flag_off`. `test_env_block_key_order_stable` — two renders with same env produce byte-identical block.
- [ ] Step: Implement `jc_env.collect_env`, wire body, implement `render_env_block` + injection + flag; run both suites to PASS.
- [ ] Step: Commit `feat(fase4): <env> block — client sends cwd/git/os/date/commits, server injects (flag-gated)`.

**Acceptance:** With the flag on and a client sending env, the system prompt carries a stable, length-clamped `<env>` block; flag off or no env = unchanged prompt.

---

### Task 3: Mid-run steering — cooperative Esc interrupt + input queue (U) [CLIENT]

Esc is a *cooperative* interrupt distinct from Ctrl-C abort: stop after the current tool completes, keep the turn context, open the composer, and inject the typed correction as the next user message at the round boundary. Typed input during a run is queued (today it is dropped by the `if self.busy` guard in `_on_submit:1407`).

**Files:**
- Modify [CLIENT]: `src/repl_ptk.py`
  - `__init__` (`:293` area) — add `self.steer_requested = False`, `self._input_queue: list[str] = []`.
  - Keybindings (`_build_app`, near `_ctrl_c` at `:1654`) — add `@kb.add("escape", filter=~approving & Condition(lambda: self.busy))` → `self.steer_requested = True` + status "⤵ styrer efter nuværende tool…". Ensure it does NOT collide with the existing approving-mode `escape` binding (that one is `filter=approving`, so filters are disjoint).
  - `_on_submit` (`:1401-1409`) — when `self.busy`, instead of only showing "arbejder stadig", append the text to `self._input_queue` and echo "�added to queue (leveres ved næste boundary)".
- Modify [CLIENT]: `src/jc_agent_loop.py` (loop body from `_turn_worker:834-864`):
  - After each round's tools complete and before the next `_run_one_step`, check `self.steer_requested` OR a non-empty `self._input_queue`: if so, flush queued/steer text as a new `{"role":"user","content":...}` appended to `api_messages`, persist it, clear the flags, and continue the loop (context preserved). This is the round boundary — distinct from Ctrl-C's `stop_requested` which breaks the loop and discards remaining work.
- **Test:** `tests/test_steering.py`.

- [ ] Step: Write failing test `test_queued_input_delivered_at_boundary` — construct `PtkApp` import-safe, set `busy=True`, call `_on_submit("also fix the tests")`; assert `_input_queue == ["also fix the tests"]` and messages NOT run immediately. Then simulate a boundary flush helper and assert the text becomes a user message in `api_messages`.
- [ ] Step: Write failing test `test_esc_sets_steer_not_abort` — assert Esc handler sets `steer_requested=True` and leaves `stop_requested=False` (context kept), whereas Ctrl-C sets `stop_requested=True`.
- [ ] Step: Write failing test `test_boundary_flush_preserves_context` — pre-seed `api_messages` with prior rounds; flush a steer message; assert prior messages still present and the correction appended last.
- [ ] Step: Implement state, keybinding, queue in `_on_submit`, boundary flush in loop; run to PASS.
- [ ] Step: Commit `feat(fase4): cooperative Esc steering + input queue at round boundary`.

**Acceptance:** Typing during a run queues instead of dropping; Esc stops after the current tool and injects the correction next round with full context intact; Ctrl-C still hard-aborts.

---

### Task 4: Prompt-caching contract — stable prefix + telemetry (V)

Deepseek (the client-owned lane's model) does automatic prefix caching (`prompt_cache_hit_tokens`). The "contract" is: keep the cacheable prefix (system+identity, then tools) **byte-stable** across steps within a turn and across turns, put the only volatile section (`<env>`, per-turn context) last, record hit/miss, and never needlessly bust the prefix on tier-switch or compaction.

**Files:**
- Modify [SERVER]: `agent_loop.py`
  - Assert prefix ordering in `agent_step` (`:357-360`): `[system(=_SYSTEM_PROMPT+identity/full, STABLE)] + [tools via payload] + [conversation]`; ensure `<env>`/full-context volatile bits are appended at the tail of the system message so the stable head does not shift.
  - Add cache telemetry: compute `prefix_signature(system_content, tools)` (`core/services/cache_telemetry.py:24`) and call `record_visible_cache(lane="jc-agent-step", provider, model, prefix_sha, prefix_len, cache_hit, cache_miss)` (`cache_telemetry.py:40`) after the model call, reading `cache_hit_tokens`/`cache_miss_tokens` already returned by the adapter (`adapters.py:556-557`). This makes the prefix stability *measurable*.
  - Return `cache_hit_tokens`/`cache_miss_tokens` in the non-stream usage block (`:387-391`) and stream done usage (`:431-434`).
  - Gate the telemetry + ordering re-assertion behind `settings.agent_step_cache_contract_enabled` (default False); flag off = today's ordering, no telemetry call.
- Modify [SERVER]: `core/runtime/settings.py` — add `agent_step_cache_contract_enabled: bool = False`.
- Modify [CLIENT]: `src/jc_agent_loop.py` — do NOT rebuild the tools list per step (already stable via `_tools_for_step`/`presented_tools`); assert the same `presented_tools` object is reused across a turn's rounds (cache-stable order is already established at `tool_catalog.build_presented_tools`). Surface `cache_hit_rate` from `turn_cost` in the footer.
- Modify [CLIENT]: `src/api.py` — pass the returned `cache_hit_tokens`/`cache_miss_tokens` into `turn_cost` usage (extend `agent_step`/`agent_step_stream` result dicts).
- **Test:** `tests/test_agent_step_fase4.py` (server).

- [ ] Step: Write failing server test `test_prefix_signature_stable_across_steps` — two POSTs with identical system+tools but growing conversation; capture `prefix_signature` args via monkeypatched `record_visible_cache`; assert `prefix_sha` identical across the two.
- [ ] Step: Write failing server test `test_env_tail_does_not_bust_prefix` — with env-block flag on, changing only the `<env>` tail must NOT change the *tools+static-system head* signature (env is outside the recorded prefix head). Assert head sha stable.
- [ ] Step: Write failing server test `test_cache_tokens_in_usage` — adapter returns `cache_hit_tokens=100`; assert response usage carries it.
- [ ] Step: Implement ordering assertion, telemetry, usage plumb, flag; run to PASS.
- [ ] Step: Commit `feat(fase4): prompt-cache stable-prefix contract + hit/miss telemetry on agent/step (flag-gated)`.

**Acceptance:** Prefix signature is stable across a turn's steps and across turns; env/volatile context sits in the non-cached tail; cache hit/miss is recorded and surfaced; flag off = unchanged.

---

### Task 5: Budget ceilings — per-run token/USD cap with typed BLOCKED + grant (W) [CLIENT]

A per-run token/USD ceiling that HALTS the loop with a typed `BLOCKED('budget')` result + a continue offer and a `+Nk` grant. Today the only backstop is `max_rounds=60` (`repl_ptk.py:270`) with no spend cap. Reimplemented client-side (no core import to `core.costing`).

**Files:**
- Modify [CLIENT]: `src/config.py` — add defaults `budget_usd_cap` (0 = off), `budget_tokens_cap` (0 = off) to `DEFAULTS` (`:42`).
- Modify [CLIENT]: `src/jc_agent_loop.py`
  - `__init__`-equivalent state: `self.run_cost_usd = 0.0`, `self.run_tokens = 0`, `self.budget_usd_cap`, `self.budget_tokens_cap`, `self.budget_grant_usd = 0.0`.
  - After each step, accumulate from `turn_cost` (`cost_usd`/`estimated_cost_usd`, prompt+completion tokens).
  - Before each round (loop head, `_turn_worker:834`), if a cap is set and `run_cost_usd > cap + grant` (or tokens), do NOT call the model: emit a typed `BLOCKED('budget')` line (`render.sb_sys`) with the current spend and a "fortsæt / +Nk" offer, set a `self._budget_blocked = True`, break. This mirrors the O2 typed-loud-error contract (never silent).
  - `grant_budget(delta_usd)` / a `/budget +Nk` composer directive raises `budget_grant_usd` and clears `_budget_blocked` so the next turn resumes.
- Modify [CLIENT]: `src/repl_ptk.py` — `/budget` slash in `_handle_slash` (`:464`): `/budget` shows caps+spend; `/budget usd 0.50` / `/budget tokens 200000` sets caps; `/budget +0.25` grants.
- **Test:** `tests/test_budget.py`.

- [ ] Step: Write failing test `test_budget_blocks_when_usd_cap_exceeded` — set `budget_usd_cap=0.01`, feed steps whose `turn_cost` sums past it; assert loop halts with a BLOCKED('budget') emit and no further model call (stub `_run_one_step` counts invocations).
- [ ] Step: Write failing test `test_budget_grant_resumes` — after block, call `grant_budget(1.0)`; assert `_budget_blocked` cleared and next turn proceeds.
- [ ] Step: Write failing test `test_no_cap_never_blocks` — caps 0 → arbitrary spend never blocks.
- [ ] Step: Implement config keys, accounting, gate, grant, slash; run to PASS.
- [ ] Step: Commit `feat(fase4): per-run budget ceiling with typed BLOCKED + grant`.

**Acceptance:** With a cap set, the loop halts with a typed BLOCKED('budget') + spend readout + continue/+Nk offer instead of silently burning; grant resumes; no cap = no change.

---

### Task 6: Session resume / continue / fork (X)

Reconcile the client `--continue`/`--session` flags with the (client-owned) JSONL session store and add **fork** (does not exist client-side). The server v2-lane fork endpoint already exists (`apps/api/jarvis_api/routes/jarvisx_sessions.py:322`); this task adds the client-JSONL fork used by the client-owned loop, and threads server-session reconciliation for `tool_loop=server`.

**Files:**
- Modify [CLIENT]: `src/session.py` — add `fork_session(session_id: str, upto_index: int | None = None) -> str`: load `load_session_raw` (`:81`), copy the first `upto_index` (or all) entries into a new `generate_session_id()` JSONL, return the new id. Reimplemented on the local JSONL store (no core import).
- Modify [CLIENT]: `src/main.py` — add `--fork ID [--fork-at N]` args (near session args `:53-57`); in the non-interactive command block (`:131-181`) handle `--fork`: create the fork, print the new id, exit. Reconciliation: `--continue`/`--session` already resolve a client JSONL id (`:208-225`) — keep as-is; when `tool_loop=server`, map the client session id to a server session via `ensure_server_session` once and store the mapping (already partially in `repl_ptk.server_session_id`).
- Modify [CLIENT]: `src/repl_ptk.py` — extend the existing `/session` handler (`:564-664`) with a `fork` subcommand: `/session fork [N]` forks the active session (optionally up to message N), switches `self.session_id`/`self.messages` to the fork, echoes the new id. Mirror the existing `select`/`delete` structure.
- **Test:** `tests/test_fork.py`.

- [ ] Step: Write failing test `test_fork_copies_all_messages` (tmp sessions dir via monkeypatched `ensure_sessions_dir`) — seed a session with 5 msgs; fork; assert new id differs and new JSONL has 5 msgs.
- [ ] Step: Write failing test `test_fork_upto_index` — fork with `upto_index=3`; assert new session has exactly 3 msgs and the original is untouched.
- [ ] Step: Write failing test `test_slash_session_fork_switches_active` — construct `PtkApp`, seed `messages`+`session_id`, call `_handle_slash("/session fork")`; assert `self.session_id` changed and points at a file with the copied messages.
- [ ] Step: Write failing test `test_main_fork_flag` (subprocess/`main([...])`) — `--fork <id>` prints a new id and exits 0.
- [ ] Step: Implement `fork_session`, `--fork`, `/session fork`; run to PASS.
- [ ] Step: Commit `feat(fase4): session fork (client JSONL) + /session fork + --fork; resume/continue reconciled`.

**Acceptance:** `--continue`/`--session` load the right JSONL; `/session fork [N]` and `--fork` produce an independent copy up to a point without mutating the source; server-lane sessions still reconcile via `ensure_server_session`.

---

### Task 7: Harness behavioural contract in system prompt (Y) [SERVER]

Add the behavioural clauses that make Claude Code *feel* stable: conciseness / no preamble-postamble, comment discipline, proactiveness bounds, refuse-with-alternative, verify-before-done. This is the highest-leverage, lowest-code change — so it is flag-gated and A/B-able.

**Files:**
- Modify [SERVER]: `agent_loop.py` — extend `_SYSTEM_PROMPT` (`:50-57`) with a `_HARNESS_CONTRACT` constant (Danish, matching the existing voice) appended in `_build_system_prompt` (`:120-131`) only when `settings.agent_step_harness_contract_enabled` (default False). Clauses: (a) svar kort, ingen indledende/afsluttende høflighedsfyld; (b) tilføj ikke kommentarer med mindre bedt om det / koden kræver det; (c) vær proaktiv når bedt om at handle, men overrask ikke brugeren med utilbedte handlinger; (d) hvis du må afvise, tilbyd et alternativ i 1-2 linjer; (e) verificér før du melder "færdig" ([[feedback_verify_visual_before_done]]). Keep it byte-stable in the *cacheable head* (before `<env>`) so Task 4's prefix stays warm.
- Modify [SERVER]: `core/runtime/settings.py` — add `agent_step_harness_contract_enabled: bool = False`.
- **Test:** `tests/test_agent_step_fase4.py` (server).

- [ ] Step: Write failing test `test_harness_contract_present_when_flag_on` — flag on; capture assembled system prompt; assert it contains the verify-before-done and no-preamble clauses.
- [ ] Step: Write failing test `test_harness_contract_absent_when_flag_off` — flag off; assert clauses absent (prompt == baseline).
- [ ] Step: Write failing test `test_harness_contract_in_cacheable_head` — with env flag also on, assert the contract text appears BEFORE the `<env>` tail (so it is inside the stable prefix).
- [ ] Step: Implement `_HARNESS_CONTRACT` + gated append; run to PASS.
- [ ] Step: Commit `feat(fase4): harness behavioural contract in agent/step system prompt (flag-gated)`.

**Acceptance:** With the flag on, the contract is present in the cacheable head; flag off = baseline prompt unchanged.

---

### Task 8: `@`-file mentions + autocomplete in composer (+) [CLIENT]

Typing `@` in the composer offers path completion; selecting inserts the path so the model can be pointed at a file (and optionally inlines a short reference).

**Files:**
- Modify [CLIENT]: `src/repl_ptk.py` — add an `@`-trigger completer alongside the existing slash-completions machinery (`_completions_frags`/`_completion_state` near `:1477-1565`). Reuse `prompt_toolkit`'s `PathCompleter` scoped to `self.cwd`; trigger when the word under the cursor starts with `@`. On accept, replace `@partial` with the resolved path. This is composer-only; no model-protocol change.
- **Test:** `tests/test_clear_and_mentions.py`.

- [ ] Step: Write failing test `test_mention_completions_lists_cwd_files` — in a tmp cwd with `foo.py`/`bar.py`, drive the completer with buffer text `@fo`; assert `foo.py` is among the completion candidates (call the completer function directly, no TTY).
- [ ] Step: Write failing test `test_mention_only_triggers_on_at` — buffer `fo` (no `@`) yields no path completions from the mention completer.
- [ ] Step: Implement the `@`-completer branch; run to PASS.
- [ ] Step: Commit `feat(fase4): @-file mentions with cwd path autocomplete in composer`.

**Acceptance:** `@` opens cwd-scoped path completion; accepting inserts the path; non-`@` input is unaffected.

---

### Task 9: `/clear` context reset (+) [CLIENT]

`/clear` resets the in-session conversation (distinct from `/compact`, which summarizes). Keeps the session id; clears `self.messages` and live regions.

**Files:**
- Modify [CLIENT]: `src/repl_ptk.py` — add `/clear` to `_handle_slash` (`:464`): clear `self.messages`, `self._round`, `self._stream_text`, reset `self._assistant_final`; echo "context ryddet (session bevaret)". Do NOT delete the JSONL (history stays on disk; only the live context window is cleared). Update `/help` (`:472-488`).
- **Test:** `tests/test_clear_and_mentions.py`.

- [ ] Step: Write failing test `test_clear_empties_messages_keeps_session` — seed `messages` + a `session_id`; `_handle_slash("/clear")`; assert `messages == []` and `session_id` unchanged.
- [ ] Step: Write failing test `test_clear_resets_live_regions` — set `_round`/`_stream_text`; after `/clear` assert both empty.
- [ ] Step: Implement; run to PASS.
- [ ] Step: Commit `feat(fase4): /clear context reset (keeps session, distinct from /compact)`.

**Acceptance:** `/clear` empties the live context but preserves the session id and on-disk history.

---

### Task 10: Read pagination (offset/limit) + line cap (+) [CLIENT]

`read_file` gains `offset`/`limit` and a default line cap (2000, like Claude Code), with a visible truncation marker. Reimplemented client-side in `tools.py`.

**Files:**
- Modify [CLIENT]: `src/tools.py`
  - `local_read_file` (`:304-315`) — add `offset: int = 0`, `limit: int | None = None`; read by lines, slice `[offset : offset+limit]`, default cap `limit or 2000`; return `content` plus `{total_lines, returned_lines, truncated: bool, offset}` and a trailing `… (afkortet: viser N/M linjer — brug offset/limit)` marker when truncated. Keep `status`/`size`.
  - `LOCAL_TOOLS` read_file schema (`:49-59`) — add `offset` (integer) and `limit` (integer) properties with descriptions.
- **Test:** `tests/test_read_pagination.py`.

- [ ] Step: Write failing test `test_read_offset_limit_slices` (tmp file 100 lines) — `local_read_file(path, offset=10, limit=5)`; assert exactly 5 lines starting at line 11 and `truncated is True`.
- [ ] Step: Write failing test `test_read_default_cap_2000` (tmp file 3000 lines) — no limit; assert 2000 lines returned + truncation marker + `total_lines==3000`.
- [ ] Step: Write failing test `test_read_small_file_untruncated` (10 lines) — `truncated is False`, all 10 returned.
- [ ] Step: Implement pagination + schema; run to PASS.
- [ ] Step: Commit `feat(fase4): read_file offset/limit pagination + 2000-line cap with visible truncation`.

**Acceptance:** `read_file` respects offset/limit, caps at 2000 lines by default, and always marks truncation visibly (never silently drops).

---

### Task 11: MultiEdit — atomic multi-edit tool (+) [CLIENT]

A `multi_edit` tool applies a list of find/replace edits to a single file atomically (all-or-nothing), with a single undo entry. Reimplemented client-side.

**Files:**
- Modify [CLIENT]: `src/tools.py`
  - Add `local_multi_edit(path: str, edits: list[dict]) -> dict` — each edit `{old_text, new_text, replace_all?}`; apply sequentially to an in-memory buffer; if ANY edit fails (old_text absent, or ambiguous without `replace_all`, mirroring `local_edit_file:353-381`) return `{"status":"error", ...}` and write nothing (atomic). On success write once, return one `diff` + one `_undo_*` triple (single undo).
  - Register in `TOOL_EXECUTORS` (`:476`) and `WRITE_TOOLS` (`:509`); add a `multi_edit` entry to `LOCAL_TOOLS` with an `edits` array schema.
- **Test:** `tests/test_multiedit.py`.

- [ ] Step: Write failing test `test_multiedit_all_apply` (tmp file) — two edits both present; assert both applied, one `diff`, one undo triple.
- [ ] Step: Write failing test `test_multiedit_atomic_rollback` — first edit valid, second `old_text` absent; assert `status=="error"` and the file on disk is UNCHANGED.
- [ ] Step: Write failing test `test_multiedit_single_undo_entry` — after success, driving undo once fully reverts the file.
- [ ] Step: Implement `local_multi_edit` + registration + schema; run to PASS.
- [ ] Step: Commit `feat(fase4): multi_edit atomic multi-edit tool with single undo`.

**Acceptance:** All edits apply or none do; a failed edit leaves the file byte-identical; success yields exactly one undo entry.

---

### Task 12: Per-subagent model selection (+) [CLIENT]

The client dispatch executor (built in Fase 2) accepts a per-subagent `model` and threads it to the dispatch call + render. Small, rides on Fase 2's dispatch client-executor.

**Files:**
- Modify [CLIENT]: `src/jc_agent_loop.py` (or the Fase-2 dispatch executor within it) — when the model requests a `dispatch`/subagent tool with a `model` argument, pass it through to the forwarded call (`route_tool_call` → `execute_native_tool`, `src/tools.py:487` / `src/api.py:447`) as part of the arguments dict; validate against `get_available_models(role)` (`src/models.py:99`) client-side and fall back to the default when unavailable. Render the chosen model in the subagent chip.
- Modify [CLIENT]: `src/api.py` — ensure `execute_native_tool` forwards arbitrary arguments (already does via `arguments=args`); no signature change needed beyond confirming `model` survives.
- **Test:** `tests/test_subagent_model.py`.

- [ ] Step: Write failing test `test_subagent_model_threaded` — stub `execute_native_tool` capturing arguments; dispatch with `model="deepseek-v4-pro"`; assert the forwarded arguments carry `model=="deepseek-v4-pro"`.
- [ ] Step: Write failing test `test_subagent_model_falls_back_when_unavailable` — request a model not in the role's tiers; assert it is replaced by the default and a note is rendered.
- [ ] Step: Implement threading + validation; run to PASS.
- [ ] Step: Commit `feat(fase4): per-subagent model selection threaded to dispatch`.

**Acceptance:** A subagent's `model` argument reaches the forwarded dispatch call; unavailable models fall back to the default with a visible note. (Depends on Fase 2 dispatch executor.)

---

### Task 13: 429 Retry-After handling (+) [CLIENT]

Honor the `Retry-After` HTTP header on 429 (the server rate-limit middleware sets it: `apps/api/jarvis_api/middleware/security_headers.py:123-124`). Today the client parses `retry_after` only from the JSON body (`src/api.py:152-160`), not the header, and does not act on it.

**Files:**
- Modify [CLIENT]: `src/api.py`
  - `agent_step` (`:334-343`) and `agent_step_stream` (`:375-384`): on `status_code == 429`, read `r.headers.get("Retry-After")` (fallback to body `retry_after`), and return a typed `{"error": ..., "status_code": 429, "error_type": "rate_limit", "retry_after": <seconds>}` (mirror the structured quota shape already at `:151-160`). Do NOT blind-retry (429 is in the non-retryable set, `:280-282`); surface it typed.
- Modify [CLIENT]: `src/jc_agent_loop.py` — when a step returns a `rate_limit`/429 typed error, emit a typed `BLOCKED('rate_limit', retry_after=Ns)` line (consistent with Task 5's typed-BLOCKED style) and halt the turn cleanly; optionally schedule a single respectful resume after `retry_after` if unattended (config `auto_resume_on_rate_limit`, default off).
- **Test:** `tests/test_retry_after.py`.

- [ ] Step: Write failing test `test_retry_after_header_parsed` — stub httpx response 429 with header `Retry-After: 30` and empty body; assert `agent_step` returns `retry_after == 30` and `error_type == "rate_limit"`.
- [ ] Step: Write failing test `test_retry_after_body_fallback` — 429 with body `retry_after_seconds` only (no header); assert parsed.
- [ ] Step: Write failing test `test_loop_blocks_typed_on_rate_limit` — step returns the typed 429; assert the loop halts with a BLOCKED('rate_limit') emit and does not blind-retry.
- [ ] Step: Implement header parse + typed surfacing + loop handling; run to PASS.
- [ ] Step: Commit `feat(fase4): honor 429 Retry-After header with typed BLOCKED('rate_limit')`.

**Acceptance:** A 429 surfaces the header/body Retry-After as a typed rate_limit block that halts cleanly (no blind retry, no silent hang).

---

## Acceptance (Fase 4)

1. **Reasoning replay (S):** a 3+ round deepseek loop replays `reasoning_content` paired to every `tool_calls` turn with zero orphan-400s; an ollama/copilot-compat loop strips reasoning on replay and also does not 400; think/`+Nk` budget threads to the provider. Flag off = today's behaviour.
2. **Env (T):** with the flag on and a client sending env, the system prompt carries a stable, length-clamped `<env>` block (cwd/git branch+status/OS/date/recent commits); flag off = unchanged.
3. **Steering (U):** typing during a run queues instead of dropping; Esc stops after the current tool and injects the correction next round with context intact; Ctrl-C still hard-aborts.
4. **Caching (V):** prefix signature is stable across a turn's steps and across turns, env/volatile context sits in the non-cached tail, cache hit/miss is recorded and surfaced; flag off = unchanged.
5. **Budget (W):** with a cap set the loop halts with a typed BLOCKED('budget') + spend readout + continue/+Nk offer; grant resumes; no cap = no change.
6. **Sessions (X):** `--continue`/`--session` load the right JSONL; `/session fork [N]` and `--fork` produce an independent copy up to a point without mutating the source.
7. **Harness contract (Y):** flag on → the conciseness/no-preamble/comment-discipline/proactiveness/refuse-with-alternative/verify-before-done clauses are present in the cacheable head; flag off = baseline.
8. **+ bucket:** `@`-mentions autocomplete cwd files; `/clear` resets live context keeping the session; `read_file` paginates + caps at 2000 lines with visible truncation; `multi_edit` is atomic with a single undo; per-subagent `model` threads to dispatch; 429 Retry-After is honored as a typed block.
9. **Regression:** all four new `RuntimeSettings` flags default False and are proven inert (baseline-identical prompt/payload when off); full jarvis-code pytest suite and the touched jarvis-v2 tests green under `-o addopts=""`.
