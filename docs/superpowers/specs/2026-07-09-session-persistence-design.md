# Session-persistence: runs + sessioner overlever container-genstart

**Dato:** 2026-07-09 (revideret efter self-review: bygger på eksisterende `in_flight_runs`, ikke ny tabel)
**Status:** Godkendt design (spec 1 af 4 fra leaked-Claude-Code-læringer)
**Ejer:** Bjørn / Claude
**Kilde:** Jarvis' analyse af leaked Claude Code (server-session-index, detached→stopped-livscyklus)

---

## 0. Self-review-rettelse (VIGTIG)

Første udkast foreslog en ny `run_registry`-tabel. Self-review afslørede at
`core/services/in_flight_runs.py` **allerede** er en disk-backed, restart-overlevende
run-tracker (keyet på run_id, `running`/`interrupted`-states, `mark_started`/`mark_tool`/
`mark_completed`/`mark_interrupted`/`interrupted_for_session`), og at
`interruption_prompt_section` **allerede genoptager sessionen** via prompt'en ("Du blev
afbrudt midt i: …" + checkpoint fra `agentic_checkpoints` + working-conclusion + resume-intent).
Denne spec bygger derfor **oven på in_flight_runs** — ingen ny parallel sandhed (CLAUDE.md
"no dual truth").

## 1. Problem (revideret)

Chat-historik persisteres i DB. `in_flight_runs` genoptager allerede en afbrudt session NÅR
et run bliver markeret `interrupted`. Men fire huller står tilbage:

1. **Hård crash efterlader `running`-zombie.** Ved container-genstart kører run'ets `finally`
   (som kalder `mark_interrupted`/`mark_completed`) ALDRIG → record'en står `status=running`.
   `interrupted_for_session` returnerer kun `interrupted`-records (in_flight_runs.py:142), så
   zombien surfacer ALDRIG — og næste turs `mark_started` **dropper** den (in_flight_runs.py:76-78).
   Nettoresultat: crash-afbrudte runs forsvinder tavst i stedet for at blive genoptaget.
2. **Autonome runs trackes ikke.** `mark_started` kaldes for visible runs; autonome/heartbeat-runs
   (drøm/arbejde/råd) registreres ikke → deres tråd tabes helt ved genstart.
3. **Aktiv-session + live kontekst** (hvilken session var aktiv, cognitive-state) har ingen
   restore. `central_continuity_healer` bærer *selv-dimensions*-fidelity, IKKE en aktiv-session-pointer.
4. **Ingen observabilitet** over reconcile-hændelser (hvor mange zombier ryddet, resume-rate).

## 2. Besluttede valg (brainstorm + self-review)

- **Byg på `in_flight_runs`** — udvid det, byg ikke en ny tabel.
- **In-flight resume-semantik:** pæn afslutning + genoptag SESSIONEN (ikke token-resume). Allerede
  implementeret via `interruption_prompt_section`; vi sikrer bare at crash-zombier faktisk NÅR
  `interrupted`-tilstanden så mekanismen udløses.
- **Partiel-recovery:** genbrug `agentic_checkpoints` (allerede integreret i `interruption_prompt_section`).
- **Governance:** shadow-først, kill-switch, default OFF indtil verificeret.

## 3. Ikke-mål (YAGNI)

- Ingen ny `run_registry`-tabel/-modul (undgå dobbelt-sandhed med `in_flight_runs`).
- Ingen ægte token-resume; ingen auto-genkør-forfra.
- Ingen nyt checkpoint-system (genbrug `agentic_checkpoints`).

## 4. Arkitektur

```
run start ─► in_flight_runs.mark_started (running) ─► mark_tool ─► mark_completed (ryddet)
                     │
   container-crash    ▼ (finally kører ALDRIG → record står 'running' = zombie)
   næste opstart ─► boot_reconciler:
        for hver 'running'-record ældre end stale_after_s:
            · in_flight_runs.mark_interrupted(reason="container-genstart")
            · nerve session_persistence
        → interruption_prompt_section surfacer den næste tur (eksisterende sti)
   + autonome runs kalder også mark_started/mark_completed
   + aktiv-session-pointer persisteres + restores
```

