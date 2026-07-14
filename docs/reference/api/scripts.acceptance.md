# `scripts.acceptance` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/acceptance/__init__.py`
_Fase 6 Task 8 — the jarvis-code migration-trigger gate._

_(no top-level classes or functions)_

## `scripts/acceptance/migration_gate.py`
_Fase 6 Task 8 — the jarvis-code migration-trigger gate._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_run_pytest` | `(cwd, args, label)` | — | [src](../../../scripts/acceptance/migration_gate.py#L32) |
| function | `_run_script` | `(cwd, args, label)` | — | [src](../../../scripts/acceptance/migration_gate.py#L47) |
| function | `_compute_numeric_bar` | `()` | Runs the SAME N=100 fuzz aggregation the committed pytest regression | [src](../../../scripts/acceptance/migration_gate.py#L83) |
| function | `run_suites` | `()` | — | [src](../../../scripts/acceptance/migration_gate.py#L99) |
| function | `evaluate` | `(results)` | Pure function: results dict -> verdict dict. No subprocess/IO here — | [src](../../../scripts/acceptance/migration_gate.py#L123) |
| function | `_self_test` | `()` | Stubbed suite-runner asserting the verdict logic itself, without | [src](../../../scripts/acceptance/migration_gate.py#L161) |
| function | `main` | `()` | — | [src](../../../scripts/acceptance/migration_gate.py#L203) |

