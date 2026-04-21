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

## Auth Rules
- UI session auth is separate from provider OAuth auth
- GitHub/Codex provider credentials must never be stored in repo
- all provider auth is profile-scoped and revocable
- credentials live in runtime state dir (`~/.jarvis-v2/config/`), never in repo
- all connections are observable in Mission Control
- revoke / rotate must be supported
- first-class connections: GitHub, Codex/OpenAI, Anthropic, Ollama (cloud), Groq,
  OpenRouter, Gemini, NIM, SambaNova, Mistral, Cloudflare, OllamaFreeAPI
- additional providers may be added under the same auth profile model

## Cache / Token / Cost Rules
- prompt/native caching must be used where provider supports it
- heartbeat must be cache-aware and budget-aware
- token accounting is required per run, provider, lane and agent
- Mission Control must expose token burn and cost trends
- no hidden expensive background loops

## UI Transport Rules
- use HTTP streaming or SSE for assistant reply streaming
- use WebSocket for realtime control-plane events
- do not collapse both concerns into one opaque transport layer

## File Size Rules
- no file over 1500 lines without explicit exception
- no core runtime file over 2000 lines
- split at 1200 lines
- one responsibility per module

## Coding Rules
- no hidden side effects
- no dual truth between config and DB
- no fake agent-authored work when LLM-led output is expected
- all risky actions require explicit policy/approval path
