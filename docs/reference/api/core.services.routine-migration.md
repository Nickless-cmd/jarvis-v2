# `core.services.routine-migration` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/services/routine_migration.py`
_Fail-closed, evidence-driven migration of legacy autonomous sources._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| class | `InvalidMigrationReport` | `` | A report is missing, malformed, or fails signature verification. | [src](../../../core/services/routine_migration.py#L25) |
| class | `MigrationSourceChanged` | `` | Legacy sources changed after classification; a fresh dry-run is required. | [src](../../../core/services/routine_migration.py#L29) |
| class | `MigrationItem` | `` | — | [src](../../../core/services/routine_migration.py#L34) |
| class | `MigrationReport` | `` | — | [src](../../../core/services/routine_migration.py#L44) |
| method | `MigrationReport.assigned_count` | `(self)` | — | [src](../../../core/services/routine_migration.py#L51) |
| method | `MigrationReport.quarantine_count` | `(self)` | — | [src](../../../core/services/routine_migration.py#L55) |
| class | `ApplyResult` | `` | — | [src](../../../core/services/routine_migration.py#L60) |
| function | `resolve_canonical_identity` | `(value)` | Resolve a structured token to one active canonical database user. | [src](../../../core/services/routine_migration.py#L66) |
| function | `_report_dir` | `()` | — | [src](../../../core/services/routine_migration.py#L99) |
| function | `report_path` | `(report_id)` | — | [src](../../../core/services/routine_migration.py#L105) |
| function | `_table_exists` | `(conn, table)` | — | [src](../../../core/services/routine_migration.py#L112) |
| function | `_columns` | `(conn, table)` | — | [src](../../../core/services/routine_migration.py#L118) |
| function | `_selected` | `(row, names)` | — | [src](../../../core/services/routine_migration.py#L122) |
| function | `_source_rows` | `(conn)` | — | [src](../../../core/services/routine_migration.py#L126) |
| function | `_source_id` | `(row)` | — | [src](../../../core/services/routine_migration.py#L164) |
| function | `_source_hash` | `(kind, source_id)` | — | [src](../../../core/services/routine_migration.py#L172) |
| function | `_watermark` | `(rows)` | — | [src](../../../core/services/routine_migration.py#L176) |
| function | `_signing_key` | `()` | — | [src](../../../core/services/routine_migration.py#L182) |
| function | `_report_master_key` | `()` | — | [src](../../../core/services/routine_migration.py#L186) |
| function | `_artifact_key` | `(principal)` | — | [src](../../../core/services/routine_migration.py#L195) |
| function | `_signature` | `(payload)` | — | [src](../../../core/services/routine_migration.py#L202) |
| function | `_sealed_json` | `(principal, value)` | — | [src](../../../core/services/routine_migration.py#L208) |
| function | `_open_json` | `(principal, value)` | — | [src](../../../core/services/routine_migration.py#L213) |
| function | `_system_owner` | `()` | — | [src](../../../core/services/routine_migration.py#L221) |
| function | `_classify` | `(row)` | — | [src](../../../core/services/routine_migration.py#L227) |
| function | `_definition` | `(row)` | — | [src](../../../core/services/routine_migration.py#L258) |
| function | `classify_legacy_sources` | `(conn)` | Classify without mutating source, Routine, link, or quarantine rows. | [src](../../../core/services/routine_migration.py#L281) |
| function | `_load_report` | `(report_id)` | — | [src](../../../core/services/routine_migration.py#L335) |
| function | `_legacy_link_exists` | `(conn, kind, source_id)` | — | [src](../../../core/services/routine_migration.py#L348) |
| function | `apply_report` | `(report_id)` | Apply one signed report iff its exact legacy source watermark is current. | [src](../../../core/services/routine_migration.py#L355) |

