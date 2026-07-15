# Delt substrat — jarvis-code ↔ v2 forening (endeligt design)

**Dato:** 2026-07-15
**Status:** Arkitektur godkendt af Bjørn (Option B, delt substrat). Afløser Option-A-designet
([2026-07-15-jarvis-code-v2-unification-design.md](2026-07-15-jarvis-code-v2-unification-design.md), historik).
**Grundlag:** [v2-responsibility-surface-map.md](2026-07-15-v2-responsibility-surface-map.md) (hjernen) +
[jarvis-code-capability-surface.md](2026-07-15-jarvis-code-capability-surface.md) (klient-fladen, parity-mål).

---

## 1. Mål

Jarvis må ALDRIG kunne mærke forskel på desk code mode og jarvis-code. Én hjerne, én hukommelse, delte
sessioner, ét capability-lag — overalt. Kun forskel: HVOR hænderne (tools) kører.

## 2. Kernemodel: ét delt loop, server-hjerne via de kald loopet allerede laver

`jc_agent_loop` er det UI-frie, delte substrat begge overflader kører (klient driver loopet). Serveren er
hjernen — leveret dér hvor loopet **allerede** kalder den. **Nøgle-indsigt:** "server ejer hjernen" kræver
IKKE "server ejer loopet", fordi model-kaldet allerede er et server-round-trip.

```
  KLIENT (jc_agent_loop, delt af desk + jarvis-code):
    rounds · tools · A1-A7-recovery · budget · self-correction · steering · hooks ·
    checkpoint · sandbox · dispatch · MCP · background-shells · skills-glue · render

  SERVER (hjernen, via loopets eksisterende sømme):
    (1) PER-STEP  → /v1/agent/step: fuld prompt-assembly + per-step-gates + cache-split
    (2) TUR-SLUT  → absorb-endpoint: ~85 trackers + memory-postprocess + cost + episodes
    (3) SESSIONER → server-ejede, delte; compaction server-side (ægte %/pause/fortsæt)
```

