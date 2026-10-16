# `scripts.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

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

## `scripts/verify_vaert_evner.py`
_Vagt: de evner den SERVERENDE vært skal have, skal faktisk være der._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_mermaid` | `()` | — | [src](../../../scripts/verify_vaert_evner.py#L59) |
| function | `tjek` | `()` | Kør alle evne-tjek. Returnér (navn, ok, grund, konsekvens) for hver. | [src](../../../scripts/verify_vaert_evner.py#L72) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_vaert_evner.py#L88) |

## `scripts/verify_vagt_graenser.py`
_Vagt: vagt-laget må NÆVNE et delsystem, aldrig importere det._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_importerede_moduler` | `(traeet)` | — | [src](../../../scripts/verify_vagt_graenser.py#L44) |
| function | `brud` | `()` | — | [src](../../../scripts/verify_vagt_graenser.py#L55) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_vagt_graenser.py#L74) |

