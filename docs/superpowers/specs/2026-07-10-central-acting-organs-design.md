# Central Acting Organs — Design Spec

**Dato:** 2026-07-10
**Status:** Godkendt (brainstorm) → afventer plan
**Tema:** To observe-only organer får hver en governed, Central-drevet aktør der *handler* — ikke bare observerer. Centralens formål er at handle (Bjørn, 10. jul).

---

## Baggrund

Jarvis relayede research fra offentligt-tilgængelige Claude-Code-prompt-leaks (denser.ai-bloggen + asgeirtj/system_prompts_leaks). De brandede navne (KAIROS, autoDream, "Magic Docs", ULTRAPLAN, "5-level permissions") er **ikke** ægte Claude-Code-internals — de er blog-udsmykning. Men de underliggende *mønstre* er reelle og værd at måle imod.

Ground-truth-audit af `core/services/` viste at Jarvis allerede har ~80% af organerne (`contradiction_engine.py`, `docs_drift_watchdog.py`, `fact_gate.py`, `idle_consolidation.py`, hele dream/consolidation-suiten, `webhook_tools.py`, `gate_kernel`). De ægte deltaer er ikke "byg nyt" men "gør et eksisterende observe-only organ til en aktør".

Tre ægte deltaer blev identificeret; **denne spec dækker de to små** med samme mønster. Den tredje (topic-specific memory loading + strict-write) er større, rører **protected prompt-core**, og får sin egen spec (Spec B) senere — ikke af proces-hensyn men fordi dens blast-radius er anderledes (en bug dér degraderer hver prompt).

**Verificeret ved design-tid:**
- `contradiction_engine.detect_contradictions()` DETEKTERER (par: aktiv *decision* ↔ nylig self-review *critique* med modsat negations-polaritet) men wires INGEN steder ind i dream/distill/consolidation (grep: 0 imports). Det er ren observe-only.
- `docs_drift_watchdog.py` er watch-only (`read_report`/`check_docs_drift`/`observe_docs_drift`/`build_..._surface` — ingen edit/write).
- `central().decide(nerve, ctx, fn, *, cluster, klass)` er den governede handlings-sti (live-switch §11.1, circuit-breaker §11.2, fail-open cognitive / fail-closed security, persistent verdict-ledger).

---

## Fælles governance-mønster (begge dele)

Begge aktører følger nøjagtig samme kontrakt — det er grunden til at de deler én spec:

1. **Handling via `central().decide`** (klass `COGNITIVE`, fail-open). Centralen ER aktøren.
2. **Kill-switch** `gate_enforce.<nerve>` (via `gate_enforcement`) — governed, owner-toggle-bar.
3. **Shadow er en tidsbegrænset RAMPE, ikke destinationen.** Default OFF i et kort verifikations-vindue hvor aktøren *registrerer* det survivor-pick/den doc-edit den VILLE lave (så vi kan efterse den), derefter **flippes ON og muterer for alvor**. Succes = live og handlende, ikke permanent observatør.
4. **Reversibilitet er strukturel** — aldrig hård-slet. Contradiction: status-flip (`superseded`, bevaret række). Doc: git-tracket (revert = reversal).
5. **Runaway-værn:** cap N handlinger pr. tick + cooling-off pr. mål (aldrig gen-resolve samme par / gen-repair samme doc inden for vindue).
6. **Observabilitet i Central-CLI, ikke MC:** `jc raw /central/<view>` + nerve-event.

---

## Del 1 — `contradiction_resolver.py`

### Ansvar
Konsumér `contradiction_engine`-findings og resolvér modsigelser gennem Centralen. Kører på den eksisterende dream/consolidation-cadence (resolution sker mens Jarvis "sover"). Detektionen forbliver **ren og uændret** i `contradiction_engine.py`.

### Fil
- Create: `core/services/contradiction_resolver.py`
- Uændret: `core/services/contradiction_engine.py` (kun læst via `detect_contradictions()`)
- Hook: den eksisterende consolidation/dream-cadence kalder `resolve_contradictions()`
- Test: `tests/test_contradiction_resolver.py`

### Komponenter
- **`classify_tier(finding) → "auto" | "escalate"`** — tier-C-gaten. Escalate når den tabende side rører identitet/self-model/værdier (nøgleord-heuristik + høj `decision_priority`); ellers auto. Lav-konfidens findings (svag token-overlap / uklar polaritet) behandles som escalate, ikke auto.
- **`pick_survivor(finding) → {winner, loser, rule, confidence}`** — authority-first, recency-tiebreak. Decision og self-review-critique er begge self-derived → tie → den nyere reflektive critique supersederer den stale decision. `confidence` fra token-overlap-styrke + polaritets-klarhed.
- **`resolve_contradictions(*, live: bool) → summary`** — pr. finding: `classify_tier` → `pick_survivor` →
  - **auto:** `central().decide(nerve="contradiction_resolution", …)` hvis handling markerer den tabende decision `superseded` (status-flip, reversibel, aldrig slettet, audit-logget med `superseded_by=review_id`, `superseded_reason`, timestamp).
  - **escalate:** skriv et resolution-*forslag* til owner/self-bekræftelse (genbrug eksisterende `*_proposal_tracking`-mønster). Muterer intet.
  - Når `live=False` (shadow-rampe): beregn survivor + intended action, emit event, men **mutér ikke**.

