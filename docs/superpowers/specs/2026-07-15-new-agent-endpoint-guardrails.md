# Nye agent-endpoint — guardrails & acceptance (MÅ IKKE bloate prompten)

**Dato:** 2026-07-15
**Formål:** Bjørns eksterne hukommelse for foreningen. ALT den nye agent-endpoint (den fulde-hjerne
klient-drevne `/v1/agent/step` under delt substrat) SKAL få rigtigt, så vi ikke bloater Jarvis' prompt og
så compaction bliver ægte. Bevis i jarvis-code FØRST, desk adopterer bagefter. Alt flag-gated.

> Bjørn (ADHD, ude af fokus): "husk alle de vigtige ting og de ting jeg glemmer at nævne." Dette dokument
> ER den huskeliste. Opdatér det når nye krav dukker op.

---

## A. Prompt-bloat guardrails — den nye endpoint MÅ:

### A1. Lean-per-round (VIGTIGST — det Bjørn understregede)
I de **agentiske runder** (mid-tur tool-loops) sendes **KUN den nødvendige lean prompt** — IKKE hele
awareness-blokken. Den fulde awareness re-komponeres **kun ved tur-grænser** (tur-start / efter hele runet).
Desk gør præcis dette (`visible_runs`: lean-prompt-snapshot pr. runde, `prompt_assembly_postool` genbygger
kun ved behov). **FÆLDE:** agent_step ctx=full's `_full_context` bygger den FULDE assembly hver step i dag →
det ville bloate HVER runde. Den nye endpoint SKAL skifte til lean-per-round + fuld-awareness-ved-grænse.

### A2. Cache-split (Fase A1, LEVERET, flag off)
Volatil hale flyttet bag samtalen → `[stabilt system + samtale]` cacheligt. Fikser 25s.

### A3. Alle desks komprimerings-lag SKAL bæres (ikke droppes i den nye endpoint)
- **Per-rolle 8000-tegns-cap** på transcript-beskeder (silent truncate).
- **Tool-resultat hot-tail/cold-storage:** fuld body på disk (`result_id`), kun `[tool]: summary` (cap 1500)
  i historikken. Ikke inline megabytes.
- **Tool-resultat-aging** i det agentiske loop: ryd/LLM-komprimér ældre tool-resultater (keep_full nyeste).
- **Awareness-budget** (6000 tegn, prioritets-sorteret drop).
- **Identity-sketch** (rullende komprimeret "hvem er Jarvis nu").
- **Alternation-trimning** (drop/merge beskeder der bryder user/assistant-veksling — ingen fabrikeret filler).
- **Micro-komprimering** af div. sektioner (jarvis_brain-budget, attention_frame osv.).

### A4. Growing-window transcript (ikke sliding)
Transcript vokser til compact-markør (cache-stabilt prefix), IKKE sliding (som dræbte cachen til 3-5%).

---

## B. Ægte compaction i jarvis-code (Claude Code-stil) — SKAL erstatte den nuværende fake

**Nuværende (fake, skal væk):** char/3-% + besked-antal-trigger (>50) + naiv 200-tegns-trunkering + INGEN
pause-UX. **Mål (ægte):**
1. Under composeren: **"xx% til komprimering"** baseret på **ægte tokens** (serverens tokenizer + reelt forbrug).
2. Ved tærskel: **STOP → compact → FORTSÆT** — ligesom Claude Code. Server-ejet compaction (ægte LLM-resumé +
   `compact_marker` + growing-window). **Kontekst bevaret** hen over compaction.
3. En **SSE-lifecycle** (compaction-started → done) som BEGGE klienter (jarvis-code + desk) renderer ens.
4. Serveren ejer al compaction; klienten rører aldrig markers.

---

## C. Den fulde hjerne SKAL fyre (ellers mister Jarvis sig selv)
- **Per-step:** fuld prompt-assembly (lean-per-round, A1) + per-step-gates (TruthGate v2 / claim_scanner /
  reasoning_interceptor) — serveren ser hvert step (round-trip), håndhæver uden at eje loopet.
- **Tur-slut (absorb):** ~85 trackers (`_update_cognitive_systems_async` ~25 + `_track_runtime_candidates`
  ~61) + memory-postprocess + episode-writers (cognitive/experience/theory_of_mind/perceptual) +
  `record_cost(lane=visible)` + eventbus + gate-verdict-ledger + model-trust.
- **Sessioner:** server-ejede, delte (cross-surface kontinuitet). user-rækken persisteres server-side (ellers
  fyrer heartbeat/inderliv proaktive pings oven på en live samtale).

---

## D. Proces-guardrails
- **jarvis-code FØRST, desk bagefter.** Desk er rimelig stabil nu — vi rører den ikke før jarvis-code beviser
  det ende-til-ende. Desk adopterer det delte substrat i Fase D.
- **Alt flag-gated, bagudkompatibelt, systemet altid kørende.**
- **Ét delt loop** (`jc_agent_loop`) — ingen divergens mellem desk og jarvis-code.

---

## E. Acceptance-checkliste (før en fase kaldes "færdig")
- [x] **Agentiske runder sender lean prompt** — LEVERET i jarvis-code (jc master 4fa5aab): `run_one_step`
  (delt substrat) → step 0 fuld kontekst, runder 2+ `identity`. Flag `lean_per_round` default True. 7 tests.
- [x] **Fuld awareness re-komponeret ved tur-grænse** — `_turn_step_idx` nulstilles pr. tur → step 0 = fuld.
- [ ] Tool-resultater cold-storaget som `[tool]: summary` (cap 1500), fuld body på disk.
- [ ] Cache-split ON: stor session cache-hit >80%, latency mod ~7-8s (før/efter-tal).
- [~] **Ægte token-% + %-trigger + synlig pause→compact→fortsæt** — LEVERET i jarvis-code (jc master
  3488563): `_context_estimate` bruger serverens prompt_tokens (ægte), trigger bundet til %'en
  (`jm.should_compact`), synlige "🗜 komprimerer…/✓ komprimeret"-linjer, kontekst bevaret. UDESTÅR: ægte
  LLM-resumé (i dag klient-lokal trunkering) + server-ownership + SSE-lifecycle → kommer i Fase C.
- [~] **Absorb fyrer alle ~85 trackers + memory + episodes** — endpoint BYGGET (v2 main aa107f83):
  `POST /v1/agent/turn-absorb` + `client_turn_absorb.py` konstruerer VisibleRun + fyrer
  set_last_visible_run_outcome (→ ~25 cognitive) + _track_runtime_candidates (~61) + _run_memory_postprocess.
  Flag `agent_turn_absorb_enabled` default off. UDESTÅR: klient-wiring (jarvis-code POSTer ved tur-slut) +
  flip + live-verifikation af at trackers faktisk fyrer på containeren.
- [ ] Delt session skrevet fra jarvis-code synlig + konsistent i desk.
- [ ] Samme prompt i desk vs jarvis-code → byte-identisk hjerne + identisk render.
- [ ] Prompt-størrelse pr. runde IKKE vokset vs desk i dag (ingen bloat-regression).

---

## Relaterede dokumenter
- [shared-substrate-unification-design.md](2026-07-15-shared-substrate-unification-design.md) — arkitekturen.
- [jarvis-code-capability-surface.md](2026-07-15-jarvis-code-capability-surface.md) — klient-parity-mål.
- [v2-responsibility-surface-map.md](2026-07-15-v2-responsibility-surface-map.md) — hjernen (compression-lag i §Lag B/C).
