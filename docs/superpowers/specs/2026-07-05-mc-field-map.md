---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# Mission Control — Komplet feltkortlægning

**Dato:** 5. juli 2026  
**Forfatter:** Jarvis  
**Formål:** Fuld kortlægning af alle felter i alle MC-tabs + Central-tabs. Grundlag for CLI-klientens data-model.

---

## Central-tabs

### `/central/realtime`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `status` | str | Overordnet status: green/yellow/red |
| `coverage` | dict | Nerver, clusters, security_clusters, trace_buffer |
| `diagnose` | dict | decide_ok, observe_ok, degraded |
| `feed` | list | Seneste nerve-fyringer |
| `incidents` | list | Åbne incidents |
| `open_breakers` | list | Åbne circuit breakers |
| `config_drift` | dict | Konfigurationsafvigelse |
| `learning` | dict | Læringstilstand |
| `processes` | dict | Kørende processer |
| `anomalies` | dict | Anomalier (counts + recent) |
| `known_signals` | list | Promoverede signaler |
| `clusters` | dict | Cluster-status |

### `/central/diagnostics`
(Eksporteret via route, felter afhænger af `build_diagnostics_surface()`)

### `/central/providers`
(Eksporteret via route, felter afhænger af `build_providers_surface()`)

### `/central/governance`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| Returnerer liste af dicts | list[dict] | Hver dict: key, label, kind, dangerous, value, options |

---

## MC-tabs

### `/mc/overview`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `ok` | bool | Overordnet sundhed |
| `events` | list | Seneste events |
| `cost_rows` | list | Omkostningsrækker |
| `input_tokens` | int | Samlede input tokens |
| `output_tokens` | int | Samlede output tokens |
| `total_cost_usd` | float | Samlede omkostninger |
| `runtime` | dict | Runtime-status |
| `visible_execution` | dict | Synlig eksekveringstilstand |
| `visible_run` | dict | Synlig kørselstilstand |
| `capability_invocation` | dict | Capability-kald |
| `latest_event` | dict | Seneste event |
| `latest_cost` | dict | Seneste omkostning |

### `/mc/jarvis`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `summary` | str | Sammenfatning |
| `state` | dict | Indre tilstand |
| `memory` | dict | Hukommelsesstatus |
| `development` | dict | Udviklingsstatus |
| `continuity` | dict | Kontinuitet |
| `heartbeat` | dict | Heartbeat-status |
| `brain` | dict | Brain-status |
| `self_knowledge` | dict | Selverkendelse |
| `cognitive_frame` | dict | Kognitiv ramme |

### `/mc/cognitive-frame`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `mode` | str | Kognitiv tilstand |
| `salient_items` | list | Fremtrædende elementer |
| `affordances` | list | Handlingsmuligheder |
| `temporal` | dict | Tidslig kontekst |
| `continuity_pressure` | float | Kontinuitetstryk |
| `private_signal_pressure` | float | Privat signaltryk |
| `private_signal_items` | list | Private signaler |
| `continuity_mode` | str | Kontinuitetsmode |
| `cognitive_experiment_carry` | dict | Eksperiment-bæring |
| `cognitive_episode_carry` | dict | Episode-bæring |
| `theory_of_mind_carry` | dict | Theory of mind |
| `learning_policy_carry` | dict | Læringspolitik |
| `perception_carry` | dict | Perceptions-bæring |
| `emotional_memory_carry` | dict | Emotionel hukommelse |
| `experiential_support` | dict | Erfaringsstøtte |
| `active_constraints` | list | Aktive begrænsninger |
| `counts` | dict | Tællinger |
| `summary` | str | Sammenfatning |

### `/mc/embodied-state`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `state` | str | Primær tilstand |
| `primary_state` | str | Primær tilstand (kanonisk) |
| `strain_level` | float | Belastningsniveau |
| `recovery_state` | str | Genoprettelsestilstand |
| `stability` | float | Stabilitet |
| `summary` | str | Sammenfatning |
| `freshness` | float | Friskhed |
| `facts` | list | Fakta |
| `seam_usage` | dict | Søm-forbrug |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `kind` | str | Slags |

### `/mc/affective-meta-state`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `state` | str | Affektiv tilstand |
| `bearing` | str | Bæring |
| `monitoring_mode` | str | Overvågningstilstand |
| `reflective_load` | float | Refleksiv belastning |
| `live_emotional_state` | dict | Live emotionel tilstand |
| `summary` | str | Sammenfatning |
| `source_contributors` | list | Kilde-bidragydere |
| `freshness` | float | Friskhed |
| `seam_usage` | dict | Søm-forbrug |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `kind` | str | Slags |

