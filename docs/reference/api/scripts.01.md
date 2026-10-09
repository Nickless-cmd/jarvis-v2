# `scripts.01` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/__init__.py`

_(no top-level classes or functions)_

## `scripts/api_docs_gen.py`
_Generate per-package codebase reference under docs/reference/api/ from AST (static, stdlib only)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `iter_py` | `(root=…)` | Yield every `.py` file under the SCAN_DIRS of `root`, sorted, skipping | [src](../../../scripts/api_docs_gen.py#L19) |
| function | `_sig` | `(node)` | — | [src](../../../scripts/api_docs_gen.py#L33) |
| function | `_summary` | `(node)` | — | [src](../../../scripts/api_docs_gen.py#L51) |
| function | `module_entry` | `(text, relpath)` | Parse module source `text` into an entry dict for `relpath`: its module | [src](../../../scripts/api_docs_gen.py#L56) |
| function | `package_of` | `(relpath)` | Return the dotted package name for a module `relpath` (its directory | [src](../../../scripts/api_docs_gen.py#L81) |
| function | `page_id` | `(pkg, module_name, sorted_names, chunk=…)` | Return the page id for `module_name` within `pkg`. Packages with at most | [src](../../../scripts/api_docs_gen.py#L88) |
| function | `_is_public` | `(name)` | — | [src](../../../scripts/api_docs_gen.py#L103) |
| function | `coverage` | `(entries)` | Aggregate docstring coverage over module `entries`. Counts functions and | [src](../../../scripts/api_docs_gen.py#L107) |
| function | `render_package_md` | `(page, entries)` | Render the Markdown reference page for `page`: a header plus, per module | [src](../../../scripts/api_docs_gen.py#L130) |
| function | `render_index_md` | `(pages, cov)` | Render the API-reference index (README) Markdown: overall docstring | [src](../../../scripts/api_docs_gen.py#L155) |
| function | `render_coverage_md` | `(cov)` | Render the docstring-coverage report Markdown from a `coverage()` dict: | [src](../../../scripts/api_docs_gen.py#L181) |
| function | `build` | `()` | Scan all source modules and build the reference. Groups module entries by | [src](../../../scripts/api_docs_gen.py#L202) |
| function | `main` | `()` | Build the reference and write it to disk: one Markdown page per page id, | [src](../../../scripts/api_docs_gen.py#L220) |

## `scripts/api_reference_gen.py`
_Generate docs/reference/API_REFERENCE.md from the FastAPI app (ground truth)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `routes_from_app` | `(app)` | Read real mounted routes from a FastAPI app. Pure over the app object. | [src](../../../scripts/api_reference_gen.py#L19) |
| function | `routes_from_ast` | `(routes_dir=…)` | Fallback: scan route files for @router.<method>("path") decorators (no import). | [src](../../../scripts/api_reference_gen.py#L38) |
| function | `collect_routes` | `()` | Try the live app first; fall back to AST. Returns (rows, source). | [src](../../../scripts/api_reference_gen.py#L51) |
| function | `render_md` | `(rows, source=…)` | — | [src](../../../scripts/api_reference_gen.py#L63) |
| function | `main` | `()` | — | [src](../../../scripts/api_reference_gen.py#L74) |

## `scripts/batch_maaling_monitor.py`
_Monitor paa vaerktoejer pr. agentisk runde. Tier medmindre tallet rykker._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `vurder` | `(serie, *, dage=…, min_runder=…)` | Returnerer (dom, snit, antal_taellende_dage). | [src](../../../scripts/batch_maaling_monitor.py#L76) |
| function | `_spredning` | `(tal)` | — | [src](../../../scripts/batch_maaling_monitor.py#L115) |
| function | `vurder_ab` | `(arme)` | Returnerer (dom, linje). Dommen er "knappen_virker_ikke", "forskel" eller None. | [src](../../../scripts/batch_maaling_monitor.py#L122) |
| function | `_besked` | `(dom, snit)` | — | [src](../../../scripts/batch_maaling_monitor.py#L161) |
| function | `_ab_besked` | `(dom, linje)` | (ref, titel, tekst). Ref'et er stabilt pr. dom, saa hver dom siges ÉN gang. | [src](../../../scripts/batch_maaling_monitor.py#L177) |
| function | `main` | `()` | — | [src](../../../scripts/batch_maaling_monitor.py#L204) |

## `scripts/beacon_rapport.py`
_Opgørelse fra vaertens crash-beacon-log._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Proeve` | `` | — | [src](../../../scripts/beacon_rapport.py#L41) |
| function | `_parse_tid` | `(raa)` | — | [src](../../../scripts/beacon_rapport.py#L53) |
| function | `parse_linje` | `(linje)` | Én beacon-linje → Proeve. None hvis linjen ikke er en maaling. | [src](../../../scripts/beacon_rapport.py#L60) |
| function | `find_genstarter` | `(proever)` | Et FALD i uptime = maskinen har vaeret nede imellem to proever. | [src](../../../scripts/beacon_rapport.py#L95) |
| function | `_tal` | `(vaerdier, andel)` | — | [src](../../../scripts/beacon_rapport.py#L108) |
| function | `proevetakt_sekunder` | `(proever)` | Median-afstand mellem to proever. Rapportens vigtigste tal ved en | [src](../../../scripts/beacon_rapport.py#L116) |
| function | `pumpekanal` | `(proever)` | Pumpen er den hurtigste kanal. Den flyttede fra fan5 til fan2 15/9-2026, | [src](../../../scripts/beacon_rapport.py#L129) |
| function | `opgoer` | `(proever)` | — | [src](../../../scripts/beacon_rapport.py#L144) |
| function | `_linje` | `(navn, s, enhed)` | — | [src](../../../scripts/beacon_rapport.py#L174) |
| function | `skriv` | `(rapport, titel)` | — | [src](../../../scripts/beacon_rapport.py#L181) |
| function | `main` | `()` | — | [src](../../../scripts/beacon_rapport.py#L207) |

## `scripts/beacon_vagt.py`
_Vagt paa vaertens beacon-log. Læser linjer fra stdin, skriver KUN hændelser._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `()` | — | [src](../../../scripts/beacon_vagt.py#L37) |

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

## `scripts/block_literal_credentials.py`
_Blokér credential-lignende NAVNE der får en literal streng-VÆRDI._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_tokens` | `(name)` | Split MAIL_PASS / mailPass / mail-pass / mail.pass -> ['mail', 'pass']. | [src](../../../scripts/block_literal_credentials.py#L87) |
| function | `_is_credential_name` | `(name)` | — | [src](../../../scripts/block_literal_credentials.py#L93) |
| function | `_suspicious` | `(line)` | — | [src](../../../scripts/block_literal_credentials.py#L109) |
| function | `check` | `(paths)` | — | [src](../../../scripts/block_literal_credentials.py#L125) |

## `scripts/block_unattributed_rebase.py`
_Reject rebases because replayed commits retain stale actor trailers._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `(argv=…)` | — | [src](../../../scripts/block_unattributed_rebase.py#L9) |

## `scripts/block_unattributed_ref_rewrite.py`
_Block local branch rewrites that can preserve stale actor attribution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_ancestor` | `(old, new)` | — | [src](../../../scripts/block_unattributed_ref_rewrite.py#L14) |
| function | `main` | `(argv=…, *, input_text=…)` | — | [src](../../../scripts/block_unattributed_ref_rewrite.py#L24) |

## `scripts/brain_salience_reset.py`
_One-off: cap runaway salience_bumps in Jarvis' brain (memory repair 2026-09-04, R1)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `reset_salience_bumps` | `(*, cap=…, apply=…)` | Cap ``salience_bumps`` at ``cap`` for every entry above it. | [src](../../../scripts/brain_salience_reset.py#L21) |
| function | `main` | `()` | — | [src](../../../scripts/brain_salience_reset.py#L65) |

## `scripts/cache_break_report.py`
_Hvor braekker praefiks-cachen — og hvilken besked gjorde det?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_faelles_praefiks` | `(a, b)` | — | [src](../../../scripts/cache_break_report.py#L36) |
| function | `_pause_s` | `(foer, efter)` | Sekunder mellem to runders created_at. None hvis en mangler. | [src](../../../scripts/cache_break_report.py#L45) |
| function | `_hent` | `(skaer)` | — | [src](../../../scripts/cache_break_report.py#L60) |
| function | `main` | `()` | — | [src](../../../scripts/cache_break_report.py#L88) |

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
| function | `module_name_from_path` | `(path, repo_root=…)` | Return the dotted module name for a file path relative to repo_root. | [src](../../../scripts/capability_audit.py#L61) |
| function | `find_python_files` | `(root)` | Return sorted .py files under the SCAN_ROOTS subdirs of root, skipping __pycache__. | [src](../../../scripts/capability_audit.py#L75) |
| function | `resolve_relative_import` | `(current_module, module, level)` | Resolve a relative ``from ... import`` into an absolute dotted module name. | [src](../../../scripts/capability_audit.py#L89) |
| function | `normalize_candidates` | `(candidates, known_modules)` | Reduce raw import candidates to modules that actually exist in the repo. | [src](../../../scripts/capability_audit.py#L112) |
| function | `parse_imports` | `(path, *, current_module=…, known_modules=…)` | Parse a file's AST and return the set of modules it imports. | [src](../../../scripts/capability_audit.py#L138) |
| function | `compute_reachability` | `(graph, entry_modules)` | BFS the import graph from entry_modules. | [src](../../../scripts/capability_audit.py#L191) |
| function | `score_service` | `(signals)` | Classify a service into a colored liveness label from its signals. | [src](../../../scripts/capability_audit.py#L217) |
| function | `git_last_touch` | `(path)` | Return (age in days, short commit) of the most recent git change to path. | [src](../../../scripts/capability_audit.py#L248) |
| function | `entry_modules` | `()` | Return the dotted module names of the reachability entry points (ENTRY_FILES + ENTRY_GLOBS). | [src](../../../scripts/capability_audit.py#L286) |
| function | `service_note` | `(signals, score)` | Build a short human note explaining why a service scored low. | [src](../../../scripts/capability_audit.py#L295) |
| function | `render_markdown` | `(signals_list)` | Render the full capability matrix report as a Markdown string. | [src](../../../scripts/capability_audit.py#L313) |
| function | `analyze_services` | `()` | Scan the repo and build ServiceSignals for every module in core/services/. | [src](../../../scripts/capability_audit.py#L412) |
| function | `print_summary` | `(signals_list)` | Print the total service count and per-score counts/shares to stdout. | [src](../../../scripts/capability_audit.py#L473) |
| function | `main` | `()` | Run the audit, write the report to DOCS_OUTPUT, print the summary; return 0. | [src](../../../scripts/capability_audit.py#L485) |

## `scripts/central_connectivity_audit.py`
_central_connectivity_audit.py — HOLDBART kort over hvad der er koblet til Centralen._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parse_route_families` | `()` | Læs FAMILY_ROUTES ∪ PRIVATE_NO_EGRESS_ROUTES's nøgler direkte fra broen (AST). | [src](../../../scripts/central_connectivity_audit.py#L85) |
| function | `_code_only` | `(src)` | Fjern kommentarer + blank string-INDHOLD (behold koden) → signal-scan tæller ikke | [src](../../../scripts/central_connectivity_audit.py#L107) |
| function | `_family_of` | `(event_name)` | — | [src](../../../scripts/central_connectivity_audit.py#L124) |
| function | `_compliant_names` | `()` | Navne på nerver der har SELV-REGISTRERET et kontrakt-compliant manifest (Fase B). | [src](../../../scripts/central_connectivity_audit.py#L131) |
| function | `scan` | `()` | — | [src](../../../scripts/central_connectivity_audit.py#L144) |
| function | `render_md` | `(data)` | — | [src](../../../scripts/central_connectivity_audit.py#L212) |
| function | `main` | `()` | — | [src](../../../scripts/central_connectivity_audit.py#L276) |

## `scripts/cheap_lane_fuld_proeve.py`
_Prøv HVER nøgle og HVER model i cheap lane — ad præcis den vej lanen selv bruger._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `konti_med_noegle` | `(udbyder)` | Konti der HAR en nøgle — også dem balanceren ikke regner for klar. | [src](../../../scripts/cheap_lane_fuld_proeve.py#L40) |
| function | `vej` | `(udbyder, konto)` | — | [src](../../../scripts/cheap_lane_fuld_proeve.py#L70) |
| function | `udgangs_ip` | `(rute, detalje)` | — | [src](../../../scripts/cheap_lane_fuld_proeve.py#L88) |
| function | `modeller_for` | `(udbyder, konto)` | — | [src](../../../scripts/cheap_lane_fuld_proeve.py#L115) |
| function | `liste_modeller` | `(udbyder, konto)` | Udbyderens egen /models, ad samme vej. (None, None, fejl) hvis den ikke svarer. | [src](../../../scripts/cheap_lane_fuld_proeve.py#L128) |
| function | `proev_kald` | `(udbyder, konto, model, timeout)` | — | [src](../../../scripts/cheap_lane_fuld_proeve.py#L174) |
| function | `proev_udbyder` | `(udbyder, timeout)` | — | [src](../../../scripts/cheap_lane_fuld_proeve.py#L198) |
| function | `main` | `()` | — | [src](../../../scripts/cheap_lane_fuld_proeve.py#L216) |

## `scripts/commit_history_report.py`
_Generér en læsbar commit-historie grupperet pr. måned og uge._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_git` | `(*args)` | — | [src](../../../scripts/commit_history_report.py#L47) |
| function | `_commits` | `()` | — | [src](../../../scripts/commit_history_report.py#L52) |
| function | `_week_span` | `(iso_year, iso_week)` | — | [src](../../../scripts/commit_history_report.py#L72) |
| function | `_new_service_files` | `()` | Hver fil der nogensinde blev TILFØJET under core/services/, med fødselsdato. | [src](../../../scripts/commit_history_report.py#L81) |
| function | `_import_counts` | `(paths)` | Hvor mange andre filer nævner modulet? 0 = værd at kigge på først. | [src](../../../scripts/commit_history_report.py#L99) |
| function | `build` | `(out_path)` | — | [src](../../../scripts/commit_history_report.py#L125) |

## `scripts/commit_with_attribution.py`
_CLI for creating a Git commit with canonical actor attribution._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_parser` | `()` | — | [src](../../../scripts/commit_with_attribution.py#L22) |
| function | `_laes_besked` | `(args)` | Beskeden, uanset hvilken vej den kom ind. | [src](../../../scripts/commit_with_attribution.py#L50) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/commit_with_attribution.py#L58) |

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

## `scripts/deferred_restart.py`
_Udskudt genstart — vent til turen er SLUT, genstart saa._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_is_alive` | `(run_id)` | True hvis runnet lever. Kan kilden ikke laeses, svarer vi True (vent). | [src](../../../scripts/deferred_restart.py#L49) |
| function | `wait_for_idle` | `(run_id, *, margin_s=…)` | Vent til runnet er doedt + margin. Returnerer sekunder ventet. | [src](../../../scripts/deferred_restart.py#L67) |
| function | `main` | `(argv)` | — | [src](../../../scripts/deferred_restart.py#L80) |

## `scripts/dispatcher_adoption.py`
_Bliver `call_loaded_tool` faktisk brugt? — tallet der afgør etape B._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rækker` | `(con, kind, siden)` | — | [src](../../../scripts/dispatcher_adoption.py#L50) |
| function | `main` | `()` | — | [src](../../../scripts/dispatcher_adoption.py#L63) |

## `scripts/docs_audit.py`
_SP1 docs auditor — classify docs/*.md against git+runtime truth. Regenerable, static_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find_docs` | `(root=…)` | Return all *.md files under root (recursive, sorted), excluding any under an _archive dir. | [src](../../../scripts/docs_audit.py#L22) |
| function | `extract_references` | `(text)` | Pull code references out of markdown text: repo paths (core/apps/scripts .py/.ts/.tsx/.md/.json) | [src](../../../scripts/docs_audit.py#L27) |
| function | `liveness` | `(refs, repo_root=…)` | Check how many of refs["paths"] still exist on disk under repo_root. | [src](../../../scripts/docs_audit.py#L35) |
| function | `git_last_touch` | `(path, repo_root=…)` | Return (days_since_last_commit, iso_commit_date) for path via `git log -1`. | [src](../../../scripts/docs_audit.py#L45) |
| function | `title_and_headings` | `(text)` | Parse markdown headings from text. Returns (title, headings): title is the first `#` heading | [src](../../../scripts/docs_audit.py#L60) |
| function | `detect_superseded` | `(docs)` | docs: [{path,title,headings,days}]. Older doc is superseded by a NEWER doc that shares the | [src](../../../scripts/docs_audit.py#L75) |
| function | `feature_shipped` | `(refs, repo_root=…)` | A superpowers spec/plan 'shipped' if any referenced path exists, or a key symbol is in the tree. | [src](../../../scripts/docs_audit.py#L93) |
| function | `classify_heuristic` | `(*, path, refs, live, days, superseded_by, is_superpowers, shipped)` | Classify a doc from its signals into a category. Returns (category, confidence, basis): | [src](../../../scripts/docs_audit.py#L108) |
| function | `_yaml_val` | `(v)` | — | [src](../../../scripts/docs_audit.py#L135) |
| function | `stamp_frontmatter` | `(text, fields)` | Idempotent, surgical YAML frontmatter merge: replaces only the given keys, preserves the rest | [src](../../../scripts/docs_audit.py#L140) |
| function | `render_manifest_md` | `(entries)` | Render the audit entries as a DOCS_MANIFEST markdown document: a generated-header line with | [src](../../../scripts/docs_audit.py#L154) |
| function | `build_gap_list` | `(entries)` | Coarse subsystem coverage: which _SUBSYSTEMS have NO færdig doc referencing them. | [src](../../../scripts/docs_audit.py#L166) |
| function | `audit` | `()` | Run the full docs audit: scan every doc, extract refs/headings/git-age, detect supersession, | [src](../../../scripts/docs_audit.py#L178) |
| function | `main` | `()` | CLI entry point: run audit(), write docs/docs_audit_raw.json, print a summary and gap list. | [src](../../../scripts/docs_audit.py#L207) |

## `scripts/docs_drift_check.py`
_SP5 docs-drift checker — catch when docs/ diverges from git+runtime truth._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `find_docs` | `(root=…)` | List all *.md files under `root`, excluding historical-record trees (_SKIP_DOC_PARTS). | [src](../../../scripts/docs_drift_check.py#L31) |
| function | `_norm` | `(text)` | Neutralize volatile 'Generated <date>' stamps so regeneration diffs are content-only. | [src](../../../scripts/docs_drift_check.py#L36) |
| function | `broken_links` | `(docs_root=…)` | HARD check: scan markdown links in every doc and return {doc, kind, target} for each | [src](../../../scripts/docs_drift_check.py#L42) |
| function | `_load_script` | `(name)` | — | [src](../../../scripts/docs_drift_check.py#L60) |
| function | `_expected_api_docs` | `()` | — | [src](../../../scripts/docs_drift_check.py#L67) |
| function | `_expected_api_reference` | `()` | — | [src](../../../scripts/docs_drift_check.py#L77) |
| function | `_expected_capabilities` | `()` | — | [src](../../../scripts/docs_drift_check.py#L83) |
| function | `_staged_under` | `(source_dirs, staged)` | — | [src](../../../scripts/docs_drift_check.py#L96) |
| function | `stale_generated` | `(only_dirs=…, repo=…)` | HARD check: re-run each generator in-memory and compare its expected output to the | [src](../../../scripts/docs_drift_check.py#L100) |
| function | `prose_drift` | `(docs_root=…, repo=…)` | SOFT check: find bare code-path mentions (core/apps/scripts/...) in prose that don't | [src](../../../scripts/docs_drift_check.py#L123) |
| function | `requirements_drift` | `(repo=…)` | SOFT check: scan imported third-party modules (via requirements_gen) and return | [src](../../../scripts/docs_drift_check.py#L140) |
| function | `staged_paths` | `(repo=…)` | Return the list of staged file paths (git diff --cached --name-only); [] on any error. | [src](../../../scripts/docs_drift_check.py#L161) |
| function | `hard_drift` | `(staged=…, repo=…)` | Collect only the gate-blocking (HARD) drift: broken links plus stale generated docs | [src](../../../scripts/docs_drift_check.py#L171) |
| function | `run_check` | `(repo=…, staged=…)` | Run all checks and return a report dict with generated_at, hard/soft drift lists and | [src](../../../scripts/docs_drift_check.py#L178) |
| function | `main` | `()` | CLI entry point. `--check` = gate mode: report hard drift and exit 1 if any, else 0. | [src](../../../scripts/docs_drift_check.py#L192) |

## `scripts/drain_before_restart.py`
_Vent til ingen tur er levende, så en genstart ikke kapper en._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `levende` | `(db=…)` | Er der et levende run lige nu? `None` = kunne ikke afgøres. | [src](../../../scripts/drain_before_restart.py#L48) |
| function | `vent` | `(loft=…, db=…)` | 0 = frit, kan genstarte. 1 = loftet nået mens noget stadig kørte. | [src](../../../scripts/drain_before_restart.py#L75) |

## `scripts/e2e_indbakke.py`
_E2E: holder indbakke-kæden usmocket, i produktionen?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `Led` | `` | Ét led i kæden. Samler sit eget udfald, så ingen kan forsvinde. | [src](../../../scripts/e2e_indbakke.py#L53) |
| method | `Led.__init__` | `(self)` | — | [src](../../../scripts/e2e_indbakke.py#L56) |
| method | `Led.__call__` | `(self, nr, navn, status, detalje=…)` | — | [src](../../../scripts/e2e_indbakke.py#L59) |
| method | `Led.bestod` | `(self)` | — | [src](../../../scripts/e2e_indbakke.py#L64) |
| function | `_trin_1_units` | `(led)` | Kører BEGGE units den kode du tror? | [src](../../../scripts/e2e_indbakke.py#L68) |
| function | `_trin_2_kilde_skriver` | `(led, bruger)` | En ÆGTE kilde skriver en post — gennem `registrer_kilde`, ikke SQL. | [src](../../../scripts/e2e_indbakke.py#L105) |
| function | `_trin_3_visningen` | `(led, bruger, kid)` | Står posten i visningen? Kørt med den rigtige interpreter. | [src](../../../scripts/e2e_indbakke.py#L140) |
| function | `_trin_4_prompten` | `(led, bruger, kid, session_id)` | Det afgørende led: BÆRER PROMPTEN DEN? | [src](../../../scripts/e2e_indbakke.py#L164) |
| function | `_trin_5_gaten` | `(led, bruger)` | Nægter gaten en ægte mutation — og NAVNGIVER den posten? | [src](../../../scripts/e2e_indbakke.py#L200) |
| function | `_trin_6_genstart` | `(led, bruger)` | Overlever tælleren en procesgenstart? | [src](../../../scripts/e2e_indbakke.py#L231) |
| function | `_trin_7_done` | `(led, bruger, kid)` | `inbox_done` lukker den, visningen falder, og posten kan STADIG findes. | [src](../../../scripts/e2e_indbakke.py#L258) |
| function | `_trin_8_intet_i_chatten` | `(led, session_id, foer)` | Er noget sivet ind i chatten som en assistant-besked? | [src](../../../scripts/e2e_indbakke.py#L287) |
| function | `_trin_9_tavse_fejlformer` | `(led, bruger)` | De tre tal huset kender som tavse fejlformer. | [src](../../../scripts/e2e_indbakke.py#L305) |
| function | `_chat_antal` | `(session_id)` | — | [src](../../../scripts/e2e_indbakke.py#L385) |
| function | `_ryd` | `(bruger, kid)` | Luk en testpost. Kaster aldrig — oprydning må ikke vælte rapporten. | [src](../../../scripts/e2e_indbakke.py#L396) |
| function | `main` | `()` | — | [src](../../../scripts/e2e_indbakke.py#L408) |

## `scripts/enforce_commit_hygiene.py`
_Pre-commit hook: catch kitchen-sink commits._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_staged_files` | `()` | — | [src](../../../scripts/enforce_commit_hygiene.py#L53) |
| function | `_classify` | `(path)` | — | [src](../../../scripts/enforce_commit_hygiene.py#L63) |
| function | `_merge_in_progress` | `()` | A merge commit combines commits that already passed this gate one by | [src](../../../scripts/enforce_commit_hygiene.py#L68) |
| function | `main` | `()` | — | [src](../../../scripts/enforce_commit_hygiene.py#L80) |

## `scripts/enforce_test_coverage.py`
_Pre-commit hook: enforces test coverage for core/ code changes._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_is_covered` | `(path)` | Check if a file path falls under a directory we enforce tests for. | [src](../../../scripts/enforce_test_coverage.py#L167) |
| function | `_expected_test_path` | `(staged_path, repo_root=…)` | Given a staged file path like 'core/services/foo.py', | [src](../../../scripts/enforce_test_coverage.py#L172) |
| function | `main` | `(argv=…)` | Entry point.  Accept optional --repo-root to override REPO_ROOT. | [src](../../../scripts/enforce_test_coverage.py#L198) |

## `scripts/eval_research_lane.py`
_Offline deterministic smoke evaluation for research routing and gates._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `evaluate_cases` | `(path=…)` | — | [src](../../../scripts/eval_research_lane.py#L16) |

## `scripts/find_tidsbomber.py`
_Find tests der går i stykker af sig selv når kalenderen skrider._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_koer` | `(spring, pytest_args)` | — | [src](../../../scripts/find_tidsbomber.py#L46) |
| function | `main` | `()` | — | [src](../../../scripts/find_tidsbomber.py#L54) |

## `scripts/forced_tool_choice_report.py`
_Aflæs sonden: honorerer providerne ``tool_choice="required"``?_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_rows` | `()` | — | [src](../../../scripts/forced_tool_choice_report.py#L42) |
| function | `main` | `()` | — | [src](../../../scripts/forced_tool_choice_report.py#L65) |

## `scripts/generate_puls_icons.py`
_Render Jarvis Puls assets. Requires rsvg-convert and Pillow; run from any cwd._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `svg` | `(*, background=…, scale=…, phase=…, attention=…, rounded=…, radius=…)` | — | [src](../../../scripts/generate_puls_icons.py#L29) |
| function | `notifikations_vektor` | `()` | Puls som Android-notifikationsikon — en monokrom silhuet. | [src](../../../scripts/generate_puls_icons.py#L46) |
| function | `render` | `(dest, size, source)` | — | [src](../../../scripts/generate_puls_icons.py#L79) |
| function | `main` | `()` | — | [src](../../../scripts/generate_puls_icons.py#L90) |

## `scripts/goal_report.py`
_Kør goal-reporteren: skriv tick-kvalitet, heed-rate og adherence til målet._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `main` | `(argv)` | — | [src](../../../scripts/goal_report.py#L17) |

## `scripts/god_file_map.py`
_Read-only god-fil-kort: alle egne .py-filer ≥1500 linjer, karakteriseret (linjer, funktioner,_

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `own_py_files` | `()` | — | [src](../../../scripts/god_file_map.py#L14) |
| function | `blast` | `(dotted, target_rel)` | — | [src](../../../scripts/god_file_map.py#L24) |

## `scripts/hollow_verify.py`
_Vagt for hollow-promise-fixet (a19939854, 9/10-2026)._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_fyringer` | `(since)` | — | [src](../../../scripts/hollow_verify.py#L33) |
| function | `_beskeder` | `(run_id, session_id, created_at)` | Beskeden for et run — filtreret på SESSION + tidsvindue. | [src](../../../scripts/hollow_verify.py#L60) |
| function | `_blokke` | `(content_json)` | — | [src](../../../scripts/hollow_verify.py#L111) |
| function | `_maal` | `(blokke)` | Find sidste text og sidste tool_use — og om rækkefølgen er rigtig. | [src](../../../scripts/hollow_verify.py#L126) |
| function | `main` | `()` | — | [src](../../../scripts/hollow_verify.py#L144) |

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

