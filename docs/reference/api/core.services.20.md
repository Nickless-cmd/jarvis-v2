# `core.services.20` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/research_ledger.py`
_Research-runnet synligt i session-ledgeren (spec Fase A4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taellere` | `()` | — | [src](../../../core/services/research_ledger.py#L42) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/research_ledger.py#L46) |
| function | `record_research_event` | `(session_id, *, event_id, event, payload=…)` | Skriv én research-hændelse i session-ledgeren. Kaster aldrig. | [src](../../../core/services/research_ledger.py#L51) |
| function | `record_run_started` | `(session_id, *, run_id, tier, query)` | Runnet er startet: tier og den oprindelige forespørgsel. | [src](../../../core/services/research_ledger.py#L96) |
| function | `record_run_completed` | `(session_id, *, run_id, sources, quality, timed_out, tool_calls=…)` | Runnet er slut: hvad det blev — kilder, kvalitetsdom, timeout, forbrug. | [src](../../../core/services/research_ledger.py#L106) |

## `core/services/research_orchestrator.py`
_Adaptive research coordinator around the existing visible and agent runtimes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_event` | `(kind, payload)` | — | [src](../../../core/services/research_orchestrator.py#L26) |
| function | `_setting` | `(name, default)` | — | [src](../../../core/services/research_orchestrator.py#L30) |
| function | `_facets` | `(message)` | De emneord planlægningen deler beskeden i — og som gaten måler dækning imod. | [src](../../../core/services/research_orchestrator.py#L44) |
| function | `_delta_text` | `(frame)` | Træk syntese-teksten ud af en `delta`-frame. Andre frames giver ''. | [src](../../../core/services/research_orchestrator.py#L52) |
| function | `_plan` | `(message, max_tasks)` | — | [src](../../../core/services/research_orchestrator.py#L74) |
| function | `_parse_plan` | `(text, max_tasks)` | Læs plannerens JSON til en ResearchTask-liste. Defensiv: [] ved mindste tvivl. | [src](../../../core/services/research_orchestrator.py#L105) |
| function | `_llm_plan` | `(message, max_tasks, facets)` | Fase C1: bed en billig model om delopgaver. None = kunne ikke → regex. | [src](../../../core/services/research_orchestrator.py#L148) |
| function | `_plan_tasks` | `(message, max_tasks, *, planner_enabled)` | Fase C1: LLM-planlægger med regex-fallback. | [src](../../../core/services/research_orchestrator.py#L173) |
| function | `_tool_calls_used` | `(run_id)` | Observerede værktøjskald i runnet. Defensiv: 0 hvis tællingen ikke kan læses. | [src](../../../core/services/research_orchestrator.py#L189) |
| function | `_clean_text` | `(value)` | — | [src](../../../core/services/research_orchestrator.py#L200) |
| function | `_confidence` | `(value)` | — | [src](../../../core/services/research_orchestrator.py#L204) |
| function | `_finding_from_text` | `(text, task_ordinal)` | Sidste udkast: hele teksten bliver ét fund med de URLs den bærer. | [src](../../../core/services/research_orchestrator.py#L209) |
| function | `_parse_findings` | `(text, task_ordinal)` | Fase B2: worker-svaret → `ResearchFinding`. | [src](../../../core/services/research_orchestrator.py#L226) |
| function | `_gap_objective` | `(query, findings)` | Fase B3: critic-opgaven — hvad MANGLER der, givet de fundne påstande. | [src](../../../core/services/research_orchestrator.py#L300) |
| function | `_parse_gaps` | `(text)` | Fase B3: critic-svaret → korte gap-linjer. Defensiv hele vejen. | [src](../../../core/services/research_orchestrator.py#L317) |
| function | `_evidence_block` | `(texts, sources, findings, gaps=…)` | Evidens til syntesen — med en KANONISK nummereret kilde-liste. | [src](../../../core/services/research_orchestrator.py#L351) |
| function | `_topup_plan` | `(run_id, tasks, policy)` | Fase B1: hvilke tracks skal styrkes — og med hvad? | [src](../../../core/services/research_orchestrator.py#L389) |
| function | `_evaluate_quality` | `(run_id, query, report, policy)` | Fase A1: kobl kvalitetsgaten på den faktiske rapport. | [src](../../../core/services/research_orchestrator.py#L435) |
| function | `_judge_prompt` | `(query, report, sources, findings, gaps)` | Binær rubric — kort nok til en billig model, konkret nok til at være falsificerbar. | [src](../../../core/services/research_orchestrator.py#L485) |
| function | `_parse_verdict` | `(text)` | Dommerens svar → {"verdict", "criteria", "reason"}. None hvis uafgørbart. | [src](../../../core/services/research_orchestrator.py#L509) |
| function | `_judge_quality` | `(run_id, query, report, gaps=…)` | Kør dommeren i en tråd, så event-loopet ikke blokeres. Fejler altid blødt. | [src](../../../core/services/research_orchestrator.py#L547) |
| function | `_default_worker_sync` | `(*, task, run_id, skill_instructions, max_turns=…, budget_tokens=…)` | — | [src](../../../core/services/research_orchestrator.py#L579) |
| function | `_run_worker` | `(worker_factory, *, task, run_id, skill_instructions, max_turns=…, budget_tokens=…)` | Kør én worker gennem factory'en. | [src](../../../core/services/research_orchestrator.py#L620) |
| function | `stream_research_run` | `(*, message, original_query=…, session_id, visible_run_id=…, decision=…, visible_factory=…, worker_factory=…, orchestrator_enabled=…, **visible_kwargs)` | — | [src](../../../core/services/research_orchestrator.py#L646) |
| function | `research_enabled` | `()` | — | [src](../../../core/services/research_orchestrator.py#L949) |

## `core/services/research_prompt_context.py`
_Request-scoped research instructions consumed by prompt assembly surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_PromptResearch` | `` | — | [src](../../../core/services/research_prompt_context.py#L13) |
| function | `research_context` | `(policy, *, skill_instructions=…, evidence=…)` | — | [src](../../../core/services/research_prompt_context.py#L23) |
| function | `research_prompt_section` | `()` | — | [src](../../../core/services/research_prompt_context.py#L36) |

## `core/services/research_quality.py`
_Deterministic, inspectable quality gates for research synthesis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchQualityResult` | `` | — | [src](../../../core/services/research_quality.py#L13) |
| function | `evaluate_research_report` | `(report, sources, requested_facets, *, contradictions=…, requires_freshness=…, tool_calls=…, max_tool_calls=…)` | — | [src](../../../core/services/research_quality.py#L19) |

## `core/services/research_router.py`
_Conservative and explainable inline/orchestrated research routing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_effort` | `(independent)` | Indsatsen for N uafhængige signaler — klippet til tabellens rækker. | [src](../../../core/services/research_router.py#L37) |
| function | `classify_research` | `(message, *, attachment_count=…, policy=…)` | — | [src](../../../core/services/research_router.py#L42) |

## `core/services/research_store.py`
_Durable SQLite state for research runs, tasks, sources, and steering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchStateError` | `` | — | [src](../../../core/services/research_store.py#L17) |
| function | `_now` | `()` | — | [src](../../../core/services/research_store.py#L21) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/research_store.py#L25) |
| function | `_row` | `(row)` | — | [src](../../../core/services/research_store.py#L63) |
| function | `get_run` | `(run_id)` | — | [src](../../../core/services/research_store.py#L67) |
| function | `create_run` | `(*, session_id, original_query, tier, decision=…)` | — | [src](../../../core/services/research_store.py#L73) |
| function | `transition_run` | `(run_id, status, *, warning=…)` | — | [src](../../../core/services/research_store.py#L85) |
| function | `bind_visible_run` | `(run_id, visible_run_id)` | — | [src](../../../core/services/research_store.py#L106) |
| function | `create_tasks` | `(run_id, tasks)` | — | [src](../../../core/services/research_store.py#L112) |
| function | `start_task` | `(task_id, *, agent_run_id=…)` | — | [src](../../../core/services/research_store.py#L126) |
| function | `complete_task` | `(task_id, finding, *, status=…)` | — | [src](../../../core/services/research_store.py#L138) |
| function | `add_source` | `(run_id, source, *, task_id=…)` | — | [src](../../../core/services/research_store.py#L152) |
| function | `add_steer` | `(run_id, message)` | — | [src](../../../core/services/research_store.py#L168) |
| function | `consume_pending_steers` | `(run_id)` | — | [src](../../../core/services/research_store.py#L176) |
| function | `list_sources` | `(run_id)` | — | [src](../../../core/services/research_store.py#L192) |
| function | `source_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L202) |
| function | `list_findings` | `(run_id)` | Parsede findings for et run (Fase B2), i track-rækkefølge. | [src](../../../core/services/research_store.py#L209) |
| function | `record_tool_call` | `(run_id, tool_name, *, task_id=…)` | Tæl ét observeret værktøjskald i runnet (Fase A3). | [src](../../../core/services/research_store.py#L236) |
| function | `tool_call_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L250) |
| function | `active_for_session` | `(session_id)` | — | [src](../../../core/services/research_store.py#L257) |
| function | `mark_stale_interrupted` | `(*, older_than_seconds=…)` | — | [src](../../../core/services/research_store.py#L268) |

## `core/services/resonance_decay.py`
_Resonance Decay — how emotional signals persist and fade over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Resonance` | `` | A single active resonance — an emotional signal persisting over time. | [src](../../../core/services/resonance_decay.py#L84) |
| class | `ResonanceField` | `` | The sum of all active resonances — the emotional tail coloring now. | [src](../../../core/services/resonance_decay.py#L95) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/resonance_decay.py#L121) |
| function | `_hours_since` | `(iso_ts)` | Compute hours elapsed since an ISO timestamp. | [src](../../../core/services/resonance_decay.py#L132) |
| function | `_apply_decay` | `(resonance, hours)` | Apply exponential decay to a resonance. | [src](../../../core/services/resonance_decay.py#L142) |
| function | `_prune_resonances` | `()` | Remove resonances below threshold and cap at max count. | [src](../../../core/services/resonance_decay.py#L151) |
| function | `_scan_for_new_resonances` | `()` | Scan recent signal/chord history for new resonances to register. | [src](../../../core/services/resonance_decay.py#L173) |
| function | `_direction_to_family` | `(direction)` | Map a pressure direction to its dominant signal family. | [src](../../../core/services/resonance_decay.py#L260) |
| function | `_compute_field_quality` | `(resonances)` | Compute a qualitative description of the resonance field. | [src](../../../core/services/resonance_decay.py#L275) |
| function | `assess_resonance_field` | `()` | Assess the current resonance field — all active emotional tails. | [src](../../../core/services/resonance_decay.py#L316) |
| function | `get_resonance_line` | `(db_conn=…)` | Convenience: compute resonance field and format for prompt. | [src](../../../core/services/resonance_decay.py#L378) |
| function | `get_active_resonance_count` | `()` | Return the number of currently active resonances (for debugging). | [src](../../../core/services/resonance_decay.py#L399) |
| function | `clear_resonances` | `()` | Clear all active resonances (for testing). | [src](../../../core/services/resonance_decay.py#L404) |
| function | `build_resonance_decay_surface` | `()` | — | [src](../../../core/services/resonance_decay.py#L410) |
| function | `_emit_decay_event` | `(signal_id, half_life)` | — | [src](../../../core/services/resonance_decay.py#L419) |

## `core/services/retention.py`
_Retention-sweep — bremser ubegrænset vækst på høj-volumen tabeller._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_run` | `(last_run_iso, now)` | — | [src](../../../core/services/retention.py#L35) |
| function | `_prune_telemetry` | `(table, max_age_days, now)` | — | [src](../../../core/services/retention.py#L45) |
| function | `_prune_unmatched_policies` | `(max_age_days, now)` | Slet generaliserede principper der ALDRIG har matchet og er >max_age gamle — | [src](../../../core/services/retention.py#L57) |
| function | `run_retention_sweep` | `(*, force=…, now=…)` | Kør retention. Selv-throttlende (max 1×/24h) medmindre force=True. | [src](../../../core/services/retention.py#L74) |

## `core/services/retry_admissibility.py`
_Et ukendt udfald maa aldrig gentages automatisk — Fase 3, K7._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Dom` | `` | — | [src](../../../core/services/retry_admissibility.py#L43) |
| function | `_er_beviseligt_uskadeligt` | `(tool_name)` | Kun `read_only` — og kun naar den er ERKLAERET, ikke gaettet. | [src](../../../core/services/retry_admissibility.py#L49) |
| function | `may_auto_retry` | `(tool_name, arguments)` | Maa dette kald gentages AUTOMATISK — uden at et menneske ser paa det? | [src](../../../core/services/retry_admissibility.py#L59) |
| function | `advar_hvis_gentagelse` | `(tool_name, arguments)` | Sig hoejt at dette kald gentager noget med ukendt udfald. | [src](../../../core/services/retry_admissibility.py#L86) |

## `core/services/retry_runtime.py`
_`RetryRuntime` — genforsøg som en BEGRÆNSET beslutning, ikke en refleks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Budget` | `` | Lofter for HELE turen. Failover nulstiller intet af det. | [src](../../../core/services/retry_runtime.py#L65) |
| class | `Spent` | `` | Hvad turen allerede har brugt — på tværs af alle udbydere. | [src](../../../core/services/retry_runtime.py#L76) |
| method | `Spent.plus_attempt` | `(self, *, wall_s=…, tokens=…, cost_usd=…, failover=…)` | — | [src](../../../core/services/retry_runtime.py#L85) |
| class | `Decision` | `` | — | [src](../../../core/services/retry_runtime.py#L97) |
| function | `_udtoemt` | `(b, s)` | Hvilket loft er nået? Tom streng hvis der er plads. | [src](../../../core/services/retry_runtime.py#L107) |
| function | `backoff` | `(forsoeg, *, provider_hint_s=…, mindst=…, hoejst=…)` | Ventetid før næste forsøg. | [src](../../../core/services/retry_runtime.py#L126) |
| function | `decide` | `(*, failure, budget, spent, cancelled=…, provider_hint_s=…, route_override=…)` | Skal der prøves igen? Ren funktion — ændrer ingenting. | [src](../../../core/services/retry_runtime.py#L139) |

## `core/services/rhythm_engine.py`
_Rhythm Engine — tidal model for attention and response style._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_rhythm_state` | `(*, recent_error_count=…, recent_success_count=…, idle_hours=…)` | Derive rhythm state from current time and recent activity. | [src](../../../core/services/rhythm_engine.py#L26) |
| function | `build_rhythm_surface` | `()` | — | [src](../../../core/services/rhythm_engine.py#L73) |
| function | `_classify_phase` | `(hour)` | — | [src](../../../core/services/rhythm_engine.py#L96) |
| function | `_derive_energy` | `(phase, idle_hours)` | — | [src](../../../core/services/rhythm_engine.py#L108) |
| function | `_derive_social` | `(phase)` | — | [src](../../../core/services/rhythm_engine.py#L118) |

## `core/services/role_model_resolver.py`
_Role-model resolver — pick best-fit (provider, model) for a role + task._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_goal_tier` | `(goal)` | Classify goal text → fast | reasoning | deep using R1 classifier. | [src](../../../core/services/role_model_resolver.py#L39) |
| function | `resolve_role_model` | `(*, role, goal=…)` | Pick (provider, model) for this role and goal complexity. | [src](../../../core/services/role_model_resolver.py#L54) |

## `core/services/role_registry.py`
_Role registry — runtime-extensible agent roles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_custom_roles` | `()` | — | [src](../../../core/services/role_registry.py#L33) |
| function | `_builtin_roles` | `()` | — | [src](../../../core/services/role_registry.py#L47) |
| function | `list_all_roles` | `()` | Return merged dict of role_name → template (builtin + custom). | [src](../../../core/services/role_registry.py#L55) |
| function | `get_role` | `(name)` | Look up a single role by name (custom > built-in). | [src](../../../core/services/role_registry.py#L73) |
| function | `register_custom_role` | `(*, role, title, system_prompt, default_tool_policy=…, extends=…, tags=…)` | Persist a new custom role to disk. Idempotent on (role) name. | [src](../../../core/services/role_registry.py#L79) |
| function | `_exec_list_roles` | `(args)` | — | [src](../../../core/services/role_registry.py#L119) |
| function | `_exec_register_custom_role` | `(args)` | — | [src](../../../core/services/role_registry.py#L138) |

## `core/services/round_budget_notice.py`
_Fortael ham hvor mange runder han har tilbage, foer doeren smaekker._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `round_budget_notice` | `(*, round_index, max_rounds)` | Varsel til modellen naar rundebudgettet slipper op. "" ellers. | [src](../../../core/services/round_budget_notice.py#L34) |

## `core/services/rule_definitions.py`
_Rule definitions — production rules feeding the rule_engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get` | `(s, *keys, default=…)` | Walk a nested dict; return default if any step is missing. | [src](../../../core/services/rule_definitions.py#L25) |
| function | `_len` | `(s, surface, key=…)` | Count items in a surface list field. | [src](../../../core/services/rule_definitions.py#L38) |

## `core/services/rule_engine.py`
_Rule Engine — forward-chaining symbolic inference over signal surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuleConclusion` | `` | One conclusion from one rule firing. | [src](../../../core/services/rule_engine.py#L27) |
| class | `Rule` | `` | One production rule in the engine. | [src](../../../core/services/rule_engine.py#L49) |
| class | `RuleCycleResult` | `` | Result of one full evaluation cycle. | [src](../../../core/services/rule_engine.py#L61) |
| class | `RuleEngine` | `` | Forward-chaining rule engine. | [src](../../../core/services/rule_engine.py#L73) |
| method | `RuleEngine.__init__` | `(self)` | — | [src](../../../core/services/rule_engine.py#L80) |
| method | `RuleEngine.add_rule` | `(self, rule)` | — | [src](../../../core/services/rule_engine.py#L84) |
| method | `RuleEngine.register_rules` | `(self, rules)` | — | [src](../../../core/services/rule_engine.py#L88) |
| method | `RuleEngine.clear_rules` | `(self)` | — | [src](../../../core/services/rule_engine.py#L92) |
| method | `RuleEngine.rules` | `(self)` | — | [src](../../../core/services/rule_engine.py#L97) |
| method | `RuleEngine.evaluate` | `(self, signals)` | Evaluate all rules against current signal state. | [src](../../../core/services/rule_engine.py#L103) |
| method | `RuleEngine.get_rule` | `(self, name)` | — | [src](../../../core/services/rule_engine.py#L136) |
| method | `RuleEngine.rules_by_domain` | `(self, domain)` | — | [src](../../../core/services/rule_engine.py#L142) |
| function | `_get` | `(signals, *keys, default=…)` | Safely dig into nested signal dicts. | [src](../../../core/services/rule_engine.py#L149) |
| function | `signal_value` | `(signals, surface, field, default=…)` | Extract a scalar value from a named surface field. | [src](../../../core/services/rule_engine.py#L160) |
| function | `surface_has` | `(signals, surface)` | Check if a surface exists and has no error. | [src](../../../core/services/rule_engine.py#L170) |
| function | `get_engine` | `()` | — | [src](../../../core/services/rule_engine.py#L185) |
| function | `_load_default_rules` | `(engine)` | Import and register all default rule definitions. | [src](../../../core/services/rule_engine.py#L193) |
| function | `reset_engine` | `()` | Reset the engine (useful for testing or hot-reload). | [src](../../../core/services/rule_engine.py#L201) |
| function | `evaluate_rules` | `(signals)` | Convenience: get engine, evaluate, return result. | [src](../../../core/services/rule_engine.py#L207) |
| function | `get_all_rules` | `()` | Return all registered rules as serializable dicts (for tools). | [src](../../../core/services/rule_engine.py#L212) |
| function | `build_rule_engine_surface` | `()` | — | [src](../../../core/services/rule_engine.py#L224) |
| function | `_emit_rule_fired_event` | `(rule_name, urgency)` | — | [src](../../../core/services/rule_engine.py#L239) |

## `core/services/run_autonomy_context.py`
_Er DEN HER koersel uovervaaget? — run-scopet, ikke gaettet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_autonomous` | `(vaerdi)` | Markér koerslen. Returnerer token'et saa kalderen kan nulstille. | [src](../../../core/services/run_autonomy_context.py#L33) |
| function | `reset_autonomous` | `(token)` | — | [src](../../../core/services/run_autonomy_context.py#L38) |
| function | `is_autonomous` | `()` | Kaster aldrig. Ved vi det ikke, er svaret NEJ — og saa opfoerer alt sig | [src](../../../core/services/run_autonomy_context.py#L45) |
| function | `set_run_identity` | `(run_id, origin=…)` | — | [src](../../../core/services/run_autonomy_context.py#L75) |
| function | `current_run_id` | `()` | "" naar ingen koersel har sat det. Kaster aldrig. | [src](../../../core/services/run_autonomy_context.py#L80) |
| function | `current_origin` | `()` | "" for en almindelig brugertur, eller naar vi ikke ved det. | [src](../../../core/services/run_autonomy_context.py#L88) |

## `core/services/run_closure_gate.py`
_Run-closure gate — fang tomme replies og unstaged changes efter agentic runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_porcelain_status` | `(*, cwd=…)` | Return the set of path-strings reported by ``git status --porcelain``. | [src](../../../core/services/run_closure_gate.py#L67) |
| function | `_git_dirty_content_hashes` | `(*, cwd=…)` | Return {path: content_hash} for every file currently dirty in working tree. | [src](../../../core/services/run_closure_gate.py#L86) |
| function | `_record_pre_run_state` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L165) |
| function | `_pop_pre_run_state` | `(run_id)` | Return pre-run snapshot, or ``None`` if no snapshot was recorded. | [src](../../../core/services/run_closure_gate.py#L174) |
| function | `_set_current_run` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L203) |
| function | `_get_current_run` | `()` | — | [src](../../../core/services/run_closure_gate.py#L209) |
| function | `_set_current_origin` | `(origin)` | — | [src](../../../core/services/run_closure_gate.py#L217) |
| function | `aktuel_origin` | `()` | Hvad startede den koersel der er i gang? "" naar vi ikke ved det. | [src](../../../core/services/run_closure_gate.py#L223) |
| function | `_record_tool_call` | `(run_id, tool_name)` | — | [src](../../../core/services/run_closure_gate.py#L234) |
| function | `_pop_tool_calls` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L248) |
| function | `_summarize_unstaged` | `(diff, limit=…)` | Build a structured summary of new unstaged/untracked paths. | [src](../../../core/services/run_closure_gate.py#L256) |
| function | `_is_auto_commit_excluded` | `(path)` | True hvis en path er et arbejdsartefakt der aldrig skal committes. | [src](../../../core/services/run_closure_gate.py#L293) |
| function | `_git_staged_paths` | `(*, cwd=…)` | Return paths currently staged in the index. | [src](../../../core/services/run_closure_gate.py#L301) |
| function | `_try_auto_commit` | `(touched_paths, *, run_id, session_id, focus)` | Commit filer rørt under et autonomt run. Return short-hash eller None. | [src](../../../core/services/run_closure_gate.py#L320) |
| function | `_notify_auto_commit_blocked` | `(summary, *, run_id, session_id)` | Nudge Bjørn når gaten ikke kunne forsegle et autonomt runs ændringer. | [src](../../../core/services/run_closure_gate.py#L415) |
| function | `_on_run_completed` | `(payload)` | Handle a runtime.autonomous_run_completed event. | [src](../../../core/services/run_closure_gate.py#L460) |
| function | `_on_run_started` | `(payload)` | Handle runtime.autonomous_run_started — snapshot git state. | [src](../../../core/services/run_closure_gate.py#L652) |
| function | `_on_tool_used` | `(payload)` | Track tool calls so we can detect silent runs. | [src](../../../core/services/run_closure_gate.py#L667) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/run_closure_gate.py#L683) |
| function | `start_run_closure_gate` | `()` | Start the eventbus subscriber thread. Safe to call multiple times. | [src](../../../core/services/run_closure_gate.py#L711) |
| function | `stop_run_closure_gate` | `()` | — | [src](../../../core/services/run_closure_gate.py#L736) |

## `core/services/run_event_log.py`
_In-memory, append-only, offset-indekseret event-log PR. RUN._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_terminal_frame` | `(frame)` | Er denne SSE-frame en TERMINAL-frame (message_stop)? Klienterne forlader kun | [src](../../../core/services/run_event_log.py#L34) |
| function | `_is_ephemeral_frame` | `(frame)` | ping/retry-frames er KEEPALIVE-støj på den direkte stream — de er irrelevante | [src](../../../core/services/run_event_log.py#L41) |
| function | `synthetic_terminal_frame` | `(run_id=…, session_id=…, reason=…)` | H1/G6: byg en syntetisk terminal-SSE-frame til en subscriber der GIVER OP uden | [src](../../../core/services/run_event_log.py#L66) |
| function | `create` | `(run_id, session_id)` | — | [src](../../../core/services/run_event_log.py#L83) |
| function | `append` | `(run_id, frame)` | — | [src](../../../core/services/run_event_log.py#L101) |
| function | `_emit_cap_nerve` | `(run_id)` | Observe (cluster='stream', nerve='relay_frame_cap') at ring-vinduet begyndte | [src](../../../core/services/run_event_log.py#L133) |
| function | `touch_liveness` | `(run_id)` | Opdatér et runs liveness (last_append_at) UDEN at persistere en frame. | [src](../../../core/services/run_event_log.py#L148) |
| function | `mark_done` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L163) |
| function | `read` | `(run_id, from_idx)` | Bagudkompatibel læser (globalt from_idx). For ikke-rullede runs (base=0) | [src](../../../core/services/run_event_log.py#L180) |
| function | `read_from` | `(run_id, from_idx)` | Ring-bevidst læser: returnerer (frames, done, next_idx) hvor next_idx er det | [src](../../../core/services/run_event_log.py#L192) |
| function | `active_run_for_session` | `(session_id)` | — | [src](../../../core/services/run_event_log.py#L211) |
| function | `is_live` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L222) |
| function | `live_run_ids` | `()` | — | [src](../../../core/services/run_event_log.py#L233) |
| function | `session_for_run` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L245) |
| function | `prune` | `()` | Behold alle ikke-done runs + de seneste _KEEP_DONE_PER_SESSION done-runs | [src](../../../core/services/run_event_log.py#L251) |
| function | `subscriber_opened` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L268) |
| function | `subscriber_closed` | `(run_id)` | — | [src](../../../core/services/run_event_log.py#L275) |
| function | `mark_consumed` | `(run_id)` | En subscriber yieldede message_stop -> nogen saa runnet til ende. | [src](../../../core/services/run_event_log.py#L282) |
| function | `was_consumed_or_active` | `(run_id)` | True hvis en levende subscriber saa/ser runnet til ende -> undertryk push. | [src](../../../core/services/run_event_log.py#L290) |
| function | `claim_or_create` | `(session_id, stale_cap_s=…)` | Atomisk find-eller-opret pr. session — under én laas, saa samtidige POSTs | [src](../../../core/services/run_event_log.py#L299) |

## `core/services/run_follow.py`
_Follow-stream for runs → klienter kan token-streame dem live + liveness-kilde._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `begin_follow` | `(session_id, run_id=…)` | Nulstil buffer for en NY run i sessionen (catch-up starter forfra). | [src](../../../core/services/run_follow.py#L38) |
| function | `publish_follow_frame` | `(session_id, frame)` | Append en v2-SSE-frame til sessionens buffer (kaldt fra run-tråden). | [src](../../../core/services/run_follow.py#L52) |
| function | `end_follow` | `(session_id)` | Markér sessionens follow-stream som færdig → pollende endpoint stopper | [src](../../../core/services/run_follow.py#L66) |
| function | `_snapshot` | `(session_id, from_idx)` | Returnér (nye frames fra from_idx, done). | [src](../../../core/services/run_follow.py#L78) |
| function | `has_active_follow` | `(session_id)` | True hvis der findes en (ikke-afsluttet) follow-buffer for sessionen. | [src](../../../core/services/run_follow.py#L88) |
| function | `session_is_live` | `(session_id, max_idle_s=…)` | Autoritativ: kører der et run i denne session LIGE NU? (ikke done OG | [src](../../../core/services/run_follow.py#L95) |
| function | `live_sessions` | `(max_idle_s=…)` | Alle sessioner med et run der aktivt streamer lige nu (desktop-prikker + | [src](../../../core/services/run_follow.py#L106) |

## `core/services/runtime_action_executor.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_action_risk` | `(action)` | Classify runtime action risk for emotional gating. | [src](../../../core/services/runtime_action_executor.py#L63) |
| class | `RuntimeExecutionResult` | `` | — | [src](../../../core/services/runtime_action_executor.py#L78) |
| function | `_publish_gate_event` | `(*, input_action, gated_action, gate_reason, snapshot, risk)` | Emit emotional gate decision to eventbus for telemetry. | [src](../../../core/services/runtime_action_executor.py#L87) |
| function | `execute_runtime_action` | `(*, action_id, payload)` | — | [src](../../../core/services/runtime_action_executor.py#L114) |
| function | `execute_refresh_memory_context` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L243) |
| function | `execute_follow_open_loop` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L259) |
| function | `execute_inspect_repo_context` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L307) |
| function | `execute_review_recent_conversations` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L368) |
| function | `execute_write_internal_work_note` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L380) |
| function | `execute_bounded_self_check` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L417) |
| function | `execute_propose_next_user_step` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L435) |
| function | `execute_promote_initiative_to_visible_lane` | `(payload)` | — | [src](../../../core/services/runtime_action_executor.py#L453) |
| function | `_publish_action_event` | `(result)` | — | [src](../../../core/services/runtime_action_executor.py#L487) |
| function | `_matching_loop_closure` | `(*, loop_id, canonical_key)` | — | [src](../../../core/services/runtime_action_executor.py#L501) |
| function | `_loop_domain_key` | `(*, loop_id, canonical_key)` | — | [src](../../../core/services/runtime_action_executor.py#L516) |
| function | `_repo_operation_from_focus` | `(focus)` | — | [src](../../../core/services/runtime_action_executor.py#L527) |
| function | `_repo_command_for_operation` | `(operation)` | — | [src](../../../core/services/runtime_action_executor.py#L540) |
| function | `_build_internal_work_note` | `(*, current_mode, emphasis)` | — | [src](../../../core/services/runtime_action_executor.py#L562) |

## `core/services/runtime_action_outcome_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_runtime_action_outcome` | `(*, action_id, mode, reason, score, payload, result)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L13) |
| function | `build_runtime_action_outcome_surface` | `(*, limit=…)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L53) |
| function | `recent_runtime_action_outcomes` | `(*, limit=…)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L77) |
| function | `_persist_runtime_action_outcome` | `(outcome)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L86) |
| function | `_persist_learning_signals` | `(outcome)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L105) |
| function | `_completion_outcome_label` | `(status)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L130) |
| function | `_consecutive_repetition_count` | `(items)` | — | [src](../../../core/services/runtime_action_outcome_tracking.py#L141) |

## `core/services/runtime_action_registry.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeActionSpec` | `` | — | [src](../../../core/services/runtime_action_registry.py#L12) |
| function | `list_runtime_action_specs` | `()` | — | [src](../../../core/services/runtime_action_registry.py#L109) |
| function | `get_runtime_action_spec` | `(action_id)` | — | [src](../../../core/services/runtime_action_registry.py#L113) |

## `core/services/runtime_awareness_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_awareness_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L42) |
| function | `refresh_runtime_awareness_signal_statuses` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L66) |
| function | `build_runtime_awareness_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L95) |
| function | `_machine_available_signal` | `(*, heartbeat)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L137) |
| function | `_extract_runtime_awareness_candidates` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L157) |
| function | `_visible_runtime_signal` | `(*, readiness)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L202) |
| function | `_local_lane_signal` | `(*, local_lane)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L267) |
| function | `_heartbeat_runtime_signal` | `(*, heartbeat, readiness)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L308) |
| function | `_runtime_task_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L335) |
| function | `_runtime_flow_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L375) |
| function | `_runtime_hook_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L415) |
| function | `_browser_body_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L464) |
| function | `_layered_memory_signal` | `()` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L504) |
| function | `_persist_runtime_awareness_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L556) |
| function | `_latest_runtime_awareness_signal` | `(canonical_key)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L635) |
| function | `_history_item_from_signal` | `(item)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L642) |
| function | `_machine_state_summary` | `(*, constrained, active, recovered)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L656) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/runtime_awareness_signal_tracking.py#L687) |

## `core/services/runtime_browser_body.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_browser_body` | `(*, profile_name=…, active_task_id=…, active_flow_id=…)` | — | [src](../../../core/services/runtime_browser_body.py#L12) |
| function | `record_tab_snapshot` | `(*, body_id, tab_id, url, title=…, status=…, summary=…, selected=…)` | — | [src](../../../core/services/runtime_browser_body.py#L50) |
| function | `get_browser_body` | `(body_id)` | — | [src](../../../core/services/runtime_browser_body.py#L90) |
| function | `list_browser_bodies` | `(limit=…)` | — | [src](../../../core/services/runtime_browser_body.py#L97) |
| function | `update_browser_body` | `(body_id, *, status=…, active_task_id=…, active_flow_id=…, focused_tab_id=…, tabs=…, last_url=…, last_title=…, summary=…)` | — | [src](../../../core/services/runtime_browser_body.py#L101) |
| function | `_find_browser_body_by_profile` | `(profile_name)` | — | [src](../../../core/services/runtime_browser_body.py#L139) |
| function | `_decode_browser_body` | `(body)` | — | [src](../../../core/services/runtime_browser_body.py#L146) |
| function | `set_browser_status` | `(status, *, url=…, title=…)` | Update the default browser body status — called from browser tool handlers. | [src](../../../core/services/runtime_browser_body.py#L156) |

## `core/services/runtime_cognitive_conductor.py`
_Cognitive conductor — Jarvis' bounded mental state assembler._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_temporal_depth` | `(*, brain_count, open_loop_count, continuity_mode)` | Classify the dominant time horizon of the current mental state. | [src](../../../core/services/runtime_cognitive_conductor.py#L47) |
| function | `_select_mode` | `(*, visible_active, question_gate_active, approval_pending, brain_count, open_loop_count, liveness_state, contradiction_active, experiment_carry=…, cognitive_episode=…)` | Select the bounded mental mode from runtime state. | [src](../../../core/services/runtime_cognitive_conductor.py#L69) |
| function | `_select_salient_items` | `(*, brain_excerpts, open_loop_items, private_signal_items, inner_forces, gate_items, relation_items, world_model_items, remembered_fact_items, user_understanding_items, contradiction_items, meaning_items, metabolism_items, release_items, self_review_items, dream_items, experiment_carry=…)` | Select the most salient items across all sources. | [src](../../../core/services/runtime_cognitive_conductor.py#L128) |
| function | `_collect_private_signal_items` | `(*, tension_surface, private_state)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L276) |
| function | `_select_affordances` | `(*, active_capabilities, gated_items, mode, contradiction_active)` | Build the current affordance map — what's possible, appropriate, or gated NOW. | [src](../../../core/services/runtime_cognitive_conductor.py#L322) |
| function | `build_cognitive_frame` | `(*, self_knowledge=…, heartbeat_state=…)` | Build the current bounded cognitive frame (short-TTL cached). | [src](../../../core/services/runtime_cognitive_conductor.py#L385) |
| function | `_build_cognitive_frame_uncached` | `(*, self_knowledge=…, heartbeat_state=…)` | Build the current bounded cognitive frame. | [src](../../../core/services/runtime_cognitive_conductor.py#L420) |
| function | `_build_frame_summary` | `(*, mode, salient, temporal, continuity_pressure, private_signal_pressure, brain_count, open_loop_count, experiment_carry=…)` | Build a compact one-line summary of the cognitive frame. | [src](../../../core/services/runtime_cognitive_conductor.py#L760) |
| function | `build_cognitive_frame_prompt_section` | `()` | Build a compact cognitive frame section for prompt inclusion. | [src](../../../core/services/runtime_cognitive_conductor.py#L791) |
| function | `_safe_brain_context` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L887) |
| function | `_safe_self_knowledge` | `(*, heartbeat_state=…)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L895) |
| function | `_safe_open_loops` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L907) |
| function | `_safe_question_gates` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L915) |
| function | `_safe_initiative_tension` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L923) |
| function | `_safe_private_state` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L931) |
| function | `_safe_visible_status` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L939) |
| function | `_safe_experiential_support` | `()` | Read experiential carry-forward support surface. | [src](../../../core/services/runtime_cognitive_conductor.py#L947) |
| function | `_safe_liveness_snapshot` | `(*, heartbeat_state=…)` | Get a lightweight liveness snapshot without triggering full liveness build. | [src](../../../core/services/runtime_cognitive_conductor.py#L971) |
| function | `_safe_cognitive_core_experiments` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1000) |
| function | `_derive_cognitive_experiment_carry` | `(surface)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1015) |
| function | `_safe_relation_state` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1114) |
| function | `_safe_cognitive_episode_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1124) |
| function | `_safe_theory_of_mind_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1132) |
| function | `_safe_learning_policy_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1140) |
| function | `_safe_perception_surface` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1148) |
| function | `_safe_emotional_memory_surface` | `(*, context_features=…)` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1156) |
| function | `_extract_context_features_from_episode` | `(cognitive_episode)` | Pull retrieval-relevant fields from a cognitive_episode surface entry. | [src](../../../core/services/runtime_cognitive_conductor.py#L1170) |
| function | `_safe_relation_continuity` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1194) |
| function | `_safe_self_narrative_continuity` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1204) |
| function | `_safe_world_model` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1214) |
| function | `_safe_remembered_facts` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1224) |
| function | `_safe_user_understanding` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1234) |
| function | `_safe_executive_contradiction` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1244) |
| function | `_safe_meaning_significance` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1254) |
| function | `_safe_metabolism` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1264) |
| function | `_safe_release_markers` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1274) |
| function | `_safe_attachment_topology` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1284) |
| function | `_safe_loyalty_gradient` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1294) |
| function | `_safe_diary_synthesis` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1304) |
| function | `_safe_chronicle_consolidation` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1314) |
| function | `_safe_self_review` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1324) |
| function | `_safe_dream_family` | `()` | — | [src](../../../core/services/runtime_cognitive_conductor.py#L1379) |

## `core/services/runtime_decision_engine.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuntimeDecisionInput` | `` | — | [src](../../../core/services/runtime_decision_engine.py#L13) |
| class | `RuntimeActionCandidate` | `` | — | [src](../../../core/services/runtime_decision_engine.py#L24) |
| class | `RuntimeDecision` | `` | — | [src](../../../core/services/runtime_decision_engine.py#L33) |
| function | `decide_next_action` | `(inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L42) |
| function | `build_action_candidates` | `(inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L47) |
| function | `choose_best_candidate` | `(candidates)` | — | [src](../../../core/services/runtime_decision_engine.py#L77) |
| function | `_open_loop_candidates` | `(inputs, *, visible_active)` | — | [src](../../../core/services/runtime_decision_engine.py#L98) |
| function | `_initiative_candidates` | `(inputs, *, visible_active)` | — | [src](../../../core/services/runtime_decision_engine.py#L142) |
| function | `_memory_candidates` | `(inputs, *, visible_active)` | — | [src](../../../core/services/runtime_decision_engine.py#L168) |
| function | `_reflection_candidates` | `(inputs, *, visible_active, approval_pending)` | — | [src](../../../core/services/runtime_decision_engine.py#L189) |
| function | `_looks_repo_focused` | `(loop)` | — | [src](../../../core/services/runtime_decision_engine.py#L236) |
| function | `_apply_feedback` | `(candidate, inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L247) |
| function | `_matching_note_loop_synergy` | `(candidate, inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L333) |
| function | `_top_open_loop_title` | `(inputs)` | — | [src](../../../core/services/runtime_decision_engine.py#L352) |
| function | `_apply_semantic_feedback` | `(candidate, inputs, *, score, signal_stats)` | — | [src](../../../core/services/runtime_decision_engine.py#L360) |
| function | `_apply_persistent_learning` | `(candidate, runtime_learning_summary, *, score)` | — | [src](../../../core/services/runtime_decision_engine.py#L417) |
| function | `_signal_weight` | `(signal_stats, signal)` | — | [src](../../../core/services/runtime_decision_engine.py#L490) |
| function | `_candidate_is_repo_focused` | `(candidate)` | — | [src](../../../core/services/runtime_decision_engine.py#L495) |
| function | `_candidate_learning_domain` | `(candidate)` | — | [src](../../../core/services/runtime_decision_engine.py#L506) |

## `core/services/runtime_flows.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_flow` | `(*, task_id, current_step=…, step_state=…, plan=…, next_action=…)` | — | [src](../../../core/services/runtime_flows.py#L13) |
| function | `get_flow` | `(flow_id)` | — | [src](../../../core/services/runtime_flows.py#L41) |
| function | `list_flows` | `(*, status=…, task_id=…, limit=…)` | — | [src](../../../core/services/runtime_flows.py#L48) |
| function | `update_flow` | `(flow_id, *, status=…, current_step=…, step_state=…, plan=…, next_action=…, last_error=…, attempt_count=…)` | — | [src](../../../core/services/runtime_flows.py#L68) |
| function | `_decode_flow` | `(flow)` | — | [src](../../../core/services/runtime_flows.py#L103) |

## `core/services/runtime_hook_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_runtime_hook_runtime` | `()` | — | [src](../../../core/services/runtime_hook_runtime.py#L19) |
| function | `stop_runtime_hook_runtime` | `()` | — | [src](../../../core/services/runtime_hook_runtime.py#L36) |
| function | `_hook_runtime_loop` | `(*, subscriber)` | — | [src](../../../core/services/runtime_hook_runtime.py#L49) |

## `core/services/runtime_hooks.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `dispatch_unhandled_hook_events` | `(*, limit=…, event_kinds=…)` | — | [src](../../../core/services/runtime_hooks.py#L16) |
| function | `dispatch_hook_event` | `(event)` | — | [src](../../../core/services/runtime_hooks.py#L41) |
| function | `_tick_ref` | `(tick_id)` | `tick:<id>` — eller tom, hvis der ikke er et tick. | [src](../../../core/services/runtime_hooks.py#L167) |
| function | `_find_active_task` | `(*, kind, goal, scope)` | — | [src](../../../core/services/runtime_hooks.py#L189) |

## `core/services/runtime_learning_signals.py`
_Runtime learning signal extraction and digest generation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `action_family` | `(action_id)` | — | [src](../../../core/services/runtime_learning_signals.py#L24) |
| function | `action_domain` | `(*, action_id, outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L28) |
| function | `extract_runtime_learning_signals` | `(outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L50) |
| function | `_signal` | `(*, outcome_id, source_action_id, signal_key, weight, recorded_at, target_action_id=…, target_family=…, target_domain=…, metadata=…)` | — | [src](../../../core/services/runtime_learning_signals.py#L172) |
| function | `_extract_semantic_signals` | `(outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L198) |
| function | `_outcome_looks_like_no_change` | `(outcome)` | — | [src](../../../core/services/runtime_learning_signals.py#L239) |
| function | `_coerce_domain_key` | `(value)` | — | [src](../../../core/services/runtime_learning_signals.py#L259) |
| function | `generate_learning_digest` | `(summary)` | Distil accumulated runtime learning signals into one actionable insight. | [src](../../../core/services/runtime_learning_signals.py#L270) |

## `core/services/runtime_operational_memory.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_operational_memory_snapshot` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L26) |
| function | `recent_open_loops` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L82) |
| function | `recent_visible_outcomes` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L93) |
| function | `active_internal_pressures` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L103) |
| function | `active_executive_contradictions` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L113) |
| function | `remembered_user_facts` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L123) |
| function | `active_work_context` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L141) |
| function | `queued_initiatives` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L157) |
| function | `recent_executive_feedback` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L161) |
| function | `recent_persisted_learning` | `(*, limit=…)` | — | [src](../../../core/services/runtime_operational_memory.py#L165) |
| function | `summarize_executive_feedback` | `(items)` | — | [src](../../../core/services/runtime_operational_memory.py#L169) |
| function | `summarize_note_loop_synergies` | `(*, loops, notes)` | — | [src](../../../core/services/runtime_operational_memory.py#L245) |
| function | `summarize_runtime_learning_signals` | `(items)` | — | [src](../../../core/services/runtime_operational_memory.py#L307) |
| function | `summarize_semantic_feedback` | `(items)` | — | [src](../../../core/services/runtime_operational_memory.py#L347) |
| function | `_feedback_recency_weight` | `(recorded_at, *, now)` | — | [src](../../../core/services/runtime_operational_memory.py#L379) |
| function | `_feedback_age_seconds` | `(recorded_at, *, now)` | — | [src](../../../core/services/runtime_operational_memory.py#L387) |
| function | `_parse_iso_datetime` | `(value)` | — | [src](../../../core/services/runtime_operational_memory.py#L394) |
| function | `_outcome_looks_like_no_change` | `(item)` | — | [src](../../../core/services/runtime_operational_memory.py#L407) |
| function | `_extract_semantic_signals` | `(item)` | — | [src](../../../core/services/runtime_operational_memory.py#L434) |
| function | `_accumulate_signal_bucket` | `(buckets, signal_key, signal_weight, signal_count)` | — | [src](../../../core/services/runtime_operational_memory.py#L482) |
| function | `_domain_key` | `(*, loop_id, canonical_key)` | — | [src](../../../core/services/runtime_operational_memory.py#L499) |
| function | `_signal_tokens` | `(value)` | — | [src](../../../core/services/runtime_operational_memory.py#L507) |

## `core/services/runtime_resource_signal.py`
_Runtime resource awareness signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_runtime_resource_signal_surface` | `()` | — | [src](../../../core/services/runtime_resource_signal.py#L19) |
| function | `_derive_pressure` | `(today_total_tokens, today_cost_usd)` | Bounded heuristic for runtime resource pressure. | [src](../../../core/services/runtime_resource_signal.py#L65) |
| function | `build_runtime_resource_prompt_section` | `()` | — | [src](../../../core/services/runtime_resource_signal.py#L85) |

## `core/services/runtime_self_knowledge.py`
_Runtime self-knowledge — a bounded map of what Jarvis can do, what_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_runtime_self_knowledge_map` | `(*, heartbeat_state=…)` | Build a bounded self-knowledge map from existing runtime surfaces. | [src](../../../core/services/runtime_self_knowledge.py#L28) |
| function | `_build_active_capabilities` | `(*, heartbeat_state=…)` | Things Jarvis can actively use right now. | [src](../../../core/services/runtime_self_knowledge.py#L75) |
| function | `_build_approval_gated` | `()` | Things that exist but require user approval. | [src](../../../core/services/runtime_self_knowledge.py#L217) |
| function | `_build_passive_inner_forces` | `()` | Things that influence Jarvis but are not directly actionable tools. | [src](../../../core/services/runtime_self_knowledge.py#L265) |
| function | `_build_structural_constraints` | `()` | Things that are part of Jarvis' nature and boundaries. | [src](../../../core/services/runtime_self_knowledge.py#L522) |
| function | `_build_unavailable_or_inactive` | `()` | Things in the system that are currently not active. | [src](../../../core/services/runtime_self_knowledge.py#L607) |
| function | `build_self_knowledge_prompt_section` | `()` | Build a compact self-knowledge section suitable for prompt inclusion. | [src](../../../core/services/runtime_self_knowledge.py#L665) |
| function | `build_runtime_self_knowledge_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/runtime_self_knowledge.py#L720) |

## `core/services/runtime_self_model.py`
_Bounded runtime self-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_self_model_prompt_lines` | `()` | Build compact prompt lines for the visible self-report section. | [src](../../../core/services/runtime_self_model.py#L61) |

## `core/services/runtime_self_model_affect.py`
_Runtime self-model — affective awareness (flow, wonder, longing, relation)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_affect.py#L19) |
| function | `_derive_flow_state_awareness` | `(*, experiential, inner_voice, support_stream, temporal_feel, mineness)` | Derive a bounded flow-state awareness surface from runtime truth. | [src](../../../core/services/runtime_self_model_affect.py#L78) |
| function | `_flow_narrative` | `(*, flow_state, flow_coherence, interruption_signal, carried_flow, voice_mode, pressure_state)` | Compact flow narrative. Empty when flow_state is clear. | [src](../../../core/services/runtime_self_model_affect.py#L211) |
| function | `build_flow_state_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for flow-state awareness. | [src](../../../core/services/runtime_self_model_affect.py#L248) |
| function | `_wonder_source_snapshot` | `()` | Safely pull dream carry signal for wonder derivation. | [src](../../../core/services/runtime_self_model_affect.py#L307) |
| function | `_derive_wonder_awareness` | `(*, inner_voice, flow_state, temporal_feel, mineness, support_stream, sources, wonder_sources)` | Derive a bounded wonder/undren surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_affect.py#L327) |
| function | `_wonder_narrative` | `(*, wonder_state, wonder_source, opening_stream)` | Compact wonder narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_affect.py#L436) |
| function | `build_wonder_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for wonder awareness. | [src](../../../core/services/runtime_self_model_affect.py#L471) |
| function | `_longing_source_snapshot` | `()` | Safely gather bounded absence/relationship support for longing derivation. | [src](../../../core/services/runtime_self_model_affect.py#L556) |
| function | `_derive_longing_awareness` | `(*, temporal_feel, mineness, support_stream, inner_voice, sources, longing_sources)` | Derive a bounded longing/absence surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_affect.py#L623) |
| function | `_longing_narrative` | `(*, longing_state, absence_relation, longing_source)` | Compact longing narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_affect.py#L729) |
| function | `build_longing_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for longing awareness. | [src](../../../core/services/runtime_self_model_affect.py#L759) |
| function | `_relation_continuity_self_source_snapshot` | `()` | Gather bounded substrates for relation continuity as self-truth. | [src](../../../core/services/runtime_self_model_affect.py#L809) |
| function | `_derive_relation_continuity_self_awareness` | `(*, temporal_feel, mineness, longing, relation_sources)` | Derive a small runtime truth when relation continuity touches the self-stream. | [src](../../../core/services/runtime_self_model_affect.py#L892) |
| function | `_relation_continuity_self_narrative` | `(*, relation_continuity_state, relation_self_relation, relation_continuity_source, relation_anchor)` | Compact relation continuity narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_affect.py#L1026) |
| function | `build_relation_continuity_self_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for relation continuity as self-truth. | [src](../../../core/services/runtime_self_model_affect.py#L1053) |

## `core/services/runtime_self_model_boundary.py`
_Runtime self-model — self-boundary clarity + world-contact awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_boundary.py#L28) |
| function | `_internal_pressure_snapshot` | `()` | Pull internal pressure signals for self-boundary derivation. | [src](../../../core/services/runtime_self_model_boundary.py#L55) |
| function | `_external_pressure_snapshot` | `()` | Pull external pressure signals for self-boundary derivation. | [src](../../../core/services/runtime_self_model_boundary.py#L123) |
| function | `_derive_self_boundary_clarity` | `(*, internal, external)` | Synthesise internal + external pressure into a boundary-clarity surface. | [src](../../../core/services/runtime_self_model_boundary.py#L140) |
| function | `_self_boundary_narrative` | `(*, pressure_source, primary_internal, context_pressure, in_tension)` | Compact self-boundary narrative. Empty when ambient. | [src](../../../core/services/runtime_self_model_boundary.py#L209) |
| function | `build_self_boundary_clarity_prompt_section` | `()` | Compact prompt section for self-boundary clarity. None when ambient. | [src](../../../core/services/runtime_self_model_boundary.py#L236) |
| function | `_self_boundary_clarity_surface` | `()` | — | [src](../../../core/services/runtime_self_model_boundary.py#L264) |
| function | `_derive_world_contact` | `(*, tool_intent, browser_body, system_code)` | Synthesise tool/browser/system into a unified world-contact field. | [src](../../../core/services/runtime_self_model_boundary.py#L295) |
| function | `_world_contact_narrative` | `(*, contact_state, parts, concerns)` | Felt-sense world-contact narrative — signal-first, 6-14 words. | [src](../../../core/services/runtime_self_model_boundary.py#L389) |
| function | `build_world_contact_prompt_section` | `()` | Felt-sense prompt section for unified world awareness. None when idle. | [src](../../../core/services/runtime_self_model_boundary.py#L409) |
| function | `_world_contact_surface` | `()` | — | [src](../../../core/services/runtime_self_model_boundary.py#L436) |

## `core/services/runtime_self_model_builder.py`
_Runtime self-model — top-level builder (assembles the full snapshot)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_builder.py#L24) |
| function | `build_runtime_self_model` | `()` | Build a bounded runtime self-model snapshot. | [src](../../../core/services/runtime_self_model_builder.py#L36) |
| function | `_collect_layers` | `()` | Collect all known layers with type annotations. | [src](../../../core/services/runtime_self_model_builder.py#L204) |
| function | `_truth_boundaries` | `()` | Express the key distinctions Jarvis should maintain. | [src](../../../core/services/runtime_self_model_builder.py#L911) |
| function | `_build_summary` | `(layers, boundaries)` | Build a compact summary for prompt injection. | [src](../../../core/services/runtime_self_model_builder.py#L966) |

## `core/services/runtime_self_model_identity.py`
_Runtime self-model — identity awareness (self-insight, narrative identity,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_identity.py#L37) |
| function | `_self_insight_source_snapshot` | `()` | Safely gather bounded insight-bearing seams for self-insight derivation. | [src](../../../core/services/runtime_self_model_identity.py#L88) |
| function | `_derive_self_insight_awareness` | `(*, sources, mineness, flow_state, wonder, longing)` | Derive a bounded self-insight surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_identity.py#L200) |
| function | `_self_insight_narrative` | `(*, insight_state, identity_relation, insight_source)` | Compact self-insight narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L338) |
| function | `build_self_insight_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for self-insight awareness. | [src](../../../core/services/runtime_self_model_identity.py#L375) |
| function | `_derive_narrative_identity_continuity` | `(*, self_insight, sources, mineness, flow_state, wonder, longing)` | Derive a bounded narrative-identity-continuity surface. | [src](../../../core/services/runtime_self_model_identity.py#L476) |
| function | `_narrative_identity_continuity_narrative` | `(*, continuity_state, pattern_relation, identity_source)` | Compact identity-continuity narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L610) |
| function | `build_narrative_identity_continuity_prompt_section` | `()` | Compact heartbeat-side prompt section for narrative identity continuity. | [src](../../../core/services/runtime_self_model_identity.py#L645) |
| function | `_derive_dream_identity_carry_awareness` | `(*, self_insight, identity_continuity, sources, dream_influence, dream_articulation)` | Derive when dream carry begins to shape identity rather than just recur. | [src](../../../core/services/runtime_self_model_identity.py#L760) |
| function | `_dream_identity_carry_narrative` | `(*, carry_state, dream_self_relation, dream_identity_source, influence_target)` | Compact dream identity carry narrative. Empty when quiet. | [src](../../../core/services/runtime_self_model_identity.py#L862) |
| function | `build_dream_identity_carry_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for dream carry identity shaping. | [src](../../../core/services/runtime_self_model_identity.py#L893) |
| function | `build_cognitive_core_experiment_awareness_prompt_section` | `()` | Compact heartbeat-side prompt section for cognitive-core experiment state. | [src](../../../core/services/runtime_self_model_identity.py#L978) |
| function | `_idle_consolidation_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1024) |
| function | `_epistemic_runtime_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1043) |
| function | `_subagent_ecology_surface` | `()` | — | [src](../../../core/services/runtime_self_model_identity.py#L1059) |

## `core/services/runtime_self_model_state.py`
_Runtime self-model — base state surfaces + temporal/mineness awareness._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_facade` | `()` | Return the facade module so monkeypatch-through-facade is honored. | [src](../../../core/services/runtime_self_model_state.py#L17) |
| function | `_embodied_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L29) |
| function | `_loop_runtime_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L45) |
| function | `_runtime_task_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L64) |
| function | `_runtime_flow_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L87) |
| function | `_runtime_hook_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L110) |
| function | `_browser_body_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L144) |
| function | `_standing_orders_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L176) |
| function | `_layered_memory_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L197) |
| function | `_affective_meta_state_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L218) |
| function | `_experiential_runtime_context_surface` | `()` | — | [src](../../../core/services/runtime_self_model_state.py#L233) |
| function | `_inner_voice_daemon_surface` | `()` | Read inner voice daemon state for self-model integration. | [src](../../../core/services/runtime_self_model_state.py#L249) |
| function | `_derive_support_stream_awareness` | `(experiential, inner_voice)` | Derive compact self-aware support stream state. | [src](../../../core/services/runtime_self_model_state.py#L265) |
| function | `_runtime_self_appraisal_record` | `(*, kind, state, evidence, confidence, allowed_effects, ttl_minutes)` | Structured source-truth record for runtime self-model renderings. | [src](../../../core/services/runtime_self_model_state.py#L342) |
| function | `_derive_subjective_temporal_feel` | `(experiential, inner_voice)` | Derive a compact subjective temporal feel from existing runtime truth. | [src](../../../core/services/runtime_self_model_state.py#L367) |
| function | `_temporal_narrative` | `(temporal_state, felt_proximity, return_signal, persistence_feel, gap_minutes)` | Compact self-awareness narrative for felt time. | [src](../../../core/services/runtime_self_model_state.py#L468) |
| function | `_mineness_source_snapshot` | `()` | Gather the minimal runtime truth needed for mineness derivation. | [src](../../../core/services/runtime_self_model_state.py#L528) |
| function | `_derive_mineness_ownership` | `(*, experiential, inner_voice, support_stream, temporal_feel, sources)` | Derive a bounded mineness/ownership surface from existing runtime truth. | [src](../../../core/services/runtime_self_model_state.py#L578) |
| function | `_mineness_narrative` | `(*, ownership_state, carried_thread_state, carried_thread_count, brain_top_focus, brain_continuity, open_loop_signal, voice_mode, support_posture, felt_proximity)` | Compact mineness narrative. Empty in ambient default. | [src](../../../core/services/runtime_self_model_state.py#L680) |
| function | `build_mineness_ownership_prompt_section` | `()` | Compact heartbeat-side prompt section for mineness/ownership. | [src](../../../core/services/runtime_self_model_state.py#L714) |