Klient-tools klassificeres via `execution_location` (Fase 0, leveret): `client` (kalderens host) ·
`runtime` (Jarvis' container) · `server` (hjernen). Kun forskellen mellem overflader.

## 3. De tre server-stykker

### (1) Per-step fuld hjerne — `/v1/agent/step`
Allerede ctx=full (kalder `build_visible_chat_prompt_assembly`). Tilføj:
- **Cache-sentinel-split (fikser 25s-problemet):** honorér `DYNAMIC_TAIL_SENTINEL` — stabilt hoved som system
  (FØR samtalen), volatil hale FLYTTET til efter samtalen. Så cacher `[stabilt system + samtale]`. Målt:
  76% stabilt hoved, 24% volatil hale. (Se responsibility-surface-map §Lag C.)
- **Per-step-gates:** kør TruthGate v2 + claim_scanner + reasoning_interceptor på step-outputtet før retur —
  serveren ser hvert step (det er et round-trip), så gates håndhæves uden at eje loopet.

### (2) Tur-absorb — nyt endpoint
`POST /v1/agent/turn-absorb` {session_id, run_id, user_message, assistant_response, tools[], tokens/cost}.
Fyrer alt `visible_runs._post_process` gør: `set_last_visible_run_outcome` → `_update_cognitive_systems_async`
(~25) + `_track_runtime_candidates` (~61) + episode-writers (cognitive/experience/theory_of_mind/perceptual)
+ `_run_memory_postprocess` + `record_cost(lane=visible)` + eventbus + gate-verdict-ledger-flush + model-trust.
Klienten kalder det ved tur-slut. Uden det mister en klient-drevet tur hele hjerne-læringen.

### (3) Server-ejede delte sessioner
Klienten persisterer user/assistant/tool-rækker via serveren (`append_chat_message` gennem endpoint) og læser
historik via serveren (`chat_session_messages_since_last_compact`). Compaction bliver server-ejet → Bjørns
"ægte %/pause/bevar/fortsæt" bliver VIRKELIG: serveren har ægte tokenizer + LLM-resumé + compact_markers +
growing-window; en SSE-lifecycle (compaction-started → done) renderes ens af begge klienter. Klientens lokale
JSONL bliver en cache/mirror (eller pensioneres).

## 4. Hårde constraints (fra kortlægningen) — håndtering
- **Ét globalt aktiv-run-slot:** klient-drevne ture registrerer et run-id server-side ved absorb; single-flight
  bevares. (Ikke to konkurrerende loops — ét loop pr. klient, serveren observerer.)
- **Aktiv-chat-gate:** klienten persisterer user-turen server-side (Fase C) → heartbeat undertrykkes korrekt.
- **compact_marker-kontrakt:** serveren ejer al compaction; klienten rører aldrig markers.
- **jarvisx todos/staged_edits/checkpoints:** todos/plans flyttes server-side (streames), checkpoint/sandbox
  forbliver klient-infra (delt kode desk+jc).
- **current_user_id-kontekst:** server-kald bærer user_id → recall/workspace scoper korrekt.

## 5. Faser (hver flag-gated, bagudkompatibel, efterlader systemet kørende)

- **Fase 0 — Tool-lokation (LEVERET, merged).** `execution_location` client|runtime|server.
- **Fase A — agent_step fuld hjerne (server).** A1 cache-sentinel-split + A2 per-step-gates. Flag-gated.
  Størst enkelt-gevinst (fikser cache + fuld tilstedeværelse per step). Rører ikke klienten.
- **Fase B — tur-absorb-endpoint (server).** Fyr ~85 trackers + memory-postprocess for en klient-drevet tur.
  Additivt endpoint. Flag-gated.
- **Fase C — server-ejede delte sessioner + compaction-lifecycle (klient+server).** jarvis-code persisterer/
  læser via server; SSE compaction-lifecycle + ægte token-%. Delte sessioner virker cross-surface.
- **Fase D — desk adopterer jc_agent_loop (desk).** Desk code mode skifter motor fra server-v2 til det delte
  substrat (klient-drevet via agent_step+absorb+sessioner), eksekverer klient-tools på desks host.
- **Fase E — pensionér gammel server-v2-code-mode-sti + jc's egen prompt-bygning (`_full_context`).**

Fase A leveres FØRST (ren server-gevinst, klient urørt). Fase 1's delegering (parkeret) bygges ikke.

## 6. Test-strategi
- Fase A: sentinel-split-assembly (stabilt hoved uændret turn-til-turn, volatil hale efter samtale); per-step-
  gate rewriting; cache-hit-måling før/efter på stor session (mål mod ~7-8s).
- Fase B: syntetisk klient-tur → absorb → verificér trackers/memory/cost/episodes fyrer (spejl visible_runs).
- Fase C: delt session skrevet fra jc synlig+konsistent i desk; compaction-lifecycle renderet; ægte %.
- Fase D: desk kører en fler-tur code-opgave via jc_agent_loop; identisk adfærd som jarvis-code.
- Acceptance: samme prompt i desk vs jarvis-code → byte-identisk hjerne + identisk render.

## 7. Risici / åbne punkter
- **Latency:** Fase A's per-step-assembly betaler stadig assembly-tid; cache-splittet + prewarm skal bringe
  det mod ~7-8s. Måles i Fase A.
- **Desk-motor-skift (Fase D):** stort — desk skal eksekvere klient-tools lokalt (Electron kan det) + rendre
  det delte substrats output. Egen faset plan.
- **Session-id-model:** jc's lokale uuid vs server `chat-<hex>` skal reconciles (Fase C) — ét id-skema.

## 8. Ikke i scope (YAGNI)
Multi-worker skalering (systemet er `--workers 1`); ny council/agent-arkitektur (separat spor); speed ud over
Fase A's cache-angreb + prewarm.
