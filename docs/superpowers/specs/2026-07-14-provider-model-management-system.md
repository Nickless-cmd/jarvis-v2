---
status: udkast v8 — live-testet, Bjørns retning 14. jul 2026
formål: Komplet provider/model management-system — auto-scanning, scoring,
 auto-opdatering, health-check på alle providers. Udvider agent-pool med
 bekræftede gratis modeller og giver Centralen livscyklus-styring.
kilder: Samtale Bjørn+Jarvis 14. jul, live API-tests (nøgle→model→svar),
 provider_router.json, settings.py, auth profiles, full provider audit,
 cheap_lane_balancer.py, cheap_provider_runtime_selection.py, provider_health_check.py
revision: v8 — Eksisterende fundament dokumenteret + agent pool router spec tilføjet
---

# Provider/Model Management System

## Problem

Jarvis' provider-landscape er statisk og manuelt vedligeholdt...

## Eksisterende fundament — hvad vi allerede har

Før vi bygger nyt: vi har allerede et sofistikeret cheap lane-system. Den nye agent pool router bygger OVEN PÅ dette, ikke ved siden af.

### Cheap Lane Balancer (`core/services/cheap_lane_balancer.py`)
- **Weighted-random load balancing** på tværs af alle (provider, model) slots
- **Circuit breaker** med 4 niveauer: normal → 5min cooldown → 15min → 1t
- **RPM tracking** via in-memory ring buffer + **daily quota** (reaktiv fra 429)
- **Provider-wide cooldown** — DNS/connection timeout køler ALLE slots fra en provider på én gang
- `call_balanced()` — prøv slot → fejl → næste slot (max 3 retries)
- Tilstand persisteres til disk (debounced saves)
- EventBus-emission for success/failure/pool_exhausted
- Cost ledger-integration

### Provider Selection + Routing (`core/services/cheap_provider_runtime_selection.py`)
- **Task-kind tiering**: `background` (public proxy først), `default` (betalt først), `important` (kun betalt)
- **Fallback chain** — fejl på én provider → automatisk prøv næste
- **Public-safe lane** (ollamafreeapi + lokal ollama)
- **Adaptive penalty** — sænker prioritet baseret på nylige failures
- **TTL-cached status surface** (5s cache, shared på tværs af workers)
- `smoke_cheap_lane()` — test ALLE providers i ét samlet kald
- `test_provider_target()` — test én enkelt provider

### Provider Health Check (`core/services/provider_health_check.py`)
- **Pinger alle providers hvert 5. minut** via heartbeat
- **Detekterer model-drift** — en provider der FØR havde N modeller men nu har 0
- **Proaktiv cooldown** — hvis ping fejler, sættes en 6-minutters cooldown FØR en daemon rammer fejlen
- **Centralen-integration** — observerer til `system/provider_health` nerven
- **Incident flagging + auto-resolve** — slår alarm, løser når de kommer tilbage
- `health_section()` — awareness-sektion der viser aktuelt nede providers

### Hvad mangler (skal bygges)

| Funktion | Status | Hvorfor |
|---|---|---|
| **Agent pool** (task-scoring) | ❌ Mangler | Cheap lane er designet til daemons, ikke agenter. Agent pool skal have task-baseret model-valg (coding vs reasoning vs classification), agent-specifik failover, kvalitets-måling |
| **Auto-discovery** af nye modeller | ❌ Mangler | Opdag nye modeller automatisk — ingen manuel opdatering af provider_router.json |
| **Auto-recovery** ved model-drift | ⚠️ Delvist | Health check DETEKTERER model drift, men GØR INTET ved det — opdaterer ikke provider_router.json automatisk |
| **Rate-limit læring** over tid | ⚠️ Delvist | Reagerer på 429'er men lærer ikke mønstre over dage/uger |
| **Selvhelbredende router** | ⚠️ Delvist | Balanceren failover'er inden for cheap lane, men agent pool har intet |

## Agent pool router — bygget oven på fundamentet

Den nye agent pool router skal udvide det eksisterende system, ikke erstatte det. Principper:

1. **`select_cheap_lane_target()` udvides** med task-kind parameter + model-kvalitets-score
2. **Task-scoring** — coding, reasoning, classification, summarization, creative, fast_lookup — hver model får en vektor
3. **Gratis > betalt > premium** — ligesom cheap lane, men med agent-specifik routing
4. **Auto-discovery daemon** — daglig scanning af alle providers' `/models` endpoints, diff mod provider_router.json
5. **Model drift detection** — hvis en model der FØR virkede nu giver 404, fjern den automatisk og log til Centralen
6. **Rate-limit profilering** — lær over tid hvilke providers der rent faktisk har kapacitet, justér vægte
7. **Self-healing** — hvis 3+ providers fejler samtidig, eskaler til visible lane med notifikation til Bjørn
8. **Centralen events** for alt — model tilføjet/fjernet/provider nede/rate-limit nået

## Live-testet provider-status (14. juli 2026)

### ✅ Virker — gratis (bevist med rigtigt model-svar)

[tabellen forbliver uændret — 17 providers, ~270 modeller]
