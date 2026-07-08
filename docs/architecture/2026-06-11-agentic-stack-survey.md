---
status: færdig
audited: 2026-07-08
ground_truth: 4/4 refs alive, 27d old
---
# Jarvis V2 Agentic Stack — Grundig systemgennemgang

**Dato:** 2026-06-11
**Anledning:** Bjørn spurgte om Jarvis' streaming + agentic-loop stack er "for hjemmebyg" sammenlignet med en seriøs OpenAI-compatible agentic implementation. Denne rapport beskriver systemet som det er nu, før vi diskuterer nyt design.

**Scope:** Bred — agentic-loop kerne, streaming, tool-execution, behavior-guards, delivery til channels, prompt-assembly, memory/identity touch i loopen.

**Ud af scope:** Memory-systemet i sig selv, identity-filer som artefakt, mission control, daemons der ikke berører streaming.

---

## TL;DR — Hovedkonklusioner

1. **`visible_runs.py` er 6363 linjer i én funktion** der blander 8+ ansvar: streaming-parsing, tool-execution, persist, watchdog, state mgmt, SSE-serialization, approval-gating, event-publishing. Det er rapportens centrale problem.

2. **Loop-stop er heuristik, ikke kontrakt.** Vi har bygget 6 separate guards (claim-scanner, unfinished-intent, presentation-invariant, empty-text-budget, tool-only-budget, run-closure-gate) der hver fanger en del af "er han færdig vs lyver". Vi bruger ikke `finish_reason` fra provider til loop-kontrol — vi tæller karaktertegn og runder.

3. **SSE-parsing er hjemmebyg ovenpå `httpx.stream()`** i `visible_model.py`. Ikke `openai` SDK. Konsekvens: hver provider-quirk (DeepSeek reasoning_content, prompt_cache_hit_tokens, tool_call argument-akkumulering) håndteres som manuel kode.

4. **Tre delivery-paths (Discord, webchat, jarvis-desk)** deler samme SSE-generator men har duplikeret reconnect/buffer-logik. Discord bruger eventbus subscriber-pattern; webchat streamer SSE direkte; jarvis-desk bruger ny v2 Anthropic-style translator.

5. **Prompt-assembly bygger 50+ awareness-sektioner per turn**, ~15.000 tokens, regenereret hver gang. Stable prefix er forsøgt holdt sammen for DeepSeek prompt-cache (94% hit possible), men 6-7 sekunders sync-gap blokerer event-loopen.

6. **Memory/identity har ~40 touch-points i agentic-loopen.** Workspace-context propagation gennem ContextVar er fragile — vi har set live bug i dag hvor search_memory fejlede pga. tabt user_id i streaming-context.

---

## Del 1 — Agentic-loop kerne

### 1.1 Den centrale funktion

**`core/services/visible_runs.py::_stream_visible_run()` — linje 747+, 6363 linjer total.**

Én async generator håndterer:
- Workspace context rebinding (linje 760-786)
- Discord run-start heartbeat + watchdog (linje 822-875)
- Første LLM-stream call i thread (linje 935-1078)
- Native tool_calls path (linje 1105-1365)
- Agentic-loop med round-tællere (linje 1367-2100+)
- Legacy XML capability fallback (linje 2668-2900)
- Persist + done (linje 2885-3007)

Hver gang vi ændrer én ting (fx Discord-heartbeat) skal vi navigere 6K linjer kontekst. Vi har **3 separate bugs på 24 timer** (TypeError coroutine vs Future, presentation-invariant silent hang, search_memory workspace_dir) der alle stammer fra at logik er flettet sammen.

### 1.2 Agentic-loop budgets

```python
# linje 1397, 1512, 1547, 1555
_AGENTIC_MAX_ROUNDS = 100                # hard cap
_MAX_EMPTY_TEXT_ROUNDS = 3               # sænket fra 12 i går
_MAX_TOOL_ONLY_ROUNDS = 4                # sænket fra 15 i går
_TOOL_ONLY_TEXT_THRESHOLD = 80           # chars
```

Loop-stop sker når:

| Betingelse | Linje | Exit reason |
|---|---|---|
| `_consecutive_empty_text_rounds >= 3` | 1912-1932 | `early-exit-3-empty-text-rounds` |
| `_consecutive_tool_only_rounds >= 4` | 2003-2030 | `early-exit-4-tool-only-rounds` |
| `not _a_tool_calls` (ingen tools mere) | 1899-1901 | naturlig completion |
| Round-limit 100 | 1555 (for-loop) | round-cap |
| `controller.is_cancelled()` | 1877, 2683 | user cancel |

