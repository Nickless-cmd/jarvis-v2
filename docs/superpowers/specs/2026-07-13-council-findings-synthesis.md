---
status: reference (råds-fund — den afledte plan 2026-07-13-dispatch-redesign-phase1 er ~70% impl, K2-bug fikset; ikke et selvstændigt byggemål)
oprindelig_status: rådets samlede fund (5 linser, 13. jul 2026)
formål: Konsolideret output fra et 5-medlems review-råd på reference-modellen
         (2026-07-13-claude-orchestration-reference.md). Rangeret, kode-grounded,
         byg-klart. Alle fund cross-checket mod faktisk kode/historik.
råd: adversarial-blindspot · jarvis-code-rendering · tests/edges/docs · dead-code · Central-wiring
---

# Rådets fund — hærdning af dispatch/råd-redesignet

Rådet fandt at reference-modellen er RIGTIG i form, men at kontrakten validerer STRUKTUR
ikke SANDHED, og at den antager levering den ikke håndhæver. To live-bugs, ét katastrofe-
landminet, og en liste hærdnings-features der gør den bulletproof. Rangeret efter alvor.

## §1 KRITISKE KORREKTIONER (skal med før noget som helst bygges)

### K1 — Council-MOTOREN er DELT. Slet den ikke. (dead-code-medlemmet)
"Det gamle council-system" er IKKE én død ting. Motoren (`create_council_session_runtime`,
`run_council_round`, `DeliberationController`, tabellerne `council_sessions`/`council_members`)
kaldes af TRE stier: (1) den blinde daemon [SLET], (2) Jarvis' egen on-demand `convene_council`-
tool [BEHOLD — simple_tools_native.py:1659], (3) Mission Control [BEHOLD — mission_control_agents.py:369].
→ "Riv council ned" = retire KUN den blinde daemon-trigger + fast-tærskel-gaten. Sletter man
motoren, brækker man et live bruger-vendt tool + MC. Den nye "råd = fan-out+syntese" GENBRUGER motoren.

### K2 — Der er en LIVE falsk-success i koden lige nu (adversarial + tests, uafhængigt)
`agent_runtime_base.py:262` hardkoder `"status": "completed"` og mangler `duration_ms` +
`tool_calls` + typet fejl-status. Det er PRÆCIS den fejltilstand kontrakten forbyder — og den
er live nu. Envelope-fixet + typet status skal lande FØR `agent_tools_enabled` flippes on.

### K3 — Byggeklodserne er allerede i FRAKOBLET+LLM-kvadranten (Central-wiring)
`council_deliberation_controller`, `agent_dispatch`, `agent_runtime_council`, `tool_scoping` m.fl.
er allerede frakoblet Centralen — den ANTI-mønster Bjørn vogter mod. Hvis den nye controller kun
emitter til agent-registry-DB/`agent_outcomes_log` (begge frakoblede), forbliver Centralen blind.

## §2 HÆRDNINGS-KONTRAKTEN (4 regler → 4 regler + 12 værn)

Reference-doc §4.2's fire regler er god FORM men validerer kun struktur. Rådet tilføjer 12 værn
(adversarial-medlemmet), hver mod en fejltilstand med præcedens i systemets egen historie:

**Trigger-værn (mod token-runaway — den vigtigste klasse):**
1. **Hysterese-bånd** på hver delta-tærskel: fyr ved θ_high, gen-arm først under θ_low (θ_low<θ_high).
   Dræber flapping (signal der oscillerer 0.24↔0.26 → fuld dispatch hver tick = VÆRRE end timeren).
2. **Debounce + coalescing:** per-signal cooldown (behold de gamle 20 min — de var beskyttende) +
   global "ét wake pr. heartbeat, batch ALLE krydsede signaler i én kontekst" (mod thundering herd
   når korrelerede signaler krydser samtidig).
3. **Persisteret baseline + cold-start-guard:** baseline i DB (ikke in-memory — Jarvis reboot'er
   konstant → in-memory=nulstil→storm ved HVER restart). På cold-start: undertryk delta-fyring de
   første M heartbeats til frisk baseline er sat.
