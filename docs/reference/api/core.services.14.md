# `core.services.14` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/jarvis_brain_visibility.py`
_Privacy-gate for Jarvis Brain recall._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_owner_id` | `()` | Hentet via owner_resolver. Wrapped så tests kan monkeypatche. | [src](../../../core/services/jarvis_brain_visibility.py#L14) |
| function | `can_recall` | `(entry_visibility, ceiling)` | True if entry's visibility is permitted at the given ceiling. | [src](../../../core/services/jarvis_brain_visibility.py#L30) |
| function | `session_visibility_ceiling` | `(session)` | Beregn visibility-ceiling for en session. | [src](../../../core/services/jarvis_brain_visibility.py#L35) |

## `core/services/jarvisx_bridge.py`
_JarvisX tool-bridge — bidirectional dispatch over WebSocket._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internal_dispatch_token` | `()` | Shared-secret som BEGGE processer kan udlede ens. | [src](../../../core/services/jarvisx_bridge.py#L47) |
| function | `_api_port` | `()` | Port for jarvis-api-procesen (hvor broen lever). Default 8080. | [src](../../../core/services/jarvisx_bridge.py#L88) |
| function | `_runtime_port` | `()` | Port for jarvis-runtime-procesen (autonome/wakeup-runs). Default 8011. | [src](../../../core/services/jarvisx_bridge.py#L99) |
| function | `_port_for_process` | `(role)` | Localhost-port for procesrollen. Begge processer kører SAMME uvicorn-app | [src](../../../core/services/jarvisx_bridge.py#L110) |
| function | `_looks_like_closed_ws` | `(exc)` | Er dette en 'send over en allerede-lukket WebSocket'-fejl? Starlette/uvicorn | [src](../../../core/services/jarvisx_bridge.py#L116) |
| function | `_ws_is_closed` | `(ws)` | Bedste-effort: er WS'en allerede lukket? Self-safe → False når ukendt, så vi | [src](../../../core/services/jarvisx_bridge.py#L126) |
| class | `BridgeConnection` | `` | One live bridge connection. WS object is platform-dependent. | [src](../../../core/services/jarvisx_bridge.py#L145) |
| method | `BridgeConnection.send_raw` | `(self, data, *, timeout_s=…)` | Send raw JSON over WS with lock and timeout. | [src](../../../core/services/jarvisx_bridge.py#L174) |
| method | `BridgeConnection.send_invoke` | `(self, *, correlation_id, tool, args, timeout_ms)` | Send tool_invoke over WS and register the pending future. | [src](../../../core/services/jarvisx_bridge.py#L206) |
| method | `BridgeConnection.deliver_result` | `(self, *, correlation_id, status, result=…, error=…)` | Complete the pending future for this correlation_id. | [src](../../../core/services/jarvisx_bridge.py#L241) |
| method | `BridgeConnection.cancel_all_pending` | `(self, *, reason=…)` | Cancel all in-flight calls (e.g. on WS disconnect). | [src](../../../core/services/jarvisx_bridge.py#L286) |
| class | `BridgeRegistry` | `` | Process-local registry of active bridges: user_id → client_id → bro. | [src](../../../core/services/jarvisx_bridge.py#L304) |
| method | `BridgeRegistry.__init__` | `(self)` | — | [src](../../../core/services/jarvisx_bridge.py#L317) |
| method | `BridgeRegistry._client_key` | `(conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L322) |
| method | `BridgeRegistry.register` | `(self, conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L325) |
| method | `BridgeRegistry.unregister` | `(self, conn)` | Remove ONLY if the registered bridge for this client IS this conn. | [src](../../../core/services/jarvisx_bridge.py#L347) |
| method | `BridgeRegistry._evict_if_current` | `(self, user_id, conn, *, reason)` | Fjern en stale/død bro fra registret HVIS den stadig er den aktuelle for | [src](../../../core/services/jarvisx_bridge.py#L362) |
| method | `BridgeRegistry._publish_presence` | `(self)` | Publicér dette registrys bro'er til shared_cache, så DEN ANDEN proces (og | [src](../../../core/services/jarvisx_bridge.py#L379) |
| method | `BridgeRegistry._diagnose_no_bridge` | `(self, user_id, *, stage)` | Fastslå HVORFOR der ikke er en bro for user_id (i stedet for et blindt | [src](../../../core/services/jarvisx_bridge.py#L407) |
| method | `BridgeRegistry._foretrukken` | `(klienter)` | Broen der bruges naar intet vaerktoej peger et bestemt sted hen. | [src](../../../core/services/jarvisx_bridge.py#L445) |
| method | `BridgeRegistry.get_bridge` | `(self, user_id, *, tool=…)` | Broen for ``user_id`` — og med ``tool`` DEN der kan udfoere det. | [src](../../../core/services/jarvisx_bridge.py#L456) |
| method | `BridgeRegistry.list_bridges` | `(self, user_id)` | Alle forbundne klienter for en bruger (computer OG telefon). | [src](../../../core/services/jarvisx_bridge.py#L493) |
| method | `BridgeRegistry.list_user_ids` | `(self)` | user_id'er med en aktiv bro (til bro_broker / override-switch). | [src](../../../core/services/jarvisx_bridge.py#L497) |
| method | `BridgeRegistry.clear` | `(self)` | Test helper — drop all registrations. | [src](../../../core/services/jarvisx_bridge.py#L501) |
| method | `BridgeRegistry.dispatch` | `(self, *, user_id, tool, args, timeout_s=…, allow_cross_process=…)` | Send tool_invoke to user's bridge, await result or timeout. | [src](../../../core/services/jarvisx_bridge.py#L508) |
| method | `BridgeRegistry._dispatch_without_local_bridge` | `(self, *, user_id, tool, args, timeout_s, allow_cross_process, stage)` | Ingen LEVENDE lokal bro for user_id (aldrig registreret, eller netop evictet | [src](../../../core/services/jarvisx_bridge.py#L608) |
| method | `BridgeRegistry._forward_cross_process` | `(self, *, user_id, tool, args, timeout_s, target_port=…)` | HTTP-forward dispatch til den proces der holder broen (dens interne endpoint). | [src](../../../core/services/jarvisx_bridge.py#L663) |
| function | `set_main_loop` | `(loop)` | Register the main uvicorn loop. Called from app startup. | [src](../../../core/services/jarvisx_bridge.py#L750) |
| function | `get_main_loop` | `()` | Return the registered main loop, or None if not set yet. | [src](../../../core/services/jarvisx_bridge.py#L756) |

## `core/services/jc_tool_telemetry.py`
_jc_tool_telemetry.py — per-tool eventbus telemetry for jarvis-code's_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `publish_tool_step` | `(*, tool, status, duration_ms=…, bytes_=…, user_id=…, session_id=…)` | Publish one `tool.jc_step` eventbus event. Returns True on a | [src](../../../core/services/jc_tool_telemetry.py#L22) |
| function | `publish_tool_steps` | `(steps, *, user_id=…, session_id=…)` | Publish a BATCH of per-tool steps (the client's step envelope may | [src](../../../core/services/jc_tool_telemetry.py#L44) |

## `core/services/jobs_engine.py`
_Jobs Engine — proper async job queue with provider selection and cost tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_prune_completed_jobs` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L46) |
| class | `JobResult` | `` | — | [src](../../../core/services/jobs_engine.py#L73) |
| function | `_storage_path` | `()` | — | [src](../../../core/services/jobs_engine.py#L87) |
| function | `_load` | `()` | — | [src](../../../core/services/jobs_engine.py#L91) |
| function | `_save` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L121) |
| function | `register_handler` | `(job_type, handler)` | Register a handler function for a given job_type. | [src](../../../core/services/jobs_engine.py#L146) |
| function | `enqueue_job` | `(*, job_type, payload=…, allowed_providers=…, prefer_free_first=…, max_requests=…, max_tokens=…, max_usd=…, window_key=…, scheduled_job_id=…, priority=…)` | Create a new pending job. Returns job_id. | [src](../../../core/services/jobs_engine.py#L154) |
| function | `select_provider` | `(allowed, *, prefer_free_first=…)` | Pick the first usable provider from the list. | [src](../../../core/services/jobs_engine.py#L203) |
| function | `_pop_next_pending` | `(items)` | — | [src](../../../core/services/jobs_engine.py#L227) |
| function | `run_next_job` | `()` | Run the highest-priority pending job via its registered handler. | [src](../../../core/services/jobs_engine.py#L235) |
| function | `cancel_job` | `(job_id)` | — | [src](../../../core/services/jobs_engine.py#L319) |
| function | `sweep_zombie_jobs` | `(stale_seconds=…)` | Mark 'running' jobs older than stale_seconds as error. | [src](../../../core/services/jobs_engine.py#L330) |
| function | `list_jobs` | `(*, status=…, limit=…)` | — | [src](../../../core/services/jobs_engine.py#L375) |
| function | `build_jobs_engine_surface` | `()` | — | [src](../../../core/services/jobs_engine.py#L382) |

## `core/services/kerne_curator.py`
_Kerne-kurator — holder USER.md `## Kerne` kort og levende (blok A, 2026-09-04)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_should_run` | `(last_run_iso, now)` | — | [src](../../../core/services/kerne_curator.py#L33) |
| function | `_workspace_dir` | `()` | — | [src](../../../core/services/kerne_curator.py#L45) |
| function | `promotion_candidates` | `(workspace_dir)` | Lært-linjer der er brugt tit nok til at høre hjemme i Kerne. | [src](../../../core/services/kerne_curator.py#L50) |
| function | `demotion_candidates` | `(workspace_dir)` | De ældste Kerne-linjer der ligger ud over loftet (tomt når under). | [src](../../../core/services/kerne_curator.py#L70) |
| function | `_move_line` | `(*, text, to_core)` | Flyt én linje mellem `## Kerne` og `## Lært` i USER.md. Atomisk. | [src](../../../core/services/kerne_curator.py#L79) |
| function | `promote_to_kerne` | `(text)` | Flyt en Lært-linje op i Kerne (altid i prompten). | [src](../../../core/services/kerne_curator.py#L111) |
| function | `demote_from_kerne` | `(text)` | Flyt en Kerne-linje ned i Lært (kun når den er relevant). | [src](../../../core/services/kerne_curator.py#L116) |
| function | `build_proposal_text` | `(workspace_dir)` | Ugens ÉNE forslag — "" når Kerne er sund og intet er modnet. | [src](../../../core/services/kerne_curator.py#L121) |
| function | `run_kerne_curator` | `(*, force=…, now=…)` | Ugentlig kuratering. Self-throttlende og self-safe — kaster aldrig. | [src](../../../core/services/kerne_curator.py#L145) |

## `core/services/keyring_store.py`
_Per-bruger nøgle-håndtering (spec §16.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_keyring` | `()` | — | [src](../../../core/services/keyring_store.py#L31) |
| function | `_get_or_create_kek` | `()` | Master-KEK fra runtime.json; genereres + persisteres atomisk ved første brug. | [src](../../../core/services/keyring_store.py#L45) |
| function | `_server_get_dek` | `(user_id)` | Hent (eller generér + wrap) en brugers DEK fra DB, unwrapped med KEK. | [src](../../../core/services/keyring_store.py#L72) |
| function | `get_user_key` | `(user_id)` | Brugerens 256-bit DEK. Prøver OS keyring; ellers server-side KEK/DEK (headless). | [src](../../../core/services/keyring_store.py#L86) |
| function | `delete_user_key` | `(user_id)` | Slet en brugers DEK (GDPR §16.7) — krypteret data bliver derefter ulæseligt. | [src](../../../core/services/keyring_store.py#L102) |
| function | `derive_key_from_password` | `(password, salt)` | PBKDF2-HMAC-SHA256 nøgle-derivation (fallback, §16.3). 600k iterationer. | [src](../../../core/services/keyring_store.py#L126) |
| function | `new_salt` | `()` | Tilfældigt 16-byte salt (gemmes pr. bruger, ikke hemmeligt). | [src](../../../core/services/keyring_store.py#L134) |

## `core/services/layer_tension_daemon.py`
_Layer Tension daemon — detects when two or more cognitive layers pull in opposite directions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_layer_tension_daemon` | `(snapshot)` | Detect layer tensions from runtime snapshot. | [src](../../../core/services/layer_tension_daemon.py#L35) |
| function | `_detect_tensions` | `(snapshot)` | — | [src](../../../core/services/layer_tension_daemon.py#L61) |
| function | `_store_tension` | `(tension, now)` | — | [src](../../../core/services/layer_tension_daemon.py#L143) |
| function | `get_active_tensions` | `()` | — | [src](../../../core/services/layer_tension_daemon.py#L190) |
| function | `build_layer_tension_surface` | `()` | — | [src](../../../core/services/layer_tension_daemon.py#L194) |

## `core/services/learning_pipeline_orchestrator.py`
_Learning Pipeline Orchestrator — Phase 3 (Loop Closure)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/learning_pipeline_orchestrator.py#L44) |
| function | `is_enabled` | `()` | Check killswitch. | [src](../../../core/services/learning_pipeline_orchestrator.py#L48) |
| function | `set_enabled` | `(value)` | Toggle killswitch without restart. | [src](../../../core/services/learning_pipeline_orchestrator.py#L57) |
| function | `_recent_events` | `(*, families, minutes=…)` | Fetch recent events from eventbus by family, ordered newest-first. | [src](../../../core/services/learning_pipeline_orchestrator.py#L66) |
| function | `_route_self_evaluation` | `(event)` | self_evaluation outcome → learning_policy + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L94) |
| function | `_route_learning_policy_rule` | `(event)` | learning_policy.rule_created (conf ≥ 0.7 + evidence ≥ 2) → abstraction + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L151) |
| function | `_route_counterfactual_cycle` | `(event)` | counterfactual.cycle_complete → skill distiller + reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L212) |
| function | `_route_agent_run` | `(event)` | agent_run.completed → reasoning_store. | [src](../../../core/services/learning_pipeline_orchestrator.py#L261) |
| function | `run_pipeline` | `(*, force=…)` | Run one full pipeline routing cycle. | [src](../../../core/services/learning_pipeline_orchestrator.py#L296) |
| function | `run_reflect_cycle` | `()` | Thin wrapper for REFLECT phase integration. | [src](../../../core/services/learning_pipeline_orchestrator.py#L418) |

## `core/services/learning_policy_engine.py`
_Explicit learning policy engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_learning_policies_from_episode` | `(*, episode=…, source_run_id=…)` | Extract and reinforce active policy rules from a cognitive episode. | [src](../../../core/services/learning_policy_engine.py#L25) |
| function | `reinforce_learning_policy` | `(rule)` | Insert or strengthen a learning policy rule. | [src](../../../core/services/learning_policy_engine.py#L50) |
| function | `build_learning_policy_surface` | `(*, limit=…)` | Return active policy rules for prompt/conductor use. | [src](../../../core/services/learning_policy_engine.py#L101) |
| function | `build_learning_policy_prompt_section` | `(*, limit=…)` | — | [src](../../../core/services/learning_policy_engine.py#L130) |
| function | `_load_state` | `()` | — | [src](../../../core/services/learning_policy_engine.py#L145) |
| function | `_latest_episode` | `()` | — | [src](../../../core/services/learning_policy_engine.py#L152) |
| function | `_decode_episode` | `(row)` | — | [src](../../../core/services/learning_policy_engine.py#L157) |
| function | `_rule_from_episode` | `(*, episode, learning, attention, policy, source_run_id)` | — | [src](../../../core/services/learning_policy_engine.py#L167) |
| function | `_classify_rule_key` | `(*, policy_update, next_behavior, lesson)` | — | [src](../../../core/services/learning_policy_engine.py#L194) |
| function | `_target_context` | `(rule_key)` | — | [src](../../../core/services/learning_policy_engine.py#L209) |
| function | `_initial_confidence` | `(*, episode, learning)` | — | [src](../../../core/services/learning_policy_engine.py#L219) |
| function | `_surface_directive` | `(rules)` | — | [src](../../../core/services/learning_policy_engine.py#L233) |

## `core/services/ledger_canary.py`
_Efterfyld en session i ledgeren og slå skyggen til._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kolonner` | `(conn)` | — | [src](../../../core/services/ledger_canary.py#L44) |
| function | `backfill` | `(session_id)` | Skriv sessionens eksisterende beskeder ind i ledgeren. Idempotent. | [src](../../../core/services/ledger_canary.py#L49) |
| function | `enable_shadow` | `(session_id)` | Efterfyld, slå skyggen til, og MÅL med det samme om det holdt. | [src](../../../core/services/ledger_canary.py#L110) |
| function | `reseed` | `(session_id)` | Skriv sessionens ledger-hændelser HELT om, i tabellens rækkefølge. | [src](../../../core/services/ledger_canary.py#L138) |

## `core/services/ledger_recovery.py`
_Afbrudte sessioner: se på dem uden at røre dem, og luk dem kun med skriveret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `inspect` | `(session_id)` | Se på sessionen UDEN at røre den. Tager ingen lease, skriver intet. | [src](../../../core/services/ledger_recovery.py#L49) |
| function | `recover` | `(session_id, *, owner=…, grund=…)` | Luk en åben tur med en balancerende hændelse. Kræver skriveret. | [src](../../../core/services/ledger_recovery.py#L77) |

## `core/services/ledger_write_path.py`
_Skrivevejen for en session hvor LEDGEREN er sandheden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `LedgerWriteFailed` | `` | Skrivningen nåede ikke ledgeren. Kalderen har IKKE fået sin besked gemt. | [src](../../../core/services/ledger_write_path.py#L42) |
| function | `append_message` | `(session_id, *, role, content, created_at=…, user_id=…, workspace_name=…, reasoning_content=…, git_sha=…, content_json=…, message_id=…, owner=…)` | Skriv én besked gennem ledgeren og lad projektoren lave rækken. | [src](../../../core/services/ledger_write_path.py#L46) |

## `core/services/lessons.py`
_Lessons service — from mistake to next conversation (memory repair 2026-09-04, R4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_today` | `()` | — | [src](../../../core/services/lessons.py#L29) |
| function | `_topic_from` | `(text)` | — | [src](../../../core/services/lessons.py#L33) |
| function | `_clip` | `(text, n)` | — | [src](../../../core/services/lessons.py#L38) |
| function | `record_correction` | `(*, session_id, user_words, jarvis_words=…, topic=…)` | Bjørn corrected the previous turn. Active immediately — his word is authoritative. | [src](../../../core/services/lessons.py#L43) |
| function | `record_self_acknowledged_correction` | `(*, session_id, user_words, jarvis_words=…)` | Jarvis indroemmede selv at han tog fejl — brug Bjoerns foregaaende ord. | [src](../../../core/services/lessons.py#L65) |
| function | `record_tool_error` | `(*, tool_name, error_text, context=…)` | A tool call failed. Proposed until it happens twice, then active. | [src](../../../core/services/lessons.py#L108) |
| function | `record_review_lessons` | `(lessons, source)` | Self-review / regret / arc-rule lessons → proposed (active at evidence ≥ 2). | [src](../../../core/services/lessons.py#L125) |
| function | `_format` | `(lesson)` | — | [src](../../../core/services/lessons.py#L139) |
| function | `build_lessons_section` | `(user_message, *, limit_similar=…, limit_strong=…)` | Render the lessons block for the prompt, or "" when nothing is active. | [src](../../../core/services/lessons.py#L149) |

## `core/services/life_milestones.py`
_Life milestones — identity-defining moments surfaced in the prompt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_milestones_file` | `()` | — | [src](../../../core/services/life_milestones.py#L17) |
| function | `_manifest_file` | `()` | — | [src](../../../core/services/life_milestones.py#L21) |
| function | `get_milestones_for_prompt` | `(max_chars=…)` | Return a formatted milestones block for prompt injection, or None. | [src](../../../core/services/life_milestones.py#L25) |
| function | `get_manifest_excerpt` | `(max_chars=…)` | Return first ~600 chars of MANIFEST.md as a first-principles reminder. | [src](../../../core/services/life_milestones.py#L47) |
| function | `build_life_history_prompt_section` | `()` | Combine milestones + manifest excerpt into a prompt section. | [src](../../../core/services/life_milestones.py#L63) |
| function | `append_milestone` | `(text)` | Append a new milestone entry to MILESTONES.md. Returns True on success. | [src](../../../core/services/life_milestones.py#L71) |
| function | `build_life_milestones_surface` | `()` | — | [src](../../../core/services/life_milestones.py#L88) |
| function | `_emit_life_milestones_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/life_milestones.py#L103) |

## `core/services/life_projects.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_life_project` | `(*, title, why, source=…, source_id=…, priority=…)` | — | [src](../../../core/services/life_projects.py#L12) |
| function | `build_life_projects_surface` | `()` | — | [src](../../../core/services/life_projects.py#L36) |
| function | `abandon_life_project` | `(initiative_id, *, note=…)` | — | [src](../../../core/services/life_projects.py#L50) |
| function | `endorse_life_project` | `(initiative_id, *, note=…)` | «Det er i orden» — projektet lever videre, nu med et menneskes ja bag sig. | [src](../../../core/services/life_projects.py#L57) |
| function | `tick_life_projects_reassessment` | `(*, trigger=…, last_visible_at=…)` | Periodisk re-vurdering af aktive life projects. | [src](../../../core/services/life_projects.py#L66) |

## `core/services/lifecycle_hooks.py`
_Livscyklus-hooks server-side — paritet med jarvis-code._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_allow` | `(context=…)` | — | [src](../../../core/services/lifecycle_hooks.py#L85) |
| function | `matcher_matches` | `(matcher, tool_name, command=…)` | Rammer et matcher-moenster dette tool-kald? Ren. | [src](../../../core/services/lifecycle_hooks.py#L91) |
| function | `decide` | `(results)` | Saml flere hook-svar til ét. Ren. | [src](../../../core/services/lifecycle_hooks.py#L129) |
| function | `config_path` | `()` | `~/.jarvis-v2/config/hooks.json` — config er runtimens sandhed for | [src](../../../core/services/lifecycle_hooks.py#L161) |
| function | `load_hooks` | `()` | {haendelse: [hook, ...]}. Self-safe → tomt. | [src](../../../core/services/lifecycle_hooks.py#L168) |
| function | `hooks_for` | `(event)` | Konfigurerede hooks for én haendelse. Self-safe → tom liste. | [src](../../../core/services/lifecycle_hooks.py#L184) |
| function | `_run_command_hook` | `(hook, context, user_id=…)` | Koer et shell-script med kontekst paa stdin. Exit 2 = block (jarvis-codes | [src](../../../core/services/lifecycle_hooks.py#L192) |
| function | `_run_http_hook` | `(hook, context)` | POST konteksten; svarets `action`/`message` gaelder. Self-safe → allow. | [src](../../../core/services/lifecycle_hooks.py#L233) |
| function | `_run_command_hook_async` | `(hook, context, user_id=…)` | Operator-grenen, kaldt fra det loop broen selv lever paa. | [src](../../../core/services/lifecycle_hooks.py#L256) |
| function | `fire_async` | `(event, context, user_id=…)` | Som `fire`, men kan koere operator-hooks. Brug denne fra async-kode. | [src](../../../core/services/lifecycle_hooks.py#L282) |
| function | `run_hook` | `(event, hook, context, user_id=…)` | Koer ÉN hook. Self-safe → allow. | [src](../../../core/services/lifecycle_hooks.py#L313) |
| function | `_advar_om_uvirksom_dom` | `(event, dom)` | Sig det hoejt naar en hook doemmer paa en haendelse der ikke kan handle. | [src](../../../core/services/lifecycle_hooks.py#L332) |
| function | `fire` | `(event, context, user_id=…)` | Fyr alle hooks for en haendelse og saml dommen. Self-safe → allow. | [src](../../../core/services/lifecycle_hooks.py#L345) |

## `core/services/liveness_registry.py`
_Liveness-registry (Stage 2, liveness-audit 2026-06-15)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_table` | `(name)` | Returnér klassifikation for en tabel. Ukendt → 'unclassified' (IKKE 'død'). | [src](../../../core/services/liveness_registry.py#L89) |
| function | `is_alive` | `(name)` | True hvis tabellen IKKE er forældreløs/død. Afløst/manuel/aktiv tæller som levende. | [src](../../../core/services/liveness_registry.py#L97) |
| function | `liveness_summary` | `()` | Aggregeret overblik — til Mission Control / anti-konfabulations-flade. | [src](../../../core/services/liveness_registry.py#L102) |

## `core/services/living_executive.py`
_Living Executive — Jarvis' active impulse/choice/action loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/living_executive.py#L31) |
| function | `_load_state` | `()` | — | [src](../../../core/services/living_executive.py#L35) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/living_executive.py#L46) |
| function | `build_living_executive_surface` | `(*, limit=…)` | — | [src](../../../core/services/living_executive.py#L50) |
| function | `choose_impulse` | `(events)` | — | [src](../../../core/services/living_executive.py#L75) |
| function | `process_event` | `(event)` | — | [src](../../../core/services/living_executive.py#L87) |
| function | `run_once` | `(*, events=…)` | One non-daemon pass used by tests and manual MC experiments. | [src](../../../core/services/living_executive.py#L94) |
| function | `execute_impulse` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L104) |
| function | `_impulse_from_event` | `(event)` | — | [src](../../../core/services/living_executive.py#L138) |
| function | `_impulse` | `(*, source_event_id, source_kind, felt_signal, impulse, intensity, action_id, choice, payload, cooldown_key, cooldown_seconds=…)` | — | [src](../../../core/services/living_executive.py#L284) |
| function | `_action_schedule_self_wakeup` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L311) |
| function | `_action_record_focus_intent` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L330) |
| function | `_action_create_jarvis_brain_observation` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L349) |
| function | `_action_propose_tool_plan` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L364) |
| function | `_record_trace` | `(impulse, *, status, outcome, details=…)` | — | [src](../../../core/services/living_executive.py#L405) |
| function | `_attach_memory_precedents` | `(impulse)` | — | [src](../../../core/services/living_executive.py#L472) |
| function | `_recent_memory_precedents` | `(*, action_hint=…, tool_hint=…, limit=…)` | — | [src](../../../core/services/living_executive.py#L486) |
| function | `_choice_bias_from_precedents` | `(impulse, precedents)` | — | [src](../../../core/services/living_executive.py#L521) |
| function | `_emotional_choice_precedents` | `(*, limit)` | — | [src](../../../core/services/living_executive.py#L541) |
| function | `_tool_family` | `(tool_name)` | — | [src](../../../core/services/living_executive.py#L561) |
| function | `_runnable_tool_proposals` | `(*, tool_name, status, reason, precedents)` | — | [src](../../../core/services/living_executive.py#L569) |
| function | `_aftertaste` | `(*, status, impulse)` | — | [src](../../../core/services/living_executive.py#L630) |
| function | `start_listener` | `()` | — | [src](../../../core/services/living_executive.py#L642) |
| function | `stop_listener` | `()` | — | [src](../../../core/services/living_executive.py#L658) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/living_executive.py#L667) |

## `core/services/living_heartbeat_cycle.py`
_Living Heartbeat Cycle — Jarvis' inner life rhythm._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `determine_life_phase` | `(*, hour=…)` | Determine current life phase based on time of day. | [src](../../../core/services/living_heartbeat_cycle.py#L111) |
| function | `_should_enter_play_mode` | `()` | Return True when internal state calls for unstructured exploration. | [src](../../../core/services/living_heartbeat_cycle.py#L146) |
| function | `format_life_phase_for_prompt` | `(phase)` | Format life phase info for heartbeat prompt injection. | [src](../../../core/services/living_heartbeat_cycle.py#L166) |
| function | `build_living_heartbeat_cycle_surface` | `()` | MC surface for living heartbeat cycle. | [src](../../../core/services/living_heartbeat_cycle.py#L183) |
| function | `_emit_living_heartbeat_cycle_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/living_heartbeat_cycle.py#L194) |

## `core/services/llm_pricing.py`
_Central LLM-pris-tabel + cost-beregner (WS2, 13. jul 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `compute_cost_usd` | `(provider, model, *, cache_hit_tokens=…, cache_miss_tokens=…, output_tokens=…, input_tokens=…)` | Beregn cost_usd fra tokens × pris. Returnerer 0.0 for ukendte (provider, model). | [src](../../../core/services/llm_pricing.py#L31) |

## `core/services/local_intent_gate.py`
_Er dét vaerktoej faktisk bestilt? — afgjort af en lille lokal model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_cache_noegle` | `(besked, navn)` | — | [src](../../../core/services/local_intent_gate.py#L83) |
| function | `er_bestilt` | `(besked, navn, beskrivelse=…)` | Beder brugeren om noget hvor ``navn`` ville blive kaldt? | [src](../../../core/services/local_intent_gate.py#L90) |

## `core/services/local_small_model.py`
_Ét-ords-spoergsmaal til den lille lokale model paa Jarvis' eget kort._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `base_url` | `()` | — | [src](../../../core/services/local_small_model.py#L39) |
| function | `spoerg_et_ord` | `(system, bruger, *, timeout_s=…)` | Foerste HELE ord af modellens svar, med STORE bogstaver. ``None`` = intet svar. | [src](../../../core/services/local_small_model.py#L47) |

## `core/services/local_tool_broker.py`
_Local-tool broker (Path B — server-owned transcript, client-local execution)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_Pending` | `` | — | [src](../../../core/services/local_tool_broker.py#L33) |
| function | `register` | `(call_id, *, session_id, name=…)` | Register a tool_call the server is about to hand to the local client. | [src](../../../core/services/local_tool_broker.py#L47) |
| function | `wait` | `(call_id, timeout=…)` | Block until the client resolves ``call_id`` (must be register()'d first) or | [src](../../../core/services/local_tool_broker.py#L56) |
| function | `collect_results` | `(call_ids, timeout=…)` | Wait on several already-register()'d call_ids (one client turn's tool batch) and | [src](../../../core/services/local_tool_broker.py#L73) |
| function | `resolve` | `(call_id, content, *, is_error=…)` | Called by POST /chat/tool_results. Deliver the client's result to the waiting run. | [src](../../../core/services/local_tool_broker.py#L84) |
| function | `pending_call_ids` | `(session_id)` | The call_ids currently awaiting a client result for a session (diagnostics). | [src](../../../core/services/local_tool_broker.py#L97) |
| function | `cancel_session` | `(session_id)` | Fail all pending calls for a session (e.g. client disconnected). Returns count. | [src](../../../core/services/local_tool_broker.py#L104) |

## `core/services/long_arc_synthesizer.py`
_Long-arc synthesizer — monthly / quarterly / annual narrative integration._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_arcs_dir` | `()` | — | [src](../../../core/services/long_arc_synthesizer.py#L37) |
| function | `_existing_arcs` | `(period)` | — | [src](../../../core/services/long_arc_synthesizer.py#L43) |
| function | `_gather_weekly_manifests` | `(weeks_back)` | Read recent WEEKLY_MANIFEST.md files (only one exists; we read its current content). | [src](../../../core/services/long_arc_synthesizer.py#L47) |
| function | `_gather_crisis_markers` | `(days)` | — | [src](../../../core/services/long_arc_synthesizer.py#L59) |
| function | `_gather_drift` | `(days)` | — | [src](../../../core/services/long_arc_synthesizer.py#L67) |
| function | `_gather_closed_goals` | `(days)` | — | [src](../../../core/services/long_arc_synthesizer.py#L75) |
| function | `_build_synthesis_prompt` | `(*, period, days, weekly, crises, drift, goals)` | — | [src](../../../core/services/long_arc_synthesizer.py#L89) |
| function | `synthesize_arc` | `(*, period)` | Generate a single arc (monthly/quarterly/annual). Skips if recent one exists. | [src](../../../core/services/long_arc_synthesizer.py#L133) |
| function | `list_arcs` | `(*, period=…)` | — | [src](../../../core/services/long_arc_synthesizer.py#L208) |
| function | `_exec_synthesize_arc` | `(args)` | — | [src](../../../core/services/long_arc_synthesizer.py#L228) |
| function | `_exec_list_arcs` | `(args)` | — | [src](../../../core/services/long_arc_synthesizer.py#L232) |

## `core/services/long_horizon_goals.py`
_Long-horizon goals — persistent objectives across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_goal` | `(*, title, description=…, priority=…, target_date=…, tags=…, created_by=…)` | — | [src](../../../core/services/long_horizon_goals.py#L32) |
| function | `update_goal` | `(*, goal_id, note, progress_delta=…, new_status=…, source=…)` | — | [src](../../../core/services/long_horizon_goals.py#L64) |
| function | `edit_goal` | `(goal_id, *, title=…, description=…, priority=…, target_date=…, tags=…)` | — | [src](../../../core/services/long_horizon_goals.py#L107) |
| function | `delete_goal` | `(goal_id)` | — | [src](../../../core/services/long_horizon_goals.py#L126) |
| function | `get_goal` | `(goal_id)` | — | [src](../../../core/services/long_horizon_goals.py#L136) |
| function | `get_goal_with_history` | `(goal_id, *, history_limit=…)` | — | [src](../../../core/services/long_horizon_goals.py#L140) |
| function | `list_active_goals` | `(*, limit=…)` | — | [src](../../../core/services/long_horizon_goals.py#L149) |
| function | `list_all_goals` | `(*, limit=…)` | — | [src](../../../core/services/long_horizon_goals.py#L153) |
| function | `format_active_goals_for_heartbeat` | `(*, max_goals=…)` | Compact single-paragraph summary for heartbeat prompt injection. | [src](../../../core/services/long_horizon_goals.py#L157) |
| function | `get_stats` | `()` | — | [src](../../../core/services/long_horizon_goals.py#L177) |

## `core/services/longing_signal_daemon.py`
_Longing-toward-user signal daemon — Spor-1 of generative autonomy._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_runtime_db_path` | `()` | — | [src](../../../core/services/longing_signal_daemon.py#L42) |
| function | `_hours_since` | `(iso_ts)` | Return hours since the given ISO timestamp, or None if invalid. | [src](../../../core/services/longing_signal_daemon.py#L46) |
| function | `_last_user_message_timestamp` | `()` | Return ISO timestamp of the most recent user-initiated visible turn. | [src](../../../core/services/longing_signal_daemon.py#L59) |
| function | `_last_jarvis_outreach_timestamp` | `()` | Return ISO timestamp of the last Jarvis-initiated outreach. | [src](../../../core/services/longing_signal_daemon.py#L88) |
| function | `_last_user_topic` | `()` | Best-effort recent user topic — short snippet from latest user message. | [src](../../../core/services/longing_signal_daemon.py#L115) |
| function | `compute_longing_intensity` | `()` | Compute current longing-toward-user intensity and supporting context. | [src](../../../core/services/longing_signal_daemon.py#L140) |
| function | `run_longing_signal_daemon_tick` | `()` | One tick of the longing daemon. Called by daemon_manager on cadence. | [src](../../../core/services/longing_signal_daemon.py#L200) |
| function | `build_longing_signal_daemon_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/longing_signal_daemon.py#L267) |

## `core/services/loop_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_loop_runtime_surface` | `()` | — | [src](../../../core/services/loop_runtime.py#L14) |
| function | `_build_loop_runtime_surface_uncached` | `()` | — | [src](../../../core/services/loop_runtime.py#L22) |
| function | `build_loop_runtime_from_sources` | `(*, open_loop_surface, proactive_loop_surface, quiet_initiative, previous=…, now=…)` | — | [src](../../../core/services/loop_runtime.py#L45) |
| function | `build_loop_runtime_prompt_section` | `(surface=…)` | — | [src](../../../core/services/loop_runtime.py#L110) |
| function | `_open_loop_items` | `(surface, *, previous_items)` | — | [src](../../../core/services/loop_runtime.py#L142) |
| function | `_proactive_loop_items` | `(surface, *, previous_items)` | — | [src](../../../core/services/loop_runtime.py#L179) |
| function | `_quiet_initiative_item` | `(quiet, *, previous_items, built_at)` | — | [src](../../../core/services/loop_runtime.py#L217) |
| function | `_loop_item_sort_key` | `(item)` | — | [src](../../../core/services/loop_runtime.py#L260) |
| function | `_reason_code_for_open_loop` | `(status)` | — | [src](../../../core/services/loop_runtime.py#L271) |
| function | `_reason_code_for_proactive_loop` | `(status, loop_state)` | — | [src](../../../core/services/loop_runtime.py#L279) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/loop_runtime.py#L288) |

## `core/services/loyalty_gradient_signal_tracking.py`
_Loyalty-gradient signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_loyalty_gradient_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L43) |
| function | `refresh_runtime_loyalty_gradient_signal_statuses` | `()` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L91) |
| function | `build_runtime_loyalty_gradient_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L95) |
| function | `_extract_loyalty_gradient_candidates` | `(*, run_id)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L99) |
| function | `_build_candidate` | `(*, domain_key, attachment_topology, relation_continuity, meaning, witness, chronicle_brief, metabolism, forgetting_candidate)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L185) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L332) |
| function | `_loyalty_gradient_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L357) |
| function | `_derive_gradient_score` | `(*, attachment_weight, attachment_state, relation_weight, meaning_weight, witness_status, witness_persistence, brief_weight, metabolism_state, metabolism_weight, forgetting_state)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L384) |
| function | `_score_to_weight` | `(score)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L419) |
| function | `_derive_gradient_state` | `(*, attachment_state, gradient_weight, witness_status, forgetting_state)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L427) |
| function | `_gradient_summary` | `(*, focus, gradient_state, gradient_weight, forgetting_candidate)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L443) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L476) |
| function | `_humanize_focus` | `(value)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L483) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L487) |
| function | `_merge_fragments` | `(*fragments)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L493) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L506) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L515) |

## `core/services/mail_checker_daemon.py`
_Mail checker daemon — checks jarvis@srvlab.dk inbox for new mail._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_automated` | `(sender, subject)` | True for bounces og autosvar — maskinstøj, ikke post der skal svares på. | [src](../../../core/services/mail_checker_daemon.py#L68) |
| function | `_is_stale` | `(date_header, now=…)` | True hvis mailen er ældre end _MAX_AGE_HOURS. | [src](../../../core/services/mail_checker_daemon.py#L73) |
| function | `_evaluate_mail` | `(sender, subject, snippet)` | Use LLM to evaluate whether a mail needs a response and draft one. | [src](../../../core/services/mail_checker_daemon.py#L93) |
| function | `_send_auto_reply` | `(to_addr, subject, reply_body)` | Send an auto-reply email via SMTP. Returns True on success. | [src](../../../core/services/mail_checker_daemon.py#L169) |
| function | `_extract_email_address` | `(sender)` | Extract bare email address from 'Name <email>' or plain email. | [src](../../../core/services/mail_checker_daemon.py#L191) |
| function | `_imap_connect` | `()` | Return an open IMAP connection. | [src](../../../core/services/mail_checker_daemon.py#L198) |
| function | `_fetch_recent` | `(conn, limit=…)` | Fetch up to `limit` most recent UNSEEN emails. | [src](../../../core/services/mail_checker_daemon.py#L207) |
| function | `_mark_as_seen` | `(imap_uids)` | Mark the given IMAP message IDs as \Seen. Returns count successfully marked. | [src](../../../core/services/mail_checker_daemon.py#L247) |
| function | `_load_mail_state` | `()` | Laes delt tilstand. Self-safe: tom dict ved enhver fejl. | [src](../../../core/services/mail_checker_daemon.py#L289) |
| function | `_save_mail_state` | `(*, check_at, new_count, senders, subjects, seen_ids)` | Skriv delt tilstand. Self-safe: en fejl her maa ikke vaelte tick'et. | [src](../../../core/services/mail_checker_daemon.py#L299) |
| function | `tick_mail_checker_daemon` | `()` | Main daemon tick — check for new mail, publish events for unseen messages. | [src](../../../core/services/mail_checker_daemon.py#L315) |
| function | `build_mail_checker_surface` | `()` | Return surface state for heartbeat context. | [src](../../../core/services/mail_checker_daemon.py#L528) |
| function | `get_latest_mail_info` | `()` | Return latest check info for other consumers. | [src](../../../core/services/mail_checker_daemon.py#L552) |
| function | `mail_awareness_section` | `()` | Ny post som en KENDSGERNING i prompten. "" naar der intet er. | [src](../../../core/services/mail_checker_daemon.py#L567) |
| function | `_mail_time_label` | `(timer)` | — | [src](../../../core/services/mail_checker_daemon.py#L610) |

## `core/services/malware_scan.py`
_Malware-scanning af uploads/vedhæftninger (spec §15.3.1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ScanReport` | `` | — | [src](../../../core/services/malware_scan.py#L21) |
| method | `ScanReport.safe` | `(self)` | — | [src](../../../core/services/malware_scan.py#L27) |
| method | `ScanReport.as_dict` | `(self)` | — | [src](../../../core/services/malware_scan.py#L30) |
| function | `clamav_available` | `()` | — | [src](../../../core/services/malware_scan.py#L35) |
| function | `scan_file` | `(path)` | Scan en fil med clamscan. Returnerer ScanReport. Blokerer aldrig på | [src](../../../core/services/malware_scan.py#L39) |
| function | `is_upload_allowed` | `(path, *, block_on_unavailable=…)` | Politik-helper: må denne upload gemmes/behandles? (§15.3.1) | [src](../../../core/services/malware_scan.py#L68) |

## `core/services/markdown_structure.py`
_Rekonstruér markdown-blokstruktur fra inline-markører._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_split_cells` | `(region)` | Split en `|`-afgrænset region i celler; drop ydre tomme (før første / | [src](../../../core/services/markdown_structure.py#L60) |
| function | `_reflow_line_table` | `(line)` | Hvis `line` indeholder en HEL tabel mast sammen på én linje | [src](../../../core/services/markdown_structure.py#L71) |
| function | `_reflow_crammed_tables` | `(text)` | Genskab tabeller hvis hele rækken er mast sammen på én linje. | [src](../../../core/services/markdown_structure.py#L120) |
| function | `_is_bullet_line` | `(line)` | — | [src](../../../core/services/markdown_structure.py#L131) |
| function | `_ensure_blank_before_lists` | `(text)` | Indsæt en blank linje før første bullet i en liste der følger prosa, så | [src](../../../core/services/markdown_structure.py#L136) |
| function | `_normalize_segment` | `(text)` | — | [src](../../../core/services/markdown_structure.py#L150) |
| function | `normalize_markdown_structure` | `(text)` | Genskab blokstruktur fra inline-markører. Beskytter kode-fences. | [src](../../../core/services/markdown_structure.py#L169) |

## `core/services/mcp_auth.py`
_OAuth/bearer til remote MCP-servere._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_expand_env` | `(value)` | `${MIN_NOEGLE}` slaas op i miljoeet, saa en config kan deles uden token. | [src](../../../core/services/mcp_auth.py#L33) |
| function | `_load` | `()` | — | [src](../../../core/services/mcp_auth.py#L38) |
| function | `_save` | `(data)` | — | [src](../../../core/services/mcp_auth.py#L45) |
| function | `get_token` | `(name)` | — | [src](../../../core/services/mcp_auth.py#L54) |
| function | `set_token` | `(name, *, access_token, refresh_token=…, expires_in=…, token_url=…, client_id=…, client_secret=…)` | — | [src](../../../core/services/mcp_auth.py#L59) |
| function | `needs_refresh` | `(name)` | — | [src](../../../core/services/mcp_auth.py#L81) |
| function | `refresh` | `(name)` | Kør refresh_token-grantet. False = intet at fornye, eller det fejlede. | [src](../../../core/services/mcp_auth.py#L91) |
| function | `resolve_headers` | `(name, config)` | Headers til en request mod *name*. | [src](../../../core/services/mcp_auth.py#L117) |

## `core/services/mcp_client.py`
_MCP-klient — stdio og HTTP, med trust-gate foran hver forbindelse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MCPClient` | `` | Én forbindelse til én MCP-server. | [src](../../../core/services/mcp_client.py#L46) |
| method | `MCPClient.__init__` | `(self, name, config)` | — | [src](../../../core/services/mcp_client.py#L49) |
| method | `MCPClient.connect` | `(self)` | Trust-gate først, DERNÆST forbindelse. Rækkefølgen er hele pointen. | [src](../../../core/services/mcp_client.py#L63) |
| method | `MCPClient._connect_stdio` | `(self)` | — | [src](../../../core/services/mcp_client.py#L80) |
| method | `MCPClient._connect_http` | `(self)` | — | [src](../../../core/services/mcp_client.py#L106) |
| method | `MCPClient.disconnect` | `(self)` | — | [src](../../../core/services/mcp_client.py#L121) |
| method | `MCPClient.connected` | `(self)` | — | [src](../../../core/services/mcp_client.py#L135) |
| method | `MCPClient._send_request` | `(self, method, params=…)` | — | [src](../../../core/services/mcp_client.py#L143) |
| method | `MCPClient._send_stdio` | `(self, req)` | — | [src](../../../core/services/mcp_client.py#L152) |
| method | `MCPClient._http_headers` | `(self)` | — | [src](../../../core/services/mcp_client.py#L179) |
| method | `MCPClient._send_http` | `(self, req)` | — | [src](../../../core/services/mcp_client.py#L186) |
| method | `MCPClient._send_notification` | `(self, method)` | — | [src](../../../core/services/mcp_client.py#L204) |
| method | `MCPClient._initialize` | `(self)` | MCP kræver dette håndtryk før alt andet — mange servere afviser | [src](../../../core/services/mcp_client.py#L217) |
| method | `MCPClient._discover_tools` | `(self)` | — | [src](../../../core/services/mcp_client.py#L231) |
| method | `MCPClient.call_tool` | `(self, tool_name, arguments)` | — | [src](../../../core/services/mcp_client.py#L238) |

## `core/services/mcp_manager.py`
_MCP-manager — forbinder registerets servere og eksponerer deres værktøjer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_server_config` | `(navn)` | — | [src](../../../core/services/mcp_manager.py#L27) |
| function | `get_client` | `(navn, *, connect=…)` | Hent (og evt. forbind) klienten for *navn*. None hvis ukendt server. | [src](../../../core/services/mcp_manager.py#L40) |
| function | `disconnect_all` | `()` | — | [src](../../../core/services/mcp_manager.py#L58) |
| function | `status` | `()` | Hvilke servere kendes, hvilke er godkendt, hvilke er forbundet? | [src](../../../core/services/mcp_manager.py#L68) |
| function | `list_tools` | `(navn)` | — | [src](../../../core/services/mcp_manager.py#L88) |
| function | `call` | `(navn, vaerktoej, arguments=…)` | — | [src](../../../core/services/mcp_manager.py#L99) |

## `core/services/mcp_registry.py`
_MCP-server-registry (§4.6) — brugerens konfigurerede MCP-endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/mcp_registry.py#L17) |
| function | `list_mcp_servers` | `()` | — | [src](../../../core/services/mcp_registry.py#L24) |
| function | `add_mcp_server` | `(name, url)` | — | [src](../../../core/services/mcp_registry.py#L28) |
| function | `remove_mcp_server` | `(server_id)` | — | [src](../../../core/services/mcp_registry.py#L40) |

## `core/services/mcp_trust.py`
_MCP-tillid: allowliste + TOFU-pinning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/mcp_trust.py#L35) |
| function | `_save` | `(data)` | — | [src](../../../core/services/mcp_trust.py#L44) |
| function | `is_allowlisted` | `(name)` | — | [src](../../../core/services/mcp_trust.py#L48) |
| function | `allow` | `(name)` | Godkend et servernavn. Idempotent. | [src](../../../core/services/mcp_trust.py#L52) |
| function | `revoke` | `(name)` | Fjern fra allowlisten OG drop pinnen. Idempotent. | [src](../../../core/services/mcp_trust.py#L65) |
| function | `list_trust` | `()` | — | [src](../../../core/services/mcp_trust.py#L80) |
| function | `_sha256_file` | `(path)` | — | [src](../../../core/services/mcp_trust.py#L85) |
| function | `check_pin_stdio` | `(name, command)` | Pin en stdio-servers binær (sti + sha256). Første syn pinner. | [src](../../../core/services/mcp_trust.py#L96) |
| function | `check_pin_http` | `(name, url)` | Pin en HTTP-servers vaert. Første syn pinner. | [src](../../../core/services/mcp_trust.py#L117) |

## `core/services/meaning_significance_signal_tracking.py`
_Meaning/significance signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_meaning_significance_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L39) |
| function | `refresh_runtime_meaning_significance_signal_statuses` | `()` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L65) |
| function | `build_runtime_meaning_significance_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L69) |
| function | `_extract_meaning_significance_candidates` | `(*, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L73) |
| function | `_build_candidate` | `(*, run_id, focus, relation_continuity, chronicle_brief, chronicle_proposal, executive_contradiction, temporal_promotion, regulation)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L103) |
| function | `_latest_chronicle_brief` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L240) |
| function | `_latest_chronicle_proposal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L252) |
| function | `_latest_executive_contradiction` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L264) |
| function | `_latest_temporal_promotion` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L276) |
| function | `_latest_regulation` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L288) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L300) |
| function | `_derive_meaning_type` | `(*, has_proposal, continuity_state, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L308) |
| function | `_derive_meaning_weight` | `(*, chronicle_weight, continuity_weight, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L324) |
| function | `_derive_status` | `(*, proposal_status, brief_status, continuity_status)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L343) |
| function | `_grounding_mode` | `(*, has_brief, has_proposal, has_contradiction, has_promotion, has_regulation)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L351) |
| function | `_meaning_summary` | `(*, focus, meaning_type, meaning_weight, continuity_alignment, continuity_watchfulness, regulation_pressure)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L373) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L390) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L398) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L409) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L421) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L433) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L450) |
| function | `_meaning_significance_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L493) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L513) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L520) |
| function | `_weight_from_summary` | `(value, *, canonical_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L528) |

## `core/services/memory_breathing.py`
_Memory Breathing — use-strengthens, disuse-fades._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get_record_salience` | `(record_id)` | — | [src](../../../core/services/memory_breathing.py#L33) |
| function | `reinforce` | `(record_ids, *, boost=…)` | Raise salience of the given records. | [src](../../../core/services/memory_breathing.py#L45) |
| function | `record_access` | `(record_ids, *, context=…, boost=…)` | Log access and reinforce simultaneously. | [src](../../../core/services/memory_breathing.py#L75) |
| function | `recent_access_stats` | `(*, limit=…)` | Return stats about recent access pattern. | [src](../../../core/services/memory_breathing.py#L97) |
| function | `build_memory_breathing_surface` | `()` | — | [src](../../../core/services/memory_breathing.py#L114) |
| function | `reset_memory_breathing` | `()` | Reset access log (for testing). | [src](../../../core/services/memory_breathing.py#L130) |

## `core/services/memory_consolidation_nudge.py`
_Memory consolidation nudge — unconditional prompt section._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `memory_consolidation_nudge_section` | `()` | Return a short prompt section that fires every turn unconditionally. | [src](../../../core/services/memory_consolidation_nudge.py#L13) |

## `core/services/memory_decay_daemon.py`
_Memory decay daemon — selective forgetting and re-discovery._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_memory_decay_daemon` | `()` | Run daily decay cycle. Returns {decayed, records_updated}. | [src](../../../core/services/memory_decay_daemon.py#L58) |
| function | `hold_fast` | `(record_id)` | Prevent a memory from decaying by resetting its salience to 1.0. | [src](../../../core/services/memory_decay_daemon.py#L96) |
| function | `maybe_rediscover` | `(force=…)` | Possibly surface a near-forgotten memory into the re-discovery buffer. | [src](../../../core/services/memory_decay_daemon.py#L101) |
| function | `get_latest_rediscovery` | `()` | — | [src](../../../core/services/memory_decay_daemon.py#L142) |
| function | `build_memory_decay_surface` | `()` | — | [src](../../../core/services/memory_decay_daemon.py#L146) |

