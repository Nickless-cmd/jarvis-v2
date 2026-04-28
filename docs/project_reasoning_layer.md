# Jarvis Reasoning Layer — Projekt Dokumentation

**Oprettet:** 2026-04-26  
**Status:** R1+R2+R3 merged (commit `7ea0973`)

---

## Baggrund

Inspireret af DeepMinds AlphaReason-arkitektur (april 2026) og neuro-symbolic reasoning-forskning.
Målet: eksplícit reasoning-lag der komponerer eksisterende classifiers i stedet for at erstatte dem.

## Arkitektur: 3 R-lag (advisory, ikke-blokerende)

### R1 — Reasoning Classifier (`core/services/reasoning_classifier.py`)
- **Rolle:** Router — vælger tier: `fast` / `reasoning` / `deep`
- **Input:** Signaler fra clarification, delegation, good_enough, self_monitor + kompleksitetsheuristik
- **Additiv point-model:** Højeste tier vinder
  - clarification `ask_first` → +30 reasoning
  - clarification `mildly_ambiguous` → +15 reasoning
  - delegation `delegate` → +25 reasoning, +15 deep hvis planner
  - risikomarkører (delete, rm -rf, force-push, secrets, prod) → +40 deep
  - lang besked (>400 chars) → +15 reasoning
  - multi-step markører (numrerede lister, "først", "derefter") → +20 reasoning
- **Vigtigt:** Erstatter IKKE eksisterende classifiers — de har forskellige temporale scopes

### R2 — Verification Gate (`core/services/verification_gate.py`)
- **Rolle:** Observational advisory — læser eventbus, klassificerer recent tool.completed events
- **To signaltyper:**
  1. **Unverified mutations** — filer skrevet/redigeret eller kommandoer kørt uden matching `verify_*` call
  2. **Failed verifications** — `verify_*` calls der returnerede `status="failed"`
- **Blokerer IKKE** — surfaces awareness kun, modellen beslutter
- **Promotion path:** R2.5 kan flippe til blocking for tier=deep actions, når vi har telemetry

### R3 — Escalation Composer (`core/services/reasoning_escalation.py`)
- **Rolle:** Komponerer tier + gate → council/sub-agent anbefaling
- **Escalation triggers (enhver af):**
  - tier=deep OG failed verify_* i recent window
  - tier=deep OG ≥3 unverified mutations
  - tier=reasoning OG ≥2 failed verify_*
- **Eskalationsveje (eksisterende tools):**
  - `convene_council(topic)` — fuld deliberation
  - `spawn_agent_task(role=critic, ...)` — uafhængig review
  - `spawn_agent_task(role=researcher, ...)` — verification i skala
- **Adfærdssikker:** Auto-spawner IKKE agents — modellen beslutter

## Designprincipper

1. **Konsolidering før addition** — R1 komponerer eksisterende classifiers, tilføjer ikke nyt uafhængigt lag
2. **Advisory, ikke blokerende** — alle 3 R-lag surfaces awareness, tvinger intet
3. **Tynd implementation** — minimal kode, ingen daemons, ingen persistens, billige at kalde
4. **Data-drevet promotion** — R2→R2.5 blocking sker kun når telemetry viser det er nødvendigt

## Risici & Mitigation

- **7 overlappende lag** (4 gamle + 3 nye): Mitigeret ved at R1 komponerer, ikke erstatter
- **Token cost ved advisory noise**: R2 læser kun on-demand, R3 trigger kun ved deep tier
- **Model ignorerer advarsler**: R2.5 blocking-tier er designet som fremtidig sikkerhedsventil

## Næste Skridt

- [ ] Telemetry: track hvor ofte R2-advarsler ignoreres vs. følges
- [ ] R2.5: conditional blocking for tier=deep + unverified mutations
- [ ] Integration i prompt-section (awareness budget cap)
- [ ] Test: unit tests for additive scoring, escalation triggers