# Jarvis V2 Build Rules

## Repo Rules
- code repo is not runtime state home
- runtime state lives in ~/.jarvis-v2/
- one source of truth per concern
- no duplicate settings in DB and config

## Codex Rules
Codex may:
- work only within stated scope
- not do repo-wide rewrites without explicit approval
- not invent architecture beyond charter
- not create megafiles
- not use persistence-producing cognition paths for visible companion output
- not change files outside task scope

Codex must:
- report exact files changed
- report exact behavior changed
- report targeted tests run or explicitly state none exist
- create commits only with explicitly provided commit message

## Runtime Rules
- all autonomy must be observable
- all reflective subsystems must declare:
  - trigger
  - budget lane
  - persistence rule
  - event emission
  - kill switch

## Cost Rules
- token accounting must exist from early phases
- heartbeat must be cost-aware
- native/provider caching should be used where available
- free models are for cheap cognition, not visible Jarvis core

## Inner Voice Rules
- private by default
- not the boredom ping path
- not persisted by default
- only promoted explicitly
