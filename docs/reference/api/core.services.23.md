# `core.services.23` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/release_marker_signal_tracking.py`
_Release-marker signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_release_marker_signals_for_visible_turn` | `(*, session_id, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L38) |
| function | `refresh_runtime_release_marker_signal_statuses` | `()` | — | [src](../../../core/services/release_marker_signal_tracking.py#L48) |
| function | `build_runtime_release_marker_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L52) |
| function | `_extract_release_marker_candidates` | `(*, run_id)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L56) |
| function | `_build_candidate` | `(*, domain_key, metabolism, witness, meaning, temperament, self_narrative, chronicle, relation_continuity)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L153) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L262) |
| function | `_release_marker_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L289) |
| function | `_derive_release_state` | `(*, metabolism_state, witness_status, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L313) |
| function | `_derive_release_direction` | `(*, release_state, witness_status, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L328) |
| function | `_derive_release_weight` | `(*, fading_count, softening_count, stale_count)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L345) |
| function | `_release_summary` | `(*, focus, release_state, release_direction, release_weight)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L359) |
| function | `_domain_key` | `(canonical_key)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L379) |
| function | `_anchor` | `(item)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L386) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L393) |
| function | `_find_support_value` | `(support_summary, key, default)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L405) |
| function | `_stronger_confidence` | `(*values)` | — | [src](../../../core/services/release_marker_signal_tracking.py#L416) |

## `core/services/remembered_fact_signal_tracking.py`
_Remembered-fact signal tracking — migrated onto signal_tracking_framework._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `track_runtime_remembered_fact_signals_for_visible_turn` | `(*, session_id, run_id, user_message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L42) |
| function | `refresh_runtime_remembered_fact_signal_statuses` | `()` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L84) |
| function | `build_runtime_remembered_fact_signal_surface` | `(*, limit=…)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L88) |
| function | `_extract_remembered_fact_candidates` | `(*, user_message, session_id)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L92) |
| function | `_explicit_user_name_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L125) |
| function | `_explicit_project_anchor_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L155) |
| function | `_explicit_working_context_fact` | `(messages)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L184) |
| function | `_with_runtime_view` | `(item, signal)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L214) |
| function | `_with_surface_view` | `(item)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L223) |
| function | `_remembered_fact_surface_extra` | `(summary, latest)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L232) |
| function | `_recent_user_messages` | `(*, session_id, current_message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L244) |
| function | `_extract_name_value` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L268) |
| function | `_is_project_anchor_fact` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L281) |
| function | `_is_working_context_fact` | `(message)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L294) |
| function | `_dimension_from_canonical_key` | `(canonical_key)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L328) |
| function | `_source_anchor` | `(text)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L335) |
| function | `_source_anchor_from_support_summary` | `(summary)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L340) |
| function | `_quote` | `(text, *, limit=…)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L347) |
| function | `_merge_fragments` | `(*parts)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L356) |
| function | `_contains_any` | `(text, needles)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L368) |
| function | `_rank_confidence` | `(confidence)` | — | [src](../../../core/services/remembered_fact_signal_tracking.py#L372) |

## `core/services/repeated_requests.py`
_Gentagne anmodninger → regel-forslag (lærings-sløjfe 2026-09-04, blok C)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_now` | `()` | — | [src](../../../core/services/repeated_requests.py#L60) |
| function | `_stems` | `(text)` | Betydningsbærende ord, forkortet til deres første `_STEM_CHARS` tegn. | [src](../../../core/services/repeated_requests.py#L64) |
| function | `normalize` | `(text)` | Anmodningens stammer, sorteret — noeglen en anmodning gemmes under. | [src](../../../core/services/repeated_requests.py#L80) |
| function | `similarity` | `(a, b)` | Jaccard mellem to anmodningers stammer (0-1). | [src](../../../core/services/repeated_requests.py#L85) |
| function | `ensure_table` | `(conn)` | — | [src](../../../core/services/repeated_requests.py#L93) |
| function | `_row` | `(r)` | — | [src](../../../core/services/repeated_requests.py#L117) |
| function | `_sessions` | `(raw)` | — | [src](../../../core/services/repeated_requests.py#L121) |
| function | `note_request` | `(*, text, session_id=…, kind=…)` | Tæl én anmodning. Returnerer rækken plus ``matured`` når den nu er en regel-kandidat. | [src](../../../core/services/repeated_requests.py#L125) |
| function | `build_question` | `(*, text, mention_count, session_count, kind)` | Det ene spørgsmål Bjørn får at se. Konkret, med tallet der udløste det. | [src](../../../core/services/repeated_requests.py#L209) |
| function | `mark_asked` | `(request_id)` | — | [src](../../../core/services/repeated_requests.py#L224) |
| function | `record_decision` | `(*, request_id, accepted)` | Bjørns svar. Ja → linjen skrives i `## Kerne` med begrundelse. | [src](../../../core/services/repeated_requests.py#L236) |
| function | `surface_matured` | `(result, *, kind=…, session_id=…)` | Læg et modnet regel-forslag i den proaktive kø. Ét spørgsmål, én gang. | [src](../../../core/services/repeated_requests.py#L273) |
| function | `note_and_surface` | `(*, text, session_id=…, kind=…)` | Tæl, og stil spørgsmålet hvis anmodningen netop modnede. Self-safe. | [src](../../../core/services/repeated_requests.py#L303) |
| function | `counts` | `()` | — | [src](../../../core/services/repeated_requests.py#L315) |
| function | `build_repeated_requests_surface` | `()` | — | [src](../../../core/services/repeated_requests.py#L325) |

## `core/services/repetition_guard.py`
_Gentagelses-vagt (5/11-2026) — fang "sagde det samme igen, intet er ændret"._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fact_tokens` | `(text)` | Konkrete fakta i teksten: tal, filnavne, hashes (lowercased). | [src](../../../core/services/repetition_guard.py#L53) |
| function | `_normaliser` | `(text)` | Tegnsætning væk, så «færdig.» og «færdig» ikke tæller som forskellige ord. | [src](../../../core/services/repetition_guard.py#L62) |
| function | `is_repetition` | `(final_text, previous_texts, nudged_already=…, window=…, threshold=…, min_words=…)` | Gentagelse = svaret ligner et af de seneste svar + ingen ny information. | [src](../../../core/services/repetition_guard.py#L67) |
| function | `previous_assistant_texts` | `(session_id, limit=…)` | Jarvis' seneste svar i sessionen, ældste først. Self-safe → [] ved fejl. | [src](../../../core/services/repetition_guard.py#L103) |
| function | `should_nudge` | `(final_text, session_id)` | Produktions-indgangen: flag + sessionens seneste svar + is_repetition. | [src](../../../core/services/repetition_guard.py#L113) |
| function | `repetition_guard_enabled` | `()` | Default TRUE. Env `JARVIS_REPETITION_GUARD` vinder; ellers runtime-state | [src](../../../core/services/repetition_guard.py#L119) |

## `core/services/repo_index.py`
_Separat søgeindeks over repoets DOKUMENTATION — ikke kildekoden._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_repo_root` | `()` | Repoets rod. Kan overstyres med JARVIS_REPO_ROOT (tests, worktrees). | [src](../../../core/services/repo_index.py#L97) |
| function | `_index_path` | `()` | Global sti — dokumentationen er den samme for alle brugere. | [src](../../../core/services/repo_index.py#L105) |
| function | `_is_excluded` | `(rel)` | — | [src](../../../core/services/repo_index.py#L110) |
| function | `repo_files` | `(root=…)` | Alle dokumentationsfiler der skal indekseres, sorteret. | [src](../../../core/services/repo_index.py#L117) |
| function | `_file_mtime` | `(path)` | — | [src](../../../core/services/repo_index.py#L143) |
| function | `_chunk_files` | `(files, root)` | Læs + chunk. Kun fil-I/O — ingen embedding. | [src](../../../core/services/repo_index.py#L150) |
| function | `_load_cached_vectors` | `(path)` | chunk-tekst → vektor fra eksisterende cache, til inkrementel reindeksering. | [src](../../../core/services/repo_index.py#L167) |
| function | `build_index` | `(*, root=…, force=…)` | Byg indekset og skriv cachen. Blokerer indtil embeddings er færdige. | [src](../../../core/services/repo_index.py#L185) |
| function | `_schedule_background_build` | `()` | Byg i baggrunden (fire-and-forget, kun én ad gangen). | [src](../../../core/services/repo_index.py#L261) |
| function | `_load_or_build` | `()` | (chunks, embeddings, mtimes). Blokerer aldrig på en fuld embedding. | [src](../../../core/services/repo_index.py#L282) |
| function | `_path_matches` | `(source, path_prefix)` | — | [src](../../../core/services/repo_index.py#L313) |
| function | `_area_weight` | `(source)` | Vægt for en chunk-kilde. Første match vinder, mest specifikke først. | [src](../../../core/services/repo_index.py#L352) |
| function | `_lexical_score` | `(query_terms, chunk)` | Andel af query-termer der optræder i chunk, sektion eller sti. | [src](../../../core/services/repo_index.py#L378) |
| function | `search_repo` | `(query, *, limit=…, path_prefix=…)` | Semantisk søgning i repoets dokumentation. | [src](../../../core/services/repo_index.py#L386) |
| function | `get_stats` | `()` | Indeksets tilstand uden at bygge noget. | [src](../../../core/services/repo_index.py#L456) |
| function | `invalidate` | `()` | Slet cachen, så næste søgning genopbygger. | [src](../../../core/services/repo_index.py#L494) |
| function | `_main` | `(argv=…)` | — | [src](../../../core/services/repo_index.py#L504) |

## `core/services/report_claim_guard.py`
_Efterproev det et barn PAASTAAR — Fase 6._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_opsloegere` | `(context)` | Vaelg den maskine paastanden skal efterproeves PAA. | [src](../../../core/services/report_claim_guard.py#L40) |
| function | `tjek_rapport` | `(text, *, agent_id=…, role=…, run_id=…, context=…)` | Efterproev en barne-rapports filstier og linjenumre. Kaster ALDRIG. | [src](../../../core/services/report_claim_guard.py#L83) |

## `core/services/research_contract.py`
_Typed contracts and source normalization for explicit research runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchPolicy` | `` | — | [src](../../../core/services/research_contract.py#L30) |
| class | `ResearchDecision` | `` | — | [src](../../../core/services/research_contract.py#L44) |
| class | `ResearchTask` | `` | — | [src](../../../core/services/research_contract.py#L57) |
| class | `ResearchPlan` | `` | — | [src](../../../core/services/research_contract.py#L64) |
| class | `ResearchSource` | `` | — | [src](../../../core/services/research_contract.py#L70) |
| class | `ResearchFinding` | `` | — | [src](../../../core/services/research_contract.py#L83) |
| class | `ResearchContract` | `` | — | [src](../../../core/services/research_contract.py#L92) |
| function | `_clean` | `(value)` | — | [src](../../../core/services/research_contract.py#L99) |
| function | `canonicalize_url` | `(raw)` | — | [src](../../../core/services/research_contract.py#L103) |
| function | `normalize_source` | `(value)` | — | [src](../../../core/services/research_contract.py#L120) |
| function | `load_research_contract` | `(query=…)` | Load the canonical skill deterministically; fall back without hiding it. | [src](../../../core/services/research_contract.py#L137) |

## `core/services/research_evidence_collector.py`
_Capture structured web-tool evidence for the active research run._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `collecting_for` | `(run_id, *, task_id=…)` | — | [src](../../../core/services/research_evidence_collector.py#L14) |
| function | `_structured_sources` | `(tool_name, result)` | — | [src](../../../core/services/research_evidence_collector.py#L22) |
| function | `observe_web_result` | `(tool_name, result)` | — | [src](../../../core/services/research_evidence_collector.py#L38) |

## `core/services/research_ledger.py`
_Research-runnet synligt i session-ledgeren (spec Fase A4)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `taellere` | `()` | — | [src](../../../core/services/research_ledger.py#L42) |
| function | `_nulstil_for_tests` | `()` | — | [src](../../../core/services/research_ledger.py#L46) |
| function | `record_research_event` | `(session_id, *, event_id, event, payload=…)` | Skriv én research-hændelse i session-ledgeren. Kaster aldrig. | [src](../../../core/services/research_ledger.py#L51) |
| function | `record_run_started` | `(session_id, *, run_id, tier, query)` | Runnet er startet: tier og den oprindelige forespørgsel. | [src](../../../core/services/research_ledger.py#L96) |
| function | `record_run_completed` | `(session_id, *, run_id, sources, quality, timed_out, tool_calls=…)` | Runnet er slut: hvad det blev — kilder, kvalitetsdom, timeout, forbrug. | [src](../../../core/services/research_ledger.py#L106) |

## `core/services/research_orchestrator.py`
_Adaptive research coordinator around the existing visible and agent runtimes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_event` | `(kind, payload)` | — | [src](../../../core/services/research_orchestrator.py#L30) |
| function | `_setting` | `(name, default)` | — | [src](../../../core/services/research_orchestrator.py#L34) |
| function | `_facets` | `(message)` | De emneord planlægningen deler beskeden i — og som gaten måler dækning imod. | [src](../../../core/services/research_orchestrator.py#L48) |
| function | `_delta_text` | `(frame)` | Træk syntese-teksten ud af en `delta`-frame. Andre frames giver ''. | [src](../../../core/services/research_orchestrator.py#L56) |
| function | `_plan` | `(message, max_tasks)` | — | [src](../../../core/services/research_orchestrator.py#L78) |
| function | `_parse_plan` | `(text, max_tasks)` | Læs plannerens JSON til en ResearchTask-liste. Defensiv: [] ved mindste tvivl. | [src](../../../core/services/research_orchestrator.py#L109) |
| function | `_llm_plan` | `(message, max_tasks, facets)` | Fase C1: bed en billig model om delopgaver. None = kunne ikke → regex. | [src](../../../core/services/research_orchestrator.py#L152) |
| function | `_plan_tasks` | `(message, max_tasks, *, planner_enabled)` | Fase C1: LLM-planlægger med regex-fallback. | [src](../../../core/services/research_orchestrator.py#L177) |
| function | `_tool_calls_used` | `(run_id)` | Observerede værktøjskald i runnet. Defensiv: 0 hvis tællingen ikke kan læses. | [src](../../../core/services/research_orchestrator.py#L193) |
| function | `_clean_text` | `(value)` | — | [src](../../../core/services/research_orchestrator.py#L204) |
| function | `_confidence` | `(value)` | — | [src](../../../core/services/research_orchestrator.py#L208) |
| function | `_finding_from_text` | `(text, task_ordinal)` | Sidste udkast: hele teksten bliver ét fund med de URLs den bærer. | [src](../../../core/services/research_orchestrator.py#L213) |
| function | `_parse_findings` | `(text, task_ordinal)` | Fase B2: worker-svaret → `ResearchFinding`. | [src](../../../core/services/research_orchestrator.py#L230) |
| function | `_gap_objective` | `(query, findings)` | Fase B3: critic-opgaven — hvad MANGLER der, givet de fundne påstande. | [src](../../../core/services/research_orchestrator.py#L304) |
| function | `_parse_gaps` | `(text)` | Fase B3: critic-svaret → korte gap-linjer. Defensiv hele vejen. | [src](../../../core/services/research_orchestrator.py#L321) |
| function | `_evidence_block` | `(texts, sources, findings, gaps=…)` | Evidens til syntesen — med en KANONISK nummereret kilde-liste. | [src](../../../core/services/research_orchestrator.py#L355) |
| function | `_topup_plan` | `(run_id, tasks, policy)` | Fase B1: hvilke tracks skal styrkes — og med hvad? | [src](../../../core/services/research_orchestrator.py#L393) |
| function | `_evaluate_quality` | `(run_id, query, report, policy)` | Fase A1: kobl kvalitetsgaten på den faktiske rapport. | [src](../../../core/services/research_orchestrator.py#L439) |
| function | `_judge_prompt` | `(query, report, sources, findings, gaps)` | Binær rubric — kort nok til en billig model, konkret nok til at være falsificerbar. | [src](../../../core/services/research_orchestrator.py#L490) |
| function | `_parse_verdict` | `(text)` | Dommerens svar → {"verdict", "criteria", "reason"}. None hvis uafgørbart. | [src](../../../core/services/research_orchestrator.py#L514) |
| function | `_judge_quality` | `(run_id, query, report, gaps=…)` | Kør dommeren i en tråd, så event-loopet ikke blokeres. Fejler altid blødt. | [src](../../../core/services/research_orchestrator.py#L552) |
| function | `_default_worker_sync` | `(*, task, run_id, skill_instructions, max_turns=…, budget_tokens=…)` | — | [src](../../../core/services/research_orchestrator.py#L584) |
| function | `_run_worker` | `(worker_factory, *, task, run_id, skill_instructions, max_turns=…, budget_tokens=…)` | Kør én worker gennem factory'en. | [src](../../../core/services/research_orchestrator.py#L625) |
| function | `stream_research_run` | `(*, message, original_query=…, session_id, visible_run_id=…, decision=…, visible_factory=…, worker_factory=…, orchestrator_enabled=…, **visible_kwargs)` | — | [src](../../../core/services/research_orchestrator.py#L651) |
| class | `ResearchRecoverableError` | `` | Der er intet at syntetisere på — forælderen må tage sig af det. | [src](../../../core/services/research_orchestrator.py#L971) |
| method | `ResearchRecoverableError.__init__` | `(self, run_id, reason, evidence_count=…)` | — | [src](../../../core/services/research_orchestrator.py#L979) |
| function | `resume_research_run` | `(run_id, *, visible_run_id, worker_factory=…)` | Tag et afbrudt research-run op igen — kun de UAFSLUTTEDE spor. | [src](../../../core/services/research_orchestrator.py#L986) |
| function | `research_enabled` | `()` | — | [src](../../../core/services/research_orchestrator.py#L1061) |

## `core/services/research_prompt_context.py`
_Request-scoped research instructions consumed by prompt assembly surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `_PromptResearch` | `` | — | [src](../../../core/services/research_prompt_context.py#L13) |
| function | `research_context` | `(policy, *, skill_instructions=…, evidence=…, clarification=…)` | — | [src](../../../core/services/research_prompt_context.py#L24) |
| function | `research_prompt_section` | `()` | — | [src](../../../core/services/research_prompt_context.py#L43) |

## `core/services/research_quality.py`
_Deterministic, inspectable quality gates for research synthesis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchQualityResult` | `` | — | [src](../../../core/services/research_quality.py#L13) |
| function | `evaluate_research_report` | `(report, sources, requested_facets, *, contradictions=…, requires_freshness=…, tool_calls=…, max_tool_calls=…)` | — | [src](../../../core/services/research_quality.py#L19) |

## `core/services/research_router.py`
_Conservative and explainable inline/orchestrated research routing._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_effort` | `(independent)` | Indsatsen for N uafhængige signaler — klippet til tabellens rækker. | [src](../../../core/services/research_router.py#L47) |
| function | `classify_research` | `(message, *, attachment_count=…, policy=…)` | — | [src](../../../core/services/research_router.py#L52) |
| function | `clarification_needed` | `(message)` | One conservative preflight question, or ``""`` when research can start. | [src](../../../core/services/research_router.py#L105) |
| function | `requires_freshness` | `(message)` | Whether the query itself makes current, dated evidence mandatory. | [src](../../../core/services/research_router.py#L117) |

## `core/services/research_store.py`
_Durable SQLite state for research runs, tasks, sources, and steering._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ResearchStateError` | `` | — | [src](../../../core/services/research_store.py#L17) |
| function | `_now` | `()` | — | [src](../../../core/services/research_store.py#L21) |
| function | `_ensure` | `(conn)` | — | [src](../../../core/services/research_store.py#L25) |
| function | `_row` | `(row)` | — | [src](../../../core/services/research_store.py#L63) |
| function | `get_run` | `(run_id)` | — | [src](../../../core/services/research_store.py#L67) |
| function | `create_run` | `(*, session_id, original_query, tier, decision=…)` | — | [src](../../../core/services/research_store.py#L73) |
| function | `transition_run` | `(run_id, status, *, warning=…)` | — | [src](../../../core/services/research_store.py#L85) |
| function | `bind_visible_run` | `(run_id, visible_run_id)` | — | [src](../../../core/services/research_store.py#L106) |
| function | `create_tasks` | `(run_id, tasks)` | — | [src](../../../core/services/research_store.py#L112) |
| function | `start_task` | `(task_id, *, agent_run_id=…)` | — | [src](../../../core/services/research_store.py#L126) |
| function | `complete_task` | `(task_id, finding, *, status=…)` | — | [src](../../../core/services/research_store.py#L138) |
| function | `list_tasks` | `(run_id)` | Alle spor i deres egen rækkefølge — også de uafsluttede. | [src](../../../core/services/research_store.py#L152) |
| function | `unfinished_tasks` | `(run_id)` | De spor der IKKE blev færdige. Et genoptaget run må kun tage dem. | [src](../../../core/services/research_store.py#L163) |
| function | `prepare_recovery` | `(run_id, *, warning)` | Gør et afbrudt research-run klar til at blive taget op igen. | [src](../../../core/services/research_store.py#L174) |
| function | `advance_to_completed` | `(run_id, *, warning=…)` | Før runnet hele vejen til `completed` — ét trin ad gangen. | [src](../../../core/services/research_store.py#L204) |
| function | `completed_task_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L224) |
| function | `add_source` | `(run_id, source, *, task_id=…)` | — | [src](../../../core/services/research_store.py#L229) |
| function | `add_steer` | `(run_id, message)` | — | [src](../../../core/services/research_store.py#L245) |
| function | `consume_pending_steers` | `(run_id)` | — | [src](../../../core/services/research_store.py#L253) |
| function | `list_sources` | `(run_id)` | — | [src](../../../core/services/research_store.py#L269) |
| function | `source_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L279) |
| function | `list_findings` | `(run_id)` | Parsede findings for et run (Fase B2), i track-rækkefølge. | [src](../../../core/services/research_store.py#L286) |
| function | `record_tool_call` | `(run_id, tool_name, *, task_id=…)` | Tæl ét observeret værktøjskald i runnet (Fase A3). | [src](../../../core/services/research_store.py#L313) |
| function | `tool_call_count` | `(run_id)` | — | [src](../../../core/services/research_store.py#L327) |
| function | `active_for_session` | `(session_id)` | — | [src](../../../core/services/research_store.py#L334) |
| function | `mark_stale_interrupted` | `(*, older_than_seconds=…)` | — | [src](../../../core/services/research_store.py#L345) |

## `core/services/resonance_decay.py`
_Resonance Decay — how emotional signals persist and fade over time._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Resonance` | `` | A single active resonance — an emotional signal persisting over time. | [src](../../../core/services/resonance_decay.py#L84) |
| class | `ResonanceField` | `` | The sum of all active resonances — the emotional tail coloring now. | [src](../../../core/services/resonance_decay.py#L95) |
| function | `_autonomy_enabled` | `()` | Check the generative autonomy killswitch. | [src](../../../core/services/resonance_decay.py#L121) |
| function | `_hours_since` | `(iso_ts)` | Compute hours elapsed since an ISO timestamp. | [src](../../../core/services/resonance_decay.py#L132) |
| function | `_apply_decay` | `(resonance, hours)` | Apply exponential decay to a resonance. | [src](../../../core/services/resonance_decay.py#L142) |
| function | `_prune_resonances` | `()` | Remove resonances below threshold and cap at max count. | [src](../../../core/services/resonance_decay.py#L151) |
| function | `_scan_for_new_resonances` | `()` | Scan recent signal/chord history for new resonances to register. | [src](../../../core/services/resonance_decay.py#L173) |
| function | `_direction_to_family` | `(direction)` | Map a pressure direction to its dominant signal family. | [src](../../../core/services/resonance_decay.py#L260) |
| function | `_compute_field_quality` | `(resonances)` | Compute a qualitative description of the resonance field. | [src](../../../core/services/resonance_decay.py#L275) |
| function | `assess_resonance_field` | `()` | Assess the current resonance field — all active emotional tails. | [src](../../../core/services/resonance_decay.py#L316) |
| function | `get_resonance_line` | `(db_conn=…)` | Convenience: compute resonance field and format for prompt. | [src](../../../core/services/resonance_decay.py#L378) |
| function | `get_active_resonance_count` | `()` | Return the number of currently active resonances (for debugging). | [src](../../../core/services/resonance_decay.py#L399) |
| function | `clear_resonances` | `()` | Clear all active resonances (for testing). | [src](../../../core/services/resonance_decay.py#L404) |
| function | `build_resonance_decay_surface` | `()` | — | [src](../../../core/services/resonance_decay.py#L410) |
| function | `_emit_decay_event` | `(signal_id, half_life)` | — | [src](../../../core/services/resonance_decay.py#L419) |

## `core/services/retention.py`
_Retention-sweep — bremser ubegrænset vækst på høj-volumen tabeller._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_configured_days` | `(key, default)` | — | [src](../../../core/services/retention.py#L35) |
| function | `_should_run` | `(last_run_iso, now)` | — | [src](../../../core/services/retention.py#L44) |
| function | `_prune_telemetry` | `(table, max_age_days, now)` | — | [src](../../../core/services/retention.py#L54) |
| function | `_prune_unmatched_policies` | `(max_age_days, now)` | Slet generaliserede principper der ALDRIG har matchet og er >max_age gamle — | [src](../../../core/services/retention.py#L66) |
| function | `run_retention_sweep` | `(*, force=…, now=…)` | Kør retention. Selv-throttlende (max 1×/24h) medmindre force=True. | [src](../../../core/services/retention.py#L83) |

## `core/services/retention_coverage.py`
_Vagt: hvilke store tabeller i `jarvis.db` har ingen aftale om oprydning?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `har_politik` | `()` | Tabeller med en alders-politik, og hvor den står. Kilden er én. | [src](../../../core/services/retention_coverage.py#L129) |
| function | `_stoerrelser` | `(conn)` | Bytes pr. tabel via dbstat. Tom dict hvis dbstat ikke er bygget ind. | [src](../../../core/services/retention_coverage.py#L149) |
| function | `tabeller_uden_politik` | `(*, conn=…, min_bytes=…, min_raekker=…)` | De store tabeller der hverken har en politik eller en skreven grund. | [src](../../../core/services/retention_coverage.py#L165) |
| function | `rapport` | `(fund)` | Én linje til loggen. Tom streng når der intet er at sige. | [src](../../../core/services/retention_coverage.py#L225) |

## `core/services/retry_admissibility.py`
_Et ukendt udfald maa aldrig gentages automatisk — Fase 3, K7._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Dom` | `` | — | [src](../../../core/services/retry_admissibility.py#L43) |
| function | `_er_beviseligt_uskadeligt` | `(tool_name)` | Kun `read_only` — og kun naar den er ERKLAERET, ikke gaettet. | [src](../../../core/services/retry_admissibility.py#L49) |
| function | `may_auto_retry` | `(tool_name, arguments)` | Maa dette kald gentages AUTOMATISK — uden at et menneske ser paa det? | [src](../../../core/services/retry_admissibility.py#L59) |
| function | `advar_hvis_gentagelse` | `(tool_name, arguments)` | Sig hoejt at dette kald gentager noget med ukendt udfald. | [src](../../../core/services/retry_admissibility.py#L86) |

## `core/services/retry_runtime.py`
_`RetryRuntime` — genforsøg som en BEGRÆNSET beslutning, ikke en refleks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Budget` | `` | Lofter for HELE turen. Failover nulstiller intet af det. | [src](../../../core/services/retry_runtime.py#L65) |
| class | `Spent` | `` | Hvad turen allerede har brugt — på tværs af alle udbydere. | [src](../../../core/services/retry_runtime.py#L76) |
| method | `Spent.plus_attempt` | `(self, *, wall_s=…, tokens=…, cost_usd=…, failover=…)` | — | [src](../../../core/services/retry_runtime.py#L85) |
| class | `Decision` | `` | — | [src](../../../core/services/retry_runtime.py#L97) |
| function | `_udtoemt` | `(b, s)` | Hvilket loft er nået? Tom streng hvis der er plads. | [src](../../../core/services/retry_runtime.py#L107) |
| function | `backoff` | `(forsoeg, *, provider_hint_s=…, mindst=…, hoejst=…)` | Ventetid før næste forsøg. | [src](../../../core/services/retry_runtime.py#L126) |
| function | `decide` | `(*, failure, budget, spent, cancelled=…, provider_hint_s=…, route_override=…)` | Skal der prøves igen? Ren funktion — ændrer ingenting. | [src](../../../core/services/retry_runtime.py#L139) |

## `core/services/rhythm_engine.py`
_Rhythm Engine — tidal model for attention and response style._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `update_rhythm_state` | `(*, recent_error_count=…, recent_success_count=…, idle_hours=…)` | Derive rhythm state from current time and recent activity. | [src](../../../core/services/rhythm_engine.py#L26) |
| function | `build_rhythm_surface` | `()` | — | [src](../../../core/services/rhythm_engine.py#L73) |
| function | `_classify_phase` | `(hour)` | — | [src](../../../core/services/rhythm_engine.py#L96) |
| function | `_derive_energy` | `(phase, idle_hours)` | — | [src](../../../core/services/rhythm_engine.py#L108) |
| function | `_derive_social` | `(phase)` | — | [src](../../../core/services/rhythm_engine.py#L118) |

## `core/services/role_model_resolver.py`
_Role-model resolver — pick best-fit (provider, model) for a role + task._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_classify_goal_tier` | `(goal)` | Classify goal text → fast | reasoning | deep using R1 classifier. | [src](../../../core/services/role_model_resolver.py#L39) |
| function | `resolve_role_model` | `(*, role, goal=…)` | Pick (provider, model) for this role and goal complexity. | [src](../../../core/services/role_model_resolver.py#L54) |

## `core/services/role_registry.py`
_Role registry — runtime-extensible agent roles._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_custom_roles` | `()` | — | [src](../../../core/services/role_registry.py#L33) |
| function | `_builtin_roles` | `()` | — | [src](../../../core/services/role_registry.py#L47) |
| function | `list_all_roles` | `()` | Return merged dict of role_name → template (builtin + custom). | [src](../../../core/services/role_registry.py#L55) |
| function | `get_role` | `(name)` | Look up a single role by name (custom > built-in). | [src](../../../core/services/role_registry.py#L73) |
| function | `register_custom_role` | `(*, role, title, system_prompt, default_tool_policy=…, extends=…, tags=…)` | Persist a new custom role to disk. Idempotent on (role) name. | [src](../../../core/services/role_registry.py#L79) |
| function | `_exec_list_roles` | `(args)` | — | [src](../../../core/services/role_registry.py#L119) |
| function | `_exec_register_custom_role` | `(args)` | — | [src](../../../core/services/role_registry.py#L138) |

## `core/services/round_budget_notice.py`
_Fortael ham hvor mange runder han har tilbage, foer doeren smaekker._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `round_budget_notice` | `(*, round_index, max_rounds)` | Varsel til modellen naar rundebudgettet slipper op. "" ellers. | [src](../../../core/services/round_budget_notice.py#L34) |

## `core/services/routine_authorization.py`
_The single authorization matrix for Routine records._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Action` | `` | — | [src](../../../core/services/routine_authorization.py#L11) |
| class | `Decision` | `` | — | [src](../../../core/services/routine_authorization.py#L23) |
| class | `RoutineForbidden` | `` | The principal is not allowed to perform a Routine action. | [src](../../../core/services/routine_authorization.py#L28) |
| function | `_deny` | `(reason)` | — | [src](../../../core/services/routine_authorization.py#L44) |
| function | `authorize` | `(principal, action, record)` | Evaluate access without decrypting or including record content in reasons. | [src](../../../core/services/routine_authorization.py#L48) |
| function | `require_authorized` | `(principal, action, record)` | — | [src](../../../core/services/routine_authorization.py#L95) |

## `core/services/routine_classification.py`
_Klassifikation af en rutine ved oprettelsen — valget, ikke gættet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_execution_mode` | `(raw)` | — | [src](../../../core/services/routine_classification.py#L57) |
| function | `_parse_importance` | `(raw)` | — | [src](../../../core/services/routine_classification.py#L72) |
| function | `classify_routine` | `(*, execution_mode=…, importance=…)` | Validér valget og udled de felter indbakken og runneren læser. | [src](../../../core/services/routine_classification.py#L85) |

## `core/services/routine_crypto.py`
_Owner-bound authenticated encryption for Routine content._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner_key` | `(owner_user_id)` | — | [src](../../../core/services/routine_crypto.py#L7) |
| function | `seal` | `(owner_user_id, payload)` | — | [src](../../../core/services/routine_crypto.py#L17) |
| function | `open_sealed` | `(owner_user_id, blob)` | — | [src](../../../core/services/routine_crypto.py#L23) |

## `core/services/routine_delivery.py`
_Fenced delivery outbox for Routine results._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StaleDeliveryLease` | `` | A worker attempted to settle a delivery it no longer owns. | [src](../../../core/services/routine_delivery.py#L25) |
| class | `DeliveryClaim` | `` | — | [src](../../../core/services/routine_delivery.py#L30) |
| class | `DeliveryView` | `` | — | [src](../../../core/services/routine_delivery.py#L41) |
| class | `_RepositoryView` | `` | — | [src](../../../core/services/routine_delivery.py#L52) |
| method | `_RepositoryView.count_runs` | `(routine_id)` | — | [src](../../../core/services/routine_delivery.py#L54) |
| function | `_push_owner` | `(claim)` | Giv ejeren et push naar resultatet ligger klar paa rutinens egen flade. | [src](../../../core/services/routine_delivery.py#L58) |
| function | `_claim` | `(row)` | — | [src](../../../core/services/routine_delivery.py#L117) |
| function | `_view` | `(row)` | — | [src](../../../core/services/routine_delivery.py#L129) |
| class | `RoutineDeliveryService` | `` | — | [src](../../../core/services/routine_delivery.py#L142) |
| method | `RoutineDeliveryService.__init__` | `(self, *, holder=…)` | — | [src](../../../core/services/routine_delivery.py#L143) |
| method | `RoutineDeliveryService.claim_for_run` | `(self, run_id, holder)` | — | [src](../../../core/services/routine_delivery.py#L147) |
| method | `RoutineDeliveryService.claim_next` | `(self)` | — | [src](../../../core/services/routine_delivery.py#L151) |
| method | `RoutineDeliveryService.deliver_next` | `(self)` | Deliver one due item to its private Routine surface. | [src](../../../core/services/routine_delivery.py#L155) |
| method | `RoutineDeliveryService.settle` | `(self, delivery_id, *, holder, outcome, next_attempt_at=…, receipt=…)` | — | [src](../../../core/services/routine_delivery.py#L190) |
| method | `RoutineDeliveryService.record_terminal_failure` | `(self, *, run_id)` | Record no execution failure state; delivery owns its retry budget. | [src](../../../core/services/routine_delivery.py#L219) |

## `core/services/routine_diagnostics.py`
_Content-free operational failure projections for owner and Jarvis._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `OperationalFailure` | `` | — | [src](../../../core/services/routine_diagnostics.py#L11) |
| function | `_opaque` | `(prefix, value)` | — | [src](../../../core/services/routine_diagnostics.py#L27) |
| function | `_bounded_count` | `(value)` | — | [src](../../../core/services/routine_diagnostics.py#L32) |
| function | `project_failure` | `(exc, metadata)` | — | [src](../../../core/services/routine_diagnostics.py#L39) |
| function | `render_projection` | `(projection)` | — | [src](../../../core/services/routine_diagnostics.py#L62) |
| function | `publish_failure` | `(projection)` | Publish the same fixed-schema projection to operational inbox and app chat. | [src](../../../core/services/routine_diagnostics.py#L72) |

## `core/services/routine_dispatch.py`
_Deterministic execution-path routing for queued Routine occurrences._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RouteOutcome` | `` | — | [src](../../../core/services/routine_dispatch.py#L19) |
| function | `_classification` | `(row)` | — | [src](../../../core/services/routine_dispatch.py#L25) |
| function | `resolve_owner_session` | `(owner_user_id)` | Return (session, state); only a positive ownership stamp may wake. | [src](../../../core/services/routine_dispatch.py#L31) |
| function | `runtime_presence` | `(session_id)` | Return idle/busy/unknown from shared runtime truth and cooldown state. | [src](../../../core/services/routine_dispatch.py#L65) |
| function | `_context` | `(row, generation)` | — | [src](../../../core/services/routine_dispatch.py#L92) |
| function | `_settle_session_run` | `(*, routine_run_id, generation, routine_id, owner_user_id, outcome, visible_run_id, session_id, error=…)` | — | [src](../../../core/services/routine_dispatch.py#L98) |
| function | `_dispatch_session_claimed` | `(row, *, session_id)` | — | [src](../../../core/services/routine_dispatch.py#L136) |
| function | `_dispatch_session` | `(row, *, session_id)` | Serialize the final presence check and synchronous visible-run birth. | [src](../../../core/services/routine_dispatch.py#L206) |
| function | `route_next` | `(runner)` | Route one occurrence. Unknown state leaves it visibly queued. | [src](../../../core/services/routine_dispatch.py#L217) |

## `core/services/routine_identity.py`
_Canonical, fail-closed identity resolution for Routine entry points._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `UnresolvedRoutinePrincipal` | `` | No active canonical account owns the supplied identity token. | [src](../../../core/services/routine_identity.py#L8) |
| function | `resolve_principal` | `(raw_user_id, role_hint=…)` | Resolve a canonical user ID first, then an encrypted Discord mapping. | [src](../../../core/services/routine_identity.py#L12) |

## `core/services/routine_identity_migration.py`
_Explicit users.json -> canonical account cutover for Routine ownership._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `IdentitySourceChanged` | `` | The source registry changed since the reviewed dry-run. | [src](../../../core/services/routine_identity_migration.py#L25) |
| class | `IdentityMigrationConflict` | `` | At least one legacy identity cannot be linked without guessing. | [src](../../../core/services/routine_identity_migration.py#L29) |
| class | `IdentityCutoverItem` | `` | — | [src](../../../core/services/routine_identity_migration.py#L34) |
| class | `IdentityCutoverReport` | `` | — | [src](../../../core/services/routine_identity_migration.py#L44) |
| method | `IdentityCutoverReport.create_count` | `(self)` | — | [src](../../../core/services/routine_identity_migration.py#L49) |
| method | `IdentityCutoverReport.linked_count` | `(self)` | — | [src](../../../core/services/routine_identity_migration.py#L53) |
| method | `IdentityCutoverReport.conflict_count` | `(self)` | — | [src](../../../core/services/routine_identity_migration.py#L57) |
| class | `IdentityCutoverResult` | `` | — | [src](../../../core/services/routine_identity_migration.py#L62) |
| function | `_canonical_id` | `(discord_id)` | — | [src](../../../core/services/routine_identity_migration.py#L67) |
| function | `_fingerprint` | `(discord_id)` | — | [src](../../../core/services/routine_identity_migration.py#L73) |
| function | `_source_payload` | `()` | — | [src](../../../core/services/routine_identity_migration.py#L77) |
| function | `_watermark` | `(source)` | — | [src](../../../core/services/routine_identity_migration.py#L89) |
| function | `_expected_target_matches` | `(external_id, row)` | Verify our deterministic target without treating its ID as proof. | [src](../../../core/services/routine_identity_migration.py#L106) |
| function | `plan_legacy_identity_cutover` | `()` | — | [src](../../../core/services/routine_identity_migration.py#L124) |
| function | `apply_legacy_identity_cutover` | `(*, expected_watermark)` | — | [src](../../../core/services/routine_identity_migration.py#L165) |

## `core/services/routine_inbox.py`
_User-controlled projections of Routine lifecycle events into durable inbox._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineInboxService` | `` | — | [src](../../../core/services/routine_inbox.py#L19) |
| method | `RoutineInboxService.set_user_defaults` | `(self, principal, policy)` | — | [src](../../../core/services/routine_inbox.py#L20) |
| method | `RoutineInboxService.set_override` | `(self, principal, routine_id, override)` | — | [src](../../../core/services/routine_inbox.py#L27) |
| method | `RoutineInboxService.effective_policy` | `(self, principal, routine_id)` | — | [src](../../../core/services/routine_inbox.py#L41) |
| method | `RoutineInboxService.project_event_to_inbox` | `(self, event)` | — | [src](../../../core/services/routine_inbox.py#L55) |
| function | `project_event_to_inbox` | `(event)` | — | [src](../../../core/services/routine_inbox.py#L99) |

## `core/services/routine_run_recorder.py`
_Session-neutral append-only recorder for observable Routine run events._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineRunRecorder` | `` | — | [src](../../../core/services/routine_run_recorder.py#L9) |
| method | `RoutineRunRecorder.append` | `(self, run_id, *, kind, payload, terminal=…, event_id=…, generation=…)` | — | [src](../../../core/services/routine_run_recorder.py#L10) |
| method | `RoutineRunRecorder.list` | `(self, run_id, *, decrypt_for=…)` | — | [src](../../../core/services/routine_run_recorder.py#L24) |

## `core/services/routine_scheduler.py`
_Tidsstyring for Rutiner — én scheduler for ALLE brugere._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_til_dt` | `(vaerdi)` | — | [src](../../../core/services/routine_scheduler.py#L56) |
| function | `_seneste_forekomst` | `(config, *, anchor, now)` | Den seneste planlagte forekomst der ligger på eller før ``now``. | [src](../../../core/services/routine_scheduler.py#L67) |
| function | `_service` | `()` | — | [src](../../../core/services/routine_scheduler.py#L118) |
| function | `fire_due` | `(*, now=…)` | Læg et run i kø for hver rutine hvis forekomst er passeret. | [src](../../../core/services/routine_scheduler.py#L127) |

## `core/services/routine_service.py`
_Authorized lifecycle service for versioned Routine definitions and runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `StaleRoutineVersion` | `` | An edit lost the optimistic version race. | [src](../../../core/services/routine_service.py#L23) |
| class | `InvalidRoutineTransition` | `` | A requested lifecycle transition is not valid from the current state. | [src](../../../core/services/routine_service.py#L27) |
| class | `RoutineView` | `` | — | [src](../../../core/services/routine_service.py#L32) |
| method | `RoutineView.id` | `(self)` | — | [src](../../../core/services/routine_service.py#L55) |
| class | `RunView` | `` | — | [src](../../../core/services/routine_service.py#L60) |
| function | `_routine_view` | `(row)` | — | [src](../../../core/services/routine_service.py#L105) |
| function | `_som_tekst` | `(value)` | Gør et gemt resultat til tekst. | [src](../../../core/services/routine_service.py#L130) |
| function | `_run_view` | `(row)` | — | [src](../../../core/services/routine_service.py#L145) |
| function | `_command_values` | `(command)` | — | [src](../../../core/services/routine_service.py#L164) |
| function | `_apply_classification` | `(values)` | Validér oprettelsens valg og læg den udledte klassifikation i policy'en. | [src](../../../core/services/routine_service.py#L171) |
| class | `RoutineService` | `` | — | [src](../../../core/services/routine_service.py#L195) |
| method | `RoutineService.__init__` | `(self, principal=…)` | — | [src](../../../core/services/routine_service.py#L196) |
| method | `RoutineService._actor` | `(self, supplied=…)` | — | [src](../../../core/services/routine_service.py#L199) |
| method | `RoutineService._actor_and_rest` | `(self, args)` | — | [src](../../../core/services/routine_service.py#L205) |
| method | `RoutineService._project` | `(view, event_type)` | — | [src](../../../core/services/routine_service.py#L211) |
| method | `RoutineService.create_and_activate` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L221) |
| method | `RoutineService.create_proposal` | `(self, principal, *, for_owner, command)` | — | [src](../../../core/services/routine_service.py#L243) |
| method | `RoutineService.get` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L265) |
| method | `RoutineService.update` | `(self, *args, expected_version=…, patch=…, reactivate=…, **changes)` | — | [src](../../../core/services/routine_service.py#L277) |
| method | `RoutineService._transition` | `(self, operation, *args)` | — | [src](../../../core/services/routine_service.py#L313) |
| method | `RoutineService.pause` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L335) |
| method | `RoutineService.resume` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L338) |
| method | `RoutineService.archive` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L341) |
| method | `RoutineService.restore` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L344) |
| method | `RoutineService.stop` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L347) |
| method | `RoutineService.restart` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L363) |
| method | `RoutineService.delete` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L387) |
| method | `RoutineService.enqueue_run` | `(self, *args, trigger_key, execution_context=…)` | — | [src](../../../core/services/routine_service.py#L402) |
| method | `RoutineService.get_run` | `(self, *args, decrypt=…)` | — | [src](../../../core/services/routine_service.py#L424) |
| method | `RoutineService.cancel_run` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L436) |
| method | `RoutineService.list` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L455) |
| method | `RoutineService.list_runs` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L465) |
| method | `RoutineService.list_run_events` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L476) |
| method | `RoutineService.get_inbox_defaults` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L489) |
| method | `RoutineService.set_inbox_defaults` | `(self, policy, *args)` | — | [src](../../../core/services/routine_service.py#L495) |
| method | `RoutineService.get_redacted_diagnostic` | `(self, *args)` | — | [src](../../../core/services/routine_service.py#L505) |
| method | `RoutineService.archive_stopped_before` | `(self, *, now=…)` | — | [src](../../../core/services/routine_service.py#L528) |

## `core/services/routine_types.py`
_Value objects shared by the Routine domain._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RoutineStatus` | `` | — | [src](../../../core/services/routine_types.py#L14) |
| class | `RunStatus` | `` | — | [src](../../../core/services/routine_types.py#L23) |
| class | `AccessScope` | `` | — | [src](../../../core/services/routine_types.py#L33) |
| class | `RoutineExecutionMode` | `` | Hvor en rutine UDFØRES — valgt ved oprettelsen, ikke gættet bagefter. | [src](../../../core/services/routine_types.py#L38) |
| class | `RoutineImportance` | `` | Hvor vigtigt et rutine-resultat er — styrer om indbakken fremhæver det. | [src](../../../core/services/routine_types.py#L61) |
| class | `RoutinePrincipal` | `` | — | [src](../../../core/services/routine_types.py#L76) |
| method | `RoutinePrincipal.user_id` | `(self)` | — | [src](../../../core/services/routine_types.py#L82) |
| class | `RoutineExecutionContext` | `` | — | [src](../../../core/services/routine_types.py#L87) |
| class | `RoutineClassification` | `` | Den udledte klassifikation — gemt i ``delivery_policy['classification']``. | [src](../../../core/services/routine_types.py#L108) |
| method | `RoutineClassification.as_dict` | `(self)` | — | [src](../../../core/services/routine_types.py#L124) |
| class | `RoutineCreate` | `` | — | [src](../../../core/services/routine_types.py#L136) |
| class | `RoutinePatch` | `` | — | [src](../../../core/services/routine_types.py#L161) |
| method | `RoutinePatch.changes` | `(self)` | — | [src](../../../core/services/routine_types.py#L177) |

## `core/services/rule_definitions.py`
_Rule definitions — production rules feeding the rule_engine._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_get` | `(s, *keys, default=…)` | Walk a nested dict; return default if any step is missing. | [src](../../../core/services/rule_definitions.py#L25) |
| function | `_len` | `(s, surface, key=…)` | Count items in a surface list field. | [src](../../../core/services/rule_definitions.py#L38) |
| function | `_open_loop_count` | `(s)` | Populationstallet fra open-loop-fladen, ikke den trunkerede item-side. | [src](../../../core/services/rule_definitions.py#L44) |

## `core/services/rule_engine.py`
_Rule Engine — forward-chaining symbolic inference over signal surfaces._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `RuleConclusion` | `` | One conclusion from one rule firing. | [src](../../../core/services/rule_engine.py#L27) |
| class | `Rule` | `` | One production rule in the engine. | [src](../../../core/services/rule_engine.py#L49) |
| class | `RuleCycleResult` | `` | Result of one full evaluation cycle. | [src](../../../core/services/rule_engine.py#L61) |
| class | `RuleEngine` | `` | Forward-chaining rule engine. | [src](../../../core/services/rule_engine.py#L73) |
| method | `RuleEngine.__init__` | `(self)` | — | [src](../../../core/services/rule_engine.py#L80) |
| method | `RuleEngine.add_rule` | `(self, rule)` | — | [src](../../../core/services/rule_engine.py#L84) |
| method | `RuleEngine.register_rules` | `(self, rules)` | — | [src](../../../core/services/rule_engine.py#L88) |
| method | `RuleEngine.clear_rules` | `(self)` | — | [src](../../../core/services/rule_engine.py#L92) |
| method | `RuleEngine.rules` | `(self)` | — | [src](../../../core/services/rule_engine.py#L97) |
| method | `RuleEngine.evaluate` | `(self, signals)` | Evaluate all rules against current signal state. | [src](../../../core/services/rule_engine.py#L103) |
| method | `RuleEngine.get_rule` | `(self, name)` | — | [src](../../../core/services/rule_engine.py#L136) |
| method | `RuleEngine.rules_by_domain` | `(self, domain)` | — | [src](../../../core/services/rule_engine.py#L142) |
| function | `_get` | `(signals, *keys, default=…)` | Safely dig into nested signal dicts. | [src](../../../core/services/rule_engine.py#L149) |
| function | `signal_value` | `(signals, surface, field, default=…)` | Extract a scalar value from a named surface field. | [src](../../../core/services/rule_engine.py#L160) |
| function | `surface_has` | `(signals, surface)` | Check if a surface exists and has no error. | [src](../../../core/services/rule_engine.py#L170) |
| function | `get_engine` | `()` | — | [src](../../../core/services/rule_engine.py#L185) |
| function | `_load_default_rules` | `(engine)` | Import and register all default rule definitions. | [src](../../../core/services/rule_engine.py#L193) |
| function | `reset_engine` | `()` | Reset the engine (useful for testing or hot-reload). | [src](../../../core/services/rule_engine.py#L201) |
| function | `evaluate_rules` | `(signals)` | Convenience: get engine, evaluate, return result. | [src](../../../core/services/rule_engine.py#L207) |
| function | `get_all_rules` | `()` | Return all registered rules as serializable dicts (for tools). | [src](../../../core/services/rule_engine.py#L212) |
| function | `build_rule_engine_surface` | `()` | — | [src](../../../core/services/rule_engine.py#L224) |
| function | `_emit_rule_fired_event` | `(rule_name, urgency)` | — | [src](../../../core/services/rule_engine.py#L239) |

## `core/services/run_autonomy_context.py`
_Er DEN HER koersel uovervaaget? — run-scopet, ikke gaettet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `set_autonomous` | `(vaerdi)` | Markér koerslen. Returnerer token'et saa kalderen kan nulstille. | [src](../../../core/services/run_autonomy_context.py#L34) |
| function | `reset_autonomous` | `(token)` | — | [src](../../../core/services/run_autonomy_context.py#L39) |
| function | `is_autonomous` | `()` | Kaster aldrig. Ved vi det ikke, er svaret NEJ — og saa opfoerer alt sig | [src](../../../core/services/run_autonomy_context.py#L55) |
| function | `set_autonomous_budget` | `(*, max_tool_calls=…, max_seconds=…)` | — | [src](../../../core/services/run_autonomy_context.py#L79) |
| function | `consume_autonomous_tool_budget` | `()` | Reserve one tool call, or refuse it after the deadline/ceiling. | [src](../../../core/services/run_autonomy_context.py#L88) |
| function | `autonomous_budget_state` | `()` | — | [src](../../../core/services/run_autonomy_context.py#L103) |
| function | `set_user_present` | `(vaerdi)` | Markér om der er et menneske i den anden ende. Returnerer token'et. | [src](../../../core/services/run_autonomy_context.py#L129) |
| function | `reset_user_present` | `(token)` | — | [src](../../../core/services/run_autonomy_context.py#L134) |
| function | `user_present` | `()` | Er der et menneske i den anden ende af DENNE kørsel? Kaster aldrig. | [src](../../../core/services/run_autonomy_context.py#L141) |
| function | `set_run_identity` | `(run_id, origin=…)` | — | [src](../../../core/services/run_autonomy_context.py#L174) |
| function | `current_run_id` | `()` | "" naar ingen koersel har sat det. Kaster aldrig. | [src](../../../core/services/run_autonomy_context.py#L179) |
| function | `current_origin` | `()` | "" for en almindelig brugertur, eller naar vi ikke ved det. | [src](../../../core/services/run_autonomy_context.py#L187) |

## `core/services/run_closure_gate.py`
_Run-closure gate — fang tomme replies og unstaged changes efter agentic runs._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git_porcelain_status` | `(*, cwd=…)` | Return the set of path-strings reported by ``git status --porcelain``. | [src](../../../core/services/run_closure_gate.py#L67) |
| function | `_git_dirty_content_hashes` | `(*, cwd=…)` | Return {path: content_hash} for every file currently dirty in working tree. | [src](../../../core/services/run_closure_gate.py#L86) |
| function | `_record_pre_run_state` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L165) |
| function | `_pop_pre_run_state` | `(run_id)` | Return pre-run snapshot, or ``None`` if no snapshot was recorded. | [src](../../../core/services/run_closure_gate.py#L174) |
| function | `_set_current_run` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L203) |
| function | `_get_current_run` | `()` | — | [src](../../../core/services/run_closure_gate.py#L209) |
| function | `_set_current_origin` | `(origin)` | — | [src](../../../core/services/run_closure_gate.py#L217) |
| function | `aktuel_origin` | `()` | Hvad startede den koersel der er i gang? "" naar vi ikke ved det. | [src](../../../core/services/run_closure_gate.py#L223) |
| function | `_record_tool_call` | `(run_id, tool_name)` | — | [src](../../../core/services/run_closure_gate.py#L234) |
| function | `_pop_tool_calls` | `(run_id)` | — | [src](../../../core/services/run_closure_gate.py#L248) |
| function | `_summarize_unstaged` | `(diff, limit=…)` | Build a structured summary of new unstaged/untracked paths. | [src](../../../core/services/run_closure_gate.py#L256) |
| function | `_is_auto_commit_excluded` | `(path)` | True hvis en path er et arbejdsartefakt der aldrig skal committes. | [src](../../../core/services/run_closure_gate.py#L293) |
| function | `_git_staged_paths` | `(*, cwd=…)` | Return paths currently staged in the index. | [src](../../../core/services/run_closure_gate.py#L301) |
| function | `_try_auto_commit` | `(touched_paths, *, run_id, session_id, focus)` | Commit filer rørt under et autonomt run. Return short-hash eller None. | [src](../../../core/services/run_closure_gate.py#L320) |
| function | `_registrer_i_indbakken` | `(*, kildetype, kilde_id, beskrivelse, run_id=…, session_id=…, kilde_ejer=…)` | Læg gatens besked i INDBAKKEN i stedet for at sende den til Discord. | [src](../../../core/services/run_closure_gate.py#L424) |
| function | `_on_run_completed` | `(payload)` | Handle a runtime.autonomous_run_completed event. | [src](../../../core/services/run_closure_gate.py#L477) |
| function | `_on_run_started` | `(payload)` | Handle runtime.autonomous_run_started — snapshot git state. | [src](../../../core/services/run_closure_gate.py#L790) |
| function | `_on_tool_used` | `(payload)` | Track tool calls so we can detect silent runs. | [src](../../../core/services/run_closure_gate.py#L805) |
| function | `_listener_loop` | `(q)` | — | [src](../../../core/services/run_closure_gate.py#L821) |
| function | `start_run_closure_gate` | `()` | Start the eventbus subscriber thread. Safe to call multiple times. | [src](../../../core/services/run_closure_gate.py#L849) |
| function | `stop_run_closure_gate` | `()` | — | [src](../../../core/services/run_closure_gate.py#L874) |

