# `core.costing` — reference

> Generated 2026-07-08 from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `core/costing/__init__.py`

_(no top-level classes or functions)_

## `core/costing/ledger.py`

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `record_cost` | `(*, lane, provider, model, input_tokens=…, output_tokens=…, cost_usd=…, cache_hit_tokens=…, cache_miss_tokens=…)` | Insert a row into the costs ledger. | [src](../../../core/costing/ledger.py#L9) |
| function | `telemetry_summary` | `()` | — | [src](../../../core/costing/ledger.py#L64) |
| function | `recent_costs` | `(limit=…)` | — | [src](../../../core/costing/ledger.py#L84) |
| function | `daily_cost_summary` | `()` | Cost per day for the last 30 days, broken down by lane. | [src](../../../core/costing/ledger.py#L113) |
| function | `weekly_cost_summary` | `()` | Cost per ISO week for all time. | [src](../../../core/costing/ledger.py#L142) |
| function | `today_cost` | `()` | Total cost in USD for today (UTC). | [src](../../../core/costing/ledger.py#L170) |
| function | `this_week_cost` | `()` | Total cost in USD for this ISO week. | [src](../../../core/costing/ledger.py#L183) |
| function | `estimate_savings_if_cheap` | `(*, days=…)` | Estimate how much would be saved by routing primary-lane calls to cheap lane. | [src](../../../core/costing/ledger.py#L196) |

