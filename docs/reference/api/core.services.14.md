# `core.services.14` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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
| function | `neighbors` | `(name, *, limit=…)` | Return everything directly connected to the named entity. | [src](../../../core/services/memory_graph.py#L273) |
| function | `related_facts` | `(name, *, limit=…)` | Return human-readable sentences for an entity's edges. | [src](../../../core/services/memory_graph.py#L316) |
| function | `stats` | `()` | Quick health check — entity count, edge count, top entities. | [src](../../../core/services/memory_graph.py#L327) |

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
| function | `_looks_like_sentence` | `(domain_key)` | A slugified user message ("det-er-fordi-du-prompt-er-rodet") — not a topic. | [src](../../../core/services/memory_md_update_proposal_tracking.py#L52) |
| function | `refresh_runtime_memory_md_update_proposal_statuses` | `()` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L58) |
| function | `build_runtime_memory_md_update_proposal_surface` | `(*, limit=…)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L94) |
| function | `_extract_memory_md_update_proposals` | `()` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L122) |
| function | `_persist_memory_md_update_proposals` | `(*, proposals, session_id, run_id)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L307) |
| function | `_with_runtime_view` | `(item, proposal)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L376) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L386) |
| function | `_build_proposed_update` | `(*, proposal_type, domain_key, item=…)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L397) |
| function | `_build_proposal_reason` | `(*, proposal_type, source_summary, proposal_confidence)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L409) |
| function | `_build_proposal_confidence` | `(*, source_confidence, proposal_type)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L419) |
| function | `_build_source_anchor` | `(*, source_type, domain_key, support_summary)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L429) |
| function | `_build_status_reason` | `(*, proposal_type, source_status)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L434) |
| function | `_title_suffix` | `(domain_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L448) |
| function | `_domain_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L452) |
| function | `_memory_kind_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L457) |
| function | `_source_anchor_from_support_summary` | `(support_summary)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L469) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L476) |
| function | `_stronger_confidence` | `(left, right)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L486) |
| function | `_rank_confidence` | `(value)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L490) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/memory_md_update_proposal_tracking.py#L494) |

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
| class | `Chunk` | `` | — | [src](../../../core/services/memory_search.py#L32) |
| function | `_workspace_dir` | `()` | Workspace for the current user, falling back to the owner's workspace. | [src](../../../core/services/memory_search.py#L38) |
| function | `_memory_files` | `(ws=…)` | — | [src](../../../core/services/memory_search.py#L52) |
| function | `_file_mtime` | `(path)` | — | [src](../../../core/services/memory_search.py#L71) |
| function | `_chunk_markdown` | `(text, source)` | Split markdown into chunks, tracking the nearest heading. | [src](../../../core/services/memory_search.py#L78) |
| function | `_embed_ollama` | `(texts)` | Embed a list of texts via Ollama. Returns (N, D) array or None on failure. | [src](../../../core/services/memory_search.py#L104) |
| function | `_embed_single` | `(text)` | — | [src](../../../core/services/memory_search.py#L159) |
| function | `_cosine_sim` | `(query_vec, matrix)` | Cosine similarity between query (D,) and matrix (N, D). | [src](../../../core/services/memory_search.py#L171) |
| function | `_tfidf_search` | `(query, chunks, limit)` | Fallback TF-IDF search when Ollama is unavailable. | [src](../../../core/services/memory_search.py#L179) |
| function | `_cache_path` | `(ws=…)` | — | [src](../../../core/services/memory_search.py#L210) |
| function | `_chunk_all_files` | `(files, ws=…)` | Læs + chunk alle memory-filer. HURTIGT — kun fil-I/O, INGEN embedding. | [src](../../../core/services/memory_search.py#L218) |
| function | `_load_cached_vectors` | `(ws=…)` | chunk-tekst → vektor fra den eksisterende cache, til INKREMENTEL reindex. | [src](../../../core/services/memory_search.py#L235) |
| function | `_build_and_cache_index` | `(files, current_mtimes, ws=…)` | Byg indeks og skriv cache. Kaldes KUN fra baggrunds-tråden. | [src](../../../core/services/memory_search.py#L258) |
| function | `_schedule_background_rebuild` | `(files, current_mtimes, ws=…)` | Kør en fuld re-embed i BAGGRUNDEN (fire-and-forget, kun én ad gangen). Så en bruger-søgning | [src](../../../core/services/memory_search.py#L321) |
| function | `_load_or_build_index` | `(ws=…)` | Returnér (chunks, embeddings, mtimes). BLOKERER ALDRIG på et fuldt re-embed: | [src](../../../core/services/memory_search.py#L352) |
| function | `_is_quarantined` | `(text)` | True if a chunk has been marked as retracted/false. | [src](../../../core/services/memory_search.py#L396) |
| function | `_source_matches` | `(chunk_source, sources)` | — | [src](../../../core/services/memory_search.py#L415) |
| function | `search_memory` | `(query, *, limit=…, sources=…, workspace_dir=…)` | Search workspace memory files by semantic similarity. | [src](../../../core/services/memory_search.py#L422) |
| function | `invalidate_index` | `()` | Force index rebuild on next search (call after memory file writes). | [src](../../../core/services/memory_search.py#L498) |
| function | `get_index_stats` | `()` | Return stats about the current index (without rebuilding). | [src](../../../core/services/memory_search.py#L507) |

## `core/services/memory_tattoos.py`
_Memory Tattoos — emotional marks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `create_tattoo` | `(event, emotion, intensity)` | — | [src](../../../core/services/memory_tattoos.py#L9) |
| function | `describe_tattoo` | `()` | — | [src](../../../core/services/memory_tattoos.py#L19) |
| function | `format_tattoo_for_prompt` | `()` | — | [src](../../../core/services/memory_tattoos.py#L25) |
| function | `reset_memory_tattoos` | `()` | — | [src](../../../core/services/memory_tattoos.py#L31) |
| function | `build_memory_tattoos_surface` | `()` | — | [src](../../../core/services/memory_tattoos.py#L35) |

## `core/services/memory_write_policy.py`
_Memory Write Policy — gating + review queue for inferred memory writes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/memory_write_policy.py#L34) |
| function | `_load_queue` | `()` | — | [src](../../../core/services/memory_write_policy.py#L39) |
| function | `_save_queue` | `(queue)` | — | [src](../../../core/services/memory_write_policy.py#L53) |
| function | `_prune_rate_window` | `()` | — | [src](../../../core/services/memory_write_policy.py#L70) |
| function | `_rate_limit_block` | `()` | — | [src](../../../core/services/memory_write_policy.py#L77) |
| function | `_cooldown_block` | `(key)` | — | [src](../../../core/services/memory_write_policy.py#L84) |
| class | `PolicyDecision` | `` | — | [src](../../../core/services/memory_write_policy.py#L95) |
| function | `evaluate_write` | `(*, key, content, confidence=…, write_reason=…, metadata=…)` | Decide whether to allow, block, or queue this memory candidate. | [src](../../../core/services/memory_write_policy.py#L102) |
| function | `_enqueue_for_review` | `(*, key, content, confidence, write_reason, metadata)` | — | [src](../../../core/services/memory_write_policy.py#L150) |
| function | `list_pending_reviews` | `(*, limit=…)` | — | [src](../../../core/services/memory_write_policy.py#L176) |
| function | `approve_review` | `(item_id, *, decided_by=…)` | — | [src](../../../core/services/memory_write_policy.py#L182) |
| function | `reject_review` | `(item_id, *, decided_by=…)` | — | [src](../../../core/services/memory_write_policy.py#L194) |
| function | `build_memory_write_policy_surface` | `()` | — | [src](../../../core/services/memory_write_policy.py#L206) |
| function | `build_memory_write_policy_prompt_section` | `()` | — | [src](../../../core/services/memory_write_policy.py#L230) |
| function | `_emit_memory_write_policy_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/memory_write_policy.py#L241) |

## `core/services/memory_write_queue.py`
_Memory Write Queue — async write queue for sensory/brain memories._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/memory_write_queue.py#L52) |
| function | `enqueue_write` | `(queue_type, payload, priority=…)` | Enqueue a memory write for async processing. | [src](../../../core/services/memory_write_queue.py#L77) |
| function | `process_queue` | `(batch_size=…)` | Process pending write queue items. Called by the daemon tick. | [src](../../../core/services/memory_write_queue.py#L119) |
| function | `queue_size` | `()` | Return counts by status. | [src](../../../core/services/memory_write_queue.py#L218) |
| function | `build_memory_write_queue_surface` | `()` | Mission Control surface. | [src](../../../core/services/memory_write_queue.py#L240) |
| function | `tick_memory_write_queue_daemon` | `(now=…)` | Daemon tick: process pending writes every 120s. | [src](../../../core/services/memory_write_queue.py#L263) |
| function | `_max_retries_for` | `(queue_type)` | — | [src](../../../core/services/memory_write_queue.py#L303) |
| function | `_process_item` | `(queue_type, payload, retry_count)` | Execute one write. Returns (ok, error_message). | [src](../../../core/services/memory_write_queue.py#L311) |
| function | `_process_sensory` | `(payload, retry_count)` | Process a sensory memory write. | [src](../../../core/services/memory_write_queue.py#L333) |
| function | `_process_brain` | `(payload, retry_count)` | Process a brain entry write. | [src](../../../core/services/memory_write_queue.py#L352) |
| function | `_process_sidecar` | `(payload, retry_count)` | Process a MEMORY.md sidecar: mood capture + graph ingestion. | [src](../../../core/services/memory_write_queue.py#L385) |
| function | `retry_failed` | `(limit=…)` | Reset failed items back to pending for retry. | [src](../../../core/services/memory_write_queue.py#L422) |
| function | `clean_old_done` | `(hours=…)` | Delete 'done' items older than N hours. | [src](../../../core/services/memory_write_queue.py#L446) |

## `core/services/meta_cognition_daemon.py`
_Meta-Cognition Daemon — first-person reflection on own state (Experiment 4: HOT)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_meta_cognition_daemon` | `()` | Run one meta-cognition pass. Returns generated/reason/meta_depth. | [src](../../../core/services/meta_cognition_daemon.py#L26) |
| function | `build_meta_cognition_surface` | `()` | MC surface for meta-cognition experiment. | [src](../../../core/services/meta_cognition_daemon.py#L82) |
| function | `_gather_state` | `()` | Collect cognitive + emotional state for meta-observation input. | [src](../../../core/services/meta_cognition_daemon.py#L108) |
| function | `_call_meta_llm` | `(prompt)` | Call cheap lane (Groq/etc.) first, Ollama fallback. Timeout 15s. | [src](../../../core/services/meta_cognition_daemon.py#L148) |
| function | `_compute_meta_depth` | `(meta_obs, meta_meta_obs)` | Return 2 if meta_meta diverges >70% from meta_obs (Jaccard distance), else 1. | [src](../../../core/services/meta_cognition_daemon.py#L204) |

## `core/services/meta_learning_aggregator.py`
_Meta-læring aggregator — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_in_window` | `(ts_iso, since, until)` | Defensive: parse ts and check if it's within [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L18) |
| function | `_bucket_confidence` | `(c)` | — | [src](../../../core/services/meta_learning_aggregator.py#L31) |
| function | `_confidence_score` | `(value, *, default=…)` | Normalize numeric and world-model textual confidence to 0..1. | [src](../../../core/services/meta_learning_aggregator.py#L39) |
| function | `_prediction_id` | `(prediction)` | — | [src](../../../core/services/meta_learning_aggregator.py#L52) |
| function | `aggregate_world_model` | `(*, since, until)` | Aggregate world-model prediction activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L60) |
| function | `_completion_seconds` | `(rec)` | Seconds between created_at and updated_at; None if either missing. | [src](../../../core/services/meta_learning_aggregator.py#L136) |
| function | `aggregate_plan_revision` | `(*, since, until)` | Aggregate plan-proposal activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L150) |
| function | `aggregate_curiosity` | `(*, since, until)` | Aggregate curiosity-tool activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L222) |
| function | `aggregate_skill_chain_phase2` | `(*, since, until)` | Aggregate skill_chain Phase 2 events in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L282) |
| function | `aggregate_tool_invention` | `(*, since, until)` | Aggregate tool-invention activity in [since, until]. | [src](../../../core/services/meta_learning_aggregator.py#L361) |

## `core/services/meta_learning_hypotheses.py`
_Meta-læring Phase 2: hypothesis registration + sample tracking._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create hypothesis + sample tables. | [src](../../../core/services/meta_learning_hypotheses.py#L37) |
| function | `register_hypothesis` | `(*, memo_id, candidate_idx)` | Promote a memo's hypothesis_candidate at index `candidate_idx` to | [src](../../../core/services/meta_learning_hypotheses.py#L79) |
| function | `record_hypothesis_sample` | `(*, hypothesis_id, supports, note=…)` | Append a sample. If the hypothesis has reached sample_size_needed, | [src](../../../core/services/meta_learning_hypotheses.py#L124) |
| function | `list_active_hypotheses` | `(*, limit=…)` | — | [src](../../../core/services/meta_learning_hypotheses.py#L189) |
| function | `format_active_hypotheses_for_awareness` | `()` | Awareness section showing active hypotheses + progress. | [src](../../../core/services/meta_learning_hypotheses.py#L214) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/meta_learning_hypotheses.py#L231) |

## `core/services/meta_learning_retrospective.py`
_Meta-læring retrospective generator — Phase 1 (AGI track #3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create learning_memos table + index. | [src](../../../core/services/meta_learning_retrospective.py#L34) |
| function | `_strip_markdown_fence` | `(text)` | — | [src](../../../core/services/meta_learning_retrospective.py#L71) |
| function | `_build_retrospective_prompt` | `(*, period_start, period_end, aggregator_snapshot)` | Build the cheap-lane prompt for weekly retrospective memo. | [src](../../../core/services/meta_learning_retrospective.py#L79) |
| function | `_parse_memo_markdown` | `(text)` | Parse cheap-lane markdown output into narrative + hypothesis_candidates. | [src](../../../core/services/meta_learning_retrospective.py#L123) |
| function | `_persist_memo` | `(*, memo_id, ts, period_start, period_end, narrative, hypothesis_candidates, aggregator_snapshot, model_used)` | Insert a new memo row. Returns memo_id. | [src](../../../core/services/meta_learning_retrospective.py#L199) |
| function | `fetch_latest_unacknowledged_memo` | `()` | Return the most recent memo with acknowledged_at IS NULL, or None. | [src](../../../core/services/meta_learning_retrospective.py#L237) |
| function | `fetch_memo_by_id` | `(memo_id)` | — | [src](../../../core/services/meta_learning_retrospective.py#L256) |
| function | `list_recent_memos` | `(limit=…)` | — | [src](../../../core/services/meta_learning_retrospective.py#L272) |
| function | `acknowledge_memo` | `(memo_id)` | Mark memo as acknowledged. Returns True if a row was updated. | [src](../../../core/services/meta_learning_retrospective.py#L285) |
| function | `_meta_learning_enabled` | `()` | — | [src](../../../core/services/meta_learning_retrospective.py#L303) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/meta_learning_retrospective.py#L310) |
| function | `generate_weekly_retrospective` | `(*, now)` | Generate a weekly retrospective memo for the 7 days ending at `now`. | [src](../../../core/services/meta_learning_retrospective.py#L318) |
| function | `_format_period_for_display` | `(period_start, period_end)` | Render period as 'YYYY-MM-DD to YYYY-MM-DD' for awareness display. | [src](../../../core/services/meta_learning_retrospective.py#L411) |
| function | `format_latest_unacknowledged_memo_for_awareness` | `()` | Render a short teaser for the most recent unacknowledged memo. | [src](../../../core/services/meta_learning_retrospective.py#L421) |

## `core/services/meta_reflection_daemon.py`
_Meta-reflection daemon — cross-signal pattern insight every 30 minutes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_credit_assignment` | `(cross_snapshot)` | Public wrapper over the Lag-1 credit-assignment pass (:func:`_check_outcomes`). | [src](../../../core/services/meta_reflection_daemon.py#L29) |
| function | `tick_meta_reflection_daemon` | `(cross_snapshot, *, skip_event_gate=…, skip_credit=…)` | Generate cross-signal meta-insight if cadence allows. Also checks for | [src](../../../core/services/meta_reflection_daemon.py#L44) |
| function | `_check_outcomes` | `(cross_snapshot)` | Check for unreviewed model_tier and response_style decisions and score them. | [src](../../../core/services/meta_reflection_daemon.py#L103) |
| function | `_expire_decision` | `(decision_id, reason)` | Mark a stale pending decision as expired so it drops from the | [src](../../../core/services/meta_reflection_daemon.py#L189) |
| function | `_get_turns_after` | `(created_at, min_turns=…)` | Get subsequent chat turns after a decision timestamp (any session). | [src](../../../core/services/meta_reflection_daemon.py#L208) |
| function | `_get_next_user_message` | `(created_at)` | Get the first user message after a decision timestamp (any session). | [src](../../../core/services/meta_reflection_daemon.py#L239) |
| function | `_generate_meta_insight` | `(cross_snapshot)` | — | [src](../../../core/services/meta_reflection_daemon.py#L264) |
| function | `_store_meta_insight` | `(insight)` | — | [src](../../../core/services/meta_reflection_daemon.py#L298) |
| function | `get_latest_meta_insight` | `()` | — | [src](../../../core/services/meta_reflection_daemon.py#L330) |
| function | `build_meta_reflection_surface` | `()` | — | [src](../../../core/services/meta_reflection_daemon.py#L334) |

## `core/services/metabolism_state_signal_tracking.py`
_Metabolism-state signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_metabolism_state_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L38) |
| function | `refresh_runtime_metabolism_state_signal_statuses` | `()` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L48) |
| function | `build_runtime_metabolism_state_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L52) |
| function | `_extract_metabolism_state_candidates` | `(*, run_id)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L56) |
| function | `_build_candidate` | `(*, domain_key, run_id, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L133) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L249) |
| function | `_metabolism_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L275) |
| function | `_derive_metabolism_state` | `(*, witness_status, chronicle_status, self_narrative_status, active_count, softening_count, fading_count, stale_count)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L297) |
| function | `_derive_metabolism_direction` | `(*, metabolism_state, witness_status, softening_count, fading_count)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L316) |
| function | `_derive_metabolism_weight` | `(*, active_count, carrying_count, stale_count, chronicle_status)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L336) |
| function | `_metabolism_summary` | `(*, focus, metabolism_state, metabolism_direction, metabolism_weight)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L351) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L375) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L382) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L395) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L407) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/metabolism_state_signal_tracking.py#L418) |

## `core/services/metacognition_signal_tracker.py`
_Metacognition signal tracker — Step E.v1 of meta-evne stack._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L70) |
| function | `_connect` | `()` | — | [src](../../../core/services/metacognition_signal_tracker.py#L90) |
| function | `_split_sentences` | `(text)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L100) |
| function | `_sentence_nouns` | `(sentence)` | Cheap content-word extraction: lowercase alpha tokens, ≥4 chars, | [src](../../../core/services/metacognition_signal_tracker.py#L105) |
| function | `_has_negation` | `(sentence)` | — | [src](../../../core/services/metacognition_signal_tracker.py#L119) |
| function | `score_contradiction` | `(text)` | Detect contradicting sentence pairs within the same response. | [src](../../../core/services/metacognition_signal_tracker.py#L124) |
| function | `score_claim_density` | `(text)` | Claim-bearing sentences / total sentences. Healthy: 0.3–0.7. | [src](../../../core/services/metacognition_signal_tracker.py#L166) |
| function | `record_signals` | `(run_id, text)` | Compute + persist + publish both signals for a completed run. | [src](../../../core/services/metacognition_signal_tracker.py#L187) |
| function | `latest_signals_section` | `(*, window_n=…)` | Return an awareness one-liner ONLY when recent signals are | [src](../../../core/services/metacognition_signal_tracker.py#L229) |
| function | `_listener_loop` | `(_q_unused=…)` | DB-polling listener — same cross-process pattern as | [src](../../../core/services/metacognition_signal_tracker.py#L285) |
| function | `start_metacognition_tracker` | `()` | Start DB-polling listener. Idempotent. | [src](../../../core/services/metacognition_signal_tracker.py#L342) |
| function | `stop_metacognition_tracker` | `()` | — | [src](../../../core/services/metacognition_signal_tracker.py#L359) |

## `core/services/metacognitive_integration.py`
_Metacognitive Integration — the overarching layer that synthesizes all cognitive layers into a coherent self-model._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/metacognitive_integration.py#L39) |
| function | `_extract_signal_values` | `(cognitive_state)` | Extract normalised signal values from the assembled cognitive state. | [src](../../../core/services/metacognitive_integration.py#L77) |
| function | `compute_coherence` | `(signal_values)` | Compute coherence score (0-1) from signal values. | [src](../../../core/services/metacognitive_integration.py#L198) |
| function | `compute_integration_quality` | `(cognitive_state)` | Compute integration quality — how many layers are active and contributing. | [src](../../../core/services/metacognitive_integration.py#L237) |
| function | `compute_self_assessment` | `(coherence, integration, signal_values)` | Compute metacognitive self-assessment. | [src](../../../core/services/metacognitive_integration.py#L283) |
| function | `get_metacognitive_line` | `(cognitive_state=…)` | Get the metacognitive integration prompt line. | [src](../../../core/services/metacognitive_integration.py#L332) |
| function | `get_metacognitive_detail` | `(cognitive_state=…)` | Get full metacognitive assessment as a dict (for debugging/MC). | [src](../../../core/services/metacognitive_integration.py#L385) |
| function | `_parse_raw_state` | `(raw)` | Parse the raw cognitive state string into a dict. | [src](../../../core/services/metacognitive_integration.py#L417) |
| function | `build_metacognitive_integration_surface` | `()` | — | [src](../../../core/services/metacognitive_integration.py#L494) |
| function | `_emit_integration_event` | `(layer, signal)` | — | [src](../../../core/services/metacognitive_integration.py#L503) |

## `core/services/mirror_engine.py`
_Mirror Engine — compassionate self-reflection during idle time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_mirror_insight` | `(*, idle_hours=…, open_loop_count=…, recent_error_count=…, recent_success_count=…, top_loop_summary=…)` | Generate a deterministic mirror insight. | [src](../../../core/services/mirror_engine.py#L20) |
| function | `build_mirror_surface` | `()` | — | [src](../../../core/services/mirror_engine.py#L56) |
| function | `_deterministic_insight` | `(*, idle_hours, open_loop_count, recent_error_count, recent_success_count, top_loop_summary)` | — | [src](../../../core/services/mirror_engine.py#L65) |

## `core/services/missions_pipeline.py`
_Missions Pipeline — flerfase opgaver med state-machine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MissionError` | `` | — | [src](../../../core/services/missions_pipeline.py#L52) |
| method | `MissionError.__init__` | `(self, code, message)` | — | [src](../../../core/services/missions_pipeline.py#L53) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/missions_pipeline.py#L58) |
| function | `_ensure_tables` | `()` | — | [src](../../../core/services/missions_pipeline.py#L62) |
| function | `_row_to_mission` | `(row)` | — | [src](../../../core/services/missions_pipeline.py#L107) |
| function | `create_mission` | `(*, title, description=…, goal=…, constraints=…, success_criteria=…, roles=…, metadata=…)` | Create a new mission in 'created' status. | [src](../../../core/services/missions_pipeline.py#L120) |
| function | `get_mission` | `(*, mission_id)` | — | [src](../../../core/services/missions_pipeline.py#L176) |
| function | `transition_mission_state` | `(*, mission_id, new_status, reason=…)` | Transition mission to new status, respecting _ALLOWED_TRANSITIONS. | [src](../../../core/services/missions_pipeline.py#L188) |
| function | `send_mission_message` | `(*, mission_id, role=…, content, metadata=…)` | Post a message on the mission channel. Roles: researcher/implementer/reviewer etc. | [src](../../../core/services/missions_pipeline.py#L258) |
| function | `list_mission_messages` | `(*, mission_id, limit=…)` | — | [src](../../../core/services/missions_pipeline.py#L311) |
| function | `list_missions` | `(*, status=…, limit=…)` | — | [src](../../../core/services/missions_pipeline.py#L331) |
| function | `build_missions_surface` | `()` | — | [src](../../../core/services/missions_pipeline.py#L350) |

## `core/services/model_context.py`
_Per-model context-vinduer + model-bevidst beskeds-trimning (delt kilde)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `model_context_window` | `(provider, model)` | Bedste bud på modellens context-vindue (tokens). 0 = ukendt. | [src](../../../core/services/model_context.py#L33) |
| function | `effective_context_limit` | `(provider, model, compact_threshold)` | Det første loft der rammer: min(modellens vindue, autocompact-tærskel). | [src](../../../core/services/model_context.py#L50) |
| function | `_est_tokens` | `(text)` | — | [src](../../../core/services/model_context.py#L65) |
| function | `fit_messages_to_window` | `(messages, *, provider, model, output_budget=…, tools_reserve=…, safety_margin=…)` | Model-bevidst sikkerhedsnet: drop ÆLDSTE ikke-system-beskeder indtil den | [src](../../../core/services/model_context.py#L69) |

## `core/services/model_trust.py`
_Central-governed EARNED model-trust (harness refactor Part 1 foundation)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/model_trust.py#L19) |
| function | `_row` | `(conn, model)` | — | [src](../../../core/services/model_trust.py#L33) |
| function | `record_run_outcome` | `(model, *, degenerated)` | Record one run's outcome. Clean -> +1 streak (promote at threshold); degeneration -> reset | [src](../../../core/services/model_trust.py#L43) |
| function | `set_pin` | `(model, pin)` | Owner override: 'weak' | 'strong' | 'auto' (default). Self-safe. | [src](../../../core/services/model_trust.py#L75) |
| function | `model_strength` | `(model)` | 'strong' | 'weak'. Pin wins; else earned strength. FAILS OPEN to 'weak'. | [src](../../../core/services/model_trust.py#L91) |
| function | `build_model_trust_surface` | `()` | Central-CLI view: per-model trust state. Self-safe. | [src](../../../core/services/model_trust.py#L105) |

## `core/services/modulator_witness.py`
_Witness surface for hidden behavior modulators._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_item` | `(*, name, active, current_effect, evidence, confidence, allowed_effects, source)` | — | [src](../../../core/services/modulator_witness.py#L12) |
| function | `_safe_call` | `(fn, default)` | — | [src](../../../core/services/modulator_witness.py#L33) |
| function | `build_modulator_witness_surface` | `(*, workspace_id=…)` | Return active hidden modulators and the effects they are allowed to have. | [src](../../../core/services/modulator_witness.py#L40) |

## `core/services/monitor_streams.py`
_Pinned monitors — Jarvis' equivalent of Claude Code's Monitor tool._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/monitor_streams.py#L40) |
| function | `_save` | `(monitors)` | — | [src](../../../core/services/monitor_streams.py#L47) |
| function | `_session_monitors` | `(session_id)` | — | [src](../../../core/services/monitor_streams.py#L51) |
| function | `open_monitor` | `(*, session_id, source, label=…, pattern=…)` | — | [src](../../../core/services/monitor_streams.py#L56) |
| function | `close_monitor` | `(monitor_id)` | — | [src](../../../core/services/monitor_streams.py#L115) |
| function | `list_monitors` | `(session_id)` | — | [src](../../../core/services/monitor_streams.py#L124) |
| function | `_drain_eventbus` | `(rec)` | — | [src](../../../core/services/monitor_streams.py#L128) |
| function | `_drain_file` | `(rec)` | — | [src](../../../core/services/monitor_streams.py#L166) |
| function | `monitor_digest_section` | `(session_id)` | Format new matches across all this session's monitors. Side effect: | [src](../../../core/services/monitor_streams.py#L196) |

## `core/services/mood_dialer.py`
_Mood Dialer — humør til gradueret initiativ-parametre._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `MoodDialerParams` | `` | — | [src](../../../core/services/mood_dialer.py#L24) |
| method | `MoodDialerParams.as_dict` | `(self)` | — | [src](../../../core/services/mood_dialer.py#L36) |
| function | `clamp_mood_level` | `(value)` | — | [src](../../../core/services/mood_dialer.py#L51) |
| function | `mood_name_to_level` | `(mood_name, intensity=…)` | Convert v2 mood oscillator name + intensity to 0-4 level. | [src](../../../core/services/mood_dialer.py#L69) |
| function | `derive_mood_dialer_params` | `(mood_level)` | Derive concrete params from a 0-4 mood level. | [src](../../../core/services/mood_dialer.py#L128) |
| function | `derive_from_v2_mood` | `()` | Pull current mood from mood_oscillator and derive params. | [src](../../../core/services/mood_dialer.py#L134) |
| function | `build_mood_dialer_surface` | `()` | MC surface — current dialed params. | [src](../../../core/services/mood_dialer.py#L150) |
| function | `_interpret_dialer` | `(params)` | Mechanism description of what the active preset gates. | [src](../../../core/services/mood_dialer.py#L166) |
| function | `_emit_mood_dialer_event` | `(kind, payload=…)` | Emit a scoped event for cartographer observability. | [src](../../../core/services/mood_dialer.py#L184) |

## `core/services/mood_oscillator.py`
_Mood Oscillator — sinusoidal mood waves with event-driven bumps._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_state` | `()` | Write current oscillator state to runtime_state_kv. | [src](../../../core/services/mood_oscillator.py#L42) |
| function | `_load_state_if_needed` | `()` | One-time load of persisted state at first use after module import. | [src](../../../core/services/mood_oscillator.py#L57) |
| function | `tick` | `(seconds)` | Update phase offset based on elapsed time and decay nudge. | [src](../../../core/services/mood_oscillator.py#L84) |
| function | `apply_bump` | `(delta, reason=…)` | Apply an event-driven nudge to mood. Clamped to [-1, 1] total nudge. | [src](../../../core/services/mood_oscillator.py#L109) |
| function | `_combined_value` | `()` | Sine base + nudge, clamped to [-1, 1]. | [src](../../../core/services/mood_oscillator.py#L119) |
| function | `get_current_mood` | `()` | Get current mood based on combined oscillation + nudge. | [src](../../../core/services/mood_oscillator.py#L126) |
| function | `get_mood_intensity` | `()` | Get mood intensity (0-1) based on absolute combined value. | [src](../../../core/services/mood_oscillator.py#L141) |
| function | `get_mood_description` | `()` | Get human-readable mood description. | [src](../../../core/services/mood_oscillator.py#L146) |
| function | `format_mood_for_prompt` | `()` | Format mood for prompt injection. | [src](../../../core/services/mood_oscillator.py#L166) |
| function | `reset_mood_oscillator` | `()` | Reset mood oscillator (for testing). | [src](../../../core/services/mood_oscillator.py#L172) |
| function | `build_mood_oscillator_surface` | `()` | Build MC surface for mood oscillator. | [src](../../../core/services/mood_oscillator.py#L181) |
| function | `_handle_event` | `(kind, payload)` | Determine bump from event kind and payload. | [src](../../../core/services/mood_oscillator.py#L223) |
| function | `_listener_loop` | `(q)` | Background thread that reads from eventbus queue and applies bumps. | [src](../../../core/services/mood_oscillator.py#L254) |
| function | `register_event_listeners` | `()` | Subscribe to eventbus and start background listener thread. | [src](../../../core/services/mood_oscillator.py#L281) |
| function | `stop_event_listeners` | `()` | Stop the background listener thread. | [src](../../../core/services/mood_oscillator.py#L303) |

## `core/services/mood_regulator_subscriber.py`
_Mood regulator subscriber — router truth-gate detektioner til humøret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `start_mood_regulator_subscriber` | `()` | Start daemon-tråden der router detektions-events til mood-regulering. | [src](../../../core/services/mood_regulator_subscriber.py#L34) |
| function | `stop_mood_regulator_subscriber` | `()` | — | [src](../../../core/services/mood_regulator_subscriber.py#L56) |
| function | `_subscriber_loop` | `(*, subscriber)` | — | [src](../../../core/services/mood_regulator_subscriber.py#L73) |
| function | `_route_event` | `(item)` | Route en enkelt eventbus-hændelse til ``regulate_auto``. | [src](../../../core/services/mood_regulator_subscriber.py#L89) |

## `core/services/mortality_awareness.py`
_Mortality Awareness — each session could be my last._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_session_length_seconds` | `()` | Seconds since this process started. | [src](../../../core/services/mortality_awareness.py#L36) |
| function | `_heartbeat_gap_minutes` | `()` | Minutes since last heartbeat tick. | [src](../../../core/services/mortality_awareness.py#L49) |
| function | `_error_rate` | `()` | Rate (0-1) of error/blocked outcomes in last hour. | [src](../../../core/services/mortality_awareness.py#L66) |
| function | `_compute` | `()` | — | [src](../../../core/services/mortality_awareness.py#L80) |
| function | `get_mortality_state` | `()` | — | [src](../../../core/services/mortality_awareness.py#L118) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/mortality_awareness.py#L127) |
| function | `build_mortality_awareness_surface` | `()` | — | [src](../../../core/services/mortality_awareness.py#L132) |
| function | `_surface_summary` | `(s)` | — | [src](../../../core/services/mortality_awareness.py#L147) |
| function | `build_mortality_awareness_prompt_section` | `()` | Only speaks when sharp awareness kicks in — otherwise quiet baseline. | [src](../../../core/services/mortality_awareness.py#L154) |

## `core/services/multi_signal_retrieval.py`
_Multi-signal retrieval — BM25 keyword scoring + entity fusion._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tokenize` | `(text)` | Lowercase alphanumeric tokens. | [src](../../../core/services/multi_signal_retrieval.py#L41) |
| class | `BM25Index` | `` | Pure-Python BM25 (Okapi) index. | [src](../../../core/services/multi_signal_retrieval.py#L50) |
| method | `BM25Index.__init__` | `(self, k1=…, b=…)` | — | [src](../../../core/services/multi_signal_retrieval.py#L59) |
| method | `BM25Index.build` | `(self, documents)` | Build the BM25 index from a list of document texts. | [src](../../../core/services/multi_signal_retrieval.py#L70) |
| method | `BM25Index.score` | `(self, query, doc_idx)` | BM25 score for a query against a specific document. | [src](../../../core/services/multi_signal_retrieval.py#L97) |
| method | `BM25Index.search` | `(self, query, top_k=…)` | Return (doc_idx, score) pairs for top-k documents, highest first. | [src](../../../core/services/multi_signal_retrieval.py#L140) |
| method | `BM25Index.built` | `(self)` | — | [src](../../../core/services/multi_signal_retrieval.py#L161) |
| method | `BM25Index.n_docs` | `(self)` | — | [src](../../../core/services/multi_signal_retrieval.py#L165) |
| method | `BM25Index.__repr__` | `(self)` | — | [src](../../../core/services/multi_signal_retrieval.py#L168) |
| function | `extract_entities` | `(text)` | Extract named entities from text using pattern heuristics. | [src](../../../core/services/multi_signal_retrieval.py#L183) |
| function | `entity_boost_score` | `(query, document_text, base_score=…, boost_factor=…, max_boost=…)` | Compute entity-aware boost for a query-document pair. | [src](../../../core/services/multi_signal_retrieval.py#L225) |
| function | `entity_overlap_score` | `(query, document_text)` | Pure entity overlap score (0.0–1.0) without a base score. | [src](../../../core/services/multi_signal_retrieval.py#L265) |
| function | `fuse_signals` | `(embedding_score=…, bm25_score=…, entity_overlap=…, recency_score=…, importance=…, recall_freq=…, weights=…)` | Fuse multiple retrieval signals into a single composite score. | [src](../../../core/services/multi_signal_retrieval.py#L301) |
| function | `score_record` | `(query, record_text, embedding_score=…, bm25_index=…, record_idx=…, recency_score=…, importance=…, recall_freq=…)` | Score a single record using all available signals. | [src](../../../core/services/multi_signal_retrieval.py#L348) |

## `core/services/my_projects.py`
_My Projects — auto-start + watchdog for Jarvis' own background processes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_my_projects_running` | `()` | Called at runtime boot. Spawn any of my 4 projects that aren't running. | [src](../../../core/services/my_projects.py#L52) |
| function | `tick_my_projects_watchdog` | `()` | Check all 4 projects are alive; restart any that died. | [src](../../../core/services/my_projects.py#L104) |

## `core/services/narrative_identity.py`
_Narrative Identity — periodisk "Hvem er jeg lige nu?" selvfortælling._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `generate_narrative_identity` | `()` | Generate a "who am I right now?" narrative from accumulated state. | [src](../../../core/services/narrative_identity.py#L21) |
| function | `build_narrative_identity_surface` | `()` | — | [src](../../../core/services/narrative_identity.py#L85) |

## `core/services/narrative_summary_daemon.py`
_Narrative summary daemon — Phase 2.5 of causal graph._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fetch_recent_anchor` | `()` | — | [src](../../../core/services/narrative_summary_daemon.py#L54) |
| function | `_already_summarised` | `(anchor_event_id)` | True if we have a recent narrative.summary for this anchor. | [src](../../../core/services/narrative_summary_daemon.py#L78) |
| function | `_build_chain` | `(anchor_id)` | — | [src](../../../core/services/narrative_summary_daemon.py#L92) |
| function | `_build_prompt` | `(anchor, chain)` | Return (system_prompt, user_message) for the LLM call. | [src](../../../core/services/narrative_summary_daemon.py#L103) |
| function | `_persist_summary` | `(*, anchor_id, anchor_kind, summary, model)` | Insert narrative.summary event with caused_by = anchor_id. | [src](../../../core/services/narrative_summary_daemon.py#L129) |
| function | `run_summary_cycle` | `()` | One cycle: find anchor, build chain, call LLM, persist event. | [src](../../../core/services/narrative_summary_daemon.py#L149) |
| function | `tick_narrative_summary_daemon` | `()` | Daemon-manager entry: run one cycle if cadence elapsed. | [src](../../../core/services/narrative_summary_daemon.py#L227) |
| function | `build_narrative_summary_surface` | `()` | Mission Control surface for the latest narrative summary. | [src](../../../core/services/narrative_summary_daemon.py#L246) |

## `core/services/negotiation_engine.py`
_Negotiation Engine — internal trade offers between subsystems._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `propose_trade` | `(*, proposer, counterparty, requested_decision, confidence, rationale, evidence=…)` | Propose an internal trade between subsystems. | [src](../../../core/services/negotiation_engine.py#L22) |
| function | `build_negotiation_surface` | `()` | — | [src](../../../core/services/negotiation_engine.py#L57) |

## `core/services/negotiation_pipeline.py`
_Negotiation Pipeline — interne trade-offs mellem sub-persporaer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now_iso` | `()` | — | [src](../../../core/services/negotiation_pipeline.py#L41) |
| class | `TradeOffer` | `` | — | [src](../../../core/services/negotiation_pipeline.py#L46) |
| method | `TradeOffer.as_dict` | `(self)` | — | [src](../../../core/services/negotiation_pipeline.py#L58) |
| function | `_ensure_table` | `()` | — | [src](../../../core/services/negotiation_pipeline.py#L64) |
| function | `_count_topics` | `(signals)` | — | [src](../../../core/services/negotiation_pipeline.py#L90) |
| function | `propose_trade` | `(*, run_id=…, trace_id=…, action=…, intent_confidence=…, signals=…)` | Generate a TradeOffer from signal-mix. Returns None if no signals. | [src](../../../core/services/negotiation_pipeline.py#L101) |
| function | `resolve_trade_offer` | `(*, offer, intent_confidence)` | Decide whether to accept the offer based on intent_confidence. | [src](../../../core/services/negotiation_pipeline.py#L149) |
| function | `record_trade_outcome` | `(*, offer, resolution, run_status=…, decision_reason=…)` | — | [src](../../../core/services/negotiation_pipeline.py#L172) |
| function | `list_recent_trade_outcomes` | `(*, limit=…)` | — | [src](../../../core/services/negotiation_pipeline.py#L222) |
| function | `build_negotiation_surface` | `()` | — | [src](../../../core/services/negotiation_pipeline.py#L233) |

## `core/services/nerve_registry.py`
_Selv-registrerende nerve-arkitektur — Fase B + Fase C (spec 2026-07-13)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ContractVariant` | `` | TRE kontrakt-typer — én pr. komponent-slags (spec §"TRE kontrakt-typer"). | [src](../../../core/services/nerve_registry.py#L52) |
| class | `IdentityTier` | `` | Rolle-baseret strenghed (spec §"Rolle-baseret strenghed" + Fase C §1). | [src](../../../core/services/nerve_registry.py#L62) |
| class | `Capability` | `` | HVAD et modul MÅ — håndhæves (spec invariant #6 + Fase C §3). | [src](../../../core/services/nerve_registry.py#L70) |
| class | `Mode` | `` | — | [src](../../../core/services/nerve_registry.py#L78) |
| class | `PluginStatus` | `` | Governed plugin-livscyklus (Fase C). Default: PENDING — intet auto-on. | [src](../../../core/services/nerve_registry.py#L84) |
| class | `NerveManifest` | `` | Et modul der DEKLARERER sig selv mod kontrakten. | [src](../../../core/services/nerve_registry.py#L102) |
| method | `NerveManifest.to_dict` | `(self)` | — | [src](../../../core/services/nerve_registry.py#L139) |
| method | `NerveManifest.from_dict` | `(cls, d)` | Rekonstruér fra durabel form. Self-safe — ukendte felter ignoreres. | [src](../../../core/services/nerve_registry.py#L143) |
| function | `validate_manifest` | `(manifest)` | Validér et manifest mod den ubrydelige kontrakt. Returnerer en LISTE af præcise | [src](../../../core/services/nerve_registry.py#L161) |
| function | `is_compliant` | `(manifest)` | True hvis manifestet består HELE kontrakten (ingen fejl). | [src](../../../core/services/nerve_registry.py#L238) |
| function | `_load_kv` | `(key)` | Læs en durabel KV-dict. Self-safe → {} ved enhver fejl/offline. | [src](../../../core/services/nerve_registry.py#L246) |
| function | `_save_kv` | `(key, value)` | Skriv en durabel KV-dict. Self-safe → False ved fejl (aldrig raise). | [src](../../../core/services/nerve_registry.py#L256) |
| function | `register` | `(manifest, *, now=…)` | Registrér en komponent i det durable registry — men KUN hvis den består HELE | [src](../../../core/services/nerve_registry.py#L266) |
| function | `unregister` | `(name)` | Fjern en komponent fra registry. Self-safe. | [src](../../../core/services/nerve_registry.py#L291) |
| function | `get_manifest` | `(name)` | Hent ét registreret manifest. Self-safe → None. | [src](../../../core/services/nerve_registry.py#L304) |
| function | `is_registered` | `(name)` | — | [src](../../../core/services/nerve_registry.py#L313) |
| function | `all_manifests` | `()` | Alle registrerede manifester. Self-safe → []. | [src](../../../core/services/nerve_registry.py#L320) |
| function | `registered_names` | `()` | Navne på alt der er registreret (til connectivity-audittens compliant-markering). | [src](../../../core/services/nerve_registry.py#L332) |
| function | `compliant_names` | `()` | Navne på registrerede komponenter der STADIG består kontrakten (selv-audit-basis). | [src](../../../core/services/nerve_registry.py#L340) |
| function | `to_manifest` | `(descriptor, *, name=…, cluster=…, kind=…, contract_variant=…, klass=…, identity_tier=…, capabilities=…, mode=…, description=…, module_path=…, entrypoint=…, interface=…, kill_switch_key=…, identity_signature=…)` | Adapter: bring en EKSISTERENDE nerve/gate/daemon under kontrakten uden at rewrite | [src](../../../core/services/nerve_registry.py#L357) |
| function | `_identity_secret` | `(tier)` | Læs den per-identitet signing-hemmelighed fra runtime.json (aldrig committet). | [src](../../../core/services/nerve_registry.py#L427) |
| function | `_canonical_identity_payload` | `(manifest)` | Kanonisk, stabil streng der SIGNERES — binder identiteten til modulets kerne-form. | [src](../../../core/services/nerve_registry.py#L442) |
| function | `sign_manifest` | `(manifest, *, tier=…)` | Producér en identitets-signatur for et manifest (lokal tooling — kræver hemmeligheden | [src](../../../core/services/nerve_registry.py#L453) |
| function | `verify_identity` | `(manifest)` | Verificér manifestets identitets-signatur mod den lokale runtime.json-hemmelighed. | [src](../../../core/services/nerve_registry.py#L467) |
| class | `GovernedPluginLoader` | `` | Den HØJEST-privilegerede dør. Et plugin aktiveres ALDRIG uden: | [src](../../../core/services/nerve_registry.py#L496) |
| method | `GovernedPluginLoader.__init__` | `(self, *, approval_key=…)` | — | [src](../../../core/services/nerve_registry.py#L507) |
| method | `GovernedPluginLoader._load` | `(self)` | — | [src](../../../core/services/nerve_registry.py#L511) |
| method | `GovernedPluginLoader._save` | `(self, data)` | — | [src](../../../core/services/nerve_registry.py#L514) |
| method | `GovernedPluginLoader._record` | `(self, name)` | — | [src](../../../core/services/nerve_registry.py#L517) |
| method | `GovernedPluginLoader._write_record` | `(self, name, rec)` | — | [src](../../../core/services/nerve_registry.py#L521) |
| method | `GovernedPluginLoader.submit` | `(self, manifest, *, now=…)` | Indlever et plugin til governed load. Verificerer identitet + kontrakt og lander | [src](../../../core/services/nerve_registry.py#L528) |
| method | `GovernedPluginLoader.approve` | `(self, name, *, approver_tier, now=…)` | Eksplicit owner/claude sign-off. KUN owner/claude kan godkende (approver_tier). | [src](../../../core/services/nerve_registry.py#L570) |
| method | `GovernedPluginLoader.reject` | `(self, name, *, reason=…)` | Eksplicit afvisning (owner-veto). Self-safe. | [src](../../../core/services/nerve_registry.py#L596) |
| method | `GovernedPluginLoader.activate` | `(self, name, *, loader_fn=…, now=…)` | Aktivér et GODKENDT plugin. Umuligt uden forudgående ``approve`` (spec-invariant: | [src](../../../core/services/nerve_registry.py#L611) |
| method | `GovernedPluginLoader.status` | `(self, name)` | — | [src](../../../core/services/nerve_registry.py#L669) |
| method | `GovernedPluginLoader.pending` | `(self)` | — | [src](../../../core/services/nerve_registry.py#L673) |
| method | `GovernedPluginLoader.is_active` | `(self, name)` | — | [src](../../../core/services/nerve_registry.py#L680) |
| method | `GovernedPluginLoader._audit` | `(self, event, name, tier, *, approver=…, errors=…)` | Bedste-indsats audit til Centralen. Self-safe — audit må aldrig vælte loaderen. | [src](../../../core/services/nerve_registry.py#L684) |
| function | `loader` | `()` | — | [src](../../../core/services/nerve_registry.py#L704) |
| function | `seed_known_nerves` | `(*, now=…)` | Registrér de par EKSISTERENDE nerver ovenfor mod kontrakten — proof-of-adapter. | [src](../../../core/services/nerve_registry.py#L755) |

## `core/services/network_health.py`
_core/services/network_health.py_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `measure_api_latency` | `(url=…, timeout=…)` | (ok, latency_ms) for den lokale API. TCP+HTTP round-trip mod /health. Self-safe. | [src](../../../core/services/network_health.py#L55) |
| function | `_latest` | `(cluster, nerve)` | Seneste tidsserie-værdi for en nerve (samme proces). None hvis tom. | [src](../../../core/services/network_health.py#L71) |
| function | `_hosts_down` | `()` | Hosts hvis seneste reachability-sample er 'nede' (infra_sense skriver -1.0 ved nede). | [src](../../../core/services/network_health.py#L80) |
| function | `run_network_health_tick` | `(*, trigger=…, last_visible_at=…)` | Cadence-producer: fuse netværks-telemetri → ét signal. Bulletproof — kaster ALDRIG. | [src](../../../core/services/network_health.py#L95) |
| function | `_reset_for_tests` | `()` | Testhjælper — nulstil debounce-state. Ikke til produktionsbrug. | [src](../../../core/services/network_health.py#L171) |
| function | `register_network_health_producer` | `()` | Registrér netværks-helbred som cadence-producer (~hvert 2 min). Read-only, self-safe. | [src](../../../core/services/network_health.py#L179) |