4. **Absolut-gulv ELLER delta:** trigger = `(delta>θ) OR (absolut>θ_abs holdt i T)`. Ren delta er
   blind for langsom monoton drift (slow-boil): signal kryber 0.001/tick i timer, ingen delta
   krydser, men absolutværdien er nu ekstrem.

**Dispatch/konvolut-værn (mod stille fejl + løgn):**
5. **Dead-man-timeout:** hvert dispatch registrerer en forventet-færdig-deadline; ingen notifikation
   → controller SYNTETISERER en `TIMED_OUT`-konvolut. Uden dette: dræbt proces (OOM/restart/
   CancelledError — kendt bug survival_spam_rootcause) → enten evig venten ELLER en `finally` der
   skriver en LØGNAGTIG "completed".
6. **Konvolut-plausibilitet:** afvis/flag `status=completed` med `tokens_out==0`; krydstjek påstået
   `tool_calls` mod faktisk `execute_tool`-gatede kald. Genbrug source-confidence/hollow-promise-
   værnene til at GRADE resultatet, ikke bare dets form (svag model fejler ved DISHONEST success).
7. **Subscriber-ack:** landings-stien skal assertere ≥1 abonnent ved dispatch (fejl højlydt ved nul)
   — så den døde-kø-bug (council.initiative_proposal havde NUL abonnenter) ikke kan gentage sig stille.
8. **Idempotens-nøgle pr. (signal, baseline-epoke):** marker delta forbrugt ATOMISK med dispatch;
   afvis gen-dispatch på samme uforbrugte krydsning (mod dobbelt-dispatch ved crash-før-record).

**System-værn (mod runaway/rekursion):**
9. **Circuit-breaker:** N fejlede dispatches i vindue → trip → stop lanen, marker til Bjørn,
   auto-reset efter cooldown (mod retry-loop når provider nede/kvote-ramt — router_adapt_quota_blind).
10. **Hård budget-loft pr. periode:** max autonome dispatches OG max cost_usd pr. rullende 24t,
    HÅNDHÆVET af det billige non-LLM-lag FØR LLM'en fyrer. Det er backstoppen der gør "idle=nul brænd"
    sikkert selv hvis alle andre værn har en bug. (`jc cost` MÅLER; dette HÅNDHÆVER.)
11. **Rekursions-guard:** max spawn-dybde (fx 2), max total samtidige autonome agenter, max fan-out
    pr. dispatch; `can-spawn` dekrementerer et dybde-budget båret i konvolutten.
12. **Gensidig udelukkelse visible↔autonom:** en lease så et autonomt nudge ikke kan mutere
    self-model/central-state mens en visible-tur kører (udskyd til markør). Løser åben-Q1 sikkert.

## §3 EVENT-TRIGGER — designbeslutninger (løser åben Q2)
Rådets svar på "hvad tæller som markant ændring": **gæt ikke tallene.** Nice-to-have #1 (adversarial):
**shadow-mode delta-meter FØRST** — kør delta-tjekket live men LOG kun hvad det VILLE have dispatchet
(antal, hvilke signaler, simuleret cost) i nogle dage (præcis som memory_scoring shadow-mode). Kalibrér
θ_high/θ_low mod ægte signal-spor i stedet for at gætte, og BEVIS at flapping/herd-værnene virker før
én token brændes. Delta-reglen selv: hysterese-bånd + absolut-gulv-OR + composite-coalescing + persisteret
baseline. Nice-to-have #2: per-signal "dispatch-effektivitet"-feedback — undertryk signaler hvis dispatches
aldrig LANDER noget (mod nudge-fatigue; lukker loopet det gamle system manglede).

