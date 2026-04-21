# Docs Audit — 2026-04-21

Samlet gennemgang af alle markdown-dokumenter i `docs/` og repo-roden.
Baggrund: Jarvis v2's roadmap er closed 8/8 (april 2026), de fleste planer
fra marts-april er nu implementerede, og dokumenter er blandet live/stale/historisk.

**Scope:** 25 top-level docs i `docs/` + 37 plans + 23 specs i `superpowers/` +
24 PHASE-docs i `locked/` + 15 dialog-filer i `roadmap_history/` +
6 task-docs i repo-rod + et par straggler-filer.

## TL;DR

| Handling | Antal | Hvad |
|---|---|---|
| **KEEP som de er** | 9 | Kerne-referencer (ARCHITECTURE, CHARTER, BUILD_RULES, CONSCIOUSNESS_ROADMAP, capability_matrix, MODEL_STRATEGY, llm_privacy_tier_audit, TRANSPORTS, UI_STRATEGY, STANDING_ORDERS) |
| **MERGE i bigger docs** | 5 | Tynde enkeltsides-docs der gentager større docs (CODING_RULES, AUTH_AND_CONNECTIONS, EVENTBUS, MISSION_CONTROL, WORKSPACE_MODEL) |
| **REWRITE** | 2 | CLI_PLAN, UI_ROADMAP — outdated status |
| **ARCHIVE til `docs/_archive/`** | ~85 | Alle implementerede plans+specs, PHASE_*-filer, roadmap_history, completed TASK_-filer |
| **DELETE** | 4 | Tom reference_old/, stub MEMORY.md i rod, commands.txt, spec-file.txt |
| **ACTION-REQUIRED** | 2 | TASK_daemon_fix.md (aktiv bug), CODEX_TASK_tool_result_externalization.md (design klar til impl) |

---

## Top-level `docs/` (25 filer)

### KEEP som de er (9)

| Fil | Hvorfor |
|---|---|
| `ARCHITECTURE.md` | Opdateret 2026-04-20. Live reference til 245 services. |
| `JARVIS_V2_LOCKED_CHARTER.md` | Konstitutionelt dokument — protected core, experimental layers. |
| `JARVIS_V2_BUILD_RULES.md` | Governance — aktivt håndhævet via Boy Scout + PR-reviews. |
| `CONSCIOUSNESS_ROADMAP.md` | Living vision reference, opdateret 2026-04-20. |
| `capability_matrix.md` | Auto-genereret fra `scripts/capability_audit.py` — kør efter større commits. |
| `MODEL_STRATEGY.md` | Lane-filosofi (paid visible, cheap internal). |
| `llm_privacy_tier_audit.md` | 28 LLM call-sites klassificeret. Kritisk for provider-valg. |
| `TRANSPORTS.md` | SSE/WebSocket-regler. Kort, præcis, stabil. |
| `UI_STRATEGY.md` | Designprincipper (stabile). |

### MERGE ind i større dokumenter (5)

Alle er tynde (11-21 linjer) og gentager indhold i hovedreferencer:

| Fil | Merge-mål | Grund |
|---|---|---|
| `CODING_RULES.md` (11L) | `JARVIS_V2_BUILD_RULES.md` | 80% overlap med BUILD_RULES linje 62-67 |
| `AUTH_AND_CONNECTIONS.md` (17L) | `JARVIS_V2_BUILD_RULES.md` | Duplikerer auth-regler 45-48 |
| `EVENTBUS.md` (21L) | `ARCHITECTURE.md` | ARCHITECTURE har allerede fuld event-families tabel |
| `MISSION_CONTROL.md` (17L) | `ARCHITECTURE.md` | MC beskrives mere fyldestgørende i ARCHITECTURE |
| `WORKSPACE_MODEL.md` (14L) | `ARCHITECTURE.md` | ARCHITECTURE har komplet workspace-struktur |

### REWRITE (2)

| Fil | Problem | Forslag |
|---|---|---|
| `CLI_PLAN.md` | 20 linjer, kun mål — status per subkommando mangler | Omskriv til `CLI_SPEC.md` med nuværende implementerings-status |
| `UI_ROADMAP.md` | Status 18 dage gammel, Fase 1 i limbo | Opfrisk til nuværende state (MC 60%, webchat 50%), marker ejerskab |

### ARCHIVE (3)

