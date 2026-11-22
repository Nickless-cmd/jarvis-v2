# `apps.api.jarvis_api.routes.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `apps/api/jarvis_api/routes/chat_flow_preferences.py`
_Self-scoped API for Desk Chat Flow presentation preferences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_StrictModel` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L23) |
| class | `PreferenceUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L27) |
| class | `OnboardingClaim` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L32) |
| class | `OnboardingAck` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L36) |
| class | `Observation` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L40) |
| class | `SuggestionOutcome` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L46) |
| function | `_principal` | `()` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L51) |
| function | `preferences_get` | `()` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L59) |
| function | `preferences_patch` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L64) |
| function | `onboarding_claim` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L76) |
| function | `onboarding_ack` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L81) |
| function | `observations_post` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L89) |
| function | `suggestion_outcome` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/chat_flow_preferences.py#L99) |

## `apps/api/jarvis_api/routes/chat_inbox.py`
_Bjørns egen vej ind i indbakken — den fjerde skriver._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InboxFlagRequest` | `` | Det et menneske flagger. | [src](../../../apps/api/jarvis_api/routes/chat_inbox.py#L39) |
| function | `flag_i_indbakken` | `(req)` | Opret en post i den autentificerede brugers indbakke. | [src](../../../apps/api/jarvis_api/routes/chat_inbox.py#L53) |

## `apps/api/jarvis_api/routes/chat_projects.py`
_Projekt-kontekst og CI-status til Desk._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BindProjektBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L26) |
| class | `OpretProjektBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L30) |
| function | `_bruger` | `()` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L35) |
| function | `_kraev_session` | `(session_id, uid)` | Samtalen skal tilhøre kalderen. Ellers 404 — ikke 403, så et gæt ikke kan bekræftes. | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L44) |
| function | `_filstoerrelse` | `(sti)` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L54) |
| function | `_projekt_ud` | `(projekt)` | Service-form (project_id/materials) → Desk-kontrakt (id/files). | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L61) |
| function | `list_projekter` | `()` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L80) |
| function | `opret_projekt` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L89) |
| function | `hent_session_projekt` | `(session_id)` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L105) |
| function | `bind_session_projekt` | `(session_id, body)` | — | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L115) |
| function | `_git` | `(root, *args)` | Kør git i ``root`` uden shell. Fejler lukket — tom streng, ingen gæt. | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L133) |
| function | `_repo_fra_root` | `(root)` | ``git@github.com:eier/rep.git`` eller https-URL → ``eier/rep``. | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L149) |
| function | `git_ci_status` | `(root=…, branch=…, kind=…)` | CI-status for en branch i et lokalt repo. | [src](../../../apps/api/jarvis_api/routes/chat_projects.py#L164) |

## `apps/api/jarvis_api/routes/chat_rewind.py`
_`POST /chat/sessions/{id}/rewind` og `…/rewind/{rewind_id}/undo`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RewindRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_rewind.py#L19) |
| function | `chat_rewind` | `(session_id, request)` | Fjern en af dine beskeder og alt efter den. Svaret bærer beskedens tekst | [src](../../../apps/api/jarvis_api/routes/chat_rewind.py#L24) |
| function | `chat_rewind_undo` | `(session_id, rewind_id)` | Læg beskederne tilbage — kun så længe der ikke er skrevet siden. | [src](../../../apps/api/jarvis_api/routes/chat_rewind.py#L36) |

## `apps/api/jarvis_api/routes/chat_run_streams.py`
_Active-run discovery and replayable SSE follow routes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_journal_sessions` | `()` | Sessioner med et levende run i den delte journal. | [src](../../../apps/api/jarvis_api/routes/chat_run_streams.py#L35) |
| function | `chat_active_runs` | `()` | Sessioner med et aktivt visible-run lige nu. | [src](../../../apps/api/jarvis_api/routes/chat_run_streams.py#L56) |
| function | `subscribe_authorized` | `(location, from_idx)` | Authorize and resolve one stream without inventing completion. | [src](../../../apps/api/jarvis_api/routes/chat_run_streams.py#L116) |
| function | `chat_run_subscribe` | `(run_id, from_idx=…)` | Gen-abonner paa et server-autoritativt run fra et offset. | [src](../../../apps/api/jarvis_api/routes/chat_run_streams.py#L147) |
| function | `chat_session_live` | `(session_id)` | Attach til sessionens aktive run fra offset nul. | [src](../../../apps/api/jarvis_api/routes/chat_run_streams.py#L153) |
| function | `chat_session_follow` | `(session_id)` | Token-stream det aktive autonome run i sessionen. | [src](../../../apps/api/jarvis_api/routes/chat_run_streams.py#L165) |

## `apps/api/jarvis_api/routes/chat_session_view.py`
_`GET/PUT /chat/sessions/{id}/view` — samtalens visningstilstand._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SessionViewRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_session_view.py#L17) |
| function | `kraev_adgang` | `(session_id)` | 403 hvis den nuværende bruger ikke må røre samtalen. | [src](../../../apps/api/jarvis_api/routes/chat_session_view.py#L21) |
| function | `chat_session_view` | `(session_id)` | Samtalens visningstilstand: normal, thinking eller verbose. | [src](../../../apps/api/jarvis_api/routes/chat_session_view.py#L33) |
| function | `chat_set_session_view` | `(session_id, request)` | Skift samtalens visningstilstand. Gælder fra næste runde, også midt i et svar. | [src](../../../apps/api/jarvis_api/routes/chat_session_view.py#L41) |

## `apps/api/jarvis_api/routes/chat_stream_v2.py`
_POST /chat/stream/v2 — Anthropic-style SSE protokol._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `udled_tool_scope` | `(mode, kind)` | Mode + samtalens art → tool-scope. Ren funktion, så reglen kan testes. | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L32) |
| function | `_ollama_model_tags` | `()` | Set of model names ollama currently serves. Cached 120s; fail-open (empty set). | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L73) |
| function | `_resolve_ollama_model_name` | `(model)` | Resolve a (possibly bare) ollama model name to an actually-served tag. | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L100) |
| class | `_ToolResultItem` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L120) |
| class | `_ToolResultsBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L126) |
| function | `chat_tool_results` | `(body)` | Client submits locally-executed tool results; resolve the paused visible run. | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L132) |
| class | `_WarmBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L149) |
| function | `chat_warm` | `(body)` | Varm den aktive sessions prefix i DeepSeeks cache (prewarm-on-return). | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L157) |
| function | `maybe_handle_override` | `(text, session_id)` | Owner-override (§6.3) i webchat/desk-kanalen: `!override <TOTP>` / | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L189) |
| function | `_override_v2_response` | `(reply, *, session_id, model, provider, lane)` | Byg et minimalt men protokol-korrekt v2-SSE-svar for en override-kvittering, | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L209) |
| function | `chat_stream_v2` | `(request)` | Anthropic-style streaming alternative til /chat/stream. | [src](../../../apps/api/jarvis_api/routes/chat_stream_v2.py#L242) |

## `apps/api/jarvis_api/routes/chat_workspace_trust.py`
_Workspace-tillid som sin egen rute-flade — udskilt fra `chat.py` 3/10-2026._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `WorkspaceTrustRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/chat_workspace_trust.py#L20) |
| function | `get_workspace_trust` | `(kind=…, root=…)` | Er det aktuelle workspace betroet for den indloggede bruger? | [src](../../../apps/api/jarvis_api/routes/chat_workspace_trust.py#L27) |
| function | `list_workspace_trust` | `(kind=…)` | De mapper brugeren har betroet — grundlaget for workstation-vaelgeren. | [src](../../../apps/api/jarvis_api/routes/chat_workspace_trust.py#L36) |
| function | `set_workspace_trust` | `(request)` | Markér/afmarkér et workspace som betroet (skrive/exec-gate i code-mode). | [src](../../../apps/api/jarvis_api/routes/chat_workspace_trust.py#L49) |

## `apps/api/jarvis_api/routes/cheap_balancer.py`
_Mission Control endpoints for cheap_lane_balancer telemetry + controls._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `get_state` | `()` | Return full snapshot: pool, slot states, recent calls. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L12) |
| function | `reset` | `(slot_id)` | Clear breaker, cooldown, and consecutive_failures for a slot. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L19) |
| function | `disable` | `(slot_id)` | Force a slot's weight to 0 (excluded from selection until enabled). | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L26) |
| function | `enable` | `(slot_id)` | Restore a manually-disabled slot to selection eligibility. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L33) |
| function | `refresh` | `()` | Rebuild slot pool from provider_router.json. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L40) |
| function | `history` | `(timer=…, lane=…)` | Pr. udbyder+model i vinduet: kald, fejl, succesrate, latens, pris. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L53) |
| function | `errors` | `(timer=…, lane=…, loft=…)` | De nyeste fejl med besked. `antal_i_vinduet` taelles separat fra loftet. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L60) |
| function | `timeseries` | `(timer=…, lane=…, spand_minutter=…)` | Kald, fejl og latens pr. tidsspand. | [src](../../../apps/api/jarvis_api/routes/cheap_balancer.py#L67) |

## `apps/api/jarvis_api/routes/cheap_lane_control.py`
_Owner-only read surface for the Cheap Lane control center._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_ControlBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L37) |
| class | `_SimulationBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L45) |
| function | `_require_owner` | `()` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L50) |
| function | `_since` | `(hours)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L56) |
| function | `_safe_row` | `(row)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L60) |
| function | `_filtered_logs` | `(*, hours, provider=…, model=…, auth_profile=…, daemon=…, status=…, error_class=…, correlation_id=…, query=…, cursor=…, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L69) |
| function | `_export_rows` | `(*, hours)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L93) |
| function | `_config_fingerprints` | `()` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L108) |
| function | `dashboard` | `(hours=…)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L117) |
| function | `capacity` | `()` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L123) |
| function | `logs` | `(hours=…, provider=…, model=…, auth_profile=…, daemon=…, status=…, error_class=…, correlation_id=…, query=…, cursor=…, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L129) |
| function | `export_logs` | `(format=…, hours=…)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L155) |
| function | `log_detail` | `(invocation_id)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L177) |
| function | `diagnostics` | `()` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L186) |
| function | `audit` | `(limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L192) |
| function | `export_diagnostics` | `(hours=…)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L198) |
| function | `control` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L218) |
| function | `simulate` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/cheap_lane_control.py#L246) |

## `apps/api/jarvis_api/routes/companion.py`
_Companion-endpoints — Jarvis' tre ønsker til mobil-appen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `companion_presence` | `()` | Er han vågen — og hvad lavede han sidst? | [src](../../../apps/api/jarvis_api/routes/companion.py#L35) |
| function | `companion_senses` | `(limit=…)` | Sansernes Arkiv — hvad Jarvis har set i hjemmet. Kun husstanden. | [src](../../../apps/api/jarvis_api/routes/companion.py#L46) |
| function | `companion_thoughts` | `(limit=…)` | Jarvis' initiativer — også dem der blev holdt tilbage. | [src](../../../apps/api/jarvis_api/routes/companion.py#L66) |

## `apps/api/jarvis_api/routes/composer_suggest_routes.py`
_`/composer/suggest` — hvad der kunne skrives videre i komponisten._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Udkast` | `` | — | [src](../../../apps/api/jarvis_api/routes/composer_suggest_routes.py#L36) |
| class | `Valg` | `` | Hvad der skete med et forslag. Se `core.runtime.db_composer_choice`. | [src](../../../apps/api/jarvis_api/routes/composer_suggest_routes.py#L46) |
| function | `suggest` | `(krop)` | Et forslag, eller tom streng. Fejler aldrig. | [src](../../../apps/api/jarvis_api/routes/composer_suggest_routes.py#L59) |
| function | `moenster` | `()` | Hvad forslaget har lært af hans valg — i klartekst. | [src](../../../apps/api/jarvis_api/routes/composer_suggest_routes.py#L79) |
| function | `choice` | `(krop)` | Registrér hvad der skete med et forslag. Fejler aldrig. | [src](../../../apps/api/jarvis_api/routes/composer_suggest_routes.py#L106) |

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
| function | `_role_owner` | `()` | (is_owner, user_id) for den indloggede bruger. Owner afgøres af bruger- | [src](../../../apps/api/jarvis_api/routes/cowork.py#L17) |
| function | `_resolve_item` | `(item_id, decision)` | Router en godkendelses-beslutning til den rette eksisterende resolver. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L33) |
| function | `cowork_queue` | `()` | Godkendelses-kø for den indloggede bruger (owner ser alt). Bygges via | [src](../../../apps/api/jarvis_api/routes/cowork.py#L69) |
| function | `cowork_opmaerksomhed` | `()` | Tilstands-hjernen: ÉN samlet tilstand for den indloggede brugers | [src](../../../apps/api/jarvis_api/routes/cowork.py#L78) |
| function | `cowork_opmaerksomhed_set` | `(session_id)` | Brugeren har åbnet samtalen — dens «færdig»/«fejlede» forsvinder. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L88) |
| function | `cowork_side_tasks` | `(scope=…)` | Jarvis' flaggede sideopgaver. `scope=open` (standard) er de åbne; | [src](../../../apps/api/jarvis_api/routes/cowork.py#L99) |
| function | `cowork_side_tasks_stream` | `()` | SSE: ét signal når sideopgave-listen ændrer sig — i stedet for tre pollere. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L127) |
| function | `cowork_side_task_opret` | `(payload=…)` | Opret en sideopgave fra Desk — den flade Bjørn bad om 15/10-2026. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L197) |
| function | `cowork_side_task_rediger` | `(side_task_id, payload=…)` | Redigér en sideopgave der endnu ikke er taget op. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L238) |
| function | `cowork_side_task_status` | `(side_task_id, payload=…)` | Skift sideopgavens runtime-status; terminale opgaver kan ikke genåbnes. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L283) |
| function | `cowork_side_task_snooze` | `(side_task_id, payload=…)` | Udskyd en sideopgave til et tidspunkt — eller væk den før tid. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L313) |
| function | `cowork_side_task_skjul` | `(side_task_id, payload=…)` | Skjul eller vis en sideopgave i chatkortet — uden at lukke den. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L341) |
| function | `cowork_plans` | `()` | Planer for den indloggede bruger (owner ser alt) via cowork_feed.list_plans | [src](../../../apps/api/jarvis_api/routes/cowork.py#L365) |
| function | `cowork_todos` | `()` | Todo-feed for den indloggede bruger (owner ser alt) via | [src](../../../apps/api/jarvis_api/routes/cowork.py#L374) |
| function | `cowork_create_todo` | `(payload=…)` | Opret en cowork-todo fra payload["content"]. Owner-only (403 ellers); | [src](../../../apps/api/jarvis_api/routes/cowork.py#L386) |
| function | `cowork_set_todo_status` | `(todo_id, payload=…)` | Sæt status på en todo. Owner-only (403 ellers); status skal være en af | [src](../../../apps/api/jarvis_api/routes/cowork.py#L400) |
| function | `cowork_delete_todo` | `(todo_id)` | Slet en todo. Owner-only (403 ellers). Kalder remove_todo_anywhere i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L414) |
| function | `cowork_set_todo_expiry` | `(todo_id, payload=…)` | Sæt (eller ryd) udløbstidspunkt på en todo fra payload["expires_at"] — tom | [src](../../../apps/api/jarvis_api/routes/cowork.py#L424) |
| function | `cowork_channels` | `()` | Kanal-status via cowork_feed.channel_status i to_thread. Owner-only (403 | [src](../../../apps/api/jarvis_api/routes/cowork.py#L437) |
| function | `cowork_agents` | `()` | Aktive dispatch-agenter (§19.5 command center). Owner-only. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L448) |
| function | `cowork_approve` | `(item_id)` | Godkend et kø-item (proposal/initiative/capability) via _resolve_item i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L458) |
| function | `cowork_reject` | `(item_id)` | Afvis et kø-item (proposal/initiative/capability) via _resolve_item i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L464) |
| function | `cowork_share_guard` | `()` | Ventende "privat eller del?"-beslutninger via share_guard_store.list_pending | [src](../../../apps/api/jarvis_api/routes/cowork.py#L473) |
| function | `cowork_share_guard_resolve` | `(decision_id, shared)` | Afgør en share-beslutning. shared=true → okay at dele; false → hold privat. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L485) |
| function | `cowork_ui_panel_pending` | `()` | Ventende UI-panel-åbnings-kald via ui_panel_store.list_pending i to_thread; | [src](../../../apps/api/jarvis_api/routes/cowork.py#L501) |
| function | `cowork_ui_panel_ack` | `(request_id)` | Kvittér et UI-panel-kald som håndteret via ui_panel_store.ack_panel i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L510) |
| function | `cowork_app_dispatch_pending` | `()` | Ventende runtime→app-instruktioner via app_dispatch_store.list_pending i | [src](../../../apps/api/jarvis_api/routes/cowork.py#L523) |
| function | `cowork_app_dispatch_ack` | `(dispatch_id)` | Kvittér en app-dispatch som udført via app_dispatch_store.ack i to_thread. | [src](../../../apps/api/jarvis_api/routes/cowork.py#L532) |

## `apps/api/jarvis_api/routes/desk_operations.py`
_Small Desk-facing operational routers grouped for app registration._

_(no top-level classes or functions)_

## `apps/api/jarvis_api/routes/desktop_stream.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bruger_id` | `(krav, privilege)` | Hvem sessionen tilhører. Uden token (auth slået fra) er det ejeren. | [src](../../../apps/api/jarvis_api/routes/desktop_stream.py#L15) |
| function | `desktop_stream` | `(ws)` | Jarvis' Linux-desktop som JPEG-frames (binære beskeder) + input tilbage. | [src](../../../apps/api/jarvis_api/routes/desktop_stream.py#L31) |

## `apps/api/jarvis_api/routes/files.py`
_Udgivne filer — per bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_min_mappe` | `(*, opret=…)` | Den autentificerede brugers filmappe, eller 401. | [src](../../../apps/api/jarvis_api/routes/files.py#L52) |
| function | `ensure_files_dir` | `()` | Den autentificerede brugers mappe, oprettet. Bevarer det gamle navn, | [src](../../../apps/api/jarvis_api/routes/files.py#L70) |
| class | `LinkOenske` | `` | Hvilken fil, og hvor længe. | [src](../../../apps/api/jarvis_api/routes/files.py#L76) |
| function | `udsted_link` | `(req)` | Et kortlivet signeret link til én af MINE filer. | [src](../../../apps/api/jarvis_api/routes/files.py#L88) |
| function | `download_file` | `(filename, ws=…)` | Hent én fil — min egen, eller en andens via et gyldigt signeret link. | [src](../../../apps/api/jarvis_api/routes/files.py#L124) |
| function | `list_files` | `()` | MINE filer. Aldrig nogen andens, og aldrig de gamle faelles. | [src](../../../apps/api/jarvis_api/routes/files.py#L173) |

## `apps/api/jarvis_api/routes/flade_deferred_turn.py`
_Chat-fladers direkte, adresserede tool-turns._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `DeferredTurnAddressBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L28) |
| class | `DeferredToolTurnBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L36) |
| class | `DeferredApprovalStatusBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L42) |
| function | `_current_user_id` | `()` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L47) |
| function | `_kraev_adgang` | `(session_id)` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L52) |
| function | `_source_message_belongs` | `(message_id, session_id)` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L57) |
| function | `_adresse` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L68) |
| function | `_validér_adresse` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L78) |
| function | `_register_approval` | `(adresse, tool_name, arguments, raw)` | Byg kortet gennem samme approval-runtime som synlige model-runs. | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L99) |
| function | `_execute_chat_tool` | `(tool_name, arguments)` | Bind chat-scope omkring BÅDE katalogopslag og udførelse. | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L133) |
| function | `flade_deferred_tool_turn` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L153) |
| function | `flade_deferred_tool_status` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/flade_deferred_turn.py#L173) |

