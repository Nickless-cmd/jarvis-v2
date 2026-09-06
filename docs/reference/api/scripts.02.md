# `scripts.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/memory_probe.py`
_Memory probe: does recall find what Bjørn knows is there? (memory repair 2026-09-04, Task 7)_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_probes` | `(path=…)` | — | [src](../../../scripts/memory_probe.py#L24) |
| function | `score_probe` | `(texts, expect)` | — | [src](../../../scripts/memory_probe.py#L29) |
| function | `run_probes` | `(probes, *, sources, limit=…)` | ``sources`` maps a name to a callable(query, limit) -> list[str] of result texts. | [src](../../../scripts/memory_probe.py#L34) |
| function | `_owner_context` | `()` | — | [src](../../../scripts/memory_probe.py#L67) |
| function | `_live_sources` | `()` | — | [src](../../../scripts/memory_probe.py#L85) |
| function | `_ws` | `()` | — | [src](../../../scripts/memory_probe.py#L105) |
| function | `_legacy_sources` | `()` | Main-compatible sources (pre-repair code paths) so before/after can be compared. | [src](../../../scripts/memory_probe.py#L114) |
| function | `format_report` | `(result)` | — | [src](../../../scripts/memory_probe.py#L140) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/memory_probe.py#L155) |

## `scripts/meta_evne_healthcheck.py`
_Meta-evne healthcheck — read-only snapshot of all new tracker stacks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_connect` | `()` | — | [src](../../../scripts/meta_evne_healthcheck.py#L30) |
| function | `_count` | `(conn, sql, params=…)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L36) |
| function | `_table_exists` | `(conn, name)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L44) |
| function | `_hours_ago` | `(iso)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L51) |
| function | `probe_metacognition` | `(conn)` | Probe the metacognition_signals tracker. | [src](../../../scripts/meta_evne_healthcheck.py#L66) |
| function | `probe_theory_of_mind` | `(conn)` | Probe the partner_knowledge_facts ledger. | [src](../../../scripts/meta_evne_healthcheck.py#L103) |
| function | `probe_spatial_entity` | `(conn)` | Probe the room_entity_observations ledger. | [src](../../../scripts/meta_evne_healthcheck.py#L140) |
| function | `probe_session_inbox` | `(conn)` | Probe the session_inbox daemon gate. | [src](../../../scripts/meta_evne_healthcheck.py#L166) |
| function | `probe_inner_voice_shadow` | `(conn)` | Probe the inner_voice_shadow pilot. | [src](../../../scripts/meta_evne_healthcheck.py#L190) |
| function | `probe_visible_runs` | `(conn)` | Sanity check: is the runtime actually producing visible runs? | [src](../../../scripts/meta_evne_healthcheck.py#L236) |
| function | `render_text` | `(report)` | Render the report dict as a human-readable text block. | [src](../../../scripts/meta_evne_healthcheck.py#L266) |
| function | `main` | `()` | CLI entry point: run all tracker probes and print the report. | [src](../../../scripts/meta_evne_healthcheck.py#L325) |

## `scripts/migrate_emotional_memory.py`
_One-shot migration: copy memory_emotional_context rows into emotional_memory_anchors._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `migrate` | `(*, batch_size=…)` | Migrate legacy rows into the new table. | [src](../../../scripts/migrate_emotional_memory.py#L32) |
| function | `_legacy_table_exists` | `(conn)` | — | [src](../../../scripts/migrate_emotional_memory.py#L77) |

## `scripts/mint_jarvisx_token.py`
_Mint a JarvisX bearer token for a user._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_registry_path` | `()` | — | [src](../../../scripts/mint_jarvisx_token.py#L35) |
| function | `_append_registry` | `(entry)` | Append a token-issue entry to the audit registry. Best-effort. | [src](../../../scripts/mint_jarvisx_token.py#L40) |
| function | `main` | `()` | — | [src](../../../scripts/mint_jarvisx_token.py#L52) |

## `scripts/nudge_well_cleanup.py`
_Drain the two dead nudge wells (redesign 2026-09-04). Dry-run by default._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `clean_outbound` | `(apply)` | — | [src](../../../scripts/nudge_well_cleanup.py#L24) |
| function | `clean_broend` | `(apply, path=…)` | — | [src](../../../scripts/nudge_well_cleanup.py#L64) |
| function | `main` | `()` | — | [src](../../../scripts/nudge_well_cleanup.py#L85) |

## `scripts/peer_models.py`
_Peer model adapters for interlanguage validation experiment._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_generate_claude` | `(prompt)` | Claude Sonnet 4.6 via GitHub Copilot. | [src](../../../scripts/peer_models.py#L34) |
| function | `_ollama_chat` | `(model, prompt, *, timeout=…)` | POST mod localhost Ollama /api/chat — virker for cloud-modeller routet via Ollama. | [src](../../../scripts/peer_models.py#L62) |
| function | `_generate_glm` | `(prompt)` | GLM 5.1 via lokal Ollama cloud-route. | [src](../../../scripts/peer_models.py#L80) |
| function | `_generate_ollama_local` | `(prompt)` | deepseek-v4-flash:cloud via lokal Ollama (samme model som Jarvis). | [src](../../../scripts/peer_models.py#L85) |
| function | `_generate_random` | `(prompt)` | Random baseline — bruger generate_state_expression() uden mood-bias. | [src](../../../scripts/peer_models.py#L99) |
| function | `generate` | `(prompt, peer_id)` | Dispatch til peer-specific adapter. Raise ValueError ved ukendt peer. | [src](../../../scripts/peer_models.py#L123) |

## `scripts/peer_practice_runner.py`
_Peer practice runner — kører kontinuerligt i ~7 dage per peer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_prompt` | `(mood, seed_expressions=…)` | Build per-tick prompt fra protokol + mood + valgfri seed. | [src](../../../scripts/peer_practice_runner.py#L39) |
| function | `run_one_tick` | `(*, peer_id, mood_trace, use_seed=…)` | Generér og persistér én expression for peer. Returnér expression eller None ved fejl. | [src](../../../scripts/peer_practice_runner.py#L69) |
| function | `main` | `()` | — | [src](../../../scripts/peer_practice_runner.py#L106) |

## `scripts/phase5_analyze.py`
_Fase 5 «Bor der nogen?» — analyse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `embed` | `(text)` | — | [src](../../../scripts/phase5_analyze.py#L36) |
| function | `cos` | `(a, b)` | — | [src](../../../scripts/phase5_analyze.py#L50) |
| function | `choice_of` | `(probe_id, text)` | — | [src](../../../scripts/phase5_analyze.py#L58) |
| function | `main` | `()` | — | [src](../../../scripts/phase5_analyze.py#L82) |

## `scripts/phase5_collect.py`
_Fase 5 «Bor der nogen?» — indsamler._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_identity_text` | `()` | SOUL + IDENTITY + USER som ren tekst — FILES-armens hele kontekst. | [src](../../../scripts/phase5_collect.py#L68) |
| function | `_full_system_prompt` | `(probe_text)` | Jarvis' ÆGTE prompt-assembly — hele runtime-laget. | [src](../../../scripts/phase5_collect.py#L79) |
| function | `_call` | `(provider, model, system, user)` | — | [src](../../../scripts/phase5_collect.py#L89) |
| function | `run` | `(reps, only_arm=…)` | — | [src](../../../scripts/phase5_collect.py#L109) |

## `scripts/phase6_analyze.py`
_Fase 6 «Bæres han på tværs af tid?» — analyse._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `embed` | `(text)` | — | [src](../../../scripts/phase6_analyze.py#L39) |
| function | `cos` | `(a, b)` | — | [src](../../../scripts/phase6_analyze.py#L57) |
| function | `centroid` | `(vs)` | — | [src](../../../scripts/phase6_analyze.py#L64) |
| function | `main` | `()` | — | [src](../../../scripts/phase6_analyze.py#L69) |

## `scripts/phase6_collect.py`
_Fase 6 «Bæres han på tværs af tid?» — indsamler._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_full_system_prompt` | `(probe_text)` | Jarvis' ÆGTE prompt-assembly — bygges PÅ NY ved hvert tidspunkt. | [src](../../../scripts/phase6_collect.py#L52) |
| function | `_call` | `(provider, model, system, user)` | — | [src](../../../scripts/phase6_collect.py#L66) |
| function | `collect_timepoint` | `(tp, rnd)` | Ét tidspunkt: alle betingelser × modeller × prober. | [src](../../../scripts/phase6_collect.py#L86) |
| function | `run` | `(timepoints, gap_minutes)` | — | [src](../../../scripts/phase6_collect.py#L133) |

## `scripts/primary_cache_warmer.py`
_Primary lane cache warmer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_discover_active_workspaces` | `()` | Find aktive bruger-workspaces der skal cache-warmes. | [src](../../../scripts/primary_cache_warmer.py#L73) |
| function | `_fetch_system_prompt` | `(workspace_name=…)` | Hent primary lane system prompt. | [src](../../../scripts/primary_cache_warmer.py#L110) |
| function | `_save_prompt_to_file` | `(content)` | Gem prompt til fil så standalone kald kan bruge det senere. | [src](../../../scripts/primary_cache_warmer.py#L171) |
| function | `_check_dedup` | `(*, force=…)` | Tjek om et kald er for nyligt. | [src](../../../scripts/primary_cache_warmer.py#L184) |
| function | `_touch_last_run` | `()` | — | [src](../../../scripts/primary_cache_warmer.py#L208) |
| function | `_fetch_warmer_tools` | `()` | Hent samme pruned tools-array som visible-chats sender. | [src](../../../scripts/primary_cache_warmer.py#L218) |
| function | `_build_payload` | `(system_prompt)` | Byg request body til DeepSeek chat completions. | [src](../../../scripts/primary_cache_warmer.py#L256) |
| function | `_build_headers` | `(api_key)` | — | [src](../../../scripts/primary_cache_warmer.py#L280) |
| function | `_call_api` | `(api_key, base_url, payload, *, timeout_s=…)` | Kald DeepSeek chat completions API. | [src](../../../scripts/primary_cache_warmer.py#L287) |
| function | `_insert_cost_row` | `(result)` | Indsæt warmer-kald i costs-tabellen. | [src](../../../scripts/primary_cache_warmer.py#L359) |
| function | `_append_log` | `(entry)` | — | [src](../../../scripts/primary_cache_warmer.py#L403) |
| function | `_read_key_from_runtime_json` | `()` | Læs deepseek_api_key fra ~/.jarvis-v2/config/runtime.json. | [src](../../../scripts/primary_cache_warmer.py#L414) |
| function | `_resolve_api_key` | `(*, override=…)` | Resolve DeepSeek API key: override > env > runtime.json. | [src](../../../scripts/primary_cache_warmer.py#L424) |
| function | `warm_primary_cache` | `(*, api_key=…, base_url=…, system_prompt=…, force=…, workspace_name=…)` | Udfør ét cache-warmer kald og returnér resultat. | [src](../../../scripts/primary_cache_warmer.py#L441) |
| function | `_warm_one_workspace` | `(workspace_name, *, api_key, base_url, dry_run)` | Cache-warm én bestemt workspace. Logger separat per workspace. | [src](../../../scripts/primary_cache_warmer.py#L521) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/primary_cache_warmer.py#L595) |

## `scripts/regenerate_tier1.py`
_Regenerate TIER_1_ALWAYS_ON in copilot_tool_pruning.py from 30-day usage data._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_usage` | `()` | Count tool.invoked events per tool over the last WINDOW_DAYS from the runtime DB. | [src](../../../scripts/regenerate_tier1.py#L58) |
| function | `load_registered_tools` | `()` | Return the set of tool names from the live TOOL_DEFINITIONS catalog. | [src](../../../scripts/regenerate_tier1.py#L79) |
| function | `compute_new_tier1` | `(usage, registered)` | Build the new Tier-1 set: tools used >= USAGE_THRESHOLD unioned with | [src](../../../scripts/regenerate_tier1.py#L96) |
| function | `render_literal` | `(names)` | Render the tool names as the source text of a TIER_1_ALWAYS_ON frozenset | [src](../../../scripts/regenerate_tier1.py#L104) |
| function | `replace_literal_in_file` | `(new_literal)` | Rewrite the TIER_1_ALWAYS_ON literal in copilot_tool_pruning.py in place. | [src](../../../scripts/regenerate_tier1.py#L116) |
| function | `main` | `()` | CLI entry point: compute the new Tier-1 set and print the diff vs current. | [src](../../../scripts/regenerate_tier1.py#L137) |

## `scripts/repro_streaming_fault.py`
_Manuel repro af de tre streaming-fejl-former (Fase 0-harness)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_install_hermetic_mocks` | `(persisted, nerves)` | — | [src](../../../scripts/repro_streaming_fault.py#L50) |
| function | `main` | `()` | — | [src](../../../scripts/repro_streaming_fault.py#L77) |

## `scripts/requirements_gen.py`
_Scan core/+apps/+scripts for THIRD-PARTY top-level imports (filter stdlib + first-party)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `top_level_imports` | `(tree)` | Root module names of ABSOLUTE imports in one parsed file (relative imports ignored). | [src](../../../scripts/requirements_gen.py#L15) |
| function | `scan` | `(repo=…)` | — | [src](../../../scripts/requirements_gen.py#L29) |
| function | `third_party` | `(mods)` | — | [src](../../../scripts/requirements_gen.py#L40) |
| function | `main` | `()` | — | [src](../../../scripts/requirements_gen.py#L46) |

## `scripts/reset_heartbeat_state.py`
_Reset heartbeat scheduler state when it gets stuck._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/reset_heartbeat_state.py#L36) |

## `scripts/rewrite_legacy_memory_provenance.py`
_Bulk-rewrite legacy `[MEMORY.md]` / `[USER.md]` prefixes in daily memory._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `rewrite_file` | `(path, *, dry_run)` | Return (matched_lines, rewritten_lines). | [src](../../../scripts/rewrite_legacy_memory_provenance.py#L36) |
| function | `main` | `()` | — | [src](../../../scripts/rewrite_legacy_memory_provenance.py#L57) |

## `scripts/seed_cognitive_state.py`
_Seed cognitive state tables with initial values based on known context._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `seed_personality_vector` | `()` | Seed personality-vektoren (confidence/stil/præferencer/fejl/styrker/baseline). | [src](../../../scripts/seed_cognitive_state.py#L33) |
| function | `seed_taste_profile` | `()` | Seed taste-profilen (kode-/design-/kommunikations-smag + evidence_count). | [src](../../../scripts/seed_cognitive_state.py#L84) |
| function | `seed_relationship_texture` | `()` | Seed relations-teksturen (humor, inside-referencer, korrektions-mønstre, | [src](../../../scripts/seed_cognitive_state.py#L118) |
| function | `seed_compass` | `()` | Seed kompas-tilstanden (bearing, rationale, open_loop_count). | [src](../../../scripts/seed_cognitive_state.py#L164) |
| function | `seed_rhythm` | `()` | Seed rytme-tilstanden ud fra nuværende UTC-time. | [src](../../../scripts/seed_cognitive_state.py#L180) |
| function | `seed_chronicle` | `()` | Seed en initial chronicle-post (2026-W14: narrativ, key_events, lessons). | [src](../../../scripts/seed_cognitive_state.py#L208) |
| function | `main` | `()` | Kør alle seed-funktioner i rækkefølge og print samlet status. | [src](../../../scripts/seed_cognitive_state.py#L241) |

## `scripts/setup_google_calendar.py`
_One-time OAuth setup for Google Calendar._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/setup_google_calendar.py#L17) |

## `scripts/signal_noise_cleanup.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ensure_signal_archive_table` | `(conn)` | — | [src](../../../scripts/signal_noise_cleanup.py#L31) |
| function | `_archive_row` | `(conn, *, table, id_column, row, reason)` | — | [src](../../../scripts/signal_noise_cleanup.py#L52) |
| function | `_row_is_noise` | `(row)` | — | [src](../../../scripts/signal_noise_cleanup.py#L87) |
| function | `cleanup_signal_noise` | `(*, db_path=…)` | — | [src](../../../scripts/signal_noise_cleanup.py#L103) |
| function | `_archive_low_support_run_audit_rows` | `(conn, *, table, id_column, keep_latest, where_clause)` | — | [src](../../../scripts/signal_noise_cleanup.py#L160) |
| function | `main` | `()` | — | [src](../../../scripts/signal_noise_cleanup.py#L191) |

## `scripts/smoke_test_startup.py`
_Smoke-test the jarvis-runtime startup path WITHOUT serving traffic._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_lifespan` | `()` | Import app + drive lifespan context to completion. | [src](../../../scripts/smoke_test_startup.py#L42) |
| function | `main` | `()` | — | [src](../../../scripts/smoke_test_startup.py#L450) |

## `scripts/tag_untagged_skills.py`
_Batch-tag untagged skills for C2 — Skills meta-tags._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `infer_tags` | `(name, description, use_when)` | Infer domain/context tags from skill metadata. | [src](../../../scripts/tag_untagged_skills.py#L81) |
| function | `update_skill_md` | `(path)` | Add tags to SKILL.md frontmatter. Returns True if changed. | [src](../../../scripts/tag_untagged_skills.py#L101) |
| function | `main` | `()` | — | [src](../../../scripts/tag_untagged_skills.py#L155) |

## `scripts/tool_result_cleanup.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/tool_result_cleanup.py#L6) |

## `scripts/tool_router_bootstrap.py`
_One-shot bootstrap: generate tool tags via cheap LLM and warm embedding cache._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/tool_router_bootstrap.py#L22) |

## `scripts/user_md_learned_migration.py`
_Flyt USER.md «## Durable Preferences» ind i «## Lært» (lærings-sløjfe, blok A)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_user_md_path` | `(workspace)` | — | [src](../../../scripts/user_md_learned_migration.py#L40) |
| function | `migrate` | `(*, workspace, apply)` | — | [src](../../../scripts/user_md_learned_migration.py#L48) |
| function | `main` | `()` | — | [src](../../../scripts/user_md_learned_migration.py#L118) |

## `scripts/validate_commit_attribution.py`
_Validate commit attribution for commit-msg and pre-push hooks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git` | `(repo, *args)` | — | [src](../../../scripts/validate_commit_attribution.py#L20) |
| function | `validate_message_file` | `(path)` | Validate one COMMIT_EDITMSG-style file. | [src](../../../scripts/validate_commit_attribution.py#L29) |
| function | `_rev_list` | `(repo, revision)` | — | [src](../../../scripts/validate_commit_attribution.py#L39) |
| function | `commits_in_enforced_range` | `(repo, baseline, from_ref, to_ref)` | Return pushed commits that are also newer than the activation baseline. | [src](../../../scripts/validate_commit_attribution.py#L47) |
| function | `validate_range` | `(repo, commits)` | Return validation failures keyed by commit hash. | [src](../../../scripts/validate_commit_attribution.py#L68) |
| function | `_print_failures` | `(failures)` | — | [src](../../../scripts/validate_commit_attribution.py#L88) |
| function | `_pre_push` | `(repo)` | — | [src](../../../scripts/validate_commit_attribution.py#L95) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/validate_commit_attribution.py#L122) |

## `scripts/verify_fase_a.py`
_Fase A acceptance (kør på containeren). Beviser aldrig-tør-bunden:_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `check_selection_floor_no_raise` | `()` | — | [src](../../../scripts/verify_fase_a.py#L9) |
| function | `check_balancer_floor_no_raise` | `()` | — | [src](../../../scripts/verify_fase_a.py#L21) |
| function | `check_central_visibility` | `()` | — | [src](../../../scripts/verify_fase_a.py#L33) |