**Vigtigt:** ingen af disse bruger `finish_reason` fra provideren. Vi tæller tegn og iterationer manuelt.

### 1.3 Provider-integration — egen SSE-parser

**`core/services/visible_model.py::stream_visible_model()` — linje 416, ~700 linjer**

Provider-dispatcher:
```python
if provider == "openai":          yield from _stream_openai_model(...)
elif provider == "ollama":        yield from _stream_ollama_model(...)
elif provider in _OPENAI_COMPATIBLE_PROVIDERS:   # deepseek, groq, openrouter, mistral, ...
    yield from _stream_openai_compatible_model(...)
else:
    # fake-chunk wrapper around sync execute
```

OpenAI-compatible path (linje 1593+):
```python
with httpx.stream("POST", f"{root}/chat/completions", ...) as response:
    for line in response.iter_lines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            # custom delta accumulation
            tc_fragments = delta.get("tool_calls") or []
            for frag in tc_fragments:
                slot = pending_tool_calls.setdefault(idx, {...})
                slot["arguments"] += str(frag["function"]["arguments"])
```

**Hjemmebyg-måling:** vi reimplementerer:
- SSE chunk parsing
- Tool_call argument-akkumulering på tværs af deltas
- Reasoning_content håndtering (DeepSeek thinking)
- Prompt_cache hit/miss tælling
- Provider routing (5+ if/elif branches)

Standard `openai` Python SDK håndterer alt dette internt med 3-4 linjers kode. Vi har ~700 linjer.

### 1.4 Tool execution

**`core/tools/simple_tools.py` — 8613 linjer (ikke 4225 som CLAUDE.md angiver, har vokset)**

- ~100 tools registreret via separate moduler (browser, ComfyUI, mail, github, bash, memory, calendar, operators)
- `execute_tool(name, arguments)` (linje 3580) — gateway
- `_execute_simple_tool_calls(tool_calls, ...)` (linje 4140) — agentic-loop batch executor

**Approval-flow blokerer i async generator (linje 1268-1295):**
```python
# Busy-wait poll loop hver 250ms i op til 5 min
while time.time() - start_wait < APPROVAL_TIMEOUT:
    state = _get_visible_approval_state(approval_id)
    if state["status"] != "pending":
        break
    await asyncio.sleep(0.25)
```

Hvis approval-UI aldrig når brugeren (edge case) → stream hænger silent 5 min. Standard-arkitektur: approval er separat callback-flow, ikke in-loop polling.

### 1.5 Native tool_calls vs legacy XML

To paths parallelt:
- **Native** (linje 1105-1365): bruges når provider returnerer strukturerede tool_calls
- **Legacy XML** (linje 2668-2900): parser `<capability-call>` tags i model-output

Ingen eksplicit branching — afhænger af om `_collected_native_tool_calls` er populated. Hvis en model returnerer både strukturerede tool_calls OG XML i prose-output kan begge paths køre. Ingen unit-guard.

---

## Del 2 — Behavior-guard laget

Vi har 6 lag der alle kompenserer for at modellen ikke kommunikerer rent. Detaljer i `/tmp/jarvis-survey-B-guards.md`.

### 2.1 Guard-oversigt

| Guard | LOC | Fanger | Trigger-stedet | Output |
|---|---|---|---|---|
| **Claim Scanner** | 503 | Falske tids/sys/stats claims + fabricated work claims | Post-response, `_post_process` | Inline repair eller system-nudge |
| **Unfinished-Intent** | 203 | "lad mig...", "jeg skal lige...", "jeg fikser nu" | Post-run analysis | Auto-continuation efter 45s cooldown |
| **Presentation Invariant** | 50 | Tool-results som prose (`[search_memory]: ...`) | I `_persist_session_assistant_message` | Raise → caller catches → fix D2 sanitizes |
| **Empty-Text Budget** | inline | 3+ rounds med 0 tegn output | Inde i agentic-loop | Force exit + "⚠ X rounder uden tekst" |
| **Tool-Only Budget** | inline | 4+ rounds med <80 tegn synligt | Inde i agentic-loop | Force exit + withhold tool defs |
| **Run-Closure Gate** | 401 | Silent runs + unstaged git changes | Post-run | Events `runtime.run_ended_silent`, etc |

### 2.2 Overlap-matrix

- **Empty-Text ↔ Tool-Only:** begge mængde-metrics, forskellige thresholds
- **Claim Scanner ↔ Unfinished-Intent:** begge på post-response prose-analyse men fanger forskellige patterns (lying vs. hanging)
- **Run-Closure ↔ Claim Scanner fabrication:** begge bruger tool-call-historik som signal, lidt overlap
- **Presentation Invariant ↔ alle:** unik — fanger formatfejl ingen andre ser