## `apps/api/jarvis_api/routes/flade_log.py`
_Klientlog ved renderbeslutningen — fire målepunkter, ingen guard._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `FladeSnapshot` | `` | Ét øjebliksbillede af en renderbeslutning. | [src](../../../apps/api/jarvis_api/routes/flade_log.py#L66) |
| function | `_antal_i_dag` | `()` | Antal linjer skrevet i dag. Læses kun når filen findes. | [src](../../../apps/api/jarvis_api/routes/flade_log.py#L82) |
| function | `flade_log` | `(snapshot)` | Modtag ét snapshot og skriv det. Svarer altid 202. | [src](../../../apps/api/jarvis_api/routes/flade_log.py#L96) |

## `apps/api/jarvis_api/routes/geo.py`
_HTTP-indgang til Nominatim-opslagene (PWA har ingen Electron-bro)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_label` | `(res, precise)` | Samme label som Electron-broen: «vej, by» (præcis) eller «by». | [src](../../../apps/api/jarvis_api/routes/geo.py#L18) |
| function | `geo_reverse` | `(lat=…, lon=…, precise=…)` | — | [src](../../../apps/api/jarvis_api/routes/geo.py#L27) |
| function | `geo_search` | `(q=…)` | — | [src](../../../apps/api/jarvis_api/routes/geo.py#L40) |

## `apps/api/jarvis_api/routes/git_panel.py`
_Git-panelets ruter: status, diff, stage, unstage, commit, log, push, worktrees._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_afkvot` | `(sti)` | `git status` citerer stier med mellemrum/specialtegn: "a b.txt". | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L46) |
| function | `parse_status` | `(tekst)` | `git status --porcelain=v1 --branch` → branch, tracking og filliste. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L54) |
| function | `parse_log` | `(tekst)` | Format `%H\x1f%h\x1f%an\x1f%aI\x1f%s\x1e` → liste af commits. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L109) |
| function | `parse_github_repo` | `(url)` | GitHub remote URL → owner/repo; andre remotes giver tom streng. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L123) |
| function | `parse_worktrees` | `(tekst)` | `git worktree list --porcelain` → liste. Første post er hovedtræet. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L134) |
| function | `rens_sti` | `(sti)` | Afvis stier der kunne læses som flag eller bryde ud af repoet. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L158) |
| function | `_mål` | `(kind, root)` | Validér target → (kind, rod, uid). Container = owner + server-repo. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L174) |
| function | `_git` | `(kind, rod, uid, *args)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L188) |
| function | `_fejl` | `(ud, standard=…)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L193) |
| function | `_status_sync` | `(kind, rod, uid)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L198) |
| function | `_diff_sync` | `(kind, rod, uid, path, mode)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L208) |
| function | `_stage_sync` | `(kind, rod, uid, paths, alle)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L237) |
| function | `_unstage_sync` | `(kind, rod, uid, paths, alle)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L243) |
| function | `_commit_sync` | `(kind, rod, uid, besked)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L258) |
| function | `_log_sync` | `(kind, rod, uid, grænse)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L281) |
| function | `_push_sync` | `(kind, rod, uid)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L293) |
| function | `_worktrees_sync` | `(kind, rod, uid)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L317) |
| class | `_PathsBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L330) |
| class | `_CommitBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L337) |
| class | `_PushBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L343) |
| function | `git_panel_status` | `(kind=…, root=…)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L349) |
| function | `git_panel_diff` | `(kind=…, root=…, path=…, mode=…)` | Diff for én fil (`path`) eller samlet (uden `path`). | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L355) |
| function | `_paths_eller_alle` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L370) |
| function | `git_panel_stage` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L379) |
| function | `git_panel_unstage` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L386) |
| function | `git_panel_commit` | `(body)` | Commit KUN det staged, med serverens attribution-trailere. | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L393) |
| function | `git_panel_log` | `(kind=…, root=…, limit=…)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L403) |
| function | `git_panel_push` | `(body)` | Push den aktuelle branch (sætter upstream til origin første gang). | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L409) |
| function | `git_panel_worktrees` | `(kind=…, root=…)` | — | [src](../../../apps/api/jarvis_api/routes/git_panel.py#L419) |

## `apps/api/jarvis_api/routes/github.py`
_Direct Desk adapter for existing GitHub PR/CI tool handlers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `CreatePrBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/github.py#L14) |
| function | `_bruger` | `()` | — | [src](../../../apps/api/jarvis_api/routes/github.py#L23) |
| function | `_result` | `(result)` | — | [src](../../../apps/api/jarvis_api/routes/github.py#L32) |
| function | `github_prs` | `(repo)` | — | [src](../../../apps/api/jarvis_api/routes/github.py#L39) |
| function | `github_ci` | `(repo, pull_number=…, commit_sha=…)` | — | [src](../../../apps/api/jarvis_api/routes/github.py#L46) |
| function | `github_create_pr` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/github.py#L54) |

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
| class | `DispatchRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/internal_discord.py#L30) |
| function | `dispatch` | `(req, request)` | — | [src](../../../apps/api/jarvis_api/routes/internal_discord.py#L36) |

## `apps/api/jarvis_api/routes/internal_errors.py`
_Internal loopback endpoint for canonical error reports (Fase 0)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_Origin` | `` | — | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L48) |
| class | `ErrorReport` | `` | Canonical fejl-wire-form (REVIEW §4 / impl-plan §3). Kun kind/severity/ | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L53) |
| function | `_build_envelope` | `(*, kind, origin_cluster, run_id, detail, scope)` | Byg en ErrorEnvelope fra kind. Foretrækker Fase-0-udvidelsen envelope_from_kind | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L68) |
| function | `_route_into_central` | `(report)` | Router én canonical fejl ind i eksisterende Central-maskineri. Returnerer | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L82) |
| function | `report_error` | `(report, request)` | Modtag én canonical fejl og router den ind i Central. Returnerer 202. | [src](../../../apps/api/jarvis_api/routes/internal_errors.py#L168) |

## `apps/api/jarvis_api/routes/internal_run_stream.py`
_Loopback-only endpoint serving the current process' run frame log._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internal_run_stream` | `(request, run_id, from_idx=…)` | — | [src](../../../apps/api/jarvis_api/routes/internal_run_stream.py#L24) |

## `apps/api/jarvis_api/routes/internal_runtime_surface.py`
_Internal runtime-surface endpoint — proxy-mål for Centralens self/mind-flader._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_require_loopback` | `(request)` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L27) |
| function | `_living_executive` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L35) |
| function | `_self_model` | `()` | LIGHT self-model: kun top-level tællere, ikke den 255KB nestede payload | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L40) |
| function | `_world_model` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L58) |
| function | `_inner_life` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L65) |
| function | `_affect` | `()` | Nervesystemets affektive fordeling — læses i RUNTIME-processen hvor | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L70) |
| function | `_hardware_body` | `()` | Live hardware-krop (CPU/temp/disk/RAM/GPU) — læses i runtime hvor psutil-samlingen sker. | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L77) |
| function | `_soul` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L84) |
| function | `_dark_products` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L89) |
| function | `_light` | `(surface)` | §24.4-reduktion: udled KUN skalarer + længder fra en fuld surface. | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L94) |
| function | `_open_loops` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L120) |
| function | `_runtime_awareness` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L127) |
| function | `_runtime_self_knowledge` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L134) |
| function | `_counterfactual` | `()` | — | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L141) |
| function | `_autonomous_history` | `()` | Jarvis' autonome historie grupperet pr. oprindelse (drøm/råd/arbejde/…): antal | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L148) |
| function | `_gate_verdicts` | `()` | Persistent verdict-fordeling pr. governet gate (survives restart). DB-backed → | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L156) |
| function | `_db_pool` | `()` | DB-forbindelses-poolen i DENNE proces — gjort læsbar i drift (15/10-2026). | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L164) |
| function | `get_runtime_surface` | `(name, request)` | Return the named runtime-surface builder's output (raw). Loopback-only, self-safe. | [src](../../../apps/api/jarvis_api/routes/internal_runtime_surface.py#L202) |

## `apps/api/jarvis_api/routes/jarvisx.py`
_JarvisX-specific routes — small endpoints used by the desktop app._

_(no top-level classes or functions)_

## `apps/api/jarvis_api/routes/jarvisx_authtokens.py`
_JarvisX bearer-token issuance + verification route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_IssueTokenPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_authtokens.py#L27) |
| class | `_RefreshTokenPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_authtokens.py#L33) |
| function | `refresh_auth_token` | `(payload)` | Veksl en refresh-token til et nyt access+refresh-par (§22.6). PUBLIC — | [src](../../../apps/api/jarvis_api/routes/jarvisx_authtokens.py#L39) |
| function | `renew_auth_token` | `(authorization=…)` | Veksl DET MEDSENDTE bearer-token til et friskt et. PUBLIC. | [src](../../../apps/api/jarvis_api/routes/jarvisx_authtokens.py#L51) |
| function | `issue_auth_token` | `(payload)` | Mint a signed bearer token for a user. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_authtokens.py#L80) |
| function | `whoami_token` | `(authorization=…)` | Inspect the bearer token attached to this request. | [src](../../../apps/api/jarvis_api/routes/jarvisx_authtokens.py#L101) |

## `apps/api/jarvis_api/routes/jarvisx_bridge.py`
_WebSocket endpoint for JarvisX tool-bridge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `internal_dispatch` | `(request)` | Intern cross-process dispatch (runtime-proces → api-proces). | [src](../../../apps/api/jarvis_api/routes/jarvisx_bridge.py#L35) |
| function | `jarvisx_bridge_ws` | `(ws)` | Accept WS from JarvisX-app, route messages between bridge and runtime. | [src](../../../apps/api/jarvis_api/routes/jarvisx_bridge.py#L163) |

## `apps/api/jarvis_api/routes/jarvisx_channels.py`
_JarvisX channels + scheduling state route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `channels_state` | `()` | Aggregate gateway status for the Channels view. | [src](../../../apps/api/jarvis_api/routes/jarvisx_channels.py#L20) |
| function | `_scheduling_visible_to` | `(item, user_id)` | True if `item` should be shown to a user with this id. | [src](../../../apps/api/jarvis_api/routes/jarvisx_channels.py#L103) |
| function | `_filter_scheduling_payload` | `(payload, user_id)` | Recursively filter dicts/lists in a scheduling-state payload. | [src](../../../apps/api/jarvis_api/routes/jarvisx_channels.py#L126) |
| function | `scheduling_state` | `()` | Aggregate scheduled tasks + recurring + self-wakeups. | [src](../../../apps/api/jarvis_api/routes/jarvisx_channels.py#L136) |

## `apps/api/jarvis_api/routes/jarvisx_common.py`
_Shared constants + guards for the JarvisX route modules._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_resolve_workspace` | `(name)` | Resolve a workspace name to its directory, with traversal guard. | [src](../../../apps/api/jarvis_api/routes/jarvisx_common.py#L46) |
| function | `_safe_subpath` | `(workspace_dir, relative)` | Resolve a relative path under workspace_dir with traversal guard. | [src](../../../apps/api/jarvis_api/routes/jarvisx_common.py#L65) |
| function | `_require_owner` | `()` | Raise 403 if the current request isn't from the owner. | [src](../../../apps/api/jarvis_api/routes/jarvisx_common.py#L78) |

## `apps/api/jarvis_api/routes/jarvisx_dispatches.py`
_JarvisX Claude-Code dispatch dashboard route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_felt` | `(row, navn)` | Et kolonne-opslag der taaler at kolonnen ikke findes endnu. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L28) |
| function | `list_dispatches` | `(limit=…)` | Recent dispatches, running first then by started_at desc. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L46) |
| function | `dispatch_budget` | `()` | Current hour's dispatch budget — count + tokens vs caps. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L137) |
| function | `get_dispatch` | `(task_id)` | Full audit row + parsed spec for a single dispatch. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L163) |
| function | `get_dispatch_diff` | `(task_id)` | Live diff of a dispatch's worktree against main. | [src](../../../apps/api/jarvis_api/routes/jarvisx_dispatches.py#L180) |

## `apps/api/jarvis_api/routes/jarvisx_processes.py`
_JarvisX process-supervisor + trading + operator-wakeup route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `list_managed_processes` | `(include_stopped=…)` | List processes Jarvis has spawned via the process_supervisor. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L36) |
| function | `tail_managed_process_log` | `(name, lines=…)` | Return the tail of a managed process's combined stdout/stderr log. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L43) |
| function | `list_background_jobs` | `(include_done=…, session_id=…)` | Alle kørende baggrundsopgaver — supervisor OG operatørens egne shells. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L59) |
| function | `_jobs_snapshot` | `(*, uid, session_id, include_done)` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L89) |
| function | `_job_source_pump` | `(uid)` | One source sampler per operator identity, shared by all Desk streams. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L100) |
| function | `_sse_frame` | `(event, data, cursor=…)` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L118) |
| function | `stream_background_jobs` | `(session_id=…, after=…, last_event_id=…)` | Replayable live stream for the session-scoped Desk jobs projection. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L128) |
| function | `_operator_exec_for_jobs` | `(navn, args)` | Bro-kald til operatørens maskine. Adskilt, så testen kan erstatte den. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L199) |
| function | `pause_background_job` | `(kilde, job_id)` | Sæt en opgave på pause. Ejer-kun. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L206) |
| function | `resume_background_job` | `(kilde, job_id)` | Kør videre hvor den slap. Ejer-kun. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L213) |
| function | `stop_background_job` | `(kilde, job_id)` | Stop en opgave for altid. Ejer-kun. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L220) |
| function | `remove_background_job` | `(kilde, job_id)` | Fjern et FAERDIGT job fra panelet. Ejer-kun. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L227) |
| function | `_remove_job` | `(kilde, job_id)` | Slet det der KAN slettes — og sig nej til resten. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L233) |
| function | `_signal_job` | `(kilde, job_id, handling)` | Én vej for alle kilder — de signaleres bare ikke samme sted. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L289) |
| function | `stop_managed_process` | `(name, grace=…)` | SIGTERM (then SIGKILL after grace) a managed process. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L383) |
| function | `remove_managed_process` | `(name)` | Remove a stopped process from the registry. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L394) |
| class | `_SpawnPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L412) |
| function | `spawn_managed_process` | `(payload)` | Spawn a managed background process. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L420) |
| function | `trading_state` | `()` | Read the current trading-bot state. Read-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L479) |
| function | `_trading_inactive_default` | `(reason)` | Synthetic 'inactive' state so UI always has something to render. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L512) |
| function | `operator_wakeup_fired` | `(payload)` | Hit af jarvis-desk når en operator_wakeup-timer fyrer. | [src](../../../apps/api/jarvis_api/routes/jarvisx_processes.py#L545) |

## `apps/api/jarvis_api/routes/jarvisx_project.py`
_JarvisX project-anchor + file-watch route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kun_ejer` | `()` | Disse ruter læser og opremser værtens filsystem. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L19) |
| function | `_skip_dir` | `(navn)` | Sandt for mapper der ikke hoerer til i en projektvisning. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L50) |
| function | `_resolve_project_root` | `(root)` | Resolve a project root with strict guards. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L62) |
| function | `_safe_project_subpath` | `(root, rel)` | Resolve a relative path under the project root, refusing escapes. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L85) |
| function | `project_tree` | `(root=…, max_depth=…)` | Return a nested tree of the project root, depth-limited. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L98) |
| function | `project_list` | `(root=…, limit=…)` | Flat list of files under root (for @file autocomplete). | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L160) |
| function | `project_read` | `(root=…, path=…)` | Read a file from inside the project root with a 1 MB cap. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L202) |
| function | `project_notes_get` | `(root=…)` | Read .jarvisx/notes.md inside the anchored project, if it exists. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L243) |
| class | `ProjectNotesUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L267) |
| function | `project_notes_set` | `(payload)` | Write .jarvisx/notes.md inside the anchored project. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L273) |
| function | `_watch_lock` | `()` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L302) |
| class | `WatchAddRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L309) |
| class | `WatchPollRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L314) |
| function | `project_watch_add` | `(payload)` | Start watching a list of files/dirs for the session. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L319) |
| function | `project_watch_poll` | `(payload)` | Return the list of watched paths whose mtime changed since last poll. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L349) |
| function | `project_watch_clear` | `(payload)` | Stop all watches for a session. | [src](../../../apps/api/jarvis_api/routes/jarvisx_project.py#L382) |

## `apps/api/jarvis_api/routes/jarvisx_sessions.py`
_JarvisX chat-session support route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `preferences_get` | `()` | User-level UI preferences (output style, tool permissions, etc). | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L23) |
| class | `PreferencesUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L50) |
| function | `preferences_set` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L57) |
| function | `tools_inventory` | `()` | Return the full tool catalog with name + description + required params. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L100) |
| function | `todos_list` | `(session_id=…)` | List todos for a session — used by JarvisX's TodoPanel UI. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L127) |
| class | `TodoStatusUpdate` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L134) |
| function | `todos_status` | `(payload)` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L141) |
| function | `chat_search` | `(q=…, limit=…, scope=…)` | Full-text search across chat_messages. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L147) |
| function | `staged_edits` | `(session_id=…)` | List staged edits for a session, including full diffs. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L233) |
| function | `staged_edits_commit` | `(session_id=…, stage_ids=…)` | Apply staged edits. Same as the commit_staged_edits tool, but | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L244) |
| function | `staged_edits_discard` | `(session_id=…, stage_ids=…)` | Drop staged edits without applying. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L255) |
| function | `get_tool_result` | `(result_id)` | Fetch the full body of a stored tool_result. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L265) |
| function | `list_plans` | `(session_id=…, include_resolved=…)` | Pending plan proposals for a session (optionally including resolved). | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L300) |
| function | `approve_plan` | `(plan_id)` | Mark a plan as approved. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L313) |
| function | `dismiss_plan` | `(plan_id)` | Mark a plan as dismissed. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L324) |
| class | `_ForkPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L340) |
| function | `fork_session` | `(payload)` | Clone a session up to a specific message_id. | [src](../../../apps/api/jarvis_api/routes/jarvisx_sessions.py#L347) |

## `apps/api/jarvis_api/routes/jarvisx_workspace.py`
_JarvisX workspace + identity/mind route group._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `whoami` | `()` | Return the resolved identity for the current request. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L37) |
| function | `list_workspaces` | `()` | List every directory under workspaces/ with the user (if any) | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L75) |
| function | `workspace_tree` | `(workspace=…)` | List canonical files + dreams + daily notes for the workspace. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L97) |
| function | `workspace_read` | `(path=…, workspace=…)` | Read a markdown / text file from the workspace. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L147) |
| function | `mind_snapshot` | `()` | One-shot summary of Jarvis's inner state for the Mind view. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L181) |
| class | `_PinPayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L316) |
| function | `add_identity_pin` | `(payload)` | Pin a piece of text as permanent awareness. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L323) |
| function | `remove_identity_pin` | `(pin_id)` | Unpin by pin_id. Owner-only. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L344) |
| class | `_ChroniclePayload` | `` | — | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L354) |
| function | `write_chronicle_entry` | `(payload)` | Append a new chronicle entry to the workspace's chronicle/ dir. | [src](../../../apps/api/jarvis_api/routes/jarvisx_workspace.py#L361) |

## `apps/api/jarvis_api/routes/live.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `websocket_stream` | `(ws)` | — | [src](../../../apps/api/jarvis_api/routes/live.py#L20) |

## `apps/api/jarvis_api/routes/mission_control.py`
_Mission Control routes — aggregator._

_(no top-level classes or functions)_

