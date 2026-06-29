# Production-Grade Streaming Spec

**Status:** Draft 1 — 2026-06-29. Author: Claude (research-grounded). Owner: Bjørn.
**Mål:** Jarvis' streaming skal være lige så robust som OpenAI SDK / Codex på transport-laget,
ALDRIG fejle lydløst, og være fuldt integreret i Den Intelligente Central.

Bygget på fire kode-funderede research-spor (29. jun):
- **A** — OpenAI Python SDK (`openai==1.109.1`) kildekode: transport-robusthedsmodel.
- **B** — Codex CLI (`codex-rs`, stripped binær + GitHub-kilde): streaming-config + failure-taksonomi.
- **C** — Audit af vores egen pipeline: lydløse huller + central-integrations-huller.
- **D** — Codex' agentic-loop (`codex-rs/core/src/session/turn.rs`): mid-turn-retry.

---

## 0. TL;DR — rod-årsags-hypotese (kode-funderet)

Bjørns symptom: "hver gang han kalder et tool, tænker lidt, BANG cutoff — random, på tværs af
modeller/providers, lokalt." 8 headless-reproduktioner kørte rent → cuttet er IKKE server-happy-path.

**Stærkeste strukturelle kandidat (research D + C):**
1. En followup-runde efter et tool-kald laver et nyt model-kald (sampling).
2. Rammer den et **forbigående** blip (stream-drop, 502/503, idle-timeout) →
3. … **dræber vores loop HELE turen** (`visible_runs.py` sætter `_a_failure` → `break`), mens
   Codex retry'er den ene runde og fortsætter (`turn.rs:1103` inner-loop).
4. Værre: vores **default deepseek/glm/copilot-followup-adapter har INTET retry**
   (`visible_followup.py:828`) — kun ollama-adapteren retry'er 3×. Så på den mest brugte bane
   bliver et forbigående blip ikke engang fanget på adapter-niveau.

→ Forbigående + intermittent + provider-agnostisk + efter tool-kald = **præcis** symptomet.
**Den højest-værdi-fix er rund-niveau-retry der bevarer turen (Fase 1).**

Sekundær, separat klasse (allerede delvist adresseret): "completed uden output" tavs cut →
lukket af #1 livscyklus-invariant (commit 5a99f64c) + #2 observabilitet (d7c2dce8).

---

## 1. Reference-model: hvad "produktions-grade" betyder

### 1A. OpenAI SDK — transport-garantier (de vi mangler)
SDK'et løser **transport-laget** stramt, men gør BEVIDST intet ved app-laget. De 22 transport-punkter
vi skal matche (uddrag — fuld 32-punkts-liste i research A):
- Retry: eksponentiel backoff `min(0.5·2ⁿ, 8.0)` + **jitter**, kun på `408/409/429/≥500` + transport-fejl,
  aldrig på `400/401/403/404/422`; honorér `retry-after(-ms)` + `x-should-retry`; idempotency-key genbrugt.
- Granulær `httpx.Timeout(connect, read, write, pool)` — ikke en watchdog-tråd der lukker en delt socket.
- Typed fejl-hierarki: `APIStatusError(status, request_id)`, `APIConnectionError`, `APITimeoutError`,
  `RateLimitError`, … (ikke `RuntimeError` + substring-matching).
- SSE-decoder der buffer'er til komplet event-blok før parse (ingen split-multibyte, multi-line data).
- Garanteret cleanup via `try/finally` (SDK lækker faktisk ved early-break uden `with` — **vi skal være bedre**).

**Hvad SDK'et IKKE gør (app-lag — det er DER vores UX-cuts bor):**
mid-stream reconnect · partial-completion-håndtering · **server-side run-buffering** · provider-failover ·
inter-token stall-watchdog. **Vores detached-run/relay løser allerede den sværeste (run-buffering) —
bedre end SDK'et.** → Derfor: lån transport-garantierne, behold vores overlegne app-lag. **Ikke** adoptér SDK'et.

### 1B. Codex — agentic-loop-garantier (de vi skal matche)
- **To-niveau-loop:** ydre = turen (`run_turn`), indre = retry af ÉN sampling-request (`run_sampling_request`).
- **Mid-turn-retry bevarer turen:** stream-drop i runde K → retry runde K, tidligere tool-resultater bevaret
  (i history), turen fortsætter. `stream_max_retries` (per-provider) vs `request_max_retries` (transport) = to budgetter.
- **`is_retryable()` taksonomi** = ÉN sandhedskilde: retryable {Stream, Timeout, 5xx, ConnectionFailed, …};
  fatal {TurnAborted, ContextWindowExceeded, InvalidRequest, UsageLimit, …}.