## §4 RETIRE-KORT (dead-code-medlemmet — lille, rent sæt)
**SLET:** `autonomous_council_daemon.py` (hele modulet — 0.25/30-min-gaten) + registry-entry
(daemon_manager.py:221) + heartbeat-tick (heartbeat_runtime_influence.py:863) + surface-reg
(signal_surface_router.py:155,251) + durable counters-kv + statiske rolle-maps + council→push_initiative-landing.
**BEHOLD-som-kim, REPLACE-rolle:** `central_convene_judge.py` (tærskel _MOVEMENT_THRESHOLD=0.30 → delta;
dens `_derive_roles`/`_derive_topic_hint` er den RIGTIGE dynamiske model — behold). `existential_wonder_daemon`
(BEHOLD wonder-output — load-bearing, fødes af 4 systemer; REPLACE kun 24t-cadencen → event/delta).
**BEHOLD urørt (load-bearing landminer):** council-motoren, `DeliberationController`, council-tabellerne,
`convene_council`/`quick_council_check`-tools, `spawn_agent_task`, `push_initiative`-køen (30+ callers,
delt bus — kun council→queue-wiringen retires), wonder-generering.
**Sikker rækkefølge (live container):** (1) neutralisér trigger via daemon-enable-flag [ingen deploy] →
(2) convene_judge shadow → (3) fjern tick+registry, deploy, compileall → (4) fjern surface (eller shim
1 deploy mod jc-500) → (5) slet modulet → (6/7) rolle-maps + wonder-cadence følger med. Hvert trin revertbart.

## §5 CENTRAL-WIRING-KONTRAKT (Central-medlemmet — byg PÅ det der findes)
3 skrive-flader: `central().observe` (synlighed→SSE-feed+trace), `central().decide` (govern+kill-switch+
drift+ledger), `central_timeseries.record` (numeriske kurver→`jc series`). Byg PÅ `core/services/agents.py`
(allerede KOBLET: note_agent_spawn/error/council/agents_summary, cluster "agents") — opfind IKKE en parallel cluster.
- **Kritisk gap:** `agent_runtime_spawn.py:398-430` beregner tokens/status men kalder IKKE `record_cost`.
  Wire `record_cost(lane="agent",…)` ved completion (:~421) + failure (:472) → agent-spend flyder til
  `jc cost` GRATIS via eksisterende chokepoint (det vi lige byggede).
- Nye nerver (alle cluster "agents"): `agent_result` (konvolutten) + timeseries `event_trigger`
  (delta-kurve, `crossed`-flag beviser idle=nul), `agent_duration_ms`, `agent_tokens`, `council_convene`.
  Typede blocks via SEPARAT `agent_blocked`-observe (IKKE note_agent_error — ville oppuste fejl-rate-drift).
  Tool-scope + approval-hits via `central().observe` + `gate_enforcement.note_suppressed_block`.
- Nye surfaces `/central/agents` + `/central/council` + `jc agents`/`jc council` — fylder Mind-hubs
  ALLEREDE-erklærede placeholder-tabs (`central_hub._SECTION_ORDER` har "council"/"agency", mangler builders).
- **Kill-switch findes:** `central_switches` + `/central/nerve/{nerve}/toggle` + `jc toggle` — genbrug.
- **ACCEPTANCE-GATE (hård):** kør `python scripts/central_connectivity_audit.py`; efter redesign SKAL
  `council_deliberation_controller`/`agent_dispatch`/`tool_scoping` være flyttet FRAKOBLET→KOBLET, og
  NUL nye FRAKOBLET+LLM-rækker. Bag ind i planens verify-trin.

## §6 jarvis-code RENDERING (rendering-medlemmet — genbrug foldbar runde-blok verbatim)
Agent-dispatch = ny entry-`kind` i samme `_round`-liste; konvolutten (`tok · dur · $`) i diff-stat-slotten.
- **Enkelt agent:** live spinner (fed ind i eksisterende `_spin_i`/liveness-tick) + optællende dur →
  lander som `[▸ agent:searcher · <topic>  41k tok · 4.2s · $0.004 ✓]`, body = agentens retur (foldet default).
- **Råd:** ét parent-entry `kind="council"` med `children=[…]`; per-medlem spinner→resultat; collapsed
  resting-linje `[▸ council · 5 agenter · 5/5 ✓ · 128k · 3.1s ✓]`; dur = MAX (parallel), tokens = sum.
- **Fejl loud+typet:** nye statuses i `_status_frag` — FAILED(rød)/TIMEOUT(rød ⧖)/BLOCKED(gul ⊘)/
  NEEDS_CTX/CONCERNS, fed badge, umuligt at overse; parent degraderer ✓→⚠ hvis barn non-green (synligt collapsed).
