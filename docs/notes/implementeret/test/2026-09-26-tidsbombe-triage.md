# Tidsbombe-triagen: 14 faste datoer, 14 gange «fin»

Status: implementeret

**Dato:** 2026-09-26
**Grundlag:** læsning af de 14 testfiler fra triage-listen + de moduler de kalder

## Problem

`2299cb4ec` (20/9-2026) rettede en test der skiftede fra grøn til rød **midt på
dagen**: `tests/test_world_model_signal_tracking.py` brugte fixturen
`"2026-09-10T10:00:00+00:00"`, og `refresh_runtime_world_model_signal_statuses`
markerer et signal «stale» efter `_STALE_AFTER_DAYS` (10). Klokken 10:00 UTC
faldt fixturen ud af vinduet.

Det efterlod et spørgsmål: hvor mange andre faste datoer er bomber der bare
ikke er sprunget endnu? Listen havde 16 kandidater; to var triageret i
forvejen, 14 stod tilbage.

**Målt 26/9-2026:** 337 af 1.756 testfiler indeholder en fast fortidig dato,
248 af dem ældre end 30 dage. En vagt der flagger dem alle ville være ren støj.

## Beslutning

Alle 14 er **fine**. Ingen rettelser foretaget.

Kriteriet, arvet fra de to første triager og bekræftet af alle 14:

> En fast dato er kun en bombe hvis produktionskoden læser det RIGTIGE ur OG
> testen asserter at fixturen ligger **inden for** et vindue.

Tre ting gør en dato inert, og mindst én af dem gælder hver gang:

1. **Testen injicerer sit eget «nu»** — enten som parameter eller ved at
   monkeypatche den funktion der ville have set på uret.
2. **Datoen er visningstekst eller sorteringsnøgle** — typisk `str(...)[:10]`.
3. **Assertionen peger den sikre vej.** En fixtur der skal være *forældet*
   bliver kun mere forældet af at ældes. Kun «denne er frisk nok» kan knække.

Dommene:

| Fil | Dom |
|---|---|
| `test_state_file_retention.py` | Datoen er en modul-konstant `NOW` som `parse_ts` sammenlignes MOD. Parser-test. |
| `test_signal_tracking_framework.py` | `parse_dt("...") is not None`. Ren parser. |
| `test_docs_drift_watchdog.py` | Skriver `generated_at` og asserter `startswith`. Rundtur af en værdi. |
| `test_memory_recall_engine.py` | Injicerer tid; modulet har nul alders-vinduer. |
| `test_turn_side_text_gc_surfaces.py` | `started_at` → `build_turn_changelog`; assertion er antal og filnavne. |
| `test_creative_journal_phase1.py` | `created_at` → `_format_yaml_frontmatter`. Ren formatering. |
| `test_current_pull_staleness.py` | `created_at` er tilstands-metadata; `expires_at` og `last_staleness_checked_at` er RELATIVE. Modulets eneste vindue gælder chronicle-entries, ikke denne dict. |
| `test_meta_learning.py` | Injicerer tid; modulet har nul alders-vinduer. |
| `test_emotional_memory_engine.py` | **Var aldrig på listen med rette** — filen har ingen faste datoer, kun `now - timedelta(days=N)`. |
| `test_sensory_perception_bridge.py` | `perceptual_event_engine` filtrerer på `last_seen_event_id`, ikke på alder. |
| `test_cross_agent_memory.py` | Testen patcher `cross_agent_recall` væk, så 30-dages-cutoffet nås aldrig; datoen bruges som `[:10]`. |
| `test_agent_self_evaluation.py` | `days_stale` gives EKSPLICIT ved siden af `last_update`; datoen bruges som `[:10]`. |
| `test_signal_and_idea_daemons.py` | Den ene fixtur SKAL være stale (ældning er den sikre vej); den anden monkeypatcher `_hours_since` til 3.0. |
| `test_session_summaries.py` | `session_summary_recent` er patchet; DELETE-cutoffet ligger i en anden funktion. |

## Overvejede alternativer

**En vagt der flagger faste datoer i tests.** Fravalgt: 337 filer har en, 248
ældre end 30 dage — og triagen viste at næsten alle er inerte. En vagt med 248
falske positiver bliver slået fra, og så beskytter den intet.

**Et fremskudt ur i CI.** Fravalgt for nu: hverken `freezegun`, `time-machine`
eller `faketime` er installeret i `ai`-miljøet, og en ny pakke skal aftales
først. Det ville være den eneste måde at FINDE bomberne frem for at læse sig
til dem — og hvis listen nogensinde bliver lang igen, er det svaret.

**At rette de 14 «for en sikkerheds skyld».** Fravalgt: en ændring uden en
målt grund er en ændring man ikke kan forsvare bagefter. Og at udlede datoer
af vindues-konstanter, hvor der ikke ER et vindue, gør testen sværere at læse
uden at gøre den mere sand.

## Konsekvenser

Listen er lukket. Skulle en ny bombe springe, er kriteriet ovenfor det der
skal bruges — og det står her, så den næste ikke skal genopfinde det.

Én ting at være opmærksom på: kriteriet kræver at man kender BEGGE sider —
testens fixtur og produktionens vindue. Jeg tog fejl to gange undervejs ved kun
at læse den ene (jeg gættede på `_RS_CACHE` og på en bus-reference i en
beslægtet fejljagt samme nat, begge forkert). Den måling der afgør sagen er
altid: *hvilken kode sammenligner denne dato med hvad?*
