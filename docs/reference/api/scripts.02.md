# `scripts.02` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/installer_desk_appimage.py`
_Installér desk-AppImage'en, og hold `.desktop` og AppArmor-profil i takt med den._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Fejl` | `` | En fejl brugeren skal se, ikke et stakspor. | [src](../../../scripts/installer_desk_appimage.py#L73) |
| function | `_koer` | `(*args, tjek=…)` | — | [src](../../../scripts/installer_desk_appimage.py#L77) |
| function | `byg_mappe` | `()` | electron-builders output-mappe, LÆST af package.json. | [src](../../../scripts/installer_desk_appimage.py#L81) |
| function | `find_appimage` | `()` | Nyeste AppImage i electron-builders output-mappe. | [src](../../../scripts/installer_desk_appimage.py#L98) |
| function | `udpak` | `(appimage, moenster, ud)` | Udpak et mønster fra AppImage'en til `ud`. Kaster ved fejl. | [src](../../../scripts/installer_desk_appimage.py#L113) |
| function | `laes_indlejret_desktop` | `(appimage)` | Nøgle→værdi fra AppImage'ens EGEN `.desktop`. | [src](../../../scripts/installer_desk_appimage.py#L124) |
| function | `byg_desktop` | `(felter, maal)` | `.desktop`-indholdet, med `--no-sandbox` fjernet og stien sat. | [src](../../../scripts/installer_desk_appimage.py#L147) |
| function | `byg_profil` | `(navn, maal)` | — | [src](../../../scripts/installer_desk_appimage.py#L167) |
| function | `_skriv_hvis_anderledes` | `(sti, indhold, toerloeb)` | — | [src](../../../scripts/installer_desk_appimage.py#L190) |
| function | `skriv_profil` | `(navn, indhold, toerloeb)` | Skriv profilen med sudo og genindlæs den. True hvis den ændrede sig. | [src](../../../scripts/installer_desk_appimage.py#L203) |
| function | `installer_ikoner` | `(appimage, toerloeb)` | Kopiér AppImage'ens egne ikoner ind i temaet. Giver antallet. | [src](../../../scripts/installer_desk_appimage.py#L226) |
| function | `verificer` | `(maal)` | Start appen SOM GNOME-SHELL GOER DET og se om zygoten overlever. | [src](../../../scripts/installer_desk_appimage.py#L243) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/installer_desk_appimage.py#L284) |

## `scripts/interlanguage_analyze.py`
_Interlanguage analysis — aggregate report over the practice corpus._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_all` | `(*, days=…)` | — | [src](../../../scripts/interlanguage_analyze.py#L42) |
| function | `analyze` | `(rows)` | — | [src](../../../scripts/interlanguage_analyze.py#L61) |
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_analyze.py#L96) |

## `scripts/interlanguage_binary_jarvis_vs_ollama.py`
_Binary: jarvis vs ollama_local — pre-check for Phase 4._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_binary_jarvis_vs_ollama.py#L40) |

## `scripts/interlanguage_classifier_final.py`
_Phase 3 FINAL classifier — pre-registered method, full 7-day data._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_raw` | `()` | Load all interlanguage_practice rows from the sqlite DB, keeping only | [src](../../../scripts/interlanguage_classifier_final.py#L110) |
| function | `apply_gap_filter` | `(rows)` | Drop peer rows (NOT jarvis rows) inside gap #1's hardware-rotation | [src](../../../scripts/interlanguage_classifier_final.py#L126) |
| function | `cleanup` | `(rows)` | Apply pre-registered §1 cleanup: drop rows with no primitive glyph, | [src](../../../scripts/interlanguage_classifier_final.py#L157) |
| function | `featurize` | `(rows, embedder)` | Build the 403-dim feature matrix: normalized sentence embeddings (384) | [src](../../../scripts/interlanguage_classifier_final.py#L191) |
| function | `permutation_p` | `(clf_template, X_train, y_train, X_test, y_test, observed_acc, n=…)` | Permutation test for classifier accuracy: refit a LogisticRegression on | [src](../../../scripts/interlanguage_classifier_final.py#L209) |
| function | `per_row_interpretation` | `(report_dict, cohort_counts)` | Pre-registered note: overall accuracy is misleading under cohort | [src](../../../scripts/interlanguage_classifier_final.py#L229) |
| function | `render_cohort_balance` | `(kept_per_peer)` | Surface cohort balance with FROZEN annotation per gap #2. | [src](../../../scripts/interlanguage_classifier_final.py#L255) |
| function | `render_text_report` | `(report)` | Format the full report for human reading. | [src](../../../scripts/interlanguage_classifier_final.py#L284) |
| function | `run` | `()` | Execute the full pre-registered Phase 3 pipeline and return the report dict. | [src](../../../scripts/interlanguage_classifier_final.py#L394) |
| function | `main` | `()` | CLI entry point. Parses --json/--allow-early, enforces the pre-registered | [src](../../../scripts/interlanguage_classifier_final.py#L500) |

## `scripts/interlanguage_classifier_interim.py`
_Interim Phase 3 classifier — pre-registered method, partial data._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_raw` | `()` | — | [src](../../../scripts/interlanguage_classifier_interim.py#L49) |
| function | `cleanup` | `(rows)` | Pre-registreret cleanup (§1): | [src](../../../scripts/interlanguage_classifier_interim.py#L62) |
| function | `featurize` | `(rows, embedder)` | — | [src](../../../scripts/interlanguage_classifier_interim.py#L101) |
| function | `permutation_p` | `(clf_template, X_train, y_train, X_test, y_test, observed_acc, n=…)` | — | [src](../../../scripts/interlanguage_classifier_interim.py#L118) |
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_classifier_interim.py#L136) |

## `scripts/interlanguage_drift_classifier.py`
_Phase 3 supplementary — drift-feature classifier for jarvis vs random._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_peer_expressions` | `(peer)` | Pull all post-cleanup expressions for one peer, chronologically ordered. | [src](../../../scripts/interlanguage_drift_classifier.py#L60) |
| function | `featurize_snapshot` | `(expressions)` | 19-dim: 5 op-freqs + 14 vocab-freqs (relative to total ops + total vocab). | [src](../../../scripts/interlanguage_drift_classifier.py#L89) |
| function | `featurize_chunk` | `(chunk)` | Return (snapshot_19, drift_19) where drift = late_half - early_half. | [src](../../../scripts/interlanguage_drift_classifier.py#L106) |
| function | `build_chunks_for_peer` | `(peer)` | Chunk expressions chronologically; return [(snapshot, drift), ...]. | [src](../../../scripts/interlanguage_drift_classifier.py#L119) |
| function | `run` | `(allow_early)` | — | [src](../../../scripts/interlanguage_drift_classifier.py#L128) |
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_drift_classifier.py#L211) |

## `scripts/interlanguage_llm_judge.py`
_LLM-judge for interlanguage validation — Phase 3+4 pre-registered design._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_expressions` | `(peer_id, *, days=…, limit=…)` | Pull expression_text for a peer from the interlanguage_practice table. | [src](../../../scripts/interlanguage_llm_judge.py#L58) |
| function | `_ollama_chat` | `(model, prompt, *, timeout=…, retries=…)` | — | [src](../../../scripts/interlanguage_llm_judge.py#L73) |
| function | `_parse_entity` | `(raw)` | Match first token of judge reply to an entity name (case-insensitive). | [src](../../../scripts/interlanguage_llm_judge.py#L98) |
| function | `run_alpha` | `(model, *, seed=…)` | — | [src](../../../scripts/interlanguage_llm_judge.py#L110) |
| function | `run_delta` | `(model, *, seed=…)` | — | [src](../../../scripts/interlanguage_llm_judge.py#L159) |
| function | `_binomial_p` | `(k, n, p0)` | One-sided binomial p-value: P(X >= k) under H0 with prob p0. | [src](../../../scripts/interlanguage_llm_judge.py#L209) |
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_llm_judge.py#L225) |

## `scripts/interlanguage_structural_classifier.py`
_Structural-feature classifier for interlanguage expressions._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_rows` | `()` | Mirror the official classifier's row loading + cleanup. | [src](../../../scripts/interlanguage_structural_classifier.py#L44) |
| function | `split_clauses` | `(text)` | Split expression into clauses by | separator. | [src](../../../scripts/interlanguage_structural_classifier.py#L89) |
| function | `first_token` | `(clause)` | First word/concept of a clause (before any operator). | [src](../../../scripts/interlanguage_structural_classifier.py#L94) |
| function | `count_operators` | `(text)` | Count each operator occurrence. | [src](../../../scripts/interlanguage_structural_classifier.py#L100) |
| function | `is_standalone_negation` | `(clause)` | A clause like '!lys' with no operator after the negated word. | [src](../../../scripts/interlanguage_structural_classifier.py#L105) |
| function | `extract_features` | `(text)` | Engineered features per Bjørn's heuristics. | [src](../../../scripts/interlanguage_structural_classifier.py#L112) |
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_structural_classifier.py#L174) |

## `scripts/jarvis.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `cmd_bootstrap` | `(_)` | Ensure runtime dirs, init the DB, create the default workspace, and print its path. | [src](../../../scripts/jarvis.py#L98) |
| function | `cmd_events` | `(args)` | Print the most recent eventbus events as JSON, up to args.limit. | [src](../../../scripts/jarvis.py#L107) |
| function | `cmd_health` | `(_)` | Print a health JSON with ok, app name and environment from loaded settings. | [src](../../../scripts/jarvis.py#L113) |
| function | `cmd_overview` | `(_)` | Print a JSON overview: visible execution/run truth, event count, cost telemetry | [src](../../../scripts/jarvis.py#L130) |
| function | `cmd_config` | `(_)` | Print the current config as JSON: visible execution truth, workspace capabilities, | [src](../../../scripts/jarvis.py#L168) |
| function | `cmd_coding_lane_status` | `(_)` | Print the coding lane execution truth as JSON. | [src](../../../scripts/jarvis.py#L205) |
| function | `cmd_local_lane_status` | `(_)` | Print the local lane execution truth as JSON. | [src](../../../scripts/jarvis.py#L218) |
| function | `cmd_workspace` | `(args)` | Ensure the workspace named args.name exists and print its path, existence and file list as JSON. | [src](../../../scripts/jarvis.py#L231) |
| function | `cmd_cancel_visible_run` | `(args)` | Cancel a visible run and print the result as JSON. | [src](../../../scripts/jarvis.py#L249) |
| function | `cmd_discord_setup` | `(_)` | Interactive wizard to configure the Discord gateway. | [src](../../../scripts/jarvis.py#L333) |
| function | `cmd_discord_status` | `(_)` | Show Discord gateway config and connection status. | [src](../../../scripts/jarvis.py#L414) |
| function | `build_parser` | `()` | Build and return the argparse parser wiring every jarvis subcommand to its handler. | [src](../../../scripts/jarvis.py#L434) |
| function | `_event_count` | `()` | — | [src](../../../scripts/jarvis.py#L679) |
| function | `_visible_run_truth` | `()` | — | [src](../../../scripts/jarvis.py#L684) |
| function | `_visible_execution_truth` | `()` | — | [src](../../../scripts/jarvis.py#L702) |
| function | `_capability_invocation_truth` | `()` | — | [src](../../../scripts/jarvis.py#L751) |
| function | `main` | `()` | CLI entry point: parse arguments and dispatch to the selected subcommand handler. | [src](../../../scripts/jarvis.py#L766) |

## `scripts/jarvis_bare_practice_runner.py`
_jarvis_bare practice runner — stripped-bare interlanguage expression generator._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_model` | `(prompt, *, timeout=…)` | Call deepseek-v4.1-flash:cloud via local Ollama. Returns text or None. | [src](../../../scripts/jarvis_bare_practice_runner.py#L64) |
| function | `_build_bare_prompt` | `()` | Build the minimal bare prompt: system line + protocol + instruction. | [src](../../../scripts/jarvis_bare_practice_runner.py#L118) |
| function | `_preflight_check` | `()` | Run a quick model ping before starting the loop. | [src](../../../scripts/jarvis_bare_practice_runner.py#L150) |
| function | `_ping_model` | `()` | Quick ping to verify model is reachable. Returns True if OK. | [src](../../../scripts/jarvis_bare_practice_runner.py#L176) |
| function | `run_one_tick` | `()` | Generate one bare expression, persist it, return expression text or None. | [src](../../../scripts/jarvis_bare_practice_runner.py#L203) |
| function | `_run_once` | `()` | Run a single tick and print result. Used by --once. | [src](../../../scripts/jarvis_bare_practice_runner.py#L222) |
| function | `_run_loop` | `(args)` | Run forever (or for args.hours hours) with args.interval_min between ticks. | [src](../../../scripts/jarvis_bare_practice_runner.py#L232) |
| function | `main` | `()` | — | [src](../../../scripts/jarvis_bare_practice_runner.py#L318) |

## `scripts/krypter_medlems_chat.py`
_Krypter de medlems-chatbeskeder der allerede ligger i klartekst (task 3.3)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_db_sti` | `()` | — | [src](../../../scripts/krypter_medlems_chat.py#L45) |
| function | `find_kandidater` | `(conn)` | Rækker i en MEDLEMS-SESSION der endnu ikke er krypteret. | [src](../../../scripts/krypter_medlems_chat.py#L49) |
| function | `koer` | `(sti, *, goer_det)` | — | [src](../../../scripts/krypter_medlems_chat.py#L76) |
| function | `main` | `()` | — | [src](../../../scripts/krypter_medlems_chat.py#L145) |

## `scripts/laering_status.py`
_Hvad fangede laeringskredsloebet siden nulpunktet?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/laering_status.py#L23) |

## `scripts/ledger_rehearsal.py`
_Generalprøve: kan ledgeren holde RIGTIGE samtaler?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `kopiér` | `(antal, mindst, hoejst)` | — | [src](../../../scripts/ledger_rehearsal.py#L39) |
| function | `main` | `()` | — | [src](../../../scripts/ledger_rehearsal.py#L70) |

## `scripts/link_google_email.py`
_Admin-migration: knyt Google-email til eksisterende konti (§12)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/link_google_email.py#L21) |

## `scripts/luk_foraeldede_flows.py`
_Engangs-oprydning: luk flows hvis opgave allerede er afsluttet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find_testdata` | `(conn)` | — | [src](../../../scripts/luk_foraeldede_flows.py#L53) |
| function | `annuller_testdata` | `(conn, testdata)` | — | [src](../../../scripts/luk_foraeldede_flows.py#L66) |
| function | `find_foraeldede` | `(conn)` | — | [src](../../../scripts/luk_foraeldede_flows.py#L78) |
| function | `luk` | `(conn, foraeldede)` | — | [src](../../../scripts/luk_foraeldede_flows.py#L92) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/luk_foraeldede_flows.py#L109) |

## `scripts/maal_indbakke.py`
_Virker indbakkens to trin? Og er 2 det rigtige tal?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_iso_graense` | `(dage)` | `strftime`, ikke `datetime('now', …)`. | [src](../../../scripts/maal_indbakke.py#L69) |
| function | `_haent` | `(dage)` | — | [src](../../../scripts/maal_indbakke.py#L82) |
| function | `_poster_i` | `(payload)` | Post-id'erne i en hændelse, uanset om den bærer én eller mange. | [src](../../../scripts/maal_indbakke.py#L103) |
| function | `maal` | `(dage=…)` | — | [src](../../../scripts/maal_indbakke.py#L113) |
| function | `_taerskel` | `()` | — | [src](../../../scripts/maal_indbakke.py#L187) |
| function | `_tilstand` | `()` | Hvad STAAR der i tabellen lige nu, uanset hvad sporet siger? | [src](../../../scripts/maal_indbakke.py#L198) |
| function | `main` | `()` | — | [src](../../../scripts/maal_indbakke.py#L214) |
| function | `registrer_vindue` | `(timer=…)` | Opgave 7 trin 3: registrér maalevinduet, saa paamindelsen melder. | [src](../../../scripts/maal_indbakke.py#L265) |

## `scripts/maal_raesonnering_ab.py`
_A/B: koster det noget at lade mellem-runderne vaere uden raesonnering?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `armdata` | `(db, *, dage=…, procent=…, siden=…)` | {arm: {ud, raeson, runs, runder, pr_dag}} — kilden BAADE CLI og monitor laeser. | [src](../../../scripts/maal_raesonnering_ab.py#L55) |
| function | `runder_pr_run_pr_dag` | `(arm, *, min_runs=…)` | Dagsserien for én arm. Dage med for faa runs udelades — én run paa en | [src](../../../scripts/maal_raesonnering_ab.py#L104) |
| function | `main` | `()` | — | [src](../../../scripts/maal_raesonnering_ab.py#L115) |

## `scripts/maal_vaerktoejer_pr_runde.py`
_Vaerktoejer pr. agentisk runde — dagsserie._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `dagsserie` | `(db, dage)` | Dagsserien, som BAADE denne CLI og monitoren laeser. | [src](../../../scripts/maal_vaerktoejer_pr_runde.py#L69) |
| function | `main` | `()` | — | [src](../../../scripts/maal_vaerktoejer_pr_runde.py#L83) |

## `scripts/maal_ventende_i_prompten.py`
_Hvor meget af Jarvis' synlige prompt er VENTENDE TILSTAND?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_label_of` | `(tekst)` | Identisk med `prompt_contract._label_of` — med vilje samme regel. | [src](../../../scripts/maal_ventende_i_prompten.py#L70) |
| function | `split_system_by_sections` | `(tekst)` | (navn, tegn, tokens) per blok, navngivet som runtimen navngiver sine dele. | [src](../../../scripts/maal_ventende_i_prompten.py#L77) |
| function | `_er_ventende` | `(navn)` | — | [src](../../../scripts/maal_ventende_i_prompten.py#L138) |
| function | `_del_ved_halen` | `(tekst)` | (stabilt prefix, dynamisk hale). Halen er det EFTER sentinel'en. | [src](../../../scripts/maal_ventende_i_prompten.py#L143) |
| function | `_byg` | `(provider, model, besked, session_id)` | — | [src](../../../scripts/maal_ventende_i_prompten.py#L158) |
| function | `_maal_en_del` | `(navn, tekst)` | Sektionér én del (prefix eller hale) og del tokens i ventende/andet. | [src](../../../scripts/maal_ventende_i_prompten.py#L166) |
| function | `_maal_aendring` | `(tekster)` | Hvilke sektioner ændrede sig mellem bygningerne? | [src](../../../scripts/maal_ventende_i_prompten.py#L194) |
| function | `main` | `()` | — | [src](../../../scripts/maal_ventende_i_prompten.py#L252) |

## `scripts/measure_prompt_payload.py`
_Measure where Jarvis's visible-chat prompt tokens come from._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `count_tokens` | `(text)` | Count tokens with tiktoken if available; else chars/4 estimate. | [src](../../../scripts/measure_prompt_payload.py#L35) |
| function | `split_system_by_sections` | `(text)` | Split a system prompt into (header, char_count, token_count) tuples. | [src](../../../scripts/measure_prompt_payload.py#L57) |
| function | `main` | `()` | — | [src](../../../scripts/measure_prompt_payload.py#L80) |

## `scripts/measure_turn_latency.py`
_Mål Jarvis' svartid — fra send til svar._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_token` | `()` | — | [src](../../../scripts/measure_turn_latency.py#L37) |
| function | `_parse` | `(ts)` | — | [src](../../../scripts/measure_turn_latency.py#L42) |
| function | `_turns` | `(session_id, limit=…)` | Par bruger-besked med det følgende assistent-svar. | [src](../../../scripts/measure_turn_latency.py#L52) |
| function | `_provider_for` | `(asked_at, answered_at)` | Hvilken provider betjente turen. | [src](../../../scripts/measure_turn_latency.py#L76) |
| function | `watch` | `(session_id)` | — | [src](../../../scripts/measure_turn_latency.py#L101) |
| function | `_api` | `(path, payload=…, stream=…)` | — | [src](../../../scripts/measure_turn_latency.py#L123) |
| function | `probe` | `(rounds, message)` | — | [src](../../../scripts/measure_turn_latency.py#L134) |

## `scripts/memory_md_dedupe_headings.py`
_Merge duplicate `## ` headings in a MEMORY.md (memory repair 2026-09-04, R7)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_norm` | `(heading)` | — | [src](../../../scripts/memory_md_dedupe_headings.py#L24) |
| function | `dedupe_headings` | `(text)` | Return (new_text, merged_count). Only `## ` headings are merged. | [src](../../../scripts/memory_md_dedupe_headings.py#L28) |
| function | `dedupe_file` | `(path, *, apply)` | — | [src](../../../scripts/memory_md_dedupe_headings.py#L78) |
| function | `main` | `()` | — | [src](../../../scripts/memory_md_dedupe_headings.py#L92) |

## `scripts/memory_noise_cleanup.py`
_One-off data cleanup after the memory repair (2026-09-04, Task 8)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_table_exists` | `(conn, name)` | — | [src](../../../scripts/memory_noise_cleanup.py#L43) |
| function | `step_brain_salience` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L50) |
| function | `step_policies_dedupe` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L56) |
| function | `step_experiential_empty` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L89) |
| function | `step_partner_facts` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L104) |
| function | `step_embeddings_released` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L123) |
| function | `step_retained_templates` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L140) |
| function | `step_md_proposals_stale` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L161) |
| function | `step_fts_rebuild` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L183) |
| function | `step_memory_md_dedupe` | `(apply)` | — | [src](../../../scripts/memory_noise_cleanup.py#L190) |
| function | `backup` | `(backup_dir)` | Consistent SQLite backup (sqlite3 backup API, safe with WAL) + MEMORY.md copy. | [src](../../../scripts/memory_noise_cleanup.py#L216) |
| function | `run` | `(*, apply, only=…, backup_dir=…)` | — | [src](../../../scripts/memory_noise_cleanup.py#L241) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/memory_noise_cleanup.py#L256) |

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

## `scripts/migrer_filer_per_bruger.py`
_Flyt de gamle fælles filer ind i ejerens egen mappe._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hash` | `(p)` | — | [src](../../../scripts/migrer_filer_per_bruger.py#L42) |
| function | `find_ejer` | `()` | Ejerens workspace-navn. Tom streng når det ikke kan afgøres. | [src](../../../scripts/migrer_filer_per_bruger.py#L50) |
| function | `migrer` | `(*, udfoer, ejer_ws=…)` | — | [src](../../../scripts/migrer_filer_per_bruger.py#L62) |

## `scripts/migrer_shared_runtime_til_state_store.py`
_Flyt seks moduler fra `shared/runtime/*.json` til `state_store`._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_gammel_sti` | `(navn)` | — | [src](../../../scripts/migrer_shared_runtime_til_state_store.py#L52) |
| function | `_har_indhold` | `(data)` | Tom liste/dict tæller ikke som indhold — så må den gerne overskrives. | [src](../../../scripts/migrer_shared_runtime_til_state_store.py#L56) |
| function | `flyt` | `(navn, *, toerloeb)` | Returnér (status, forklaring) for ét modul. | [src](../../../scripts/migrer_shared_runtime_til_state_store.py#L65) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/migrer_shared_runtime_til_state_store.py#L94) |

## `scripts/minimal_mode_baseline.py`
_Minimal-mode-basislinje — hvad kan modellen UDEN Jarvis' stillads?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_kald` | `(beskeder, *, timeout=…)` | — | [src](../../../scripts/minimal_mode_baseline.py#L153) |
| function | `_koer` | `(cmd, cwd, timeout=…)` | — | [src](../../../scripts/minimal_mode_baseline.py#L173) |
| function | `_udfoer_vaerktoej` | `(navn, args, mappe)` | — | [src](../../../scripts/minimal_mode_baseline.py#L184) |
| function | `koer_opgave` | `(navn, spec, *, maks_runder)` | — | [src](../../../scripts/minimal_mode_baseline.py#L206) |
| function | `main` | `()` | — | [src](../../../scripts/minimal_mode_baseline.py#L248) |

## `scripts/mint_jarvisx_token.py`
_Mint a JarvisX bearer token for a user._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_registry_path` | `()` | — | [src](../../../scripts/mint_jarvisx_token.py#L35) |
| function | `_append_registry` | `(entry)` | Append a token-issue entry to the audit registry. Best-effort. | [src](../../../scripts/mint_jarvisx_token.py#L40) |
| function | `main` | `()` | — | [src](../../../scripts/mint_jarvisx_token.py#L52) |

## `scripts/model_catalogue_sweep.py`
_Ugentlig gennemgang af cheap lane: hvilke modeller lever, og hvad kan de?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/model_catalogue_sweep.py#L36) |

## `scripts/navngiv_kode_sessioner.py`
_Døb de sessioner der aldrig fik et navn, efter deres første brugerbesked._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/navngiv_kode_sessioner.py#L27) |

## `scripts/normalize_sensory_sources.py`
_Normalisér kilde-navnene i Sansernes Arkiv — én gang, med tør-kørsel først._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_laes_alle` | `(conn)` | — | [src](../../../scripts/normalize_sensory_sources.py#L30) |
| function | `_plan` | `(rows)` | Returnér (id, gammel_json, ny_json, nye_metadata) for rækker der ændres. | [src](../../../scripts/normalize_sensory_sources.py#L35) |
| function | `main` | `()` | — | [src](../../../scripts/normalize_sensory_sources.py#L59) |

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
| function | `_generate_ollama_local` | `(prompt)` | deepseek-v4.1-flash:cloud via lokal Ollama (samme model som Jarvis). | [src](../../../scripts/peer_models.py#L85) |
| function | `_generate_random` | `(prompt)` | Random baseline — bruger generate_state_expression() uden mood-bias. | [src](../../../scripts/peer_models.py#L99) |
| function | `generate` | `(prompt, peer_id)` | Dispatch til peer-specific adapter. Raise ValueError ved ukendt peer. | [src](../../../scripts/peer_models.py#L123) |

## `scripts/peer_practice_runner.py`
_Peer practice runner — kører kontinuerligt i ~7 dage per peer._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_build_prompt` | `(mood, seed_expressions=…)` | Build per-tick prompt fra protokol + mood + valgfri seed. | [src](../../../scripts/peer_practice_runner.py#L39) |
| function | `run_one_tick` | `(*, peer_id, mood_trace, use_seed=…)` | Generér og persistér én expression for peer. Returnér expression eller None ved fejl. | [src](../../../scripts/peer_practice_runner.py#L69) |
| function | `main` | `()` | — | [src](../../../scripts/peer_practice_runner.py#L106) |

## `scripts/perception_mix.py`
_Hvad består Jarvis' perception af — og hvor meget af den er hans egen støj?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_hent` | `(siden)` | — | [src](../../../scripts/perception_mix.py#L42) |
| function | `_tabel` | `(navn, taelling, i_alt)` | — | [src](../../../scripts/perception_mix.py#L64) |
| function | `main` | `()` | — | [src](../../../scripts/perception_mix.py#L72) |

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

