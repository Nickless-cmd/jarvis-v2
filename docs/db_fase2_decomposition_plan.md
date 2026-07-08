---
status: færdig
audited: 2026-07-08
ground_truth: 1/1 refs alive, 0d old
---
# db.py Fase-2 dekomponerings-plan — den tanglede kerne

**Genereret 2026-07-07 efter Fase-1 (db.py 33494→28985, 15 nye db_*-moduler, alle grønne).**
Fase 1 tog de 0-grænse-koblede skuffer. Dette er "det egentlige projekt": den tanglede kerne.

## Diagnosen (opdateret mod live db.py = 28985 linjer)

- **568 module-level funktioner · ~26.000 linjer · 125 tabeller** — resten af db.py udover init_db.
- **KRITISK fund:** kun **7 tabeller** har rene `_ensure_*_tables/columns`-ankre (security_guard,
  teams, tool_router, notification, multiuser-kolonner, soft-delete, tool-intent-approval).
  De **øvrige ~118 CREATE TABLE ligger INLINE i `init_db`** (1056-linjers funktion).
  → Plan-doc'ens oprindelige "split efter `_ensure_*`-feature-cluster" dækker kun en håndfuld.
  **Fase 2 må klynge efter SEMANTISK NAVNE-PRÆFIKS**, ikke efter schema-ankre.
- **53 `upsert_runtime_*_signal`-familier** er næsten-identiske (record/get/list/supersede pr.
  tabel, ~6 funcs/~381 linjer hver). Det er kedelpladen §65-noten pegede på — men **split FØRST**,
  DRY bagefter (Fase 2b).

## Metode (uændret, bevist 5× i Fase 1)

Pr. domæne: flyt tabellens INLINE `CREATE TABLE` fra `init_db` → `ensure_<domæne>_tables(conn)` i
nyt `db_<domæne>.py`; `init_db` kalder ensure-funktionen; flyt CRUD + single-use row-mappers; re-
eksportér fra bunden af db.py (`# noqa: E402,F401`) så ingen af ~767 importører brækker. Fuld-suite-
gate pr. batch. Row-mappers (`_runtime_*_from_row`) co-lokaliseres med deres domæne.

**Ekstra Fase-2-nuance:** init_db-inline-CREATE betyder hver batch redigerer den store init_db-krop.
Bevar RÆKKEFØLGEN af ensure-kald (nogle tabeller har FK/ALTER-afhængigheder på tidligere CREATEs).

## Foreslåede feature-domæner (~13 moduler + 5 små anker-moduler)

### Store semantiske klynger
| Modul | Indhold | ~funcs | ~linjer |
|-------|---------|--------|---------|
| `db_runtime_self.py` | runtime_self_* (self_model_signal, self_narrative_continuity, selfhood_proposal, self_authored_prompt) | ~28 | ~1900 |
| `db_runtime_self_review.py` | self_review_signal/record/run/outcome/cadence (sub-familie, 5 tabeller) | ~20 | ~1150 |
| `db_runtime_private.py` | private_initiative_tension, inner_interplay, inner_note, state_snapshot, temporal_curiosity, temporal_promotion | ~36 | ~2300 |
| `db_runtime_dream.py` | dream_adoption_candidate, dream_hypothesis_signal, dream_influence_proposal | ~18 | ~1170 |
| `db_runtime_chronicle.py` | chronicle_consolidation_brief/proposal/signal, consolidation_target | ~18 | ~1155 |

### Signal-klynger (de 53 near-identiske familier, grupperet tematisk)
| Modul | Signal-familier | ~funcs |
|-------|-----------------|--------|
| `db_runtime_cognition_signals.py` | reflection, reflective_critic, internal_opposition, meaning_significance, witness, awareness, executive_contradiction, metabolism_state | ~30 |
| `db_runtime_relational_signals.py` | relation_continuity, relation_state, attachment_topology, loyalty_gradient, user_understanding, user_md_update, inner_visible_support | ~28 |
| `db_runtime_temporal_memory_signals.py` | temporal_recurrence, remembered_fact, memory_md_update, release_marker, selective_forgetting, regulation_homeostasis, temperament_tendency | ~28 |
| `db_runtime_executive_signals.py` | goal, world_model, development_focus, autonomy_pressure, open_loop, open_loop_closure, contract_candidate, proactive_loop_lifecycle, proactive_question_gate | ~36 |

### Små anker-moduler (de 7 rene `_ensure_*` — laveste risiko, kan tages først som Fase-2 opvarmning)
`db_security_guard.py` (abuse_events, user_flags, audit_log) · `db_teams.py` (teams, team_members) ·
`db_tool_router.py` (tool_router_decisions, load_more) · `db_notifications.py` (notification_preferences) ·
`db_multiuser.py` (multiuser-kolonner + soft_deleted_at + tool_intent_approval — kolonne-migrations).

### Rest
`db_runtime_misc.py` — hvad der bliver tilbage (dele-helpers, tabeller uden klar familie). Mål:
db.py = tynd re-eksport-hub + init_db, <3000 linjer til sidst.

## Rækkefølge

1. **Opvarmning:** de 5 små anker-moduler (rene `_ensure_*`, ~0 risiko, bygger init_db-surgery-rutine).
2. **Store klynger:** self_review → dream → chronicle → private → self (størst/mest sammenhængende).
3. **Signal-klynger:** de 4 signal-moduler (kedelplade, meget regulær — kan agent-batches à 2 familier).
4. **Rest → misc**, derefter re-kør `scripts/db_decomposition_map.py` til db.py er ~re-eksport-hub.

## Fase 2b — kedelplade-DRY (EFTER split, separat runde)

De 53 `upsert_*`-familier deler form. Efter split: indfør én delt
`_upsert_signal(table, key_cols, value_cols, row)`-helper i `db_core` som de tynde wrappere kalder.
IKKE én funktion-der-gør-mange-ting (bryder én-ansvarlighed) — men fælles kerne + tynde navngivne
wrappere pr. tabel. Reducerer måske yderligere ~8-10k linjer. Gør KUN efter skufferne står.

## Risiko & værn

- Højere blast-radius end Fase 1 (init_db-surgery pr. batch). Bevar ensure-kald-rækkefølge.
- Fuld-suite-gate pr. batch (kendt: ~19 min; 1 rotende DB-state pollution-flake består alene).
- Samme re-eksport-invariant: ingen af ~767 importører må brække; verificér `import core.runtime.db`
  + `apps.api.jarvis_api.app` + fresh-DB-init-smoke pr. batch.
- Estimat: ~13-18 batches → egen fase, ikke én session. Anbefaling: Bjørn styrer tempo som med Fase 1.

## Data-kilder
`scripts/db_decomposition_map.py` (re-kør pr. snit) · denne fils klynge-analyse (AST +
navne-præfiks + `upsert_runtime_*`-familie-enumeration, 2026-07-07).