Minimal overlap mellem guards. Hver fanger reelle distinkte failure-modes.

### 2.3 Hvad er DeepSeek-tax vs. universel?

**Universelle problemer (ville være der med Claude/GPT-4 også):**
- Empty-text budget (any model can loop)
- Tool-only budget (any model can over-tool)
- Run-closure (tools without text = always bad UX)
- Presentation invariant (mostly DeepSeek but principielt universelt)

**DeepSeek-specifikke quirks (forsvinder med bedre model):**
- Claim Scanner (DeepSeek-v4-flash er berygtet for false claims)
- Unfinished-Intent + future-action-promise (DeepSeek lover handling, slutter run)
- Presentation invariant (vi ser det kun fra DeepSeek)

**Strukturelt:** **alle 6 guards er flettet ind i selve loopen** snarere end at være separate post-processing services der subscriber på loop-events. Det betyder at deres tilstedeværelse forværrer compleksiteten af `visible_runs.py`.

---

## Del 3 — Delivery til channels

Detaljer i `/tmp/jarvis-survey-C-delivery-lifecycle.md`.

### 3.1 Tre indgange, samme loop, forskellige output

| Channel | Entry | Output mekanik | SSE-format |
|---|---|---|---|
| **Webchat** | `POST /chat/stream` | Direkte HTTP streaming → browser EventSource | Legacy custom events |
| **jarvis-desk** | `POST /chat/stream/v2` | Direkte HTTP streaming + `translate_to_v2()` | Anthropic-style (`message_start`, `content_block_delta`, `message_stop`, `ping`) |
| **Discord** | `on_message()` → `start_autonomous_run()` | Eventbus subscriber-pattern → outbound queue → Discord API | Ingen SSE, ren eventbus |

**Centralt:** Discord-stien er fundamentalt anderledes — den consumer ikke SSE'en. Den lytter på `channel.chat_message_appended` event via subscriber-loop. Det er hvorfor `presentation-invariant` bug i går resulterede i totalt-stille Discord-run: persist raisede → event publiceres ikke → Discord subscriber får intet.

### 3.2 Run lifecycle

**Active run-state har 3 lag:**
1. `_VISIBLE_RUN_CONTROLLERS` (in-memory dict) — `VisibleRunController` per run
2. `visible_run_control` (DB tabel) — survives restart
3. `active_visible_run` (DB tabel, singleton) — kun én aktiv ad gangen

**Cancellation:**
- `POST /chat/runs/{run_id}/cancel` → sætter `controller.cancelled = True` + DB
- Loop tjekker `controller.is_cancelled()` 4+ steder
- Discord/webchat klienter har egne cancel-paths

