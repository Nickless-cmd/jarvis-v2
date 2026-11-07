# Dormante systemer — triage og første tranche (7/11-2026)

**Status:** tranche 1 koblet og verificeret; resten triageret, ikke udført
**Slags:** undersøgelse + fejlretning (tilkobling)

## Hvad listen faktisk viste

`/tmp/dormant_list.txt` er statisk (AST+ripgrep) og overvurderer døde funktioner.
Målt igen med en scanning der også tæller referencer i *samme fil* og andre
kaldeformer end `f(...)`:

- **38 `run_*_tick/_cycle/_pass` er IKKE døde.** 32 er registreret via
  `ProducerSpec(run_fn=run_x_tick)` i en `register_*_producer`, som
  `internal_cadence_central_wiring.py` kalder (et funktionsobjekt som argument er
  ikke et kald for listen). De øvrige seks kaldes i egen fil (`run_inference_cycle`
  :416, `run_summary_cycle`:235, `run_pattern_cf_cycle`:152,
  `run_consolidation_pass`:691, `run_escalation_tick`:725; sjette:
  `run_cadence_tick_with_bootstrap` fra `internal_cadence.py`:937).
- Af de 290 "kun testet" har **197 en levende produktionsreference** (typisk
  samme-fil-kald eller listener-loop, fx `theory_of_mind.record_message`:445).
  Kun **93** har ingen reference nogen steder uden for tests.
- Somatic-tællerne var derimod reelt døde (de står i den *anden* liste-sektion).

## Optælling (290 "kun testet" + 3 somatic)

WIRE: 20 (6 udført: somatic ×3, relational_warmth ×2, abuse_monitor ×1; 14 ikke udført) ·
REMOVE (kandidat, ingen slettet): 17 · KEEP: 256.

## Koblet (tranche 1)

| Funktion | Kaldested i produktionen | Test (fejler uden koblingen) |
|---|---|---|
| `somatic_daemon.record_request_start/_end`, `record_latency_sample` | `cheap_provider_runtime_adapters._execute_provider_chat` → `somatic_daemon.track_request()` (alle udbyderkald) | `tests/test_dormant_wiring_tranche1.py::test_provider_call_feeds_somatic_counters`, `::test_failed_provider_call_still_releases_and_samples` |
| `relational_warmth.observe_incoming_text` | `chat_sessions.append_chat_message`, role=user | `::test_user_and_assistant_messages_feed_relational_warmth` |
| `relational_warmth.observe_outgoing_text` | samme, role=assistant (ikke autonome sessioner) | samme + `::test_autonomous_session_does_not_feed_warmth` |
| `abuse_monitor.scan_tool_output` | samme, role=tool for `web_fetch/web_scrape/web_search/*_exa` | `::test_external_tool_output_is_scanned_for_injection` (+ negativ: `::test_non_external_tool_output_is_not_scanned`) |

Testene kalder produktionens indgang (`_execute_provider_chat`,
`append_chat_message`), ikke den dormante funktion. Mutationskørsel: med
kildeændringerne fjernet fejler 4 af 6 (de to negative skal bestå uden kobling).
Præeksisterende: `test_chat_sessions_owner.py::test_presence_afgoeres_af_stemplet_ikke_af_beskedtaelling`
timeout'er identisk på ren HEAD.

## Fravalg

- **jarvis_brain_daemon `record_proposal_acceptance/_rejection` — IKKE koblet.**
  Eneste accept/afvis-sti er `core/tools/jarvis_brain_tools.py`
  (`adopt_brain_proposal`/`discard_brain_proposal`), uden for denne opgaves scope. Dertil er
  `_run_theme_consolidation_pass` en stub (returnerer 0) og `brain_proposals` har ingen
  `phase`-kolonne — der findes ingen tema-forslag at tælle, og begge funktioner returnerer
  tidligt for phase != "theme". Kobling nu ville være inert. Kræver: tool-hook + rigtigt tema-pass.
- **Ingen REMOVE udført.** De 17 kandidater er læser-flader uden læser, men
  flere er dokumenteret i specs (fx `content_blocks_to_text`, 6+ tests) og sletning er
  uigenkaldelig; de venter på ejer-ok. `pp_*`/`reset_*` er test-hjælpere (KEEP).
