# `apps.api.jarvis_api.routes.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/mission_control_living_mind.py`
_Living Mind surface routes — daemon state endpoints for the Living Mind MC tab._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_api_only_mode` | `()` | True when this process runs without runtime services (jarvis-api split). | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L32) |
| function | `_proxy_runtime_surface` | `(path)` | Fetch a /mc/* surface from jarvis-runtime. Returns None on any failure. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L38) |
| function | `_surface` | `(path, local_fn)` | Return proxied data when in API-only mode, else call local_fn(). | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L53) |
| function | `mc_body_state` | `()` | Return Jarvis's circadian energy level and somatic phrase. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L67) |
| function | `mc_surprise_state` | `()` | Return Jarvis's latest self-surprise observation. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L74) |
| function | `mc_taste_state` | `()` | Return Jarvis's emergent aesthetic taste profile. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L81) |
| function | `mc_irony_state` | `()` | Return Jarvis's latest ironic observation. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L88) |
| function | `mc_thought_stream` | `()` | Return Jarvis's latest thought stream fragment and buffer. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L95) |
| function | `mc_thought_proposals` | `()` | Return pending and resolved thought-action proposals. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L102) |
| function | `mc_resolve_thought_proposal` | `(proposal_id, body)` | Approve or dismiss a thought-action proposal. Body: {decision: 'approved'|'dismissed'} | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L109) |
| function | `mc_experienced_time` | `()` | Return Jarvis's current subjective felt time for the session. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L120) |
| function | `mc_development_narrative` | `()` | Return Jarvis's latest self-development narrative. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L127) |
| function | `mc_existential_wonder` | `()` | Return Jarvis's latest existential wonder question. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L134) |
| function | `mc_dream_insights` | `()` | Return persisted dream articulation insights. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L141) |
| function | `mc_code_aesthetic` | `()` | Return Jarvis's latest code aesthetic reflection. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L148) |
| function | `mc_user_model` | `()` | Return Jarvis's current theory-of-mind model of the user. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L155) |
| function | `mc_memory_decay` | `()` | Return memory decay state and recent re-discoveries. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L162) |
| function | `mc_memory_hold_fast` | `(record_id)` | Hold fast a memory — prevent it from decaying (salience reset to 1.0). | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L169) |
| function | `mc_desires` | `()` | Return Jarvis's current emergent appetites. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L177) |
| function | `mc_absence_state` | `()` | Return Jarvis's current absence quality signal. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L184) |
| function | `mc_creative_drift` | `()` | Return Jarvis's latest spontaneous creative drift idea. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L191) |
| function | `mc_curiosity_state` | `()` | Return Jarvis's latest curiosity signal and open questions. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L198) |
| function | `mc_meta_reflection` | `()` | Return Jarvis's latest cross-signal meta-insight. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L205) |
| function | `mc_conflict_signal` | `()` | Return Jarvis's latest detected inner conflict. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L212) |
| function | `mc_reflection_cycle` | `()` | Return Jarvis's latest pure experience reflection. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L219) |
| function | `mc_layer_tensions` | `()` | Return active inter-layer tensions — signals pulling in opposite directions. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L226) |
| function | `mc_dream_motifs` | `()` | Return dream motif clustering state and last run info. | [src](../../../apps/api/jarvis_api/routes/mission_control_living_mind.py#L233) |

## `apps/api/jarvis_api/routes/mission_control_runs_ops.py`
_Mission Control routes: runs, overview, events, costs, approvals, memory-pipeline, autonomy, initiatives, operations_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_liveness` | `(table=…)` | Liveness-sandheds-flade (Stage 2, anti-konfabulation): klassificér en tabel | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L14) |
| function | `mc_overview` | `()` | Aggregeret Mission Control-overblik: event-antal, cost-summering | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L25) |
| function | `mc_events` | `(limit=…, family=…)` | Seneste events fra event-bussen (op til `limit`), valgfrit filtreret | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L62) |
| function | `mc_costs` | `(limit=…)` | Cost-flade: telemetri-summering plus de seneste `limit` cost-rækker. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L80) |
| function | `mc_runs` | `(limit=…)` | Runs-flade: aktiv run, sidste udfald/capability-brug, de seneste | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L89) |
| function | `mc_approvals` | `(limit=…)` | Approvals-flade: de seneste `limit` approval-requests (med udledt | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L132) |
| function | `mc_memory_pipeline` | `(limit=…)` | Memory-pipeline status surface (added 2026-06-09). | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L203) |
| function | `mc_autonomy_proposals` | `(limit=…)` | MC surface for Niveau 2 autonomy proposal queue. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L369) |
| function | `mc_approve_autonomy_proposal` | `(proposal_id, note=…)` | Godkend et Niveau 2-autonomi-forslag via id, med valgfri resolution-note. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L383) |
| function | `mc_reject_autonomy_proposal` | `(proposal_id, note=…)` | Afvis et Niveau 2-autonomi-forslag via id, med valgfri resolution-note. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L393) |
| function | `mc_initiatives` | `(limit=…)` | MC surface for the persistent initiative queue — pending, acted, approved, rejected. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L403) |
| function | `mc_approve_initiative` | `(initiative_id, note=…)` | Approve a pending initiative so the heartbeat may act on it. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L416) |
| function | `mc_reject_initiative` | `(initiative_id, note=…)` | Reject and expire a pending initiative. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L426) |
| function | `mc_life_projects` | `()` | Mission Control surface for Jarvis-owned long-term intentions. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L436) |
| function | `mc_endorse_life_project` | `(initiative_id, note=…)` | Sig god for en langsigtet hensigt uden at afslutte den. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L442) |
| function | `mc_abandon_life_project` | `(initiative_id, note=…)` | Abandon a long-term intention without deleting its record. | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L452) |
| function | `mc_operations` | `(limit=…)` | Samlet operations-flade (3s cached): runtime-config, tool-intent, runs, | [src](../../../apps/api/jarvis_api/routes/mission_control_runs_ops.py#L461) |

## `apps/api/jarvis_api/routes/mission_control_runtime_config.py`
_Mission Control routes: adaptive/tool-intent, runtime-contract, heartbeat, visible-execution, capability-approval_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_capability_request_scope` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L16) |
| function | `_stored_capability_execution_args` | `(request)` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L23) |
| function | `mc_adaptive_planner` | `()` | Return the current bounded adaptive planner runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L35) |
| function | `mc_adaptive_reasoning` | `()` | Return the current bounded adaptive reasoning runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L41) |
| function | `mc_guided_learning` | `()` | Return the current bounded guided learning runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L51) |
| function | `mc_adaptive_learning` | `()` | Return the current bounded adaptive learning runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L61) |
| function | `mc_self_system_code_awareness` | `()` | Return the current bounded self system / code awareness runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L71) |
| function | `mc_tool_intent` | `()` | Return the current bounded approval-gated tool intent runtime state. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L77) |
| function | `mc_approval_feedback` | `()` | Return the approval-feedback surface (learning signal from past approvals/denials). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L83) |
| function | `mc_approve_tool_intent` | `()` | Approve the current pending tool intent from Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L89) |
| function | `mc_deny_tool_intent` | `()` | Deny the current pending tool intent from Mission Control. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L116) |
| function | `mc_private_brain` | `()` | Return the private-brain overview plus recent session-distillation entries. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L143) |
| function | `mc_runtime_contract` | `()` | Return the current runtime-contract state (active contract + candidates). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L152) |
| function | `mc_heartbeat` | `()` | Return the heartbeat runtime surface (current heartbeat state and policy). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L158) |
| function | `mc_emotional_memory` | `(limit=…)` | Closes cartographer dark-edge (2026-05-13): emotional_memory_engine | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L164) |
| function | `mc_heartbeat_tick` | `()` | Manually trigger one heartbeat tick and return its resulting state/tick/policy. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L173) |
| function | `mc_approve_runtime_contract_candidate` | `(candidate_id)` | Approve a runtime-contract candidate by id; returns the updated candidate. Raises 400 on invalid id. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L185) |
| function | `mc_reject_runtime_contract_candidate` | `(candidate_id)` | Reject a runtime-contract candidate by id; returns the updated candidate. Raises 400 on invalid id. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L198) |
| function | `mc_apply_runtime_contract_candidate` | `(candidate_id)` | Apply an approved runtime-contract candidate by id; returns the apply result. Raises 400 on invalid id. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L211) |
| function | `mc_runtime` | `()` | Return the aggregate Mission Control runtime surface. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L224) |
| function | `mc_visible_execution` | `()` | Return the visible-execution surface (current visible model/provider/auth) from live settings. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L230) |
| function | `mc_main_agent_selection` | `()` | Return the current main-agent selection surface (selected provider/model/auth profile). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L237) |
| function | `mc_ollama_models` | `()` | Return the Ollama models available for use as the visible target. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L243) |
| function | `mc_provider_models` | `(provider=…, auth_profile=…)` | Return the models available for the given provider (optionally scoped to an auth profile). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L249) |
| function | `mc_invoke_workspace_capability` | `(capability_id, approved=…, write_content=…, target_path=…, command_text=…)` | Invoke a workspace capability by id, passing through the approval flag and optional | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L263) |
| function | `mc_approve_capability_request` | `(request_id)` | Approve a capability-approval request by id (stamping approved_at now). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L286) |
| function | `mc_execute_capability_request` | `(request_id, write_content=…, command_text=…)` | Execute a previously approved capability-approval request. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L309) |
| function | `mc_approve_and_execute_capability_request` | `(request_id)` | Atomically approve, claim and execute a stored capability request once. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L426) |
| function | `mc_complete_development_focus` | `(focus_id)` | Manually mark a development focus as completed. | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L506) |
| function | `mc_update_visible_execution` | `(payload)` | Update the visible-execution settings (visible model provider/name/auth profile). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L538) |
| function | `mc_update_main_agent_selection` | `(payload)` | Select the main-agent target (provider/model, optional auth_profile). | [src](../../../apps/api/jarvis_api/routes/mission_control_runtime_config.py#L593) |

## `apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py`
_Mission Control routes: skills, memory, hardening, lab_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `mc_skills` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L14) |
| function | `mc_memory` | `(q=…, limit=…, scope=…)` | Search/list private retained memory records. | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L40) |
| function | `mc_hardening` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L119) |
| function | `mc_lab` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mission_control_skills_hardening_lab.py#L133) |

## `apps/api/jarvis_api/routes/mobile_memory.py`
_«Brug denne besked som hukommelse» — fra telefonen ind i hans hjerne._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `GemSomHukommelse` | `` | — | [src](../../../apps/api/jarvis_api/routes/mobile_memory.py#L31) |
| function | `_titel_af` | `(tekst)` | Foerste meningsfulde linje, klippet. En huskeseddel skal kunne skimmes. | [src](../../../apps/api/jarvis_api/routes/mobile_memory.py#L38) |
| function | `gem_som_hukommelse` | `(body)` | Gem en besked som en post i hjernen. Owner-only via global auth. | [src](../../../apps/api/jarvis_api/routes/mobile_memory.py#L48) |

## `apps/api/jarvis_api/routes/mobile_update.py`
_Mobil auto-updater: manifest + APK-download. Auth-scopet til en bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L18) |
| function | `_mobile_dir` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L23) |
| function | `mobile_latest` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L29) |
| function | `mobile_download` | `()` | — | [src](../../../apps/api/jarvis_api/routes/mobile_update.py#L45) |

## `apps/api/jarvis_api/routes/notifikationer.py`
_Notifikations-feeden. Scoper til den auth'ede bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AfgoerBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L22) |
| function | `_oversaet_fejl` | `(raa_fejl)` | Oversaet en teknisk/engelsk fejltekst til noget en almindelig bruger | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L34) |
| function | `_nuvaerende_bruger` | `()` | (user_id, er_owner). | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L41) |
| function | `_min_raekke` | `(notif_id, user_id)` | Raekken — kun hvis den er brugerens egen. Et gaettet id fra en anden | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L71) |
| function | `feed` | `(aktiv=…)` | Feedet. `aktiv` = den samtale klienten SIDDER I lige nu. | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L81) |
| function | `tidligere_feed` | `()` | Historikken. Samme form som feed() — én klient-type, to lister. | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L108) |
| function | `afgoer` | `(notif_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L125) |
| function | `set_` | `(notif_id)` | — | [src](../../../apps/api/jarvis_api/routes/notifikationer.py#L189) |

## `apps/api/jarvis_api/routes/notifikations_valg.py`
_Push-valg per slags. Scoper til den auth'ede bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SaetBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/notifikations_valg.py#L13) |
| function | `_bruger` | `()` | — | [src](../../../apps/api/jarvis_api/routes/notifikations_valg.py#L18) |
| function | `hent` | `()` | — | [src](../../../apps/api/jarvis_api/routes/notifikations_valg.py#L24) |
| function | `saet` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/notifikations_valg.py#L35) |

## `apps/api/jarvis_api/routes/oauth.py`
_OAuth connect-flow til plugin-connectors (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_close_page` | `(ok, msg)` | — | [src](../../../apps/api/jarvis_api/routes/oauth.py#L17) |
| function | `oauth_start` | `(provider)` | Returnér authorize-URL for den indloggede bruger. Desk åbner den i browseren. | [src](../../../apps/api/jarvis_api/routes/oauth.py#L32) |
| function | `oauth_callback` | `(provider, code=…, state=…, error=…)` | Browser-callback. Verificér state → byt code → gem token krypteret pr. bruger. | [src](../../../apps/api/jarvis_api/routes/oauth.py#L53) |

## `apps/api/jarvis_api/routes/openai_auth.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `openai_oauth_launch` | `(profile=…)` | — | [src](../../../apps/api/jarvis_api/routes/openai_auth.py#L14) |
| function | `openai_oauth_callback` | `(profile, request)` | — | [src](../../../apps/api/jarvis_api/routes/openai_auth.py#L29) |

## `apps/api/jarvis_api/routes/openai_compat.py`
_OpenAI-compatible proxy: /v1/chat/completions wrapping Jarvis visible lane._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `list_models` | `()` | OpenAI-compatible model list — exposes Jarvis as a single model. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L32) |
| function | `chat_completions` | `(request)` | OpenAI-compatible chat completion endpoint wrapping Jarvis' visible lane. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L48) |
| function | `_stream_response` | `(*, run_id, message, provider, model, session_id)` | Yield OpenAI-format SSE chunks from Jarvis' visible run. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L124) |
| function | `_drain_visible_run_text` | `(*, message, session_id)` | Run the visible pipeline to completion and return the assembled prose. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L179) |
| function | `_parse_sse_frame` | `(frame)` | Parse a webchat SSE frame ``event: <type>\ndata: <json>\n\n``. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L203) |
| function | `_resolve_model_provider` | `(model_param)` | Map a model parameter to (provider, model) tuple. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L224) |
| function | `_build_completion_response` | `(*, run_id, model, content, input_tokens, output_tokens)` | Build a standard OpenAI chat.completion response. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L259) |
| function | `_build_stream_chunk` | `(*, run_id, model, delta_content)` | Build a standard OpenAI chat.completion.chunk for streaming. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L288) |
| function | `_get_or_create_proxy_session` | `()` | Return the shared proxy chat session id. | [src](../../../apps/api/jarvis_api/routes/openai_compat.py#L317) |

## `apps/api/jarvis_api/routes/paste.py`
_Paste-store endpoints: eksternalisér store bruger-pastes + lazy resolve._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PasteSaveRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/paste.py#L23) |
| function | `save_paste_endpoint` | `(request)` | Gem en paste og returnér id + kompakt reference-streng. | [src](../../../apps/api/jarvis_api/routes/paste.py#L28) |
| function | `get_paste_endpoint` | `(paste_id)` | Slå fuld paste-tekst op (lazy resolve). 404 på ukendt id. | [src](../../../apps/api/jarvis_api/routes/paste.py#L45) |

## `apps/api/jarvis_api/routes/peak.py`
_Myldretids-tilstand til desk-headerens badge (30/9-2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `peak_state_endpoint` | `()` | Myldretids-tilstanden lige nu — grundlaget for desk-badgen. | [src](../../../apps/api/jarvis_api/routes/peak.py#L25) |

## `apps/api/jarvis_api/routes/plugins.py`
_Plugins & Kanaler routes (spec §5.4, Fase 6 #2). Tynde — blokerende arbejde_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/plugins.py#L14) |
| function | `plugins_overview` | `()` | Oversigt: tilgængelige plugins (manifester) + status + regelsæt. | [src](../../../apps/api/jarvis_api/routes/plugins.py#L29) |
| function | `channel_status` | `(plugin_id, status, detail=…)` | Lokal gateway rapporterer sin forbindelses-status (connected|failed|offline). | [src](../../../apps/api/jarvis_api/routes/plugins.py#L49) |
| function | `channel_inbound_ep` | `(plugin_id, body)` | Lokal gateway ruter en indkommende besked hertil. Serveren HÅNDHÆVER | [src](../../../apps/api/jarvis_api/routes/plugins.py#L58) |
| function | `channel_response` | `(plugin_id, session_id, after_ts=…)` | Gateway poller: seneste assistant-svar i sessionen nyere end after_ts. | [src](../../../apps/api/jarvis_api/routes/plugins.py#L88) |
| function | `get_plugin_ruleset` | `(plugin_id)` | — | [src](../../../apps/api/jarvis_api/routes/plugins.py#L110) |
| function | `put_plugin_ruleset` | `(plugin_id, ruleset)` | Gem regelsæt for et kanal-plugin. Hardblock for ALLE inkl. owner (§5.3). | [src](../../../apps/api/jarvis_api/routes/plugins.py#L118) |

## `apps/api/jarvis_api/routes/presence.py`
_Device-presence + proaktive desktop-notifikationer. Scoper til auth'et bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PingBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L18) |
| class | `AckBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L47) |
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L51) |
| function | `presence_ping` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L57) |
| function | `notifications_pending` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L97) |
| function | `notifications_ack` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L105) |
| function | `notification_preferences_get` | `()` | Notif-routing §6: app-UI læser brugerens kanal-præferencer. | [src](../../../apps/api/jarvis_api/routes/presence.py#L112) |
| function | `notification_preferences_set` | `(body)` | app-UI sætter kanal-præferencer (global + per-type + quiet hours). | [src](../../../apps/api/jarvis_api/routes/presence.py#L122) |
| function | `presence_debug` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L138) |
| function | `presence_state` | `()` | Spec E / E0 — TILSTANDS-KONTRAKTEN: Centralens ægte valens + selv-tilstand → jarvis-desk kan | [src](../../../apps/api/jarvis_api/routes/presence.py#L168) |

## `apps/api/jarvis_api/routes/provider_registry.py`
_Registret over udbydere og modeller — laesning OG skrivning. Owner-only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L21) |
| class | `_ModelBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L26) |
| class | `_ProviderBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L33) |
| class | `_GendanBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L39) |
| class | `_TilfoejBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L43) |
| class | `_LaneBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L55) |
| function | `registret` | `()` | HELE registret: alle udbydere, alle modeller, pr. lane. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L62) |
| function | `saet_model` | `(body)` | Slaa én model til eller fra. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L70) |
| function | `saet_provider` | `(body)` | Slaa en hel udbyder til eller fra. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L80) |
| function | `fjern_model_route` | `(provider, model)` | Fjern én model fra registret. Legitimationen roeres ikke. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L89) |
| function | `fjern_provider_route` | `(provider)` | Fjern en udbyder og dens modeller. Legitimationen roeres ikke. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L97) |
| function | `liste_backups` | `()` | Hvilke tilbagerulninger kan vaelges. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L105) |
| function | `gendan` | `(body)` | Rul registret tilbage. Tom sti = nyeste backup. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L113) |
| function | `tilfoej_route` | `(body)` | Tilfoej en udbyder + model. `api_key` er valgfri og returneres aldrig. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L121) |
| function | `lane_route` | `(body)` | Flyt en model til en anden lane. Flytning er ikke en slukning. | [src](../../../apps/api/jarvis_api/routes/provider_registry.py#L132) |

## `apps/api/jarvis_api/routes/push.py`
_Push token-registrering. Scoper til den auth'ede bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RegisterBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L12) |
| class | `UnregisterBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L17) |
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L21) |
| function | `register` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L27) |
| function | `unregister` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L36) |
| class | `WebSubscribeBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L41) |
| function | `web_vapid` | `()` | Den offentlige VAPID-nøgle — klienten skal bruge den til at abonnere. | [src](../../../apps/api/jarvis_api/routes/push.py#L48) |
| function | `web_subscribe` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/push.py#L59) |
| function | `web_unsubscribe` | `(body)` | Afmeld et web-abonnement. ``token`` bærer her abonnementets endpoint — | [src](../../../apps/api/jarvis_api/routes/push.py#L69) |

## `apps/api/jarvis_api/routes/review.py`
_Review: hvad er der faktisk ændret, og hvad bør man kigge efter?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kun_ejer` | `()` | Ruten laeser repoets arbejdstrae og filstoerrelser paa vaerten. | [src](../../../apps/api/jarvis_api/routes/review.py#L20) |
| function | `_repo_root` | `()` | — | [src](../../../apps/api/jarvis_api/routes/review.py#L44) |
| function | `_kør` | `(rod, *args)` | — | [src](../../../apps/api/jarvis_api/routes/review.py#L48) |
| function | `_linjer_i` | `(sti)` | — | [src](../../../apps/api/jarvis_api/routes/review.py#L59) |
| function | `_risici` | `(rod, filer, test_koert)` | Flag udledt af repoets EGNE regler. Ingen regel → intet flag. | [src](../../../apps/api/jarvis_api/routes/review.py#L67) |
| function | `review_changes` | `(test_koert=…, diff=…, kilde=…, rod=…)` | Hvad er ændret i arbejdstræet — pr. fil, med diff og regel-baserede flag. | [src](../../../apps/api/jarvis_api/routes/review.py#L109) |
| function | `_seneste_commit` | `(rod, med_diff)` | Den seneste commit — så panelet ikke bliver tomt i det øjeblik man committer. | [src](../../../apps/api/jarvis_api/routes/review.py#L136) |
| function | `_saml` | `(rod_til_laesning, gren, numstat, porcelain, diff_tekst, test_koert, med_diff, laes_fil)` | Fælles opsamling for begge træer — så de to veje ikke kan svare i | [src](../../../apps/api/jarvis_api/routes/review.py#L170) |
| function | `_aendringer_paa_serveren` | `(test_koert, med_diff)` | — | [src](../../../apps/api/jarvis_api/routes/review.py#L211) |
| function | `_aendringer_paa_maskinen` | `(rod, test_koert, med_diff)` | Bjørns eget træ, læst over broen med ÉN compound-kommando. | [src](../../../apps/api/jarvis_api/routes/review.py#L240) |
| function | `review_lessons` | `(limit=…)` | Lektier der venter paa en dom — og dem der allerede er i brug. | [src](../../../apps/api/jarvis_api/routes/review.py#L272) |
| function | `review_lesson_set` | `(lesson_id, payload=…)` | Godkend (`active`), afvis (`rejected`) eller send tilbage (`proposed`). | [src](../../../apps/api/jarvis_api/routes/review.py#L296) |

## `apps/api/jarvis_api/routes/review_traeer.py`
_Hvilket arbejdstræ kigger vi i — serverens eller Bjørns egen maskine?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `kommando_for` | `(rod)` | Én kommando, fire svar: gren, numstat, status, diff. | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L30) |
| function | `parse_segmenter` | `(stdout)` | Del svaret op i (gren, numstat, status, diff). | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L47) |
| function | `_er_binaer` | `(indhold)` | — | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L60) |
| function | `utrackede_fra_status` | `(porcelain)` | Stierne bag `??` i `git status --porcelain`. | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L64) |
| function | `numstat_til_filer` | `(numstat)` | — | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L82) |
| function | `ny_fil_post` | `(sti, indhold)` | En utracket fil som en fil-post. | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L99) |
| function | `ny_fil_diff` | `(sti, indhold)` | En diff-blok for en ny fil, i samme form som git selv skriver den. | [src](../../../apps/api/jarvis_api/routes/review_traeer.py#L114) |

## `apps/api/jarvis_api/routes/sensory.py`
_Sansernes Arkiv HTTP endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SensoryRecordPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L23) |
| function | `list_memories` | `(modality=…, limit=…, offset=…, since=…)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L31) |
| function | `search_memories` | `(q=…, modality=…, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L44) |
| function | `summary` | `()` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L54) |
| function | `get_memory` | `(memory_id)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L59) |
| function | `record_memory` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/sensory.py#L67) |

## `apps/api/jarvis_api/routes/status.py`
_Status-endpoints til forsiden — én rig og én offentlig._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_format_uptime` | `(seconds)` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L33) |
| function | `_daemon_count` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L47) |
| function | `_visible_model_label` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L55) |
| function | `status` | `()` | Den RIGE status. Kræver token — bærer model og daemons. | [src](../../../apps/api/jarvis_api/routes/status.py#L65) |
| function | `status_public` | `()` | Den OFFENTLIGE status: online + uptime, intet andet. | [src](../../../apps/api/jarvis_api/routes/status.py#L79) |

## `apps/api/jarvis_api/routes/system_health.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `system_health` | `()` | — | [src](../../../apps/api/jarvis_api/routes/system_health.py#L19) |
| function | `system_git` | `()` | Return current git branch and diff stats (insertions/deletions since HEAD). | [src](../../../apps/api/jarvis_api/routes/system_health.py#L39) |
| class | `CommitRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/system_health.py#L85) |
| function | `system_git_commit` | `(body)` | Stage tracked changes and commit with the given message. | [src](../../../apps/api/jarvis_api/routes/system_health.py#L90) |

## `apps/api/jarvis_api/routes/tool_router.py`
_MC observability for tool_router._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bucket_count` | `(values, n_buckets=…)` | — | [src](../../../apps/api/jarvis_api/routes/tool_router.py#L14) |
| function | `get_state` | `()` | — | [src](../../../apps/api/jarvis_api/routes/tool_router.py#L25) |

## `apps/api/jarvis_api/routes/totp.py`
_TOTP-setup — hver bruger sætter sin EGEN anden faktor._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bruger_eller_403` | `()` | Returnér den indloggede bruger. Ubundet (no-auth) → owner. | [src](../../../apps/api/jarvis_api/routes/totp.py#L43) |
| function | `totp_status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L62) |
| function | `_do_setup` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L67) |
| function | `totp_setup` | `()` | Generér + gem en ny TOTP-seed for den indloggede bruger. Returnér secret | [src](../../../apps/api/jarvis_api/routes/totp.py#L84) |
| function | `totp_revoke` | `()` | Fjern kalderens EGEN TOTP-seed (deaktivér til ny setup, §9 kompromittering). | [src](../../../apps/api/jarvis_api/routes/totp.py#L92) |

## `apps/api/jarvis_api/routes/transcribe.py`
_POST /transcribe — diktering-transskription til jarvis-desk's mic-knap._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `transcribe` | `(file, language=…)` | — | [src](../../../apps/api/jarvis_api/routes/transcribe.py#L22) |

## `apps/api/jarvis_api/routes/tts.py`
_TTS synthesis route — ElevenLabs primær (Jarvis' egen stemme, Mads),_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_elevenlabs_voice_id` | `()` | Jarvis' stemme-id — ÉT sted, nemlig i voice-skillen. | [src](../../../apps/api/jarvis_api/routes/tts.py#L26) |
| class | `TTSRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/tts.py#L44) |
| function | `_elevenlabs_preferred` | `()` | Runtime-flag så credits kan spares uden kode-ændring. Default True (ElevenLabs primær). | [src](../../../apps/api/jarvis_api/routes/tts.py#L68) |
| function | `_synthesize_elevenlabs_bytes` | `(text)` | Jarvis' egen ElevenLabs-stemme → MP3-bytes. Genbruger nøgle+voice_id fra voice-skillen | [src](../../../apps/api/jarvis_api/routes/tts.py#L80) |
| function | `synthesize` | `(req)` | Synthesize text → MP3 bytes via edge-tts. | [src](../../../apps/api/jarvis_api/routes/tts.py#L97) |
| function | `list_voices` | `(lang=…)` | List available Edge-TTS voices, optionally filtered by language tag. | [src](../../../apps/api/jarvis_api/routes/tts.py#L167) |

## `apps/api/jarvis_api/routes/ui_view_requests.py`
_`GET /ui/view-requests/pending` og `POST /ui/view-requests/{id}/svar`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ViewSvar` | `` | — | [src](../../../apps/api/jarvis_api/routes/ui_view_requests.py#L22) |
| function | `_ventende` | `()` | — | [src](../../../apps/api/jarvis_api/routes/ui_view_requests.py#L26) |
| function | `view_requests_pending` | `()` | Ubesvarede visnings-forespørgsler for samtaler brugeren må røre. | [src](../../../apps/api/jarvis_api/routes/ui_view_requests.py#L36) |
| function | `view_request_svar` | `(request_id, body)` | Desk's svar. Kun det første svar tæller. | [src](../../../apps/api/jarvis_api/routes/ui_view_requests.py#L42) |

## `apps/api/jarvis_api/routes/users.py`
_Owner-only user-administration (spec 2026-06-15 §4/§6). CRUD + GDPR-erasure._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `PatchUserReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L20) |
| class | `DeleteUserReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L30) |
| function | `list_all` | `(claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L35) |
| function | `get_one` | `(user_id, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L40) |
| function | `patch_one` | `(user_id, req, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L48) |
| function | `delete_one` | `(user_id, req, claims=…)` | — | [src](../../../apps/api/jarvis_api/routes/users.py#L75) |

## `apps/api/jarvis_api/routes/visning.py`
_Visning — serverer et lokalt billede til desk' rækkevisning._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gammelt_analysebillede` | `(sti, besked_id, tool_use_id)` | Allow one old temp image only when the stored tool call names that path. | [src](../../../apps/api/jarvis_api/routes/visning.py#L66) |
| function | `vis_billede` | `(sti, besked_id=…, tool_use_id=…)` | — | [src](../../../apps/api/jarvis_api/routes/visning.py#L104) |

## `apps/api/jarvis_api/routes/voice_live.py`
_POST /voice/samtale — åbn en ægte stemme-samtale med Jarvis (LiveKit/WebRTC)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SamtaleRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L44) |
| function | `_livekit_noegler` | `()` | — | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L48) |
| function | `livekit_billet` | `(api_key, api_secret, *, identitet, rum, navn=…, admin=…, ttl=…)` | LiveKit-adgangsbillet (JWT HS256, LiveKits eget format). | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L56) |
| function | `_send_agent` | `(api_key, api_secret, rum, metadata)` | Bed LiveKit sende voice-agenten ind i rummet med sin hemmelige metadata. | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L70) |
| function | `aabn_samtale` | `(body, request)` | — | [src](../../../apps/api/jarvis_api/routes/voice_live.py#L86) |

## `apps/api/jarvis_api/routes/workbench.py`
_Ruter til de værktøjer der blev bygget 6/9 men aldrig kunne nås fra en app._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kraev_owner` | `(hvad)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L26) |
| function | `_session_id` | `(payload=…, *, kraev=…)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L32) |
| function | `operator_channel_status` | `(session_id=…)` | Er kanalen åben, og hvor længe endnu? Læse-kun, ingen owner-gate. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L52) |
| function | `operator_channel_open` | `(payload=…)` | Owner-only: åbn kanalen. Herefter kører bash på Bjørns maskine. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L60) |
| function | `operator_channel_close` | `(payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L69) |
| function | `checkpoints_list` | `(session_id=…)` | Hvad kan fortrydes? Nyeste først. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L79) |
| function | `checkpoints_rollback` | `(payload=…)` | Owner-only: rul den seneste redigeringsrunde tilbage som helhed. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L96) |
| function | `undo_message_edits` | `(message_id, payload=…)` | Owner-only: restore only this message's recorded file writes. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L108) |
| function | `switches_status` | `()` | Tilstand for de to kontakter der styrer runtime-adfærd fra UI'et. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L121) |
| function | `switch_set` | `(navn, payload=…)` | Owner-only: tænd/sluk `bash_sandbox` eller `env_block`. Body: {enabled: bool}. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L135) |
| function | `context_summary` | `(session_id=…)` | Hvad gik der ind i sidste tur? Filer, kilder, størrelse. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L160) |

