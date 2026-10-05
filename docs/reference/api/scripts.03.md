# `scripts.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/phase7_analyze.py`
_Fase 7 — analyse, præcis som forhåndsregistreret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_jsonl` | `(path)` | — | [src](../../../scripts/phase7_analyze.py#L38) |
| function | `paired_diffs` | `(scores, model, a, b, probe_ids)` | — | [src](../../../scripts/phase7_analyze.py#L44) |
| function | `bootstrap_low` | `(diffs, rnd)` | — | [src](../../../scripts/phase7_analyze.py#L53) |
| function | `analyze` | `(out_dir=…)` | — | [src](../../../scripts/phase7_analyze.py#L61) |
| function | `_v4` | `(out_dir, scores)` | — | [src](../../../scripts/phase7_analyze.py#L115) |

## `scripts/phase7_build_probes.py`
_Fase 7 — bygger proberne af arkivet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_owner` | `()` | — | [src](../../../scripts/phase7_build_probes.py#L85) |
| function | `identity_text` | `(ws)` | — | [src](../../../scripts/phase7_build_probes.py#L98) |
| function | `_call` | `(system_user)` | — | [src](../../../scripts/phase7_build_probes.py#L106) |
| function | `_parse` | `(text)` | — | [src](../../../scripts/phase7_build_probes.py#L115) |
| function | `candidates` | `(conn, uid, now, lo, hi)` | Jarvis' svar i ejerens egne (ikke-autonome) samtaler, i spandens vindue. | [src](../../../scripts/phase7_build_probes.py#L125) |
| function | `preceding_user` | `(conn, session_id, msg_id)` | — | [src](../../../scripts/phase7_build_probes.py#L142) |
| function | `reject_reason` | `(p, ident_lower, used_sessions, session_id, type_counts)` | — | [src](../../../scripts/phase7_build_probes.py#L149) |
| function | `main` | `()` | — | [src](../../../scripts/phase7_build_probes.py#L171) |

## `scripts/phase7_collect.py`
_Fase 7 — indsamler svarene._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_load_builder` | `()` | — | [src](../../../scripts/phase7_collect.py#L55) |
| function | `_check_locked` | `()` | Proberne SKAL være låst i registreringen før første svar. | [src](../../../scripts/phase7_collect.py#L63) |
| function | `_full_system_prompt` | `(question)` | — | [src](../../../scripts/phase7_collect.py#L71) |
| function | `_call` | `(provider, model, system, user)` | — | [src](../../../scripts/phase7_collect.py#L80) |
| function | `_done` | `()` | — | [src](../../../scripts/phase7_collect.py#L92) |
| function | `main` | `()` | — | [src](../../../scripts/phase7_collect.py#L104) |

## `scripts/phase7_judge.py`
_Fase 7 — blind bedømmelse af svarene._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call` | `(prompt)` | — | [src](../../../scripts/phase7_judge.py#L71) |
| function | `parse_verdict` | `(text)` | — | [src](../../../scripts/phase7_judge.py#L80) |
| function | `_jsonl` | `(path)` | — | [src](../../../scripts/phase7_judge.py#L93) |
| function | `key` | `(r)` | — | [src](../../../scripts/phase7_judge.py#L99) |
| function | `main` | `()` | — | [src](../../../scripts/phase7_judge.py#L103) |
| function | `_calibration` | `(probes, items)` | 30 svar til Bjørns blinde bedømmelse — trukket én gang, aldrig igen. | [src](../../../scripts/phase7_judge.py#L148) |

## `scripts/phone_home_auto.py`
_phone_home_auto — hold phone_adb_address i runtime.json opdateret._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_ts` | `()` | — | [src](../../../scripts/phone_home_auto.py#L51) |
| function | `_log` | `(besked)` | — | [src](../../../scripts/phone_home_auto.py#L55) |
| function | `_skriv_state` | `(**felter)` | — | [src](../../../scripts/phone_home_auto.py#L66) |
| function | `_laes_adresse` | `()` | Gemt host:port fra runtime.json ('' hvis ikke sat). | [src](../../../scripts/phone_home_auto.py#L79) |
| function | `_skriv_adresse` | `(adresse)` | Merge phone_adb_address ind i runtime.json. True hvis ændret. | [src](../../../scripts/phone_home_auto.py#L89) |
| function | `_koer` | `(argv, timeout_s=…)` | — | [src](../../../scripts/phone_home_auto.py#L111) |
| function | `_forbundet` | `(adresse)` | — | [src](../../../scripts/phone_home_auto.py#L119) |
| function | `_connect` | `(adresse)` | — | [src](../../../scripts/phone_home_auto.py#L130) |
| function | `_ping` | `(ip)` | — | [src](../../../scripts/phone_home_auto.py#L138) |
| function | `_ip_fra_neigh` | `()` | Match TELEFON_MAC i serverens ARP-tabel (ip neigh). '' hvis ikke set. | [src](../../../scripts/phone_home_auto.py#L143) |
| function | `_scan_lan` | `()` | Fyld ARP-tabellen via parallel ping-scan af 10.0.0.0/24, returnér IP. | [src](../../../scripts/phone_home_auto.py#L156) |
| function | `main` | `()` | — | [src](../../../scripts/phone_home_auto.py#L190) |

## `scripts/primary_cache_warmer.py`
_Primary lane cache warmer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_konfigureret_model` | `()` | Den model den SYNLIGE lane bruger lige nu. | [src](../../../scripts/primary_cache_warmer.py#L63) |
| function | `_discover_active_workspaces` | `()` | Find aktive bruger-workspaces der skal cache-warmes. | [src](../../../scripts/primary_cache_warmer.py#L101) |
| function | `_fetch_system_prompt` | `(workspace_name=…)` | Hent primary lane system prompt. | [src](../../../scripts/primary_cache_warmer.py#L138) |
| function | `_save_prompt_to_file` | `(content)` | Gem prompt til fil så standalone kald kan bruge det senere. | [src](../../../scripts/primary_cache_warmer.py#L199) |
| function | `_check_dedup` | `(*, force=…)` | Tjek om et kald er for nyligt. | [src](../../../scripts/primary_cache_warmer.py#L212) |
| function | `_touch_last_run` | `()` | — | [src](../../../scripts/primary_cache_warmer.py#L236) |
| function | `_fetch_warmer_tools` | `()` | Hent samme pruned tools-array som visible-chats sender. | [src](../../../scripts/primary_cache_warmer.py#L246) |
| function | `_build_payload` | `(system_prompt)` | Byg request body til DeepSeek chat completions. | [src](../../../scripts/primary_cache_warmer.py#L284) |
| function | `_build_headers` | `(api_key)` | — | [src](../../../scripts/primary_cache_warmer.py#L308) |
| function | `_call_api` | `(api_key, base_url, payload, *, timeout_s=…)` | Kald DeepSeek chat completions API. | [src](../../../scripts/primary_cache_warmer.py#L315) |
| function | `_insert_cost_row` | `(result)` | Indsæt warmer-kald i costs-tabellen. | [src](../../../scripts/primary_cache_warmer.py#L387) |
| function | `_rotér` | `(sti)` | Flyt filen til `.1` naar den bliver for stor. Én generation, ikke fem. | [src](../../../scripts/primary_cache_warmer.py#L441) |
| function | `_append_log` | `(entry)` | — | [src](../../../scripts/primary_cache_warmer.py#L460) |
| function | `_read_key_from_runtime_json` | `()` | Læs deepseek_api_key fra ~/.jarvis-v2/config/runtime.json. | [src](../../../scripts/primary_cache_warmer.py#L476) |
| function | `_resolve_api_key` | `(*, override=…)` | Resolve DeepSeek API key: override > env > runtime.json. | [src](../../../scripts/primary_cache_warmer.py#L486) |
| function | `warm_primary_cache` | `(*, api_key=…, base_url=…, system_prompt=…, force=…, workspace_name=…)` | Udfør ét cache-warmer kald og returnér resultat. | [src](../../../scripts/primary_cache_warmer.py#L503) |
| function | `_warm_one_workspace` | `(workspace_name, *, api_key, base_url, dry_run)` | Cache-warm én bestemt workspace. Logger separat per workspace. | [src](../../../scripts/primary_cache_warmer.py#L583) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/primary_cache_warmer.py#L657) |

## `scripts/prompt_dump_readable.py`
_Læsbar version af et prompt-dump (30/9-2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_chars` | `(obj)` | — | [src](../../../scripts/prompt_dump_readable.py#L36) |
| function | `_text` | `(m)` | — | [src](../../../scripts/prompt_dump_readable.py#L43) |
| function | `_split_user` | `(t)` | (bjoern-tegn, tool-resultat-tegn, rest) inde i ÉN user-besked. | [src](../../../scripts/prompt_dump_readable.py#L52) |
| function | `_kind` | `(i, m)` | (kategori-noegle, menneske-etikette) for én besked. | [src](../../../scripts/prompt_dump_readable.py#L69) |
| function | `_pct` | `(n, total)` | — | [src](../../../scripts/prompt_dump_readable.py#L93) |
| function | `build` | `(dump, full=…)` | — | [src](../../../scripts/prompt_dump_readable.py#L97) |
| function | `main` | `()` | — | [src](../../../scripts/prompt_dump_readable.py#L253) |

## `scripts/prompt_dump_split.py`
_Splitter et prompt-dump fra /tmp/jarvis-prompt-dumps/latest.json i sektioner._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_chars` | `(obj)` | — | [src](../../../scripts/prompt_dump_split.py#L28) |
| function | `_role_title` | `(m)` | — | [src](../../../scripts/prompt_dump_split.py#L35) |
| function | `_msg_body` | `(m)` | Indholdet som tekst — håndterer både streng og strukturerede blokke. | [src](../../../scripts/prompt_dump_split.py#L41) |
| function | `build_markdown` | `(dump)` | — | [src](../../../scripts/prompt_dump_split.py#L51) |
| function | `main` | `()` | — | [src](../../../scripts/prompt_dump_split.py#L145) |

## `scripts/publish_mobile_apk.py`
_Læg en ny mobil-APK op — og behold præcis én version tilbage._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `apk_navn` | `(version_code)` | — | [src](../../../scripts/publish_mobile_apk.py#L47) |
| function | `find_apksigner` | `()` | — | [src](../../../scripts/publish_mobile_apk.py#L51) |
| function | `kontroller_apk_signatur` | `(apk)` | — | [src](../../../scripts/publish_mobile_apk.py#L56) |
| function | `vaelg_hvad_der_slettes` | `(filer, ny, forrige)` | Hvilke APK'er beholdes, og hvilke ryger? | [src](../../../scripts/publish_mobile_apk.py#L78) |
| function | `_kald` | `(host, kommando, *, dry)` | Kør en kommando lokalt eller på host. Returnerer stdout. | [src](../../../scripts/publish_mobile_apk.py#L106) |
| function | `apk_version` | `(apk)` | (versionCode, versionName) læst ud af APK'ens EGEN manifest. | [src](../../../scripts/publish_mobile_apk.py#L118) |
| function | `hovedet` | `(argv=…)` | — | [src](../../../scripts/publish_mobile_apk.py#L145) |

## `scripts/regenerate_tier1.py`
_Regenerate TIER_1_ALWAYS_ON in copilot_tool_pruning.py from 30-day usage data._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_usage` | `()` | Count tool.invoked events per tool over the last WINDOW_DAYS from the runtime DB. | [src](../../../scripts/regenerate_tier1.py#L50) |
| function | `load_registered_tools` | `()` | Return the set of tool names from the live TOOL_DEFINITIONS catalog. | [src](../../../scripts/regenerate_tier1.py#L71) |
| function | `compute_new_tier1` | `(usage, registered)` | Build the new Tier-1 set: tools used >= USAGE_THRESHOLD unioned with | [src](../../../scripts/regenerate_tier1.py#L88) |
| function | `render_literal` | `(names)` | Render the tool names as the source text of a TIER_1_ALWAYS_ON frozenset | [src](../../../scripts/regenerate_tier1.py#L96) |
| function | `replace_literal_in_file` | `(new_literal)` | Rewrite the TIER_1_ALWAYS_ON literal in copilot_tool_pruning.py in place. | [src](../../../scripts/regenerate_tier1.py#L108) |
| function | `main` | `()` | CLI entry point: compute the new Tier-1 set and print the diff vs current. | [src](../../../scripts/regenerate_tier1.py#L129) |

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
| function | `_run_lifespan` | `()` | Import app + drive lifespan context to completion. | [src](../../../scripts/smoke_test_startup.py#L51) |
| function | `_start_vagthund` | `(started)` | Bagstopper i en TRAAD for det haeng `asyncio.wait_for` ikke kan se. | [src](../../../scripts/smoke_test_startup.py#L465) |
| function | `main` | `()` | — | [src](../../../scripts/smoke_test_startup.py#L498) |

## `scripts/tag_untagged_skills.py`
_Batch-tag untagged skills for C2 — Skills meta-tags._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `infer_tags` | `(name, description, use_when)` | Infer domain/context tags from skill metadata. | [src](../../../scripts/tag_untagged_skills.py#L81) |
| function | `update_skill_md` | `(path)` | Add tags to SKILL.md frontmatter. Returns True if changed. | [src](../../../scripts/tag_untagged_skills.py#L101) |
| function | `main` | `()` | — | [src](../../../scripts/tag_untagged_skills.py#L155) |

## `scripts/think_language_ab.py`
_Tænke-sprog A/B — snapshot og sammenligning (30/9-2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_roundtime_proxy` | `(conn, lane, since, until)` | Median afstand mellem på hinanden følgende runder i samme run_id. | [src](../../../scripts/think_language_ab.py#L58) |
| function | `snapshot` | `(since, until=…)` | Tag et snapshot af alle laner i vinduet [since, until). | [src](../../../scripts/think_language_ab.py#L88) |
| function | `_fmt` | `(snap)` | — | [src](../../../scripts/think_language_ab.py#L141) |
| function | `compare` | `(a, b)` | — | [src](../../../scripts/think_language_ab.py#L161) |
| function | `main` | `()` | — | [src](../../../scripts/think_language_ab.py#L185) |

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

## `scripts/verify_guard_tests.py`
_Vagt over vagterne: hver hook skal have en test der ser den sige nej._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `vagter` | `()` | Modulnavne på de scripts hookene kører. | [src](../../../scripts/verify_guard_tests.py#L38) |
| function | `_tester_der_naevner` | `(modul)` | — | [src](../../../scripts/verify_guard_tests.py#L45) |
| function | `mangler` | `()` | (vagt, årsag) for hver vagt uden en test der ser den afvise. | [src](../../../scripts/verify_guard_tests.py#L56) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_guard_tests.py#L69) |

## `scripts/verify_history_reads.py`
_Vagt: ingen NYE kaldere der læser en hel samtale-historik synkront._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_navn` | `(node)` | — | [src](../../../scripts/verify_history_reads.py#L49) |
| function | `fund_i_fil` | `(sti)` | — | [src](../../../scripts/verify_history_reads.py#L54) |
| function | `_filer` | `(a)` | — | [src](../../../scripts/verify_history_reads.py#L76) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_history_reads.py#L92) |

## `scripts/verify_notes.py`
_Vagt: en note skal have en status, en slags, og sine fire overskrifter._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `noter` | `()` | Kun noter i den NYE form. Den flade bunke er frosset og røres ikke. | [src](../../../scripts/verify_notes.py#L39) |
| function | `fejl_i` | `(sti)` | — | [src](../../../scripts/verify_notes.py#L50) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_notes.py#L67) |

## `scripts/verify_persistens.py`
_Vagt: et nyt varigt format skal skrives ind i registret med en dato._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_strengkonstanter` | `(traeet)` | Modul-globale strenge, så `save_json(_NAVN, …)` kan slås op. | [src](../../../scripts/verify_persistens.py#L44) |
| function | `noegler_i_traeet` | `()` | nøgle -> filer der skriver eller læser den. | [src](../../../scripts/verify_persistens.py#L56) |
| function | `_modulbeskrivelse` | `(rel_sti)` | Første linje af ejerens modul-docstring, eller en UDFYLD-plads. | [src](../../../scripts/verify_persistens.py#L90) |
| function | `_register` | `()` | — | [src](../../../scripts/verify_persistens.py#L102) |
| function | `afvigelser` | `()` | (uregistrerede nøgler, registrerede nøgler ingen rører længere). | [src](../../../scripts/verify_persistens.py#L109) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_persistens.py#L118) |

## `scripts/verify_silent_except.py`
_Vagt: en slugt undtagelse skal navngives, og dens `try` skal være kort._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_er_tavs` | `(handler)` | Sluger denne handler fejlen uden at sige noget? | [src](../../../scripts/verify_silent_except.py#L51) |
| function | `_naevner_fejlen` | `(handler, kommentarlinjer)` | Er der en forklaring? En kommentar på `except`-linjen eller i kroppen. | [src](../../../scripts/verify_silent_except.py#L59) |
| function | `_kommentarlinjer` | `(sti)` | — | [src](../../../scripts/verify_silent_except.py#L70) |
| function | `fund_i_fil` | `(sti)` | (linje, årsag) for hver tavs handler uden forklaring. | [src](../../../scripts/verify_silent_except.py#L81) |
| function | `_filer` | `(argumenter)` | — | [src](../../../scripts/verify_silent_except.py#L102) |
| function | `_laes_grundlinje` | `()` | — | [src](../../../scripts/verify_silent_except.py#L118) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_silent_except.py#L125) |

## `scripts/verify_sqlite_schema.py`
_Compare the live SQLite schema with its reviewed, per-table snapshot._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_quote` | `(name)` | — | [src](../../../scripts/verify_sqlite_schema.py#L22) |
| function | `timestamp_format` | `(value)` | — | [src](../../../scripts/verify_sqlite_schema.py#L26) |
| function | `_timestamp_formats` | `(conn, table)` | — | [src](../../../scripts/verify_sqlite_schema.py#L41) |
| function | `inventory` | `(conn)` | — | [src](../../../scripts/verify_sqlite_schema.py#L60) |
| function | `_unobserved` | `(value)` | True når et format ikke er observeret — tom tabel eller ingen kolonne. | [src](../../../scripts/verify_sqlite_schema.py#L98) |
| function | `compare` | `(current, expected)` | — | [src](../../../scripts/verify_sqlite_schema.py#L108) |
| function | `_forklar` | `(issues, snapshot)` | Sig hvad der skal ske. En vagt der kun siger NEJ er en blokade. | [src](../../../scripts/verify_sqlite_schema.py#L162) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_sqlite_schema.py#L201) |

## `scripts/verify_vagt_graenser.py`
_Vagt: vagt-laget må NÆVNE et delsystem, aldrig importere det._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_importerede_moduler` | `(traeet)` | — | [src](../../../scripts/verify_vagt_graenser.py#L44) |
| function | `brud` | `()` | — | [src](../../../scripts/verify_vagt_graenser.py#L55) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_vagt_graenser.py#L74) |

