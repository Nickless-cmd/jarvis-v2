# db.py dekomponerings-plan (snit-liste)

**Genereret read-only af `scripts/db_decomposition_map.py` (6. jul). Re-kør efter hvert snit.**

## Diagnosen

`core/runtime/db.py` = **33.494 linjer · 672 CRUD-funktioner · 157 tabeller · 2 schema-init-funktioner.**
Det er ikke én ting — det er 157 tabellers get/list/upsert/update (98 `get_`, 95 `list_`, 71 `upsert_`,
68 `update_`, 54 `supersede_`) proppet i én fil. En rodeskuffe. Kuren er skuffer med labels
(`db_<domæne>.py` + re-eksport fra db.py), **ikke** én kæmpe-funktion.

Metoden er allerede bevist i repoet: `db_core.py`, `db_gate_verdicts.py`, `db_central_incidents.py`,
`db_api_connections.py` er udskilt sådan. Re-eksport betyder ingen af de 767 refererende filer brækker.

## Struktur (funktions-koblede komponenter)

- **32 SMÅ TRYGGE domæner** — 0 grænse-kobling, ≤8 tabeller hver. Tilsammen **~3.535 linjer, 91
  funktioner, NUL risiko.** Dette er Fase 1.
- **1 TANGLET KERNE** — 122 tabeller, 504 funktioner, **~25.315 linjer (75% af db.py).** Dette er
  det egentlige projekt (Fase 2).

## FASE 1 — de trygge snit (start her, baseline FØR hvert)

Rækkefølge (størst gevinst først, alle 0-risiko):

| # | Ny fil | tabeller | func | ~linjer |
|---|--------|----------|------|---------|
| 1 | `db_heartbeat.py` | heartbeat_runtime_state | 3 | 364 |
| 2 | `db_private.py` | private_growth_notes, private_inner_notes, protected_inner_voices | 12 | 348 |
| 3 | `db_visible.py` | visible_runs, visible_work_notes | 4 | 239 |
| 4 | (+ heartbeat_runtime_ticks) | | 4 | 236 |
| 5 | `db_runtime_tasks.py` | runtime_tasks | 4 | 194 |
| 6 | `db_runtime_flows.py` | runtime_flows | 4 | 160 |
| 7 | `db_agent_registry.py` | agent_registry | 4 | 150 |
| 8 | `db_runtime_browser.py` | runtime_browser_bodies | 3 | 144 |

…+ 24 flere ≤8-tabel-domæner. Batch 3-5 pr. session.

**Snit-procedure (pr. domæne):**
1. `conda activate ai && python -m pytest tests/ -q` → **gem baseline-tal FØR** (gardener-læren:
   uden baseline kan man ikke tolke fuld-suite-tal).
2. `central_surgery.snapshot_file("core/runtime/db.py")` → atomisk rollback-net.
3. Flyt domænets `CREATE TABLE` + dets CRUD-funktioner til `db_<domæne>.py`.
4. I db.py: `from core.runtime.db_<domæne> import *` (re-eksport → imports brækker ikke).
5. Compile + import + pytest → **sammenlign med baseline** (samme tal = grønt).
6. Commit. Re-kør `scripts/db_decomposition_map.py` (db.py-linjer skal falde).

## FASE 2 — den tanglede kerne (122 tabeller)

**Hvorfor tanglet?** IKKE god-funktioner — de tungeste 'entanglers' rører kun 4-7 tabeller og er
små `_ensure_*_tables`-schema-hjælpere (multiuser/security_guard/teams). Kernen er kædet sammen af
et VÆV af 2-3-tabel-funktioner + disse feature-schema-hjælpere.

**Strategi:** split efter FEATURE-KLYNGE — hver `_ensure_<feature>_tables` + dens tabellers CRUD =
ét naturligt domæne (`db_multiuser.py`, `db_security_guard.py`, `db_teams.py`, …). Accepter et par
kryds-imports mellem de nye moduler (uundgåeligt i et væv). Kræver Fase 2-analyse: kortlæg hver
`_ensure_*`'s tabel-sæt → ~15-20 feature-domæner.

## Succes-mål
- db.py linjer ↓ pr. snit (re-kør map-scriptet).
- `jc excess` pres ↓ over tid.
- Fuld-suite = baseline (ingen regression).
- Slut-tilstand: db.py = tynd re-eksport-hub + ~40-50 fokuserede `db_*.py` under 1500 linjer hver.

## "Smart funktion der kan flere ting" (Bjørns idé) — note
De 71 `upsert_X` er per-tabel-varianter af SAMME form. DRY-gevinsten = én delt `_upsert(table,
keys, values)`-hjælper som de tynde wrappere kalder — IKKE én funktion der gør mange ting (anti-
mønster: bryder én-ansvarlighed, svær at teste). Men **split først**; kedelplade-DRY er en senere,
mindre runde oven på skufferne.