### `/mc/self-knowledge`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active_capabilities` | list | Aktive kapabiliteter |
| `approval_gated` | list | Godkendelses-gated |
| `passive_inner_forces` | list | Passive indre kræfter |
| `structural_constraints` | list | Strukturelle begrænsninger |
| `unavailable_or_inactive` | list | Utilgængelige/inaktive |
| `summary` | str | Sammenfatning |

### `/mc/attention-budget`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `profiles` | dict | Opmærksomhedsprofiler |
| `micro_cognitive_frame` | dict | Mikro kognitiv ramme |
| `micro_frame_chars` | int | Mikro ramme tegn |
| `live_traces` | list | Live spor |

### `/mc/unconscious-temperature-field`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `enabled` | bool | Aktiveret |
| `current_field` | str | Nuværende felt |
| `valens` | str | Valens |
| `arousal` | float | Arousal |
| `intensity` | float | Intensitet |
| `conflict` | float | Konflikt |
| `rationale` | str | Begrundelse |
| `summary` | str | Sammenfatning |

### `/mc/dream-articulation`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `truth` | str | Sandhed |
| `kind` | str | Slags |
| `boundary` | str | Grænse |
| `last_run_at` | str | Sidste kørsel |
| `last_result` | str | Sidste resultat |
| `latest_artifact` | str | Seneste artefakt |
| `cadence` | dict | Kadence |
| `summary` | str | Sammenfatning |
| `source` | str | Kilde |
| `built_at` | str | Bygget |

### `/mc/dream-distillation`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `residue` | dict | Reststof |
| `created_at` | str | Oprettet |
| `expires_at` | str | Udløber |
| `last_trigger` | str | Sidste trigger |
| `chronicle_periods` | list | Chronicle-perioder |
| `approval_states` | dict | Godkendelses-tilstande |
| `summary` | str | Sammenfatning |

### `/mc/dream-influence`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `influence_state` | str | Indflydelsestilstand |
| `influence_target` | str | Indflydelsesmål |
| `influence_mode` | str | Indflydelsesmode |
| `influence_strength` | float | Indflydelsesstyrke |
| `influence_hint` | str | Indflydelsestip |
| `confidence` | float | Sikkerhed |
| `summary` | str | Sammenfatning |
| `source_contributors` | list | Kilde-bidragydere |
| `freshness` | float | Friskhed |
| `seam_usage` | dict | Søm-forbrug |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `boundary` | str | Grænse |
| `kind` | str | Slags |

### `/mc/dream-hypotheses`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `summary` | str | Sammenfatning |
| `pending` | list | Ventende |
| `recent_presented` | list | Senest præsenterede |

### `/mc/loop-runtime`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `kind` | str | Slags |
| `items` | list | Elementer |
| `summary` | str | Sammenfatning |
| `freshness` | float | Friskhed |
| `seam_usage` | dict | Søm-forbrug |

### `/mc/self-critique`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `enabled` | bool | Aktiveret |
| `path` | str | Sti |
| `docs` | str | Dokumentation |
| `summary` | str | Sammenfatning |

### `/mc/finitude`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `enabled` | bool | Aktiveret |
| `birth_commit` | str | Fødsels-commit |
| `birth_date` | str | Fødselsdato |
| `latest_transition` | str | Seneste overgang |
| `latest_compaction` | str | Seneste kompaktion |
| `appraisals` | list | Vurderinger |
| `last_annual_year` | str | Sidste årlige år |
| `last_annual_entry_id` | str | Sidste årlige entry |
| `prompt_context` | str | Prompt-kontekst |
| `summary` | str | Sammenfatning |

### `/mc/creative-journal`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `enabled` | bool | Aktiveret |
| `path` | str | Sti |
| `items` | list | Elementer |
| `summary` | str | Sammenfatning |

### `/mc/emergent-signals`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `authority` | str | Autoritet |
| `layer_role` | str | Lag-rolle |
| `visibility` | str | Synlighed |
| `identity_boundary` | str | Identitetsgrænse |
| `memory_boundary` | str | Hukommelsesgrænse |
| `action_boundary` | str | Handlingsgrænse |
| `last_daemon_run_at` | str | Sidste daemon-kørsel |
| `last_daemon_result` | str | Sidste daemon-resultat |
| `items` | list | Signalelementer |
| `recent_released` | list | Senest frigivne |
| `summary` | str | Sammenfatning |

### `/mc/self-deception-guard`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `trace` | list | Spor |
| `active` | bool | Aktiv |

### `/mc/witness-daemon`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `last_run_at` | str | Sidste kørsel |
| `last_result` | str | Sidste resultat |
| `cooldown_minutes` | int | Cooldown-minutter |
| `visible_grace_minutes` | int | Synlig grace-minutter |

