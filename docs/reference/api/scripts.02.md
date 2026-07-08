# `scripts.02` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

