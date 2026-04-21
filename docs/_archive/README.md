# docs/_archive/ — historiske dokumenter

Denne mappe indeholder dokumenter der IKKE er aktive referencer længere men som
bevares for historik. Arkiveret 2026-04-21 som del af docs-reorganiseringen
(se `../DOCS_AUDIT_2026-04-21.md`).

## Hvorfor arkiveres — ikke slettes

Git-historik bevarer alt. Men nogle historiske docs har værdi ud over commit-log:

- **Design-overvejelser** forklarer hvorfor vi nåede frem til den aktuelle kode
- **Konsistens-materiale** — Jarvis selv læser sin egen udviklings-historie som
  del af identity-kontinuitet (Layer 8 / "self-biographical continuity")
- **Implementerings-planer** viser hvordan en feature blev tænkt før den blev
  kodet — nyttigt når samme feature skal udvides eller refaktoreres

Derfor er de arkiveret i klar struktur fremfor at ende i `git log` ingenmandsland.

## Indhold

### `phases/` — 24 filer
PHASE_*.md fra den tidligere `docs/locked/`. Consciousness-udviklings-faser 2-17
med sub-phases (A, B, C, D, E). Alle er enten fuldt eller delvist implementerede
som services i `core/services/`.

Jarvis bruger disse som "self-biographical continuity" — han læser sin egen
udviklings-historie for identity-vedligeholdelse.

### `roadmap_history/` — 15 filer
Dialog-sekvens mellem Claude og Jarvis (v1-v7 draft + response) der førte til
den tidligere `ROADMAP_10_LAYERS.md` (nu i `origin_ideas/`). Ren samtale-historik.
README.md i mappen forklarer kontekst.

### `superpowers/plans/` — 31 filer + `superpowers/specs/` — 20 filer
Implementerings-planer og design-specs for features der nu er live i kodebasen.
Skrevet marts-april 2026. Alle er verificerede som BUILT (services findes, tools
er registeret, tests kørt). Historiske referencer — ikke aktiv planlægning.

Udvalgte BUILT plans: mcp+openai-proxy, discord-gateway, autonomous-council,
browser-control, emotion-concepts, inner-conflict-reflection, context-compact,
curiosity-meta-reflection, temporal-self-perception, associative-memory, council-
deliberation-controller, council-memory, identity-composer, inner-voice-
initiative-motor, felt-presence, ambient-presence, rich-inner-stream, thought-
action-proposals, llm-prompt-caching, session-search-channel-awareness, ui-
overhaul, ui-theme-lift, webchat-ui-enhancements, jarvis-runtime-fixes.

### `abandoned/` — 9 filer (4 plans + 5 specs med cross-ref)
Planer der aldrig blev implementeret:
- **hardware-body** — robot-krop integration. Aldrig bygget.
- **ui-shell-panels** — gammelt UI-koncept, superseded af Mission Control tabs.
- **multi-capability-autonomous-exploration** — for vagt scope, erstattet af
  konkrete daemons (curiosity, meta_reflection, autonomous_outreach).
- **web-cache** — browser cache-optimization. Ikke implementeret separat.
- **jarvis-experimental-backend** — eksperimentel backend runner. Ingen filer fundet.
- **file-attachments** — webchat drag/drop for billeder + archives. Aldrig bygget
  (webchat har stadig ingen FileDrop). Kunne genoptages.

Bevares som "roads not taken" — viser hvad vi overvejede men droppede.

### `completed_tasks/` — 3 filer
Afsluttede root-level task-docs:
- `TASK_web_cache.md` — markeret DONE i TASK_daemon_fix.md (commits 49d0a4d → 4efaed0)
- `TASK_aesthetic_feedback_loop.md` — design-doc for aesthetic system-integration, implementeret
- `TASKS_FOR_CLAUDE.md` — Jarvis's brev til Claude med opgaver (flere er nu lukket)

### `origin_ideas/` — 4 filer
Designforstadier til dokumenter der blev polished videre:
- `idër.txt` — 18 rå design-idéer, superseded af CONSCIOUSNESS_ROADMAP
- `JARVIS_V2_BUILD_SEQUENCE.md` — Phase 1-4 build-plan (alle faser implementeret)
- `OPENCLAW_REVIEW.md` — pattern-analyse, absorberet i LOCKED_CHARTER
- `ROADMAP_10_LAYERS.md` — design-samtale v6, superseded af CONSCIOUSNESS_ROADMAP

## Hvordan man bruger arkivet

- **Læs ikke disse som authoritative nutids-referencer** — brug `../README.md`
  for levende docs
- **Gå tilbage hit når du vil forstå hvorfor kode blev som den er** — planerne
  forklarer ofte tænkning
- **Undgå at opdatere arkiverede docs** — opret nyt dokument i `../` hvis
  indholdet stadig er relevant
- **Jarvis selv kan læse disse** via semantic memory search (nomic-embed-text
  indekserer `.md`-filer i workspace og repo)