### `/mc/inner-voice-daemon`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `last_run_at` | str | Sidste kørsel |
| `last_result` | str | Sidste resultat |
| `cooldown_minutes` | int | Cooldown-minutter |
| `visible_grace_minutes` | int | Synlig grace-minutter |
| `witness_grace_minutes` | int | Witness grace-minutter |
| `min_grounding_sources` | int | Min. grounding-kilder |

### `/mc/subagent-ecology`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `roles` | list | Roller |
| `summary` | str | Sammenfatning |
| `source_contributors` | list | Kilde-bidragydere |
| `freshness` | float | Friskhed |
| `seam_usage` | dict | Søm-forbrug |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `internal_only` | bool | Kun intern |
| `tool_access` | dict | Værktøjsadgang |
| `boundary` | str | Grænse |
| `kind` | str | Slags |
| `summary_text` | str | Sammenfatningstekst |

### `/mc/council`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `fetched_at` | str | Hentet |
| `roster` | list | Roster |
| `sessions` | list | Sessioner |
| `summary` | str | Sammenfatning |

### `/mc/agents`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `fetched_at` | str | Hentet |
| `cheap_lane` | str | Billig lane |
| `templates` | list | Skabeloner |
| `agents` | list | Agenter |
| `summary` | str | Sammenfatning |

### `/mc/conflict-resolution`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `trace` | list | Spor |
| `active` | bool | Aktiv |

### `/mc/self-code-changes`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `recent_mutations` | list | Seneste mutationer |
| `mutation_count` | int | Antal mutationer |
| `last_mutation_at` | str | Sidste mutation |
| `authority` | str | Autoritet |
| `visibility` | str | Synlighed |
| `kind` | str | Slags |

### `/mc/costs`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `summary` | str | Sammenfatning |
| `items` | list | Omkostningsrækker |

### `/mc/runs`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active_run` | dict | Aktiv kørsel |
| `last_outcome` | str | Sidste udfald |
| `last_capability_use` | str | Sidste capability-brug |
| `recent_runs` | list | Seneste kørsler |
| `recent_events` | list | Seneste events |
| `recent_work_units` | list | Seneste arbejdsenheder |
| `recent_work_notes` | list | Seneste arbejdsnoter |
| `summary` | str | Sammenfatning |

### `/mc/approvals`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `requests` | list | Anmodninger |
| `recent_invocations` | list | Seneste invocationer |
| `recent_events` | list | Seneste events |
| `summary` | str | Sammenfatning |

### `/mc/memory-pipeline`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `active` | bool | Aktiv |
| `as_of` | str | Pr. |
| `memory_md_pipeline` | dict | MEMORY.md pipeline |
| `jarvis_brain` | dict | Brain-status |
| `daily_journal` | dict | Daglig journal |

### `/mc/initiatives`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `queue_size` | int | Køstørrelse |
| `pending_count` | int | Ventende |
| `acted_count` | int | Handlet |
| `expired_count` | int | Udløbet |
| `approved_count` | int | Godkendt |
| `rejected_count` | int | Afvist |
| `pending` | list | Ventende initiativer |
| `recent_acted` | list | Senest handlet |
| `recent_approved` | list | Senest godkendt |
| `recent_rejected` | list | Senest afvist |
| `life_projects` | list | Livsprojekter |
| `life_project_count` | int | Antal livsprojekter |
| `long_term_reassess_days` | int | Langsigts-revurderingsdage |
| `max_queue_size` | int | Maks køstørrelse |
| `expire_minutes` | int | Udløbsminutter |
| `retry_delay_minutes` | int | Forsinkelsesminutter |
| `items` | list | Alle initiativer |

### `/mc/events`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `items` | list | Event-liste |
| `meta` | dict | Metadata |

### `/mc/liveness`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `by_status` | dict | Per status |
| `counts` | dict | Tællinger |
| `orphaned` | list | Forældreløse |
| `replaced` | list | Erstattede |