### Data-flow
```
consolidation tick
  → detect_contradictions()          (uændret, ren)
  → classify_tier                    (auto | escalate)
  → pick_survivor                    (authority → recency)
  → auto:     central().decide → apply_supersede(decision)
    escalate: write_proposal
  → emit nerve cognition/contradiction_resolved
```

### Handling: supersede
- Marker den tabende decision med status→`superseded` (+ `superseded_by`, `superseded_reason`, `superseded_at`).
- Række bevares → reversibel. Owner-reversal via Central-CLI (`superseded → active`).
- Præcis tabel/kolonne-detalje afklares i planen mod decision-storen (`_fetch_active_decisions` viser en status-baseret model).

### Error handling
Fail-open (COGNITIVE): enhver fejl → SKIP, vælter aldrig consolidation-tick'en. Escalate-tier muterer aldrig. Cap + cooling-off mod runaway.

### Test
- Unit: `classify_tier` (identitet→escalate, operationel→auto, lav-konfidens→escalate); `pick_survivor` (authority-vinder, recency-tiebreak, konfidens-beregning); `resolve_contradictions` shadow (registrerer, 0 mutation) vs live (muterer + event); fail-open ved fejl; cap + cooling-off (samme par ikke gen-resolvet).
- Integration: seed contradicting decision+review → live-run markerer decision `superseded` + emitter nerve; escalate-case skriver forslag og muterer intet.

### Observabilitet
`jc raw /central/contradictions` + nerve `cognition/contradiction_resolved` — viser resolved, proposed, survivor-rule, reversal-handle.

---

## Del 2 — `doc_repair_agent.py`

### Ansvar
Opgradér doc-vedligehold fra watch→repair via en scope-begrænset aktør. Detektion forbliver **uændret** i `docs_drift_watchdog.py` (den fortæller allerede *hvilke* docs der er drevet).

### Fil
- Create: `core/services/doc_repair_agent.py`
- Uændret: `core/services/docs_drift_watchdog.py` (kun læst via drift-signal)
- Hook: idle/consolidation-cadence kalder repair-tick
- Test: `tests/test_doc_repair_agent.py`

### Komponenter
- **`find_stale_docs() → list[DocTarget]`** — konsumér `docs_drift_watchdog`-drift-signalet.
- **`repair_doc(target, *, live) → outcome`** — to modes:
  - **(a) deterministisk regenerering** når doc'en har en kendt generator (klareste, zero-LLM case: `capability_matrix.md` ← `capability_audit.py`).
  - **(b) scope-begrænset LLM-draft** for narrative docs.
  - Anvender skrivningen gennem `central().decide(nerve="doc_repair", …)`.

### Sikkerhed = scope-lock
- **Path-allowlist begrænset til `docs/`** — aktøren kan fysisk ikke skrive uden for `docs/`, rører aldrig kode. Dette er det kritiske invariant.
- Git-tracket → reversal er en revert.

### Governance
Identisk med Del 1: `central().decide` nerve `doc_repair`, kill-switch `gate_enforce.doc_repair`, shadow-rampe→live, cap pr. tick, cooling-off pr. doc.

### Error handling
Fail-open: fejl → SKIP, vælter aldrig cadence. Deterministisk regen foretrækkes (verificerbar) over LLM-draft.

### Test
- Unit: **path-allowlist afviser enhver ikke-`docs/`-sti** (kritisk test); deterministisk regen matcher generator-output; shadow vs live; fail-open; cap.
- Integration: seed en stale doc m. generator → live-run regenererer + emitter nerve; ikke-`docs/`-mål afvises hårdt.

### Observabilitet
`jc raw /central/doc-repair` + nerve `maintenance/doc_repaired`.

---

## Byggerækkefølge

Sekventielt (Bjørn: "en efter en"):
1. **Del 1** contradiction_resolver — byg, shadow-rampe, verificér survivor-picks, flip live.
2. **Del 2** doc_repair_agent — byg, shadow-rampe, verificér regen, flip live.

Hver del deployes inkrementelt (container ff-pull + genstart begge services; `bs@10.0.0.39`). Ingen desk-build (rent backend).

## Uden for scope (bevidst)
- **Spec B (senere):** topic-specific memory loading + strict-write-discipline (protected prompt-core, egen spec).
- KAIROS-webhooks, ULTRAPLAN human-in-loop, 5-level permissions — allerede dækket eller lav marginal værdi (council/Keymaker/gate_kernel findes).

## Rammer
- Ingen ny fil > 1500 linjer (begge er små, enkelt-ansvar).
- Ingen dobbelt-sandhed: detektion forbliver i eksisterende organer; kun handlings-siden er ny.
- Boy Scout ved berøring af store filer (cadence-hook-sitet).
