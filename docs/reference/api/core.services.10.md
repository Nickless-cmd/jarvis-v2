# `core.services.10` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `core/services/delete_policy.py`
_Slette-model — hvem må slette hvad, og hvor hårdt (spec §4.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `resolve_delete_action` | `(*, role, is_own_workspace, gdpr_erasure=…)` | Afgør slette-mode for (rolle, om det er eget workspace). | [src](../../../core/services/delete_policy.py#L22) |
| function | `is_delete_confirmed` | `(*, role, confirmations_received)` | True hvis sletningen må udføres givet antal modtagne bekræftelser. | [src](../../../core/services/delete_policy.py#L55) |

## `core/services/delta_trace.py`
_Delta-sporet: hvor i kæden bliver streamen klumpet? (3/10-2026)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taendt` | `()` | Er sporet slået til? Enhver tvivl → nej, så det aldrig koster noget. | [src](../../../core/services/delta_trace.py#L79) |
| function | `noter` | `(punkt, run_id, tegn)` | Registrér én delta. No-op når sporet er slukket. | [src](../../../core/services/delta_trace.py#L88) |
| function | `_fordeling` | `(huller)` | (median, p95, max, indeks-for-max) i millisekunder. | [src](../../../core/services/delta_trace.py#L118) |
| function | `afslut` | `(noegle, *, run_id=…)` | Skriv opsummeringen og ryd den. No-op når slukket. | [src](../../../core/services/delta_trace.py#L129) |
| function | `noter_laesning` | `(noegle, *, blokeret_s, behandlet_s)` | Registrér ÉN læsning fra udbyderens stream — og hvor tiden gik. | [src](../../../core/services/delta_trace.py#L180) |
| function | `afslut_laesning` | `(noegle, *, run_id=…)` | Skriv læse-opsummeringen og ryd den. No-op når slukket. | [src](../../../core/services/delta_trace.py#L232) |

## `core/services/desire_daemon.py`
_Desire daemon — emergent appetites based on Jarvis' actual experiences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_persist_appetites` | `()` | — | [src](../../../core/services/desire_daemon.py#L61) |
| function | `tick_desire_daemon` | `(signals, skip_event_gate=…)` | Update appetites based on current signals. | [src](../../../core/services/desire_daemon.py#L69) |
| function | `get_active_appetites` | `()` | Return active appetites sorted by intensity descending. | [src](../../../core/services/desire_daemon.py#L136) |
| function | `build_desire_surface` | `()` | — | [src](../../../core/services/desire_daemon.py#L141) |
| function | `_apply_decay` | `(now)` | — | [src](../../../core/services/desire_daemon.py#L155) |
| function | `_prune_expired` | `()` | — | [src](../../../core/services/desire_daemon.py#L165) |
| function | `_find_appetite_by_type` | `(appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L171) |
| function | `_appetite_intensity` | `(appetite_type)` | Current intensity of an appetite type (0.0 when absent). Non-LLM. | [src](../../../core/services/desire_daemon.py#L178) |
| function | `_text_signal` | `(value)` | Deterministic 0..1 proxy of a short text state so the event-gate can | [src](../../../core/services/desire_daemon.py#L184) |
| function | `_spawn_appetite` | `(label, appetite_type, now)` | — | [src](../../../core/services/desire_daemon.py#L192) |
| function | `raw_signal_mode_enabled` | `()` | Kill-switch for rå-signal-mode. Default OFF — flip via runtime-state. | [src](../../../core/services/desire_daemon.py#L228) |
| function | `_build_raw_appetite_label` | `(spawning_type)` | Byg label udelukkende fra rå intensiteter — ingen LLM. | [src](../../../core/services/desire_daemon.py#L242) |
| function | `_generate_appetite_label` | `(signal_text, appetite_type)` | — | [src](../../../core/services/desire_daemon.py#L260) |

## `core/services/desktop_notifications.py`
_Per-bruger in-memory kø af proaktive desktop-notifikationer. Desktop poller_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reset` | `()` | — | [src](../../../core/services/desktop_notifications.py#L15) |
| function | `enqueue` | `(user_id, item)` | — | [src](../../../core/services/desktop_notifications.py#L20) |
| function | `drain` | `(user_id)` | — | [src](../../../core/services/desktop_notifications.py#L30) |
| function | `prune` | `()` | — | [src](../../../core/services/desktop_notifications.py#L37) |

## `core/services/desperation_awareness.py`
_Desperation Awareness — self-noticing safety signal._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hardware_component` | `()` | 0..1 contribution from hardware pressure. | [src](../../../core/services/desperation_awareness.py#L28) |
| function | `_tension_component` | `()` | 0..1 contribution from active layer tensions. | [src](../../../core/services/desperation_awareness.py#L42) |
| function | `_isolation_component` | `()` | 0..1 contribution from time since last user interaction. | [src](../../../core/services/desperation_awareness.py#L58) |
| function | `_error_component` | `()` | 0..1 contribution from recent error rate in heartbeat outcomes. | [src](../../../core/services/desperation_awareness.py#L81) |
| function | `compute_desperation_score` | `()` | Compute current desperation composite score in [0, 1] with reasons. | [src](../../../core/services/desperation_awareness.py#L100) |
| function | `tick` | `(_seconds=…)` | Evaluate desperation and emit inner-voice event on threshold crossing. | [src](../../../core/services/desperation_awareness.py#L138) |
| function | `_emit_crossing_event` | `(state, *, direction)` | Publish an inner-voice event so the crossing lands in chronicle. | [src](../../../core/services/desperation_awareness.py#L159) |
| function | `_narrative_for` | `(state, direction)` | — | [src](../../../core/services/desperation_awareness.py#L176) |
| function | `is_currently_pressed` | `()` | — | [src](../../../core/services/desperation_awareness.py#L183) |
| function | `build_desperation_awareness_surface` | `()` | — | [src](../../../core/services/desperation_awareness.py#L187) |
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/desperation_awareness.py#L203) |
| function | `build_desperation_awareness_prompt_section` | `()` | Surfaces only when pressed or desperate — silent when calm. | [src](../../../core/services/desperation_awareness.py#L214) |
| function | `reset_desperation_awareness` | `()` | Reset state (for testing). | [src](../../../core/services/desperation_awareness.py#L226) |

## `core/services/development_focus_tracking.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_development_focuses_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/development_focus_tracking.py#L32) |
| function | `refresh_runtime_development_focus_statuses` | `()` | — | [src](../../../core/services/development_focus_tracking.py#L76) |
| function | `build_runtime_development_focus_surface` | `(*, limit=…)` | — | [src](../../../core/services/development_focus_tracking.py#L120) |
| function | `_extract_focus_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L143) |
| function | `_explicit_learning_focus` | `(message)` | — | [src](../../../core/services/development_focus_tracking.py#L177) |
| function | `_repeated_correction_focus` | `(message, *, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L222) |
| function | `_runtime_development_focus` | `()` | — | [src](../../../core/services/development_focus_tracking.py#L276) |
| function | `_persist_focuses` | `(*, focuses, session_id, run_id)` | — | [src](../../../core/services/development_focus_tracking.py#L316) |
| function | `_apply_completion_signals` | `(*, user_message, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L391) |
| function | `_enrich_focus_support` | `(candidate, *, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L438) |
| function | `_candidate_history` | `(canonical_key, *, session_id)` | — | [src](../../../core/services/development_focus_tracking.py#L457) |
| function | `_recent_user_message_history` | `(*, limit_sessions, per_session_limit)` | — | [src](../../../core/services/development_focus_tracking.py#L477) |
| function | `_matches_correction_key` | `(canonical_key, message)` | — | [src](../../../core/services/development_focus_tracking.py#L498) |
| function | `_after_marker` | `(text, markers)` | — | [src](../../../core/services/development_focus_tracking.py#L509) |
| function | `_parse_dt` | `(value)` | — | [src](../../../core/services/development_focus_tracking.py#L517) |
| function | `_rank` | `(ranks, value)` | — | [src](../../../core/services/development_focus_tracking.py#L524) |
| function | `_quote` | `(text)` | — | [src](../../../core/services/development_focus_tracking.py#L528) |
| function | `_slug` | `(value)` | — | [src](../../../core/services/development_focus_tracking.py#L535) |
| function | `_now_iso` | `()` | — | [src](../../../core/services/development_focus_tracking.py#L540) |

## `core/services/development_narrative_daemon.py`
_Development narrative daemon — daily LLM narrative about how Jarvis has changed._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tick_development_narrative_daemon` | `()` | Generate a daily development narrative if cadence allows. | [src](../../../core/services/development_narrative_daemon.py#L16) |
| function | `_generate_narrative` | `()` | — | [src](../../../core/services/development_narrative_daemon.py#L33) |
| function | `_store_narrative` | `(narrative)` | — | [src](../../../core/services/development_narrative_daemon.py#L71) |
| function | `get_latest_development_narrative` | `()` | — | [src](../../../core/services/development_narrative_daemon.py#L100) |
| function | `build_development_narrative_surface` | `()` | — | [src](../../../core/services/development_narrative_daemon.py#L104) |

## `core/services/development_ritual.py`
_Ugentligt udviklings-ritual — Jarvis' egen vej til at ændre sig (blok D, 4/9)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_state_get` | `(key, default=…)` | — | [src](../../../core/services/development_ritual.py#L43) |
| function | `_state_set` | `(key, value)` | — | [src](../../../core/services/development_ritual.py#L52) |
| function | `_parse_iso` | `(value)` | — | [src](../../../core/services/development_ritual.py#L60) |
| function | `_due` | `(last_run, now)` | — | [src](../../../core/services/development_ritual.py#L68) |
| function | `gather_material` | `(*, limit=…)` | Hvad har han lært om sig selv og om arbejdet den seneste uge? | [src](../../../core/services/development_ritual.py#L73) |
| function | `build_paragraph` | `(material)` | Ét afsnit om ugen. Tom streng når der ikke er noget at sige. | [src](../../../core/services/development_ritual.py#L97) |
| function | `current_focus` | `(workspace_dir)` | Den nyeste `## Udvikling`-linje — hans aktive udviklingsfokus. | [src](../../../core/services/development_ritual.py#L108) |
| function | `propose` | `(*, now=…)` | Stil ugens udviklings-forslag. Ét ad gangen — aldrig to i kø. | [src](../../../core/services/development_ritual.py#L125) |
| function | `veto` | `(*, reason=…)` | Bjørn sagde fra. Forslaget droppes, intet skrives. | [src](../../../core/services/development_ritual.py#L153) |
| function | `apply_if_due` | `(*, now=…)` | Skriv forslaget når vetoperioden er udløbet. Tavshed er et ja. | [src](../../../core/services/development_ritual.py#L163) |
| function | `run_development_ritual` | `(*, force=…, now=…)` | Ugentligt: stil forslaget. Dagligt: skriv det der har ligget 24 timer. | [src](../../../core/services/development_ritual.py#L192) |
| function | `build_development_ritual_surface` | `()` | — | [src](../../../core/services/development_ritual.py#L214) |

## `core/services/development_sense.py`
_Development senses — realtime felt-sense of growth, stuck, appetite, resistance._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_crisis_resolution_ratio` | `(days=…)` | Resolved-vs-opened over window. None when insufficient data. | [src](../../../core/services/development_sense.py#L34) |
| function | `_adherence_score` | `()` | — | [src](../../../core/services/development_sense.py#L50) |
| function | `_skill_principles_recent` | `(days=…)` | Count skill_mutations recorded in the last N days. Each is a | [src](../../../core/services/development_sense.py#L66) |
| function | `_tick_quality_trend_bonus` | `()` | — | [src](../../../core/services/development_sense.py#L86) |
| function | `growth_pulse` | `()` | Composite 0-1 pulse + components. None-safe. | [src](../../../core/services/development_sense.py#L96) |
| function | `stuck_signal` | `()` | Detect repeating friction without resolution. | [src](../../../core/services/development_sense.py#L139) |
| function | `_topic_words_from_thought_fragments` | `(limit=…)` | — | [src](../../../core/services/development_sense.py#L198) |
| function | `appetite_signal` | `()` | What words/topics show up unprompted in his thought stream + open | [src](../../../core/services/development_sense.py#L214) |
| function | `resistance_signal` | `()` | Where am I acting against my own commitments / drifting from baseline? | [src](../../../core/services/development_sense.py#L233) |
| function | `_is_after` | `(ts, cutoff)` | — | [src](../../../core/services/development_sense.py#L278) |
| function | `development_sense_section` | `()` | Render all 4 senses as one COMPACT prompt-awareness block (2026-05-03). | [src](../../../core/services/development_sense.py#L288) |

## `core/services/developmental_valence.py`
_Developmental Valence — compass needle for flourishing vs withering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_within_window` | `(iso_str, days=…)` | — | [src](../../../core/services/developmental_valence.py#L41) |
| function | `_clamp` | `(x, lo=…, hi=…)` | — | [src](../../../core/services/developmental_valence.py#L49) |
| function | `_intention_closure_rate` | `()` | Of goal_signals updated in the window, what fraction are still active? | [src](../../../core/services/developmental_valence.py#L55) |
| function | `_dream_confirmation_rate` | `()` | Of dream_hypothesis_signals in window, fraction still carried. | [src](../../../core/services/developmental_valence.py#L76) |
| function | `_loop_health` | `()` | Closed vs total loops in window. Higher = closing what opens. | [src](../../../core/services/developmental_valence.py#L93) |
| function | `_relation_sustained` | `()` | Trust trajectory tail + recent contact density. | [src](../../../core/services/developmental_valence.py#L111) |
| function | `_metabolism` | `()` | Signal → action conversion. | [src](../../../core/services/developmental_valence.py#L149) |
| function | `_compute_components` | `()` | — | [src](../../../core/services/developmental_valence.py#L175) |
| function | `_components_to_vector` | `(components)` | Average of available components, re-centered to [-1, +1]. | [src](../../../core/services/developmental_valence.py#L185) |
| function | `_trajectory_label` | `(vector, delta)` | Map vector + derivative to trajectory label. | [src](../../../core/services/developmental_valence.py#L198) |
| function | `_recompute` | `()` | — | [src](../../../core/services/developmental_valence.py#L211) |
| function | `get_developmental_state` | `()` | Return cached compass state, recomputing only periodically. | [src](../../../core/services/developmental_valence.py#L242) |
| function | `tick` | `(_seconds=…)` | Heartbeat hook — no hot work, just trigger recompute when due. | [src](../../../core/services/developmental_valence.py#L252) |
| function | `build_developmental_valence_surface` | `()` | — | [src](../../../core/services/developmental_valence.py#L257) |
| function | `_surface_summary` | `(state)` | — | [src](../../../core/services/developmental_valence.py#L274) |
| function | `build_developmental_valence_prompt_section` | `()` | Speaks up when trajectory is notable — quiet when steady. | [src](../../../core/services/developmental_valence.py#L282) |
| function | `reset_developmental_valence` | `()` | Reset cached state (for testing). | [src](../../../core/services/developmental_valence.py#L305) |

