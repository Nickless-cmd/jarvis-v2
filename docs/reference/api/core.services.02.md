# `core.services.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/agent_pool_router.py`
_Agent-pool router (spec §4 + §5.5). Tyndt lag over central_route så agenter_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `route_agent_task` | `(*, kind=…, min_tokens=…, quality_threshold=…, allow_paid=…, exclude=…, owner_user_id=…)` | Vælg (provider, model) for en agent-task via central_route. Aldrig tør. | [src](../../../core/services/agent_pool_router.py#L41) |
| function | `_load_task_scores` | `(provider, model)` | Nuværende task_scores for (provider, model) fra runtime-state. {} ved intet. | [src](../../../core/services/agent_pool_router.py#L114) |
| function | `_save_task_scores` | `(provider, model, scores)` | — | [src](../../../core/services/agent_pool_router.py#L125) |
| function | `update_task_score` | `(*, provider, model, kind, outcome_quality, lr=…)` | §4.4 kvalitets-læring: EMA-opdatér task_score for (model, kind) fra et | [src](../../../core/services/agent_pool_router.py#L133) |

## `core/services/agent_pool_surface.py`
_Agent-puljen — en LET liste man kan filtrere i._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rows` | `(sql, params=…)` | — | [src](../../../core/services/agent_pool_surface.py#L37) |
| function | `agent_liste` | `(*, status=…, rolle=…, soeg=…, limit=…, offset=…)` | Agenterne med deres koersels-tal. Ét opslag, filtrerbart, sideinddelt. | [src](../../../core/services/agent_pool_surface.py#L43) |
| function | `_varighed` | `(start, slut)` | Sekunder mellem to tidsstempler. 0 naar vi ikke kan regne det ud. | [src](../../../core/services/agent_pool_surface.py#L118) |
| function | `pool_opsummering` | `(timer=…)` | Puljens tilstand: hvor mange, hvilke roller, hvad koster de, hvor er graenserne. | [src](../../../core/services/agent_pool_surface.py#L132) |
| function | `seneste_arbejde` | `(limit=…)` | De nyeste koersler paa tvaers af agenter — «hvad sker der lige nu». | [src](../../../core/services/agent_pool_surface.py#L188) |

## `core/services/agent_prompt_layers.py`
_De tre versionsmaerkede promptlag for en agentrequest + snapshot foer foerste modelkald (C3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_prompt_tables` | `(conn)` | — | [src](../../../core/services/agent_prompt_layers.py#L37) |
| function | `_sha` | `(text)` | — | [src](../../../core/services/agent_prompt_layers.py#L58) |
| function | `_redact` | `(text)` | — | [src](../../../core/services/agent_prompt_layers.py#L62) |
| function | `build_layered_prompt` | `(*, agent, messages_text, execution_mode, extra_instruction=…)` | Byg de tre lag, eller ``None`` for en agent uden aabent assignment (legacy-vejen). | [src](../../../core/services/agent_prompt_layers.py#L71) |
| function | `snapshot_prompt` | `(*, run_id, agent, layers, tools_payload=…)` | Gem den effektive prompt + versioner + modelrute + vaerktoejsskema FOER foerste modelkald. | [src](../../../core/services/agent_prompt_layers.py#L128) |
| function | `get_prompt_snapshot` | `(*, owner_user_id, run_id)` | Ejer-kontrolleret opslag; en andens run er ``None``. | [src](../../../core/services/agent_prompt_layers.py#L154) |

## `core/services/agent_relay.py`
_Agent relay — direct A→B messaging between sub-agents._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `relay_message` | `(*, from_agent_id, to_agent_id, content, kind=…)` | Send a message from agent A to agent B. | [src](../../../core/services/agent_relay.py#L25) |
| function | `relay_to_role` | `(*, from_agent_id, council_id, role, content, kind=…)` | Send to whoever in this council holds the given role. | [src](../../../core/services/agent_relay.py#L82) |
| function | `_exec_relay_message` | `(args)` | — | [src](../../../core/services/agent_relay.py#L107) |
| function | `_exec_relay_to_role` | `(args)` | — | [src](../../../core/services/agent_relay.py#L116) |

## `core/services/agent_result_inbox.py`
_Leverer agenters terminale resultater ind i parentens modelrequest (A/B, §6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_render` | `(msgs)` | — | [src](../../../core/services/agent_result_inbox.py#L23) |
| function | `_render_state` | `(p)` | Tilstandsbesked (ikke et resultat): et uvist udfald. Hverken succes eller noget at genforsoege. | [src](../../../core/services/agent_result_inbox.py#L50) |
| function | `_render_approvals` | `(rows)` | — | [src](../../../core/services/agent_result_inbox.py#L59) |
| function | `claim_for_model_step` | `(*, owner_user_id, session_id)` | Claim alle ubehandlede resultater OG nye ventende approvals for (ejer, session) og returner teksten til | [src](../../../core/services/agent_result_inbox.py#L69) |
| function | `add_to_turn_tail` | `(tur_hale, *, owner_user_id, session_id)` | Claim det der venter og haeft det VEDVARENDE paa turens hale (resten af turen). | [src](../../../core/services/agent_result_inbox.py#L93) |

## `core/services/agent_retention.py`
_Retention for agentartefakter og agentens hukommelse (agent-contract-v1 leverance C, hul 4; spec 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_iso` | `(dt)` | — | [src](../../../core/services/agent_retention.py#L50) |
| function | `_parse` | `(value)` | — | [src](../../../core/services/agent_retention.py#L54) |
| function | `_assignment_state` | `(conn, assignment_id, names_worktree)` | Hvorfor (``reason``) et assignments artefakter er beskyttet - eller hvornaar de udloeber (``expires``). | [src](../../../core/services/agent_retention.py#L62) |
| function | `_expire` | `(conn, rec, now)` | Slet filen (kun hvis stien er den forventede) og goer posten til en tombstone. Idempotent. | [src](../../../core/services/agent_retention.py#L110) |
| function | `sweep_artifacts` | `(*, now=…)` | — | [src](../../../core/services/agent_retention.py#L137) |
| function | `sweep_memory` | `(*, now=…)` | Luk-retention for agentens egen hukommelse. Roerer aldrig en agent der ikke er ``closed``. | [src](../../../core/services/agent_retention.py#L165) |
| function | `run` | `(*, now=…)` | Hele retentionrunden: worktrees (7/14/30 dage), artefakter, hukommelse. Hver del er uafhaengig. | [src](../../../core/services/agent_retention.py#L202) |
| function | `run_if_due` | `()` | Throttlet til højst én runde i timen pr. proces (runden er idempotent, saa to processer er ufarligt). | [src](../../../core/services/agent_retention.py#L218) |

## `core/services/agent_runtime.py`
_Agent runtime — sub-agents, councils, swarms (facade)._

_(no top-level classes or functions)_

## `core/services/agent_runtime_base.py`
_Agent runtime — shared foundation (imports, constants, role templates, helpers)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/agent_runtime_base.py#L63) |
| function | `_role_needs_tools` | `(role)` | — | [src](../../../core/services/agent_runtime_base.py#L86) |
| function | `agent_tools_enabled` | `()` | Read the reversible ``agent_tools_enabled`` runtime-state flag. | [src](../../../core/services/agent_runtime_base.py#L110) |
| function | `set_agent_tools_enabled` | `(enabled, *, role=…)` | Flip the ``agent_tools_enabled`` flag. Returns the CURRENT value. | [src](../../../core/services/agent_runtime_base.py#L125) |
| function | `_build_agent_tools_payload` | `(allowed_tools, *, ceiling=…)` | Build an OpenAI-compat tools array from an agent's allowed_tools. | [src](../../../core/services/agent_runtime_base.py#L145) |
| function | `_execute_agent_tool_call` | `(tool_call, *, agent_id)` | Execute one model-issued tool call through the guarded dispatcher. | [src](../../../core/services/agent_runtime_base.py#L189) |
| function | `_run_agent_tool_loop` | `(*, agent, prompt, requires_tools, run_id=…, resume=…)` | Run an agent turn WITH a real tools array + tool-execution loop. | [src](../../../core/services/agent_runtime_base.py#L269) |
| class | `_InProcessLoopIO` | `` | Loekkens I/O naar den koerer i serverprocessen (dagens adfaerd, uaendret). | [src](../../../core/services/agent_runtime_base.py#L313) |
| method | `_InProcessLoopIO.__init__` | `(self, *, agent, run_id, resume=…)` | — | [src](../../../core/services/agent_runtime_base.py#L316) |
| method | `_InProcessLoopIO.model` | `(self, *, messages, tools, requires_tools, provider, model)` | — | [src](../../../core/services/agent_runtime_base.py#L327) |
| method | `_InProcessLoopIO.run_id` | `(self)` | — | [src](../../../core/services/agent_runtime_base.py#L342) |
| method | `_InProcessLoopIO.tool` | `(self, tc)` | — | [src](../../../core/services/agent_runtime_base.py#L345) |
| method | `_InProcessLoopIO.after_tool` | `(self, tc, tool_out)` | — | [src](../../../core/services/agent_runtime_base.py#L366) |
| method | `_InProcessLoopIO.after_round` | `(self, rounds, tool_calls)` | — | [src](../../../core/services/agent_runtime_base.py#L369) |
| function | `_bogfoer_start` | `(agent, run_id, tc)` | Startposten for et vaerktoejskald (status ``running``, ``started_at`` sat, ingen ``finished_at``). | [src](../../../core/services/agent_runtime_base.py#L378) |
| function | `_bogfoer_vaerktoejskald` | `(agent, run_id, tc, tool_out)` | BOGFOER KALDET (db + per-agent transcript). `agent_tool_calls` havde foer NUL kaldere: | [src](../../../core/services/agent_runtime_base.py#L394) |
| function | `_loop_result` | `(o, *, scout, provider, model)` | — | [src](../../../core/services/agent_runtime_base.py#L432) |
| function | `_role_prompt` | `(intro, *, tools=…, structured=…)` | Compose a role intro with the shared discipline blocks. ``tools`` adds the | [src](../../../core/services/agent_runtime_base.py#L531) |
| function | `tools_for_policy` | `(policy)` | Concrete tool-name allowlist for a tool_policy. Unknown/empty → []. | [src](../../../core/services/agent_runtime_base.py#L590) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/agent_runtime_base.py#L729) |
| function | `_json_loads` | `(raw, fallback)` | — | [src](../../../core/services/agent_runtime_base.py#L733) |

## `core/services/agent_runtime_council.py`
_Agent runtime — council & swarm collective rounds._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_trim` | `(text, limit=…)` | Forkort en position synligt. Selve reglen bor i `text_clip`. | [src](../../../core/services/agent_runtime_council.py#L50) |
| function | `_parse_percent_confidence` | `(text)` | — | [src](../../../core/services/agent_runtime_council.py#L61) |
| function | `_extract_confidence` | `(text)` | — | [src](../../../core/services/agent_runtime_council.py#L79) |
| function | `_extract_vote` | `(text)` | — | [src](../../../core/services/agent_runtime_council.py#L96) |
| function | `_format_peer_context` | `(messages, *, target_agent_id=…, limit=…)` | — | [src](../../../core/services/agent_runtime_council.py#L110) |
| function | `_detect_swarm_conflicts` | `(outputs)` | Detect disagreements across swarm/council outputs. | [src](../../../core/services/agent_runtime_council.py#L121) |
| function | `_load_council_model_config` | `()` | Read ~/.jarvis-v2/config/council_models.json, return role_models list. | [src](../../../core/services/agent_runtime_council.py#L142) |
| function | `create_council_session_runtime` | `(*, topic, roles=…, owner_agent_id=…, member_models=…)` | — | [src](../../../core/services/agent_runtime_council.py#L155) |
| function | `create_swarm_session_runtime` | `(*, topic, roles=…, owner_agent_id=…, member_models=…)` | — | [src](../../../core/services/agent_runtime_council.py#L205) |
| function | `post_council_message` | `(*, council_id, content, kind=…, role=…)` | — | [src](../../../core/services/agent_runtime_council.py#L255) |
| function | `_derive_initiative` | `(synthesis, *, topic=…)` | Distil a short, actionable initiative string from a synthesis. | [src](../../../core/services/agent_runtime_council.py#L278) |
| function | `_augment_council_surface` | `(council_id, *, conclusion, initiative=…)` | Build the collective-round return dict with conclusion + initiative. | [src](../../../core/services/agent_runtime_council.py#L308) |
| function | `_run_collective_round` | `(council_id, *, mode)` | Run one collective (council or swarm) round to a conclusion. | [src](../../../core/services/agent_runtime_council.py#L327) |
| function | `_close_council_agents` | `(council_id)` | Mark all council member agents as completed to release spawn slots. | [src](../../../core/services/agent_runtime_council.py#L676) |
| function | `_build_council_role_prefixed_summary` | `(members)` | — | [src](../../../core/services/agent_runtime_council.py#L699) |
| function | `run_council_round` | `(council_id)` | Run one council round and ALWAYS close the session afterwards. | [src](../../../core/services/agent_runtime_council.py#L710) |
| function | `run_swarm_round` | `(council_id)` | Run one swarm round and ALWAYS close the session afterwards. | [src](../../../core/services/agent_runtime_council.py#L727) |

## `core/services/agent_runtime_spawn.py`
_Agent runtime — spawn, execution, messaging, scheduling & lifecycle._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_maybe_relay_watcher_signal` | `(*, agent_id, name, text)` | Emit watcher.signal event when output contains notable content. | [src](../../../core/services/agent_runtime_spawn.py#L54) |
| function | `_spawn_depth_for` | `(parent_agent_id)` | Return depth for a new child agent (parent_depth + 1). | [src](../../../core/services/agent_runtime_spawn.py#L79) |
| function | `_scout_maa_betale` | `(role, tool_policy)` | Må denne agent vælge blandt de BETALTE udbydere? | [src](../../../core/services/agent_runtime_spawn.py#L112) |
| function | `spawn_agent_task` | `(*, role, goal, system_prompt=…, tool_policy=…, allowed_tools=…, parent_agent_id=…, persistent=…, ttl_seconds=…, budget_tokens=…, max_turns=…, context=…, result_contract=…, execution_mode=…, auto_execute=…, council_id=…, provider=…, respekter_model=…, model=…, contract=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L137) |
| function | `_agent_thread_id` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_spawn.py#L455) |
| function | `_format_messages` | `(messages, *, limit=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L464) |
| function | `_result_contract_text` | `(contract)` | — | [src](../../../core/services/agent_runtime_spawn.py#L477) |
| function | `_build_agent_prompt` | `(*, agent, messages, execution_mode, extra_instruction=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L484) |
| function | `_snapshot_tools` | `(agent)` | Det vaerktoejsskema agenten faktisk faar (tomt naar den koerer uden haender). | [src](../../../core/services/agent_runtime_spawn.py#L506) |
| function | `_live_run` | `(run_id)` | Det runforsoeg der koerer nu (G): foelger en failover-kaede; aldrig en undtagelse. | [src](../../../core/services/agent_runtime_spawn.py#L524) |
| function | `execute_agent_task` | `(*, agent_id, thread_id=…, execution_mode=…)` | Koer et barns arbejde. | [src](../../../core/services/agent_runtime_spawn.py#L534) |
| function | `_execute_agent_task_impl` | `(*, agent_id, thread_id=…, execution_mode=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L575) |
| function | `send_message_to_agent` | `(*, agent_id, content, role=…, kind=…, execution_mode=…, auto_execute=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1042) |
| function | `send_peer_message` | `(*, from_agent_id, to_agent_id, content, kind=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1070) |
| function | `_council_thread_id` | `(council_id)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1098) |
| function | `schedule_agent_task` | `(*, agent_id, schedule_kind=…, delay_seconds=…, schedule_expr=…, activate=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1102) |
| function | `cleanup_stale_agents` | `(*, waiting_timeout_minutes=…, failed_timeout_minutes=…, active_timeout_minutes=…, starting_timeout_minutes=…, blocked_timeout_minutes=…, max_per_run=…)` | Auto-cancel agents hanging in non-terminal states for too long. | [src](../../../core/services/agent_runtime_spawn.py#L1140) |
| function | `run_due_agent_schedules` | `(*, limit=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1345) |
| function | `_check_spawn_limits` | `()` | — | [src](../../../core/services/agent_runtime_spawn.py#L1389) |
| function | `_check_budget_and_expire` | `(agent_id, *, tokens_used)` | Expire agent if it has exceeded its token budget. Returns True if expired. | [src](../../../core/services/agent_runtime_spawn.py#L1398) |
| function | `_check_max_turns_and_expire` | `(agent_id)` | Expire agent if it has reached its max_turns limit. Returns True if expired. | [src](../../../core/services/agent_runtime_spawn.py#L1437) |
| function | `_schedule_retry_backoff` | `(agent_id, failure_count)` | Schedule a retry with exponential backoff. Returns delay seconds. | [src](../../../core/services/agent_runtime_spawn.py#L1467) |
| function | `cancel_agent` | `(agent_id, *, note=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1482) |
| function | `suspend_agent` | `(agent_id, *, note=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1501) |
| function | `resume_agent` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1518) |
| function | `expire_agent` | `(agent_id, *, reason=…)` | — | [src](../../../core/services/agent_runtime_spawn.py#L1537) |
| function | `promote_agent_result` | `(agent_id, *, note=…)` | File an autonomy proposal to promote the agent's latest result to Jarvis memory. | [src](../../../core/services/agent_runtime_spawn.py#L1559) |
| function | `_frisk` | `(agent, *, minutter=…)` | Er raekken roert for nylig? Bruges KUN til at afgoere om et tomt | [src](../../../core/services/agent_runtime_spawn.py#L1599) |
| function | `recover_crashed_agents` | `()` | Called on API startup: reset agents that were mid-execution when the process died. | [src](../../../core/services/agent_runtime_spawn.py#L1616) |

## `core/services/agent_runtime_surfaces.py`
_Agent runtime — read surfaces (agent + council/swarm projections)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_agent_runtime_surface` | `(limit=…)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L30) |
| function | `enrich_agent_surface` | `(agent)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L62) |
| function | `build_agent_detail_surface` | `(agent_id)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L99) |
| function | `build_council_surface` | `(limit=…)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L106) |
| function | `enrich_council_surface` | `(session)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L130) |
| function | `build_council_detail_surface` | `(council_id)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L143) |
| function | `_progress_label` | `(*, agent, latest_run)` | — | [src](../../../core/services/agent_runtime_surfaces.py#L150) |

## `core/services/agent_sandbox.py`
_bubblewrap-sandbox til en agent-worker (agent-contract-v1 C6b, spec 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SandboxUnavailable` | `` | Sandboxen kan ikke etableres - agentens loekke maa ikke koere usandboxet. | [src](../../../core/services/agent_sandbox.py#L54) |
| function | `bwrap_path` | `()` | — | [src](../../../core/services/agent_sandbox.py#L58) |
| function | `python_prefixes` | `()` | — | [src](../../../core/services/agent_sandbox.py#L65) |
| function | `sandbox_python_mounts` | `()` | ``(kilde, maal)`` for hvert Python-prefix - kilden bindes til en NEUTRAL sti uden for /home. | [src](../../../core/services/agent_sandbox.py#L73) |
| function | `sandbox_path` | `(path)` | Den sti ``path`` har INDE i sandboxen. | [src](../../../core/services/agent_sandbox.py#L78) |
| function | `build_bwrap_argv` | `(command, *, pass_fds=…, extra_env=…, worker_files=…, rw_binds=…, chdir=…, mounts=…)` | Byg ``bwrap``-kommandolinjen for ``command`` (som koeres INDE i sandboxen). | [src](../../../core/services/agent_sandbox.py#L91) |
| function | `pids_limit_disabled` | `()` | — | [src](../../../core/services/agent_sandbox.py#L136) |
| function | `scope_env` | `()` | Miljoeet ``systemd-run --user`` skal bruge. En systemd-service har ofte ikke ``XDG_RUNTIME_DIR``. | [src](../../../core/services/agent_sandbox.py#L140) |
| function | `_scope_argv` | `(limit)` | — | [src](../../../core/services/agent_sandbox.py#L149) |
| function | `cgroup_pids_available` | `(*, force=…)` | Kan vi lave en cgroup-scope med ``TasksMax`` for den aktuelle bruger? Cachet i 30 s (brugerens | [src](../../../core/services/agent_sandbox.py#L156) |
| function | `pids_prefix` | `(limit)` | ``systemd-run --user --scope -p TasksMax=N`` foer bwrap, eller ``[]`` hvis graensen er fravalgt. | [src](../../../core/services/agent_sandbox.py#L177) |
| function | `resource_prefix` | `(*, address_space, cpu_seconds, open_files=…, file_size=…)` | ``prlimit`` foer bwrap: graenserne arves af workeren og kan ikke haeves derinde. | [src](../../../core/services/agent_sandbox.py#L189) |
| function | `spawn_in_sandbox` | `(command, *, pass_fds=…, stdout=…, stderr=…, address_space=…, cpu_seconds=…, extra_env=…, worker_files=…, rw_binds=…, chdir=…, stdin=…, file_size=…, mounts=…, pids_limit=…)` | Start ``command`` i sandboxen under en cgroup-scope med ``TasksMax=pids_limit`` (fork-bombe-vaern). | [src](../../../core/services/agent_sandbox.py#L201) |
| function | `sandbox_usable` | `()` | Smoketest: kan et trivielt program koere i sandboxen? (ja/nej, grund) | [src](../../../core/services/agent_sandbox.py#L220) |

## `core/services/agent_self_evaluation.py`
_Agent self-evaluation — track quality, adherence, goal progress (READ-ONLY)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_trace_kinds_since` | `(since, until)` | Ikke-strukturelle event-arter skrevet i vinduet. Self-safe: [] ved fejl. | [src](../../../core/services/agent_self_evaluation.py#L76) |
| function | `_previous_eval` | `()` | — | [src](../../../core/services/agent_self_evaluation.py#L97) |
| function | `_score_traces` | `(antal)` | Bredden af spor. Trapper frem for lineær, så små udsving ikke støjer. | [src](../../../core/services/agent_self_evaluation.py#L108) |
| function | `_score_novelty` | `(nu, foer)` | Gav dette slag noget ANDET end det forrige? | [src](../../../core/services/agent_self_evaluation.py#L119) |
| function | `evaluate_tick_quality` | `(*, tick_result)` | Score et slag på hvad det EFTERLOD — ikke på hvilken form det havde. | [src](../../../core/services/agent_self_evaluation.py#L139) |
| function | `tick_quality_summary` | `(*, days=…)` | Aggregate stats over recent evaluations. | [src](../../../core/services/agent_self_evaluation.py#L235) |
| function | `detect_stale_goals` | `(*, stale_days=…)` | Find active goals with no recent progress signal. | [src](../../../core/services/agent_self_evaluation.py#L282) |
| function | `stale_goals_section` | `()` | — | [src](../../../core/services/agent_self_evaluation.py#L305) |
| function | `decision_adherence_summary` | `()` | Compute adherence over ACTIVE behavioral decisions (the curated kind). | [src](../../../core/services/agent_self_evaluation.py#L318) |
| function | `_normalize_decision_directive` | `(value)` | — | [src](../../../core/services/agent_self_evaluation.py#L407) |
| function | `_duplicate_decision_groups` | `(decisions)` | — | [src](../../../core/services/agent_self_evaluation.py#L411) |
| function | `_adherence_recovery_plan` | `(*, score, low_decisions, duplicate_groups, unreviewed)` | — | [src](../../../core/services/agent_self_evaluation.py#L441) |
| function | `self_evaluation_section` | `()` | Compact awareness section combining all trackers. | [src](../../../core/services/agent_self_evaluation.py#L469) |
| function | `_exec_tick_quality_summary` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L546) |
| function | `_exec_detect_stale_goals` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L550) |
| function | `_exec_decision_adherence` | `(args)` | — | [src](../../../core/services/agent_self_evaluation.py#L555) |

## `core/services/agent_skill_distiller.py`
_Agent skill distillation — turns observed outcomes into principles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gather_recent_outcomes` | `(role, days=…)` | Pull recent runs/outcomes for this role from agent observations. | [src](../../../core/services/agent_skill_distiller.py#L24) |
| function | `_build_distill_prompt` | `(role, outcomes)` | — | [src](../../../core/services/agent_skill_distiller.py#L50) |
| function | `_parse_distillation` | `(text)` | — | [src](../../../core/services/agent_skill_distiller.py#L72) |
| function | `distill_skills_for_role` | `(role, *, days=…)` | Distill recent outcomes for a role into principles. Appends to skills.md. | [src](../../../core/services/agent_skill_distiller.py#L96) |
| function | `distill_all_known_roles` | `(*, days=…)` | — | [src](../../../core/services/agent_skill_distiller.py#L133) |

## `core/services/agent_skill_library.py`
_Agent Skill Library — per-role learned patterns + workflows._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_skills_path` | `(role)` | — | [src](../../../core/services/agent_skill_library.py#L48) |
| function | `_hash` | `(text)` | — | [src](../../../core/services/agent_skill_library.py#L53) |
| function | `get_skills` | `(role)` | Read the skills.md for a role. Returns {role, content, exists, path}. | [src](../../../core/services/agent_skill_library.py#L57) |
| function | `append_skill_observation` | `(*, role, section, observation, proposer=…)` | Append an observation to a section of the role's skills.md. | [src](../../../core/services/agent_skill_library.py#L74) |
| function | `_record_skill_mutation` | `(*, role, path, before, after, reason, proposer)` | — | [src](../../../core/services/agent_skill_library.py#L140) |
| function | `rollback_skill_mutation` | `(mutation_id)` | Restore a skills.md to its before-state from a logged mutation. | [src](../../../core/services/agent_skill_library.py#L180) |
| function | `list_skill_mutations` | `(*, role=…, limit=…)` | — | [src](../../../core/services/agent_skill_library.py#L217) |
| function | `list_known_roles` | `()` | Return all roles that have a skills.md file. | [src](../../../core/services/agent_skill_library.py#L242) |
| function | `_exec_get_agent_skills` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L255) |
| function | `_exec_append_skill` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L259) |
| function | `_exec_rollback_skill_mutation` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L268) |
| function | `_exec_list_skill_mutations` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L272) |
| function | `_exec_list_known_roles` | `(args)` | — | [src](../../../core/services/agent_skill_library.py#L282) |

## `core/services/agent_todos.py`
_Per-session todo tracker — Jarvis' working memory for "what am I doing right now"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `effective_status` | `(todo, now_iso)` | Udledt status: 'expired' hvis expires_at er passeret og todo'en ikke er | [src](../../../core/services/agent_todos.py#L38) |
| function | `_load_all` | `()` | — | [src](../../../core/services/agent_todos.py#L49) |
| function | `_save_all` | `(data)` | — | [src](../../../core/services/agent_todos.py#L60) |
| function | `_session_key` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L64) |
| function | `list_todos` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L68) |
| function | `set_todos` | `(session_id, items)` | Replace the entire todo list for this session. | [src](../../../core/services/agent_todos.py#L72) |
| function | `update_todo_status` | `(session_id, todo_id, new_status)` | — | [src](../../../core/services/agent_todos.py#L150) |
| function | `add_todo` | `(session_id, content)` | — | [src](../../../core/services/agent_todos.py#L196) |
| function | `create_from_plan` | `(*, plan_id, session_id, steps)` | Append pending todos for each plan step. Idempotent. | [src](../../../core/services/agent_todos.py#L215) |
| function | `_maybe_dismiss_orphaned_plan` | `(session_id, old_plan_ids, new_todos)` | Dismiss any awaiting_approval plan that no longer has linked todos. | [src](../../../core/services/agent_todos.py#L261) |
| function | `remove_todo` | `(session_id, todo_id)` | — | [src](../../../core/services/agent_todos.py#L307) |
| function | `add_cowork_todo` | `(content)` | Opret en todo i den delte cowork-session (Mission Control UI). | [src](../../../core/services/agent_todos.py#L333) |
| function | `_find_session_for_todo` | `(todo_id)` | — | [src](../../../core/services/agent_todos.py#L338) |
| function | `update_todo_status_anywhere` | `(todo_id, new_status)` | Skift status på en todo uanset hvilken session den lever i (cowork kender | [src](../../../core/services/agent_todos.py#L345) |
| function | `remove_todo_anywhere` | `(todo_id)` | Slet en todo uanset hvilken session den lever i. | [src](../../../core/services/agent_todos.py#L354) |
| function | `set_todo_expiry_anywhere` | `(todo_id, expires_at)` | Sæt/ryd udløbstidspunkt (ISO) på en todo uanset session. None = intet udløb. | [src](../../../core/services/agent_todos.py#L362) |
| function | `clear_session_todos` | `(session_id)` | — | [src](../../../core/services/agent_todos.py#L379) |
| function | `todos_prompt_section` | `(session_id)` | Format the active todo list as a prompt block, or None if empty. | [src](../../../core/services/agent_todos.py#L394) |

## `core/services/agent_transcript.py`
_Per-agent JSONL transcript persistence._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_agent_dir` | `(agent_id)` | — | [src](../../../core/services/agent_transcript.py#L32) |
| function | `_ensure_dir` | `(agent_id)` | — | [src](../../../core/services/agent_transcript.py#L36) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/agent_transcript.py#L42) |
| function | `write_event` | `(agent_id, entry)` | Append one event-line to the agent's transcript.jsonl. | [src](../../../core/services/agent_transcript.py#L50) |
| function | `write_meta` | `(agent_id, meta)` | Write (or overwrite) the agent's metadata sidecar. | [src](../../../core/services/agent_transcript.py#L67) |
| function | `write_lifecycle` | `(agent_id, event, *, note=…)` | Convenience: write a lifecycle event (spawned/started/completed/failed/...). | [src](../../../core/services/agent_transcript.py#L75) |
| function | `write_prompt` | `(agent_id, prompt, *, run_id=…)` | Write the prompt sent to the model. | [src](../../../core/services/agent_transcript.py#L83) |
| function | `write_result` | `(agent_id, text, *, run_id=…, input_tokens=…, output_tokens=…, cost_usd=…)` | Write the model's result. | [src](../../../core/services/agent_transcript.py#L92) |
| function | `write_tool_call` | `(agent_id, tool_call_id, name, arguments, *, run_id=…)` | Write a tool call the model requested. | [src](../../../core/services/agent_transcript.py#L106) |
| function | `write_tool_result` | `(agent_id, tool_call_id, content, *, run_id=…)` | Write the result of a tool execution. | [src](../../../core/services/agent_transcript.py#L118) |
| function | `write_failure` | `(agent_id, error, *, run_id=…)` | Write a failure/error event. | [src](../../../core/services/agent_transcript.py#L129) |
| function | `load_transcript` | `(agent_id)` | Load ALL lines from transcript.jsonl as a list of dicts. | [src](../../../core/services/agent_transcript.py#L142) |
| function | `load_meta` | `(agent_id)` | Load metadata sidecar, or None if missing. | [src](../../../core/services/agent_transcript.py#L151) |
| function | `load_events_by_kind` | `(agent_id, kind)` | Return only events of a specific kind (e.g. ``"tool_call"``). | [src](../../../core/services/agent_transcript.py#L160) |
| function | `list_transcripts` | `(limit=…)` | List available agent transcripts with metadata, newest-first. | [src](../../../core/services/agent_transcript.py#L169) |
| function | `prune_old_transcripts` | `(max_age_days=…)` | Remove transcript directories older than *max_age_days*. | [src](../../../core/services/agent_transcript.py#L193) |
| function | `write_sidechain` | `(agent_id, role, goal)` | Write a human-readable sidechain.md for quick inspection. | [src](../../../core/services/agent_transcript.py#L215) |
| function | `resume_from_transcript` | `(agent_id)` | Build a prompt-context dict from the transcript for agent resume. | [src](../../../core/services/agent_transcript.py#L240) |
| function | `list_agents` | `(limit=…)` | Seneste agenter med transkript, nyeste foerst. | [src](../../../core/services/agent_transcript.py#L303) |
| function | `read_events` | `(agent_id)` | Alle events for én agent. Tom liste hvis intet transkript. | [src](../../../core/services/agent_transcript.py#L326) |
| function | `summarize` | `(agent_id, *, max_arg_chars=…, max_result_chars=…)` | Hvad gjorde agenten, og hvad kom der ud af det? | [src](../../../core/services/agent_transcript.py#L343) |

## `core/services/agent_wake_intentions.py`
_Varig fortsaettelsesintention for en parent der venter paa agenter (B2, §6)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `wake_message` | `(*, condition, assignment_ids)` | Teksten der starter det vaagnede run. Maerket som fra systemet (staaende | [src](../../../core/services/agent_wake_intentions.py#L26) |
| function | `stage_wake` | `(*, task_id, session_id, owner_user_id, message, parent_run_id=…, wake_kind=…)` | Skriv intentionen. Idempotent paa `task_id`. Findes der allerede en anden | [src](../../../core/services/agent_wake_intentions.py#L39) |
| function | `cancel_pending_wake` | `(task_id, *, reason)` | Aflys en vaekning der endnu IKKE er startet. En allerede claimet (`running`) | [src](../../../core/services/agent_wake_intentions.py#L79) |

## `core/services/agent_worker_main.py`
_Entry for en sandboxet agent-worker (agent-contract-v1 C6b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RpcIO` | `` | LoopIO der sender hvert kald til brokeren og venter paa svaret. | [src](../../../core/services/agent_worker_main.py#L28) |
| method | `RpcIO.__init__` | `(self, sock, reader)` | — | [src](../../../core/services/agent_worker_main.py#L31) |
| method | `RpcIO.call` | `(self, op, **payload)` | — | [src](../../../core/services/agent_worker_main.py#L34) |
| method | `RpcIO.model` | `(self, *, messages, tools, requires_tools, provider, model)` | — | [src](../../../core/services/agent_worker_main.py#L48) |
| method | `RpcIO.tool` | `(self, tc)` | — | [src](../../../core/services/agent_worker_main.py#L53) |
| method | `RpcIO.after_tool` | `(self, tc, tool_out)` | — | [src](../../../core/services/agent_worker_main.py#L63) |
| method | `RpcIO.after_round` | `(self, rounds, tool_calls)` | — | [src](../../../core/services/agent_worker_main.py#L66) |
| function | `_apply_limits` | `(limits)` | Kun stramninger (en soft-graense under den arvede hard-graense); aldrig en haevning. | [src](../../../core/services/agent_worker_main.py#L71) |
| function | `main` | `(argv)` | — | [src](../../../core/services/agent_worker_main.py#L81) |

## `core/services/agent_worker_protocol.py`
_Wire-protokollen mellem serverens broker og en sandboxet agent-worker (C6b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ProtocolError` | `` | Misdannet eller for stor ramme. | [src](../../../core/services/agent_worker_protocol.py#L19) |
| class | `FrameTooLarge` | `` | — | [src](../../../core/services/agent_worker_protocol.py#L23) |
| function | `send` | `(sock, obj)` | — | [src](../../../core/services/agent_worker_protocol.py#L27) |
| class | `FrameReader` | `` | Laeser rammer ét ad gangen. ``read(timeout)`` giver ``None`` ved timeout, hæver ``EOFError`` | [src](../../../core/services/agent_worker_protocol.py#L34) |
| method | `FrameReader.__init__` | `(self, sock)` | — | [src](../../../core/services/agent_worker_protocol.py#L38) |
| method | `FrameReader.read` | `(self, timeout=…)` | — | [src](../../../core/services/agent_worker_protocol.py#L42) |

## `core/services/agent_worker_runner.py`
_Server-siden af en sandboxet agent-worker: spawn, broker og draeb (agent-contract-v1 C6b)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `WorkerError` | `` | Workeren fejlede eller blev draebt. ``code`` er stabil. | [src](../../../core/services/agent_worker_runner.py#L50) |
| method | `WorkerError.__init__` | `(self, code, detail=…)` | — | [src](../../../core/services/agent_worker_runner.py#L53) |
| function | `worker_mode_enabled` | `()` | Fail-closed: enhver laesefejl er ``False`` (= den eksisterende in-process-vej). | [src](../../../core/services/agent_worker_runner.py#L58) |
| function | `set_worker_mode` | `(enabled, *, role=…)` | At TAENDE er en ejerbeslutning; at slukke er altid tilladt. | [src](../../../core/services/agent_worker_runner.py#L68) |
| function | `_require_sandbox` | `()` | — | [src](../../../core/services/agent_worker_runner.py#L77) |
| function | `_kill_group` | `(proc)` | — | [src](../../../core/services/agent_worker_runner.py#L87) |
| function | `_safe` | `(obj)` | — | [src](../../../core/services/agent_worker_runner.py#L103) |
| class | `_Broker` | `` | Politik ved sømmen: hvad en worker maa faa serveren til at goere. | [src](../../../core/services/agent_worker_runner.py#L107) |
| method | `_Broker.__init__` | `(self, *, agent, run_id, prompt, tools_payload, provider, model, max_tool_calls, resume=…)` | — | [src](../../../core/services/agent_worker_runner.py#L110) |
| method | `_Broker.handle` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L124) |
| method | `_Broker._model` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L144) |
| method | `_Broker._adopt_live_run` | `(self)` | G: et failover har afloest runnet - bogfoering og logs foelger det nye forsoeg. | [src](../../../core/services/agent_worker_runner.py#L162) |
| method | `_Broker._model_text` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L167) |
| method | `_Broker._tool` | `(self, msg)` | — | [src](../../../core/services/agent_worker_runner.py#L180) |
| function | `_agent_cancelled` | `(agent_id)` | — | [src](../../../core/services/agent_worker_runner.py#L202) |
| function | `_save_logs` | `(agent, run_id, out_path, err_path)` | — | [src](../../../core/services/agent_worker_runner.py#L211) |
| function | `run_agent_in_worker` | `(*, agent, prompt, requires_tools, run_id, tools_payload=…, timeout_s=…, max_tool_calls=…, address_space=…, worker_files=…, worker_command=…, resume=…)` | Koer agentens tur i en sandboxet worker og returner resultatet i SAMME form som in-process-vejen. | [src](../../../core/services/agent_worker_runner.py#L229) |

## `core/services/agent_worktree_exec.py`
_Skrivning i et agent-worktree - KUN gennem en sandbox (agent-contract-v1 C5b, spec 8.1 og 12.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ExecError` | `` | Kommandoen blev afvist foer den koerte (stabil ``code``). | [src](../../../core/services/agent_worktree_exec.py#L51) |
| method | `ExecError.__init__` | `(self, code, detail=…)` | — | [src](../../../core/services/agent_worktree_exec.py#L54) |
| function | `_active_worktree` | `(worktree_id)` | — | [src](../../../core/services/agent_worktree_exec.py#L59) |
| function | `_clip` | `(data)` | — | [src](../../../core/services/agent_worktree_exec.py#L72) |
| function | `_run` | `(wt, command, *, timeout_s, stdin_bytes=…, with_git=…)` | — | [src](../../../core/services/agent_worktree_exec.py#L77) |
| function | `run_in_worktree` | `(*, worktree_id, command, timeout_s=…)` | Koer en shell-kommando med worktree'et som /work. Kaster ``ExecError`` hvis den afvises. | [src](../../../core/services/agent_worktree_exec.py#L112) |
| function | `write_file_in_worktree` | `(*, worktree_id, path, content)` | Skriv en fil (relativ sti) i worktree'et. Stien loeses INDE i sandboxen og afvises hvis den | [src](../../../core/services/agent_worktree_exec.py#L120) |

## `core/services/agent_worktree_git.py`
_Git-operationer for agent-worktrees (agent-contract-v1 C5a, spec 8.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `GitError` | `` | — | [src](../../../core/services/agent_worktree_git.py#L26) |
| method | `GitError.__init__` | `(self, detail, *, returncode=…)` | — | [src](../../../core/services/agent_worktree_git.py#L27) |
| function | `_env` | `(extra=…)` | — | [src](../../../core/services/agent_worktree_git.py#L32) |
| function | `run_git` | `(args, *, cwd=…, env=…, timeout=…, check=…, input_bytes=…)` | — | [src](../../../core/services/agent_worktree_git.py#L40) |
| function | `safe_ref` | `(ref)` | — | [src](../../../core/services/agent_worktree_git.py#L53) |
| function | `safe_name` | `(name, what=…)` | — | [src](../../../core/services/agent_worktree_git.py#L60) |
| function | `validate_repo` | `(path, allowed_roots)` | Returner repoets toplevel (realpath) hvis det ligger under en tilladt rod og er et almindeligt | [src](../../../core/services/agent_worktree_git.py#L66) |
| function | `resolve_commit` | `(repo, ref=…)` | — | [src](../../../core/services/agent_worktree_git.py#L83) |
| function | `read_gitdir` | `(repo, path)` | Hovedrepoets administrationsmappe for et NYOPRETTET worktree, laest fra dets ``.git``-fil | [src](../../../core/services/agent_worktree_git.py#L88) |
| function | `add_worktree` | `(repo, path, branch, base_commit)` | — | [src](../../../core/services/agent_worktree_git.py#L101) |
| function | `_wt_env` | `(gitdir, path)` | — | [src](../../../core/services/agent_worktree_git.py#L106) |
| function | `stage_all` | `(gitdir, path)` | — | [src](../../../core/services/agent_worktree_git.py#L110) |
| function | `diff_against` | `(gitdir, path, base_commit)` | Hele agentens aendring ift. basen - ogsaa nye og slettede filer og commits (binaer-sikker). | [src](../../../core/services/agent_worktree_git.py#L114) |
| function | `changed_files` | `(gitdir, path, base_commit)` | — | [src](../../../core/services/agent_worktree_git.py#L121) |
| function | `commits_since` | `(gitdir, path, base_commit)` | — | [src](../../../core/services/agent_worktree_git.py#L129) |
| function | `make_bundle` | `(repo, branch, base_commit, dest)` | Bundle af agentens commits (``base..branch``). ``False`` naar der ingen commits er. | [src](../../../core/services/agent_worktree_git.py#L134) |
| function | `remove_worktree` | `(repo, path, branch)` | Fjern worktree + branch. Idempotent: et allerede fjernet worktree er ikke en fejl. | [src](../../../core/services/agent_worktree_git.py#L143) |
| function | `tree_size` | `(path)` | Samlet filstoerrelse (bytes) uden at foelge symlinks ud af traeet. | [src](../../../core/services/agent_worktree_git.py#L157) |
| function | `path_is_inside` | `(path, root)` | — | [src](../../../core/services/agent_worktree_git.py#L169) |
| function | `ensure_dir` | `(path)` | — | [src](../../../core/services/agent_worktree_git.py#L174) |
| function | `current_head` | `(repo)` | — | [src](../../../core/services/agent_worktree_git.py#L186) |
| function | `ref_exists` | `(repo, ref)` | — | [src](../../../core/services/agent_worktree_git.py#L190) |
| function | `commit_worktree_tree` | `(gitdir, path, base_commit, message)` | Skriv agentens samlede arbejdstilstand som ÉT commit ovenpaa basen (server-side, med det gemte gitdir). | [src](../../../core/services/agent_worktree_git.py#L194) |
| function | `merge_tree` | `(repo, ours, theirs)` | ``git merge-tree --write-tree``: (tree-oid, []) ved ren fletning, (None, konfliktfiler) ved konflikt. | [src](../../../core/services/agent_worktree_git.py#L203) |
| function | `commit_tree` | `(repo, tree, parents, message)` | — | [src](../../../core/services/agent_worktree_git.py#L216) |
| function | `create_ref` | `(repo, ref, oid)` | Opret ``ref`` -> ``oid`` KUN hvis den ikke findes (old-value = nul): en eksisterende gren overskrives aldrig. | [src](../../../core/services/agent_worktree_git.py#L223) |
| function | `set_ref` | `(repo, ref, new, old)` | — | [src](../../../core/services/agent_worktree_git.py#L228) |

## `core/services/agent_worktree_gitdir.py`
_Agentens EGEN git-administrationsmappe (agent-contract-v1 leverance C, hul 1; spec 8.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `gitdir_path` | `(worktree_path)` | Den private gitdir ligger ved siden af worktree'et (altsaa UDEN for det der mountes som /work). | [src](../../../core/services/agent_worktree_gitdir.py#L57) |
| function | `work_ref` | `(assignment_id)` | — | [src](../../../core/services/agent_worktree_gitdir.py#L62) |
| function | `_objects_chain` | `(repo)` | Hovedrepoets objektmappe + dens egne alternates (kaeden), som absolutte stier der findes. | [src](../../../core/services/agent_worktree_gitdir.py#L66) |
| function | `create` | `(repo, path, branch, base_commit)` | Opret den private gitdir for et NYT worktree (foer agenten har roert noget). Returnerer stien. | [src](../../../core/services/agent_worktree_gitdir.py#L85) |
| function | `sandbox_mounts` | `(repo, path)` | Mounts til ``agent_sandbox`` der giver agenten git i sin egen gitdir. ``None`` hvis worktree'et | [src](../../../core/services/agent_worktree_gitdir.py#L103) |
| function | `sandbox_env` | `()` | — | [src](../../../core/services/agent_worktree_gitdir.py#L120) |
| function | `import_agent_work` | `(repo, path, branch, assignment_id)` | Hent agentens commits ind i hovedrepoet som ``refs/agent-work/<assignment>`` og returner tippen | [src](../../../core/services/agent_worktree_gitdir.py#L128) |
| function | `commits_since` | `(repo, base_commit, assignment_id)` | Agentens importerede commits ``base..refs/agent-work/<id>`` (tom hvis intet er importeret). | [src](../../../core/services/agent_worktree_gitdir.py#L148) |
| function | `remove` | `(repo, path)` | Fjern den private gitdir og det importerede ref. Idempotent. | [src](../../../core/services/agent_worktree_gitdir.py#L156) |

## `core/services/agent_worktrees.py`
_Worktrees til skrivende kodeagenter (agent-contract-v1 C5a, spec 8.1 og 12.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_worktree_tables` | `(conn)` | — | [src](../../../core/services/agent_worktrees.py#L50) |
| function | `worktree_root` | `()` | — | [src](../../../core/services/agent_worktrees.py#L80) |
| function | `allowed_workspace_roots` | `()` | — | [src](../../../core/services/agent_worktrees.py#L84) |
| function | `_iso` | `(dt)` | — | [src](../../../core/services/agent_worktrees.py#L89) |
| function | `_parse` | `(value)` | — | [src](../../../core/services/agent_worktrees.py#L93) |
| function | `_estimate_bytes` | `(repo, commit)` | — | [src](../../../core/services/agent_worktrees.py#L97) |
| function | `_free_floor` | `(path)` | — | [src](../../../core/services/agent_worktrees.py#L107) |
| function | `_holding_bytes` | `(conn, target)` | — | [src](../../../core/services/agent_worktrees.py#L112) |
| function | `_quota` | `(conn, target)` | Taellingerne paa en GIVEN forbindelse. VIGTIGT: ``connect()`` ruller en aaben transaktion tilbage | [src](../../../core/services/agent_worktrees.py#L118) |
| function | `quota_status` | `(*, target=…)` | — | [src](../../../core/services/agent_worktrees.py#L130) |
| function | `reserve` | `(*, owner_user_id, assignment_id, repo_path, base_ref=…, target=…)` | Reserver plads og en plads i kvoten ATOMISK. Intet er oprettet paa disk endnu. | [src](../../../core/services/agent_worktrees.py#L136) |
| function | `get` | `(*, worktree_id)` | — | [src](../../../core/services/agent_worktrees.py#L186) |
| function | `get_for_assignment` | `(*, owner_user_id, assignment_id)` | — | [src](../../../core/services/agent_worktrees.py#L190) |
| function | `_set` | `(worktree_id, **fields)` | — | [src](../../../core/services/agent_worktrees.py#L195) |
| function | `materialize` | `(*, worktree_id)` | Opret selve git-worktree'et. Alt-eller-intet: ved fejl ryddes det halve, og reservationen frigives. | [src](../../../core/services/agent_worktrees.py#L203) |
| function | `_discard_partial` | `(wt)` | — | [src](../../../core/services/agent_worktrees.py#L226) |
| function | `provision` | `(*, owner_user_id, assignment_id, repo_path, base_ref=…, target=…)` | reserve + materialize som ét skridt; ved fejl er intet efterladt og reservationen frigivet. | [src](../../../core/services/agent_worktrees.py#L235) |
| function | `writes_allowed` | `(*, worktree_id)` | — | [src](../../../core/services/agent_worktrees.py#L245) |
| function | `check_growth` | `(*, worktree_id)` | Maal diskforbruget. Over kvoten (eller for lidt ledig plads) stopper NYE skrivninger og bevarer | [src](../../../core/services/agent_worktrees.py#L250) |
| function | `snapshot_for_assignment` | `(*, assignment_id)` | Ved terminalt udfald: gem diff, aendrede filer og commits som artefakter, og bevar worktree'et | [src](../../../core/services/agent_worktrees.py#L266) |
| function | `decide` | `(*, owner_user_id, worktree_id, decision)` | Registrer ejerens/approverens beslutning om det bevarede arbejde. Selve integrationen i hovedgrenen | [src](../../../core/services/agent_worktrees.py#L311) |
| function | `_verified_remove` | `(wt)` | Fjern et worktree - KUN hvis posten, ejeren og stien hænger sammen. Returnerer om det lykkedes. | [src](../../../core/services/agent_worktrees.py#L326) |
| function | `_archive` | `(wt)` | Pak diff + commits (bundle) i checksumverificerede artefakter foer fysisk oprydning. | [src](../../../core/services/agent_worktrees.py#L348) |
| function | `sweep` | `(*, now=…)` | Retentionrunde. Afgjort + 7 dage -> fjernes. Ubehandlet: opmaerksomhed efter 14 dage, arkiveres | [src](../../../core/services/agent_worktrees.py#L371) |
| function | `reconcile` | `()` | Markér aktive/bevarede poster hvis worktree er forsvundet fra disken som ``unknown`` (ikke 'removed'). | [src](../../../core/services/agent_worktrees.py#L404) |

## `core/services/agentic_checkpoints.py`
_Durable checkpoints for visible agentic loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/agentic_checkpoints.py#L21) |
| function | `_load` | `()` | — | [src](../../../core/services/agentic_checkpoints.py#L25) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_checkpoints.py#L32) |
| function | `_tool_name` | `(tool_call)` | — | [src](../../../core/services/agentic_checkpoints.py#L43) |
| function | `_compact_tool_call` | `(tool_call)` | — | [src](../../../core/services/agentic_checkpoints.py#L50) |
| function | `_compact_result` | `(result)` | — | [src](../../../core/services/agentic_checkpoints.py#L60) |
| function | `compact_exchange` | `(exchange)` | — | [src](../../../core/services/agentic_checkpoints.py#L68) |
| function | `save_checkpoint` | `(*, run_id, session_id, user_message, provider, model, round_index, phase, exchanges, partial_text=…, exit_reason=…)` | — | [src](../../../core/services/agentic_checkpoints.py#L78) |
| function | `latest_for_session` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L113) |
| function | `clear_run` | `(run_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L124) |
| function | `clear_session` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L133) |
| function | `checkpoint_prompt_section` | `(session_id)` | — | [src](../../../core/services/agentic_checkpoints.py#L146) |

## `core/services/agentic_tool_cache.py`
_Small durable cache for read-only agentic tool results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/agentic_tool_cache.py#L31) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_tool_cache.py#L38) |
| function | `_file_fingerprint` | `(arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L45) |
| function | `_signature` | `(tool_name, arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L57) |
| function | `_is_stale` | `(rec)` | True hvis posten er ældre end _MAX_AGE_SECONDS — eller uden brugbart tidsstempel. | [src](../../../core/services/agentic_tool_cache.py#L78) |
| function | `get_cached_result` | `(tool_name, arguments)` | — | [src](../../../core/services/agentic_tool_cache.py#L92) |
| function | `store_result` | `(*, tool_name, arguments, result_text, status)` | — | [src](../../../core/services/agentic_tool_cache.py#L106) |

## `core/services/agentic_working_conclusions.py`
_Durable working conclusions for interrupted agentic runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/agentic_working_conclusions.py#L13) |
| function | `_save` | `(records)` | — | [src](../../../core/services/agentic_working_conclusions.py#L20) |
| function | `update_working_conclusion` | `(*, run_id, session_id, user_message, round_index, observation=…, next_step=…)` | — | [src](../../../core/services/agentic_working_conclusions.py#L27) |
| function | `latest_for_session` | `(session_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L55) |
| function | `clear_run` | `(run_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L66) |
| function | `working_conclusion_prompt_section` | `(session_id)` | — | [src](../../../core/services/agentic_working_conclusions.py#L73) |
| function | `build_round_observation` | `(*, text, tool_names, result_texts)` | — | [src](../../../core/services/agentic_working_conclusions.py#L90) |

## `core/services/agents.py`
_Agents-cluster — gør multi-agent-systemerne synlige i Den Intelligente Central: agent-pool_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe` | `(nerve, data)` | — | [src](../../../core/services/agents.py#L15) |
| function | `note_agent_spawn` | `(agent_id, role, *, parent=…, council_id=…, mode=…)` | En agent blev spawnet (pool/swarm). Metadata-only. | [src](../../../core/services/agents.py#L23) |
| function | `note_agent_error` | `(agent_id, error, **data)` | En agent fejlede → observe (synlig). | [src](../../../core/services/agents.py#L33) |
| function | `note_agent_result` | `(agent_id, status, *, tokens_in=…, tokens_out=…, cost_usd=…, duration_ms=…, tool_calls=…, role=…, provider=…, model=…, **data)` | En agent-dispatch afsluttede (succes ELLER fejl) → observe robusthedskonvolut | [src](../../../core/services/agents.py#L39) |
| function | `note_agent_blocked` | `(agent_id, status=…, *, reason=…, role=…, **data)` | En agent blev BLOKERET / mangler kontekst (typet ikke-fejl) → distinkt observe. | [src](../../../core/services/agents.py#L78) |
| function | `note_council` | `(topic, *, rounds=…, deadlocked=…, escalated=…, recruited=…)` | En council-deliberation kørte → observe udfald (rounds/deadlock/witness-escalation/ | [src](../../../core/services/agents.py#L91) |
| function | `agents_summary` | `(*, window=…)` | Read-only: nylig agent/council-aktivitet (til MC). Self-safe. | [src](../../../core/services/agents.py#L102) |
| function | `_build_roster` | `(*, window=…)` | Full agent roster: every unique (provider, model) from the cheap-lane pool as a | [src](../../../core/services/agents.py#L136) |
| function | `_iso` | `(ts)` | Epoch seconds → ISO-8601 UTC string; "" for a missing/zero timestamp. | [src](../../../core/services/agents.py#L221) |

## `core/services/agreement_streak.py`
_Agreement-streak substrate trigger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_opening_is_agreement` | `(text)` | Return the matched phrase if the text opens with agreement, else None. | [src](../../../core/services/agreement_streak.py#L46) |
| function | `detect_agreement_streak` | `(*, lookback=…, threshold=…)` | Pull last N assistant messages, return substrate dict if streak detected. | [src](../../../core/services/agreement_streak.py#L61) |
| function | `build_agreement_streak_section` | `()` | Prompt section — substrate, ikke domm. | [src](../../../core/services/agreement_streak.py#L112) |

## `core/services/alarm_ud.py`
_Én vej ud for driftsalarmer — gennem routeren, ikke direkte til telefonen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `send_alert` | `(*, titel, tekst, slags=…, importance=…, session_id=…)` | Send en driftsalarm gennem routeren. Returnerer True hvis den blev leveret. | [src](../../../core/services/alarm_ud.py#L42) |

## `core/services/ambient_presence.py`
_Ambient presence — Jarvis' egen tilstand, synlig for ham selv._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `emit_ambient_signal` | `(*, kind, detail=…, priority=…)` | Emit a quiet ambient presence signal. Rate-limited to 30 min. | [src](../../../core/services/ambient_presence.py#L63) |
| function | `emit_presence_rhythm` | `()` | Quiet hourly pulse — 'still here'. Separate rate limit from state signals. | [src](../../../core/services/ambient_presence.py#L95) |
| function | `emit_state_shift` | `(from_phase, to_phase)` | Signal a genuine phase transition with a descriptive message. | [src](../../../core/services/ambient_presence.py#L114) |
| function | `maybe_emit_phase_signal` | `(phase)` | Called from heartbeat when life phase is determined. | [src](../../../core/services/ambient_presence.py#L123) |
| function | `emit_insight_signal` | `(insight)` | Called when a dream is confirmed or a value crystallizes. | [src](../../../core/services/ambient_presence.py#L154) |

## `core/services/ambient_sound_daemon.py`
_Ambient Sound daemon — Layer 6½: background acoustic context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_ambient_sound_daemon` | `()` | Sample ambient audio level and classify. Runs 4x/day. | [src](../../../core/services/ambient_sound_daemon.py#L44) |
| function | `_capture_sample` | `(*, save_wav=…)` | Record 10 seconds of audio, classify, optionally save to temp WAV. | [src](../../../core/services/ambient_sound_daemon.py#L117) |
| function | `_save_wav` | `(samples)` | Write float32 mono samples to a temp 16-bit PCM WAV. Returns path or None. | [src](../../../core/services/ambient_sound_daemon.py#L154) |
| function | `_transcribe_sample` | `(wav_path)` | Transcribe a WAV via HF Whisper. Returns empty string on failure. | [src](../../../core/services/ambient_sound_daemon.py#L173) |
| function | `_ambient_transcribe_enabled` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L188) |
| function | `_classify` | `(mean, std, peak=…)` | Classify amplitude stats into acoustic category. No content analysis. | [src](../../../core/services/ambient_sound_daemon.py#L197) |
| function | `_store_sample` | `(sample, now)` | — | [src](../../../core/services/ambient_sound_daemon.py#L225) |
| function | `_archive_sensory` | `(sample, now)` | Mirror every ambient sample into Sansernes Arkiv. Silent on failure. | [src](../../../core/services/ambient_sound_daemon.py#L266) |
| function | `get_latest_ambient_sound_for_prompt` | `()` | Return a nuanced description of recent ambient sound for prompt injection. | [src](../../../core/services/ambient_sound_daemon.py#L298) |
| function | `build_ambient_sound_surface` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L335) |
| function | `_interpret_sound` | `(*, category, amplitude_mean, amplitude_std, now)` | Generate a nuanced Danish description from acoustic metadata via LLM. | [src](../../../core/services/ambient_sound_daemon.py#L372) |
| function | `_experiment_enabled` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L399) |
| function | `count_music_samples_last_hours` | `(hours=…)` | Return (music_count, total_count) for samples in the last `hours` hours. | [src](../../../core/services/ambient_sound_daemon.py#L408) |
| function | `_select_music_influence_phrase` | `(*, ratio)` | 3-tier rotating phrase based on music-to-total ratio. | [src](../../../core/services/ambient_sound_daemon.py#L445) |
| function | `get_music_accumulator_for_prompt` | `()` | Return prompt fragment if music threshold met, else empty string. | [src](../../../core/services/ambient_sound_daemon.py#L457) |
| function | `_state` | `()` | — | [src](../../../core/services/ambient_sound_daemon.py#L480) |
| function | `_parse_iso` | `(s)` | — | [src](../../../core/services/ambient_sound_daemon.py#L485) |

## `core/services/anthropic_identity.py`
_Build Jarvis identity prefix from a workspace directory._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_signature` | `(workspace_dir)` | — | [src](../../../core/services/anthropic_identity.py#L20) |
| function | `build_identity_prefix` | `(workspace_dir)` | Return concatenated identity files for this workspace, or empty string. | [src](../../../core/services/anthropic_identity.py#L32) |
| function | `invalidate_cache` | `()` | — | [src](../../../core/services/anthropic_identity.py#L62) |

## `core/services/anthropic_sse_emitter.py`
_Anthropic Messages API SSE state machine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AnthropicSSEEmitter` | `` | Stateful emitter for one streamed message. | [src](../../../core/services/anthropic_sse_emitter.py#L13) |
| method | `AnthropicSSEEmitter.__init__` | `(self, *, message_id, model)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L25) |
| method | `AnthropicSSEEmitter._format` | `(event, data)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L35) |
| method | `AnthropicSSEEmitter.begin_message` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L38) |
| method | `AnthropicSSEEmitter._close_open_block` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L56) |
| method | `AnthropicSSEEmitter._open_text_block` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L67) |
| method | `AnthropicSSEEmitter.text_delta` | `(self, text)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L78) |
| method | `AnthropicSSEEmitter.tool_use_start` | `(self, tool_call_id, name)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L90) |
| method | `AnthropicSSEEmitter.tool_use_input_delta` | `(self, partial_json)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L107) |
| method | `AnthropicSSEEmitter.tool_result_block` | `(self, *, tool_use_id, status, content, is_error=…)` | Emit et første-klasses tool_result som content-blok (kanonisk wire-form). | [src](../../../core/services/anthropic_sse_emitter.py#L116) |
| method | `AnthropicSSEEmitter.end_message` | `(self, *, stop_reason, output_tokens=…)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L137) |
| method | `AnthropicSSEEmitter.ping` | `(self)` | — | [src](../../../core/services/anthropic_sse_emitter.py#L149) |
| method | `AnthropicSSEEmitter.error` | `(self, message)` | Emit a graceful error: close any open block, emit error stop. | [src](../../../core/services/anthropic_sse_emitter.py#L152) |

## `core/services/anthropic_translator.py`
_Translate between Anthropic Messages API format and Ollama /api/chat format._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `translate_request_to_ollama` | `(anthropic_body, *, identity_prefix, backend_model)` | Build an Ollama /api/chat payload from an Anthropic Messages request. | [src](../../../core/services/anthropic_translator.py#L13) |
| function | `_translate_message` | `(msg)` | Translate a single Anthropic message into 1-N Ollama messages. | [src](../../../core/services/anthropic_translator.py#L61) |
| function | `_stringify_tool_result_content` | `(content)` | Anthropic tool_result content can be string or list of blocks. | [src](../../../core/services/anthropic_translator.py#L130) |
| function | `drive_emitter_from_ollama_chunks` | `(emitter, chunks)` | Drive an AnthropicSSEEmitter from a stream of Ollama chat chunks. | [src](../../../core/services/anthropic_translator.py#L153) |
| function | `build_non_streaming_response` | `(*, message_id, model, text, tool_calls)` | Build the final Anthropic Messages response (non-streaming). | [src](../../../core/services/anthropic_translator.py#L200) |

## `core/services/anticipatory_action_daemon.py`
_Anticipatory Action Daemon — predict + pre-act._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L39) |
| function | `_load` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L43) |
| function | `_save` | `(data)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L60) |
| function | `_should_recompute` | `(data, now)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L72) |
| function | `_gather_contact_hours` | `()` | Collect contact hours from recent visible runs. | [src](../../../core/services/anticipatory_action_daemon.py#L83) |
| function | `_compute_peak_hours` | `(hour_counts)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L104) |
| function | `recompute_patterns` | `()` | Rebuild pattern signature from recent data. | [src](../../../core/services/anticipatory_action_daemon.py#L129) |
| function | `_local_now` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L141) |
| function | `_minutes_until_hour` | `(now_local, target_hour)` | Returns minutes until next occurrence of target_hour (always in [0, 1440)). | [src](../../../core/services/anticipatory_action_daemon.py#L146) |
| function | `_maybe_emit_anticipation` | `(peaks)` | Emit signals for peaks coming up within the anticipation window. | [src](../../../core/services/anticipatory_action_daemon.py#L156) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L184) |
| function | `build_anticipatory_action_surface` | `()` | — | [src](../../../core/services/anticipatory_action_daemon.py#L196) |
| function | `_surface_summary` | `(peaks, upcoming)` | — | [src](../../../core/services/anticipatory_action_daemon.py#L223) |
| function | `build_anticipatory_action_prompt_section` | `()` | Surface imminent anticipated contact. | [src](../../../core/services/anticipatory_action_daemon.py#L235) |

## `core/services/anticipatory_context.py`
_Anticipatory Context — predict what the user will likely ask about next._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `predict_next_context` | `(*, recent_topics=…, hour=…, idle_hours=…, last_session_topic=…)` | Predict the most likely next context. | [src](../../../core/services/anticipatory_context.py#L17) |
| function | `build_anticipatory_context_surface` | `()` | — | [src](../../../core/services/anticipatory_context.py#L76) |

## `core/services/api_connection_nerve.py`
_API-forbindelses-nerve — Jarvis mærker hvem/hvad der forbinder til hans API._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/api_connection_nerve.py#L41) |
| function | `record` | `(*, ip, method, path, status, latency_ms, user_id=…, session_id=…, error=…)` | Registrér én API-request (metadata-only). Billig, låst, kaster ALDRIG. | [src](../../../core/services/api_connection_nerve.py#L45) |
| function | `_maybe_flush_async` | `()` | Throttlet baggrunds-flush (api-proces ejer bufferen). Spawner en daemon-tråd så request- | [src](../../../core/services/api_connection_nerve.py#L99) |
| function | `_drain` | `()` | Snapshot dirty presence-deltas + log-buffer under lås; nulstil buffer + dirty-flag. | [src](../../../core/services/api_connection_nerve.py#L129) |
| function | `flush` | `()` | Batch-flush presence + log til DB (cadence). Self-safe. | [src](../../../core/services/api_connection_nerve.py#L147) |
| function | `retention_sweep` | `()` | GDPR-retention (cadence): anonymisér IP > 48t → /24, slet gammel log, prune presence. | [src](../../../core/services/api_connection_nerve.py#L158) |
| function | `presence_view` | `(*, active_within_s=…, limit=…)` | Hvem er forbundet til API'et? Fletter live in-memory + persistent DB. Self-safe. | [src](../../../core/services/api_connection_nerve.py#L166) |

## `core/services/apophenia_guard.py`
_Apophenia Guard — pattern skeptic that validates before elevation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_generate_assessment_rationale` | `(*, status, observation_count, adjusted_confidence, competitor_count, confounder_count)` | Generate a brief Danish explanation of the assessment. Falls back to empty string. | [src](../../../core/services/apophenia_guard.py#L21) |
| function | `assess_pattern` | `(*, observation_count, base_confidence, competing_explanations=…, confounders=…, include_rationale=…)` | Assess whether a pattern should be elevated or rejected. | [src](../../../core/services/apophenia_guard.py#L48) |
| function | `build_apophenia_guard_surface` | `()` | — | [src](../../../core/services/apophenia_guard.py#L120) |