- **Baggrunds-dispatch (§1.8):** fryser som running, wake-on-done emitter frozen scrollback-linje via samme
  grammatik `⟲ agent:builder landede · 62k · 48.3s ✓ (baggrund)`. Matcher eksisterende freeze-model.
- Funktioner at udvide navngivet: `render._status_frag/_status_label/envelope_meta/council_summary/
  tool_entry_lines/render_round`; `repl_ptk._round_add/_round_update/_agent_add/_council_add`. Holder desk i sync
  (ToolCard.tsx samme head-grammatik).

## §7 TESTS/EDGES/DOCS (tests-medlemmet — dæknings-matrix)
Testfiler (NYE): `test_signal_delta_trigger.py` (fires-on-rise / flat-fires-NUL-LLM / hysterese-bånd /
debounce / baseline-updates / cold-start), `test_dispatch_envelope.py` (7 nøgler / typet-fejl-ikke-completed
= regression-guard på :262 / usage-på-fejl / cost→ledger), `test_return_or_stop.py`, `test_agent_tools_gate.py`
(allowlist honored / flag off→text-only / execute_tool-gate holder), + council fan-out + Central-surface.
**Bevis-testen for hele præmissen:** `test_flat_for_n_ticks_zero_llm_calls` — assertér provider-kald == 0
over mange flade ticks. Uden den er "dræber"-problemet ubevist.
**13 edges hver m. fangende test:** flapping, cold-start-no-baseline, concurrent-dispatch-race (durable lease),
agent-timeout, tom/malformet retur, flag-flip-mid-dispatch (frys scope ved dispatch-start), budget-exhausted-
mid-council, missed-tick (persisteret baseline), DB-utilgængelig-ved-konvolut-skriv (fail-loud), idle-burn-
regression, all-agents-fail (ingen fabrikeret syntese), retry-uden-ændring, restart-churn.
**Docs:** denne ref (pin delta-tal + typet-status-enum + testbar-kontrakt-subsektion), 2026-07-03-spec
(status færdig→in-progress; markér daemon superseded), CLAUDE.md (envelope-regel + retire-Boy-Scout), NY runbook
(kill-switch-flags + aktiverings-rækkefølge + in-memory→durable-baseline).

## §8 ANBEFALET BYG-RÆKKEFØLGE (rådets samlede logik)
1. **Konvolut + typet status + record_cost(lane=agent)** — fix K2's live-bug; alt hviler på det.
2. **Central-wiring af det eksisterende** (agents.py-nerver + record_cost-seam) — så vi kan SE alt fra tur 1.
3. **Event-trigger i SHADOW** (delta-meter, logger-kun) — kalibrér θ mod ægte spor; convene_judge shadow.
4. **Hærdnings-værnene** (§2) som del af triggeren, IKKE bagefter — hysterese/dead-man/budget-loft/idempotens.
5. **Retire den blinde daemon** (§4 rækkefølge) — først når den nye trigger er bevist i shadow.
6. **jarvis-code rendering** (§6) parallelt — klient-loop + konvolut-visning.
7. **Flip flags** (event-trigger on, så `agent_tools_enabled` on) — kun efter konvolut+værn+audit-gate grøn.
8. **Acceptance:** connectivity-audit grøn (3 flyttet, 0 nye FRAKOBLET+LLM) + idle-burn-test 0 kald + jc cost før/efter.

## §9 DE 3 ÅBNE SPØRGSMÅL — rådets anbefalede svar
- **Q1 (vække vs markør):** MARKØR default (værn #12: gensidig udelukkelse — afbryd aldrig en visible-tur).
  Kun proaktiv vækning når Jarvis er idle OG signalet er høj-værdi. → marker-first, opt-in wake.
- **Q2 (markant ændring):** gæt ikke — SHADOW-meter først (§3), sæt θ_high/θ_low fra ægte spor; delta-regel =
  hysterese + absolut-gulv-OR + composite-coalesce + persisteret baseline.
- **Q3 (selv-indkald eksistentielt):** behold KAPACITETEN (wonder er load-bearing) men event-gated som alt
  andet — wonders rutes gennem convene_judge/event-trigger, ikke en blind 24t-timer.
