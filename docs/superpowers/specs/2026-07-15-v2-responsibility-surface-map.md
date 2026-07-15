# v2's ansvarsflade — samlet kort (grundlag for jarvis-code ↔ v2 forening)

**Dato:** 2026-07-15
**Formål:** Kortlægge ALT v2-endpointet (`/chat/stream/v2` → `visible_runs`) ejer per tur og per session,
så vi kan designe "samme Jarvis overalt: delt session + server-hjerne + klient-hænder" mod den
rigtige grænse — ikke en halv forståelse. Bygget fra 6 parallelle read-only kortlægninger.

Kontekst: To chat-endpoints i dag.
- **v2** (`chat_stream_v2.py` → `visible_runs._stream_visible_run`): desk (chat+code), web, mobil. Ejer sessioner + hukommelse + prompt + kognition + gates + cost.
- **agent_step** (`agent_loop.py`): jarvis-code CLI. Kører loop + tools KLIENT-side. Server-side **tilstandsløs** — får `session_id` men skriver aldrig til `chat_messages`; bygger sin EGEN (lettere, parallelle) prompt via `_full_context`.

---

## 1. Hjernen — hvad v2 ejer (fem lag)

### Lag A — Sessioner & lagring (`chat_sessions.py`, `db_schema.py`)
- Session = `chat-<hex>` i `chat_sessions` (kolonner: id, session_id, title, created/updated_at, workspace_kind, workspace_root, team_id, locked/locked_reason/locked_at).
- Beskeder i `chat_messages` (roller: user/assistant/tool/**compact_marker**; ingen `system` gemmes). Kolonner inkl. `content_json` (kanonisk block-array), `reasoning_content`, `user_id`, `git_sha`.
- **Adgang = ren session_id.** Ingen per-forbindelse-ejerskab. Bruger-scoping er BLØD (kun ved list/search). Desk/web/mobil deler allerede sessioner.
- **Cross-client dedup findes allerede** (900s-vindue, `_DEDUP_WINDOW_SECONDS`) — indført fordi overflader allerede spejler ind (249 prod-dubletter).
- Mobil↔desk-bro = emergent fra delt session_id + follow-buffere (`run_follow.py`, `run_event_log.py`), IKKE en separat flag.
- **Læsestier:** `chat_session_messages_since_last_compact` (growing-window, cache-venlig, foretrukket), `recent_chat_session_messages`, `..._by_user_turns`. Alle ekskluderer compact_marker.

### Lag B — Compaction & kompression (`session_compact.py`, `auto_compact.py`, `transcript_sections.py`, `compact_ground_truth.py`)
- **To uafhængige triggere per tur:** synkron pre-LLM ved ~240k×0.8 (eller window×0.70); baggrundstråd ved ~130k (eller fraction×window). Plus `/compact`.
- Skriver `compact_marker`-rækker + LLM-resumé (cheap-lane, Groq-sidst). `keep_recent=20` seneste bevares verbatim.
- **Anti-hallucinations-lag:** ground-truth-grounding, post-compact-validering (`compaction_validation_failures`), self-healing af stale markers.
- **Yderligere kompression:** tool-resultat hot-tail/cold-storage (fuld body på disk, `[tool]: summary` i historik, cap 1500), tool-result-aging, per-rolle 8000-tegns-cap, identity-sketch, alternation-trimning.
- Token-tælling = `chars/3.5` heuristik (ikke rigtig tokenizer).

### Lag C — Prompt-assembly (`prompt_contract.py::build_visible_chat_prompt_assembly`)
- ~38 nummererede sektioner + en **~30-sektions awareness-blok** (6000-tegns budget) + **7 parallelle LLM-futures** (relevance, cognitive_state, self_state, frame, self_report, memory_selection, recall_bundle) under ét **12s-assembly-budget** med per-future deadlines.
- **Cache-grænse ALLEREDE bygget:** sentinel `⟦◆DYNAMIC-TAIL-DO-NOT-CACHE◆⟧` deler stabil prefix / volatil hale. `visible_model` finder sentinel'en og flytter halen over på sidste bruger-besked → `[system+transcript]` byte-stabilt/cachet.
- **jarvis-codes `_full_context` læser KUN `.text` og ignorerer sentinel'en** → laver aldrig hale-splittet → cachen knækker ved token 0. Målt: 76% stabilt hoved, 24% volatil hale (cognitive_state/emotion/self-narrativ) der skifter hver tur.
- Kræver `current_user_id()`-kontekst (ContextVar); uden den fejler workspace-recall stille → [].
- Output `PromptAssembly`: `.text` (med sentinel bagt ind), `transcript_messages`, `attention_trace`, `derived_inputs`. **Stabil/volatil-split er IKKE eksponeret programmatisk** — kun som sentinel-streng i `.text`.

### Lag D — Hukommelse (`memory_recall_engine.py`, `visible_runs_memory.py`, `memory_write_queue.py`, cluster_memory)
- **Recall (læs) i hot-path:** multi-signal (BM25+entity+embedding+recency+importance+recall_freq). 4s-deadline (enrichment, aldrig load-bearing). Bruger **lokal Ollama nomic-embed** (127.0.0.1:11434) — SAMME Ollama der streamer svaret → kilden til cutoff-frys.
- **Skrivning (næsten alt async):** `_post_process`-baggrundstråd efter turen → distillation (private_brain), end-of-run-konsolidering (MEMORY.md/USER.md-kandidater + auto-apply), session-summary, experiential memory, næste-turs background-recall. Plus 120s write-queue-daemon + cluster_memory-familie (decay/pruning/maintenance/safeguard/consolidation).
- Alle skrivninger server-lokale (SQLite + bruger-scopet `workspace_dir` + lokal embedder). **Ingen sikker at køre klient-side.**

### Lag E — Turn-eksekvering & side-effekter (`visible_runs.py`)
- Multi-runde agentisk loop (default 100 runder), retry/failover, loop-control-gate, force-summary, approval-gate (blokerende poll), post-tool prompt-re-assembly.
- **Side-effect-regnskab: 55 punkter per tur.** Tre klasser:
  - **(a) Læses under assembly** — klient kan reproducere/springe over.
  - **(b) Synkrone finalize-skrivninger** — cost-ledger (`record_cost lane=visible`), 4 episode-writers (cognitive/experience/theory_of_mind/perceptual), TruthGate v2 (kan omskrive output), claim_scanner, assistant-persist + `channel.chat_message_appended`, in_flight_runs.
  - **(c) Async post-`done`** — `_update_cognitive_systems_async` (~25 systemer: personality/taste/relationship/rhythm/surprise/value/flow/…) + `_track_runtime_candidates` (~61 trackers: self_model, self_review, world_model, goal, reflection, internal_opposition, autonomy_pressure, memory/user-md-proposals…) + memory-postprocess + shadow-gates + verdict-ledger-flush + model-trust.

---

## 2. Tværgående systemer en tur fodrer

- **Eventbus** (async SQLite-write bus): `runtime.visible_run_started/completed`, `runtime.agentic_round_start`, `cost.recorded`, `tool.invoked/completed`, `channel.chat_message_appended`, `memory.*`, `prompt.assembly_size`. Central læser via **polling af `events`-tabellen** + direkte `central().observe/decide` — ikke in-process subscription.
- **Gates (~18 moduler + ~8 guards):**
  - INLINE enforcing (former model-tokens/tools): reasoning_interceptor (RED tømmer tool-liste), loop_gate (hard-stop), TruthGate v2 (omskriver output pre-done), claim_scanner, hollow_promise_guard, affect-modulation-budget.
  - Async shadow/observability: gate_shadow (6 gates, 5 enforced), truth-cluster, verdict-ledger. Turen **flusher selv** verdict-ledger (`gate_verdict_ledger.flush()` i API-processen).
- **Cost/økonomi:** `costs`-tabel (lane, provider, model, tokens, cache_hit/miss). Cache-telemetri (`record_visible_cache`) observerer Central direkte. Circuit-breaker + model-trust + credit-assignment.
- **Central/heartbeat/kontinuitet:** **Aktiv-chat-gate læser `chat_messages` user-rækken** → undertrykker proaktive heartbeat-pings. in_flight_runs-interruption-bogholderi. current_pull/continuity læses (skrives af daemons).

---

## 3. Hårde constraints ENHVER plan skal håndtere

1. **Ét globalt "aktiv-run"-slot server-wide** (`visible_runs.active_run`), ikke per session. Klient-loop + desk-v2-run slås om samme slot. Single-flight collapser samme-session-sends.
2. **Aktiv-chat-gate afhænger af user-rækken** i `chat_messages`. Persisterer klienten ikke user-turen → heartbeat/inderliv fyrer proaktive pings oven på en live samtale (konkret regression).
3. **compact_marker-kontrakten:** klient må ALDRIG skrive/slette markers; skal læse growing-window + prepende marker-resumé, ellers korrumperes read-boundary + cache.
4. **jarvisx per-session-state** desk code mode forventer autoritativ: `agent_todos`, `staged_edits`, `in_flight_runs`-checkpoints, `session_inbox`-nudges.
5. **Single-process** (`--workers 1`): live-buffere in-memory; deling via DB + runtime_state KV.
6. **`current_user_id()`-kontekst** kræves for korrekt workspace/hukommelse-scoping; mangler den → stille tom recall.

---

## 4. Grænsen: hænder vs hjerne

- **Hænder (jarvis-code KAN eje klient-side):** agent-loopet, generiske fil/bash/edit-tools, retry/failover, force-summary, tool-progress-UI.
- **Hjerne (SKAL blive server-side ELLER eksponeres som endpoints):** prompt-assembly (Lag C), al hukommelse (Lag D), de ~85 kognitive/self-trackers + 4 episode-writers, cost-ledger + cache-telemetri, model-routing + rolle-clamp, override/identitet, operator/bridge-tools, approval, alle gates, v2-SSE-terminal-kontrakt, Central-legibilitet.

**Konsekvens:** "klient-side hænder" kan IKKE betyde "klienten kalder bare DeepSeek selv" — så mister Jarvis hukommelse, læring, kognition og gates hver tur. Foreningen er **delt session + server-hjerne + klient-hænder**.

---

## 5. Tre arkitektur-optioner (beslutning udestår)

### Option 1 — Server-eksekutor, klient-tools (server driver loopet; klienten er hænderne)
Serveren kører `visible_runs`-loopet + hjerne + gates + alle side-effekter (INTET tabt). Værktøjer der skal køre på brugerens maskine emitteres som `tool_use` over v2-SSE; klienten eksekverer lokalt, poster `tool_result`, serveren fortsætter loopet (Anthropics egen klient-tool-model). Desk code mode + jarvis-code renderer/eksekverer bare tools. Én hjerne, ét loop, delte sessioner automatisk.
- **Pro:** taber intet; opløser "to prompts" (serveren er eneste eksekutor); klient-tools lokalt.
- **Con:** stadig server-assembly-latency (10-25s) på model-kaldet. Speed er en SEPARAT server-optimering (sentinel-split findes allerede; async-cachet kontekst; prewarm).

### Option 2 — Klient-eksekutor loop + server-absorb (klienten driver; serveren brackets)
Klienten kører loopet + tools + konsumerer server-assembleret prompt. Efter loopet POSTer den `(session_id, run_id, user_message, assistant_response, tools, tokens/cost/cache)` til et "absorb"-endpoint der fyrer hele side-effekt-maskineriet.
- **Pro:** beholder klient-hastigheden (6-7s).
- **Con:** INLINE enforcing gates (reasoning_interceptor, TruthGate v2, loop_gate) former tokens UNDER loopet — svære at replikere trofast klient-side → enten ugoverneret output eller mid-loop server-round-trips (dræber speed). ~85 trackers + gates at bracke. Skrøbeligt.

### Option 3 — Hybrid tiers
Chat/lette ture server-side (Option 1); tunge code-ture klient-loop + absorb (Option 2). Mest kompleksitet.

---

## 6. Anbefaling

**Option 1 som arkitektur.** Den matcher Bjørns vision præcist ("samme Jarvis, tool-boksen er den eneste klient-side-forskel"), taber intet af hjernen by construction, og opløser "to prompts"-problemet fordi jarvis-code holder op med at bygge sin egen prompt. Speed bliver en ren server-assembly-optimering vi angriber bagefter (og som vi allerede kender vejen på: sentinel-split + async-cachet kontekst + prewarm). Option 2's "tab intet"-version kræver at replikere/bracke en enorm flade — dyrt og skrøbeligt.

Kernebeslutningen der låser resten: **hvor bor turn-eksekutoren?**

---

## Kilder
Bygget fra 6 read-only kortlægninger (session-livscyklus, compaction, prompt-assembly, hukommelse, turn-loop, tværgående systemer), 2026-07-15. Alle fil:linje-referencer i agent-transkripterne.