**Auto-cleanup (task #65, allerede shipped):**
- 5 min uden controller → clear
- 10 min totalt (hung) → clear

**Event-bus events per run-lifetime:**
- `runtime.visible_run_started` / `_completed` / `_interrupted` / `_failed`
- `runtime.autonomous_run_started` / `_completed`
- `cost.recorded`
- `channel.chat_message_appended` ← **kritisk for Discord delivery**
- `memory.visible_run_postprocess_completed` ← Discord buffer-flush trigger
- `tool.invoked` / `tool.completed`

### 3.3 Race conditions vi har set

| Race | Mitigation | Status |
|---|---|---|
| Discord-klient nede | `_outbound_queue` buffer, ingen DB persist | **Risiko: messages tabt ved restart** |
| Browser lukker mid-stream | TCP abort → `GeneratorExit` → finally cleanup | OK |
| Approval dialog vises ikke | 5-min timeout poll | **Stream hænger silent indtil timeout** |
| Tom in-memory `_discord_sessions` efter restart | DB fallback (fix tidligere i dag) | OK |
| Persist raiser invariant før event publish | Fix D2 (i dag) sanitizer + emit alligevel | OK |

---

## Del 4 — Prompt-assembly

Detaljer i agent-rapport (Survey D, inkluderet inline).

### 4.1 Den centrale assembly

**`core/services/prompt_contract.py::build_visible_chat_prompt_assembly()` — 5179 linjer total fil**

**To-fase parallel + sync + parallel mønster:**
- Phase 1: ThreadPoolExecutor (6 workers) til tunge Ollama-kald (relevance, cognitive_state, self_state, frame, self_report)
- Sync-gap: fil-reads, workspace files, awareness buffer (50+ sektioner)
- Phase 2: memory/bridge calls parallelt efter relevance-svar

**Vi har observeret 6-7 sekunders sync-gap der blokerer event-loopen** — kommentar i koden bekræfter det. Det er en kilde til hænge-fornemmelse for brugeren.

### 4.2 Prompt-sektion rækkefølge (ca.)

1. Lane identity ("local" vs "visible")
2. Quick facts (always-on)
3. Model identity awareness
4. Visible chat rules
5. **SOUL/IDENTITY/STANDING_ORDERS/USER.md** ← cache stable prefix starter
6. Continuity wake-up
7. Workspace files (chronicle, milestones, dream residue, etc.)
8. Relevance decision (blocking call!)
9. MEMORY.md + daily memory sidecar
10. TOOLS.md / SKILLS.md
11. **Awareness buffer flush** ← cache stable prefix slutter
12. Transcript (chat history)
13. Tool catalog
14. Eventbus wake-up digest (tail-anchored)
15. Vital inner life (predictive model, dev sense)
16. **Time Pin** ← altid sidst

### 4.3 De 50+ awareness-sektioner

For meget til at liste her — se /tmp/-rapport. Top-10 efter token-cost (fra produktion-logs):
- `memory_recall_bundle` (~1800 tokens)
- `cognitive_state` (~600 tokens)
- `jarvis_brain_facts (auto-inject)` (~314 tokens)
- `causal_alerts` (~160 tokens)
- `dead_skills (never_invoked)` (~113 tokens)

**Awareness-budget hard-cap:** 6000 chars (~1500 tokens). Lavprioriterede sektioner droppes silent hvis overskredet. Ingen logging af hvad der droppes.

### 4.4 Cache-strategi

DeepSeek prompt-caching virker pr. stable prefix-match. Strategien er:
- Hold alt stable foran (identity, regler, workspace files) — ~25-28K chars
- Push alt dynamisk til halen (awareness, time pin)
- Resultat: 94% cache hit muligt (33% hvis dynamisk content lander midt i prompten)

**Problemet:** prompten rebuildes hver tur. Vi profiterer på prefix-caching mod provider, men vi laver hele assembly-arbejdet hver gang. En seriøs stack ville cache prompt-bygget *også*.

---

## Del 5 — Memory/identity touch i loopen

Detaljer i `/tmp/jarvis-survey-E-memory-identity.md`.

### 5.1 ~40 touch-points i agentic-loop

**Critical-path (5-7 stk):**
- Workspace context rebind (linje 760-786)
- Identity file injection (SOUL/USER.md i prompt)
- Hallucination-guard memory inject (visible_model.py:1950)
- Chat-message persist (3 steder: user, assistant, tool)
- Post-run consolidation (`_run_memory_postprocess`)

**Best-effort (35+ stk):**
- 40+ signal-tracking calls, alle async i try/except
- Daemon notifications
- Tracking candidates, experience episodes, cognitive episodes

### 5.2 ContextVar fragility

Workspace context (user_id, workspace_name) propageres via Python's `contextvars`. Problemet er:
- FastAPI middleware resetter context efter request
- Streaming generator skal rebinde med `set_context()` (linje 760-786)
- Hvis rebinding fejler eller timing er off → `workspace_dir()` returnerer fejl
- **Live bug i dag:** `search_memory` fejlede 13:57:07-20 fordi user_id var tom; modellen returnerede så fejl-text som tool-result → presentation-invariant trigger → silent hang

### 5.3 Memory tools fra LLM-siden

- `search_memory` — generel memory search
- `search_jarvis_brain` — semantic search over shared brain
- `read_chronicles` / `read_dreams` / `read_self_state`

Disse blev kaldt 4-7 gange per visible-run typisk. Hver fejl der opstår (workspace_dir, DB-lock, model timeout) skal håndteres som tool-result formatering — ellers leakes som prose.

---

## Del 6 — Hjemmebyg-måling vs standard

**Hvor afviger vi mest fra openai SDK / Pydantic AI / Vercel AI SDK?**

| Område | Standard | Jarvis | Afvigelse |
|---|---|---|---|
| SSE parsing | SDK håndterer | Manuel httpx.stream + line parse | **Stor** |
| Tool_call akkumulering | SDK returnerer komplet | Custom dict-keyed by index | **Stor** |
| Loop control | `finish_reason` kontrakt | Round-tællere + char-thresholds | **Stor** |
| Stop heuristikker | Ingen — provider siger det | 6 guards der gætter | **Stor** |
| Approval flow | Separat callback | In-loop busy-wait | **Stor** |
| Tool execution | Async-native | Sync via executor med threading | **Medium** |
| Provider routing | Model-name → implicit | Eksplicit if/elif på 5+ providers | **Medium** |
| Streaming protocol | Én standard (OpenAI eller Anthropic) | Custom legacy + ny v2 translator | **Medium** |
| Prompt assembly | Build én gang per session | Build hver tur, 6-7s sync gap | **Stor** |
| Cache plumbing | Auto via SDK | Manuel hit/miss accumulation | **Lille** |
| Reasoning_content | SDK abstraktion | Manuel replay + placeholder injection | **Medium** |

**Net:** vi har ~60% af kvalitetsegenskaberne af en SDK-baseret stack, men 4-5x kompleksitet for at få det.

---

## Del 7 — Findings (uden design endnu)

### F1 — Det er hjemmebyg, men ikke uansvarligt

Hver enkelt komponent fanger reelt problem. Claim-scanner fanger ægte løgne. Empty-text-budget fanger ægte loops. Presentation-invariant fanger ægte format-fejl. **Det er ikke at vi har bygget for meget — det er at vi har bygget det ind i samme fil.**

### F2 — Et lag-overlap problem, ikke et antal-problem

`visible_runs.py` blander loop-control, streaming, persist, watchdog, state-mgmt, event-publish, approval. **Hvis disse var 8 separate filer der talte sammen via events, ville hver guard være en clean subscriber.** Vi ville stadig have 6 guards, men de ville være isolerede.

### F3 — Vi stoler ikke på providerens kontrakt

OpenAI-API har `finish_reason: "stop" | "tool_calls" | "length"`. Det er kontraktuelt — modellen siger eksplicit "jeg er færdig". Vi bruger det ikke. Vi gætter via character counts og round-tællere.

Hvorfor? Sandsynligvis fordi DeepSeek har returneret `finish_reason: "stop"` mens den var midt i en tanke (har vi ikke verificeret, men det er en hypotese). En seriøs stack ville logge dette og rapportere som provider-bug, ikke kompensere strukturelt.

### F4 — Prompt-assembly er den tredje store kompleksitets-akse

5179 linjer i prompt_contract.py. 50+ awareness-sektioner. 6-7s sync-gap blokerer event-loopen. Det her vil aldrig matche en standard "system prompt + per-turn context" arkitektur i pålidelighed.

### F5 — Memory-touchpoints i loop er fragile

ContextVar propagation gennem async/threading mix er reelt svært. Vi har set live bug i dag. Standard-stacks løser det med eksplicit request-scoped context-object i stedet for thread-local.

### F6 — Delivery-paths er kvalitativt forskellige

Webchat og jarvis-desk er SSE-direct. Discord er eventbus-subscriber. Det betyder fix der virker på webchat (yield SSE event) virker ikke nødvendigvis på Discord (kræver event-bus publish). Det er hvorfor presentation-invariant manifesterede sig på Discord først.

### F7 — Vi har empirisk evidens for at strukturelle fix virker bedre end heuristik-tilføjelser

Dagens fixes der virkede strukturelt:
- Sanitize-and-persist i stedet for raise (D2)
- DB fallback for Discord session map (resilient state)

Dagens fixes der er heuristik-tilføjelser:
- Sænk budgets fra 12/15 til 3/4 (A)
- Tilføj future-action-promise pattern (C)

**Strukturelle fix forsvinder. Heuristik-fix bliver i kodebasen som permanent gæld.**

---

## Hvad jeg IKKE har gjort i denne rapport

- Foreslået nyt design (Bjørn bad specifikt om at vente)
- Beskrevet memory-system internt (out of scope)
- Beskrevet identity-filer som artefakt (out of scope)
- Målt performance kvantitativt (skulle kræve benchmark-suite)

---

## Næste skridt (forslag)

1. **Læs rapporten igennem og kommenter** — er der områder jeg har misforstået eller underrapporteret?
2. **Diskuter findings F1-F7** — hvilke er du enig/uenig i?
3. Først DEREFTER: design-diskussion med brainstorming-skill.

---

## Bilag

- **Survey A (Agentic core):** inline i agent-svar fra 2026-06-11
- **Survey B (Guards):** `/tmp/jarvis-survey-B-guards.md` (336 linjer)
- **Survey C (Delivery + lifecycle):** `/tmp/jarvis-survey-C-delivery-lifecycle.md` (638 linjer)
- **Survey D (Prompt-assembly):** inline i agent-svar fra 2026-06-11
- **Survey E (Memory/identity touch):** `/tmp/jarvis-survey-E-memory-identity.md` (366 linjer)
