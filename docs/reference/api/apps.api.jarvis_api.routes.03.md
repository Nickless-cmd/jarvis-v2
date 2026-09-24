# `apps.api.jarvis_api.routes.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| class | `PasteSaveRequest` | `` | — | [src](../../../apps/api/jarvis_api/routes/paste.py#L22) |
| function | `save_paste_endpoint` | `(request)` | Gem en paste og returnér id + kompakt reference-streng. | [src](../../../apps/api/jarvis_api/routes/paste.py#L27) |
| function | `get_paste_endpoint` | `(paste_id)` | Slå fuld paste-tekst op (lazy resolve). 404 på ukendt id. | [src](../../../apps/api/jarvis_api/routes/paste.py#L43) |

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
| class | `PingBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L14) |
| class | `AckBody` | `` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L30) |
| function | `_current_user` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L34) |
| function | `presence_ping` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L40) |
| function | `notifications_pending` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L65) |
| function | `notifications_ack` | `(body)` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L73) |
| function | `notification_preferences_get` | `()` | Notif-routing §6: app-UI læser brugerens kanal-præferencer. | [src](../../../apps/api/jarvis_api/routes/presence.py#L80) |
| function | `notification_preferences_set` | `(body)` | app-UI sætter kanal-præferencer (global + per-type + quiet hours). | [src](../../../apps/api/jarvis_api/routes/presence.py#L90) |
| function | `presence_debug` | `()` | — | [src](../../../apps/api/jarvis_api/routes/presence.py#L106) |
| function | `presence_state` | `()` | Spec E / E0 — TILSTANDS-KONTRAKTEN: Centralens ægte valens + selv-tilstand → jarvis-desk kan | [src](../../../apps/api/jarvis_api/routes/presence.py#L136) |

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
| function | `_saml` | `(rod_til_laesning, gren, numstat, porcelain, diff_tekst, test_koert, med_diff, laes_fil)` | Fælles opsamling for begge træer — så de to veje ikke kan svare i | [src](../../../apps/api/jarvis_api/routes/review.py#L136) |
| function | `_aendringer_paa_serveren` | `(test_koert, med_diff)` | — | [src](../../../apps/api/jarvis_api/routes/review.py#L177) |
| function | `_aendringer_paa_maskinen` | `(rod, test_koert, med_diff)` | Bjørns eget træ, læst over broen med ÉN compound-kommando. | [src](../../../apps/api/jarvis_api/routes/review.py#L201) |
| function | `review_lessons` | `(limit=…)` | Lektier der venter paa en dom — og dem der allerede er i brug. | [src](../../../apps/api/jarvis_api/routes/review.py#L233) |
| function | `review_lesson_set` | `(lesson_id, payload=…)` | Godkend (`active`), afvis (`rejected`) eller send tilbage (`proposed`). | [src](../../../apps/api/jarvis_api/routes/review.py#L257) |

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
_Public-safe /status endpoint._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_format_uptime` | `(seconds)` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L22) |
| function | `_daemon_count` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L36) |
| function | `_visible_model_label` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L44) |
| function | `status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/status.py#L54) |

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
_TOTP-setup for owner-override (spec §6.2). Armerer bagdøren: generér nøgle,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_or_403` | `()` | Returnér owner-User eller rejs 403. Ubundet (no-auth) → owner. | [src](../../../apps/api/jarvis_api/routes/totp.py#L16) |
| function | `totp_status` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L30) |
| function | `_do_setup` | `()` | — | [src](../../../apps/api/jarvis_api/routes/totp.py#L35) |
| function | `totp_setup` | `()` | Generér + gem en ny TOTP-seed for owner. Returnér secret + otpauth-URI | [src](../../../apps/api/jarvis_api/routes/totp.py#L52) |
| function | `totp_revoke` | `()` | Fjern owners TOTP-seed (deaktivér override til ny setup, §9 kompromittering). | [src](../../../apps/api/jarvis_api/routes/totp.py#L59) |

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
| function | `_session_id` | `(payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L32) |
| function | `operator_channel_status` | `(session_id=…)` | Er kanalen åben, og hvor længe endnu? Læse-kun, ingen owner-gate. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L43) |
| function | `operator_channel_open` | `(payload=…)` | Owner-only: åbn kanalen. Herefter kører bash på Bjørns maskine. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L51) |
| function | `operator_channel_close` | `(payload=…)` | — | [src](../../../apps/api/jarvis_api/routes/workbench.py#L60) |
| function | `checkpoints_list` | `(session_id=…)` | Hvad kan fortrydes? Nyeste først. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L70) |
| function | `checkpoints_rollback` | `(payload=…)` | Owner-only: rul den seneste redigeringsrunde tilbage som helhed. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L87) |
| function | `undo_message_edits` | `(message_id, payload=…)` | Owner-only: restore only this message's recorded file writes. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L99) |
| function | `switches_status` | `()` | Tilstand for de to kontakter der styrer runtime-adfærd fra UI'et. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L112) |
| function | `switch_set` | `(navn, payload=…)` | Owner-only: tænd/sluk `bash_sandbox` eller `env_block`. Body: {enabled: bool}. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L126) |
| function | `context_summary` | `(session_id=…)` | Hvad gik der ind i sidste tur? Filer, kilder, størrelse. | [src](../../../apps/api/jarvis_api/routes/workbench.py#L151) |

