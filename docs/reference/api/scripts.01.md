# `scripts.01` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/__init__.py`

_(no top-level classes or functions)_

## `scripts/api_docs_gen.py`
_Generate per-package codebase reference under docs/reference/api/ from AST (static, stdlib only)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `iter_py` | `(root=…)` | — | [src](../../../scripts/api_docs_gen.py#L20) |
| function | `_sig` | `(node)` | — | [src](../../../scripts/api_docs_gen.py#L28) |
| function | `_summary` | `(node)` | — | [src](../../../scripts/api_docs_gen.py#L46) |
| function | `module_entry` | `(text, relpath)` | — | [src](../../../scripts/api_docs_gen.py#L51) |
| function | `package_of` | `(relpath)` | — | [src](../../../scripts/api_docs_gen.py#L72) |
| function | `page_id` | `(pkg, module_name, sorted_names, chunk=…)` | — | [src](../../../scripts/api_docs_gen.py#L77) |
| function | `_is_public` | `(name)` | — | [src](../../../scripts/api_docs_gen.py#L89) |
| function | `coverage` | `(entries)` | — | [src](../../../scripts/api_docs_gen.py#L93) |
| function | `render_package_md` | `(page, entries)` | — | [src](../../../scripts/api_docs_gen.py#L112) |
| function | `render_index_md` | `(pages, cov)` | — | [src](../../../scripts/api_docs_gen.py#L134) |
| function | `render_coverage_md` | `(cov)` | — | [src](../../../scripts/api_docs_gen.py#L156) |
| function | `build` | `()` | — | [src](../../../scripts/api_docs_gen.py#L174) |
| function | `main` | `()` | — | [src](../../../scripts/api_docs_gen.py#L189) |

## `scripts/api_reference_gen.py`
_Generate docs/reference/API_REFERENCE.md from the FastAPI app (ground truth)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `routes_from_app` | `(app)` | Read real mounted routes from a FastAPI app. Pure over the app object. | [src](../../../scripts/api_reference_gen.py#L19) |
| function | `routes_from_ast` | `(routes_dir=…)` | Fallback: scan route files for @router.<method>("path") decorators (no import). | [src](../../../scripts/api_reference_gen.py#L38) |
| function | `collect_routes` | `()` | Try the live app first; fall back to AST. Returns (rows, source). | [src](../../../scripts/api_reference_gen.py#L51) |
| function | `render_md` | `(rows, source=…)` | — | [src](../../../scripts/api_reference_gen.py#L63) |
| function | `main` | `()` | — | [src](../../../scripts/api_reference_gen.py#L74) |

## `scripts/bench_ollama_concurrency.py`
_Reproducérbart latency/concurrency-benchmark for Ollama-lanen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call` | `(model, stream, prompt)` | Returnér (ttft, total) i sekunder. ttft=None for non-stream. | [src](../../../scripts/bench_ollama_concurrency.py#L32) |
| function | `_median` | `(xs)` | — | [src](../../../scripts/bench_ollama_concurrency.py#L54) |
| function | `bench_chat` | `(model, n=…)` | Chat-responsivitet: TTFT + fuld svartid (streaming), median af n. | [src](../../../scripts/bench_ollama_concurrency.py#L58) |
| function | `bench_sequential_loop` | `(model, rounds=…, n=…)` | Agentisk kompounding: `rounds` sekventielle kald (hver venter på forrige). | [src](../../../scripts/bench_ollama_concurrency.py#L68) |
| function | `bench_concurrency` | `(model, ks=…)` | Concurrency-skalering: K parallelle kald, wall-clock pr. K. | [src](../../../scripts/bench_ollama_concurrency.py#L79) |
| function | `main` | `()` | — | [src](../../../scripts/bench_ollama_concurrency.py#L93) |

## `scripts/cache_rate_monitor.py`
_Cache hit rate monitor._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_aggregate_events` | `(rows)` | Aggregate hit/miss across a list of cost.recorded payloads. | [src](../../../scripts/cache_rate_monitor.py#L38) |
| function | `_by_lane` | `(rows)` | Same aggregation grouped by lane. | [src](../../../scripts/cache_rate_monitor.py#L64) |
| function | `_fetch_costs` | `(con, since_sql)` | Fetch cost rows from the costs table as dicts with cache_hit/miss keys. | [src](../../../scripts/cache_rate_monitor.py#L73) |
| function | `collect_snapshot` | `()` | Read costs from DB and produce a rich snapshot — ALL lanes. | [src](../../../scripts/cache_rate_monitor.py#L94) |
| function | `append_log` | `(snapshot)` | — | [src](../../../scripts/cache_rate_monitor.py#L118) |
| function | `main` | `()` | — | [src](../../../scripts/cache_rate_monitor.py#L124) |

## `scripts/capabilities_gen.py`
_Generate docs/reference/CAPABILITIES.md from the live tool registry. Regenerable._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `tools_from_registry` | `(handlers, mutating)` | Pure: map the name→handler registry to rows with kind + mutating flag. | [src](../../../scripts/capabilities_gen.py#L15) |
| function | `render_md` | `(rows)` | — | [src](../../../scripts/capabilities_gen.py#L24) |
| function | `collect` | `()` | — | [src](../../../scripts/capabilities_gen.py#L35) |
| function | `main` | `()` | — | [src](../../../scripts/capabilities_gen.py#L44) |

## `scripts/capability_audit.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `ServiceSignals` | `` | — | [src](../../../scripts/capability_audit.py#L45) |
| function | `module_name_from_path` | `(path, repo_root=…)` | — | [src](../../../scripts/capability_audit.py#L61) |
| function | `find_python_files` | `(root)` | — | [src](../../../scripts/capability_audit.py#L71) |
| function | `resolve_relative_import` | `(current_module, module, level)` | — | [src](../../../scripts/capability_audit.py#L84) |
| function | `normalize_candidates` | `(candidates, known_modules)` | — | [src](../../../scripts/capability_audit.py#L101) |
| function | `parse_imports` | `(path, *, current_module=…, known_modules=…)` | — | [src](../../../scripts/capability_audit.py#L121) |
| function | `compute_reachability` | `(graph, entry_modules)` | — | [src](../../../scripts/capability_audit.py#L167) |
| function | `score_service` | `(signals)` | — | [src](../../../scripts/capability_audit.py#L188) |
| function | `git_last_touch` | `(path)` | — | [src](../../../scripts/capability_audit.py#L214) |
| function | `entry_modules` | `()` | — | [src](../../../scripts/capability_audit.py#L246) |
| function | `service_note` | `(signals, score)` | — | [src](../../../scripts/capability_audit.py#L254) |
| function | `render_markdown` | `(signals_list)` | — | [src](../../../scripts/capability_audit.py#L267) |
| function | `analyze_services` | `()` | — | [src](../../../scripts/capability_audit.py#L361) |
| function | `print_summary` | `(signals_list)` | — | [src](../../../scripts/capability_audit.py#L416) |
| function | `main` | `()` | — | [src](../../../scripts/capability_audit.py#L427) |

## `scripts/central_connectivity_audit.py`
_central_connectivity_audit.py — HOLDBART kort over hvad der er koblet til Centralen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_route_families` | `()` | Læs FAMILY_ROUTES ∪ PRIVATE_NO_EGRESS_ROUTES's nøgler direkte fra broen (AST). | [src](../../../scripts/central_connectivity_audit.py#L85) |
| function | `_code_only` | `(src)` | Fjern kommentarer + blank string-INDHOLD (behold koden) → signal-scan tæller ikke | [src](../../../scripts/central_connectivity_audit.py#L107) |
| function | `_family_of` | `(event_name)` | — | [src](../../../scripts/central_connectivity_audit.py#L124) |
| function | `scan` | `()` | — | [src](../../../scripts/central_connectivity_audit.py#L131) |
| function | `render_md` | `(data)` | — | [src](../../../scripts/central_connectivity_audit.py#L189) |
| function | `main` | `()` | — | [src](../../../scripts/central_connectivity_audit.py#L237) |

## `scripts/db_decomposition_map.py`
_Read-only db.py dekomponerings-kort — grupperer 171 tabeller i naturlige domæner efter_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find` | `(x)` | — | [src](../../../scripts/db_decomposition_map.py#L36) |
| function | `union` | `(a, b)` | — | [src](../../../scripts/db_decomposition_map.py#L40) |
| function | `comp_of` | `(t)` | — | [src](../../../scripts/db_decomposition_map.py#L55) |

## `scripts/db_path_fixture_audit.py`
_Audit: find test fixtures that monkeypatch DB_PATH on db but not db_core._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/db_path_fixture_audit.py#L20) |

## `scripts/db_split_baseline.py`
_Mål cold + warm import-tid for core.runtime.db._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `measure` | `(label)` | — | [src](../../../scripts/db_split_baseline.py#L18) |
| function | `main` | `()` | — | [src](../../../scripts/db_split_baseline.py#L43) |

## `scripts/docs_audit.py`
_SP1 docs auditor — classify docs/*.md against git+runtime truth. Regenerable, static_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find_docs` | `(root=…)` | — | [src](../../../scripts/docs_audit.py#L22) |
| function | `extract_references` | `(text)` | — | [src](../../../scripts/docs_audit.py#L26) |
| function | `liveness` | `(refs, repo_root=…)` | — | [src](../../../scripts/docs_audit.py#L32) |
| function | `git_last_touch` | `(path, repo_root=…)` | — | [src](../../../scripts/docs_audit.py#L40) |
| function | `title_and_headings` | `(text)` | — | [src](../../../scripts/docs_audit.py#L53) |
| function | `detect_superseded` | `(docs)` | docs: [{path,title,headings,days}]. Older doc is superseded by a NEWER doc that shares the | [src](../../../scripts/docs_audit.py#L66) |
| function | `feature_shipped` | `(refs, repo_root=…)` | A superpowers spec/plan 'shipped' if any referenced path exists, or a key symbol is in the tree. | [src](../../../scripts/docs_audit.py#L84) |
| function | `classify_heuristic` | `(*, path, refs, live, days, superseded_by, is_superpowers, shipped)` | — | [src](../../../scripts/docs_audit.py#L99) |
| function | `_yaml_val` | `(v)` | — | [src](../../../scripts/docs_audit.py#L123) |
| function | `stamp_frontmatter` | `(text, fields)` | Idempotent, surgical YAML frontmatter merge: replaces only the given keys, preserves the rest | [src](../../../scripts/docs_audit.py#L128) |
| function | `render_manifest_md` | `(entries)` | — | [src](../../../scripts/docs_audit.py#L142) |
| function | `build_gap_list` | `(entries)` | Coarse subsystem coverage: which _SUBSYSTEMS have NO færdig doc referencing them. | [src](../../../scripts/docs_audit.py#L152) |
| function | `audit` | `()` | — | [src](../../../scripts/docs_audit.py#L164) |
| function | `main` | `()` | — | [src](../../../scripts/docs_audit.py#L191) |

## `scripts/docs_drift_check.py`
_SP5 docs-drift checker — catch when docs/ diverges from git+runtime truth._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find_docs` | `(root=…)` | — | [src](../../../scripts/docs_drift_check.py#L29) |
| function | `_norm` | `(text)` | Neutralize volatile 'Generated <date>' stamps so regeneration diffs are content-only. | [src](../../../scripts/docs_drift_check.py#L33) |
| function | `broken_links` | `(docs_root=…)` | — | [src](../../../scripts/docs_drift_check.py#L39) |
| function | `_load_script` | `(name)` | — | [src](../../../scripts/docs_drift_check.py#L76) |
| function | `_expected_api_docs` | `()` | — | [src](../../../scripts/docs_drift_check.py#L83) |
| function | `_expected_api_reference` | `()` | — | [src](../../../scripts/docs_drift_check.py#L93) |
| function | `_expected_capabilities` | `()` | — | [src](../../../scripts/docs_drift_check.py#L99) |
| function | `_staged_under` | `(source_dirs, staged)` | — | [src](../../../scripts/docs_drift_check.py#L112) |
| function | `stale_generated` | `(only_dirs=…, repo=…)` | — | [src](../../../scripts/docs_drift_check.py#L116) |
| function | `prose_drift` | `(docs_root=…, repo=…)` | — | [src](../../../scripts/docs_drift_check.py#L135) |
| function | `requirements_drift` | `(repo=…)` | — | [src](../../../scripts/docs_drift_check.py#L150) |
| function | `staged_paths` | `(repo=…)` | — | [src](../../../scripts/docs_drift_check.py#L168) |
| function | `hard_drift` | `(staged=…, repo=…)` | — | [src](../../../scripts/docs_drift_check.py#L177) |
| function | `run_check` | `(repo=…, staged=…)` | — | [src](../../../scripts/docs_drift_check.py#L182) |
| function | `main` | `()` | — | [src](../../../scripts/docs_drift_check.py#L193) |

## `scripts/enforce_commit_hygiene.py`
_Pre-commit hook: catch kitchen-sink commits._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_staged_files` | `()` | — | [src](../../../scripts/enforce_commit_hygiene.py#L53) |
| function | `_classify` | `(path)` | — | [src](../../../scripts/enforce_commit_hygiene.py#L63) |
| function | `main` | `()` | — | [src](../../../scripts/enforce_commit_hygiene.py#L68) |

## `scripts/enforce_test_coverage.py`
_Pre-commit hook: enforces test coverage for core/ code changes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_covered` | `(path)` | Check if a file path falls under a directory we enforce tests for. | [src](../../../scripts/enforce_test_coverage.py#L135) |
| function | `_expected_test_path` | `(staged_path, repo_root=…)` | Given a staged file path like 'core/services/foo.py', | [src](../../../scripts/enforce_test_coverage.py#L140) |
| function | `main` | `(argv=…)` | Entry point.  Accept optional --repo-root to override REPO_ROOT. | [src](../../../scripts/enforce_test_coverage.py#L166) |

## `scripts/god_file_map.py`
_Read-only god-fil-kort: alle egne .py-filer ≥1500 linjer, karakteriseret (linjer, funktioner,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `own_py_files` | `()` | — | [src](../../../scripts/god_file_map.py#L14) |
| function | `blast` | `(dotted, target_rel)` | — | [src](../../../scripts/god_file_map.py#L24) |

## `scripts/honesty_metrics.py`
_Honesty-metrics — tæl hvor ofte hvert anti-løgn-lag fyrer (16. jun 2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_journal` | `(unit, since)` | — | [src](../../../scripts/honesty_metrics.py#L34) |
| function | `main` | `()` | — | [src](../../../scripts/honesty_metrics.py#L45) |

## `scripts/identity_formation_monitor.py`
_Identity formation monitor — daily snapshot of Jarvis' becoming._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/identity_formation_monitor.py#L36) |

## `scripts/injection_richness_check.py`
_Rigdoms-gate for injektions-migration (spec 2026-07-05 §7)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_lines` | `(text)` | — | [src](../../../scripts/injection_richness_check.py#L10) |
| function | `richness_ok` | `(*, direct, cached)` | — | [src](../../../scripts/injection_richness_check.py#L14) |

## `scripts/interlanguage_binary_jarvis_vs_ollama.py`
_Binary: jarvis vs ollama_local — pre-check for Phase 4._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_binary_jarvis_vs_ollama.py#L40) |

## `scripts/interlanguage_classifier_final.py`
_Phase 3 FINAL classifier — pre-registered method, full 7-day data._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `load_raw` | `()` | — | [src](../../../scripts/interlanguage_classifier_final.py#L110) |
| function | `apply_gap_filter` | `(rows)` | Drop peer rows (NOT jarvis rows) inside gap #1's hardware-rotation | [src](../../../scripts/interlanguage_classifier_final.py#L123) |
| function | `cleanup` | `(rows)` | — | [src](../../../scripts/interlanguage_classifier_final.py#L154) |
| function | `featurize` | `(rows, embedder)` | — | [src](../../../scripts/interlanguage_classifier_final.py#L184) |
| function | `permutation_p` | `(clf_template, X_train, y_train, X_test, y_test, observed_acc, n=…)` | — | [src](../../../scripts/interlanguage_classifier_final.py#L199) |
| function | `per_row_interpretation` | `(report_dict, cohort_counts)` | Pre-registered note: overall accuracy is misleading under cohort | [src](../../../scripts/interlanguage_classifier_final.py#L215) |
| function | `render_cohort_balance` | `(kept_per_peer)` | Surface cohort balance with FROZEN annotation per gap #2. | [src](../../../scripts/interlanguage_classifier_final.py#L241) |
| function | `render_text_report` | `(report)` | Format the full report for human reading. | [src](../../../scripts/interlanguage_classifier_final.py#L270) |
| function | `run` | `()` | — | [src](../../../scripts/interlanguage_classifier_final.py#L380) |
| function | `main` | `()` | — | [src](../../../scripts/interlanguage_classifier_final.py#L481) |

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
| function | `cmd_bootstrap` | `(_)` | — | [src](../../../scripts/jarvis.py#L98) |
| function | `cmd_events` | `(args)` | — | [src](../../../scripts/jarvis.py#L106) |
| function | `cmd_health` | `(_)` | — | [src](../../../scripts/jarvis.py#L111) |
| function | `cmd_overview` | `(_)` | — | [src](../../../scripts/jarvis.py#L127) |
| function | `cmd_config` | `(_)` | — | [src](../../../scripts/jarvis.py#L163) |
| function | `cmd_coding_lane_status` | `(_)` | — | [src](../../../scripts/jarvis.py#L198) |
| function | `cmd_local_lane_status` | `(_)` | — | [src](../../../scripts/jarvis.py#L210) |
| function | `cmd_workspace` | `(args)` | — | [src](../../../scripts/jarvis.py#L222) |
| function | `cmd_cancel_visible_run` | `(args)` | — | [src](../../../scripts/jarvis.py#L239) |
| function | `cmd_discord_setup` | `(_)` | Interactive wizard to configure the Discord gateway. | [src](../../../scripts/jarvis.py#L317) |
| function | `cmd_discord_status` | `(_)` | Show Discord gateway config and connection status. | [src](../../../scripts/jarvis.py#L398) |
| function | `build_parser` | `()` | — | [src](../../../scripts/jarvis.py#L418) |
| function | `_event_count` | `()` | — | [src](../../../scripts/jarvis.py#L662) |
| function | `_visible_run_truth` | `()` | — | [src](../../../scripts/jarvis.py#L667) |
| function | `_visible_execution_truth` | `()` | — | [src](../../../scripts/jarvis.py#L685) |
| function | `_capability_invocation_truth` | `()` | — | [src](../../../scripts/jarvis.py#L734) |
| function | `main` | `()` | — | [src](../../../scripts/jarvis.py#L749) |

## `scripts/jarvis_bare_practice_runner.py`
_jarvis_bare practice runner — stripped-bare interlanguage expression generator._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_call_model` | `(prompt, *, timeout=…)` | Call deepseek-v4-flash:cloud via local Ollama. Returns text or None. | [src](../../../scripts/jarvis_bare_practice_runner.py#L64) |
| function | `_build_bare_prompt` | `()` | Build the minimal bare prompt: system line + protocol + instruction. | [src](../../../scripts/jarvis_bare_practice_runner.py#L118) |
| function | `_preflight_check` | `()` | Run a quick model ping before starting the loop. | [src](../../../scripts/jarvis_bare_practice_runner.py#L150) |
| function | `_ping_model` | `()` | Quick ping to verify model is reachable. Returns True if OK. | [src](../../../scripts/jarvis_bare_practice_runner.py#L176) |
| function | `run_one_tick` | `()` | Generate one bare expression, persist it, return expression text or None. | [src](../../../scripts/jarvis_bare_practice_runner.py#L203) |
| function | `_run_once` | `()` | Run a single tick and print result. Used by --once. | [src](../../../scripts/jarvis_bare_practice_runner.py#L222) |
| function | `_run_loop` | `(args)` | Run forever (or for args.hours hours) with args.interval_min between ticks. | [src](../../../scripts/jarvis_bare_practice_runner.py#L232) |
| function | `main` | `()` | — | [src](../../../scripts/jarvis_bare_practice_runner.py#L318) |

## `scripts/link_google_email.py`
_Admin-migration: knyt Google-email til eksisterende konti (§12)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/link_google_email.py#L21) |

## `scripts/measure_prompt_payload.py`
_Measure where Jarvis's visible-chat prompt tokens come from._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `count_tokens` | `(text)` | Count tokens with tiktoken if available; else chars/4 estimate. | [src](../../../scripts/measure_prompt_payload.py#L35) |
| function | `split_system_by_sections` | `(text)` | Split a system prompt into (header, char_count, token_count) tuples. | [src](../../../scripts/measure_prompt_payload.py#L57) |
| function | `main` | `()` | — | [src](../../../scripts/measure_prompt_payload.py#L80) |

## `scripts/meta_evne_healthcheck.py`
_Meta-evne healthcheck — read-only snapshot of all new tracker stacks._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_connect` | `()` | — | [src](../../../scripts/meta_evne_healthcheck.py#L30) |
| function | `_count` | `(conn, sql, params=…)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L36) |
| function | `_table_exists` | `(conn, name)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L44) |
| function | `_hours_ago` | `(iso)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L51) |
| function | `probe_metacognition` | `(conn)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L66) |
| function | `probe_theory_of_mind` | `(conn)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L96) |
| function | `probe_spatial_entity` | `(conn)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L126) |
| function | `probe_session_inbox` | `(conn)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L146) |
| function | `probe_inner_voice_shadow` | `(conn)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L165) |
| function | `probe_visible_runs` | `(conn)` | Sanity check: is the runtime actually producing visible runs? | [src](../../../scripts/meta_evne_healthcheck.py#L204) |
| function | `render_text` | `(report)` | — | [src](../../../scripts/meta_evne_healthcheck.py#L234) |
| function | `main` | `()` | — | [src](../../../scripts/meta_evne_healthcheck.py#L287) |

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
| function | `load_usage` | `()` | — | [src](../../../scripts/regenerate_tier1.py#L58) |
| function | `load_registered_tools` | `()` | — | [src](../../../scripts/regenerate_tier1.py#L74) |
| function | `compute_new_tier1` | `(usage, registered)` | — | [src](../../../scripts/regenerate_tier1.py#L85) |
| function | `render_literal` | `(names)` | — | [src](../../../scripts/regenerate_tier1.py#L90) |
| function | `replace_literal_in_file` | `(new_literal)` | — | [src](../../../scripts/regenerate_tier1.py#L99) |
| function | `main` | `()` | — | [src](../../../scripts/regenerate_tier1.py#L114) |

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
| function | `seed_personality_vector` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L33) |
| function | `seed_taste_profile` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L79) |
| function | `seed_relationship_texture` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L109) |
| function | `seed_compass` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L150) |
| function | `seed_rhythm` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L162) |
| function | `seed_chronicle` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L185) |
| function | `main` | `()` | — | [src](../../../scripts/seed_cognitive_state.py#L214) |