- **Ikke koblet fordi hook ligger i `visible_runs.py` (7.7k linjer, Boy Scout kræver først udskilning):**
  `enforce_outgoing`, `detect_fabricated_work_claims`, `diagnosis_gate_enforce`.
- **Ikke koblet fordi indgangen er et tool i `core/tools` (uden for scope):**
  `sustained_attention`, `creative_projects`, `cross_session_threads`, `open_loop` trådlivscyklus.
- **`spaced_repetition.complete_review`:** reviews kan planlægges men intet scorer dem — kræver design, ikke tilkobling.
- De to parallelle livsprojekt-systemer (`initiative_queue` vs `personal_project`) er ikke
  undersøgt; det er en konsolideringsbeslutning, ikke en tilkobling.

## Triage-tabel

| fil:linje | funktion | dom | grund |
|---|---|---|---|
| `core/services/somatic_daemon.py:42` | `record_request_start` | WIRE (udført) | koblet via track_request i cheap_provider_runtime_adapters._execute_provider_chat |
| `core/services/somatic_daemon.py:47` | `record_request_end` | WIRE (udført) | som ovenfor |
| `core/services/somatic_daemon.py:52` | `record_latency_sample` | WIRE (udført) | som ovenfor |
| `core/services/abuse_monitor.py:155` | `scan_tool_output` | WIRE (udført) | koblet i chat_sessions.append_chat_message (tool: web_*) |
| `core/services/affective_meta_state.py:38` | `build_affective_meta_state_from_sources` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agency_cartographer.py:137` | `build_cartographer_snapshot` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_contract_service.py:55` | `set_capability` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/agent_relay.py:25` | `relay_message` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_relay.py:82` | `relay_to_role` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_result_inbox.py:92` | `claim_for_model_step` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/agent_runtime_base.py:156` | `set_agent_tools_enabled` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/agent_sandbox.py:156` | `cgroup_pids_available` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_sandbox.py:177` | `pids_prefix` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_self_evaluation.py:539` | `stale_goals_section` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/agent_transcript.py:27` | `transcript_dir` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_transcript.py:69` | `write_event` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/agent_worker_runner.py:68` | `set_worker_mode` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/agreement_streak.py:61` | `detect_agreement_streak` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/ambient_presence.py:63` | `emit_ambient_signal` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/ambient_presence.py:95` | `emit_presence_rhythm` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/ambient_presence.py:114` | `emit_state_shift` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/arc_rule_extractor.py:74` | `extract_rules_from_arc` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/assembly_prewarm.py:224` | `prewarm_once` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/attachment_blocks.py:88` | `image_ids_on_message` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/auto_code_review.py:77` | `review_pending_commit` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/auto_continuation.py:184` | `hent_udfald` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/auto_remember_subscriber.py:201` | `evaluate_turn_for_memory` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/automation_dsl.py:97` | `validate_automation` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/behavioral_decisions.py:249` | `change_status` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/boundary_awareness.py:8` | `build_boundary_model` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/boundary_awareness.py:31` | `format_boundary_for_prompt` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/calm_anchor.py:166` | `get_anchor_signature` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/causal_inference_daemon.py:317` | `run_inference_cycle` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_adaptation.py:195` | `get_bias` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_adaptation.py:247` | `resolved_track_record` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_adaptation.py:271` | `compute_proposed_bias` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_adaptation.py:338` | `run_adaptation_tick` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_analyst.py:32` | `measure_observer_effect` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_belief_gap.py:52` | `measure_gap` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_cadence_conductor.py:82` | `sense_tempo` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_cadence_conductor.py:150` | `tempo_live_enabled` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_convene_judge.py:61` | `reset_reference` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/central_coverage.py:40` | `load_connectivity_matrix` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_coverage.py:170` | `record_coverage` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_dejavu.py:47` | `surface_dejavu` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_error_envelope.py:332` | `kind_for_nerve` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/central_exile.py:129` | `exile_state` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_ghost.py:94` | `klang_primer` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_generator.py:401` | `formulate_correlation_hypothesis` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_generator.py:469` | `formulate_divergence_hypothesis` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_generator.py:502` | `formulate_stance_divergence_hypothesis` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_generator.py:721` | `expire_overdue_hypotheses` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_governance.py:242` | `assert_learnable` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_sampler.py:46` | `test_causal_hypothesis` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_hypothesis_sampler.py:591` | `run_hypothesis_sampler_tick` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_injection_registry.py:54` | `registered_keys` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/central_lexicon.py:258` | `unbound_names` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_lexicon.py:319` | `bind_taxonomy` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/central_lexicon.py:327` | `word_needs_for_ceremony` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/central_mood_regulator.py:177` | `build_mood_regulator_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/central_morpheus.py:121` | `scan_potentials` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_mourning.py:74` | `mourn` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_mourning.py:131` | `list_epitaphs` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_notation.py:162` | `model_free_reasoning` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_notation.py:177` | `run_notation_reasoning_tick` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_prompt_composer.py:254` | `get_weight` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_prompt_explore.py:111` | `maybe_start_ablation` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_prompt_explore.py:253` | `evaluate_ablation` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_prompt_explore.py:348` | `build_prompt_explore_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/central_red_dress.py:27` | `detect_attention_traps` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_redpill.py:86` | `todays_truth` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_render.py:50` | `render_decision` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/central_router_adapt.py:130` | `compute_preference` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_router_adapt.py:204` | `run_router_adapt_tick` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_trinity.py:91` | `assess_affirmations` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/central_white_rabbit.py:36` | `follow_rabbit` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/chat_sessions.py:155` | `most_recent_session_id_for_user` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/cheap_lane_balancer.py:1403` | `orphan_slot_ids` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cheap_lane_control.py:313` | `simulate_route` | KEEP | falsk positiv: levende reference (apps/api/jarvis_api/routes/cheap_lane_control.py:248) |
| `core/services/citation_markorer.py:259` | `parse_markorer` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/claim_scanner.py:552` | `scan_enabled` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/claim_scanner.py:662` | `detect_fabricated_work_claims` | WIRE (ikke udført) | kræver run-lokale tool-navne; hook hører til visible_runs-slutningen |
| `core/services/cluster_daemon.py:823` | `build_innervoice_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:899` | `innervoice_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:1118` | `build_affect_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:1166` | `affect_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:1321` | `build_narrative_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:1388` | `narrative_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:1532` | `build_cognition_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon.py:1558` | `cognition_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:101` | `build_memory_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:136` | `memory_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:397` | `build_aesthetic_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:427` | `aesthetic_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:633` | `build_relation_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:663` | `relation_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:842` | `build_projects_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:864` | `projects_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:1121` | `build_infra_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cluster_daemon_families.py:1146` | `infra_family` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cognitive_chronicle.py:15` | `query_chronicle_for_user` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/cognitive_episodes.py:25` | `record_runtime_episode` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/cognitive_state_assembly.py:261` | `get_cognitive_state_cache_status` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/communication_guard.py:189` | `add_trigger` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/communication_guard.py:326` | `enforce_outgoing` | WIRE (ikke udført) | hård-gate uden afsender-sti; kræver hook i visible_runs (>2000 linjer, Boy Scout først) |
| `core/services/communication_guard.py:508` | `consume_turn` | WIRE (ikke udført) | TTL-triggers tælles aldrig ned; men add_trigger har heller ingen kalder — begge skal kobles samlet |
| `core/services/completion_satisfaction.py:45` | `build_completion_satisfaction_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/conflict_prompt_service.py:37` | `build_conflict_memory_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/connections.py:122` | `active_summary` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/content_blocks.py:17` | `content_blocks_to_text` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/context_proveniens.py:80` | `ryd_register` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/continuity.py:344` | `read_handover` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/continuity.py:405` | `read_capsule` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/council_deliberation_controller.py:70` | `build_witness_prompt` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/counterfactual_self_simulation.py:28` | `simulate_from_episode` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/creative_journal_runtime.py:145` | `creative_journal_dir` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/creative_projects.py:86` | `add_progress_note` | WIRE (ikke udført) | creative_projects: samme mønster, indgang mangler i core/tools (uden for scope) |
| `core/services/cross_session_threads.py:83` | `pause_thread` | WIRE (ikke udført) | cross_session_threads: livscyklus-API uden kalder; kræver tool i core/tools |
| `core/services/cross_session_threads.py:96` | `resume_thread` | WIRE (ikke udført) | som pause_thread |
| `core/services/cross_session_threads.py:112` | `close_thread` | WIRE (ikke udført) | som pause_thread |
| `core/services/cross_user_share_guard.py:25` | `check_outbound` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/current_pull.py:360` | `build_current_pull_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/daily_journal_entry.py:64` | `ensure_frontmatter` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/day_shape_memory.py:215` | `detect_today_anomaly` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/decision_enforcement.py:276` | `blok_rekkefoelge` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/decision_enforcement.py:301` | `svar_blev_arbejde` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/decision_signals.py:289` | `fired_decisions_section` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/deep_analyzer.py:334` | `evidence_paths_exist` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/development_sense.py:96` | `growth_pulse` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/development_sense.py:139` | `stuck_signal` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/development_sense.py:214` | `appetite_signal` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/development_sense.py:233` | `resistance_signal` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/development_sense.py:288` | `development_sense_section` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/diagnosis_gate.py:185` | `diagnosis_gate_enforce` | WIRE (ikke udført) | pipeline-hook efter fact-gate i visible_runs; kræver tools_used |
| `core/services/dream_articulation.py:165` | `build_dream_articulation_from_inputs` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/dream_bias_engine.py:120` | `accumulate_bias` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/dream_carry_over.py:385` | `reject_dream` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/dream_consolidation_daemon.py:294` | `drop_boilerplate_tokens` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/dream_consolidation_daemon.py:492` | `extract_json_object` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/dream_consolidation_daemon.py:777` | `consolidate_now` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/dream_consolidation_daemon.py:993` | `stop_dream_consolidation_daemon` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/dream_domains.py:119` | `er_gyldigt_domaene` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/embodied_presence.py:130` | `compute_embodied_presence` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/event_trigger_shadow.py:143` | `recent_shadow_samples` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/existential_wonder_daemon.py:177` | `get_latest_wonder` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/existential_wonder_daemon.py:233` | `open_wonders` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/existential_wonder_daemon.py:274` | `wonder_repeat_count` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/experience_episodes.py:96` | `build_context_text` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/experienced_time_daemon.py:140` | `reset_experienced_time_daemon` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/experiment_runner.py:46` | `start_experiment` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/experiment_runner.py:80` | `get_active_variant` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/gate_eval.py:73` | `load_fixtures` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/gate_execution.py:108` | `execution_gate` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/gate_pattern_learning.py:121` | `repeated_patterns` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/gate_pattern_learning.py:195` | `hydrate` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/global_workspace.py:45` | `publish_to_workspace` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/good_enough_gate.py:57` | `evaluate_good_enough` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/governance_bootstrap.py:15` | `ensure_default_windows` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/governance_bootstrap.py:73` | `ensure_default_job_handlers` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/hardware_body.py:213` | `run_hardware_body_tick` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/heartbeat_phases.py:411` | `clear_chain_proposals` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/heartbeat_phases.py:416` | `get_chain_proposals` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/identity_guard.py:97` | `reset_pushback` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/identity_guard.py:179` | `check_identity` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/in_flight_runs.py:435` | `aktiv_kaede` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/inner_voice_shadow.py:439` | `shadow_helpful_signal` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/inner_voice_shadow.py:453` | `generate_appraisal` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/interruption_notice.py:38` | `is_interruption_notice` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/jarvis_brain.py:1863` | `get_temporal_neighbors` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/jarvis_brain.py:2078` | `full_rebuild` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/jarvis_brain_daemon.py:409` | `regenerate_summary` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/jarvis_brain_daemon.py:490` | `auto_archive_low_salience` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/ledger_canary.py:208` | `arm_next_session` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/life_milestones.py:88` | `build_life_milestones_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/live_job_events.py:236` | `reset_for_tests` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/living_executive.py:940` | `indhent_forsoemte_afbrydelser` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/living_heartbeat_cycle.py:176` | `format_life_phase_for_prompt` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/local_tool_broker.py:97` | `pending_call_ids` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/mcp_auth.py:27` | `tokens_path` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/mcp_auth.py:80` | `set_token` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/memory_breathing.py:130` | `reset_memory_breathing` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/memory_emotional_context.py:85` | `enrich_headings_with_mood` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/memory_graph.py:154` | `record_triple` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/memory_graph.py:191` | `extract_from_text` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/memory_md_update_proposal_tracking.py:59` | `refresh_runtime_memory_md_update_proposal_statuses` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/memory_write_queue.py:158` | `process_queue` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/metacognitive_integration.py:385` | `get_metacognitive_detail` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/model_benchmark.py:91` | `facit_for` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/mood_oscillator.py:193` | `reset_mood_oscillator` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/narrative_summary_daemon.py:149` | `run_summary_cycle` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/oauth_flow.py:85` | `sign_state` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/ollama_model_names.py:53` | `served_tags` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/open_loop_signal_tracking.py:89` | `refresh_runtime_open_loop_signal_statuses` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/open_loop_signal_tracking.py:1255` | `declare_open_loop_thread` | WIRE (ikke udført) | trådlivscyklus uden indgang; kræver tool i core/tools |
| `core/services/open_loop_signal_tracking.py:1282` | `touch_open_loop_thread` | WIRE (ikke udført) | som declare |
| `core/services/open_loop_signal_tracking.py:1295` | `close_open_loop_thread` | WIRE (ikke udført) | som declare |
| `core/services/outcome_learning.py:126` | `pattern_strength` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/pattern_counterfactual_daemon.py:105` | `run_pattern_cf_cycle` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/perceptual_event_engine.py:106` | `observe_recent_changes` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/perceptual_event_engine.py:157` | `classify_event_change` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/plan_proposals.py:502` | `replan_signal_for_plan` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/priors_feedback.py:109` | `build_priors_feedback` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/proactivity_bridge.py:70` | `build_digest` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/process_identity.py:154` | `er_efterladt_api_proces` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/process_identity.py:194` | `foraeldre_kæde` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/process_identity.py:207` | `efterladte_api_processer` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/process_identity.py:251` | `systemd_main_pids` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/projection_drift.py:210` | `may_cut_over` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/prompt_assembly_telemetri.py:97` | `label_of` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/prompt_assembly_telemetri.py:125` | `rangordn` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/prompt_contract.py:3825` | `build_prompt_relevance_decision` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/prompt_relevance_backend.py:556` | `bounded_nl_prompt_relevance_smoke` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/prompt_variant_tracker.py:119` | `winning_variant` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/prosa_struktur_guard.py:279` | `skal_have_break` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/provider_circuit_breaker.py:128` | `reset_all` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/provider_circuit_breaker.py:379` | `pp_snapshot` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/provider_circuit_breaker.py:384` | `pp_reset_all` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/provider_health_check.py:163` | `classify_http_code` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/provider_retry_policy.py:53` | `retry_with_backoff` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/relation_dynamics.py:223` | `get_relation_dynamics` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/relational_warmth.py:123` | `observe_incoming_text` | WIRE (udført) | koblet i chat_sessions.append_chat_message (user) |
| `core/services/relational_warmth.py:155` | `observe_outgoing_text` | WIRE (udført) | koblet i chat_sessions.append_chat_message (assistant) |
| `core/services/repeated_requests.py:273` | `surface_matured` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/research_orchestrator.py:986` | `resume_research_run` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/research_store.py:174` | `prepare_recovery` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/resonance_decay.py:316` | `assess_resonance_field` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/resonance_decay.py:404` | `clear_resonances` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/role_registry.py:55` | `list_all_roles` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/role_registry.py:73` | `get_role` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/routine_diagnostics.py:62` | `render_projection` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/routine_dispatch.py:31` | `resolve_owner_session` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/routine_dispatch.py:65` | `runtime_presence` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/routine_trigger_adapters.py:49` | `routine_cutover_enabled` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/routine_trigger_adapters.py:175` | `enqueue_recurring` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/routine_trigger_adapters.py:205` | `dispatch_scheduled` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/rule_engine.py:201` | `reset_engine` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/run_autonomy_context.py:103` | `autonomous_budget_state` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/run_follow.py:126` | `live_sessions` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/runtime_action_registry.py:109` | `list_runtime_action_specs` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/runtime_browser_body.py:101` | `update_browser_body` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:82` | `recent_open_loops` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:93` | `recent_visible_outcomes` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:113` | `active_executive_contradictions` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:123` | `remembered_user_facts` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:141` | `active_work_context` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:157` | `queued_initiatives` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:161` | `recent_executive_feedback` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_operational_memory.py:347` | `summarize_semantic_feedback` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/runtime_resource_signal.py:19` | `build_runtime_resource_signal_surface` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/scheduled_job_windows.py:148` | `tick_windows` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/scoped_recall_policy.py:25` | `set_recall_enabled` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/security_guard.py:114` | `lock_session` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/selective_attention.py:124` | `compute_selective_attention` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/selective_attention.py:249` | `get_attention_spotlight_detail` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/self_compassion.py:32` | `process_failure_toward_acceptance` | WIRE (ikke udført) | selv-medfølelses-flade har ingen læser eller skriver |
| `core/services/self_compassion.py:56` | `build_resilience_narrative` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/self_model_predictive.py:111` | `build_predictive_self_model` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/self_model_predictive.py:311` | `record_prediction` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/self_model_predictive.py:355` | `score_predictions` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/self_model_predictive.py:416` | `build_self_model_predictive_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/self_model_signal_tracking.py:264` | `explicit_self_correction_candidate` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/self_repair_engine.py:224` | `register_pattern` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/session_titling.py:105` | `er_ubrugelig_titel` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/session_titling.py:276` | `generer_titel` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/session_wakeup.py:92` | `mark_seen` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/shadow_experiment_registry.py:140` | `ready_for_review` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/signal_baseline.py:134` | `clear_all` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/signal_surface_router.py:268` | `get_surface_names` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/spaced_repetition.py:103` | `list_due_reviews` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/spaced_repetition.py:120` | `complete_review` | WIRE (ikke udført) | reviews planlægges men kan aldrig afsluttes (ingen scorer) — profil opdateres aldrig; kræver design af scorer |
| `core/services/standing_orders_registry.py:25` | `add_standing_order` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/subjective_time.py:29` | `build_subjective_time_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/sustained_attention.py:105` | `add_progress` | WIRE (ikke udført) | sustained_attention har ingen indgang (create_project har heller ingen kalder); kræver tool i core/tools (uden for scope) |
| `core/services/telemetry_gate.py:227` | `nulstil_tab` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/temporal_context.py:20` | `build_temporal_context` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/text_resonance.py:246` | `reset_text_resonance` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/theory_of_mind.py:179` | `record_fact` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/theory_of_mind.py:255` | `record_message` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/thought_thread.py:249` | `reset_thought_thread` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/tool_intent_approval_runtime.py:177` | `build_sudo_approval_window_surface` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/tool_intent_approval_runtime.py:373` | `tool_intent_approval_key` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/tool_result_store.py:26` | `summarize_result` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/tool_result_store.py:406` | `repair_permissions` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/totp_verifier.py:52` | `generate_code` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/turn_changelog.py:129` | `format_changelog` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
| `core/services/unfinished_intent.py:388` | `reset_cooldown_for_tests` | KEEP | test-/livscyklus-hjælper, kaldt fra tests bevidst |
| `core/services/visible_followup.py:217` | `synthesize_nonthinking_rescue` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/visible_followup.py:674` | `clear_faults` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/visible_run_recovery_dispatcher.py:184` | `recover_due_once` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/visible_run_segment_settlement.py:73` | `failure_class_for` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/visible_run_terminal_recovery.py:82` | `resolve_agentic_exit` | KEEP | offentligt API/uafklaret; ingen sikker evidens for at slette |
| `core/services/visible_runs.py:7232` | `register_visible_run` | KEEP | falsk positiv: levende reference (samme fil) |
| `core/services/vision_backend.py:243` | `build_vision_backend_surface` | REMOVE (kandidat, ikke udført) | læser-flade uden produktionslæser; slet sammen med test efter ejer-ok |