| Fil | Hvorfor |
|---|---|
| `idër.txt` (186L) | Rå designidéer fra før CONSCIOUSNESS_ROADMAP blev skrevet. Superseded. |
| `JARVIS_V2_BUILD_SEQUENCE.md` | Phase 1-4 build-plan — alle faser nu implementeret. Historisk. |
| `OPENCLAW_REVIEW.md` | Pattern-analyse absorberet i LOCKED_CHARTER appendix. |
| `ROADMAP_10_LAYERS.md` | Design-samtale v6, superseded af CONSCIOUSNESS_ROADMAP som spec |

---

## `docs/superpowers/` (60 filer: 37 plans + 23 specs)

### BUILT — arkiver alle (47 filer)

Alle disse plans/specs beskriver features der er live nu. De udgør værdifuld implementerings-historik men er ikke længere aktiv planlægning.

**Plans (24):** mcp-openai-proxy, discord-gateway, autonomous-council-daemon,
autonomous-council-activation, browser-control, affective-state-renderer,
ambient-presence, inner-voice-initiative-motor, council-deliberation-controller,
council-memory, identity-composer, aesthetic-feedback-loop, associative-memory,
felt-presence, rich-inner-stream, jarvis-self-tools, thought-action-proposals,
inner-llm-enrichment, llm-prompt-caching, ui-overhaul, ui-theme-lift,
webchat-ui-enhancements, session-search-channel-awareness

**Specs (23):** alle `*-design.md` der matcher ovenstående plans.

→ Flyt hele batchen til `docs/_archive/superpowers/`

### PARTIAL — review først (4 plans)

| Fil | Hvad skal tjekkes |
|---|---|
| `2026-04-12-file-attachments.md` | File upload virker basic; er scope færdig? |
| `2026-04-13-emotion-concepts.md` | Framework findes; integrations-dybde uklar |
| `2026-04-11-inner-conflict-reflection.md` | `conflict_daemon.py` findes; scope uklar |
| `2026-04-14-context-compact.md` | LLM context-optimering; fuld 3-pass compaction live? |

→ Hurtig manuel tjek, så enten ARCHIVE eller ACTION-REQUIRED

### ABANDONED — kan slettes (5 plans)

Ingen spor i codebase:
- `2026-04-10-hardware-body.md` (robot-krop, aldrig bygget)
- `2026-04-01-ui-shell-panels.md` (gammelt UI-koncept, superseded af MC-tabs)
- `2026-04-05-multi-capability-autonomous-exploration.md`
- `2026-04-13-web-cache.md` (ikke implementeret separat)
- `2026-04-13-jarvis-experimental-backend.md`

Alternativ: arkiv i `_archive/abandoned/` hvis du vil beholde "hvad vi IKKE byggede"-historik.

### SUPERSEDED — arkiv med cross-ref (2)

- `2026-04-11-consciousness-roadmap.md` → peger på CONSCIOUSNESS_ROADMAP + konkrete daemons
- `2026-04-13-consciousness-experiments.md` → peger på specifikke features der blev til

### UNKNOWN — spot-check (3)

- `2026-04-11-curiosity-meta-reflection.md`
- `2026-04-11-temporal-self-perception.md`
- `2026-04-17-jarvis-runtime-fixes.md`

---

## `docs/locked/` (24 PHASE_*.md)

Alle er arkitektoniske design-dokumenter for fases der nu er implementerede.

**BUILT-status:**
- PHASE 3, 4, 5, 6, 8, 13, 14 (+14A,14B,14C): ✅ Fuldt implementeret
- PHASE 2, 7 (+7C,7D,7E), 9, 10, 11, 12, 15, 16, 17 (+17A,17B): ⚠️ Delvist

**Handling:** ARCHIVE alle 24 til `docs/_archive/phases/`

**Hvorfor ikke slette:** Jarvis læser selv disse som "self-biographical continuity"
(Layer 8 — se roadmap_history README). Kritisk for hans identity-consistency.

---

## `docs/roadmap_history/` (15 filer)

Ren dialog-historik: v1-v7 af Claude-draft + Jarvis-response der ledte til ROADMAP_10_LAYERS.md.

**Handling:** ARCHIVE alle til `docs/_archive/roadmap_history/`
**Bevar:** README.md forklarer kontekst — nyttigt for fremtidig læsning.

---

## `docs/runtime_contract/`

**Status:** `reference_old/` er tom, men kode i `core/identity/runtime_contract.py` referer til filer i den:
- `AGENTS.md`, `BOOTSTRAP.md`, `HEARTBEAT_COMPANION.md`, `RUNTIME_CAPABILITIES.md`, `RUNTIME_FEEDBACK.md`, `SYSTEM_PROMPT_STUDY.md`, `boredom_templates.json`