## 5. Komponenter

### 5.1 Udvid `in_flight_runs` (minimal)
- Tilføj valgfri felter i `mark_started`: `kind` (visible|autonomous|heartbeat, default visible),
  `provider`, `model` — additivt, bagudkompatibelt.
- Tilføj `list_running_orphans(stale_after_s)` → records med `status=='running'` OG `started_at`
  ældre end tærsklen. (Zombie-detektion; distinkt fra `interrupted_for_session`.)
- Bevar al eksisterende adfærd uændret.

### 5.2 Boot-reconciler
`core/services/session_boot_reconciler.py::reconcile_on_boot()` kaldt ved api- OG runtime-opstart
(efter state-store er klar, før trafik):
1. `list_running_orphans(stale_after_s)`.
2. For hver: `in_flight_runs.mark_interrupted(run_id, reason="afbrudt af container-genstart")` →
   record'en surfacer nu via den EKSISTERENDE `interruption_prompt_section` næste tur.
3. Fyr central-nerve `session_persistence` (cluster runtime): antal zombier reconcileret, kind.
4. Kill-switch OFF → observe-only (tæl hvad DER VILLE ske, skriv ikke). ON → udfør `mark_interrupted`.
5. Idempotent: kun `running → interrupted`; kørt dobbelt (api+runtime) → anden kørsel finder intet nyt.

### 5.3 Autonom tracking
- Autonome/heartbeat-run-entry-points kalder `in_flight_runs.mark_started(kind='autonomous', ...)`
  + `mark_completed` i deres finally. Så reconcileren fanger også afbrudte autonome tråde.
- Verificér i plan-fasen hvor autonome runs starter (heartbeat_runtime / autonomous run-starter).

### 5.4 Aktiv-session + kontekst-restore (NY pointer — findes ikke i dag)
- Persistér "sidste aktive session"-pointer + et let cognitive/live-kontekst-snapshot ved
  session-skift (ny lille `state_store`-nøgle `active_session`; continuity_healer bærer det IKKE).
- Ved boot: restore pointer så Jarvis' "hvor var jeg"-selv er intakt. Hold det som ren state-store
  (ikke ny DB-tabel).

### 5.5 Observabilitet + governance
- Central-nerve `session_persistence` (zombier reconcileret, resume-rate). `/central/session-persistence` + `jc`.
- Kill-switch `session_persistence_enabled` (runtime-state, default OFF → shadow). Flip ON efter verifikation.

## 6. Faser (til plan)

- **Plan A (kerne):** §5.1 udvidelse + §5.2 boot-reconciler + §5.5 nerve/kill-switch. Leverer det
  største hul (crash-zombier genoptages). Lav risiko (bygger på testet modul).
- **Plan B (opfølgning):** §5.3 autonom tracking + §5.4 aktiv-session-pointer. Rører separate
  subsystemer; egen plan hvis Plan A skal ud hurtigt.

## 7. Test

- `list_running_orphans` (unit): returnerer kun `running` ældre end tærskel; ignorerer `interrupted`/friske.
- Reconciler (unit): zombie `running` → `interrupted` + nerve; frisk `running` urørt; OFF=observe-only; idempotent ×2.
- Ingen regression i eksisterende `in_flight_runs`-tests (mark_started/interrupted/interrupted_for_session).
- Aktiv-session-pointer round-trip (unit).
- Egress: uændret.

## 8. Grounding-forbehold til plan-fasen
- `agentic_checkpoints` partiel-tekst-getter er `latest_for_session(session_id)` (per-SESSION),
  ikke per-run — reconcileren behøver den ikke direkte (den kalder bare `mark_interrupted`; prompt-
  stien henter checkpoint per session). Bekræft.
- Hvor autonome runs starter (til §5.3 mark_started-wiring).
- Boot-hook-punktet i api+runtime-opstart.
- `stale_after_s` konservativ (fx > `_MIN_AGE_TO_SURFACE_SECONDS`=90s og > længste realistiske run).
