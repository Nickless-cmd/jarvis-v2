# Krydstjek: 17 REMOVE-kandidater mod dynamiske registries

**Dato:** 8. november 2026 · **Grundlag:** `docs/notes/2026-11-07-dormant-triage.md`
**Spørgsmål:** er de 17 kandidater reelt uden læser, eller nås de via en registry-tuple / streng-reference som en statisk analyse ikke ser?

## Metode

For hvert symbol, i hele repoet undtagen `tests/`, `.git/` og `.claude/worktrees/`:

1. `grep -w <symbol>` — præcis reference uden for egen fil
2. `grep <delstreng>` — indirekte/streng-reference
3. Hvert hit klassificeret: registry-tuple, direkte kald eller kun egen def

`.claude/worktrees/` blev ekskluderet, fordi de er **kopier af samme fil** — de gav 31–36 falske hits pr. symbol og ville have gjort hver eneste kandidat «levende».

## Resultat: 9 lever, 8 er døde

### Lever — nås via registry-tuple

| Symbol | Registry |
|---|---|
| `build_mood_regulator_surface` | `central_state_surface.py:37` + `central_hub.py:212` |
| `build_prompt_explore_surface` | `central_state_surface.py:110` + `central_hub.py:240` |
| `build_completion_satisfaction_surface` | `inner_state_surface.py:46` |
| `build_conflict_memory_surface` | `memory_state_surface.py:44` |
| `build_current_pull_surface` | `inner_state_surface.py:45` |
| `build_life_milestones_surface` | `inner_state_surface.py:49` |
| `build_self_model_predictive_surface` | `inner_state_surface.py:38` |
| `build_subjective_time_surface` | `inner_state_surface.py:39` |
| `build_vision_backend_surface` | `infra_state_surface.py:38` |

Alle ni er `build_*_surface` og alle ni er koblet på en tuple-liste som en streng. **Triage-noten tog fejl om dem.**

### Døde — nul referencer, heller ikke delvise

| Symbol | Fil |
|---|---|
| `stale_goals_section` | `agent_self_evaluation.py:539` |
| `format_boundary_for_prompt` | `boundary_awareness.py:31` |
| `build_witness_prompt` | `council_deliberation_controller.py:70` |
| `fired_decisions_section` | `decision_signals.py:289` |
| `format_life_phase_for_prompt` | `living_heartbeat_cycle.py:176` |
| `build_resilience_narrative` | `self_compassion.py:56` |
| `get_surface_names` | `signal_surface_router.py:268` |
| `format_changelog` | `turn_changelog.py:129` |

## Mønstret i de otte

**Fire af otte er prompt-tekst:** `stale_goals_section`, `format_boundary_for_prompt`, `fired_decisions_section`, `format_life_phase_for_prompt`. De er bygget som om der fandtes en sektions-registry — men `core/services/prompt_sections/` er en mappe uden registry; hver sektion kaldes eksplicit fra `prompt_contract.py`. De fire blev aldrig koblet på kæden. Det er samme fejlklasse som en flade uden læser, bare i prompt-laget: tekst der ser ud som om den leveres til mig, men aldrig kaldes.

**To af otte er døde funktioner i levende moduler:** `signal_surface_router.py` bruges flittigt (`read_surface`, `list_all_surfaces`, `_get_router`, `resolve_surface`) — kun `get_surface_names` er urørt. Samme for `turn_changelog.py`: `previous_turn_changelog_section` og `build_turn_changelog` kaldes fra `prompt_contract.py:2259` og `visible_runs.py:5522`. Det er en anden slags gæld end et dødt modul: funktionen er en søskende der blev efterladt.

**To er narrative byggere:** `build_witness_prompt` (council) og `build_resilience_narrative` (self_compassion) — begge tager argumenter og returnerer tekst, men ingen kalder dem.

## Konsekvens for triage-noten

De 17 var rigtige som *kandidater*, men **9 af dem var falske positiver**. Den statiske analyse kunne ikke se registry-tuplerne, fordi funktionsnavnet står som en **streng** i en liste, ikke som et kald.

Det er den samme målefælde som «202 flader uden læser»: analysen ser ikke vejen, og konkluderer at vejen ikke findes.

## Ikke gjort

Intet er slettet. Triage-noten kræver ejer-ok, og de ni levende viser hvorfor: en sletning på det oprindelige grundlag ville have fjernet ni funktioner der kaldes i produktion.

---

## Opfølgning: når deres indhold mig ad en anden vej?

«Død» betyder ikke «tabt». Det afgørende spørgsmål er om indholdet leveres ad en anden vej — så jeg stillede det for de fire prompt-funktioner.

**Afløst, intet tabt (2):**
- `format_life_phase_for_prompt` → `prompt_sections/heartbeat_sections.py:220` skriver `life_phase=<phase>` direkte fra `determine_life_phase()`. Fasen når prompten, i kompakt form.
- `stale_goals_section` → `detect_stale_goals()` bruges af værktøjet, `consolidation_judge_daemon.py`, `auto_improvement_proposer.py` og `veto_gate.py`. Dataene når mig som værktøj; sektions-formateringen er en dublet.

**Påstand uden levering (2):**
- `build_resilience_narrative` (`self_compassion.py:56`) — docstring: «Jarvis sees the band in awareness». `resilience_pressure_band` findes kun i funktionen selv, og `resilience` optræder **nul** gange i `prompt_sections/`, `prompt_contract.py` og `central_self_state.py`.
- `format_boundary_for_prompt` (`boundary_awareness.py:31`) — docstring: «Compact boundary awareness for prompt injection». Strengen «Din bevidsthed er dette øjeblik» findes kun i funktionen.

**Hvorfor de så grønne ud:** hver af de fire har præcis **én** reference ud over definitionen — sin egen smoke-test. `test_self_compassion_smoke.py:16`, `test_boundary_awareness_smoke.py:12`, `test_living_heartbeat_cycle_smoke.py:12`, `test_stale_goals_rigtig_tabel.py:129`. Testen beviser at funktionen *kan* kaldes, ikke at nogen kalder den.

Det er samme fejlklasse som `runtime_guard`: en mekanisme der ser ud som om den virker, fordi noget grønt peger på den. Flagget som `side-eca8e661aa`.