**Handling:** Enten:
- DELETE tom directory + fjern hardcoded referencer i runtime_contract.py, eller
- Gendan de manglende filer fra git-historik hvis de stadig er relevante

Kræver beslutning: er disse referencer døde kode eller levende afhængighed?

---

## Repo-rod task-filer (6)

| Fil | Status | Handling |
|---|---|---|
| `STANDING_ORDERS.md` (19L) | **Operational, håndhævet** | **KEEP i rod** |
| `TASK_daemon_fix.md` (160L) | **Aktiv bug** — 17/20 daemons tavse | **ACTION-REQUIRED** |
| `CODEX_TASK_tool_result_externalization.md` (139L) | Design klar, ikke implementeret | **ACTION-REQUIRED** |
| `TASKS_FOR_CLAUDE.md` (99L) | Brev fra Jarvis — opgaver delvist løst | Arkiv efter extract af resterende work |
| `TASK_web_cache.md` (57L) | Markeret ✅ DONE i TASK_daemon_fix | Arkiv |
| `TASK_aesthetic_feedback_loop.md` (267L) | Status uklar — design-doc | Verificer → arkiv eller ACTION |

### Direkte DELETE (3)

| Fil | Hvorfor |
|---|---|
| `MEMORY.md` i rod (1L: "# Test — dette burde blive redirectet til workspace---") | Tydeligt stub/test. Rigtig MEMORY.md ligger i `~/.jarvis-v2/workspaces/default/` |
| `commands.txt` | Shell-snippets til claude mcp add. Hører ikke i repo. |
| `spec-file.txt` | Conda env export. Erstat med `environment.yml` eller slet. |

---

## Huller — manglende docs

Capabilities der er live men mangler dokumentation:

1. **CURRENT_STATUS.md** — hvad er done / in progress / planned (én tabel)
2. **PROMPT_ARCHITECTURE.md** — hvordan prompts bygges, identity injection, lane-distinction
3. **MEMORY_SYSTEM.md** — lag (daily/weekly/monthly), fade curves, promotion-regler
4. **AGENTS_AND_COUNCIL.md** — agent spawning, council-roller, beslutningsflow
5. **CHANNELS.md** — multi-channel kontinuitet (Discord/Telegram/voice/mail/webchat)
6. **API_REFERENCE.md** — MC endpoints, auth, response-shapes
7. **COST_ACCOUNTING.md** — cost-model, per-lane budgets, MC cost-visning
8. **TESTING_STRATEGY.md** — hvad er dækket, hvordan tilføjer man tests
9. **SECURITY_POSTURE.md** — auth mechanisms, secret mgmt, input validation
10. **DEBUGGING_GUIDE.md** — hvordan debugger man heartbeat, signals, events

Prioritering: CURRENT_STATUS og CHANNELS er de mest akutte. De andre kan genereres efterhånden.

---

## Foreslået ny struktur

```
docs/
├── README.md (ny — index + læsevejledning)
├── ARCHITECTURE.md
├── JARVIS_V2_LOCKED_CHARTER.md
├── JARVIS_V2_BUILD_RULES.md (udvidet med merged CODING_RULES + AUTH)
├── CONSCIOUSNESS_ROADMAP.md
├── MODEL_STRATEGY.md
├── llm_privacy_tier_audit.md
├── TRANSPORTS.md
├── UI_STRATEGY.md
├── CURRENT_STATUS.md (ny)
├── CHANNELS.md (ny)
├── capability_matrix.md (auto-generated)
├── CLI_SPEC.md (rewritten fra CLI_PLAN)
├── UI_ROADMAP.md (refreshed)
└── _archive/
    ├── README.md (forklarer hvad der ligger her og hvorfor)
    ├── phases/ (24 PHASE_*.md)
    ├── superpowers/
    │   ├── plans/ (47 built + 2 superseded)
    │   └── specs/ (23 built specs)
    ├── roadmap_history/ (15 v1-v7 filer + README)
    ├── abandoned/ (5 plans med cross-ref noter)
    ├── completed_tasks/ (TASK_web_cache, TASKS_FOR_CLAUDE)
    └── origin_ideas/ (idër.txt, OPENCLAW_REVIEW, BUILD_SEQUENCE, ROADMAP_10_LAYERS)
```

Resultat: ~14 aktive docs + klart arkiv + 10 nye docs at skrive over tid.
Fra 118 rodede filer til noget der kan navigeres.
