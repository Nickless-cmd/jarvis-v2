# `scripts.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

