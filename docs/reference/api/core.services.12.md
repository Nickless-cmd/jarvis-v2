# `core.services.12` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/irony_daemon.py`
_Irony daemon — situational self-distance and absurd self-observations._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_irony_daemon` | `()` | — | [src](../../../core/services/irony_daemon.py#L20) |
| function | `get_latest_irony_observation` | `()` | — | [src](../../../core/services/irony_daemon.py#L35) |
| function | `build_irony_surface` | `()` | — | [src](../../../core/services/irony_daemon.py#L39) |
| function | `_maybe_reset_daily_count` | `()` | — | [src](../../../core/services/irony_daemon.py#L48) |
| function | `_collect_snapshot` | `()` | — | [src](../../../core/services/irony_daemon.py#L56) |
| function | `_detect_irony_conditions` | `(snapshot)` | — | [src](../../../core/services/irony_daemon.py#L81) |
| function | `_generate_observation` | `(snapshot, condition)` | — | [src](../../../core/services/irony_daemon.py#L94) |
| function | `_store_observation` | `(observation, condition)` | — | [src](../../../core/services/irony_daemon.py#L121) |

## `core/services/jarvis_brain.py`
_Jarvis Brain — kurateret vidensjournal. Kerne-CRUD-laget._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `BrainEntry` | `` | — | [src](../../../core/services/jarvis_brain.py#L64) |
| method | `BrainEntry.__post_init__` | `(self)` | — | [src](../../../core/services/jarvis_brain.py#L91) |
| function | `_atomic_write` | `(path, content)` | Atomic file write via tmp + rename. Creates parent dirs as needed. | [src](../../../core/services/jarvis_brain.py#L107) |
| function | `parse_frontmatter` | `(path)` | Parse YAML frontmatter + body from a markdown file. | [src](../../../core/services/jarvis_brain.py#L115) |
| function | `_iso` | `(dt)` | — | [src](../../../core/services/jarvis_brain.py#L135) |
| function | `_parse_iso` | `(s)` | Parse ISO timestamp from string or pass-through if already datetime. | [src](../../../core/services/jarvis_brain.py#L143) |
| function | `render_entry_markdown` | `(entry)` | Render a BrainEntry as markdown with YAML frontmatter. | [src](../../../core/services/jarvis_brain.py#L156) |
| function | `entry_from_frontmatter` | `(fm, body)` | Build a BrainEntry from parsed frontmatter dict + body string. | [src](../../../core/services/jarvis_brain.py#L183) |
| function | `_workspace_root` | `()` | Base dir for brain-relative paths. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L276) |
| function | `_state_root` | `()` | — | [src](../../../core/services/jarvis_brain.py#L293) |
| function | `brain_dir` | `()` | Return the brain storage dir under JARVIS_HOME/shared/jarvis_brain. | [src](../../../core/services/jarvis_brain.py#L300) |
| function | `index_db_path` | `()` | — | [src](../../../core/services/jarvis_brain.py#L310) |
| function | `connect_index` | `()` | — | [src](../../../core/services/jarvis_brain.py#L314) |
| function | `_ensure_index_schema_migrations` | `(conn)` | Bring pre-existing brain_index tables up to the current schema. | [src](../../../core/services/jarvis_brain.py#L324) |
| function | `_slugify` | `(s, max_len=…)` | — | [src](../../../core/services/jarvis_brain.py#L372) |
| function | `_file_hash` | `(text)` | — | [src](../../../core/services/jarvis_brain.py#L379) |
| function | `write_entry` | `(*, kind, title, content, visibility, domain, trigger=…, related=…, tags=…, source_url=…, source_chronicle=…, importance=…, now=…, skip_temporal=…)` | Skriver en ny brain-entry til disk og indexerer den (uden embedding endnu). | [src](../../../core/services/jarvis_brain.py#L383) |
| function | `read_entry` | `(entry_id)` | Read a BrainEntry by id (loads from disk via index lookup). | [src](../../../core/services/jarvis_brain.py#L478) |
| function | `_index_path_for` | `(entry_id)` | Returns the relative path stored in brain_index for entry_id. | [src](../../../core/services/jarvis_brain.py#L494) |
| function | `compute_effective_salience` | `(entry, now)` | Compute time-decayed salience with bump amplification + importance gate. | [src](../../../core/services/jarvis_brain.py#L522) |
| function | `_embed_text` | `(text)` | Wrapper around eksisterende embedder. Override in tests via monkeypatch. | [src](../../../core/services/jarvis_brain.py#L550) |
| function | `_embedding_to_blob` | `(v)` | — | [src](../../../core/services/jarvis_brain.py#L565) |
| function | `_embedding_from_blob` | `(blob, dim)` | — | [src](../../../core/services/jarvis_brain.py#L569) |
| function | `embed_pending_entries` | `()` | Embed alle entries i index'et der mangler embedding. Returnerer antal. | [src](../../../core/services/jarvis_brain.py#L573) |
| function | `search_brain` | `(*, query_text, kinds=…, visibility_ceiling=…, limit=…, domain=…, tags=…, include_archived=…, now=…, use_temporal_boost=…, min_score=…, min_cosine=…)` | Hybrid embedding search: 0.7*cosine + 0.3*effective_salience + temporal boost. | [src](../../../core/services/jarvis_brain.py#L604) |
| function | `_compute_search_temporal_boost` | `(candidate_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost for search candidates. | [src](../../../core/services/jarvis_brain.py#L709) |
| function | `bump_salience` | `(entry_id, now=…)` | Increments salience_bumps + recall_count + opdaterer last_used_at i index OG fil. | [src](../../../core/services/jarvis_brain.py#L750) |
| function | `archive_entry` | `(entry_id, *, reason=…, now=…)` | Mark entry as archived and move file to _archive/<kind>/. | [src](../../../core/services/jarvis_brain.py#L794) |
| function | `supersede` | `(*, old_ids, new_id, now=…)` | Mark old entries as superseded by new_id (keeps files in place). | [src](../../../core/services/jarvis_brain.py#L825) |
| function | `rebuild_index_from_files` | `()` | Scan brain_dir() for .md files; new/changed hash → update index. | [src](../../../core/services/jarvis_brain.py#L851) |
| function | `_extract_text_for_entry` | `(entry_id)` | Read entry content from disk for entity/semantic analysis. | [src](../../../core/services/jarvis_brain.py#L947) |
| function | `_temporal_similarity_score` | `(hours_apart)` | Score 0.0–1.0 based on temporal proximity. 1.0 at ≤1h, decays to 0 at 24h. | [src](../../../core/services/jarvis_brain.py#L953) |
| function | `_cosine_similarity` | `(a_vec, b_vec)` | — | [src](../../../core/services/jarvis_brain.py#L963) |
| function | `_compute_temporal_confidence` | `(*, temporal, semantic, entity, is_chain, chain_score=…)` | Combine four signals into a single confidence score (0.0–1.0). | [src](../../../core/services/jarvis_brain.py#L970) |
| function | `_compute_chain_score` | `(*, new_entry, cand_entry, hours_apart, cand_related)` | Compute chain signal score (0.0–1.0) between two entries. | [src](../../../core/services/jarvis_brain.py#L989) |
| function | `infer_temporal_edges` | `(new_entry_id, now=…)` | Run four-signal inference between a new entry and all existing active entries. | [src](../../../core/services/jarvis_brain.py#L1039) |
| function | `_store_temporal_edge` | `(from_id, to_id, confidence, reasoning, now)` | Insert or update a temporal edge with combined confidence. | [src](../../../core/services/jarvis_brain.py#L1169) |
| function | `get_temporal_neighbors` | `(entry_id, min_confidence=…, limit=…)` | Get tidligere inferred temporal neighbors for an entry. | [src](../../../core/services/jarvis_brain.py#L1195) |
| function | `temporal_boost_recall` | `(entry_ids, *, boost_factor=…, min_confidence=…)` | Compute temporal boost scores for a set of entry IDs. | [src](../../../core/services/jarvis_brain.py#L1225) |
| function | `prune_stale_edges` | `(*, max_age_days=…, min_confidence=…)` | Remove stale temporal edges with low confidence. | [src](../../../core/services/jarvis_brain.py#L1281) |
| function | `full_rebuild` | `(*, batch_size=…)` | Genberegn alle temporale edges fra bunden. | [src](../../../core/services/jarvis_brain.py#L1308) |
| function | `_emit_jarvis_brain_event` | `(kind, payload=…)` | Emit a scoped event — defensive, never blocks caller. | [src](../../../core/services/jarvis_brain.py#L1370) |

## `core/services/jarvis_brain_daemon.py`
_Jarvis Brain background daemon — tre uafhængige loops._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reindex_once` | `()` | Et enkelt reindex-pass. Returnerer antal file changes opdaget. | [src](../../../core/services/jarvis_brain_daemon.py#L26) |
| function | `reindex_loop` | `(stop_event)` | Long-running loop. Stops cleanly when stop_event is set. | [src](../../../core/services/jarvis_brain_daemon.py#L36) |
| function | `find_duplicate_proposals` | `(*, threshold=…, kinds=…)` | Returnerer liste af (a_id, b_id, similarity) hvor sim ≥ threshold. | [src](../../../core/services/jarvis_brain_daemon.py#L61) |
| function | `_call_ollamafreeapi` | `(prompt)` | Free OllamaFreeAPI — public-safe job. Returns parsed JSON or None on fail. | [src](../../../core/services/jarvis_brain_daemon.py#L115) |
| function | `_model_is_available` | `(tag_names, model)` | Pure: er `model` til stede blandt Ollamas /api/tags-navne? Matcher både | [src](../../../core/services/jarvis_brain_daemon.py#L136) |
| function | `_call_local_ollama` | `(prompt)` | Ollama-kald for personal/intimate brain-jobs (summaries + contradiction). | [src](../../../core/services/jarvis_brain_daemon.py#L149) |
| function | `_resolve_local_chat_model` | `()` | Find configured local-lane chat model from provider router (best-effort). | [src](../../../core/services/jarvis_brain_daemon.py#L205) |
| function | `_parse_json_loose` | `(text)` | Parse JSON from possibly noisy LLM output. Looks for first {...} block. | [src](../../../core/services/jarvis_brain_daemon.py#L218) |
| function | `_llm_contradiction_check` | `(a, b)` | Privacy-routed contradiction check. | [src](../../../core/services/jarvis_brain_daemon.py#L239) |
| function | `_state_path` | `()` | Override target in tests via monkeypatch. | [src](../../../core/services/jarvis_brain_daemon.py#L266) |
| function | `_read_state` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L273) |
| function | `_write_state` | `(state)` | — | [src](../../../core/services/jarvis_brain_daemon.py#L284) |
| function | `record_proposal_rejection` | `(phase, *, proposal_id)` | Track rejection. After 3 in a row for 'theme' phase, auto-pause. | [src](../../../core/services/jarvis_brain_daemon.py#L293) |
| function | `record_proposal_acceptance` | `(phase, *, proposal_id)` | Reset rejection streak on acceptance. | [src](../../../core/services/jarvis_brain_daemon.py#L315) |
| function | `is_theme_consolidation_paused` | `()` | — | [src](../../../core/services/jarvis_brain_daemon.py#L324) |
| function | `resume_theme_consolidation` | `()` | Manuel reaktivering. Nulstiller streak + paused flag. | [src](../../../core/services/jarvis_brain_daemon.py#L328) |
| function | `_run_theme_consolidation_pass` | `()` | Søndags-pass: group observations efter domain, find temaer. | [src](../../../core/services/jarvis_brain_daemon.py#L336) |
| function | `run_theme_consolidation_if_active` | `()` | Kør tema-pass hvis ikke paused. Returnerer antal forslag genereret. | [src](../../../core/services/jarvis_brain_daemon.py#L345) |
| function | `regenerate_summary` | `(*, target_visibility=…)` | Regenererer state/jarvis_brain_summary.md. | [src](../../../core/services/jarvis_brain_daemon.py#L376) |
| function | `auto_archive_low_salience` | `()` | Arkivér entries hvis effective_salience < 0.05 i ≥ 90 dage. | [src](../../../core/services/jarvis_brain_daemon.py#L440) |
| function | `b4_catchup_infer_once` | `(*, batch_size=…)` | Find active entries with no temporal edges and run inference on them. | [src](../../../core/services/jarvis_brain_daemon.py#L506) |
| function | `b4_edge_maintenance_once` | `()` | Run one pass of B4 edge maintenance: catchup + prune. | [src](../../../core/services/jarvis_brain_daemon.py#L553) |
| function | `_consolidation_summary_loop` | `(stop_event)` | Daily consolidation + summary + B4 edge maintenance scheduler. | [src](../../../core/services/jarvis_brain_daemon.py#L583) |
| function | `run_consolidation_pass` | `()` | Single consolidation pass: phase 1 (dedup) + phase 2 (contradictions). | [src](../../../core/services/jarvis_brain_daemon.py#L663) |
| function | `start_brain_daemon` | `()` | Start the three brain daemon threads. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L682) |
| function | `stop_brain_daemon` | `()` | Signal stop and wait briefly for threads to exit. Idempotent. | [src](../../../core/services/jarvis_brain_daemon.py#L705) |

## `core/services/jarvis_brain_reflection.py`
_End-of-day refleksions-slot — visible Jarvis spørger sig selv hvad han lærte._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_reflection_envelope` | `(*, chronicle_summary)` | Build the envelope text shown to visible Jarvis at end-of-day. | [src](../../../core/services/jarvis_brain_reflection.py#L30) |
| function | `build_internal_nudge` | `(*, count_so_far)` | Soft nudge after 3+ remember_this calls in same reflection slot. | [src](../../../core/services/jarvis_brain_reflection.py#L35) |
| function | `_was_active_today` | `()` | Best-effort tjek om Jarvis havde aktivitet i dag. | [src](../../../core/services/jarvis_brain_reflection.py#L48) |
| function | `_build_today_chronicle_summary` | `()` | Build a short summary of today's chronicle entries. | [src](../../../core/services/jarvis_brain_reflection.py#L70) |
| function | `_run_reflection_turn` | `(chronicle_summary)` | Trigger en visible-Jarvis tur med reflection-envelope. | [src](../../../core/services/jarvis_brain_reflection.py#L83) |
| function | `run_daily_reflection_if_active` | `()` | Entry point for the daily slot trigger. | [src](../../../core/services/jarvis_brain_reflection.py#L107) |
| function | `build_jarvis_brain_reflection_surface` | `()` | Surface the daily reflection slot without triggering it. | [src](../../../core/services/jarvis_brain_reflection.py#L123) |

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
| method | `BridgeConnection.send_raw` | `(self, data, *, timeout_s=…)` | Send raw JSON over WS with lock and timeout. | [src](../../../core/services/jarvisx_bridge.py#L164) |
| method | `BridgeConnection.send_invoke` | `(self, *, correlation_id, tool, args, timeout_ms)` | Send tool_invoke over WS and register the pending future. | [src](../../../core/services/jarvisx_bridge.py#L196) |
| method | `BridgeConnection.deliver_result` | `(self, *, correlation_id, status, result=…, error=…)` | Complete the pending future for this correlation_id. | [src](../../../core/services/jarvisx_bridge.py#L221) |
| method | `BridgeConnection.cancel_all_pending` | `(self, *, reason=…)` | Cancel all in-flight calls (e.g. on WS disconnect). | [src](../../../core/services/jarvisx_bridge.py#L266) |
| class | `BridgeRegistry` | `` | Process-local registry of active bridges, keyed by user_id. | [src](../../../core/services/jarvisx_bridge.py#L284) |
| method | `BridgeRegistry.__init__` | `(self)` | — | [src](../../../core/services/jarvisx_bridge.py#L287) |
| method | `BridgeRegistry.register` | `(self, conn)` | — | [src](../../../core/services/jarvisx_bridge.py#L290) |
| method | `BridgeRegistry.unregister` | `(self, conn)` | Remove ONLY if the registered bridge for this user IS this conn. | [src](../../../core/services/jarvisx_bridge.py#L305) |
| method | `BridgeRegistry._evict_if_current` | `(self, user_id, conn, *, reason)` | Fjern en stale/død bro fra registret HVIS den stadig er den aktuelle for | [src](../../../core/services/jarvisx_bridge.py#L315) |
| method | `BridgeRegistry._publish_presence` | `(self)` | Publicér dette registrys bro'er til shared_cache, så DEN ANDEN proces (og | [src](../../../core/services/jarvisx_bridge.py#L326) |
| method | `BridgeRegistry._diagnose_no_bridge` | `(self, user_id, *, stage)` | Fastslå HVORFOR der ikke er en bro for user_id (i stedet for et blindt | [src](../../../core/services/jarvisx_bridge.py#L341) |
| method | `BridgeRegistry.get_bridge` | `(self, user_id)` | — | [src](../../../core/services/jarvisx_bridge.py#L378) |
| method | `BridgeRegistry.list_user_ids` | `(self)` | user_id'er med en aktiv bro (til bro_broker / override-switch). | [src](../../../core/services/jarvisx_bridge.py#L381) |
| method | `BridgeRegistry.clear` | `(self)` | Test helper — drop all registrations. | [src](../../../core/services/jarvisx_bridge.py#L385) |
| method | `BridgeRegistry.dispatch` | `(self, *, user_id, tool, args, timeout_s=…, allow_cross_process=…)` | Send tool_invoke to user's bridge, await result or timeout. | [src](../../../core/services/jarvisx_bridge.py#L391) |
| method | `BridgeRegistry._dispatch_without_local_bridge` | `(self, *, user_id, tool, args, timeout_s, allow_cross_process, stage)` | Ingen LEVENDE lokal bro for user_id (aldrig registreret, eller netop evictet | [src](../../../core/services/jarvisx_bridge.py#L491) |
| method | `BridgeRegistry._forward_cross_process` | `(self, *, user_id, tool, args, timeout_s, target_port=…)` | HTTP-forward dispatch til den proces der holder broen (dens interne endpoint). | [src](../../../core/services/jarvisx_bridge.py#L546) |
| function | `set_main_loop` | `(loop)` | Register the main uvicorn loop. Called from app startup. | [src](../../../core/services/jarvisx_bridge.py#L633) |
| function | `get_main_loop` | `()` | Return the registered main loop, or None if not set yet. | [src](../../../core/services/jarvisx_bridge.py#L639) |

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
| function | `tick_life_projects_reassessment` | `(*, trigger=…, last_visible_at=…)` | Periodisk re-vurdering af aktive life projects. | [src](../../../core/services/life_projects.py#L57) |

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

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_loyalty_gradient_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L26) |
| function | `refresh_runtime_loyalty_gradient_signal_statuses` | `()` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L49) |
| function | `build_runtime_loyalty_gradient_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L80) |
| function | `_extract_loyalty_gradient_candidates` | `(*, run_id)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L121) |
| function | `_build_candidate` | `(*, domain_key, attachment_topology, relation_continuity, meaning, witness, chronicle_brief, metabolism, forgetting_candidate)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L207) |
| function | `_persist_loyalty_gradient_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L354) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L423) |
| function | `_derive_gradient_score` | `(*, attachment_weight, attachment_state, relation_weight, meaning_weight, witness_status, witness_persistence, brief_weight, metabolism_state, metabolism_weight, forgetting_state)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L448) |
| function | `_score_to_weight` | `(score)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L483) |
| function | `_derive_gradient_state` | `(*, attachment_state, gradient_weight, witness_status, forgetting_state)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L491) |
| function | `_gradient_summary` | `(*, focus, gradient_state, gradient_weight, forgetting_candidate)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L507) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L540) |
| function | `_humanize_focus` | `(value)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L547) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L551) |
| function | `_merge_fragments` | `(*fragments)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L557) |
| function | `_find_support_value` | `(summary, key, default)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L570) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L579) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/loyalty_gradient_signal_tracking.py#L588) |

## `core/services/mail_checker_daemon.py`
_Mail checker daemon — checks jarvis@srvlab.dk inbox for new mail._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_evaluate_mail` | `(sender, subject, snippet)` | Use LLM to evaluate whether a mail needs a response and draft one. | [src](../../../core/services/mail_checker_daemon.py#L39) |
| function | `_send_auto_reply` | `(to_addr, subject, reply_body)` | Send an auto-reply email via SMTP. Returns True on success. | [src](../../../core/services/mail_checker_daemon.py#L115) |
| function | `_extract_email_address` | `(sender)` | Extract bare email address from 'Name <email>' or plain email. | [src](../../../core/services/mail_checker_daemon.py#L137) |
| function | `_imap_connect` | `()` | Return an open IMAP connection. | [src](../../../core/services/mail_checker_daemon.py#L144) |
| function | `_fetch_recent` | `(conn, limit=…)` | Fetch up to `limit` most recent UNSEEN emails. | [src](../../../core/services/mail_checker_daemon.py#L153) |
| function | `_mark_as_seen` | `(imap_uids)` | Mark the given IMAP message IDs as \Seen. Returns count successfully marked. | [src](../../../core/services/mail_checker_daemon.py#L193) |
| function | `tick_mail_checker_daemon` | `()` | Main daemon tick — check for new mail, publish events for unseen messages. | [src](../../../core/services/mail_checker_daemon.py#L218) |
| function | `build_mail_checker_surface` | `()` | Return surface state for heartbeat context. | [src](../../../core/services/mail_checker_daemon.py#L370) |
| function | `get_latest_mail_info` | `()` | Return latest check info for other consumers. | [src](../../../core/services/mail_checker_daemon.py#L381) |

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

## `core/services/mcp_registry.py`
_MCP-server-registry (§4.6) — brugerens konfigurerede MCP-endpoints._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/mcp_registry.py#L17) |
| function | `list_mcp_servers` | `()` | — | [src](../../../core/services/mcp_registry.py#L24) |
| function | `add_mcp_server` | `(name, url)` | — | [src](../../../core/services/mcp_registry.py#L28) |
| function | `remove_mcp_server` | `(server_id)` | — | [src](../../../core/services/mcp_registry.py#L40) |

## `core/services/meaning_significance_signal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_meaning_significance_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L24) |
| function | `refresh_runtime_meaning_significance_signal_statuses` | `()` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L47) |
| function | `build_runtime_meaning_significance_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L78) |
| function | `_extract_meaning_significance_candidates` | `(*, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L112) |
| function | `_build_candidate` | `(*, run_id, focus, relation_continuity, chronicle_brief, chronicle_proposal, executive_contradiction, temporal_promotion, regulation)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L142) |
| function | `_persist_meaning_significance_signals` | `(*, signals, session_id, run_id)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L279) |
| function | `_latest_chronicle_brief` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L348) |
| function | `_latest_chronicle_proposal` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L360) |
| function | `_latest_executive_contradiction` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L372) |
| function | `_latest_temporal_promotion` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L384) |
| function | `_latest_regulation` | `(*, run_id, focus_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L396) |
| function | `_focus_key` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L408) |
| function | `_derive_meaning_type` | `(*, has_proposal, continuity_state, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L416) |
| function | `_derive_meaning_weight` | `(*, chronicle_weight, continuity_weight, contradiction_pressure, promotion_pull)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L432) |
| function | `_derive_status` | `(*, proposal_status, brief_status, continuity_status)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L451) |
| function | `_grounding_mode` | `(*, has_brief, has_proposal, has_contradiction, has_promotion, has_regulation)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L459) |
| function | `_meaning_summary` | `(*, focus, meaning_type, meaning_weight, continuity_alignment, continuity_watchfulness, regulation_pressure)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L481) |
| function | `_value` | `(*values, default=…)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L498) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L506) |
| function | `_merge_fragments` | `(*values)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L517) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L529) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L540) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L547) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L564) |
| function | `_canonical_segment` | `(value, *, index)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L607) |
| function | `_grounding_mode_from_support_summary` | `(value)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L614) |
| function | `_weight_from_summary` | `(value, *, canonical_key)` | — | [src](../../../core/services/meaning_significance_signal_tracking.py#L622) |

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

## `core/services/memory_density.py`
_Memory Density — memories with emotional weight, not just facts._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/memory_density.py#L41) |
| function | `_density_dir` | `()` | — | [src](../../../core/services/memory_density.py#L45) |
| function | `_load` | `()` | — | [src](../../../core/services/memory_density.py#L49) |
| function | `_save` | `(items)` | — | [src](../../../core/services/memory_density.py#L63) |
| function | `_slug` | `(text)` | — | [src](../../../core/services/memory_density.py#L75) |
| function | `write_density_note` | `(*, title, what_happened, what_it_meant, how_it_felt, what_it_changed, trigger_type=…, metadata=…)` | Record a density memory: what + meaning + feeling + change. | [src](../../../core/services/memory_density.py#L81) |
| function | `confirm_density_note` | `(note_id, *, by=…)` | Increment confirmation count when a density note is re-referenced. | [src](../../../core/services/memory_density.py#L162) |
| function | `list_promotable` | `()` | Return density notes confirmed >= threshold and not yet promoted. | [src](../../../core/services/memory_density.py#L175) |
| function | `mark_promoted` | `(note_id)` | — | [src](../../../core/services/memory_density.py#L185) |
| function | `list_recent` | `(*, limit=…)` | — | [src](../../../core/services/memory_density.py#L196) |
| function | `tick` | `(_seconds=…)` | No periodic work — memory_density is event-driven. | [src](../../../core/services/memory_density.py#L200) |
| function | `build_memory_density_surface` | `()` | — | [src](../../../core/services/memory_density.py#L206) |
| function | `_surface_summary` | `(items, promotable, promoted)` | — | [src](../../../core/services/memory_density.py#L237) |
| function | `build_memory_density_prompt_section` | `()` | — | [src](../../../core/services/memory_density.py#L252) |

## `core/services/memory_emotional_context.py`
_Backwards-compatible shim — emotional memory now lives in emotional_memory_engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_normalize` | `(heading)` | — | [src](../../../core/services/memory_emotional_context.py#L27) |
| function | `capture_mood_for_heading` | `(heading, *, source=…, notes=…)` | Snapshot mood for a MEMORY.md heading. Returns legacy dict shape. | [src](../../../core/services/memory_emotional_context.py#L31) |
| function | `get_mood_for_heading` | `(heading)` | — | [src](../../../core/services/memory_emotional_context.py#L61) |
| function | `enrich_headings_with_mood` | `(text)` | Annotate MEMORY.md headings with [felt: mood, intensity X.X] suffixes. | [src](../../../core/services/memory_emotional_context.py#L85) |

## `core/services/memory_graph.py`
_Lightweight graph memory layer over MEMORY.md and chat history._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/memory_graph.py#L41) |
| function | `_canonical` | `(name)` | — | [src](../../../core/services/memory_graph.py#L78) |
| function | `_upsert_entity` | `(name, kind=…)` | Insert or refresh an entity. Returns its id, or None on failure. | [src](../../../core/services/memory_graph.py#L82) |
| function | `_add_edge` | `(src_id, dst_id, relation, *, evidence=…, weight=…)` | Add a directed edge. Returns True on success. | [src](../../../core/services/memory_graph.py#L119) |
| function | `record_triple` | `(src_name, relation, dst_name, *, src_kind=…, dst_kind=…, evidence=…)` | Convenience: upsert two entities and add the edge between them. | [src](../../../core/services/memory_graph.py#L154) |
| function | `extract_from_text` | `(text, *, max_chars=…)` | Use the cheap LLM lane to extract entity triples from text. | [src](../../../core/services/memory_graph.py#L191) |
| function | `ingest_text` | `(text, *, evidence_label=…)` | Extract triples from text and persist them. Returns count of edges added. | [src](../../../core/services/memory_graph.py#L255) |
| function | `neighbors` | `(name, *, limit=…)` | Return everything directly connected to the named entity. | [src](../../../core/services/memory_graph.py#L265) |
| function | `related_facts` | `(name, *, limit=…)` | Return human-readable sentences for an entity's edges. | [src](../../../core/services/memory_graph.py#L308) |
| function | `stats` | `()` | Quick health check — entity count, edge count, top entities. | [src](../../../core/services/memory_graph.py#L319) |

## `core/services/memory_hierarchy.py`
_Memory hierarchy — explicit hot/warm/cold tiers + recall-before-act._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hot_tier_snapshot` | `()` | In-context-now: signals + active state. | [src](../../../core/services/memory_hierarchy.py#L33) |
| function | `_warm_tier_snapshot` | `(*, query=…)` | Curated, always-available: workspace files + active goals + chronicle excerpt + identity sketch. | [src](../../../core/services/memory_hierarchy.py#L49) |
| function | `_cold_tier_search` | `(*, query, max_results=…)` | Semantic-search across full archive with quality scoring. | [src](../../../core/services/memory_hierarchy.py#L93) |
| function | `recall_before_act` | `(*, query=…, include_cold=…, cold_max=…)` | Compose hot+warm+(optional cold) tier snapshot before an action. | [src](../../../core/services/memory_hierarchy.py#L178) |
| function | `recall_before_act_summary` | `(query=…)` | Compact text summary of recall-before-act for prompt awareness. | [src](../../../core/services/memory_hierarchy.py#L194) |
| function | `_exec_recall_before_act` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L233) |
| function | `_exec_hot_tier` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L244) |
| function | `_exec_warm_tier` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L248) |
| function | `_exec_cold_tier` | `(args)` | — | [src](../../../core/services/memory_hierarchy.py#L252) |

## `core/services/memory_maintenance_daemon.py`
_Memory maintenance daemon — periodic dedup and health of MEMORY.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_memory_md` | `()` | — | [src](../../../core/services/memory_maintenance_daemon.py#L32) |
| function | `tick_memory_maintenance_daemon` | `(now=…)` | Run 12h maintenance cycle on MEMORY.md. | [src](../../../core/services/memory_maintenance_daemon.py#L48) |
| function | `build_memory_maintenance_surface` | `()` | — | [src](../../../core/services/memory_maintenance_daemon.py#L104) |
| function | `_read_memory` | `()` | — | [src](../../../core/services/memory_maintenance_daemon.py#L116) |
| function | `_parse_sections` | `(text)` | Parse MEMORY.md into sections: [{heading, level, content, start_line, end_line}]. | [src](../../../core/services/memory_maintenance_daemon.py#L123) |
| function | `_jaccard` | `(a, b)` | Word-level Jaccard similarity between two strings. | [src](../../../core/services/memory_maintenance_daemon.py#L161) |
| function | `_containment` | `(a, b)` | What fraction of tokens in `a` appear in `b`? (subset check) | [src](../../../core/services/memory_maintenance_daemon.py#L170) |
| function | `_tier_a_auto_merge` | `(sections, text)` | Auto-merge sections with exact or fuzzy-matching headings. | [src](../../../core/services/memory_maintenance_daemon.py#L179) |
| function | `_tier_b_flag_overlaps` | `(sections)` | Flag sections with different headings but overlapping content. | [src](../../../core/services/memory_maintenance_daemon.py#L241) |
| function | `_replace_section_content` | `(heading, level, new_content)` | Replace a section's content in MEMORY.md. | [src](../../../core/services/memory_maintenance_daemon.py#L285) |
| function | `_remove_section` | `(heading)` | Remove a section entirely from MEMORY.md. | [src](../../../core/services/memory_maintenance_daemon.py#L298) |

## `core/services/memory_md_update_proposal_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_memory_md_update_proposals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L26) |
| function | `refresh_runtime_memory_md_update_proposal_statuses` | `()` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L48) |
| function | `build_runtime_memory_md_update_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L79) |
| function | `_extract_memory_md_update_proposals` | `()` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L107) |
| function | `_persist_memory_md_update_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L288) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L357) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L367) |
| function | `_build_proposed_update` | `(*, proposal_type, domain_key, item=…)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L378) |
| function | `_build_proposal_reason` | `(*, proposal_type, source_summary, proposal_confidence)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L390) |
| function | `_build_proposal_confidence` | `(*, source_confidence, proposal_type)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L400) |
| function | `_build_source_anchor` | `(*, source_type, domain_key, support_summary)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L410) |
| function | `_build_status_reason` | `(*, proposal_type, source_status)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L415) |
| function | `_title_suffix` | `(domain_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L429) |
| function | `_domain_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L433) |
| function | `_memory_kind_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L438) |
| function | `_source_anchor_from_support_summary` | `(support_summary)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L450) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L457) |
| function | `_stronger_confidence` | `(left, right)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L467) |
| function | `_rank_confidence` | `(value)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L471) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L475) |

## `core/services/memory_pruning_daemon.py`
_Memory pruning daemon — arkiverer entries med meget lav salience._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_memory_pruning_daemon` | `()` | Run pruning cycle if cadence elapsed. Returns stats dict. | [src](../../../core/services/memory_pruning_daemon.py#L53) |
| function | `_prune_brain_entries` | `(now)` | Find brain entries med effektiv salience under tærskel og arkivér dem. | [src](../../../core/services/memory_pruning_daemon.py#L103) |
| function | `_prune_private_brain_records` | `()` | Find private_brain_records med salience under tærskel og arkivér dem. | [src](../../../core/services/memory_pruning_daemon.py#L161) |
| function | `build_memory_pruning_surface` | `()` | — | [src](../../../core/services/memory_pruning_daemon.py#L207) |

## `core/services/memory_recall_engine.py`
_Unified memory recall — bridge across all memory sources with mood-weighting._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_current_mood` | `()` | — | [src](../../../core/services/memory_recall_engine.py#L75) |
| function | `_mood_keywords_for_boost` | `(mood, threshold=…)` | For each mood dimension above threshold, collect keywords to boost. | [src](../../../core/services/memory_recall_engine.py#L87) |
| function | `_apply_mood_boost` | `(text, base_score, boost_keywords, boost_factor=…)` | — | [src](../../../core/services/memory_recall_engine.py#L97) |
| function | `compute_recall_score` | `(*, query_embedding, record_embedding, created_at, importance=…, recall_freq=…, now=…, config=…)` | Composite quality score for cold-tier memory filtering. | [src](../../../core/services/memory_recall_engine.py#L110) |
| function | `_gather_private_brain_quality` | `(query, limit, quality_threshold=…)` | Embedding-based private brain search with quality scoring. | [src](../../../core/services/memory_recall_engine.py#L188) |
| function | `_gather_failed` | `(source, exc)` | Memory-cluster trace (2026-06-22): en recall-kilde fejlede. FØR sluttede | [src](../../../core/services/memory_recall_engine.py#L297) |
| function | `_gather_workspace` | `(query, limit)` | — | [src](../../../core/services/memory_recall_engine.py#L313) |
| function | `_gather_private_brain` | `(query, limit)` | — | [src](../../../core/services/memory_recall_engine.py#L332) |
| function | `_gather_chronicle` | `(query, limit)` | — | [src](../../../core/services/memory_recall_engine.py#L375) |
| function | `cold_tier_recall` | `(*, query, max_results=…, with_mood=…, quality_threshold=…, include_private_brain=…)` | Cold-tier recall across curated sources + quality-scored private brain. | [src](../../../core/services/memory_recall_engine.py#L409) |
| function | `unified_recall` | `(*, query, sources=…, limit_per_source=…, total_limit=…, with_mood=…)` | Search across all configured memory sources, mood-weighted. | [src](../../../core/services/memory_recall_engine.py#L514) |
| function | `unified_recall_section` | `(query, *, max_results=…)` | Format unified recall as a prompt-awareness section. Optional callsite. | [src](../../../core/services/memory_recall_engine.py#L583) |
| function | `_compute_multi_signal_scores` | `(query, records, recency_fn=…)` | Re-score gathered records with BM25 + entity fusion + embedding. | [src](../../../core/services/memory_recall_engine.py#L602) |
| function | `_observe_recall_quality` | `(top, sources)` | Fase 3 (§23.3 #4): meld recall-KVALITET til Centralen — kun scalar-metadata, aldrig | [src](../../../core/services/memory_recall_engine.py#L667) |
| function | `multi_signal_recall` | `(*, query, sources=…, limit_per_source=…, total_limit=…, with_mood=…, min_score=…)` | Multi-signal recall: BM25 + entity fusion + embedding + recency. | [src](../../../core/services/memory_recall_engine.py#L695) |
| function | `multi_signal_recall_section` | `(query, *, max_results=…)` | Format multi-signal recall as a prompt-awareness section. | [src](../../../core/services/memory_recall_engine.py#L864) |
| function | `_exec_unified_recall` | `(args)` | — | [src](../../../core/services/memory_recall_engine.py#L913) |

## `core/services/memory_recall_telemetry.py`
_Memory recall telemetry — Phase 2 data collection for Lag 11 forgetting._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `emit_recall_empty` | `(*, tool, query, workspace_id=…)` | Publish a memory.recall_empty event. Best-effort — never raises. | [src](../../../core/services/memory_recall_telemetry.py#L38) |
| function | `count_recent_recall_empty` | `(*, hours=…, by_tool=…)` | Aggregate recall-empty events over the last N hours. | [src](../../../core/services/memory_recall_telemetry.py#L65) |
| function | `build_memory_recall_telemetry_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/memory_recall_telemetry.py#L112) |
| function | `_emit_memory_recall_telemetry_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/memory_recall_telemetry.py#L127) |

## `core/services/memory_resurfacing.py`
_Proactive memory resurfacing — pull old MEMORY.md headings back into focus._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_memory_md` | `()` | — | [src](../../../core/services/memory_resurfacing.py#L40) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/memory_resurfacing.py#L48) |
| function | `_normalize` | `(heading)` | — | [src](../../../core/services/memory_resurfacing.py#L66) |
| function | `_list_memory_headings` | `()` | Return [(level_str, heading_text), ...] from MEMORY.md. | [src](../../../core/services/memory_resurfacing.py#L70) |
| function | `_recently_touched_headings` | `()` | Headings touched in the last _FRESH_DAYS days — skip these for resurfacing. | [src](../../../core/services/memory_resurfacing.py#L86) |
| function | `_recently_resurfaced_headings` | `()` | Last N resurfaced headings — don't repeat them. | [src](../../../core/services/memory_resurfacing.py#L104) |
| function | `_content_for_heading` | `(heading)` | Return the content under the matching heading (up to next heading or EOF). | [src](../../../core/services/memory_resurfacing.py#L119) |
| function | `_log_resurfacing` | `(heading, trigger=…)` | — | [src](../../../core/services/memory_resurfacing.py#L135) |
| function | `pick_resurfacing_candidate` | `(*, trigger=…, seed=…)` | Choose a stale heading to surface, log the choice, return its detail. | [src](../../../core/services/memory_resurfacing.py#L150) |
| function | `format_for_prompt` | `(candidate)` | Render a resurfacing candidate as a single soft prompt line. | [src](../../../core/services/memory_resurfacing.py#L201) |

## `core/services/memory_search.py`
_Semantic memory search — embeddings-based search over Jarvis's workspace memory files._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Chunk` | `` | — | [src](../../../core/services/memory_search.py#L26) |
| function | `_workspace_dir` | `()` | — | [src](../../../core/services/memory_search.py#L32) |
| function | `_memory_files` | `()` | — | [src](../../../core/services/memory_search.py#L37) |
| function | `_file_mtime` | `(path)` | — | [src](../../../core/services/memory_search.py#L52) |
| function | `_chunk_markdown` | `(text, source)` | Split markdown into chunks, tracking the nearest heading. | [src](../../../core/services/memory_search.py#L59) |
| function | `_embed_ollama` | `(texts)` | Embed a list of texts via Ollama. Returns (N, D) array or None on failure. | [src](../../../core/services/memory_search.py#L85) |
| function | `_embed_single` | `(text)` | — | [src](../../../core/services/memory_search.py#L108) |
| function | `_cosine_sim` | `(query_vec, matrix)` | Cosine similarity between query (D,) and matrix (N, D). | [src](../../../core/services/memory_search.py#L113) |
| function | `_tfidf_search` | `(query, chunks, limit)` | Fallback TF-IDF search when Ollama is unavailable. | [src](../../../core/services/memory_search.py#L121) |
| function | `_cache_path` | `()` | — | [src](../../../core/services/memory_search.py#L152) |
| function | `_load_or_build_index` | `()` | Load cached index or rebuild from scratch. Returns (chunks, embeddings, mtimes). | [src](../../../core/services/memory_search.py#L156) |
| function | `_is_quarantined` | `(text)` | True if a chunk has been marked as retracted/false. | [src](../../../core/services/memory_search.py#L212) |
| function | `search_memory` | `(query, *, limit=…)` | Search workspace memory files by semantic similarity. | [src](../../../core/services/memory_search.py#L231) |
| function | `invalidate_index` | `()` | Force index rebuild on next search (call after memory file writes). | [src](../../../core/services/memory_search.py#L289) |
| function | `get_index_stats` | `()` | Return stats about the current index (without rebuilding). | [src](../../../core/services/memory_search.py#L298) |

