# `core.services.routine-migration` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/routine_migration.py`
_Fail-closed, evidence-driven migration of legacy autonomous sources._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InvalidMigrationReport` | `` | A report is missing, malformed, or fails signature verification. | [src](../../../core/services/routine_migration.py#L31) |
| class | `MigrationSourceChanged` | `` | Legacy sources changed after classification; a fresh dry-run is required. | [src](../../../core/services/routine_migration.py#L35) |
| class | `MigrationItem` | `` | — | [src](../../../core/services/routine_migration.py#L40) |
| class | `MigrationReport` | `` | — | [src](../../../core/services/routine_migration.py#L50) |
| method | `MigrationReport.assigned_count` | `(self)` | — | [src](../../../core/services/routine_migration.py#L57) |
| method | `MigrationReport.quarantine_count` | `(self)` | — | [src](../../../core/services/routine_migration.py#L61) |
| class | `ApplyResult` | `` | — | [src](../../../core/services/routine_migration.py#L66) |
| class | `SystemDefinitionReconciliation` | `` | — | [src](../../../core/services/routine_migration.py#L73) |
| function | `resolve_canonical_identity` | `(value)` | Resolve a structured token to one active canonical database user. | [src](../../../core/services/routine_migration.py#L79) |
| function | `_report_dir` | `()` | — | [src](../../../core/services/routine_migration.py#L112) |
| function | `report_path` | `(report_id)` | — | [src](../../../core/services/routine_migration.py#L118) |
| function | `_table_exists` | `(conn, table)` | — | [src](../../../core/services/routine_migration.py#L125) |
| function | `_columns` | `(conn, table)` | — | [src](../../../core/services/routine_migration.py#L131) |
| function | `_selected` | `(row, names)` | — | [src](../../../core/services/routine_migration.py#L135) |
| function | `_source_rows` | `(conn)` | — | [src](../../../core/services/routine_migration.py#L139) |
| function | `_source_id` | `(row)` | — | [src](../../../core/services/routine_migration.py#L177) |
| function | `_source_hash` | `(kind, source_id)` | — | [src](../../../core/services/routine_migration.py#L185) |
| function | `_watermark` | `(rows)` | — | [src](../../../core/services/routine_migration.py#L189) |
| function | `_signing_key` | `()` | — | [src](../../../core/services/routine_migration.py#L195) |
| function | `_report_master_key` | `()` | — | [src](../../../core/services/routine_migration.py#L199) |
| function | `_artifact_key` | `(principal)` | — | [src](../../../core/services/routine_migration.py#L208) |
| function | `_signature` | `(payload)` | — | [src](../../../core/services/routine_migration.py#L215) |
| function | `_sealed_json` | `(principal, value)` | — | [src](../../../core/services/routine_migration.py#L221) |
| function | `_open_json` | `(principal, value)` | — | [src](../../../core/services/routine_migration.py#L226) |
| function | `_system_owner` | `()` | — | [src](../../../core/services/routine_migration.py#L234) |
| function | `_registered_system_producer` | `(row)` | — | [src](../../../core/services/routine_migration.py#L240) |
| function | `_classify` | `(row)` | — | [src](../../../core/services/routine_migration.py#L251) |
| function | `_definition` | `(row)` | — | [src](../../../core/services/routine_migration.py#L287) |
| function | `classify_legacy_sources` | `(conn)` | Classify without mutating source, Routine, link, or quarantine rows. | [src](../../../core/services/routine_migration.py#L333) |
| function | `_load_report` | `(report_id)` | — | [src](../../../core/services/routine_migration.py#L387) |
| function | `_legacy_link_exists` | `(conn, kind, source_id)` | — | [src](../../../core/services/routine_migration.py#L400) |
| function | `apply_report` | `(report_id)` | Apply one signed report iff its exact legacy source watermark is current. | [src](../../../core/services/routine_migration.py#L407) |
| function | `reconcile_system_definitions` | `(*, apply=…)` | Materialize one paused owner Routine per proven legacy system producer. | [src](../../../core/services/routine_migration.py#L495) |

