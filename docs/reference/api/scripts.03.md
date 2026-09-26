# `scripts.03` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `scripts/verify_vagt_graenser.py`
_Vagt: vagt-laget må NÆVNE et delsystem, aldrig importere det._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_importerede_moduler` | `(traeet)` | — | [src](../../../scripts/verify_vagt_graenser.py#L44) |
| function | `brud` | `()` | — | [src](../../../scripts/verify_vagt_graenser.py#L55) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_vagt_graenser.py#L74) |

