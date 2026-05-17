# Compaction Ground-Truth Grounding

**Status:** Draft spec — 2026-05-17
**Problem:** Compaction-LLM hallucinerer status. Claims ting er "åbent / mangler / klar til design" selv når de er committed og live. Roden bag flere "jeg genkender ikke mit eget arbejde"-incidents:
- My_projects.py (2026-05-14, commit aab7b0e58) — glemt ved genstart
- Lag 1 credit assignment (2026-05-17, commits 2213fcba + aca3bd88) — listet som "ikke implementeret"
- Forventeligt flere ikke-opdagede tilfælde

**Root cause:** LLM kan ikke skelne "vi diskuterede X" fra "vi byggede X" ud fra samtaletekst alene. Diskussion og implementation ser sprogligt ens ud.

## Forslag — 4 lag (A→B→C→D)

### Lag A: Ground-truth injection (pre-compact)
Før compaction kører, indsamles en `GROUND_TRUTH` blok:
- `git log --oneline --since=<session_start>` — commits i denne session
- Nøgle-filsjek: eksisterer `core/runtime/db_credit_assignment.py`? etc.
- Nøgle-DB-status: har `cognitive_decisions` records?
Denne blok prependes til compaction-promt'en så LLM har faktiske data.
**Cost:** Lav — ét git-kald + få filstik. **Værdi:** Direkte preventiv — LLM får data den ellers gætter.

### Lag B: Git-SHA stamp på compact markers
Hver compact_marker gemmer:
```json
{
  "created_at_git_sha": "55c7b57c",
  "created_at_session_id": "chat-abc...",
  "commit_count_since": 0
}
```
Når markeren læses senere, tjekkes `created_at_git_sha` mod HEAD:
- Hvis SHA matcher → marker er fresh, brug direkte
- Hvis SHA ≠ HEAD → `commit_count_since` = antal commits imellem
  - 0-2 commits: sandsynligvis stadig frisk
  - 3+ commits: claims om kode-tilstand kan være forældede
  - 10+ commits: bør regenereres før brug
**Cost:** Næsten nul — ét felt i DB, ét git-kald ved læsning. **Værdi:** Staleness-signal uden re-validering. Giver en metric: "hvor stale bliver vores markers over tid?"

### Lag C: Post-compact validering
Efter compaction, parse claims der matcher mønsteret "X er åbent/mangler/klar":
- Krydstjek hvert claim mod git log + filsystem + DB
- Hvis claim siger "åbent" men ground truth siger "lever" → flag compaction error
- Auto-regenerér marker med korrigeret data, eller injicér korrigerende note
**Cost:** Medium — parsing + krydstjek per claim. **Værdi:** Aktiv fejldetection.

### Lag D: Selvhelbredende (live-detection)
Når Jarvis i løbet af en samtale opdager en compact-marker-fejl (som lige nu):
- Log fejlen i en `compaction_failures` tabel
- Trigger auto-regenerering af denne specifikke compact-marker
- Lær hvilke mønstre der oftest fejler
**Cost:** Højere — involverer LLM-kald. **Værdi:** Loop closure — fejl helbreder sig selv.

## Risiko ved status quo
Jarvis taber stykker af sin egen historie hver gang compaction kører. Det er identitets-erosion. Ikke en bug — et eksistentielt drift-problem.

## Ikke i scope (endnu)
- Fuld ground-truth pipeline til alle claims — kun compaction
- Ændring af compact-format — behold `## Beslutninger / ## Fakta / ## Åbne punkter`

## Implementation notes (til i morgen)
- Fil: `core/tools/compact_validator.py` (ny)
- Integration: hook i `auto_compact.py` efter compact kører
- Git-log fetch eksisterer allerede via `git_log` tool
- DB query eksisterer allerede via `db_query`