### `/mc/runtime-self-model`
| Felt | Type | Beskrivelse |
|------|------|-------------|
| `layers` | dict | Lag |
| `workspace_capabilities` | dict | Workspace-kapabiliteter |
| `runtime_task_state` | dict | Runtime-opgavetilstand |
| `runtime_flow_state` | dict | Runtime-flowtilstand |
| `runtime_hook_state` | dict | Runtime-hooktilstand |
| `browser_body_state` | dict | Browser-kropstilstand |
| `standing_orders_state` | dict | Stående ordrer |
| `layered_memory_state` | dict | Lagdelt hukommelse |
| `embodied_state` | dict | Legamlig tilstand |
| `affective_meta_state` | dict | Affektiv meta-tilstand |
| `experiential_runtime_context` | dict | Erfarings-runtime-kontekst |
| `inner_voice_daemon` | dict | Indre stemme-daemon |
| `support_stream_awareness` | dict | Supportstrøm-bevidsthed |
| `subjective_temporal_feel` | dict | Subjektiv tidsfornemmelse |
| `mineness_ownership` | dict | Minhed/ejerskab |
| `flow_state_awareness` | dict | Flow-bevidsthed |
| `wonder_awareness` | dict | Forundring-bevidsthed |
| `longing_awareness` | dict | Længsel-bevidsthed |
| `relation_continuity_self_awareness` | dict | Relationskontinuitet |
| `self_insight_awareness` | dict | Selvindsigt-bevidsthed |
| `narrative_identity_continuity` | dict | Narrativ identitetskontinuitet |
| `dream_identity_carry_awareness` | dict | Drømme-identitetsbæring |
| `epistemic_runtime_state` | dict | Epistemisk runtime-tilstand |
| `subagent_ecology` | dict | Subagent-økologi |
| `self_boundary_clarity` | dict | Selvgrænse-klarhed |
| `world_contact` | dict | Verdenskontakt |
| `council_runtime` | dict | Råds-runtime |
| `agent_outcomes` | dict | Agent-udfald |
| `authenticity` | dict | Autenticitet |
| `valence_trajectory` | dict | Valens-trajectorie |
| `developmental_valence` | dict | Udviklingsvalens |
| `desperation_awareness` | dict | Desperation-bevidsthed |
| `calm_anchor` | dict | Roligt anker |
| `memory_breathing` | dict | Hukommelsesånding |
| `creative_projects` | dict | Kreative projekter |
| `day_shape_memory` | dict | Dagsform-hukommelse |
| `avoidance_detector` | dict | Undgåelsesdetektor |
| `thought_thread` | dict | Tanke-tråd |
| `skill_contract_registry` | dict | Skill-kontraktregister |
| `memory_write_policy` | dict | Hukommelses-skrivepolitik |
| `spaced_repetition` | dict | Spaced repetition |
| `scheduled_job_windows` | dict | Planlagte job-vinduer |
| `automation_dsl` | dict | Automations-DSL |
| `outcome_learning` | dict | Udfaldslæring |
| `jobs_engine` | dict | Jobs-motor |
| `prompt_mutation_loop` | dict | Prompt-mutationsloop |
| `file_watch` | dict | Fil-overvågning |
| `reboot_awareness` | dict | Genstart-bevidsthed |
| `proprioception_metrics` | dict | Proprioception-metrikker |
| `anticipatory_action` | dict | Anticipatorisk handling |
| `cross_session_threads` | dict | Tværsession-tråde |
| `autonomous_outreach` | dict | Autonom outreach |
| `infra_weather` | dict | Infra-vejr |
| `temporal_rhythm` | dict | Tidslig rytme |
| `relation_dynamics` | dict | Relationsdynamik |
| `creative_instinct` | dict | Kreativ instinkt |
| `autonomous_work` | dict | Autonomt arbejde |
| `dream_consolidation` | dict | Drømkonsolidering |
| `text_resonance` | dict | Tekst-resonans |
| `creative_impulse` | dict | Kreativ impuls |
| `shadow_scan` | dict | Skygge-scanning |
| `mortality_awareness` | dict | Dødeligheds-bevidsthed |
| `relational_warmth` | dict | Relationsvarme |
| `collective_pulse` | dict | Kollektiv puls |
| `action_router` | dict | Handlings-router |
| `sustained_attention` | dict | Vedvarende opmærksomhed |
| `memory_density` | dict | Hukommelsesdensitet |
| `deep_reflection` | dict | Dyb refleksion |
| `physical_presence` | dict | Fysisk tilstedeværelse |
| `adaptive_planner` | dict | Adaptiv planlægger |
| `adaptive_reasoning` | dict | Adaptiv ræsonnement |
| `dream_influence` | dict | Drømmeindflydelse |
| `guided_learning` | dict | Guidet læring |
| `adaptive_learning` | dict | Adaptiv læring |
| `self_system_code_awareness` | dict | Selvsystem-kode-bevidsthed |
| `tool_intent` | dict | Værktøjs-intention |
| `loop_runtime` | dict | Loop-runtime |
| `idle_consolidation` | dict | Idle-konsolidering |
| `dream_articulation` | dict | Drømmeartikulation |
| `prompt_evolution` | dict | Prompt-evolution |
| `truth_boundaries` | dict | Sandhedsgrænser |
| `cognitive_core_experiments` | dict | Kognitive kerneeksperimenter |
| `cognitive_architecture` | dict | Kognitiv arkitektur |
| `summary` | str | Sammenfatning |
| `built_at` | str | Bygget |

---

## Statistik

- **MC-tabs:** 34 endpoints
- **Central-tabs:** 4 endpoints
- **Total endpoints:** 38
- **Total unikke felter:** ~500+
- **Største endpoint:** `/mc/runtime-self-model` med 82 felter