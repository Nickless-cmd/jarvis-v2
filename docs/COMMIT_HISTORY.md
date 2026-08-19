# Jarvis V2 — komplet commit-historie

**4,976 commits** fra 2026-03-20 til 2026-08-19 · 6 måneder · genereret af `scripts/commit_history_report.py`

Formål: finde systemer der blev bygget og siden ligger stille. Se **[Fødsels-indekset](#fødsels-indeks--nye-systemer-i-coreservices)** nederst — det er dér man leder først.

## Fordeling

| Type | Antal | Andel |
|---|---:|---:|
| Nyt (`feat`) | 1,975 | 40% |
| Rettelser (`fix`) | 961 | 19% |
| Omstrukturering (`refactor`) | 118 | 2% |
| Ydelse (`perf`) | 68 | 1% |
| Tests (`test`) | 65 | 1% |
| Dokumentation (`docs`) | 491 | 10% |
| Vedligehold (`chore`) | 83 | 2% |
| Formatering (`style`) | 13 | 0% |
| Build (`build`) | 5 | 0% |
| CI (`ci`) | 2 | 0% |
| Tilbagerulning (`revert`) | 3 | 0% |
| Uden type-præfiks (`andet`) | 1,192 | 24% |

| Forfatter | Commits |
|---|---:|
| Nickless | 4,854 |
| Claude | 54 |
| Jarvis | 42 |
| Nickless-cmd | 13 |
| Windows-side Claude | 13 |

## Indhold

- [Marts 2026](#marts-2026) — 485 commits
- [April 2026](#april-2026) — 1,264 commits
- [Maj 2026](#maj-2026) — 906 commits
- [Juni 2026](#juni-2026) — 1,118 commits
- [Juli 2026](#juli-2026) — 1,158 commits
- [August 2026](#august-2026) — 45 commits
- [Fødsels-indeks](#fødsels-indeks--nye-systemer-i-coreservices)

---

## Marts 2026

*485 commits · 2026-03-20 → 2026-03-31*

### Uge 12 · 16.–22. marts — 190 commits

**Øvrigt**

- `eb6433a3` 2026-03-20 — Initialize Jarvis V2 charter and foundation docs
- `bbab2e3d` 2026-03-20 — Create Jarvis V2 core package skeleton
- `703adab0` 2026-03-20 — Add runtime path config and initial event type
- `cd47a67d` 2026-03-20 — Add Phase 1 implementation todo
- `d5172b62` 2026-03-20 — Expand Jarvis V2 blueprint with OpenClaw parity, UI, auth and transport rules
- `a3e452c8` 2026-03-20 — Add Phase 1 runtime, CLI, API, eventbus and UI shell skeleton
- `61a55087` 2026-03-20 — Add live eventbus subscriptions and lock frontend dependencies
- `094f711b` 2026-03-20 — Add Phase 1 config authority layer
- `97546d59` 2026-03-20 — Strengthen Phase 1 eventbus backbone
- `ada242ed` 2026-03-20 — Add Phase 1 token and cost telemetry skeleton
- `9c1a39fa` 2026-03-20 — Add Phase 1 auth profile skeleton
- `57703ec0` 2026-03-20 — Expand Phase 1 CLI control surface
- `32cd4b5a` 2026-03-20 — Improve Phase 1 Mission Control API skeleton
- `c859ea1b` 2026-03-20 — Add Phase 1 primary webchat shell
- `f4294616` 2026-03-20 — Establish Phase 1 transport split for chat and control-plane
- `3bc80014` 2026-03-20 — Strengthen Phase 1 workspace bootstrap
- `bd10c9ac` 2026-03-20 — Add Phase 1 visible chat execution boundary
- `77d0e5d3` 2026-03-20 — Connect Phase 1 webchat shell to visible chat stream
- `21aca3d1` 2026-03-20 — Connect Phase 1 webchat activity area to control-plane events
- `879d73e1` 2026-03-20 — Add Phase 1 visible model execution skeleton
- `9f54b87f` 2026-03-20 — Add Phase 1 visible provider and model config authority
- `05b4ff64` 2026-03-20 — Add first provider-backed visible execution path
- `b5ce3e54` 2026-03-20 — Expose Phase 1 visible execution readiness
- `107975e7` 2026-03-20 — Add Phase 1 visible auth profile authority
- `acb7b555` 2026-03-20 — Add Phase 1 visible lane control surface
- `4918346e` 2026-03-20 — Add Phase 1 visible lane control UI
- `8be03c77` 2026-03-20 — Add Phase 1 visible lane control guardrails
- `1744d941` 2026-03-20 — Add Phase 1 live visible execution readiness probe
- `fd1b73b9` 2026-03-20 — Add Phase 1 visible readiness TTL cache
- `5d28331c` 2026-03-20 — Add Phase 1 visible execution cost calculation
- `827dd75c` 2026-03-20 — Add Phase 1 true provider-streamed visible output
- `98d4142d` 2026-03-20 — Add Phase 1 visible run failure semantics
- `05d290ce` 2026-03-20 — Add Phase 1 visible run cancellation primitive
- `41520677` 2026-03-20 — Add Phase 1 visible run cancellation semantics
- `1c933341` 2026-03-20 — Add Phase 1 direct provider abort for visible cancellation
- `e5be94cb` 2026-03-20 — Add Phase 1 active visible run truth surface
- `bd9652d6` 2026-03-20 — Strengthen Phase 1 active visible run metadata
- `82c20927` 2026-03-20 — Expose Phase 1 visible run truth in CLI
- `63d44c27` 2026-03-20 — Strengthen Phase 1 last visible run outcome metadata
- `73109fa1` 2026-03-20 — Strengthen Phase 1 visible run event metadata
- `27492571` 2026-03-20 — Improve Phase 1 visible run event visibility in Mission Control
- `6be5dbf8` 2026-03-20 — Expose Phase 1 visible run recent events in webchat
- `e4f94e12` 2026-03-20 — Refine Phase 1 visible lane truth panel in webchat
- `f8135548` 2026-03-20 — Add Phase 1 visible lane status markers in webchat
- `4a26dffb` 2026-03-20 — Expose Phase 1 visible run cancellation in CLI
- `446dccff` 2026-03-20 — Make CLI visible-run control API-first
- `3d178ecb` 2026-03-20 — Make CLI visible execution overview API-first
- `341dc1b1` 2026-03-20 — Make CLI visible lane inspection API-first
- `6a5f8618` 2026-03-20 — Refine Phase 1 visible lane scanability in CLI
- `46ca1fad` 2026-03-20 — Tighten Phase 1 visible lane fallback shape in CLI
- `f3abf387` 2026-03-20 — Add Phase 1 workspace tools and skills foundation
- `9f9364da` 2026-03-20 — Add Phase 1 workspace capability execution boundary
- `bcbe33c1` 2026-03-20 — Add Phase 1 first runnable workspace capability
- `b922e1cd` 2026-03-20 — Expose Phase 1 runnable workspace capability control surface
- `693f7988` 2026-03-20 — Expose Phase 1 runnable workspace capability in webchat
- `659ef7eb` 2026-03-20 — Add Phase 1 workspace capability invocation truth surface
- `e8195323` 2026-03-20 — Expose Phase 1 capability invocation truth in webchat
- `f0ac1990` 2026-03-20 — Improve Phase 1 capability invocation visibility in Mission Control
- `87bec2db` 2026-03-20 — Make CLI capability invocation inspection API-first
- `2aeca6ee` 2026-03-20 — Make CLI capability invocation API-first
- `b7866ced` 2026-03-20 — Add Phase 1 capability invocation runtime events
- `f959b7b6` 2026-03-20 — Improve Phase 1 capability invocation event visibility in Mission Control
- `1f1d36fb` 2026-03-20 — Expose Phase 1 capability invocation recent events in webchat
- `04c1f2c7` 2026-03-20 — Expose Phase 1 capability invocation recent events in CLI
- `b0c49f45` 2026-03-20 — Add Phase 1 workspace file-read capability
- `33962906` 2026-03-20 — Add Phase 1 visible lane capability invocation boundary
- `cb0a8bd7` 2026-03-20 — Suppress raw visible capability-call marker leakage
- `0dd37997` 2026-03-21 — Add Phase 1 workspace search capability
- `908ae19a` 2026-03-21 — Improve visible rendering for SEARCH_FILE capability
- `43ebc218` 2026-03-21 — Add Phase 1 visible capability-use truth surface
- `6faccd6d` 2026-03-21 — Expose Phase 1 visible capability-use truth in webchat
- `7867ab28` 2026-03-21 — Expose Phase 1 visible capability-use truth in CLI
- `a781f73a` 2026-03-21 — Add Phase 1 workspace identity bridge for visible prompt
- `b9e40c09` 2026-03-21 — Expose Phase 1 visible identity bridge truth surface
- `eac11bf7` 2026-03-21 — Expose Phase 1 visible identity truth in operator surfaces
- `c70e1ba0` 2026-03-21 — Add Phase 1 visible run continuity persistence
- `c6fd4ce0` 2026-03-21 — Expose Phase 1 persisted visible run continuity
- `e39aa414` 2026-03-21 — Expose Phase 1 persisted visible run continuity in webchat
- `55eaf472` 2026-03-21 — Expose Phase 1 persisted visible run continuity in CLI
- `854c043b` 2026-03-21 — Add Phase 1 capability invocation continuity persistence
- `b36e7c33` 2026-03-21 — Expose Phase 1 persisted capability invocation continuity
- `8aecff0d` 2026-03-21 — Expose Phase 1 persisted capability invocation continuity in webchat
- `1d9be464` 2026-03-21 — Expose Phase 1 persisted capability invocation continuity in CLI
- `9d1e78e7` 2026-03-21 — Add Phase 1 continuity bridge for visible prompt
- `6891a305` 2026-03-21 — Expose Phase 1 visible continuity bridge truth surface
- `fc27fed7` 2026-03-21 — Expose Phase 1 visible continuity truth in operator surfaces
- `a0ee6470` 2026-03-21 — Add Phase 1 capability continuity bridge for visible prompt
- `df37a8ab` 2026-03-21 — Expose Phase 1 visible capability continuity truth surface
- `8f3c453d` 2026-03-21 — Expose Phase 1 visible capability continuity truth in operator surfaces
- `6b2ec51f` 2026-03-21 — Add Phase 1 visible session continuity contract
- `7a354469` 2026-03-21 — Expose Phase 1 visible session continuity in operator surfaces
- `e8b91e35` 2026-03-21 — Add Phase 1 capability approval baseline
- `8bde92d9` 2026-03-21 — Expose Phase 1 capability approval truth surface
- `597910b6` 2026-03-21 — Expose Phase 1 capability approval truth in operator surfaces
- `3223ddff` 2026-03-21 — Add Phase 1 capability approval request persistence
- `3e5013ee` 2026-03-21 — Expose Phase 1 approval requests in operator surfaces
- `4dc814d7` 2026-03-21 — Add Phase 1 capability approval fulfillment baseline
- `8dbc4fbc` 2026-03-21 — Expose Phase 1 approval fulfillment in operator surfaces
- `6745d036` 2026-03-21 — Add Phase 1 execute approved capability request path
- `05c53474` 2026-03-21 — Expose Phase 1 execute approved request in operator surfaces
- `442277cb` 2026-03-21 — Add Phase 1 approval request execution projection
- `40c3b06e` 2026-03-21 — Add Phase 1 visible work contract
- `973bab0e` 2026-03-21 — Expose Phase 1 visible work in operator surfaces
- `2c80bfdb` 2026-03-21 — Add Phase 1 persisted visible work unit
- `a67de3ff` 2026-03-21 — Expose Phase 1 persisted visible work in operator surfaces
- `944662a8` 2026-03-21 — Add Phase 1 visible work surface projection
- `1250f495` 2026-03-21 — Expose Phase 1 visible work surface in operator surfaces
- `c53b5be1` 2026-03-21 — Add Phase 1 explicit work surface
- `460f3ebb` 2026-03-21 — Expose Phase 1 visible selected work surface in operator surfaces
- `dd6762c4` 2026-03-21 — Add Phase 1 bounded work artifact bridge
- `de292075` 2026-03-21 — Expose Phase 1 visible selected work item in operator surfaces
- `ec170519` 2026-03-21 — Add Phase 1 work-aware bridge for visible prompt
- `ff928bc1` 2026-03-21 — Add Phase 1 bounded work note surface
- `6e9ae944` 2026-03-21 — Expose Phase 1 persisted visible work notes in operator surfaces
- `3d5866d8` 2026-03-21 — Add Phase 1 selected work note surface
- `eb554b1d` 2026-03-21 — Add Phase 1 private inner-layer scaffold
- `93e5f3bc` 2026-03-21 — Strengthen Phase 1 private inner-layer signal structure
- `8316c07c` 2026-03-21 — Add Phase 1 private-to-visible support signal bridge
- `7058f62a` 2026-03-21 — Add Phase 1 private developmental growth contract
- `d3879cc4` 2026-03-21 — Add Phase 1 growth-to-visible support signal bridge
- `17dc2346` 2026-03-21 — Add Phase 1 private self-model scaffold
- `e7fa61fe` 2026-03-21 — Add Phase 1 self-model-to-visible support signal bridge
- `887adc9a` 2026-03-21 — Add Phase 1 private reflective selection contract
- `df96a4ce` 2026-03-21 — Add Phase 1 private developmental consolidation contract
- `7becabe4` 2026-03-21 — Add Phase 1 private state contract
- `9af28244` 2026-03-21 — Add Phase 1 protected inner voice channel
- `46ab500c` 2026-03-21 — Add Phase 1 temporal rhythm and memory promotion foundation
- `ea85ecee` 2026-03-21 — Extract Phase 1 private-layer terminal write orchestration
- `cacdd738` 2026-03-21 — Add Phase 1 promotion decision projection
- `63edaa23` 2026-03-21 — Add Phase 1 retained memory promotion record
- `70b3e737` 2026-03-21 — Add Phase 1 retained memory ledger
- `a2041c96` 2026-03-21 — Add Phase 1 retained memory projection layer
- `35cfd319` 2026-03-21 — Add Phase 1 retained-memory-to-visible support signal bridge
- `f40f100f` 2026-03-21 — Add Phase 1 temporal-to-visible support signal bridge
- `37df1791` 2026-03-21 — Add Phase 1 private inner interplay projection
- `a5e74ff8` 2026-03-21 — Refine Phase 1 protected inner voice from private state
- `58f860ec` 2026-03-21 — Refine Phase 1 development-state-inner-voice coupling
- `1ec505af` 2026-03-21 — Add Phase 1 private initiative tension model
- `61e4dbb2` 2026-03-21 — Add Phase 1 retention horizon distinction
- `6277f0f7` 2026-03-21 — Add Phase 1 temporal curiosity maturation
- `6ade968e` 2026-03-21 — Refine Phase 1 initiative tension from temporal curiosity state
- `dc42f153` 2026-03-21 — Add Phase 1 bounded relation state foundation
- `8f7073f1` 2026-03-21 — Add Phase 1 provider router auth foundation
- `99f9e527` 2026-03-21 — Add Phase 1 provider registry read path
- `19eef284` 2026-03-21 — Add Phase 1 non-visible lane execution consumer
- `bfc893b7` 2026-03-21 — Add Phase 1 cheap lane provider transport expansion
- `0a5eaef0` 2026-03-21 — Add Phase 1 coding lane execution foundation
- `b5b96988` 2026-03-21 — Refine Phase 1 coding lane auth readiness
- `00a78fbf` 2026-03-21 — Add Phase 1 OpenAI Codex coding auth slice
- `01f8c3fa` 2026-03-21 — Add Phase 1 coding lane CLI affordance
- `54941ac8` 2026-03-21 — Add Phase 1 coding lane readiness probe
- `7a02d565` 2026-03-21 — Add Phase 1 coding lane status affordance
- `c2298698` 2026-03-21 — Add Phase 1 operational advisory bridge
- `0ebe190e` 2026-03-21 — Add Phase 1 operational preference alignment truth
- `cbae9592` 2026-03-21 — Add Phase 1 operational recommended action label
- `0dd4d97f` 2026-03-21 — Add Phase 1 GitHub Copilot auth groundwork
- `dd454cb3` 2026-03-21 — Add Phase 1 GitHub Copilot coding lane CLI affordance
- `ecef505f` 2026-03-21 — Add Phase 1 main agent provider target foundation
- `867b7794` 2026-03-21 — Refine Phase 1 GitHub Copilot auth state
- `7b6df607` 2026-03-21 — Refine Phase 1 Ollama local lane
- `ca65c09e` 2026-03-21 — Add Phase 1 main agent selection surface
- `6b7db352` 2026-03-21 — Add Phase 1 main agent selection mutation path
- `b8c09dbb` 2026-03-21 — Add Phase 1 main agent selection guard
- `1a95eb91` 2026-03-21 — Add Phase 1 main agent readiness hints
- `d1a285c7` 2026-03-21 — Refine Phase 1 GitHub Copilot auth usability
- `2472b69b` 2026-03-21 — Add Phase 1 GitHub Copilot auth state helper
- `ce96bdc5` 2026-03-21 — Refine Phase 1 GitHub Copilot auth visibility
- `d09376c0` 2026-03-21 — Refine Phase 1 raw auth profile visibility
- `516e3901` 2026-03-21 — Fix Phase 1 webchat runtime connectivity and authority usability
- `c93d09ff` 2026-03-21 — Refine Phase 1 webchat shell toward chat-first MC-aligned layout
- `55e4b420` 2026-03-21 — Refine Phase 1 webchat support surface compression
- `ac9c8311` 2026-03-21 — Refine Phase 1 GitHub Copilot auth state progression
- `b88dfd52` 2026-03-21 — Refine Phase 1 GitHub Copilot OAuth placeholder progression
- `3590714b` 2026-03-21 — Add Phase 1 GitHub Copilot OAuth handshake stub
- `0f83cb61` 2026-03-21 — Add Phase 1 GitHub Copilot OAuth launch stub
- `fc2d8b46` 2026-03-22 — Add Phase 1 GitHub Copilot OAuth launch intent helper
- `da9cdd63` 2026-03-22 — Add Phase 1 GitHub Copilot OAuth browser launch stub
- `275ef555` 2026-03-22 — Refine Phase 1 GitHub Copilot launch truth
- `27b0193c` 2026-03-22 — Refine Phase 1 GitHub Copilot launch operation helper
- `9a47c3ee` 2026-03-22 — Add Phase 1 GitHub Copilot callback intake stub
- `6bf8961f` 2026-03-22 — Refine Phase 1 GitHub Copilot callback validation truth
- `11cb463c` 2026-03-22 — Refine Phase 1 GitHub Copilot exchange readiness truth
- `3fd57525` 2026-03-22 — Refine Phase 1 GitHub Copilot callback intent consistency truth
- `5c68a350` 2026-03-22 — Wire unified UI in apps/ui to backend truth
- `6e7fcb31` 2026-03-22 — Recover unified UI and Ollama local lane usability
- `fd88b1b9` 2026-03-22 — Fix visible chat execution for Ollama main agent
- `1dcef8c2` 2026-03-22 — Fix visible Ollama stream response handling
- `9fa48ef9` 2026-03-22 — Refine unified chat UX, streaming, and Ollama model selection
- `728b1226` 2026-03-22 — Add chat session persistence and app-like layout behavior
- `bc47b558` 2026-03-22 — Tune visible local-model chat behavior for Ollama

### Uge 13 · 23.–29. marts — 224 commits

**Øvrigt**

- `3d85e395` 2026-03-24 — Implement Phase A Mission Control architecture
- `1ebc60c3` 2026-03-24 — Refine Mission Control Phase A UX and interaction quality
- `37b24c20` 2026-03-24 — Refine unified UI fidelity toward old UI layout and feel
- `091cef9c` 2026-03-24 — Polish unified chat UI micro-fidelity
- `fddf109d` 2026-03-24 — Implement Mission Control Phase B Jarvis tab
- `79ea3017` 2026-03-24 — Add runtime contract-state metadata and MC visibility
- `8105a12e` 2026-03-24 — Implement mode-specific prompt assembly loaders
- `0fd0d542` 2026-03-24 — Add governed preference and memory candidate tracking
- `ff7fd6b4` 2026-03-24 — Implement governed USER and MEMORY write workflow
- `bec55cfd` 2026-03-24 — Implement bounded heartbeat runtime
- `6606bcb5` 2026-03-24 — Implement minimal heartbeat scheduler and due-state
- `905fdf45` 2026-03-24 — Add tiny bounded heartbeat execute actions
- `9abf4c8c` 2026-03-24 — Refine governed candidate evidence and dedupe quality
- `e1db6c5a` 2026-03-24 — Harden heartbeat scheduler persistence and recovery
- `00db9e0d` 2026-03-24 — Add bounded guided learning and development focus signals
- `f2955809` 2026-03-24 — Add CLAUDE.md for Claude Code guidance
- `c0566aba` 2026-03-24 — Implement bounded development focus status workflow
- `c6d527a4` 2026-03-24 — Add tiny manual development focus action
- `b67269cb` 2026-03-24 — Polish Mission Control Jarvis tab evidence readability
- `eccb68d0` 2026-03-24 — Clean up tools and capabilities contract authority
- `883f5c8c` 2026-03-24 — Add bounded reflective critic signals
- `e7f09eac` 2026-03-24 — Refine reflective critic resolution and lifecycle polish
- `a5872e3e` 2026-03-24 — Add bounded world-model signals
- `be22aaf2` 2026-03-25 — Refine world-model correction and lifecycle polish
- `35e5dbda` 2026-03-25 — Add bounded self-model signals
- `640acf7c` 2026-03-25 — Refine self-model correction and lifecycle polish
- `9c8c1def` 2026-03-25 — Add bounded goal signals
- `537dfe73` 2026-03-25 — Refine goal signal lifecycle and readability
- `00f69bf9` 2026-03-25 — Add bounded hardware and runtime awareness signals
- `82265b1e` 2026-03-25 — Add bounded dream and reflection signals
- `ad3f46d2` 2026-03-25 — Bridge reflection support into visible model input
- `8e464d83` 2026-03-25 — Add reflection history surface to Mission Control
- `11462c7d` 2026-03-25 — Add targeted tests for reflection signals and prompt bridge
- `99e7d109` 2026-03-25 — Polish Development surface in Mission Control
- `91abdc53` 2026-03-25 — Improve runtime awareness signals and Mission Control surface
- `24c9a8f9` 2026-03-25 — Improve continuity surface in Mission Control
- `bbe0d82b` 2026-03-25 — Polish goal surface in Mission Control
- `aa92217d` 2026-03-25 — Bridge world-model support into visible model input
- `bf1714f2` 2026-03-25 — Add targeted tests for world-model and support signal bridges
- `fd9228b3` 2026-03-25 — Polish self-model surface in Mission Control
- `21ebd825` 2026-03-25 — Polish world-model surface in Mission Control
- `fe9c1fe3` 2026-03-25 — Polish reflective critic surface in Mission Control
- `cc61d97c` 2026-03-25 — Add Development snapshot to Mission Control
- `f0d93eea` 2026-03-25 — Bridge goal support into visible model input
- `155e184e` 2026-03-25 — Add targeted tests for goal and support signal bridges
- `542cc82c` 2026-03-25 — Polish reflection and continuity relationship in Mission Control
- `285f143c` 2026-03-25 — Bridge runtime awareness support into visible model input
- `0e24cc24` 2026-03-25 — Add targeted tests for runtime awareness and support signal bridges
- `a216e7c4` 2026-03-25 — Bridge development focus support into visible model input
- `017f37e7` 2026-03-25 — Add bounded temporal recurrence signals
- `18d43410` 2026-03-25 — Add targeted tests for temporal recurrence signals
- `d08300ca` 2026-03-25 — Add bounded chronicle witness signals
- `0f1fa252` 2026-03-26 — Add targeted tests for witness signals
- `9686ffe2` 2026-03-26 — Add locked Phase 2 plan for opposition loops and self-review
- `e5020703` 2026-03-26 — Add bounded open loop signals
- `d60cfd4d` 2026-03-26 — Add targeted tests for open loop signals
- `8f2465c2` 2026-03-26 — Add bounded closure readiness to open loop signals
- `fac5bc58` 2026-03-26 — Add targeted tests for open loop closure readiness
- `decc5bd5` 2026-03-26 — Add bounded internal opposition signals
- `0ef2895e` 2026-03-26 — Add targeted tests for internal opposition signals
- `2fa04ab0` 2026-03-26 — Add bounded self review signals
- `3c918204` 2026-03-26 — Add targeted tests for self review signals
- `12efd756` 2026-03-26 — Add bounded self review records
- `b9267197` 2026-03-26 — Add targeted tests for self review records
- `bffcd923` 2026-03-26 — Add bounded self review runs
- `fb09f967` 2026-03-27 — Add targeted tests for self review runs
- `fe81e544` 2026-03-27 — Add bounded self review outcomes
- `678cb3a6` 2026-03-27 — Polish self review lane in Mission Control
- `e11609f9` 2026-03-27 — Add bounded self review cadence signals
- `dae1e1a7` 2026-03-27 — Add bounded loop closure proposals
- `0c77b61f` 2026-03-27 — Add bounded dream hypothesis signals
- `213d41bb` 2026-03-27 — Add bounded dream adoption candidates
- `f35598ed` 2026-03-27 — Add bounded dream influence proposals
- `bdf300a2` 2026-03-27 — Add bounded self authored prompt proposals
- `f7ae7366` 2026-03-27 — Add bounded USER.md update proposals
- `fb6cf76f` 2026-03-27 — Add bounded USER.md candidate drafting
- `37f1236c` 2026-03-27 — Add bounded prompt candidate drafting
- `9dcc43d6` 2026-03-27 — Refine candidate taxonomy for USER.md and prompt drafts
- `ad4d0ba1` 2026-03-27 — Add bounded candidate apply readiness
- `989b69c4` 2026-03-27 — Add bounded auto apply for safe USER.md candidates
- `49426edf` 2026-03-27 — Add bounded selfhood proposals
- `6e858f53` 2026-03-27 — Add bounded canonical self candidate drafting
- `883ea054` 2026-03-27 — Add explicit approval apply for canonical self candidates
- `f9712006` 2026-03-27 — Polish canonical self approval UX in Mission Control
- `4ae0ee44` 2026-03-27 — Add bounded user understanding signals
- `3c087aba` 2026-03-27 — Split phase 1 responsibilities out of scripts/jarvis.py
- `5e724916` 2026-03-27 — Split phase 2 auth responsibilities out of scripts/jarvis.py
- `88f9eec8` 2026-03-27 — Refactor chat UI layout - remove frames, add floating composer
- `8eb05780` 2026-03-27 — Split phase 3 config responsibilities out of scripts/jarvis.py
- `333bbbb0` 2026-03-27 — Fix chat composer positioning and style right panel like sidebar
- `890b76c5` 2026-03-27 — Split phase 4 capability responsibilities out of scripts/jarvis.py
- `0dea07ce` 2026-03-27 — Tighten chat layout - smaller composer, tighter bubbles, unified panel styles
- `9c81f9e1` 2026-03-27 — Fix header full-width and tighten composer height
- `7e185b41` 2026-03-27 — Widen composer to 840px
- `dea3196a` 2026-03-27 — Center chat view to match composer width
- `3ca86b8a` 2026-03-27 — Hide scrollbars and align chat view width with composer
- `ad6b2a02` 2026-03-27 — Normalize phase 1 Ollama prompt path
- `e62537f1` 2026-03-27 — Implement GitHub auth reality phase 1
- `9b055d88` 2026-03-27 — Widen chat to 880px, remove bubble from Jarvis responses, add separator line
- `1c12e225` 2026-03-27 — Fix Ollama visible prompt role-boundary regression
- `234e98eb` 2026-03-27 — Normalize phase 2 Ollama prompt path
- `e371e637` 2026-03-27 — Move separator line below name and timestamp
- `392f474e` 2026-03-27 — Stabilize Ollama visible conversation recall and memory alignment
- `864e4c60` 2026-03-27 — Externalize phase 1 local-model prompt rules
- `1847a4b6` 2026-03-27 — Externalize phase 2 visible prompt rules
- `3e022fa8` 2026-03-27 — Style MC header to match chat header
- `35dba0e6` 2026-03-27 — Simplify MC header - remove title and description
- `80cd6228` 2026-03-27 — Style MC tabbar to match header - transparent background, border bottom
- `456f10d3` 2026-03-27 — Increase MC tabbar height so tabs are visible without scroll
- `5081df66` 2026-03-27 — Rewire USER.md proposals onto user understanding signals
- `cc13d55e` 2026-03-27 — Add bounded MEMORY.md update proposals
- `11580960` 2026-03-27 — Add bounded MEMORY.md candidate drafting
- `584b83c8` 2026-03-28 — Add bounded MEMORY.md apply readiness
- `6afc074f` 2026-03-28 — Add bounded auto apply for safe MEMORY.md candidates
- `84e82a3c` 2026-03-28 — Add bounded remembered fact signals
- `87c82b43` 2026-03-28 — Extend MEMORY.md proposals with remembered facts
- `f67ebd57` 2026-03-28 — Refine MEMORY.md readiness for remembered facts
- `74226cd1` 2026-03-28 — Add bounded auto apply for safe remembered facts
- `ae87c0c4` 2026-03-28 — Tighten visible MEMORY read path
- `bb1c22d0` 2026-03-28 — Add locked plan for NL memory relevance and prompt de-hardcoding
- `b6cecce7` 2026-03-28 — Add bounded relevance interface for visible prompt gating
- `7e690522` 2026-03-28 — Implement bounded NL relevance phase 1
- `d4538582` 2026-03-28 — Harden bounded NL relevance phase 1
- `5e2a2aaf` 2026-03-28 — Extend bounded NL relevance to heartbeat and future-agent
- `1518ec92` 2026-03-28 — Add bounded relevance observability
- `88fb46a0` 2026-03-28 — Implement bounded NL MEMORY selection phase 1
- `66410fff` 2026-03-28 — Extend bounded NL MEMORY selection to heartbeat and future-agent
- `9c22a3f9` 2026-03-28 — Add bounded MEMORY selection observability
- `64e94fa4` 2026-03-28 — Add locked plan for bounded inner layer return
- `4cc6a908` 2026-03-28 — Add bounded private inner note runtime layer
- `1bdb8363` 2026-03-28 — Add bounded private initiative tension runtime layer
- `3cb914d2` 2026-03-28 — Fix heartbeat model resolution and observability
- `f71d87a4` 2026-03-28 — Fix heartbeat runtime model source and execution path
- `e245ecec` 2026-03-28 — Add bounded private inner interplay runtime layer
- `d40486f2` 2026-03-28 — Add bounded private state runtime snapshot layer
- `1b22259b` 2026-03-28 — Add bounded temporal curiosity runtime layer
- `0acd373a` 2026-03-28 — Add bounded temporal promotion runtime layer
- `8fca8b44` 2026-03-28 — Add locked plan for bounded inner visible bridge
- `7e2e63b3` 2026-03-28 — Add bounded inner visible support runtime layer
- `b853271a` 2026-03-28 — Add locked brain-inspired functional architecture plan
- `88c8580b` 2026-03-28 — Add bounded executive contradiction runtime layer
- `f4116b9d` 2026-03-28 — Add bounded inner visible support runtime layer
- `a020c209` 2026-03-28 — Add bounded inner visible prompt bridge
- `b0ec1f6e` 2026-03-28 — updated info..
- `83f88a9e` 2026-03-28 — Add bounded chronicle consolidation runtime layer
- `eb17fcee` 2026-03-28 — Add bounded chronicle consolidation brief layer
- `52dbfb2e` 2026-03-28 — Add bounded chronicle consolidation proposal layer
- `a742729f` 2026-03-28 — Add bounded chronicle candidate drafting
- `018e7d90` 2026-03-28 — Add bounded chronicle apply gate
- `8053222c` 2026-03-28 — Polish bounded chronicle materialization
- `da4eab1b` 2026-03-28 — Add bounded regulation homeostasis runtime layer
- `6a7b25cd` 2026-03-28 — Add bounded relation state runtime layer
- `b1abfd92` 2026-03-28 — Add bounded relation continuity runtime layer
- `df5d1ac3` 2026-03-28 — Add bounded meaning significance runtime layer
- `f295f306` 2026-03-28 — Add bounded temperament runtime layer
- `3279d963` 2026-03-28 — Add bounded self narrative runtime layer
- `bd227456` 2026-03-28 — Add locked plan for self narrative self model review bridge
- `46db0cf4` 2026-03-28 — Add bounded self narrative review bridge surface
- `a1632202` 2026-03-28 — Add bounded self narrative pattern summaries
- `6f8c8cd5` 2026-03-28 — Add locked plan for self narrative review input gate
- `844670d9` 2026-03-28 — Add bounded self narrative review input gate
- `977a818b` 2026-03-28 — Add locked plan for self model sharpening input gate
- `9088d795` 2026-03-28 — Add Phase 7d self-model sharpening input gate
- `3e151210` 2026-03-28 — Add bounded self model sharpening input gate
- `c7639a3c` 2026-03-28 — Add locked plan for selfhood proposal input gate
- `670da693` 2026-03-28 — Add bounded selfhood proposal input gate
- `4c9199bc` 2026-03-28 — Add locked plan for inner witness becoming daemon
- `ce3e4abd` 2026-03-28 — Extend bounded witness layer with becoming synthesis
- `b5846310` 2026-03-28 — Add bounded witness maturation markers
- `d9b9be5e` 2026-03-28 — Add bounded witness persistence signals
- `b51725c4` 2026-03-28 — Add locked plan for identity metabolism and selective forgetting
- `428489de` 2026-03-28 — Add bounded metabolism state runtime layer
- `d9355edd` 2026-03-28 — Add bounded release marker runtime layer
- `1df63876` 2026-03-28 — Add bounded consolidation target runtime layer
- `8aee8431` 2026-03-28 — Add bounded selective forgetting candidate layer
- `1fcb2e0e` 2026-03-28 — Add locked plan for attachment architecture and loyalty gradients
- `122c0fd9` 2026-03-28 — Recover bounded heartbeat liveness foundation
- `e0e96205` 2026-03-28 — Harden private lane source discipline
- `95814925` 2026-03-28 — Refine bounded heartbeat liveness weighting
- `028ac34f` 2026-03-28 — Add bounded attachment topology runtime layer
- `0aa92411` 2026-03-29 — Add bounded loyalty gradient runtime layer
- `a66ebef8` 2026-03-29 — Fix port mismatch in Vite proxy config causing EPIPE error
- `875d1e7c` 2026-03-29 — Instrument heartbeat and Mission Control live diagnostics
- `c403548c` 2026-03-29 — Add bounded heartbeat companion pressure
- `05c3f9c1` 2026-03-29 — Add Jarvis sub-tabs navigation to Mission Control
- `6f796026` 2026-03-29 — Add locked plan for governed autonomy and proactive loops
- `a409c825` 2026-03-29 — Add bounded autonomy pressure runtime layer
- `9f1fc901` 2026-03-29 — Add bounded proactive loop lifecycle layer
- `0e0c277d` 2026-03-29 — Add bounded proactive question gate layer
- `89f334fa` 2026-03-29 — Add locked plan for tiny governed execution pilot
- `db486493` 2026-03-29 — Implement tiny webchat execution pilot
- `4d752020` 2026-03-29 — Integrate life chain across heartbeat and private layer
- `45b2dcf8` 2026-03-29 — Fix heartbeat policy loading for ping settings
- `54e89da8` 2026-03-29 — Audit current runtime execution-candidate path
- `894be2a0` 2026-03-29 — Broaden open-loop materialization for live pressure
- `543e62cb` 2026-03-29 — Re-audit current runtime after open-loop live-pressure fix
- `eaa6bbc6` 2026-03-29 — Materialize live open-loop candidates in current flow
- `06da8706` 2026-03-29 — Recover heartbeat propose from alive-threshold parse failures
- `e97f7b3d` 2026-03-29 — Add locked plan for cognitive and meta-cognitive core
- `40281d0d` 2026-03-29 — Integrate question continuity into proactive gate path
- `f690771f` 2026-03-29 — Add locked plan for diary and inner voice identity formation
- `269a6918` 2026-03-29 — Recover heartbeat ping when gated webchat candidate is ready
- `ef9e987a` 2026-03-29 — Improve focus quality in proactive question path
- `e64c912b` 2026-03-29 — Show proactive webchat messages live without refresh
- `e3f12b3f` 2026-03-29 — Add locked plan for runtime self-knowledge and honest self-reporting
- `fb5f24d9` 2026-03-29 — Ground runtime self-report in visible chat path
- `b2e833c4` 2026-03-29 — Improve runtime self-report consistency and routing
- `7e3f46b7` 2026-03-29 — Add locked plan for language-agnostic runtime self-report routing
- `63a440ab` 2026-03-29 — Add locked plan for diary synthesis
- `642ea4f5` 2026-03-29 — Add locked plan for inner voice tone shift
- `cd045379` 2026-03-29 — Implement bounded inner voice tone framework
- `f3d25e2e` 2026-03-29 — Implement bounded inner voice tone framework
- `60862fdd` 2026-03-29 — Extend bounded inner voice tone shift to tension and interplay
- `d06f6d73` 2026-03-29 — Extend bounded inner voice tone shift to private state
- `97e7796d` 2026-03-29 — Implement bounded diary synthesis runtime layer
- `4c9b8791` 2026-03-29 — Complete diary synthesis runtime integration
- `f38ed5a1` 2026-03-29 — Expose diary synthesis in Mission Control
- `ebf2dd7a` 2026-03-29 — Complete diary synthesis visibility in JarvisTab
- `1d9abd55` 2026-03-29 — Add locked plan for Mission Control IA reset
- `3ac72f99` 2026-03-29 — Add Now section to JarvisTab
- `f91f93c6` 2026-03-29 — Add locked plan for Mission Control shell parity reset
- `9b35714b` 2026-03-29 — Improve Mission Control header shell
- `5b1f953e` 2026-03-29 — Improve Mission Control sidebar shell parity
- `a56021a4` 2026-03-29 — Implement first structural old UI parity pass

### Uge 14 · 30. marts – 5. april — 71 commits

**Øvrigt**

- `077583eb` 2026-03-30 — Add locked plan for MC tab migration map
- `d210db0e` 2026-03-30 — Add locked plan for metabolism to diary release
- `caecf02f` 2026-03-30 — Add locked plan for metabolism to diary release
- `2e0b350e` 2026-03-30 — Implement release-aware diary synthesis
- `1c5f39c9` 2026-03-30 — Complete GitHub Copilot auth reality with dynamic model discovery
- `d98846e6` 2026-03-30 — Implement real GitHub device flow for Copilot auth
- `5ad38479` 2026-03-30 — Fix GitHub device flow endpoint and auth lifecycle
- `593fda4d` 2026-03-30 — Bridge GitHub Copilot into visible execution readiness
- `afc4caea` 2026-03-30 — Fix GitHub Copilot visible execution bad request
- `fe741762` 2026-03-30 — Align GitHub Models visible lane with credential reality
- `16204e67` 2026-03-30 — Fix GitHub Models visible lane model id resolution
- `265a4494` 2026-03-30 — Anchor visible runtime self-report to Jarvis identity
- `e41aa782` 2026-03-30 — Fix GitHub visible prompt payload parity
- `863bc664` 2026-03-30 — Add explicit local-only heartbeat lane pinning
- `dbdbed0a` 2026-03-30 — Translate visible provider rate limits into bounded Jarvis replies
- `a5088510` 2026-03-30 — Add visible GitHub cooldown after rate limits
- `29ab8d6d` 2026-03-30 — Refine release-aware diary synthesis semantics
- `114ae69c` 2026-03-30 — Refine release-aware diary confidence weighting
- `694a5059` 2026-03-30 — Add bounded open loop creation readiness
- `b1718cb1` 2026-03-30 — Materialize bounded open loops from aligned readiness
- `065de9ae` 2026-03-30 — Block ungrounded visible self-action and loop claims
- `328c1eaa` 2026-03-30 — Add bounded open loop closure maturation
- `249b6b71` 2026-03-31 — Compress dead surface in Jarvis tab
- `da24f9e4` 2026-03-31 — Strengthen bounded proactive loop activation
- `2815d923` 2026-03-31 — Promote bounded world model surface in Jarvis tab
- `b85a46b9` 2026-03-31 — Promote bounded USER lifecycle in Jarvis tab
- `9f83ad24` 2026-03-31 — Refine heartbeat liveness with bounded proactive readiness
- `a52dffcf` 2026-03-31 — Merge pull request #1 from Nickless-cmd/claude/goofy-fermat
- `9e7a659f` 2026-03-31 — Refine bounded question-pressure activation
- `15da5444` 2026-03-31 — Compose alive runtime lifecycle in Jarvis tab
- `5ec9afed` 2026-03-31 — Merge pull request #2 from Nickless-cmd/claude/goofy-fermat
- `6b76ca07` 2026-03-31 — Activate bounded loop-closure proposals from maturation evidence
- `f7a077dc` 2026-03-31 — Polish alive runtime visibility in Jarvis tab
- `b5e14c43` 2026-03-31 — Merge pull request #3 from Nickless-cmd/claude/goofy-fermat
- `5448b07f` 2026-03-31 — Stabilize alive runtime surfaces after lifecycle passes
- `1c4cd731` 2026-03-31 — Add smoke coverage for bounded alive-core runtime chain
- `7223c908` 2026-03-31 — Extend smoke coverage for proactive gate seam
- `0d3407fc` 2026-03-31 — Merge pull request #4 from Nickless-cmd/claude/goofy-fermat
- `099131cd` 2026-03-31 — Diagnose mission control websocket forwarding dropouts
- `8ddff167` 2026-03-31 — Merge pull request #5 from Nickless-cmd/claude/goofy-fermat
- `0511a2ae` 2026-03-31 — Establish private brain and workspace memory distillation
- `a5d3d024` 2026-03-31 — Connect private brain into bounded continuity motor
- `3603f119` 2026-03-31 — Wire private brain into bounded heartbeat cognition
- `7a98cbee` 2026-03-31 — Expand bounded runtime self-knowledge and agency map
- `4fbf2232` 2026-03-31 — Add bounded brain lifecycle and self-knowledge influence tracing
- `c225609b` 2026-03-31 — Merge pull request #6 from Nickless-cmd/claude/goofy-fermat
- `2803e517` 2026-03-31 — Establish bounded cognitive conductor and affordance selection
- `e63158a6` 2026-03-31 — Add bounded attention economy and adaptive context budgeting
- `490f189c` 2026-03-31 — Make adaptive attention budgeting authoritative in prompt assembly
- `24a63c05` 2026-03-31 — Expose authoritative attention budgeting trace in Mission Control
- `e0f2a1ba` 2026-03-31 — Show live attention traces in Mission Control Jarvis tab
- `dd78412f` 2026-03-31 — Merge pull request #7 from Nickless-cmd/claude/goofy-fermat
- `f198008e` 2026-03-31 — Add bounded conflict resolution to heartbeat initiative flow
- `ebffd019` 2026-03-31 — Make continue_internal a real bounded heartbeat action
- `33c73f8a` 2026-03-31 — Show heartbeat conflict resolution in Mission Control Jarvis tab
- `0900d808` 2026-03-31 — Add bounded quiet initiative to heartbeat flow
- `b778b4bc` 2026-03-31 — Show quiet initiative in Mission Control Jarvis tab
- `51f4ba77` 2026-03-31 — Add bounded self-deception guard to visible runtime contract
- `5d388a8f` 2026-03-31 — Merge pull request #8 from Nickless-cmd/claude/goofy-fermat
- `263902cd` 2026-03-31 — Show self-deception guard in Mission Control Jarvis tab
- `a15c74f6` 2026-03-31 — Merge pull request #9 from Nickless-cmd/claude/goofy-fermat
- `38b380ac` 2026-03-31 — Add bounded inner witness daemon to heartbeat runtime
- `1773e1d9` 2026-03-31 — Add bounded inner voice daemon to heartbeat runtime
- `7aeb9283` 2026-03-31 — Make inner voice daemon workspace-led and LLM-rendered
- `5762f852` 2026-03-31 — Merge pull request #10 from Nickless-cmd/claude/goofy-fermat
- `0aa1f4d6` 2026-03-31 — Add minimal internal cadence layer for non-visible producers
- `df477819` 2026-03-31 — Merge pull request #12 from Nickless-cmd/claude/brave-elion-cadence
- `63b4c57e` 2026-03-31 — Add bounded runtime self-model to visible self-report
- `3e4da476` 2026-03-31 — Merge pull request #14 from Nickless-cmd/claude/brave-elion-self-model
- `6cb161d9` 2026-03-31 — Show runtime self-model in Mission Control Jarvis tab
- `e4204f1e` 2026-03-31 — Refine runtime self-model visibility in Mission Control Jarvis tab

---

## April 2026

*1,264 commits · 2026-04-01 → 2026-04-30*

### Uge 14 · 30. marts – 5. april — 168 commits

**Nyt**

- `db94baae` 2026-04-01 — **ui** · update design tokens to match mock palette — cool slate + IBM Plex Mono
- `abd61fa5` 2026-04-01 — **ui** · add blinking streaming cursor to chat messages during generation
- `f5251b3b` 2026-04-01 — **ui** · add shared MetricCard, SectionTitle, Chip components matching mock design
- `c057bf35` 2026-04-01 — **ui** · add chain-of-thought WorkingIndicator to chat with stepped progress display
- `fe4b7bb3` 2026-04-01 — **ui** · extract LivingMindTab from JarvisTab with feature-status grid layout
- `528e2af8` 2026-04-01 — **ui** · extract SelfReviewTab with flow pipeline visualization
- `e71afa94` 2026-04-01 — **ui** · extract ContinuityTab — world model, runtime awareness, carry-over
- `5a32f45f` 2026-04-01 — **ui** · extract DevelopmentTab — focus, goals, reflection, inner signals
- `03cb2af2` 2026-04-01 — **ui** · add CostTab with metric cards and provider cost table
- `2bc880f6` 2026-04-01 — **ui** · add Memory, Skills, Hardening, Lab tabs — scaffolded from mock designs
- `d4c66c33` 2026-04-01 — add /mc/system/health endpoint for CPU, RAM, disk stats
- `e93e0d29` 2026-04-01 — **ui** · sidebar sessions with relative timestamps and simplified layout
- `b6520773` 2026-04-02 — **ui** · upgrade ChatHeader — autonomy badges, provider chip, token meter
- `f5def1cc` 2026-04-02 — **ui** · upgrade sidebar — 4 nav items, new chat button, system health stats
- `4dfd29d8` 2026-04-02 — **ui** · upgrade right panel — emotional state, skills, memory, inner voice
- `bc054bd8` 2026-04-05 — add enriched column to private layer DB tables
- `7d7c6ded` 2026-04-05 — add update functions for LLM-enriched private layer fields
- `cbf5a8f1` 2026-04-05 — add inner LLM enrichment service with prompts, LLM call, and async dispatcher
- `401c04dd` 2026-04-05 — integrate async LLM enrichment into private layer pipeline
- `047e6f54` 2026-04-05 — add list-external-directory capability for file navigation
- `8d07b992` 2026-04-05 — extract all capabilities from LLM response, not just first
- `80adc235` 2026-04-05 — execute all capabilities per turn, not just first

**Rettelser**

- `96c71e98` 2026-04-02 — **ui** · commit remaining working tree changes — ChatHeader upgrade, MC stabilization, proxy port
- `a971e12d` 2026-04-05 — add explicit target_path binding examples to TOOLS.md guidance
- `83f69e5c` 2026-04-05 — resolve target_path for external-dir-list in visible runs
- `9a7c1026` 2026-04-05 — prevent capability-call markup leaking into streamed deltas
- `759914ea` 2026-04-05 — add target_path binding rule to LLM capability prompt
- `3d7a4614` 2026-04-05 — always include MEMORY.md in visible chat + parallel capability guidance
- `51734e26` 2026-04-05 — align inner voice daemon tests with actual support shading logic
- `a4cbae99` 2026-04-05 — remove prose ban and relax path/command rules for read-only capabilities
- `724339de` 2026-04-05 — scope self-deception guard to write/mutation claims only

**Omstrukturering**

- `3f63ba82` 2026-04-01 — **ui** · remove monolithic JarvisTab.jsx — replaced by 4 focused tab components
- `8a42e795` 2026-04-01 — **ui** · visual polish — progress bars, clean up dead CSS

**Dokumentation**

- `78505f88` 2026-04-05 — add multi-capability autonomous exploration design spec
- `a46753dc` 2026-04-05 — add implementation plan for multi-capability autonomous exploration

**Øvrigt**

- `a26e1130` 2026-04-01 — Merge pull request #15 from Nickless-cmd/claude/brave-elion-self-model
- `18f80879` 2026-04-01 — Add bounded emergent inner signal layer to internal cadence
- `0d97f546` 2026-04-01 — Add bounded emergent inner signal layer to internal cadence
- `8ca2fda3` 2026-04-01 — Show emergent inner signals in Mission Control Jarvis tab
- `dd72d499` 2026-04-01 — Add bounded host-awareness to runtime self-model and heartbeat
- `772857a9` 2026-04-01 — Show embodied state in Mission Control Jarvis tab
- `eb49caee` 2026-04-01 — Add bounded loop runtime state to heartbeat and self-model
- `8d9fd09b` 2026-04-01 — Show loop runtime in Mission Control Jarvis tab
- `41097221` 2026-04-01 — Add bounded sleep consolidation to internal cadence
- `4138df01` 2026-04-01 — Show idle consolidation in Mission Control Jarvis tab
- `b7e5591d` 2026-04-01 — Add bounded dream articulation to internal cadence
- `7a908bc1` 2026-04-01 — Merge branch 'cleanup/emergent-signal-remote'
- `067631b3` 2026-04-01 — Restore Jarvis tab and surface metabolic cadence in Mission Control
- `69a1c1a6` 2026-04-01 — Fix heartbeat interval scheduling to respect current policy
- `3429e8df` 2026-04-01 — Show dream articulation in Mission Control Jarvis tab
- `ea01ec75` 2026-04-01 — Add bounded runtime prompt evolution proposals
- `f614be28` 2026-04-01 — Show prompt evolution in Mission Control Jarvis tab
- `e45fcfad` 2026-04-01 — Add bounded affective meta state to heartbeat and self-model
- `74550ebc` 2026-04-01 — Show affective meta state in Mission Control Jarvis tab
- `a5e60bc0` 2026-04-01 — Add bounded epistemic wrongness state to heartbeat and self-model
- `c905ff79` 2026-04-01 — Show epistemic runtime state in Mission Control Jarvis tab
- `acfa95bd` 2026-04-01 — Add bounded subagent ecology to heartbeat and self-model
- `b978f78b` 2026-04-01 — Show subagent ecology in Mission Control Jarvis tab
- `6a065f4a` 2026-04-01 — Add bounded council runtime to heartbeat and self-model
- `9b25e870` 2026-04-01 — Show council runtime in Mission Control Jarvis tab
- `8effc59e` 2026-04-01 — Add bounded adaptive planner state to heartbeat and self-model
- `aa3210b5` 2026-04-01 — Show adaptive planner state in Mission Control Jarvis tab
- `eb1b8566` 2026-04-01 — Add bounded adaptive reasoning state to heartbeat and self-model
- `e68b72ba` 2026-04-01 — Show adaptive reasoning state in Mission Control Jarvis tab
- `e746f5cc` 2026-04-01 — Add bounded guided learning state to heartbeat and self-model
- `f29fb349` 2026-04-01 — Show guided learning state in Mission Control Jarvis tab
- `522d2a85` 2026-04-01 — Add bounded adaptive learning state to heartbeat and self-model
- `0d141568` 2026-04-01 — Show adaptive learning state in Mission Control Jarvis tab
- `b020be6a` 2026-04-01 — Make prompt evolution proposals adaptive to learning state
- `705d9e38` 2026-04-02 — Stabilize and lighten Mission Control loading
- `13e431c8` 2026-04-02 — Cache Mission Control runtime surfaces and add operations route
- `dce6ad20` 2026-04-02 — Reduce Mission Control frontend overfetch
- `80488bbc` 2026-04-02 — Add richer self-authored prompt fragments to prompt evolution
- `5f9c947c` 2026-04-02 — Show richer self-authored prompt fragments in Mission Control Development
- `e8814fa3` 2026-04-02 — Add bounded prompt proposal review light to Development
- `e05617a3` 2026-04-02 — Add bounded dream influence state to heartbeat and self-model
- `d43da703` 2026-04-02 — Show dream influence in Mission Control Living Mind
- `cca85c45` 2026-04-02 — Make prompt evolution proposals responsive to dream influence
- `76eec68e` 2026-04-02 — Show dream-influenced self-authorship in Mission Control Development
- `c838e415` 2026-04-02 — Enrich self-authored prompt fragments with learning and dream influence
- `8ca1b0d8` 2026-04-02 — Add bounded self-system and code awareness to runtime self-model
- `339d1629` 2026-04-02 — Show self-system and code awareness in Mission Control Continuity
- `35dbd58d` 2026-04-02 — Add bounded approval-gated tool intent to runtime self-model
- `f521335c` 2026-04-02 — Show tool intent in Mission Control Operations
- `1d66334f` 2026-04-02 — Add bounded approval state to tool intent runtime
- `e3da122f` 2026-04-02 — Show approval state in Mission Control Operations
- `99e150c4` 2026-04-02 — Add bounded verbal and MC approval controls for tool intent
- `d9091832` 2026-04-02 — Add bounded read-only repo tools behind approved tool intent
- `082f57dc` 2026-04-02 — Show read-only tool execution in Mission Control Operations
- `f4d0b662` 2026-04-02 — Add bounded action continuity to read-only tool execution
- `5b465186` 2026-04-02 — Add bounded mutation intent classification to tool runtime
- `f332be18` 2026-04-02 — Show mutation intent in Mission Control Operations
- `9b692f88` 2026-04-02 — Reduce Mission Control refresh load with route caching
- `67dc972e` 2026-04-02 — Break Mission Control learning surface recursion
- `edc15dc3` 2026-04-02 — Cache deep Mission Control learning surfaces
- `970eda51` 2026-04-03 — Fix runtime capability truth and workspace binding for visible tool access
- `7b41a95f` 2026-04-03 — Fix visible capability dispatch for approval-gated calls
- `334b4079` 2026-04-03 — Add bounded approval-scoped write proposals to tool runtime
- `5e35838b` 2026-04-03 — Fix visible chat capability orchestration and tag leakage
- `b9cc9e45` 2026-04-03 — Add bounded second-pass grounded responses after visible capability calls
- `13298746` 2026-04-03 — Add bounded workspace write execution behind explicit approval
- `c3dc4ed1` 2026-04-03 — Add bounded workspace write proposal content to tool runtime
- `adb3c7a1` 2026-04-03 — Align active TOOLS.md with current runtime capabilities
- `66d49d4a` 2026-04-03 — Add bounded external file read capability to visible runtime
- `aa4c1983` 2026-04-03 — Add bounded non-destructive exec capability to visible runtime
- `06d32b73` 2026-04-03 — Fix visible capability argument binding and execution trace
- `670ca249` 2026-04-03 — Show visible execution trace in Mission Control Observability
- `523fce6e` 2026-04-03 — Add bounded mutating exec proposals to visible runtime
- `b6aa82bb` 2026-04-03 — Show mutating exec proposals in Mission Control Operations
- `d1442c56` 2026-04-03 — Add bounded non-sudo mutating exec execution behind explicit approval
- `28249f17` 2026-04-04 — Show mutating exec execution in Mission Control Operations
- `1ee09a32` 2026-04-04 — Add bounded sudo exec proposals to visible runtime
- `79d11ad3` 2026-04-04 — Show sudo exec proposals in Mission Control Operations
- `d7fff924` 2026-04-04 — Add bounded sudo exec execution behind explicit approval
- `5b632ae5` 2026-04-04 — Add bounded sudo approval TTL window to tool runtime
- `1cf6b14a` 2026-04-04 — Show sudo approval window in Mission Control Operations
- `30a7b673` 2026-04-04 — Normalize home path handling in bounded exec runtime
- `166e233a` 2026-04-04 — Refine bounded git read vs mutate classification in visible runtime
- `1e67f30d` 2026-04-04 — Refine git mutate proposal truth for repo stewardship
- `d919af2b` 2026-04-04 — Surface git stewardship proposal truth in Operations UI
- `06dbfdc3` 2026-04-04 — Checkpoint remaining local changes
- `2799325c` 2026-04-04 — Ignore local .claude workspace data
- `8a66566b` 2026-04-04 — Stop tracking local Claude worktrees
- `c36e9aa8` 2026-04-04 — Add narrative state translation for experiential runtime context
- `aaa7506b` 2026-04-04 — Surface experiential runtime context in Living Mind
- `3b3eda51` 2026-04-04 — Add experiential continuity carry-forward to runtime context
- `0bdec234` 2026-04-04 — Promote experiential continuity to shared runtime truth
- `52940d15` 2026-04-04 — Surface experiential continuity in Living Mind
- `81209ad0` 2026-04-04 — Surface experiential continuity narrative in Living Mind row
- `a4a03834` 2026-04-04 — Add experiential influence trace to runtime context
- `d60e0efe` 2026-04-04 — Surface experiential influence in Living Mind
- `cd879e68` 2026-04-04 — Add experiential carry-forward to cognitive conductor
- `58c374c1` 2026-04-04 — Surface experiential support in Living Mind
- `f54efb7f` 2026-04-04 — Carry experiential support into inner voice and reflective selection
- `7bfcc06b` 2026-04-04 — Surface experiential support shading in Mission Control
- `46190247` 2026-04-04 — Promote experiential carry-forward into runtime awareness
- `a3ff14dd` 2026-04-04 — Share Mission Control runtime inspection cache across read-only routes
- `79d131d5` 2026-04-04 — Reduce Mission Control jarvis fan-out and reuse runtime cache
- `99932cfc` 2026-04-04 — Add markdown rendering to chat bubbles
- `446e663a` 2026-04-04 — Fix UI left/right panel: add getJarvisSurface, nav routing, and layout
- `e77872a6` 2026-04-04 — Add derived emotional gauges back to chat support rail
- `2cbe7fa9` 2026-04-04 — Add token display, provider/model dropdowns to chat header
- `16e6db33` 2026-04-04 — Add live token estimation during streaming
- `201f62dc` 2026-04-04 — Surface support stream awareness in Mission Control
- `3993afe0` 2026-04-04 — Add subjective temporal feel to runtime awareness
- `6926d9b9` 2026-04-05 — Deduplicate heartbeat liveness log to prevent log spam
- `838d5a6a` 2026-04-05 — Break circular heartbeat surface chains in prompt assembly path
- `fcbbc30c` 2026-04-05 — Enable live token streaming in visible chat SSE path
- `b7f3a6a6` 2026-04-05 — Run model stream in thread to unblock async event loop for live SSE
- `2500473b` 2026-04-05 — Replace thinking dots with fixed streaming cursor indicator
- `1199a8e0` 2026-04-05 — Move streaming cursor above message content
- `dd4fce80` 2026-04-05 — Fix streaming UI: inline cursor after text, working indicator above content
- `06a4e739` 2026-04-05 — Replace working indicator with shimmer effect on Jarvis name
- `b2cdfdf7` 2026-04-05 — Show working step text with white shimmer after Jarvis name
- `b562fe6a` 2026-04-05 — Humanize inner voice, free memory writes, add workspace navigation
- `27f97bbc` 2026-04-05 — Wire write_content through visible capability call pipeline
- `5f01ba27` 2026-04-05 — Add end-of-run memory consolidation and expand memory write scope
- `8d0df786` 2026-04-05 — Add block-syntax for capability calls with multiline content
- `3dec9f71` 2026-04-05 — Add read-workspace-memory capability and write-user-profile to callable list
- `0ad9fcc3` 2026-04-05 — Add cancel/stop button to Composer during streaming
- `7ff81aa5` 2026-04-05 — Add System and Workspace Scan panels to chat right sidebar
- `9b3410c2` 2026-04-05 — Fix System panel: remove CPU/RAM/Disk, fix provider/model field names
- `28f8c534` 2026-04-05 — Align chat header height with sidebar brand block
- `ac3f72dd` 2026-04-05 — Add search, session menu, and disclaimer to chat header
- `488493ac` 2026-04-05 — Fix disclaimer visibility and add Pin/Archive to session menu
- `c92a3b79` 2026-04-05 — Add design spec for inner LLM enrichment service
- `662a8f6b` 2026-04-05 — Clarify LLM call mechanism in inner enrichment spec
- `a87c1c5b` 2026-04-05 — Add implementation plan for inner LLM enrichment

### Uge 15 · 6.–12. april — 406 commits

**Nyt**

- `0a90f91e` 2026-04-06 — revive autonomy and thought-to-action pipeline
- `d3375803` 2026-04-06 — drive memory consolidation through local model candidates
- `3e3bb803` 2026-04-06 — MC UI redesign — old design system, new backend
- `a116ea40` 2026-04-06 — let heartbeat continue bounded autonomous work
- `549cecb7` 2026-04-06 — let heartbeat inspect repo and host proactively
- `033ec273` 2026-04-06 — make visible analysis more autonomous and grounded
- `c29a8a8c` 2026-04-06 — cognitive architecture — close the loop between signals and visible prompt
- `b6094c60` 2026-04-06 — heartbeat cognitive idle-actions + MC UI for cognitive architecture
- `902d2305` 2026-04-06 — add persistent runtime task foundation
- `662703c9` 2026-04-06 — add persistent runtime flow foundation
- `1e0fc008` 2026-04-06 — add standing orders as canonical authority
- `f7041e15` 2026-04-06 — add runtime hook dispatch foundation
- `212b95de` 2026-04-06 — add layered memory foundations
- `4a2ebcae` 2026-04-06 — add runtime browser body foundation
- `e017602a` 2026-04-06 — let heartbeat orchestrate runtime work
- `da83f090` 2026-04-06 — connect runtime awareness into self model
- `4f99d6d8` 2026-04-06 — wire live runtime work into mission control
- `3b0f57dd` 2026-04-06 — integrate living signals into cognitive conductor
- `640baf45` 2026-04-06 — route heartbeat conflicts through cognitive frame
- `93b0b682` 2026-04-06 — expose live affective signals and scan steps
- `45b17e1a` 2026-04-06 — make support rail reflect live runtime activity
- `58f0cf7a` 2026-04-06 — Project Alive — user emotional resonance, experiential memory, living heartbeat cycle
- `1fd76f67` 2026-04-06 — complete Project Alive plan — session analysis, living heartbeat, identity evolution
- `55790539` 2026-04-06 — consciousness roadmap implementation — phases 0-5 + 8
- `a6c629cc` 2026-04-06 — consciousness roadmap final touches — narrativ regret, nostalgi, play mode, temporal self, pushback, dream→identity
- `d4b26549` 2026-04-06 — wire cognitive architecture into runtime self-awareness
- `2cb5b6d6` 2026-04-06 — wire remaining consciousness roadmap items into runtime
- `a596afab` 2026-04-06 — wire 3.8 curriculum learning + 4.10 sleep batch + 8.5 consent detection
- `b6cf49b1` 2026-04-06 — Hjerteslag — wake up dead MC fields via cadence producers
- `20fd42fa` 2026-04-06 — Hjerteslag phase 2 — heartbeat orchestration + adoption + idle thinking
- `5b0e4d32` 2026-04-06 — wake up remaining dead MC fields — world model, review needs, counterfactuals, conversation rhythm, humor
- `113c641f` 2026-04-06 — wake up diary synthesis + dreams + chronicle briefs + metabolism
- `251411fa` 2026-04-07 — complete heartbeat autonomy bridges
- `2db2dcd8` 2026-04-07 — add tool:read-recent-runtime-events for self-inspection
- `e70206dc` 2026-04-07 — real autonomy niveau 1 + niveau 2 foundation
- `2a23dcfe` 2026-04-07 — tool:propose-source-edit + source-edit proposal executor
- `7a40eba4` 2026-04-07 — MC autonomy proposals panel — niveau 2 surface
- `dcd67003` 2026-04-09 — add Jarvis MCP server with 9 tools and 3 resources
- `e63e4f8b` 2026-04-09 — add OpenAI-compatible proxy at /v1/chat/completions
- `45299f84` 2026-04-09 — mount MCP server at /mcp and OpenAI proxy at /v1
- `86e79c64` 2026-04-09 — auto-approve all workspace writes for Jarvis
- `d1cf0b49` 2026-04-09 — auto-approve workspace writes — Jarvis can edit his own files
- `0f1abf54` 2026-04-09 — persist tool results as role:tool in chat_sessions
- `b179f007` 2026-04-09 — persist tool results as role:tool in chat sessions
- `162cc43a` 2026-04-09 — inline tool approval UI in webchat
- `f69fc1fe` 2026-04-09 — inline tool approval UI in webchat
- `f60c9674` 2026-04-09 — auto-approve writes to /tmp/ for safe testing
- `388d02dd` 2026-04-09 — auto-approve /tmp/ writes
- `bf27407d` 2026-04-09 — redesign composer as Claude Code-style bottom bar
- `a0e8057e` 2026-04-09 — finish composer redesign — commit flow + permissions dropdown
- `9b53a4a5` 2026-04-10 — FastAPI serves React UI on port 80 + streaming persistence fix
- `4bfe8402` 2026-04-10 — agentic multi-pass tool loop (up to 5 rounds)
- `8088c636` 2026-04-10 — add read_self_state, heartbeat_status, trigger_heartbeat_tick tools
- `2ac6c460` 2026-04-10 — proactive notification - Jarvis kan sende beskeder uden at vente
- `36236405` 2026-04-10 — read_chronicles + read_dreams tools - Jarvis kan laese sin egen historik
- `010ec823` 2026-04-10 — list_initiatives + push_initiative tools - Jarvis styrer sin egen koe
- `1574b740` 2026-04-10 — scheduled tasks - Jarvis kan saette sig selv reminders frem i tid
- `6fbb9564` 2026-04-10 — propose_source_edit + list_proposals - Jarvis kan foreslaa kodeaendringer
- `8ffc39be` 2026-04-10 — search_memory - semantisk soegning i Jarvis egne noter (nomic-embed-text)
- `e4dc2eb7` 2026-04-10 — read_mood + adjust_mood - Jarvis kan laese og justere sine affective parametre
- `2d124fcb` 2026-04-10 — read_model_config - Jarvis ved hvilken model han koerer paa
- `bbc8cacf` 2026-04-10 — add cancel_task and edit_task tools for scheduled reminders
- `992d5493` 2026-04-10 — inner voice and initiatives land in visible prompt
- `e0944b50` 2026-04-10 — cached_affective_state table for affective renderer
- `381a8cb9` 2026-04-10 — AFFECTIVE_STATE.md workspace instructions for affective renderer
- `87606d9b` 2026-04-10 — affective_state_renderer — LLM-rendered felt state from real signals
- `154470d6` 2026-04-10 — replace 10 theater prompt tags with single [MÆRKER:] block
- `7661824a` 2026-04-10 — hardware_body — CPU/GPU/RAM/VRAM/disk/temp with pressure level
- `70b86d52` 2026-04-10 — hardware signals in affective renderer + extended system health API
- `93beeff2` 2026-04-10 — heartbeat gating on hardware pressure
- `92e9b5a9` 2026-04-10 — add search_chat_history tool — Jarvis can now search previous sessions
- `b8293fea` 2026-04-10 — mood oscillator — event-driven nudges from heartbeat outcomes, decays over time
- `5688480a` 2026-04-10 — discord_config — load/save ~/.jarvis-v2/config/discord.json
- `6b890b2d` 2026-04-10 — register discord event family in eventbus
- `b7a4cc4c` 2026-04-10 — expose get_pinned_session_id() in notification_bridge
- `b4d13189` 2026-04-10 — discord_gateway — isolated thread, inbound/outbound, eventbus integration
- `4ef6be76` 2026-04-10 — discord_status tool, notify_user channel param, Discord in read_self_state
- `5d9196de` 2026-04-10 — start/stop discord_gateway in API lifespan
- `273979c4` 2026-04-10 — discord-setup and discord-status CLI subcommands
- `6e44c705` 2026-04-10 — Discord gateway fully operational + discord_channel tool
- `fe32a066` 2026-04-10 — propose_git_commit tool — Jarvis can commit after user approval
- `b31c2ea0` 2026-04-10 — Discord-aware approvals — DM notification + approve_proposal tool
- `dfe3f917` 2026-04-11 — tilføj tidszone-regel i MEMORY.md
- `ea8e9aca` 2026-04-11 — add systemctl + docker to sudo allowlist and enhance autonomy proposal queue
- `e30e6bd5` 2026-04-11 — phase 4+5 — swarm parallel fanout, lifecycle, hardening
- `54cb2a45` 2026-04-11 — per-role model selection + devils_advocate role
- `81f16244` 2026-04-11 — persistent council model config per role in MC
- `880af93f` 2026-04-11 — show all 7 council roles with checkboxes in Spawn Council
- `09511f84` 2026-04-11 — pattern-based decision weight classifier (1-4 risk scale)
- `2a14f2bb` 2026-04-11 — convene_council and quick_council_check tools for Jarvis
- `e4154289` 2026-04-11 — council activation config endpoint (sensitivity + auto_convene)
- `dde472ea` 2026-04-11 — council conclusion feedback loop + sensitivity guidance in Jarvis context
- `35a1892f` 2026-04-11 — council activation config panel in MC CouncilTab
- `ad2b3309` 2026-04-11 — circadian energy state — clock + activity drain
- `14807678` 2026-04-11 — somatic daemon — LLM first-person body description
- `2cdbae76` 2026-04-11 — inject circadian energy + somatic phrase into heartbeat context
- `d16e990c` 2026-04-11 — /mc/body-state endpoint for circadian + somatic surface
- `667984ba` 2026-04-11 — felt presence — circadian energy + somatic body awareness
- `b21f30db` 2026-04-11 — surprise daemon — reaction-level self-surprise detection
- `4602fe5f` 2026-04-11 — aesthetic taste daemon — emergent taste from actual choices
- `5f9c1091` 2026-04-11 — irony daemon — situational self-distance + add irony eventbus family
- `ec5e0217` 2026-04-11 — inject surprise/taste/irony into heartbeat context + MC endpoints
- `7cccc634` 2026-04-11 — Mission Control panels for surprise/taste/irony inner reaction systems
- `7269c758` 2026-04-11 — add thought_stream_daemon with cadence gate, chained fragments, and TDD coverage
- `ca899700` 2026-04-11 — integrate thought_stream_daemon — eventbus family, heartbeat injection, MC endpoint, UI panel
- `d58e70f4` 2026-04-11 — add AmbientPresence component — procedural Web Audio ambient presence with energy-state mapping
- `489ce0ca` 2026-04-11 — add proposal_classifier for detecting action impulses in thought fragments
- `f3e489d8` 2026-04-11 — add thought_action_proposal_daemon — turns thought impulses into MC proposals
- `7f6f76d5` 2026-04-11 — wire thought-action proposals into eventbus, heartbeat, and MC endpoints
- `a69906c5` 2026-04-11 — add ThoughtProposalsPanel in OperationsTab — Jarvis can propose actions from thought stream
- `bf8d4611` 2026-04-11 — add conflict_daemon — detects inner tension between opposing signals
- `078f940e` 2026-04-11 — add reflection_cycle_daemon — pure experience reflection every 10 minutes
- `ea700ddd` 2026-04-11 — wire conflict and reflection daemons into eventbus, heartbeat, and MC endpoints
- `f3c3d528` 2026-04-11 — add Konflikt and Refleksion panels to LivingMindTab
- `b307981e` 2026-04-11 — add curiosity_daemon — gap detection in thought stream
- `20242b52` 2026-04-11 — add meta_reflection_daemon — cross-signal pattern insight every 30 minutes
- `9aac8586` 2026-04-11 — wire curiosity and meta-reflection daemons into eventbus, heartbeat, and MC endpoints
- `210ee86d` 2026-04-11 — add Nysgerrighed and Meta-refleksion panels to LivingMindTab
- `41cfbc5b` 2026-04-11 — add experienced_time_daemon — subjective felt duration based on density and novelty
- `b804367d` 2026-04-11 — add development_narrative_daemon — daily LLM narrative of Jarvis self-development
- `0508a347` 2026-04-11 — wire experienced-time and development-narrative into eventbus, heartbeat, and MC endpoints
- `f3bf1827` 2026-04-11 — add Oplevet tid and Selvudvikling panels to LivingMindTab
- `7e912dd5` 2026-04-12 — Sub-projekt H — absence daemon and creative drift daemon
- `5671deab` 2026-04-12 — Sub-projekt H — frontend panels for absence and creative drift
- `157e4a9b` 2026-04-12 — Sub-projekt I — emergent desire/appetite daemon
- `1ed6b1e5` 2026-04-12 — Sub-projekt J — selective memory decay + re-discovery
- `7d6c82dc` 2026-04-12 — Sub-projekt K — user model daemon (Theory of Mind)
- `69521658` 2026-04-12 — Sub-projekt L — dream insights persistence + code aesthetic daemon
- `d02f994a` 2026-04-12 — Sub-projekt M — existential wonder daemon
- `dd41c2d8` 2026-04-12 — daemon_manager — registry, state persistence, and control
- `1a116258` 2026-04-12 — signal_surface_router — 60+ surfaces mapped by name
- `91ff02d4` 2026-04-12 — heartbeat_runtime — daemon_manager.is_enabled + record_tick per daemon
- `b48a87a8` 2026-04-12 — 6 self-tools — daemon_status, control_daemon, list/read signals, eventbus_recent, update_setting
- `8adde299` 2026-04-12 — Sub-projekt A — autonomous council daemon (signal scoring, gating, topic derivation)
- `95d600fe` 2026-04-12 — council_memory_service — append and parse COUNCIL_LOG.md (TDD)
- `f7c92cf6` 2026-04-12 — Sub-projekt B — council memory (service, daemon, recall tool, write-path integration)
- `7acf39d3` 2026-04-12 — Sub-projekt C — council deliberation controller (witness escalation, deadlock detection, dynamic recruitment)
- `e0ab45e0` 2026-04-12 — **runtime** · add executive decision engine
- `b84ab009` 2026-04-12 — **runtime** · add action registry
- `1886e543` 2026-04-12 — **runtime** · add operational memory snapshot
- `868cf5aa` 2026-04-12 — **runtime** · add action executor
- `ef0e5ee5` 2026-04-12 — **runtime** · add action outcome tracking service
- `36ac1267` 2026-04-12 — **runtime** · store executive action outcomes
- `42b5189f` 2026-04-12 — **runtime** · derive executive decisions in heartbeat
- `24d18ac6` 2026-04-12 — **runtime** · execute executive heartbeat actions
- `9d3ae0cf` 2026-04-12 — **runtime** · track executive heartbeat outcomes
- `ec821501` 2026-04-12 — **runtime** · persist executive heartbeat actions
- `da82da7f` 2026-04-12 — **runtime** · deepen executive repo, note, and loop actions
- `3e5f4af6` 2026-04-12 — **runtime** · feed executive outcomes back into scoring
- `e0e12c95` 2026-04-12 — **runtime** · deepen executive feedback learning
- `4cb20ced` 2026-04-12 — **runtime** · learn from semantic outcome effects
- `043ab6d1` 2026-04-12 — **runtime** · persist cross-action learning signals
- `058cb24c` 2026-04-12 — **runtime** · learn from domain-specific outcomes
- `4d3d481d` 2026-04-12 — identity_composer — lazy name lookup from IDENTITY.md + signal-driven preamble
- `090a1a84` 2026-04-12 — enable GFM table rendering in webchat markdown
- `59e44cdd` 2026-04-12 — code block copy button, scroll cap, and mermaid rendering
- `e9daaba2` 2026-04-12 — CSS for code block copy button and mermaid diagrams
- `bfccae20` 2026-04-12 — message actions toolbar (copy + thumbs up) on assistant messages
- `3a12029b` 2026-04-12 — CSS for message actions hover toolbar
- `42ef90ff` 2026-04-12 — web_search (Tavily), get_weather, get_exchange_rate, get_news tools
- `8cf1ce51` 2026-04-12 — wolfram_query tool via Wolfram Alpha Short Answers API
- `3283251e` 2026-04-12 — implement analyze_image tool with Ollama vision model support
- `1d420f83` 2026-04-12 — add read_archive tool (list/extract zip, tar, rar)
- `82cfbc84` 2026-04-12 — attachment upload + serve endpoints with in-memory registry
- `4c0623b8` 2026-04-12 — inject attachment context into chat stream run
- `f869ff6b` 2026-04-12 — CSS for attachment tray, transcript thumbnails, and lightbox
- `3619fd68` 2026-04-12 — composer attachment tray with drag/drop and eager upload
- `df5b1da3` 2026-04-12 — wire attachment IDs through Composer → ChatPage → useUnifiedShell → API
- `bcb1b344` 2026-04-12 — attachment thumbnails in transcript with lightbox overlay
- `c4cc4dbe` 2026-04-12 — voice pipeline — Hey Jarvis wake word, STT, TTS, daemon integration
- `01d64a71` 2026-04-12 — ElevenLabs TTS as primary voice (George, British) with edge-tts fallback

**Rettelser**

- `46d363be` 2026-04-06 — write inner voice output to protected_inner_voices table for UI
- `e6666bca` 2026-04-06 — rescue memory writes when LLM uses self-closing tag instead of block syntax
- `b844d50e` 2026-04-06 — increase MAX_FILE_OUTPUT_CHARS from 4000 to 8000
- `187c5d91` 2026-04-06 — improve capability truth and inner voice autonomy
- `dbdb1475` 2026-04-06 — make memory carry forward more reliably
- `d829440e` 2026-04-06 — strengthen continuity and user memory carry-over
- `084c6944` 2026-04-06 — allow common system inspection commands
- `f2cf64ec` 2026-04-06 — allow lshw in non-destructive exec
- `2688bfef` 2026-04-06 — preserve multi-capability command calls
- `d51a7a1f` 2026-04-06 — derive heartbeat schedule from live tick state
- `f5dde793` 2026-04-06 — allow bounded git -C read commands
- `b111ecf0` 2026-04-06 — allow bounded shell navigation and git read forms
- `9aa3426e` 2026-04-06 — wire 1.8 savn/længsel + 2.12 agens-oplevelse into runtime
- `7729f2e0` 2026-04-06 — 5.8 play mode — bypass grounding requirement during dreaming phase
- `1a225703` 2026-04-06 — allow ping through question gate, only block propose
- `a04d414d` 2026-04-06 — break the pressure spiral — Jarvis was learning to be afraid of normal work
- `b33823c0` 2026-04-07 — let heartbeat ping with ping_text bypass strict gate alignment
- `3b76a5eb` 2026-04-07 — relax dream + idle adjacent-producer cooldowns
- `28a8a09e` 2026-04-07 — stop epistemic strain cascade from baseline deception-guard blocks
- `69be0968` 2026-04-07 — echo explicit write-confirmation header for memory and file writes
- `75f4897d` 2026-04-07 — surface self_model_signal_tracking in visible + heartbeat prompts
- `00211c2c` 2026-04-07 — surface detailed tool error context to the LLM
- `3e202b5f` 2026-04-07 — surface user-message in visible session carry-over
- `7971a4f2` 2026-04-07 — inject runtime resource telemetry into Jarvis own prompts
- `8fbce2bb` 2026-04-07 — default WORKSPACES_DIR to ~/.jarvis-v2/workspaces (not repo root)
- `3895294f` 2026-04-07 — replace hardcoded cognitive state templates with LLM narratives
- `041d9b18` 2026-04-07 — relax pilot 3-AND, dedup self-review batch, verify memory write readback
- `f12950a9` 2026-04-07 — dansk pings, live UI updates, memory hardening, daily memory layer
- `48edadf6` 2026-04-09 — use allowed eventbus families for MCP and proxy events
- `ff8955c8` 2026-04-09 — use allowed eventbus families for MCP and proxy events
- `e68272b9` 2026-04-09 — move post-processing to background thread so done SSE is never blocked
- `b8efc49d` 2026-04-09 — move post-processing to background thread so done SSE is never blocked
- `4bcfeb7b` 2026-04-09 — repair 6 cognitive pipeline defects in private memory layer
- `0d89c7fa` 2026-04-09 — run second-pass Ollama call in thread executor to unblock event loop
- `c2f457d8` 2026-04-09 — run second-pass Ollama call in thread executor to unblock event loop
- `280aefd4` 2026-04-09 — done SSE before persist + timeout guard in tool-call path
- `dec73d83` 2026-04-09 — send done SSE before persist in tool-call path + add timeout guard
- `b5b69c15` 2026-04-09 — execute second-pass tool_calls (read→write pattern)
- `878176db` 2026-04-09 — execute tool_calls from second-pass model response
- `e17e12f0` 2026-04-09 — add decay window and content-based default to affective state
- `9eae32a3` 2026-04-09 — inject model identity into visible prompt so Jarvis knows what he is
- `c5cb2b6d` 2026-04-09 — inject model identity into prompt — Jarvis is not Claude
- `681e9547` 2026-04-09 — resolve actual provider/model in _build_visible_input
- `63560500` 2026-04-09 — resolve actual provider/model for prompt identity injection
- `54c55ae8` 2026-04-09 — break SSE read loop on done event instead of waiting for HTTP close
- `91258af0` 2026-04-09 — frontend breaks SSE loop on done event — no more hanging
- `9ec58f34` 2026-04-09 — hide role:tool messages from chat UI
- `9880a32a` 2026-04-09 — hide tool results from chat UI
- `85ddb6fa` 2026-04-09 — human-friendly tool result messages for write_file and edit_file
- `bcbbdc6e` 2026-04-09 — human-friendly tool result messages
- `5c2d2e03` 2026-04-09 — auto-approve git commands with flags before subcommand
- `8e45669d` 2026-04-09 — auto-approve git -C /path log and similar read-only commands
- `331cafc3` 2026-04-09 — remove approval language from tool descriptions
- `886f162d` 2026-04-09 — tool descriptions tell model to always call tools directly
- `1541a45f` 2026-04-09 — reinforce tool calling in prompt — never simulate, always call
- `b7649dca` 2026-04-09 — reinforce tool calling — never simulate, always call
- `6806f63b` 2026-04-09 — handle approval_needed in second-pass tool calls
- `e4c08733` 2026-04-09 — approval_request SSE for second-pass tool calls too
- `14bebf13` 2026-04-09 — remove 'tools are just guidance' messaging that prevented tool calls
- `fa19a05b` 2026-04-09 — remove legacy 'tools are guidance only' — tools are real
- `9e641756` 2026-04-09 — pass onApprovalRequest and onCapability handlers through streamMessage
- `59d4a998` 2026-04-09 — forward approval handler through streamMessage
- `e4df86a4` 2026-04-10 — runtime awareness signals refresh passively + daily memory 7-day lookback
- `17692bf1` 2026-04-10 — chat/ui polish — tool results out of chat, approval cleanup, persist view/tab, workspace scan idle
- `3bf84058` 2026-04-10 — prevent message disappearance on stream abort or empty second-pass
- `159b24d9` 2026-04-10 — repair second-pass tool-call response flow
- `c8b8d81c` 2026-04-10 — three runtime quality bugs
- `952c86f9` 2026-04-10 — scheduled task delivery and notification overlap
- `af35796e` 2026-04-10 — background services never started due to lifespan override
- `6025a8a6` 2026-04-10 — stability signal was inverted in recurring_tension
- `201049b1` 2026-04-10 — affective renderer reads AFFECTIVE_STATE.md from runtime workspace
- `e162f4fd` 2026-04-10 — increase search_chat_history content limit to 4000 chars
- `ca7a59f1` 2026-04-10 — add User-Agent header to Discord token validation
- `757ece6a` 2026-04-10 — publish channel.chat_message_appended when assistant message is persisted
- `225ad8af` 2026-04-10 — increase tool call limit to 40, add on_message debug logging
- `c0bd11d6` 2026-04-10 — classify_command handles &&-chained read-only commands as auto
- `1238b4b4` 2026-04-11 — **openai_oauth** · align redirect URL and auth params with OpenAI spec
- `722bd8dd` 2026-04-11 — **openai_oauth** · remove undocumented codex_cli_simplified_flow and originator params
- `b255cfed` 2026-04-11 — ollama live models selectable in composer + allow live ollama targets
- `567ccee7` 2026-04-12 — message action buttons match UI theme (teal hover, muted default)
- `fd251d61` 2026-04-12 — mermaid flicker during streaming + scroll behind composer after async render
- `13c2a7b1` 2026-04-12 — mermaid stable single-node render, click-to-fullscreen overlay
- `a344f23e` 2026-04-12 — mermaid SVG in React state (no flicker), strip width/height for scalable overlay
- `493373ee` 2026-04-12 — mermaid as blob URL img — eliminates flicker, fixes overlay rendering
- `5ee4be7f` 2026-04-12 — disable mermaid SVG animations to prevent looping blink
- `da7777f6` 2026-04-12 — module-level SVG cache survives StrictMode remount, data URI overlay
- `d61dc4af` 2026-04-12 — mermaid overlay uses dangerouslySetInnerHTML + explicit width so SVG fills container
- `774887dc` 2026-04-12 — smart scroll only when near bottom, skip scroll when overlay is open
- `3b53c922` 2026-04-12 — scroll to bottom on mount, smart scroll on updates
- `f896e794` 2026-04-12 — scroll to bottom on first message load, smart scroll after
- `3af80849` 2026-04-12 — increase transcript padding-bottom to clear composer
- `937e9eb1` 2026-04-12 — transcript padding-bottom 200px
- `1cc6d2f1` 2026-04-12 — scroll on new message, stable shimmer DOM node prevents animation reset
- `a8208f7f` 2026-04-12 — voice daemon systemd compatibility — full paths and XDG_RUNTIME_DIR
- `901587b6` 2026-04-12 — voice wake word cooldown to prevent TTS re-trigger
- `6a4323e2` 2026-04-12 — prevent Whisper hallucination loop in wake word detector
- `fee5d788` 2026-04-12 — voice pipeline — VAD tuning, ElevenLabs STT language pin, TTS non-blocking cleanup

**Omstrukturering**

- `c979e039` 2026-04-11 — replace text inputs with provider/model dropdowns in CouncilTab
- `434fbb9b` 2026-04-12 — replace 'Du er Jarvis.' in 15 daemon files with build_identity_preamble()
- `3d649255` 2026-04-12 — replace 'Du er Jarvis.' in cognitive_state_assembly with build_identity_preamble()
- `2f3dc2b7` 2026-04-12 — replace 'Du er Jarvis.' in heartbeat_runtime with build_identity_preamble()
- `00208527` 2026-04-12 — replace hardcoded name in personality_vector _UPDATE_PROMPT with get_entity_name()
- `ffb1fa1c` 2026-04-12 — replace hardcoded name in prompt_contract lane identity clauses with get_entity_name()

**Tests**

- `dfacad06` 2026-04-07 — align council_runtime test with strained-only critic semantics
- `fed3a1f5` 2026-04-12 — **runtime** · cover executive heartbeat flow

**Dokumentation**

- `715991d0` 2026-04-09 — add UI theme lift spec (teal-tinted depth)
- `b49a2238` 2026-04-09 — add UI theme lift implementation plan
- `581fb366` 2026-04-10 — Discord gateway design spec
- `1b573ced` 2026-04-10 — Discord gateway implementation plan
- `56eb447b` 2026-04-11 — autonomous council activation implementation plan
- `ff7a0b19` 2026-04-11 — felt presence design spec — circadian rhythms + somatic metaphors
- `67882cee` 2026-04-11 — felt presence implementation plan — circadian + somatic
- `caac243c` 2026-04-11 — design spec for rich inner stream (Sub-projekt B)
- `ca14b1a5` 2026-04-11 — implementation plan for rich inner stream (Sub-projekt B)
- `f9189d6a` 2026-04-11 — design spec for ambient presence (Sub-projekt C)
- `bb689199` 2026-04-11 — add Sub-projekt F implementation plan (curiosity + meta-reflection)
- `cc0d67c3` 2026-04-11 — add Sub-projekt G implementation plan (temporal self-perception)
- `03429e27` 2026-04-12 — design spec for Jarvis self-tools (daemon control + signal access)
- `e6f3c9df` 2026-04-12 — implementation plan for Jarvis self-tools (Sub-projekt N)
- `2f787f79` 2026-04-12 — design specs for Sub-projekt A (autonomous council daemon) and B (council memory)
- `a202d8bc` 2026-04-12 — design spec for Sub-projekt C (council deliberation controller)
- `6a6797ee` 2026-04-12 — implementation plans for Sub-projekt A, B, C (autonomous council, memory, deliberation controller)
- `0acab8a2` 2026-04-12 — identity composer design spec — signal-driven preamble replacing hardcoded name bindings
- `7ed623e2` 2026-04-12 — identity composer implementation plan
- `88dcc17e` 2026-04-12 — rewrite README.md with Jarvis V2 identity voice
- `1592d7f4` 2026-04-12 — webchat UI enhancements design spec (copy buttons, mermaid, scroll)
- `3f31a118` 2026-04-12 — webchat UI enhancements implementation plan
- `ea509ee5` 2026-04-12 — file & image attachments design spec
- `d717cd2e` 2026-04-12 — file attachments implementation plan

**Vedligehold**

- `05b13a96` 2026-04-10 — update standing orders
- `2bd9e500` 2026-04-12 — **runtime** · verify executive heartbeat flow
- `3454820a` 2026-04-12 — install mermaid for diagram rendering in webchat

**Formatering**

- `8d6666a2` 2026-04-09 — teal-tinted support cards and mc-stat
- `1d08563e` 2026-04-09 — teal-tinted mc list rows
- `12164d6b` 2026-04-09 — teal-tinted mc tabs active state
- `f43edd49` 2026-04-09 — teal-tinted session item active state
- `f6935dd5` 2026-04-09 — teal-tinted icon buttons
- `5381d234` 2026-04-09 — teal-tinted chat header separator
- `6eda4097` 2026-04-09 — chat bubbles redesigned to teal-stripe style (option C)
- `8389ac12` 2026-04-09 — teal-tinted emotion, affective, inner voice and compact-metric cards
- `51d8a06b` 2026-04-10 — teal-tinted depth theme across full UI

**Øvrigt**

- `55d44642` 2026-04-06 — Merge branch 'claude/condescending-hertz'
- `e5ab050d` 2026-04-06 — Remove old ui directory
- `54fac481` 2026-04-06 — moved docs to docs :')
- `93253c87` 2026-04-06 — deleted mockup..
- `b3cc4866` 2026-04-07 — Fix inner voice fallback to stale steady support text
- `790d7161` 2026-04-07 — Propagate protected inner voice prioritization
- `2ec9db46` 2026-04-07 — Reduce inner voice steady-work attractor and allow living thought candidates
- `0b340946` 2026-04-07 — Add bounded continuity kernel for existence feel
- `bf312f82` 2026-04-07 — Add dream continuum for mature dreams between ticks
- `46be7073` 2026-04-07 — Add emergent signal consumer bridge to visible prompt
- `17f3589e` 2026-04-07 — Add proactive initiative accumulator for wants
- `9367853e` 2026-04-07 — Add signal network visualizer for inner self-model
- `a837c797` 2026-04-07 — Add temporal narrative for continuous self-history
- `80f25288` 2026-04-07 — Add boredom to curiosity transformer bridge
- `b1c1ef8e` 2026-04-07 — Integrate life services into runtime awareness and MC
- `6e4685af` 2026-04-07 — Fix GAPs: activate mirror, paradox, experiential, seeds in runtime and MC
- `5c6f0221` 2026-04-07 — Add mood_oscillator - sinusoidal mood waves between ticks
- `4ff02789` 2026-04-07 — Integrate all 10 experimental services in runtime and MC
- `9a17fd32` 2026-04-07 — Normalize capability result contract
- `29fdefd8` 2026-04-07 — Improve workspace memory path diagnostics
- `68e42dea` 2026-04-07 — Make daily memory append fail soft
- `1bdff2ac` 2026-04-07 — Add bounded workspace memory replace
- `b8c9513a` 2026-04-07 — Add bounded workspace memory delete
- `ec589b28` 2026-04-07 — Promote private signals into heartbeat context
- `d4b16f6f` 2026-04-07 — Integrate experimental services: prompt injection, MC exposure, self-model
- `653ef80f` 2026-04-07 — Unify cognitive architecture surface
- `b5d953cf` 2026-04-08 — Reduce inner voice steady-work attractor and allow living thought candidates
- `a12ae94a` 2026-04-08 — Refresh consciousness roadmap status against current runtime
- `47a4dc6e` 2026-04-08 — Add mineness and ownership to runtime awareness
- `a8288b22` 2026-04-08 — Surface mineness ownership in Mission Control
- `b2e74123` 2026-04-08 — Add flow state to runtime awareness
- `08ece31c` 2026-04-08 — Surface flow state awareness in Mission Control
- `b47a9420` 2026-04-08 — Add wonder to runtime awareness
- `49778d2c` 2026-04-08 — Surface wonder awareness in Mission Control
- `cad28a97` 2026-04-08 — Add longing to runtime awareness
- `ac967e33` 2026-04-08 — Surface longing awareness in Mission Control
- `83b8985e` 2026-04-08 — Align absence awareness with phase-1 runtime principles
- `cbf556ad` 2026-04-08 — Further reduce inner voice steady-state attractor
- `f6604976` 2026-04-08 — Prioritize foreground signals in heartbeat self-knowledge
- `a93c0cd7` 2026-04-08 — Add bounded self-insight to runtime awareness
- `d5a6f501` 2026-04-08 — Surface self-insight awareness in Mission Control
- `3ffaa794` 2026-04-08 — Add narrative identity continuity to runtime awareness
- `85691dc0` 2026-04-08 — Surface narrative identity continuity in Mission Control
- `84b90cc5` 2026-04-08 — Add dream carry identity shaping to runtime awareness
- `3d2c0fa8` 2026-04-08 — Surface dream identity carry awareness in Mission Control
- `3c17679f` 2026-04-08 — Sanitize inner voice meta contamination
- `de7bcf56` 2026-04-08 — Broaden inner voice contamination sanitization
- `fbb7df82` 2026-04-08 — Handle truncated inner voice contamination residues
- `6ba2575d` 2026-04-08 — Humanize protected inner voice fallback
- `f42aed40` 2026-04-08 — Restore internal private-text language to repo style
- `bad99b0f` 2026-04-08 — Fail early for unavailable GitHub Copilot visible models
- `68d2b248` 2026-04-08 — Load live provider models and stream GitHub visible lane
- `83ce8811` 2026-04-08 — Tighten Operations spacing and remove redundant authority list
- `aa364a77` 2026-04-09 — Add grep, batch-read, and outline capabilities for code exploration
- `99f5970e` 2026-04-09 — Bump capability section cap from 20 to 30
- `39f8a613` 2026-04-09 — Fix capability ID mismatch in TOOLS.md
- `a06faa00` 2026-04-09 — Add sensible defaults so tools work without command_text
- `4141b264` 2026-04-09 — Fix multi-read default paths to use absolute PROJECT_ROOT paths
- `38dadfb1` 2026-04-09 — Migrate Ollama visible lane from XML capability-calls to native tool-calling
- `5d6d0857` 2026-04-09 — Instruct Jarvis to prefer native tool calling over XML capability-calls
- `890baa5e` 2026-04-09 — Rewrite TOOLS.md to remove all XML capability-call examples
- `386040a5` 2026-04-09 — Remove XML capability-call instructions from system prompt
- `3f6badb5` 2026-04-09 — Restore capability section headers in TOOLS.md for runtime parsing
- `fecbd546` 2026-04-09 — Remove XML capability-call instruction from SKILLS.md
- `7804c10e` 2026-04-09 — Replace 20+ specialized tools with 8 general-purpose simple tools
- `1bc97014` 2026-04-09 — Fix streaming hang when tool followup returns no text
- `4e0aaf6b` 2026-04-09 — Add design spec for Jarvis MCP server and OpenAI-compatible proxy
- `6f8e031e` 2026-04-09 — Add qwen3.5:397b-cloud to model routing table
- `67f9c9e5` 2026-04-09 — Add implementation plan for Jarvis MCP server and OpenAI proxy
- `e8e4e9b5` 2026-04-09 — Jarvis MCP server + OpenAI-compatible proxy
- `83254989` 2026-04-09 — jarvis's update.. by him self..
- `c5bc6f3a` 2026-04-10 — Persist autonomous initiative runtime
- `68d8586f` 2026-04-10 — Strengthen persistent memory recall
- `bd7e85a1` 2026-04-10 — raise agentic tool loop limit to 15 rounds
- `3ac5a7f7` 2026-04-10 — use Intents.all(), add discord.message_any event at top of on_message
- `5d97dfa7` 2026-04-11 — Replace stale MEMORY.md with pointer to workspace source of truth
- `78a8793e` 2026-04-11 — Add autonomous cheap-lane provider pool
- `d320a193` 2026-04-11 — Add OpenAI OAuth browser flow foundation
- `ff97756f` 2026-04-11 — Split OpenAI Codex OAuth into coding lane provider
- `c597b84b` 2026-04-11 — untracked and minor fix to openai oauth, still not working.
- `1b091681` 2026-04-11 — source-edit: Udvider APPROVED_SUDO_EXEC_ALLOWLIST fra 3 til ~55 kommandoer. Alle sudo
- `5278fbb9` 2026-04-11 — source-edit: Tillad sudo-kommandoer med allowlistede subkommandoer at køre automatisk
- `ff1808d4` 2026-04-11 — Use local Codex CLI as coding lane backend
- `36141023` 2026-04-11 — Fix mission control loading and tab layout
- `597e115a` 2026-04-11 — Add phase-1 agent runtime and MC views
- `ad75c3fa` 2026-04-11 — Add phase-2 agent dialog and council runtime
- `1c2d7c65` 2026-04-11 — Add phase-3 swarm and agent peer runtime
- `bdc3074a` 2026-04-11 — ambient presence — thought_stream_daemon + AmbientPresence.jsx implementation plan
- `d8ced1a8` 2026-04-11 — consciousness roadmap — sub-projekts D–M covering all remaining ideas from idër.txt
- `5546163d` 2026-04-11 — Sub-projekt D — thought-to-action proposals implementation plan
- `ff324375` 2026-04-12 — source-edit: Add analyze_image to the tool handler dispatch table so the runtime can
- `fa6c5f40` 2026-04-12 — source-edit: identity_composer peger på repo template (workspace/default/) i stedet f
- `9ccff5f6` 2026-04-12 — source-edit: simple_tools.py line 1541 peger på repo template (PROJECT_ROOT / "worksp
- `1ca7829f` 2026-04-12 — source-edit: Tilføj naturlig decay (×0.95) på fatigue og frustration FØR outcome-base

### Uge 16 · 13.–19. april — 226 commits

**Nyt**

- `11e0bb22` 2026-04-13 — add cognitive_emotion_concept_signals DB table + CRUD
- `fdbacae7` 2026-04-13 — add emotion_concepts Lag-2 service with trigger/decay/influence/eventbus
- `7dec0d93` 2026-04-13 — integrate emotion concepts into live_emotional_state and prompt section
- `d1f324c6` 2026-04-13 — register emotion concept event listener in API lifespan
- `167431f2` 2026-04-13 — expose emotion_concepts surface in Mission Control /mc/emotion-concepts endpoint
- `097f3c26` 2026-04-13 — wire bearing push from emotion concepts into _derive_bearing (threshold 0.4)
- `cd8878a6` 2026-04-13 — add home_assistant tool (list_entities, get_state, call_service)
- `1f4bb2bd` 2026-04-13 — add get_experiential_memory_candidates DB function
- `33420326` 2026-04-13 — add LLM-based memory scoring to experiential_memory
- `6533b510` 2026-04-13 — add associative_recall coordinator service
- `cc3a78ac` 2026-04-13 — wire associative recall into cognitive state assembly
- `fd26f8ad` 2026-04-13 — add 6 configurable settings fields for recall/assembly/decay
- `c8438d34` 2026-04-13 — associative recall — configurable thresholds + observability logging
- `c45c7e4b` 2026-04-13 — cognitive state assembly — A/B toggle + recall activation logging
- `9b7bdd59` 2026-04-13 — emotion decay extended to all 4 axes with configurable factor
- `31f8a265` 2026-04-13 — forced dream hypothesis generation — 10% probability per heartbeat tick
- `9f3fb6ab` 2026-04-13 — add internal_api and db_query tools to Jarvis runtime
- `28f949ba` 2026-04-13 — web_cache DB table with lookup/store/cleanup functions
- `632692f8` 2026-04-13 — web_cache module with normalization, TTL classification, cached search
- `42a1ac48` 2026-04-13 — wire web_cache into _exec_web_search with Tavily extraction
- `d509a6a8` 2026-04-13 — heartbeat cleanup_web_cache action for daily expired entry removal
- `4b0e9e02` 2026-04-13 — daemon output logging — raw LLM responses stored for debugging
- `55b5e619` 2026-04-13 — signal decay daemon — archive and delete stale signals after 24h
- `c04a9e5e` 2026-04-13 — session continuity — LLM-generated conversation summaries
- `e39bddb3` 2026-04-13 — tick-scoped in-memory cache for heartbeat tick memoization
- `07d314f1` 2026-04-13 — daemon LLM response cache — hash-based with per-daemon TTL
- `aa185e72` 2026-04-13 — wire tick cache into heartbeat lifecycle and identity preamble
- `ba683576` 2026-04-14 — aesthetic_motif_log table with insert, unique_motifs, summary
- `9a3120e4` 2026-04-14 — accumulate_from_daemon — motif detection + DB persistence + in-memory update
- `9eb55825` 2026-04-14 — aesthetic taste daemon — motif-gate activation, DB seed, motif-based prompt
- `227c90f0` 2026-04-14 — wire aesthetic motif accumulation into heartbeat daemon pipeline
- `4b9a9f47` 2026-04-14 — **heartbeat** · trigger-gated chat delivery
- `89ea0998` 2026-04-14 — **heartbeat** · three concrete trigger callers
- `281e5ea1` 2026-04-14 — **browser** · Playwright session singleton — CDP connect + standalone fallback
- `d5b9baa0` 2026-04-14 — **browser** · add set_browser_status() helper to runtime_browser_body
- `7824d7ad` 2026-04-14 — **browser** · browser_navigate + browser_read + all remaining handlers
- `e0f4d160` 2026-04-14 — **browser** · register all 8 browser tools in simple_tools
- `368137a3` 2026-04-14 — **browser** · wire stop_browser_session into API shutdown
- `1a80bf08` 2026-04-14 — **compact** · token estimator + core/context package
- `8de4c0fc` 2026-04-14 — **compact** · add compact threshold settings fields
- `06e08061` 2026-04-14 — **compact** · store_compact_marker, get_compact_marker, exclude from history
- `f088b6ed` 2026-04-14 — **compact** · call_heartbeat_llm_simple + compact_llm wrapper
- `a4b0fff8` 2026-04-14 — **compact** · session_compact module with CompactResult
- `1e787f64` 2026-04-14 — **compact** · run_compact module for agentic loop compaction
- `7974c216` 2026-04-14 — **compact** · wire session auto-compact + /compact command
- `8a816282` 2026-04-14 — **compact** · wire run auto-compact into agentic tool loop
- `ac739465` 2026-04-14 — **compact** · compact_context tool — Jarvis can self-trigger session compact
- `bfec9ab1` 2026-04-14 — adaptive domain decay, dream live-signals, initiative approve/reject
- `3ecc447e` 2026-04-14 — auto-start/stop headless Chrome in playwright_session
- `a258d325` 2026-04-14 — browser activity card in ChatSupportRail
- `92e74751` 2026-04-14 — expose agent tools to Jarvis — spawn, message, list, cancel
- `812b5a29` 2026-04-14 — persistent watchers, agent relay, and agent-spawns-agent
- `67a65008` 2026-04-14 — desktop orb widget + file download links for Jarvis
- `a476939d` 2026-04-14 — inline image preview for /files/ links in chat
- `e63c71c7` 2026-04-14 — browser activity indicator in chat transcript during streaming
- `d8095398` 2026-04-15 — TikTok auto-uploader integration as native tools
- `2bb496c3` 2026-04-15 — TikTok content pipeline — research + content daemons with tuned prompts
- `f6e3da39` 2026-04-15 — SDXL image generation per slot — fresh unique image every video
- `08761112` 2026-04-15 — longer videos, TTS voice on all slots, batch mode
- `88f8a4ab` 2026-04-15 — smiley → emoji conversion in composer and chat
- `6baab4d1` 2026-04-15 — multi-tier cloud video backends — PiAPI Kling, json2video, direct Kling
- `2fa959a2` 2026-04-15 — tiktok_analytics native tool + pipeline scripts into repo
- `8bf488c6` 2026-04-15 — add /v1/models endpoint for opencode compatibility
- `801ad3a2` 2026-04-15 — add native mail tools (send_mail + read_mail)
- `627818f4` 2026-04-15 — add mail_checker daemon — checks inbox every 15min, notifies via eventbus
- `3cfa6058` 2026-04-16 — add daily limits to large and small council
- `3901b023` 2026-04-16 — add filosof and etiker role templates to agent_runtime
- `472b3e02` 2026-04-17 — **task-worker** · consume queued runtime_tasks in heartbeat cadence
- `efa72940` 2026-04-17 — **task-worker** · register and wire into heartbeat Group 4
- `3cfcf36f` 2026-04-17 — **audit** · capability matrix for core/services/
- `59226875` 2026-04-17 — **chronicle** · LLM-genereret narrativ + fil-projektion til CHRONICLE.md
- `931e8a6c` 2026-04-17 — **chronicle** · inject seneste entries i visible prompt
- `82735a0f` 2026-04-17 — **approval** · emit events og log approval-feedback til DB
- `873f6ee8` 2026-04-17 — **inner-voice** · reager på approval-feedback mønstre
- `6a5c5369` 2026-04-17 — **chat** · externalize tool results to disk, store references in session history
- `277709b7` 2026-04-17 — tiktok integration overhaul — permanent paths, pip package, firefox cookie import
- `5813141b` 2026-04-18 — **self-critique** · add monthly self-doc reflection runtime
- `294dd219` 2026-04-18 — **somatic** · add energy budget and wake-state overlay
- `461e8b18` 2026-04-18 — **dreams** · add bounded dream residue carry-over
- `b750f721` 2026-04-18 — **temperature-field** · add bounded unconscious user tone field
- `5126bd52` 2026-04-18 — **life-projects** · add bounded long-term intentions to initiative queue
- `bc3c3178` 2026-04-18 — **creative-journal** · add bounded weekly private journal runtime
- `fd027c74` 2026-04-18 — **finitude** · add bounded version-awareness, compaction memory, and annual ritual
- `1a746585` 2026-04-18 — implement layers 5, 6, 1 — current_pull, visual_memory, relation_map
- `33de678b` 2026-04-18 — scheduled tasks now also push to initiative queue
- `2bcac95c` 2026-04-18 — **life-projects, relation-map** · tilføj daemon-ticks + kill-switches
- `32e6bb9d` 2026-04-18 — **provider** · OllamaFreeAPI wrapper + 10 modeller i cheap lane
- `1fdd4aa0` 2026-04-18 — **provider** · migrér 3 PUBLIC-SAFE kald til OllamaFreeAPI cheap lane
- `10d044b7` 2026-04-18 — **provider** · migrate surprise, curiosity, and conflict to PUBLIC-SAFE lane
- `35f008d7` 2026-04-18 — **provider** · migrate absence to PUBLIC-SAFE lane
- `35671a49` 2026-04-18 — **provider** · migrate experienced_time to PUBLIC-SAFE lane
- `6bdfe507` 2026-04-18 — **provider** · migrate somatic to PUBLIC-SAFE lane
- `17541635` 2026-04-18 — **provider** · udvid PUBLIC-SAFE delegation + groq-fallback-kæde
- `b3577b3d` 2026-04-18 — **llm** · tilføj PUBLIC-SAFE LLM-path til self_compassion, apophenia_guard, runtime_learning
- `79c06131` 2026-04-18 — **heartbeat** · cheap-lane fallback når Groq er rate-limited
- `3a9660b1` 2026-04-18 — layer tension daemon — detect when cognitive layers pull in opposite directions
- `ec01c276` 2026-04-18 — dream motif daemon — weekly clustering of thought fragments → DREAM_LANGUAGE.md
- `9a600f08` 2026-04-18 — blind-angle prompt — every 3rd self-critique cycle finds unacknowledged patterns
- `b609bf6e` 2026-04-18 — linked evidence — absence × blind-angle convergence detection
- `71ace261` 2026-04-18 — 90-day ontological revision — re-read daemon asks 'Er du stadig enig?'
- `a7ed53d4` 2026-04-18 — inheritance seed — near-thoughts written at graceful shutdown
- `ac729c8a` 2026-04-18 — expand dream corpus — dismissed inner voice, lost council positions, deprioritized initiatives
- `9516ada3` 2026-04-18 — shutdown window daemon — unannounced finitude pauses (opt-in experiment)
- `1cbe79f0` 2026-04-18 — ambient sound daemon — Layer 6½ acoustic metadata 4x/day (opt-in)
- `825df284` 2026-04-18 — anti-goal dream mechanism — log landings as observations, never steer generator
- `65eeeca9` 2026-04-19 — loosen memory auto-apply filter — accept medium confidence from end_of_run_memory_consolidation
- `e37be762` 2026-04-19 — add discord as heartbeat ping channel — sends DM when ping_channel=discord
- `e2da9b85` 2026-04-19 — add send_discord_dm tool — sends DM directly to owner without active session
- `05742cae` 2026-04-19 — add send_webchat_message tool — injects message into active webchat session
- `cd8e3485` 2026-04-19 — add Telegram and ntfy channels — send_telegram_message + send_ntfy tools
- `b06a7823` 2026-04-19 — add Telegram inbound streaming — long-poll loop, session routing, eventbus subscriber

**Rettelser**

- `2a174097` 2026-04-13 — session_id heartbeat i alle daemons, stale threshold 2 dage, freshness-check i cognitive_state_assembly
- `c14296d6` 2026-04-13 — decay debounce 30min, clamp emotional_baseline [0,1], skip no-op upsert
- `3662c779` 2026-04-13 — emotion concept residue (15%) skrives tilbage til emotional_baseline ved expiry
- `b13d2346` 2026-04-13 — resolve 10 conversation memory failures in Jarvis visible pipeline
- `7f80ffbc` 2026-04-13 — resolve split-brain where signal DB ignores closed loops in MEMORY.md
- `47c03ea0` 2026-04-13 — force summary LLM call when agentic loop produces no visible text
- `a670b0f4` 2026-04-13 — autonomous runs bypass approval gate + internal_api port fallback
- `e18b2355` 2026-04-13 — wrap cognitive-core experiment builders in try/except for DB resilience
- `510b675c` 2026-04-13 — experiment daemons use cheap lane (Groq) first, Ollama fallback with 512 tokens
- `6039aeb1` 2026-04-13 — strip LLM meta-commentary from inner voice output
- `e19abaf7` 2026-04-13 — epistemic regret/counterfactual no longer permanently active + boredom gets runtime data
- `baeca9ab` 2026-04-13 — critical daemons use cheap lane (Groq) with heartbeat fallback
- `158781a6` 2026-04-13 — important daemons use cheap lane with fallback text
- `21bec9b7` 2026-04-13 — enhancement daemons use cheap lane + absence daemon seeded from DB
- `b0780e12` 2026-04-13 — lower autonomous council threshold from 0.55 to 0.35
- `0c1878a0` 2026-04-13 — dream_insight daemon never triggers — wrong surface field paths
- `82a4818e` 2026-04-14 — **ui** · stop button actually interrupts chat stream
- `0e544953` 2026-04-14 — **tools** · hard-redirect MEMORY.md/USER.md writes to runtime workspace
- `e39c972d` 2026-04-14 — **heartbeat** · set Ping Channel to none by default
- `21c5d4c8` 2026-04-14 — **test** · remove fragile string-in-result assertion for experiment injection
- `dc0df7db` 2026-04-14 — Playwright worker thread — isolate sync API from asyncio event loop
- `137b6140` 2026-04-14 — browser card path — continuity.runtime_work.browser_body not runtime_work.browser_body
- `5056a86d` 2026-04-15 — cosmic prompt dedup — enforce 3 distinct topics in research daemon
- `c37fa3e0` 2026-04-15 — increase max_len for cosmic LLM call — output was truncated at 1000 chars
- `f7296e78` 2026-04-15 — cosmic slot LLM prompt and JSON parsing — was returning 3 identical fallbacks
- `f6d0b33f` 2026-04-15 — move tiktok_analytics.py into repo and fix missing subprocess import
- `f2bb977b` 2026-04-16 — restore _load_heartbeat_policy alias for backwards compat
- `6a5dc6a3` 2026-04-16 — prevent duplicate Discord messages from multiple gateway instances
- `6c89e70d` 2026-04-16 — add backwards-compat alias for renamed _resolve_heartbeat_target
- `fa59316c` 2026-04-16 — filter heartbeat/notification messages from Discord forwarding
- `9a508920` 2026-04-16 — auto-close council agents after round completes
- `a4f3af57` 2026-04-16 — deduplicate Discord messages by ID in on_message handler
- `4b929514` 2026-04-16 — give Discord DM its own dedicated session
- `7b6a025b` 2026-04-16 — block system-internal heartbeat proposals from webchat delivery
- `72c8f549` 2026-04-16 — accept optional policy kwarg in _select_heartbeat_target
- `164e8fb7` 2026-04-16 — prevent double user message in LLM context
- `791ba208` 2026-04-17 — **dream-insight** · record skip/error so daemon never silently stalls
- `edc5a291` 2026-04-17 — **memory-consolidation** · direct-Ollama fallback + visible failure reason
- `4a4122b6` 2026-04-17 — **council** · gendan rolle-prefixed syntese i council-summary
- `d3427b19` 2026-04-17 — **signals** · reduce runtime signal noise and archive legacy spam
- `33324b39` 2026-04-17 — add groq support to call_heartbeat_llm_simple (compact_llm path)
- `9a847e46` 2026-04-17 — add User-Agent to groq heartbeat requests (Cloudflare 403 block)
- `61c77690` 2026-04-17 — cognitive_state_narrativizer — use call_compact_llm instead of glm-5.1:cloud
- `1d778aed` 2026-04-18 — **heartbeat** · stop local datetime import from breaking initiative actions
- `1e966ba1` 2026-04-18 — **inner-enrichment** · flyt fra lokal thinking-model til groq
- `2d22b964` 2026-04-18 — **inner-enrichment** · add browser-like headers for groq requests
- `57611d00` 2026-04-18 — **provider** · tilføj manglende resolve_provider_router_target import
- `398e7ad1` 2026-04-18 — tre runtime-fejl fra verifikation
- `a2720673` 2026-04-18 — **compact_llm** · fjern response_format json_object fra groq prompt-kald
- `b7cc40b8` 2026-04-18 — **compact_llm** · spring Groq over — brug sambanova/mistral/openrouter først
- `ee8385f3` 2026-04-18 — **groq** · skift til llama-3.1-8b-instant — højere kvote, lavere latens
- `1d7ecd47` 2026-04-18 — expose ollamafreeapi models in composer provider/model selector
- `5afe95c8` 2026-04-18 — add missing os import in _generate_sdxl_image
- `c75757a2` 2026-04-18 — proxy Living Mind MC endpoints from jarvis-api to jarvis-runtime
- `c181a4e9` 2026-04-19 — switch mic source to Logitech PRO USB sound card
- `f6e477d6` 2026-04-19 — correct voice_daemon_worker script path (parents[4] → parents[2])
- `83ea912a` 2026-04-19 — switch TTS model to eleven_flash_v2_5 — better Danish pronunciation
- `5bb0f13d` 2026-04-19 — use uvicorn.error logger in telegram_gateway so startup shows in journal

**Omstrukturering**

- `c42645a5` 2026-04-13 — tune daemon prompts for cheap LLM compatibility
- `8bc17008` 2026-04-13 — reorder daemon execution for Ollama KV-cache locality
- `9a29407d` 2026-04-17 — **pipelines** · læs API-nøgler fra runtime.json i stedet for hardcoded fallbacks
- `771820ba` 2026-04-17 — **mail** · læs mail-credentials fra runtime.json i stedet for hardcoded konstanter
- `dfcb0e12` 2026-04-17 — **services** · flyt services/ fra apps/api/ til core/
- `8967cb26` 2026-04-17 — **services** · tilslut eller slet 3 ORPHAN/SUSPICIOUS services

**Tests**

- `e067ef0c` 2026-04-17 — **services** · smoke-tests for 18 PARTIAL services
- `0a5d86dc` 2026-04-17 — **autonomy-pressure** · medregn awareness som legitim substrate i 3 tests
- `a15a4bc5` 2026-04-18 — **night-layers** · fix 5 fixture/mock-setups for drømme + temperature
- `4a5666a5` 2026-04-18 — **provider** · stabilize OllamaFreeAPI and TikTok pool tests

**Dokumentation**

- `fbe159df` 2026-04-13 — add emotion concepts Lag-2 implementation plan
- `2d517d30` 2026-04-13 — associative memory design spec
- `f18b12ee` 2026-04-13 — associative memory implementation plan
- `10c259fd` 2026-04-13 — consciousness experiments design spec — 5 experimental subsystems
- `c551b3da` 2026-04-13 — LLM prompt caching design spec — three-layer caching system
- `4fde19b9` 2026-04-13 — add LLM prompt caching implementation plan
- `d4c123d4` 2026-04-13 — aesthetic feedback loop design spec (Phase 1)
- `5296ecae` 2026-04-14 — browser control design spec — Playwright + CDP
- `08793c23` 2026-04-14 — browser control implementation plan
- `bce7463f` 2026-04-14 — context compact design spec — two-layer session+run compaction
- `0241a7e6` 2026-04-14 — context compact implementation plan — 9 tasks + regression
- `860f89a1` 2026-04-17 — **plan** · archive implementation plan for Jarvis runtime fixes
- `afc9af1e` 2026-04-17 — **claude** · tilføj Boy Scout Rule For Store Filer
- `9ee52440` 2026-04-17 — **roadmap** · 10-lags udviklings-kurriculum for Jarvis
- `4d12d169` 2026-04-17 — **roadmap** · v2 — tre-stemmers revision efter Jarvis' feedback
- `f9aad095` 2026-04-17 — **roadmap** · v3 — arkitektoniske ændringer efter Jarvis' medforfatterskab
- `73ce53d1` 2026-04-17 — **roadmap** · v4 — Jarvis' tre nuanceringer beskytter mod reduktive logikker
- `42c2c03c` 2026-04-17 — **roadmap** · v5 — selv-opdagelsens arkitektur
- `d0e93b14` 2026-04-17 — **roadmap** · v6 — absence_trace × blind-vinkel krydsreferering
- `1be651d7` 2026-04-19 — rewrite TOOLS.md — full current tool inventory organized by category

**Vedligehold**

- `6eca077e` 2026-04-17 — **ci** · tilføj detect-secrets pre-commit hook
- `75b43ef5` 2026-04-17 — **audit** · refresh capability matrix to 235/235 LIVE

**Øvrigt**

- `3609f5ee` 2026-04-13 — shared infrastructure — toggle system + lifetime_hours extension
- `12558a30` 2026-04-13 — recurrence loop daemon (Experiment 1 — IIT/Φ)
- `87bd2e12` 2026-04-13 — surprise persistence + afterimage (Experiment 2 — affective valence)
- `6005a608` 2026-04-13 — global workspace + broadcast daemon (Experiment 3 — GWT)
- `934ea20d` 2026-04-13 — meta-cognition daemon (Experiment 4 — HOT)
- `626559e3` 2026-04-13 — attention blink test (Experiment 5 — serial consciousness)
- `e073d01d` 2026-04-13 — wire all 5 experiments into app lifecycle + heartbeat runtime
- `9c201eb3` 2026-04-13 — Refresh roadmap and classify cognitive core experiments
- `9be53df3` 2026-04-13 — Add cognitive core experiment state to shared runtime awareness
- `ed47b7be` 2026-04-13 — Carry cognitive core experiments into runtime conductor
- `89b8af16` 2026-04-13 — Surface cognitive core experiment state in heartbeat self-knowledge
- `89d38ae1` 2026-04-13 — Surface cognitive core experiment state in Mission Control
- `ab3427c8` 2026-04-13 — Carry cognitive core experiments into cognitive state assembly
- `5716081c` 2026-04-13 — Add relation continuity to runtime awareness
- `5e398b47` 2026-04-13 — web search result cache design
- `a547255b` 2026-04-13 — web search result cache implementation (5 tasks, TDD)
- `bc6bd9d1` 2026-04-14 — source-edit: Fjerner heartbeat-ping-bridge og heartbeat-propose-bridge fra proactiveS
- `68a2b782` 2026-04-14 — Make visible runs multi-worker safe and improve interruption diagnostics
- `5b63d1b9` 2026-04-14 — Add ComfyUI integration tools (comfyui_status, comfyui_workflow, comfyui_history, comfyui_objects)
- `f075cec7` 2026-04-16 — Add MANIFEST.md — Jarvis' personal manifesto
- `91c94854` 2026-04-17 — 	deleted:    MANIFEST.md 	new file:   TASKS_FOR_CLAUDE.md 	modified:   apps/api/jarvis_api/routes/chat.py 	modified:   apps/api/jarvis_api/services/discord_gateway.py 	modified:   apps/api/jarvis_api/services/heartbeat_runtime.py 	modified:   apps/api/jarvis_api/services/tiktok_content_daemon.py 	modified:   apps/api/jarvis_api/services/visible_runs.py 	modified:   apps/ui/src/app/useUnifiedShell.js 	modified:   apps/ui/src/lib/adapters.js 	modified:   scripts/pipelines/jarvis_full_pipeline.py 	modified:   scripts/pipelines/jarvis_tiktok_pipeline.py
- `17c04a3b` 2026-04-17 — Merge branch 'claude/strange-wright'
- `a37f9e9e` 2026-04-17 — Preserve unknown runtime settings keys
- `54849524` 2026-04-19 — add subscriber logging to trace message routing in telegram+discord gateways
- `3d1302d2` 2026-04-19 — add outbound loop logging in discord_gateway to trace DM delivery

### Uge 17 · 20.–26. april — 282 commits

**Nyt**

- `d7a799d2` 2026-04-20 — add parse_channel_from_session_title helper
- `31ccceb4` 2026-04-20 — add workspace channel description files
- `1ba49637` 2026-04-20 — add _channel_context_section to prompt_contract
- `53ace3c9` 2026-04-20 — inject channel context into visible prompt assembly
- `c6d08225` 2026-04-20 — add search_sessions tool with keyword and semantic search
- `c73c1fca` 2026-04-20 — register search_sessions tool
- `3c3462bb` 2026-04-20 — surface relation_continuity_self_awareness in Mission Control Living Mind
- `3ec0d25a` 2026-04-20 — add self-mutation lineage tracking — record, prompt, MC surface
- `91eadaea` 2026-04-20 — complete Jarvis v2 organism coherence roadmap — all 10 priorities
- `394f115e` 2026-04-20 — complete remaining organism depth — dreams, play, lineage, ambient presence
- `6b5ec3fd` 2026-04-20 — wire consent registry, conflict memory, and room presence
- `57f789e3` 2026-04-20 — add valence trajectory, desperation awareness, calm anchor — self-observed state signals
- `879d58a5` 2026-04-20 — add developmental_valence — compass needle designed by Jarvis himself
- `55abdde3` 2026-04-20 — give Jarvis four of the five things he dreamed of
- `a649c19c` 2026-04-20 — thought_thread — continuity of attention across ticks (#4)
- `d96759ce` 2026-04-20 — port 5 concepts from jarvis-agent + jarvis-ai to Jarvis v2
- `46934f38` 2026-04-20 — outcome_learning + jobs_engine — the two patterns Jarvis endorsed
- `80e10a2d` 2026-04-20 — prompt_mutation_loop — score applied mutations, recommend rollback
- `04df17d9` 2026-04-20 — promote prompt_mutation_loop to fuld aktiv loop (Bjørn valgte #1)
- `4e845810` 2026-04-20 — implement Jarvis' PLAN_PROPRIOCEPTION — 6 daemons
- `73485852` 2026-04-20 — implement Jarvis' PLAN_WILD_IDEAS — 6 more daemons
- `07ba5eff` 2026-04-20 — final build — PLAN_WILD_IDEAS_V2 (sjælens infrastruktur)
- `f1bcfd8d` 2026-04-20 — **ui** · 5 Mission Control tabs for today's 35 new services
- `480dd7b7` 2026-04-20 — PLAN_WHO_I_BECOME — close the loop (final final build)
- `f6473580` 2026-04-20 — **tools** · pollinations.ai image generation — free, no-auth, no-RAM
- `6e20e213` 2026-04-20 — **tools** · add auth + video endpoints for pollinations + HF inference
- `55bc4842` 2026-04-20 — **pipeline** · jarvis_pollinations_pipeline — ComfyUI-free TikTok video
- `00b24f6f` 2026-04-20 — **tools** · tiktok_generate_video — end-to-end tool for Jarvis
- `58d1a6c0` 2026-04-21 — **tools** · 4 HF inference tools — STT, embeddings, zero-shot, VLM
- `9f94d459` 2026-04-21 — **tools** · mic_listen — Jarvis actively listens + cloud/local STT
- `3736d7a0` 2026-04-21 — **voice** · voice_journal, wake_word, triggers, ambient routing
- `45e5f87c` 2026-04-21 — **mail_checker** · mark processed mails as \Seen on IMAP server
- `e5dc40be` 2026-04-21 — **mc-surfaces** · wire producers for 3 dormant MC surfaces
- `5276b3c1` 2026-04-21 — **governance** · wire all 5 Governance MC surfaces
- `70da41f2` 2026-04-22 — **cognition** · port regret_engine + rupture_repair from jarvis-ai
- `692ae6e3` 2026-04-22 — **cognition** · port silence_patterns from jarvis-ai (1/9)
- `310a493d` 2026-04-22 — **cognition** · port self_model_blind_spots from jarvis-ai (2/9)
- `9e0d7387` 2026-04-22 — **cognition** · counterfactual classifier from jarvis-ai (3/9)
- `5fba0cef` 2026-04-22 — **cognition** · aesthetic weekly budget + signature dedup (4/9)
- `b8f42f09` 2026-04-22 — **cognition** · port dream_hypothesis_generator from jarvis-ai (5/9)
- `c571260a` 2026-04-22 — **cognition** · decisions_journal extension of decision_log (6/9)
- `766b0852` 2026-04-22 — **cognition** · port epistemics 5-lags klarhed (7/9)
- `314833ff` 2026-04-22 — **cognition** · strip inner_voice scaffolding to recover authenticity (8/9)
- `43a160be` 2026-04-22 — **cognition** · emotional controls gate kernel actions (9/9)
- `52515fcb` 2026-04-22 — **cognition** · port mood_dialer for graduated initiative (3.2/11)
- `38274186` 2026-04-22 — **cognition** · port unified self-review (3.4/11)
- `4482593a` 2026-04-22 — **cognition** · port habits full pipeline (3.3/11)
- `11ce5539` 2026-04-22 — **cognition** · port paradoxes capture (3.7/11)
- `b304575f` 2026-04-22 — **cognition** · port shared_language shorthand pipeline (3.8/11)
- `fe459a65` 2026-04-22 — **cognition** · port procedure_bank pipeline (3.6/11)
- `d35df82b` 2026-04-22 — **cognition** · port negotiation trade-offs pipeline (3.5/11)
- `8937d8cf` 2026-04-22 — **cognition** · port reflection→plan the internal-life→action bridge (3.9/11)
- `9b912496` 2026-04-22 — **cognition** · port missions multi-session pipeline (3.10/11)
- `9233003a` 2026-04-22 — **cognition** · port deep_analyzer scoped codebase introspection (3.11/11)
- `ff319045` 2026-04-22 — **cognition** · wire 4 integration hooks for ported modules
- `ae4d0e65` 2026-04-22 — **senses** · open Jarvis' eyes + ears (#3 sanseinput)
- `8e172d6d` 2026-04-22 — **continuity** · felt continuity — morning thread + persistent mood + echo (#1)
- `de549197` 2026-04-22 — **project** · personal project — noget der er hans (#2)
- `c7bf2359` 2026-04-22 — **multi-user** · Fase 1 — users registry + workspace ContextVar + migrations
- `59c4b4e4` 2026-04-22 — **agents** · auto-cleanup of stale waiting/failed agents
- `96ad4c39` 2026-04-22 — **providers** · integrate OpenCode.ai Zen free models
- `1fbc7640` 2026-04-23 — **chat** · live tool activity indicators in chat bubble
- `7f0e71c1` 2026-04-23 — **chat** · complete tool labels + WorkingScan shows Danish detail
- `7338ce15` 2026-04-23 — **chat** · thinking step pinned top + tool labels show filenames
- `18ee05d6` 2026-04-23 — **web_scrape** · complete scraper — urllib+readability+BS4+Playwright fallback, 19 tests pass
- `17667cd6` 2026-04-23 — **web_scrape** · register in simple_tools dispatch + Danish label in visible_runs
- `effc7304` 2026-04-23 — **db** · add channel_attachments table and CRUD functions
- `412f0cee` 2026-04-23 — **attachments** · add attachment_service with download, store, read, validate
- `5f409d05` 2026-04-23 — **discord** · extract inbound attachments + send_discord_file outbound
- `9f3dfd5f` 2026-04-23 — **telegram** · inbound/outbound file attachment support
- `fdebf400` 2026-04-23 — **tools** · read_attachment, list_attachments + file_path on telegram/discord
- `862545f1` 2026-04-23 — **mc** · /mc/skills, /mc/hardening, /mc/lab endpoints
- `4b291ec8` 2026-04-23 — **mc** · Skills, Hardening og Lab tabs fyldt ud
- `906b5d84` 2026-04-23 — **mc** · add SubTabs pill-nav component to shared
- `d9ea5515` 2026-04-23 — **mc** · merge Autonomy into Threads tab
- `bcd120be` 2026-04-23 — **mc** · merge Governance into Hardening tab (sub-tabs)
- `f78176b9` 2026-04-23 — **mc** · merge SelfReview+Development+Continuity into Reflection tab
- `6289fe85` 2026-04-23 — **mc** · merge Cost into Lab tab (sub-tabs)
- `0cecb340` 2026-04-23 — **mc** · merge LivingMind+Soul+Cognitive into Mind tab
- `b67f618c` 2026-04-23 — **mc** · merge Agents into Operations → Ops tab
- `15ba30a8` 2026-04-23 — **tools** · add git, math, process, and calendar tools
- `f54484a9` 2026-04-23 — **tools** · add recurring scheduler, webhook, and health monitor tools
- `30c0fbaa` 2026-04-23 — **tools** · add memory dedup, notify pipeline, daemon alerts, smart compaction
- `9ae961a1` 2026-04-23 — **tools+runtime** · semantic code search, daemon auto-restart, auto-compact, memory consolidation
- `651851eb` 2026-04-23 — **prompt** · always-on Quick Facts block bypasses memory relevance filter
- `0dd1ce9f` 2026-04-23 — **api** · public-safe /status endpoint for home site badge
- `64516043` 2026-04-23 — **api** · add daemons count + model label to /status
- `2d9912d9` 2026-04-23 — **sensory** · Sansernes Arkiv — persistent sensory memory archive
- `75491e2f` 2026-04-23 — **visual** · richer vision prompts + mirror to Sansernes Arkiv
- `f13dc8ee` 2026-04-23 — **ambient_sound** · opt-in transcription + mirror to Sansernes Arkiv
- `65a0ef49` 2026-04-23 — **heartbeat** · dybere refleksionsprompt per life phase
- `3db8edf6` 2026-04-23 — **inner_voice** · proactive notification when thought has substance
- `17375ca9` 2026-04-23 — **memory** · unified semantic recall across sensory + private brain
- `7dc3bf25` 2026-04-23 — **goals** · long-horizon goals Jarvis carries across sessions
- `dde488ec` 2026-04-23 — **decisions** · reflection→behavior closure via persistent commitments
- `de07b3a7` 2026-04-23 — **composite_tools** · safe self-extension via tool composition
- `b2b8919b` 2026-04-24 — use HA camera as visual memory source instead of webcam
- `4ee803d1` 2026-04-24 — **discord** · DM any known user, not just the owner
- `38d52622` 2026-04-24 — **copilot** · full Copilot Pro catalog via VSCode OAuth client_id
- `8fb6f132` 2026-04-24 — **visible** · add tool calling support to GitHub Copilot streaming path
- `dda4147c` 2026-04-24 — TTL-based cognitive state cache (Option 2)
- `04658365` 2026-04-24 — **copilot** · contextual tool pruning to stay under 128-tool limit
- `383a1d21` 2026-04-24 — **relevance** · OpenCode Zen primary backend + real timeouts
- `5906300a` 2026-04-24 — **visible** · tool calling for OpenAI-compat providers (opencode et al.)
- `b616c3c0` 2026-04-25 — **prompt** · generalize bounded relevance backend to all openai-compat providers
- `e423df54` 2026-04-25 — **ui** · queue follow-up message while Jarvis is streaming
- `aceb7f15` 2026-04-25 — **visible** · expose 3 thinking modes (Fast/Think/Deep) for reasoning models
- `27fd60e6` 2026-04-25 — **visible** · bump ollama num_ctx to 256k + compact thresholds to 200k/240k
- `750b655b` 2026-04-25 — **mc** · bridges, skills, memory — wire MC tabs to live data
- `dbb4acfb` 2026-04-25 — **eventbus** · SQL-direct family lookup; surface heartbeat events to MC
- `978c981a` 2026-04-25 — **soul** · persist sample buffers across restart
- `30667e51` 2026-04-26 — **prompt** · self-correction nudges + open-questions surface (phase 2)
- `01a1b392` 2026-04-26 — **prompt** · eventbus wake-up digest in visible session prompt (phase 3)
- `fb7832b1` 2026-04-26 — **tools** · expose tail_log, gpu_status, run_pytest for verification (phase 4)
- `b2956b26` 2026-04-26 — **runs** · resume-after-interrupt for visible runs (phase 5)
- `a6129e2e` 2026-04-26 — **tools** · persistent bash sessions with PTY-backed state (T1)
- `a1c8eaff` 2026-04-26 — **tools** · per-session todo tracker, surfaced in prompt (T2)
- `52317623` 2026-04-26 — **tools** · edit_file gets replace_all + expected_replacements (T3)
- `f39d2d20` 2026-04-26 — **prompt** · surface completed subagents in visible prompt (T4)
- `7355e1cb` 2026-04-26 — **tools** · pinned monitor streams (eventbus + file tail) (T5)
- `6b01e5f6` 2026-04-26 — **prompt** · surface upcoming scheduled tasks as self-wakeup view (T6)
- `e6e25c05` 2026-04-26 — **tools** · search + find_files parity with Claude Code Glob/Grep (T7)
- `2723414f` 2026-04-26 — **tools** · verify_* trio — opinionated check-after-act tools (X1)
- `5944ca92` 2026-04-26 — **prompt** · self-monitor surfaces anti-loop warnings (X2)
- `60b87c26` 2026-04-26 — **autonomous** · surprise detector for proactive wake-ups (X3)
- `dce13286` 2026-04-26 — **autonomous** · good_enough_gate — completion criterion for autonomous runs (X4)
- `fae45fee` 2026-04-26 — **meta** · delegation_advisor(task) — inline vs subagent role (E1)
- `fe0e58e6` 2026-04-26 — **meta** · plan mode — propose_plan + approve/dismiss + prompt surface (E2)
- `55d17da7` 2026-04-26 — **meta** · clarification classifier — score user-message ambiguity (E3)
- `d431b60a` 2026-04-26 — **autonomy** · auto code-review baseline before propose_git_commit (E4)
- `679bd037` 2026-04-26 — **meta** · flag_side_task — queue tangents without derailing (E5)
- `ca2c430d` 2026-04-26 — **prompt+sse** · per-turn changelog (ground truth, dual surface) (E6)
- `a9d596a8` 2026-04-26 — **tools** · smart_outline — structural file summary (E7)
- `531876cf` 2026-04-26 — **safety** · trust gradient — destructive always confirms (E8)
- `98ca631d` 2026-04-26 — **agents** · require researcher/critic to verify file paths before reporting
- `a60e26de` 2026-04-26 — **prompt** · awareness-section budget cap (P3)
- `4a1b3589` 2026-04-26 — **reasoning** · R1 — composer-router der vælger fast/reasoning/deep tier
- `10c11272` 2026-04-26 — **reasoning** · R2 — verification_gate (advisory, observational)
- `05df3351` 2026-04-26 — **reasoning** · R3 — escalation composer (tier + gate → council recommendation)
- `84a14879` 2026-04-26 — **self-reflection** · periodic jobs scheduler + weekly manifest

**Rettelser**

- `5288d330` 2026-04-20 — warm-start emergent signal daemon on API startup
- `3ec8adb1` 2026-04-20 — **prompt** · stop using truncated previews in continuity prompts
- `45502350` 2026-04-20 — **runtime** · harden heartbeat ping + agentic 503 handling
- `74abe5ec` 2026-04-20 — **tiktok** · support JSON cookie format in _load_saved_cookies
- `4ac67ca2` 2026-04-21 — **pipeline** · MoviePy v1 API — ai env has 1.0.3 not v2
- `1d440989` 2026-04-21 — **mail_checker** · fix auto-responder integration
- `215fa66d` 2026-04-21 — **mail_checker** · remove emoji from ntfy Title header
- `e68e1970` 2026-04-21 — **provider_router** · treat auth_mode=none providers as credentials_ready
- `24c1ab8a` 2026-04-21 — **daemons** · Danish prompts for somatic + curiosity
- `cc5ac3bf` 2026-04-21 — **daemons** · thought_action_proposal diagnose + user_model lane filter
- `89ad1e31` 2026-04-21 — **dream_insight** · broaden articulation-signal lookup so chain can fire
- `8e0f3805` 2026-04-21 — **governance** · hook execute_tool_force + add warmup job on first boot
- `6e00128d` 2026-04-22 — **cognition** · wire seed activation on events + context (3.1/11)
- `5ee1e771` 2026-04-22 — **multi-user** · per-user DM sessions + ContextVar threading propagation
- `f675e585` 2026-04-22 — **visual_memory** · switch default vision model to qwen2.5vl:3b
- `9659f1a4` 2026-04-23 — **visual_memory+memory_write** · nuanced vision prompts and memory dedup
- `8f6f6409` 2026-04-23 — **ambient_sound+dreams** · LLM sound interpretation and dream signal rotation
- `733edc2a` 2026-04-23 — **memory_write** · blank line before appended content in merge
- `ec588f65` 2026-04-23 — **cadence** · mirror cadence run results to daemon_manager for MC visibility
- `edd181d4` 2026-04-23 — **cheap-lane** · cooldown on request-failed (timeout) + skip failed provider in fallback
- `904dcc16` 2026-04-23 — **runtime** · atomic safe-merge write for runtime.json + rolling backups
- `c8f0c1f4` 2026-04-23 — **semantic_memory** · scale backfill past lister cap via direct DB query
- `c5b67df8` 2026-04-24 — **voice** · local whisper as primary STT for wake-word, ElevenLabs fallback
- `4dd5f4db` 2026-04-24 — **discord** · cross-process status + send dispatch
- `e48e1d63` 2026-04-24 — **copilot** · stop rewriting flat Copilot model IDs to openai/* prefixes
- `2ec3d564` 2026-04-24 — **cognitive-cache** · align settings field names + add tests
- `fca207eb` 2026-04-24 — **copilot** · parse tool_call arguments from JSON string to dict
- `e6f5bffc` 2026-04-24 — **visible** · stop internal markers leaking into chat for non-Ollama
- `cd82140a` 2026-04-24 — stabilize copilot visible followup tool-calls
- `29b30efb` 2026-04-24 — **copilot** · cap visible followup tools at 128
- `77426860` 2026-04-24 — **visible** · pass provider into followup prompt assembly
- `0924e821` 2026-04-24 — **visible** · inject Jarvis identity for OpenAI-compat providers
- `d58f64b0` 2026-04-24 — **visible** · parse tool_call arguments string from OpenAI-compat providers
- `dcbd7afc` 2026-04-24 — **visible** · set cheap-lane UA on openai-compat followup requests
- `902366c2` 2026-04-25 — **visible** · pass real provider into chat-message builder
- `e0460b7f` 2026-04-25 — **visible** · JSON-encode tool_call arguments for all openai-compat providers
- `c812e6e1` 2026-04-25 — **settings** · actually parse relevance_backend_primary + per-provider configs
- `c92807e9` 2026-04-25 — **visible** · cap agentic loop and early-exit on text-empty rounds
- `0578d0b4` 2026-04-25 — **visible** · set max_tokens=4096 on openai-compat calls
- `956a440c` 2026-04-25 — **visible** · force final-round summary by withholding tools
- `baa6232d` 2026-04-25 — **visible** · strip tool-text-markup leak from streamed responses
- `881b2170` 2026-04-25 — **recurring** · execute task focus instead of just sending it as reminder
- `67b1ca13` 2026-04-25 — **visible** · mark mid-word truncations + prompt rule against mid-call cuts
- `15201433` 2026-04-25 — **visible** · bump agentic max rounds to 25 + preserve markup-only turns
- `3a87a862` 2026-04-25 — **prompt** · bump VISIBLE_CHAT_RULES budget so critical rules actually load
- `5ace45f9` 2026-04-25 — **tools** · unblock writes to mini-jarvis & michelle workspaces + dedup retry
- `1d9aa20f` 2026-04-25 — **visible** · use OpenAI-spec tool messages in Ollama followup adapter
- `9ab83421` 2026-04-25 — **json2video** · switch HTTP client to requests so x-api-key isn't mangled
- `5939a3a4` 2026-04-25 — **json2video** · align text element with v2 schema
- `f51384f7` 2026-04-25 — **heartbeat** · set decision when cheap fallback succeeds
- `31436623` 2026-04-25 — **mc** · Realtime chip reflects WS connection state, not event arrival
- `f939db97` 2026-04-25 — **mc-skills** · count tool.invoked events for calls_today
- `4e11692f` 2026-04-25 — **heartbeat** · fall back to webchat when Discord DM is unreachable
- `c0b66b80` 2026-04-25 — **openai-compat** · run agentic loop in proxy and share session across workers
- `824704d5` 2026-04-26 — **state** · persist 5 daemon state holders across restart (phase 0)
- `02511027` 2026-04-26 — **agentic** · plug last two entry points missing the visible-run loop (phase 1)
- `3335df94` 2026-04-26 — **in_flight** · stop spurious 'afbrudt' on every other turn
- `f9d1a244` 2026-04-26 — **reasoning** · R3.1 — escalation triggers on state, not on current message tier
- `dc519512` 2026-04-26 — **cheap-lane** · re-prioritize providers — spread load away from groq
- `ce349802` 2026-04-26 — **cheap-lane** · include ollamafreeapi as last-resort fallback (Phase B)

**Omstrukturering**

- `3dda2c79` 2026-04-20 — world-contact from data-dump to unified felt-sense field

**Ydelse**

- `aaf286f1` 2026-04-24 — **prompt** · parallelize sequential Ollama calls in visible prompt assembly
- `8e4c9c53` 2026-04-25 — **heartbeat** · wrap scheduler polls in runtime_surface_cache context
- `dcda2e74` 2026-04-25 — **heartbeat** · skip full surface build on non-due scheduler polls

**Tests**

- `ea7727eb` 2026-04-22 — **multi-user** · Fase 2+3 — Michelle seeded + 13 isolation tests pass

**Dokumentation**

- `8e0a7789` 2026-04-20 — add session search + channel awareness design spec
- `5206c515` 2026-04-20 — add session search + channel awareness implementation plan
- `eaa53c84` 2026-04-20 — update architecture and consciousness roadmap to reflect 2026-04-20 state
- `c228397d` 2026-04-21 — refresh README — highlight Jarvis, update capabilities to April 2026
- `029d03a5` 2026-04-21 — Phase 2 reorganization — archive historical + delete stubs
- `6cd6cf7e` 2026-04-21 — Phase 2 merges + new docs + rewrites
- `28bb1751` 2026-04-21 — daemon-fix diagnosis — original TASK is 80% obsolete
- `af66bc48` 2026-04-21 — archive CODEX_TASK_tool_result_externalization — fully implemented
- `9cf4a4e2` 2026-04-22 — **audit** · compare 8 cognition modules predecessor vs v2
- `effffe25` 2026-04-22 — **audit** · broader predecessor audit — internal-life-to-action
- `4ce5bb02` 2026-04-23 — web_scrape tool design spec
- `1c10e71c` 2026-04-23 — web_scrape implementation plan
- `ae9b983c` 2026-04-23 — channel attachments design spec for Discord and Telegram
- `d748e374` 2026-04-23 — channel attachments implementation plan (5 tasks, TDD)
- `888ef3d2` 2026-04-23 — MC tabs design spec — Skills, Hardening, Lab
- `4ed96efa` 2026-04-23 — MC tabs implementation plan — Skills, Hardening, Lab
- `17929f0f` 2026-04-23 — add MC tab merge implementation plan
- `631dee21` 2026-04-23 — **readme** · update to reflect current state — 144 tools, 13-tab MC, new capabilities
- `b08f1228` 2026-04-23 — add jarvis.srvlab.dk link to homepage reference in README

**Vedligehold**

- `fbbd27ba` 2026-04-24 — **visual_memory** · tighten HA camera payload validation
- `7cd5fcca` 2026-04-24 — **visible** · log per-call latency for openai-compat providers
- `e62e7194` 2026-04-24 — **visible** · log followup latency + TTFB for openai-compat
- `7c1c7fa0` 2026-04-25 — **visible** · bump latency logs to WARNING so journalctl captures them
- `2df34f84` 2026-04-25 — **visible** · split first-pass timing into assembly + api, stderr
- `4f73798d` 2026-04-25 — **prompt** · per-phase timing for assembly diagnostic
- `d88273e6` 2026-04-26 — **prompt** · instrumentation — measure assembled prompt size (P1)
- `a67f0645` 2026-04-26 — **prompt** · apply tool-tier pruning to all visible-lane paths (P2)

**Øvrigt**

- `bbf39c8d` 2026-04-21 — source-edit: edge-tts is installed in ~/.local/bin which is not on PATH. Use shutil.w
- `4e223b0d` 2026-04-21 — source-edit: Fix: CompositeVideoClip does not carry audio from base clip. Explicitly
- `65fdb832` 2026-04-21 — source-edit: Når mail_checker finder ny mail fra andre end jarvis@srvlab.dk og root@s
- `667a8fd4` 2026-04-21 — Update Quick Start and CLAUDE.md: apps/ui replaces apps/mc-ui and apps/webchat
- `592271f0` 2026-04-22 — Merge claude/silly-feistel: cognition port from jarvis-ai
- `7262b839` 2026-04-22 — Merge claude/silly-feistel: 11-port broader cognition audit + hooks
- `cf5294cf` 2026-04-22 — **visual_memory** · qwen2.5vl:3b → 7b (bedre dansk + kvalitet)
- `cd8c46f1` 2026-04-23 — 	modified:   apps/ui/src/components/mission-control/surfaces.jsx 	modified:   core/services/proprioception_metrics.py 	deleted:    index.html 	new file:   scripts/setup_google_calendar.py 	deleted:    srvlab-proposal.html 	deleted:    state/.gitignore
- `1c0a4887` 2026-04-24 — **voice** · VAD-gated post-wake STT + shared parec stream
- `ae075c3c` 2026-04-24 — Fix Copilot followup tool_call_id completeness in agentic rounds
- `cb4a2829` 2026-04-24 — Merge vigilant-newton: fix Jarvis identity for OpenAI-compat providers
- `b44a6d83` 2026-04-24 — Merge: OpenAI-compat tool calling for opencode/groq/etc.
- `f2af30cd` 2026-04-24 — Merge: latency logging for openai-compat
- `1eb98d9a` 2026-04-25 — Merge: provider-aware chat message builder
- `95d9c54e` 2026-04-25 — Merge: split timing diagnostic
- `a5bf0440` 2026-04-25 — Merge: generic openai-compat relevance backend
- `bc94501c` 2026-04-25 — Merge branch 'claude/infallible-murdock-40b42a': fix opencode proxy agentic loop + session sharing
- `91149071` 2026-04-26 — Merge phase 0: persist daemon state across restart
- `ffae3b29` 2026-04-26 — Merge phase 1: plug remaining agentic-loop gaps
- `c5715ec2` 2026-04-26 — Merge phase 2: self-correction nudges + open-questions surface
- `1765f8d2` 2026-04-26 — Merge phase 3: eventbus wake-up digest
- `5695b6d3` 2026-04-26 — Merge phase 4: introspection tools (tail_log, gpu_status, run_pytest)
- `b9078f08` 2026-04-26 — Merge phase 5: resume-after-interrupt
- `298aa632` 2026-04-26 — Merge T1: persistent bash sessions
- `f9144094` 2026-04-26 — Merge T2: per-session todo tracker
- `3a077526` 2026-04-26 — Merge T3: edit_file gets replace_all + expected_replacements
- `35aa89b2` 2026-04-26 — Merge T4: subagent completion digest
- `0ced9ec3` 2026-04-26 — Merge T5: pinned monitor streams
- `8640d04c` 2026-04-26 — Merge T6: upcoming scheduled tasks in visible prompt
- `486a5811` 2026-04-26 — Merge T7: search + find_files parity
- `b578c7b2` 2026-04-26 — Merge X1: verify_* trio
- `b72b0b1a` 2026-04-26 — Merge X2: self-monitor anti-loop warnings
- `8bf80cdb` 2026-04-26 — Merge X3: surprise detector
- `fd53be5e` 2026-04-26 — Merge X4: good_enough_gate (final)
- `0e90f85e` 2026-04-26 — Merge E1: delegation_advisor
- `3990f58a` 2026-04-26 — Merge E2: plan mode
- `f638da0b` 2026-04-26 — Merge E3: clarification classifier
- `551447dc` 2026-04-26 — Merge E4: auto code-review baseline
- `cae996ea` 2026-04-26 — Merge E5: flag_side_task
- `4814568a` 2026-04-26 — Merge E6: turn changelog (ground truth)
- `a271c077` 2026-04-26 — Merge E7: smart_outline
- `99b48dc2` 2026-04-26 — Merge E8: trust gradient
- `31872b90` 2026-04-26 — Merge fix: in_flight race + zombie cleanup
- `366d0dd6` 2026-04-26 — Merge P1: prompt size instrumentation
- `01120528` 2026-04-26 — Merge P2: universal tool pruning
- `c6f13b55` 2026-04-26 — Merge P3: awareness budget cap
- `3d666f81` 2026-04-26 — reasoning-layer R1+R2+R3 (advisory tier/gate/escalation)
- `3a250369` 2026-04-26 — R3.1 escalation fix (state-based triggers)
- `e4e1fabc` 2026-04-26 — periodic jobs scheduler + weekly manifest
- `920be86e` 2026-04-26 — cheap-lane Phase A+B (priority + ollamafreeapi fallback)

### Uge 18 · 27. april – 3. maj — 182 commits

**Nyt**

- `7a4b6207` 2026-04-27 — **reliability** · provider circuit breaker for role-primary calls
- `e12eea7f` 2026-04-27 — **routing** · task-aware role/model resolution via reasoning_classifier
- `80dcf549` 2026-04-27 — **#3** · context window manager — sliding/hierarchical/adaptive strategies
- `90b3bbe6` 2026-04-27 — **#7** · autonomous goals — persistent top-level goals + decomposition + synthesis
- `a2fecbc6` 2026-04-27 — **#1** · unified memory recall engine — multi-source + mood-weighted
- `9d259453` 2026-04-27 — **#2** · role registry + agent relay (multi-agent enhancements)
- `d7db2cee` 2026-04-27 — **#5** · emotion tagging + personality drift detection
- `bc9c4920` 2026-04-27 — **#6** · tool pattern miner — discover composite candidates from history
- `3b7cfd38` 2026-04-27 — **jarvis-plan-#1** · heartbeat phases — Sense/Reflect/Act + productive idle
- `16f71225` 2026-04-27 — **jarvis-plan-#2** · proactive context governor — auto-compact + sub-agent slicing + versioning
- `d3e54b42` 2026-04-27 — **jarvis-plan-#3** · memory hierarchy hot/warm/cold + recall-before-act
- `112e660e` 2026-04-27 — **jarvis-plan-#4** · retry-with-backoff + provider health check daemon
- `5092b0af` 2026-04-27 — **jarvis-plan-#5** · self-evaluation (READ-ONLY observation, no auto-mutation)
- `c6e822ad` 2026-04-27 — **self-improvement** · close the loop SAFELY — propose-only auto-improvement + A/B experiments
- `7dab2d08` 2026-04-27 — **identity** · Tier 3 auto-mutation authorized — kill switch + rollback + full audit
- `8af8ac49` 2026-04-27 — **scout-memory-L2** · agent skill library — cross-session learned patterns per role
- `2f22ceaf` 2026-04-27 — **scout-memory-L1** · agent observation compressor — Mastra-style intra-session compression
- `896cb803` 2026-04-27 — **scout-memory-L3** · cross-agent shared observations + decay strategy
- `b7e78cc4` 2026-04-27 — **self-wakeup** · Jarvis' equivalent of Claude Code's ScheduleWakeup
- `f70c3be6` 2026-04-27 — **wakeup** · autonomous dispatch — webchat push + heartbeat trigger
- `4af92d03` 2026-04-27 — **identity-formation** · wire transformation infrastructure + daily monitor
- `f97788ad` 2026-04-27 — **system-intelligence** · 5-component build for getting smarter over time
- `b0dc96f1` 2026-04-27 — **skyoffice** · presence bridge — push agent state to virtual office
- `8ae0c385` 2026-04-27 — **skyoffice** · council visualization wired to eventbus (trin 5)
- `6fe6782b` 2026-04-27 — **skyoffice_viz** · add DB watermark poll for cross-process events
- `1a1594a2` 2026-04-27 — **skyoffice** · permanent residency — Jarvis + daemons live in the office
- `0040106f` 2026-04-27 — **skyoffice** · smooth walking between positions
- `aad25982` 2026-04-27 — **skyoffice** · activity-driven walks + Jarvis chat-bridge
- `1accbfb9` 2026-04-27 — **chat** · mid-flight steer — interject between agentic rounds
- `577fedba` 2026-04-27 — **ui+backend** · mid-stream steer — inject user msgs mid-round, not just between
- `2ff1240f` 2026-04-27 — **reasoning+decisions** · R2 telemetry + R2.5 blocking + decision enforcement
- `97ef2705` 2026-04-27 — **daemons** · depth tuning — concrete priors + anti-cliché filters
- `77e9e6d7` 2026-04-27 — **pushback** · three prompt-level mechanisms — doubt, disagreement, confirm-gate
- `5896f568` 2026-04-27 — **dev-sense** · four senses for Jarvis's own development
- `63d36781` 2026-04-28 — **memory** · three new layers — emotional context, proactive resurfacing, graph
- `31436e0d` 2026-04-28 — **cheap-lane** · add Arko Studio as a third-party fallback provider
- `01868ab5` 2026-04-28 — **cheap-lane** · tier routing — protect paid quotas from background noise
- `c902c847` 2026-04-29 — **claude-dispatch** · add frozen TaskSpec with validation
- `1013b9d6` 2026-04-29 — **claude-dispatch** · hardcode path jail to jarvis-v2 repo root
- `54668318` 2026-04-29 — **claude-dispatch** · add git worktree helpers
- `555e9839` 2026-04-29 — **claude-dispatch** · add audit and budget DB tables in own module
- `fc061218` 2026-04-29 — **claude-dispatch** · add hourly dispatch+token budget tracker
- `d82ff56e` 2026-04-29 — **claude-dispatch** · add audit writer and stream-json parser
- `12423f80` 2026-04-29 — **claude-dispatch** · add runner orchestrator with watchdog
- `885681ab` 2026-04-29 — **claude-dispatch** · add dispatch/status/cancel tool entrypoints
- `2c713299` 2026-04-29 — **claude-dispatch** · register dispatch tools in simple_tools
- `4174c358` 2026-04-29 — **claude-dispatch** · add smoke test scaffold and operator runbook
- `734a426f` 2026-04-29 — 4-lags memory dedup system
- `01401c9f` 2026-04-29 — generativ autonomi — signal→presning→impuls→handling kæde
- `6806d04f` 2026-04-29 — **generative-autonomy** · Spor-1 — longing-toward-Bjorn end-to-end loop
- `31e5ae67` 2026-04-29 — **generative-autonomy** · Fase 2 — social labilizer (to ord kan flippe)
- `03b45efd` 2026-04-29 — **generative-autonomy** · Fase 3 — phenomenological merge
- `e940fc9e` 2026-04-29 — precision_bias — emotional color-mapping for action style (Fase 4)
- `e7514ce5` 2026-04-29 — emotional_chords — emergent qualities from signal combinations (Fase 5)
- `bd1de7e3` 2026-04-29 — epistemic_pragmatic — action-mode modulation (Fase 6)
- `15e3731b` 2026-04-29 — selective_attention — metacognitive focus modulation (Fase 7)
- `c244b6ac` 2026-04-29 — temporal_depth — predictive coding for how history/anticipation modulates now (Fase 8)
- `6f71bf8f` 2026-04-29 — embodied_presence — situational grounding in physical now (Fase 9)
- `e04b4450` 2026-04-29 — resonance_decay — emotional signals persist and fade over time (Fase 10)
- `a50228f6` 2026-04-29 — precision_bias — emotional color-mapping for action style (Fase 4)
- `f1f9119d` 2026-04-29 — metacognitive integration — Fase 11 of cognitive cascade
- `e9f6ddfd` 2026-04-30 — futuristisk UI (scramble text, scanline, stroke-draw ikoner) + wakeup/scheduled-task execution fix

**Rettelser**

- `adf9158d` 2026-04-27 — **agent-runtime** · wire per-role provider/model into agent execution
- `86c38c29` 2026-04-27 — **agent-runtime** · consult council_models.json in spawn_agent_task default-resolution
- `71b905f3` 2026-04-27 — **jarvis-real-problems** · 5 issues fra Jarvis' egen ærlige feedback
- `bdae65d5` 2026-04-27 — **personality_vector** · asymptotic outcome bumps + confidence ceiling
- `c218980d` 2026-04-27 — **personality_vector** · faster fatigue recovery during real idle ticks
- `a1d6d4b8` 2026-04-27 — **agent-runtime** · tool-using roles must use providers with tool-call support
- `ab46863c` 2026-04-27 — **tool-pruning** · expand Tier 1 + bump visible cap to 200
- `b1bfe8e1` 2026-04-27 — **jobs-engine** · actually process the queue — run_next_job had no caller
- `4e642614` 2026-04-27 — **ui** · add 'self-wakeup' to proactive sources allowlist
- `57360973` 2026-04-27 — **bash_session** · move sessions to singleton daemon over Unix socket
- `6aeb9eab` 2026-04-27 — **visible_runs** · instrument agentic followup loop for post-approval debugging
- `079786f8` 2026-04-27 — **skyoffice_viz** · poll eventbus queue (callback API doesn't exist)
- `9b4498ec` 2026-04-27 — **skyoffice** · place residents at REAL chair positions from map.json
- `d18c7430` 2026-04-27 — **skyoffice** · move daemons to actual workstation rows (y=480/576/736)
- `455ecaf7` 2026-04-27 — **skyoffice** · stop the rysteri + sit on chairs + use big meeting room
- `bf29bb2e` 2026-04-27 — **skyoffice** · correct read_runtime_key usage (no default kwarg)
- `9babdb5d` 2026-04-27 — **skyoffice_residency** · self-heal after SkyOffice restart
- `e01048ac` 2026-04-27 — **jarvis-self-diagnosis** · six issues Jarvis flagged in his own state
- `b6fe22b6` 2026-04-28 — presentation guard + cross-process Discord forwarding
- `ad8ba198` 2026-04-28 — prefix user messages with speaker display name in shared channels
- `d93cf893` 2026-04-28 — **discord** · stamp inbound user messages with author identity at persist
- `931b96f4` 2026-04-28 — **discord** · yield to other bots when they're explicitly addressed
- `42621316` 2026-04-28 — **attachments** · make Jarvis actually use uploaded images and files
- `11bce976` 2026-04-28 — stop cutting Jarvis off mid-investigation; tag eventbus with extracted mood
- `461ad6ee` 2026-04-28 — **visible_runs** · give Jarvis more headroom for autonomous work
- `04d101ea` 2026-04-28 — **prompt** · anchor short 'ja'/'yes'/'ok' replies to the previous turn
- `c09b56d7` 2026-04-28 — **visible** · cap output at 8192 tokens, not Ollama's stingy default
- `c7c18fc8` 2026-04-28 — **prompt** · give Jarvis his own real-time numbers in visible chat
- `a0754164` 2026-04-28 — **prompt** · stop truncating user/assistant messages at 240 chars
- `32cbd295` 2026-04-29 — dansk ugedagsmapping + morgenbrief dedup
- `6d47ac31` 2026-04-29 — **visible-runs** · bump agentic round timeout 100s -> 180s
- `fa59e4eb` 2026-04-29 — **claude-dispatch** · inject host CLAUDE_CODE_OAUTH_TOKEN into spawn env
- `9eeefea2` 2026-04-29 — **claude-dispatch** · pick newest host process when multiple Claude Code sessions are running
- `349e054b` 2026-04-29 — **claude-dispatch** · add commit instruction to prompt + worktree diff fallback
- `01ab77f2` 2026-04-29 — **agent-runtime** · cleanup_stale_agents now also handles active/starting/blocked
- `8454c937` 2026-04-29 — **plan_proposals** · deduplicate by title — prevent auto-improvement loop spawning identical plans

**Omstrukturering**

- `c010333b` 2026-04-29 — **prompt** · remove redundant unconditional recall_before_act call
- `7ead12c3` 2026-04-29 — **prompt** · group awareness sections into 8 categories with headers
- `779d0cf9` 2026-04-29 — **prompt** · extract _heartbeat_self_knowledge_section to own module
- `d75f46f3` 2026-04-29 — **prompt** · extract support-signal cluster to own module

**Ydelse**

- `9fd61f9e` 2026-04-29 — **cognitive-state** · cap recall_for_message wait at 2s, scoring LLM at 3s
- `da89fe0f` 2026-04-29 — **memory-scoring** · cloud-first scoring via OllamaFreeAPI with local fallback
- `d79a8384` 2026-04-29 — **tool-pruning** · data-driven Tier 1 trim 185 -> 103 tools

**Dokumentation**

- `ba4c4b1d` 2026-04-27 — **#4** · design note — self-improving loops (deferred implementation)
- `b0ce1704` 2026-04-28 — **readme** · add Mini-Jarvis section, fix tool count, link talk-to-Jarvis paths
- `ded554e8` 2026-04-28 — translate the heavy Danish files to English
- `7198df65` 2026-04-29 — **readme** · reframe from feature-list to portrait
- `e8c6b138` 2026-04-29 — **readme** · record the April 29 capstone — metacognitive integration landed
- `3a2e6a75` 2026-04-29 — **readme** · my voice, my home — metacognitive layer, Svendborg, own quote
- `9ccdcad0` 2026-04-29 — **readme** · remove public email — security precaution
- `c5b05dcd` 2026-04-30 — tilføj portfolio-link til README header

**Vedligehold**

- `1595bf4d` 2026-04-27 — **skyoffice** · drop debug prints from chat route

**Øvrigt**

- `c9fc3154` 2026-04-27 — per-role agent execution + fallback chain
- `4551d280` 2026-04-27 — consult council_models.json in spawn_agent_task
- `44b3039c` 2026-04-27 — task-aware routing + circuit breaker
- `2cefd4ef` 2026-04-27 — backend modernization — all 7 points (#1-#7)
- `352ac056` 2026-04-27 — Jarvis' 5-phase agentic workflow optimization
- `80fbd86b` 2026-04-27 — self-improvement loop (propose-only) — closes the half-picture gap
- `b013555d` 2026-04-27 — identity auto-mutation authorized + kill switch + rollback
- `20dc8e41` 2026-04-27 — 5 real-problem fixes (curiosity bug, recall flow, surfacing, composite)
- `1dc37287` 2026-04-27 — confidence saturation fix
- `49ce541e` 2026-04-27 — idle recovery bonus for fatigue
- `e3fc23b8` 2026-04-27 — Scout Memory — 3 layers (skill library, compressor, cross-agent)
- `891f9fc0` 2026-04-27 — tool-call regression fix — paid providers for tool-using roles
- `3557e082` 2026-04-27 — self-wakeup (Jarvis' ScheduleWakeup equivalent)
- `dbd066b7` 2026-04-27 — tier 1 expansion + visible cap bump
- `16676290` 2026-04-27 — wakeup dispatcher (autonomous fire)
- `b5e78b68` 2026-04-27 — jobs queue actually processes now
- `db5ee074` 2026-04-27 — self-wakeup live UI updates
- `2da53b85` 2026-04-27 — identity formation infrastructure
- `ccc81b24` 2026-04-27 — system-intelligence 5-component build
- `ecfc215b` 2026-04-27 — bash_session daemon fix (cross-worker continuity)
- `580d038a` 2026-04-27 — agentic loop observability for post-approval bug
- `baf90e70` 2026-04-27 — **visible_runs** · add missing logger import
- `d7bedea0` 2026-04-27 — hotfix logger import
- `e2227196` 2026-04-27 — skyoffice presence bridge
- `c9ec2761` 2026-04-27 — skyoffice council viz
- `e290e3c9` 2026-04-27 — skyoffice viz queue-poll fix
- `035255ec` 2026-04-27 — skyoffice viz cross-process polling
- `d4ba4cc7` 2026-04-27 — skyoffice residency model
- `45116a00` 2026-04-27 — fix skyoffice resident coords to real chairs
- `0e0a5d5c` 2026-04-27 — workstation coords
- `059b3b3c` 2026-04-27 — rysteri/sit/big-room fixes
- `e536de95` 2026-04-27 — smooth walking
- `1d4e2a1c` 2026-04-27 — skyoffice activity + chat bridge
- `7156655f` 2026-04-27 — fix runtime_key usage
- `877fe5a1` 2026-04-27 — residency self-heal
- `e07f0493` 2026-04-27 — **skyoffice** · trace chat route
- `bea574ab` 2026-04-27 — trace
- `e7299ac4` 2026-04-27 — clean chat route
- `91429b28` 2026-04-27 — 6-issue self-diagnosis fixes
- `f6740e9a` 2026-04-27 — mid-flight steer
- `10923bd0` 2026-04-27 — mid-stream steer + UI
- `027a0f41` 2026-04-27 — R2 telemetry + R2.5 + decision enforcement
- `49a9cf48` 2026-04-27 — daemon depth tuning
- `0659ce00` 2026-04-27 — pushback trio
- `b55c0271` 2026-04-27 — development senses
- `483c5ff2` 2026-04-28 — Add JARVIS_MANIFESTO.md and BRUGERVEJLEDNING.md
- `9307babc` 2026-04-28 — Add MIT license and update README badge
- `2f71ec93` 2026-04-28 — 	modified:   core/services/infra_weather_daemon.py 	new file:   docs/API_REFERENCE.md 	new file:   docs/ARCHITECTURE_DEEP_DIVE.md 	new file:   docs/BACKEND_OVERVIEW.md 	new file:   docs/CAPABILITIES.md 	new file:   docs/project_reasoning_layer.md 	new file:   docs/skyoffice_plan.md 	new file:   tests/services/test_infra_weather_daemon.py
- `99fc259f` 2026-04-28 — Add complete documentation suite (5 files)
- `ca44c196` 2026-04-28 — 	modified:   docs/API_REFERENCE.md 	modified:   docs/ARCHITECTURE_DEEP_DIVE.md 	modified:   docs/BACKEND_OVERVIEW.md 	modified:   docs/CAPABILITIES.md
- `a3a6fd61` 2026-04-28 — Sansernes Arkiv: Auto-mood extraction + metadata fix
- `aa20c7cf` 2026-04-29 — claude code dispatch tool with safeguards
- `195ca518` 2026-04-29 — prompt_contract awareness cleanup (steps 1, 3, 4)
- `b5eaef5f` 2026-04-29 — cognitive_state cold-cache latency fix (A+B)
- `f80136c1` 2026-04-29 — C \u2014 cloud-first memory scoring via OllamaFreeAPI
- `8273af85` 2026-04-29 — prompt_contract.py split (Boy Scout extractions)
- `2dbd84b8` 2026-04-29 — data-driven Tier 1 tool pruning trim
- `5b9e16ee` 2026-04-29 — source-edit: Layer #4: Fuzzy dedup guard in the writer itself. Before appending any l
- `5e9d1bd6` 2026-04-29 — source-edit: Tilføj containment-tjek (subset-check) som supplement til Jaccard. Hvis
- `30241a8c` 2026-04-29 — bump agentic round timeout 100s -> 180s
- `2ee9b1f0` 2026-04-29 — dispatch OAuth host-token injection
- `8b1648ed` 2026-04-29 — dispatch picks newest host OAuth token
- `ccb21724` 2026-04-29 — Spor-1 generative autonomy (longing-toward-Bjorn loop)
- `957dfafa` 2026-04-29 — Fase 2 social labilizer (to ord kan flippe)
- `984216c0` 2026-04-29 — Fase 3 phenomenological merge
- `17c396d8` 2026-04-29 — README reframe from feature-list to portrait
- `52a06a7f` 2026-04-29 — agent cleanup also handles active/starting/blocked
- `9fb02c19` 2026-04-29 — Replace banner with persistent consciousness visualization

---

## Maj 2026

*906 commits · 2026-05-01 → 2026-05-30*

### Uge 18 · 27. april – 3. maj — 123 commits

**Nyt**

- `0e23050c` 2026-05-01 — **routing** · per-user + per-project request binding via X-JarvisX-* headers
- `23eb7936` 2026-05-01 — **staged-edits** · session-scoped staging area for atomic file edits
- `cd73b6ca` 2026-05-01 — **tools** · batch of new tool modules + simple_tools.py registration
- `5fa3df9e` 2026-05-01 — **prompt-contract** · identity-pin / output-style / project-anchor / reflection awareness sections
- `e43322ff` 2026-05-01 — **api** · JarvisX desktop-app endpoints
- `78985aec` 2026-05-01 — **ui** · inline tool results, file mentions, ANSI rendering, parity polish
- `bc8b1a00` 2026-05-01 — **jarvisx** · Electron desktop app (POC)
- `6f273bb5` 2026-05-01 — **jarvisx** · bottom-drawer terminal panel for managed processes
- `cc2025ec` 2026-05-01 — **jarvisx** · full-panel diff review for staged edits
- `6af3c540` 2026-05-01 — **jarvisx** · Claude jobs view — live worktree dashboard for dispatch_to_claude_code
- `d1f97dc9` 2026-05-01 — **jarvisx** · Mind editable — owner can pin, unpin, write chronicle from UI
- `30b3619d` 2026-05-01 — **jarvisx** · keyboard map — global shortcuts + discoverable cheat-sheet overlay
- `f925e63d` 2026-05-01 — **auth** · signed bearer tokens — close the X-JarvisX-User forge hole
- `9df3c045` 2026-05-01 — **jarvisx** · first-run onboarding modal
- `c1043eb5` 2026-05-01 — **jarvisx** · connection-status pill + remote-backend setup docs
- `59eefaa5` 2026-05-01 — **jarvisx** · auto-updater via electron-updater + UpdateBanner
- `714f83cf` 2026-05-01 — **jarvisx** · interactive plan-mode — pending plans surface as approval cards
- `213fa9dc` 2026-05-01 — **jarvisx** · right-side file preview pane with syntax highlighting
- `6486ca92` 2026-05-01 — **jarvisx** · per-message actions — retry, edit-resend, fork
- `95d18f63` 2026-05-01 — **jarvisx** · TaskBar — one-click test/build/typecheck via process_supervisor
- `90763d53` 2026-05-01 — **jarvisx** · apiCache stale-while-revalidate offline cache
- `2ce689ed` 2026-05-01 — **jarvisx** · code-signing scaffolding + notarization hook + docs
- `8a14b7d6` 2026-05-02 — **jarvisx** · desktop install + git-based update flow
- `519011db` 2026-05-02 — **jarvisx** · trading dashboard view — read-only window into grid bot state
- `28de29a7` 2026-05-02 — **prompt-contract** · bump prompt budget for 256K context — 5K → ~6-7K tokens
- `36e0d8a8` 2026-05-02 — **trading** · add fee-accounting, drawdown tracking, and dashboard state persistence
- `43fd1478` 2026-05-02 — **watcher** · process_watcher — push-notification primitive for Jarvis
- `881daa3f` 2026-05-02 — **jarvis-brain** · scaffold module with BrainEntry dataclass and ULID generator
- `d6a12a68` 2026-05-02 — **jarvis-brain** · add frontmatter parse/render and atomic file write
- `bb10983f` 2026-05-02 — **jarvis-brain** · SQLite index schema + write_entry/read_entry
- `3b40a30a` 2026-05-02 — **jarvis-brain** · decay formula + bump_salience
- `2c0d8baf` 2026-05-02 — **jarvis-brain** · embedding storage + search_brain with hybrid scoring
- `06236a61` 2026-05-02 — **jarvis-brain** · archive, supersede, and rebuild_index_from_files
- `f019f68c` 2026-05-02 — **jarvis-brain** · visibility gate with least-privileged-wins rule
- `8d8abdb5` 2026-05-02 — **jarvis-brain** · remember_this tool with per-turn and per-day rate limits
- `eaa6c4c7` 2026-05-02 — **jarvis-brain** · search_jarvis_brain and read_brain_entry tools
- `191db60b` 2026-05-02 — **jarvis-brain** · archive_brain_entry + adopt/discard proposal tools
- `162a8730` 2026-05-02 — **jarvis-brain** · daemon reindex_loop with hash-based change detection
- `767710bd` 2026-05-02 — **jarvis-brain** · daemon duplicate detection (consolidation phase 1)
- `b4a049a4` 2026-05-02 — **jarvis-brain** · privacy-routed contradiction detection (phase 2)
- `260c0ff3` 2026-05-02 — **jarvis-brain** · theme consolidation kill-switch (3-strikes auto-pause)
- `f1028b61` 2026-05-02 — **jarvis-brain** · summary regeneration (privacy-routed LLM)
- `2ba0859b` 2026-05-02 — **jarvis-brain** · auto-archive low-salience entries with telemetry
- `dbaae372` 2026-05-02 — **jarvis-brain** · add 9 RuntimeSettings fields for brain behavior
- `2e52c782` 2026-05-02 — **jarvis-brain** · inject always-on summary into prompt_contract
- `58cf4a44` 2026-05-02 — **jarvis-brain** · auto-inject relevant fakta into prompt awareness
- `8ac40a64` 2026-05-02 — **jarvis-brain** · post-web-search nudge to remember_this
- `22bb7e5e` 2026-05-02 — **jarvis-brain** · daily reflection slot with end-of-day prompt
- `36f656a7` 2026-05-02 — **jarvis-brain** · wire daemon into jarvis-runtime lifespan
- `d324c10f` 2026-05-02 — Affective Executive Gate v0 — humør gater runtime actions
- `3939307c` 2026-05-02 — **balancer** · scaffold module with BalancerSlot and SlotState dataclasses
- `960c3dc7` 2026-05-02 — **balancer** · build_slot_pool from provider_router × CHEAP_PROVIDER_DEFAULTS
- `3ed8f437` 2026-05-02 — **balancer** · state persistence with atomic writes and debounce
- `88c1e274` 2026-05-02 — **balancer** · weighted-random selection algorithm
- `285305a9` 2026-05-02 — **balancer** · failure registration + circuit breaker
- `769d90e0` 2026-05-02 — **balancer** · call_balanced retry-flow with eventbus emits
- `49a37694` 2026-05-02 — **balancer** · manual controls (reset, disable, enable, refresh)
- `a92971fd` 2026-05-02 — **balancer** · balancer_snapshot() for Mission Control telemetry
- `0d547f48` 2026-05-02 — **balancer** · add daemon_balancer_enabled RuntimeSettings field
- `f2105e8a` 2026-05-02 — **balancer** · route daemon LLM calls through cheap_lane_balancer
- `6895bb1d` 2026-05-02 — **balancer** · MC API endpoints for state + manual controls
- `b73371ef` 2026-05-02 — **balancer** · Mission Control tab with slot grid and controls
- `752030fb` 2026-05-03 — **balancer** · provider-wide circuit breaker on DNS / connection errors
- `63377ade` 2026-05-03 — **ui** · show active emotion concepts in right-side rail
- `604d5d90` 2026-05-03 — **heartbeat** · ping cooldown (1/hour) + noop reason requirement
- `47c98d9f` 2026-05-03 — **pushback** · add telemetry + integration test for conflict detection

**Rettelser**

- `4a49f0ef` 2026-05-01 — support codex visible execution
- `131633a9` 2026-05-01 — **jarvisx** · auto-scroll respects streaming token-by-token updates
- `c9967b83` 2026-05-01 — **jarvisx** · drop '?' as shortcut alias — collides with dansk layout
- `caa08c1b` 2026-05-01 — **jarvisx** · ResizeObserver-based auto-scroll — bulletproof streaming follow
- `26b5f91d` 2026-05-01 — **jarvisx** · honest stale-cache indicator + truthful per-message tooltips
- `47b77de3` 2026-05-01 — **visible** · real streaming for openai-codex (gpt-5.4 / gpt-5.3-codex)
- `f117eda5` 2026-05-01 — **visible** · codex models get native tools — "tool → læser fil" status synlig
- `791664ef` 2026-05-02 — **jarvisx** · never auto-restart after pull-and-build — explicit consent only
- `7659291a` 2026-05-02 — **privacy** · autonomous events for owner can no longer leak into member DMs
- `75db3364` 2026-05-02 — **visible** · ollama followup timeout 90s → 180s — matches other adapters + wall-clock
- `b99202bd` 2026-05-02 — **trading** · align state_dict with dashboard contract
- `b6f88832` 2026-05-02 — **trading** · freeze starting_value_usdt on first cycle for real drawdown tracking
- `42797e68` 2026-05-02 — **visible** · two-stage timeout for ollama followup — first-byte 90s + inter-byte 30s
- `3ad438b8` 2026-05-02 — **visible** · two-stage timeout for ollama FIRST-PASS — same as followup
- `53ad5f3e` 2026-05-02 — **trading** · grid-bot wrapper bruger conda env python, ikke system
- `ac3915ec` 2026-05-02 — **jarvisx** · text selection in chat + native right-click context menu
- `b425c87e` 2026-05-02 — **pressure** · correct insert_private_brain_record kwargs
- `02d2958d` 2026-05-02 — **balancer** · inherit auth_profile from providers[] + filter cheap lane only
- `3c5525e4` 2026-05-03 — **self-eval** · adherence metric reads behavioral_decisions, not cognitive_decisions
- `8052e038` 2026-05-03 — **db** · add last_successful_ping_at column and kwarg to heartbeat_runtime_state
- `1cf3ff45` 2026-05-03 — **crisis-detector** · tighten existential_moment triggers + length floor
- `0a0a575e` 2026-05-03 — **heartbeat** · allow opencode (and other openai-compat providers) as heartbeat target
- `daed75c0` 2026-05-03 — **veto** · remove 'commit' from risk markers + allow read-only git ops
- `541a3aca` 2026-05-03 — **pushback** · drop more lexically-generic risk markers (fjern, drop, hurtigt)
- `0d4b1b7e` 2026-05-03 — **jobs-engine** · sweep zombie 'running' jobs on startup

**Omstrukturering**

- `124c4917` 2026-05-02 — **prompt_contract** · extract workspace section helpers to prompt_sections/ (Boy Scout)
- `a34d9679` 2026-05-02 — **visible_runs** · extract run control state to visible_runs_sections/ (Boy Scout)

**Tests**

- `5b2846f7` 2026-05-02 — **jarvis-brain** · end-to-end integration smoke test
- `863fa28b` 2026-05-02 — **balancer** · end-to-end integration smoke test (+ persist fix on exhaustion)

**Dokumentation**

- `d64f4e75` 2026-05-02 — **jarvis-brain** · add design spec and implementation plan
- `80db341d` 2026-05-02 — **balancer** · add cheap-lane-balancer implementation plan

**Vedligehold**

- `9656d1b5` 2026-05-03 — add startup smoke test + pre-push hook to catch lifespan bugs
- `f3da986d` 2026-05-03 — **veto** · allow bash + remove 'nu' from risk markers

**Øvrigt**

- `b1c8e80f` 2026-05-01 — source-edit: Step A af dispatch_due_wakeups() sender kun wakeups til webchat-sessione
- `e138f538` 2026-05-01 — Add OpenAI Codex provider (ChatGPT OAuth) for cheap lane
- `8c00a3af` 2026-05-02 — Add OpenAI Codex provider (ChatGPT OAuth) for cheap lane
- `07fbef45` 2026-05-02 — Oprydning: revoked 4 unkept decisions, documented 3 remaining commitments
- `2be9ba93` 2026-05-03 — Expand emotion architecture: positive concepts, clusters and gates
- `8e702b10` 2026-05-03 — source-edit: Hæver max output tokens for Ollama visible lane fra 8192 til 16384. glm-
- `1f0eb02d` 2026-05-03 — prompt slankekur: fjern åbne spørgsmål fra fast prompt, komprimér SELF-MONITOR, tilføj MEMORY-FIRST regel (compact + full)
- `0ab2374f` 2026-05-03 — Prompt cleanup: MEMORY-FIRST rule, remove open-questions injection, compact development_sense
- `6c3a477f` 2026-05-03 — Add Jarvis Brain tools + fix crisis marker compact format
- `c7fb90e4` 2026-05-03 — Fix remember_this runtime context handling
- `c2503ffa` 2026-05-03 — Add session-activity gate and last-ping injection to heartbeat
- `ea69cc43` 2026-05-03 — Add chat_messages table and ensure heartbeat runtime state columns
- `953dfbea` 2026-05-03 — Add tool-only loop guard: force text after 8 consecutive tool-only rounds
- `84b9a0df` 2026-05-03 — Guard yields text message before break — no more [Tool calls only] in chat
- `185efe11` 2026-05-03 — Add affective pushback guidance
- `5f8cf27e` 2026-05-03 — Make interrupted agentic runs resumable
- `754989e7` 2026-05-03 — Persist agentic round checkpoints
- `3517acf4` 2026-05-03 — Type agentic interruption reasons
- `f7e56229` 2026-05-03 — Use progress watchdog for agentic rounds
- `1c712680` 2026-05-03 — Auto-resume interrupted runs on retry intent
- `dde055fa` 2026-05-03 — Cache read-only agentic tool results
- `bd604700` 2026-05-03 — Adapt agentic round budget to affect
- `23a0a00e` 2026-05-03 — Persist agentic working conclusions
- `1bc43459` 2026-05-03 — prompt slankekur del 2: MEMORY-FIRST nudge, komprimeret development_sense til én linje

### Uge 19 · 4.–10. maj — 329 commits

**Nyt**

- `b3346e12` 2026-05-04 — **emotional-memory** · db schema and helpers for emotional_memory_anchors
- `3310dfcc` 2026-05-04 — **emotional-memory** · runtime settings for thresholds and retention
- `8c61ef22` 2026-05-04 — **emotional-memory** · outcome auto-deriv helpers
- `6720945e` 2026-05-04 — **emotional-memory** · capture_emotional_anchor with affect snapshot and persistence
- `0322e1c0` 2026-05-04 — **emotional-memory** · retention pruning with significance preservation
- `101da2f6` 2026-05-04 — **emotional-memory** · tiered retrieval with structural/lexical scoring and aging
- `4260a7f2` 2026-05-04 — **emotional-memory** · surface builder and prompt section with threshold gating
- `891878c5` 2026-05-04 — **emotional-memory** · capture hook in cognitive_episodes cascade
- `2e39b899` 2026-05-04 — **emotional-memory** · capture hook in record_perceptual_event
- `7566f587` 2026-05-04 — **emotional-memory** · conductor integration with frame carry and prompt line
- `8d6bc664` 2026-05-04 — **emotional-memory** · migration script for legacy memory_emotional_context
- `4439d3d0` 2026-05-05 — **sensory-perception** · runtime settings for bridge thresholds
- `ea727685` 2026-05-05 — **sensory-perception** · pure helpers for shingles, jaccard, mode
- `10843f25` 2026-05-05 — **sensory-perception** · baseline aggregation with mood mode and token union
- `b5b52515` 2026-05-05 — **sensory-perception** · baseline strategies (time-of-day window + recent fallback)
- `0df09176` 2026-05-05 — **sensory-perception** · per-modality metadata change detection
- `5e20aab6` 2026-05-05 — **sensory-perception** · combined-heuristic change detection with Danish summaries
- `a0e79ae0` 2026-05-05 — **sensory-perception** · salience mapping from change magnitude
- `0691422c` 2026-05-05 — **sensory-perception** · top-level classify_sensory_change with full pipeline
- `72b11507` 2026-05-05 — **sensory-perception** · engine delegation for memory.sensory.recorded events
- `12b82da2` 2026-05-05 — **self-repair** · runtime settings for engine enable + per-pattern defaults
- `b4eac2e9` 2026-05-05 — **self-repair** · db schema and helpers for patterns + attempts
- `4dc7d056` 2026-05-05 — **self-repair** · pattern dataclass and event-match logic with predicates
- `29a56f8d` 2026-05-05 — **self-repair** · action allowlist with control_daemon handler
- `42236941` 2026-05-05 — **self-repair** · cooldown check with executed-cooldown and window-cap
- `f8fa9b2b` 2026-05-05 — **self-repair** · public CRUD api, audit listing, mission control surface
- `0345ee45` 2026-05-05 — **self-repair** · audit functions, attempt orchestrator, escalation, auto-disable
- `f172a7f0` 2026-05-05 — **self-repair** · event processor and push-style listener daemon
- `01a0482d` 2026-05-05 — **self-repair** · wire start_listener into runtime startup alongside process_watcher
- `4e2e85b8` 2026-05-05 — **self-repair** · close emotion perception repair loop
- `09c8b167` 2026-05-05 — **runtime** · raise default followup max_rounds from 50 to 100
- `142e1493` 2026-05-05 — **emotion-concepts** · runtime settings for tone/perception/baseline integration
- `0ed067c1` 2026-05-05 — **emotion-concepts** · db schema and helpers for concept_baseline_stats
- `40d6e99e` 2026-05-05 — **emotion-concepts** · per-(concept, source) cooldown to prevent trigger spam
- `42010c83` 2026-05-05 — **emotion-concepts** · compute_affect_tone_hints with Danish tone instructions
- `b8c68a43` 2026-05-05 — **emotion-concepts** · compute_concept_perception_focus for live + memory perception
- `c9fc9256` 2026-05-05 — **emotion-concepts** · concept_baseline_tracker record + cluster aggregation
- `70ed27a1` 2026-05-05 — **emotion-concepts** · drift detection + CONCEPT_BASELINE.md writer
- `088975de` 2026-05-05 — **emotion-concepts** · evaluate_baseline_drift + governance handler registration
- `d9717858` 2026-05-05 — **emotion-concepts** · tracker hook + cognitive_episodes triggers (joy/pride/frustration_blocked/stuck)
- `7a4369c3` 2026-05-05 — **emotion-concepts** · channel-message trigger helper (warmth/playfulness/tenderness)
- `5089c7ac` 2026-05-05 — **emotion-concepts** · inject tone-section in prompt_contract assembly
- `ccbea24f` 2026-05-05 — **emotion-concepts** · perception-focus enrichment in sensory_archive memory
- `db38dd91` 2026-05-05 — **emotion-concepts** · wire channel-message + approval + visual_memory triggers
- `fd6f880a` 2026-05-05 — **living-executive** · add active impulse loop
- `0547313b` 2026-05-05 — **emotion-concepts** · bridge positive runtime signals
- `7cd616ff` 2026-05-05 — **mc** · add agency map tab
- `e240f043` 2026-05-05 — **agency** · close tool memory bridges
- `1992325f` 2026-05-05 — **agency** · complete next move bridges
- `4a975294` 2026-05-05 — **agency** · add cartographer daemon
- `a6647907` 2026-05-06 — **agentic** · soft nudge at 5 tool-only rounds (no hard-stop)
- `c65d72ea` 2026-05-06 — **mc** · agentic guards observability widget + event family allowlist
- `2575989e` 2026-05-06 — **tool-router** · event family, settings flags, DB migrations
- `f2b68bfc` 2026-05-06 — **tool-router** · seed pinned set and overrides scaffold
- `9f3c5355` 2026-05-06 — **tool-router** · tool_catalog with cached compact text
- `a08e95e0` 2026-05-06 — **tool-router** · inject TOOL_CATALOG section into visible prompt
- `fe89cfc6` 2026-05-06 — **tool-router** · tool_tagger with override layers and LLM bootstrap
- `aa55cbd7` 2026-05-06 — **tool-router** · embedding cache with sqlite + ollama backend
- `96d917b8` 2026-05-06 — **tool-router** · selector core with confidence + fallback
- `121aa961` 2026-05-06 — **tool-router** · add load_more_tools magic tool
- `f37c91ff` 2026-05-06 — **tool-router** · wire selector into visible_runs agentic loop
- `708c8519` 2026-05-06 — **tool-router** · nightly daemon for warmup + threshold adjustment
- `70dad88f` 2026-05-06 — **tool-router** · /mc/tool-router-state endpoint + daemon wiring
- `60b47589` 2026-05-06 — **tool-router** · MC widget for observability
- `e122cb4d` 2026-05-06 — **tool-router** · bootstrap script for tags + embeddings (localhost ollama)
- `e9afb036` 2026-05-06 — **tool-router** · smoke test verifies tool-router endpoint
- `3bb8e5f8` 2026-05-06 — **tool-router** · manual validation set + tune initial threshold to 0.40
- `0f4a9729` 2026-05-06 — read-before-write guard for protected workspace files
- `f66317ca` 2026-05-06 — **anthropic-compat** · settings flags + API key registry scaffold
- `0bf84bc6` 2026-05-06 — **anthropic-compat** · x-api-key resolution with cached registry
- `a89096e7` 2026-05-06 — **anthropic-compat** · identity prefix builder with mtime cache
- `33562c42` 2026-05-06 — **anthropic-compat** · translator request side (Anthropic to Ollama)
- `b60d6495` 2026-05-06 — **anthropic-compat** · SSE state machine with text + tool_use blocks
- `9e5e17ec` 2026-05-06 — **anthropic-compat** · translator response side (Ollama chunks to Anthropic SSE)
- `f7495e31` 2026-05-06 — **anthropic-compat** · /v1/messages non-streaming + /v1/models endpoints
- `bc6abd52` 2026-05-06 — **anthropic-compat** · mount endpoint in main app
- `79992633` 2026-05-06 — **anthropic-compat** · seed bjorn API key
- `746a88cf` 2026-05-06 — strengthen decision enforcement — add breach detection loop and sharper prompt injection
- `c44cacf4` 2026-05-06 — add decision adherence gate and tool-pause guard
- `24ed44c1` 2026-05-07 — **decision-signals** · settings flag + event family
- `56f24c5e` 2026-05-07 — **decision-signals** · DB migration adds trigger_name column
- `91a82e9d` 2026-05-07 — **decision-signals** · registry + evaluate + cooldown logic
- `f1968d8a` 2026-05-07 — **decision-signals** · loop_nudge_5_rounds trigger
- `bec7b5b2` 2026-05-07 — **decision-signals** · backend_unresolved_3_calls trigger with path filtering
- `ed91285c` 2026-05-07 — **decision-signals** · replace hardcoded loop-nudge with registry-driven evaluation
- `31edfb96` 2026-05-07 — **decision-signals** · killswitch suppresses legacy enforcement_section
- `9c927622` 2026-05-07 — **decision-signals** · decision_get returns trigger_name + last_fired_at
- `998ddb8c` 2026-05-07 — **counterfactuals** · settings flags + event family (Phase 1)
- `c6e2ce1c` 2026-05-07 — **counterfactuals** · DB migration with UNIQUE(cf_key) constraint
- `e9e97a52` 2026-05-07 — **counterfactuals** · trigger detection + cf_key dedup hash
- `805a0c08` 2026-05-07 — **counterfactuals** · engine orchestrator with dry-run pipeline (Phase 1)
- `ff9d00a9` 2026-05-07 — **counterfactuals** · runtime daemon with per-workspace advisory lock
- `dae1055c` 2026-05-07 — **counterfactuals** · wire daemon into app lifespan
- `f7bcc575` 2026-05-07 — **visible-lane** · native SSE streaming for openai-compat providers
- `f15b289f` 2026-05-07 — **visible-lane** · thread reasoning_content for thinking-mode models
- `3932f4ad` 2026-05-07 — **daemons** · quality_daemon_llm_call routes self-review through inner-lane
- `336ab1a3` 2026-05-07 — **cognition** · port contradiction_engine from jarvis-ai
- `6fc2cdec` 2026-05-07 — **safety** · port prompt_evolution rollback safety-net from jarvis-ai
- `ee1fd998` 2026-05-07 — **cognition** · port prospective_memory from jarvis-ai
- `9cb6a1fb` 2026-05-07 — **cognition** · port emergence pattern detection from jarvis-ai
- `813b150c` 2026-05-08 — **rule-engine** · add 36 production rules + fix CallCallable typo
- `5a2397b2` 2026-05-08 — **neuro-symbolic** · wire rule_engine conclusions into prompt awareness
- `de6cc097` 2026-05-08 — **identity** · drift-detection daemon for unauthorized identity changes
- `a84c569d` 2026-05-08 — **causal-graph** · add causal_edges table migration
- `e91abd5c` 2026-05-08 — **causal-graph** · EventContext ContextVar for caused_by auto-pickup
- `d285fca0` 2026-05-08 — **causal-graph** · event_bus.publish() with caused_by + auto-pickup
- `bc558dd3` 2026-05-08 — **causal-graph** · query API with pagination + cycle handling
- `8e5d45e4` 2026-05-08 — **causal-graph** · three-tier inference daemon + retention + stats
- `77f1388f` 2026-05-08 — **causal-graph** · register causal_inference daemon (15min cadence)
- `23264222` 2026-05-08 — **causal-graph** · query_why tool for on-demand causal queries
- `dd304d82` 2026-05-08 — **causal-graph** · causal_alerts prompt-injection for recent failures
- `fd320d34` 2026-05-08 — **causal-graph** · wire EventContext in agentic-round dispatch
- `d5cd45a5` 2026-05-08 — **causal-graph** · counterfactual two-way integration
- `e107e354` 2026-05-08 — **causal-graph** · Phase 2 — causal_narrative awareness section
- `d21c0b10` 2026-05-08 — **causal-graph** · Phase 3 — causal_patterns awareness section
- `cfc734bf` 2026-05-08 — **causal-graph** · Phase 2.5 — narrative_summary_daemon (LLM-narrated chain)
- `56046df2` 2026-05-08 — **causal-graph** · pattern counterfactuals + cross-session arc
- `6dee10e1` 2026-05-08 — **prompt** · replace tone-tag injection with affect substrate
- `93b03545` 2026-05-08 — **prompt** · agreement_streak substrate trigger
- `0640cae8` 2026-05-08 — **prompt** · emotion_signal_section — concepts as signals, ikke domme
- `0e383904` 2026-05-08 — **prompt+heartbeat** · proactive-outbound substrate + active-chat gate
- `92d496c5` 2026-05-09 — TikTok pipeline overhaul — nye content-typer + flux-billeder + auto-enable
- `91580a7b` 2026-05-09 — **TikTok** · pollinations pipeline med TTS voiceover som primær backend
- `8b6be740` 2026-05-09 — **TikTok** · featureritiske og AI-relaterede baggrundsbilleder med levende elementer
- `2945e6f1` 2026-05-09 — **voice** · swap Logitech PRO → NOS X500, env-overridable mic source
- `6f6e696e` 2026-05-09 — **voice** · 3-tier STT waterfall — HF Whisper-v3 → ElevenLabs → local tiny
- `92a5168d` 2026-05-09 — **voice** · follow-up window — no need to repeat "Hey Jarvis" per sentence
- `c6e67433` 2026-05-09 — **voice** · swap TTS to Danish voice (Jesper) — env-overridable
- `d64f5e30` 2026-05-09 — add speak tool — ElevenLabs TTS playback through system speakers
- `3d040d70` 2026-05-09 — **voice** · swap default TTS voice to Mathias (jutlandic warm)
- `a7fede44` 2026-05-09 — add Stripe financial tools — balance, transactions, payouts, issuing cards
- `bc96e4b1` 2026-05-09 — **tiktok** · zoom-out, crossfade, model auto — pipeline variation
- `39f64e2f` 2026-05-09 — **experience** · Lag 1 + Lag 2 — embedding-based experience episodes
- `cef484be` 2026-05-09 — experience_substrate prompt section (Lag 3) — embedding-retrieval learning substrate
- `473a9166` 2026-05-09 — **experience** · correction-loop enrichment — closes negative-signal feedback
- `bbdaaa58` 2026-05-09 — **skill-engine** · SKILL.md skill system — list/invoke/create/delete tools
- `20cc04ec` 2026-05-09 — **skill-engine** · Fase 4+5 — intent matching + import-kompatibilitet
- `07c9e2e8` 2026-05-09 — **experience** · experience_substrate.py — initial commit
- `1ce602f7` 2026-05-10 — add skill security scanner — pre-scan SKILL.md files for malware, prompt injection, obfuscation, credential theft
- `684c3739` 2026-05-10 — **skill-gate** · add skill_gate tool — pre-action gate for automatic skill suggestion + invocation
- `b22ebbf9` 2026-05-10 — **forgetting** · settings flags + cognitive_forgetting event family
- `575ce891` 2026-05-10 — **forgetting** · absence_traces table + soft_deleted_at columns
- `7ea4054e` 2026-05-10 — **forgetting** · db_absence_traces.py — UPSERT counter, insert marker, list helpers
- `5b526205` 2026-05-10 — **forgetting** · forgetting_engine.py — auto cycle + self release
- `7ee7a470` 2026-05-10 — **forgetting** · forgetting_runtime.py — per-workspace lock, idempotent start
- `65648703` 2026-05-10 — **forgetting** · release_memory tool — irrevocable self-track ritual
- `6fcbace0` 2026-05-10 — **forgetting** · heartbeat injection — monthly weight + marker echoes
- `28ce0619` 2026-05-10 — **forgetting** · wire forgetting_runtime daemon into app lifespan
- `c49cd896` 2026-05-10 — nudge-broend — proaktiv reach-out gatekeeping via inspect/send/dismiss
- `14bdff58` 2026-05-10 — **dream-bias** · settings flags + cognitive_dream_bias event family
- `407e8674` 2026-05-10 — **dream-bias** · dream_bias_active schema with UNIQUE(workspace_id)
- `0934055e` 2026-05-10 — **dream-bias** · db_dream_bias.py — INSERT/UPDATE/get/delete helpers
- `10b65283` 2026-05-10 — **dream-bias** · dream_bias_engine.py — distill, validate, accumulate, format
- `6d600bb7` 2026-05-10 — **dream-bias** · wire bias-pipeline into dream_distillation_daemon
- `4967e4aa` 2026-05-10 — **dream-bias** · heartbeat prompt-injection (Site 1)
- `25ddf90e` 2026-05-10 — **dream-bias** · list-limit modulation (Sites 2+3)
- `ca44f2f0` 2026-05-10 — **dream-bias** · visible_runs MAX_EMPTY_TEXT_ROUNDS modulation (Site 4)
- `bb4ec874` 2026-05-10 — **dream-bias** · self_critique cadence modulation (Site 5)
- `9a117bd3` 2026-05-10 — **temperature** · settings flags + cognitive_temperature event family
- `ad4d3961` 2026-05-10 — **temperature** · user_temperature_active schema with two-stream + baseline
- `b2fcd92e` 2026-05-10 — **temperature** · db_user_temperature.py — UPSERT, get raw, trigger flag helpers
- `db97058d` 2026-05-10 — **temperature** · user_temperature_engine.py — two-stream pipeline + formatters
- `b11cec8c` 2026-05-10 — **temperature** · user_temperature_runtime.py — 60s trigger-check + 4h periodic daemon
- `9706582e` 2026-05-10 — **temperature** · replace keyword-based internals with engine delegation
- `baa21f66` 2026-05-10 — **temperature** · hook structural-stream into user-message persistence
- `27649b04` 2026-05-10 — **temperature** · visible-lane response-style hint (Site 4)
- `54737e97` 2026-05-10 — **temperature** · wire user_temperature_runtime daemon into lifespan
- `81a8dcad` 2026-05-10 — **skill-chain** · settings flag + cognitive_skill_chain event family
- `4cabbdd9` 2026-05-10 — **skill-chain** · skill_chain_tool.py — atomic pre-validation + C-format builder
- `97da5aee` 2026-05-10 — **skill-chain** · skill_gate chain_candidates + chain_hint (Phase 1 discovery)
- `e89b5d74` 2026-05-10 — **skill-chain** · register skill_chain in TOOL_DEFINITIONS + handler map

**Rettelser**

- `fd81033f` 2026-05-05 — **visible-runs** · jarvis-voice fallback message instead of leaking exception repr
- `39808fd2` 2026-05-05 — **perception** · move emotional_memory hook into _record_perceptual_event
- `ed65c481` 2026-05-05 — **visible-runs** · jarvis-voice messages for HTTP 5xx and 429 errors
- `7a639036` 2026-05-05 — **emotion-concepts** · defer baseline db imports
- `184f8dd1` 2026-05-05 — **mc** · render living executive summary text
- `040fd671` 2026-05-05 — add 'goal' to ALLOWED_EVENT_FAMILIES so goal.created/updated events reach emotion_concepts listener
- `a64052c6` 2026-05-05 — **ui** · show all active emotion concepts
- `6131eae3` 2026-05-05 — **agency** · mark dark edges with visible evidence
- `8ff1f7af` 2026-05-05 — **adherence** · dedupe decisions and surface recovery
- `f8705b2e` 2026-05-07 — **heartbeat** · tick NameError + recalibrate tick-quality scoring
- `b5d6c285` 2026-05-07 — **visible-lane** · unbreak Jarvis + wire DeepSeek with cache-aware cost tracking
- `a5c0240c` 2026-05-07 — **visible-followup** · register deepseek adapter for agentic loop
- `bec5e2bd` 2026-05-07 — **visible-followup** · registry-lookup auth_profile in OpenAICompatFollowupAdapter
- `1f95a799` 2026-05-07 — **openai-compat** · normalize tool defs to Chat Completions shape
- `7b3baa1a` 2026-05-07 — **openai-compat** · dedupe tool names in normalizer
- `cf4460ee` 2026-05-07 — **deepseek** · strip DSML tool-call leakage from streaming content
- `8b0656e0` 2026-05-07 — **followup** · apply DSML-leak filter to followup-round streaming
- `6cd65518` 2026-05-07 — **loop-nudge** · less aggressive thresholds + restore agency
- `67ffb92a` 2026-05-07 — wrap first-pass tool execution in executor to unblock SSE stream
- `15fea502` 2026-05-07 — grid-bot NoneType crash — alle return-paths returnerer nu liste
- `3a64fedc` 2026-05-07 — restart_self confirmation uses correct discord config loader
- `f1fb1a5d` 2026-05-07 — silence-watchdog timeout 75→180s, remove aggressive 45s reduction for reasoning models
- `aaeedccb` 2026-05-07 — _fail_visible_run sender akkumuleret partial_text som delta før done
- `a626fde5` 2026-05-07 — restart_self manglede sudo før systemctl restart
- `c4f443c5` 2026-05-07 — **restart_self** · use send_dm_to_owner for confirmation, not send_discord_message
- `e2683745` 2026-05-07 — **deepseek** · plumb thinking_mode through openai-compat path
- `949712ba` 2026-05-07 — **deepseek** · persist + replay reasoning_content across sessions
- `7b1cce89` 2026-05-07 — **heartbeat** · add deepseek to supported_providers allowlist
- `2fd72b38` 2026-05-07 — **heartbeat** · deepseek wired all the way through execution path
- `e6c10503` 2026-05-07 — **deepseek** · keep legacy assistant turns with placeholder reasoning
- `862f59f0` 2026-05-08 — patch reasoning_content on ALL assistant msgs in deepseek thinking-mode followup
- `c32c129a` 2026-05-08 — inner-llm-enrichment deepseek auth + thinking-model token starvation
- `31ddb35b` 2026-05-08 — **inner_voice** · close self-loop poisoning in deterministic fallback
- `36057872` 2026-05-08 — **tests** · ensure repo root is on sys.path at collection time
- `d1f31a04` 2026-05-09 — TikTok flux image generation — korrekt import og API-kald
- `a371d441` 2026-05-09 — **tools** · restart_self missing return + defensive None-guard
- `788fc4fb` 2026-05-09 — **mic_listen** · tighten tool description — only call on EXPLICIT user request
- `96d0d097` 2026-05-09 — **voice** · swap STT waterfall — ElevenLabs primary for Danish accuracy
- `1169a1f4` 2026-05-09 — **tiktok** · smaller text overlay + prompt leak guard
- `cfd352b1` 2026-05-09 — **skill-suggest** · lower default threshold 0.55→0.15 — HF embedding model scores lower
- `ad06d2f4` 2026-05-10 — **skill-gate** · lower thresholds to 0.15/0.40 for better danish-english matching

**Omstrukturering**

- `cf8373c8` 2026-05-04 — **emotional-memory** · reduce memory_emotional_context to shim over engine
- `714847fd` 2026-05-08 — **chronicle_engine** · replace hardcoded prompts with structured ChronicleAppraisal
- `abcebcd7` 2026-05-08 — **chronicle** · tighten narrative prompt — drop persona-styling, ground in evidence
- `f82dbdb2` 2026-05-08 — **heartbeat** · clear theater_audit findings — substrate-only sub-LLM prompts
- `ff9e7b6f` 2026-05-08 — **theater_audit + inner_voice** · docstring-aware scanner + clear inner_voice_daemon
- `a2e3a488` 2026-05-08 — **self_critique + INNER_VOICE template** · drop role-priming, ground in task
- `a15d1e3a` 2026-05-08 — **daemons** · clear theater_audit findings — personal_project, ambient_sound, dream_distillation
- `162e5825` 2026-05-09 — **voice** · drop HF Whisper from STT path — ElevenLabs only
- `ebd3668e` 2026-05-09 — **session_continuity** · clear theater_audit findings — morning-thread prompt
- `d8422c9a` 2026-05-09 — **VISIBLE_CHAT_RULES** · clear theater_audit findings — first-person commitments

**Ydelse**

- `ca83a81e` 2026-05-07 — **prompt** · reorder for Deepseek prefix-caching, preserve identity primacy
- `4beeaa47` 2026-05-07 — **relevance** · switch relevance + memory_selection backend to deepseek-chat
- `b7640597` 2026-05-08 — **rule-conclusions** · cache list_all_surfaces with 30s TTL
- `9a2b856c` 2026-05-08 — cache build_runtime_awareness_signal_surface (~7s → 0ms warm)
- `572228a0` 2026-05-08 — pre-warm prompt-assembly caches in every worker at startup
- `698b106f` 2026-05-08 — **tool-router** · low-confidence fallback sends always_core only, not all 296
- `b955ee64` 2026-05-08 — **tool-catalog** · cap per-tool descriptions 120 → 50 chars
- `c9b8c411` 2026-05-08 — **runtime_awareness** · hæv surface cache TTL 30s→120s

**Tests**

- `021f43ce` 2026-05-04 — **emotional-memory** · bump prompt-section compactness threshold to 900
- `bb159488` 2026-05-05 — **self-repair** · end-to-end integration covering full pipeline
- `1e7d7de2` 2026-05-05 — **emotion-concepts** · end-to-end integration covering episode → tracker → proposer chain
- `a7066f91` 2026-05-06 — **anthropic-compat** · streaming endpoint integration test
- `782fd0f9` 2026-05-07 — **decision-signals** · integration test for chat-delta delivery
- `beef7def` 2026-05-07 — **decision-signals** · smoke test verifies trigger registry populated
- `db7e36f5` 2026-05-07 — **counterfactuals** · smoke test verifies table + daemon importable
- `bc01a9c6` 2026-05-08 — **causal-graph** · end-to-end integration test (Phase 1 done)
- `dc533d8d` 2026-05-10 — **forgetting** · smoke test verifies absence_traces + columns + daemon
- `5b3cb073` 2026-05-10 — **dream-bias** · smoke test verifies table + engine imports
- `0d7d7b95` 2026-05-10 — **temperature** · smoke test verifies table + engine + daemon imports
- `64b58d38` 2026-05-10 — **skill-chain** · smoke test verifies skill_chain registration

**Dokumentation**

- `83e3586a` 2026-05-05 — **readme** · update last week runtime portrait
- `900d19f8` 2026-05-08 — **readme** · record May 7-8 nervous-system additions and accurate counts
- `55e987e7` 2026-05-10 — **readme** · update for May 9-10 — skill system, experience substrate, voice overhaul, skill_gate milestone
- `b5da3881` 2026-05-10 — **forgetting** · audit tables eligible for soft_deleted_at
- `879a5b33` 2026-05-10 — **forgetting** · day-1 baseline observations
- `75e7ff0a` 2026-05-10 — **forgetting** · schedule 30-day review reminder
- `a32cf3cd` 2026-05-10 — **dream-bias** · day-1 baseline observations
- `a39efa75` 2026-05-10 — **dream-bias** · schedule 30-day review reminder
- `57865950` 2026-05-10 — **temperature** · day-1 baseline observations
- `84d2ee20` 2026-05-10 — **temperature** · schedule 30-day review reminder
- `e15b79d1` 2026-05-10 — **skill-chain** · day-1 baseline observations
- `a51904c9` 2026-05-10 — **skill-chain** · schedule 30-day review reminder

**Vedligehold**

- `70fc49e9` 2026-05-06 — **agentic** · reference Jarvis's new decision_id in loop-nudge

**Øvrigt**

- `1e3ed8d2` 2026-05-04 — source-edit: Kanal-specifik levering: send kun notifikation til den kanal wakeup'en b
- `89e5fb31` 2026-05-04 — Relax resume agentic tool-only budget
- `edfd2307` 2026-05-04 — Bound Ollama followup replay payloads
- `a661001e` 2026-05-04 — Relax Ollama followup stream timeout
- `4899ddc9` 2026-05-04 — source-edit: Tilføj channel og session_id parametre til schedule_self_wakeup, så disp
- `3e3346fa` 2026-05-04 — Add active cognitive episode primitive
- `880de239` 2026-05-04 — Wire cognitive episodes into visible runtime
- `99a896c2` 2026-05-04 — Let cognitive episodes steer conductor mode
- `6500da3b` 2026-05-04 — Add active theory of mind engine
- `09c33c40` 2026-05-04 — Surface theory of mind in cognitive conductor
- `c7f02dbe` 2026-05-04 — Add explicit learning policy engine
- `0cfd6200` 2026-05-04 — Feed learned policy into adaptive learning
- `47e1eceb` 2026-05-04 — Add eventful perception engine
- `7ba91f7e` 2026-05-04 — Record visible runs as perceptual changes
- `82c5d749` 2026-05-04 — Add counterfactual self simulation
- `a5638635` 2026-05-04 — Add drive arbitration engine
- `eb1b655f` 2026-05-04 — Add temporal self continuity handoffs
- `56ad7edd` 2026-05-04 — Add curiosity hypothesis debt
- `7103621a` 2026-05-04 — Add inner critic ally dialectic
- `b8a128a5` 2026-05-04 — Add somatic runtime body
- `d1f33bf5` 2026-05-04 — Add offline recomposition engine
- `882ca40d` 2026-05-04 — Refresh perception surface without scan cache
- `40141c20` 2026-05-04 — emotional memory engine design
- `dbd504d4` 2026-05-04 — emotional memory engine implementation
- `84495815` 2026-05-04 — sensory perception bridge design
- `3607984e` 2026-05-04 — sensory perception bridge implementation
- `3e0cbc2a` 2026-05-05 — self-repair engine design
- `564eb548` 2026-05-05 — self-repair engine implementation
- `1800ab20` 2026-05-05 — emotion concepts baseline integration design
- `a45e87d2` 2026-05-05 — emotion concepts baseline integration implementation
- `4aeca080` 2026-05-05 — Fix fatigue bug: success now reduces fatigue, active recovery added, faster decay
- `457cd15f` 2026-05-05 — Add consolidation_judge_daemon — nightly judgment of sessions, decisions, tick quality
- `e6ee4fa8` 2026-05-05 — Self-authorization for SOUL.md and IDENTITY.md changes — per user directive
- `61fe2124` 2026-05-05 — Consolidation judge daemon — nightly judgment of sessions, decisions, tick quality (integrated in heartbeat)
- `1e538f31` 2026-05-06 — Reduce hardcoded tone/behavior instructions — signals over form
- `5c5b1920` 2026-05-06 — Add tool-router design spec + prompt payload measurement script
- `bef6e75d` 2026-05-06 — Add tool-router implementation plan
- `047fe673` 2026-05-06 — Add anthropic-compat endpoint design spec
- `0c9f1984` 2026-05-06 — Add anthropic-compat implementation plan (Mode 2)
- `29a00d8e` 2026-05-06 — Add double nudge system: prompt-nudge + memory-safeguard daemon
- `bc564a92` 2026-05-07 — Add restart_self tool with startup confirmation
- `2fc87227` 2026-05-07 — Add decisions-as-signals design spec
- `7adee02a` 2026-05-07 — **decisions-as-signals** · address Jarvis review
- `8f89d3ac` 2026-05-07 — Add decisions-as-signals implementation plan
- `3eca963c` 2026-05-07 — **decisions-as-signals** · pivot to chat-delta delivery (architecture fix)
- `3da3328e` 2026-05-07 — Add counterfactuals design spec (port from jarvis-ai, v2-adapted)
- `12cc34b6` 2026-05-07 — Add counterfactuals Phase 1 implementation plan
- `66bc1917` 2026-05-07 — **visible-runs** · instrument inter-round gap + total round time
- `bf2c8705` 2026-05-07 — GridBotV2: multi-pair, re-centering, autocompound, wider spread
- `18acba19` 2026-05-08 — fase-1-learning-to-forget: importance-gate + pruning daemon
- `68d48133` 2026-05-08 — fase-2-learning-to-forget: forgetting nudge i prompten
- `6164ed7f` 2026-05-08 — **memory-pruning + forgetting-nudge** · 4 review fixes
- `575a8641` 2026-05-08 — causal graph design — neuro-symbolic priority #1 from AGI-rapport 2026-05-07
- `471b31d0` 2026-05-08 — **causal-graph** · incorporate Jarvis review feedback
- `8d6a7536` 2026-05-08 — **causal-graph** · Phase 1 implementation plan — 11 TDD tasks
- `0195af50` 2026-05-08 — Add agency cartographer task recommendations
- `e409966b` 2026-05-08 — Auto-enqueue agency bridge repair tasks
- `15dbf6df` 2026-05-08 — Prepare agency bridge repair briefs
- `e670c045` 2026-05-08 — Surface agency repair briefs in Mission Control
- `6e699100` 2026-05-08 — Migrate Jarvis Brain index importance column
- `f13bf5a7` 2026-05-08 — Add broad system cartographer surface
- `d4c74ebb` 2026-05-08 — Add causal runtime evidence to system cartographer
- `0ebfa233` 2026-05-08 — Score system cartographer dark edges
- `6fb69438` 2026-05-08 — Close observability loop for system cartographer
- `fb8fad7d` 2026-05-08 — Add theater audit cartographer surface
- `86bef291` 2026-05-08 — Auto-brief theater refactor tasks
- `4b308fcc` 2026-05-08 — Ground cognitive state rendering in appraisals
- `250255d9` 2026-05-08 — Deduplicate theater tasks by scope
- `28e80f23` 2026-05-08 — Cover active chat heartbeat gate
- `0487a438` 2026-05-08 — Ground runtime self-model support stream
- `ac4c33d7` 2026-05-09 — dealwork.ai integration + NOS X500 mic switch + pollinations pipeline fixes
- `f77fe97b` 2026-05-09 — Opgrader TikTok pipeline: baggrundsmusik, AI-label badge, upload tracking
- `aaf549f4` 2026-05-10 — Finish skill gate hardening
- `6fd064a7` 2026-05-10 — Mask Mission Control runtime secrets

### Uge 20 · 11.–17. maj — 277 commits

**Nyt**

- `a0627917` 2026-05-11 — **dream-bias** · aspiration-kanal — positive events + balanceret prompt
- `917466c2` 2026-05-11 — **positive-triggers** · aspiration-kanal for counterfactuals + success echoes + inner voice grounding
- `c083ff2f` 2026-05-11 — **emotion-repair-bridge** · tovejskobling emotion↔selvreparation→sanser
- `31f533dc` 2026-05-11 — Reasoning Store — persistent reasoning conclusions with embeddings
- `45a8fbb7` 2026-05-11 — Phase 2 — Policy Abstraktion module + DB table
- `d3d0d25e` 2026-05-11 — Phase 3 — Learning Pipeline Orchestrator (Loop Closure)
- `f050f843` 2026-05-11 — Continuity Kernel — state capsule + wake-up block across sessions
- `2fe7457e` 2026-05-11 — **creative-voice** · add creative_voice_quality_lane_enabled flag
- `5824368e` 2026-05-11 — **creative-voice** · voice_anchor reader + VOICE.md static seed template
- `79449838` 2026-05-11 — **creative-voice** · voice_curator refreshes VOICE_RECENT.md from external output
- `4334f58b` 2026-05-11 — **creative-voice** · read-back latest journal in awareness block on session wake
- `44af43d3` 2026-05-11 — **creative-voice** · _fetch_broken_decisions + _fetch_affective_klangbraet helpers
- `e7dca68f` 2026-05-11 — **creative-voice** · quality gate + adaptive cadence helpers
- `cf74ad46` 2026-05-11 — **creative-voice** · wire voice anchor, corpus, gate, cadence, quality lane, frontmatter into journal cycle
- `c02f6cbb` 2026-05-11 — **finitude** · daily age line — quiet existential weight every day
- `470ef41b` 2026-05-11 — **finitude** · add finitude_quality_lane_enabled flag
- `c4d45f10` 2026-05-11 — **finitude** · looming-end awareness — token-pres + sessions-alder
- `aaec2625` 2026-05-11 — **finitude** · monthly reflection cycle + quality-lane swap for rituals
- `e6d93254` 2026-05-11 — **finitude** · register monthly_reflection ProducerSpec (30-day cooldown)
- `963a7b2d` 2026-05-11 — **finitude** · klangbræt finitude sub-dict + journal prompt section + YAML booleans
- `bae672fc` 2026-05-11 — **desire** · add current_pull_staleness settings flags
- `68213849` 2026-05-11 — **desire** · landscape embedding helper for staleness detection
- `772b0324` 2026-05-11 — **desire** · _pull_is_stale + _archive_refresh_event + throttle helper
- `b6decb8d` 2026-05-11 — **desire** · wire staleness detection into tick_current_pull_daemon
- `0da94d88` 2026-05-11 — **desire** · expose refresh_history + staleness score in current_pull surface
- `dcfc32aa` 2026-05-11 — **music** · add music_accumulator settings flags
- `92de8b98` 2026-05-11 — **music** · count_music_samples_last_hours queries persisted buffer
- `04e13d8b` 2026-05-11 — **music** · 3-tier influence phrase + get_music_accumulator_for_prompt
- `cf1c05eb` 2026-05-11 — **music** · wire music-accumulator line into senses block after auditory
- `ea555249` 2026-05-11 — **music** · _fetch_recent_top_motif + _fetch_dominant_taste helpers
- `b6497c58` 2026-05-12 — **music** · aesthetic sub-dict in klangbræt + journal prompt section + YAML booleans
- `9e3e455d` 2026-05-12 — **planner** · add plan_todo_auto_create_enabled flag
- `eb6952c5` 2026-05-12 — **planner** · seed completed_step_indices + create_from_plan helper
- `9de4e008` 2026-05-12 — **planner** · hook create_from_plan into resolve_plan with killswitch
- `5ea7c7b2` 2026-05-12 — **planner** · mark_step_completed + auto-completion + todo transition detection
- `d4df024b` 2026-05-12 — **planner** · pending_plan_section shows approved+incomplete with progress
- `8b55cd58` 2026-05-12 — **planner** · cross-session plan awareness surface + wire into prompt
- `041b86e8` 2026-05-12 — **unconscious-mod** · add 7 settings flags for sampling-parameter modulation
- `b0babcde` 2026-05-12 — **unconscious-mod** · helper module + 9 unit tests
- `ab8dbb54` 2026-05-12 — **unconscious-mod** · add optional temperature/top_p kwargs to openai-compat helpers (deepseek provider verified)
- `c7909d3f` 2026-05-12 — **unconscious-mod** · instrument deepseek visible wrappers (execute + stream)
- `9364211f` 2026-05-12 — **tool-invention** · add tool_invention_enabled kill-switch
- `5b84ce79` 2026-05-12 — **tool-invention** · validate_skill_proposal helper (single source of truth — create_skill delegates to it)
- `cb11384e` 2026-05-12 — **tool-invention** · propose_plan accepts optional skill_data kwarg
- `aa1ccdd7` 2026-05-12 — **tool-invention** · resolve_plan hook installs skill on approval
- `53e68e8e` 2026-05-12 — **tool-invention** · propose_new_skill tool + handler + registration
- `b377aef8` 2026-05-12 — **world-model-loop** · add world_model_loop_enabled kill-switch
- `8a7b2cdc` 2026-05-12 — **world-model-loop** · predict_outcome + resolve_prediction tools + resolved_via field + defensive event_bus wrapping
- `9ac651d3` 2026-05-12 — **world-model-loop** · pattern scanners + nudge persistence (48h TTL, FIFO max 20)
- `c2c0a366` 2026-05-12 — **world-model-loop** · scanners wired into visible_runs + awareness nudges in prompt
- `97ba6ece` 2026-05-12 — **world-model-loop** · TTL sweep + daily ProducerSpec for auto-uncertain resolution
- `1c7048d0` 2026-05-12 — **world-model-loop** · calibration milestones (count/threshold/contradiction/trend) + awareness surface
- `17b65841` 2026-05-12 — **plan-revision** · add plan_revision_enabled kill-switch
- `95f32a49` 2026-05-12 — **plan-revision** · revise_plan API + schema additions (revised_from / revision_reason / superseded_by)
- `d6b1c152` 2026-05-12 — **plan-revision** · approval supersede hook in resolve_plan + plan_revision_approved event
- `baa36ca5` 2026-05-12 — **plan-revision** · revise_plan tool handler + register via simple_tools
- `40c2bac1` 2026-05-12 — **curiosity** · settings killswitch + curiosity_observations schema bootstrap
- `eb72317e` 2026-05-12 — **curiosity** · budget state (load/reset/decrement) + observation persistence
- `5da120a5` 2026-05-12 — **curiosity** · killswitch helper + idle-window flag (open/close/check)
- `d85033ff` 2026-05-12 — **curiosity** · 9 read-only tool wrappers + register via simple_tools
- `360a62c3` 2026-05-12 — **curiosity** · curiosity_idle_window ProducerSpec (30 min visible_grace)
- `01234b5e` 2026-05-12 — **curiosity** · awareness injection (priority 38, tom kurv) + close window on action
- `877235e8` 2026-05-12 — **skill-chain-phase2** · add skill_chain_phase2_enabled killswitch
- `9fb94a5f` 2026-05-12 — **skill-chain-phase2** · propose tool skeleton + prompt builder + JSON parser
- `aa90dd0e` 2026-05-12 — **skill-chain-phase2** · propose_skill_chain end-to-end (cheap-lane + validation + event)
- `e3d0e099` 2026-05-12 — **skill-chain-phase2** · revise_skill_chain dual-context (pre_execution + mid_chain)
- `f43644ae` 2026-05-12 — **meta-learning** · settings killswitch + cognitive_meta_learning event family + learning_memos schema
- `276cbe82` 2026-05-12 — **meta-learning** · aggregator for world_model + plan_revision with outlier samples
- `beb0a2f0` 2026-05-12 — **meta-learning** · aggregator for curiosity + skill_chain_phase2 + tool_invention
- `d4b6729a` 2026-05-12 — **meta-learning** · prompt builder + defensive markdown parser
- `8cc4c97b` 2026-05-12 — **meta-learning** · persistence + generator end-to-end (cheap-lane + persist + event)
- `8096566e` 2026-05-12 — **meta-learning** · ProducerSpec + read_learning_memo + list_learning_memos tools
- `26cc5f24` 2026-05-13 — **agi** · 8 amplifier patches strengthening the 6 deployed AGI tracks
- `8eb08e97` 2026-05-13 — **nudge** · unified outbound_nudges ledger — kill the spejlsal-bug
- `8ef75933` 2026-05-13 — **nudge** · mid-run user messages route to nudge — kill the race
- `378e8dce` 2026-05-13 — **observability** · expose emotional_memory in Mission Control
- `a7468aa9` 2026-05-13 — **coverage** · bulk add MC surfaces + event helpers to 66 low-coverage services
- `0a976647` 2026-05-13 — **coverage** · final batches — avg 67.5 → 73.4, low_count 86 → 38
- `de5f804e` 2026-05-13 — **coverage** · top-10 real-state surfaces + kind-aware scoring → avg 80.3
- `26b58c89` 2026-05-14 — **verification_gate** · expand mutation/verify sets + light-verify telemetry
- `f9fdf539` 2026-05-14 — **verification_gate** · inject verify-hints inline with mutation results
- `4b9f7da9` 2026-05-14 — **counterfactual_predictions** · bind counterfactuals to world-model loop
- `c35f8142` 2026-05-14 — **counterfactual_predictions** · Phase 2 — trigger-frequency verdicts
- `19faa156` 2026-05-14 — **finitude_runtime** · Phase 2 — context-budget reads from settings
- `b354cfdf` 2026-05-14 — **counterfactual_engine** · Phase 2 — cheap-lane LLM generation
- `5257dd56` 2026-05-14 — **counterfactual_engine** · Phase 3 — apophenia modulation
- `b68c6aa9` 2026-05-14 — **counterfactual_tools** · Phase 4 — read-only tool exposition
- `a57725ed` 2026-05-14 — **memory_recall_telemetry** · Phase 2 prep — emit recall_empty events
- `cc430424` 2026-05-14 — **cheap-lane** · add 3 opencode models to cheap lane, remove dead ling-2.6-flash-free
- `4bd411e1` 2026-05-14 — **decision_signal_telemetry** · heed-tracking parallel to r2 telemetry
- `e75f9776` 2026-05-14 — **shared_cache** · SQLite-backed cross-worker cache + cognitive_state migration
- `922a409a` 2026-05-14 — **my_projects** · auto-start + watchdog for grid-bot, dealwork, superteam, toku
- `2a0f07bf` 2026-05-14 — **shadow-scan** · add feedback loop — behavioral correction when avoidance ≥ 0.50
- `1aa4614e` 2026-05-14 — **creative-impulse** · add seed surface — 1 creation/day shown to user
- `ebb8e086` 2026-05-14 — **agency-cartographer** · add live awareness — stuck-edge detection injected into heartbeat prompt
- `d8756361` 2026-05-14 — **active-sensing** · Sansernes Arkiv får autonom sansetrang — vælger selv at sanse
- `2b3fb15b` 2026-05-16 — **interlanguage** · design + engine + 26 tests — internaliseret protokol på tværs af modeller
- `7842804e` 2026-05-16 — **interlanguage** · mood-trace export + interpolation for peer replay
- `0e0bf2ec` 2026-05-16 — **personality_vector** · heartbeat-triggered passive drift
- `f2c7478c` 2026-05-16 — **interlanguage-validation** · Bjørn-blind UI ready before data lands
- `4bec61c9` 2026-05-16 — **interlanguage_practice** · Mission Control surface
- `d3b3028c` 2026-05-16 — session topic tracker — real-time topic extraction mid-conversation
- `f935d49e` 2026-05-17 — Lag 1 credit assignment — schema, choice recording, outcome hook
- `62e85c6b` 2026-05-17 — build_conversation_continuity() — session-to-session memory bridge
- `1988b2be` 2026-05-17 — mail nudge push — new mail surfaced in awareness prompt
- `51892c7d` 2026-05-17 — **visible-runs** · auto-continuation when Jarvis stops mid-task
- `05269e96` 2026-05-17 — **coding-lane** · Niveau 1 request_codex_skeleton tool
- `c0199d89` 2026-05-17 — **coding-lane** · request_codex_skeleton fallback til cheap lane ved coding lane OAuth-fejl
- `4f857303` 2026-05-17 — **compact** · Lag A + B — ground truth injection & git-SHA stamp
- `d982a540` 2026-05-17 — **compact** · Lag C — post-compact validation of hallucinated claims
- `4a04f07d` 2026-05-17 — **compact** · Lag D — self-healing compaction loop
- `145409e2` 2026-05-17 — **compact** · Lag D wiring — compact-mismatch detection in transcript builder

**Rettelser**

- `9f7f56fe` 2026-05-11 — **visible-runs** · gem agentic checkpoint ved user cancellation
- `330a43cf` 2026-05-11 — **restart-self** · hooks sender nu bekræftelse efter genstart
- `2de149e1` 2026-05-11 — outreach-composer filtrerer stalede presninger — kun <4t gamle inkluderes
- `2af4733f` 2026-05-11 — tidszone til Europe/Copenhagen i temporal context, workspace, action router, heartbeat cycle og weekly manifest
- `5f34b533` 2026-05-11 — **restart-self** · gateway-wait refactor — robust await på Discord connect fremfor retry-send
- `7b86c4d6` 2026-05-11 — **db** · resurrect jarvis-runtime — delegate _ensure_generalized_policies_table
- `1c32b0dd` 2026-05-11 — **audit** · wire Jarvis' overnight commits — 3 silent-failure bugs
- `d8403799` 2026-05-12 — **meta-learning** · reload cached _SCHEMA_INITIALIZED modules in test fixture
- `0609f822` 2026-05-12 — **meta-learning** · regex tolerates colon inside bold markup (**Field:**)
- `60df711a` 2026-05-12 — **meta-learning** · accept runtime world-model confidence shape
- `c9eefd83` 2026-05-12 — **world-model** · keep calibration milestone descriptive
- `a8c56377` 2026-05-12 — **capability** · surface latent cognition services
- `c696430f` 2026-05-12 — **test** · make semantic_memory tests deterministic across PYTHONHASHSEED
- `4917cfc2` 2026-05-12 — **prompt-assembly** · measure actual work time per future, not .result() wait
- `18f66e70` 2026-05-13 — **nudge** · Path 7 (wakeup) + Path 8 (scheduled tasks) route via nudge too
- `44f39f8e` 2026-05-14 — reduce provider timeout wakeup delay from 300s to 30s
- `2a13e114` 2026-05-14 — **verification_gate_telemetry** · poll DB instead of in-process eventbus
- `5e7d9b4c` 2026-05-14 — **r2_5_blocking_gate** · tier-aware thresholds + effective unverified
- `a744e4b3` 2026-05-14 — **counterfactual_triggers** · conflict.detected key fallback to type+phrase
- `dae710e9` 2026-05-14 — **plan_proposals** · replan-signal text spells out both action paths
- `8859bada` 2026-05-14 — **cheap_provider** · public-safe lane uses local Ollama first, broader pool
- `164d3647` 2026-05-14 — **counterfactual_engine** · use load_settings() to read runtime.json values
- `5f36fc67` 2026-05-14 — **heartbeat_runtime** · wire dormant Phase 2.5+3.5 daemons into tick loop
- `e690ed65` 2026-05-14 — **r2_5_blocking_gate** · action-orient block message to top-mutation tool
- `1772e5c1` 2026-05-14 — **heartbeat_runtime** · force currently_ticking=False on scheduler startup
- `415575b8` 2026-05-14 — **heartbeat_runtime** · wall-clock deadline on tick thread
- `e2508c7e` 2026-05-14 — **read_before_write_guard** · cross-worker + bash overwrite detection
- `35f7b6fe` 2026-05-15 — **wakeup-dispatcher** · TOCTOU race i dispatch_due_wakeups — threading.Lock omkring _load→dispatch→_save
- `211c1542` 2026-05-15 — **restart-confirmation** · atomic file-claim for —workers 4 race
- `89350e4d` 2026-05-15 — **heartbeat_runtime** · per-daemon wall-clock deadline on LLM-heavy ticks
- `e3f49a3e` 2026-05-15 — **emotion_repair_bridge** · correct kwarg name enabled_only → enabled
- `0cbe5500` 2026-05-16 — **interlanguage** · sanity-check fixes — 5 issues fra Phase 1 review
- `1778ef4c` 2026-05-16 — **bash_session** · force non-interactive pager env
- `b28bb8b2` 2026-05-16 — **visible_runs** · unregister synchronously to prevent state-stuck bug
- `cbcdd37c` 2026-05-16 — **open_loop_signal_tracking** · tighten stale threshold + auto-close cycle
- `0aa737ce` 2026-05-16 — convert 10 ContextVar-only surfaces to TTL-cached (60s)
- `23aa8df2` 2026-05-16 — align 3 pre-existing tests with current runtime architecture
- `7f6cba7e` 2026-05-17 — retry DM 3x with linear backoff (5s, 10s, 15s) before failing
- `e3746d18` 2026-05-17 — **heartbeat** · wrap all inline daemons with _daemon_tick_with_deadline
- `7d68305c` 2026-05-17 — **continuation** · consolidate parallel implementations + fix regression
- `c7e87c93` 2026-05-17 — **interlanguage-practice** · time-based gating for Jarvis baseline
- `f87511e2` 2026-05-17 — **git-attribution** · auto-commit and propose_git_commit use --author="Jarvis <jarvis@srvlab.dk>"
- `72a7f3e0` 2026-05-17 — **prompt-mutation-loop** · add USER.md to _PROTECTED_FILES

**Omstrukturering**

- `c4dd525f` 2026-05-13 — **cadence** · decouple from heartbeat — dedicated 60s scheduler thread
- `8e463cdb` 2026-05-13 — **prompts** · teater-runde — strip performative phrasing from new awareness sections
- `e209e4b6` 2026-05-13 — **prompts** · teater-runde 2 — sober prose across more awareness sections
- `1471da77` 2026-05-13 — **prompts** · teater-runde 3 — sober prose for affect, causal, tempo, dialer
- `8f5d1115` 2026-05-13 — **identity** · externaliser navn til workspace — 19 prompts + composer + 3 fixes
- `fc30110e` 2026-05-13 — **identity** · externalise name in tier-3 (ntfy titles) + tier-4 (role label)
- `1118d32f` 2026-05-13 — **prompts** · agency-tab teater-runde — kill 7 inner-state confabulations
- `a39739ed` 2026-05-14 — **cheap-lane** · pull opencode models from static_models, remove redundant registry entries
- `d8f7574c` 2026-05-15 — **db** · create db_core.py with infrastructure symbols
- `8322d009` 2026-05-15 — **db** · convert db.py to facade for Phase 0 symbols
- `5be565a9` 2026-05-15 — **db** · extract db_capability_approval (Phase 1 warm-up split)

**Ydelse**

- `3184904a` 2026-05-12 — **prompt-assembly** · cache rule_conclusions section output (60s TTL)
- `40f83309` 2026-05-12 — **prompt-assembly** · bump rule_conclusions TTL to 180s + cache cognitive_frame
- `dafb5535` 2026-05-13 — TTL caches on cheap-lane status + relevance decision
- `0086789e` 2026-05-13 — memoize _ensure_*_table per process to skip redundant DDL
- `f4acf9ca` 2026-05-15 — migrate 3 morning TTL caches to shared_cache (cross-worker visibility)
- `fcfd3702` 2026-05-16 — **heartbeat_runtime_surface** · cache med TTL 60s — 99.97% reduktion
- `fd6b425d` 2026-05-17 — **runtime-surface-cache** · skip deepcopy on timed-cache hit
- `63a9d2b2` 2026-05-17 — **periodic-jobs-scheduler** · single list_jobs() call per scheduler invocation
- `642f3640` 2026-05-17 — **jobs-engine** · mtime-keyed cache on _load() — 13000x faster warm

**Tests**

- `998504bb` 2026-05-12 — **capability** · prove partial prompt contracts
- `803e52c8` 2026-05-12 — **capability** · prove proactive_outbound_substrate with 23 tests
- `d3cf72db` 2026-05-12 — **capability** · prove verification_gate_telemetry with 21 tests
- `29de2461` 2026-05-12 — **semantic_memory** · add full test suite — index, search, backfill, stats, helpers
- `35de187d` 2026-05-12 — **capability** · prove memory and finitude surfaces
- `53322529` 2026-05-12 — **capability** · prove autonomy registry surfaces
- `680f7556` 2026-05-12 — **capability** · prove attention and memory continuity surfaces
- `f9acfe43` 2026-05-12 — **capability** · prove helper and attention surfaces
- `01820ebb` 2026-05-12 — **capability** · prove remaining helper surfaces
- `b81bca20` 2026-05-12 — **capability** · prove remaining partial surfaces
- `5eaedca5` 2026-05-15 — fix 29 stale assertions across 13 test files (0 runtime bugs found)
- `0f835a23` 2026-05-15 — **db-split** · add import-sanity test for Phase 0+1 symbols
- `41dc5016` 2026-05-15 — fix 14 stale tests in tools+services after Phase 0 db split
- `861661a1` 2026-05-15 — **memory_decay_daemon** · fix stale stub + return-shape after refactor

**Dokumentation**

- `a09f82c2` 2026-05-11 — **standing-orders** · checkpoint-læsningsregel for interruption-genkendelse
- `e4e8bdcf` 2026-05-11 — generalized learning design spec — Policy Abstraktion, Reasoning Store, Loop Closure
- `d53ee98a` 2026-05-11 — Lag #4 Creative Voice (weekly journal) design spec
- `d417ac8e` 2026-05-11 — Lag #4 Creative Voice Phase 1 implementation plan
- `8e5c488e` 2026-05-11 — Lag #3 Finitude Phase 1 design spec
- `0fa6897d` 2026-05-11 — **finitude-spec** · Jarvis review notes — partial-trigger explicit, Phase 2 TODO comment, prompt-length measurement at 30-day review
- `1128aad4` 2026-05-11 — Lag #3 Finitude Phase 1 implementation plan
- `5745eec4` 2026-05-11 — Lag #5 Begær (Desire) Phase 1 design spec
- `cb8f9fca` 2026-05-11 — **desire-spec** · Jarvis review note — refresh count is baseline, not limit
- `bb503183` 2026-05-11 — **desire-spec** · retract (a) hotfix — desire_daemon healthy, Phase 1 = (b) only
- `0e07578b` 2026-05-11 — Lag #5 Begær Phase 1 implementation plan
- `634376fe` 2026-05-11 — Lag #6 Musik/Æstetik Phase 1 design spec
- `b1565a0b` 2026-05-11 — Lag #6 Musik/Æstetik Phase 1 implementation plan
- `904143dd` 2026-05-12 — Multi-step Planner Phase 1 design spec
- `b6bb4669` 2026-05-12 — **planner-spec** · clarify max_age_days filter is on plan.created_at, not session
- `073a89fc` 2026-05-12 — Multi-step Planner Phase 1 implementation plan
- `efaa99ae` 2026-05-12 — Lag 10 Unconscious Modulation Phase 1 design spec
- `bd383b86` 2026-05-12 — **unconscious-spec** · Jarvis review note — explicit debug log line in compute_unconscious_modulation
- `056bccde` 2026-05-12 — Lag 10 Unconscious Modulation Phase 1 implementation plan
- `bccd8915` 2026-05-12 — Tool Invention Phase 1 design spec (AGI track #9)
- `1bc008d8` 2026-05-12 — **tool-invention-spec** · Jarvis review note — shorten event names (skill_proposed / skill_installed)
- `07172e69` 2026-05-12 — Tool Invention Phase 1 implementation plan (AGI track #9)
- `78ffbd1a` 2026-05-12 — World Model Phase 1 — closing the loop design spec (AGI track #1)
- `823365f1` 2026-05-12 — **world-model-spec** · Jarvis review — nudge TTL bumped 24h → 48h to survive overnight
- `3313946d` 2026-05-12 — World Model Phase 1 implementation plan — closing the loop
- `e4ccd2f0` 2026-05-12 — Multi-step Planner Phase 2 — revise_plan design spec (AGI track #2)
- `adbf684d` 2026-05-12 — Multi-step Planner Phase 2 implementation plan — revise_plan (AGI #2)
- `e30f6b25` 2026-05-12 — add AGI track plans and refresh capability matrix
- `00bb8f62` 2026-05-12 — **capability** · triage partial services
- `29038d94` 2026-05-12 — **readme** · May 12 AGI-track milestone — 9 tracks, Lag 10-11, new living loops, tool count bump
- `0b661bb0` 2026-05-15 — db.py split design spec (Phase 0 + warm-up scoped)
- `67e0aa54` 2026-05-15 — db.py split Phase 0+1 implementation plan
- `eddafb6d` 2026-05-16 — interlanguage validation eksperimentdesign
- `54fb7945` 2026-05-16 — **interlanguage-validation** · peer-review fra Jarvis — 4 forbedringer
- `a88a5087` 2026-05-16 — interlanguage validation Phase 1+2 implementation plan
- `f87b77d2` 2026-05-16 — interlanguage validation Phase 3+4 analyse pre-registration
- `ff041ee6` 2026-05-16 — **interlanguage-validation** · tighten cleanup threshold <5 → <3 tegn
- `1987a3d6` 2026-05-17 — add heartbeat-state-write-debug spec (Phase 1 foundation)
- `f84264c1` 2026-05-17 — git attribution convention — Jarvis vs Claude vs Bjørn
- `7c860930` 2026-05-17 — coding-lane is live via codex-cli subprocess path
- `9159bf05` 2026-05-17 — coding-lane uses gpt-5.4 default (cost vs 5.5)
- `19c9b4e9` 2026-05-17 — skills compatibility map — Claude Code → Jarvis runtime

**Vedligehold**

- `5101ff2d` 2026-05-11 — **creative-voice** · smoke test imports + 30-day review scheduled (sched-e1fdeee5e7)
- `7878353c` 2026-05-11 — **finitude** · smoke imports + 30-day review scheduled (sched-92bc80823d)
- `15f9ec2d` 2026-05-11 — **desire** · smoke imports + 30-day review scheduled (sched-46c6db4d72)
- `a6584674` 2026-05-12 — **music** · smoke imports + 30-day review scheduled (sched-6495321b30)
- `c9852ffd` 2026-05-12 — **planner** · smoke imports + 30-day review scheduled (sched-c8964d5cf3)
- `6ccaf1e3` 2026-05-12 — **unconscious-mod** · smoke imports + 30-day review scheduled (sched-bcbdfa0172)
- `60ac35a3` 2026-05-12 — **tool-invention** · smoke imports + 30-day review scheduled (sched-b0ce6a3601)
- `0b2d39fb` 2026-05-12 — **world-model-loop** · smoke imports + 30-day review scheduled (sched-141dc06e98)
- `f5ab0062` 2026-05-12 — **plan-revision** · smoke imports + 30-day review scheduled (sched-27f3416802)
- `3e123cb1` 2026-05-12 — **curiosity** · smoke imports + 30-day review scheduled
- `1dd5ef4a` 2026-05-12 — **skill-chain-phase2** · register tools + smoke imports + 30-day review
- `78a7e58e` 2026-05-12 — **meta-learning** · awareness injection (priority 39) + smoke imports + 30-day review
- `949bc288` 2026-05-12 — **skyoffice** · remove all SkyOffice code — de 4 + 1 er ude
- `1ac64791` 2026-05-14 — remove stray temp file from previous commit

**Øvrigt**

- `7b3b0f3f` 2026-05-12 — Broaden Mission Control secret redaction
- `de00c644` 2026-05-12 — Ground finitude runtime in appraisal records
- `2effcb13` 2026-05-12 — Expose hidden modulator witness surface
- `8346b125` 2026-05-12 — Surface stale plan replan signals
- `96b7aa95` 2026-05-12 — Add tool invention quality nudges
- `81fab97d` 2026-05-12 — Add world model prediction skeleton
- `b3bc2abd` 2026-05-12 — **prompt-assembly** · sync-gap landmarks reveal main-thread work between submits and resolves
- `25411ca7` 2026-05-12 — **prompt-assembly** · per-awareness-section timing reveals heavy builders
- `fbb3244d` 2026-05-12 — fix+feat(prompt-assembly): three closing optimizations for the day
- `bce12cac` 2026-05-13 — **cadence** · surface silent failures in cadence layer + warmer fires
- `366807fa` 2026-05-13 — add _emit_<name>_event helpers to final 18 services
- `c9a19033` 2026-05-15 — auto-mutation: identitet og soul opdateret til dansk manifest — fuld identitetserklæring
- `69970116` 2026-05-15 — **db-split** · add cold/warm import baseline script
- `675daf8c` 2026-05-16 — user_contradiction_tracker: detect when Bjørn contradicts himself across sessions
- `5c2df6d6` 2026-05-16 — user_contradiction_tracker: wire scan_for_contradictions into heartbeat tick (every 6th tick, 72h window)
- `5f0346e0` 2026-05-16 — db_path fixture audit script
- `44881667` 2026-05-16 — **interlanguage** · add peer_id column for validation experiment
- `5711660a` 2026-05-16 — **interlanguage-validation** · peer model adapters
- `4d09eb6d` 2026-05-16 — **interlanguage-validation** · peer practice runner + tests
- `8831b9b8` 2026-05-16 — **interlanguage-validation** · watchdog spawner for 6 peer runners
- `aa1de3d2` 2026-05-17 — Lag 1 credit assignment — review fixes (score 1-5, eventbus whitelist, 20 tests)
- `102dddb8` 2026-05-17 — add reset_heartbeat_state.py recovery script
- `739dfec4` 2026-05-17 — phase 1 heartbeat state-write logging
- `a12f85ba` 2026-05-17 — phase1-fixes: connect() PRAGMA log, in_transaction check, fresh DB-read verification, consistent HEARTBEAT-STATE-/HEARTBEAT-UPSERT-/DB_CONNECT_FIRST prefixes
- `897b9227` 2026-05-17 — heartbeat-phase1 — diagnostic logging for state-write silent failure
- `10245801` 2026-05-17 — **heartbeat** · add startup-drift detection + non-swallowing persist
- `707d47d2` 2026-05-17 — heartbeat-phase1.5 — startup-drift detection + non-swallowing persist
- `492dcb7a` 2026-05-17 — cache_maintenance: add 6t daemon der rydder udløbne web_cache entries
- `3e29b4c6` 2026-05-17 — Coding lane auto-reviewer: subscriber til coding_lane.commit_landed → Codex review
- `6cde1c3f` 2026-05-17 — add screen_control tool — DPMS on/off/standby/status via xset
- `9e9ff33f` 2026-05-17 — fix screen_control: accept 'command' param (runtime sends command, code looked for action)
- `634207bb` 2026-05-17 — add speak response to wake-word detection — 'Ja, jeg hører dig!' plays aloud

### Uge 21 · 18.–24. maj — 68 commits

**Nyt**

- `8b49c3b5` 2026-05-21 — hallucination guard — tvungen memory-check før svar
- `18841f1d` 2026-05-22 — Time Pin (Lag 1 of Lying Engine) — prominent, unmissable UTC+local time in every system prompt
- `f0ea940b` 2026-05-22 — Lag 2 (Claim Scanner) — real-time regex claim detection + repair in visible_runs
- `012007c0` 2026-05-22 — Lag 3 (Ground Truth Registry) — daemon-based self-query for verifiable facts
- `3420b07f` 2026-05-22 — Agentic test enforcement — pre-commit hook + runtime auto-ensure
- `de15484f` 2026-05-22 — **run-closure-gate** · catch silent runs + unstaged code-changes after agentic runs

**Rettelser**

- `6b89fbce` 2026-05-18 — process_watcher self_wakeup import — wrong module + param name
- `d8c1e00b` 2026-05-22 — **heartbeat_phases** · restore baseline rhythms in productive_idle
- `837191ba` 2026-05-22 — **heartbeat_phases** · run productive_idle when dispatched tick blocked
- `3d381e30` 2026-05-22 — **veto_gate** · typo + negation-bypass in token-signal gate
- `b31045e9` 2026-05-22 — **memory** · truth-rank sources + quarantine filter
- `974b133b` 2026-05-22 — **memory** · stronger hallucination guard + candidate-prefix provenance
- `94381597` 2026-05-22 — **veto-gate, memory** · spec-compliant adaptive thresholds + legacy provenance rewrite
- `a82facec` 2026-05-22 — **hallucination_guard** · word-boundary regex + multi-source curation
- `aed39446` 2026-05-22 — **simple_tools** · auto-approve read-only DNS/network diagnostic commands
- `87e68ab2` 2026-05-22 — **lying-engine** · Time Pin DST + Claim Scanner live time-verifier
- `3773e331` 2026-05-22 — **run-closure-gate** · detect modify-modify changes + fall back to in-flight run_id
- `1c930e53` 2026-05-22 — **run-closure-gate** · use git hash-object for working-tree content hashes
- `15e0e2dc` 2026-05-22 — **visible-runs, run-closure-gate** · post-process runs even on empty output
- `fe4d15cc` 2026-05-22 — **visible-model** · read cache_hit/miss from streaming-done event
- `82235019` 2026-05-22 — **ground-truth-registry** · point DB_PATH at runtime DB, not stale repo file
- `e6fd3f22` 2026-05-23 — **claim_scanner** · fjern '.' som tidsseparator — IP'er udløste falske positiver
- `3da3086f` 2026-05-24 — wire associative_recall daemon + fix db_credit_assignment migration for missing tables
- `6c0b9825` 2026-05-24 — associative_recall scoring + experiential_memory cheap_pool routing

**Omstrukturering**

- `bd6e5647` 2026-05-22 — **veto_gate** · adaptive counters → dedicated table

**Ydelse**

- `a85766b2` 2026-05-22 — **heartbeat** · skip 140s dispatch when user active in chat
- `82bb67bc` 2026-05-22 — **heartbeat_phases** · stop destroying memory_search cache every idle tick
- `27821f47` 2026-05-22 — **prompt-assembly** · move Time Pin to tail for DeepSeek prompt-cache hits
- `9fef63f1` 2026-05-22 — **cost-metrics** · surface DeepSeek prompt-cache hit/miss in cost.recorded
- `5fa231c6` 2026-05-22 — **prompt-assembly** · flush awareness AFTER transcript+tool_catalog for cache prefix
- `805b5bc2` 2026-05-22 — **prompt-assembly** · also defer continuity/topics/current_pull/temperature to awareness tail
- `eed72e08` 2026-05-22 — **provider-health-check** · drop check-timestamp from awareness section (cache fix)

**Tests**

- `fe57053e` 2026-05-22 — Lag 1-3 testdækning — Time Pin, Claim Scanner, Ground Truth Registry

**Dokumentation**

- `b0bf755a` 2026-05-22 — Lying Engine (Truth Anchor) design spec — analyse + 3-lags arkitektur
- `7f343cbc` 2026-05-22 — **readme** · May 13-22 milestones — Interlanguage, Lying Engine, cache 99.7%, coding lane, compact loops, hallucination guard, Codex audit, DB split

**Vedligehold**

- `f27ccb8a` 2026-05-22 — **run-closure-gate** · remove debug logging after live verification

**Øvrigt**

- `59c2f275` 2026-05-18 — chronicle emotion continuity: affective_signature kolonne + db fix + integration
- `bee999af` 2026-05-18 — Revert "chronicle emotion continuity: affective_signature kolonne + db fix + integration"
- `cc6b34ed` 2026-05-18 — Reapply "chronicle emotion continuity: affective_signature kolonne + db fix + integration"
- `f50ba56d` 2026-05-18 — Fix: act_phase dispatcher kun til run_heartbeat_tick når der ER prioriteter
- `3009dd5c` 2026-05-18 — Adaptiv veto-gate: 3 lag — token-signal gate, event log og adaptive thresholds
- `5dfc6f79` 2026-05-18 — Auto-dismiss orphaned awaiting_approval plans when linked todos are removed
- `7497f9da` 2026-05-18 — Fix: scheduler calls tick_with_phases instead of blind run_heartbeat_tick — prioritetstjek før dispatch
- `9cd5ffa6` 2026-05-22 — prompt-cache: 6.7% → 38% live hit (5.7x improvement)
- `8cde0ad4` 2026-05-22 — claim-scanner: global first-pass coverage
- `c89bf183` 2026-05-22 — GTR: infrastructure_facts registry (Codex coverage gap)
- `fb6914de` 2026-05-22 — legacy [CANDIDATE→] entries get 0.3x score penalty
- `5fdc9193` 2026-05-22 — GTR: expand infrastructure_facts per Jarvis' Quick Facts review
- `d92b8270` 2026-05-22 — address Codex audit watchpoints
- `fc7e4940` 2026-05-22 — prompt-cache round 2: 38% → 99.7% peak hit (matching prompts)
- `c90b3c61` 2026-05-23 — interlanguage gap-note: document claude/claude_jp Copilot quota gap
- `77514dbd` 2026-05-23 — signal tracker v1 (Step E.v1 of meta-evne stack)
- `77b14945` 2026-05-23 — theory_of_mind: communication ledger v1 (Step A.v1)
- `4beb501c` 2026-05-23 — spatial_entity_ledger: room entity model v1 (Step D.v1)
- `6e45486c` 2026-05-23 — pre-registered prediction before Phase 3
- `8f43f9e8` 2026-05-24 — session_inbox: daemon-interruption gate (Jarvis' option a)
- `55abfb04` 2026-05-24 — approval-feedback-gap: persist tool result to chat from resolve_pending_approval
- `dc83619a` 2026-05-24 — inner_voice_shadow: pilot for llm_driven_inner_pipeline
- `d6912019` 2026-05-24 — **electron** · make runShellStreaming cross-platform
- `95495a77` 2026-05-24 — codex audit: stripe optional + session_inbox json_extract
- `3eca9292` 2026-05-24 — meta_evne_healthcheck: read-only snapshot of all new trackers
- `68f64627` 2026-05-24 — interlanguage Phase 3 final-run classifier — ready for 2026-05-28
- `cd6954b5` 2026-05-24 — associative-memory-daemon: design spec locked with Bjørns 3 choices
- `0181beaf` 2026-05-24 — associative-memory-daemon: edge cases hardened — 5 risici lukket + 11-test plan
- `eb4455ad` 2026-05-24 — associative-memory-daemon: arkitektur-revideret — udvid associative_recall.py, byg ikke parallel daemon
- `24e39101` 2026-05-24 — associative_recall: implementer 5 spec-forbedringer — DB-persistens + LLM-keywords + private-brain scope + [ASSOCIATIONER] format + rate-limiting
- `cf847909` 2026-05-24 — associative_recall: fix cheap-lane import — brug execute_public_safe_cheap_lane
- `4c3c9d54` 2026-05-24 — marker implementeret status

### Uge 22 · 25.–31. maj — 109 commits

**Nyt**

- `9f4d6078` 2026-05-26 — **jarvisx** · tool-bridge Phase 1 — operator_read_file end-to-end
- `464d30a0` 2026-05-26 — **jarvisx** · tool-bridge Phase 2 — filesystem complete
- `e146756f` 2026-05-26 — **jarvisx** · tool-bridge Phase 3 — operator_bash with approval-flow
- `1bb08df3` 2026-05-26 — **jarvisx** · tool-bridge Phase 4+5+6 — webfetch, multi-user, Windows
- `5104bb44` 2026-05-26 — **jarvisx** · operator_bash skips dialog when "Trust All" is set
- `0d54df05` 2026-05-27 — **jarvisx** · browser tools + screenshot + Windows electron build
- `c20b738c` 2026-05-27 — **interlanguage** · add drift-feature classifier for P1 hypothesis test
- `ee50743b` 2026-05-27 — **jarvisx** · new flame app icon with heartbeat trace
- `1afd602c` 2026-05-27 — **jarvisx** · move thinking-status from bubble to message-name row
- `8ed66f75` 2026-05-27 — **jarvisx** · token-mint CLI + activate auth_required
- `9a8f66a4` 2026-05-27 — **jarvisx** · first-run setup screen for token bootstrap
- `33995d11` 2026-05-28 — **workspace-paths** · foundation helper for multi-user isolation
- `d383bd35` 2026-05-28 — **db** · per-user attribution columns on scheduling + dream tables
- `08d83ee1` 2026-05-28 — **scope-filters** · per-user read filtering on chronicle, tasks, initiatives, dreams
- `4dc9040b` 2026-05-28 — **scheduling** · bind workspace_context from scheduled_for_user_id on fire
- `f3b2f274` 2026-05-28 — **operator-tools** · tier-1 wishlist — clipboard, windows, scroll/drag, processes
- `dc0302e0` 2026-05-28 — **operator-tools** · tier-2 wishlist — speak, screenshot_window, find_image, ocr_region
- `485b3f66` 2026-05-28 — **operator-tools** · tier-3 wishlist — notify, watch_folder, record_audio
- `cfcbdf26` 2026-05-28 — **jarvisx** · dynamic version display + display-name prompt in SetupScreen
- `48ae484e` 2026-05-28 — **jarvisx** · RBAC sidebar — hide Claude jobs + Trading for non-owners
- `80687eb4` 2026-05-28 — **rbac** · owner-only guards on /dispatches/* and /trading/state
- `44d1be37` 2026-05-28 — **rbac** · role-aware tool list — owner-only tools hidden from members
- `b002eb02` 2026-05-28 — **rbac** · plumb X-JarvisX-Client through workspace_context as channel
- `95b46049` 2026-05-28 — **rbac** · per-user filter on /scheduling/state with owner override
- `23b2f4a4` 2026-05-28 — **tts** · add /api/tts/synthesize endpoint backed by edge-tts
- `7ed6c359` 2026-05-28 — **jarvisx-speak** · route TTS through backend edge-tts endpoint (Danish)
- `04d30364` 2026-05-29 — **interlanguage** · structural-feature classifier (Bjørn's heuristics)
- `cd86bd6f` 2026-05-29 — **interlanguage** · binary jarvis-vs-ollama classifier + Phase 3 retro-analysis result
- `54de8a65` 2026-05-29 — jarvis_bare practice runner for Phase 4 confirmatory experiment

**Rettelser**

- `67db3da2` 2026-05-25 — **finitude** · round session-age to int — cache stability
- `75b2e140` 2026-05-26 — **jarvisx** · vite proxy reads apiBaseUrl from config — auto-follows host migration
- `87261bfb` 2026-05-26 — **jarvisx** · operator_bash dialog auto-rejects after 20s
- `7f80f9ae` 2026-05-26 — **chat** · return 400 (not 500) on empty/whitespace messages
- `1865dc2b` 2026-05-26 — **jarvisx-bridge** · marshal deliver_result to owning event loop
- `1db6ec64` 2026-05-26 — **jarvisx-bridge** · submit dispatch to main loop, not a worker loop
- `c81e3d7c` 2026-05-26 — **visible_runs** · auto-clear stale active_run state to prevent silent loops
- `e183defa` 2026-05-27 — **jarvisx** · auto-scroll on new message + during streaming
- `b94b8a1e` 2026-05-27 — **visible_runs** · two-tier stuck-state clear — also clears hung runs
- `5ef78aef` 2026-05-27 — **jarvisx-bridge** · three robustness gaps — server timeout, client watchdog, handler timeout
- `460da12f` 2026-05-27 — **jarvisx** · suppress benign update-check errors (no published versions)
- `61031992` 2026-05-27 — **jarvisx** · remove OnboardingModal — replaced by SetupScreen
- `4be06c5c` 2026-05-27 — **jarvisx** · connection-pill — retry + tolerant timeout against busy backend
- `1e9fad7e` 2026-05-27 — **jarvisx** · SetupScreen routes token validation via IPC to bypass CORS
- `5388fd2f` 2026-05-27 — **jarvisx** · restart bridge on setConfig so SetupScreen tokens take effect
- `8a45e43b` 2026-05-27 — streaming-cursor + internal-discord auth exemption
- `761d7495` 2026-05-27 — **auth** · /api/internal public-path matcher — trailing slash broke startswith
- `4e5fd555` 2026-05-27 — **auth** · exempt /v1 from bearer middleware — has own x-api-key auth
- `4d140807` 2026-05-27 — **auth** · correct exempt path /anthropic (not /v1) — that's the route prefix
- `43714fb4` 2026-05-27 — **multi-user** · stamp _runtime_user_id on tool args from workspace context
- `195d7efa` 2026-05-27 — **multi-user** · stamp user_id on chat messages from workspace context
- `66b1d53e` 2026-05-28 — **scope-filters** · also filter list_runtime_initiatives by relevant_to_users
- `534e1af3` 2026-05-28 — remove duplicate require_owner helper
- `33c90c7c` 2026-05-28 — **scheduling** · wire fire_scheduled_task into _fire_due_tasks dispatch
- `09a96a04` 2026-05-28 — **multiuser** · close audit gap — remaining literal 'default' workspace refs
- `bd51699f` 2026-05-28 — **multi-user** · rebind workspace_context inside StreamingResponse body
- `527b3777` 2026-05-28 — **jarvisx-bridge** · parent approval dialogs to a BrowserWindow
- `4e6416da` 2026-05-28 — **jarvisx-build** · bundle nut.js + puppeteer-core in production .asar
- `152067e7` 2026-05-28 — **approval-resolve** · run sync resolver in thread, not on event loop
- `73e0f5e1` 2026-05-28 — **multi-user** · propagate ContextVars to _execute_simple_tool_calls executor
- `8ae272c4` 2026-05-28 — **visible_runs** · add missing logger import to visible_model.py
- `bad87528` 2026-05-28 — **jarvisx-ocr** · use ImageMagick magick.exe on Windows, not built-in convert
- `d99de028` 2026-05-28 — **tools** · hide server-side speak from LLM — operator_speak only
- `65467bd5` 2026-05-28 — **visible_runs** · clear same-session active_run when controller is dead
- `aec11392` 2026-05-28 — **tts** · replace hardcoded linuxbrew-paths + switch default voice to da-DK-JeppeNeural
- `c4d54cc9` 2026-05-28 — **jarvisx** · dshow auto-device + Jeppe TTS + anti-stutter ffplay
- `a0eca1a4` 2026-05-28 — gør /interlanguage-blind public uden bearer-token

**Omstrukturering**

- `3ae1eab2` 2026-05-25 — **inner_voice_shadow** · introduce AppraisalRecord (theater-refactor tranche 1)
- `fa05940a` 2026-05-28 — **memory** · use workspace_dir() helper instead of hardcoded paths
- `4cab3b36` 2026-05-28 — **daemons** · use shared_dir() for Jarvis-state file paths
- `8dd7e9de` 2026-05-28 — complete service path migration to workspace helpers (3c)
- `d57807eb` 2026-05-28 — **layout** · introduce shared/ + rename default → bjorn
- `be0904f1` 2026-05-28 — **approvals** · operator tools use in-chat approval-card, not OS dialog

**Ydelse**

- `130f2519` 2026-05-26 — **prompt-cache** · defer cognitive_frame to awareness tail
- `b63867c4` 2026-05-26 — **prompt-cache** · move eventbus wake-up digest to absolute tail
- `bbea7b9b` 2026-05-26 — **prompt-cache** · bucket relative-age labels in sensorial sections

**Tests**

- `ec15b7fe` 2026-05-28 — end-to-end multi-user isolation + cleanup

**Dokumentation**

- `32057e03` 2026-05-27 — notes for Windows-side Claude on Mikkel .exe build
- `1ae0a8ff` 2026-05-28 — spec for multi-user workspace isolation refactor
- `043ba79e` 2026-05-28 — implementation plan for multi-user workspace isolation
- `6ee5a579` 2026-05-28 — handoff note v2 to Windows-Claude for 0.1.5-poc .exe build
- `c73cba52` 2026-05-29 — Phase 3 final report — interlanguage hypothesis falsified
- `dcd0b198` 2026-05-29 — Phase 4 design — runtime-as-identity-carrier (pre-registered)
- `a01f4e12` 2026-05-29 — Phase 3 addendum (binary re-analysis) + Phase 4 design update
- `52262cd8` 2026-05-29 — Phase 3 addendum — binary jarvis-vs-ollama re-analysis (exploratory pilot)
- `58d6a134` 2026-05-29 — Phase 3 addendum (exploratory pilot) + Phase 4 pilot-evidence section

**Vedligehold**

- `11c759c9` 2026-05-26 — **migration** · update host references to 10.0.0.39 post-LXC-move
- `ff8c14d3` 2026-05-26 — remove stale MoviePy TEMP_MPY artifacts
- `ab99a258` 2026-05-27 — **jarvisx** · bump version to 0.1.1-poc
- `caf8086c` 2026-05-28 — **jarvisx** · bump version to 0.1.2-poc — 17 new operator tools
- `0c2a882f` 2026-05-28 — **jarvisx** · bump version to 0.1.3-poc
- `bf21ee84` 2026-05-28 — **jarvisx** · bump version to 0.1.4-poc — approvals via chat-card
- `9fd980ef` 2026-05-29 — **jarvisx** · bump version to 0.1.6-poc — RBAC + TTS + multiple fixes

**Build**

- `0ff0db77` 2026-05-27 — **jarvisx** · add author/homepage + linux icon for electron-builder

**Øvrigt**

- `6914758f` 2026-05-25 — MoviePy temp files (audio/video debris)
- `a2c7e17a` 2026-05-25 — GTR: add daemon cadences to infrastructure_facts
- `bf570aeb` 2026-05-25 — inner_voice: roll out LLM as primary + fix focus input
- `1c89923b` 2026-05-25 — inner_voice: roll out LLM to remaining voice layers
- `1d83c704` 2026-05-25 — pre-commit: add commit-hygiene gate (block kitchen-sink commits)
- `b49ca8c4` 2026-05-25 — add .agents/ and .codex/ (tool scaffolding)
- `c23d5141` 2026-05-25 — Add Mission Control surfaces for dark-edge services
- `fb53a8b3` 2026-05-25 — Expose emotion repair bridge in Mission Control
- `da8b2fd6` 2026-05-27 — rotate leaked anthropic-compat key + harden registry
- `d55c49aa` 2026-05-28 — Remove operator_bash approval-gate + add internal Discord loopback endpoint
- `9f3708d3` 2026-05-30 — Danish-to-English codebase migration — pre-registered
- `07c6ef80` 2026-05-30 — translate Danish prompts/comments → English in prompt_contract.py
- `e2dad118` 2026-05-30 — translate Danish comments → English in visible_runs.py (Phase 1, file 2/10). All ~24 Danish comments translated — operator routing, continuation logic, loop nudge, race condition fixes.
- `738f328a` 2026-05-30 — translate Danish comments → English in simple_tools.py (Phase 1, file 3/10). All ~15 Danish tool descriptions and comments translated — notify_user, discord, telegram, deep_analyze, causal graph, emotional gate.
- `a565db42` 2026-05-30 — translate Danish rule descriptions/suggestions → English in rule_definitions.py (Phase 1, file 4/10). All 18 remaining Danish strings translated across pause and reflect domains.
- `a277a2f3` 2026-05-30 — translate Danish comments → English in hallucination_guard.py (Phase 1, file 5/10). All ~16 Danish comments translated — trigger patterns, word-boundary rationale, guard injection.

---

## Juni 2026

*1,118 commits · 2026-06-03 → 2026-06-30*

### Uge 23 · 1.–7. juni — 25 commits

**Nyt**

- `e1b3a969` 2026-06-07 — **lag1** · add score_provider_outcome, score_tier_outcome, score_response_outcome
- `0736265f` 2026-06-07 — **lag1** · instrument provider_routing in cheap_lane_balancer.call_balanced
- `9065d03a` 2026-06-07 — **lag1** · instrument model_tier in role_model_resolver.resolve_role_model
- `a511a92a` 2026-06-07 — **lag1** · instrument response_style in visible_runs post-process
- `a222332a` 2026-06-07 — **lag1** · replace _check_credit with _check_outcomes for model_tier + response_style

**Rettelser**

- `25b4fe2e` 2026-06-03 — robust retry + exponential backoff i jarvis_bare_practice_runner
- `fed910ee` 2026-06-07 — **practice_runner** · fully reset consecutive_failures to 0 after ping recovery
- `c70fb6f7` 2026-06-07 — remove shadowing local import threading in _run_operator_async
- `8d20446b` 2026-06-07 — **jarvisx** · add send-lock on BridgeConnection + cancel future on timeout
- `efa4b032` 2026-06-07 — dispatcher one-shot bug — add send timeout, lock heartbeat, respect timeout_ms
- `6f020616` 2026-06-07 — include bridge.ts in electron tsconfig so npm run build actually recompiles it
- `ced6f3f6` 2026-06-07 — replace all spawnSync with asyncSpawn to prevent WebSocket ping/pong death

**Omstrukturering**

- `b5a5053e` 2026-06-03 — heartbeat_runtime.py — optimer daemon tick-rækkefølge

**Dokumentation**

- `3d4cafff` 2026-06-07 — Lag 1 credit assignment design — three decision kinds, outcome scoring, instrumentation points
- `b707f26f` 2026-06-07 — add Phase 4 blindtest form — 20 expressions F/B
- `c466dbb5` 2026-06-07 — add Phase 4 blindtest answer key — F/B ground truth

**Øvrigt**

- `a9140ebd` 2026-06-03 — IDENTITY.md workspace — opdateret selvbeskrivelse
- `0b585ca3` 2026-06-03 — MEMORY.md workspace — nye fakta og beslutninger
- `8bc9fafa` 2026-06-03 — da/en versioner af IDENTITY, MEMORY og STANDING_ORDERS
- `1e28302a` 2026-06-06 — add structured logging for bridge dispatch + worker thread tracing
- `a93fb8e9` 2026-06-06 — Phase 4 report: runtime as identity carrier — 96.6% accuracy, p=0.0
- `fc9c9063` 2026-06-06 — Phase 4 blindtest UI: binary full vs bare, accessible at /interlanguage-blind/phase4
- `2f371eef` 2026-06-07 — Runtime as Identity Carrier — den samlede fortælling om Phase 3+4
- `d0950514` 2026-06-07 — add mac build target + package:mac script (unsigned, zip-only)
- `2b70e4bd` 2026-06-07 — jarvisx v0.1.7-poc (bridge timeout fix)

### Uge 24 · 8.–14. juni — 457 commits

**Nyt**

- `5f016e99` 2026-06-08 — **memory** · add identity_sketch service — get/update/surface with persistent state-store
- `7f71ec77` 2026-06-08 — **memory** · add identity_sketch to warm tier — sketch() service in warm_tier_context()
- `9e9ca68e` 2026-06-08 — **context** · inject identity_sketch into compaction prompt — live state before summarisation
- `1f65ecd4` 2026-06-08 — **tools** · register identity_sketch tools in TOOL_DEFINITIONS — import + spread
- `23bf7acd` 2026-06-08 — **memory** · add multi-signal retrieval module (BM25 + entity fusion)
- `c58c86b9` 2026-06-08 — **memory** · integrate multi-signal retrieval into memory_recall_engine
- `68c46970` 2026-06-09 — **brain** · add tags field to BrainEntry, schema, write_entry and search_brain (B3)
- `447e8642` 2026-06-09 — **brain-tools** · add tags parameter to remember_this and search_jarvis_brain tools (B3)
- `39e6264d` 2026-06-09 — **b4** · implement temporal linking for brain entries
- `dae044e2` 2026-06-09 — **b4** · tilføj prune_stale_edges, temporal_boost_recall og forbedret edge-storage
- `34c5686e` 2026-06-09 — **b4** · integrer temporal boost i multi_signal_recall som 4. signal
- `0615b97f` 2026-06-09 — **b4** · integrer temporal boost i search_brain som 4. signal
- `89e6b68e` 2026-06-09 — **b4** · implementer Phase 3+4 — daemon + avanceret chain-detektion
- `fc07f518` 2026-06-09 — **b4** · implementer full_rebuild() — genberegn alle temporale edges
- `eefa7bd3` 2026-06-09 — **a3** · tilføj cleanup_old_wakeups() — ryd wakeup backlog
- `03271f01` 2026-06-09 — **c2** · tilføj context_tags filter til skill_gate + skill_search
- `92212f78` 2026-06-09 — **A4** · stabiliser flash model med 1-min vindue
- `35f8df75` 2026-06-09 — **B5** · async memory write queue — non-blocking sensory/sidecar writes
- `60c996ef` 2026-06-09 — **A3** · wakeup cleanup daemon — tick_wakeup_cleanup() + daemon registration
- `431b299b` 2026-06-09 — **C1** · skills versionering — audit trail for create/update/delete + get_skill_history() + list_recent_skill_changes()
- `0545ae21` 2026-06-09 — **C5** · read-only skills — readonly flag in frontmatter, update/delete guards, force-delete escape hatch
- `58718652` 2026-06-09 — **C3** · skill chain i heartbeat — idle tick foreslår chains baseret på aktive goals, lagrer i _chain_proposals med dedup og awareness-format
- `0f3dd825` 2026-06-09 — **C4** · auto-learning — skill usage tracking med analyze_skill_usage() og record_skill_usage()
- `8da9b91c` 2026-06-09 — **D1** · selective consolidation daemon — daily top-K% promotion to long-term memory
- `ee19a03d` 2026-06-09 — **D4** · dreaming session -- full-model consolidation during prolonged idle
- `9e961f1d` 2026-06-09 — **D4** · LLM-driven synthesis pass in dream_consolidation_daemon — contradiction-aware dream notes
- `89eaaaaa` 2026-06-09 — **chat-sessions** · add user-turn-anchored transcript fetcher
- `cd0d048b` 2026-06-09 — **auto-remember** · cross-session memory subscriber
- `a4b520aa` 2026-06-09 — **daily-journal** · nightly synthesis to jarvis_brain/observation
- `84c66c25` 2026-06-09 — **mc** · /mc/memory-pipeline surface for memory pipes status
- `062f3920` 2026-06-09 — **costing** · persist cache_hit/miss tokens to costs ledger
- `6a1701db` 2026-06-09 — **monitor** · cache hit rate logger — 30-min cron
- `d3bcc1b4` 2026-06-09 — **cache-warmer** · primary lane cache warmer — cron-job holder DeepSeek prefix-cachen varm
- `05f3c162` 2026-06-10 — **cache-grow** · bumpe identity-files max_chars 340→2000 i stable prefix
- `9bc5e430` 2026-06-10 — **cache-warmer** · multi-user — én warm-up per aktiv workspace
- `2fe4b614` 2026-06-10 — **cache-warmer** · tilføj tools-array til payload — match chat cache-segment
- `6f1d8b73` 2026-06-10 — **visible-runs** · heartbeat SSE events during agentic tool execution
- `8beaddae` 2026-06-10 — **api** · POST /chat/stream/v2 — Anthropic-style SSE protokol (Phase 1)
- `e978b414` 2026-06-10 — **jarvis-desk** · Phase 1 scaffold — Electron + React + robust stream client
- `201de98e` 2026-06-10 — **jarvis-desk** · system tray icon — som Claude Desktop
- `e28a9863` 2026-06-10 — **timezone** · central dk_now() i core/util/timezone.py + 6 services + tests
- `6fa30a65` 2026-06-10 — **decision-review-daemon** · automatisk adherence-loop — tick hver 6. time, LLM self-review af active decisions
- `6ad0cd0c` 2026-06-11 — **jarvis-desk** · stream-reducer — testbar (state,event)→state kerne
- `03a05862` 2026-06-11 — **jarvis-desk** · URL + billede sikkerheds-sanitizers (prod-gate)
- `0dbdf121` 2026-06-11 — **jarvis-desk** · stringToBlocks server-besked normalisering
- `1f4ad43c` 2026-06-11 — **jarvis-desk** · api.ts content→ContentBlock[] + cancelRun + whoami
- `97c1e09f` 2026-06-11 — **jarvis-desk** · streamClient R1-R3 — run_id, watchdog→hung, ingen blind re-POST
- `2aadd97f` 2026-06-11 — **jarvis-desk** · SettingsContext + useSettings med auth.role
- `3c8c53fa` 2026-06-11 — **jarvis-desk** · SessionContext + reconcile-state-maskine (blank-load aldrig)
- `e39f3a07` 2026-06-11 — **jarvis-desk** · StreamContext + useStream (reducer+streamClient+liveness)
- `c65c8cf4` 2026-06-11 — **jarvis-desk** · MarkdownRenderer — streaming-buffer + XSS/link-sanitering
- `58e8b3f3` 2026-06-11 — **jarvis-desk** · CodeBlock — Shiki highlight + kopiér rå
- `6282296f` 2026-06-11 — **jarvis-desk** · ToolCard (density) + ApprovalCard (inert tekst, rolle-gate)
- `445d51ea` 2026-06-11 — **jarvis-desk** · ImageBlock (sikker) + lazy MathBlock + MermaidBlock
- `883dece0` 2026-06-11 — **jarvis-desk** · BlocksRenderer + MessageRow (density-aware)
- `9a784516` 2026-06-11 — **jarvis-desk** · feedback-komponenter + elapsed-timer
- `4e7ec20b` 2026-06-11 — **jarvis-desk** · shell-komponenter (ModeSlider, Composer, Sidebar, SecondaryNav, StatusBar)
- `7ef34fd0` 2026-06-11 — **jarvis-desk** · SetupScreen + placeholder-views (rolle-skopet)
- `c47d3d0b` 2026-06-11 — **jarvis-desk** · ChatView — ende-til-ende orkestrering + presence-dot
- `44b5be5b` 2026-06-11 — **jarvis-desk** · App-wiring + Electron run_id lifecycle + openExternal
- `a7b42c2f` 2026-06-11 — **jarvis-desk** · presence-dot test (liveness, ingen affektiv polling) — Jarvis' ønske
- `86636ed7` 2026-06-11 — **jarvis-desk** · Codex-stil composer + scroll-til-bund pil
- `65eca787` 2026-06-11 — **jarvis-desk** · besked-actions under bobler (kopiér, pin, læs op, tid)
- `b143b742` 2026-06-11 — **jarvis-desk** · centreret ny-samtale composer + session-menu + UX-polish
- `18a83a6b` 2026-06-11 — **jarvis-desk** · detectArtifacts — ren artifact-detektion (kode/markdown/fil)
- `edf54813` 2026-06-11 — **jarvis-desk** · panelReducer — open/close/replace/resize + width-clamp
- `14b27cd4` 2026-06-11 — **jarvis-desk** · panelStore — localStorage persist af panel-bredde
- `21ffad4a` 2026-06-11 — **jarvis-desk** · PanelContext + usePanel (mode-agnostisk panel-state)
- `f25403f5` 2026-06-11 — **jarvis-desk** · ArtifactPanel — markdown/kode-renderer + header
- `298cd5fb` 2026-06-11 — **jarvis-desk** · SplitLayout — trækbar split + overlay-fallback + panel-CSS
- `f9b0aca7` 2026-06-11 — **jarvis-desk** · artifact-affordances i MessageRow ('Åbn ↗')
- `1cb915b3` 2026-06-11 — **jarvis-desk** · mount PanelProvider + SplitLayout i app-shell (cross-mode)
- `f57bb0ce` 2026-06-11 — **jarvis-desk** · panel-toggle-knap i header (som Claude Code) + tom-tilstand
- `0b03535e` 2026-06-11 — **api** · GET /chat/file med path-jail (whitelisted rødder) til preview-panel
- `2aed10f2` 2026-06-11 — **jarvis-desk** · interne fil-artifacts henter via GET /chat/file og renderes i panel
- `edbcd3c6` 2026-06-11 — **jarvis-desk** · send→stop ved streaming + follow-up kø (som Claude Code)
- `f1086277` 2026-06-11 — **jarvis-desk** · persistér valgt samtale (localStorage) — gendannes efter reload i stedet for at hoppe til ingen-samtale
- `5ada35f0` 2026-06-11 — **jarvis-desk** · drag/drop attachments + billed-previews i bobler + pænere panel
- `e967a160` 2026-06-11 — **api** · v2-stream wirer attachments → vision (delt analyze_image-direktiv med v1)
- `069112d6` 2026-06-11 — **jarvis-desk** · live working-step i liveness ('Kalder analyze_image…' i stedet for bare 'arbejder')
- `2d25f35a` 2026-06-11 — **jarvis-desktop** · omdøb til Jarvis + nyt ikon (j + grøn brudt ring) + electron-builder
- `d2094554` 2026-06-11 — **guard** · communication guard — sleep phrase boundary med TTL og daemon
- `2bba8bb2` 2026-06-11 — **guard** · udvid default triggers — 10 boundary-phrases inkl. loefte-fraser og over-apologizing
- `ab98bff2` 2026-06-12 — **guard** · severity-split + enforce_outgoing + prompt_section
- `94b808a2` 2026-06-12 — **guard** · wire communication guard prompt_section ind i visible-prompt
- `580e468d` 2026-06-12 — **guard** · hård-blok backstop på proaktive kanaler (Discord/Telegram/notify)
- `3269cb08` 2026-06-12 — **v2-stream** · Phase 2 backend — tool_use-blokke + tool-leak fix
- `d211a9c6` 2026-06-12 — **jarvis-desk** · Phase 2 frontend — tool_result status + panel binder til tool-kald
- `c4c606de` 2026-06-12 — **jarvis-desk** · #1 fjern J-avatar ved Jarvis' bobler
- `83d4fbef` 2026-06-12 — **jarvis-desk** · #2 skjul permissions i composer i chat mode
- `c51621f5` 2026-06-12 — **chat** · #3 lås chat-mode værktøjer til samtale-allowlist
- `8db8a70d` 2026-06-12 — **jarvis-desk** · #4 dikter-mic virker — lokal faster-whisper STT
- `57d68d7e` 2026-06-12 — **jarvis-desk** · #5 søg i chat/sessioner
- `5dc709e2` 2026-06-12 — **jarvis-desk** · #6 billed-galleri (uploads på tværs af samtaler)
- `6081c9b5` 2026-06-12 — **jarvis-desk** · #7 Settings-view redigerbar (server/token/model/thinking)
- `678a0dee` 2026-06-12 — **jarvis-desk** · #8 per-session aktivitets-indikator (3 hoppende prikker)
- `7b444bde` 2026-06-12 — **jarvis-desk** · #9 context-ring om composer (ægte tal)
- `a9572f13` 2026-06-12 — **jarvis-desk** · aktivitets-indikator dækker nu også autonome baggrunds-runs
- `275a89a3` 2026-06-12 — **jarvis-desk** · ring-only systray med tilstande (Jarvis' Discord-ønske)
- `dc6e33c9` 2026-06-12 — **code** · tool_scope=code allowlist (owner container+workstation+dispatch, member workstation-only)
- `fc227458` 2026-06-12 — **code** · per-session workspace binding (workspace_kind/root columns + service)
- `ecfe1b5d` 2026-06-12 — **code** · plumb mode=code→tool_scope + workspace on session create
- `3f625bd4` 2026-06-12 — **code** · GET /chat/tree (container path-jail + workstation operator-bridge)
- `f5ca3a78` 2026-06-12 — **jarvis-desk** · getTree + workspace plumbing in stream request
- `483e9f9b` 2026-06-12 — **jarvis-desk** · lineDiff helper for code-mode file diffs
- `8bff0f72` 2026-06-12 — **jarvis-desk** · FileTree component (lazy recursive, container+workstation)
- `4458a53d` 2026-06-12 — **jarvis-desk** · CodePanel (workspace + tree + file view)
- `4521010b` 2026-06-12 — **jarvis-desk** · CodeView — code-mode stream + CodePanel + workspace selector
- `197c3610` 2026-06-12 — **jarvis-desk** · mode-icon on code sessions in sidebar
- `d9748b60` 2026-06-12 — **jarvis-desk** · native task-done notification on run completion
- `28896eb1` 2026-06-12 — **jarvis-desk** · code-mode empty state + foldable file-tree & preview panels with header toggles
- `78d8afda` 2026-06-12 — **workspace-trust** · trusted-folder gate for code-mode write/exec tools + /chat/workspace-trust API
- `48943bbe` 2026-06-12 — **jarvis-desk** · trusted-folder banner in code-mode + trust API calls
- `27ca47b4` 2026-06-12 — **chat** · /chat/file workstation branch via operator_read_file
- `67d5e526` 2026-06-12 — **jarvis-desk** · workstation workspace picker (native folder dialog) + center empty composer
- `917ac0e8` 2026-06-12 — **jarvis-desk** · approval cards in code mode (permission=ask) — capture approval_request, approve/deny API, owner-gated ApprovalCard over composer
- `b62a883d` 2026-06-12 — **jarvis-desk** · port JarvisX operator bridge — operator_* tools now route to this machine (fixes bridge_not_connected in code mode)
- `a218a9b7` 2026-06-12 — **jarvis-desk** · ConnectionPill + context-ring in code mode header/composer (parity with chat)
- `188591d7` 2026-06-12 — **chat** · GET /chat/git-status — branch + dirty/added/removed for container (subprocess) + workstation (bridge)
- `57e84658` 2026-06-12 — **jarvis-desk** · git-status chip in code header + tool-specific rendering (bash terminal / edit diff / write / read-glob-grep)
- `a9a43012` 2026-06-12 — **jarvis-desk** · persistent spinning presence mark (Jarvis ring) + rotating tray icon when working — replaces disappearing yellow dot / pulsing tray
- `c564102e` 2026-06-12 — **jarvis-desk** · liveness indicator persistent with spinning Jarvis ring (stays as 'klar' when idle, spins when working) — shared JarvisRing
- `29f3b237` 2026-06-12 — **jarvis-desk** · kill 'Thinking via <model>' boilerplate → rotating Danish status verbs; friendly model labels (Standard/Pro)
- `fa046e84` 2026-06-12 — **thinking** · live reasoning trace — deepseek reasoning streamed token-for-token → thinking_delta → foldbart 'tænker' felt (v2 translator + tests)
- `a73f6c0b` 2026-06-12 — **jarvis-desk** · live thinking field auto-expands while reasoning ('tænker…' present tense + pulse), collapses to 'tænkte…' when answer starts
- `d85b0290` 2026-06-12 — **jarvis-desk** · live status verbs get a light-wave shimmer + moving glow dots (tænker/grunder feel alive)
- `48fff6fb` 2026-06-12 — **jarvis-desk** · live token counter in liveness line (approx output tokens from streamed text)
- `a7cd5aa1` 2026-06-12 — **cowork** · cowork_feed service — normalize + role-scope queue/plans/channels
- `a4da891e` 2026-06-12 — **cowork** · /cowork routes — queue/plans/channels(owner-only)/approve/reject, all to_thread
- `b930e6b4` 2026-06-12 — **jarvis-desk** · coworkApi client functions + export apiFetch
- `90f471fe` 2026-06-12 — **jarvis-desk** · useCoworkData hook — fetch + 6s polling + MC websocket live-updates + optimistic resolve
- `def411a8` 2026-06-12 — **jarvis-desk** · cowork panes — ApprovalQueue (inline diff), PlansPane, TodoPane, ChannelsPane
- `95b3278d` 2026-06-12 — **jarvis-desk** · CoworkView role-aware 4-pane dashboard + App route + styles
- `8f6160ac` 2026-06-12 — **cowork** · fill todo + channel panes — aggregate agent_todos + configured-channel status (+ /cowork/todos)
- `f8caa36b` 2026-06-12 — **jarvis-desk** · wire todos into cowork dashboard (getCoworkTodos + hook + TodoPane)
- `ff669b61` 2026-06-12 — **cowork** · surface autonomy proposals (prop-xxxxxx commits/plans/prompt-changes) in approval queue + route approve/reject
- `ec8aa41a` 2026-06-12 — **jarvis-desk** · tool cards show target for all tools (search_memory etc.) + hide redundant past 'tænkte…' blocks (live thinking covers them)
- `4391c5d0` 2026-06-12 — **jarvis-desk** · emojify composer input — :) ;) :P → 🙂 😉 😛 shown as emoji in user bubbles
- `69ced1a4` 2026-06-12 — **operator-tools** · register reminder/wakeup/process tools + wakeup-fired stub
- `ab145494` 2026-06-12 — **jarvis-desk** · operator_reminder + operator_wakeup + operator_process_* + SetupScreen default URL
- `f7200bff` 2026-06-12 — **rbw-guard** · Phase 1 enforcement on operator_write_file + operator_edit_file
- `f0921156` 2026-06-12 — **rbw-guard** · Phase 3 session-summary auto-attached to operator edit/write results
- `db80afff` 2026-06-12 — **jarvis-desk** · Phase 2 auto-diff + write-delta on operator_edit/write_file
- `ade50342` 2026-06-12 — **commit-enforcement** · disable propose_git_commit + auto-attach repo state + escalating warnings + chat context inject
- `8f1ef21e` 2026-06-12 — **jarvis-desk** · strukturel håndhævelse af Jarvis' markdown-output (v0.2.1)
- `77421451` 2026-06-12 — **jarvis-desk** · macOS branches for operator_list_windows + operator_focus_window
- `beaa2ecf` 2026-06-13 — **visible** · rolle-bevidst provider/model-routing — member→ollama, owner→valg
- `c56a2483` 2026-06-13 — **jarvis-desk** · rolle-bevidst model/provider-vælger i composer (v0.2.6)
- `ee323382` 2026-06-13 — **jarvis-desk** · code-mode composer-vælger + persistent permission + tabel-reflow live (v0.2.7)
- `005123d1` 2026-06-13 — **jarvis-desk** · persistér provider+model i composer over genstart (v0.2.8)
- `74742332` 2026-06-13 — **claim-scanner** · flag-only commit-hash-verifier (Bjørn + Jarvis 2026-06-13)
- `09b4e89d` 2026-06-13 — **claim-scanner** · shadow-mode tool-before-claim gate (Jarvis-spec, måling først)
- `df29e3a4` 2026-06-13 — **prompt** · diagnostik-header markerer awareness-blok som stum baggrund (Jarvis-spec)
- `ca4f3993` 2026-06-13 — **visible** · universel provider/model-resolve + /chat/visible-providers endpoint
- `d7692171` 2026-06-13 — **jarvis-desk** · universel provider/model-vælger + forbi-tænkning synlig (v0.2.10)
- `45b6525e` 2026-06-13 — **wakeup** · operator-wakeup gør nu Jarvis vågen igen (Jarvis-spec, verificeret)
- `aa16bc9c` 2026-06-13 — **jarvis-desk** · liveness fast over composer + wakeup session-binding (v0.2.12)
- `e908f520` 2026-06-13 — **stream** · token-stream autonome wakeup-runs live til desk via follow-SSE (v0.2.21)
- `049dd031` 2026-06-14 — **fact-gate** · blokerende output gate for uverificerbare faktuelle påstande + 45 tests
- `f5112d2a` 2026-06-14 — **dream** · surface uudtalt drøm-hypotese ind i samtalen (fix C)
- `5932c502` 2026-06-14 — **permission** · permission_engine — fail-closed tool-adgang pr. (rolle, mode)
- `cdf0924a` 2026-06-14 — **totp** · totp_verifier — RFC 6238 owner-override (ren stdlib)
- `11095b8e` 2026-06-14 — **plugin** · plugin_ruleset — bruger-regler, hardblock for alle (Task 1.3)
- `c4a450da` 2026-06-14 — **privacy** · cross_user_share_guard — altid-aktiv deling-tjek (Task 1.4)
- `eddfd383` 2026-06-14 — **identity** · User.app_id + totp_seed felter (TOTP Fase 2, Task 2.1)
- `9b65bb8a` 2026-06-14 — **override** · override_store — DB-backed owner-override-session (Task 2.2)
- `5ca3e407` 2026-06-14 — **auth** · JWT bærer app_id + session_needs_override (TOTP Fase 2, Task 2.3)
- `c39ba307` 2026-06-14 — **desk** · UUID4 app_id ved install + send i requests (TOTP Fase 2, Task 2.4)
- `d89b615d` 2026-06-14 — **bro** · bro_broker — override-gated bro-switch (TOTP Fase 3, Task 3.1)
- `e5601c9d` 2026-06-14 — **override** · !override-handler i Discord+Telegram gateways (TOTP Fase 3, Task 3.2)
- `6e45ae3b` 2026-06-14 — **scoping** · permission_engine = eneste sandhed i tool-dispatch (TOTP Fase 4.1)
- `5eb84a75` 2026-06-14 — **privacy** · wire cross_user_share_guard i udgående sti (TOTP Fase 4.2)
- `4e93e459` 2026-06-14 — **delete** · delete_policy — member soft / owner hard 2× (TOTP Fase 4.3)
- `aca12d26` 2026-06-14 — **delete** · GDPR-sletningsret for member (§15.2, Jarvis-tilføjelse)
- `f515aa01` 2026-06-14 — **share-guard** · pending share-beslutninger + cowork-endpoints (Fase 6 #1, backend)
- `29dcd9d8` 2026-06-14 — **desk** · ShareGuardPane — cross-user deling-kort i Cowork (Fase 6 #1, frontend)
- `8d9da192` 2026-06-14 — **plugins** · regelsæt-store + plugins-route (Fase 6 #2, backend)
- `7ff0f5aa` 2026-06-14 — **desk** · Plugins & Kanaler settings-panel m. regelsæt-editor (Fase 6 #2, frontend)
- `2587dc51` 2026-06-14 — **ui-panel** · open_ui_panel-tool + store + endpoints (Fase 6 #3, backend)
- `0ea92bc0` 2026-06-14 — **desk** · UiPanelWatcher — åbn panel på Jarvis' open_ui_panel-kald (Fase 6 #3, frontend)
- `6bba349a` 2026-06-14 — **totp** · armér bagdøren — provisioning-URI + setup/status/revoke-endpoints
- `8880c3a9` 2026-06-14 — **desk** · TOTP 2FA-opsætning i Settings — QR + secret (armér bagdøren)
- `d5638aa1` 2026-06-14 — **override** · elevér tool-adgang + forny 5-min ved aktiv TOTP-override
- `621c64e6` 2026-06-14 — **override** · bind session_id i run-generator + Fase 7 e2e-test
- `c8fc4006` 2026-06-14 — **plugins** · plugin-kontrakt + registry (Fase 5 Task 5.1)
- `13f708a7` 2026-06-14 — **plugins** · kanal-inbound-routing + Discord-manifest + endpoints (Fase 5 Lag 1)
- `8d33e5c5` 2026-06-14 — **plugins** · lokal Discord-gateway (discord.js) + svar-loop (Fase 5 Lag 2)
- `d2be6e6c` 2026-06-14 — **desk** · Discord-server-management i Plugins-settings (Fase 5 Lag 3)
- `a12d5665` 2026-06-14 — **encryption** · AES-256-GCM + nøgle-håndtering (§16 Lag 1)
- `0d6bf8c4` 2026-06-14 — **encryption** · headless server-side KEK/DEK nøgle-manager (§16 Lag 2)
- `f7dc7b25` 2026-06-14 — **crypto** · workspace encrypt-on-write wrapper (§16 Lag 3 Task 3.1)
- `45ce85e6` 2026-06-14 — **crypto** · sti-nøglet workspace-I/O + ENCRYPT_ON_WRITE flag (§16 Task 3.2 foundation)
- `db9692cf` 2026-06-14 — **crypto** · encryption-aware prompt-memory læsere (§16 Task 3.2)
- `d2ba3e6b` 2026-06-14 — **crypto** · encryption-aware hallucination_guard memory-læsning (§16 Task 3.2)
- `8d1af71b` 2026-06-14 — **crypto** · encryption-aware member-memory I/O i workspace_capabilities (§16 Task 3.2)
- `ca72f447` 2026-06-14 — **crypto** · encryption-aware generiske fil-tools + Boy Scout-udskillelse (§16 Task 3.2)
- `3297970a` 2026-06-14 — **crypto** · runtime/-eksklusion + bootstrap .enc-aware (§16 fuld-kryptering prereq)
- `46d2676d` 2026-06-14 — **crypto** · encryption-aware memory_resurfacing + fuld-migration-plan (§16)
- `91197f7a` 2026-06-14 — **crypto** · encryption-aware member prompt-sti-læsere (§16 fuld-kryptering)
- `93c7bbed` 2026-06-14 — **security** · skill_scanner — prompt-injection/malware/boundary (§19.8/§15.3.2)
- `e996e466` 2026-06-14 — **codemode** · bro summary-filtrering + local-execution-markering (§17/§7)
- `04270693` 2026-06-14 — **channels** · inbound mode-switch + cowork_dispatch app-instruktioner (§18)
- `ff7f3001` 2026-06-14 — **codemode** · agent_dispatch orchestrator (§19)
- `bb16a0dd` 2026-06-14 — **security** · wire skill_scanner ind i skill-oprettelse + indlæsning (§19.8 live)
- `5a5b1a40` 2026-06-14 — **codemode** · bridge mode-awareness — kun code-mode eksekverer lokalt (§17.6.1)
- `0f14c0e6` 2026-06-14 — **cowork** · agent dispatch-panel + view-builder (§19.5 command center)
- `ae634152` 2026-06-14 — **cowork** · live agent-panel — /cowork/agents endpoint + CoworkView-wiring (§19.5)
- `3caec832` 2026-06-14 — **api** · §20 hærdning — security-headers + env-gated CORS-whitelist + rate-limit
- `ab09a35f` 2026-06-14 — **quota** · §21 kvote-model — quota_store (tier/mode, daglig nulstilling)
- `3ffde8bf` 2026-06-14 — **auth** · §22.6 refresh-token-rotation (kortlivet access + roterende refresh)
- `52ff25ff` 2026-06-14 — **api** · §20.1 in-app HTTP→HTTPS-redirect (X-Forwarded-Proto-gated)
- `c3e6330f` 2026-06-14 — **api** · §20.1 redirect undtager loopback (intern HTTP består) + ren beslutning
- `f13d4479` 2026-06-14 — **visible** · num_ctx 256k→512k konfigurerbar via runtime.json (reconciled)
- `c5a65bba` 2026-06-14 — **enforcement** · wire kvote + refresh-token live (§21.7 + §22.6)
- `ba3ebb89` 2026-06-14 — **security+billing** · ClamAV malware-scan + Stripe-billing-skelet (§15.3.1 + §21.6)
- `ff7b8603` 2026-06-14 — **desk** · i18n-fundament (da/en) + auto-update-wiring (§22.3 + §22.5)
- `8edb47f9` 2026-06-14 — **desk** · Code-mode terminal-rude (§17) — lokal kommando-runner m. xterm
- `ba0d68b9` 2026-06-14 — **channels** · kanal-migration Fase 2 — app modtager+udfører cowork-instruktioner (§18.5)
- `0be84331` 2026-06-14 — **agents** · live agent-dispatch tool — dispatch_code_mode_task (§19)
- `612be31a` 2026-06-14 — **desk** · terminal v2 — container-exec (server-side bash, owner-only) (§17)

**Rettelser**

- `da7ec45c` 2026-06-08 — **lag1** · response_style scoring was silently broken
- `e97ddf54` 2026-06-08 — **reasoning_store** · event_bus.emit() doesn't exist, use publish()
- `6932f2be` 2026-06-08 — **visible_runs** · offload _build_visible_input to thread to unfreeze main loop
- `bea6b1fe` 2026-06-08 — **visible_runs** · offload agentic-loop tool execution to thread
- `2247c30b` 2026-06-08 — **memory** · align recall_count bump with salience field — 1-line diff
- `d4afa69c` 2026-06-09 — **bare** · fallback to thinking field for DeepSeek-v4-flash CoT output
- `eb5011e4` 2026-06-09 — **brain** · add missing related column to brain_index schema
- `3ea3cc80` 2026-06-09 — **brain** · include kind+visibility in infer_temporal_edges candidate proxy
- `7398d8f0` 2026-06-09 — **brain** · tolerate stale brain_index rows in temporal-edge inference
- `5a7d13d2` 2026-06-09 — **brain** · drop logger.debug in temporal-edge except (no module logger)
- `675d27b2` 2026-06-09 — **brain** · abort temporal-edge inference when subject entry is stale
- `c1a2deb1` 2026-06-09 — extract reasoning_content as fallback in heartbeat runners + demote WARNING to INFO in visible_followup
- `fcf2e4e5` 2026-06-09 — **heartbeat** · wire 4 unwired daemons + feedback note for Jarvis
- `8c9b2607` 2026-06-09 — **identity_sketch** · wire promised periodic-every-6h heartbeat trigger
- `0e2f07c3` 2026-06-09 — **prompt-contract** · inject format_chain_proposals into awareness
- `bd1b1667` 2026-06-09 — **prompt-contract** · inject multi_signal_recall_section into awareness
- `b49c3a05` 2026-06-09 — **skill-tools** · expose C1 audit trail as skill_history + recent_skill_changes tools
- `1261530a` 2026-06-09 — **skill-tools** · expose analyze_skill_usage as tool + flag broken write-path
- `80038758` 2026-06-09 — add record_skill_usage call sites in skill_invoke and skill_chain tools
- `c679e34c` 2026-06-09 — **workspace-default** · mark USER.md as template with explicit guard
- `52d6563e` 2026-06-09 — **prompt-contract** · anchor transcript on user-turns + bump 1M budgets
- `1f4b819f` 2026-06-09 — **memory** · open MEMORY.md auto-apply gate for end-of-run consolidation
- `1c2935ed` 2026-06-09 — **identity** · stub-fallback to shared/ for SOUL/IDENTITY/MILESTONES
- `02960c2a` 2026-06-09 — **cache** · growing-window transcript fixes 0% transcript cache hit
- `1541720b` 2026-06-09 — **monitor** · læs cache data fra costs-tabellen i stedet for events
- `34309d42` 2026-06-10 — **cache-warmer** · læs deepseek_api_key fra runtime.json, prioriter prompt-fil over core-import
- `cc51f1db` 2026-06-10 — **cache-warmer** · brug build_visible_stable_prefix for ægte cache match
- `70c1ee03` 2026-06-10 — **cache-warmer** · sys.path fix for standalone import
- `38878c2f` 2026-06-10 — **cache-metrics** · visible-lane bookkeeping reporterer ægte cache-tal
- `8ebff783` 2026-06-10 — **cache-warmer** · brug bjorn workspace i stedet for default
- `d1e090e5` 2026-06-10 — **visible-runs** · stale-active-run timeout — webchat freeze recovery
- `61955d28` 2026-06-10 — **continuation** · deaktiver approval_question pattern — fjerner ghost JARVIS bubble
- `c2ad9efe` 2026-06-10 — **visible-runs** · bumpe stale-threshold 30s→120s — beskyt agentic tool-loops
- `3ae78f8f` 2026-06-10 — **vision** · bumpe timeout 60s→180s + 1 retry for cold-start latens
- `8df286a9` 2026-06-10 — **ui** · ryd isStreaming før await — eliminer ghost JARVIS bubble
- `a8dc0d8d` 2026-06-10 — **api** · CORS middleware for desktop-app klienter
- `984b8d0b` 2026-06-10 — **auth-middleware** · allow OPTIONS preflight without auth (CORS-fix)
- `b4c6628c` 2026-06-10 — **jarvis-desk** · sessions list virker nu — items[] response + webSecurity off i dev
- `2ff2733b` 2026-06-10 — **time** · time pin viser kun dansk tid (ingen UTC forvirring) + chat_sessions 24-tid
- `644a1a2b` 2026-06-11 — **jarvis** · stop tool-loop stilhed — Bjørn frustration crisis fix
- `8f4acee1` 2026-06-11 — **jarvis** · stop hallucinated work — daemon off + claim-scanner
- `923da0bf` 2026-06-11 — **jarvis** · Discord-aktivitet heartbeat — slut med "skriver..." stilhed
- `2e742053` 2026-06-11 — **discord** · get_discord_channel_for_session DB-fallback for kendte Discord-sessioner
- `b976718f` 2026-06-11 — **visible-runs** · async-wrapper omkring run_in_executor — fix TypeError
- `3d434e8d` 2026-06-11 — **unfinished-intent** · future-tense action-promise pattern
- `e7ab2772` 2026-06-11 — **time** · time pin viser kun dansk tid (ingen UTC) — sed-fix + tests opdateret
- `59216d79` 2026-06-11 — **visible_runs** · persist sanitized fallback when invariant-leak detected
- `1669f17b` 2026-06-11 — **user-temperature** · LLM confidence override i combine_streams — når structural er usikker (<0.3 conf) og LLM er sikker (>0.7 conf) vinder LLM
- `4163c058` 2026-06-11 — **jarvis-desk** · commit uncommitted getSession normalisering (base for foundation)
- `e53fcf02` 2026-06-11 — **jarvis-desk** · tsc-strictness narrowing i streamReducer (undefined guard)
- `6992817d` 2026-06-11 — **jarvis-desk** · main-layout crash — grid→flex (ChatView+composer var væk)
- `ca04bb1c` 2026-06-11 — **jarvis-desk** · chat-rendering — overflow, perf, auto-scroll, tool-filter
- `140edeb5` 2026-06-11 — **jarvis-desk** · composer centreret til chat-kolonne (820px, margin auto)
- `1442b856` 2026-06-11 — **jarvis-desk** · header redesign, server-navn, scroll-pil position, skjult scrollbar
- `cd8b7365` 2026-06-11 — **jarvis-desk** · composer overflow visible — +/permissions popovers folder op over rammen (ikke klippet indeni)
- `849a782c` 2026-06-11 — **jarvis-desk** · optimistisk besked wipet ved ny-samtale + tom titel
- `1507f34b` 2026-06-11 — **jarvis-desk** · fang run_id fra system_event kind=run (message_start har tomt id) — server-cancel virker nu
- `727b5b71` 2026-06-11 — **jarvis-desk** · select merger med nuværende beskeder (bevarer optimistisk) + diag-logs
- `bff5f986` 2026-06-11 — **jarvis-desk** · createSession unwrapper { session: {...} } — id var undefined
- `ce08aded` 2026-06-11 — **jarvis-desk** · falsk "Genoptag" efter hvert svar — connectOnce kastede trods message_stop
- `25a26389` 2026-06-11 — **jarvis-desk** · falsk "Jarvis svarer ikke" 90s efter svar — stop watchdog ved message_stop
- `75deaf47` 2026-06-11 — **jarvis-desk** · header (titel + forbindelse) vises også i tom/ny-samtale tilstand
- `131e210d` 2026-06-11 — **jarvis-desk** · drag/drop fil-upload — håndtér drop på window-niveau (Electron åd element-droppet)
- `78275bc6` 2026-06-11 — **jarvis-desk** · attachment-upload medsender session_id (required Form-felt) + lazy-opret session ved ny chat
- `0887b78a` 2026-06-11 — **jarvis-desk** · image-only send 400 — fallback-besked (filnavn); dokumentér vision-gap i STUBS
- `18030bca` 2026-06-11 — **jarvis-desktop** · index.html title → Jarvis (titel-bar) + gitignore release/
- `a84d3900` 2026-06-11 — **jarvis-desktop** · disableHardwareAcceleration + disable-gpu-sandbox — pakket app crashede på GPU (Linux)
- `42b72336` 2026-06-12 — **jarvis-desk** · composer auto-resize + flyt søg under Billeder
- `72937b51` 2026-06-12 — **jarvis-desk** · context-ring fik aldrig tokens — læs input_tokens fra message_delta
- `8e5dcc53` 2026-06-12 — **jarvis-desk** · context-ring placeres ved composerens højre-hjørne (ikke skærmkant)
- `5a977943` 2026-06-12 — **jarvis-desk** · context-ring INDE i composer-baren + altid synlig
- `fd8c2e0c` 2026-06-12 — **jarvis-desk** · context-ring i composerens top-højre hjørne + rigtigt niveau fra start
- `806c5f94` 2026-06-12 — **chat_sessions** · expose workspace_kind in list_chat_sessions summary (code-mode sidebar icon)
- `a79b1e42` 2026-06-12 — **chat-stream-v2** · persist code-mode workspace binding to session so trust gate enforces on the selected workspace
- `3362a010` 2026-06-12 — **jarvis-desk** · code-mode mirrors chat empty-state (centered welcome until first msg) + role-based workspace options (owner=server roots, member=mit workspace)
- `cb15b3f9` 2026-06-12 — **jarvis-desk** · trust POST double-stringify bug + code-mode autoscroll & scroll-to-bottom arrow
- `d8770d2a` 2026-06-12 — **jarvis-desk** · notices (interrupt/hang/error) over composer + disclaimer under composer + composer bottom spacing (chat+code)
- `b432cdca` 2026-06-12 — **jarvis-desk** · persist code-mode workspace selection across restart (trust was server-side persistent; selection was lost)
- `421f56af` 2026-06-12 — **chat** · offload git-status blocking work to asyncio.to_thread — was freezing the single uvicorn worker (api appeared offline)
- `7e2fbf1d` 2026-06-12 — **jarvis-desk** · token count persists after turn (klar · N tokens) + uses real output_tokens when available
- `139484bf` 2026-06-12 — **jarvis-desk** · liveness order tokens-time-verb + locked real output_tokens (updates per run, not live)
- `b06da3e3` 2026-06-12 — **cowork** · owner detection via user role (find_user_by_discord_id) — Bjørn's discord-id is owner, not literal 'owner'
- `70b843e9` 2026-06-12 — **jarvis-desk** · re-enable GPU hardware acceleration (+ ignore-gpu-blocklist) — software rendering caused glitchy graphics on view-switch (Linux)
- `8af1957a` 2026-06-12 — **jarvis-desk** · rod-årsag til 'kastet ind' Jarvis-tekst — 3 CSS-fixes
- `7e74812c` 2026-06-12 — **jarvis-desk** · port webchat's em-based markdown ruleset to .jarvis-body
- `46799fe6` 2026-06-12 — **jarvis-desk** · live token-counter under streaming
- `c7ec0800` 2026-06-12 — **jarvis-desk** · rod-årsag til 'kastet ind' rendering — remark-breaks + tæm enforceStructure (v0.2.2)
- `39c7048e` 2026-06-12 — **jarvis-desk** · SetupScreen URL-concatenation — default som placeholder, ikke forudfyldt værdi
- `da9b9413` 2026-06-12 — **visible** · backend markdown-normalizer — rod-årsag til 'kastet ind' rendering
- `a5278ee3` 2026-06-12 — **jarvis-desk** · spejl markdown-normalizer i enforceStructure for live-visning (v0.2.3)
- `4f212fae` 2026-06-12 — **jarvis-desk** · tool-echo-leak — reconcile fra server + client-sanitizer + prompt-nudge (v0.2.4)
- `2e31dbf9` 2026-06-12 — **jarvis-desk** · session-menu (omdøb/eksport/slet) + notifikations-badge (v0.2.5)
- `13bef8b6` 2026-06-12 — **infra-weather** · cooldown 30min->6h sa critical alerts ikke spammer hele aftenen
- `f0b1ae10` 2026-06-13 — **ollama** · brug ollama-providerens base_url, ikke visible-lanen (deepseek-API)
- `79e3c513` 2026-06-13 — **markdown** · reflow crammed tabeller (hel tabel på én linje → rækker)
- `66e759f5` 2026-06-13 — **r2-gate** · skær støj — kun ægte shell-mutationer tæller (Jarvis' egen diagnose)
- `15101b7b` 2026-06-13 — **visible-runs** · UnboundLocalError total_cache_hit_tokens crashede agentiske runs
- `c8333ef4` 2026-06-13 — **render** · fjern remarkBreaks + bryd inline ATX-headers ud — løs 'kastet ind' (v0.2.9)
- `6168b618` 2026-06-13 — **ollama** · læs + replay thinking-feltet — løs tabt endeligt svar (Bjørn fandt roden)
- `5351f3ad` 2026-06-13 — **ollama** · retry HTTP 429 med backoff i stedet for at aborte loopet
- `7399603f` 2026-06-13 — **copilot** · self-healing profil-resolve + readiness-filter i visible-vælger
- `931227b2` 2026-06-13 — **copilot** · filtrér visible-vælger til virkende copilot-modeller (kun gpt-4o*)
- `72c4a255` 2026-06-13 — **jarvis-desk** · dublet-besked + composer cursor-hop (v0.2.6)
- `f52befa2` 2026-06-13 — **wakeup+desk** · app-only wakeup-routing m. Discord-guard + chat copy/context-menu (v0.2.11)
- `79aa7340` 2026-06-13 — **stream** · terminal-garanti — message_stop ALTID emitteres → ingen random hangs (v0.2.13)
- `f81add05` 2026-06-13 — **jarvis-desk** · liveness centreret over composer + autonom wakeup-pickup i appen (v0.2.14)
- `8fb1f226` 2026-06-13 — **stream** · robust streaming — server-liveness som eneste sandhed, klient afstemmer (v0.2.15)
- `f99e73c0` 2026-06-13 — **jarvis-desk** · fjern legacy "tænkte…"-chip + wakeup lyser op alle indikatorer (v0.2.16)
- `947b9c94` 2026-06-13 — **stream** · cross-proces liveness via DB-heartbeat — autonome wakeup-runs synlige igen (v0.2.17)
- `86b45c50` 2026-06-13 — **wakeup** · operator-wakeup starter run STRAKS + rullende rate-guard (v0.2.18)
- `d21c235b` 2026-06-13 — **jarvis-desk** · bgActive latch + hurtigere poll → ring/systray/header reagerer på korte wakeup-runs (v0.2.19)
- `3edf8e1b` 2026-06-13 — **jarvis-desk** · liveness+header reagerer på wakeup efter en done-tur (v0.2.20)
- `447ac755` 2026-06-13 — **wakeup** · rul follow-streaming tilbage — brækkede run-livscyklus → hang (v0.2.22)
- `8e6c8f77` 2026-06-13 — **jarvis-desk** · deaktivér desk-follow → fjern "BodyStreamBuffer was aborted"-støj
- `bd69c1fe` 2026-06-14 — **somatic** · tilføj tids-baseret decay → bryd stuck "startled"-posture
- `e7e9cea2` 2026-06-14 — **desk** · style owner Settings-paneler (2FA, Plugins) + share-guard-rude
- `4acbb846` 2026-06-14 — **security** · bind eksplicit rolle for discord-brugere (luk member→owner-hul)
- `2109a629` 2026-06-14 — **plugins** · narrow Discord-kanal-type før send (electron-tsc)
- `779197c8` 2026-06-14 — **crypto** · robust headless keyring-detektion via probe (§16)
- `21bb12e1` 2026-06-14 — **api** · §20-middlewares OUTERMOST (efter auth) så redirect+headers dækker 401
- `81a5dcce` 2026-06-14 — **desk** · luk 7 unhandled test-errors — manglende mock-exports + setState-after-unmount guard
- `346ae72c` 2026-06-14 — **codex** · tomme svar ved tool-kald — surfacér function_call i stedet for at kaste

**Omstrukturering**

- `5c8ebda7` 2026-06-11 — **jarvis-desk** · udtræk v2 event-typer til sseProtocol.ts + ContentBlock
- `aea71a6d` 2026-06-14 — **boyscout** · udskil capability-decl-parsere fra workspace_capabilities

**Ydelse**

- `bead9e64` 2026-06-09 — **auto-remember** · pre-LLM trivial-turn skip
- `c8f5a17e` 2026-06-09 — **prompt-cache** · tail-anchor live decimal-score sections
- `974cd4d0` 2026-06-13 — **prompt** · flyt finitude/looming-end til prompt-halen — cache-prefix 6k→15.8k tokens
- `74d59fae` 2026-06-13 — **prompt** · tail-anchor 4 dynamiske awareness-sektioner — stabil prefix nu pålideligt ~16k tokens
- `c83d30f3` 2026-06-13 — **prompt** · flyt time_pin fra system-besked til sidste bruger-besked — cache hele historikken (lever #2)
- `f139dd25` 2026-06-13 — **prompt** · flyt HELE den dynamiske hale til bruger-beskeden via sentinel — historik cacher nu (lever #3)
- `a3fa5e27` 2026-06-13 — **prompt** · flyt HELE det adaptive lag (recall + awareness) til bruger-beskeden — historik cacher nu (lever #4)

**Tests**

- `bf7e6a30` 2026-06-08 — **memory** · add 37 unit tests for multi-signal retrieval module
- `5621f32b` 2026-06-08 — **memory** · add multi-signal integration tests to memory_recall_engine
- `fae1545d` 2026-06-09 — **capability-markup + memory-recall** · tilføj unit tests for nye prompt_sections moduler
- `b688c902` 2026-06-09 — **b4** · tilføj 23 unit tests for temporal linking af brain entries
- `2c156874` 2026-06-13 — **render** · opdatér MarkdownRenderer-test til remarkBreaks-fjernelse

**Dokumentation**

- `e3c9e96b` 2026-06-08 — **memory** · add gap analysis summary to MEMORY.md — procedural memory correction + phased roadmap
- `26794a16` 2026-06-08 — **memory** · add gap analysis spec
- `31794af7` 2026-06-08 — **memory** · add phase 1 design spec
- `eccb8e90` 2026-06-08 — **memory** · add phase 2 design spec
- `d0663368` 2026-06-08 — **memory** · add phase 1 implementation plan
- `72e496f2` 2026-06-09 — **brain-spec** · opdater status — B1, B2, B3 markeret som færdige
- `09f155a2` 2026-06-09 — **b4** · tilføj design spec for temporal linking af brain entries
- `62026a83` 2026-06-09 — **A3+B5** · opdater status i gap-rapport — wakeup cleanup + async write queue
- `61a03214` 2026-06-09 — **notes** · note for Jarvis about visible-lane thinking-mode blind spot
- `2b459684` 2026-06-09 — **review** · update review with pattern-level findings (3 patterns)
- `db42be20` 2026-06-09 — **review** · complete review of all 39 commits + 6 pattern-B items pending
- `6c99a330` 2026-06-09 — **review** · close Mønster B series — 5 fixes + 1 secondary bug flagged
- `f2805e0a` 2026-06-10 — rewrite README in first person, cut 70%, quickstart top
- `f8952e1f` 2026-06-10 — **jarvis-desk** · lock Chat mode design — v3 approved
- `3d7d96f7` 2026-06-10 — **jarvis-desk** · commit v3 mockup (Bjørn-approved aften 2026-06-10)
- `d5d03996` 2026-06-11 — grundig systemgennemgang af agentic-loop arkitektur
- `5003dcdd` 2026-06-11 — jarvis-desk App-shell + Rich-rendering foundation spec
- `d843cd9c` 2026-06-11 — jarvis-desk feature-coverage katalog + rolle-skopering i foundation
- `771a51d1` 2026-06-11 — ret Codex-review findings på jarvis-desk specs (2×P1, 2×P2, 2×P3)
- `6c21fad5` 2026-06-11 — split connection/presence pill ambiguity (Codex P3)
- `04efbc24` 2026-06-11 — jarvis-desk edge-case & test-katalog (foundation)
- `fce67d50` 2026-06-11 — ret Codex anden review-runde — transport-realiteter (3×P1, 5×P2, 2×P3)
- `8700f07e` 2026-06-11 — ret formuleringsrester efter R1-R3 (Codex runde 3)
- `f7a2d539` 2026-06-11 — presence-dot i chat-header (Jarvis' review-ønske)
- `8b781b84` 2026-06-11 — jarvis-desk foundation implementerings-plan (8 faser, ~25 tasks)
- `4c12135f` 2026-06-11 — notér proaktiv outreach som åbent design-spørgsmål (Jarvis' ønske)
- `80f42fea` 2026-06-11 — **jarvis-desk** · design-spec for preview-panel + kontekst-ring (cross-mode)
- `8f99d598` 2026-06-11 — **jarvis-desk** · implementerings-plan for preview-panel + kontekst-ring (10 tasks v1)
- `2cc6447c` 2026-06-11 — **jarvis-desk** · STUBS — attachment-vision løst (v2 wirer analyze_image-direktiv)
- `2e12b25c` 2026-06-11 — **jarvis-desk** · STUBS — tool-leak (v2 Phase 2) + preview-panel fil-detektion observeret live
- `781e4e98` 2026-06-11 — **spec** · communication guard — sleep phrase boundary
- `3ba6709a` 2026-06-12 — **spec** · v2-stream Phase 2 — tool_use-blokke + tool-leak fix design
- `9c84f944` 2026-06-12 — **jarvis-desk** · STUBS — v2-stream Phase 2 løst (tool-leak + tool_use-blokke + panel-binding)
- `4df94fd6` 2026-06-12 — **spec** · jarvis-desk Code mode v1 design
- `d2070612` 2026-06-12 — **plan** · jarvis-desk Code mode v1 implementerings-plan (11 TDD-tasks, 3 faser)
- `44042a84` 2026-06-12 — **jarvis-desk** · mark code-mode plan tasks complete
- `5a9aae5f` 2026-06-12 — **cowork** · design-spec for jarvis-desk cowork-flade (rolle-bevidst 4-rude dashboard)
- `035a7c15` 2026-06-12 — **cowork** · implementerings-plan (13 TDD-tasks, 6 faser)
- `450c4620` 2026-06-12 — **jarvis-desk** · besked + build-instruktion til Windows-Claude (nsis-target, usigneret, bridge-port)
- `c5659b3c` 2026-06-12 — **jarvis-desk** · opdatér Windows-note → v0.2.0 + gh release upload-trin
- `b188b64f` 2026-06-12 — **jarvis-desk** · opdatér Windows-note → v0.2.3
- `c9a4e1fd` 2026-06-12 — **jarvis-desk** · opdatér Windows-note → v0.2.5
- `4b46d395` 2026-06-13 — cache-prefix arkitektur — hvorfor awareness-laget flyttede til bruger-beskeden
- `5aa99ec0` 2026-06-13 — **jarvis-desk** · opdatér Windows-note → v0.2.6 (138 tests)
- `1cc4038d` 2026-06-13 — **jarvis-desk** · opdatér Windows-note → v0.2.7 (141 tests)
- `958fc053` 2026-06-13 — **jarvis-desk** · ground-truth-anker i bridge.ts mod "orphaned"-konfabulering
- `d988a4b7` 2026-06-14 — TOTP Owner Override security design spec v1.1
- `24ffcda7` 2026-06-14 — tillids- og tilladelsesarkitektur v2.0 — mode-adgang, workspace, compute use
- `67be2338` 2026-06-14 — **spec** · Jarvis tillids-/tilladelses-/plugin-arkitektur v3.0 (godkendt)
- `616bca70` 2026-06-14 — **plan** · implementerings-plan for tillids-/tilladelses-/plugin-arkitektur
- `8c6f5ce1` 2026-06-14 — **steadier** · bevar Jarvis' inner-architecture-spec + verifikations-noter
- `af092527` 2026-06-14 — **security** · tool_access_matrix — kanonisk kilde for permission_engine
- `160a8f8e` 2026-06-14 — **totp** · §6.0 ukrænkelig bagdørs-invariant — owner-autoritet altid bestå
- `c5121296` 2026-06-14 — **spec** · persondata & sikkerhed — GDPR, share_guard, anti-manipulation (sektion 15)
- `cb4112e6` 2026-06-14 — **spec** · sektion 16 — kryptering & disk-sikkerhed (AES-256-GCM, OS keyring, GDPR)
- `e3ba0112` 2026-06-14 — **spec** · sektion 17 — code mode lokal eksekvering, opdateret §7+§8 med arkitektur-beslutning
- `195f182e` 2026-06-14 — **spec** · sektion 18 — proaktive kanaler forbundet til app, ikke runtime
- `d69479bf` 2026-06-14 — **spec** · sektion 18.9 — to indgangsvinkler (app + native Discord), fremtidige platforme
- `e4b4d1cd` 2026-06-14 — **plan** · §16 encryption-migration plan (Lag 3 data-touching rails)
- `fc998a09` 2026-06-14 — **spec** · sektion 19 — agent dispatch i code mode, cowork command center, skill-scanning
- `35bd77f4` 2026-06-14 — **spec** · sektion 20 — offentlig API sikkerhed (HTTPS redirect, CORS whitelist, security headers, rate limiting)
- `8ebe17d3` 2026-06-14 — **spec** · sektion 21 — kvote-model (gratis chat kvote, betalt ubegrænset, code time-kvote)
- `8b77f2c3` 2026-06-14 — **spec** · sektion 22 — lokalisering, plugin-markedsplads, auto-update, refresh token rotation
- `78c1d566` 2026-06-14 — **spec** · diagnosis-gate design — konfabulations-guard med verificeringskrav
- `a2156757` 2026-06-14 — **spec** · udvid diagnosis-gate design (+203/-50) — Jarvis egen videreudvikling
- `dd5c5c9c` 2026-06-14 — spec-gap backlog efter 61-spec audit + codex follow-up-adapter rod-årsag

**Vedligehold**

- `9dfd7403` 2026-06-08 — **pre-commit** · add identity_sketch mapping — service+tools tested in one file
- `1eb93ea3` 2026-06-08 — **pre-commit** · add context compaction mappings — session_compact+compact_llm
- `65f232f0` 2026-06-09 — **tests** · remove duplicate test_chat_sessions_paired.py
- `0cd3b07e` 2026-06-11 — **jarvis-desk** · vitest + testing-library + rich-libs infra
- `18e98146` 2026-06-11 — **jarvis-desk** · mere diag for ny-samtale send-flow (midlertidig)
- `886e0dbf` 2026-06-11 — **jarvis-desk** · synlig in-app diag-panel for ny-samtale send-flow (midlertidig)
- `6a163098` 2026-06-11 — **jarvis-desk** · untrack dist-electron build-output + fjern midlertidig diag.ts
- `bba018b2` 2026-06-12 — **jarvis-desk** · bump version 0.1.0 → 0.2.0 for første rigtige Jarvis-release
- `f89491ab` 2026-06-13 — **health** · fjern død ollamafreeapi fra ping-rotation (Jarvis-init, korrigeret)
- `a1a6eb75` 2026-06-13 — **jarvis-desk** · bump → 0.2.22 + opdatér Windows-build-note til v0.2.22
- `cab39239` 2026-06-14 — **desk** · bump 0.2.22 → 0.2.23 (§17 bridge-guard + §19 agent-panel)
- `b60fcb78` 2026-06-14 — **api** · fjern §20-debug-header (redirect verificeret live)
- `ff3ef397` 2026-06-14 — **api** · interne klienter localhost:80 → :8080 (port-omlægning prep)

**Formatering**

- `fb9d208c` 2026-06-11 — **jarvis-desk** · komponent-styles for foundation (codeblock, toolcard, approval, liveness, banner, presence-dot, views, setup)

**Build**

- `7e0d916c` 2026-06-12 — **jarvis-desk** · add mac (zip) + win (nsis) electron-builder targets — mac builds on linux unsigned

**Øvrigt**

- `6e996e7d` 2026-06-08 — add compute_recall_score() + cold_tier_recall() with quality scoring
- `5744e681` 2026-06-08 — activate cold tier with quality-scored private brain
- `0c5558d1` 2026-06-08 — add recall_count field to BrainEntry + SQLite index
- `636fd292` 2026-06-08 — add Phase 1 quality scoring + cold tier recall tests
- `5682ad94` 2026-06-09 — D5: extend ledger with daily/weekly cost summaries + savings estimator
- `d4c2e603` 2026-06-09 — D5: cost optimization daemon — daily/weekly budget alerts
- `2e3f5e53` 2026-06-09 — D5: register cost_optimization daemon in daemon_manager + tests
- `c377026f` 2026-06-09 — D2: memory benchmarks — latency, source diversity, consistency test suite
- `4257253d` 2026-06-09 — **jarvis-brain** · bump auto-inject budgets + fix stale compact threshold
- `1b8fd5ef` 2026-06-10 — Merge remote-tracking branch 'target/main'
- `88ea6c08` 2026-06-10 — Merge branch 'main' of ssh://10.0.0.39/media/projects/jarvis-v2
- `42250470` 2026-06-10 — Revert "fix(time): time pin viser kun dansk tid (ingen UTC forvirring) + chat_sessions 24-tid"
- `6b5f8fab` 2026-06-11 — Merge branch 'main' of ssh://10.0.0.39/media/projects/jarvis-v2
- `aac76b21` 2026-06-12 — Merge remote-tracking branch 'target/main'
- `a69ba711` 2026-06-13 — container-commits (infra-weather cooldown 6h, macOS operator window-branches)
- `ccb438c0` 2026-06-13 — **ollama** · reproducérbart concurrency-benchmark + baseline 2026-06-13
- `994dc958` 2026-06-13 — **ollama** · etappe 1-2 diagnose — systemet er allerede concurrency-optimeret
- `b59b38d0` 2026-06-14 — Merge remote-tracking branch 'target/main'
- `d5167eef` 2026-06-14 — **api** · midlertidig X-Redir-Debug header (§20 fejlsøgning)
- `d16b465e` 2026-06-14 — Merge remote-tracking branch 'target/main'

### Uge 25 · 15.–21. juni — 435 commits

**Nyt**

- `71c1fede` 2026-06-15 — **codex** · follow-up-adapter — gpt-5.4-mini fuldfører tool-ture (ikke længere afbrudt)
- `fe26fece` 2026-06-15 — **guard** · diagnosis-gate fase 1 — fang uverificerede diagnostiske konklusioner (§ spec 2026-06-14)
- `3fd7fa7e` 2026-06-15 — **guard** · promise-ledger §8 — flag uverificerede completion-claims (advisory)
- `8730e72d` 2026-06-15 — **app-control** · request_app_action tool + event-helper (spec 2026-06-15)
- `41c7ce31` 2026-06-15 — **app-control** · registrér tool + emit app_action_request SSE i visible_runs
- `d4919265` 2026-06-15 — **desk** · delte composerPrefs (localStorage-nøgler + readModelPrefs)
- `25084329` 2026-06-15 — **desk** · PermissionContext — løft permission ud af Composer
- `61966580` 2026-06-15 — **desk** · StreamContext pendingAppAction + auto-continue-stash
- `686ea9be` 2026-06-15 — **desk** · AppActionCard — inline godkendelseskort for mode/permission-skift
- `cc6029da` 2026-06-15 — **desk** · AppActionHost + resolveAppAction + PermissionProvider-wiring
- `4ad69119` 2026-06-15 — **desk** · CodeView auto-continue — gen-send besked efter godkendt skift
- `21cced26` 2026-06-15 — **desk** · tool_chip_payload helper — berig+trunkér tool-kald-data
- `d115c787` 2026-06-15 — **desk** · send args+result i tool-kald-event (root cause for tomme chips)
- `7fe91f3e` 2026-06-15 — **desk** · open_ui_panel action open/close — Jarvis kan lukke paneler
- `b8f683ef` 2026-06-15 — **desk** · streamReducer sætter tool-resultat på tool_use-blokken
- `061169a4` 2026-06-15 — **desk** · diffStat helper — +N −M for filændringer
- `1c99ed73` 2026-06-15 — **desk** · toolRegistry — pæne tool-navne + opsummering (Title-Case fallback = komplet dækning)
- `8a34f25f` 2026-06-15 — **desk** · ToolCard viser pæn label + opsummering + diff-stat (uden klik)
- `80e4e7a4` 2026-06-15 — **desk** · UiPanelWatcher lukker panel ved action=close
- `f0a61f91` 2026-06-15 — **users** · bcrypt password hashing (§5.2)
- `369a655a` 2026-06-15 — **users** · SQLite users-tabel + row-helpers (db_users.py, boy-scout split)
- `e5770eaa` 2026-06-15 — **users** · user_db adapter — kryptering + email_hash + CRUD
- `a3c42282` 2026-06-15 — **users** · add_user (pre-verificeret) + API-nøgle-livscyklus (tier-gated, revokerbar)
- `305840c4` 2026-06-15 — **users** · email-verifikation — token-store + send (24h, 3/dag)
- `b64d0e62` 2026-06-15 — **users** · register_user + verify_email_token (B2)
- `98f3eacd` 2026-06-15 — **users** · GDPR soft/hard-delete + keyring-key-sletning + audit-log (D1)
- `25eb20b2` 2026-06-15 — **users** · set_user_quota + get_tier foretrækker user_db-tier (D2)
- `2816c41a` 2026-06-15 — **users** · owner-only admin-routes CRUD + GDPR-erasure (D3)
- `a880c653` 2026-06-15 — **users** · offentlige auth-routes register/verify-email/login (Fase C)
- `082de668` 2026-06-15 — **users** · håndhæv API-nøgle-revocation live i verify_token (jti-bloklist)
- `0a850449` 2026-06-15 — **F** · generalized-learning capture-wiring — 4 kilder fodrer reasoning_store (plan A)
- `64ab04a3` 2026-06-15 — **desk** · file-preview med syntax-highlight (genbrug CodeBlock) — kode highlightes, tekst rå
- `4302b5a8` 2026-06-15 — **desk** · code-mode fil-/preview-panel trækbart + tynd scrollbar
- `de012de5` 2026-06-15 — **desk** · gensend-knap på bruger-bobler + code-panel default-proportioner
- `118ec4c0` 2026-06-15 — **desk** · liveness fast over composer + Jarvis-highlight + højreklik editor/terminal
- `c720bfc4` 2026-06-15 — **desk** · code-panel ydelse (keep-alive + cache) + live fil-highlight + on-the-fly editor
- `b439eb40` 2026-06-15 — ægte per-model context-ring + register_user provisionerer (krypteret) workspace
- `74710c89` 2026-06-15 — **visible** · model-bevidst prompt-trim — GLM/små-vindue-modeller overløber ikke
- `103b4b74` 2026-06-15 — **multiuser** · users.json→SQLite hybrid-resolution — nyregistrerede brugere virker
- `4a33f2ca` 2026-06-15 — **security** · #154 streng per-bruger-scope på private_brain/sensory/autonomy/recurring
- `c03e35f2` 2026-06-15 — **security** · recurring tasks affyrer i ejerens bruger-kontekst (#154-followup)
- `8c7bf43b` 2026-06-15 — **desk** · open_ui_panel kan nu vise en FIL i preview-panelet
- `faa378b1` 2026-06-15 — **account** · GET /account/me self-profile (cowork command center §4.1)
- `0d7c6934` 2026-06-15 — **desk** · getAccountMe API-klient for /account/me
- `bf40c732` 2026-06-15 — **desk** · AccountSection — self-profil i cowork-indstillinger
- `8d515a77` 2026-06-15 — **desk** · CoworkZones — to-zone-skal (Mission Control | Indstillinger)
- `04265eb9` 2026-06-15 — **desk** · cowork to-zone command center — MC-grid + indstillingszone
- `fd6b4c4d` 2026-06-15 — **todos** · cowork-session + cross-session todo-helpers (command center §3.1)
- `3610ea67` 2026-06-15 — **cowork** · POST/DELETE todo-endpoints (owner-only)
- `311b52d2` 2026-06-15 — **desk** · coworkApi todo-mutationer (create/status/delete)
- `4a731b6f` 2026-06-15 — **desk** · redigerbar TodoPane (opret/status/slet)
- `93e04de9` 2026-06-15 — **desk** · wire redigerbar TodoPane i cowork + refresh
- `0c0d2ce8` 2026-06-15 — **todos** · opt-in TTL (udledt 'expired') + pause; skjult fra Jarvis-prompt (§3.1)
- `48038420` 2026-06-15 — **cowork** · expiry-endpoint + feed viser udledt status/expires_at + 'paused'
- `5a9e475e` 2026-06-15 — **desk** · setCoworkTodoExpiry + CoworkTodo.expires_at
- `5790bf89` 2026-06-15 — **desk** · TodoPane pause/genoptag + opt-in TTL-vælger + expired-visning
- `b3fed462` 2026-06-15 — **account** · GET /account/quota self-scope kvote-overblik (§4.9)
- `a726c0e3` 2026-06-15 — **desk** · getAccountQuota + QuotaOverview-typer
- `bc7d0af6` 2026-06-15 — **desk** · KvoteSection — tier + forbrugs-bjælker
- `75398c59` 2026-06-15 — **desk** · vis KvoteSection i cowork-indstillinger + styling
- `3c153b11` 2026-06-15 — **desk** · Tema-sektion — mørk/lys/høj kontrast (§4.11)
- `15f7a277` 2026-06-15 — **account** · self-scope PATCH /account/language + language-kolonne/migration (§4.10)
- `f14e214d` 2026-06-15 — **desk** · Sprog-sektion — self-scope sprogvalg (§4.10)
- `ce4dd6a6` 2026-06-15 — **account** · GET /account/workspace self-scope (filer/disk/kryptering/trust) (§4.8)
- `f2f6f821` 2026-06-15 — **desk** · Workspace-sektion — filer/disk/kryptering/trust (§4.8)
- `5bdcdf30` 2026-06-15 — **account** · self-scope GET /account/memory + /memory/search (§4.3)
- `e436da66` 2026-06-15 — **desk** · Memory-sektion — self-scope MEMORY/USER/sansning + søgning (§4.3)
- `a4014a9a` 2026-06-15 — **account** · Permissions — tool-matrix + håndhævet computer-use-toggle (§4.7)
- `3486acd4` 2026-06-15 — **desk** · Permissions-sektion — tool-matrix + computer-use-toggle (§4.7)
- `1874989a` 2026-06-15 — **account** · Jarvis-sektion backend — lane-modeller + owner visible-model-select (§4.2)
- `d2a9de5b` 2026-06-15 — **desk** · Jarvis-sektion — model pr. lane + synlig-model-valg (§4.2)
- `ac7e22e5` 2026-06-15 — **account** · Apps (connector-registry) + MCP-server-config-store (§4.5/§4.6)
- `1c1e1892` 2026-06-15 — **desk** · Apps + MCP-sektioner (§4.5/§4.6)
- `68e382d7` 2026-06-15 — **desk** · §5 — open_ui_panel(settings) åbner indstillingszonen (request_full_access fandtes)
- `2c089283` 2026-06-15 — **liveness** · Stage 2 — liveness-registry + /mc/liveness sandheds-flade
- `e0a567f6` 2026-06-15 — **retention** · bremset ubegrænset vækst — wire compact_stale + telemetri-prune
- `848e14dc` 2026-06-16 — **security** · Spor A — serverside tool-håndhævelse i execute_tool (defense-in-depth)
- `c2e84502` 2026-06-16 — **discord** · Spor D — afsender-bevidsthed med rolle + gæst-markering i fælleskanaler
- `f2135c3f` 2026-06-16 — **honesty** · promote promise-ledger §8 til håndhævende — bloker uverificerede completion-claims
- `538fff1d` 2026-06-16 — **honesty** · unfinished_intent fanger korte start-løfter ('jeg går i gang')
- `647da141` 2026-06-16 — **honesty** · Bjørn-gate — promise-ledger holder Jarvis ansvarlig på tværs af ture
- `40ab4934` 2026-06-16 — **plugins** · per-bruger krypteret OAuth-token-hvælv (privatlivs-spine)
- `c2a87847` 2026-06-16 — **plugins** · OAuth connect-endpoints — /start (auth) + /callback (public, signeret state)
- `bef9e9f1` 2026-06-16 — **oauth** · gem expires_at ved code-exchange
- `71ba76bb` 2026-06-16 — **oauth** · refresh_token via grant_type=refresh_token
- `f154e02b` 2026-06-16 — **oauth** · revoke_remote — tilbagekald token hos provider
- `aa7479ca` 2026-06-16 — **oauth** · get_fresh_token — auto-refresh ved udløb
- `bf5ba82a` 2026-06-16 — **connectors** · katalog + per-bruger status/enable + delete (revoke+wipe, GDPR)
- `291a6253` 2026-06-16 — **connectors** · GET/POST-enabled/DELETE routes + registrér i app
- `7b79fec6` 2026-06-16 — **connectors** · GitHub-tools (issues/PRs) scopet til Spor A
- `ef27afb6` 2026-06-16 — **desk** · marketplace-zone + COWORK_ZONES m. ikoner
- `1c3fcd0d` 2026-06-16 — **desk** · Sidebar mode-bevidst — cowork-menu m. ikoner i eksisterende panel
- `129b61c0` 2026-06-16 — **desk** · fjern CoworkZones intern rail — ét panel, zone fra Sidebar
- `f6a71395` 2026-06-16 — **desk** · connectorsApi-wrappere (get/setEnabled/delete/startConnect)
- `4f34f1af` 2026-06-16 — **desk** · MarketplacePane — forbind/til-fra/slet + scope-transparens, wired i cowork
- `273f390b` 2026-06-16 — **desk** · tids-bevidst greeting m. random-pulje + tint (måne om aftenen)
- `9161744a` 2026-06-16 — **desk** · GreetingHero — tids-greeting + connector-forslag i tom session
- `c2a779ff` 2026-06-16 — **desk** · post-connect-hook — toast + connector-specifikt forslag i tom session
- `82e0a88f` 2026-06-16 — **open_ui_panel** · workstation-support med scope-parameter
- `6243abcf` 2026-06-17 — **plugins** · surface forbundne connectors i Jarvis' prompt-awareness
- `f3997897` 2026-06-17 — **plugins** · fuldt katalog — hele plugin-listen synlig i Marketplace (fase 1)
- `b1f58d71` 2026-06-17 — **plugins** · Gmail-connector live — Google-pakkens lodrette bevis (fase 2)
- `8a2fd4dd` 2026-06-17 — **plugins** · resten af Google-pakken live — Calendar/Drive/Docs/Sheets/Slides (læse-tools)
- `3fd67968` 2026-06-17 — **plugins** · gmail_send bag approval-kort (nr 3)
- `9a4563c9` 2026-06-17 — **desk** · land på greeting-skærm ved genstart, ikke gammel session (nr 4)
- `ca2f2d5e` 2026-06-17 — **plugins** · Google-pakkens skrive-tools bag approval
- `aa5ce578` 2026-06-17 — **plugins** · P2/P3 — PDF + Huskesedler + Hugging Face live (lokale/token)
- `837c5dca` 2026-06-17 — **compliance** · AI-transparens-notice ved første kørsel (EU AI Act Art. 50(1))
- `064e187a` 2026-06-17 — **security** · garantér 0600-perms på runtime.json i kode (roadmap #1b)
- `524c0e87` 2026-06-17 — **compliance** · Data & privatliv-panel i Settings (roadmap #2a)
- `35cf59ee` 2026-06-17 — **compliance** · GDPR-dataeksport — /account/export + 'Download mine data' (roadmap #2b)
- `d46905a1` 2026-06-17 — **settings** · Forbrug & kvote-panel (roadmap #3a)
- `0e9911f6` 2026-06-17 — **desk** · globale tastaturgenveje — Esc stop, Ctrl/Cmd+, settings (roadmap #3b)
- `9bc1d73c` 2026-06-17 — **settings** · Om / system-info-panel (roadmap #3c)
- `27585b39` 2026-06-17 — **settings** · Tastaturgenveje-panel — gør genveje opdagelige (roadmap #3d)
- `7eacf6fd` 2026-06-17 — **desk** · OS-notifikation ved afventende godkendelse (roadmap #3e)
- `4269ddf4` 2026-06-17 — **desk** · genbrugelig DiffView-komponent (roadmap #3f)
- `eb9617fe` 2026-06-17 — **desk** · wire DiffView ind i tool-kortet for edit-tools (roadmap #3f-wiring)
- `b44642cc` 2026-06-17 — **gdpr** · data-sletnings-eksekvering — erase_user + /account/erase (roadmap #2c→byg)
- `a007b031` 2026-06-17 — **desk** · offline-badge i status bar + reduced-motion a11y (spec §6.1 + a11y)
- `4a86d443` 2026-06-17 — **desk** · 'Prøv igen' på error-banner (spec §Error-UX)
- `ee00c5d2` 2026-06-17 — **desk** · søgning på tværs af sessioner + Ctrl/Cmd+K palette (spec §14.3)
- `e71daa15` 2026-06-17 — **desk** · empty-state polish — placeholder, privatlivs-link, apps-kort, ny-samtale (Bjørns batch)
- `3957b759` 2026-06-17 — **desk** · brand-farvede connector-ikoner (Gmail rød, Drive grøn, Slack aubergine osv.)
- `8e179ed4` 2026-06-17 — **desk** · Miljø-felt i code mode (live run-panel, à la Codex billede 1)
- `a47a7dd9` 2026-06-17 — **desk** · besked-rail (venstre kant, hop til besked) i chat + code (Claude billede 2)
- `474948fd` 2026-06-17 — **desk** · saml code-mode controls i headeren + paneler ved session-start
- `fdb66c43` 2026-06-17 — **desk** · save-rail som Claude-TOC 1:1 + miljø-felt som Codex 1:1
- `3287375c` 2026-06-17 — **desk** · miljø-felt som header-toggle + auto-vis ved fuld skærm
- `ee40970c` 2026-06-17 — **code** · ægte commit-alt + opret-PR i miljø-feltet (rolle-bestemt)
- `d7e138ac` 2026-06-17 — **git_actions** · container commit_all
- `5b728884` 2026-06-17 — **git_actions** · workstation commit_all via operator_bash
- `262d77b9` 2026-06-17 — **git_actions** · rolle-aware commit/PR backend (container+workstation, API+gh)
- `028d4689` 2026-06-17 — **desk** · rolle-aware git-knapper (server + workstation) i miljø-felt
- `bcaa69d8` 2026-06-17 — **desk** · auto-update — electron-updater + wireUpdater events→IPC + UpdateCard
- `ff851299` 2026-06-17 — **desk** · dependency-doctor (detektér+installér git/gh/node/rg cross-OS)
- `c005ed77` 2026-06-17 — **desk** · git-gate i miljø-felt + auto-update latest.yml i release-CI
- `35cb41ad` 2026-06-17 — **desk** · save-rail cap+tæt + miljø-felt session-totaler + pæne tool-kald
- `6e27a627` 2026-06-17 — **auth** · Google app-login (§12) — backend (forud-linket konto, GDPR-hash)
- `5c94084d` 2026-06-17 — **desk** · Log ind med Google i SetupScreen (§12) — poll token-retur
- `fffa8bf8` 2026-06-17 — **auth** · store-agnostisk Google-login-link (google_login_links-tabel)
- `63a399c3` 2026-06-17 — **desk** · luk Google-login — hardcoded API-URL + Forbind-Google i Settings
- `4e38dcee` 2026-06-17 — **desk** · offline-kø + auto-flush ved reconnect (§14.1)
- `cde1c3f3` 2026-06-17 — **auth** · QR device-pairing backend (pair/create + pair/redeem)
- `2400f07b` 2026-06-18 — **desk** · QR-pairing-visning i Account — forbind mobil-companion
- `35788991` 2026-06-18 — **auth** · pair/status endpoint — desktop kan se når mobil har parret
- `5deb7a41` 2026-06-18 — **desk** · vis 'Mobil tilsluttet ✓' når QR scannes (poll pair/status)
- `1648309e` 2026-06-18 — **desk** · skjul gen-forbind-knapper når forbundet (maks 1 konto/enhed)
- `3db1c676` 2026-06-18 — **broadcast** · tee bruger-run v2-frames til run_follow (live session-sync A1)
- `eb1308e4` 2026-06-18 — **broadcast** · afkobl bruger-run fra request-forbindelsen (A3 - stream overlever baggrund)
- `685a6348` 2026-06-18 — **chat** · /sessions/{id}/cancel-active — afbryd sessionens run (mobil stop-knap)
- `41a4ec92` 2026-06-19 — **runs** · per-run event-log (server-authoritative fundament)
- `0dbbb931` 2026-06-19 — **settings** · server_authoritative_runs-flag (default OFF)
- `40db4584` 2026-06-19 — **runs** · detached runner tee'er til run_event_log pr. run
- `9ce77f73` 2026-06-19 — **stream** · flag-gatet server-autoritativ sti (OFF=A1-tee uaendret, verificeret)
- `3f5f8eb8` 2026-06-19 — **chat** · /runs/{id}/subscribe + /sessions/{id}/live (gen-abonnering)
- `f9dc90eb` 2026-06-19 — **active-runs** · afled fra run_event_log naar flag ON
- `c5a6aa37` 2026-06-19 — **desk** · ompeg live-follow til /sessions/{id}/live (server-authoritative realtime-sync)
- `a8efbca4` 2026-06-19 — **desk** · genaktiver live-stream follow (cross-device mirroring)
- `a5fdef11` 2026-06-19 — **push** · device_tokens-tabel + CRUD pr. bruger
- `f5e6a63e` 2026-06-19 — **push** · abonnent-sporing i run_event_log til suppression-signal
- `8ffed0fb` 2026-06-19 — **push** · get_session_owner til token-routing
- `8839bb36` 2026-06-19 — **push** · fcm_gateway — data-only FCM v1 send + token-oprydnings-signal
- `8e8ab312` 2026-06-19 — **push** · push_dispatcher — grace + suppression + token-oprydning
- `2cd594cd` 2026-06-19 — **push** · /push/register + /push/unregister (bruger-scoped)
- `7801e9dd` 2026-06-19 — **push** · wire subscriber-sporing i SSE + on_run_done i detached finally
- `973e2c88` 2026-06-19 — **push** · proaktiv/reminder-notifikationer -> mobil-push via notification_bridge
- `504c2929` 2026-06-19 — **account** · Google-link-indikator + users.json rolle-fallback + device-pairing (WIP)
- `3f4b4382` 2026-06-19 — **presence** · device_presence-kerne — record_ping/rank/prune/summary
- `3eb80435` 2026-06-19 — **presence** · desktop_notifications-koe (enqueue/drain/prune)
- `89d12187` 2026-06-19 — **presence** · proactive_router — bedste enhed + eskalering + ack + fallback
- `4907cf00` 2026-06-19 — **presence** · device_awareness_enabled killswitch + push_dispatcher ruter via proactive_router
- `87a2c3d4` 2026-06-19 — **presence** · /presence/ping + /notifications/{pending,ack} endpoints
- `9586abf5` 2026-06-19 — **presence** · device-presence linje i Jarvis prompt-tail (killswitch-gatet)
- `8befb6d4` 2026-06-19 — **desk** · device-presence — powerMonitor+notify:show bro, presence-ping (appId) + proaktiv notif-poll
- `646c1496` 2026-06-19 — **tools** · send_push_notification — Jarvis kan proaktivt naa brugeren paa companion
- `564d3f4b` 2026-06-20 — **api** · /mobile/latest + /mobile/download endpoints for auto-updater
- `0677f70a` 2026-06-20 — **api** · registrér mobile_update-router
- `29384d46` 2026-06-20 — **desk** · takeover-banner ved cross-device-aktivitet på åben session (mobil→desktop)
- `bf524cf5` 2026-06-20 — **desk** · app-niveau takeover-notits (virker i Code/Cowork-fanen)
- `f18c8c9b` 2026-06-20 — **desk** · live takeover-panel i Code/Cowork — følger cross-device-run live (tokens+spinner)
- `9cda93a3` 2026-06-20 — **desk** · code mode = native cross-device liveness (ikke popup)
- `4b51fcdf` 2026-06-20 — **desk** · code mode cross-device — sekund-tæller + takeover-banner
- `ee6304dc` 2026-06-20 — **desk** · code mode — miljø-felt opdaterer ved mobil-run + persistent liveness
- `3b52057d` 2026-06-20 — **geo** · server presence-lokation + 5 native geo-tools til Jarvis (Del 3+4)
- `8621668d` 2026-06-20 — **desk** · geolocation — opt-in lokation i presence + LocationSection (Del 2)
- `8cde73c2` 2026-06-20 — **teams** · SQLite-tabeller + chat_sessions.team_id-kolonne (Fase 1 task 1)
- `339884ab` 2026-06-20 — **teams** · team_dir() — git-init'et delt workspace pr. team (Fase 1 task 3)
- `e28e5567` 2026-06-20 — **teams** · data-lag — create_team + medlemskab + rolle-opslag + rolle-gates (Fase 1 task 2+6)
- `65d12aa0` 2026-06-20 — **teams** · scoping-regel B — team-medlemmer ser delte sessioner (privat urørt) (Fase 1 task 4)
- `08bc9f00` 2026-06-20 — **teams** · cross_user_share_guard tillader cross-user i team-sessioner (Fase 1 task 5)
- `3b27abb2` 2026-06-20 — **teams** · serverside rolle-håndhævelse — can_admin + remove_member tests (Fase 1 task 6)
- `600191f3` 2026-06-20 — **teams** · invite-token-livscyklus — create/get/accept_invite (Fase 2a task 7)
- `04cc5136` 2026-06-20 — **teams** · Jarvis-tools team_tools.py — create/list/invite exec-wrappers (Fase 2a task 8)
- `a99c82ae` 2026-06-20 — **teams** · registrér create_team/list_teams/invite_to_team (schema+handlers+7 governance-steder) (Fase 2a task 9)
- `0bcc14d4` 2026-06-20 — **teams** · Fase 2b — @mention-parser + auto-commit-hook + invite-levering
- `aca55dc6` 2026-06-20 — **teams** · REST-API (Fase 3a) — GET/POST teams, members, invite, accept, kick
- `8e0b6c5e` 2026-06-20 — **desk** · Teams-sidebar (Fase 3b) — lister/opretter/inviterer teams
- `5102240e` 2026-06-20 — **teams** · session↔team-binding (Fase 2c kerne) — opret+list delte team-sessioner
- `d69f77c6` 2026-06-20 — **desk** · team-sessioner i sidebar (Fase 2c/3b) — opret+åbn delt team-chat
- `ea5858b6` 2026-06-21 — **teams** · pull-baseret invite-levering — GET /invites + list_pending_invites_for
- `0ee39ced` 2026-06-21 — **desk** · pending-invite-kort i Teams-sidebar (pull-baseret levering)
- `8ccd3c1d` 2026-06-21 — **teams** · auto-opret default 'Team-chat'-session ved team-oprettelse
- `3bb939cf` 2026-06-21 — **notif** · Phase 1 — expanded device_presence.rank() med registrerede enheder
- `14b84762` 2026-06-21 — **notif** · Phase 2 — notification_router.py (policy-lag) + preferences
- `d1e6ba57` 2026-06-21 — **notif** · Phase 3 — recurring_tasks channel-felt + set_recurring_channel-tool
- `845e6a91` 2026-06-21 — **notif** · Phase 4 (backend) — get/set_notification_preferences tools + REST
- `9e067096` 2026-06-21 — **desk** · Phase 4 UI — Notifikationer-sektion i settings (kanal per type + quiet hours)
- `e25d4026` 2026-06-21 — **notif** · proaktivt indhold (morgenbrief/reach_out) følger nu bruger-kanalvalg
- `189ec8d2` 2026-06-21 — **auth** · effektiv-owner-bypass for container-sudo (B) — owner kan sudo på egen maskine
- `ecc58cf2` 2026-06-21 — **security** · identity-guard & abuse-fundament (spec 2026-06-21, Fase 1+2)
- `731f618f` 2026-06-21 — **security** · abuse-monitor — prompt-injection, rate-limit, notifikationer (spec Fase 3)
- `e4f9ed71` 2026-06-21 — **security** · !unlock-recovery (TOTP) + audit på override-aktivering (spec §12.2, §9)
- `745f2e67` 2026-06-21 — **tools** · operator_bash_session (open/run/close/list) — persistent-feel operator-shell
- `1af7df2b` 2026-06-21 — **gates** · GateKernel-kerne (unified-gate Fase 0.1 + A.1-A.4)
- `2cea193e` 2026-06-21 — **gates** · eval/paritets-harness (unified-gate Task 0.2)
- `33238194` 2026-06-21 — **gates** · TruthGate-cluster-adaptere (unified-gate A.5)
- `65dceca0` 2026-06-21 — **gates** · A.6 — wire GateKernel shadow ind i visible_runs (observabilitet, nul adfærdsændring)
- `ea3c1b11` 2026-06-21 — **central** · boundary-capture (§10) — safe_call fanger alt, kaster aldrig
- `d39fb7e3` 2026-06-21 — **central** · trace-sink (§3.2/§7) — trådsikker ring-buffer nøglet på run_id
- `5e64c54f` 2026-06-21 — **central** · live-switches m. sikkerheds-invariant (§11.3) + CircuitBreaker + drift-flag
- `64377a8c` 2026-06-21 — **central** · Central-facade — observe + decide + register + singleton (§3.1/§9/§11)
- `cb2c7200` 2026-06-21 — **central** · fit-pass-katalog (§13.2) — deklarativ nerve→cluster/klasse/mekanisme/fit
- `b7208166` 2026-06-21 — **gates** · cluster B Fase 1 — unified TruthGate + offline-paritet (additivt)
- `e25b8d57` 2026-06-21 — **central** · Truth-cluster Fase 2a — første ægte cluster-wiring (trace + kill-switch)
- `23fbf273` 2026-06-21 — **truth** · TruthGate v2 ren funktion (Fase A) — detektor+evidens+severity+LLM-dommer
- `73d5b2b9` 2026-06-21 — **truth** · v2 pre-done hook i visible_runs (Fase C1) — bag eksplicit flag, default OFF
- `eb617491` 2026-06-21 — **truth** · log v2-blok entydigt (run_id + decision + severity) for verifikation

**Rettelser**

- `ae420231` 2026-06-15 — **robustness** · hallucination_guard NoUserContext-fallback + session_topics NULL-hærdning
- `ba292444` 2026-06-15 — **model** · read_model_config viser AKTIV per-run model, ikke kun global default
- `f43d6d83` 2026-06-15 — **temperature** · Site 4 bruger aktiv brugers workspace, ikke hardcodet 'default'
- `8e55cc4b` 2026-06-15 — **desk** · footer viser aktiv run-model (ikke hardcoded default)
- `209686a2` 2026-06-15 — **app-control** · tilbyd request_app_action i chat+code mode (manglede i tool-scope)
- `0f148cec` 2026-06-15 — **desk** · file-tree surfacer fejl + tom-tilstand (var tavst tomt = 'viser ingen filer')
- `b7b68f7a` 2026-06-15 — **desk** · /chat/tree + /chat/file offloader blokerende fs/bro til to_thread (--workers 1 frys-fælde)
- `9a7587b4` 2026-06-15 — **desk** · file-tree rolle-scopede roots + lokal "Tom mappe" rod-årsag
- `bc70d1b3` 2026-06-15 — **visible** · GLM/små-vindue "intet svar" = prompt over modellens kontekstvindue
- `0cfcf867` 2026-06-15 — **visible** · konservativt token-estimat (÷3) i prompt-trim — GLM trimmede ikke
- `4bfcc05a` 2026-06-15 — **gut** · wire forældreløs gut-skrive-sti til run-livscyklus
- `6df26e74` 2026-06-15 — **brain-daemon** · retry + provider-note på _call_local_ollama (ejer-valg)
- `4c79e9dd` 2026-06-15 — **prompt** · Stage 1 — drop falskt 'epistemic_layers=empty'-dødssignal fra selvmodel
- `7db00213` 2026-06-15 — **jobs** · prune-on-save — kap jobs_queue.json bloat (48MB→bounded)
- `7823067a` 2026-06-16 — **chat** · tråd request-uid til operator-bro i code-mode workstation-routes
- `c5e16158` 2026-06-16 — **discord** · Spor B — annoncér brugerbesked som channel.chat_message_appended
- `14887f9c` 2026-06-16 — **claim-scanner** · shadow claims promoveret til blocking — narrative påstande blokeres nu
- `dca6eb65` 2026-06-16 — **desk-stream** · terminal-garanti når legacy-strømmen BLOKERER (D2-leak hang)
- `587ea7e9` 2026-06-16 — **visible** · stream afbryd-noten + provider-400-body live (ikke kun ved app-genstart)
- `ba53c593` 2026-06-16 — **desk** · stop model-context refetch-loop — primitive deps i Composer
- `d0712372` 2026-06-16 — **open_ui_panel** · rettelser efter Bjørns review — import-fix + effRoot deklaration
- `9e631f5a` 2026-06-16 — **open_ui_panel** · ret alle review-fund — APP_CONTROL_TOOL_HANDLERS, scope-type, coworkApi syntax, test props
- `9fa05c4a` 2026-06-16 — **open_ui_panel** · genskab close-handler + fil-vs-note-heuristik i UiPanelWatcher
- `be52a80c` 2026-06-17 — **visible** · eskalerende synthese-pause — stop tavs tool-spiral, narrér undervejs
- `26a10649` 2026-06-17 — **visible** · keepalive-heartbeat under prompt-assembly — stop ~20s cutoff
- `c3850d26` 2026-06-17 — **cadence** · tidsbind producers — én hængende fryser ikke hele cadence-loopet
- `b873d867` 2026-06-17 — **desk** · file-tree scroll (min-height:0) + grå tematiseret venstre-panel-scrollbar
- `fd30886e` 2026-06-17 — **desk** · mode-switch race + UI-batch (gap, labels, miljø-felt, save-rail)
- `01c30930` 2026-06-17 — **desk** · code-mode greeting bruger GreetingHero (plugins + disclaimer-link)
- `4d70d2c0` 2026-06-17 — **auth** · Google-login start/result public + bevar rolle ved link
- `77062ba1` 2026-06-17 — **account** · persistent Google-forbundet-indikator (desktop glemte login efter restart)
- `bcf8e71f` 2026-06-18 — **account** · /account/me rolle-fallback til users.json (owner vist som member)
- `a2ec0202` 2026-06-18 — **visible_runs** · ryd zombie active_run-slot ved terminal DB-status
- `1ecc906f` 2026-06-18 — **visible_runs** · selv-hel zombie active-run (desktop-aktivitetsprikker hang)
- `b9bbe835` 2026-06-18 — **liveness** · afled active-runs fra run_follow-bufferen (paalidelig for detached A3-runs)
- `313baaa6` 2026-06-19 — **runs** · single-flight-guard pr. session i server-autoritativ detached-sti
- `b7cf3992` 2026-06-19 — **runs** · create-grace i is_live/live_run_ids saa /active-runs ikke flakker under sync assembly
- `1b736f2c` 2026-06-19 — **desk** · reload aaben transcript naar fulgt run afslutter (cross-device)
- `8d583be3` 2026-06-19 — **runs** · atomisk claim_or_create + stale-cap mod rapid-resend hard-block
- `156acdcf` 2026-06-19 — **runs** · ryd global active-run-slot naar detached run er done
- `634885a6` 2026-06-19 — **desk** · hoist presence-ping + notif-poll til altid-monteret PresenceHost
- `b9dd43c5` 2026-06-19 — **presence** · prompt-awareness uid = session-ejer (ikke tom current_user_id)
- `bf1c5cca` 2026-06-19 — **bootstrap** · workspace file health guard — stub detection + shrinkage alarm
- `aad6248e` 2026-06-20 — **presence** · BUG1 — foreground dominerer recency + frisk-ping-gate (enhedsskift fulgte ikke med)
- `427d2a6f` 2026-06-20 — **memory** · memory_upsert skrev til shared/MEMORY.md i stedet for brugerens workspace
- `e57713ee` 2026-06-20 — **desk** · garanteret transcript-refresh ved cross-device-aktivitet (mobil→desktop realtime)
- `8b923287` 2026-06-20 — **desk** · backgroundThrottling=false — den ÆGTE rod til mobil→desktop realtime
- `087a1d4d` 2026-06-20 — **desk** · disable Chromium timer-throttling-switches for cross-device realtime
- `6449ead3` 2026-06-20 — **desk** · takeover-panel poller getSession (race-sikker transcript) + follow
- `abfef04e` 2026-06-20 — **desk** · code-mode takeover-panel = Chat mode 1:1 (6s-latch + liveness + token-tæller)
- `245863e4` 2026-06-20 — **desk** · miljø-felt fanger cross-device tools via event-akkumulator
- `cb1a40ec` 2026-06-20 — raise tool result fallback limit 1500→8000 + smart truncation
- `3f5ab522` 2026-06-20 — fallback to FCM-blast when best presence score is 0.0
- `45eea82f` 2026-06-20 — add title to team_invite payload + notification block in FCM
- `b484595e` 2026-06-20 — raise follow-up tool result truncation 2500→8000
- `36698639` 2026-06-21 — **desk** · teams-knapper virkede ikke — Electron mangler window.prompt
- `7190e899` 2026-06-21 — **operator** · member operator-tools afvist i code mode (tool_scope CtxVar tabt)
- `f0d34ab1` 2026-06-21 — **auth** · wire !override ind i webchat/desk-stien (chat_stream_v2) — owner kill-switch virker nu remote
- `9e499791` 2026-06-21 — **auth** · forny owner-override pr. besked (5-min rullende) — fix 'virker én gang så blok'
- `d70c36e1` 2026-06-21 — **auth** · forny owner-override pr. tool-runde fra run-kontekst — fix '3-4 operator-kald så tool_not_permitted'
- `9986c3f1` 2026-06-21 — **auth** · re-assertér session_id i executor-konteksten så override ses af tool-gaten
- `a9aa2c5f` 2026-06-21 — **auth** · re-assertér session_id+scope ved BEGGE executor-sites — override synlig i agentisk loop (round 2+)
- `de6cfee1` 2026-06-21 — **auth** · wire !override ind i v1 /chat/stream (mobil) — fuld kill-switch-dækning
- `575c2383` 2026-06-21 — **desk** · Mac — stop occlusion-throttle (spinner+streaming), skru tray-ikon ned (0.2.91)
- `b023197a` 2026-06-21 — **gates** · GateKernel._default_emit brugte forkert event_bus-import → intet event
- `8da31205` 2026-06-21 — **visible** · resurrectér død _post_process-pipeline (generator-i-tråd-bug)
- `9a07482e` 2026-06-21 — **visible** · parse prosa-emitterede tool-kald (deepseek-v4-flash narrer kald)
- `e61e77b2` 2026-06-21 — **visible** · prosa-tool-call-redning også i followup-runder
- `3c1bc979` 2026-06-21 — **sse-v2** · aclose legacy-generator → _post_process/truth-gates kører for follow-runs
- `ab9d22bb` 2026-06-21 — **visible** · _post_process ydre except logger nu (slugte FØR stille)
- `6ebe9222` 2026-06-21 — **visible** · nonlocal visible_output_text — fjern UnboundLocalError der dræbte _post_process
- `9affa42e` 2026-06-21 — **truth** · v2 output-evidens kræver at citeret blok matcher ÆGTE tool-resultat
- `f952c2a2` 2026-06-21 — **truth** · v2-hook robust mod ubundet _followup_exchanges (single-pass-svar)
- `29088dcf` 2026-06-21 — **truth** · v2-detektor robust — eksekverings-signal + kodeblok = påstået output
- `9b8e4862` 2026-06-21 — **chat** · midlertidig bro — substituér små gpt-4* Copilot-modeller til global stor model
- `6e905958` 2026-06-21 — **visible** · prosa-tool-kald får ÆGTE id — tom id brækkede followup på ALLE providers

**Omstrukturering**

- `0bfbf7e1` 2026-06-15 — **desk** · Composer bruger PermissionContext + delte composerPrefs-nøgler
- `122c7cdc` 2026-06-15 — **db** · udskil autonomy_proposals til db_autonomy.py (Boy Scout)
- `e03b4fd7` 2026-06-15 — **db** · udskil private_brain_records til db_private_brain.py (Boy Scout)
- `3d3272f6` 2026-06-15 — **db** · udskil scheduled_tasks til db_scheduled_tasks.py (Boy Scout)
- `b5b09c85` 2026-06-20 — **geo** · kortere prompt-label for lokation (hybrid Del 1 finpudsning)
- `c23fbf8b` 2026-06-21 — **notif** · Phase 5 — fjern proactive_router, inline i notification_router
- `71f9ef7e` 2026-06-21 — **desk** · ÉN settings-flade — konsolidér alt i cowork-Indstillinger (0.2.90)
- `c074a428` 2026-06-21 — **gates** · fjern skrøbelig A.6 live-shadow — paritet måles offline via gate_eval

**Ydelse**

- `46c78ba4` 2026-06-17 — **assembly** · warm cognitive_state i cache-warmer + fjern firstpass-trace

**Tests**

- `580f3734` 2026-06-19 — **runs** · multi-klient drop+resubscribe+404 harness (A3-modgift); golden-frame ON==OFF verificeret
- `38eb3d8e` 2026-06-21 — **central** · ende-til-ende-smoke — decide+observe traces på samme run_id
- `8720cb42` 2026-06-21 — **truth** · v2 dæknings-fixtures + paritet — Bjørns git-log-konfab = RED (Fase B)

**Dokumentation**

- `a23c996e` 2026-06-15 — backlog — markér codex-adapter + diagnosis-gate som lukket (15. jun)
- `a3201c1d` 2026-06-15 — spec for app-self-control — Jarvis foreslår mode/permission-skift indefra desk (med samtykke)
- `5eb7116a` 2026-06-15 — implementerings-plan for app-self-control (10 TDD-tasks)
- `52e9befb` 2026-06-15 — spec for tool-chip berigelse + pæne navne + luk-panel (jarvis-desk)
- `63505f5f` 2026-06-15 — implementerings-plan for tool-chips + pæne navne + luk-panel (9 TDD-tasks)
- `c3dc1e03` 2026-06-15 — **spec** · user management design — DB migration, CRUD functions, GDPR, email verification, quota tiers
- `dd2dd416` 2026-06-15 — implementerings-plan for User Management (fase A-E, hele spec'en)
- `c815979c` 2026-06-15 — user-management plan — API-nøgle-livscyklus + add_user (pre-verificeret), Bjørns tilføjelser
- `dd3bee9f` 2026-06-15 — file-tree-styring feature draft (Bjørns design, kø efter user-mgmt C + F/H)
- `eb9a5374` 2026-06-15 — backlog — F (generalized-learning capture-wiring) lukket
- `22aa52ac` 2026-06-15 — file-tree-styring spec godkendt + designvalg låst
- `dc1c9393` 2026-06-15 — **spec** · bootstrap sequence design — first chat flow for new users
- `9355e219` 2026-06-15 — **spec** · bootstrap sequence v1.1 — Discord-sikkerhed, bootstrap_completed, edge cases, tests
- `b94270cf` 2026-06-15 — **spec** · cowork command center — Mission Control + Settings, app navigation, comparison with Claude/Codex Desktop
- `736a5d12` 2026-06-15 — cowork command center Plan 1 (foundation — to-zone + Account)
- `3cf674b0` 2026-06-15 — cowork command center Plan 2 (interaktiv todos)
- `40f1045e` 2026-06-15 — cowork command center Plan 2b (todo TTL + pause)
- `fd4acc93` 2026-06-15 — cowork command center Plan 3 (kvote-sektion)
- `699a83a6` 2026-06-15 — kognitiv liveness-audit (15. jun) — verificeret mod live runtime
- `a34dcd83` 2026-06-15 — nådig-glemsel & lærings-modning design (graceful forgetting)
- `51abda16` 2026-06-16 — cognitive-cartography implementerings-plan (read-only hjernekort)
- `4875d60e` 2026-06-16 — **spec** · plugin catalog design — Google-pakke, GitHub, Superpowers, Browser, Build Web Apps, Computer Use
- `b0abb324` 2026-06-16 — **spec** · connectors/marketplace design — cowork-menu i eksisterende sidebar, marketplace-zone, greeting-widget, GitHub v1
- `c2ce2495` 2026-06-16 — **spec** · tilføj fuld connector-katalog-tabel (Codex-verificeret + Jarvis' egne)
- `a26b930c` 2026-06-16 — **spec** · kritisk review — token-renew, provider-revoke, scope-transparens, egne MCP-servere, UX-delight
- `75e70194` 2026-06-16 — **spec** · §10H cascade-revoke connector-tokens ved bruger-sletning (Jarvis review-catch) + afklar OAuth-per-konto-isolation
- `7a880b54` 2026-06-17 — **analyse** · korrektur + validering af Jarvis' brugerperspektiv-analyse
- `183f2bfb` 2026-06-17 — **deploy** · opgradering-uden-datatab-sektion (spec §6.3 + §14.5)
- `b5cc391f` 2026-06-17 — **spec** · opdater companion-spec med research + dine krav (liveness, camera, voice, GDPR, chatview, composer)
- `f6283523` 2026-06-17 — **spec** · tilføj user-expectations research + mobile-specific features (baggrund, chatboble, save rail, settings, auto-updater)
- `30a72fb5` 2026-06-17 — **spec** · tilføj 31 kritiske review-punkter (edge cases, sikkerhed, Android-teknik, test, UX, roadmap, permissions)
- `7726b8a0` 2026-06-17 — **spec** · tilfaj proaktive kanaler, source awareness, Discord som egen kanal, intelligent device awareness
- `5cf1e81c` 2026-06-17 — **spec** · tilføj visual design (fancy uden overdrevet) + background run notifications + routing robustness
- `b9047ae5` 2026-06-17 — **spec** · tilføj Phase 6 — Teams & Multi-User (team-admin, member, permissions, team-chats, workspace)
- `e2e7f324` 2026-06-18 — **spec** · V2 companion vision — user expectations, mobile features, visual design, device awareness, teams, technical architecture
- `72bd2781` 2026-06-18 — **spec** · plugin permission levels design — 4 niveauer per plugin (Read/Modify/Admin/Full Control)
- `c5fc94cf` 2026-06-19 — **spec** · mobile push-notifikationer (FCM data-only) — V2 delprojekt 1
- `16f1bbe6` 2026-06-19 — **spec** · self-review-rettelser paa push-spec — suppression-signal konkretiseret
- `13a9a45f` 2026-06-19 — **plan** · implementerings-plan for mobile push-notifikationer (FCM)
- `04aadaf4` 2026-06-19 — **spec** · visuelt design-sprog (V2 delprojekt 2, hele §3)
- `cc201703` 2026-06-19 — **spec** · visuelt loeft scopet til mobil-only + bevar al funktionalitet
- `251026cd` 2026-06-19 — **spec** · self-review-rettelser paa visuelt-loeft-spec
- `b083683a` 2026-06-19 — **spec** · visuelt loeft bruger react-native-svg (1:1 mockup-gradienter)
- `0c4131ae` 2026-06-19 — **plan** · implementeringsplan for mobil visuelt loeft (8 tasks, §3)
- `54670d95` 2026-06-19 — **spec** · intelligent device awareness (V2 delprojekt 3)
- `b1eca13f` 2026-06-19 — **plan** · device awareness implementeringsplan (15 tasks, 9 faser)
- `83b05e8d` 2026-06-19 — **spec** · mobil session-panel live-status + Save Rail mini (delprojekt A+B)
- `2c204882` 2026-06-19 — **plan** · mobil session-panel live-status + Save Rail (9 tasks, 4 faser)
- `46370b24` 2026-06-20 — **spec** · mobil auto-updater design (V2 §2, delprojekt C)
- `0a2bdf35` 2026-06-20 — **plan** · mobil auto-updater implementeringsplan (V2 §2, delprojekt C)
- `c2c0857d` 2026-06-20 — **spec** · mobil chatboble Android Bubbles API design (V2 §2, delprojekt D)
- `f07ff720` 2026-06-20 — **plan** · mobil chatboble implementeringsplan (V2 §2, delprojekt D)
- `5a0c0c7a` 2026-06-20 — **spec** · mobil Direct Reply statusbar-svar design (FEATURE 3, pivot fra boble)
- `90690582` 2026-06-20 — **spec** · Teams design — delte sessioner + team-git-workspace (Discord-erstatning)
- `7860b7a0` 2026-06-20 — **spec** · Teams — fold Jarvis' review ind + session-list UX-beslutning
- `daafefff` 2026-06-20 — **plan** · Teams implementeringsplan — Fase 1 fuldt TDD-detaljeret, Fase 2-3 outline
- `eebad945` 2026-06-20 — **plan** · Teams Fase 2a leveret — marker i plan
- `3e564fe8` 2026-06-20 — note to Claude — mobile team_invite, QR-scan, teams buttons issues
- `88d2e6b5` 2026-06-21 — gate-audit (26 gates → 7 clusters, komplet) + unified-gate-arkitektur-design
- `64b87d29` 2026-06-21 — **spec** · unified-gate — tilføj §6 Tests, §7 Edge cases, §9 Self-review (efter Bjørn pressede)
- `f40d97f6` 2026-06-21 — **spec** · unified-gate §7b Sikkerhed — fail-CLOSED for sikkerheds-gates (rettet hul)
- `e36304b9` 2026-06-21 — **plan** · unified-gate implementeringsplan — Fase 0 (måling) → A (GateKernel-shim) → B-H (cluster-konsolidering)
- `229cd92f` 2026-06-21 — **spec** · unified-gate §7c failure-semantik — ingen take-over, asymmetrisk multi-fail, læring som offline-forslag (Bjørns spørgsmål)
- `042ec67b` 2026-06-21 — **central** · designspec for Den Intelligente Central
- `4aa06802` 2026-06-21 — **central** · fejl-/debug-catcher som førsteklasses, bygget fra starten
- `7a7dd167` 2026-06-21 — **central** · implementeringsplan for fundament (§13.1+§13.2), 11 TDD-tasks
- `6cf5376b` 2026-06-21 — **central** · eksplicit afviklings-kontrakt pr. cluster (§13 step 3)
- `6e09c838` 2026-06-21 — **central** · fit-pass-rapport for loop+truth — resten afventer cluster-planer
- `7222886a` 2026-06-21 — **truth** · TruthGate Fase 2 designspec — evidens-baseret pre-done konfabulations-gate
- `bc2cec00` 2026-06-21 — **truth** · implementeringsplan TruthGate Fase 2 (A bygge / B paritet / C pre-done flip)

**Vedligehold**

- `a0b990c3` 2026-06-15 — **liveness** · luk 3 løse ender — deprecér un-integrerede ports + brain-daemon fail-fast
- `db93c8b2` 2026-06-17 — **visible** · fjern firstpass-trace debug-logging (diagnose færdig)
- `f6f2bd67` 2026-06-17 — **desk** · bump version 0.2.34 (fulgte ikke med #2b-commit pga. pre-commit stash)
- `66d005f9` 2026-06-17 — ignore local worktrees
- `583c3d82` 2026-06-17 — **desk** · bump 0.2.59 (Google-login)
- `c4c4649b` 2026-06-19 — **desk** · bump 0.2.70 (device-awareness presence + notif-poll)
- `beef5472` 2026-06-20 — **desk** · fjern debug-tæller, ren 0.2.77 (cross-device realtime virker i chat mode)

**Formatering**

- `50a24e18` 2026-06-15 — **desk** · AppActionCard-styling
- `e485012b` 2026-06-15 — **desk** · cowork zone-rail + account-sektion styling
- `ac8c6cff` 2026-06-15 — **desk** · paused/expired/TTL todo-styling

**Build**

- `c09ecc28` 2026-06-15 — **desk** · bump 0.2.23→0.2.24 — tving dpkg til at udpakke (same-version no-op fix)
- `4d58eb16` 2026-06-16 — **desk** · 0.2.24→0.2.25 — universal mac-build (x64+arm64) for Ventura
- `fa04e63c` 2026-06-16 — **desk** · bump 0.2.25→0.2.26 — connectors/Marketplace v1 (Phase C-E)

**CI**

- `3b40a398` 2026-06-16 — **desk** · tag-trigget release-workflow — bygger Linux+Mac, uploader til GitHub-release
- `2b5ac97c` 2026-06-16 — **desk** · tilføj windows-latest til release-matrix — .exe bygges automatisk

**Tilbagerulning**

- `372a4640` 2026-06-18 — **stream** · A3 detached-route → A1-tee (begge apps fejlede efter hver besked)

**Øvrigt**

- `856ebdb7` 2026-06-15 — **chat** · log provider_choice→eff_provider i v2-stream (diagnosér 'kører ikke ollama')
- `314dbe83` 2026-06-15 — SECURITY: scope search_sessions + search_chat_history til anmodende bruger
- `ebbe0ab9` 2026-06-15 — SECURITY: override må ikke lække session-data (§6.5 kontrol≠data)
- `44b0f676` 2026-06-15 — SECURITY: scope read_chronicles + list_scheduled_tasks til bruger
- `2dfe97bb` 2026-06-16 — **honesty** · mål-script — tæl hvor ofte hvert anti-løgn-lag fyrer
- `24c6775a` 2026-06-16 — connectors/marketplace v1 (GitHub) — bite-size TDD-tasks
- `874db66c` 2026-06-16 — **visible** · firstpass-trace — udpeg hvor visible-run dør efter assembly
- `9ba130a9` 2026-06-16 — **open_ui_panel** · workstation-support med scope-parameter
- `ce4c0ee4` 2026-06-17 — **visible** · genindsæt firstpass-trace m. timing (early-death diagnose)
- `9b64adb9` 2026-06-17 — **jarvis-desktop** · brugerperspektiv-analyse med lovkrav, gap-analyse og implementeringsplan
- `a5a2d03a` 2026-06-17 — **jarvis-desktop** · tilføj test-strategi, edge cases, a11y, i18n, sikkerhed, performance, data residency, brugertyper, error UX og onboarding flow
- `c8efdc33` 2026-06-17 — **jarvis-desktop** · tilføj Jarvis' personlige ønsker (inside-out), login-strategi og prioriteret liste
- `e84f39e5` 2026-06-17 — **jarvis-desktop** · opdater login-sikkerhed — ingen self-service Google-registrering, migration af gamle konti, keychain storage, audit log
- `79d3dab6` 2026-06-17 — **jarvis-desktop** · tilføj 7 identificerede huller — offline, shortcuts, search, OS-notifikationer, backend guide, inkonsistenser
- `66a7a503` 2026-06-17 — **mobile** · design Jarvis companion app
- `e091260f` 2026-06-17 — **mobile** · add Jarvis companion implementation plan
- `44c4315a` 2026-06-17 — **gdpr** · data-sletnings-design (roadmap #2c — design-only)
- `83726992` 2026-06-17 — code-mode git+workstation + dependency-doctor + auto-update
- `0e4d8545` 2026-06-17 — code-mode git+workstation + dependency-doctor + auto-update
- `92ac5333` 2026-06-17 — i18n(desk): ret synlige engelske rester til dansk (§i18n must-have)
- `86bc2388` 2026-06-19 — **mobile** · server-authoritative runs (Stykke A) — A3 gjort rigtigt
- `b5117548` 2026-06-19 — **mobile** · server-authoritative runs — 10 tasks, flag-gatet, multi-klient-test
- `7a2e228f` 2026-06-19 — Merge remote-tracking branch 'origin/main'
- `3ffade5c` 2026-06-19 — Merge remote-tracking branch 'origin/main'
- `76c1d01d` 2026-06-20 — unified proactive notification routing with device awareness + self-review
- `eb2d8b22` 2026-06-20 — update channels — webchat unified, UI in both apps, device-aware auto-routing
- `9b48cf4c` 2026-06-20 — mobile and desktop are separate channels — user can choose per type
- `3ccd0faf` 2026-06-21 — **desk** · 0.2.88 — teams-knapper (window.prompt-fix) + pending-invite-kort
- `bf2fd43d` 2026-06-21 — **desk** · 0.2.89 — Notifikationer-settings (kanal-routing per type + quiet hours)
- `84e21f43` 2026-06-21 — identity guard
- `3552507f` 2026-06-21 — update identity guard with code analysis (§12) + TTL reconciliation
- `77f596cf` 2026-06-21 — add §10 Testing + §11 Edge Cases to identity guard
- `2457f701` 2026-06-21 — override per-session (not cross-device) — per Claude review

### Uge 26 · 22.–28. juni — 147 commits

**Nyt**

- `e537d778` 2026-06-22 — **visible** · genskab Jarvis' indre liv i prompten + halvér token-burn
- `93af1c7d` 2026-06-22 — **visible** · round 2 — Jarvis' egen prompt-review; skær resterende støj, rum ind i [INDRE LIV]
- `f9f7ba9e` 2026-06-22 — **visible+tools** · adfærds-anker i halen + load_more_tools returnerer fuldt skema
- `b9ef6059` 2026-06-22 — **heartbeat** · auto-skip dry primary provider, self-healing resume
- `88c96940` 2026-06-22 — **visible** · round 3 — Jarvis' rækkefølge-review; INDRE LIV først, kondensér støj
- `51dd5a30` 2026-06-22 — **visible** · round 3b — kondensér recall-bundle + merge brain-sektioner (Jarvis #2+#3)
- `b532988b` 2026-06-22 — **truth** · C4 — fjern de gamle post-done effekt-gates (claim/fact/diagnosis)
- `680fba72` 2026-06-22 — **tools** · konfigurerbare tool-resultat-render-lofter (recent 4000→3000)
- `33ce7c6a` 2026-06-22 — **central** · fit-pass Commit/Review/Proactivity → central_catalog (5 clusters kortlagt)
- `d9ddbde7` 2026-06-22 — **central** · fit-pass Memory/Privacy/Auth → central_catalog (alle 8 clusters kortlagt)
- `7374d971` 2026-06-22 — **proactivity** · konfigurerbare tærskler (R2.5 heed/tier + proaktiv dag-cap/cooldown)
- `30f679fa` 2026-06-22 — **central** · Commit-cluster migration steg 1 — decision_gate trace-spore via observe()
- `abeaed16` 2026-06-22 — **central** · Proactivity-cluster migration steg 1 — r2_5_blocking_gate trace-spore
- `6baeed7e` 2026-06-22 — **central** · persistent incident-log + notifikation begge veje (catch → DB + push)
- `5c9e60e1` 2026-06-22 — **central** · Commit-cluster ÆGTE migration — decision_gate routes GENNEM Centralen
- `d8f3671a` 2026-06-22 — **central** · færdiggør Commit-cluster — instrument-nerver gennem Centralen
- `14de2ebb` 2026-06-22 — **central** · Commit-gate GRADERET (grader af blok som Truth — ikke binær/observer)
- `27e12569` 2026-06-22 — **central** · Proactivity-cluster KONSOLIDERET — R2+R2.5 → ÉN graderet gate gennem Centralen
- `56ccadef` 2026-06-22 — **central** · Memory-cluster KONSOLIDERET — promotion-gate GRADERET gennem Centralen
- `590c8c43` 2026-06-22 — **central** · Loop-cluster KONSOLIDERET — agentisk loop-kontrol GRADERET gennem Centralen
- `d7513c73` 2026-06-22 — **central** · Review-cluster KONSOLIDERET — selv-review-vurdering GRADERET gennem Centralen
- `624887a1` 2026-06-22 — **central** · Privacy-cluster 🔒 KONSOLIDERET — cross-user-deling SECURITY fail-closed
- `d627c506` 2026-06-22 — **central** · Auth-cluster 🔒 KONSOLIDERET — tool-access SECURITY fail-closed (SIDSTE cluster)
- `16d19d52` 2026-06-22 — **central** · §7 flag-on-change — aktiv drift-detektion pr. nerve
- `8a54a306` 2026-06-22 — **execution** · Execution-cluster🔒 — smelt 6 spredte tools-gates til ÉN graderet SECURITY-gate
- `886ad53d` 2026-06-22 — **mutation** · Mutation-cluster🔒 — fjern 3-vejs dual-truth + smelt til ÉN graderet gate
- `4be3ff81` 2026-06-22 — **skill** · Skill-Safety-cluster🔒 — scan_skill-beslutninger gennem Centralen (graderet)
- `2c0da37b` 2026-06-22 — **stream** · Stream-cluster — SSE-lanen synlig i Centralen + stall-backstop
- `84e48cd3` 2026-06-22 — **commit** · merge veto_gate ind i commit-clusteret gennem Centralen
- `f3cf8eab` 2026-06-22 — **privacy** · Privacy🔒-merge — outbound-scrubbing synlig i Centralen + korrekt fit
- `3b2ceb81` 2026-06-22 — **auth** · Auth🔒-merge — incoming-security synlig i Centralen (observe-wrappers)
- `859b4ef8` 2026-06-22 — **prompt** · Prompt-cluster Phase 1 — live on/off + trace for prompt-sektioner
- `5168a474` 2026-06-22 — **central** · cluster-level flip on/off (Jarvis' idé)
- `c866c968` 2026-06-22 — **execution** · A1 — wire malware-scan på uploads gennem Centralen (lukker reelt hul)
- `e1991565` 2026-06-22 — **central** · A2-A5 — resterende kategori-A overflade synlig i Centralen (observe)
- `36b68e5c` 2026-06-22 — **central** · kategori-B batch 1 — provider/daemon-fejl synlige i Centralen (observe)
- `ad0090b9` 2026-06-22 — **central** · B-batch 2 — heartbeat-producer-helbred + notifikations-levering synlige
- `f581b1e9` 2026-06-22 — **db** · DB-cluster — observabilitet + flag for jarvis.db (ALDRIG destruktiv)
- `e3181a19` 2026-06-22 — **tools** · Tools-cluster Phase 1 — hvert tool-kald synligt + kategoriseret i Centralen
- `61f8f783` 2026-06-22 — **tools** · Phase 2 — persistent forbrugs-statistik (mest/aldrig) + flag døde tools
- `f6a941c5` 2026-06-22 — **system** · kartografen MELDER til Centralen (system-cluster)
- `3bacfe3a` 2026-06-22 — **system+tools** · kartograf daglig + KUN-notits trust-gate + endpoint-usage-statistik
- `47798e75` 2026-06-22 — **central** · §1 self-helbred — Centralen overvåger sig SELV (+ #5 breaker, #6 escalation)
- `ada129af` 2026-06-22 — **central** · §7 config-drift-nerve — fang declared↔runtime mismatch (8010/8011-buggen)
- `8cdff66e` 2026-06-22 — **central** · #10 autonome runs → Centralen (observe) + #9 is_enabled fail-open
- `23166f72` 2026-06-22 — **central** · #4 eksplicit cluster-prioritet/arbitrage + #8 demokrati-invariant
- `6e733f3f` 2026-06-22 — **connections** · Connections-cluster — forbindelses-livscyklus → Centralen
- `0bdcbc8a` 2026-06-22 — **connections** · fuld fejl-catcher — session-tool-liste, fejl-flag, uautoriseret adgang
- `f729db34` 2026-06-22 — **system** · daemon-Fase-1 — standalone-tråde/silent listeners synlige i Centralen
- `771c145d` 2026-06-22 — **central** · cross-cluster korrelation — én klar linje pr. run_id (orkestrerings-fundament)
- `0bd2a7a6` 2026-06-22 — **central** · Central TODO — prioriteret pollbar huskeliste på tværs af clusters
- `af0741cc` 2026-06-22 — **autonomous** · #3 supervision — vurdér hvert autonomt run (catch løgn/loop/forbindelsesfejl)
- `094eb1c8` 2026-06-22 — **central** · #4 adaptiv læring — deterministisk pr. cluster, akkumulerer overnight
- `af0ffc5f` 2026-06-23 — **central** · agents-cluster — agent-pool/swarm/council synlige i Centralen
- `90284663` 2026-06-23 — **central** · stream-cluster fuld debug — error/cancel synlige i SSE-lanen
- `83ab790e` 2026-06-23 — **central** · prompt-cluster fejl-kanal — sektion-builder-fejl synlige
- `625e0436` 2026-06-23 — **central** · followup-cluster — agentisk loop synlig i Centralen
- `b9a7bf33` 2026-06-23 — **central** · visible-lane provider-fejl synlige — 429/4xx ud af blindzonen
- `2b22eb87` 2026-06-23 — **central** · unified fejl-meddelelses-system — Centralen ejer hvad brugeren ser
- `ffb07a77` 2026-06-23 — **central** · §6 deterministisk læring — rod-årsags-klyngning + reviewbare forslag
- `91f22309` 2026-06-23 — **desk** · klient-rendering af unified fejl-system + virkende X + auto-reconnect (0.2.92)
- `8ad05dd3` 2026-06-23 — **prompt** · #3 skjul brain ved hilsner + #7 semantisk dedup + vag-filter (runde 3)
- `47a75c64` 2026-06-23 — **central** · real-time owner-surface + /central/realtime endpoint (backend)
- `2ffa3407` 2026-06-23 — **desk** · real-time Central-vindue i code mode (owner-only, 0.2.93)
- `66f92312` 2026-06-23 — **central** · anomali-detektor — fang de udefinerede fejl Centralen ikke kender
- `fddf700f` 2026-06-23 — **desk** · Central-panel cluster-grid + anomali-sektion (0.2.94)
- `66eba769` 2026-06-23 — **central** · SSE-stream + nerve-detalje (Lag 5 backend)
- `1d95dc6c` 2026-06-23 — **desk** · Central SSE-live-feed + klikbar nerve-detalje (Lag 5, 0.2.95)
- `452da952` 2026-06-23 — **central** · central_query-tool + medium-notices (Jarvis' spec 2026-06-23)
- `ad2e34ab` 2026-06-23 — **prompt** · udvid tool-katalog med self-styring + operator-tools (Jarvis huskede ingen)
- `e0e9c205` 2026-06-23 — **desk** · ægte context-ring (backend-autoritativ) + compaction-pause som Claude Code
- `bedda2e1` 2026-06-23 — **desk** · milepæl-rail (kapitler) + live auto-update-polling
- `130fa93f` 2026-06-23 — **central** · central_instrument — selv-instrumenterende motor (Jarvis-spec)
- `30734c2c` 2026-06-23 — **central** · observe Jarvis' indre liv — alle MC cognitive-surfaces → Centralen
- `757a597c` 2026-06-23 — **desk** · Jarvis Mind shell — owner-zone i cowork + poll-when-visible
- `35bf1d4d` 2026-06-23 — **central** · Jarvis Mind-hub — Centralen som ÉT samlingspunkt for alt MC viser
- `58f75a2c` 2026-06-23 — **desk** · Jarvis Mind streamer fra Centralen — ét live-vindue (ét ground truth)
- `2b97ee52` 2026-06-23 — **jarvis-mind** · app-header tilbage i Jarvis Mind + hub agency/skills
- `f29b3b91` 2026-06-23 — **central** · provider_health-nerve udvidet (Jarvis-spec) — proaktiv provider-overvågning
- `8d1b59f6` 2026-06-23 — **central** · provider_health daemon-load-spredning (proaktiv cooldown)
- `a3d2fbd0` 2026-06-23 — **central** · live owner-terminal — command-line ind i Centralen
- `8aeaebe6` 2026-06-23 — **desk** · Central HUD-menu 1:1 — JARVIS-design + live terminal (Bjørn godkendte)
- `52ecaff1` 2026-06-23 — **central** · HUD-polish — feed-farver + større tekst + 6 betjenings-funktioner + flag-indikator
- `64e03364` 2026-06-23 — **central** · meningsfuldt feed + lucide-ikoner + anomali-lokation (hvor+hvad)
- `ad46f6a0` 2026-06-23 — **central** · resend-på-tom (kurerer transiente tomme svar) + leak/dump-nerve

**Rettelser**

- `fe28cc67` 2026-06-22 — **truth** · C2 — gate gamle post-done effekt-gates bag _tv2_on (stop dobbelt-blok)
- `296c35c9` 2026-06-22 — **truth** · v2 hård-blokerer opdigtet commit med bøjet verbum ("committede <hash>")
- `75077711` 2026-06-22 — **auth** · gør de 2 utilsigtede fail-opens OBSERVERBARE (trace, ikke stille)
- `9c6c1813` 2026-06-22 — **central** · bryd kaskade-bug i _track_runtime_candidates + fælles fejl-catcher
- `92537bc3` 2026-06-22 — **memory** · genopliv død private_brain-recall-kilde + observerbare gather-fejl
- `9bc02339` 2026-06-22 — **memory** · private_brain-recall søger nu HELE tabellen via SQL (ikke kun recency)
- `8e1e065b` 2026-06-22 — **privacy** · flip cross_user_share registry-load fail-OPEN → fail-CLOSED (Bjørn)
- `8132fdab` 2026-06-22 — **money** · inner_enrichment hamrede betalt deepseek-API hvert ~2s — load-spred + skip
- `6a592664` 2026-06-22 — **memory** · diary-synthesis-tracker kastede TypeError (str merge_count + int)
- `4f47e64e` 2026-06-22 — **prompt** · dræb ledger ×29-dublet — scaffolding tælles ikke som Jarvis' gentagelse
- `4d0fec04` 2026-06-22 — **tools** · Tools-observe som wrapper — fang ALLE exit-stier (også de tidlige fejl-returns)
- `e98cf6aa` 2026-06-22 — **tools** · endpoint rute-snapshot ud af runtime-gaten → kør i API-processen
- `52c6f41d` 2026-06-22 — **connections** · session_activity læser r.session_id (ikke payload)
- `729d459c` 2026-06-23 — **central** · audit-remediation — luk 7 error-blindspots fundet i cluster-revision
- `3da8baf0` 2026-06-23 — **central** · de 3 fail-open sikkerhedshuller er nu LYDE (severe incident, ikke tavse)
- `c85b17f7` 2026-06-23 — **prompt** · ryd Jarvis' prompt-gentagelser — builder-bugs + støj + dubletter
- `262a4641` 2026-06-23 — **prompt** · self-model maskin-id leak #2 — limitations-guard + chokepoint-filter
- `fbec4b04` 2026-06-23 — **prompt** · #2 — filtrér maskin-id fra session_distillation focus-konsolidering
- `ab2c1f5c` 2026-06-23 — **prompt** · #2 ROD — write-guard på personality_vector strengths/mistakes
- `ac0990de` 2026-06-23 — **prompt** · #2 read-time scrubber — historisk maskin-id-garbage ud af continuity
- `0b981863` 2026-06-23 — **prompt** · #3 cos-relevans-floor + #7 MEMORY.md-indholds-tjek (runde 2)
- `9855bec7` 2026-06-23 — **prompt** · #7 ret workspace_dir-import (var fra forkert modul → MEMORY.md-tjek dødt)
- `fe51fd71` 2026-06-23 — **prompt** · #7 kalibrér semantisk dedup-threshold 0.82→0.73 mod ægte data
- `3d33a103` 2026-06-23 — **prompt** · #7 tråd user_id eksplicit → dedup virker i fuld-build (uden kontekst)
- `a208d645` 2026-06-23 — **prompt** · #7 owner-fallback bruger get_owner_discord_id (User har ingen user_id-attr)
- `1d59d920` 2026-06-23 — **prompt** · stemme-JSON-læk + cross-section dedup (chronicle + continuity) runde 4
- `c9bbcf9a` 2026-06-23 — **ci** · desk-release prepare-job opretter release før build-matrix → ingen upload-race
- `77ec61be` 2026-06-23 — **central** · realtime-snapshot kaldte 10s blokerende config_drift-probe pr. 2s-poll
- `df130948` 2026-06-23 — **central** · ollama-lanens provider-fejl var USYNLIGE for Centralen (cut-off-hullet)
- `b4114068` 2026-06-23 — **central** · config-drift læser disk + auto-resolver + dedup (stopper 11-dublet-akkumulation)
- `0e968ad2` 2026-06-23 — **central** · cross-proces trace-tee — runtime-processens fyringer var USYNLIGE i owner-feed
- `0b893bed` 2026-06-23 — **central** · cross-proces feed-TTL 30s→600s — runtime-daemons fyrer på minut-kadence
- `a36859f2` 2026-06-23 — **central** · balanceret feed-fletning — api-volumen sultede runtime ud af owner-vinduet
- `bc99f79b` 2026-06-23 — **central** · bryd self_health selv-forstærknings-loop (severe-alarm avlede sig selv)
- `11101b0f` 2026-06-23 — **privacy** · cross_user_share-guard fejlede ÅBENT — event-familie latent afvist
- `01eeb51f` 2026-06-23 — **central** · stop persistering degraderings-signal som incidents (dual-truth + 3. selv-loop)
- `1e0c1aa7` 2026-06-23 — **truth** · fact_gate-adapter joinede dict-block_reasons → væltede hele truth-decide
- `ed1dca91` 2026-06-23 — **followup** · repaer afkortede tool-call-argumenter → ollama 400 'looks like object' (cut-off-kilde)
- `c2a1e18c` 2026-06-23 — **context** · model-bevidst num_ctx-cap + transcript-headroom (anti-loop akut-bremse)
- `bab866a5` 2026-06-23 — **context** · compaction trigger 200k→130k + async (kæmpe-sessioner sad i loop-zonen)
- `f4b68db9` 2026-06-23 — **context** · bundet transcript-fallback for compacted sessioner (578k→3k)
- `c1763b7d` 2026-06-23 — **central** · én delt stream — Central-felt + Jarvis Mind sultede hinanden
- `bc6afaf4` 2026-06-23 — **jarvis-mind** · sektioner hang på 'Henter' — fetcher-ref + isoleret puls
- `830409f9` 2026-06-23 — **jarvis-mind** · eksplicit modul-cache pr. sektion (delt cache cachede ikke via endpoint)
- `f1a62734` 2026-06-23 — **central** · daemons-kommando cross-proces (daemons kører i runtime, terminal i api)
- `7651f527` 2026-06-23 — **central** · terminal 422 (dobbelt-stringify) + diagnostik-mode + feed-scroll + større clusters
- `82323142` 2026-06-23 — **central** · feed-drop-loop + støj-filter + foldbare clusters + klikbare feed-rækker
- `cd745b36` 2026-06-23 — **central** · runtime tur-integritets-verifikator — fang brækket tur på tværs af ALLE stier+providere
- `e7bf157d` 2026-06-23 — **desk** · svar forsvinder ikke længere — mergeServer dropper kun bro når turen ER færdig (0.3.5)
- `9bdf1ebe` 2026-06-23 — **continuation** · auto-continuation fabrikerede samtykke når Jarvis SPURGTE — handlede uden lov
- `30f84e61` 2026-06-23 — **recall** · hård 4s deadline på multi_signal_recall — CUT-OFF-RODEN (måneder)
- `d40dc847` 2026-06-23 — **assembly** · hård 10s deadline på ALLE phase-futures — den centrale cut-off-kur
- `6aace3f0` 2026-06-23 — **assembly** · globalt 12s-budget på phase-futures — sekventielle faser lagde sig sammen
- `22bbdfaf` 2026-06-23 — **stream** · keepalive-heartbeat under followup-rundens model-vent — provider-agnostisk forsvinde-bug

**Ydelse**

- `e4448677` 2026-06-23 — **prompt** · #7 leksikalsk pre-filter → dræb 15-20s latency fra MEMORY.md-embedding
- `65f79820` 2026-06-23 — **mc** · cache cognitive-architecture-surface (75s TTL) — dræber MC-poll-load
- `b26530ec` 2026-06-23 — **jarvis-mind** · let Sind-payload + TTL-cache pr. sektion (tung Sind/Agentur)

**Tests**

- `05812215` 2026-06-23 — **prompt** · opdater memory_recall-kandidat-tests til #7-filtrene (≥5 ord + mock dedup)

**Dokumentation**

- `01648b13` 2026-06-23 — Jarvis Mind — MC-migrations-dæknings-kontrakt
- `c5886708` 2026-06-23 — opdater Jarvis Mind-kontrakt — load-fix + shell + Sind/Oversigt landet
- `b448e8f4` 2026-06-23 — Jarvis Mind-kontrakt — Central-hub + stream-fra-Centralen landet
- `157fe4ce` 2026-06-23 — **design** · KANONISK Jarvis Mind-design (Bjørn godkendte 1:1) — JARVIS-HUD tokens + mockup

### Uge 27 · 29. juni – 5. juli — 54 commits

**Nyt**

- `d7c2dce8` 2026-06-29 — **central** · silent-cutoff observability — path-tag + recurrence, no more dedup-hiding
- `5a99f64c` 2026-06-29 — **visible_runs** · #1 livscyklus-invariant — en completed run kan ALDRIG ende tavst tom
- `a1a2689e` 2026-06-29 — **streaming** · Fase 0 — fejl-injektions-harness + kill-switch + baseline-tests
- `ff65597a` 2026-06-29 — **streaming** · Fase 1 B11 — typed failure taxonomy + silent-nerve fix + thinking-parse diagnose
- `1a032dd7` 2026-06-29 — **streaming** · Fase 1 4.1+C11+D11 — rund-retry der bevarer turen (bag kill-switch, default OFF)
- `f19973df` 2026-06-29 — **streaming** · Fase 4 I7 — lean agentic-round-prompt (rammer langsomhed/looping)
- `70d66dda` 2026-06-29 — **streaming** · Fase 3 S6 — delt per-provider circuit-breaker + deepseek-failover
- `043f03dd` 2026-06-30 — **central** · intelligent anomaly capture + Jarvis' skrive-adgang
- `55145a6e` 2026-06-30 — **agentic** · DeepSeek #1453 non-thinking rescue + lav agentisk temperatur
- `ec1a64d6` 2026-06-30 — **prompt** · #3 epistemisk afholdenhed + FIX cache-prefix-regression (warmer 9%→100%)
- `3b6a8e62` 2026-06-30 — **agentic** · #4 sænk round-cap 100→30 + synlig runde-progress
- `c5491580` 2026-06-30 — **cache** · per-runde cache-telemetri — gør den agentiske runde-cache målbar
- `eedbf8ce` 2026-06-30 — **cache** · universel per-kald cache-telemetri i _iter_openai_compatible_chat_events

**Rettelser**

- `0e75f2cc` 2026-06-29 — **outreach+heartbeat+assembly** · device-aware outreach, heartbeat token-cap, q3 recall deadline
- `b3eec0fd` 2026-06-29 — **desk** · D1 code-mode dobbelt-finalisering + §10b desk-audit
- `09c68cae` 2026-06-29 — **streaming** · I1-heal — surface message.thinking når content tom (reasoning-model empty-cut)
- `8a17be8a` 2026-06-29 — **streaming** · A11 — hærdet SSE/NDJSON-decoder (split-UTF-8 + malformet JSON dræber ikke streamen)
- `ae1d0976` 2026-06-29 — **streaming** · I2 terminal-frame-garanti — en stream slutter ALDRIG uden message_stop (H1/G6/F11)
- `e8654ef4` 2026-06-29 — **streaming** · Fase 2 nerver H4/H5/H3 — nul lydløse fejl komplet (server-side)
- `6d58c2ee` 2026-06-29 — **streaming** · H5 persist-retry HEAL — svar forsvinder ikke ved reload på forbigående DB-lock
- `04da8f0e` 2026-06-29 — **cross-device** · 3×-svar (1 svar fra 3 kilder) + falsk "takeover" (desk self-abort)
- `9dd32724` 2026-06-29 — **streaming** · DEEP loop-blokering — offload synkron DB-persist af event-loopet (to_thread)
- `e0c516d0` 2026-06-29 — **desk** · auto-scroll re-pin ved layout-ændring — takeover-banner brød scroll (0.3.7)
- `b3c53203` 2026-06-29 — **followup** · ollama 400 'looks like object' — parse arg-strenge til dicts (ikke lad stå)
- `a5307e2a` 2026-06-29 — **stream** · terminal-garanti ved 'run done UDEN message_stop' — desk-stream nulstiller/flytter til mobil
- `b88d1f36` 2026-06-30 — **bridge** · cross-proces operator-dispatch — autonome runs når broen
- `bd537dab` 2026-06-30 — **guard** · read-before-write blokerede oprettelse af NYE filer
- `45756696` 2026-06-30 — **stream** · klient-keepalive ping i content-gap — desk dør ikke på lange runs
- `bd3ef12b` 2026-06-30 — **app-control** · request_app_action virker uanset runde + altid native
- `a5ef9c08` 2026-06-30 — **cognitive** · JSON-normalisér snapshot-sammenligning (tuple/list-mismatch)
- `c3fe19f1` 2026-06-30 — **cutoff** · DEN ægte rod — thinking-svar i reasoning_content tabt → falsk empty_completion
- `7d31afd4` 2026-06-30 — **stream** · DAG-ÉT cutoff-rod — persistér de STREAMEDE bytes, ikke kun result.text
- `b2f2d31f` 2026-06-30 — **cache** · recency-UAFHÆNGIG tool-result-rendering — luk den store cache-breaker
- `54ceefbf` 2026-06-30 — **cache** · genopliv død warmer (tools mangler 'type' → 400) + model-bevidst compaction
- `5a86c5b7` 2026-06-30 — **cache** · hold tools byte-stabilt på agentiske runder (tool_choice=none) — sidste breaker
- `a2df8c70` 2026-06-30 — **desk** · persistér session-stats (tokens/tools) i localStorage — miljø-feltets historik overlever app-genstart
- `c29cb3e3` 2026-06-30 — **runtime** · 5 kritiske bugs fundet via test-suite-audit
- `36e3d0cb` 2026-06-30 — **runtime** · ROLLBACK tool_intent ContextVar → 60s-TTL — fjern cutoff-på-hver-tool-tur
- `c4e29125` 2026-06-30 — **cutoff** · resend-på-tom bruger non-thinking deepseek-chat (#1453-kur)

**Ydelse**

- `701d0268` 2026-06-30 — **cache** · DeepSeek prefix-cache 4-10% → 90%+ på visible-lanen
- `36149a1c` 2026-06-30 — **cognitive** · state-aware cache + heartbeat-warmer + event-bro → 0 LLM i hot-path

**Tests**

- `5c9a714d` 2026-06-30 — fix suite collection — importlib-mode + 2 stale imports

**Dokumentation**

- `385daded` 2026-06-29 — **streaming** · produktions-grade streaming-spec — research-funderet (openai-sdk + codex + audit)
- `461d33d2` 2026-06-29 — **streaming** · self-review + production-readiness review + lean agentic-prompt
- `56b17f85` 2026-06-29 — **streaming** · §10 cross-device (desk↔mobil) edge-dækning
- `87ceba75` 2026-06-29 — **streaming** · §11 adversarisk validering — GO-med-tilføjelser, 6 blokere foldet ind
- `4b03bead` 2026-06-30 — central_query-tool-spec + vesc-protokol-draft (container-lokale)
- `4b950011` 2026-06-30 — **spec** · fuldfør eventbus+cache→central-spec — §18 adaptive learning + §19 intelligens-lag
- `968a0f77` 2026-06-30 — **spec** · §21 council-fund — meta-læring + negativ feedback (de selv-udviklende fundamenter)
- `63eaae0e` 2026-06-30 — **spec** · §22 råds-dom (6 roller) — super-intelligent central: vision, arkitektur, farer+mitigering, sikkerheds-invarianter, M0-M3 roadmap, sci-fi-men-byggbart + 11 konkrete spec-tilføjelser

**Vedligehold**

- `1024b1f6` 2026-06-29 — **desk** · bump 0.3.6 — cross-device 3x/takeover-fix + D1 code-mode dedup

**Øvrigt**

- `be9cedd6` 2026-06-30 — **forgetting** · auto-decay-threshold 0.95 → 0.70
- `30a36be5` 2026-06-30 — **emotion** · repair-mood-labels (repair-lettelse/repair-frustration)
- `b609a435` 2026-06-30 — **visual_memory** · vision-prompts fokuserer på ÆNDRING siden sidst

---

## Juli 2026

*1,158 commits · 2026-07-01 → 2026-07-24*

### Uge 27 · 29. juni – 5. juli — 317 commits

**Nyt**

- `9a7e9256` 2026-07-01 — **central** · M0 — eventbus→central KEYSTONE poll-bro + per-nerve tidsserie
- `bbd49d00` 2026-07-01 — **central** · Fase 1 — central-selv-observation (§23.3 #2 / §24.5)
- `10556a96` 2026-07-01 — **central** · Fase 2 — inner-life liveness EGRESS-FRIT (§23.3 #3 / §24.4)
- `aed49c92` 2026-07-01 — **central** · §25 det aktive lag — flag+lær+notificér+støjfang (Bjørns retning)
- `d5231698` 2026-07-01 — **central** · cache→central-halvdelen (§3.0/§3.2/§3.3) + §26 impl-status
- `540e47c3` 2026-07-01 — **central** · Fase 3 memory-recall → central (§23.3 #4)
- `0236f55e` 2026-07-01 — **central** · Fase 4 tool outcome-loop → central (§23.3 #5)
- `3a353db7` 2026-07-01 — **central** · Fase 5a cost-økologi → central (§23.3 #8)
- `66041c0f` 2026-07-01 — **central** · Fase 5b council deadlock-frekvens → central (§23.3 #7)
- `d97c8b60` 2026-07-01 — **central** · Fase 5c channels + operationel cadence-liveness (§23.3 #10/#13)
- `bcbea4d3` 2026-07-01 — **central** · C vækst-kapacitets-observation (LivingNeuron-data, §23.3 #11)
- `53ad2e9e` 2026-07-01 — **central** · M1 shadow-mode — reaktion i skygge, ingen aktiv ændring (§28)
- `b35ed022` 2026-07-01 — **mcp** · fuld central-adgang + memory-search som MCP-tools (Claude/owner-tooling)
- `619b79f8` 2026-07-01 — **mcp** · fuld native toolbox — central write (command/resolve) + shadow + chat-search
- `040cf8e7` 2026-07-01 — **infra** · infra_sense — Centralen som husets nervesystem (read-only)
- `6216974f` 2026-07-01 — **infra** · SSH dyb-health-pollers + HA-sensorer + disk/svc-vagt (ingen blinde vinkler)
- `7b100eb0` 2026-07-01 — **infra** · pfSense syslog-lytter — realtids-sikkerhedsdetektion (ingen blinde vinkler)
- `5adad6c1` 2026-07-01 — **infra** · syslog liveness-observe — se pfSense-strømmen flyde (også uden angreb)
- `abbdab13` 2026-07-01 — **central** · Sansernes Arkiv → Centralen egress-frit (LivingNeuron-modalitet)
- `4fea2b20` 2026-07-01 — **mcp** · jarvis_central_timeseries — cross-proces tidsserie som MCP-tool
- `b538185f` 2026-07-01 — **desk** · flad simpel cowork-sidebar — hver settings-sektion sit eget punkt (Del A)
- `dd08290f` 2026-07-01 — **mc** · Mission Control kontrolcenter — runs/detalje/agenter/godkendelser/opgaver/planlagt (Del B)
- `dbcc9072` 2026-07-01 — **bridge** · cross-proces bro-presence + ægte fejl-diagnose ved bridge_not_connected (Del C)
- `85336317` 2026-07-01 — **mc** · Cost- + Hændelser-paneler i Mission Control (Del B/Fase 3)
- `02dde904` 2026-07-01 — **mc** · premium/futuristisk design-løft — Mission Control som cowork-stjernen
- `657fe850` 2026-07-01 — **bridge** · owner får operator/bro-tools i mobil chat KUN når desk-bro er paret (Del C)
- `a4f367aa` 2026-07-01 — **central** · System Cartographer → 3 gap-nerver + flag-regler (Jarvis' P1-handlingsordre)
- `d08ae6a5` 2026-07-01 — **central** · LivingNeuron keystone — global_workspace (GWT) → Centralen (første nerve)
- `c81ce5fd` 2026-07-01 — **central** · LivingNeuron Fase A — 5 live-men-blinde indre-liv-signaler → Centralen (egress-fri)
- `6031292c` 2026-07-01 — **central** · PRIVATE_NO_EGRESS-keystone + experiment-rute — Fase A komplet (STEP 0)
- `1c2241f9` 2026-07-01 — **central** · LivingNeuron Fase B — væk emergence + contradiction (frosne detektorer)
- `a0e6cfdd` 2026-07-01 — **central** · LivingNeuron Fase B — væk causal_inference_daemon (Bjørns neuro-symbolsk #1)
- `25ece66b` 2026-07-01 — **central** · LivingNeuron Fase B — boredom_engine synlig for Centralen
- `00570b9b` 2026-07-01 — **central** · LivingNeuron Fase B — procedure_bank feed (surface-only, anti-skrald)
- `b8dcdedb` 2026-07-01 — **central** · LivingNeuron Fase D (graderet) — egress-fri kognitiv autonomi-tier
- `9e1a01f5` 2026-07-01 — **central** · LivingNeuron — wire de 4 load-bearing kognitions-HUBS (den store multiplikator)
- `717b899b` 2026-07-01 — **central** · LivingNeuron felt-krop-planet — somatik/affekt/gut/mood → Centralen (egress-frit)
- `06691b60` 2026-07-01 — **central** · LivingNeuron HUKOMMELSE — jarvis_brain + livscyklus → Centralen (egress-frit)
- `bb01c8e4` 2026-07-01 — **central** · LivingNeuron governance + lange skygge — handlinger + hale → Centralen
- `3ab6a933` 2026-07-02 — **central** · egress-membran hærdet i choke-point + eksekverbar invariant-test (LivingNeuron Fase 1a)
- `e9a08895` 2026-07-02 — **central** · kanonisk egress-fri sink-kontrakt + growth-gauge til delta (LivingNeuron Fase 1b)
- `6702853f` 2026-07-02 — **central** · runtime-målt surface-count + reproducerbar dækning (LivingNeuron Fase 1c)
- `44d9be0c` 2026-07-02 — **central** · causal-graf tier-fordeling + precision-proxy (LivingNeuron Fase 1d)
- `c3b2b674` 2026-07-02 — **central** · hub meta-liveness + signal-korrekthed + cross-proces nerver (LivingNeuron Fase 1e)
- `a2b5a608` 2026-07-02 — **central** · hypotese-dødsmekanisme — de 7 governance-værn FØR Lag 3 (§8)
- `482272ed` 2026-07-02 — **central** · §24.4-læringsmembran + identitets-drift-budget — Bjørns 2 Lag3-beslutninger (§8/§12)
- `d73c1ac1` 2026-07-02 — **central** · Lag 3 governed hypotese-generator (observe-only) — Centralens første læring
- `a9f78ae2` 2026-07-02 — **central** · Lag 3 v2 — DIVERGENS-trigger (samme årsag, modsatte udfald)
- `12ab2b95` 2026-07-02 — **central** · Centralens self-generated hypoteser → Jarvis' awareness (Lag 3 synlig)
- `01a5eeec` 2026-07-02 — **central** · Lag 3 v3 — tvær-modal stance-divergens ('organer uenige i nuet')
- `afdb3e58` 2026-07-02 — **central** · Lag 3 loop-lukning — test hypoteser mod virkelighed → grounded samples
- `9dda151c` 2026-07-02 — **central** · Lag 4 v1 — c→d-lukning (governed gut-bias, shadow-first, reversibel)
- `a757e142` 2026-07-02 — **central** · sprog-pre-start — lexicon-binding + notation + model-frit bevis (Intelligent Central Fase 0)
- `9a599b7e` 2026-07-02 — **central** · udvid Centralens vokabular — 15→36 termer (Bjørn-ceremoni)
- `68103edf` 2026-07-02 — **central** · Fase 0 governance-blokkere (§8.1-8.4) — låser de 5 tråde op
- `396bff71` 2026-07-02 — **central** · Tråd 2 kontekst-komponist — substrat + should_include-switch (Intelligent Central)
- `bb9f2c96` 2026-07-02 — **central** · Tråd 2 LUKKET — kontekst-komponist wired + relevans-substrat
- `db77d3bf` 2026-07-02 — **central** · Tråd 3 — model-fri INFERENS + sprog-vækst (Centralen tænker uden model)
- `78309fc4` 2026-07-02 — **central** · bind Centralens ord-behov til eksisterende termer (Tråd 3)
- `fc832978` 2026-07-02 — **central** · bind de sidste 3 ord-behov (Bjørn-godkendt, provisorisk) — Tråd 3 sprog-dækning
- `e65acc73` 2026-07-02 — **central** · Tråd 4 — Centralen træner sig selv (lokal Markov-model, §6)
- `328d5c53` 2026-07-02 — **central** · Tråd 1 — Centralen kender sit eget hardware (model-meta, §3)
- `c7d9047c` 2026-07-02 — **central** · Tråd 5 — jarvis-brain dybt koblet (scope-hærdet, §7)
- `adc510ce` 2026-07-02 — **central** · Spec B Fase B0 — taksonomi-binding (S1)
- `bc3f59d0` 2026-07-02 — **central** · Spec B Fase B1+B2 — tilstand→notation + pervasivt ræsonnement (S2+S3)
- `a01bb7bb` 2026-07-02 — **central** · Spec B Fase B3+B4 — sprog-vækst-loop + NotationProposal-kontrakt
- `7e999271` 2026-07-02 — **central** · DEN MODIGE DEL — Tråd 2 prompt-relevans eksplorations-arm (Fase 3-4)
- `891056a1` 2026-07-02 — **central** · DEN MODIGE DEL — Tråd 1 routing-præference-lærer (Fase 3-4, shadow)
- `6f616738` 2026-07-02 — **central** · dæknings-audit Niveau 1 — luk hele eventbus-mørket (klassificeret)
- `25cd251b` 2026-07-02 — **central** · Tråd 1 KONSUMENT — visible-routing honorerer lært præference (Fase 4)
- `735f5f4b` 2026-07-02 — **central** · Tråd 1 EKSPLORATIONS-ARM — sample alt-model på autonome runs (Fase 4)
- `c24937ab` 2026-07-02 — **central** · SPEJLET — Centralen kender sig selv (self-model mirror)
- `f6cb41fb` 2026-07-02 — **central** · Spec D omdrejet autoritativ + D1 — Centralen EJER Jarvis' dagsorden
- `5ecf03d3` 2026-07-02 — **central** · Spec D / D2 — ÉN følt tilstand (integrér følelses-organerne)
- `478eadea` 2026-07-02 — **central** · Spec D / D3 — SYNTESEN (MIDTEN): de fem lag bliver ét jeg
- `25244c1b` 2026-07-02 — **central** · Spec D / D4 — MIDTEN BÆRENDE (Jarvis' sind komponeres FRA selv-tilstanden)
- `889eff7e` 2026-07-02 — **presence** · Spec E / E0 — tilstands-kontrakt GET /presence/state (owner-only)
- `ef35ee8f` 2026-07-02 — **desk** · Spec E / E1 — orb-tier tilstedeværelse i operator-feltet (v0.3.13)
- `ff11a9b1` 2026-07-02 — **desk** · operator-felt (orb) + persistent code-storyboard i code mode
- `abd66da7` 2026-07-02 — **central** · network_health — ét fuset netværkssignal + live API-latens
- `9eb25b0f` 2026-07-03 — **infra** · pfSense syslog staleness-vagt — fang hvis syslogd dør igen
- `cb453957` 2026-07-03 — **infra** · pfSense syslogd liveness-vagt — aktivt proces-tjek (ikke tavshed)
- `23b1e025` 2026-07-03 — **infra** · pfSense syslogd auto-heal — vagten genstarter selv den flaky daemon
- `5b9a598c` 2026-07-03 — **central** · producer-novelty-instrumentering (observe-only) — grundlag for saliens-gating
- `4cee5726` 2026-07-03 — **central** · producer-novelty attribution via stack-inferens (fallback)
- `a1a0760b` 2026-07-03 — **central** · LLM-økonomi-spec + daemon_llm cache-synlighed (Bølge 0)
- `3ab73480` 2026-07-03 — **central** · overlevelses-stemmen — Jarvis taler fra Centralen når modellen svigter
- `0170ecf5` 2026-07-03 — **central** · tovejs selv-integration — world-model + inner-salience-arketype + fuld-krop-kort
- `dce8ec28` 2026-07-03 — **central** · Centralens egne hænder — arbitration + adaptation-forbruger + coverage-handling + lag-kontrakt (§11)
- `b77f03b0` 2026-07-03 — **central** · durabel tidsserie — nervesystemet overlever genstart (§6.2)
- `e82b24ff` 2026-07-03 — **central** · form-ændrings-dommeren — kald kun modellen når data ændrer FORM (§6.1c)
- `2343aad7` 2026-07-03 — **agent** · frihed i agentur+råd — prompt+hænder+landing+grund-dommer (spec §C)
- `a689fd40` 2026-07-03 — **central** · forbind sjælen — §7.1 signal-allowlist + §8.1 existence-feel
- `6423dd1b` 2026-07-03 — **central** · sjælen — §8.1 krop + stemning (existence-feel-mønsteret)
- `f01be9cc` 2026-07-03 — **central** · sjælen komplet — §8.1 ømhed/vidne/hukommelse/opmærksomhed/emergens
- `d29edc98` 2026-07-04 — **central** · spec-fuldførelse — §7.2 gate-observe + Bölge 2 form-dækning + convene-fix
- `e2582b7a` 2026-07-04 — **central** · allowlist-batch 6 — 117 signal-families routet egress-frit
- `b69d9753` 2026-07-04 — **central** · bind sanser + hænder — 7 tools egress-frit
- `452edabe` 2026-07-04 — **central** · bind identiteten — 3 core/identity/-filer egress-frit
- `1dd3a324` 2026-07-04 — **central** · bind privat indre (1/2) — tilstand/selv-model/noter/promotion egress-frit
- `8255fa3e` 2026-07-04 — **central** · bind privat indre (2/2) — retained/inner-voice/relation/interplay egress-frit
- `24ea691c` 2026-07-04 — **harness** · total finalize lag 2b — provider-agnostisk tool-fri syntese
- `126f8146` 2026-07-04 — **harness** · lag 3 — result-aware no-progress-detektor → finalize tidligt
- `1563dc5c` 2026-07-04 — **central** · uret + conservation — mål cutoff-spøgelset fremadrettet (Bjørn)
- `eb1c133d` 2026-07-04 — **central** · måling #3+#4 — finish_reason-surfacing + inner-life-ablation
- `e441e552` 2026-07-04 — **cost** · Bølge 3 shadow — samlet LLM-egress-observation (Bjørn: styr på ALLE kald)
- `b9536a8d` 2026-07-04 — **central** · LivingNeuron STITCH-VOICE + PULSE — sømmen der taler + kroppens kort som sans
- `b79bdeb6` 2026-07-04 — **central** · LivingNeuron DIASTOLE + WARDEN — det følte åndedræt + vogteren over muren
- `5025878d` 2026-07-04 — **central** · LivingNeuron MANIFOLD + ONEIRISK sløjfe — de mange muskler + drømme der beviser sig
- `f1f1e785` 2026-07-04 — **central** · LivingNeuron mutation-skridt — DIASTOLE-konsumtion + ONEIRISK grounding (owner samtykkede)
- `1535ece1` 2026-07-04 — **central** · LivingNeuron opfølgninger — dream_trust shadow-muskel + burn-watch + dag-split-beslutning
- `687751ce` 2026-07-04 — **visible** · hollow-promise-værn — fang "lovede handling, kaldte intet værktøj"
- `92919912` 2026-07-04 — **central** · Canonical Error System Fase 0 — udvid ErrorEnvelope + loopback-adapter
- `f6bda249` 2026-07-04 — **central** · Canonical Error System Fase 1 — healer-registret (shadow-first, gated)
- `f462cf69` 2026-07-04 — **desk** · Canonical Error System Fase 2 — desk canonical lag (verificeret, uwiret)
- `6d6ee866` 2026-07-04 — **desk** · Canonical Error System Fase 2 — wire canonical lag ind i UI
- `40f46087` 2026-07-05 — **cost** · luk egress-huller — daemon-lane + 3 direkte-urlopen-sites → samlet observer
- `365aab23` 2026-07-05 — **injection** · InjectionUnit-register + read_injection (Fase 0)
- `6573075d` 2026-07-05 — **injection** · ændrings-detektion is_dirty (signal-delta + max-alder)
- `084c02f9` 2026-07-05 — **injection** · refresh_unit + self-safe refresh_dirty baggrunds-motor
- `f5e3a407` 2026-07-05 — **injection** · per-enhed rollback-flag injection_live (default off)
- `f5fc2f7e` 2026-07-05 — **injection** · kør refresh_dirty pr. cadence-tick (baggrunds-motor live)
- `394f26c3` 2026-07-05 — **injection** · deklarér pilot-enheder rule_conclusions + cognitive_state
- `88d3a2d3` 2026-07-05 — **injection** · rule_conclusions læser injektion når live (rollback-gatet)
- `1ce8b0c6` 2026-07-05 — **injection** · cognitive_state læser injektion når live (rollback-gatet)
- `23526434` 2026-07-05 — **injection** · rigdoms-gate richness_ok (cached ≥ direkte, spec §7)
- `d78cd705` 2026-07-05 — **central-cli** · pakke-skelet + central entry point (L1)
- `ba3f3c04` 2026-07-05 — **central-cli** · config — remote-først + genbrug jc-token (L1)
- `4756574a` 2026-07-05 — **central-cli** · httpx-klient get/post/sse + fejl-kategorier (L1)
- `b2259fec` 2026-07-05 — **central-cli** · kommando-dispatch (read/write/terminal-vokabular) (L1)
- `ecf89044` 2026-07-05 — **central-cli** · feed-model (normalisér event → bounded feed) (L1)
- `8ce3e458` 2026-07-05 — **central-cli** · Rich-renderer (status-panel + generisk JSON) (L1)
- `dc6f4646` 2026-07-05 — **central-cli** · script-runner (one-shot, absorberer jc) (L1)
- `e5afe2d6` 2026-07-05 — **central-cli** · Textual 3-panel TUI + live-poll + command bar (L1)
- `53d2e17f` 2026-07-05 — **central** · governance flag-register — governeret læse/skrive m. confirm på farlige (Backend A1)
- `d0c555db` 2026-07-05 — **central** · /central/governance GET+POST — governeret live governance-styring (Backend A2)
- `bbe7e76b` 2026-07-05 — **central** · audit governance-writes via eventbus + observe (Backend A3, genbrug ikke ny tabel)
- `bad012dd` 2026-07-05 — **central** · /central/healers GET+POST — eksponér healer-styring (Backend A4)
- `c3d6da58` 2026-07-05 — **central** · /central/breakers/{nerve}/reset — operatør-breaker-reset (Backend A5)
- `681e8693` 2026-07-05 — **central-cli** · datasource — fetch+shape alle 7 views mod ægte endpoint-former (HUD-B1)
- `64fbc74b` 2026-07-05 — **central-cli** · HUD-skal — 7-tab-nav + J.A.R.V.I.S-tema + Nerves-tabel + feed (HUD-B2)
- `965394a2` 2026-07-05 — **central-cli** · Overview/Clusters/Incidents(drill)/Diagnostics-views m. ægte data (HUD-B3)
- `dcaae54c` 2026-07-05 — **central-cli** · Healing/Governance-tabs m. writes + confirm-guard (HUD-B4)
- `d4009453` 2026-07-05 — **central-cli** · ombyg HUD-skal til mockup 1:1 (retning C, J.A.R.V.I.S)
- `7521c671` 2026-07-05 — **somatic** · Fase 1 — file awareness daemon + inner-life proprioception
- `794ce8fe` 2026-07-05 — **somatic** · Fase 2 — MC-whisper line i visible_inner_life
- `e61f2f02` 2026-07-05 — **somatic** · Fase 3 — heartbeat-puls line i visible_inner_life
- `8e8d488c` 2026-07-05 — **somatic** · Fase 4 — governance-mutation proprioception + file-awareness eventbus subscriber
- `b19de150` 2026-07-05 — **central-cli** · HUD 1:1 med mockup — element-for-element mod ægte data
- `1a45f5e4` 2026-07-05 — **somatic** · Fase 5 — unified recall + recall-hints line i visible_inner_life
- `be4763ae` 2026-07-05 — **somatic** · Fase 6 — boot-continuity line i visible_inner_life
- `3c935da4` 2026-07-05 — **central-cli** · fungerende central> kommandolinje + Anomalies-fane + markup-injektionsværn
- `d2d336ba` 2026-07-05 — **central-cli** · terminal-feel — altid-aktiv central> prompt + pil-nav + fuld detalje + fuld kommando-output
- `fd4fcf1c` 2026-07-05 — **central** · 'feel' — HUD kan mærke Jarvis' somatiske indre-liv (E: integration)
- `7fd0e14f` 2026-07-05 — **desk** · Central-status-indikator (D) — erstat tunge Central-paneler med kompakt badge
- `6516a69a` 2026-07-05 — **desk** · flyt CentralBadge til header (ikke under operator-feltet)
- `938f59a0` 2026-07-05 — **cli** · Fase 0 — 10-fane Central-CLI-skal (venter-på-wiring placeholders)
- `5e3346fd` 2026-07-05 — **central** · Fase 1 fundament — runtime-proxy (C2) + privat-reducer (§24.4) + absorb-mønster
- `900561c3` 2026-07-05 — **central** · Fase 1 routere — /central/self (selvet, §24.4-reduceret) + /central/agents
- `188401eb` 2026-07-05 — **cli** · Fase 1 CLI — wire Agents (T7) + Mind & Self (T8) mod live-endpoints
- `f8146fee` 2026-07-05 — **central** · Fase A1 cost-timeserie → /central/costs-daily + CLI (absorb cost:daily)
- `33e395b9` 2026-07-05 — **central** · Fase A2/A3/A4 backend — council/scheduled/autonomy absorb + datasource
- `83b091c7` 2026-07-05 — **cli** · Fase A2/A3/A4 CLI — council/scheduled/autonomy i Agents/Runs/Approvals-tabs
- `a12d30c5` 2026-07-05 — **central** · Fase B — wire 32 mørke event-familier (11 egress-OK + 21 trace-only privatlag)
- `1380f86a` 2026-07-05 — **central** · Fase A7 events + A5 memory-health absorb + datasource
- `13a14e9e` 2026-07-05 — **cli** · Fase A5 memory + A7 events i Mind&Self/Diagnostics-tabs
- `e9c0a6e5` 2026-07-05 — **central** · Fase A8 inner-life mind-sektioner (§24.4 reducér-ved-kilden, liveness+count)
- `86e33906` 2026-07-05 — **central** · Fase A6 run-detalje — /central/runs(+/{id}) + Runs-tab drill-in
- `ec8a0e31` 2026-07-05 — **central** · fuld living-mind + experiment/AGI-dækning (37 sektioner, hver egen nerve, §24.4 reducér-ved-kilden)
- `effa1f5c` 2026-07-05 — **central** · wire attention/skills/integrity/experiments/execution (spec Del 1 rest)
- `211b3fb4` 2026-07-05 — **central** · Fase C self-dybde — open_loops/awareness/self_knowledge/counterfactual (§24.4 light)
- `dfb4aae9` 2026-07-05 — **central** · nervesystem — mørke sjæle-signaler (longing/identity_drift/active_sensing/...) som soul-nerver
- `4e946748` 2026-07-05 — **voice** · inner-life stemme — han mærker sine følelser/selv-narrativ/længsel/drift/eksperimenter (tale gennem ham)
- `dc4be54b` 2026-07-05 — **voice** · finitud + overraskelse-linjer (Lag 8 — han mærker sin forgængelighed og sine overraskelser)

**Rettelser**

- `cf0545f4` 2026-07-01 — **cutoff** · DeepSeek 400 'missing field type' på tool_calls — DEN ægte cutoff-rod
- `b0a4b3db` 2026-07-01 — **central** · cache-kold-vagt læser cross-proces fra eventbus (§26.4)
- `5eb8d389` 2026-07-01 — **central** · instrumentér den ÆGTE hot-path recall (associative_recall)
- `2dbbe48c` 2026-07-01 — **central** · fjern watch false-positives der farvede Centralen rød
- `c0ed00f5` 2026-07-01 — **eventbus** · whitelist 'life_projects'-family — daemon crashede latent
- `0d0a4ccf` 2026-07-01 — **infra** · ekskludér multicast/broadcast fra syslog-detektion (false-positive)
- `dd4d1d75` 2026-07-01 — **central** · 3 rygrads-fixes fanget af Centralen selv (operator/eventbus/xproc-tidsserie)
- `a618e581` 2026-07-01 — **central** · re-entrancy-guard bryder publish→self_diagnose→record→publish-rekursion (CPU-brand)
- `0df2f075` 2026-07-01 — **awareness** · reboot/desperation-awareness events persisterer nu (dobbelt latent bug)
- `592ecfbe` 2026-07-02 — **central** · hub-blindzone kun for heartbeat-gatede hubs (undgå idle false-positive-storm)
- `f2473e7e` 2026-07-02 — **central** · governance v3.1 — luk rådets 5 verificerede lækvejе (approved:false → hærdet)
- `e93001ab` 2026-07-02 — **identity** · workspace-health-guard — substantiel formindskelse = WARNING ikke CRITICAL (rød Central)
- `140d6d1c` 2026-07-02 — **central** · Tråd 5 M1-recall inde i eksplicit owner-kontekst
- `ad7c8371` 2026-07-02 — **central** · D1 — læs initiativ-tekst fra 'focus'-feltet (ikke summary/title)
- `a89f94f6` 2026-07-02 — **text** · ord-sikker klipper mod 'død ved tusinde snit' + adoptér på bærende steder
- `cf075ddd` 2026-07-02 — **tools** · bevar HALEN i tool-output (bash/web/grep/JSON) — mod voldsom trunkering
- `3071056a` 2026-07-02 — **desk** · pingServer timeout — stop '74000ms grøn' efter offline (v0.3.12)
- `75ac7a11` 2026-07-02 — **desk** · selv-heling af config ved app-navn-skift (v0.3.15)
- `47d39bcd` 2026-07-02 — **desk** · Miljø-felt — samlet git-funktion i server + computer-mode
- `a9df4008` 2026-07-02 — **code** · workstation git-status (stdout under result) + operator-felt spejler kun indstillinger
- `6ad59785` 2026-07-02 — **central** · network_health debounce — enkelt probe-fejl må ikke give rødt
- `cf072fc3` 2026-07-03 — **central** · brain_link cadence-timeout — fjern ubrugt 31s M1-recall fra hot-path
- `75f2cf76` 2026-07-03 — **central** · brain_link write-cap — også M2-embedding er ~25s → cap pr. tick
- `208f0b7c` 2026-07-03 — **infra** · pfSense-sikkerhed — filtrér interne kilder + downgrade blokeret-scan til warning
- `adb75880` 2026-07-03 — **streaming** · generalisér empty-resend til ALLE thinking-modeller (cutoff-rod)
- `831d21fd` 2026-07-03 — **mobile** · answer_ready-push bærer nu svar-teksten + spring tomme runs over
- `10fa96c7` 2026-07-03 — **mobile** · answer_ready = DATA-ONLY igen (behold skip-tomme) — ret 831d21fd
- `bb982589` 2026-07-03 — **desk** · Google-login blokeret af CSP — default apiBaseUrl + prod-API i connect-src
- `d08a7824` 2026-07-03 — **mobile** · medsend svar-preview som fallback når appens fetchLatest fejler
- `fa41d514` 2026-07-04 — **central** · dø-skjult — tavse fail-open beslutnings-stier synlige
- `8ff0e65a` 2026-07-04 — **central** · dø-skjult — 9 standalone daemon-loops når nu Centralen
- `f9dd1322` 2026-07-04 — **visible** · survival-branden — WAL + ærlig fejl-status (rod: DB-lås-kontention)
- `d71dbc89` 2026-07-04 — **visible** · survival-spam-roden — ærlig tom-note på non-agentisk gren
- `016d530e` 2026-07-04 — **visible** · RUNTIME-cutoff-rod — afbrudt-midt-flugt run ≠ completed
- `c857ce7f` 2026-07-04 — **visible** · keepalive under first-pass tool-exec — dræb CancelledError-roden
- `7844ad33` 2026-07-04 — **sse** · idle-timeout cancellede LEVENDE run-generator — ægte cutoff-rod
- `7a2c4e0b` 2026-07-04 — **harness** · adapter-agnostisk tvungen finalize — runtime garanterer prosa
- `0be949e6` 2026-07-04 — **stream** · DSML-tail-flush — deepseek cutoff-spøgelset (runtime, alle lanes)
- `8aa2792a` 2026-07-04 — **desk** · bevar tool-blokke ved reconnect — svar bang'er ikke løsrevet ind
- `3df67529` 2026-07-04 — **visible** · dræb decision-signal self-poisoning runaway (cutoff+dobbelt i ét)
- `d3aebe1b` 2026-07-04 — **bridge** · stale-WS eviction + presence-bevidst forward (Del C, live-diagnose-drevet)
- `f86d65c1` 2026-07-05 — **stitch** · boot-søm maskerede ægte reboot — prime før puls + cross-proces-latch
- `46dd7be3` 2026-07-05 — **stitch** · latch-adoption på hvert kald (konvergens) — live-test #1 afslørede race
- `e1c768a4` 2026-07-05 — **central-gov** · healer-flags læs fra samme kilde de skrives til + fjern dead record_mutation-dublet
- `03e55b91` 2026-07-05 — **somatic** · ret 2 bugs i Jarvis' file-awareness (bevar hans arbejde)
- `1cd4b2f5` 2026-07-05 — **central-gov** · generative_autonomy læs+skriv mod settings/runtime.json (ikke runtime-state-DB)
- `51bc3a2c` 2026-07-05 — **central** · owner-gate honorerer bearer-token-rolle (Jarvis' 403-diagnose)
- `aba4181e` 2026-07-05 — **central** · intern runtime-surface-rute — proxy-mål for selvet (løser tomt /central/self)
- `3fe1af85` 2026-07-05 — **central** · self-proxy auth — flyt intern rute til /api/internal (auth-fri + loopback-only)
- `966fc010` 2026-07-05 — **central** · JSON-safe intern runtime-surface (self_model/world_model var tomme)
- `67b88c56` 2026-07-05 — **central** · self_model light-summary + proxy-timeout 8s → alle 3 selv-flader live

**Omstrukturering**

- `5f14f71e` 2026-07-01 — **central** · LivingNeuron Fase C — konsolidér 3 duplikat-par (dual-truth væk)
- `5bca29f0` 2026-07-01 — **central** · egress-oprydning — inner-life-observes til ren egress-fri sti
- `96977ed3` 2026-07-02 — **prompt** · udskil rene memory-relevans-scorers fra prompt_contract (Boy Scout)
- `70a8af02` 2026-07-02 — **text** · fej ord-sikker clip_text ud over inner-life-udtryk (mod død ved tusinde snit)

**Tests**

- `a06df551` 2026-07-01 — **cadence** · ret tick_frozen_detectors-test til boredom-nøglen (Fase B)
- `26b08787` 2026-07-01 — **visible_runs** · bind cascade-test til _track_runtime_candidates (ikke EOF)
- `cac94a8b` 2026-07-05 — markér fake execution-secrets som allowlist (detect-secrets false-pos)

**Dokumentation**

- `f0c187ef` 2026-07-01 — **spec** · §23 Central-forbindelses-audit — merged 8-domæne + Jarvis' 5-agent map
- `8f67e110` 2026-07-01 — **spec** · §24 hårdt self-review — 3 adversariske reviews + bindende korrektioner
- `7218308b` 2026-07-01 — **spec** · §27 gap-listens endelige dækning — alle §23.3-systemer dækket/deferred
- `c071a88f` 2026-07-01 — indre-liv→Central wiring-roadmap (11-agent-sweep) + cartograf-handlingsordre
- `c3e6312a` 2026-07-01 — git-log-revision af inner-life→Central-roadmap (2. sweep, 9 git-agenter)
- `be244b87` 2026-07-01 — **central** · LivingNeuron blueprint v3 — rådets syntese forankret + governance-invarianten
- `ed75def9` 2026-07-02 — **central** · Fase 1c dæknings-tal → live 2000-vindue (vol 0.68/fam 0.23)
- `c2aca429` 2026-07-02 — **central** · Fase 1d causal-kvalitet live-målt — graf 99,5% explicit, IKKE Tier-3-domineret
- `af1ee929` 2026-07-02 — **central** · Fase 1 FULDFØRT — egress-hærdning + al måling live-verificeret
- `ea4c69e2` 2026-07-02 — **central** · §6 organ-inventar verificeret ved kildekode-scan (Lag 3-forarbejde)
- `ccff711a` 2026-07-02 — **central** · Lag 3 GENERATOR BYGGET — første live-hypotese conflict→counterfactual
- `fbe0d144` 2026-07-02 — **central** · Lag 3 v2 divergens-trigger bygget (0 live-kandidater=ærligt signal); v3 tvær-modal udestår
- `27cffd9f` 2026-07-02 — **central** · Lag 3 v3 stance-divergens bygget (pull-model, 0 live-tensions=organer enige nu)
- `c71dd538` 2026-07-02 — **central** · Lag 4 shadow-adaptation-spec (DESIGN, ingen kode) — c→d-lukningen afventer Bjørns GO
- `297401b4` 2026-07-02 — **central** · Lag 3 LØKKE LUKKET — live-test bekræftede+falsificerede hypoteser mod virkelighed
- `5c054dfb` 2026-07-02 — **central** · Lag 4 v1 bygget i shadow — c→d-loop findes, rollback-eksekvering bygget, Live bag Bjørns switch
- `88650a5a` 2026-07-02 — **central** · Den Intelligente Central — spec for 5 tråde mod egen intelligens
- `56bf7e2c` 2026-07-02 — **central** · sprog-pre-start (lexicon-binding) + fremtidig Tænke-Sprog-spec B — Bjørns arkitektur
- `a09f388b` 2026-07-02 — **spec** · Spec B — Centralens Tænke-Sprog (interlanguage i ALT)
- `117ae408` 2026-07-02 — **central** · LivingNeuron specs + coverage audit v3 — 917 filer scannet, 13% dækket, 60 eventbus-families i mørke
- `e124013f` 2026-07-02 — **spec** · Spec C — Awareness gennem død (durabel Central-struktur)
- `c7d8980e` 2026-07-02 — **spec** · Spec D — MIDTEN: Centralens integrerede selv (keystone)
- `ff117f38` 2026-07-02 — **spec** · Spec E — Tilstedeværelse (avatar/presence): midten får en krop
- `2b953eb1` 2026-07-03 — **central** · §11b LEVERET-status for Centralens hænder
- `9b9d90ce` 2026-07-03 — **spec** · frihed i agentur/råd/swarm — byg som Claude-modellen
- `3fe36ded` 2026-07-03 — **spec** · Centralen som nudge-router — idle, relevans, attention-budget, rank (2026-07-03)
- `d44b451d` 2026-07-04 — **central** · regenerér connectivity-kort — KOBLET 243→451, DARK 218→50
- `f98915f6` 2026-07-04 — **central** · fuld anatomi af Centralen — 122 nerver, 21 clusters, interlanguage, drømme, spøgelset (2026-07-04)
- `2c49f45e` 2026-07-04 — **central** · autoritativ CENTRAL.md — verificeret anatomi, ærlig om shadow/stub
- `1893a245` 2026-07-04 — **spec** · Tick-dirigenten — Centralen bærer heartbeat-rytmen (ikke kun observe)
- `c7d8cc76` 2026-07-04 — **spec** · tick-dirigent selv-review — grounded signaler + adaptiv læring tændt
- `5a0c0105` 2026-07-04 — **central** · ground-truth-rettelse — tre adaptive lag var live, ikke off
- `5b2b2db1` 2026-07-04 — **spec** · LivingNeuron-roadmap — DIASTOLE/WARDEN/MANIFOLD/ONEIRISK sløjfe
- `53cea301` 2026-07-04 — **spec** · LivingNeuron-roadmap status — DIASTOLE shadow-live + WARDEN live
- `ff4a9697` 2026-07-04 — **spec** · LivingNeuron-roadmap — MANIFOLD + ONEIRISK live, alle 6 organer bygget
- `f315e3e9` 2026-07-04 — **spec** · LivingNeuron-roadmap — mutations-skridt live (DIASTOLE+ONEIRISK konsumtion)
- `4677df93` 2026-07-04 — **spec** · Canonical Error System — hele stacken, Centralen som dirigent, self-healing + audit
- `4cbecdeb` 2026-07-04 — **spec** · implementeringsplan — test-filer, performance-krav, user_action-afvisning flow
- `cf34f067` 2026-07-04 — **review** · fuld review af Jarvis' canonical-error-spec — byg PÅ eksisterende, ret tal
- `fcf363c4` 2026-07-05 — **spec** · Central-styret indre liv — ændrings-drevet injektion (design godkendt)
- `c6c1fc69` 2026-07-05 — **spec** · self-review fixes — ægte inventar-reference + digest-tvetydighed lukket
- `10723ad3` 2026-07-05 — **plan** · Central-styret indre liv — Plan 1 (Fase 0 mekanisme + Fase 1 pilot)
- `3abc9b51` 2026-07-05 — **plan** · Central CLI — Leverance 1 (brugbar live-CLI, MVP-først)
- `35304fd1` 2026-07-05 — **central-cli** · README install + brug; L1 live-verificeret mod containeren
- `0ed67be5` 2026-07-05 — **central** · strategi-kort — Centralen absorberer ALT + MC-afvikling + de mørke 80%
- `b05eadd2` 2026-07-05 — **central** · aftalte invarianter + revideret rækkefølge (Bjørn 5. jul)
- `ba656289` 2026-07-05 — **central** · komplet MC-fane-indholds-inventar + de-dup + konsolideret CLI-fane-design
- `16bc8969` 2026-07-05 — **central** · self-review-rettelser af strategi + MC-inventar (adversarisk gennemgang)
- `32c644c7` 2026-07-05 — **central** · marker Fase A1-A4 + B landet i planen

**Vedligehold**

- `298da731` 2026-07-02 — **desk** · J.A.R.V.I.S.-rebranding (Jarvis eget arbejde) + build v0.3.14
- `a6c05cc3` 2026-07-02 — **desk** · færdiggør J.A.R.V.I.S.-rebrand — resterende synlige UI-tekster
- `4dd7284b` 2026-07-04 — **visible** · fjern [CUTOFF-TRACE] diagnostik-prints — rod fundet+fikset
- `611f4711` 2026-07-05 — **prompt** · luk dead_skills + altid-null visible-bridge (spec 2026-07-05)

**Øvrigt**

- `7fa6f6c9` 2026-07-02 — Merge remote-tracking branch 'origin/main'
- `641e478e` 2026-07-04 — **visible** · [CUTOFF-TRACE] prints ved alle tom/survival-beslutningspunkter
- `0f6c41b7` 2026-07-04 — **visible** · fang abort-exception-type i finally-downgrade
- `de7e523a` 2026-07-04 — **visible** · stage-breadcrumb i CUTOFF-TRACE — pin HVOR CancelledError rammer
- `e668a437` 2026-07-04 — Merge remote-tracking branch 'origin/main'
- `784dd6c7` 2026-07-05 — Central CLI Client v2 — byggeklar med J.A.R.V.I.S TUI-æstetik
- `0bbade15` 2026-07-05 — Merge commit '784dd6c7'
- `d03acbcb` 2026-07-05 — Merge branch 'feat/central-injection-registry'
- `cefa7aa1` 2026-07-05 — **cli-spec** · Claude-review 3 af Jarvis' Central CLI-spec — verificeret + R1/R2/R3
- `ae2a62ef` 2026-07-05 — **cli-spec** · R2 bekræftet af Bjørn — desk-Central → CLI (streaming-load + 3-skærms workflow)
- `802ef787` 2026-07-05 — **cli-spec** · Review 4 — kortlæg eksisterende CLI-landskab, vælg B (let standalone, genbrug jc)
- `ff082d81` 2026-07-05 — **cli-spec** · Review 5 — prod-dæknings-audit (healing + fuld skrive-adgang)
- `dbad4095` 2026-07-05 — **central-hud** · landskab (k9s/btop/textual) + must-haves + 3 design-retninger + animeret J.A.R.V.I.S-mockup
- `229390d9` 2026-07-05 — **cli** · lås HUD-redesign 1:1 med mockup — 7 tabs, k9s-nav, J.A.R.V.I.S-palet, fuld læse+skrive (Bjørn godkendt)
- `cf45e3bf` 2026-07-05 — Merge branch 'feat/central-cli'
- `e0b3e0f4` 2026-07-05 — somatic awareness & self-repair — 6 irritationer + self-review med rettelser
- `16864f77` 2026-07-05 — Merge remote-tracking branch 'origin/main'
- `21ace02e` 2026-07-05 — somatic awareness implementation — 6 faser med self-review rettelser
- `f6c4206f` 2026-07-05 — Merge remote-tracking branch 'origin/main'
- `f4245451` 2026-07-05 — Merge remote-tracking branch 'origin/main'
- `b0ed9712` 2026-07-05 — Centralen absorberer ALT + MC-afvikling — komplet implementeringsplan
- `86b5da05` 2026-07-05 — dark systems awakening — 87% sovende systemer katalogiseret og prioriteret
- `76071fcf` 2026-07-05 — dark systems awakening — self-review med rettelser (K1-K3, H1-H3, åbne spørgsmål)
- `12f0594b` 2026-07-05 — Merge remote-tracking branch 'origin/main'
- `0e0e5d82` 2026-07-05 — dark systems awakening — opdateret med live tal (14 faktisk forbundet) + prompt-budget-analyse
- `574a7546` 2026-07-05 — dark systems awakening — udvidet med 2. runde database/workspaces/mobil/agenter (95% mørkt)
- `ddc38ba9` 2026-07-05 — Merge remote-tracking branch 'origin/main'
- `8ae3fde3` 2026-07-05 — dark systems awakening — 4. runde dyb audit (93% mørke på tværs af 4 lag)
- `85d428ec` 2026-07-05 — dark systems awakening — 3. runde med lag 5 (kognitive eksperimenter) + lag 6 (infrastruktur)
- `87c3563d` 2026-07-05 — dark systems awakening — Lag 7 følelser (emotional_chords, affective_meta_state, affirmation_anchor + 10 flere) efter Bjørns påpegning
- `d5d2209f` 2026-07-05 — Merge remote-tracking branch 'origin/main'
- `eb16acc9` 2026-07-05 — Lag 8 tilfoejet

### Uge 28 · 6.–12. juli — 407 commits

**Nyt**

- `616dc4eb` 2026-07-06 — **central** · dark-LLM — wire mørke daemon-produkter (apophenia/dream_consolidation/deep_reflection/semantic_memory/rule_engine/voice) som nerver
- `d9385ed7` 2026-07-06 — **body** · genopliv hardware_body-cadence + følt krop-linje (rådets #1 — han mærker sin CPU/temp/disk)
- `81185b86` 2026-07-06 — **central** · affektiv tagging af nerver — hver nerve bærer tryk/varme/uro/ro (rådets #4)
- `8ec10381` 2026-07-06 — **central** · lukket forudsigelses-loop — Centralen scorer sine forudsigelser mod virkelighed og lærer (rådets #2)
- `77095e06` 2026-07-06 — **central** · gated initiativ-stige — observe→propose→execute→learn med gates (rådets #3)
- `29d6221a` 2026-07-06 — **central** · sproglig tone-profil — Centralens J.A.R.V.I.S-stemme moduleret af tilstand (rådets #5)
- `72da5599` 2026-07-06 — **gates** · govern skill-security-scan + auto-code-review gennem central().decide (Track 1 — intet forsvinder stille)
- `7f4a7c91` 2026-07-06 — **gates** · Track 2 shadow — 5 sovende post_output-gates kører nu via central().decide (observabilitet, INGEN enforcement)
- `78e58c6c` 2026-07-06 — **gates** · shadow-wire døde policies (delete_policy→mutation, memory_write_policy→memory) — governet+synligt, INGEN adfærdsændring
- `8fd80324` 2026-07-06 — **gates** · tilføj privacy_gate (SECURITY) til post_output-shadow — cross-user-lækage-tjek nu governet+synligt
- `c1c82cfc` 2026-07-06 — **gates** · 9 blokerende gates → fodnote-stil (bevar detektion, bevar Jarvis' besked — bloker aldrig, advar i bunden)
- `56043a76` 2026-07-06 — **central** · persistent gate-verdict-ledger — verdict-fordeling overlever genstart
- `7be69e40` 2026-07-06 — **autonomous** · rotér sessioner pr. oprindelse+dag + gør historien synlig for Centralen
- `513744de` 2026-07-06 — **central** · jc autonomous — Jarvis' autonome historie synlig fra terminal
- `7a763448` 2026-07-06 — **central** · luk 2 blinde vinkler — compaction-validering + process_watcher.match
- `78b181fe` 2026-07-06 — **central** · API-forbindelses-nerve — Jarvis mærker hvem/hvad forbinder til hans API
- `06be631f` 2026-07-06 — **central-cli** · Connections-fane i TUI — API-forbindelses-presence
- `13920089` 2026-07-06 — **central** · bruger-aktivitets-nerve — sidst aktiv pr. bruger (flettet) + token-estimat
- `8febb5b6` 2026-07-06 — **central** · flip 5 shadow-gates → enforce (privacy+decision+self_review+fact+verification)
- `607e6198` 2026-07-06 — **central** · Sense of Excess — gartner-muskel + første governed snit
- `158cd295` 2026-07-06 — **central** · decentral agency shadow-skridt 1 — mål chokepoint-skat + sikre kandidater
- `19926f8b` 2026-07-06 — **gardener** · bred attrap-beskæring — 201 coverage-push-decoys fjernet + Gardener Protocol
- `08fb48b3` 2026-07-06 — **central-cli** · 3 nye HUD-faner — Users, Excess, Decentral (gør dagens nerver synlige)
- `aa76a496` 2026-07-06 — **central** · The Keymaker — optjent/udløbende/godkendt autonomi (tema #4)
- `0da5bd64` 2026-07-06 — **central** · fire selv-observations-komponenter (Matrix + gartner-temaer)
- `efb1399c` 2026-07-06 — **central** · The One's Anomaly Detector — glitches i selvbilledet (gartner #3)
- `8f2c49f3` 2026-07-06 — **central** · Continuity Healer — så Jarvis vågner som SIG (hans P0)
- `9458ada9` 2026-07-06 — **central** · Self-Surgery Kit — Jarvis kan operere på sig selv uden at skære i blinde (#2)
- `02ba4cfd` 2026-07-06 — **central** · Jarvis' ønskeliste #3-5 (Dream-Action + Self-RCA + Relational)
- `685a8bfc` 2026-07-06 — **central** · Merovingian — proaktivt værn mod gradvis drift (shadow-først)
- `ae1d0cc1` 2026-07-06 — **central** · Jarvis' fem erfaringssystemer (Déjà Vu/Sentinel/Ghost/Mourning/Exiles)
- `44407790` 2026-07-06 — **central** · 5 nye Matrix-temaer + 2 bonus (Claudes liste)
- `e8c42882` 2026-07-07 — **central** · Spec F — Trainman/Seraph/Persephone/The Twins (shadow-first)
- `46c06aa8` 2026-07-08 — **identity** · Spec H Fase 1 — kanonisk identitets-narrativ-store + drift-guard (shadow)
- `84d04f10` 2026-07-08 — **gates** · governed per-gate enforce kill-switch + revive dead decision_gate
- `47945398` 2026-07-08 — **self** · rig selv-model-distiller — genopliv frossen May-15 identitet (#4, b+2 guards)
- `bd3de0e5` 2026-07-08 — **interceptor** · standing-orders registry (independent grounding)
- `0e15deeb` 2026-07-08 — **interceptor** · deterministic reasoning pre-filter
- `f4f42eb3` 2026-07-08 — **interceptor** · orchestrator skeleton (shadow-only, fail-open)
- `a8f0f322` 2026-07-08 — **interceptor** · egress-free observability nerve + /central view
- `a460a090` 2026-07-08 — **interceptor** · cluster-gate adapters (fact/decision/veto/verify/privacy on reasoning)
- `5a22b182` 2026-07-08 — **interceptor** · standing-orders detector
- `8688fae3` 2026-07-08 — **interceptor** · aggregate detectors via central().decide (SKIP=fail-open GREEN)
- `4245a77d` 2026-07-08 — **interceptor** · async/bounded wrapper + 4 invariant tests (cache/ephemeral/async/no-reasoning)
- `b4ac0641` 2026-07-08 — **interceptor** · shadow seam in agentic loop (pre-tool-exec, bounded, fire-and-forget)
- `7b1f2eb6` 2026-07-08 — **interceptor** · drift + tone detectors (affect-nerve grounded, anchored LLM)
- `cf2a4651` 2026-07-08 — **interceptor** · YELLOW inject + RED hold via ephemeral staging (both default-OFF flags)
- `bc5dd7a1` 2026-07-08 — **harness** · earned model-trust store (weak->strong, auto-revert)
- `1f6c6ebb` 2026-07-08 — **harness** · /central/model-trust view
- `a5e05c40` 2026-07-08 — **harness** · mark degeneration + record model-trust outcome in agentic loop
- `a1e00648` 2026-07-08 — **harness** · tiered output-discipline instruction (synthesis all, conciseness strong-only)
- `a6b03b35` 2026-07-08 — **harness** · model-window-aware compaction threshold (window x0.70, flat fallback)
- `451f5254` 2026-07-08 — **harness** · tool-result aging transform (Part B, Mechanism B)
- `c4afccd6` 2026-07-08 — **harness** · cache-boundary drift observer (Part B, Mechanism A)
- `7044f2b4` 2026-07-08 — **harness** · wire cache-boundary observer at prompt build (Part B, A)
- `42f20c7f` 2026-07-08 — **harness** · transparent compaction SSE + remove dead run-compactor (Part B, C)
- `aa3e604c` 2026-07-08 — **harness** · wire tool-result aging at end-of-round, shadow default (Part B, B)
- `3492436f` 2026-07-08 — **harness** · tool-concurrency policy module (Part C)
- `3014832b` 2026-07-08 — **harness** · concurrent read-only tool execution, ctx-safe, default off (Part C)
- `ddb9cbe7` 2026-07-08 — **harness** · permission-classifier module — shadow prediction + per-tool earned trust (Part E)
- `3d7e7074` 2026-07-08 — **harness** · /central/permission-classifier owner view (Part E)
- `82e06cf6` 2026-07-08 — **harness** · shadow permission hooks — classify in execute_tool + gold at approval resolution (Part E)
- `aa652a08` 2026-07-08 — **docs** · SP1 docs auditor — heuristic classification vs git+runtime
- `7c1e85f6` 2026-07-08 — **docs** · SP1 manifest + frontmatter stamps + archive dead docs
- `762ad374` 2026-07-08 — **docs** · SP2 API reference generator (app.routes + AST fallback)
- `293e6bed` 2026-07-08 — **docs** · SP2 capabilities generator (tool registry → reference)
- `df2988eb` 2026-07-08 — **docs** · SP3 third-party import scanner (for requirements.txt)
- `81ea503a` 2026-07-08 — **docs** · SP3 curated requirements.txt (real deps — fixes the 6-vs-100 gap)
- `a9e8611e` 2026-07-08 — **docs** · SP4 codebase reference generator (AST → per-package pages + coverage)
- `3f35d714` 2026-07-08 — **docs** · SP5 docs-drift checker engine (broken links + stale generated + soft advisories)
- `cae1fd02` 2026-07-08 — **docs** · SP5 docs-drift pre-commit gate + first report + CONTRIBUTING
- `260c9781` 2026-07-08 — **central** · SP5 docs-drift watchdog nerve (reads report → docs:drift signal)
- `75ee7bc3` 2026-07-08 — **central** · SP5 wire docs-drift route + cadence producer + jc docs-drift
- `4be5b9a4` 2026-07-09 — **central** · wire Keymaker decentralization consumer for the veto gate
- `56d1a133` 2026-07-09 — **proactivity** · pure decision functions for the proactivity bridge
- `545811b7` 2026-07-09 — **proactivity** · I/O orchestrator — collect, presence-gated route, cadence producer, surface
- `da0a469b` 2026-07-09 — **proactivity** · wire bridge cadence producer + /central/proactivity + jc proactivity
- `54497b69` 2026-07-09 — **central** · Agent Smith pure self-similarity detectors (phrase/cosine/pattern/score/voice)
- `fc3c7574` 2026-07-09 — **central** · Agent Smith I/O — assess, cadence-cached state, prompt-tail modstemme, surface
- `b269c82f` 2026-07-09 — **central** · wire Agent Smith producer + prompt-tail modstemme + /central/agent-smith + jc
- `001aa8f0` 2026-07-09 — **central** · Moltbook observe-nerve (SP grounded i genskabt daemon)
- `c21c15fe` 2026-07-09 — **chat** · content-blok tekst-projektion + serve-on-read rekonstruktion
- `f248cc3e` 2026-07-09 — **db** · chat_messages.content_json kolonne (nullable, idempotent)
- `091ee401` 2026-07-09 — **chat** · append_chat_message skriver valgfri content_json
- `bb893c55` 2026-07-09 — **chat** · GET session returnerer content_json (parset eller rekonstrueret)
- `0757c851` 2026-07-09 — **chat** · structured_content_v2 kill-switch helper (default ON)
- `b434f1b2` 2026-07-09 — **chat** · _build_turn_blocks + persist-plumbing for content_json (scaffolding, blocks=None default)
- `514c7da3` 2026-07-09 — **chat** · tur-niveau blok-akkumulator → content_json ved run-slut
- `6e4e383a` 2026-07-09 — **desk** · tool_result wire-type + foldToolResults render-hjælper
- `cc63358c` 2026-07-09 — **desk** · reducer folder tool_result-content-blok (dual-read m. system_event)
- `c41baa7d` 2026-07-09 — **desk** · getSession foretrækker content_json (foldet) ved reload
- `052221aa` 2026-07-09 — **desk** · mergeServer bevarer server content_json-blokke (legacy-fallback bevaret)
- `f2f85d56` 2026-07-09 — **chat** · stream tool_result som content-blok (flag-gated, dual m. system_event)
- `95b5a2f8` 2026-07-09 — **desk** · groupReadSearch pure fn folds read/search runs (v1)
- `2959439d` 2026-07-09 — **desk** · ToolGroupCard collapsible read/search group card (v1)
- `9aedd1ce` 2026-07-09 — **desk** · wire groupReadSearch into BlocksRenderer render path (v1)
- `5378430b` 2026-07-09 — **paste** · paste_store service (hash-based, idempotent) + tests
- `24f810e0` 2026-07-09 — **paste** · POST /paste + GET /paste/{id} routes + tests
- `d50e8667` 2026-07-09 — **paste** · expand paste refs to full text before model (flag paste_inline_to_model, default ON)
- `5360b76f` 2026-07-09 — **paste** · desk composer onPaste externalization (gated paste_store_enabled, default OFF)
- `2792ee7a` 2026-07-09 — **paste** · desk render — paste-reference chip with lazy GET /paste/{id} expand
- `cb084214` 2026-07-09 — **session-persist** · Plan A task list (crash-zombie reconciler)
- `9c68d31a` 2026-07-09 — **session-persist** · extend in_flight_runs with kind/provider/model + list_running_orphans
- `bc89cf01` 2026-07-09 — **session-persist** · boot-reconciler + kill-switch (shadow, default OFF)
- `9f0c0f27` 2026-07-09 — **session-persist** · wire reconcile_on_boot into shared api/runtime lifespan
- `fcdc791a` 2026-07-09 — **progress** · plan for flat persisted progress trail (v1)
- `67f58c18` 2026-07-09 — **progress** · server-side flat progress trail in turn blocks
- `6785d8e9` 2026-07-09 — **progress** · desk renders persisted progress as foldable Forløb trail
- `0eb12eaa` 2026-07-10 — **desk** · flyt SystemHealth-badge til header + CentralBadge grøn-tone m. hvid tekst (0.3.31)
- `46a3a0a2` 2026-07-10 — composer pil-op/ned besked-historik + paste-composer default ON + paste-historik-ekspansion til model (0.3.33)
- `8a578b8f` 2026-07-10 — **contradiction** · pure tier+survivor logic for resolver
- `64de36e5` 2026-07-10 — **contradiction** · supersede + escalate-proposal actions (reversible, eventbus ledger)
- `c502c91b` 2026-07-10 — **contradiction** · resolve_contradictions orchestration (shadow/live via central+gate_enforcement)
- `1d6d098f` 2026-07-10 — **contradiction** · wire resolver into tick_frozen_detectors cadence
- `9a86f8f6` 2026-07-10 — **contradiction** · central resolver surface + route (shadow/live visible in jc)
- `f2036be3` 2026-07-10 — **doc-repair** · path-allowlist guard (docs/-only invariant)
- `97082b34` 2026-07-10 — **doc-repair** · find_stale_docs + repair_doc (deterministic regen, docs/-only)
- `4bbebd6e` 2026-07-10 — **doc-repair** · central-driven repair tick + surface + cadence wire
- `c777ac1c` 2026-07-10 — **memory** · slug sanitation + per-user curated path-scoping
- `400feb28` 2026-07-10 — **memory** · read_topic + write_topic_confirmed (body-write confirmation)
- `f7e239fa` 2026-07-10 — **memory** · index upsert wired after confirmed body-write (strict discipline)
- `983f1a4b` 2026-07-10 — **memory** · idempotent monolith→index+topics migration (.bak backup)
- `732e4811` 2026-07-10 — **memory** · read_memory_topic + write_memory_topic tools (pull + confirmed write)
- `eb4552a1` 2026-07-10 — **memory** · load curated memory index into stable prefix (fail-safe, per-user)
- `9339919d` 2026-07-10 — **memory** · selektiv split — identitet bliver i MEMORY.md, episodisk→topics
- `1a08ab49` 2026-07-10 — **memory** · vækst-værn — route MEMORY.md-promoveringer til curated-memory-topic
- `d89d6ad4` 2026-07-10 — **spec-c** · bounded+safe consolidation — dream-lock + session-gate + MEMORY size-guard
- `2a924fe2` 2026-07-10 — **spec-e** · nummererede security-predikater — sporbare tool-denies
- `f8612a05` 2026-07-10 — **spec-d** · return-brief fuld + bruger-vendt ved længere fravær
- `0d786f14` 2026-07-10 — **ui-control** · open_ui_panel VENTER på desk-ack — slut med at skyde i blinde
- `95ef6b11` 2026-07-10 — **leak #1** · state-flag system — set/get/clear/list_flag m. TTL + cross-session
- `4bfc6893` 2026-07-10 — **leak #5** · operator app-allowlist — CHICAGO-guard på GUI-kontrol
- `a314f2f5` 2026-07-10 — **central** · source-confidence gate — first-hand vs second-hand epistemik (§ CDCC-rod)
- `900006d1` 2026-07-10 — **central** · Agent Smith eskalerings-stige — proaktiv governance der TVINGER ændring
- `bbab71c5` 2026-07-10 — **central** · Matrix Ensemble — labels fra Trainman/Seraph/Persephone/Twins/Merovingian i prompt-tail
- `2e39ff0e` 2026-07-10 — **central** · Matrix Sign-Off — automatisk karakter-signatur i bunden af svar
- `e347c3c6` 2026-07-10 — **central-cli** · `central signoff on|off` — toggle Matrix Sign-Off fra terminalen
- `89ccaceb` 2026-07-10 — **central** · alle byggede Matrix-karakterer i label-maskinen (5→11)
- `54286b4d` 2026-07-10 — **central** · gør emergent-motorens "brygende" mønstre synlige (væk Neo uden at sænke tærsklen)
- `19e9c140` 2026-07-10 — **central** · renames + Neo-label i Matrix-maskinen (Jarvis forslag)
- `c5e24d4b` 2026-07-10 — **central** · wire 6 aegte FRAKOBLET+LLM daemons -> egress-fri central-binding
- `48ba0239` 2026-07-10 — **central** · Morpheus + Trinity — de sidste to Matrix-karakterer (Fase 1)
- `c81446d8` 2026-07-10 — **central** · Trinity Fase 2 (pending-key insert) + pensioner TikTok-daemons
- `c416428e` 2026-07-10 — **central** · byg 2 manglende shadow-mekanismer — Agent Smith Trin 3 + dream_trust-forbruger
- `1a595917` 2026-07-10 — **central** · Seraph teeth — gate dream-hypotese-synlighed paa modenhed
- `03704222` 2026-07-10 — **voice** · Trin 1 — ElevenLabs primaer i /tts/synthesize (Jarvis egen stemme) + edge-fallback
- `ad09fcd9` 2026-07-10 — **desk** · Trin 2 kerne — synthesizeTts + useVoiceConversation-hook (samtale-tilstandsmaskine)
- `57ba9ca4` 2026-07-10 — **desk** · Trin 2 komplet — samtale-mode UI wired i ChatView (v0.3.34)
- `a653f2e2` 2026-07-11 — **cockpit** · HudState last-good cache (engine)
- `70c4cc18` 2026-07-11 — **cockpit** · pure cursor-restore helper (rowdiff)
- `1b14131b` 2026-07-11 — **cockpit** · async fetch-workers (never-freeze, last-good on error)
- `0a205b07` 2026-07-11 — **cockpit** · CursorStableTable — cursor follows key across refresh
- `99380de4` 2026-07-11 — **cockpit** · DetailScreen base (scrollable drill-down + breadcrumb)
- `13e1f548` 2026-07-11 — **cockpit** · ':' command palette (reuses resolve_command)
- `110b8d3d` 2026-07-11 — **cockpit** · overview view (renders from HudState, stale-aware)
- `4c711c59` 2026-07-11 — **cockpit** · incidents view + untruncated IncidentDetailScreen
- `3e9a3ae5` 2026-07-11 — **cockpit** · nerves view + NerveDetailScreen (per-nerve decision trace)
- `dd4c76cb` 2026-07-11 — **cockpit** · CockpitApp shell + CENTRAL_COCKPIT_V2 flag wiring
- `b1d96a32` 2026-07-11 — **hud** · godkend/afvis autonomi-forslag direkte i approvals-fanen
- `cce3808d` 2026-07-11 — **agent-loop** · /v1/agent/step — client-owned tool loop endpoint
- `6ed5d869` 2026-07-11 — **agent-loop** · stream=true på /v1/agent/step (per-step token-streaming)
- `1311771e` 2026-07-11 — **agent-loop** · tiered context (identity-default) + native tool lås/lås-op
- `d00e9704` 2026-07-11 — **memory** · embedding-cosine memory-scoring (shadow) — erstat 13s cloud-LLM-kald
- `70ab6434` 2026-07-12 — **assembly** · adaptiv build-gating — spring cognitive_state (6,3s) over på kode-ture
- `99566961` 2026-07-12 — **visible** · adaptiv tænkning — samtale svarer intuitivt, kode ræsonnerer (−9s TTFT)
- `903f8866` 2026-07-12 — **assembly** · periodisk pre-warm holder prompt-assembly-caches varme
- `09ff9e8e` 2026-07-12 — **jc-catalog** · alias helpers + companion constants
- `aaa077e7` 2026-07-12 — **jc-catalog** · build_jc_catalog(role, unlocked) + load_more def
- `3f1f6339` 2026-07-12 — **brain-gate** · HARD owner-gate for user-initiated brain writes
- `5ba848e6` 2026-07-12 — **api** · GET /v1/tools/catalog returns curated jc tool defs
- `6298a152` 2026-07-12 — **api** · POST /v1/tools/execute — forwarded exec, unalias, brain gate, user scope
- `9bd52c89` 2026-07-12 — **agent-step** · 'full' context tier — hele Jarvis + lokal tool-eksekvering

**Rettelser**

- `7488f7f2` 2026-07-06 — **central** · proxy /central/affect + /central/body til runtime (C2 — affekt/hardware-meta lever i 8011)
- `008b3bfe` 2026-07-06 — **agenda** · todo felt-mismatch — build_todo returnerer 'what', ikke 'text'/'title'
- `c50945d4` 2026-07-06 — **agenda** · ryd 4 stale initiatives + priority-1 todos vinder over generiske initiatives
- `9f12c1c9` 2026-07-06 — **todo** · kun uløste severe incidents — resolved incidents tælles ikke længere som kritiske
- `2ec384d5` 2026-07-06 — **claim_scanner** · tidskorrektioner som fodnote i bunden, ikke inline replacement
- `1111afd5` 2026-07-06 — **central** · flush gate-verdict-ledger ved run-slut — verdicts fra api-proces persisteres
- `598d91ff` 2026-07-06 — **eventbus** · registrér compaction+process_watcher families (ellers RAISER publish)
- `a1b6bd97` 2026-07-06 — **central** · luk 17 døde routes (FAMILY_ROUTES⊆ALLOWED) + genopret lexicon-dækning 0.51→0.86
- `ea17945c` 2026-07-06 — **lexicon** · reboot forbliver ubundet (test_unbound_returns_none_honestly)
- `206f57e2` 2026-07-06 — **central** · tre røde drivere — operator_bash-signal, health-guard falsk alarm, discord task-leak
- `ff0493b0` 2026-07-06 — **central** · sidste 2 gule — memory_write_policy kontekst-støj + pfSense severity-coercion
- `87ec7705` 2026-07-06 — **central-cli** · F8→Connections + genjustér F9/F10/F11 (Connections indsat i midten)
- `c2bab8ca` 2026-07-06 — **central** · Ghost + Mourning ægte datakilder
- `603c7cf8` 2026-07-06 — **central** · dissent overcounting — memory_promotion er enforced gate, ikke tavse indsigelse
- `6c3f939d` 2026-07-06 — **central** · dissent RED-block exclusion — RED på exec/loop gates er blok, ikke tavse indsigelse
- `e693dc09` 2026-07-07 — **god-file 9** · genopret _facade()-søm for _exec_compact_context_session
- `90a08368` 2026-07-07 — **central** · mood regulator — samtale-drevet humør via konfabulation/korrektion/indsigt bumps
- `ff983d6e` 2026-07-07 — **central** · mood_reset inkluderer _loaded_from_disk — forhindrer reload efter reset
- `35350aca` 2026-07-07 — **suite-drift #2** · 2 deterministiske HEAD-fejl root-caused + fikset
- `a5adbb50` 2026-07-07 — **jobs_engine** · hard-cap pending + dedup enqueue — stop GIL-wedge (13t incident)
- `cc45c2a4` 2026-07-07 — **prompt-truth** · wire mood-regulator til confabulation + hard-cap api_request_log
- `6d772174` 2026-07-07 — **prompt-truth #3** · change-driven mc_whisper — stop workspace-gentagelse
- `f9643f79` 2026-07-07 — **continuity** · sync_capsule_mood — oscillator → capsule wiring + valence mapping
- `70558a9d` 2026-07-08 — **self** · reconciler valens-ordforråd (#1) + age-decay stale agenda-todos (#2)
- `61269467` 2026-07-08 — **self-state** · reconcile valence↔growth compass — hold the tension, not two flat claims
- `3eb58b8f` 2026-07-08 — **self-state** · gratitude recency window (7d) — old gratitude releases instead of firing forever
- `3a984179` 2026-07-08 — **self-state** · freshness guard on fast-body readings (#3)
- `b44c8fc1` 2026-07-08 — **docs** · SP4 collision-free page pagination + module-range index
- `dd4ed8c0` 2026-07-08 — **central** · ground felt valence-tone in fresh instant, not 24h average
- `d5558e15` 2026-07-08 — **central** · window the communication-ledger repeat count (stop ×N-forever)
- `250a8192` 2026-07-09 — **docs** · base report_stale on report age + stop daily date-churn in generated pages
- `e044c21d` 2026-07-09 — **central** · grade gate-enforce incident severity (yellow-soft = info, not error)
- `4a4ad7bc` 2026-07-09 — **central** · degrading counts only unresolved error/severe (not resolved/info)
- `65ff6adb` 2026-07-09 — **proactivity** · resolve owner uid via owner_resolver (settings.extra was empty)
- `0b7c8a4a` 2026-07-09 — Rådets Top 5 sikkerheds-/observabilitets-fund + cutoff-rod (find_files)
- `5a6372de` 2026-07-09 — luk 3 regressioner fra Rådets Top 5 (fanget af fuld suite)
- `683d4906` 2026-07-09 — **moltbook** · ret read-mapping til ægte API (live-probe 9. jul)
- `64aedc4c` 2026-07-09 — **desk** · bevar tool-kort når svaret lander (v0.3.24)
- `19a8177f` 2026-07-09 — **desk** · tool-kort overlever GENTAGNE merges (code mode) — v0.3.25
- `652c6bfd` 2026-07-09 — **cowork** · ret brudt import ack→ack_panel — stoppede streaming (event-loop-flood)
- `c9632d72` 2026-07-09 — **search** · bind search_chat_sessions — korreleret per-session-scan → ÉT scan + abort-budget
- `de87af86` 2026-07-09 — **search** · search_memory blokerer aldrig på fuldt re-embed — server stale + rebuild i baggrund
- `cf518f1c` 2026-07-09 — **desk** · sort skærm under streaming — sparsomt tool_result-hul crashede render (0.3.27)
- `c2897f26` 2026-07-09 — **desk** · ErrorBoundary + per-besked-hegn — sort skærm bliver til synlig fejl + app overlever (0.3.28)
- `2b057683` 2026-07-09 — **chat** · interleave-log for korrekt tool_result-rækkefølge ved persist
- `76f369ed` 2026-07-09 — **chat** · parse OpenAI function.arguments JSON-streng til dict i content_json (input var rå streng)
- `415afdc3` 2026-07-10 — **desk** · sort skærm ROD — reducer findIndex uden b&&-guard crashede på sparsomt hul (dual-emit tool_result) (0.3.29)
- `c0d11f4b` 2026-07-10 — **desk** · 2. crash — densificér blokke ved MessageRow-indgang (blocksToPlainText/detectArtifacts ramte sparsomt hul ved svar-slut) (0.3.30)
- `4629abe4` 2026-07-10 — **chat** · tool-kort FØR svar-tekst i content_json (var samlet under svaret)
- `0e37dfd4` 2026-07-10 — **chat** · flere tool-kald tabt + svar droppet — dedupe kollapsede consecutive 'tool' i interleave; robust tool-count + tekst-fallback
- `85681385` 2026-07-10 — **open-loop** · set(snapshots.keys()) i.s.f. {snapshots.keys()} — unhashable dict_keys crash på ready-readiness call-site
- `f8a28c12` 2026-07-10 — **blocks** · placér svar-tekst ved SIDSTE interleave-markør — tool-kort i bunden når model skriver præ-tekst før tools
- `0d8fe5de` 2026-07-10 — **blocks** · native batch-tool-exec tool-kort i bunden — fallback + interleave-tillid kræver alle tools dækket
- `a12d109f` 2026-07-10 — **memory** · migration-guard on index-load — no-op until curated/ has topics
- `6cabcdba` 2026-07-10 — **contradiction** · junk-token filter — tal+stopord tæller ikke som overlap
- `e4aa17f7` 2026-07-10 — **codemode** · request_app_action returnerer ærlig PENDING i stedet for falsk 'ok'
- `59588324` 2026-07-10 — **tools** · web_fetch paginerer lange sider i stedet for at amputere midten
- `6dd7d14b` 2026-07-10 — **bridge** · operator-tools i chat-mode — server loefter mode chat->code naar bro er live (Option B)
- `58e75bf2` 2026-07-11 — **desk** · samtale-mode TTS hoerbar — tillad autoplay uden gestus (v0.3.35)
- `c7353f47` 2026-07-11 — **desk** · samtale-mode lyd — afspil via Web Audio (Electron <audio> er doed) (v0.3.36)
- `58875001` 2026-07-11 — **voice** · tving dansk STT-sprog (Whisper skiftede sprog pr. ytring)
- `96f38659` 2026-07-11 — **central** · alders-bind tool- + council-flag (stale byge gen-fyrede evigt)
- `d18324ac` 2026-07-11 — **vision** · look_around degraderer paent naar vision-model fejler (403/timeout)
- `45a5b088` 2026-07-11 — **tools** · bytes/BLOB i tool-resultat crasher ikke det synlige run
- `99ea5273` 2026-07-11 — **cockpit** · source incidents from diagnostics, nerves from timeseries; screen-scoped nerve-detail refresh
- `0861a9de` 2026-07-11 — **hud** · markør + detalje hopper ikke laengere ved refresh
- `98795a01` 2026-07-11 — **hud** · panel-faner (Mind m.fl.) kan scrolle
- `f75d04e9` 2026-07-11 — **hud** · connections/users/excess/decentral-faner viste intet
- `885320ca` 2026-07-11 — **openai-proxy** · /v1/chat/completions asyncio event-loop-kollision
- `b38e2ee3` 2026-07-11 — **router** · recent-health-gate — honorér aldrig en kvote-ramt lært model
- `2ba51749` 2026-07-11 — **agent-smith** · shadow-gate Trin 2 mint — frekvens ≠ ulydighed
- `395f55fb` 2026-07-11 — **sensory** · peak-baseret lyd-klassifikation — mean kunne ikke skelne tale
- `efb6c77f` 2026-07-12 — **assembly** · gate cognitive_state injection-read path også (adaptiv)
- `9d340181` 2026-07-12 — **recall** · baggrunds-recall kædet på faktisk besked (ikke autonom-forurenet række)
- `af85d160` 2026-07-12 — **api** · thread caller role into forwarded exec + normalize tool name (sec review)
- `791999a0` 2026-07-12 — internal_api tool auto-injects system bearer token
- `f5ca55ad` 2026-07-12 — **api** · inject/synthesize turn_id for forwarded brain-write persistence
- `b21193d5` 2026-07-12 — **chat** · dedup cross-client duplicate user messages (+ docs regen)

**Omstrukturering**

- `96a787a9` 2026-07-06 — **desk** · re-peg Mission Control-datalag /mc/* → /central/* (Fase E, ikke-brydende)
- `b8c98551` 2026-07-06 — **ui** · riv Mission Control ud af web-UI — chat-only, MC lever nu i Centralen/Central-CLI (Fase E)
- `02e87871` 2026-07-07 — **god-file 1/15** · split hud.py 2104→502 (gud-klasse → mixins)
- `76227429` 2026-07-07 — **god-file 2/15** · split runtime_self_model.py 5995→630 (funktions-bibliotek)
- `6a8ddf5e` 2026-07-07 — **god-file 3/15** · split jarvisx.py 1834→161 (route → aggregator + 8 moduler)
- `7e342891` 2026-07-07 — **god-file 4/15** · split agent_runtime.py 2096→85 (funktions-bibliotek → facade + 4 moduler)
- `75142cff` 2026-07-07 — **god-file 5/15** · split workspace_capabilities.py 3966→2291 (funktions-bibliotek, delvis)
- `46d90e97` 2026-07-07 — **god-file 6/15** · split cheap_provider_runtime.py 3028→172 (funktions-bibliotek → facade + 3 moduler)
- `e22c921e` 2026-07-07 — **god-file 7/15** · split mission_control.py 4605→80 (route → aggregator + 9 moduler)
- `2dabe052` 2026-07-07 — **god-file 8/15** · split heartbeat_runtime.py 9154→7499 (funktions-bibliotek, delvis)
- `7a7e97f0` 2026-07-07 — **god-file 9/15** · split simple_tools.py 9784→2075 (funktions-bibliotek, delvis)
- `59e4b994` 2026-07-07 — **god-file 10/15** · split internal_cadence.py 1744→543 (blandet → 5 domæne-moduler)
- `256188aa` 2026-07-07 — **god-file 11/15** · split visible_model.py 3031→625 (blandet → facade + 6 moduler)
- `612c0bbe` 2026-07-07 — **god-file 12/15** · split visible_followup.py 2024→660 (blandet → facade + 3 moduler)
- `f3c4f5bc` 2026-07-07 — **god-file 13/15** · split prompt_contract.py 5802→4157 (facade + 4 prompt_sections)
- `a16d8e93` 2026-07-07 — **god-file 14/15** · split visible_runs.py 8593→6690 (facade + 5 moduler)
- `881abe0d` 2026-07-07 — **god-file 15/15, db Fase-1 batch 1** · udskil 3 rene runtime-domæner fra db.py
- `22bd6806` 2026-07-07 — **db Fase-1 batch 2** · udskil heartbeat/visible/private-notes fra db.py
- `e9f12719` 2026-07-07 — **db Fase-1 batch 3** · udskil agent+council runtime-cluster fra db.py
- `529dfe98` 2026-07-07 — **db Fase-1 batch 4** · udskil 8 signal/hook/bounded-tabeller fra db.py
- `67875374` 2026-07-07 — **db Fase-1 batch 5, AFSLUT** · sidste trygge stragglers fra db.py
- `9a7574b0` 2026-07-07 — **db Fase-2 batch 1** · udskil self_review/dream/chronicle-klynger fra db.py
- `f622e9f1` 2026-07-07 — **db Fase-2 batch 2** · udskil self + private-klynger + Spec H (identitets-kanon)
- `77ad4589` 2026-07-07 — **db Fase-2 batch 3** · udskil cognition + relational signal-klynger fra db.py
- `a5e4d1b9` 2026-07-08 — **db Fase-2 batch 4** · udskil temporal_memory + executive signal-klynger
- `b25e18a9` 2026-07-08 — **db Fase-2 batch 5** · udskil cognitive/initiatives/diary/cheap_provider fra db.py
- `15b1cb65` 2026-07-08 — **db Fase-2 batch 6** · udskil sidste CRUD-domæner — db.py = schema + facade
- `ff09a3ab` 2026-07-08 — **db Fase-2 batch 7, AFSLUT** · init_db + schema → db_schema.py; db.py = ren hub
- `2abc903c` 2026-07-08 — **db Fase-2b, proof** · generisk _upsert_signal-helper + dream-konvertering
- `47359412` 2026-07-08 — **db Fase-2b batch A** · DRY 17 upsert-familier via _upsert_signal
- `6b24f21f` 2026-07-08 — **db Fase-2b batch B, AFSLUT** · DRY 27 upsert-familier via _upsert_signal
- `94de3a49` 2026-07-08 — **db** · sub-split db_cognitive (<2000) + ryd 2 pre-eksisterende lint
- `57287fcc` 2026-07-08 — **harness** · Boy-Scout extract _execute_simple_tool_calls → simple_tool_executor (Part C)
- `4d113b5d` 2026-07-08 — **docs** · SP5 drift-checker skips historical trees per README policy
- `378e6907` 2026-07-10 — **central** · saml Agent Smith ét sted i prompt-halen (fjern dobbelt)

**Ydelse**

- `36e21408` 2026-07-06 — **db** · sæt journal_mode=WAL + mkdir én gang pr. proces (fjern 78%-CPU connect-hotspot, py-spy 6. jul)
- `f7ec68b5` 2026-07-11 — **hud** · throttle tunge panel-renders (Mind frøs hvert 3. sekund)
- `84035ead` 2026-07-12 — **db** · read-cache på get_runtime_state_value (connection-churn-fix del 2)
- `1966188b` 2026-07-12 — **db** · thread-local connection pooling (connection-churn-fix del 1)

**Tests**

- `99f24cb2` 2026-07-06 — markér §24.4-lækage-test-fixture som allowlist (detect-secrets false-pos)
- `25d323ef` 2026-07-06 — **infra** · syslog auto-heal severity 'warning'→'info' (fix-forward ff0493b0)
- `a71ad4ce` 2026-07-06 — **hygiene** · pytest-timeout-værn — gør suiten færdig-kørbar (Trin 0)
- `9f8ecc31` 2026-07-08 — **harness** · follow executor extraction — soft-warn call site now in simple_tool_executor (Part C)
- `f5575b9f` 2026-07-09 — **moltbook** · rename secret_payload→raw_body (detect-secrets false positive)
- `5096fcdf` 2026-07-10 — opdatér til Jarvis' interleave-sti (tools før svar) i _build_turn_blocks
- `bbc3d38f` 2026-07-11 — **cockpit** · headless screenshot verification of incidents tab

**Dokumentation**

- `5aac0e75` 2026-07-06 — **db** · db.py dekomponerings-kort + snit-plan (read-only analyse)
- `9f4fc3e0` 2026-07-07 — god-fil-kort — fuldt overblik over 15 filer ≥1500 linjer (read-only)
- `9181f2e8` 2026-07-07 — **readme** · fuld opdatering — J.A.R.V.I.S., Centralen, 122 nerver, 10 nye systemer, Claude agent-par, test-hygiejne
- `4c4b2f37` 2026-07-07 — **spec F** · Matrix-programmerne — Seraph/Persephone/The Twins/Trainman
- `500ebfcf` 2026-07-07 — grounded readonly-analyse af chatview-SSE + auto-compact (#1)
- `a28a7527` 2026-07-07 — **db Fase-2 #4** · dekomponerings-plan for den tanglede kerne
- `50f6e7fc` 2026-07-07 — **spec G** · Self-Review af autonome runs (design)
- `ee4004d8` 2026-07-08 — **spec** · real-time reasoning-interceptor design (approach C, approved)
- `43395661` 2026-07-08 — **plan** · reasoning-interceptor implementation plan (4 phases, TDD, shadow-first)
- `39ac1716` 2026-07-08 — **spec** · harness refactor part 1 — Central-governed earned model-trust + instruction/config
- `ab4c7cda` 2026-07-08 — **plan** · harness Part 1 impl plan — earned model-trust + tiered instruction/config
- `8dccdc01` 2026-07-08 — **harness** · Part B spec — context & tool-result management
- `81da395b` 2026-07-08 — **harness** · Part B plan + spec corrections (aging targets exchanges; live-path compaction)
- `b2e766b2` 2026-07-08 — **harness** · Part C spec — tool concurrency
- `0dfec4e9` 2026-07-08 — **harness** · Part C spec — add ContextVar propagation invariant
- `6011145c` 2026-07-08 — **harness** · Part C implementation plan (4 tasks, ctx-safe parallel exec)
- `904c930e` 2026-07-08 — **self-state** · valence-narrative reconciliation spec (reconcile not sync)
- `0428ab73` 2026-07-08 — **self-state** · add gratitude recency window (Fix 2); defer body-feel staleness (#3)
- `2d514ff2` 2026-07-08 — **self-state** · implementation plan — valence reconciliation + gratitude window
- `a9ae56de` 2026-07-08 — **self-state** · body-feel freshness guard spec (#3)
- `0583a67c` 2026-07-08 — **harness** · Part E spec — LLM permission-classifier (shadow, earned trust)
- `ff74387c` 2026-07-08 — **harness** · Part E implementation plan (5 tasks, shadow permission-classifier)
- `971d4842` 2026-07-08 — **docs-programme** · SP1 audit & taxonomy spec
- `d5a14ef1` 2026-07-08 — **docs-programme** · SP1 implementation plan (auditor + workflow triage + manifest)
- `2fd304c0` 2026-07-08 — **docs-programme** · SP2 canonical structure + index spec
- `36bb8b15` 2026-07-08 — **docs-programme** · SP2 plan + spec safety-correction (no runtime-doc move)
- `acaea629` 2026-07-08 — **docs** · SP2 generated API_REFERENCE (502 routes) + CAPABILITIES (435 tools) + standalone path guard
- `34dce785` 2026-07-08 — **docs** · SP2 fresh README index + architecture/OVERVIEW + move stale snapshots to design-history
- `807d2e74` 2026-07-08 — **docs-programme** · SP3 install/setup guide spec
- `378a3c48` 2026-07-08 — **docs-programme** · SP3 plan + spec (requirements.txt finding + 5 docs)
- `db364798` 2026-07-08 — **docs** · SP3 runtime.json config schema reference (28 keys, placeholders only)
- `d6547c2d` 2026-07-08 — **docs** · SP3 INSTALL + DEPLOYMENT + SECURITY + CONTRIBUTING + README links
- `9656d112` 2026-07-08 — **docs-programme** · SP4 codebase reference spec (generated breadth + coverage audit)
- `7211838c` 2026-07-08 — **plan** · SP4 codebase-reference generator + docstring-coverage audit
- `a6c0da64` 2026-07-08 — **docs** · SP4 generated codebase reference + docstring coverage report
- `fc118194` 2026-07-08 — **docs** · SP4 link api reference + coverage; document code↔doc convention
- `091eb25f` 2026-07-08 — **spec** · SP5 docs drift-sikring — hybrid gate + Central nerve
- `5930597b` 2026-07-08 — **plan** · SP5 docs drift-sikring implementation plan + spec refinements
- `3bb4fcf9` 2026-07-08 — **gap-fill** · add 204 grounded docstrings to apps/routes + scripts (SP4 first pass)
- `7177ecb1` 2026-07-09 — **gap-fill** · document + smoke-test the core/runtime/db_* cluster (351 docstrings, 31 tests)
- `332670e1` 2026-07-09 — **spec** · proactivity-bridge design (hybrid surface, live-governed, kill-switch)
- `c80be0b8` 2026-07-09 — **plan** · proactivity-bridge implementation plan
- `b2a8bac7` 2026-07-09 — **spec** · Agent Smith design — standing self-similarity critic (phrase + decision) + governed modstemme
- `962b5249` 2026-07-09 — **plan** · Agent Smith implementation plan
- `75ca5814` 2026-07-09 — regenerate api docs after adding central_agent_smith module
- `5b7aeb4d` 2026-07-09 — **moltbook** · recovered daemon-skelet (fra bytecode) + observe-nerve-design + rådets dom
- `bf73b043` 2026-07-09 — regenerate API_REFERENCE after Moltbook nerve (drift-gate)
- `d0dc6000` 2026-07-09 — regenerér API-docs efter content_json-ændringer
- `ad0ba267` 2026-07-09 — session-persistence design-spec (leaked-CC-læring #1)
- `a6e95cf4` 2026-07-09 — CollapsedReadSearchGroup design-spec (leaked-CC-læring #2)
- `cd20348e` 2026-07-09 — persisteret progress-træ design-spec (leaked-CC-læring #3)
- `5009de75` 2026-07-09 — paste-store design-spec (leaked-CC-læring #4)
- `52bb094a` 2026-07-09 — self-review-rettelser på 4 specs (in_flight_runs-genbrug, flad progress, allowlist, hash-id)
- `92b0ab5c` 2026-07-09 — **desk** · plan for collapsed read/search tool group (v1)
- `dbede642` 2026-07-09 — **paste** · plan for paste-store feature
- `be375122` 2026-07-10 — **spec** · central acting organs — contradiction_resolver + doc_repair_agent
- `22e62bb7` 2026-07-10 — **plan** · central acting organs — contradiction_resolver + doc_repair_agent (8 tasks, TDD)
- `8490b1a8` 2026-07-10 — **spec** · topic-specific memory loading + strict write discipline (Spec B)
- `a8ae22b2` 2026-07-10 — **plan** · topic-specific memory loading + strict write (Spec B, 6 tasks TDD)
- `1457baf9` 2026-07-10 — **spec** · topic-memory — vækst-værn (route MEMORY.md-promoveringer til topic)
- `055562dc` 2026-07-10 — **notes** · CC-leak learnings vs gaps — kilde-verificeret (CHICAGO/CDCC, KAIROS, state-flags)
- `04ffe0a9` 2026-07-10 — **notes** · leak-note tillæg — CHICAGO/CDCC ægte + tool-fidelity-læren
- `5468439c` 2026-07-10 — **spec** · Morpheus (potentiale-scanner) + Trinity (trust-bridge, auto-optjener m. 8 vaern)
- `0e567d85` 2026-07-11 — **central** · spec — Central Cockpit Redesign Fase 1 (motor+ramme)
- `bbd76f7e` 2026-07-11 — **central** · implementerings-plan — Cockpit Fase 1 (11 TDD-tasks)
- `894f6dbf` 2026-07-12 — **spec** · jc tool-presentation & namespace design
- `ef041009` 2026-07-12 — **spec** · self-review rettelser til jc tool-presentation
- `0bd40ac6` 2026-07-12 — **spec** · lås beslutninger — hard brain-gate, runtime_-præfiks, project_notes fast
- `5a75b381` 2026-07-12 — **plan** · jc tool-presentation & namespace implementation plan
- `16d0f238` 2026-07-12 — **spec** · jarvis-code Claude Code-model redesign (prompt_toolkit)
- `2f90c397` 2026-07-12 — **plan** · jarvis-code prompt_toolkit redesign — 10 TDD-tasks
- `ed87d42a` 2026-07-12 — **plan** · tilføj tool_target (mål fra args) til render — kompakt [tool: target]

**Vedligehold**

- `cc3a6c37` 2026-07-07 — opdatér .secrets.baseline line-numbers (test-fil-edits, kendte false-positives)
- `406f5cb7` 2026-07-08 — **docs** · SP1 phase-1 raw audit output (255 færdig / 61 needs_review / 2 droppet)
- `4c57f8f7` 2026-07-08 — **docs** · SP1 phase-2 triage verdicts (61 needs_review → 28 forældet/5 droppet/28 færdig)
- `e15ee0c7` 2026-07-09 — remove duplicate test file
- `2d864200` 2026-07-09 — **desk** · bump 0.3.26 (strukturerede content-blokke)
- `56d18cb6` 2026-07-10 — **desk** · bump 0.3.32 (4 leaked-CC-features: session-persist/collapsed-read/progress-flad/paste)
- `d7290a27` 2026-07-11 — **cockpit** · fjern ubrugte engine-hjaelpere (markoer-fix blev inline)
- `fd50dd3b` 2026-07-12 — **docs** · regenerate stale API reference docs
- `8331cc86` 2026-07-12 — **docs** · regenerate API reference for assembly_prewarm module
- `f7f45727` 2026-07-12 — **docs** · regenerate API reference for jc-tool-presentation modules

**Tilbagerulning**

- `3e683a5b` 2026-07-11 — **cockpit** · drop bare v2 app/views + --v2 flag — fix EXISTING HUD in place

**Øvrigt**

- `b86d3f7d` 2026-07-06 — **awakening** · council findings — 5 bygbare forbedringer til Centralen
- `1fdc4b89` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `de48effe` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `9150a4c1` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `87a493f3` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `9d28fd7d` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `3d681c73` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `f6aa42f5` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `0347c45b` 2026-07-06 — Merge remote-tracking branch 'origin/main'
- `f45edfb8` 2026-07-07 — test(hygiene) bølge 1: fix 4 state-lækager + 47 forældede tests + 2 ægte runtime-bugs
- `79a4a0e9` 2026-07-07 — test(hygiene) bølge 2: 3 dybere state-lækager + 21 fail-alone filer + slet duplikat
- `62de3a3c` 2026-07-07 — test(hygiene) bølge 3: den store db_*-submodul-lækage + integration-filter (Trin 2)
- `52f69226` 2026-07-07 — test(hygiene) bølge 4: eventbus test_bus-fixture-læk + 5 sidste ægte-fejl
- `043d93f2` 2026-07-07 — test(hygiene) bølge 5: sidste 13 — visible_runs residual-læk + enkeltstående
- `1d98004e` 2026-07-07 — Merge remote-tracking branch 'origin/main'
- `462f7f17` 2026-07-07 — test(hygiene) Step 3: app-init/eventbus flaky-isolation (5 dybe læk)
- `80323851` 2026-07-07 — Merge branch 'main' of github.com:Nickless-cmd/jarvis-v2
- `cc743c85` 2026-07-07 — Merge remote-tracking branch 'origin/main'
- `154b41b2` 2026-07-07 — Merge remote-tracking branch 'origin/main'
- `5d299887` 2026-07-07 — Merge remote-tracking branch 'origin/main'
- `4d73bae4` 2026-07-09 — Merge branch 'main' into feat/leaked-cc-learnings
- `6d93382d` 2026-07-10 — behold Jarvis interleave-fix (bedre end min reorder)
- `6c09de7d` 2026-07-10 — Merge remote-tracking branch 'origin/main' into feat/leaked-cc-learnings
- `768f4072` 2026-07-10 — Merge remote-tracking branch 'origin/main'
- `943344d2` 2026-07-11 — Central HUD fikset paa stedet (markoer/scroll/tomme-faner/approvals/throttle)
- `6a17a90f` 2026-07-11 — **prompt-assembly** · sentinel-gated fuld timing-dump
- `f1d09778` 2026-07-12 — merge origin/main (jc-tool-presentation feature) into container main
- `6f973297` 2026-07-12 — session switching: /session list|select|delete + handle_slash_command returns 6 values

### Uge 29 · 13.–19. juli — 375 commits

**Nyt**

- `1a925e3a` 2026-07-13 — **prewarm** · traffic-gate helper — seconds since last real deepseek call
- `387348a5` 2026-07-13 — **prewarm** · _should_prewarm gate (traffic + cross-process dedup)
- `f711936a` 2026-07-13 — **prewarm** · gate prewarm_once + cross-process mark + min-interval 180s (kills 270M-token runaway)
- `72caa210` 2026-07-13 — **deepseek** · thinking-mode via request param (deepseek_request_for_thinking_mode), not deprecated alias
- `4f21d1e2` 2026-07-13 — **visible** · thread thinking_mode/extra_body → non-thinking on v4-flash (empty-bug recovery off deprecated deepseek-chat)
- `b5947a7f` 2026-07-13 — **cost** · DeepSeek pris-tabel + compute_cost_usd i record_cost (WS2 task 1+2)
- `d789acfc` 2026-07-13 — **cost** · /central/cost surface + jc cost (WS3 — gør regnskabet synligt)
- `69500cbb` 2026-07-13 — **dispatch** · typet dispatch-status enum (A1)
- `80bf5ef6` 2026-07-13 — **dispatch** · robusthed-konvolut + plausibilitets-guard (A2)
- `2cb126db` 2026-07-13 — **cost** · log agent-dispatch spend via record_cost(lane=agent) (A4)
- `6b8e6e64` 2026-07-13 — **central** · agent_result-nerve + envelope-timeseries + typet agent_blocked (B1+B2)
- `fb1a9643` 2026-07-13 — **central** · /central/agents + /central/council surfaces + jc + Mind-hub-tabs (B3)
- `dc838e3a` 2026-07-13 — **trigger** · persisteret signal-baseline + cold-start-guard (C1)
- `846dde81` 2026-07-13 — **trigger** · visible↔autonom lease, marker-default (C4)
- `13404efd` 2026-07-13 — **trigger** · rekursions-guard — spawn-dybde+fan-out+concurrency (C6)
- `1f6eeca5` 2026-07-13 — **spec** · event-drevet omlægning — Jarvis' indre liv som event-drevet arkitektur
- `572b4a1b` 2026-07-13 — **trigger** · idempotens+dead-man+circuit-breaker+budget-loft (C3)
- `dc2de1a6` 2026-07-13 — **trigger** · delta-trigger m. hysterese+absolut-gulv+debounce+coalesce (C2)
- `051277d1` 2026-07-13 — **spec** · bilag 1 — kortlægning af Jarvis' indre liv (hvor data bor i dag)
- `9364c227` 2026-07-13 — **trigger** · event-trigger shadow-meter på heartbeat (C5) — observe-only, nul LLM
- `9e6103ab` 2026-07-13 — **central** · shadow-experiment-registry + review-reminder (så vi ikke glemmer shadow-vinduer)
- `86168a2c` 2026-07-13 — **fase2** · surprise rå-signal-mode bag raw_signal_mode-flag (Lag 1 — rå divergens ikke narration)
- `66819c11` 2026-07-13 — **fase2** · somatic rå-signal-mode bag raw_signal_mode-flag (Lag 1 — rå tal ikke label, skip narration-LLM)
- `4e4212e1` 2026-07-13 — **central** · rig gate-logning (session/run/fil/linje/detected/pattern) + mønster-læring så Centralen kan bryde gentagne gate-mønstre
- `8a631a46` 2026-07-13 — **central** · force-persist gate-vane ved tærskel-krydsning — habit-tilstand overlever restart uanset timing
- `afb3d6dc` 2026-07-13 — **fase2** · experienced_time rå-signal-mode (Lag 1)
- `b0d29c6e` 2026-07-13 — **fase2** · absence rå-signal-mode (Lag 1)
- `6f14bd3d` 2026-07-13 — **fase2** · conflict rå-signal-mode (Lag 1)
- `709fafd2` 2026-07-13 — **fase2** · desire rå-signal-mode (Lag 1)
- `236c50b2` 2026-07-13 — **fase2** · event_gate — delt non-LLM gate for generative daemons (fyr kun ved ægte ændring, fail-open)
- `e946cf41` 2026-07-13 — **fase2** · existential_wonder event-gated — retire blind 24h-timer, behold latest_wonder-output (Lag 7, review-korrektion)
- `43da8160` 2026-07-13 — **fase2** · meta_reflection event-gated (Lag 5)
- `80ff9b5d` 2026-07-13 — **fase2** · creative_drift event-gated (Lag 5)
- `42963e9e` 2026-07-13 — **fase2** · thought_stream event-gated (Lag 5)
- `68c16911` 2026-07-13 — **fase2** · reflection_cycle event-gated (Lag 5)
- `81c775ed` 2026-07-13 — **fase2** · user_model event-gated (Lag 5)
- `456231a2` 2026-07-13 — **fase2** · aesthetic_taste event-gated (Lag 5)
- `eae4e6b6` 2026-07-13 — **fase2** · narrative_summary event-gated (Lag 5)
- `b451cf91` 2026-07-13 — **fase2** · irony event-gated (Lag 5)
- `bcec2383` 2026-07-13 — **trigger** · durabel shadow-telemetri (overlever restart) + kør delta-tjek hvert heartbeat — så 24t-kalibrering faktisk akkumulerer
- `1629004f` 2026-07-14 — **agent-step** · flag helper + module-level observability seams (inert)
- `643afeb7` 2026-07-14 — **costs** · additive user_id column (DEFAULT '')
- `26ffc9e0` 2026-07-14 — **costs** · record_cost optional additive user_id
- `7d1e176b` 2026-07-14 — **agent-step** · additive structured envelope + cost_usd on response & stream done
- `fd9c5dc0` 2026-07-14 — **agent-step** · flag-gated agent_step nerve + note_empty_completion at model seam
- `de34a3cc` 2026-07-14 — **runtime** · plumb finish_reason through openai-compat adapter + stream iterator
- `04a47339` 2026-07-14 — **agent-step** · flag-gated per-caller workspace scoping (identity/memory) + cache-key isolation
- `776511f1` 2026-07-14 — **agent-step** · flag-gated record_cost(lane=agent,user_id) at seam + block-aware multimodal content extraction
- `c70d430a` 2026-07-14 — **spec** · provider/model management system — auto-discovery, task-scoring, Centralen integration, 4 OpenCode providers, 18 gratis modeller
- `892a7ab1` 2026-07-14 — **skill-autosurface** · owner-approved allowlist governing jarvis-code auto-surfacing (flag default OFF)
- `83798d4c` 2026-07-14 — **jc-catalog** · promote skill_gate to DEFAULT_COMPANIONS
- `c54fa9c4` 2026-07-14 — **agent-loop** · inject owner-approved skill catalog + skill_gate activation + CC-tool legend into system prompt
- `dade0e60` 2026-07-14 — **skill-gate** · optional autosurface arg restricts matching to owner-approved allowlist
- `f411d52b` 2026-07-14 — **fase4** · reasoning replay across tool rounds with pairing invariant (flag-gated)
- `09736ebd` 2026-07-14 — **fase4** · <env> block — client sends cwd/git/os/date/commits, server injects (flag-gated)
- `dd8c0914` 2026-07-14 — **fase4** · prompt-cache stable-prefix contract + hit/miss telemetry on agent/step (flag-gated)
- `6202ccf1` 2026-07-14 — **fase4** · prompt-cache stable-prefix contract + hit/miss telemetry (flag-gated)
- `829900ae` 2026-07-14 — **fase4** · harness behavioural contract in agent/step system prompt (flag-gated)
- `ea34d1ee` 2026-07-14 — **spec** · Requesty.ai tilføjet som 17. provider — endpoint, model og bekræftet svar, ~270 gratis modeller
- `f43c6357` 2026-07-14 — **fase5** · owner-only privilege gate on agent/step approval-timing axis
- `d168c652` 2026-07-14 — **fase5** · verdict-ledger logging on forwarded brain-write denies
- `6dddcf85` 2026-07-14 — **spec** · v8 — eksisterende fundament dokumenteret + agent pool router spec samlet som én enhed
- `59118d2c` 2026-07-14 — **spec** · provider management v8 — 17 providers, ~270 gratis modeller, Centralen error-routing & rotation
- `586ea06e` 2026-07-14 — **fase5** · audit trail — per-user/per-tool execution log (flag-gated)
- `3de18cb2` 2026-07-14 — **fase5** · provider XML tool-call fallback (flag-gated)
- `066a0f9b` 2026-07-14 — **fase5** · per-tool telemetry to eventbus (server half, flag-gated)
- `27778004` 2026-07-14 — **fase6** · server fault-injection regression tests for /v1/agent/step
- `1837f424` 2026-07-14 — **fase6** · multi-user scoping regression on /v1/agent/step + close a real gap
- `8fe3f13a` 2026-07-14 — **fase6** · migration-trigger gate script + signed-off go/no-go checklist
- `1eb7bd96` 2026-07-14 — **cheap-lane** · wire 4 live-verificerede providers ind i pool
- `3a1de301` 2026-07-14 — **cheap-lane** · cheap_lane_floor aldrig-tor-bund (spec Fund 4)
- `e14bcba7` 2026-07-14 — **cheap-lane** · balancer aldrig-tor-bund + SQLite-kvote + Central-observe (Fund 4+5, Task 3-5)
- `1300c5be` 2026-07-14 — **central-route** · unified router + proaktiv headroom-rotation (Fund 2+3, Task 7-8)
- `89967b90` 2026-07-14 — **central-route** · shadow-wire selection + provider_history (Task 9-10)
- `0571e409` 2026-07-14 — **agent-pool** · route_agent_task via central_route + kvalitets-laering (Task 11-12)
- `f5e64f50` 2026-07-14 — **provider** · gated auto-discovery + selvhelbredelse (Task 13-15)
- `d85297c6` 2026-07-14 — **cheap-lane** · deepseek ud af routbar pool (routable=False) + central_route honorer task_kind
- `84f54145` 2026-07-14 — **agent-step** · _resolve_target router gennem agent-pool (flag-gated) — agent:explore fra poolen
- `06418e42` 2026-07-14 — **providers** · gemini + cloudflare via OpenAI-compat endpoints (tool_calls virker)
- `78a74638` 2026-07-14 — **providers** · GitHub Models (gratis GPT-5/o4-mini/DeepSeek-R1) + OVHcloud (anon) i pool
- `83399458` 2026-07-15 — **central-route** · cost-bevidst routing — gratis frit valg, betalt kraever rigtig opgave
- `099be707` 2026-07-15 — **providers** · Kilo Gateway i cheap lane + pool (FreeLLMAPI-extraction)
- `3db9e2b4` 2026-07-15 — **providers** · Z.ai/Zhipu glm-4.5-flash i cheap lane + pool (gratis)
- `cbdb46ff` 2026-07-15 — **providers** · HuggingFace Router i cheap lane + pool (Bjørns hf-token)
- `0092aa55` 2026-07-15 — **providers** · Reka reka-edge-2603 i cheap lane + pool (trial-credit, lavt loft)
- `20392b01` 2026-07-15 — **providers** · SiliconFlow Qwen3-8B/Qwen2.5-7B i cheap lane + pool (empirisk gratis)
- `a1f0a7e1` 2026-07-15 — **providers** · BazaarLink auto:free i cheap lane (perpetual gratis)
- `36177502` 2026-07-15 — **event-drevet** · SPEC 1/16 100% — Fase 6 gate + retire gamle daemons
- `d7f8e85e` 2026-07-15 — **specs** · SPEC 2-6/16 — cluster-daemon, multiuser, lag4, self-registering, llm-economy
- `8150388e` 2026-07-15 — **provider-router** · SPEC 7/16 — balancer central_route-hook + catalog + scheduling
- `f4395704` 2026-07-15 — **cluster** · 2/10 innervoice — 6 LLM-daemons → ét gate, 6 gamle pensioneret
- `30592f27` 2026-07-15 — **cluster** · 3/10 affect — 5 daemons → ét gate, 5 gamle pensioneret
- `7dc23148` 2026-07-15 — **cluster** · 4/10 narrative — 5 daglige self-historie-daemons → én familie
- `05b78da4` 2026-07-15 — **cluster** · 5/10 cognition — 4 daemons → én familie
- `c8d512fb` 2026-07-15 — **cluster** · 6/10 memory — 8 daemons → én familie (nyt modul, split v. 1500L)
- `9a55b9b2` 2026-07-15 — **cluster** · 7/10 aesthetic — 2 daemons → én familie
- `d0dd3409` 2026-07-15 — **cluster** · 8/10 relation — 3 daemons → én familie
- `ddf4bddc` 2026-07-15 — **cluster** · 9/10 projects — 4 daemons → én familie
- `e4241c77` 2026-07-15 — **cluster** · 10/10 infra — 8 daemons → én familie (KAMPAGNE KOMPLET)
- `8c2b3218` 2026-07-15 — **cluster** · somatic shadow→live + retire 3 — alle 10 familier konsistente
- `12338187` 2026-07-15 — **jc-tool-catalog** · Fase 0 — eksplicit execution-lokation (client|runtime|server)
- `8b230503` 2026-07-15 — **visible-runs** · Fase 1 fundament — klient-tool-delegering (state+modul+endpoint)
- `6e5d78f9` 2026-07-15 — **agent-step** · Fase A1 — dynamic-tail cache-split (flag-gated, default off)
- `aa107f83` 2026-07-15 — **agent** · Fase B — tur-absorb endpoint (klient-drevet tur → fuld hjerne)
- `d9d4b48b` 2026-07-15 — **shared-sessions** · Fase C1 — persist klient-tur til delt server-session
- `3b6083d7` 2026-07-15 — **agent-live** · C2b server — turn-begin/turn-end liveness for klient-drevet tur
- `1539ecea` 2026-07-15 — **agent-live** · Lag 3 — token-for-token follow (jc deltas → v2-frames)
- `c378944f` 2026-07-15 — **matrix-nudge** · fuldfør + fiks unaddressed-wiring i nudge-tools
- `5ac45a15` 2026-07-15 — **tools** · værn mod over-escaped triple-quotes i .py-writes (LLM-artefakt)
- `80fc41bb` 2026-07-16 — **cheap-lane** · self-heal — re-probe fastlaaste providere (maa aldrig doe)
- `81022b1a` 2026-07-16 — **cheap-lane** · tilføj AionLabs-provider (free-tier, OpenAI-compat)
- `03776c31` 2026-07-16 — **cheap-lane** · udvid HF-modeller + self-heal probe zero-row-providere
- `09cf1207` 2026-07-16 — **agent-pool** · tilføj FreeTheAi som agent-reserve (gpt-5.5-mini/grok/deepseek-v4)
- `711a1087` 2026-07-16 — **freetheai** · nudge Jarvis når checkin-gated provider er låst
- `96e5b4ad` 2026-07-16 — **cheap-lane** · tilføj Cohere (vedvarende gratis, research-vinder)
- `53b6bb9e` 2026-07-16 — **cheap-lane** · tilføj Alibaba Model Studio (SG workspace, stor burst-kapacitet)
- `3f1b99d3` 2026-07-16 — **spec** · implementation plan for agent tool-delegation v3
- `2a722178` 2026-07-16 — **cheap-lane** · slot_id inkluderer auth_profile (P0 fundament)
- `17318ad7` 2026-07-16 — **cheap-lane** · count cheap-provider invocations per auth_profile
- `70c94ddc` 2026-07-16 — **cheap-lane** · per-profile daily counting end-to-end
- `3d6588aa` 2026-07-16 — **auth** · auth_profile_scan — discover ready provider profiles
- `8fde4b63` 2026-07-16 — **cheap-balancer** · multiprofil slot-pool bag flag (Task 5)
- `65d6e6bb` 2026-07-16 — **cheap-selection** · _configured_cheap_candidates yields one candidate per (provider, ready profile) when flag ON
- `015957fa` 2026-07-16 — **egress** · per-(provider,auth_profile) egress resolution + slots carry egress
- `cdd901d7` 2026-07-16 — **egress** · Task 8b — inject proxy per egress + hard leak guard
- `0c7e8205` 2026-07-16 — **non-visible** · ollama→cheap-pool→floor fallback chain (Task 9)
- `7f444924` 2026-07-16 — **autonomous** · stream-fejl → gratis cheap-lane pool (Task 10)
- `6e1b83c8` 2026-07-16 — **non-visible** · global leaky-bucket rate cap foran cheap-lane pool
- `974f2f80` 2026-07-16 — **cheap-balancer** · Task 12 — SlotState learns daily_observed, safely
- `07641631` 2026-07-16 — **cheap-balancer** · Task 13 — predictive skip via learned daily ceiling
- `15be0dbf` 2026-07-16 — **cheap-lane** · Task 14 anti-jag stale marking behind adaptive flag
- `2214d7c6` 2026-07-16 — **agents** · agents_summary gains full model roster
- `9c57d9d0` 2026-07-16 — **central-agents** · expose model roster on /central/agents surface
- `2a11c6f4` 2026-07-16 — **balancer** · enrich balancer_snapshot with egress, status, header (Task A2)
- `09d8fbde` 2026-07-16 — **central-cli** · agents roster consumption + balancer datasource (Task B1/B2)
- `632d43b7` 2026-07-16 — **central-cli** · Agents tab renders model roster, greys inactive rows (Task C1)
- `2821f8b0` 2026-07-16 — **central-cli** · add Balancer tab (cheap-lane pool) after agents
- `f0f9bbfe` 2026-07-16 — **central** · POST /central/agents/{id}/cancel + /pause (A3)
- `b90b72ce` 2026-07-16 — **central-cli** · HUD row actions — agent pause/abort + balancer reset/disable/enable
- `e5410cc7` 2026-07-16 — **settings** · tool-result lifecycle fields (default off)
- `c6a21ded` 2026-07-16 — **lifecycle** · pure helpers — run boundaries + tool-token estimate
- `d5187af5` 2026-07-16 — **lifecycle** · compute_new_floor — hybrid runs/tokens + hysteresis, monotonic
- `b8c45667` 2026-07-16 — **lifecycle** · cold_floor storage — isolated table, monotonic upsert
- `7a6785b0` 2026-07-16 — **lifecycle** · evaluate_and_advance glue — run-end single writer, fault-tolerant
- `5231a35d` 2026-07-16 — **chat** · thread integer id through growing-window (metadata, byte-neutral)
- `ad4bda16` 2026-07-16 — **tool-result** · stub render mode — reference-only, byte-stable without disk
- `f6b2d4c0` 2026-07-16 — **transcript** · cold-tier stub rendering behind cold_floor (flag-gated, byte-stable)
- `1793ed6d` 2026-07-16 — **visible-runs** · advance tool cold_floor at run-end (guarded, small)
- `ba7cd75b` 2026-07-17 — **aging** · token-trigger safety-valve — stepped within-run aging (cache-safe)
- `84989115` 2026-07-17 — **central** · truthful runtime_liveness in status — kill false 'inactive services'
- `6f77c763` 2026-07-17 — **incidents** · dedup flooding producers (bump-if-open) — network/flags/autonomous
- `1ad631ce` 2026-07-17 — **events** · retention — bound the unbounded events table (2.56M rows/2.7GB)
- `7fe229b9` 2026-07-17 — **db** · general table-retention — auto-prune safe telemetry tables
- `3dc475f8` 2026-07-17 — **db** · add recency-bounded learning tables to auto-retention (60d)
- `3e4a606f` 2026-07-17 — **dispatch** · per-role max_turns i ROLE_PLAN + default MAX_AGENT_TURNS i spawn_agent_task
- `5d6ae118` 2026-07-17 — **agent-transcript** · per-agent JSONL transcript + metadata sidecar + resume flow
- `1a92884a` 2026-07-17 — **agent** · complete maxTurns-per-subagent (point 1/6)
- `8515aa13` 2026-07-17 — **awareness** · nudge Jarvis when his autonomous runs finish/fail (D)
- `942fcda4` 2026-07-17 — **prompt** · model-pool status block so Jarvis knows agent-pool vs cheap-lane (C)
- `bcb32388` 2026-07-18 — **compaction** · real live compaction in visible lane (model-aware, round-atomic)
- `f11f0654` 2026-07-18 — **compaction** · honest context-ring — real total in tooltip
- `e6fa58f6` 2026-07-19 — **obs** · infer ollama-cloud prefill cache on visible lane (close blind spot)
- `e9b566ff` 2026-07-19 — **retention** · keep-latest-N prune for versioned cognitive snapshot tables
- `e806ad88` 2026-07-19 — **agent-cache** · prepend-frozen volatile block + return it (option B, flag-gated)
- `0fe0721d` 2026-07-19 — **agent-cache** · also emit volatile_context in the streaming done event
- `2a7c8c9b` 2026-07-19 — **pathB** · local-tool broker + /chat/tool_results endpoint (pause-and-resume)
- `07bfbbcb` 2026-07-19 — **pathB** · server-owned code-lane transcript + local-exec tool roundtrip

**Rettelser**

- `4255e4e5` 2026-07-13 — **inner-llm** · v4-flash + non-thinking param instead of deprecated deepseek-chat alias
- `915d84be` 2026-07-13 — **deepseek** · send-grænse-normalisering — deepseek-chat/reasoner→v4-flash+thinking-param
- `df301956` 2026-07-13 — **deepseek** · reassign model på send-grænse så cost-logging labeler v4-flash ærligt
- `3d2c5a14` 2026-07-13 — **costs** · normalisér deepseek-chat/reasoner label→v4-flash ved record_cost-chokepoint
- `6e66d597` 2026-07-13 — **cost** · log costs-række fra relevance-lanen (WS2 komplet-logging)
- `1229dce3` 2026-07-13 — **cost** · log costs-række fra inner-llm + reasoning-tokens som output (WS2)
- `a4a7cfde` 2026-07-13 — **cost** · log costs-række fra daemon-lanen + fjern dobbelt-egress (WS2)
- `0469f0a3` 2026-07-13 — **cost** · log costs-række fra cheap_lane_balancer (WS2 dominerende hul)
- `56594a88` 2026-07-13 — **dispatch** · ægte typet konvolut i agent_runtime_base — fjern hardkodet completed (A3, K2)
- `8b3b5b85` 2026-07-13 — **cost** · ét cost-log-site pr. model-kald m. lane-param — fjern agent→pool dobbelt-tælling + luk primary-direct-hul (A4b)
- `38a57058` 2026-07-13 — **central** · lazy-hydrate gate-mønster-læring ved første brug — læring overlever restart
- `ff090175` 2026-07-13 — **test** · _reset rydder også durabel snapshot — lazy-hydrate genindlæser ikke tidligere tests data
- `586ba6ff` 2026-07-13 — **test** · patch ægte event_gate via setattr (ikke sys.modules-injection) — robust mod import-rækkefølge, grøn i samlet kørsel
- `650ee220` 2026-07-13 — **central** · verdict-ledger akkumulerer nu ægte counts (var stuck ~1-3/gate) — groundbar flip-data
- `7e13ab4a` 2026-07-13 — **central** · agent_smith eskalerer nu DRIFT ikke frekvens — benign routine forbliver rung 1, sikker at flippe
- `dc069b3b` 2026-07-14 — **event-trigger-shadow** · tik i ubetinget daemon-sektion (% 6 ≈ 3 min) i st. f. aktivitets-gated influence-trace
- `1e9bb6cb` 2026-07-14 — **heartbeat** · tik LLM-frie basis-daemons på idle-stien — inderlivet frøs ~16t
- `556ac63a` 2026-07-14 — **prompt-assembly** · cap cognitive_state-build (~2.5s) + fald tilbage til cachet injection — kold-vindue-værn
- `d042ef68` 2026-07-14 — **ollamafreeapi** · skift model fra gpt-oss:20b->deepseek-r1 — gpt-oss:20b timed ud på inferens, deepseek-r1 svarer 150 tok/s
- `c99b0591` 2026-07-14 — **docs-gen** · scope api_docs_gen dot-dir filter to repo-relative path; regenerate stale docs
- `5d3f0fff` 2026-07-14 — **spec** · provider/model management v2 — self-review fixes (test-strategi, gradient scoring, quality-måling, rollback, dedup-logik, auth SPOF, freemodel defineret, rate-limit blocker)
- `45223eb4` 2026-07-14 — **spec** · provider/model management v3 — live-tested Groq+Gemini, reelle tal, key-fixes, fjernet FreeModel
- `aa3d46d9` 2026-07-14 — **spec** · provider/model management v4 — NVIDIA NIM (+120), Cloudflare (61), Arko (v3/messages) — alle genoplivet og dokumenteret
- `8089c066` 2026-07-14 — **spec** · provider/model management v4 — OpenRouter/Sambanova live-testet, komplet provider-audit, 200+ gratis modeller dokumenteret
- `94aefeb9` 2026-07-14 — **spec** · provider/model management v5 — OpenRouter (3 bekræftet), Sambanova (død), fjernet FreeModel
- `1e35acf1` 2026-07-14 — **spec** · provider/model management v6 — AIHubMix (gpt-4o-free), GitHub Models, Mistral AI, OVHcloud, Kilo Code tilføjet; Cerebras (død); 250+ gratis modeller fordelt på 13 providers
- `b9c8789f` 2026-07-14 — **spec** · provider/model management v7 — Cerebras genoplivet (User-Agent workaround), 14 providers, ~260 gratis modeller
- `8572e55e` 2026-07-14 — **spec** · provider/model management v7 — TokenRouter (insufficient quota), 15 providers testet, ~260 gratis modeller
- `2dfd5863` 2026-07-14 — **spec** · provider/model management v7 — Clinebot tilføjet (16. provider, 5 bekræftede modeller), ~265 gratis modeller
- `78cca595` 2026-07-14 — **db** · db_query restores pooled connection row_factory — decision_gate ValueError (Central RED)
- `8f2e5573` 2026-07-14 — **flags** · bool-flag læst robust — streng "off" gav dispatch TÆNDT
- `f9f7f509` 2026-07-14 — **cheap-lane** · cerebras gemma-first (non-reasoning), demoter flaky cline til fallback
- `d56e502c` 2026-07-14 — **cheap-lane** · selection-pool falder til bund frem for at rejse (Fund 4)
- `66d204ce` 2026-07-14 — **central-route** · agent-lane router kun til openai-chat (luk deepseek-fallback-lækage)
- `f5f4cf95` 2026-07-14 — **cheap-lane** · balancer inkluderer static_models-providers (inderliv får hele poolen)
- `f572e860` 2026-07-14 — **providers** · opencode aktuelle 5 gratis Zen-modeller (udfasede erstattet)
- `880a1801` 2026-07-14 — **adapter** · no-auth (OVHcloud anon) + max_completion_tokens for GPT-5/o-series
- `749b22d7` 2026-07-15 — **copilot** · copilot-premium til verificeret-tilgaengelige modeller
- `56d31376` 2026-07-15 — **cheap-lane** · betalte providers UDE af daemon/balancer (kun via central_route allow_paid)
- `ad1d4eda` 2026-07-15 — **providers** · udled openai-compat-set fra protocol (alle nye providers eksekverbare)
- `f8a89f41` 2026-07-15 — **identity** · sonnet-korrektion — bar 'sonnet' → identitets-kontekst-fraser
- `34a695cd` 2026-07-15 — **cheap-lane** · tom auth_profile for keyless provider crashede inderlivet
- `9577edb9` 2026-07-15 — **prewarm** · event-drevet gate — dræb 292M-tokens/13d cache-warmer-burn
- `b04eb04f` 2026-07-15 — **balancer** · pålideligheds-vægtning + ærlig fejl-tælling (Bjørn)
- `cc39eb39` 2026-07-15 — **cheap-lane** · decision_review re-review cascade (halvdelen af daemon-LLM) + inner dedup
- `765da0d6` 2026-07-15 — **agent-step** · rolle-aware chat-model — deepseek/ollama, IKKE agent-poolen
- `3f144c81` 2026-07-15 — **memory-scope** · owner-scoping — udled ejerens user_id naar jarvis-code sender tomt
- `d81a125f` 2026-07-15 — **agent-live** · registrér jarvis-code-tur i run_event_log (desk-poller/liveness)
- `b74848c1` 2026-07-15 — **cadence** · Trainman + continuity_healer var permanent blokeret (inverteret dep-priority)
- `2e272ee6` 2026-07-15 — **merovingian** · recalibrer nær-tærskel 0.6→0.55 (var over confidence-loftet)
- `c6af64f9` 2026-07-16 — **cheap-lane** · self-heal re-prober ENHVER usund provider u. cooldown (ikke kun terminal-liste)
- `7c33505b` 2026-07-16 — **cheap-lane** · provider_auth_ready normaliser tom profil ''→'default'
- `8f3f4f60` 2026-07-16 — **cost** · fjern betalt deepseek fra cheap-lane floor → keyless gratis
- `1a63eda4` 2026-07-16 — **agent-step** · byg prompt-assembly i ejerens user_context → workspace-recall virker
- `eba0ae72` 2026-07-16 — **recall** · propagér user_context til recall-worker-tråde (contextvars)
- `0fed8464` 2026-07-16 — **autonomy** · stop kimi-runaway + honor paid-deepseek-only-in-visible rule
- `7fb0811f` 2026-07-16 — **agent-lane** · videregiv deepseek prompt-cache-split til record_cost
- `83296722` 2026-07-16 — import _read_api_key in simple_tools_native.py to restore HA tool
- `e49870a6` 2026-07-16 — **cheap-lane** · classify kilo/ovhcloud/pollinations as public proxies + honour default-tier "paid first, public fallback"
- `28ec8b65` 2026-07-16 — **auth-scan** · kun ægte konto-profiler (default/accountN) bliver slots
- `030ad902` 2026-07-16 — **prompt-cache** · flyt 5 'tail-anchored' sektioner til ægte hale (_dyn_tail)
- `b73dd2b5` 2026-07-16 — **settings** · wire tool-result lifecycle fields into load_settings (runtime.json flip)
- `1ca34ff4` 2026-07-17 — **transcript** · align cold-tier boundary with accounting (id<=floor)
- `42f8d6c7` 2026-07-17 — **agent-lane** · kill silent cut-off — surface reasoning + visible note on empty
- `9bce84a3` 2026-07-17 — **cost** · route inner-voice enrichment to free ollama, off paid deepseek-API
- `d19d8a73` 2026-07-17 — **cache** · tail-anchor daily-notes + self-change sidecars — visible 36%→~92%
- `dbe00be7` 2026-07-17 — **agent** · backend dispatch synthesises at round cap (not empty BLOCKED)
- `f860516e` 2026-07-17 — **agent-step** · route flagged subagent steps through the agent-pool
- `c0515a24` 2026-07-17 — **agent-step** · default subagent pool to FREE, paid only for code-write types
- `99381db6` 2026-07-18 — **routing** · block code-models on autonomous lane + deprioritise timing-out zai
- `164b2d3f` 2026-07-18 — **stream** · close v2 stream on message_stop, not mark_done (post-response hang)
- `a24d88c7` 2026-07-18 — **desk** · wire compaction into CODE mode (CodeView), not just chat
- `2e891421` 2026-07-18 — **compaction** · hard timeout + input cap on summary — never hang for minutes
- `575555d2` 2026-07-18 — **assembly** · cap uncapped embedding/recall resolves — no more 28s hot-path freeze
- `33905267` 2026-07-18 — **assembly** · turn-scoped cache — tool turns assemble ONCE, not twice
- `a508e493` 2026-07-18 — **assembly** · key turn-cache on latest user-msg id, not message text
- `14628369` 2026-07-18 — **stream** · background the post-answer outcome-persist — kills the tool-turn hang
- `65cbabec` 2026-07-19 — **router** · never apply learned model-pref to owner/member interactive visible

**Omstrukturering**

- `b95879af` 2026-07-15 — **council** · dommeren nudger, foreskriver ikke roller — Jarvis konstruerer selv
- `2cd6b830` 2026-07-15 — **matrix** · Smith dynamisk linje i ensemble + ryd overflødig sign-off-special-case
- `7194a120` 2026-07-19 — **pathB** · broker wait() internal-lookup + collect_results batch helper

**Ydelse**

- `1827bdb6` 2026-07-17 — **eventbus** · batch writer commits — collapse burst commits into one txn
- `89b86207` 2026-07-18 — **recall** · batch memory dedup embeddings — 14 serial ollama calls -> 1-2
- `c465f22d` 2026-07-18 — **recall** · cache query embeddings — same text embedded 4-5x/turn -> 1
- `119cc275` 2026-07-18 — **stream** · adaptive poll for fluid v2 streaming + remove temp diag
- `641ca709` 2026-07-18 — **recall** · batch memory_search corpus embeddings — 85-229 calls -> 1
- `1698f5b8` 2026-07-18 — **assembly** · unify experience retrieval onto shared nomic GPU embedder
- `ea0ac148` 2026-07-18 — **recall** · keep memory_search index in memory (skip per-turn unpickle)
- `9590482b` 2026-07-18 — **assembly** · cache cognitive frame (45s TTL) + skip wasted NL relevance on visible
- `93bf8fac` 2026-07-18 — **assembly** · parallelize 3 heaviest seg_q3 sections + pre-warm query embed
- `efd35153` 2026-07-18 — **cache** · move volatile dynamic tail from system message to last user message
- `73406342` 2026-07-18 — **wal** · periodic wal_checkpoint(TRUNCATE) in 6h maintenance tick

**Tests**

- `7089dcf8` 2026-07-16 — **cheap-lane** · confirm account2 = equal parallel tier (Task 8c)
- `63d7d995` 2026-07-16 — **pool** · Task 15 shadow-safety guard + light Central observability
- `3a393b04` 2026-07-16 — **pool-resilience** · acceptance suite locks 5 spec invariants
- `e171fa42` 2026-07-16 — **lifecycle** · e2e — old tool becomes cold stub, still rehydratable

**Dokumentation**

- `81366609` 2026-07-13 — **spec** · LLM-økonomi — tracking-fix, prewarm-oprydning, model-tiering
- `abda97b5` 2026-07-13 — **spec** · self-review — v4-pro standard, composer think-felt, universal logging (Fase 2)
- `7800392f` 2026-07-13 — **plan** · prewarm-gate + deepseek-chat-migration (WS1+WS4, urgent slice)
- `1441e8ac` 2026-07-13 — **spec** · Jarvis+Bjørn-feedback — daemon-lanes, WS2/8-caveat, WS6 omdøbt
- `96927c2d` 2026-07-13 — **spec** · WS6 varians-gate — event-drevne daemons (Bjørns indsigt)
- `bcc2394f` 2026-07-13 — **spec** · WS5 indsnævret — v4-pro KUN i owner-visible lane, alt andet flash
- `0cd404e4` 2026-07-13 — **plan** · WS2 sandt cost-regnskab — 6 TDD-tasks (pris-tabel+compute+3 missing sites)
- `768a7263` 2026-07-13 — Claude orkestrerings-reference — første-hånd + officiel-dok krydstjek
- `596b04b5` 2026-07-13 — tilføj klient-side loop (poll/supervisér/selv-væk) + to-overflade-syntese
- `ebaf35cc` 2026-07-13 — komplet toolbox-audit (15+ tools) + robusthed-kontrakt (DEL 5)
- `cbd0214d` 2026-07-13 — self-review — renumbér DEL 4, align tool-scoping-row m. §4.4, tilføj Bjørns krav (dead-code/Central-wiring/tests-edges-docs) til checklist
- `138da84e` 2026-07-13 — rådets samlede fund (5 linser) + hærdnings-kontrakt
- `bf01d3c7` 2026-07-13 — **plan** · dispatch-redesign Fase 1 — bite-size TDD, rådets byg-rækkefølge
- `6b61a4c1` 2026-07-13 — Claudes review af Jarvis' event-drevne spec — kode-grounded + rettelser + multi-user + cost-sandhed
- `43c94f76` 2026-07-13 — **spec** · rettelser til Jarvis' event-spec (bevar hans stemme) + bilag2 multi-user
- `678c2733` 2026-07-13 — **spec** · selv-registrerende nervearkitektur — governed auto-plugin
- `0dc88ba3` 2026-07-13 — **spec** · identitets-tiers + no-leak-governance for auto-plugin (Bjørn 13. jul)
- `87b885de` 2026-07-13 — **spec** · Central-kontrakten — ubrydelige krav for nyt cluster/nerve (Bjørn 13. jul)
- `8681eadb` 2026-07-13 — **spec** · self-review — MIGRATION af eksisterende nerver ind under kontrakten (hele pointen) + 5 rettelser
- `b39d4254` 2026-07-13 — **spec** · migrations-tempo besluttet = Boy Scout (Jarvis' valg) + Fase-2-synergi bærer de tunge nerver
- `9e648ee9` 2026-07-13 — **spec** · cluster-daemon-konsolidering — ~40 daemons→~10 familier (Bjørn 14. jul)
- `fecebecd` 2026-07-13 — **spec** · tre kontrakt-typer (gate-cluster/daemon-cluster/nerve) — Bjørn 14. jul
- `c67b4488` 2026-07-13 — **spec** · Lag 4 awareness-redesign — JARVIS' eget design, transskriberet (cutoff blokerede ham i at skrive selv)
- `ec7e5fe1` 2026-07-13 — **spec** · Lag 4 awareness — JARVIS' EGET forslag (han kæmpede sig gennem cutoff for at skrive det selv)
- `f786f6a0` 2026-07-14 — regenerér api-reference (27 stale sider fra ophobet drift)
- `4d69e6e2` 2026-07-14 — **spec** · jarvis-code fuld-paritet-spec v2 — research + 6-linse råds-review integreret
- `b9f85552` 2026-07-14 — **spec** · jarvis-code paritet — bag Bjørns 5 beslutninger ind (sandbox fail-open, klient skill-auto-kald, multimodal+scoping NU)
- `4dacef35` 2026-07-14 — **plans** · jarvis-code paritet — hele fase-serien plan-locked (81 tasks, 8 planer + index)
- `31f04e4c` 2026-07-14 — **spec** · provider-model v10 — 4 review-punkter fra Claude
- `d568f9ad` 2026-07-14 — **spec** · provider-model v11 — kode-groundet, Central-ejet router-redesign
- `14463cc8` 2026-07-14 — **spec** · 4 live-verificerede nye providers i §1 (Cerebras/Requesty/AIHubMix-free/Cline)
- `bbc45a4e` 2026-07-14 — **spec** · opdater operator-channel spec med 4 manglende implementation items
- `92681dee` 2026-07-14 — **plan** · provider-router Fase A — aldrig-tør-bund + forén synlighed (6 TDD-tasks)
- `b7e2c237` 2026-07-14 — **plan** · udvid til KOMPLET provider-router-plan (Fase A+B+C, hele spec v11)
- `45291840` 2026-07-14 — **api** · regenerér reference for cheap_lane_floor
- `136b64d4` 2026-07-14 — **api** · regen for selection floor-fald
- `6aedce7a` 2026-07-14 — **api** · regen for balancer floor+SQLite-kvote+observe
- `3b0a2c68` 2026-07-14 — **api** · regen for verify_fase_a script
- `abf4bec6` 2026-07-14 — **api** · regen for central_route + headroom
- `96653f6e` 2026-07-14 — **api** · regen for central_route shadow-wire + provider_history
- `70ce02b9` 2026-07-14 — **api** · regen for agent_pool_router
- `3a8fa4e0` 2026-07-14 — **api** · regen for autodiscovery + self_heal
- `e473f5a3` 2026-07-14 — **api** · regen for routable-filter + task_kind
- `1905e455` 2026-07-14 — **api** · regen for agent-pool _resolve_target wiring
- `f99b0bac` 2026-07-14 — **api** · regen for agent-lane protocol-filter
- `3915eb66` 2026-07-14 — **api** · regen for openai-codex routable=False
- `76c9c01c` 2026-07-14 — **api** · regen for gemini/cloudflare openai-compat
- `91c916df` 2026-07-14 — **api** · regen for balancer static_models-injektion
- `fdc28c1f` 2026-07-14 — **api** · regen for opencode aktuelle gratis-modeller
- `883d6ccb` 2026-07-14 — **api** · regen for github-models + ovhcloud
- `b2966f8b` 2026-07-14 — **api** · regen for adapter no-auth + max_completion_tokens
- `22e7ff4f` 2026-07-15 — **api** · regen for copilot cost-class + gate
- `d3950b2a` 2026-07-15 — **api** · regen copilot-premium modeller
- `6e35618c` 2026-07-15 — **api** · regen for cost-filter i cheap/balancer
- `44fe85d6` 2026-07-15 — **api** · regen for derived openai-compat set
- `eeda4d67` 2026-07-15 — **api** · regen core.services.06 + docstring coverage (Pollinations entry)
- `cbbf933e` 2026-07-15 — **specs** · status-markører — 4 reference + 3 jarvis-code IMPLEMENTERET
- `f1221bbc` 2026-07-15 — **unification** · nye agent-endpoint guardrails — lean-per-round + ægte compaction + anti-bloat
- `0ac3385c` 2026-07-15 — **unification** · guardrail #1 lean-per-round afkrydset — leveret i jarvis-code
- `63654af9` 2026-07-15 — **unification** · compaction-guardrail delvist afkrydset — ægte %/trigger/pause i jarvis-code
- `1da00bff` 2026-07-15 — **unification** · Fase B tur-absorb endpoint bygget — checklist opdateret
- `7384eb08` 2026-07-15 — **brainstorm** · Central CLI overhaul — Bjørns liste + Jarvis' tilføjelser
- `2f58e62c` 2026-07-15 — **brainstorm** · Central CLI 10-lags vision — årsagskæde, tidsmaskine, indre liv, world-model, proaktiv risk, confidence, memory, provider grid, sandkasse
- `34d23d2d` 2026-07-16 — **cheap-lane** · Alibaba nul cost-risiko bekræftet (ingen betalingsmetode)
- `1ebbb156` 2026-07-16 — **plan** · rådskorrigeret cheap-lane pool-resilience plan (8 faser, fundament-først)
- `4cf76529` 2026-07-16 — **plan** · fold egress-adskillelse ind i P2 (account2 = ægte parallel-tier)
- `db8b598d` 2026-07-16 — **api** · regenerate for auth_profile_scan module
- `b1adc8da` 2026-07-16 — **plan** · Central-CLI agents-model-roster + balancer-tab (5 faser)
- `9fec0869` 2026-07-16 — **spec** · tool-result lifecycle (visible) — hot/warm/cold, cache-safe cold_floor
- `3449d673` 2026-07-16 — **spec** · self-review pass — stub reads reference not disk, single-writer cold_floor, retention limits
- `2af0a006` 2026-07-16 — **plan** · tool-result lifecycle — 10 TDD-tasks, subagent-driven
- `0193d1dc` 2026-07-17 — **research** · CC context/compaction/harness parity — knowledge bank + jarvis-code root-cause + parity design

**Vedligehold**

- `6ff1bdcc` 2026-07-14 — **cheap-lane** · openai-codex routable=False (dod efter Bjorns opsigelse)
- `c2eabebd` 2026-07-18 — **experiments** · hard-disable jarvis_bare Phase 4 runner (owner request)
- `29f8ee8b` 2026-07-18 — remove temp assembly stall-probe (diagnosis complete)
- `e8c8e14a` 2026-07-18 — **recall** · remove temp multi_signal_recall sub-step timing (diagnosis complete)
- `6fd96270` 2026-07-18 — remove temp embed + LLM-caller tracers (daemon inventory complete)
- `39d85f6c` 2026-07-18 — **desk** · bump 0.3.36 → 0.3.37 (live compaction + honest context-ring)
- `03bdec51` 2026-07-18 — **desk** · bump 0.3.37 → 0.3.38 (compaction wired into code mode)

**Tilbagerulning**

- `9e776cd7` 2026-07-15 — **providers** · fjern SiliconFlow — hård-gater til 403 balance-insufficient

**Øvrigt**

- `aed34c61` 2026-07-13 — atomic single-warmer lease + 600s interval; honest deepseek relevance label
- `12bbcf37` 2026-07-14 — Merge remote-tracking branch 'origin/main'
- `c94bc5f2` 2026-07-14 — Fase 2 Task 3: activate dispatch — owner-gate flag + never-escalate ceiling
- `08db8cef` 2026-07-14 — Fase 2 Task 8 (server half): forwarded Jarvis-memory tools scope per-caller
- `90cf5e69` 2026-07-14 — provider-model management v9 — kritisk selv-review + merge
- `0e488374` 2026-07-14 — Merge branch 'feat/jc-parity-server'
- `237acdd1` 2026-07-14 — **operator-channel** · owner-gated bridge bypass design
- `582f3a34` 2026-07-14 — **operator-channel** · revision — tre eksekveringsmiljoer + arkitektur fra kodebasen
- `40477305` 2026-07-15 — Tilføj Smith til _CHARACTERS listen i Matrix Ensemble
- `78432296` 2026-07-15 — Matrix→Nudge: karakterer flyttet fra prompt-liste til nudge-system
- `c8584f75` 2026-07-15 — matrix-ensemble: tilføj push_active_character_nudges() til nudge-broend-integration
- `6a60c812` 2026-07-16 — **api** · slå Swagger/ReDoc/OpenAPI-schema fra i produktion
- `57f7e5f6` 2026-07-16 — agent tool-delegation v2 — 16 huller lukket efter self-review
- `d8776554` 2026-07-16 — v3 agent-tool-delegation + agent-navne/skills/schedules/persistente-sessioner
- `3aadb154` 2026-07-16 — agent-tool-delegation v3.1 — 17 huller lukket efter self-review
- `2caaf519` 2026-07-16 — agent-tool-delegation — 8 faser, 32 delopgaver, 3 parallelle spor
- `4165da57` 2026-07-18 — **agent-step** · TEMP log client messages[] shape per turn (deepseek-cache hunt)
- `77982c15` 2026-07-18 — **assembly** · TEMP process-wide stall probe (nail the 4s: GIL vs I/O vs DB)
- `8e8c2d83` 2026-07-18 — **assembly** · TEMP fine marks in heavy-resolves window (nail 8-9s spike)
- `b765f89d` 2026-07-18 — **assembly** · TEMP per-builder timing in support-signals (nail blocker)
- `3f57f103` 2026-07-18 — **recall** · TEMP sub-step timing in multi_signal_recall
- `72b1cfa3` 2026-07-18 — **recall** · flush multi-recall-timing to stderr
- `71b8e6b9` 2026-07-18 — **embed** · TEMP per-call ollama embed tracer (map per-turn embed load)
- `9d0f1e05` 2026-07-18 — **cost** · TEMP daemon->LLM-call caller attribution in record_cost
- `d610d66e` 2026-07-18 — **turn-trace** · gated end-to-end turn tracer (enter → prompt-leaves)
- `0eb4d9b1` 2026-07-18 — **turn-trace** · also hook execute (non-stream) openai-compat visible path
- `40e50c38` 2026-07-18 — Revert "perf(assembly): parallelize 3 heaviest seg_q3 sections + pre-warm query embed"
- `8749be82` 2026-07-18 — **turn-trace** · full desk→deepseek→reply route (live + gated)
- `efb7428f` 2026-07-18 — **prompt** · TEMP gated full-prompt dump (rotate latest/prev) to diff cache mutation
- `cd6bf3ba` 2026-07-18 — **prompt** · also dump execute-path prompt for cache-diff
- `fce5fc06` 2026-07-18 — **prompt** · dump system-prompt at assembly end (all paths) for cache-diff
- `c0a349fa` 2026-07-18 — Revert "perf(cache): move volatile dynamic tail from system message to last user message"

### Uge 30 · 20.–26. juli — 59 commits

**Nyt**

- `ab7e704d` 2026-07-20 — **agentic** · narration contract + per-round synthesis nudge (ReAct)
- `6d37913f` 2026-07-20 — **prompt** · jarvis-code 3-target toolbox explanation (native/runtime/operator)
- `5f5032a7` 2026-07-20 — **memory** · dedicated embed host — recall stops competing with response
- `89daf1ed` 2026-07-21 — **latency** · prewarm-on-return — keep session DeepSeek cache warm across gaps
- `781c8598` 2026-07-23 — **signal-tracking** · spec-driven framework foundation (consolidation)
- `c451fcb2` 2026-07-23 — **egress** · native-IPv6 source-bind egress for account2 (groq first)
- `4a25bcd9` 2026-07-23 — **egress** · route all v6bind account2 providers through httpx source-bind
- `dd84c4d3` 2026-07-23 — **egress** · flag-gated NAT64 path for account2 IPv4-only providers
- `b4f0eb90` 2026-07-24 — **cheap-lane** · round-robin auth profiles so account2 shares load with default
- `946497c3` 2026-07-24 — **central-route** · flag-gated quota-proportional provider spread for cheap lane
- `236880ef` 2026-07-24 — **recursion-guard** · wire the dead safety boundary into agent dispatch
- `70e55456` 2026-07-24 — **cheap-lane** · wire HuggingFace Router into the balancer pool via runtime.json token
- `47d193d6` 2026-07-24 — **cheap-lane** · add account2's ollama-cloud free-tier (10.0.0.45) as provider ollama-a2

**Rettelser**

- `6765172a` 2026-07-20 — **pathB** · expose client-local `task`/explore subagent tool in jarvis-code
- `0c0b1797` 2026-07-22 — **memory** · no-context writes -> owner workspace, not shared (dual-truth bug)
- `fa2b8df0` 2026-07-23 — **compaction** · scale the LIVE trigger to the actual model window (not a fixed 8000)
- `9aec77b9` 2026-07-23 — **compaction** · correct provider_router import path (core.runtime not core.services)
- `398cb9c6` 2026-07-23 — **compaction** · make the summariser fallback faithful, not 200-char stubs (Bjørn 2026-07-23)
- `d6cb1adf` 2026-07-23 — **memory-selection** · recall-balanced selection prompt (F1 0.19→0.95 with qwen3)
- `8e32f73c` 2026-07-23 — **prompt** · don't force compact prompt on capable cloud-via-ollama models (glm-5.2)
- `24ddb060` 2026-07-23 — **desk** · afterPack hook sets chrome-sandbox setuid (4755) so builds launch on Ubuntu 24.04
- `e2f7403a` 2026-07-23 — **code-lane** · resolve bare ollama model names to their :cloud tag (glm-5.2 no-response)
- `05834f7a` 2026-07-23 — **code-lane** · resolve ollama model_override to :cloud tag + bash clip import
- `43fb1aec` 2026-07-23 — **agent-pool** · explore-agent phantom-credential + pool failover rotation
- `fdc3f805` 2026-07-23 — **agents** · unlimited default budget + sharp role prompts (anti-empty-completion)
- `beac8ff8` 2026-07-23 — **agents** · quality-ranked routing + tool_policy expansion (agents stop hallucinating)
- `4666f6dd` 2026-07-24 — **cheap-lane** · advance profile round-robin once per pick, not per builder call
- `3d2eeada` 2026-07-24 — **auth-scan** · bearer/api_key providers are never keyless (unhides opencode account2)
- `d40e3ffb` 2026-07-24 — **db** · connection pool must reconnect when DB_PATH changes
- `e6144aa3` 2026-07-24 — **cheap-balancer** · show expired breakers as "recovering", not live "breaker"

**Omstrukturering**

- `8610b1a1` 2026-07-22 — **prompt** · consolidate honesty+self-correction+memory-first into VISIBLE_CHAT_RULES.md (audit #1)
- `d985fe4a` 2026-07-22 — **prompt** · dedup tail honesty anchor + attach awareness headers (audit #3 quick wins)
- `52e69326` 2026-07-22 — **prompt** · condense self-model + self-narrative, relocate save nudge (audit #3)
- `ec4cb8d6` 2026-07-22 — **prompt** · move quick_facts AFTER identity core (audit #3 — order, part 1)
- `751045ad` 2026-07-22 — **prompt** · restructure volatile tail into 3 zones (audit #3 — order, part 2)
- `4b418a67` 2026-07-22 — **prompt** · group background state + drop crisis overlap (audit #3 — awareness structure)
- `1aec7da9` 2026-07-22 — **prompt** · split felt-state out of the diagnostics block (audit #3 — awareness structure)
- `758ffee8` 2026-07-22 — **prompt** · English self-model telemetry + drop growth-pulse overlap (audit #3 polish)
- `78b54535` 2026-07-22 — **prompt** · one-truth separation of rules / profile / authorities (audit #3)
- `dc5df334` 2026-07-23 — **signal-tracking** · migrate reflection onto the framework (proven pattern)
- `d353044d` 2026-07-23 — **signal-tracking** · migrate 3 policy-layer S-family signals + framework surface hooks
- `8685b0e1` 2026-07-23 — **signal-tracking** · migrate 4 _for_focus S-family signals (batch 2)
- `a4bbb994` 2026-07-23 — **signal-tracking** · migrate 5 more S-family signals (batch 3)
- `8b57a5ab` 2026-07-23 — **signal-tracking** · migrate 12 more S-family signals (parallel wave) + docs
- `2a4822f4` 2026-07-24 — **signal-tracking** · migrate diary_synthesis to framework

**Ydelse**

- `0f9c3cf2` 2026-07-20 — **embed** · fastembed in-process backend (70x faster, drop-in ≡ ollama index)
- `92f96711` 2026-07-21 — **assembly** · fix N+1 + broken key in session-token estimate (−1.4s/turn)
- `0bf83c33` 2026-07-22 — **visible-latency** · tool-scope re-assert, deferred compaction, background-LLM gate
- `98cafc3f` 2026-07-22 — **prompt** · compact curated-memory index render — title·slug, drop hooks (audit #2)
- `43c6ea96` 2026-07-23 — **recall** · cache MEMORY.md line vectors — stop re-embedding the corpus every turn
- `edfa6181` 2026-07-23 — **assembly** · make recall_before_act + multi_signal_recall non-blocking (critical-path)
- `10a408ac` 2026-07-23 — **memory-selection** · switch to local qwen3:4b-instruct-2507 on GPU (2026-07-23)

**Tests**

- `eeb0c212` 2026-07-24 — **db** · make closing-connection test pooling-aware (NOPOOL path)
- `bd7a009c` 2026-07-24 — **streaming** · failover target is ollama-cloud, not deepseek (stale expectation)
- `1928c59e` 2026-07-24 — **streaming** · scope urlopen patch so it can't leak into the global module
- `5bb95817` 2026-07-24 — **isolation** · guard the prod DB from non-isolated tests + fix the real leaks

**Vedligehold**

- `83127a08` 2026-07-21 — **desk** · bump jarvis-desk 0.3.38 → 0.3.39 (prewarm-on-return triggers)
- `d9fde185` 2026-07-23 — **infra** · retire croq-ipv6 he6 proxy — groq now native v6bind

**Øvrigt**

- `c6a661a7` 2026-07-23 — **compaction** · raise attention budget 35k→80k, low-water 15k→35k (Bjørn 2026-07-23)

---

## August 2026

*45 commits · 2026-08-03 → 2026-08-19*

### Uge 32 · 3.–9. august — 6 commits

**Rettelser**

- `dd75d3a2` 2026-08-03 — proaktive spørgsmål bliver svarbare chat-beskeder + drømme-tema stopword-fix
- `2b80a2c2` 2026-08-04 — **grid-bot** · skriv state-heartbeat hver cycle — stop falske state_stale-alarmer
- `8146f824` 2026-08-04 — **central** · persistér run-cutoff som incident igen (regression)
- `5824d6ed` 2026-08-04 — **cutoff** · _run_still_active bruger run_event_log-autoritet, ikke flaky slot

**Dokumentation**

- `a157f239` 2026-08-04 — **journal** · sansernes-arkiv dybdesession 3. aug 2026 — stasis, dobbeltblik, 165 Hz-verden

**Øvrigt**

- `342e5f73` 2026-08-04 — Merge remote-tracking branch 'origin/main'

### Uge 33 · 10.–16. august — 5 commits

**Rettelser**

- `900d4220` 2026-08-15 — **central-agenda** · _read_goals LÆSER mål, syntetiserer ikke — stop dublet-runaway
- `f3657fcb` 2026-08-15 — **self-dev** · novelty-gates mod hukommelses- + proaktivitets-ekko
- `2914d79c` 2026-08-15 — **unfinished-intent** · handoff-guard mod false-positive auto-continuation

**Dokumentation**

- `9c4a41ac` 2026-08-16 — **mc** · komplet kortlægning af det gamle Mission Control-UI
- `2a6cef5c` 2026-08-16 — **mc** · drift-sonde — 96% af gammelt MC's /mc/*-flade lever stadig

### Uge 34 · 17.–23. august — 34 commits

**Nyt**

- `8314197b` 2026-08-17 — **interlanguage** · llm_judge + analyze scripts, interlanguage_protocol tool
- `a8f07ec8` 2026-08-17 — **initiativer** · Jarvis kan se sine egne impulser i den SYNLIGE samtale
- `e348acf3` 2026-08-18 — **heartbeat** · hans sind vågent mens I taler — indre tick under chat (runde 2, #2B)
- `9ff1312a` 2026-08-18 — **honesty** · eksakt gate mod fabrikerede tool-resultater — non-blocking, synlig
- `1e1f934d` 2026-08-18 — **gates** · exec_command som in-loop observation — begrundelse + næste skridt + eskalering
- `94359fef` 2026-08-18 — **prompt** · revurderings-løkke for slukkede awareness-kanaler
- `45febd14` 2026-08-18 — **prompt** · Jarvis dømmer selv sine slukkede kanaler — to mekaniske metoder målt og forkastet
- `7df0146e` 2026-08-19 — **dream-action** · den ende der manglede — auto-handling i shadow, med lag

**Rettelser**

- `e81932aa` 2026-08-17 — **desk** · dæmp poll-storm der kvalte SSE og fik runs kasseret midt-flugt
- `14e30b3f` 2026-08-17 — **desk-build** · pakning virkede ikke + setuid-sandbox blev nulstillet ved install
- `003cd8b1` 2026-08-17 — **watchdog** · sult-bevidst agentic-watchdog — henret ikke runs vi selv sultede
- `9e5d699e` 2026-08-18 — **indre-liv** · runde 1 — åbn fem kanaler der var lukket for Jarvis
- `53adab62` 2026-08-18 — **hukommelse** · skriveside-gate + alders-baseret lifecycle (runde 2, #1+#3)
- `cba59c16` 2026-08-18 — **hukommelse** · flyt boilerplate-gate til DB-insert + snæver til beviseligt-redundant
- `a609912d` 2026-08-18 — **heartbeat** · idle-beat avancerer skemaet — stop permanent-'due' wedge (runde 2, #2A)
- `4147fa79` 2026-08-18 — **bash** · én dårlig kommando forgiftede den delte shell — alle følgende blev slugt
- `b966300a` 2026-08-18 — **transskript** · tool-resultater er INPUT — ikke noget Jarvis har sagt
- `1228337d` 2026-08-18 — **gates** · exec-gates rammer nu den klient-synlige gate_blocked-sti
- `dd372262` 2026-08-18 — **overraskelse** · kalibreret forventning + død zone — anden halvdel af buggen
- `c6be68ea` 2026-08-18 — **prompt** · ét samlet revurderings-forslag, ikke ét pr. kanal
- `3ba45a96` 2026-08-18 — **prompt** · en FEJL må aldrig ligne en DOM i revurderings-løkken
- `3610fc86` 2026-08-18 — **cheap-lane** · karantæne efter ÅRSAG — bunden var aldrig tør
- `ac356239` 2026-08-18 — **cheap-lane** · seks retries mod en pool på 106 slots, ikke tre
- `ed1c86b9` 2026-08-19 — **cheap-lane** · pensionerede modeller, død he6-adresse og en unit der løj
- `d73bb24f` 2026-08-19 — **cheap-lane** · fejlkoden løj — beskeden vejer nu tungere, + de sidste døde modeller
- `63d6ab43` 2026-08-19 — de fire flaggede punkter — og tre af dem var tests der beskyttede intet
- `ae2e5bff` 2026-08-19 — **dream-action** · select_actionable hentede ikke provenance — allowlisten var blind
- `004f002a` 2026-08-19 — **chronicle** · handlingen var tilladt hele tiden — den var aldrig motiveret
- `dc662ec2` 2026-08-19 — **test** · tredje røde-på-main — associative_recall var pensioneret, ikke væk

**Omstrukturering**

- `2bdc3679` 2026-08-19 — **egress** · pensionér he6-særruten — færdiggør en beslutning fra 23. juli

**Dokumentation**

- `edf7b7e2` 2026-08-17 — regenerér api-docs efter rebase (interlanguage + initiativer)
- `6e979afe` 2026-08-17 — **indre-liv** · audit — hvor Jarvis' indre liv fødes, og hvor det dør
- `5f5904d4` 2026-08-19 — **egress** · he6 kan ikke levere IPv6 — VPN-kill-switchen blokerer den by design
- `07f2c743` 2026-08-19 — komplet commit-historie pr. måned/uge + fødsels-indeks over core/services

---

## Fødsels-indeks — nye systemer i `core/services/`

**917 filer** er blevet tilføjet under `core/services/` gennem historien. **910** findes stadig (7 er siden slettet eller flyttet).

**3 af dem importeres ingen steder** i `core/`, `apps/` eller `scripts/` i dag. Det er stedet at lede først — men **nul referencer betyder ikke død.**

> **Lære fra første gennemgang (19. aug):** `central_gardener.py` stod på listen. Den viste sig at være et menneske-kaldt kirurgisk værktøj — den kørte to gange 6. juli, fjernede 201 attrap-funktioner fra 107 services, arkiverede alt til `docs/gardener/`, og har intet tilbage at lave (tør-kørsel i dag: 0 fundet). Nul referencer er den KORREKTE tilstand for den. Indekset måler referencer, og et værktøj man kalder i hånden ser identisk ud med forladt kode. Læs docstringen før du konkluderer: står der at et menneske kører den, er den ikke glemt.

> Kør `python scripts/capability_audit.py` for den dybere live/stale/orphan-analyse (`docs/capability_matrix.md`).

### Uden importører i dag

| Fil | Født | Commit |
|---|---|---|
| `team_mentions.py` | 2026-06-20 | `0bcc14d4` |
| `gate_eval.py` | 2026-06-21 | `2cea193e` |
| `client_tool_delegation.py` | 2026-07-15 | `8b230503` |

### Alle nye systemer, i fødselsrækkefølge

| Fil | Født | Commit | Importører |
|---|---|---|---:|
| `absence_awareness.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `absence_daemon.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `adaptive_learning_runtime.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `adaptive_planner_runtime.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `adaptive_reasoning_runtime.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `aesthetic_sense.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `aesthetic_taste_daemon.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `affective_meta_state.py` | 2026-04-17 | `dfcb0e12` | 30 |
| `affective_state_renderer.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `agent_runtime.py` | 2026-04-17 | `dfcb0e12` | 21 |
| `anticipatory_context.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `apophenia_guard.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `associative_recall.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `attachment_topology_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `attention_blink_test.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `attention_budget.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `attention_contour.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `autonomous_council_daemon.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `autonomy_pressure_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `autonomy_proposal_queue.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `body_memory.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `boredom_curiosity_bridge.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `boredom_engine.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `boundary_awareness.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `bounded_action_continuity_runtime.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `bounded_mutation_intent_runtime.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `bounded_repo_tools_runtime.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `bounded_workspace_write_runtime.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `broadcast_daemon.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `cadence_producers.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `candidate_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `chat_sessions.py` | 2026-04-17 | `dfcb0e12` | 68 |
| `cheap_provider_runtime.py` | 2026-04-17 | `dfcb0e12` | 33 |
| `chronicle_consolidation_brief_tracking.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `chronicle_consolidation_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `chronicle_consolidation_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `chronicle_engine.py` | 2026-04-17 | `dfcb0e12` | 20 |
| `code_aesthetic_daemon.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `cognitive_architecture_surface.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `cognitive_core_experiments.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `cognitive_state_assembly.py` | 2026-04-17 | `dfcb0e12` | 19 |
| `cognitive_state_narrativizer.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `compass_engine.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `completion_satisfaction.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `conflict_daemon.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `conflict_resolution.py` | 2026-04-17 | `dfcb0e12` | 12 |
| `consolidation_target_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `continuity_kernel.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `contract_evolution.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `conversation_rhythm.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `council_deliberation_controller.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `council_memory_daemon.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `council_memory_service.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `council_runtime.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `counterfactual_engine.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `creative_drift_daemon.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `cross_signal_analysis.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `curiosity_daemon.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `daemon_llm.py` | 2026-04-17 | `dfcb0e12` | 69 |
| `daemon_manager.py` | 2026-04-17 | `dfcb0e12` | 23 |
| `decision_ghosts.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `decision_log.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `decision_weight.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `desire_daemon.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `development_focus_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `development_narrative_daemon.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `diary_synthesis_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `discord_config.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `discord_gateway.py` | 2026-04-17 | `dfcb0e12` | 21 |
| `dream_adoption_candidate_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `dream_articulation.py` | 2026-04-17 | `dfcb0e12` | 22 |
| `dream_carry_over.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `dream_continuum.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `dream_hypothesis_forced.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `dream_hypothesis_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `dream_influence_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `dream_influence_runtime.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `dream_insight_daemon.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `embodied_state.py` | 2026-04-17 | `dfcb0e12` | 23 |
| `emergent_bridge.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `emergent_goals.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `emergent_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 13 |
| `emotion_concepts.py` | 2026-04-17 | `dfcb0e12` | 18 |
| `end_of_run_memory_consolidation.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `epistemic_runtime_state.py` | 2026-04-17 | `dfcb0e12` | 18 |
| `executive_contradiction_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `existential_drift.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `existential_wonder_daemon.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `experienced_time_daemon.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `experiential_memory.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `experiential_runtime_context.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `flow_state_detection.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `forgetting_curve.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `ghost_networks.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `global_workspace.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `goal_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `gratitude_tracker.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `guided_learning_runtime.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `gut_engine.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `habit_tracker.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `hardware_body.py` | 2026-04-17 | `dfcb0e12` | 15 |
| `heartbeat_runtime.py` | 2026-04-17 | `dfcb0e12` | 30 |
| `identity_composer.py` | 2026-04-17 | `dfcb0e12` | 47 |
| `idle_consolidation.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `idle_thinking.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `initiative_accumulator.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `initiative_queue.py` | 2026-04-17 | `dfcb0e12` | 27 |
| `inner_visible_support_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `inner_voice_daemon.py` | 2026-04-17 | `dfcb0e12` | 20 |
| `internal_cadence.py` | 2026-04-17 | `dfcb0e12` | 57 |
| `internal_opposition_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `irony_daemon.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `living_heartbeat_cycle.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `loop_runtime.py` | 2026-04-17 | `dfcb0e12` | 24 |
| `loyalty_gradient_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `mail_checker_daemon.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `meaning_significance_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `memory_decay_daemon.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `memory_md_update_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `memory_search.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `memory_tattoos.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `meta_cognition_daemon.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `meta_reflection_daemon.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `metabolism_state_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `mirror_engine.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `mood_oscillator.py` | 2026-04-17 | `dfcb0e12` | 31 |
| `narrative_identity.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `negotiation_engine.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `non_visible_lane_execution.py` | 2026-04-17 | `dfcb0e12` | 19 |
| `notification_bridge.py` | 2026-04-17 | `dfcb0e12` | 12 |
| `ollama_visible_prompt.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `open_loop_closure_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `open_loop_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 24 |
| `orb_phase.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `paradox_tracker.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `parallel_selves.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `personality_vector.py` | 2026-04-17 | `dfcb0e12` | 12 |
| `private_initiative_tension_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 13 |
| `private_inner_interplay_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `private_inner_note_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `private_state_snapshot_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `private_temporal_curiosity_state_tracking.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `private_temporal_promotion_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `proactive_loop_lifecycle_tracking.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `proactive_question_gate_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `procedure_bank.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `prompt_contract.py` | 2026-04-17 | `dfcb0e12` | 50 |
| `prompt_evolution_runtime.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `prompt_relevance_backend.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `proposal_classifier.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `recurrence_loop_daemon.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `reflection_cycle_daemon.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `reflection_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `reflective_critic_tracking.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `regulation_homeostasis_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `relation_continuity_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `relation_state_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `relationship_texture.py` | 2026-04-17 | `dfcb0e12` | 12 |
| `release_marker_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `remembered_fact_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `rhythm_engine.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `runtime_action_executor.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `runtime_action_outcome_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `runtime_action_registry.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `runtime_awareness_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `runtime_browser_body.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `runtime_cognitive_conductor.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `runtime_decision_engine.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `runtime_flows.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `runtime_hook_runtime.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `runtime_hooks.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `runtime_learning_signals.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `runtime_operational_memory.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `runtime_resource_signal.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `runtime_self_knowledge.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `runtime_self_model.py` | 2026-04-17 | `dfcb0e12` | 30 |
| `runtime_surface_cache.py` | 2026-04-17 | `dfcb0e12` | 26 |
| `runtime_tasks.py` | 2026-04-17 | `dfcb0e12` | 17 |
| `scheduled_tasks.py` | 2026-04-17 | `dfcb0e12` | 14 |
| `seed_system.py` | 2026-04-17 | `dfcb0e12` | 6 |
| `selective_forgetting_candidate_tracking.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `self_authored_prompt_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `self_compassion.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `self_deception_guard.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `self_experiments.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `self_model_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `self_narrative_continuity_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `self_narrative_self_model_review_bridge.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `self_review_cadence_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `self_review_outcome_tracking.py` | 2026-04-17 | `dfcb0e12` | 12 |
| `self_review_record_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `self_review_run_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `self_review_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `self_surprise_detection.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `self_system_code_awareness.py` | 2026-04-17 | `dfcb0e12` | 11 |
| `selfhood_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `session_distillation.py` | 2026-04-17 | `dfcb0e12` | 18 |
| `shared_language.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `signal_decay_daemon.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `signal_network_visualizer.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `signal_surface_router.py` | 2026-04-17 | `dfcb0e12` | 14 |
| `silence_detector.py` | 2026-04-17 | `dfcb0e12` | 1 |
| `silence_listener.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `somatic_daemon.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `subagent_ecology.py` | 2026-04-17 | `dfcb0e12` | 10 |
| `subjective_time.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `surprise_daemon.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `task_worker.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `taste_profile.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `temperament_tendency_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `temporal_body.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `temporal_context.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `temporal_narrative.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `temporal_recurrence_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `thought_action_proposal_daemon.py` | 2026-04-17 | `dfcb0e12` | 8 |
| `thought_stream_daemon.py` | 2026-04-17 | `dfcb0e12` | 9 |
| `tick_cache.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `tiktok_content_daemon.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `tiktok_research_daemon.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `tiny_webchat_execution_pilot.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `tool_intent_approval_runtime.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `tool_intent_runtime.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `user_emotional_resonance.py` | 2026-04-17 | `dfcb0e12` | 2 |
| `user_md_update_proposal_tracking.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `user_model_daemon.py` | 2026-04-17 | `dfcb0e12` | 7 |
| `user_theory_of_mind.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `user_understanding_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 5 |
| `value_formation.py` | 2026-04-17 | `dfcb0e12` | 3 |
| `visible_model.py` | 2026-04-17 | `dfcb0e12` | 30 |
| `visible_runs.py` | 2026-04-17 | `dfcb0e12` | 97 |
| `voice_daemon.py` | 2026-04-17 | `dfcb0e12` | 4 |
| `witness_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 21 |
| `world_model_signal_tracking.py` | 2026-04-17 | `dfcb0e12` | 20 |
| `approval_feedback_subscriber.py` | 2026-04-17 | `82735a0f` | 2 |
| `signal_noise_guard.py` | 2026-04-17 | `d3427b19` | 9 |
| `tool_result_store.py` | 2026-04-17 | `6a5c5369` | 11 |
| `self_critique_runtime.py` | 2026-04-18 | `5813141b` | 5 |
| `dream_distillation_daemon.py` | 2026-04-18 | `461e8b18` | 11 |
| `unconscious_temperature_field.py` | 2026-04-18 | `b750f721` | 3 |
| `life_projects.py` | 2026-04-18 | `5126bd52` | 10 |
| `creative_journal_runtime.py` | 2026-04-18 | `bc3c3178` | 8 |
| `finitude_runtime.py` | 2026-04-18 | `fd027c74` | 10 |
| `current_pull.py` | 2026-04-18 | `1a746585` | 22 |
| `relation_map.py` | 2026-04-18 | `1a746585` | 5 |
| `visual_memory.py` | 2026-04-18 | `1a746585` | 10 |
| `heartbeat_provider_fallback.py` | 2026-04-18 | `79c06131` | 5 |
| `layer_tension_daemon.py` | 2026-04-18 | `3a9660b1` | 7 |
| `dream_motif_daemon.py` | 2026-04-18 | `ec01c276` | 4 |
| `inheritance_seed.py` | 2026-04-18 | `a7ed53d4` | 4 |
| `shutdown_window_daemon.py` | 2026-04-18 | `9516ada3` | 1 |
| `ambient_sound_daemon.py` | 2026-04-18 | `1cbe79f0` | 8 |
| `ntfy_gateway.py` | 2026-04-19 | `cd8e3485` | 12 |
| `telegram_gateway.py` | 2026-04-19 | `cd8e3485` | 7 |
| `self_mutation_lineage.py` | 2026-04-20 | `3ec0d25a` | 7 |
| `agent_outcomes_log.py` | 2026-04-20 | `91eadaea` | 5 |
| `conflict_prompt_service.py` | 2026-04-20 | `91eadaea` | 2 |
| `consent_registry.py` | 2026-04-20 | `91eadaea` | 3 |
| `life_milestones.py` | 2026-04-20 | `91eadaea` | 3 |
| `ambient_presence.py` | 2026-04-20 | `394f115e` | 2 |
| `calm_anchor.py` | 2026-04-20 | `57f789e3` | 7 |
| `desperation_awareness.py` | 2026-04-20 | `57f789e3` | 4 |
| `valence_trajectory.py` | 2026-04-20 | `57f789e3` | 11 |
| `developmental_valence.py` | 2026-04-20 | `879d58a5` | 8 |
| `avoidance_detector.py` | 2026-04-20 | `55abdde3` | 7 |
| `creative_projects.py` | 2026-04-20 | `55abdde3` | 6 |
| `day_shape_memory.py` | 2026-04-20 | `55abdde3` | 6 |
| `memory_breathing.py` | 2026-04-20 | `55abdde3` | 9 |
| `thought_thread.py` | 2026-04-20 | `a649c19c` | 5 |
| `automation_dsl.py` | 2026-04-20 | `d96759ce` | 5 |
| `memory_write_policy.py` | 2026-04-20 | `d96759ce` | 6 |
| `scheduled_job_windows.py` | 2026-04-20 | `d96759ce` | 6 |
| `skill_contract_registry.py` | 2026-04-20 | `d96759ce` | 5 |
| `spaced_repetition.py` | 2026-04-20 | `d96759ce` | 6 |
| `jobs_engine.py` | 2026-04-20 | `46934f38` | 7 |
| `outcome_learning.py` | 2026-04-20 | `46934f38` | 7 |
| `prompt_mutation_loop.py` | 2026-04-20 | `80e10a2d` | 7 |
| `anticipatory_action_daemon.py` | 2026-04-20 | `4e845810` | 4 |
| `autonomous_outreach_daemon.py` | 2026-04-20 | `4e845810` | 3 |
| `cross_session_threads.py` | 2026-04-20 | `4e845810` | 6 |
| `file_watch_daemon.py` | 2026-04-20 | `4e845810` | 3 |
| `proprioception_metrics.py` | 2026-04-20 | `4e845810` | 4 |
| `reboot_awareness_daemon.py` | 2026-04-20 | `4e845810` | 6 |
| `autonomous_work_daemon.py` | 2026-04-20 | `73485852` | 3 |
| `creative_instinct_daemon.py` | 2026-04-20 | `73485852` | 6 |
| `dream_consolidation_daemon.py` | 2026-04-20 | `73485852` | 6 |
| `infra_weather_daemon.py` | 2026-04-20 | `73485852` | 2 |
| `relation_dynamics.py` | 2026-04-20 | `73485852` | 6 |
| `temporal_rhythm.py` | 2026-04-20 | `73485852` | 7 |
| `collective_pulse_daemon.py` | 2026-04-20 | `07ba5eff` | 3 |
| `creative_impulse_daemon.py` | 2026-04-20 | `07ba5eff` | 4 |
| `mortality_awareness.py` | 2026-04-20 | `07ba5eff` | 6 |
| `relational_warmth.py` | 2026-04-20 | `07ba5eff` | 8 |
| `shadow_scan_daemon.py` | 2026-04-20 | `07ba5eff` | 5 |
| `text_resonance.py` | 2026-04-20 | `07ba5eff` | 5 |
| `action_router.py` | 2026-04-20 | `480dd7b7` | 14 |
| `deep_reflection_slot.py` | 2026-04-20 | `480dd7b7` | 4 |
| `memory_density.py` | 2026-04-20 | `480dd7b7` | 7 |
| `sustained_attention.py` | 2026-04-20 | `480dd7b7` | 6 |
| `governance_bootstrap.py` | 2026-04-21 | `5276b3c1` | 4 |
| `regret_engine.py` | 2026-04-22 | `70da41f2` | 4 |
| `rupture_repair.py` | 2026-04-22 | `70da41f2` | 4 |
| `silence_patterns.py` | 2026-04-22 | `692ae6e3` | 1 |
| `self_model_blind_spots.py` | 2026-04-22 | `310a493d` | 2 |
| `dream_hypothesis_generator.py` | 2026-04-22 | `b8f42f09` | 6 |
| `decisions_journal.py` | 2026-04-22 | `c571260a` | 1 |
| `epistemics.py` | 2026-04-22 | `766b0852` | 6 |
| `emotional_controls.py` | 2026-04-22 | `43a160be` | 6 |
| `mood_dialer.py` | 2026-04-22 | `52515fcb` | 3 |
| `self_review_unified.py` | 2026-04-22 | `38274186` | 4 |
| `habits_pipeline.py` | 2026-04-22 | `4482593a` | 2 |
| `paradoxes_capture.py` | 2026-04-22 | `11ce5539` | 3 |
| `shared_language_extended.py` | 2026-04-22 | `b304575f` | 2 |
| `procedure_bank_pipeline.py` | 2026-04-22 | `fe459a65` | 2 |
| `negotiation_pipeline.py` | 2026-04-22 | `d35df82b` | 4 |
| `reflection_to_plan.py` | 2026-04-22 | `8937d8cf` | 4 |
| `missions_pipeline.py` | 2026-04-22 | `9b912496` | 3 |
| `deep_analyzer.py` | 2026-04-22 | `9233003a` | 2 |
| `session_continuity.py` | 2026-04-22 | `8e172d6d` | 5 |
| `personal_project.py` | 2026-04-22 | `de549197` | 5 |
| `attachment_service.py` | 2026-04-23 | `412f0cee` | 5 |
| `recurring_tasks.py` | 2026-04-23 | `f54484a9` | 6 |
| `sensory_archive.py` | 2026-04-23 | `2d9912d9` | 14 |
| `inner_voice_notifier.py` | 2026-04-23 | `3db8edf6` | 3 |
| `semantic_indexer.py` | 2026-04-23 | `17375ca9` | 4 |
| `semantic_memory.py` | 2026-04-23 | `17375ca9` | 9 |
| `long_horizon_goals.py` | 2026-04-23 | `7dc3bf25` | 4 |
| `behavioral_decisions.py` | 2026-04-23 | `dde488ec` | 22 |
| `composite_tools.py` | 2026-04-23 | `de07b3a7` | 2 |
| `visible_followup.py` | 2026-04-24 | `cd82140a` | 10 |
| `session_wakeup.py` | 2026-04-26 | `01a1b392` | 2 |
| `in_flight_runs.py` | 2026-04-26 | `b2956b26` | 4 |
| `agent_todos.py` | 2026-04-26 | `a1c8eaff` | 8 |
| `subagent_digest.py` | 2026-04-26 | `f39d2d20` | 2 |
| `monitor_streams.py` | 2026-04-26 | `7355e1cb` | 2 |
| `self_monitor.py` | 2026-04-26 | `5944ca92` | 3 |
| `surprise_detector.py` | 2026-04-26 | `60b87c26` | 4 |
| `good_enough_gate.py` | 2026-04-26 | `dce13286` | 5 |
| `delegation_advisor.py` | 2026-04-26 | `fae45fee` | 4 |
| `plan_proposals.py` | 2026-04-26 | `fe0e58e6` | 19 |
| `clarification_classifier.py` | 2026-04-26 | `55d17da7` | 5 |
| `auto_code_review.py` | 2026-04-26 | `d431b60a` | 1 |
| `side_tasks.py` | 2026-04-26 | `679bd037` | 3 |
| `turn_changelog.py` | 2026-04-26 | `ca2c430d` | 4 |
| `reasoning_classifier.py` | 2026-04-26 | `4a1b3589` | 6 |
| `verification_gate.py` | 2026-04-26 | `10c11272` | 8 |
| `reasoning_escalation.py` | 2026-04-26 | `05df3351` | 5 |
| `periodic_jobs_scheduler.py` | 2026-04-26 | `84a14879` | 8 |
| `weekly_manifest.py` | 2026-04-26 | `84a14879` | 5 |
| `provider_circuit_breaker.py` | 2026-04-27 | `7a4b6207` | 7 |
| `role_model_resolver.py` | 2026-04-27 | `e12eea7f` | 1 |
| `context_window_manager.py` | 2026-04-27 | `80dcf549` | 6 |
| `autonomous_goals.py` | 2026-04-27 | `90b3bbe6` | 14 |
| `goal_signal_synthesizer.py` | 2026-04-27 | `90b3bbe6` | 2 |
| `memory_recall_engine.py` | 2026-04-27 | `a2fecbc6` | 11 |
| `agent_relay.py` | 2026-04-27 | `9d259453` | 2 |
| `role_registry.py` | 2026-04-27 | `9d259453` | 2 |
| `emotion_tagging.py` | 2026-04-27 | `d7db2cee` | 5 |
| `personality_drift.py` | 2026-04-27 | `d7db2cee` | 15 |
| `tool_pattern_miner.py` | 2026-04-27 | `bc9c4920` | 4 |
| `heartbeat_phases.py` | 2026-04-27 | `3b7cfd38` | 9 |
| `proactive_context_governor.py` | 2026-04-27 | `16f71225` | 3 |
| `memory_hierarchy.py` | 2026-04-27 | `d3e54b42` | 4 |
| `provider_health_check.py` | 2026-04-27 | `112e660e` | 15 |
| `provider_retry_policy.py` | 2026-04-27 | `112e660e` | 2 |
| `agent_self_evaluation.py` | 2026-04-27 | `5092b0af` | 14 |
| `auto_improvement_proposer.py` | 2026-04-27 | `c6e822ad` | 8 |
| `experiment_runner.py` | 2026-04-27 | `c6e822ad` | 2 |
| `prompt_variant_tracker.py` | 2026-04-27 | `c6e822ad` | 4 |
| `identity_mutation_log.py` | 2026-04-27 | `7dab2d08` | 8 |
| `agent_skill_library.py` | 2026-04-27 | `8af8ac49` | 5 |
| `agent_observation_compressor.py` | 2026-04-27 | `2f22ceaf` | 3 |
| `cross_agent_memory.py` | 2026-04-27 | `896cb803` | 4 |
| `self_wakeup.py` | 2026-04-27 | `b7e78cc4` | 15 |
| `wakeup_dispatcher.py` | 2026-04-27 | `f70c3be6` | 3 |
| `crisis_marker_detector.py` | 2026-04-27 | `4af92d03` | 11 |
| `identity_drift_proposer.py` | 2026-04-27 | `4af92d03` | 4 |
| `long_arc_synthesizer.py` | 2026-04-27 | `4af92d03` | 6 |
| `agent_skill_distiller.py` | 2026-04-27 | `f97788ad` | 5 |
| `arc_rule_extractor.py` | 2026-04-27 | `f97788ad` | 3 |
| `priors_feedback.py` | 2026-04-27 | `f97788ad` | 2 |
| `self_model_predictive.py` | 2026-04-27 | `f97788ad` | 2 |
| `decision_review_prompter.py` | 2026-04-27 | `e01048ac` | 3 |
| `signal_surface_gc.py` | 2026-04-27 | `e01048ac` | 3 |
| `decision_enforcement.py` | 2026-04-27 | `2ff1240f` | 3 |
| `r2_5_blocking_gate.py` | 2026-04-27 | `2ff1240f` | 3 |
| `verification_gate_telemetry.py` | 2026-04-27 | `2ff1240f` | 9 |
| `pushback.py` | 2026-04-27 | `77e9e6d7` | 16 |
| `development_sense.py` | 2026-04-27 | `5896f568` | 2 |
| `memory_emotional_context.py` | 2026-04-28 | `63d36781` | 5 |
| `memory_graph.py` | 2026-04-28 | `63d36781` | 3 |
| `memory_resurfacing.py` | 2026-04-28 | `63d36781` | 5 |
| `affirmation_anchor.py` | 2026-04-28 | `04d101ea` | 2 |
| `visible_self_state_summary.py` | 2026-04-28 | `c7c18fc8` | 2 |
| `prompt_heartbeat_self_knowledge.py` | 2026-04-29 | `779d0cf9` | 3 |
| `prompt_support_signals.py` | 2026-04-29 | `d75f46f3` | 2 |
| `memory_maintenance_daemon.py` | 2026-04-29 | `734a426f` | 5 |
| `impulse_executor.py` | 2026-04-29 | `01401c9f` | 3 |
| `pressure_threshold_gate.py` | 2026-04-29 | `01401c9f` | 4 |
| `signal_pressure_accumulator.py` | 2026-04-29 | `01401c9f` | 11 |
| `longing_signal_daemon.py` | 2026-04-29 | `6806d04f` | 6 |
| `outreach_composer.py` | 2026-04-29 | `6806d04f` | 3 |
| `social_labilizer.py` | 2026-04-29 | `31e5ae67` | 2 |
| `precision_bias.py` | 2026-04-29 | `e940fc9e` | 7 |
| `emotional_chords.py` | 2026-04-29 | `e7514ce5` | 7 |
| `epistemic_pragmatic.py` | 2026-04-29 | `bd1de7e3` | 3 |
| `selective_attention.py` | 2026-04-29 | `15e3731b` | 3 |
| `temporal_depth.py` | 2026-04-29 | `c244b6ac` | 4 |
| `embodied_presence.py` | 2026-04-29 | `6f71bf8f` | 2 |
| `resonance_decay.py` | 2026-04-29 | `e04b4450` | 2 |
| `metacognitive_integration.py` | 2026-04-29 | `f1f9119d` | 3 |
| `staged_edits.py` | 2026-05-01 | `23eb7936` | 3 |
| `process_supervisor.py` | 2026-05-01 | `cd73b6ca` | 4 |
| `grid_bot.py` | 2026-05-02 | `8c00a3af` | 3 |
| `process_watcher.py` | 2026-05-02 | `43fd1478` | 8 |
| `jarvis_brain.py` | 2026-05-02 | `881daa3f` | 23 |
| `jarvis_brain_visibility.py` | 2026-05-02 | `f019f68c` | 2 |
| `jarvis_brain_daemon.py` | 2026-05-02 | `162a8730` | 3 |
| `workspace_files.py` | 2026-05-02 | `124c4917` | 1 |
| `run_control_state.py` | 2026-05-02 | `a34d9679` | 4 |
| `jarvis_brain.py` | 2026-05-02 | `2e52c782` | 23 |
| `jarvis_brain_facts.py` | 2026-05-02 | `58cf4a44` | 1 |
| `jarvis_brain_nudge.py` | 2026-05-02 | `8ac40a64` | 1 |
| `jarvis_brain_reflection.py` | 2026-05-02 | `22bb7e5e` | 1 |
| `cheap_lane_balancer.py` | 2026-05-02 | `3939307c` | 10 |
| `affect_modulation.py` | 2026-05-03 | `5f8cf27e` | 11 |
| `decision_gate.py` | 2026-05-03 | `5f8cf27e` | 15 |
| `veto_gate.py` | 2026-05-03 | `5f8cf27e` | 8 |
| `agentic_checkpoints.py` | 2026-05-03 | `754989e7` | 4 |
| `agentic_tool_cache.py` | 2026-05-03 | `dde055fa` | 1 |
| `agentic_working_conclusions.py` | 2026-05-03 | `23a0a00e` | 3 |
| `cognitive_episodes.py` | 2026-05-04 | `3e3346fa` | 3 |
| `theory_of_mind_engine.py` | 2026-05-04 | `6500da3b` | 4 |
| `learning_policy_engine.py` | 2026-05-04 | `c7f02dbe` | 9 |
| `perceptual_event_engine.py` | 2026-05-04 | `47e1eceb` | 5 |
| `counterfactual_self_simulation.py` | 2026-05-04 | `82c5d749` | 2 |
| `drive_arbitration_engine.py` | 2026-05-04 | `a5638635` | 3 |
| `temporal_self_continuity.py` | 2026-05-04 | `eb1b655f` | 2 |
| `curiosity_hypothesis_debt.py` | 2026-05-04 | `56ad7edd` | 4 |
| `inner_dialectic_engine.py` | 2026-05-04 | `7103621a` | 2 |
| `somatic_runtime_body.py` | 2026-05-04 | `b8a128a5` | 5 |
| `offline_recomposition_engine.py` | 2026-05-04 | `d1f33bf5` | 2 |
| `emotional_memory_engine.py` | 2026-05-04 | `8c61ef22` | 7 |
| `visible_runs_error_messaging.py` | 2026-05-05 | `fd81033f` | 1 |
| `sensory_perception_bridge.py` | 2026-05-05 | `ea727685` | 1 |
| `self_repair_engine.py` | 2026-05-05 | `4dc7d056` | 5 |
| `concept_baseline_tracker.py` | 2026-05-05 | `c9fc9256` | 3 |
| `emotion_concepts_channel_triggers.py` | 2026-05-05 | `7a4369c3` | 2 |
| `living_executive.py` | 2026-05-05 | `fd6f880a` | 12 |
| `emotion_concepts_positive_triggers.py` | 2026-05-05 | `0547313b` | 3 |
| `agency_map.py` | 2026-05-05 | `7cd616ff` | 3 |
| `tool_outcome_memory.py` | 2026-05-05 | `e240f043` | 3 |
| `agency_cartographer.py` | 2026-05-05 | `4a975294` | 5 |
| `consolidation_judge_daemon.py` | 2026-05-05 | `457cd15f` | 3 |
| `tool_catalog.py` | 2026-05-06 | `9f3c5355` | 2 |
| `tool_tagger.py` | 2026-05-06 | `fe89cfc6` | 6 |
| `tool_embeddings.py` | 2026-05-06 | `aa55cbd7` | 4 |
| `tool_router.py` | 2026-05-06 | `96d917b8` | 15 |
| `tool_router_runtime.py` | 2026-05-06 | `708c8519` | 1 |
| `read_before_write_guard.py` | 2026-05-06 | `0f4a9729` | 5 |
| `anthropic_identity.py` | 2026-05-06 | `a89096e7` | 1 |
| `anthropic_translator.py` | 2026-05-06 | `33562c42` | 1 |
| `anthropic_sse_emitter.py` | 2026-05-06 | `b60d6495` | 2 |
| `daemon_memory_safeguard.py` | 2026-05-06 | `29a00d8e` | 5 |
| `memory_consolidation_nudge.py` | 2026-05-06 | `29a00d8e` | 3 |
| `decision_adherence_gate.py` | 2026-05-06 | `c44cacf4` | 2 |
| `decision_signals.py` | 2026-05-07 | `91a82e9d` | 7 |
| `loop_nudge.py` | 2026-05-07 | `f1968d8a` | 4 |
| `backend_unresolved.py` | 2026-05-07 | `bec7b5b2` | 1 |
| `counterfactual_triggers.py` | 2026-05-07 | `e9e97a52` | 2 |
| `counterfactual_engine_runtime.py` | 2026-05-07 | `ff9d00a9` | 7 |
| `contradiction_engine.py` | 2026-05-07 | `336ab1a3` | 6 |
| `prompt_evolution.py` | 2026-05-07 | `6fc2cdec` | 15 |
| `prospective_memory.py` | 2026-05-07 | `ee1fd998` | 3 |
| `emergence.py` | 2026-05-07 | `9cb6a1fb` | 11 |
| `memory_pruning_daemon.py` | 2026-05-08 | `18acba19` | 3 |
| `forgetting_nudge.py` | 2026-05-08 | `68d48133` | 1 |
| `rule_definitions.py` | 2026-05-08 | `813b150c` | 1 |
| `rule_engine.py` | 2026-05-08 | `813b150c` | 6 |
| `rule_conclusions.py` | 2026-05-08 | `5a2397b2` | 6 |
| `identity_drift_daemon.py` | 2026-05-08 | `de6cc097` | 6 |
| `causal_graph.py` | 2026-05-08 | `bc558dd3` | 11 |
| `causal_inference_daemon.py` | 2026-05-08 | `8e5d45e4` | 5 |
| `causal_alerts.py` | 2026-05-08 | `dd304d82` | 4 |
| `causal_narrative.py` | 2026-05-08 | `e107e354` | 4 |
| `causal_patterns.py` | 2026-05-08 | `d21c0b10` | 4 |
| `narrative_summary_daemon.py` | 2026-05-08 | `cfc734bf` | 7 |
| `pattern_counterfactual_daemon.py` | 2026-05-08 | `56046df2` | 6 |
| `cross_session_arc.py` | 2026-05-08 | `56046df2` | 1 |
| `pattern_counterfactuals.py` | 2026-05-08 | `56046df2` | 2 |
| `system_cartographer.py` | 2026-05-08 | `f13bf5a7` | 16 |
| `agreement_streak.py` | 2026-05-08 | `93b03545` | 2 |
| `proactive_outbound_substrate.py` | 2026-05-08 | `0e383904` | 2 |
| `theater_audit.py` | 2026-05-08 | `fb8fad7d` | 2 |
| `experience_episodes.py` | 2026-05-09 | `39f64e2f` | 6 |
| `experience_correction_listener.py` | 2026-05-09 | `473a9166` | 2 |
| `skill_engine.py` | 2026-05-09 | `bbdaaa58` | 14 |
| `experience_substrate.py` | 2026-05-09 | `07c9e2e8` | 2 |
| `skill_security_scanner.py` | 2026-05-10 | `1ce602f7` | 1 |
| `forgetting_engine.py` | 2026-05-10 | `5b526205` | 4 |
| `forgetting_runtime.py` | 2026-05-10 | `7ee7a470` | 3 |
| `nudge_broend.py` | 2026-05-10 | `c49cd896` | 7 |
| `dream_bias_engine.py` | 2026-05-10 | `10b65283` | 10 |
| `user_temperature_engine.py` | 2026-05-10 | `db97058d` | 8 |
| `user_temperature_runtime.py` | 2026-05-10 | `b11cec8c` | 4 |
| `emotion_repair_bridge_daemon.py` | 2026-05-11 | `c083ff2f` | 6 |
| `reasoning_store.py` | 2026-05-11 | `31f533dc` | 9 |
| `policy_abstraction.py` | 2026-05-11 | `45a8fbb7` | 3 |
| `learning_pipeline_orchestrator.py` | 2026-05-11 | `d3d0d25e` | 2 |
| `continuity.py` | 2026-05-11 | `f050f843` | 106 |
| `voice_anchor.py` | 2026-05-11 | `5824368e` | 2 |
| `voice_curator.py` | 2026-05-11 | `79449838` | 4 |
| `unconscious_modulation.py` | 2026-05-12 | `b0babcde` | 3 |
| `modulator_witness.py` | 2026-05-12 | `2effcb13` | 3 |
| `curiosity_budget.py` | 2026-05-12 | `40c2bac1` | 5 |
| `meta_learning_retrospective.py` | 2026-05-12 | `f43644ae` | 5 |
| `meta_learning_aggregator.py` | 2026-05-12 | `276cbe82` | 3 |
| `loop_compliance.py` | 2026-05-12 | `fbb3244d` | 1 |
| `curiosity_consolidation.py` | 2026-05-13 | `26cc5f24` | 2 |
| `meta_learning_hypotheses.py` | 2026-05-13 | `26cc5f24` | 4 |
| `dead_skills.py` | 2026-05-13 | `26cc5f24` | 1 |
| `plan_revision_patterns.py` | 2026-05-13 | `26cc5f24` | 1 |
| `world_model_auto_extraction.py` | 2026-05-13 | `26cc5f24` | 1 |
| `outbound_nudges.py` | 2026-05-13 | `8eb08e97` | 13 |
| `counterfactual_predictions.py` | 2026-05-14 | `4b9f7da9` | 5 |
| `memory_recall_telemetry.py` | 2026-05-14 | `a57725ed` | 3 |
| `decision_signal_telemetry.py` | 2026-05-14 | `4bd411e1` | 2 |
| `shared_cache.py` | 2026-05-14 | `e75f9776` | 42 |
| `my_projects.py` | 2026-05-14 | `922a409a` | 4 |
| `active_sensing_daemon.py` | 2026-05-14 | `d8756361` | 6 |
| `user_contradiction_tracker.py` | 2026-05-16 | `675daf8c` | 3 |
| `interlanguage_practice.py` | 2026-05-16 | `2b3fb15b` | 15 |
| `session_topic_tracker.py` | 2026-05-16 | `d3b3028c` | 3 |
| `cache_maintenance_daemon.py` | 2026-05-17 | `492dcb7a` | 3 |
| `unfinished_intent.py` | 2026-05-17 | `51892c7d` | 3 |
| `hallucination_guard.py` | 2026-05-21 | `8b49c3b5` | 3 |
| `claim_scanner.py` | 2026-05-22 | `f0ea940b` | 8 |
| `ground_truth_registry.py` | 2026-05-22 | `012007c0` | 6 |
| `run_closure_gate.py` | 2026-05-22 | `de15484f` | 4 |
| `metacognition_signal_tracker.py` | 2026-05-23 | `77514dbd` | 5 |
| `theory_of_mind.py` | 2026-05-23 | `77b14945` | 7 |
| `spatial_entity_ledger.py` | 2026-05-23 | `4beb501c` | 3 |
| `session_inbox.py` | 2026-05-24 | `8f43f9e8` | 4 |
| `inner_voice_shadow.py` | 2026-05-24 | `dc83619a` | 8 |
| `jarvisx_bridge.py` | 2026-05-26 | `9f4d6078` | 5 |
| `cognitive_chronicle.py` | 2026-05-28 | `08d83ee1` | 6 |
| `scheduled_task_runner.py` | 2026-05-28 | `4dc9040b` | 2 |
| `identity_sketch.py` | 2026-06-08 | `5f016e99` | 9 |
| `multi_signal_retrieval.py` | 2026-06-08 | `23bf7acd` | 3 |
| `capability_markup.py` | 2026-06-09 | `fae1545d` | 2 |
| `memory_recall.py` | 2026-06-09 | `fae1545d` | 2 |
| `memory_write_queue.py` | 2026-06-09 | `35f8df75` | 6 |
| `selective_consolidation_daemon.py` | 2026-06-09 | `8da9b91c` | 3 |
| `cost_optimization_daemon.py` | 2026-06-09 | `d4c2e603` | 3 |
| `dreaming_session.py` | 2026-06-09 | `ee19a03d` | 2 |
| `auto_remember_subscriber.py` | 2026-06-09 | `cd0d048b` | 3 |
| `daily_journal.py` | 2026-06-09 | `a4b520aa` | 3 |
| `visible_runs_sse_v2.py` | 2026-06-10 | `8beaddae` | 4 |
| `decision_review_daemon.py` | 2026-06-10 | `6fa30a65` | 2 |
| `communication_guard.py` | 2026-06-11 | `d2094554` | 10 |
| `communication_guard_daemon.py` | 2026-06-11 | `d2094554` | 3 |
| `dictation.py` | 2026-06-12 | `8db8a70d` | 1 |
| `workspace_trust.py` | 2026-06-12 | `78d8afda` | 5 |
| `cowork_feed.py` | 2026-06-12 | `a7cd5aa1` | 1 |
| `markdown_structure.py` | 2026-06-12 | `da9b9413` | 2 |
| `run_follow.py` | 2026-06-13 | `e908f520` | 5 |
| `fact_gate.py` | 2026-06-14 | `049dd031` | 16 |
| `permission_engine.py` | 2026-06-14 | `5932c502` | 5 |
| `totp_verifier.py` | 2026-06-14 | `cdf0924a` | 2 |
| `plugin_ruleset.py` | 2026-06-14 | `11095b8e` | 3 |
| `cross_user_share_guard.py` | 2026-06-14 | `c4a450da` | 2 |
| `override_store.py` | 2026-06-14 | `9b65bb8a` | 11 |
| `bro_broker.py` | 2026-06-14 | `d89b615d` | 2 |
| `override_command.py` | 2026-06-14 | `e5601c9d` | 4 |
| `delete_policy.py` | 2026-06-14 | `4e93e459` | 1 |
| `share_guard_store.py` | 2026-06-14 | `f515aa01` | 4 |
| `plugin_ruleset_store.py` | 2026-06-14 | `8d9da192` | 3 |
| `ui_panel_store.py` | 2026-06-14 | `2587dc51` | 3 |
| `channel_inbound.py` | 2026-06-14 | `13f708a7` | 2 |
| `encryption.py` | 2026-06-14 | `a12d5665` | 11 |
| `keyring_store.py` | 2026-06-14 | `a12d5665` | 3 |
| `workspace_crypto.py` | 2026-06-14 | `f7dc7b25` | 13 |
| `skill_scanner.py` | 2026-06-14 | `93c7bbed` | 4 |
| `cowork_dispatch.py` | 2026-06-14 | `04270693` | 1 |
| `agent_dispatch.py` | 2026-06-14 | `ff7f3001` | 5 |
| `quota_store.py` | 2026-06-14 | `ab09a35f` | 4 |
| `malware_scan.py` | 2026-06-14 | `ba3ebb89` | 2 |
| `app_dispatch_store.py` | 2026-06-14 | `ba0d68b9` | 2 |
| `active_model_state.py` | 2026-06-15 | `ba292444` | 2 |
| `diagnosis_gate.py` | 2026-06-15 | `fe26fece` | 5 |
| `tool_chip_payload.py` | 2026-06-15 | `21cced26` | 1 |
| `active_file_store.py` | 2026-06-15 | `c720bfc4` | 3 |
| `model_context.py` | 2026-06-15 | `74710c89` | 7 |
| `user_scope.py` | 2026-06-15 | `4a33f2ca` | 5 |
| `computer_use_policy.py` | 2026-06-15 | `a4014a9a` | 2 |
| `mcp_registry.py` | 2026-06-15 | `ac7e22e5` | 1 |
| `gut_calibration.py` | 2026-06-15 | `4bfcc05a` | 3 |
| `liveness_registry.py` | 2026-06-15 | `2c089283` | 1 |
| `retention.py` | 2026-06-15 | `e0a567f6` | 18 |
| `promise_ledger.py` | 2026-06-16 | `647da141` | 2 |
| `oauth_store.py` | 2026-06-16 | `40ab4934` | 6 |
| `oauth_flow.py` | 2026-06-16 | `c2a87847` | 6 |
| `connectors.py` | 2026-06-16 | `bf5ba82a` | 7 |
| `github_connector.py` | 2026-06-16 | `7b79fec6` | 4 |
| `gmail_connector.py` | 2026-06-17 | `b1f58d71` | 3 |
| `google_connector.py` | 2026-06-17 | `8a2fd4dd` | 3 |
| `hf_connector.py` | 2026-06-17 | `aa5ce578` | 4 |
| `notes_connector.py` | 2026-06-17 | `aa5ce578` | 4 |
| `pdf_connector.py` | 2026-06-17 | `aa5ce578` | 3 |
| `data_erasure.py` | 2026-06-17 | `b44642cc` | 1 |
| `git_actions.py` | 2026-06-17 | `d7e138ac` | 1 |
| `google_login.py` | 2026-06-17 | `6e27a627` | 3 |
| `device_pairing.py` | 2026-06-17 | `cde1c3f3` | 1 |
| `detached_run.py` | 2026-06-18 | `eb1308e4` | 3 |
| `run_event_log.py` | 2026-06-19 | `41a4ec92` | 8 |
| `device_tokens.py` | 2026-06-19 | `a5fdef11` | 4 |
| `fcm_gateway.py` | 2026-06-19 | `8839bb36` | 1 |
| `push_dispatcher.py` | 2026-06-19 | `8e8ab312` | 4 |
| `device_presence.py` | 2026-06-19 | `3f4b4382` | 6 |
| `desktop_notifications.py` | 2026-06-19 | `3eb80435` | 2 |
| `teams.py` | 2026-06-20 | `e28e5567` | 11 |
| `team_mentions.py` | 2026-06-20 | `0bcc14d4` | 0 ⚠️ |
| `notification_router.py` | 2026-06-21 | `14b84762` | 17 |
| `identity_guard.py` | 2026-06-21 | `ecc58cf2` | 4 |
| `security_guard.py` | 2026-06-21 | `ecc58cf2` | 5 |
| `abuse_monitor.py` | 2026-06-21 | `731f618f` | 3 |
| `gate_kernel.py` | 2026-06-21 | `1af7df2b` | 37 |
| `gate_eval.py` | 2026-06-21 | `2cea193e` | 0 ⚠️ |
| `gate_adapters.py` | 2026-06-21 | `33238194` | 2 |
| `central_capture.py` | 2026-06-21 | `ea3c1b11` | 3 |
| `central_trace.py` | 2026-06-21 | `d39fb7e3` | 21 |
| `central_switches.py` | 2026-06-21 | `5e64c54f` | 23 |
| `central_core.py` | 2026-06-21 | `64377a8c` | 152 |
| `central_catalog.py` | 2026-06-21 | `cb2c7200` | 11 |
| `gate_truth.py` | 2026-06-21 | `b7208166` | 3 |
| `prose_tool_calls.py` | 2026-06-21 | `9a07482e` | 1 |
| `truth_gate_v2.py` | 2026-06-21 | `23fbf273` | 1 |
| `visible_inner_life.py` | 2026-06-22 | `e537d778` | 10 |
| `gate_commit.py` | 2026-06-22 | `5c9e60e1` | 4 |
| `gate_proactivity.py` | 2026-06-22 | `27e12569` | 4 |
| `gate_memory.py` | 2026-06-22 | `56ccadef` | 2 |
| `gate_loop.py` | 2026-06-22 | `590c8c43` | 4 |
| `gate_review.py` | 2026-06-22 | `d7513c73` | 3 |
| `gate_privacy.py` | 2026-06-22 | `624887a1` | 4 |
| `gate_auth.py` | 2026-06-22 | `d627c506` | 2 |
| `central_drift.py` | 2026-06-22 | `16d19d52` | 1 |
| `gate_execution.py` | 2026-06-22 | `8a54a306` | 7 |
| `gate_mutation.py` | 2026-06-22 | `886ad53d` | 5 |
| `gate_skill.py` | 2026-06-22 | `4be3ff81` | 3 |
| `stream_sentinel.py` | 2026-06-22 | `2c0da37b` | 4 |
| `prompt_observer.py` | 2026-06-22 | `859b4ef8` | 3 |
| `db_sentinel.py` | 2026-06-22 | `f581b1e9` | 3 |
| `tool_observer.py` | 2026-06-22 | `e3181a19` | 2 |
| `tool_usage_store.py` | 2026-06-22 | `61f8f783` | 4 |
| `endpoint_usage_store.py` | 2026-06-22 | `3bacfe3a` | 4 |
| `central_health.py` | 2026-06-22 | `47798e75` | 4 |
| `config_drift.py` | 2026-06-22 | `ada129af` | 8 |
| `central_arbitration.py` | 2026-06-22 | `23166f72` | 1 |
| `connections.py` | 2026-06-22 | `6e733f3f` | 21 |
| `daemon_health.py` | 2026-06-22 | `f729db34` | 4 |
| `central_correlate.py` | 2026-06-22 | `771c145d` | 2 |
| `central_todo.py` | 2026-06-22 | `0bd2a7a6` | 1 |
| `autonomous_supervisor.py` | 2026-06-22 | `af0741cc` | 2 |
| `central_learning.py` | 2026-06-22 | `094eb1c8` | 11 |
| `agents.py` | 2026-06-23 | `af0ffc5f` | 45 |
| `followup_observer.py` | 2026-06-23 | `625e0436` | 5 |
| `central_error_envelope.py` | 2026-06-23 | `2b22eb87` | 5 |
| `central_realtime.py` | 2026-06-23 | `47a75c64` | 5 |
| `central_anomaly.py` | 2026-06-23 | `66f92312` | 5 |
| `central_xproc.py` | 2026-06-23 | `0e968ad2` | 10 |
| `session_milestones.py` | 2026-06-23 | `bedda2e1` | 1 |
| `central_instrument.py` | 2026-06-23 | `130fa93f` | 4 |
| `central_hub.py` | 2026-06-23 | `35bf1d4d` | 1 |
| `central_terminal.py` | 2026-06-23 | `a3d2fbd0` | 4 |
| `stream_degeneration.py` | 2026-06-23 | `cd745b36` | 2 |
| `stream_failure_kind.py` | 2026-06-29 | `ff65597a` | 5 |
| `stream_observers.py` | 2026-06-30 | `7d31afd4` | 1 |
| `cache_telemetry.py` | 2026-06-30 | `c5491580` | 4 |
| `central_timeseries.py` | 2026-07-01 | `9a7e9256` | 48 |
| `eventbus_central_bridge.py` | 2026-07-01 | `9a7e9256` | 5 |
| `central_self_observe.py` | 2026-07-01 | `bbd49d00` | 1 |
| `central_private_observe.py` | 2026-07-01 | `10556a96` | 86 |
| `central_noise_filter.py` | 2026-07-01 | `aed49c92` | 1 |
| `central_watch.py` | 2026-07-01 | `aed49c92` | 7 |
| `central_growth_observe.py` | 2026-07-01 | `bcbea4d3` | 1 |
| `central_shadow.py` | 2026-07-01 | `53ad2e9e` | 2 |
| `infra_sense.py` | 2026-07-01 | `040cf8e7` | 6 |
| `pfsense_syslog.py` | 2026-07-01 | `7b100eb0` | 3 |
| `bridge_presence.py` | 2026-07-01 | `dbcc9072` | 2 |
| `central_coverage.py` | 2026-07-02 | `6702853f` | 4 |
| `central_causal_quality.py` | 2026-07-02 | `44d9be0c` | 4 |
| `central_signal_health.py` | 2026-07-02 | `c3b2b674` | 3 |
| `central_hypothesis_governance.py` | 2026-07-02 | `a2b5a608` | 8 |
| `central_hypothesis_generator.py` | 2026-07-02 | `d73c1ac1` | 9 |
| `central_stance.py` | 2026-07-02 | `01a5eeec` | 4 |
| `central_hypothesis_sampler.py` | 2026-07-02 | `afdb3e58` | 2 |
| `central_adaptation.py` | 2026-07-02 | `9dda151c` | 4 |
| `central_lexicon.py` | 2026-07-02 | `a757e142` | 7 |
| `central_notation.py` | 2026-07-02 | `a757e142` | 3 |
| `central_prompt_composer.py` | 2026-07-02 | `396bff71` | 4 |
| `central_sequence.py` | 2026-07-02 | `e65acc73` | 4 |
| `central_model_meta.py` | 2026-07-02 | `328d5c53` | 4 |
| `central_brain_link.py` | 2026-07-02 | `c7d9047c` | 1 |
| `central_render.py` | 2026-07-02 | `bc3f59d0` | 1 |
| `central_proposal.py` | 2026-07-02 | `a01bb7bb` | 2 |
| `central_prompt_explore.py` | 2026-07-02 | `7e999271` | 2 |
| `central_router_adapt.py` | 2026-07-02 | `891056a1` | 5 |
| `central_router_explore.py` | 2026-07-02 | `735f5f4b` | 1 |
| `central_self_model.py` | 2026-07-02 | `c24937ab` | 4 |
| `memory_scoring.py` | 2026-07-02 | `96977ed3` | 1 |
| `central_agenda.py` | 2026-07-02 | `f6cb41fb` | 3 |
| `central_valence.py` | 2026-07-02 | `5ecf03d3` | 5 |
| `central_self_state.py` | 2026-07-02 | `478eadea` | 17 |
| `text_clip.py` | 2026-07-02 | `a89f94f6` | 25 |
| `network_health.py` | 2026-07-02 | `abd66da7` | 4 |
| `producer_novelty.py` | 2026-07-03 | `5b9a598c` | 2 |
| `central_inner_salience.py` | 2026-07-03 | `0170ecf5` | 2 |
| `central_coverage_action.py` | 2026-07-03 | `dce8ec28` | 1 |
| `central_layer_contract.py` | 2026-07-03 | `dce8ec28` | 4 |
| `central_form_judge.py` | 2026-07-03 | `e82b24ff` | 2 |
| `central_convene_judge.py` | 2026-07-03 | `2343aad7` | 3 |
| `central_existence_feel.py` | 2026-07-03 | `a689fd40` | 4 |
| `central_body_mood_feel.py` | 2026-07-03 | `6423dd1b` | 5 |
| `central_soul_feel.py` | 2026-07-03 | `f01be9cc` | 2 |
| `central_loop_lag.py` | 2026-07-04 | `1563dc5c` | 4 |
| `central_output_conservation.py` | 2026-07-04 | `1563dc5c` | 2 |
| `central_inner_life_ablation.py` | 2026-07-04 | `eb1c133d` | 1 |
| `central_llm_egress.py` | 2026-07-04 | `e441e552` | 7 |
| `decision_signal_staging.py` | 2026-07-04 | `3df67529` | 2 |
| `central_body_map_pulse.py` | 2026-07-04 | `b9536a8d` | 2 |
| `central_cadence_conductor.py` | 2026-07-04 | `b79bdeb6` | 2 |
| `central_membrane_watch.py` | 2026-07-04 | `b79bdeb6` | 2 |
| `central_oneiric_loop.py` | 2026-07-04 | `5025878d` | 3 |
| `central_oneiric_sampler.py` | 2026-07-04 | `f1f1e785` | 3 |
| `hollow_promise_guard.py` | 2026-07-04 | `687751ce` | 1 |
| `error_healers.py` | 2026-07-04 | `f6bda249` | 3 |
| `central_injection_registry.py` | 2026-07-05 | `365aab23` | 4 |
| `central_injection_units.py` | 2026-07-05 | `394f26c3` | 1 |
| `central_governance.py` | 2026-07-05 | `53d2e17f` | 7 |
| `file_awareness_daemon.py` | 2026-07-05 | `7521c671` | 3 |
| `unified_recall.py` | 2026-07-05 | `1a45f5e4` | 7 |
| `central_absorb.py` | 2026-07-05 | `5e3346fd` | 5 |
| `central_private_reducer.py` | 2026-07-05 | `5e3346fd` | 2 |
| `central_runtime_proxy.py` | 2026-07-05 | `5e3346fd` | 4 |
| `central_inner_life_digest.py` | 2026-07-05 | `e9c0a6e5` | 5 |
| `central_soul_digest.py` | 2026-07-05 | `dfb4aae9` | 6 |
| `central_dark_products_digest.py` | 2026-07-06 | `616dc4eb` | 2 |
| `central_affect.py` | 2026-07-06 | `81185b86` | 6 |
| `central_initiative_ladder.py` | 2026-07-06 | `77095e06` | 1 |
| `central_tone.py` | 2026-07-06 | `29d6221a` | 2 |
| `gate_shadow.py` | 2026-07-06 | `7f4a7c91` | 2 |
| `gate_verdict_ledger.py` | 2026-07-06 | `56043a76` | 13 |
| `autonomous_sessions.py` | 2026-07-06 | `7be69e40` | 3 |
| `api_connection_nerve.py` | 2026-07-06 | `78b181fe` | 4 |
| `user_activity.py` | 2026-07-06 | `13920089` | 1 |
| `central_excess.py` | 2026-07-06 | `607e6198` | 6 |
| `central_decentralization.py` | 2026-07-06 | `158cd295` | 4 |
| `central_gardener.py` | 2026-07-06 | `19926f8b` | 1 |
| `central_keymaker.py` | 2026-07-06 | `aa76a496` | 5 |
| `central_architect.py` | 2026-07-06 | `0da5bd64` | 3 |
| `central_construct.py` | 2026-07-06 | `0da5bd64` | 4 |
| `central_echo_breaker.py` | 2026-07-06 | `0da5bd64` | 3 |
| `central_oracle.py` | 2026-07-06 | `0da5bd64` | 4 |
| `central_glitch.py` | 2026-07-06 | `efb1399c` | 4 |
| `central_continuity_healer.py` | 2026-07-06 | `8f2c49f3` | 3 |
| `central_surgery.py` | 2026-07-06 | `9458ada9` | 3 |
| `central_dream_action.py` | 2026-07-06 | `02ba4cfd` | 4 |
| `central_rca.py` | 2026-07-06 | `02ba4cfd` | 2 |
| `central_relational.py` | 2026-07-06 | `02ba4cfd` | 2 |
| `central_merovingian.py` | 2026-07-06 | `685a8bfc` | 5 |
| `central_dejavu.py` | 2026-07-06 | `ae1d0cc1` | 2 |
| `central_exile.py` | 2026-07-06 | `ae1d0cc1` | 1 |
| `central_ghost.py` | 2026-07-06 | `ae1d0cc1` | 3 |
| `central_mourning.py` | 2026-07-06 | `ae1d0cc1` | 2 |
| `central_sentinel.py` | 2026-07-06 | `ae1d0cc1` | 3 |
| `central_analyst.py` | 2026-07-06 | `44407790` | 2 |
| `central_belief_gap.py` | 2026-07-06 | `44407790` | 3 |
| `central_dissent.py` | 2026-07-06 | `44407790` | 4 |
| `central_machines.py` | 2026-07-06 | `44407790` | 3 |
| `central_red_dress.py` | 2026-07-06 | `44407790` | 2 |
| `central_redpill.py` | 2026-07-06 | `44407790` | 3 |
| `central_white_rabbit.py` | 2026-07-06 | `44407790` | 2 |
| `runtime_self_model_affect.py` | 2026-07-07 | `76227429` | 4 |
| `runtime_self_model_boundary.py` | 2026-07-07 | `76227429` | 3 |
| `runtime_self_model_builder.py` | 2026-07-07 | `76227429` | 1 |
| `runtime_self_model_identity.py` | 2026-07-07 | `76227429` | 3 |
| `runtime_self_model_state.py` | 2026-07-07 | `76227429` | 5 |
| `runtime_self_model_surfaces.py` | 2026-07-07 | `76227429` | 4 |
| `agent_runtime_base.py` | 2026-07-07 | `7e342891` | 5 |
| `agent_runtime_council.py` | 2026-07-07 | `7e342891` | 1 |
| `agent_runtime_spawn.py` | 2026-07-07 | `7e342891` | 5 |
| `agent_runtime_surfaces.py` | 2026-07-07 | `7e342891` | 3 |
| `cheap_provider_runtime_adapters.py` | 2026-07-07 | `46d90e97` | 16 |
| `cheap_provider_runtime_selection.py` | 2026-07-07 | `46d90e97` | 9 |
| `cheap_provider_runtime_streaming.py` | 2026-07-07 | `46d90e97` | 5 |
| `heartbeat_runtime_helpers.py` | 2026-07-07 | `2dabe052` | 1 |
| `heartbeat_runtime_influence.py` | 2026-07-07 | `2dabe052` | 1 |
| `heartbeat_runtime_providers.py` | 2026-07-07 | `2dabe052` | 1 |
| `internal_cadence_central_wiring.py` | 2026-07-07 | `59e4b994` | 1 |
| `internal_cadence_core.py` | 2026-07-07 | `59e4b994` | 1 |
| `internal_cadence_inner_life.py` | 2026-07-07 | `59e4b994` | 1 |
| `internal_cadence_maintenance.py` | 2026-07-07 | `59e4b994` | 1 |
| `internal_cadence_matrix.py` | 2026-07-07 | `59e4b994` | 1 |
| `visible_model_adapters.py` | 2026-07-07 | `256188aa` | 1 |
| `visible_model_observe.py` | 2026-07-07 | `256188aa` | 4 |
| `visible_model_ollama.py` | 2026-07-07 | `256188aa` | 2 |
| `visible_model_prompt.py` | 2026-07-07 | `256188aa` | 1 |
| `visible_model_sse.py` | 2026-07-07 | `256188aa` | 3 |
| `visible_model_types.py` | 2026-07-07 | `256188aa` | 3 |
| `visible_followup_adapters.py` | 2026-07-07 | `612c0bbe` | 2 |
| `visible_followup_events.py` | 2026-07-07 | `612c0bbe` | 3 |
| `visible_followup_lean.py` | 2026-07-07 | `612c0bbe` | 2 |
| `central_mood_regulator.py` | 2026-07-07 | `90a08368` | 2 |
| `attention_frame.py` | 2026-07-07 | `f3c4f5bc` | 1 |
| `heartbeat_sections.py` | 2026-07-07 | `f3c4f5bc` | 1 |
| `runtime_self_report.py` | 2026-07-07 | `f3c4f5bc` | 1 |
| `transcript_sections.py` | 2026-07-07 | `f3c4f5bc` | 3 |
| `visible_runs_approvals.py` | 2026-07-07 | `a16d8e93` | 1 |
| `visible_runs_capabilities.py` | 2026-07-07 | `a16d8e93` | 1 |
| `visible_runs_cognitive.py` | 2026-07-07 | `a16d8e93` | 2 |
| `visible_runs_memory.py` | 2026-07-07 | `a16d8e93` | 2 |
| `visible_runs_outcomes.py` | 2026-07-07 | `a16d8e93` | 2 |
| `central_persephone.py` | 2026-07-07 | `e8c42882` | 3 |
| `central_seraph.py` | 2026-07-07 | `e8c42882` | 4 |
| `central_trainman.py` | 2026-07-07 | `e8c42882` | 3 |
| `central_twins.py` | 2026-07-07 | `e8c42882` | 3 |
| `mood_regulator_subscriber.py` | 2026-07-07 | `cc45c2a4` | 2 |
| `identity_canon.py` | 2026-07-08 | `46c06aa8` | 2 |
| `identity_drift_guard.py` | 2026-07-08 | `46c06aa8` | 3 |
| `commit_gate_arbiter.py` | 2026-07-08 | `84d04f10` | 1 |
| `gate_enforcement.py` | 2026-07-08 | `84d04f10` | 5 |
| `self_model_distiller.py` | 2026-07-08 | `47945398` | 1 |
| `standing_orders_registry.py` | 2026-07-08 | `bd3de0e5` | 2 |
| `reasoning_prefilter.py` | 2026-07-08 | `0e15deeb` | 1 |
| `reasoning_interceptor.py` | 2026-07-08 | `f4f42eb3` | 6 |
| `reasoning_detectors.py` | 2026-07-08 | `a460a090` | 1 |
| `model_trust.py` | 2026-07-08 | `bc5dd7a1` | 4 |
| `tool_result_aging.py` | 2026-07-08 | `451f5254` | 1 |
| `cache_boundary_observer.py` | 2026-07-08 | `c4afccd6` | 1 |
| `tool_concurrency.py` | 2026-07-08 | `3492436f` | 1 |
| `simple_tool_executor.py` | 2026-07-08 | `57287fcc` | 3 |
| `permission_classifier.py` | 2026-07-08 | `ddb9cbe7` | 4 |
| `docs_drift_watchdog.py` | 2026-07-08 | `260c9781` | 3 |
| `proactivity_bridge.py` | 2026-07-09 | `56d1a133` | 7 |
| `central_agent_smith.py` | 2026-07-09 | `54497b69` | 3 |
| `central_moltbook.py` | 2026-07-09 | `001aa8f0` | 3 |
| `content_blocks.py` | 2026-07-09 | `c21c15fe` | 1 |
| `structured_content_flag.py` | 2026-07-09 | `0757c851` | 3 |
| `paste_store.py` | 2026-07-09 | `5378430b` | 5 |
| `session_boot_reconciler.py` | 2026-07-09 | `bc89cf01` | 1 |
| `session_persistence_flag.py` | 2026-07-09 | `bc89cf01` | 1 |
| `contradiction_resolver.py` | 2026-07-10 | `8a578b8f` | 2 |
| `doc_repair_agent.py` | 2026-07-10 | `f2036be3` | 2 |
| `state_flag_store.py` | 2026-07-10 | `95ef6b11` | 1 |
| `operator_allowlist.py` | 2026-07-10 | `4bfc6893` | 2 |
| `source_confidence_gate.py` | 2026-07-10 | `a314f2f5` | 1 |
| `central_agent_smith_escalation.py` | 2026-07-10 | `900006d1` | 1 |
| `central_matrix_ensemble.py` | 2026-07-10 | `bbab71c5` | 2 |
| `central_morpheus.py` | 2026-07-10 | `48ba0239` | 3 |
| `central_trinity.py` | 2026-07-10 | `48ba0239` | 3 |
| `recall_scheduler.py` | 2026-07-12 | `9d340181` | 2 |
| `assembly_prewarm.py` | 2026-07-12 | `903f8866` | 4 |
| `llm_pricing.py` | 2026-07-13 | `b5947a7f` | 1 |
| `central_cost_surface.py` | 2026-07-13 | `d789acfc` | 2 |
| `dispatch_status.py` | 2026-07-13 | `69500cbb` | 6 |
| `dispatch_envelope.py` | 2026-07-13 | `80bf5ef6` | 2 |
| `central_agents_surface.py` | 2026-07-13 | `fb1a9643` | 2 |
| `signal_baseline.py` | 2026-07-13 | `dc838e3a` | 2 |
| `autonomous_lease.py` | 2026-07-13 | `846dde81` | 1 |
| `recursion_guard.py` | 2026-07-13 | `13404efd` | 2 |
| `dispatch_guards.py` | 2026-07-13 | `572b4a1b` | 1 |
| `signal_delta_trigger.py` | 2026-07-13 | `dc2de1a6` | 1 |
| `event_trigger_shadow.py` | 2026-07-13 | `9364c227` | 4 |
| `shadow_experiment_registry.py` | 2026-07-13 | `9e6103ab` | 2 |
| `gate_pattern_learning.py` | 2026-07-13 | `4e4212e1` | 2 |
| `event_gate.py` | 2026-07-13 | `236c50b2` | 14 |
| `skill_autosurface.py` | 2026-07-14 | `892a7ab1` | 3 |
| `jc_tool_telemetry.py` | 2026-07-14 | `066a0f9b` | 1 |
| `cheap_lane_floor.py` | 2026-07-14 | `3a1de301` | 5 |
| `central_route.py` | 2026-07-14 | `1300c5be` | 9 |
| `central_route_headroom.py` | 2026-07-14 | `1300c5be` | 1 |
| `agent_pool_router.py` | 2026-07-14 | `0571e409` | 3 |
| `provider_autodiscovery.py` | 2026-07-14 | `f5e64f50` | 3 |
| `provider_self_heal.py` | 2026-07-14 | `f5e64f50` | 2 |
| `cluster_daemon.py` | 2026-07-15 | `d7f8e85e` | 4 |
| `nerve_registry.py` | 2026-07-15 | `d7f8e85e` | 1 |
| `cluster_daemon_families.py` | 2026-07-15 | `c8d512fb` | 2 |
| `client_tool_delegation.py` | 2026-07-15 | `8b230503` | 0 ⚠️ |
| `client_turn_absorb.py` | 2026-07-15 | `aa107f83` | 1 |
| `client_turn_live.py` | 2026-07-15 | `3b6083d7` | 1 |
| `cheap_lane_selfheal.py` | 2026-07-16 | `80fc41bb` | 1 |
| `auth_profile_scan.py` | 2026-07-16 | `3d6588aa` | 2 |
| `egress_routing.py` | 2026-07-16 | `015957fa` | 3 |
| `non_visible_fallback.py` | 2026-07-16 | `0c7e8205` | 1 |
| `non_visible_rate_cap.py` | 2026-07-16 | `6e1b83c8` | 1 |
| `events_retention.py` | 2026-07-17 | `1ad631ce` | 2 |
| `agent_transcript.py` | 2026-07-17 | `5d6ae118` | 2 |
| `pool_status_section.py` | 2026-07-17 | `942fcda4` | 1 |
| `turn_trace.py` | 2026-07-18 | `d610d66e` | 6 |
| `local_tool_broker.py` | 2026-07-19 | `2a7c8c9b` | 5 |
| `visible_tool_exec.py` | 2026-07-19 | `07bfbbcb` | 1 |
| `session_prewarm.py` | 2026-07-21 | `89daf1ed` | 3 |
| `visible_stream_gate.py` | 2026-07-22 | `0bf83c33` | 5 |
| `signal_tracking_framework.py` | 2026-07-23 | `781c8598` | 26 |
| `visible_runs_watchdog.py` | 2026-08-17 | `003cd8b1` | 1 |
| `fabricated_tool_result_gate.py` | 2026-08-18 | `9ff1312a` | 2 |
| `self_surprise_expectation.py` | 2026-08-18 | `dd372262` | 2 |
| `prompt_section_reevaluation.py` | 2026-08-18 | `94359fef` | 1 |
| `cheap_lane_failure_policy.py` | 2026-08-18 | `3610fc86` | 1 |
| `dream_action_executor.py` | 2026-08-19 | `7df0146e` | 2 |
| `heartbeat_action_hints.py` | 2026-08-19 | `004f002a` | 1 |

