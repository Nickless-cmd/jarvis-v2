# Plan A (kerne) — Session-persistence: crash-zombier genoptages

**Dato:** 2026-07-09
**Spec:** `docs/superpowers/specs/2026-07-09-session-persistence-design.md` (§6 Plan A)
**Scope:** §5.1 (udvid `in_flight_runs`) + §5.2 (boot-reconciler) + §5.5 (nerve + kill-switch).
**IKKE i scope (Plan B, separat opfølgning):** §5.3 autonom tracking, §5.4 aktiv-session-pointer.

## Problem (det ene hul Plan A lukker)
Ved hård container-crash kører run'ets `finally` (mark_interrupted/mark_completed) ALDRIG →
record'en står `status='running'` = zombie. `interrupted_for_session` returnerer kun
`interrupted`-records, så zombien surfacer ALDRIG i prompt'en — og næste `mark_started`
dropper den (in_flight_runs.py:76-78). Crash-afbrudt arbejde forsvinder tavst.

Fix: en boot-reconciler flipper forældede `running` → `interrupted`, så den EKSISTERENDE
`interruption_prompt_section` genoptager sessionen næste tur.

## Principper
- Byg på `in_flight_runs` (ingen ny tabel, ingen dobbelt-sandhed).
- Shadow-først: kill-switch `session_persistence` default OFF. OFF = observe-only (skriv intet).
- Fail-open: en reconciler-fejl må ALDRIG crashe opstart. Alt i try/except.
- Idempotent: kun `running → interrupted`; anden kørsel (api+runtime deler entrypoint) finder intet nyt.

## Opgaver (TDD, commit pr. enhed)

### 1. Plan-doc (denne fil). Commit.

### 2. Udvid `core/services/in_flight_runs.py` (bagudkompatibelt)
- `mark_started` får valgfri keyword-args `kind="visible"`, `provider=""`, `model=""` → gemt i record.
  Alle eksisterende callere upåvirket (keyword-only, defaulted).
- Ny `list_running_orphans(stale_after_s: float) -> list[dict]`: records med `status=='running'`
  OG `started_at` ældre end `stale_after_s`. Ren læsning (ingen skrivning).
- Tests: nye felter persisteres; `list_running_orphans` returnerer kun forældede `running`
  (ikke `interrupted`, ikke friske `running`).

### 3. Kill-switch `core/services/session_persistence_flag.py`
- Spejler `structured_content_flag.py`, men **default OFF** (usat → False; kun eksplicit
  on/1/true/yes → True). Læse-fejl → False (shadow er sikker default).
- `session_persistence_enabled() -> bool`.

### 4. Boot-reconciler `core/services/session_boot_reconciler.py`
- Konstant `STALE_AFTER_SECONDS = 600` (> `_MIN_AGE_TO_SURFACE_SECONDS`=90 og > længste realistiske run).
- `reconcile_on_boot(stale_after_s=STALE_AFTER_SECONDS) -> dict`:
  1. `orphans = in_flight_runs.list_running_orphans(stale_after_s)`.
  2. Kill-switch ON → for hver orphan: `in_flight_runs.mark_interrupted(run_id, reason="afbrudt af container-genstart")`.
     Kill-switch OFF → observe-only (tæl hvad DER VILLE ske, skriv intet).
  3. Fyr central-nerve `session_persistence` (cluster `runtime`) med count + kinds + enforced-flag.
  4. Returnér summary-dict (count, enforced, kinds).
  - Hele kroppen i try/except → returnér tom summary ved fejl, crash ALDRIG opstart.
- Tests: zombie `running` > stale → interrupted + nerve (når ON); frisk `running` urørt;
  allerede-`interrupted` urørt; OFF → observe-only ingen skrivning; idempotent ×2; swallower exceptions.

### 5. Wire `reconcile_on_boot()` ind i opstart
- api + runtime deler ÉN entrypoint (`apps.api.jarvis_api.app:app`, differentieret kun af
  `JARVIS_ENABLE_RUNTIME_SERVICES`). Wire i lifespan i den UBETINGEDE sektion (før runtime-gaten),
  efter state-store/dirs er klar, i egen try/except. Idempotent → begge processer må køre den.

### 6. (Valgfri) `/central/session-persistence`-surface — kun hvis trivielt; ellers noteret.

## Verifikation
```bash
conda activate ai
python -m pytest tests/test_in_flight_runs.py tests/test_session_boot_reconciler.py -v
python -m compileall -q core/services/in_flight_runs.py \
  core/services/session_boot_reconciler.py \
  core/services/session_persistence_flag.py \
  apps/api/jarvis_api/app.py
```
Eksisterende `in_flight_runs`-tests skal forblive grønne.
