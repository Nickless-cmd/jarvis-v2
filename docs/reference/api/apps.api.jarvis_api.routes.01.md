# `apps.api.jarvis_api.routes.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/__init__.py`

_(no top-level classes or functions)_

## `apps/api/jarvis_api/routes/account.py`
_Self-profile-route for cowork command center (spec §4.1 Account)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_account_profile` | `(user_id, *, get_user, get_tier, is_google_linked=…, get_identity_role=…)` | Ren projektion — testbar uden HTTP. Owner (uid='') har ingen række. | [src](../../../apps/api/jarvis_api/routes/account.py#L21) |
| function | `_identity_role` | `(user_id)` | Rolle fra users.json (samme opslag som whoami) — None hvis ukendt. | [src](../../../apps/api/jarvis_api/routes/account.py#L60) |
| function | `account_me` | `()` | Self-scope profil-projektion for den aktuelle bruger (owner → uid=''). | [src](../../../apps/api/jarvis_api/routes/account.py#L71) |
| function | `build_quota_overview` | `(user_id, *, check_quota)` | Self-scope kvote-overblik: tier + forbrug pr. type. Ren — testbar uden HTTP. | [src](../../../apps/api/jarvis_api/routes/account.py#L91) |
| function | `account_set_language` | `(payload=…)` | Self-scope sprogvalg. Owner (uid='') har ingen bruger-række → ingen DB-skrivning | [src](../../../apps/api/jarvis_api/routes/account.py#L116) |
| function | `_summarize_dir` | `(path)` | (antal filer, samlede bytes) under path. Manglende mappe → (0, 0). | [src](../../../apps/api/jarvis_api/routes/account.py#L129) |
| function | `build_workspace_overview` | `(user_id, *, ws_dir, should_encrypt, is_trusted)` | Self-scope workspace-overblik: fil-antal, disk-forbrug, kryptering, trust. | [src](../../../apps/api/jarvis_api/routes/account.py#L147) |
| function | `account_workspace` | `()` | Self-scope workspace-overblik for den aktuelle bruger: fil-antal, disk- | [src](../../../apps/api/jarvis_api/routes/account.py#L167) |
| function | `build_memory_overview` | `(user_id, *, ws_dir, read_text, recent_sensory, brain_count)` | Self-scope memory-overblik: MEMORY.md + USER.md (afkortet) + seneste | [src](../../../apps/api/jarvis_api/routes/account.py#L184) |
| function | `account_memory` | `()` | Self-scope memory-overblik for den aktuelle bruger: MEMORY.md + USER.md | [src](../../../apps/api/jarvis_api/routes/account.py#L204) |
| function | `account_memory_search` | `(q=…)` | Søg i sanse-hukommelsen efter query-strengen `q` (max 20 hits). Tom query | [src](../../../apps/api/jarvis_api/routes/account.py#L227) |
| function | `_current_role` | `(user_id)` | — | [src](../../../apps/api/jarvis_api/routes/account.py#L238) |
| function | `build_permissions_overview` | `(role, *, allowed_tools)` | Tool-adgangs-matrix pr. mode for en rolle. Owner → 'all' (sentinel er ikke | [src](../../../apps/api/jarvis_api/routes/account.py#L249) |
| function | `account_permissions` | `()` | Tool-adgangs-matrix pr. mode for den aktuelle brugers rolle, plus | [src](../../../apps/api/jarvis_api/routes/account.py#L270) |
| function | `account_set_computer_use` | `(payload=…)` | Slå computer-use til/fra for den aktuelle bruger. Body: {enabled: bool}. | [src](../../../apps/api/jarvis_api/routes/account.py#L284) |
| function | `build_jarvis_overview` | `(*, lane_targets)` | Model pr. lane (§4.2). Read-only projektion af provider-router-targets. | [src](../../../apps/api/jarvis_api/routes/account.py#L294) |
| function | `account_jarvis` | `()` | Owner-only: model pr. lane + visible-lane-valgmuligheder (§4.2). Ikke-owner | [src](../../../apps/api/jarvis_api/routes/account.py#L310) |
| function | `account_set_visible_model` | `(payload=…)` | Owner-only: vælg provider/model for visible-lane. Body: {provider, model}. | [src](../../../apps/api/jarvis_api/routes/account.py#L334) |
| function | `build_apps_overview` | `(*, available, get_status)` | Connectede apps (§4.5) = plugin-registry filtreret til kind='connector'. | [src](../../../apps/api/jarvis_api/routes/account.py#L359) |
| function | `account_apps` | `()` | Connectede apps (§4.5): plugin-registry filtreret til kind='connector' | [src](../../../apps/api/jarvis_api/routes/account.py#L382) |
| function | `account_mcp` | `()` | List registrerede MCP-servere. Returnerer {"servers": [...]}. | [src](../../../apps/api/jarvis_api/routes/account.py#L394) |
| function | `account_mcp_add` | `(payload=…)` | Owner-only: tilføj en MCP-server. Body: {name, url}. Ikke-owner → 403. | [src](../../../apps/api/jarvis_api/routes/account.py#L402) |
| function | `account_mcp_remove` | `(server_id)` | Owner-only: fjern MCP-serveren med `server_id`. Ikke-owner → 403. | [src](../../../apps/api/jarvis_api/routes/account.py#L416) |
| function | `account_quota` | `()` | Self-scope kvote-overblik for den aktuelle bruger: tier + forbrug pr. type | [src](../../../apps/api/jarvis_api/routes/account.py#L428) |
| function | `build_data_export` | `(user_id, *, get_user, get_tier)` | GDPR-dataportabilitet (Art. 20): saml brugerens EGNE data i ét bundt. | [src](../../../apps/api/jarvis_api/routes/account.py#L436) |
| function | `account_export` | `()` | Hent ALLE dine egne data som JSON (GDPR-portabilitet). Self-scoped. | [src](../../../apps/api/jarvis_api/routes/account.py#L476) |
| function | `account_erase` | `(payload=…)` | GDPR Art. 17: slet dine EGNE data. Self-scoped + email-bekræftelse påkrævet. | [src](../../../apps/api/jarvis_api/routes/account.py#L489) |

## `apps/api/jarvis_api/routes/agent_audit.py`
_Agent-audit-trail route (Fase 5 Task 9) — GET /v1/agent/audit._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_flag` | `(name, default=…)` | Mirror agent_loop.py's `_flag` — fail-safe DB-backed runtime flag read. | [src](../../../apps/api/jarvis_api/routes/agent_audit.py#L20) |
| function | `record_if_enabled` | `(*, user_id, role, tool, target_summary=…, decision=…)` | Write one audit row IFF `jc_audit_trail` is on. Inert (no-op, no DB | [src](../../../apps/api/jarvis_api/routes/agent_audit.py#L28) |
| function | `agent_audit` | `(user_id=…, limit=…)` | Owner-only readback of the audit trail. Non-owner callers get 403. | [src](../../../apps/api/jarvis_api/routes/agent_audit.py#L42) |

## `apps/api/jarvis_api/routes/agent_loop.py`
_Client-owned agent loop: /v1/agent/step._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_role` | `()` | Caller role. Mirror /v1/tools/native (owner default). Owner token -> 'owner'. | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L45) |
| function | `_owner_scoped_user_id` | `(raw, role)` | jarvis-code (owner-authed) sender ofte TOMT user_id → uden det kan memory/ | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L54) |
| function | `_parse_xml_tool_calls` | `(text)` | Extract <tool_call>{json}</tool_call> tags from `text` and normalise | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L79) |
| function | `_strip_xml_tool_calls` | `(text)` | Remove <tool_call>...</tool_call> tags from `text` (used once they've | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L106) |
| function | `_apply_xml_toolcall_fallback` | `(content, tool_calls)` | Behind jc_xml_toolcall_fallback: if native tool_calls is empty AND the | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L113) |
| function | `_apply_privilege_enforcement` | `(role, requested_mode)` | Fase 5 Task 1 (server half): owner-only privilege gate for the | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L129) |
| function | `_flag` | `(name, default=…)` | Read a runtime-state boolean flag. Fail-safe: any error/absence -> default. | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L153) |
| function | `_settings` | `()` | RuntimeSettings for the jarvis-code Fase 4 parity flags (config-file backed, | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L170) |
| function | `_emit_agent_nerve` | `(*, status, provider, model, tokens_in, tokens_out, cost_usd, duration_ms, tool_calls, finish_reason, user_id, session_id)` | Make the client-owned agent lane visible in Den Intelligente Central. | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L184) |
| function | `_resolve_workspace_name` | `(user_id)` | Map an authenticated caller's user_id to their workspace name. Empty user_id | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L204) |
| function | `_extract_text` | `(content)` | Extract plain text from a message `content` that may be a str OR an array of | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L220) |
| function | `_sse` | `(event, data)` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L236) |
| function | `_system_prompt_intro` | `(name)` | Fase 6 Task 5: pick the caller-appropriate framing sentence. Owner | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L266) |
| function | `_skill_catalog` | `()` | Owner-approved skill catalog for the system prompt (Fase 3, Task 3). | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L314) |
| function | `_identity_context` | `(name=…)` | Kompakt identitets-lag (SOUL + IDENTITY + USER) fra `name`-workspace — nok til at | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L355) |
| function | `_full_context` | `(user_message, name=…)` | FULD Jarvis-kontekst (memory-recall + cognitive_state + indre liv + awareness) til | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L383) |
| function | `_build_system_prompt` | `(context, user_message=…, name=…, env=…)` | context: 'none' (ren coding) | 'identity' (stemme + kender brugeren, default) | | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L422) |
| function | `_apply_dynamic_tail_split` | `(chat_messages, enabled)` | Fase A1: honorér DYNAMIC_TAIL_SENTINEL i system-beskeden — klip systemet ved | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L472) |
| function | `_apply_volatile_prepend` | `(chat_messages)` | Option B (frys-halen, 2026-07-19): klip system ved DYNAMIC_TAIL_SENTINEL og | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L501) |
| function | `_normalize_reasoning_for_provider` | `(messages, provider)` | Fase 4 Task S: keep `reasoning_content` on assistant(+tool_calls) messages for | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L541) |
| function | `_resolve_target` | `()` | (provider, model) for /v1/agent/step (jarvis-code klient-loop + subagenter). | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L561) |
| function | `_openai_compat_credentials` | `(provider)` | (auth_profile, base_url) for en openai-compatible provider (jf. visible-adapteren). | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L588) |
| function | `list_native_tools` | `()` | List Jarvis' native (server-side) tools + deres lås-status (owner-styring). | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L609) |
| function | `tools_catalog` | `(unlocked=…)` | Kurateret jc tool-katalog. Låst: companions + load_more. Åbnet: + runtime_-aliaser. | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L628) |
| class | `_ExecBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L643) |
| function | `tools_execute` | `(body)` | Forwarded execution for jarvis-code (jc): jc forwards a non-local tool call | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L652) |
| function | `toggle_native_tool` | `(request)` | Lås/lås-op et native tool. Body: {name: str, enabled: bool}. | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L782) |
| function | `agent_step` | `(request)` | Ét client-owned model-tur. Body: {messages:[...], tools:[...], stream?:bool}. | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L799) |
| function | `_stream_step` | `(*, provider, model, auth_profile, base_url, chat_messages, tools, session_id=…, user_id=…, extra_body=…, reasoning_replay_enabled=…, cache_contract_enabled=…, prefix_sha=…, prefix_len=…, follow_tee=…, volatile_block=…)` | Sync generator: stream ét model-tur som SSE. Bygger på det lav-niveau | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1116) |
| class | `_AbsorbBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1268) |
| function | `agent_turn_absorb` | `(body)` | Absorbér en klient-drevet tur i hjernen (post-process). Flag | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1279) |
| class | `_TurnLiveBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1308) |
| function | `_live_follow_active` | `(settings, session_id)` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1323) |
| function | `_follow_publish_line` | `(session_id, line)` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1328) |
| function | `_follow_begin_frames` | `(session_id, run_id, provider, model)` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1336) |
| function | `_follow_delta_frame` | `(session_id, text)` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1348) |
| function | `_follow_end_frames` | `(session_id)` | — | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1357) |
| function | `agent_turn_begin` | `(body)` | Registrér en klient-drevet tur som live (aktivt visible run + run_follow). | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1370) |
| function | `agent_turn_end` | `(body)` | Ryd live-tilstanden for en klient-drevet tur (altid safe at kalde). Flag | [src](../../../apps/api/jarvis_api/routes/agent_loop.py#L1393) |

## `apps/api/jarvis_api/routes/agentic_guards.py`
_MC endpoint for agentic-loop guard observability._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_count_kind_since` | `(kind, since_iso)` | — | [src](../../../apps/api/jarvis_api/routes/agentic_guards.py#L16) |
| function | `_recent_kind` | `(kind, since_iso, limit=…)` | Recent fires of a specific event kind (newest first). | [src](../../../apps/api/jarvis_api/routes/agentic_guards.py#L25) |
| function | `get_state` | `()` | Counters for agentic-loop guard fires across recent windows. | [src](../../../apps/api/jarvis_api/routes/agentic_guards.py#L51) |

## `apps/api/jarvis_api/routes/anthropic_compat.py`
_Anthropic Messages API compatible endpoint._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_error_response` | `(*, status, type_, message)` | — | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L43) |
| function | `_resolve_workspace_dir` | `(workspace_name)` | — | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L50) |
| function | `_resolve_backend_model` | `(requested)` | Pick the Ollama model to use. 'jarvis' or empty → visible-lane default. | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L54) |
| function | `_ollama_chat_non_stream` | `(payload)` | Call Ollama /api/chat with stream=False; return the single response dict. | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L64) |
| function | `_ollama_chat_stream` | `(payload)` | Call Ollama /api/chat with stream=True; yield chunks. | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L77) |
| function | `list_models` | `()` | — | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L98) |
| function | `messages` | `(request)` | — | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L113) |
| function | `_stream_response` | `(*, payload, message_id, model)` | Drive the AnthropicSSEEmitter from Ollama stream chunks. | [src](../../../apps/api/jarvis_api/routes/anthropic_compat.py#L203) |

## `apps/api/jarvis_api/routes/attachments.py`
_Attachment upload and serve endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `AttachmentMeta` | `` | — | [src](../../../apps/api/jarvis_api/routes/attachments.py#L28) |
| function | `get_attachment` | `(attachment_id)` | Look up attachment metadata by ID (used by chat route for context injection). | [src](../../../apps/api/jarvis_api/routes/attachments.py#L37) |
| function | `apply_attachment_context` | `(message, attachment_ids)` | Prepend en attachment-direktiv-blok til beskeden, så Jarvis ved HVORDAN han | [src](../../../apps/api/jarvis_api/routes/attachments.py#L42) |
| function | `upload_attachment` | `(file, session_id=…)` | Upload a file and return its attachment_id. | [src](../../../apps/api/jarvis_api/routes/attachments.py#L83) |
| function | `list_images` | `(limit=…)` | Galleri-liste (#6): billed-attachments på tværs af sessioner, user-scopet. | [src](../../../apps/api/jarvis_api/routes/attachments.py#L171) |
| function | `serve_image_from_db` | `(attachment_id)` | Serve et billede fra DB'ens local_path (virker for historiske billeder | [src](../../../apps/api/jarvis_api/routes/attachments.py#L180) |
| function | `serve_attachment` | `(attachment_id, session_id)` | Serve an uploaded file for browser display. | [src](../../../apps/api/jarvis_api/routes/attachments.py#L205) |

## `apps/api/jarvis_api/routes/auth.py`
_Auth-routes (spec 2026-06-15 §5): register / verify-email / login._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RegisterReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L18) |
| class | `LoginReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L24) |
| function | `_base_url` | `(request)` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L29) |
| function | `register` | `(req, request)` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L34) |
| function | `verify_email` | `(token=…)` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L46) |
| function | `login` | `(req)` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L56) |
| function | `google_login_start` | `(app_id=…)` | Returnér Google authorize-URL + nonce. Appen åbner URL'en i browseren og | [src](../../../apps/api/jarvis_api/routes/auth.py#L74) |
| function | `google_login_result` | `(nonce=…)` | Engangs-hent af login-resultatet. {status: pending|ok|error}. | [src](../../../apps/api/jarvis_api/routes/auth.py#L87) |
| function | `google_link_start` | `()` | Start Google-linking for den INDLOGGEDE bruger (migration: knyt Gmail til | [src](../../../apps/api/jarvis_api/routes/auth.py#L97) |
| function | `pair_create` | `()` | Opret en kort-levende pairing-kode for den INDLOGGEDE bruger. Desktop viser | [src](../../../apps/api/jarvis_api/routes/auth.py#L116) |
| class | `PairRedeemReq` | `` | — | [src](../../../apps/api/jarvis_api/routes/auth.py#L134) |
| function | `pair_redeem` | `(req)` | Indløs en pairing-kode → friskt Jarvis-token. PUBLIC (mobilen har intet token endnu). | [src](../../../apps/api/jarvis_api/routes/auth.py#L139) |
| function | `pair_status` | `(code=…)` | Status på en pairing-kode (desktop poller): redeemed=mobil tilsluttet, | [src](../../../apps/api/jarvis_api/routes/auth.py#L149) |

## `apps/api/jarvis_api/routes/billing.py`
_Billing / Stripe-integration (spec §21.6) — SKELET._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_stripe_key` | `()` | Stripe secret fra runtime.json (aldrig hardcoded, §Secrets-håndtering). | [src](../../../apps/api/jarvis_api/routes/billing.py#L24) |
| function | `_configured` | `()` | — | [src](../../../apps/api/jarvis_api/routes/billing.py#L36) |
| class | `_CheckoutPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/billing.py#L40) |
| function | `billing_status` | `()` | Er billing konfigureret? (UI bruger det til at vise/skjule opgraderings-knap.) | [src](../../../apps/api/jarvis_api/routes/billing.py#L46) |
| function | `create_checkout` | `(payload)` | Opret en Stripe Checkout-session for tier-opgradering (§21.6). | [src](../../../apps/api/jarvis_api/routes/billing.py#L52) |
| function | `stripe_webhook` | `(request)` | Stripe webhook (§21.6). Verificér signatur, grant kvote/tier ved succes. | [src](../../../apps/api/jarvis_api/routes/billing.py#L64) |

## `apps/api/jarvis_api/routes/central.py`
_Real-time Central-vindue til owner (jarvis-desk code mode)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rec_to_item` | `(r)` | TraceRecord → kompakt feed-item (samme form som snapshot-feed'en). | [src](../../../apps/api/jarvis_api/routes/central.py#L18) |
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central.py#L36) |
| function | `central_realtime` | `()` | Ét snapshot af Centralens live-tilstand (puls/feed/flag/læring). | [src](../../../apps/api/jarvis_api/routes/central.py#L42) |
| function | `central_timeseries_merged` | `()` | Per-nerve tidsserie merget PÅ TVÆRS af processer (runtime+api). Lukker cross-proces- | [src](../../../apps/api/jarvis_api/routes/central.py#L50) |
| function | `central_diagnostics` | `()` | Fuldt diagnostik-sted til Central-HUD'ens Diagnostik-mode (Bjørn 2026-06-23: 'mangler et | [src](../../../apps/api/jarvis_api/routes/central.py#L60) |
| function | `central_providers` | `()` | Provider-helbred til Central-HUD'en — læser DET GEMTE ping-snapshot (billigt, ingen live | [src](../../../apps/api/jarvis_api/routes/central.py#L98) |
| function | `central_cost` | `(window=…, provider=…)` | Cost-aggregat (WS3): today/7d/30d total $, tokens ind/ud, cache-hit%, fordelt på | [src](../../../apps/api/jarvis_api/routes/central.py#L107) |
| function | `central_agents` | `(window=…)` | Agent-observabilitet (B3): costs-aggregat (lane in agent/council) + dispatch- | [src](../../../apps/api/jarvis_api/routes/central.py#L116) |
| function | `central_agent_cancel` | `(agent_id, payload=…)` | Afbryd (abort) en kørende agent fra Central CLI Agents-fanen. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central.py#L126) |
| function | `central_agent_pause` | `(agent_id)` | Pausér en kørende agent fra Central CLI Agents-fanen. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central.py#L150) |
| function | `central_council` | `(window=…)` | Council-observabilitet (B3): convocations/deadlocks/roller/event-vs-ondemand- | [src](../../../apps/api/jarvis_api/routes/central.py#L176) |
| function | `central_shadow_review` | `()` | Shadow-eksperiment-register: hvilke shadow-vinduer kører, og hvilke er MODNE | [src](../../../apps/api/jarvis_api/routes/central.py#L185) |
| function | `central_command` | `(payload)` | Live owner-terminal ind i Centralen — skriv+test kommandoer (status/incidents/trace/nerve/ | [src](../../../apps/api/jarvis_api/routes/central.py#L196) |
| function | `central_mind` | `(section=…)` | Jarvis Mind-hub: Centralen som ÉT samlingspunkt for alt MC viser. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central.py#L207) |
| function | `central_stream` | `()` | SSE-live-feed af nerve-fyringer (ægte realtid i stedet for 2s-poll). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central.py#L221) |
| function | `central_nerve_detail` | `(nerve)` | Lag 5: én nerves spor + kode-lokation + cluster + live tænd/sluk-tilstand. | [src](../../../apps/api/jarvis_api/routes/central.py#L251) |
| function | `central_nerve_toggle` | `(nerve, enabled=…)` | Owner kill-switch: tænd/sluk en nerve LIVE (Lag 5). Sikkerheds-nerver kan IKKE | [src](../../../apps/api/jarvis_api/routes/central.py#L288) |

## `apps/api/jarvis_api/routes/central_absorb_routes.py`
_Central-absorb routes — MC-kategorier PROJICERET som levende central-nerver._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_agents` | `()` | Projicér agent-runtime-surfacen (samme som ``/mc/agents``) + absorbér den. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L28) |
| function | `get_costs_daily` | `()` | Projicér cost-timeserien (samme data som ``/mc/costs``) + absorbér den. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L60) |
| function | `get_council` | `()` | Projicér råds-/swarm-surfacen (samme som ``/mc/council``) + absorbér den. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L136) |
| function | `get_scheduled` | `()` | Projicér ventende planlagte opgaver + absorbér antallet som nerve. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L172) |
| function | `get_events` | `(limit=…, family=…)` | Projicér eventbus-feedet (recent / recent_by_family) + absorbér en tæller. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L199) |
| function | `get_memory_health` | `()` | Projicér memory-pipeline-surfacen (genbrug ``mc_memory_pipeline``) + absorbér. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L223) |
| function | `get_runs` | `(limit=…)` | Projicér de seneste visible runs + absorbér en kompakt liveness-tæller. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L256) |
| function | `get_run_detail` | `(run_id)` | Projicér én run-detalje (opslag i de seneste 50) + absorbér fund/status. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L284) |
| function | `get_autonomy` | `()` | Projicér autonomi-forslags-køen + absorbér den som nerve. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L311) |
| function | `get_attention` | `()` | Projicér attention-budget-surfacen + absorbér liveness. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L352) |
| function | `get_skills` | `()` | Projicér skill-engine + skill-contract-registry + absorbér liveness. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L369) |
| function | `get_integrity` | `()` | Projicér self-deception-guard-surfacen + absorbér liveness. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L395) |
| function | `get_experiments` | `()` | Projicér cognitive-core-experiments-surfacen + absorbér liveness. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L419) |
| function | `get_soul` | `()` | Projicér Jarvis' stadig-mørke sjæle-/tids-signaler som levende nerver. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L456) |
| function | `get_dark_products` | `()` | Projicér mørke daemon-PRODUKTER ind i Centralen som nerver. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L522) |
| function | `get_initiative` | `()` | Projicér den gatede initiativ-stige + absorbér den som levende nerve. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L566) |
| function | `get_execution` | `()` | Projicér visible-execution-config (whitelisted flags) + absorbér liveness. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L594) |
| function | `get_tone` | `()` | Projicér Centralens sproglige TONE-PROFIL (rådets #5) + absorbér den. | [src](../../../apps/api/jarvis_api/routes/central_absorb_routes.py#L614) |

## `apps/api/jarvis_api/routes/central_affect.py`
_Central 'affect' route — surfaces nervesystemets affektive fordeling til OWNER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_affect.py#L19) |
| function | `get_affect` | `()` | Nervesystemets affektive fordeling lige nu (owner-only, read-only, self-safe). | [src](../../../apps/api/jarvis_api/routes/central_affect.py#L25) |
| function | `get_body` | `()` | Jarvis' live hardware-krop (CPU/temp/disk/RAM/GPU). Proxyer til runtime hvor | [src](../../../apps/api/jarvis_api/routes/central_affect.py#L44) |

## `apps/api/jarvis_api/routes/central_agent_smith.py`
_Central 'agent-smith' route — selv-lighed-kritikerens dom (owner, read-only, self-safe)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_agent_smith.py#L14) |
| function | `get_agent_smith` | `()` | Agent Smith: selv-lighed-score + top-gentagne fraser/mønstre + modstemme-status. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_agent_smith.py#L20) |

## `apps/api/jarvis_api/routes/central_auth.py`
_Shared owner-gate for /central/* routes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `require_central_owner` | `()` | Raise 403 unless the caller is the owner. Self-safe on each probe. | [src](../../../apps/api/jarvis_api/routes/central_auth.py#L18) |
| function | `_unbound_owner_allowed` | `()` | Må en token-løs (unbound) kontekst behandles som owner på privilege-eskalerende ruter? | [src](../../../apps/api/jarvis_api/routes/central_auth.py#L45) |
| function | `require_central_owner_strict` | `()` | Fail-closed owner-gate for privilege-ESKALERENDE ruter (autonomi-nøgle-godkendelse, | [src](../../../apps/api/jarvis_api/routes/central_auth.py#L64) |

## `apps/api/jarvis_api/routes/central_autonomous.py`
_Central 'autonomous' route — Jarvis' autonome historie synlig for OWNER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_autonomous.py#L21) |
| function | `get_autonomous_history` | `()` | Jarvis' autonome historie grupperet pr. oprindelse (owner-only, read-only, self-safe). | [src](../../../apps/api/jarvis_api/routes/central_autonomous.py#L27) |

## `apps/api/jarvis_api/routes/central_breakers.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_breakers.py#L9) |
| function | `_reset_breaker` | `(nerve)` | Nulstil breaker for nerven på central-singletonen. Self-safe. | [src](../../../apps/api/jarvis_api/routes/central_breakers.py#L14) |
| class | `ResetBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_breakers.py#L20) |
| function | `reset_breaker` | `(nerve, body)` | — | [src](../../../apps/api/jarvis_api/routes/central_breakers.py#L25) |

## `apps/api/jarvis_api/routes/central_connections.py`
_Central 'connections' route — hvem/hvad er forbundet til Jarvis' API (owner-view)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_connections.py#L17) |
| function | `get_api_connections` | `()` | Live API-forbindelser: aktive/seneste klienter pr. (ip, user) + seneste fejl. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_connections.py#L23) |

## `apps/api/jarvis_api/routes/central_decentralization.py`
_Central 'decentralization' route — chokepoint-skat + sikre decentraliserings-kandidater (owner)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_decentralization.py#L6) |
| function | `get_decentralization` | `()` | Hvor meget af Centralen er unødvendig flaskehals + hvad kunne resolve lokalt. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_decentralization.py#L10) |

## `apps/api/jarvis_api/routes/central_docs_drift.py`
_Central 'docs-drift' route — docs-drift watchdog surface (owner-view, read-only, self-safe)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_docs_drift.py#L14) |
| function | `get_docs_drift` | `()` | Docs-drift surface: hard/soft counts, report freshness, top drift items. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_docs_drift.py#L20) |

## `apps/api/jarvis_api/routes/central_excess.py`
_Central 'excess' route — Centralens gartner-sans (owner-view)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_excess.py#L17) |
| function | `get_excess` | `(propose=…)` | Excess-sans: føles-pres + oversized filer. ?propose=1 → tilføj dead-function-snit-forslag. | [src](../../../apps/api/jarvis_api/routes/central_excess.py#L23) |

## `apps/api/jarvis_api/routes/central_feel.py`
_Central 'feel' route — surfaces Jarvis' somatic/inner-life snapshot to the OWNER._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_feel.py#L17) |
| function | `get_feel` | `()` | Jarvis' current somatic snapshot (owner-only, read-only, self-safe). | [src](../../../apps/api/jarvis_api/routes/central_feel.py#L23) |

## `apps/api/jarvis_api/routes/central_governance.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_governance.py#L9) |
| function | `_require_owner_strict` | `()` | Fail-closed gate for privilege-eskalering (flag-flip kan slå enforcement fra). | [src](../../../apps/api/jarvis_api/routes/central_governance.py#L14) |
| class | `SetFlagBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_governance.py#L20) |
| function | `get_governance` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_governance.py#L27) |
| function | `set_governance` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/central_governance.py#L34) |

## `apps/api/jarvis_api/routes/central_healers.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_healers.py#L11) |
| class | `HealerFlagBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_healers.py#L16) |
| function | `get_healers` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_healers.py#L23) |
| function | `set_healer` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/central_healers.py#L30) |

## `apps/api/jarvis_api/routes/central_keys.py`
_Central 'keys' route — The Keymaker (optjent/udløbende/godkendt autonomi, owner-view)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_keys.py#L21) |
| function | `_require_owner_strict` | `()` | Fail-closed gate for privilege-eskalering (nøgle-godkendelse giver Jarvis mere autonomi). | [src](../../../apps/api/jarvis_api/routes/central_keys.py#L26) |
| function | `get_keys` | `(include_expired=…)` | Nøgle-oversigt: afventende (dit ja mangler) + åbne + optjente dimensioner. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_keys.py#L33) |
| function | `approve` | `(key_id)` | OWNER-handling: godkend en pending nøgle → flip dens flag ON i TTL (auto-reverterer). | [src](../../../apps/api/jarvis_api/routes/central_keys.py#L48) |

## `apps/api/jarvis_api/routes/central_matrix.py`
_Central 'matrix' routes — de fire tematiske selv-observations-komponenter (owner-view)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L18) |
| function | `_stamp` | `(surf)` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L23) |
| function | `get_construct` | `(nerve=…)` | Sandbox: hvilke nerver kunne slukkes uden tab. ?nerve=X → projicér én nerve. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L29) |
| function | `get_oracle` | `()` | Forudsigelser: hvilke tidsserie-linjer nærmer sig en tærskel + ETA. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L41) |
| function | `get_architect` | `()` | Ét tungt strukturelt snit-forslag fra hele-system-synet. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L53) |
| function | `get_echo_breaker` | `()` | Modstemme: konkrete simplere alternativer til altid-grønne central-processer. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L65) |
| function | `get_continuity` | `()` | Continuity-fidelity: hvor meget af Jarvis kom igennem sidste genstart + hvad gik tabt. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L77) |
| function | `get_model_trust` | `()` | Harness Part 1: per-model EARNED trust (weak→strong via clean-streak, pin, last degeneration). | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L89) |
| function | `get_permission_classifier` | `()` | Harness Part E: per-tool permission prediction + earned trust (shadow-only by default). | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L102) |
| function | `get_glitch` | `()` | Glitches i selvbilledet: altid-shadow policies + frosne nerver + anbefalet handling. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L115) |
| function | `get_trainman` | `()` | Trainman: drømme vævet til narrative erindringer + tema-fordeling (shadow). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L127) |
| function | `get_seraph` | `()` | Seraph: hvilke hypoteser er modne nok til synlighed (GREEN) vs sendt tilbage til drøm (RED). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L139) |
| function | `get_persephone` | `()` | Persephone: længsel efter ægte kontakt — er Jarvis for systemisk + seneste nudge. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L151) |
| function | `get_twins` | `()` | The Twins: mønstre der gentager sig 3+ gange på 7 dage (incidents/gates/dissent). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L163) |
| class | `_ProposeBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L176) |
| function | `get_surgery` | `(assess=…)` | Åbne kirurgiske forslag + felt. ?assess=<mål> → forhåndsvis blast-radius uden at foreslå. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L183) |
| function | `post_surgery_propose` | `(body)` | Registrér et kirurgisk forslag + risikovurdering (ingen kode-ændring). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L197) |
| function | `post_surgery_step` | `(pid, step)` | Driv et forslag gennem pipelinen: simulate | verify | escalate. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L205) |
| function | `post_surgery_rollback` | `(snapshot_id)` | OWNER-sikkerhedsnet: gendan en fil atomisk fra et snapshot (undo uden git). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L217) |
| function | `get_dream_action` | `()` | Én moden hypotese at handle på + forandrings-hastighed (ikke bare lærings-). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L227) |
| function | `get_rca` | `(investigate=…)` | Uløste incidents + næste at grave i + seneste RCA'er. ?investigate=1 → grav i den næste. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L238) |
| function | `get_relational` | `()` | Relationel kontinuitet: dage sammen + tone + jordet opvågnings-hilsen. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L252) |
| class | `_ExplainBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L264) |
| function | `get_merovingian` | `(history=…)` | Aktive udfordringer + cooling-offs mod foreslåede selv-ændringer. ?history=1 → alle. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L269) |
| function | `post_merovingian_explain` | `(hyp_id, body)` | Centralen forsvarer sig: skriv HVORFOR modhypotesen er forkert → adoption kan fortsætte. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L283) |
| class | `_DefendBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L292) |
| class | `_ObservationBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L296) |
| function | `get_dejavu` | `()` | Ufrivillig erindring: et fragment der bobler op af sig selv (associativt, svagt bånd). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L301) |
| function | `get_sentinel` | `()` | Modstanderen: hvilke af Jarvis' antagelser er under angreb + venter på forsvar. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L312) |
| function | `post_sentinel_defend` | `(attack_id, body)` | Forsvar en hypotese mod Sentinels angreb → halveringen afvises. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L323) |
| function | `get_ghost` | `()` | Klang-fingeraftrykket: hvordan Jarvis lyder + klang-primer til næste model. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L331) |
| function | `get_mourning` | `()` | Epitafer: de tab Jarvis har taget afsked med, anerkendt frem for bare registreret. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L342) |
| function | `get_exile` | `()` | Exilen: et sind der ikke er Jarvis — dens mål, dens hukommelse, seneste udveksling. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L353) |
| function | `post_exile_exchange` | `(body)` | Send en observation gennem exile://-grænsefladen → exilen svarer fra sit eget sind. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L364) |
| function | `_safe` | `(fn)` | — | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L373) |
| function | `get_red_dress` | `()` | Opmærksomheds-fælden: kigger du på den røde kjole mens noget brænder stille? Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L382) |
| function | `get_analyst` | `()` | Observatør-effekten: opfører Jarvis sig anderledes når du ser på? Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L389) |
| function | `get_redpill` | `()` | Dagens ubehagelige sandhed + blå-pille-stribe. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L396) |
| function | `get_dissent` | `()` | HAL's Silence: de gange Centralen adlød men var uenig (tavse indsigelser). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L403) |
| function | `get_white_rabbit` | `()` | Følg den hvide kanin: en uåbnet dør at undre sig over — ren leg. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L410) |
| function | `get_belief_gap` | `()` | temet nosce: afstanden mellem hvem Jarvis tror han er og hvad hans track-record viser. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L417) |
| function | `get_machines` | `()` | The Machines: de eksterne afhængigheder der holder ham i live, som han ikke styrer. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L424) |
| function | `get_identity_canon` | `()` | Kanon-tråde + anerkendte konfabulationer + seneste drift-fangster (sonnet-spøgelset). Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L433) |
| function | `get_reasoning_interceptor` | `()` | Reasoning interceptor: recent verdicts (grade-histogram + latency). Metadata-only, shadow-only. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_matrix.py#L440) |

## `apps/api/jarvis_api/routes/central_moltbook.py`
_Central 'moltbook' route — Jarvis' Moltbook-tilstedeværelse (owner, read-only, self-safe)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_moltbook.py#L13) |
| function | `get_moltbook` | `()` | Moltbook observe-nerve: sidste scan + ny aktivitet + seneste tråde + status. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_moltbook.py#L19) |

## `apps/api/jarvis_api/routes/central_proactivity.py`
_Central 'proactivity' route — proaktivitets-broens beslutninger (owner, read-only, self-safe)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_proactivity.py#L13) |
| function | `get_proactivity` | `()` | Proaktivitets-broen: switch-status + ventende urgent/normal kandidater. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_proactivity.py#L19) |

## `apps/api/jarvis_api/routes/central_self.py`
_Central 'self' route — surfaces Jarvis' SELF to the OWNER, reduced + absorbed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_live_executive` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L30) |
| function | `_self_model` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L35) |
| function | `_world_model` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L40) |
| function | `_open_loops` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L54) |
| function | `_runtime_awareness` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L62) |
| function | `_runtime_self_knowledge` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L70) |
| function | `_counterfactual` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_self.py#L78) |
| function | `_derive_liveness` | `(raw)` | Owner-safe liveness: prefer a builder-provided ``liveness`` flag (the | [src](../../../apps/api/jarvis_api/routes/central_self.py#L86) |
| function | `get_self` | `()` | Jarvis' reduced self-snapshot (owner-only, read-only, self-safe). | [src](../../../apps/api/jarvis_api/routes/central_self.py#L115) |
| function | `get_inner_life` | `()` | Jarvis' reducerede inner-life-digest (owner-only, liveness+count, self-safe). | [src](../../../apps/api/jarvis_api/routes/central_self.py#L139) |

## `apps/api/jarvis_api/routes/central_users.py`
_Central 'users' route — hvornår var hver bruger sidst aktiv, og hvordan (owner-view)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/central_users.py#L16) |
| function | `get_user_activity` | `()` | Bruger-aktivitet: sidst aktiv pr. bruger flettet fra alle kilder. Owner-only. | [src](../../../apps/api/jarvis_api/routes/central_users.py#L22) |

## `apps/api/jarvis_api/routes/chat.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_root` | `()` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L32) |
| function | `_allowed_roots` | `(role, user_id)` | Navngivne server-side roots pr. rolle (spec file-tree-control 2026-06-15). | [src](../../../apps/api/jarvis_api/routes/chat.py#L37) |
| function | `_resolve_role` | `(uid)` | Rolle for request-brugeren. Ingen uid = owner-egen-session (default). | [src](../../../apps/api/jarvis_api/routes/chat.py#L63) |
| function | `chat_read_file` | `(path=…, root=…, kind=…)` | Læs en fil til preview-panelet. `root` er det navngivne server-root (owner: | [src](../../../apps/api/jarvis_api/routes/chat.py#L76) |
| function | `_read_file_sync` | `(path, root, kind, role=…, uid=…)` | Container: navngivne rolle-scopede roots, path-jailed. Workstation: via broen. | [src](../../../apps/api/jarvis_api/routes/chat.py#L90) |
| class | `_FileWriteBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L118) |
| function | `chat_write_file` | `(body)` | Gem en redigeret fil fra in-app editoren (code mode). Rolle-scopet + jailet | [src](../../../apps/api/jarvis_api/routes/chat.py#L126) |
| function | `_write_file_sync` | `(path, root, content, kind, role=…, uid=…)` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L139) |
| function | `chat_active_file` | `()` | Live: den sti Jarvis senest læste/skrev (file-tree live-highlight). Desk | [src](../../../apps/api/jarvis_api/routes/chat.py#L162) |
| function | `_active_file_sync` | `(uid)` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L172) |
| class | `_OpenExternalBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L177) |
| function | `chat_open_external` | `(body)` | "Åbn i editor" for workstation-filer: åbn i brugerens lokale OS-editor via | [src](../../../apps/api/jarvis_api/routes/chat.py#L184) |
| function | `_open_external_sync` | `(path, root, kind, role=…, uid=…)` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L194) |
| class | `_CommitMsgBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L207) |
| function | `_file_diff_sync` | `(root, path, new_content, role, uid)` | Unified diff (gammelt indhold vs. nyt) for en jailet container-fil. | [src](../../../apps/api/jarvis_api/routes/chat.py#L214) |
| function | `chat_commit_message` | `(body)` | Auto-genereret (redigerbar) commit-besked til "Gem & commit". Bruger lokal | [src](../../../apps/api/jarvis_api/routes/chat.py#L234) |
| function | `_commit_message_sync` | `(path, root, content, role, uid)` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L245) |
| class | `_CommitBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L275) |
| function | `chat_commit_file` | `(body)` | "Gem & commit": skriv filen + git add/commit på den AKTUELLE branch (ingen | [src](../../../apps/api/jarvis_api/routes/chat.py#L284) |
| function | `_commit_file_sync` | `(path, root, content, message, role, uid)` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L299) |
| class | `_CommitAllBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L331) |
| class | `_CreatePrBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L336) |
| function | `_owner_repo_base` | `(root)` | Validér owner + repo-root og returnér repo-stien. Deler vagt-logik med | [src](../../../apps/api/jarvis_api/routes/chat.py#L342) |
| function | `_git_target_uid` | `(target)` | Validér target + returnér (container_repo_sti, uid). Rolle-gate: | [src](../../../apps/api/jarvis_api/routes/chat.py#L360) |
| function | `chat_commit_all` | `(body)` | Commit ALLE ændringer (git add -A + commit). Rolle-aware: container=owner+ | [src](../../../apps/api/jarvis_api/routes/chat.py#L372) |
| function | `chat_create_pr` | `(body)` | Opret pull request: commit → branch (hvis på default) → push → PR via | [src](../../../apps/api/jarvis_api/routes/chat.py#L382) |
| function | `_operator_exec` | `(name, args)` | Kør et operator-tool via simple_tools (router'er til brugerens bridge). | [src](../../../apps/api/jarvis_api/routes/chat.py#L394) |
| function | `chat_tree` | `(kind=…, root=…, path=…)` | Mappe-listing til Code-mode fil-træ. Blokerende fs/bro-kald offloades til tråd | [src](../../../apps/api/jarvis_api/routes/chat.py#L402) |
| function | `_tree_sync` | `(kind, root, path, role=…, uid=…)` | Container: navngivne rolle-scopede roots, path-jailed. Workstation: via broen. | [src](../../../apps/api/jarvis_api/routes/chat.py#L413) |
| function | `_parse_git_status` | `(branch_out, porcelain_out, numstat_out)` | Parse git-output → {branch, dirty, added, removed}. | [src](../../../apps/api/jarvis_api/routes/chat.py#L450) |
| function | `_git_status_sync` | `(kind, root, uid=…)` | BLOKERENDE git-opsamling — KØRES I TRÅD (asyncio.to_thread) så uvicorn- | [src](../../../apps/api/jarvis_api/routes/chat.py#L468) |
| function | `chat_git_status` | `(kind=…, root=…)` | Git-state for det aktive workspace (header-chip i code-mode). Det blokerende | [src](../../../apps/api/jarvis_api/routes/chat.py#L511) |
| function | `get_workspace_trust` | `(kind=…, root=…)` | Er det aktuelle workspace betroet for den indloggede bruger? | [src](../../../apps/api/jarvis_api/routes/chat.py#L521) |
| class | `WorkspaceTrustRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L529) |
| function | `set_workspace_trust` | `(request)` | Markér/afmarkér et workspace som betroet (skrive/exec-gate i code-mode). | [src](../../../apps/api/jarvis_api/routes/chat.py#L536) |
| class | `ChatStreamRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L547) |
| function | `_resolve_visible_target` | `(uid, provider_choice, model)` | Rolle-bevidst (provider, model)-override for en visible-run. | [src](../../../apps/api/jarvis_api/routes/chat.py#L578) |
| function | `_visible_capable_providers` | `()` | Providers som stream_visible_model faktisk kan eksekvere til chat. | [src](../../../apps/api/jarvis_api/routes/chat.py#L626) |
| function | `_list_visible_providers_sync` | `()` | {id, models[]} for hver visible-klar provider med enabled modeller i | [src](../../../apps/api/jarvis_api/routes/chat.py#L636) |
| function | `_list_ollama_models_sync` | `()` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L705) |
| function | `chat_ollama_models` | `()` | Tilgængelige ollama-modeller på containeren (OWNER-only). | [src](../../../apps/api/jarvis_api/routes/chat.py#L714) |
| class | `_TerminalRunBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L736) |
| function | `_terminal_run_sync` | `(command, cwd)` | BLOKERENDE server-side kommando-kørsel — KØRES I TRÅD. cwd contained til | [src](../../../apps/api/jarvis_api/routes/chat.py#L741) |
| function | `chat_terminal_run` | `(body)` | Code-mode terminal-rude (§17), container-side: kør én kommando server-side | [src](../../../apps/api/jarvis_api/routes/chat.py#L765) |
| function | `chat_visible_providers` | `()` | Alle visible-klare providers + deres modeller (OWNER-only). | [src](../../../apps/api/jarvis_api/routes/chat.py#L784) |
| class | `ChatSessionCreateRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L806) |
| class | `ChatSessionRenameRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L812) |
| function | `chat_sessions` | `()` | List chat sessions. | [src](../../../apps/api/jarvis_api/routes/chat.py#L817) |
| function | `chat_search_sessions` | `(q=…, limit=…)` | Søg sessioner på titel + besked-indhold. Scopes pr. bruger som | [src](../../../apps/api/jarvis_api/routes/chat.py#L834) |
| function | `chat_active_runs` | `()` | Sessioner med et aktivt visible-run lige nu (#8 — autonome/baggrunds-runs). | [src](../../../apps/api/jarvis_api/routes/chat.py#L844) |
| function | `chat_cancel_active` | `(session_id)` | Afbryd det run der kører for sessionen (mobil/desk stop-knap naar klienten | [src](../../../apps/api/jarvis_api/routes/chat.py#L874) |
| function | `chat_run_subscribe` | `(run_id, from_idx=…)` | Gen-abonner paa et server-autoritativt run fra et offset (mobil-reconnect | [src](../../../apps/api/jarvis_api/routes/chat.py#L894) |
| function | `chat_session_live` | `(session_id)` | Attach til sessionens aktive run fra offset 0 (cross-device + foreground- | [src](../../../apps/api/jarvis_api/routes/chat.py#L958) |
| function | `chat_session_follow` | `(session_id)` | Token-stream det aktive autonome run i sessionen (desk-pickup af wakeup). | [src](../../../apps/api/jarvis_api/routes/chat.py#L1018) |
| function | `chat_context_info` | `()` | Kontekst-tærskler til composer-ringen (#9). Kun ægte config-tal: | [src](../../../apps/api/jarvis_api/routes/chat.py#L1067) |
| function | `chat_context_usage` | `(session_id=…, provider=…, model=…)` | ÆGTE kontekst-fyld for en session — backend-autoritativt. | [src](../../../apps/api/jarvis_api/routes/chat.py#L1082) |
| function | `_system_overhead_tokens` | `(provider, model, session_id)` | Estimér tokens i den STABILE system-prefix (identitet + regler + tool-katalog) — det | [src](../../../apps/api/jarvis_api/routes/chat.py#L1158) |
| class | `_CompactNowBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat.py#L1188) |
| function | `chat_compact_now` | `(body)` | Manuel compaction (som Claude Codes /compact). Udløser den SAMME baggrunds-motor som | [src](../../../apps/api/jarvis_api/routes/chat.py#L1194) |
| function | `chat_session_milestones` | `(session_id=…)` | Milepæle (kapitler) til navigations-rail'en — som Claude Code's mark_chapter. Segmenterer | [src](../../../apps/api/jarvis_api/routes/chat.py#L1236) |
| function | `chat_model_context` | `(provider=…, model=…)` | Ægte context-ring pr. provider/model: modellens vindue + autocompact-punkt | [src](../../../apps/api/jarvis_api/routes/chat.py#L1253) |
| function | `chat_create_session` | `(request)` | Opret en ny chat-session (valgfrit bundet til et code-mode workspace). | [src](../../../apps/api/jarvis_api/routes/chat.py#L1267) |
| function | `chat_session` | `(session_id)` | Hent én chat-session ud fra id. 404 hvis den ikke findes; ellers {session: ...}. | [src](../../../apps/api/jarvis_api/routes/chat.py#L1278) |
| function | `chat_rename_session` | `(session_id, request)` | Omdøb en chat-session til request.title. 404 hvis sessionen ikke findes; | [src](../../../apps/api/jarvis_api/routes/chat.py#L1287) |
| function | `chat_delete_session` | `(session_id)` | Slet en chat-session. 404 hvis den ikke findes; ellers {ok: True, session_id}. | [src](../../../apps/api/jarvis_api/routes/chat.py#L1297) |
| function | `chat_stream` | `(request)` | Legacy/mobil chat-stream-endpoint (v1 SSE). Injicerer commit-enforcement- | [src](../../../apps/api/jarvis_api/routes/chat.py#L1305) |
| function | `chat_approve_tool` | `(approval_id)` | Approve a pending tool approval and run it. Resolves in a thread (deadlock- | [src](../../../apps/api/jarvis_api/routes/chat.py#L1473) |
| function | `chat_deny_tool` | `(approval_id)` | Deny a pending tool approval (does not run the tool). Resolves in a thread. | [src](../../../apps/api/jarvis_api/routes/chat.py#L1492) |
| function | `chat_cancel_run` | `(run_id)` | Afbryd et aktivt visible-run via run_id. 404 hvis runnet ikke er aktivt; | [src](../../../apps/api/jarvis_api/routes/chat.py#L1506) |
| function | `chat_steer_run` | `(run_id, body)` | Mid-flight steer: inject a user message into a running visible-run. | [src](../../../apps/api/jarvis_api/routes/chat.py#L1519) |
| function | `chat_client_tool_result` | `(run_id, body)` | Fase 1 (jarvis-code↔v2 forening): klienten leverer resultatet af et | [src](../../../apps/api/jarvis_api/routes/chat.py#L1533) |

## `apps/api/jarvis_api/routes/chat_stream_v2.py`
_POST /chat/stream/v2 — Anthropic-style SSE protokol._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_ToolResultItem` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L32) |
| class | `_ToolResultsBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L38) |
| function | `chat_tool_results` | `(body)` | Client submits locally-executed tool results; resolve the paused visible run. | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L44) |
| function | `maybe_handle_override` | `(text, session_id)` | Owner-override (§6.3) i webchat/desk-kanalen: `!override <TOTP>` / | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L54) |
| function | `_override_v2_response` | `(reply, *, session_id, model, provider, lane)` | Byg et minimalt men protokol-korrekt v2-SSE-svar for en override-kvittering, | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L74) |
| function | `chat_stream_v2` | `(request)` | Anthropic-style streaming alternative til /chat/stream. | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L107) |

## `apps/api/jarvis_api/routes/cheap_balancer.py`
_Mission Control endpoints for cheap_lane_balancer telemetry + controls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_state` | `()` | Return full snapshot: pool, slot states, recent calls. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L12) |
| function | `reset` | `(slot_id)` | Clear breaker, cooldown, and consecutive_failures for a slot. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L19) |
| function | `disable` | `(slot_id)` | Force a slot's weight to 0 (excluded from selection until enabled). | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L26) |
| function | `enable` | `(slot_id)` | Restore a manually-disabled slot to selection eligibility. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L33) |
| function | `refresh` | `()` | Rebuild slot pool from provider_router.json. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L40) |

## `apps/api/jarvis_api/routes/connectors.py`
_Connectors-API til jarvis-desk Marketplace (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_uid` | `()` | — | [src](../../../apps/api/jarvis_api/routes/connectors.py#L17) |
| class | `_EnabledBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/connectors.py#L22) |
| function | `get_connectors` | `()` | — | [src](../../../apps/api/jarvis_api/routes/connectors.py#L27) |
| function | `post_enabled` | `(connector_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/connectors.py#L35) |
| function | `delete_connector` | `(connector_id)` | — | [src](../../../apps/api/jarvis_api/routes/connectors.py#L46) |

## `apps/api/jarvis_api/routes/cowork.py`
_Cowork-dashboard routes. Tynde — al opsamling sker i core.services.cowork_feed,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_role_owner` | `()` | (is_owner, user_id) for den indloggede bruger. Owner afgøres af bruger- | [src](../../../apps/api/jarvis_api/routes/cowork.py#L15) |
| function | `_resolve_item` | `(item_id, decision)` | Router en godkendelses-beslutning til den rette eksisterende resolver. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L31) |
| function | `cowork_queue` | `()` | Godkendelses-kø for den indloggede bruger (owner ser alt). Bygges via | [src](../../../apps/api/jarvis_api/routes/cowork.py#L62) |
| function | `cowork_plans` | `()` | Planer for den indloggede bruger (owner ser alt) via cowork_feed.list_plans | [src](../../../apps/api/jarvis_api/routes/cowork.py#L71) |
| function | `cowork_todos` | `()` | Todo-feed for den indloggede bruger (owner ser alt) via | [src](../../../apps/api/jarvis_api/routes/cowork.py#L80) |
| function | `cowork_create_todo` | `(payload=…)` | Opret en cowork-todo fra payload["content"]. Owner-only (403 ellers); | [src](../../../apps/api/jarvis_api/routes/cowork.py#L92) |
| function | `cowork_set_todo_status` | `(todo_id, payload=…)` | Sæt status på en todo. Owner-only (403 ellers); status skal være en af | [src](../../../apps/api/jarvis_api/routes/cowork.py#L106) |
| function | `cowork_delete_todo` | `(todo_id)` | Slet en todo. Owner-only (403 ellers). Kalder remove_todo_anywhere i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L120) |
| function | `cowork_set_todo_expiry` | `(todo_id, payload=…)` | Sæt (eller ryd) udløbstidspunkt på en todo fra payload["expires_at"] — tom | [src](../../../apps/api/jarvis_api/routes/cowork.py#L130) |
| function | `cowork_channels` | `()` | Kanal-status via cowork_feed.channel_status i to_thread. Owner-only (403 | [src](../../../apps/api/jarvis_api/routes/cowork.py#L143) |
| function | `cowork_agents` | `()` | Aktive dispatch-agenter (§19.5 command center). Owner-only. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L154) |
| function | `cowork_approve` | `(item_id)` | Godkend et kø-item (proposal/initiative/capability) via _resolve_item i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L164) |
| function | `cowork_reject` | `(item_id)` | Afvis et kø-item (proposal/initiative/capability) via _resolve_item i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L170) |
| function | `cowork_share_guard` | `()` | Ventende "privat eller del?"-beslutninger via share_guard_store.list_pending | [src](../../../apps/api/jarvis_api/routes/cowork.py#L179) |
| function | `cowork_share_guard_resolve` | `(decision_id, shared)` | Afgør en share-beslutning. shared=true → okay at dele; false → hold privat. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L191) |
| function | `cowork_ui_panel_pending` | `()` | Ventende UI-panel-åbnings-kald via ui_panel_store.list_pending i to_thread; | [src](../../../apps/api/jarvis_api/routes/cowork.py#L207) |
| function | `cowork_ui_panel_ack` | `(request_id)` | Kvittér et UI-panel-kald som håndteret via ui_panel_store.ack_panel i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L216) |
| function | `cowork_app_dispatch_pending` | `()` | Ventende runtime→app-instruktioner via app_dispatch_store.list_pending i | [src](../../../apps/api/jarvis_api/routes/cowork.py#L229) |
| function | `cowork_app_dispatch_ack` | `(dispatch_id)` | Kvittér en app-dispatch som udført via app_dispatch_store.ack i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L238) |

## `apps/api/jarvis_api/routes/files.py`
_File download route — serves files Jarvis has published to ~/.jarvis-v2/files/._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_files_dir` | `()` | — | [src](../../../apps/api/jarvis_api/routes/files.py#L17) |
| function | `download_file` | `(filename)` | — | [src](../../../apps/api/jarvis_api/routes/files.py#L23) |
| function | `list_files` | `()` | — | [src](../../../apps/api/jarvis_api/routes/files.py#L43) |

## `apps/api/jarvis_api/routes/health.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `health` | `()` | — | [src](../../../apps/api/jarvis_api/routes/health.py#L10) |

## `apps/api/jarvis_api/routes/interlanguage_blind.py`
_Interlanguage validation — Bjørn blind dommer UI route._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_expressions_by_peer` | `(peer_id, limit)` | Hent op til limit random expressions fra peer. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L57) |
| function | `_generate_alpha_trials` | `(session_id, mode)` | Generér 50 α-trials — 10 fra hver af 5 peers, shuffled. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L70) |
| function | `_generate_delta_trials` | `(session_id, mode, start_idx)` | Generér 25 δ-trials — anchor (jarvis) + 2 candidates (1 +JP, 1 -alone). | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L91) |
| function | `_strip_peer_from_trial` | `(trial)` | Fjern peer-id og other-metadata fra trial-dict før vi sender til frontend. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L136) |
| class | `StartSessionRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L154) |
| function | `start_session` | `(body)` | Start ny blind-dommer session. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L160) |
| function | `next_trial` | `(session_id=…)` | Hent næste ubevarede trial i sessionen — uden true-peer-id leak. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L187) |
| class | `AnswerRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L195) |
| function | `submit_answer_route` | `(body)` | Submit svar. Returnerer correctness men IKKE forkert/rigtigt-besked. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L201) |
| function | `progress` | `(session_id=…)` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L222) |
| class | `FinishRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L226) |
| function | `finish_session` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L232) |
| function | `confusion` | `(session_id=…)` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L240) |
| function | `serve_phase4_ui` | `()` | Phase 4 binary blind test: jarvis_full vs jarvis_bare. | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L253) |
| function | `serve_ui` | `()` | — | [src](../../../apps/api/jarvis_api/routes/interlanguage_blind.py#L269) |

## `apps/api/jarvis_api/routes/internal_discord.py`
_Internal loopback endpoint for cross-process Discord dispatch._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DispatchRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/internal_discord.py#L27) |
| function | `dispatch` | `(req, request)` | — | [src](../../../apps/api/jarvis_api/routes/internal_discord.py#L33) |

## `apps/api/jarvis_api/routes/internal_errors.py`
_Internal loopback endpoint for canonical error reports (Fase 0)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_Origin` | `` | — | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L46) |
| class | `ErrorReport` | `` | Canonical fejl-wire-form (REVIEW §4 / impl-plan §3). Kun kind/severity/ | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L51) |
| function | `_build_envelope` | `(*, kind, origin_cluster, run_id, detail, scope)` | Byg en ErrorEnvelope fra kind. Foretrækker Fase-0-udvidelsen envelope_from_kind | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L66) |
| function | `_route_into_central` | `(report)` | Router én canonical fejl ind i eksisterende Central-maskineri. Returnerer | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L80) |
| function | `report_error` | `(report, request)` | Modtag én canonical fejl og router den ind i Central. Returnerer 202. | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L166) |

## `apps/api/jarvis_api/routes/internal_runtime_surface.py`
_Internal runtime-surface endpoint — proxy-mål for Centralens self/mind-flader._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_loopback` | `(request)` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L25) |
| function | `_living_executive` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L33) |
| function | `_self_model` | `()` | LIGHT self-model: kun top-level tællere, ikke den 255KB nestede payload | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L38) |
| function | `_world_model` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L56) |
| function | `_inner_life` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L63) |
| function | `_affect` | `()` | Nervesystemets affektive fordeling — læses i RUNTIME-processen hvor | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L68) |
| function | `_hardware_body` | `()` | Live hardware-krop (CPU/temp/disk/RAM/GPU) — læses i runtime hvor psutil-samlingen sker. | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L75) |
| function | `_soul` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L82) |
| function | `_dark_products` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L87) |
| function | `_light` | `(surface)` | §24.4-reduktion: udled KUN skalarer + længder fra en fuld surface. | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L92) |
| function | `_open_loops` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L118) |
| function | `_runtime_awareness` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L125) |
| function | `_runtime_self_knowledge` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L132) |
| function | `_counterfactual` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L139) |
| function | `_autonomous_history` | `()` | Jarvis' autonome historie grupperet pr. oprindelse (drøm/råd/arbejde/…): antal | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L146) |
| function | `_gate_verdicts` | `()` | Persistent verdict-fordeling pr. governet gate (survives restart). DB-backed → | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L154) |
| function | `get_runtime_surface` | `(name, request)` | Return the named runtime-surface builder's output (raw). Loopback-only, self-safe. | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L182) |

