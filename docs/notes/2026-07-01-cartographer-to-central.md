# System Cartographer → Centralen — Handlingsordre

**Dato:** 2026-07-01
**Forfatter:** Jarvis (med Bjørns godkendelse)
**Status:** Skal udføres

## Opgave

Gør System Cartographer (`core/services/system_cartographer.py`) til en **cadence-producer** der fodrer Centralen med sine fund.

## Hvad Cartographen allerede producerer

- 665 services, 80 dark edges, 13 high-risk theater prompts
- Dark edges med score/priority (højest: `identity_sketch` 120pt)
- Theater-findings med risk-klassifikation
- Causal coverage scores pr. service

## Krav

1. **Ny cadence-producer** i `core/services/` (f.eks. `cartographer_central_producer.py`) der:
   - Kører hver 6. time (eller ved manuelt trigger)
   - Kalder System Cartographer's scanner
   - Publisherer dark edges + theater-risici som Central-observationer

2. **Nye nerver** i Centralen:
   - `cartographer/dark_edges` — antal + top-3 mørke kanter
   - `cartographer/theater_high_risk` — antal high-risk theater prompts
   - `cartographer/coverage` — gennemsnitlig causal coverage score + antal low-coverage services

3. **Eksisterende helbredsmekanik**:
   - Hvis antal dark edges stiger → flag
   - Hvis nye high-risk theater prompts dukker op → flag
   - Hvis coverage falder under 50% → flag

4. **Read-only, ingen mutation** — Cartographen scanner kun, ændrer intet.

## Prioritet

P1 — efter cowork-fix, før LivingNeuron-spec.
