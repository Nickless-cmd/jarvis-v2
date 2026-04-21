# Daemon Fix — Diagnose 2026-04-21

Opdateret diagnose af den oprindelige TASK_daemon_fix.md (dateret 2026-04-13,
8 dage gammel). Rapporten sagde "17 af 20 daemons er tavse".
**Virkelighed pr. 2026-04-21: kun 7 af 19 er tavse, og de fleste er tavse by design.**

## Metode

Tabellen `daemon_output_log` har været populated siden 2026-04-13 via
`daemon_llm_call` i `core/services/daemon_llm.py`. Den logger success/failure +
rå LLM-output og parsed result for hver tick. Det giver ground truth mod rapportens påstande.

## Status pr. 2026-04-21

### 12 daemons der FUNGERER (claimed silent, actually live)

| Daemon | Success calls | Failed | Last success |
|---|---|---|---|
| `somatic` | 200 | 7 | 2026-04-21 18:17 |
| `thought_stream` | 575 | 3 | 2026-04-21 18:34 |
| `reflection_cycle` | 573 | 3 | 2026-04-21 18:34 |
| `curiosity` | 454 | 4 | 2026-04-21 18:34 |
| `meta_reflection` | 317 | 3 | 2026-04-21 18:17 |
| `aesthetic_taste` | 286 | 2 | 2026-04-21 18:17 |
| `absence` | 104 | 1 | 2026-04-21 18:17 |
| `code_aesthetic` | 89 | 1 | 2026-04-21 18:17 |
| `development_narrative` | 88 | 2 | 2026-04-21 18:17 |
| `existential_wonder` | 22 | 0 | 2026-04-21 15:54 |
| `conflict` | 15 | 0 | 2026-04-19 05:44 (stale) |
| `irony` | 9 | 0 | 2026-04-20 06:04 |

Disse producerer korrekt LLM-output hver tick. Oprindelig "generated: False"-observation
var enten fra før LLM-pipeline var færdig, eller de har siden fået fix-commits.

**Kvalitetsproblemer observeret:**
- **`somatic`**: svarer på **engelsk**, selvom prompten er på dansk. Ikke silent, men prompt bør stramme sprog-kravet.
- **`curiosity`**: output er kort og repetitiv ("Hvorfor?"). Genererer technically, men degenereret.
- **`conflict`**: stale — sidste success 2026-04-19. Trigger-betingelser (inner tensions) rammes ikke, hvilket er ok hvis der ikke er konflikter at detektere.

### 7 daemons der stadig er SILENT (ingen rows i daemon_output_log)

Root causes fundet via kode-inspektion:

| Daemon | Root cause | Handling |
|---|---|---|
| `memory_decay` | **Mekanisk, ikke LLM** — decayer records. `decayed: False` betyder "intet at decaye". By design. | Skip — by-design silent. |
| `autonomous_council` | **Score-gated** — `triggered: False` (score for lav). | Skip — by-design silent. |
| `council_memory` | **Depends on council** — `no_entries` betyder ingen council-sessions endnu. | Skip — afhængig af #2. |
| `dream_insight` | **Chain broken** — venter på `dream_articulation` signals. `dream_articulation.build_dream_articulation_surface()` returnerer `last_state='idle', last_reason='no-run-yet'`. | **FIX — dream_articulation har ingen tick-funktion.** |
| `surprise` | LLM-called, men early-return på `len(_mode_history) < 3` og cooldown. Ikke rigtig silent — bare stram precondition. | Tjek om precondition er fornuftig. |
| `thought_action_proposal` | Kræver `fragment: str` arg. Wired i heartbeat linje 2363 `_tap_result = tick_thought_action_proposal_daemon(_ts_fragment)`. | Verificér at thought_stream's fragment faktisk propageres. |
| `user_model` | Kræver `recent_messages: list[str]`. Wired i heartbeat linje 2487 `tick_user_model_daemon([])` — kaldes med tom liste. | Verificér at intern læsning af `recent_visible_runs` fungerer. |

## Konkrete next steps (prioriteret)

### P1 — dream_insight-kæden
`dream_articulation.py` er 557 linjer men har ingen `tick_*` eller periodisk
trigger. Den er en pure passive service. Hvis vi vil have dream-insights, skal:
1. Enten oprette `tick_dream_articulation_daemon` der processerer pending dream hypotheses
2. Eller koble den på en eksisterende daemon (fx `dream_distillation` der producerer hypotheses)

### P2 — kvalitetsproblemer på fungerende daemons
- `somatic`: sprog-problem. Prompt skal stramme at output SKAL være dansk første-person.
- `curiosity`: degenereret output. Prompt eller model skiftes.

### P3 — wired-men-tavse daemons
- `thought_action_proposal`: verificér at `_ts_fragment` ikke er tom når den kaldes.
- `user_model`: tilføj logging der viser om `recent_visible_runs` faktisk har rows.

### P4 — dokumentation (by-design silent)
Dokumentér i `CURRENT_STATUS.md` at `memory_decay`, `autonomous_council`, `council_memory`
er *by-design* silent og at det ikke er en bug.

## Allerede bygget fra original TASK

- **Improvement 6: Daemon Output Logging** — ✅ **live**. Tabel `daemon_output_log`
  har 2000+ rækker. Ingen grund til at bygge noget.
- **Improvement 4: Web Cache** — ✅ DONE (commits 49d0a4d → 4efaed0, noteret i
  original TASK).
- **Improvement 5: Session Continuity Summaries** — delvist implementeret
  (`session_summary`-daemon har 290 success-calls).

### Stadig åbent

- **Improvement 3: Stale Signal Auto-Cleanup** — status ukendt. Skal verificeres.
- **Improvement 7: Signal Decay Daemon** — separat fra `memory_decay`. Status ukendt.

## Verdict

**Original TASK er 80% færdig uden at nogen har taget fat i den direkte.**
Kodebasen har fået nok commits siden 2026-04-13 til at 12 af de 17 påståede
silent daemons nu er fully working. De 7 resterende er mostly by-design silent
eller har klart diagnosticerede problemer med isolerede fixes.

Ingen grund til at lave "add debug logging to 4 critical daemons" som rapporten
foreslog — logging er allerede på plads i `daemon_llm_call`.