- **"Tom stream = fejl, ikke completed":** intet `response.completed` før close → `Stream("closed before completed")`
  → retryable. Der findes INGEN "completed-med-tomt"-sti. (Validerer vores #1-invariant — men Codex går videre: retry.)
- **`stream_idle_timeout_ms` per provider** — inter-token-watchdog (vi har faktisk dette + mere).
- **Synlig "Reconnecting n/m"-event** under retry, så skærmen aldrig ser frosset ud.

---

## 2. Hvor vi står (audit C)

### På/over Codex-paritet (rør ikke):
- Idle-timeout (first-byte 90s + inter-byte watchdog + ydre round-watchdog total+silence).
- Keepalives: 4 lag (first-pass 6s, followup 5s, tool-exec 15s, v2-ping 5s).
- Event-taksonomi (delta/reasoning/steer/heartbeat/round-start/central-error-envelope) — rigere end Codex.
- Concurrency/cancel: ét aktivt run/session, zombie-slot-kur, steer-drain mellem runder, RAII-checkpoint.
- **#1 livscyklus-invariant** (5a99f64c): ingen "completed uden output" lydløst.
- **#2 empty-completion-observabilitet** (d7c2dce8): sti-tag + recurrence, ingen dedup-skjul.

### Lydløse huller (rangeret efter hvor ofte de rammer et interaktivt tool-run):
| # | file:line | Hvad sluges | Bruger ser | Central-nerve? |
|---|-----------|-------------|------------|----------------|
| H1 | `chat_stream_v2.py:279` | `_subscribe` opgiver efter ~24s stilhed: bart `break`, intet `message_stop`, ingen fejl-frame | **Hæng → tavs stop** | **INGEN** (`subscriber_timeout`-nerve er DØD kode) |
| H2 | `visible_followup.py:828` | Default deepseek/glm/copilot-followup: **intet retry** (ét `urlopen`) | Forbigående blip dræber fler-runde-run | Delvist (`note_round_failed` kun ved endelig fejl) |
| H3 | `visible_model.py:1621` | Ollama inter-byte-frys ubundet (watchdog disarmer efter byte 1) | Hæng ~180s på default-banen | Kun hvis den til sidst kaster |
| H4 | `visible_model.py:1387,1124` | openai-responses/codex provider-fejl: `except: raise` UDEN observe | Fejl surfacer, men usynlig i Central | **INGEN** for de baner |
| H5 | `visible_runs.py:3156,3720` | `_persist_session_assistant_message` i `except: pass` | Svar vist live, **VÆK ved reload** | **INGEN** |
| H6 | `run_event_log.py:49` / `detached_run.py:72` | Frame-drop ved 4000-cap / append-exception | Trunkeret run for re-subscriber | **INGEN** |

### Central-integrations-huller (fejl-modes uden nerve):
Subscriber-give-up (H1) · `subscriber_timeout`/`zombie_slot` døde nerver · openai-responses/codex provider-fejl ·
buffer-trunkering · persisterings-fejl · ollama inter-byte-frys · agentic-watchdog-timeout (rammer kun
`runtime.visible_run_interrupted`, ikke `followup_failed`-clusteret → undertæller timeout-død).

---

## 3. Acceptkriterier (hårde invarianter — definitionen af "færdig")

- **I1 — Ingen tom completion:** et run kan ALDRIG ende `completed` uden synligt output. *(LUKKET: #1)*
- **I2 — Garanteret terminal-frame:** ingen stream slutter uden at ENTEN `message_stop` ELLER en typed
  fejl-frame når klienten. (H1 + H6 lukker dette.)
- **I3 — Mid-turn-resiliens:** hver forbigående runde-fejl retry'es (rund-niveau, tur bevaret) FØR turen dør.
- **I4 — Nul lydløse fejl:** hver fejl-sti enten REDDER turen ELLER lander i Centralen. Intet `except: pass`
  må afslutte/trunkere et run uden en nerve.
- **I5 — Typed taksonomi:** én retryable/fatal-sandhedskilde (ikke substring-matching).
- **I6 — Per-provider config:** retry-budgetter + idle-timeout pr. provider, ikke globale konstanter.

---

## 4. Design

### 4.1 Rund-niveau stream-retry der bevarer turen (Codex `run_sampling_request`-mønster) — KERNEN
I `visible_runs.py`-loopet: når `_a_failure` sættes OG fejlen er **retryable** (I5), så `break` IKKE.
I stedet: bevar `_followup_exchanges` (allerede checkpointet), anvend backoff+jitter, emit `retry`-SSE
("Reconnecting runde N, forsøg k/m"), og **kør samme runde igen** (separat `_round_retry_count`, ikke
runde-budgettet). Først når `round_stream_max_retries` er opbrugt → fald til nuværende interruption-sti.

### 4.2 Typed retryable/fatal-taksonomi (I5)
Lille klassifikator ved siden af `_classify_visible_run_interruption`:
- **retryable:** stream-closed-before-done · URLError/socket · 429 · 500/502/503/504 · watchdog-silence-timeout.
- **fatal:** 400/422 invalid_request (copilot-thinking-bug, gemini thought_signature) · 401/403 ·
  context-window · bruger-cancel. Én sandhedskilde; 4.1 retry'er kun på retryable.

### 4.3 Split budgetter + per-provider config (I6)
Løft `attempts=3` ud af ollama-adapteren til `_agentic_budget` som `round_stream_max_retries` (default 3) =
loop-niveau stream-budget, der wrapper adapter-niveau request-budget — Codex' to-lags-split. Emit i round-start-nerven.

### 4.4 Transport-hærdning (lån fra SDK)
- **httpx granulær timeout** på de resterende urllib-baner (ollama/copilot/openai-responses) — erstat
  watchdog-tråd-der-lukker-delt-socket (race-følsom anti-pattern, `visible_model.py:1577`).
- **Retry+jitter på first-pass** (i dag intet retry på transient first-pass 429/5xx).
- **Garanteret cleanup** ved early-break (vi er allerede gode; bekræft `try/finally` dækker aclose-failure-grenen).

### 4.5 Central-nerver der skal tilføjes (I4)
- `note_round_retry(run_id, round, attempt, reason)` — **NY** (retried-men-reddet runde i dag usynlig).
- `subscriber_timeout` — wire H1 (i dag død nerve) + emit syntetisk `message_stop` + fejl-frame før break.
- `note_round_failed` på watchdog-timeout-stien (H? — i dag bypasses observer).
- `_observe_visible_provider_error` på openai-responses/codex-baner (H4).
- buffer-trunkerings-nerve i `run_event_log.append` + `detached_run` (H6).
- persisterings-fejl-nerve (H5) — "vist live, væk ved reload" er en distinkt klasse.

### 4.6 Resume-from-offset (I2, resilience)
HTTP-route accepterer klient-offset/`Last-Event-ID` → re-subscribe genoptager fra idx i stedet for at
replaye fra frame 0. Hæv/nerve 4000-frame-cap.

---

## 5. Implementerings-plan (faser, prioriteret efter cut-impact)

**Fase 1 — Stop blødningen (rammer cut-roden direkte):**
1. Rund-niveau stream-retry der bevarer turen (4.1).
2. Retryable/fatal-taksonomi (4.2).
3. Split budgetter + retry på default-adapteren (4.3 + H2).
4. `note_round_retry`-nerve (4.5).
→ Forventet effekt: forbigående mid-turn-blip dræber ikke længere turen. Den primære cut-klasse lukket.

**Fase 2 — Luk lydløse huller (I4):**
H1 subscriber-give-up (nerve + terminal-frame) · watchdog-timeout-nerve · persisterings-fejl-nerve (H5) ·
provider-error-observe for responses/codex (H4) · buffer-trunkerings-nerve (H6). + ryd døde nerver.

**Fase 3 — Transport-hærdning (4.4):**
httpx på resterende urllib-baner + granulær timeout + retry+jitter first-pass + erstat watchdog-socket-close.

**Fase 4 — Resilience-polish:**
Resume-from-offset (4.6) · empty-completion 1× retry før fallback · per-provider-config-surface · frame-cap hævet.

---

## 6. Eksplicitte ikke-mål
- **IKKE** adoptér openai-sdk wholesale: bryder ollama-native `message.thinking` (load-bearing for followup-replay,
  [[reference_ollama_thinking_models]]) + multi-provider-abstraktionen. SDK'et passer kun openai-compat-banen,
  som ALLEREDE kører httpx.
- **IKKE** rewrite klient-vendt Anthropic-style SSE (Bjørn kan det, det virker, det er ikke buggen).
- httpx — ikke openai-sdk — er det rigtige universelle transport, og kodebasen er allerede på vej derhen.

---

## 7. Verifikation (hvordan vi VED det er produktions-grade)
- Reproducér mid-turn-fejl ved fejl-injektion (mock 502/stream-drop i runde 2 af 3) → turen skal overleve + retry synlig i Central.
- Last-fuzz: mange samtidige tool-runs → ingen tavs cut, hver afslutter med terminal-frame.
- Central-dækningstest: hver fejl-sti i §2-tabellen skal producere en nerve (automatiseret assertion).
- Acceptkriterier I1-I6 som tjekliste pr. PR.
