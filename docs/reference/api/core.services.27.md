# `core.services.27` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/visible_runs_watchdog.py`
_Agentic-round watchdog — hvornår skal en runde opgives?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `effective_silence_budget_s` | `(max_silence_s, loop_lag_peak_ms)` | Tavsheds-budget justeret for hvor blokeret vores eget loop har været. | [src](../../../core/services/visible_runs_watchdog.py#L34) |
| function | `agentic_watchdog_timeout_reason` | `(*, started_at, last_progress_at, now, max_total_s, max_silence_s, loop_lag_peak_ms=…)` | Returnér watchdog-timeout-grunden, eller None hvis runden må fortsætte. | [src](../../../core/services/visible_runs_watchdog.py#L47) |

## `core/services/visible_self_state_summary.py`
_Visible-chat self-state summary — let Jarvis answer questions about_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_decision_summary` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L29) |
| function | `_goals_summary` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L56) |
| function | `_recent_tick_quality` | `()` | — | [src](../../../core/services/visible_self_state_summary.py#L87) |
| function | `build_self_state_block` | `()` | Return a short prompt section. Empty string when nothing useful to add. | [src](../../../core/services/visible_self_state_summary.py#L112) |

## `core/services/visible_stream_gate.py`
_In-process real-time gate: is a VISIBLE turn actively assembling/streaming right now?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `visible_streaming` | `()` | True hvis mindst én synlig tur i øjeblikket assembler/streamer i denne proces. | [src](../../../core/services/visible_stream_gate.py#L27) |
| function | `enter_visible_stream` | `()` | — | [src](../../../core/services/visible_stream_gate.py#L38) |
| function | `exit_visible_stream` | `()` | — | [src](../../../core/services/visible_stream_gate.py#L44) |
| function | `visible_stream` | `()` | Context manager: markér at en synlig tur er aktiv i dens levetid. Self-safe — | [src](../../../core/services/visible_stream_gate.py#L52) |

## `core/services/visible_terminal_policy.py`
_Single source of truth for visible task terminal decisions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TerminalState` | `` | — | [src](../../../core/services/visible_terminal_policy.py#L14) |
| class | `TerminalEvidence` | `` | — | [src](../../../core/services/visible_terminal_policy.py#L23) |
| class | `TerminalDecision` | `` | — | [src](../../../core/services/visible_terminal_policy.py#L36) |
| function | `has_pending_tool_intent` | `(text)` | — | [src](../../../core/services/visible_terminal_policy.py#L51) |
| function | `is_recoverable_exit_reason` | `(reason)` | — | [src](../../../core/services/visible_terminal_policy.py#L55) |
| function | `classify_terminal` | `(evidence)` | — | [src](../../../core/services/visible_terminal_policy.py#L92) |
| function | `recovery_notice` | `(reason, *, continuing=…)` | — | [src](../../../core/services/visible_terminal_policy.py#L128) |

## `core/services/visible_text_scrub.py`
_Fjern runtime'ens interne markører fra den tekst brugeren ser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_slut_paa_note` | `(tekst, start)` | Indeks EFTER den klamme der lukker noten der begynder på `start`. | [src](../../../core/services/visible_text_scrub.py#L52) |
| function | `_foerste_markoer` | `(tekst, fra=…)` | Indeks på den tidligste interne markør fra `fra`, eller -1. | [src](../../../core/services/visible_text_scrub.py#L70) |
| function | `fjern_interne_markoerer` | `(tekst)` | Teksten uden runtime-noter, med tomme linjer ryddet op efter sig. | [src](../../../core/services/visible_text_scrub.py#L77) |
| function | `_ryd_tomrum` | `(tekst)` | Noten stod i sit eget afsnit. Fjerner man den, står der tre tomme | [src](../../../core/services/visible_text_scrub.py#L95) |
| function | `_uden_markoerord` | `(tekst)` | Teksten med selve markoer-ordene fjernet, men indholdet bevaret. | [src](../../../core/services/visible_text_scrub.py#L103) |
| class | `StroemSkrubber` | `` | Samme fjernelse, men på en strøm hvor markøren kan være delt over flere | [src](../../../core/services/visible_text_scrub.py#L110) |
| method | `StroemSkrubber.__init__` | `(self)` | — | [src](../../../core/services/visible_text_scrub.py#L119) |
| method | `StroemSkrubber.foed` | `(self, stykke)` | Den del af `stykke` der trygt kan sendes videre nu. | [src](../../../core/services/visible_text_scrub.py#L122) |
| method | `StroemSkrubber.skyl` | `(self)` | Resten, når strømmen er slut. Uafsluttede noter ryger. | [src](../../../core/services/visible_text_scrub.py#L137) |
| function | `fjern_interne_markoerer_stroem` | `(buffer)` | (klar-til-udsendelse, hale-der-skal-holdes-tilbage). | [src](../../../core/services/visible_text_scrub.py#L144) |
| function | `_klap_tomrum_sammen` | `(tekst)` | Tre eller flere linjeskift bliver til ét afsnitsbrud. | [src](../../../core/services/visible_text_scrub.py#L191) |
| function | `_muligt_praefiks` | `(buffer)` | Den slut-stump der kunne være starten på en markør — ellers «». | [src](../../../core/services/visible_text_scrub.py#L202) |

## `core/services/visible_thinking_trace.py`
_Hvor længe tænkte han? — målt ét sted, læst ét sted._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_evict_if_needed` | `()` | Hold kortet lille. Ældste post ryger — kaldes altid under _lock. | [src](../../../core/services/visible_thinking_trace.py#L31) |
| function | `mark_start` | `(run_id)` | Første tænke-blok i turen. Senere kald ignoreres. | [src](../../../core/services/visible_thinking_trace.py#L38) |
| function | `mark_end` | `(run_id)` | Seneste tænke-blok lukkede. Sidste lukning vinder — se mark_start. | [src](../../../core/services/visible_thinking_trace.py#L54) |
| function | `take_seconds` | `(run_id)` | Varigheden i sekunder, og RYD posten. None hvis der ikke blev tænkt. | [src](../../../core/services/visible_thinking_trace.py#L66) |
| function | `peek_seconds` | `(run_id)` | Som take_seconds, men uden at rydde. Til observation/test. | [src](../../../core/services/visible_thinking_trace.py#L90) |

## `core/services/visible_tool_exec.py`
_Shared tool-exec pump for the visible run (Boy-Scout extraction, 2026-07-19)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bruger_til_stede` | `(run)` | Er der et menneske i den anden ende af den her tur? | [src](../../../core/services/visible_tool_exec.py#L36) |
| function | `run_tool_batch` | `(tool_calls, *, run, loop, tool_scope, step_counter, heartbeat_interval_s, heartbeat_phase, out, heartbeat_extra=…, exec_start=…, er_afbrudt=…)` | Announce → execute → heartbeat pump for one tool batch. | [src](../../../core/services/visible_tool_exec.py#L66) |

## `core/services/visible_turn_accumulator.py`
_Turens content-blokke, samlet i den rækkefølge de faktisk opstod._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TurnAccumulator` | `` | Samler tekst-segmenter, værktøjskald og deres rækkefølge for én tur. | [src](../../../core/services/visible_turn_accumulator.py#L30) |
| method | `TurnAccumulator.add_text` | `(self, chunk)` | Læg tekst i det ÅBNE segment, eller åbn et nyt. | [src](../../../core/services/visible_turn_accumulator.py#L62) |
| method | `TurnAccumulator.close_segment` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L76) |
| method | `TurnAccumulator.note_text` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L80) |
| method | `TurnAccumulator.note_tool` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L84) |
| method | `TurnAccumulator._luk_tanketid` | `(self)` | En tanke varer til det NÆSTE begynder — ikke til dens sidste token. | [src](../../../core/services/visible_turn_accumulator.py#L88) |
| method | `TurnAccumulator.add_tools` | `(self, tool_calls, results)` | Optag et batch af kald og deres resultater. Kaster ALDRIG. | [src](../../../core/services/visible_turn_accumulator.py#L102) |
| method | `TurnAccumulator.add_thinking` | `(self, chunk)` | Læg reasoning i det ÅBNE tanke-segment, eller åbn et nyt. | [src](../../../core/services/visible_turn_accumulator.py#L141) |
| method | `TurnAccumulator.close_thinking` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L160) |
| method | `TurnAccumulator._nu` | `(self)` | — | [src](../../../core/services/visible_turn_accumulator.py#L163) |
| method | `TurnAccumulator.thinking_seconds` | `(self)` | Sekunder pr. tanke-segment; None hvor der ikke blev maalt noget. | [src](../../../core/services/visible_turn_accumulator.py#L169) |
| method | `TurnAccumulator.add_round_label` | `(self, etik)` | Gem en runde-etiket som den blok Claude Desktop selv gemmer. | [src](../../../core/services/visible_turn_accumulator.py#L182) |
| method | `TurnAccumulator.build_blocks` | `(self, text)` | Den kanoniske blok-liste for turen. | [src](../../../core/services/visible_turn_accumulator.py#L212) |
| function | `coerce_tool_input` | `(raw)` | Normalisér tool-input til et DICT. | [src](../../../core/services/visible_turn_accumulator.py#L232) |

## `core/services/visible_turn_blocks.py`
_Den kanoniske content-blok-array for en assistent-tur (spec §4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tool_label` | `(tool_name, arguments=…)` | Narrationen for ét værktøjskald — samme tekst som live-visningen brugte. | [src](../../../core/services/visible_turn_blocks.py#L31) |
| function | `_tool_hint` | `(tool_name, arguments=…)` | Emnet alene — «git status», «raekkeModel.ts», uden label foran. | [src](../../../core/services/visible_turn_blocks.py#L42) |
| function | `_build_progress_blocks` | `(tool_calls, tool_results)` | Byg det FLADE progress-spor for en tur (spec §5). | [src](../../../core/services/visible_turn_blocks.py#L54) |
| function | `_tanke_blok` | `(par)` | Én tanke-blok. Halen er nok: klienten viser den foldet ud, og en hel | [src](../../../core/services/visible_turn_blocks.py#L108) |
| function | `_build_turn_blocks` | `(*, text, tool_calls, tool_results, interleave=…, text_segments=…, thinking_segments=…, thinking_seconds=…)` | Byg den kanoniske content-blok-array for en assistant-tur (spec §4). | [src](../../../core/services/visible_turn_blocks.py#L124) |

## `core/services/vision_backend.py`
_Hvilke øjne bruger han? — valg af vision-model (2026-09-05)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `model_can_see` | `(model)` | Kan DENNE model selv se et billede? | [src](../../../core/services/vision_backend.py#L86) |
| function | `active_visible_target` | `()` | (provider, model) for den synlige tur der koerer lige nu — ("","") hvis ingen. | [src](../../../core/services/vision_backend.py#L99) |
| function | `resolve_vision_target` | `()` | (provider, model, kilde) for syns-vaerktoejerne lige nu. | [src](../../../core/services/vision_backend.py#L111) |
| function | `resolve_vision_provider` | `(model)` | `"ollama"` eller `"deepseek"`. Eksplicit konfig vinder over gættet. | [src](../../../core/services/vision_backend.py#L125) |
| function | `describe_via_deepseek` | `(image_b64, *, model, prompt, run_id=…)` | Send billedet til DeepSeeks vision-model og returnér svaret. | [src](../../../core/services/vision_backend.py#L141) |
| function | `_record_cost` | `(usage, *, model, run_id)` | — | [src](../../../core/services/vision_backend.py#L191) |
| function | `describe` | `(image_bytes=…, *, image_b64=…, model, prompt, run_id=…, provider=…)` | Beskriv/besvar et billede med den valgte backend. | [src](../../../core/services/vision_backend.py#L214) |
| function | `build_vision_backend_surface` | `()` | — | [src](../../../core/services/vision_backend.py#L237) |

## `core/services/visual_memory.py`
_Visual memory — webcam snapshots beskrevet af vision-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_compare_suffix` | `(previous_desc, time_ago_label)` | Mandatory instruction: always describe what has changed. | [src](../../../core/services/visual_memory.py#L95) |
| function | `_ollama_base_url` | `()` | Pull Ollama base URL from provider_router.json (falls back to localhost). | [src](../../../core/services/visual_memory.py#L108) |
| function | `tick_visual_memory_daemon` | `()` | Capture webcam snapshot and describe it via vision model. | [src](../../../core/services/visual_memory.py#L128) |
| function | `get_visual_memories` | `(*, limit=…)` | Return most recent visual memory records (newest first). | [src](../../../core/services/visual_memory.py#L200) |
| function | `get_latest_visual_memory_for_prompt` | `()` | Return the most recent visual memory as a quiet prompt hint. | [src](../../../core/services/visual_memory.py#L207) |
| function | `_coarse_age_label` | `(minutes_ago)` | Bucket minutes-since into coarse labels so prompt cache stays stable. | [src](../../../core/services/visual_memory.py#L250) |
| function | `look_around_now` | `(*, where=…, prompt_override=…)` | On-demand capture — Jarvis chooses to look. Bypasses cadence-limit. | [src](../../../core/services/visual_memory.py#L275) |
| function | `build_visual_memory_surface` | `()` | MC observability surface. | [src](../../../core/services/visual_memory.py#L362) |
| function | `_fold` | `(text)` | Sammenlign navne uden at snuble over æøå, store bogstaver og bindestreger. | [src](../../../core/services/visual_memory.py#L427) |
| function | `known_cameras` | `()` | Alle kendte kameraer — config vinder over det indbyggede kort. | [src](../../../core/services/visual_memory.py#L440) |
| function | `default_camera` | `()` | Nøglen på det kamera der bruges når ingen har sagt hvor der skal kigges. | [src](../../../core/services/visual_memory.py#L454) |
| function | `resolve_camera` | `(where=…)` | Slå et menneskeligt stednavn op. Tom streng giver standardkameraet. | [src](../../../core/services/visual_memory.py#L475) |
| function | `capture_from_camera` | `(where=…)` | Hent et billede. Returnerer (base64-jpeg, kamera-nøgle, læsbart navn). | [src](../../../core/services/visual_memory.py#L519) |
| function | `describe_cameras` | `()` | Én linje pr. kamera — til værktøjsbeskrivelser og prompten. | [src](../../../core/services/visual_memory.py#L534) |
| function | `_capture_image` | `(where=…)` | Hent et billede fra et navngivet kamera. Returnerer (base64-jpeg, kameranavn). | [src](../../../core/services/visual_memory.py#L548) |
| function | `_capture_source` | `()` | Return 'ha_camera' or 'webcam' based on runtime config. | [src](../../../core/services/visual_memory.py#L569) |
| function | `_ha_camera_entity` | `()` | Return HA camera entity_id from runtime config. | [src](../../../core/services/visual_memory.py#L575) |
| function | `_capture_ha_camera` | `(entity_id=…)` | Fetch snapshot from Home Assistant camera and return as base64 JPEG string. | [src](../../../core/services/visual_memory.py#L581) |
| function | `_capture_webcam` | `(device_index=…)` | Capture one frame from webcam and return as base64 JPEG string. | [src](../../../core/services/visual_memory.py#L617) |
| function | `_describe_image` | `(image_b64, *, model, provider, prompt=…, previous=…)` | Send image to vision model and return description. | [src](../../../core/services/visual_memory.py#L642) |
| function | `_previous_time_label` | `(captured_at)` | — | [src](../../../core/services/visual_memory.py#L664) |
| function | `_build_prompt` | `(previous=…, prompt_index=…)` | Assemble the full vision prompt: prefix + rotating focus + optional compare. | [src](../../../core/services/visual_memory.py#L679) |
| function | `_describe_via_ollama` | `(image_b64, *, model, prompt=…, previous=…)` | Call Ollama generate API with image payload. | [src](../../../core/services/visual_memory.py#L701) |
| function | `_load_records` | `()` | — | [src](../../../core/services/visual_memory.py#L756) |
| function | `_prune_old_records` | `()` | — | [src](../../../core/services/visual_memory.py#L763) |
| function | `_vision_model` | `()` | Return (model_name, provider) — den valgte model vinder over config. | [src](../../../core/services/visual_memory.py#L771) |
| function | `_enabled` | `()` | — | [src](../../../core/services/visual_memory.py#L804) |
| function | `_archive_sensory` | `(description, *, metadata)` | Mirror every visual memory into Sansernes Arkiv. Silent on failure. | [src](../../../core/services/visual_memory.py#L809) |

## `core/services/voice_anchor.py`
_Voice anchor — combined static seed + auto-refreshed external exemplars._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `read_voice_anchor` | `()` | Return concatenated VOICE.md + VOICE_RECENT.md, or empty string. | [src](../../../core/services/voice_anchor.py#L20) |

## `core/services/voice_curator.py`
_Voice curator — refresh VOICE_RECENT.md from EXTERNAL output only._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `refresh_voice_recent` | `()` | Rebuild workspace/VOICE_RECENT.md from external output. | [src](../../../core/services/voice_curator.py#L34) |
| function | `_pick_diverse` | `(*, chat, chronicle, journals)` | Pick up to _TARGET_TOTAL exemplars, max _MAX_PER_SOURCE per source. | [src](../../../core/services/voice_curator.py#L65) |
| function | `_format_recent` | `(exemplars)` | Render exemplars as a markdown blob for VOICE_RECENT.md. | [src](../../../core/services/voice_curator.py#L96) |
| function | `_fetch_chat_exemplars` | `(*, limit)` | Pull recent assistant replies from chat_messages (all sessions). | [src](../../../core/services/voice_curator.py#L112) |
| function | `_fetch_chronicle_exemplars` | `(*, limit)` | Pull recent chronicle narratives as voice exemplars. | [src](../../../core/services/voice_curator.py#L149) |
| function | `_fetch_journal_exemplars` | `(*, limit)` | Pull recent journal entry bodies as voice exemplars. | [src](../../../core/services/voice_curator.py#L170) |
| function | `_strip_frontmatter` | `(text)` | Drop a leading `---\n...\n---\n` YAML block if present. | [src](../../../core/services/voice_curator.py#L203) |

## `core/services/voice_daemon.py`
_Voice daemon — runs the Hey Jarvis voice loop as a background thread._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_voice_enabled` | `()` | Check if voice is enabled via config or env. | [src](../../../core/services/voice_daemon.py#L24) |
| function | `_run_loop` | `()` | Supervisor thread: start worker, restart on crash until stopped. | [src](../../../core/services/voice_daemon.py#L30) |
| function | `start_voice_daemon` | `()` | — | [src](../../../core/services/voice_daemon.py#L60) |
| function | `stop_voice_daemon` | `()` | — | [src](../../../core/services/voice_daemon.py#L73) |
| function | `build_voice_daemon_surface` | `()` | Mission Control surface — read-only meta-projection. | [src](../../../core/services/voice_daemon.py#L84) |

## `core/services/wakeup_dispatcher.py`
_Wakeup dispatcher — autonomous fire of self-wakeups._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_bruger_skrev_for_nylig` | `(session_id)` | Skrev brugeren inden for karantænen? Self-safe → False ved enhver fejl. | [src](../../../core/services/wakeup_dispatcher.py#L52) |
| function | `_active_turn_blocks` | `(session_id)` | Returnér en skip-årsag hvis en FERSK visible-tur kører i sessionen. | [src](../../../core/services/wakeup_dispatcher.py#L80) |
| function | `pick_wakeup_run_target` | `(*, channel, record_session, app_resolver, owner_resolver, is_external)` | Beslut hvilken session et wakeup-run skal lande i — med Discord-guard. | [src](../../../core/services/wakeup_dispatcher.py#L153) |
| function | `dispatch_due_wakeups` | `()` | Find newly-fired wakeups, push them out via webchat + heartbeat tick. | [src](../../../core/services/wakeup_dispatcher.py#L184) |
| function | `_exec_dispatch_due_wakeups` | `(args)` | — | [src](../../../core/services/wakeup_dispatcher.py#L360) |

## `core/services/weekly_manifest.py`
_Weekly manifest — Jarvis' running self-reflection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_weekly_manifest_path` | `()` | — | [src](../../../core/services/weekly_manifest.py#L32) |
| function | `_gather_context` | `()` | Pull recent self-state to ground the reflection. | [src](../../../core/services/weekly_manifest.py#L36) |
| function | `_build_prompt` | `(ctx)` | — | [src](../../../core/services/weekly_manifest.py#L58) |
| function | `build_weekly_manifest` | `()` | Generate weekly manifest, write to WEEKLY_MANIFEST.md, return summary. | [src](../../../core/services/weekly_manifest.py#L73) |

## `core/services/witness_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_witness_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L29) |
| function | `refresh_runtime_witness_signal_statuses` | `()` | — | [src](../../../core/services/witness_signal_tracking.py#L51) |
| function | `build_runtime_witness_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/witness_signal_tracking.py#L120) |
| function | `_extract_witness_candidates` | `(*, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L156) |
| function | `_persist_witness_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/witness_signal_tracking.py#L254) |
| function | `_build_candidate` | `(*, domain_key, signal_type, title, summary, rationale, status_reason, source_items, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L323) |
| function | `_focus_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L456) |
| function | `_goal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L468) |
| function | `_reflection_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L472) |
| function | `_temporal_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L477) |
| function | `_domain_title` | `(domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L482) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/witness_signal_tracking.py#L487) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/witness_signal_tracking.py#L496) |
| function | `_latest_self_narrative_continuity` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L569) |
| function | `_latest_meaning_significance` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L577) |
| function | `_latest_temperament_tendency` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L585) |
| function | `_latest_relation_continuity` | `(*, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L593) |
| function | `_latest_signal_for_domain` | `(items, *, run_id, domain_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L601) |
| function | `_focus_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L618) |
| function | `_witness_domain_key` | `(canonical_key)` | — | [src](../../../core/services/witness_signal_tracking.py#L623) |
| function | `_derive_becoming_direction` | `(*, signal_type, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L628) |
| function | `_derive_becoming_weight` | `(*, self_narrative, meaning, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L657) |
| function | `_derive_maturation_hint` | `(*, signal_type, self_narrative, temperament, relation_continuity)` | — | [src](../../../core/services/witness_signal_tracking.py#L677) |
| function | `_derive_maturation_state` | `(*, signal_type, status, becoming_direction, becoming_weight, maturation_hint)` | — | [src](../../../core/services/witness_signal_tracking.py#L698) |
| function | `_derive_maturation_marker` | `(*, maturation_state, maturation_hint)` | — | [src](../../../core/services/witness_signal_tracking.py#L719) |
| function | `_derive_persistence_state` | `(*, status, becoming_direction, maturation_state, support_count, session_count)` | — | [src](../../../core/services/witness_signal_tracking.py#L739) |
| function | `_derive_persistence_marker` | `(*, persistence_state, maturation_state)` | — | [src](../../../core/services/witness_signal_tracking.py#L760) |
| function | `_becoming_summary` | `(*, domain_title, becoming_direction, becoming_weight, signal_type)` | — | [src](../../../core/services/witness_signal_tracking.py#L780) |
| function | `_maturation_summary` | `(*, domain_title, becoming_direction, maturation_state, maturation_marker)` | — | [src](../../../core/services/witness_signal_tracking.py#L796) |
| function | `_persistence_summary` | `(*, domain_title, persistence_state, persistence_marker, becoming_direction)` | — | [src](../../../core/services/witness_signal_tracking.py#L811) |
| function | `_summary_marker` | `(text, key)` | — | [src](../../../core/services/witness_signal_tracking.py#L826) |
| function | `_last_summary_fragment` | `(text)` | — | [src](../../../core/services/witness_signal_tracking.py#L835) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/witness_signal_tracking.py#L841) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/witness_signal_tracking.py#L847) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/witness_signal_tracking.py#L860) |
| function | `run_witness_daemon` | `(*, trigger=…, last_visible_at=…)` | Bounded inner witness daemon — produces witness signals without visible turn. | [src](../../../core/services/witness_signal_tracking.py#L884) |
| function | `get_witness_daemon_state` | `()` | Return current witness daemon state for MC observability. | [src](../../../core/services/witness_signal_tracking.py#L1000) |

## `core/services/workspace_crypto.py`
_Krypteret workspace-fil-I/O (spec §16, Lag 3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `encrypt_on_write` | `()` | True hvis non-owner skrivninger faktisk skal krypteres (sti-nøglet path). | [src](../../../core/services/workspace_crypto.py#L33) |
| function | `should_encrypt` | `(user_id)` | True hvis denne brugers data skal krypteres (alle undtagen owner, §16.2). | [src](../../../core/services/workspace_crypto.py#L46) |
| function | `write_workspace_file` | `(path, content, user_id)` | Skriv en workspace-fil. Non-owner → krypteret (.enc); owner → plaintext. | [src](../../../core/services/workspace_crypto.py#L65) |
| function | `read_workspace_file` | `(path, user_id)` | Læs en workspace-fil. Prøver krypteret (.enc) først for non-owner, ellers | [src](../../../core/services/workspace_crypto.py#L91) |
| function | `member_user_id_for_path` | `(path)` | Udled discord_id for filens NON-owner ejer ud fra `workspaces/<navn>/…`. | [src](../../../core/services/workspace_crypto.py#L113) |
| function | `read_text_for_path` | `(path, *, encoding=…)` | Læs workspace-fil-tekst sti-nøglet. Returnerer None hvis hverken plaintext | [src](../../../core/services/workspace_crypto.py#L153) |
| function | `write_text_for_path` | `(path, content)` | Skriv workspace-fil-tekst sti-nøglet. Mens ENCRYPT_ON_WRITE er FRA skrives | [src](../../../core/services/workspace_crypto.py#L171) |

## `core/services/workspace_trust.py`
_Trusted-folder gate for code/cowork workspaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/workspace_trust.py#L30) |
| function | `is_trusted` | `(user_id, kind, root)` | True hvis (user_id, kind, root) er markeret betroet. | [src](../../../core/services/workspace_trust.py#L44) |
| function | `list_trusted` | `(user_id, kind=…)` | De mapper brugeren har betroet — nyeste foerst. | [src](../../../core/services/workspace_trust.py#L57) |
| function | `set_trusted` | `(user_id, kind, root, trusted)` | Markér/afmarkér et workspace som betroet. Returnerer den nye trust-tilstand. | [src](../../../core/services/workspace_trust.py#L87) |
| function | `set_trust_context` | `(*, kind, root, trusted)` | — | [src](../../../core/services/workspace_trust.py#L110) |
| function | `clear_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L114) |
| function | `current_trust_context` | `()` | — | [src](../../../core/services/workspace_trust.py#L118) |
| function | `guard_code_write` | `(tool_name)` | Returnér en fejl-besked hvis ``tool_name`` er en skrive-/exec-handling i et | [src](../../../core/services/workspace_trust.py#L122) |

## `core/services/world_facts.py`
_Evidence-bounded world facts and their visible prompt representation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_world_fact` | `(*, canonical_key, statement, status, confidence, source_kind, source_ref=…, observed_at=…, valid_from=…, valid_until=…, contradicts_fact_id=…, supersedes_fact_id=…, evidence_count=…, distinct_source_count=…)` | — | [src](../../../core/services/world_facts.py#L37) |
| function | `list_world_facts` | `(*, status=…, limit=…)` | — | [src](../../../core/services/world_facts.py#L98) |
| function | `build_world_fact_prompt_section` | `(*, limit=…, facts=…)` | — | [src](../../../core/services/world_facts.py#L107) |

## `core/services/world_model_auto_extraction.py`
_World Model Phase 2: auto-extract structured predictions from Jarvis' replies._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_today_iso` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L35) |
| function | `_load_rate_state` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L39) |
| function | `_increment_rate` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L48) |
| function | `_under_rate_limit` | `()` | — | [src](../../../core/services/world_model_auto_extraction.py#L55) |
| function | `_extract_json` | `(text)` | — | [src](../../../core/services/world_model_auto_extraction.py#L59) |
| function | `_build_prompt` | `(context_excerpt, matched_phrase)` | — | [src](../../../core/services/world_model_auto_extraction.py#L71) |
| function | `auto_extract_and_record` | `(*, matched_phrase, context_excerpt, session_id=…)` | Try to extract a structured prediction from a matched phrase. | [src](../../../core/services/world_model_auto_extraction.py#L89) |
| function | `_emit_world_model_auto_extraction_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/world_model_auto_extraction.py#L172) |

## `core/services/world_model_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_observe_world_model` | `(nerve, *, value=…, meta=…)` | EGRESS-FRI binding til Centralen (§24.4): world-model-livscyklus (prediction lavet, | [src](../../../core/services/world_model_signal_tracking.py#L88) |
| function | `record_runtime_world_model_prediction` | `(*, subject, expectation, horizon=…, confidence=…, evidence=…, source=…, now=…)` | Record an explicit, falsifiable world-model expectation. | [src](../../../core/services/world_model_signal_tracking.py#L105) |
| function | `resolve_runtime_world_model_prediction` | `(prediction_id, *, observed, outcome, now=…, resolved_via=…)` | Resolve a prediction with a later observation. | [src](../../../core/services/world_model_signal_tracking.py#L169) |
| function | `build_runtime_world_model_prediction_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L219) |
| function | `track_runtime_world_model_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L255) |
| function | `refresh_runtime_world_model_signal_statuses` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L295) |
| function | `build_runtime_world_model_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/world_model_signal_tracking.py#L324) |
| function | `_extract_pattern_matches` | `(text, patterns)` | Return list of {matched_phrase, context_excerpt} for each regex hit. | [src](../../../core/services/world_model_signal_tracking.py#L350) |
| function | `extract_prediction_language` | `(text)` | Find prediction-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L379) |
| function | `extract_resolution_language` | `(text)` | Find resolution-shape phrases in Jarvis' own response text. | [src](../../../core/services/world_model_signal_tracking.py#L384) |
| function | `_loop_enabled` | `()` | World-model-loop kill-switch check. | [src](../../../core/services/world_model_signal_tracking.py#L389) |
| function | `_load_nudges` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L397) |
| function | `_save_nudges` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L407) |
| function | `record_prediction_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt)` | Append a prediction-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L411) |
| function | `record_resolution_nudge` | `(*, session_id, run_id, matched_phrase, context_excerpt, candidate_prediction_id=…)` | Append a resolution-language nudge to state (FIFO, max 20, 48h TTL). | [src](../../../core/services/world_model_signal_tracking.py#L438) |
| function | `_next_weekday` | `(d, target_weekday)` | Next occurrence of given weekday (0=Mon..6=Sun) at end-of-day. | [src](../../../core/services/world_model_signal_tracking.py#L471) |
| function | `_parse_horizon` | `(horizon, created)` | Return the cutoff datetime when horizon would have elapsed. | [src](../../../core/services/world_model_signal_tracking.py#L479) |
| function | `_ttl_sweep_open_predictions` | `(*, now=…)` | Scan open predictions; auto-resolve as 'uncertain' if past horizon+grace. | [src](../../../core/services/world_model_signal_tracking.py#L503) |
| function | `format_world_model_nudges_for_awareness` | `(*, session_id=…)` | Surface up to 1 prediction-nudge + 1 resolution-nudge for the awareness block. | [src](../../../core/services/world_model_signal_tracking.py#L541) |
| function | `_load_milestones` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L589) |
| function | `_save_milestones` | `(data)` | — | [src](../../../core/services/world_model_signal_tracking.py#L596) |
| function | `_resolved_predictions_chrono` | `()` | Return resolved predictions in chronological order (oldest first). | [src](../../../core/services/world_model_signal_tracking.py#L600) |
| function | `_calibration_of` | `(predictions)` | % supported among supported+contradicted; uncertain is excluded. | [src](../../../core/services/world_model_signal_tracking.py#L612) |
| function | `_has_milestone` | `(kind, value=…)` | Check if a milestone of given kind (+ optional value) has been recorded. | [src](../../../core/services/world_model_signal_tracking.py#L621) |
| function | `_append_milestone` | `(kind, value, message, now)` | — | [src](../../../core/services/world_model_signal_tracking.py#L632) |
| function | `_compute_calibration_milestone` | `(*, now=…)` | Compute the latest calibration milestone if any rule fires. | [src](../../../core/services/world_model_signal_tracking.py#L649) |
| function | `format_world_model_milestone_for_awareness` | `()` | Surface one unrendered milestone per call. Returns '' when nothing. | [src](../../../core/services/world_model_signal_tracking.py#L721) |
| function | `_load_predictions` | `()` | — | [src](../../../core/services/world_model_signal_tracking.py#L737) |
| function | `_save_predictions` | `(predictions)` | — | [src](../../../core/services/world_model_signal_tracking.py#L744) |
| function | `_extract_world_model_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L748) |
| function | `_project_context_signal` | `(message, *, session_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L775) |
| function | `_workspace_scope_signal` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L810) |
| function | `_persist_world_model_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/world_model_signal_tracking.py#L832) |
| function | `_apply_correction_signals` | `(*, user_message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L905) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/world_model_signal_tracking.py#L949) |
| function | `_matches_project_context` | `(message)` | — | [src](../../../core/services/world_model_signal_tracking.py#L970) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L975) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/world_model_signal_tracking.py#L982) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/world_model_signal_tracking.py#L986) |

