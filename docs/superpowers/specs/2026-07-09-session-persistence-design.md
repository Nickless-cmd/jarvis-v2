# Session-persistence: runs + sessioner overlever container-genstart

**Dato:** 2026-07-09
**Status:** Godkendt design → (spec 1 af 4 fra leaked-Claude-Code-læringer)
**Ejer:** Bjørn / Claude
**Kilde:** Jarvis' analyse af leaked Claude Code (server-session-index, detached→stopped-livscyklus)

---

## 1. Problem

Chat-sessioner + beskeder persisteres allerede i DB og overlever genstart. Men fire ting går tabt når containeren (jarvis-api / jarvis-runtime) genstarter:

1. **In-flight runs** — et run der streamer NÅR containeren genstarter dør midt i. Brugeren ser en halv besked; svaret tabes.
2. **Aktiv-session + live kontekst** — hvilken session var aktiv, cognitive/arousal-state, "den igangværende samtale-kontekst" nulstilles.
3. **Autonom kontinuitet** — heartbeat/autonome runs (drøm/arbejde/råd) taber deres tråd; Jarvis starter forfra i stedet for at samle op.
4. **Run-registry / kilde-af-sandhed** — der findes intet in-memory-overlevende register over "hvad kørte da vi gik ned" (Claude Codes `server-sessions.json` med `starting→running→detached→stopping→stopped`).

**Referencemodel (Claude Code):** en persisteret session-index med livscyklus-states; ved genstart genoptages SESSIONEN (kontekst), ikke selve token-strømmen.

## 2. Besluttede valg (brainstorm)

- **Fuld bredde:** alle fire tab adresseres.
- **Fundament:** et persisteret run/session-registry er kilde-af-sandhed; de tre andre læser fra det.
- **In-flight resume-semantik:** **pæn afslutning + genoptag SESSIONEN** — ikke ægte token-resume, ikke auto-genkør-forfra. Det døde run markeres `interrupted`, det streamede-indtil-nu persisteres ærligt (hvis et checkpoint findes), og sessionen er genoptagelig fordi konteksten ligger i DB.
- **Partiel-recovery:** byg på eksisterende `agentic_checkpoints` hvor den findes; hvor den ikke gør, accepter "kun `interrupted`-markør" (ingen partiel tekst) frem for et nyt tungt checkpoint-lag.
- **Governance:** shadow-først, kill-switch, default OFF indtil verificeret.

## 3. Ikke-mål (YAGNI)

- Ægte token-for-token generering-resume (provider-afhængigt, reasoning-modeller bryder).
- Auto-genkør-hele-run'et-forfra (spild + dublet-tool-effekter + loop-risiko).
- Et nyt parallelt checkpoint-system (genbrug `agentic_checkpoints`).
- Migration af eksisterende data (registry er additivt; tomt indtil runs registrerer).

## 4. Arkitektur

```
run start ─► run_registry (running) ─► heartbeat_at opdateres ─► stopped (ren afslutning)
                     │
   container-genstart ▼ (efterlader running/starting forældreløse)
             boot-reconciler ─► for hver forældreløs:
                 · markér interrupted
                 · persistér partiel tekst (fra agentic_checkpoints hvis den findes)
                 · fyr central-nerve session_persistence
                 · session forbliver genoptagelig (kontekst i DB)
             + restore aktiv-session-pointer + autonom-tråd re-kø
```

## 5. Komponenter

### 5.1 `run_registry`-tabel
Ny tabel (idempotent ALTER-mønster som `_ensure_chat_messages_*`):
```sql
CREATE TABLE IF NOT EXISTS run_registry (
    run_id TEXT PRIMARY KEY,
    session_id TEXT,
    kind TEXT NOT NULL,          -- visible | autonomous | heartbeat
    state TEXT NOT NULL,         -- starting|running|detached|stopping|stopped|interrupted
    origin TEXT NOT NULL DEFAULT '',
    provider TEXT NOT NULL DEFAULT '',
    model TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    streamed_chars INTEGER NOT NULL DEFAULT 0
)
```
Modul `core/services/run_registry.py`: `register_run(...)`, `mark_state(run_id, state)`, `touch(run_id, streamed_chars)`, `list_orphaned(stale_after_s)`, `stop(run_id)`. Ren DB, ét-ansvar, enhedstestbar.

