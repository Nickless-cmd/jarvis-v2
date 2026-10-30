# `scripts.04` — reference

> Generated from source (AST). Regenerate: `python scripts/api_docs_gen.py`. DO NOT hand-edit.

## `scripts/verify_memory_status.py`
_Skraldespærre mod statuspåstande i MEMORY.md der ikke kan efterprøves._

| Kind | Name | Signature | Summary | Source |
|---|---|---|---|---|
| function | `_qf_loft` | `()` | Promptens FAKTISKE klip-loft for QUICK_FACTS — læst fra kilden. | [src](../../../scripts/verify_memory_status.py#L150) |
| function | `quick_facts_brud` | `(sti)` | QUICK_FACTS.md skal være et OPSLAG — ikke en hukommelsesbank. | [src](../../../scripts/verify_memory_status.py#L187) |
| function | `_filer` | `()` | De vogtede filer — stien løses ved KALDSTID, ikke ved import. | [src](../../../scripts/verify_memory_status.py#L226) |
| function | `fund_i_fil` | `(sti)` | (linjenummer, tekst) for hver `## `-overskrift der er en påstand uden spor. | [src](../../../scripts/verify_memory_status.py#L249) |
| function | `fund_i_broedtekst` | `(sti)` | (linjenummer, tekst) for hver brødtekst-linje der er en påstand uden spor. | [src](../../../scripts/verify_memory_status.py#L261) |
| function | `_navn` | `(sti)` | Kort, entydigt navn til grundlinjen: <workspace>/<fil>. | [src](../../../scripts/verify_memory_status.py#L287) |
| function | `main` | `(argv=…)` | — | [src](../../../scripts/verify_memory_status.py#L292) |

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

