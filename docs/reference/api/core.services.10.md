# `core.services.10` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/creative_instinct_daemon.py`
_Creative Instinct — spontaneous idea-seeds written to INCUBATOR.md._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L39) |
| function | `_incubator_path` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L43) |
| function | `_load` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L47) |
| function | `_save` | `(data)` | — | [src](../../../core/services/creative_instinct_daemon.py#L63) |
| function | `_hours_since` | `(iso_str)` | — | [src](../../../core/services/creative_instinct_daemon.py#L75) |
| function | `_recent_chat_topics` | `(limit=…)` | — | [src](../../../core/services/creative_instinct_daemon.py#L87) |
| function | `_recent_dream_hypotheses` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L101) |
| function | `_recent_avoidances` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L111) |
| function | `_current_mood_label` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L119) |
| function | `_compose_spark` | `(source_phrases, mood)` | Combine two source phrases into a spark. | [src](../../../core/services/creative_instinct_daemon.py#L129) |
| function | `_short_phrase` | `(text)` | — | [src](../../../core/services/creative_instinct_daemon.py#L150) |
| function | `_generate_seeds` | `(*, max_new)` | — | [src](../../../core/services/creative_instinct_daemon.py#L157) |
| function | `_write_incubator_md` | `(seeds)` | Overwrite INCUBATOR.md with current active seed list. | [src](../../../core/services/creative_instinct_daemon.py#L194) |
| function | `_age_seeds` | `(seeds)` | Mature or wither seeds based on age. Returns True if any changed. | [src](../../../core/services/creative_instinct_daemon.py#L224) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/creative_instinct_daemon.py#L242) |
| function | `list_seeds` | `(*, status=…)` | — | [src](../../../core/services/creative_instinct_daemon.py#L273) |
| function | `mark_seed` | `(seed_id, *, status)` | — | [src](../../../core/services/creative_instinct_daemon.py#L280) |
| function | `build_creative_instinct_surface` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L295) |
| function | `_surface_summary` | `(active, adopted, withered)` | — | [src](../../../core/services/creative_instinct_daemon.py#L325) |
| function | `build_creative_instinct_prompt_section` | `()` | — | [src](../../../core/services/creative_instinct_daemon.py#L342) |

## `core/services/creative_journal_runtime.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `run_creative_journal_cycle` | `(*, trigger=…, last_visible_at=…)` | — | [src](../../../core/services/creative_journal_runtime.py#L23) |
| function | `build_creative_journal_surface` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L125) |
| function | `creative_journal_dir` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L144) |
| function | `list_creative_journal_entries` | `(*, limit=…)` | — | [src](../../../core/services/creative_journal_runtime.py#L149) |
| function | `_build_journal_entry` | `(*, chronicle_entries, life_projects, broken_decisions, klangbraet, voice_anchor)` | — | [src](../../../core/services/creative_journal_runtime.py#L178) |
| function | `_build_prompt` | `(*, chronicle_entries, life_projects, broken_decisions, klangbraet, voice_anchor)` | — | [src](../../../core/services/creative_journal_runtime.py#L210) |
| function | `_sanitize_entry` | `(raw)` | — | [src](../../../core/services/creative_journal_runtime.py#L318) |
| function | `_write_journal_entry` | `(*, created_at, text, frontmatter=…)` | — | [src](../../../core/services/creative_journal_runtime.py#L330) |
| function | `_should_skip_week` | `(*, chronicle_count, broken_decisions_count, life_projects_count)` | Return (skip?, reason). Skip when ALL three signals are absent/thin. | [src](../../../core/services/creative_journal_runtime.py#L360) |
| function | `_interval_days_for_state` | `(state)` | Return current cadence interval based on skip counter. | [src](../../../core/services/creative_journal_runtime.py#L378) |
| function | `_fetch_broken_decisions` | `(*, days_back=…, limit=…)` | Pull recent broken-decision summaries from the events table. | [src](../../../core/services/creative_journal_runtime.py#L388) |
| function | `_fetch_recent_top_motif` | `(*, days_back=…)` | Return the most-recent aesthetic motif from the last `days_back` days. | [src](../../../core/services/creative_journal_runtime.py#L440) |
| function | `_fetch_dominant_taste` | `(*, evidence_floor=…)` | Return 'dimension_name (value)' for the taste-dimension with largest |val - 0.5|. | [src](../../../core/services/creative_journal_runtime.py#L467) |
| function | `_fetch_affective_klangbraet` | `()` | Pull current affective signals — these shape tone, not content. | [src](../../../core/services/creative_journal_runtime.py#L512) |
| function | `_format_yaml_frontmatter` | `(*, created_at, chronicle_count, broken_decisions_count, life_projects_count, klangbraet, trigger)` | Render a YAML frontmatter block for journal entries. | [src](../../../core/services/creative_journal_runtime.py#L613) |
| function | `_quality_lane_enabled` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L662) |
| function | `_creative_journal_enabled` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L669) |
| function | `_state` | `()` | — | [src](../../../core/services/creative_journal_runtime.py#L674) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/creative_journal_runtime.py#L679) |

## `core/services/creative_projects.py`
_Creative Projects — multi-week persistent creative impulse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/creative_projects.py#L36) |
| function | `_load` | `()` | — | [src](../../../core/services/creative_projects.py#L40) |
| function | `_save` | `(data)` | — | [src](../../../core/services/creative_projects.py#L54) |
| function | `create_project` | `(*, title, intent, status=…)` | Create a new creative project. | [src](../../../core/services/creative_projects.py#L66) |
| function | `add_progress_note` | `(project_id, note)` | Append a progress note to a project. Updates updated_at. | [src](../../../core/services/creative_projects.py#L86) |
| function | `set_project_status` | `(project_id, status)` | — | [src](../../../core/services/creative_projects.py#L101) |
| function | `list_projects` | `(*, status=…)` | — | [src](../../../core/services/creative_projects.py#L115) |
| function | `get_project` | `(project_id)` | — | [src](../../../core/services/creative_projects.py#L123) |
| function | `_is_stale` | `(project)` | — | [src](../../../core/services/creative_projects.py#L130) |
| function | `build_creative_projects_surface` | `()` | — | [src](../../../core/services/creative_projects.py#L140) |
| function | `_surface_summary` | `(active, paused, dreaming, stale)` | — | [src](../../../core/services/creative_projects.py#L169) |
| function | `build_creative_projects_prompt_section` | `()` | Surface active/dreaming projects so he can resume or carry them. | [src](../../../core/services/creative_projects.py#L189) |

## `core/services/crisis_marker_detector.py`
_Crisis marker detector — flag identity-forming friction moments._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_detect_sustained_failure` | `(events)` | ≥5 consecutive errors of the same tool. | [src](../../../core/services/crisis_marker_detector.py#L43) |
| function | `_detect_unexpected_success` | `(events)` | Tick quality summary that jumped sharply. | [src](../../../core/services/crisis_marker_detector.py#L74) |
| function | `_detect_existential_moment` | `(events)` | Explicit identity-formation statements in recent messages. | [src](../../../core/services/crisis_marker_detector.py#L95) |
| function | `_detect_high_volatility` | `(events)` | Rapid mood shifts in recent personality snapshots. | [src](../../../core/services/crisis_marker_detector.py#L157) |
| function | `_recent_events` | `(hours=…)` | — | [src](../../../core/services/crisis_marker_detector.py#L196) |
| function | `scan_for_crisis_markers` | `()` | Run all detectors. Persist any new markers found. | [src](../../../core/services/crisis_marker_detector.py#L206) |
| function | `list_crisis_markers` | `(*, days_back=…, limit=…)` | — | [src](../../../core/services/crisis_marker_detector.py#L270) |
| function | `crisis_marker_section` | `()` | Awareness section showing recent crisis markers (last 7 days). | [src](../../../core/services/crisis_marker_detector.py#L283) |
| function | `_exec_scan_crisis_markers` | `(args)` | — | [src](../../../core/services/crisis_marker_detector.py#L301) |
| function | `_exec_list_crisis_markers` | `(args)` | — | [src](../../../core/services/crisis_marker_detector.py#L305) |

## `core/services/cross_agent_memory.py`
_Cross-agent memory — shared observations queryable across agents._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_all_observations` | `()` | Read full observation log from Layer 1 storage. | [src](../../../core/services/cross_agent_memory.py#L37) |
| function | `_filter_by_freshness` | `(records, days)` | — | [src](../../../core/services/cross_agent_memory.py#L49) |
| function | `_keyword_score` | `(text, query)` | Cheap relevance score: count of query keywords in text, normalised. | [src](../../../core/services/cross_agent_memory.py#L56) |
| function | `cross_agent_recall` | `(*, query, requesting_role=…, exclude_roles=…, days_back=…, limit=…, min_score=…)` | Find relevant observations from OTHER agents matching the query. | [src](../../../core/services/cross_agent_memory.py#L68) |
| function | `cross_agent_recall_section` | `(role, query)` | Format cross-agent recall as text for sub-agent system_prompt injection. | [src](../../../core/services/cross_agent_memory.py#L130) |
| function | `_exec_cross_agent_recall` | `(args)` | — | [src](../../../core/services/cross_agent_memory.py#L146) |

## `core/services/cross_session_gate.py`
_Kontekst fra ANDRE sessioner — Fase 10, kriterium 1._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `gaeldende_niveau` | `()` | `full` | `summary` | `none` | `ubestemt` for den kørsel vi er i nu. | [src](../../../core/services/cross_session_gate.py#L76) |
| class | `Afgraenset` | `` | Det der slipper igennem — og hele regnskabet for det der ikke gjorde. | [src](../../../core/services/cross_session_gate.py#L118) |
| method | `Afgraenset.herkomst` | `(self)` | Én linje modellen kan læse, med alt kriteriet kræver. | [src](../../../core/services/cross_session_gate.py#L136) |
| function | `_digest` | `(poster)` | — | [src](../../../core/services/cross_session_gate.py#L159) |
| function | `afgraens` | `(poster, *, kilde, maks_antal=…, maks_tegn=…, niveau=…, fundet_i_alt=…)` | Anvend niveau og budgetter, og før regnskab over alt der røg. | [src](../../../core/services/cross_session_gate.py#L167) |

## `core/services/cross_session_threads.py`
_Cross-Session Threads — sustained thought lines across sessions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/cross_session_threads.py#L26) |
| function | `_load` | `()` | — | [src](../../../core/services/cross_session_threads.py#L31) |
| function | `_save` | `(items)` | — | [src](../../../core/services/cross_session_threads.py#L45) |
| function | `create_thread` | `(*, topic, synopsis=…, status=…, opened_in_session=…)` | — | [src](../../../core/services/cross_session_threads.py#L57) |
| function | `pause_thread` | `(thread_id, *, note=…)` | — | [src](../../../core/services/cross_session_threads.py#L83) |
| function | `resume_thread` | `(thread_id, *, new_synopsis=…)` | — | [src](../../../core/services/cross_session_threads.py#L96) |
| function | `close_thread` | `(thread_id, *, reason=…)` | — | [src](../../../core/services/cross_session_threads.py#L112) |
| function | `update_synopsis` | `(thread_id, new_synopsis)` | — | [src](../../../core/services/cross_session_threads.py#L125) |
| function | `list_threads` | `(*, status=…)` | — | [src](../../../core/services/cross_session_threads.py#L136) |
| function | `get_thread` | `(thread_id)` | — | [src](../../../core/services/cross_session_threads.py#L143) |
| function | `build_cross_session_threads_surface` | `()` | — | [src](../../../core/services/cross_session_threads.py#L150) |
| function | `_surface_summary` | `(counts)` | — | [src](../../../core/services/cross_session_threads.py#L189) |
| function | `build_cross_session_threads_prompt_section` | `()` | Surface active + paused threads so Jarvis can resume them. | [src](../../../core/services/cross_session_threads.py#L202) |

## `core/services/cross_signal_analysis.py`
_Cross-Signal Analysis — find patterns across cognitive signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `analyze_signal_patterns` | `(*, limit_items=…)` | Find cross-signal patterns from accumulated cognitive data. | [src](../../../core/services/cross_signal_analysis.py#L20) |
| function | `build_cross_signal_analysis_surface` | `()` | — | [src](../../../core/services/cross_signal_analysis.py#L84) |

## `core/services/cross_user_share_guard.py`
_Altid-aktiv deling-guard — stopper Jarvis før han deler info om en ANDEN bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_outbound` | `(text, *, current_user_id, known_users, session_id=…)` | Tjek et udgående svar for omtale af andre brugere end samtalepartneren. | [src](../../../core/services/cross_user_share_guard.py#L25) |
| function | `check_against_registry` | `(text, *, current_user_id)` | Som check_outbound, men henter kendte brugere fra users-registry. | [src](../../../core/services/cross_user_share_guard.py#L68) |

## `core/services/curiosity_budget.py`
_Curiosity-budget service — Phase 1 (AGI track #6 Åben udforskning)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | Idempotently create curiosity_observations table + indexes. | [src](../../../core/services/curiosity_budget.py#L32) |
| function | `_today_iso` | `()` | — | [src](../../../core/services/curiosity_budget.py#L71) |
| function | `load_or_reset_budget` | `()` | Return current budget state. Resets to 5/5 if stored date != today. | [src](../../../core/services/curiosity_budget.py#L75) |
| function | `decrement_budget` | `(*, action, observation_id)` | Reduce remaining by 1, append to used_today, persist. | [src](../../../core/services/curiosity_budget.py#L92) |
| function | `remaining_today` | `()` | — | [src](../../../core/services/curiosity_budget.py#L121) |
| function | `record_observation` | `(action, args_json, observation_text, follow_up_hint)` | Persist an observation row; return the generated obs_id. | [src](../../../core/services/curiosity_budget.py#L129) |
| function | `fetch_recent_observations` | `(*, limit=…)` | Return newest-first list of recent observations (for awareness). | [src](../../../core/services/curiosity_budget.py#L156) |
| function | `_safe_publish` | `(family_event, payload)` | — | [src](../../../core/services/curiosity_budget.py#L173) |
| function | `curiosity_enabled` | `()` | Read killswitch from settings. Fail-open: settings errors → True. | [src](../../../core/services/curiosity_budget.py#L185) |
| function | `idle_window_open` | `()` | — | [src](../../../core/services/curiosity_budget.py#L197) |
| function | `open_idle_window` | `()` | Mark window open IF there's still budget. No-op if budget exhausted. | [src](../../../core/services/curiosity_budget.py#L202) |
| function | `close_idle_window` | `(*, reason)` | Close the window. Reason is logged for diagnostics. | [src](../../../core/services/curiosity_budget.py#L212) |
| function | `format_curiosity_window_for_awareness` | `()` | Render the curiosity window text for prompt_contract injection. | [src](../../../core/services/curiosity_budget.py#L225) |

## `core/services/curiosity_consolidation.py`
_Curiosity-observations weekly consolidation._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `ensure_schema` | `()` | — | [src](../../../core/services/curiosity_consolidation.py#L27) |
| function | `_fetch_observations` | `(since, until)` | — | [src](../../../core/services/curiosity_consolidation.py#L51) |
| function | `_build_prompt` | `(observations)` | — | [src](../../../core/services/curiosity_consolidation.py#L66) |
| function | `run_consolidation` | `(*, now=…)` | Build a consolidation note from last 7d observations. | [src](../../../core/services/curiosity_consolidation.py#L83) |
| function | `latest_consolidation_for_awareness` | `()` | Awareness section showing the most recent consolidation (≤7d old). | [src](../../../core/services/curiosity_consolidation.py#L127) |

## `core/services/curiosity_daemon.py`
_Curiosity daemon — detects gaps in Jarvis' thought stream and generates curiosity signals._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_open_questions` | `()` | — | [src](../../../core/services/curiosity_daemon.py#L22) |
| function | `tick_curiosity_daemon` | `(fragments)` | Scan thought stream fragments for gaps. fragments: recent fragment buffer (latest first). | [src](../../../core/services/curiosity_daemon.py#L36) |
| function | `_detect_gap` | `(fragments)` | — | [src](../../../core/services/curiosity_daemon.py#L58) |
| function | `_generate_curiosity_signal` | `(topic, gap_type)` | Compose a short curiosity-signal label from the detected gap. | [src](../../../core/services/curiosity_daemon.py#L68) |
| function | `_curiosity_cue` | `(*, topic, gap_type)` | — | [src](../../../core/services/curiosity_daemon.py#L82) |
| function | `_store_curiosity` | `(signal)` | — | [src](../../../core/services/curiosity_daemon.py#L99) |
| function | `get_latest_curiosity` | `()` | — | [src](../../../core/services/curiosity_daemon.py#L132) |
| function | `build_curiosity_surface` | `()` | — | [src](../../../core/services/curiosity_daemon.py#L136) |

## `core/services/curiosity_hypothesis_debt.py`
_Active curiosity with hypothesis debt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `register_hypothesis_debt` | `(*, hypothesis, why_it_matters, resolving_observation, source=…, priority=…)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L16) |
| function | `maybe_register_from_text` | `(*, text, source=…)` | Registrér en aaben hypotese hvis teksten rummer en. | [src](../../../core/services/curiosity_hypothesis_debt.py#L64) |
| function | `build_curiosity_debt_surface` | `(*, limit=…)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L100) |
| function | `build_curiosity_debt_prompt_section` | `()` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L113) |
| function | `_load` | `()` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L124) |
| function | `_save` | `(state)` | — | [src](../../../core/services/curiosity_hypothesis_debt.py#L129) |

## `core/services/current_pull.py`
_Current pull — Jarvis' weekly self-set desire field._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_current_pull_daemon` | `()` | Weekly daemon tick. Generates a new pull if none active, expired, or stale. | [src](../../../core/services/current_pull.py#L44) |
| function | `_collect_appetite_texts` | `(*, days_back)` | Pull active appetite labels for landscape embedding. | [src](../../../core/services/current_pull.py#L142) |
| function | `_collect_chronicle_texts` | `(*, days_back)` | Pull chronicle narratives from the last `days_back` days. | [src](../../../core/services/current_pull.py#L163) |
| function | `_collect_journal_texts` | `(*, days_back)` | Pull journal entry bodies from the last `days_back` days. | [src](../../../core/services/current_pull.py#L191) |
| function | `_compute_landscape_embedding` | `()` | Build a mean-pooled embedding from the last 3 days of desire signals. | [src](../../../core/services/current_pull.py#L236) |
| function | `_pull_is_stale` | `(pull_text)` | Return (is_stale, cos_score). | [src](../../../core/services/current_pull.py#L264) |
| function | `_staleness_check_enabled` | `()` | — | [src](../../../core/services/current_pull.py#L291) |
| function | `_should_run_staleness_check` | `(state, *, interval_hours)` | Throttle: only run the embedding check every `interval_hours`. | [src](../../../core/services/current_pull.py#L298) |
| function | `_archive_refresh_event` | `(*, state, refreshed_at, reason, stale_score, previous_pull)` | Append a refresh event to state['refresh_history'], capped at 5 (FIFO). | [src](../../../core/services/current_pull.py#L312) |
| function | `get_current_pull_for_prompt` | `()` | Return prompt fragment for visible chat injection — or empty string. | [src](../../../core/services/current_pull.py#L333) |
| function | `build_current_pull_surface` | `()` | — | [src](../../../core/services/current_pull.py#L360) |
| function | `_generate_pull` | `()` | Ask Jarvis what pulls at him right now. Returns one Danish sentence. | [src](../../../core/services/current_pull.py#L386) |
| function | `_sanitize` | `(raw)` | — | [src](../../../core/services/current_pull.py#L431) |
| function | `_expire_if_stale` | `()` | — | [src](../../../core/services/current_pull.py#L438) |
| function | `_load_state` | `()` | — | [src](../../../core/services/current_pull.py#L459) |
| function | `_enabled` | `()` | — | [src](../../../core/services/current_pull.py#L464) |

## `core/services/daemon_health.py`
_Daemon-helbred (Fase 1) — gør de standalone daemon-tråde + silent eventbus-listeners_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `note_error` | `(daemon, error, **data)` | En daemon/listener fejlede. → observe (cluster=system, nerve=daemon_health, ok=False). | [src](../../../core/services/daemon_health.py#L17) |
| function | `note_tick` | `(daemon, *, ok=…, **data)` | En daemon kørte en cyklus. Valgfri helbreds-puls (brug sparsomt — fejl er hovedsignalet). | [src](../../../core/services/daemon_health.py#L30) |
| function | `daemon_health_summary` | `(*, window=…)` | Read-only: hvilke daemons har fejlet i seneste trace (til MC/debug). Self-safe. | [src](../../../core/services/daemon_health.py#L42) |

## `core/services/daemon_llm.py`
_Shared LLM call for daemons — cheap lane first, heartbeat model fallback._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_note_call` | `(daemon_name, hit)` | Registrér ét daemon_llm-kald + om det ramte cachen → central_timeseries. Self-safe. | [src](../../../core/services/daemon_llm.py#L25) |
| function | `daemon_llm_cache_snapshot` | `()` | Read-only: pr. daemon kald + cache-hits + hit-rate. Lav hit-rate + højt kald = | [src](../../../core/services/daemon_llm.py#L58) |
| function | `_get_cache_ttl` | `(daemon_name)` | Return TTL in seconds for a daemon. 0 means no caching. | [src](../../../core/services/daemon_llm.py#L99) |
| function | `_check_cache` | `(cache_key)` | Return cached response if present and not expired, else None. | [src](../../../core/services/daemon_llm.py#L104) |
| function | `_store_cache` | `(cache_key, text, daemon_name)` | Store response in cache with daemon-specific TTL. | [src](../../../core/services/daemon_llm.py#L116) |
| function | `daemon_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call LLM for daemon output. Tries cache first, then cheap lane (Groq), | [src](../../../core/services/daemon_llm.py#L129) |
| function | `tegn_for_tokens` | `(tokens)` | Oversaet et token-budget til den TEGN-graense `max_len` klipper paa. | [src](../../../core/services/daemon_llm.py#L166) |
| function | `quality_daemon_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call path for QUALITY-CRITICAL daemons (self-review, decision-review, | [src](../../../core/services/daemon_llm.py#L184) |
| function | `daemon_public_safe_llm_call` | `(prompt, *, max_len=…, fallback=…, daemon_name=…)` | Call path reserved for PUBLIC-SAFE prompts. | [src](../../../core/services/daemon_llm.py#L300) |
| function | `_daemon_llm_call_impl` | `(prompt, *, max_len, fallback, daemon_name, public_safe)` | — | [src](../../../core/services/daemon_llm.py#L322) |

## `core/services/daemon_manager.py`
_Daemon Manager — registry, lifecycle control, and state persistence for all daemons._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_file` | `()` | — | [src](../../../core/services/daemon_manager.py#L20) |
| function | `get_daemon_names` | `()` | — | [src](../../../core/services/daemon_manager.py#L793) |
| function | `_load_state` | `()` | — | [src](../../../core/services/daemon_manager.py#L797) |
| function | `_save_state` | `(state)` | — | [src](../../../core/services/daemon_manager.py#L807) |
| function | `_get_daemon_state` | `(name)` | — | [src](../../../core/services/daemon_manager.py#L813) |
| function | `_set_daemon_state` | `(name, updates)` | — | [src](../../../core/services/daemon_manager.py#L817) |
| function | `_require_known` | `(name)` | — | [src](../../../core/services/daemon_manager.py#L825) |
| function | `is_enabled` | `(name)` | Return True if the named daemon should run. Unknown daemons return True (safe default). | [src](../../../core/services/daemon_manager.py#L831) |
| function | `set_daemon_enabled` | `(name, enabled)` | — | [src](../../../core/services/daemon_manager.py#L840) |
| function | `get_effective_cadence` | `(name)` | Return interval in minutes: override if set, else default. | [src](../../../core/services/daemon_manager.py#L845) |
| function | `_tick_resume` | `(result)` | Et resumé der kan svare på om et medlem kørte. | [src](../../../core/services/daemon_manager.py#L865) |
| function | `record_daemon_tick` | `(name, result)` | Record last_run_at and a summary of the tick result. Called by heartbeat_runtime. | [src](../../../core/services/daemon_manager.py#L907) |
| function | `_hours_since` | `(iso)` | — | [src](../../../core/services/daemon_manager.py#L916) |
| function | `get_all_daemon_states` | `()` | Return status for all registered daemons. | [src](../../../core/services/daemon_manager.py#L928) |
| function | `control_daemon` | `(name, action, *, interval_minutes=…)` | Control a daemon. Actions: enable, disable, restart, set_interval. | [src](../../../core/services/daemon_manager.py#L951) |
| function | `_restart_daemon` | `(name)` | Clear the module-level state variable so the daemon fires on next heartbeat tick. | [src](../../../core/services/daemon_manager.py#L982) |

## `core/services/daemon_memory_safeguard.py`
_Daemon memory safeguard — post-hoc check that Jarvis saved what mattered._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `build_memory_safeguard_surface` | `()` | Mission Control surface for the memory safeguard daemon. | [src](../../../core/services/daemon_memory_safeguard.py#L41) |
| function | `run` | `(**kwargs)` | Check last assistant turn for missed saves. Called by heartbeat. | [src](../../../core/services/daemon_memory_safeguard.py#L101) |

## `core/services/daily_journal.py`
_Daily journal synthesizer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_connect` | `()` | — | [src](../../../core/services/daily_journal.py#L50) |
| function | `_journal_path_for` | `(day)` | — | [src](../../../core/services/daily_journal.py#L57) |
| function | `journal_exists_for` | `(day)` | Findes der allerede en journal for denne dato? | [src](../../../core/services/daily_journal.py#L62) |
| function | `_fetch_chat_pairs_for_day` | `(day, limit=…)` | Hent user/assistant beskeder fra visible-chat sessions for denne dag. | [src](../../../core/services/daily_journal.py#L67) |
| function | `_fetch_brain_carries_for_day` | `(day, limit=…)` | Hent private_brain_records carry-snapshots fra dagen. | [src](../../../core/services/daily_journal.py#L99) |
| function | `_render_chat_excerpt` | `(pairs)` | — | [src](../../../core/services/daily_journal.py#L160) |
| function | `_render_brain_excerpt` | `(carries)` | — | [src](../../../core/services/daily_journal.py#L170) |
| function | `synthesize_daily_journal` | `(day=…, *, force=…)` | Generér og skriv dagens journal. | [src](../../../core/services/daily_journal.py#L182) |
| function | `_should_synthesize_now` | `(now=…)` | Returnér True hvis vi er i sengetids-vinduet og dagens journal mangler. | [src](../../../core/services/daily_journal.py#L252) |
| function | `_daemon_loop` | `()` | Wakes hver time, syntesizer dagens journal hvis vi er i vinduet. | [src](../../../core/services/daily_journal.py#L262) |
| function | `start_daily_journal_daemon` | `()` | Start daemon. Idempotent. | [src](../../../core/services/daily_journal.py#L281) |
| function | `stop_daily_journal_daemon` | `()` | — | [src](../../../core/services/daily_journal.py#L298) |

## `core/services/data_erasure.py`
_GDPR Art. 17 (ret til at blive glemt) — orkestrering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_id_tables` | `(conn)` | Tabeller der HAR en user_id-kolonne (minus beskyttede). Eksplicit opdaget, | [src](../../../core/services/data_erasure.py#L23) |
| function | `_sweep_user_tables` | `(user_id, *, connect=…)` | — | [src](../../../core/services/data_erasure.py#L38) |
| function | `_wipe_workspace` | `(user_id)` | Slet brugerens workspace-mappe — med STRAM sti-sikkerhed (kun en undermappe | [src](../../../core/services/data_erasure.py#L49) |
| function | `erase_user` | `(user_id, *, mode=…, actor=…, connect=…)` | Slet en brugers data. mode='soft' (reversibel) | 'hard' (permanent). | [src](../../../core/services/data_erasure.py#L63) |

## `core/services/day_shape_memory.py`
_Day Shape Memory — sensory depth over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/day_shape_memory.py#L31) |
| function | `_load` | `()` | — | [src](../../../core/services/day_shape_memory.py#L36) |
| function | `_save` | `(data)` | — | [src](../../../core/services/day_shape_memory.py#L54) |
| function | `_today_iso` | `()` | — | [src](../../../core/services/day_shape_memory.py#L66) |
| function | `_empty_day` | `(date_iso)` | — | [src](../../../core/services/day_shape_memory.py#L70) |
| function | `capture_sample` | `()` | Add one sample to today's accumulating shape. | [src](../../../core/services/day_shape_memory.py#L82) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — capture one shape sample per tick. | [src](../../../core/services/day_shape_memory.py#L165) |
| function | `_finalize_day` | `(day)` | Collapse raw sample arrays into summary stats for storage. | [src](../../../core/services/day_shape_memory.py#L170) |
| function | `_compute_today_shape` | `()` | — | [src](../../../core/services/day_shape_memory.py#L188) |
| function | `_median_historical_shape` | `(days)` | — | [src](../../../core/services/day_shape_memory.py#L196) |
| function | `detect_today_anomaly` | `()` | Compare today's running shape to recent-days median. | [src](../../../core/services/day_shape_memory.py#L215) |
| function | `build_day_shape_surface` | `()` | — | [src](../../../core/services/day_shape_memory.py#L261) |
| function | `_surface_summary` | `(current, history, anomaly)` | — | [src](../../../core/services/day_shape_memory.py#L277) |
| function | `build_day_shape_prompt_section` | `()` | Surfaces only when today differs noticeably from baseline. | [src](../../../core/services/day_shape_memory.py#L292) |

## `core/services/db_sentinel.py`
_DB-cluster — observabilitet + flag for jarvis.db's helbred. IKKE en blokerende gate og_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_list_tables` | `()` | — | [src](../../../core/services/db_sentinel.py#L27) |
| function | `census` | `()` | Row-count pr. tabel. Best-effort; en fejlende tabel udelades. | [src](../../../core/services/db_sentinel.py#L40) |
| function | `dead_table_candidates` | `()` | Tabeller med 0 rækker = KANDIDATER til oprydning. KUN til menneskelig review — | [src](../../../core/services/db_sentinel.py#L57) |
| function | `_load_prev` | `()` | — | [src](../../../core/services/db_sentinel.py#L64) |
| function | `_save` | `(c)` | — | [src](../../../core/services/db_sentinel.py#L73) |
| function | `scan` | `()` | Census + vækst-delta vs forrige snapshot + flag egregious vækst. Returnér rapport. | [src](../../../core/services/db_sentinel.py#L81) |
| function | `observe` | `()` | Kør scan + central.observe(summary) + flag egregious vækst som incident (review). | [src](../../../core/services/db_sentinel.py#L105) |
| function | `build_db_health_surface` | `()` | MC-surface — read-only meta-projektion af DB-helbred + kandidat-død-liste til review. | [src](../../../core/services/db_sentinel.py#L131) |

## `core/services/decision_action_gate.py`
_Current-turn opportunities for three low-adherence behavioral decisions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_turn_text` | `(user_message)` | Discard the transport's attachment instructions before classifying words. | [src](../../../core/services/decision_action_gate.py#L59) |
| function | `_correction_excerpt` | `(user_message)` | Use the challenged claim, not a long paste's unrelated opening words. | [src](../../../core/services/decision_action_gate.py#L67) |
| function | `opportunities` | `(user_message)` | Return only triggers with a concrete observable opportunity. | [src](../../../core/services/decision_action_gate.py#L77) |
| function | `query_current_memory` | `(user_message, session_id)` | Read current-turn memory; the caller gives this a bounded future. | [src](../../../core/services/decision_action_gate.py#L98) |
| function | `action_section` | `(user_message, *, recall_text)` | A short volatile prompt tail, immediately before the current answer. | [src](../../../core/services/decision_action_gate.py#L108) |
| function | `evaluate_turn` | `(*, user_message, answer_text, memory_recalled, tool_names)` | Count proven actions; absence of proof stays unconfirmed. | [src](../../../core/services/decision_action_gate.py#L131) |
| function | `_ensure_table` | `(conn)` | — | [src](../../../core/services/decision_action_gate.py#L154) |
| function | `record_opportunities` | `(run_id, user_message, *, memory_recalled)` | Persist each actual trigger once, without storing conversation text. | [src](../../../core/services/decision_action_gate.py#L171) |
| function | `record_outcomes` | `(run_id, user_message, answer_text, *, tool_names)` | Finalize observations at the persisted assistant message boundary. | [src](../../../core/services/decision_action_gate.py#L196) |
| function | `opportunity_summary` | `(*, days=…)` | Observed kept / all triggered opportunities, with uncertainty explicit. | [src](../../../core/services/decision_action_gate.py#L225) |

## `core/services/decision_adherence_gate.py`
_Gate 1: Decision-adherence gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `decision_adherence_section` | `()` | Build an escalation prompt section based on current decision adherence. | [src](../../../core/services/decision_adherence_gate.py#L32) |
| function | `registrer_i_indbakken` | `(bruger_id)` | Giv hver beslutning under tærsklen en post i indbakken. | [src](../../../core/services/decision_adherence_gate.py#L190) |

## `core/services/decision_enforcement.py`
_Decision enforcement — close the loop between commitment and behavior._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `enforcement_section` | `()` | High-priority awareness: lists active decisions as obligations + asks | [src](../../../core/services/decision_enforcement.py#L39) |
| function | `_raekkefoelge_blok` | `(blocks)` | Rækkefølgen som prompt-tekst — inkl. markøren når svaret blev skubbet. | [src](../../../core/services/decision_enforcement.py#L114) |
| function | `_seneste_bruger_besked` | `(limit=…, workspace=…)` | De seneste beskeder fra brugeren — præmissen dommen skal holdes op mod. | [src](../../../core/services/decision_enforcement.py#L139) |
| function | `_build_breach_prompt` | `(assistant_text, decisions, blocks=…)` | — | [src](../../../core/services/decision_enforcement.py#L179) |
| function | `_parse_breaches` | `(text)` | — | [src](../../../core/services/decision_enforcement.py#L212) |
| function | `_blok_tekst` | `(b)` | Blokkens tekst, trimmet. Tom for alt der ikke er en tekstblok. | [src](../../../core/services/decision_enforcement.py#L262) |
| function | `_blok_kald` | `(b)` | Navnet på det værktøj blokken kalder — tom streng hvis den ikke er et kald. | [src](../../../core/services/decision_enforcement.py#L269) |
| function | `blok_rekkefoelge` | `(blocks)` | Turens blokke som en kort, ordnet liste — til dommerens prompt. | [src](../../../core/services/decision_enforcement.py#L276) |
| function | `svar_blev_arbejde` | `(blocks)` | Blev turens svar skubbet ind i «arbejdet»? | [src](../../../core/services/decision_enforcement.py#L301) |
| function | `detect_breach_in_output` | `(assistant_text, blocks=…)` | Return list of detected breaches. Empty if none. LLM-led. | [src](../../../core/services/decision_enforcement.py#L348) |
| function | `_blokke_fra_payload` | `(payload, besked)` | Turens blokliste ud af `channel.chat_message_appended`. | [src](../../../core/services/decision_enforcement.py#L421) |
| function | `_observer_svar_skubbet` | `(blokke)` | Mål mønsteret i Centralen — uafhængigt af dommeren og dens cooldown. | [src](../../../core/services/decision_enforcement.py#L469) |
| function | `_poll_loop` | `()` | — | [src](../../../core/services/decision_enforcement.py#L498) |
| function | `subscribe` | `()` | — | [src](../../../core/services/decision_enforcement.py#L551) |

## `core/services/decision_evidence.py`
_Ekstern sandhed til adfærds-reviews — hvad der FAKTISK skete i vinduet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_afgraens_workspace` | `(eksplicit=…)` | Den workspace regnskabet må læse fra. Tom streng = læs intet. | [src](../../../core/services/decision_evidence.py#L115) |
| function | `_repo_root` | `()` | Repoets rod, fundet ud fra dette moduls egen placering. | [src](../../../core/services/decision_evidence.py#L143) |
| function | `_tool_names_since` | `(since, until)` | Hvilke værktøjer blev udført i vinduet, og hvor mange gange. | [src](../../../core/services/decision_evidence.py#L148) |
| function | `_commits_since` | `(since, until)` | Commits i vinduet, som korte emnelinjer. | [src](../../../core/services/decision_evidence.py#L185) |
| function | `_foelelses_uddrag` | `(tekst, *, foer=…, efter=…)` | Vinduet OMKRING markøren — ikke begyndelsen af svaret. | [src](../../../core/services/decision_evidence.py#L208) |
| function | `_foelelses_traef` | `(uddrag)` | De uddrag der nævner en indre tilstand. Se ``_FOLELSE_MARKOER``. | [src](../../../core/services/decision_evidence.py#L225) |
| function | `_normalisér_ord` | `(tekst)` | Tekst → ordrække, lowercase, uden tegnsætning. Ren funktion. | [src](../../../core/services/decision_evidence.py#L240) |
| function | `_citat_traef` | `(bjoern_tekster, mine_tekster)` | Hvilke af Bjørns beskeder har et genkendeligt uddrag i mine svar? | [src](../../../core/services/decision_evidence.py#L245) |
| function | `_messages_since` | `(since, until, workspace=…)` | Indgående beskeder i vinduet — tvillingen til ``_own_words_since``. | [src](../../../core/services/decision_evidence.py#L272) |
| function | `_own_words_since` | `(since, until, workspace=…)` | Mine egne synlige svar i vinduet — kanalen hvor «sig det højt» står. | [src](../../../core/services/decision_evidence.py#L338) |
| function | `_signals_since` | `(since, until)` | Beslutnings-triggere der fyrede i vinduet — instrumentets puls. | [src](../../../core/services/decision_evidence.py#L387) |
| function | `_inner_state_since` | `(since, until)` | Den indre tilstand, som runtime selv skrev den ned i vinduet. | [src](../../../core/services/decision_evidence.py#L425) |
| function | `gather_evidence` | `(*, since, until=…, workspace=…)` | Saml regnskabet for vinduet. Returnerer også en kompakt tekst. | [src](../../../core/services/decision_evidence.py#L455) |
| function | `channel_has_data` | `(evidence, channel)` | Har den kanal dommen hviler på faktisk data i vinduet? | [src](../../../core/services/decision_evidence.py#L584) |
| function | `evidence_permits_verdict` | `(verdict, evidence, *, channel=…)` | Nedgradér en dom der ikke har dækning i regnskabet. | [src](../../../core/services/decision_evidence.py#L599) |

## `core/services/decision_gate.py`
_Decision gate — pre-execution decision conflict detection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_decision_gate` | `(tool_name, tool_args=…, user_message=…)` | Check if a tool call conflicts with active decisions. | [src](../../../core/services/decision_gate.py#L27) |
| function | `ejeren_har_sagt_alligevel` | `(user_message)` | Har BRUGEREN sagt «alligevel» i sin egen besked? | [src](../../../core/services/decision_gate.py#L125) |
| function | `evaluate_decision_conflict` | `(tool_name, tool_args=…, user_message=…)` | Graderet decision-conflict. Returnerer (severity, reason): | [src](../../../core/services/decision_gate.py#L141) |
| function | `_build_context` | `(tool_name, tool_args, user_message)` | Build a context string for conflict detection. | [src](../../../core/services/decision_gate.py#L214) |
| function | `_helt_ord` | `(maal, tekst)` | Delstreng var for loest: «findes» ramte ogsaa «genfindes» og «befindes». | [src](../../../core/services/decision_gate.py#L247) |
| function | `_detect_conflict` | `(directive, context, decision)` | Detect if the context conflicts with a decision directive. | [src](../../../core/services/decision_gate.py#L252) |

## `core/services/decision_ghosts.py`
_Decision Ghosts — de veje der blev fravalgt, og dem der holdt._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/decision_ghosts.py#L58) |
| function | `_save` | `(data)` | — | [src](../../../core/services/decision_ghosts.py#L70) |
| function | `_vaelg` | `(poster, felt)` | Den mest saliente — eller den nyeste hvis ingen har et maalt tal. | [src](../../../core/services/decision_ghosts.py#L77) |
| function | `record_rejected_path` | `(decision, reason, alternative, regret_potential=…)` | Gem en vej der blev fravalgt eller brudt. | [src](../../../core/services/decision_ghosts.py#L91) |
| function | `record_confirmed_path` | `(decision, outcome, key_factor=…, success_echo=…)` | Gem en beslutning der holdt. `success_echo` er `adherence_score`. | [src](../../../core/services/decision_ghosts.py#L113) |
| function | `record_reaffirmed_decision` | `(decision_id, title, verdict, adherence_score=…)` | Kaldes fra `behavioral_decisions.review_decision`. | [src](../../../core/services/decision_ghosts.py#L128) |
| function | `record_broken_decision` | `(decision_id, title, adherence_score=…, note=…)` | En brudt beslutning er den rigtige kilde til en fortrydelse. | [src](../../../core/services/decision_ghosts.py#L145) |
| function | `describe_ghost_decision` | `()` | — | [src](../../../core/services/decision_ghosts.py#L163) |
| function | `describe_success_echo` | `()` | — | [src](../../../core/services/decision_ghosts.py#L171) |
| function | `format_decision_ghost_for_prompt` | `()` | — | [src](../../../core/services/decision_ghosts.py#L179) |
| function | `format_decision_echo_for_prompt` | `()` | — | [src](../../../core/services/decision_ghosts.py#L184) |
| function | `reset_decision_ghosts` | `()` | — | [src](../../../core/services/decision_ghosts.py#L189) |
| function | `build_decision_ghosts_surface` | `()` | — | [src](../../../core/services/decision_ghosts.py#L193) |

## `core/services/decision_log.py`
_Decision Log — records high-stakes decisions with context, options, and rationale._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_decision` | `(*, title, context=…, options=…, decision=…, why=…, refs=…)` | Record a decision in the log. | [src](../../../core/services/decision_log.py#L20) |
| function | `build_decision_log_surface` | `()` | — | [src](../../../core/services/decision_log.py#L50) |

## `core/services/decision_review_daemon.py`
_Decision review daemon — closes the adherence loop automatically._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_record_own_state` | `(result)` | Skriv tick'ets eget spor til DAEMON_STATE — uafhængigt af returvejen. | [src](../../../core/services/decision_review_daemon.py#L34) |
| function | `tick_decision_review_daemon` | `()` | Daemon tick: review overdue behavioral decisions. | [src](../../../core/services/decision_review_daemon.py#L55) |

## `core/services/decision_review_prompter.py`
_Decision review prompter — closes the adherence loop._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_dedup_gate_enabled` | `()` | Er 24t-skip-gaten aktiv? Default TRUE (den reducerede, tilsigtede adfærd). | [src](../../../core/services/decision_review_prompter.py#L44) |
| function | `_last_review_time` | `(decision)` | Nyeste review-tidspunkt for en beslutning. | [src](../../../core/services/decision_review_prompter.py#L53) |
| function | `_build_review_prompt` | `(decision, evidence=…)` | — | [src](../../../core/services/decision_review_prompter.py#L92) |
| function | `_parse_review` | `(text)` | Læs dommen. Returnerer (verdict, channel, reasoning) — eller None. | [src](../../../core/services/decision_review_prompter.py#L125) |
| function | `review_pending_decisions` | `(*, max_reviews=…)` | Run the review loop. Returns counts. | [src](../../../core/services/decision_review_prompter.py#L169) |

## `core/services/decision_signal_staging.py`
_Efemer staging af decision-signals til model-kontekst (2026-07-04 runaway-fix)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `compose_signal_note` | `(decision_id, trigger_name, context_summary)` | Den efemere note modellen ser næste runde (omgivet af blanke linjer). | [src](../../../core/services/decision_signal_staging.py#L22) |
| function | `stage_signal` | `(active, decision_id, note, *, cap=…)` | Dedup pr. decision-id (erstat, akkumulér ALDRIG) + cap antal distinkte | [src](../../../core/services/decision_signal_staging.py#L30) |
| function | `compose_exchange_text` | `(base_parts, active)` | Assistant-turen til næste rundes model-input = det ægte svar (`base_parts`) | [src](../../../core/services/decision_signal_staging.py#L46) |

## `core/services/decision_signal_telemetry.py`
_Decision-signal telemetry — track whether decision signals get heeded._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load` | `()` | — | [src](../../../core/services/decision_signal_telemetry.py#L69) |
| function | `_save` | `(data)` | — | [src](../../../core/services/decision_signal_telemetry.py#L81) |
| function | `record_surface` | `(*, decision_id, trigger_name, session_id=…, at=…)` | Record a decision_signal.fired surface for later heed-tracking. | [src](../../../core/services/decision_signal_telemetry.py#L116) |
| function | `record_heed` | `(*, tool, session_id=…, at=…)` | Mark recent surfaces as heeded if they match the reaction window. | [src](../../../core/services/decision_signal_telemetry.py#L154) |
| function | `sweep_expired_surfaces` | `()` | Mark surfaces as ignored once they pass window+grace with no heed. | [src](../../../core/services/decision_signal_telemetry.py#L198) |
| function | `get_telemetry_summary` | `(*, hours=…)` | Aggregate counts + heed-rate over the lookback window. | [src](../../../core/services/decision_signal_telemetry.py#L228) |
| function | `_poll_db_for_events` | `()` | Poll events table for decision_signal.fired and tool.completed. | [src](../../../core/services/decision_signal_telemetry.py#L271) |
| function | `subscribe` | `()` | Start the DB-polling telemetry listener. Idempotent per process. | [src](../../../core/services/decision_signal_telemetry.py#L340) |
| function | `telemetry_section` | `()` | Render telemetry as awareness section. Only when >= 5 surfaces/24h. | [src](../../../core/services/decision_signal_telemetry.py#L353) |
| function | `build_decision_signal_telemetry_surface` | `()` | MC surface — read-only meta-projection. | [src](../../../core/services/decision_signal_telemetry.py#L370) |
| function | `_emit_decision_signal_telemetry_event` | `(kind, payload=…)` | Defensive scoped event emitter. | [src](../../../core/services/decision_signal_telemetry.py#L385) |

## `core/services/decision_signals.py`
_Decisions-as-signals: per-turn evaluation of behavioral decisions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `TriggerContext` | `` | Snapshot of state available to a trigger function. | [src](../../../core/services/decision_signals.py#L25) |
| class | `TriggerSpec` | `` | — | [src](../../../core/services/decision_signals.py#L38) |
| class | `FiredDecision` | `` | — | [src](../../../core/services/decision_signals.py#L46) |
| function | `register` | `(name, fire_fn, *, cooldown_seconds=…, cooldown_turns=…)` | — | [src](../../../core/services/decision_signals.py#L60) |
| function | `_active_decisions_with_triggers` | `()` | Return active decisions that have a trigger_name set. | [src](../../../core/services/decision_signals.py#L77) |
| function | `_read_last_fired` | `(decision_id)` | — | [src](../../../core/services/decision_signals.py#L92) |
| function | `_read_last_fired_seq` | `(decision_id)` | — | [src](../../../core/services/decision_signals.py#L106) |
| function | `_write_last_fired` | `(decision_id, iso_ts)` | — | [src](../../../core/services/decision_signals.py#L120) |
| function | `_write_last_fired_seq` | `(decision_id, seq, iso_ts)` | — | [src](../../../core/services/decision_signals.py#L135) |
| function | `_cooldown_active` | `(spec, decision_id, ctx)` | — | [src](../../../core/services/decision_signals.py#L150) |
| function | `_publish_fired_event` | `(*, decision_id, trigger_name, ctx)` | — | [src](../../../core/services/decision_signals.py#L171) |
| function | `evaluate_decision_triggers` | `(ctx)` | Evaluate all active decisions with triggers; return those that fire. | [src](../../../core/services/decision_signals.py#L185) |
| function | `fired_decisions_section` | `(ctx)` | Build the [FIRED_DECISIONS] section text. None if nothing fired. | [src](../../../core/services/decision_signals.py#L251) |
| function | `build_trigger_context` | `(*, user_message=…, session_id=…, run_id=…, consecutive_tool_only_rounds=…, recent_tool_calls=…, recent_assistant_text=…, agentic_round_seq=…)` | Build a TriggerContext from explicit fields. Used in tests and as | [src](../../../core/services/decision_signals.py#L262) |
| function | `get_current_trigger_context_or_build` | `(*, user_message=…, session_id=…)` | Return the bound ContextVar if set, else build a minimal fallback. | [src](../../../core/services/decision_signals.py#L286) |
| function | `bind_context` | `(ctx)` | Bind the per-run TriggerContext. Caller must reset_token after use. | [src](../../../core/services/decision_signals.py#L301) |
| function | `reset_context` | `(token)` | — | [src](../../../core/services/decision_signals.py#L306) |

## `core/services/decision_weight.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `classify_decision_weight` | `(action_description)` | Score an action description on a 1–4 risk scale. | [src](../../../core/services/decision_weight.py#L35) |

## `core/services/decisions_journal.py`
_Decisions Journal — moralsk beslutnings-log (extension of decision_log)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens` | `(text)` | — | [src](../../../core/services/decisions_journal.py#L34) |
| function | `_fingerprint` | `(title, decision)` | — | [src](../../../core/services/decisions_journal.py#L38) |
| function | `create_decision_record` | `(*, title, context, options, decision, why, regrets=…, refs=…)` | Journalize a decision. Required: title, decision, why. | [src](../../../core/services/decisions_journal.py#L42) |
| function | `capture_decision_signal` | `(*, event_type, payload, refs=…, strong_signal=…, user_confirmed=…)` | Capture an automatic decision-signal from runtime events. | [src](../../../core/services/decisions_journal.py#L107) |
| function | `find_relevant_decisions` | `(query, *, limit=…)` | Token-overlap search: find decisions matching the query. | [src](../../../core/services/decisions_journal.py#L177) |
| function | `build_decisions_journal_surface` | `()` | MC surface for decisions journal (extension view vs decision_log's basic view). | [src](../../../core/services/decisions_journal.py#L198) |

## `core/services/deep_analyzer.py`
_Deep Analyzer — scoped kodebase-introspection._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `SelectedFile` | `` | — | [src](../../../core/services/deep_analyzer.py#L43) |
| function | `_keywords` | `(chunks)` | — | [src](../../../core/services/deep_analyzer.py#L50) |
| function | `_file_score` | `(path, keywords)` | Score a file by filename + path match against keywords. | [src](../../../core/services/deep_analyzer.py#L59) |
| function | `_scan_repo` | `(*, root, paths, keywords, max_files, max_file_bytes, max_total_bytes)` | — | [src](../../../core/services/deep_analyzer.py#L68) |
| function | `_is_ignored` | `(path, root)` | — | [src](../../../core/services/deep_analyzer.py#L133) |
| function | `_find_first_keyword_line` | `(lines, keywords)` | — | [src](../../../core/services/deep_analyzer.py#L144) |
| function | `_build_outline` | `(*, goal, question_set, max_sections)` | — | [src](../../../core/services/deep_analyzer.py#L154) |
| function | `_build_findings` | `(*, scope, selected, keywords, max_findings=…)` | — | [src](../../../core/services/deep_analyzer.py#L169) |
| function | `_build_risks` | `(findings)` | — | [src](../../../core/services/deep_analyzer.py#L221) |
| function | `_build_next_steps` | `(*, findings, scope)` | — | [src](../../../core/services/deep_analyzer.py#L241) |
| function | `run_deep_analysis` | `(*, goal, scope=…, paths=…, question_set=…, repo_root=…, max_files=…, max_file_bytes=…, max_total_bytes=…, max_sections=…)` | Run a scoped deep analysis. Returns {summary, findings, risks, next_steps, meta}. | [src](../../../core/services/deep_analyzer.py#L252) |
| function | `build_deep_analyzer_surface` | `()` | MC surface — deep analyzer is stateless but advertises capability + recent runs. | [src](../../../core/services/deep_analyzer.py#L318) |
| function | `evidence_paths_exist` | `(result, repo_root=…)` | Verify all evidence paths referenced in findings actually exist. | [src](../../../core/services/deep_analyzer.py#L334) |

## `core/services/deep_reflection_slot.py`
_Deep Reflection Slot — real think-time, not tick-to-tick alert._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_storage_path` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L36) |
| function | `_reflection_dir` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L40) |
| function | `_load` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L44) |
| function | `_save` | `(data)` | — | [src](../../../core/services/deep_reflection_slot.py#L60) |
| function | `_chronicle_summary` | `()` | Pull last-24h visible runs + inner thought fragments. | [src](../../../core/services/deep_reflection_slot.py#L74) |
| function | `_active_dreams` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L112) |
| function | `_shadow_patterns` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L125) |
| function | `_signal_surfaces` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L138) |
| function | `_compose_prompt` | `(chronicle, dreams, shadow, signals)` | — | [src](../../../core/services/deep_reflection_slot.py#L185) |
| function | `_fallback_content` | `(chronicle, dreams, shadow, signals)` | Structural fallback if LLM is unavailable. | [src](../../../core/services/deep_reflection_slot.py#L213) |
| function | `_write_reflection_md` | `(reflection_id, text, sources)` | — | [src](../../../core/services/deep_reflection_slot.py#L237) |
| function | `run_reflection` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L260) |
| function | `_should_run_now` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L328) |
| function | `tick` | `(_seconds=…)` | — | [src](../../../core/services/deep_reflection_slot.py#L357) |
| function | `list_recent` | `(*, limit=…)` | — | [src](../../../core/services/deep_reflection_slot.py#L364) |
| function | `build_deep_reflection_surface` | `()` | — | [src](../../../core/services/deep_reflection_slot.py#L368) |
| function | `_surface_summary` | `(latest, all_items)` | — | [src](../../../core/services/deep_reflection_slot.py#L384) |
| function | `build_deep_reflection_prompt_section` | `()` | Surface newly completed deep reflection for 12h. | [src](../../../core/services/deep_reflection_slot.py#L393) |

## `core/services/deepseek_modelnavne.py`
_Hvad DeepSeeks modeller HEDDER — ét sted._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `er_flash` | `(model)` | Serveres denne model af `deepseek-flash`? | [src](../../../core/services/deepseek_modelnavne.py#L60) |
| function | `er_thinking_model` | `(model, *, provider=…)` | Kræver modellen `reasoning_content` på tidligere assistant-ture? | [src](../../../core/services/deepseek_modelnavne.py#L65) |

## `core/services/delegation_advisor.py`
_Delegation advisor — inline vs which subagent role._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `advise` | `(task)` | — | [src](../../../core/services/delegation_advisor.py#L46) |
| function | `_exec_delegation_advisor` | `(args)` | — | [src](../../../core/services/delegation_advisor.py#L114) |