### 5.2 Registrering + liveness i `visible_runs`
- Ved run-start: `register_run(run_id, session_id, kind, ...)` (state=`running`).
- Undervejs: `touch(run_id, streamed_chars)` billigt (throttlet, fx hvert 2s / hvert checkpoint) — dette er ogsÅ liveness-signalet.
- Ved ren afslutning/cancel/fejl: `mark_state(run_id, 'stopped')`.
- Alt fail-open: en registry-fejl må ALDRIG bryde et run (try/except-indkapslet, som blok-akkumulatoren).

### 5.3 Boot-reconciler
`core/services/session_boot_reconciler.py::reconcile_on_boot()` kaldt ved api- OG runtime-opstart (efter DB-ensure, før trafik). Skridt:
1. `list_orphaned(stale_after_s)` — runs i `running`/`starting` hvis `heartbeat_at` er ældre end tærsklen (dvs. ikke ryddet ordentligt = crash/genstart).
2. For hver: hent partiel tekst fra `agentic_checkpoints` (hvis den findes) → persistér som assistant-besked med ærlig "⚠ Jeg blev afbrudt af en genstart her" (eller bare markér uden tekst). Genbrug `_persist_session_assistant_message`-stien.
3. `mark_state(run_id, 'interrupted')`.
4. Fyr central-nerve `session_persistence` (cluster runtime) med årsag + kind.
5. Kill-switch OFF → observe-only (registrér hvad DER VILLE ske, ingen skrivning). ON → udfør.

### 5.4 Aktiv-session + kontekst-restore
- Persistér "sidste aktive session"-pointer + cognitive/live-kontekst-snapshot ved session-skift (genbrug eksisterende cognitive-state-persistering hvis den findes; ellers en lille runtime-state-nøgle).
- Ved boot: restore pointer så Jarvis' "hvor var jeg"-selv er intakt. Byg på eksisterende continuity_healer ([[project_jarvis_wishlist]] #1) hvis den allerede bærer dette — undgå dobbelt-sandhed.

### 5.5 Autonom kontinuitet
- Autonome runs registreres med `kind='autonomous'` + `origin`.
- Reconcileren: forældreløse autonome runs → re-kø den autonome tråd (via eksisterende initiative/heartbeat-kø) i stedet for at tabe den. Idempotent (ingen dobbelt-spawn).

### 5.6 Observabilitet + governance
- Central-nerve `session_persistence`: reconcileret-antal, resume-events, forældreløs-alder. `/central/session-persistence` + `jc`.
- Kill-switch `session_persistence_enabled` (runtime-state, default OFF → shadow). Flip ON efter shadow-verifikation.

## 6. Blast-radius & afbødning

| Risiko | Afbødning |
|--------|-----------|
| Registry-skrivning i run-hot-path | Throttlet upsert, try/except fail-open, aldrig bryd run |
| Reconciler kører dobbelt (api+runtime) | Idempotent: `interrupted`-transition kun fra `running/starting`; row-lås/CAS |
| Falsk-forældreløs (langt legitimt run) | `stale_after_s` > længste realistiske run + heartbeat holder live runs friske |
| Partiel tekst findes ikke | Degradér til ren `interrupted`-markør; session stadig genoptagelig |
| Dobbelt-sandhed vs continuity_healer/cognitive-state | Genbrug eksisterende; registry ejer KUN run-livscyklus |

## 7. Test

- `run_registry` (unit): register→touch→mark→stop; `list_orphaned` respekterer `stale_after_s`.
- Reconciler (unit): forældreløs `running` → `interrupted` + nerve; frisk run urørt; OFF=observe-only.
- Idempotens: reconcile ×2 → én transition, ingen dublet-besked/-respawn.
- Hot-path: registry-fejl bryder ikke run (fail-open test).
- Egress: uændret (ren intern DB-state).

## 8. Faser

1. `run_registry`-modul + tabel (isoleret, testbar).
2. Registrering + liveness i visible_runs (hot-path, Claude inline).
3. Boot-reconciler + nerve + kill-switch (shadow).
4. Aktiv-session/kontekst-restore (byg på continuity_healer).
5. Autonom kontinuitet re-kø.
6. Shadow-verifikation → flip ON.

## 9. Åbne detaljer til plan-fasen
- Præcis `agentic_checkpoints`-API for partiel-tekst-hentning (verificér i Task 1).
- Om continuity_healer allerede bærer aktiv-session/kontekst (undgå dobbelt).
- Boot-hook-punktet i api+runtime-opstart (hvor DB-ensure allerede kaldes).
- `stale_after_s`-værdi (start konservativt, fx 2× længste observerede run).
