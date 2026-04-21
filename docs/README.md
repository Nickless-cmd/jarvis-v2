# docs/ — dokumentations-index

Velkommen til Jarvis v2's dokumentation. Denne mappe er reorganiseret 2026-04-21
(se `DOCS_AUDIT_2026-04-21.md`). Tidligere fragment-docs er enten merged ind i
hovedreferencerne eller arkiveret under `_archive/`.

## Levende dokumenter (læs disse)

### Foundation & governance
- **[JARVIS_V2_LOCKED_CHARTER.md](JARVIS_V2_LOCKED_CHARTER.md)** — Konstitutionelt
  dokument. Definerer protected core vs. experimental layers. Læs først hvis du
  er ny.
- **[JARVIS_V2_BUILD_RULES.md](JARVIS_V2_BUILD_RULES.md)** — Alle build-/codex-/
  runtime-/auth-/cost-/coding-regler. Håndhæves via pre-commit og PR-reviews.
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — Teknisk reference til 245+ services,
  mappestruktur, eventbus-familier, multi-model identity contract, Mission
  Control overblik, workspace-model.

### Vision & roadmap
- **[CONSCIOUSNESS_ROADMAP.md](CONSCIOUSNESS_ROADMAP.md)** — 10-fase
  consciousness-aktiveringsplan (89 concepts). Living reference.
- **[CURRENT_STATUS.md](CURRENT_STATUS.md)** — Hvad er done / in progress /
  planned, i en enkelt tabel. Opdatér efter større commits.

### Strategy
- **[MODEL_STRATEGY.md](MODEL_STRATEGY.md)** — Paid visible, cheap internal.
  Lane-filosofi.
- **[llm_privacy_tier_audit.md](llm_privacy_tier_audit.md)** — 28 LLM call-sites
  klassificeret i LOCAL-REQUIRED / CONTROLLED-CLOUD / PUBLIC-SAFE. Kør igen
  kvartalsvis.
- **[UI_STRATEGY.md](UI_STRATEGY.md)** — Design-principper for MC + webchat.

### Specifications
- **[CLI_SPEC.md](CLI_SPEC.md)** — CLI-kommandoer med nuværende status per
  subkommando.
- **[TRANSPORTS.md](TRANSPORTS.md)** — SSE til chat, WebSocket til control plane.
- **[UI_ROADMAP.md](UI_ROADMAP.md)** — MC + webchat implementeringsstatus.
- **[CHANNELS.md](CHANNELS.md)** — Multi-channel kontinuitet: webchat, Discord,
  Telegram, voice, mail, ntfy.

### Auto-generated
- **[capability_matrix.md](capability_matrix.md)** — Genereres af
  `scripts/capability_audit.py`. Live/stale/orphan-status for alle services.

### Audits (historiske snapshots)
- **[DOCS_AUDIT_2026-04-21.md](DOCS_AUDIT_2026-04-21.md)** — Denne reorganisering.

## Arkiv

Historiske dokumenter ligger i `_archive/`. Se `_archive/README.md` for oversigt.
Kort: 24 PHASE-docs (consciousness-fases), 15 roadmap-dialog-filer, 51
implementerede plans+specs fra superpowers/, 9 abandoned planer, 4 origin-idea
docs, 3 completed TASK_*-docs. Alle bevaret for historisk reference.

## Hvad mangler

Capabilities der er live men mangler dedikeret dokumentation (prioriteret):

1. **PROMPT_ARCHITECTURE.md** — hvordan prompts bygges, identity injection
2. **MEMORY_SYSTEM.md** — lag (daily/weekly/monthly), fade curves, promotion
3. **AGENTS_AND_COUNCIL.md** — agent spawning, council-roller, deliberation
4. **API_REFERENCE.md** — MC endpoints, auth, response-shapes
5. **COST_ACCOUNTING.md** — cost-model, per-lane budgets
6. **TESTING_STRATEGY.md** — test coverage, CI/CD
7. **SECURITY_POSTURE.md** — auth, secret mgmt, validation, audit logging
8. **DEBUGGING_GUIDE.md** — hvordan debugger man heartbeat, signals, events

Skriv efter behov.

## Konventioner

- Markdown + UTF-8
- Dansk + engelsk blandet OK (Jarvis er tosproget)
- Datoer i filnavne: ISO (`YYYY-MM-DD-topic.md`)
- Nye docs refereret her; ellers er de usynlige
- Ved større refaktor: opdater `DOCS_AUDIT_*`-filer med næste dato så historikken er læselig
