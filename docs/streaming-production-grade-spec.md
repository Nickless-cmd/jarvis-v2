# Production-Grade Streaming Spec

**Status:** Draft 2 — 2026-06-29 (adversarisk valideret, §11 blokerende tilføjelser foldet ind). Owner: Bjørn.
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
- **I7 — Bounded kontekst i agentic loop:** lean prompt for runde ≥2 + overløb som navngivet failure_kind,
  så lange/autonome loops ikke bloater sig ihjel (§4.7).
- **SLO (P2):** ≥99,5% interaktive tool-runs når terminal-besked · p99 rund-retry < 2 · 0 tavse stops/døgn.
  Retry må ALDRIG re-eksekvere tools (S3) · hårdt total-retry-loft pr. tur (S2) · kill-switch pr. risikabel fase (P1).

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

### 4.7 Lean agentic-round-prompt (I7 — ny; Bjørns spørgsmål 29. jun)
**Verificeret problem:** `visible_followup.py:313` sender `list(base_messages) + exchanges` HVER runde —
dvs. hele den tunge assembly-prompt (~26k tegn/6.5k tokens: system + 45-dels awareness/inner-life/somatik)
re-sendes hver agentic-runde, plus de voksende tool-exchanges. Konsekvens:
- **Kontekst-bloat → overløb** (lange/autonome runs rammer model-vinduet → Ollama 400 "prompt too long"
  → tavst svar, [[reference_model_context_windows]]). Reel cut-årsag i lange agentic loops.
- **Flere fejl for thinking-modeller** (mere at ræsonnere over) + unødig latency + token-kost.

**Design:** introducér en LEAN prompt for runde ≥2 af et agentic loop:
- BEHOLD: identitet-kerne (hvem han er, kort), tool-katalog, den oprindelige bruger-opgave, ALLE tool-resultater.
- DROP: tung per-turn awareness-berigelse (inner-life/somatik/mood/digests/causal/nudges) — den framer kun
  *første* svar, ikke opgave-eksekvering.
- BEVAR de 2 load-bearing anti-løgn-rækker (fact-grounding) hvis de er billige.
- **Cache-interaktion:** selv hvis prefix er cachet (billig kost) tæller den STADIG mod kontekst-vinduet og
  fortyndes — så trimning hjælper fejl+overløb uanset cache. Mål token-besparelsen pr. runde.
- **Risiko at respektere:** dropper man for meget mister Jarvis personlighed midt i et loop. Test at lean-prompten
  bevarer stemme + at tool-resultater aldrig trimmes væk.

Dette er et selvstændigt arbejde der KAN reducere både agentic-cuts (overløb) OG autonom-looping. Egen fase.

---

## 5. Implementerings-plan (faser, prioriteret efter cut-impact)

**Fase 0 — Fundament FØR vi rører den hotte loop (P7, S1):**
Fejl-injektions-harness (mock 502/stream-drop/overløb i runde K) + kill-switch-flag-mønster + central-
dæknings-assertion-test. Ingen hot-loop-ændring uden dette. Reproducér en ægte cut via #2-observabilitet først.

**Fase 1 — Stop blødningen (rammer cut-roden direkte):**
1. Rund-niveau stream-retry der bevarer turen (4.1) — bag `AGENTIC_ROUND_RETRY_ENABLED`-flag (P1).
2. Retryable/fatal-taksonomi (4.2) — inkl. context-window-overløb som navngivet kind (S5).
3. Split budgetter + retry på default-adapteren (4.3 + H2) + **hårdt total-retry-loft pr. tur** (S2).
4. Invariant: retry re-sampler KUN, re-eksekverer ALDRIG tools (S3).
5. Keepalive + "Reconnecting n/m"-event under backoff (S4).
6. `note_round_retry`-nerve med `recovered`/`exhausted`-udfald (4.5 + S7).
→ Forventet effekt: forbigående mid-turn-blip dræber ikke længere turen. Den primære cut-klasse lukket.

**Fase 2 — Luk lydløse huller (I4):**
H1 subscriber-give-up (nerve + syntetisk `message_stop` + fejl-frame) på **ALLE TRE relay-endpoints**
(`chat_stream_v2.py:279` POST + `chat.py:913` /runs/subscribe + `chat.py:953` /sessions/live — G6, rammer
cross-device) · watchdog-timeout-nerve · persisterings-fejl-nerve (H5) · provider-error-observe for
responses/codex (H4) · buffer-trunkerings-nerve (H6). + ryd døde nerver.

**Fase 2.5 — Klient-integritet (P4, "ingen hemmelige bræk" på klient-siden):**
Mobil `mergeServer`-bro (luk wholesale-replace-race der får svar til at forsvinde) · desk+mobil ignorerer
ukendte SSE-events graциøst (verificér mod nye retry-events) · persisterings-pålidelighed/-retry (H5/P5).

**Fase 3 — Transport-hærdning (4.4) + circuit-breaker:**
httpx på resterende urllib-baner + granulær timeout + retry+jitter first-pass + erstat watchdog-socket-close.
\+ provider-helbreds-cirkelbryder (S6): N fejl i træk → kort-slut + observér + valgfri fallback-provider.

**Fase 4 — Lean agentic-prompt (4.7, I7) + operabilitet:**
Lean prompt for runde ≥2 (reducér overløb/fejl i lange+autonome loops) · operator cut-overblik + proaktiv
alerting (P3) · SLO-instrumentering (P2).

**Fase 5 — Resilience-polish:**
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
- Acceptkriterier I1-I7 som tjekliste pr. PR.

---

## 8. Self-review (korrekthed/fuldstændighed) — fundne huller i spec'en

- **S1 — Roden er en HYPOTESE, ikke bevist.** 8 reproduktioner kørte rent; mid-turn-retry-teorien er
  stærk + kode-funderet men IKKE bekræftet ved reproduktion. **Krav:** Fase 1 skal være korrekt UANSET
  om hypotesen holder (den hærder loopet generelt), og vi erklærer IKKE sejr før #2-observabiliteten viser
  en `note_round_retry`/`empty_completion`-sti der matcher en ægte cut. Byg fejl-injektion (S-verifikation) FØRST.
- **S2 — Kompounderende retries.** Rund-retry (3) × adapter-retry (3) = op til 9 provider-kald pr. runde,
  og × runder = eksplosion. **Krav:** hårdt TOTAL-loft (samlet forsøg + samlet wall-clock pr. tur), ikke kun pr. lag.
- **S3 — Retry må KUN re-sample, ALDRIG re-eksekvere tools.** Tools har side-effekter (memory_upsert, bash).
  Codex bevarer tool-resultater i history og re-sampler kun. **Krav:** eksplicit invariant — retry genbruger
  `_followup_exchanges` (tool-output bevaret), kører ALDRIG et tool igen.
- **S4 — Backoff blokerer streamen.** Under retry-backoff flyder ingen tokens. **Krav:** keepalive +
  "Reconnecting n/m"-event SKAL fyre under backoff, ellers genindfører vi et tavst gap.
- **S5 — Manglende failure_kind: context-window-overløb.** §4.7 afslørede det. **Krav:** overløb er en
  navngivet (fatal-men-actionable) failure_kind med egen nerve + lean-prompt-mitigering, ikke et tavst 400.
- **S6 — Intet circuit-breaker / provider-failover.** Mod en DØD provider piler 3× retry × mange runs op
  (thundering herd trods jitter). Codex har transport+provider-failover; vi har intet. **Krav:** provider-helbreds-
  cirkelbryder (efter N fejl i træk → kort-slut + observér + evt. fald til fallback-provider) — mindst Fase 3.
- **S7 — "Reddet" vs "opbrugt" skal være distinkte signaler.** `note_round_retry(attempt)` + et separat
  `recovered`/`exhausted`-udfald, så Centralen viser om retry FAKTISK redder eller bare udskyder døden.

## 9. Production-readiness review (set fra en der skal DRIVE det) — operabilitets-huller

- **P1 — Kill-switch.** Fase 1 rører den hotte loop. **Krav:** env/config-flag (`AGENTIC_ROUND_RETRY_ENABLED`)
  så vi kan slå rund-retry FRA uden redeploy hvis den opfører sig forkert. Gælder hver risikabel fase.
- **P2 — Udefineret SLO = udefineret "færdig".** "Produktions-grade" kræver et mål. **Forslag:**
  ≥99,5% af interaktive tool-runs når en terminal-besked; p99 rund-retry < 2; 0 tavse stops/døgn (terminal-frame
  garanteret). Uden tal kan vi ikke sige "lukket en gang for alle".
- **P3 — Operator-view + alerting, ikke kun passiv central.** I dag skal man poll'e incidents. **Krav:**
  ét "cut-overblik" (recurrence-rate pr. failure_kind/provider) + PROAKTIV alert når empty_completion/round-retry-
  exhausted spiker over tærskel. Ellers opdager vi næste regression for sent (præcis Bjørns "ingen hemmelige bræk").
- **P4 — Klient-kompat for nye events + den uafsluttede mobil-bug.** Nye `retry`/round-retry-SSE: desk+mobil SKAL
  ignorere ukendte events grациøst (verificér). Og: **mobilens wholesale-replace** (`sessions.select` →
  `setMessages(server)` racer post-svar-halen → svar forsvinder, fundet 29. jun) er et "hemmeligt bræk" i scope
  for "intet må fejle lydløst" — skal med (port desk's `mergeServer`-bro til mobil).
- **P5 — Persisterings-pålidelighed (H5), ikke kun en nerve.** "Vist live, væk ved reload" er data-integritet.
  **Krav:** persist-retry/transaktionel garanti — en nerve fortæller os det skete, men brugeren har stadig tabt svaret.
- **P6 — Total-run wall-clock SLA.** Retries må ikke gøre en tur til minutters hæng. **Krav:** hård total-tur-deadline
  (degradér til "jeg brugte for lang tid, her er hvad jeg nåede" — aldrig uendeligt).
- **P7 — Rollout-disciplin.** Byg fejl-injektions-harness (mock 502/drop/overløb) FØR den hotte loop røres;
  hver fase bag flag; verificér mod I1-I7 + SLO før næste fase. Ingen big-bang.

**Konklusion på reviews:** spec'ens RETNING er solid (transport-garantier + codex-loop-mønster + nul-lydløs),
men den var ikke produktions-klar uden: total-retry-loft (S2), re-sample-ikke-re-exec-invariant (S3),
circuit-breaker (S6), kill-switch (P1), SLO (P2), proaktiv alerting (P3), mobil-merge-fix (P4) og
fejl-injektion-først (P7). Disse er nu indarbejdet. **MED dem + §10 (cross-device) er vi klar til Fase 1.**

---

## 10. Cross-device edges (jarvis-desk ↔ mobile companion) — eksplicit dækning

Multi-device er hvor "lukket en gang for alle" holder eller falder. Mobil-kilden er worktree
`.worktrees/jarvis-mobile-companion-v1/apps/mobile` (vc52, omskrevet 23-29 jun — MERE hærdet end ventet;
ingen main-tree-kopi). Edge-audit (29. jun):

**Ægte HANDLED (rør ikke):**
- **Samtidig drive:** server-single-flight `claim_or_create` (`run_event_log.py:157`) + frame-0-replay → begge
  enheder ser samme run, intet dobbelt-run.
- **FCM vs live-stream:** push undertrykkes når en subscriber så/ser runnet (`was_consumed_or_active`,
  `run_event_log.py:140`) → ingen dobbelt/tab ved foreground.

**Hullerne (G1-G6):**
- **G1 (LOAD-BEARING) — mobilen wholesale-replacer beskeder uden merge-bro.** `SessionContext.tsx:46`
  `setMessages(result.messages)` uden merge; `mergeServer`/`server_missing_keep_stream` (som desk BEVISTE
  virker, `desk/SessionContext.tsx:158`) blev aldrig porteret. HVER foreground-resync / busy→idle / notif-tap /
  retry-udløst `select` kan wipe det live snapshot midt i halen. **De planlagte retry-events (§4.1) udløser
  denne race OFTERE** (flere mid-turn-frames → flere refresh-triggers). → **Fase 1-BLOKERENDE prerequisite for
  at sende de nye streaming-ændringer til mobil.** Resten af partial-edges bunder i denne.
- **G2 — ~~desk mangler live token-follow~~ → RETTET af desk-audit: HANDLED.** `followRun` → `/sessions/{id}/live`
  ER wired i både ChatView (`:213`) og CodeView. Cross-device-audit'en var stale her. Rest: follow'ens egen
  resiliens (desk D4).
- **G3 — retry-under-resync-flimmer:** lukkes af G1's merge; indtil da gør de nye retry-events G1 værre.
- **G4 — dual-finalize:** fallback-besked (#1/§Fase 5) skal være `run_id`-keyet + reconciled, så to enheder ikke
  begge injicerer den. Mobil deduper intra-device (`persistedRunRef`) men mangler cross-device merge (= G1 igen).
- **G5 — ~~ingen takeover-banner~~ → RETTET af desk-audit: HANDLED på desk** (`ChatView.tsx:422` "📱→🖥 Aktiv på
  en anden enhed — følger med her live"). Mobil mangler stadig en eksplicit. UX, lav prioritet.
- **G6 — H1 rammer ALLE TRE relay-endpoints, ikke kun POST:** `chat_stream_v2.py:279`, `chat.py:913`
  (`/runs/{id}/subscribe`), `chat.py:953` (`/sessions/{id}/live`) gør alle `if empty>300: break` UDEN syntetisk
  `message_stop`/fejl-frame. En anden enhed der følger et stallet run får en bar socket-luk. I2-bruddet er
  identisk på alle tre — H1-fixet skal dække alle tre, ikke kun POST.

**Fase-tilknytning:**
- **G1** → **Fase 2.5, men Fase-1-BLOKERENDE for mobil-rollout** (porter desk's mergeServer-bro). Højeste cross-device-prioritet.
- **G6** → **Fase 2** (udvid H1 til alle tre relay-endpoints).
- **G2** → **Fase 2.5** (desk live-follow-paritet; server-støtte findes).
- **G3, G4** → **Fase 2.5 / Fase 5** (følger G1).
- **G5** → **Fase 4** (UX-polish).

**Net:** edges 3+6 HANDLED; 1,2,4,5,7,8 PARTIAL med G1 som den fælles rod. **G1 er Fase-1-gate for mobil:**
vi sender ikke retry-events til mobil før merge-broen er på plads, ellers forværrer vi wipe-racen.

### 10b. Desk-specifik audit (29. jun) — desk er den HÆRDEDE klient

**Dom: desk er produktions-klar for streaming-kernen. INGEN hul på niveau med mobilens G1.** Terminal-garantien
er tripel-backstoppet (message_stop-gendispatch / 9s stale-detektor / 90s watchdog), `mergeServer` +
`server_missing_keep_stream` dedup'er korrekt (det mobil mangler), og de nye `retry`-events tolereres uden at
brække reduceren (verificeret + testet `streamReducer.ts:111`). Code-mode deler SAMME stream-klient som chat
(ingen separat sti). Når serverens H1/I2 syntetiske `message_stop` lander, forbruger desk den uden ændringer.

| ID | Hul | Severity | Fase |
|----|-----|----------|------|
| **D1** | **CodeView reconcile manglede `reconciledForRun`-dedup-vagt → code-mode kunne dobbelt-finalisere svar (dublet). RETTET 29. jun (tsc grøn) — afventer desk-rebuild for at shippe.** | Medium (korrekthed) | **FIKSET** |
| D2 | Desks eget-drop-resume re-subscriber via `followRun` UDEN `Last-Event-ID`/`from_idx` → frame-0-replay (taber intet i dag pga. reducer-reset, men kan ikke bruge §4.6 før desk sender offset) | Lav | Fase 5 |
| D3 | Approval-POST-fejl rydder `pendingApproval` optimistisk + surfacer som generisk error; server-stream blokeret → degraderer til 90s onHung-hæng | Lav-Medium | Fase 2.5 |
| D4 | `followRun` (live-follow) har ingen intern reconnect; mid-follow-drop falder til poll-refresh, frame-0 på næste bgActive-kant | Lav | Fase 2.5 |
| D5 | Nye `retry`/"Reconnecting n/m"-events renderer harmløst men USYNLIGT (reducer ignorerer ukendte kinds) → kræver en reducer-case + UI for faktisk at vise "Reconnecting n/m" | Lav (UX) | Fase 2.5/4 |
| D6 | Ingen `powerMonitor.on('resume')` → re-sync efter sleep er poll-baseret (1.5s), ikke event-drevet | Lav | Fase 3 |
| D7 | `onHung` prompter i stedet for auto-reattach (inkonsistent med netværks-drop-stien). Bevidst, forsvarligt | Triviel (UX) | Fase 4 |

**Net desk:** kun D1 var en ægte bug (nu fikset, afventer rebuild). D2-D7 er lav-severity polish eller rene
afhængigheder af allerede-planlagte server-faser. Desk kræver **ingen** ændring for H1/I2-fixet.

---

## 11. Adversarisk validering (5 røde-hold + synteser, 29. jun) — dom + blokerende tilføjelser

**Dom: GO-med-tilføjelser.** Kerne-diagnosen + retningen er kode-verificeret korrekte (cut-roden, retry-seamet,
Fase-0-først). MEN spec'en var som skrevet **IKKE failsafe-complete** og matchede **IKKE** SDK+codex endnu.
Seks blokerende huller (alle verificeret mod kode) — to af dem betyder at fixet som specificeret enten er
**umuligt** (B) eller **aktivt korrumperende** (C). Disse er ægte blockers, ikke polish.

### 11.1 Blokerende (skal foldes ind FØR/SOM-DEL-AF de berørte faser)

- **B11 — I5 typed-taksonomi er UTILFREDSSTILLELIG som-er → skal bygges FØR 4.1.**
  `FollowupFailed` (`visible_followup.py:78`) bærer kun `round_index:int, error:str, summary:str`; HTTP-koden
  stringificeres ind i `summary` ("provider-error: HTTP 502"), og watchdog'en føder en ANDEN streng
  (`visible_runs.py:2157`). 4.1's retryable-beslutning afhænger af et struktureret `failure_kind`+`http_status`
  der ikke findes. **FIX: tilføj `failure_kind(enum)`+`http_status(int|None)` til `FollowupFailed` OG watchdog-
  `_a_failure`, populér ved ALLE 5+ raise/yield-steder. Sekvens: FØR 4.1 i Fase 1.**

- **C11 — 4.1-retry DOBBELT-emitter/-persisterer partielle deltas (NY regression fixet selv indfører).**
  Deltas yieldes til klient OG appendes til `_all_followup_parts` (`visible_runs.py:2210`); ved retry nulstilles
  kun `_a_parts` (2014), IKKE `_all_followup_parts` (som føder det persisterede svar, 3043). En runde der
  streamer partiel tekst og så fejler → teksten står live + i persistering; 4.1's re-run re-yielder friske deltas
  → **dubleret synlig tekst + dobbelt-tællet persistering på præcis "tænker-lidt-BANG"-casen.** **FIX: snapshot
  `len(_all_followup_parts)` ved runde-start; ved retry trunkér tilbage til den grænse + emit typed
  `round_restart_discard_partial`-SSE; spec desk/mobil-reducer-discard-kontrakt i Fase 1 (ikke 2.5). FØR hot-loop.**

- **D11 — Forældreløs samtidig provider-stream + silence-timeout fejl-klassificeret.**
  4.1-retry spawner en ANDEN `_pump_agentic` mens den første executor-tråd er ukancellérbar (`visible_runs.py:2107`)
  → to samtidige streams/runde (dobbelt last/kost + hængende forbindelse). OG: silence-timeout (GLM 44-102s TTFT-
  klasse) er listet retryable, men retry af en stallet provider re-trigger samme timeout → brænder budget for
  ~nul recovery. **FIX: split retryable i `transient_drop` (retry samme provider) vs `provider_stall` (skip retry →
  S6 circuit-breaker/failover); fence den døde pump (epoch-token + force-close socket) FØR retry. FØR hot-loop.**

- **A11 — Egen SSE-decoder uhærdet (split-UTF-8 / malformet JSON dræber streamen mid-turn).**
  `_iter_sse_events` (`visible_model.py:2737`) gør `raw_line.decode("utf-8")` uden `errors=` + `json.loads` uden
  guard; DELT af first-pass OG hver followup-adapter. Et split multibyte-codepoint (æøå/emoji = Jarvis' normale
  stemme) eller 200-så-malformet-JSON-chunk → exception ud af generatoren → stream dræbt. **Usynlig for 4.1's retry
  (generator-exception, ikke FollowupFailed)** og et medlem af den EKSAKTE symptom-klasse. §1A påstår den dækket,
  §4/§5 planlægger den intetsteds. **FIX: byte-buffer-til-event-grænse + `errors="replace"` + `json.loads` try/except
  → typed retryable `malformed_stream_payload`; ind i §2-tabel + nerve + Fase-0-fejlcase.**

- **E11 — Tur-scoped total-retry-loft ikke wired ind i 4.1 (900-kald worst-case).**
  S2/P6 påstår total-loft, men 4.1 introducerer kun per-runde `_round_retry_count`; med `_AGENTIC_MAX_ROUNDS=100`
  (`visible_runs.py:1799`) → 9×100. **FIX: `_turn_total_retries`+`_turn_started_at` som førsteklasses del af 4.1
  (init ved for-loop 1965), tjekket i retry-grenen, konkrete tal (≤12 stream-retries/tur, ~600s wall-clock = P6).
  Afklar eksplicit om ollama's interne attempts=3 fjernes eller beholdes.**

- **F11 — 4000-frame-cap dropper TERMINAL-frames lydløst på lange runs → DETERMINISTISK I2-brud.**
  `run_event_log.append` (`run_event_log.py:49`) dropper frames over cap uden nerve. En lang agentic/autonom run
  (>4000 frames = §4.7-målet) taber sit `message_stop` → hver re-subscriber/cross-device-følger (chat.py:913/953)
  ser intet 'done' → H1's bare break → **I2-brud på HVER lang run, ikke intermittent.** De nye retry/heartbeat-frames
  accelererer cap'en. **FIX: terminal-frames ALDRIG underlagt cap (reserveret hale-slot) + trunkerings-nerve FØR drop;
  heartbeat/retry-frames live-only (ikke persisteret til replay-log). Træk ind i Fase 1/2, ikke Fase 5.**

### 11.2 Ikke-blokerende, men skal med (heal-ikke-bare-observér + faktuelle rettelser)

- **I1 var OVERSTATED:** `_guarantee_visible_outcome` (`visible_runs.py:6716`) skriver en STATISK undskyldnings-streng,
  den re-sampler IKKE. Reframe I1 som "ingen LYDLØS tom completion (observér + ærlig fallback)" — IKKE en heal.
  **Træk empty-completion 1× re-sample fra Fase 5 til Fase 1** (genbrug `note_resend`-primitivet `visible_runs.py:1429`);
  undskyldning fyrer kun EFTER re-sample fejler. I1's SLO = recovered-rate.
- **S6 faktuelt forkert:** der FINDES en circuit-breaker (ofa/arko, `cheap_provider_runtime.py:1890`). **Fase 3 = LØFT
  den til en delt per-provider-breaker** (ikke greenfield — respektér konsoliderings-reglen). Og: visible-lane
  provider-**failover** (mindst deepseek-v4-flash som fallback) skal være KRÆVET, ellers er S6 stop-ikke-heal.
- **Jitter i den DELTE backoff-helper** (`visible_followup.py:463` er ren eksponentiel uden jitter) — så BÅDE den
  løftede ollama-retry og 4.1 arver den; ellers genskaber vi den thundering-herd S6 skal dæmpe.
- **Retry-After:** håndtér RFC-7231 HTTP-date-form (ikke kun numerisk; `:460` `float(...or 0)` nuller date-form →
  øjeblikkelig retry der defeater cooldown). Én delt parser; uparselbar → default-backoff, ikke 0.
- **P6 graceful-degrade ind i 4.1-udmattelse:** emit den checkpointede partial (`_all_followup_parts`) + ærlig note
  FØR interruption-nerven — udmattelse må ALDRIG være et tomt tab (partiel tekst findes allerede).
- **H5 persist-retry (P5)** → tildel Fase 2.5 (heal, ikke kun nerve; `_persist_session_assistant_message` er i `except:pass`).
- **§4.6:** fraværende/ugyldig Last-Event-ID → replay fra frame 0 (bevarer §10 cross-device HANDLED); offset er ren
  optimering, aldrig en korrekthедs-afhængighed. `read(from_idx)` findes allerede (`run_event_log.py:61`) → scope =
  klient-sender-offset + cap-hævning.
- **SLO-målbarhed:** "0 tavse stops/døgn" er gated på Fase-2-nerver → kan ikke validere Fase-1-exit. Træk H1+watchdog-
  nerve-sliven ind i Fase 1, ELLER nedgradér Fase-1-exit til `note_round_retry` recovered-rate. Angiv hvilken nerve
  bakker hvert SLO-tal.
- **Fase 0-harness 3 former** (ikke kun clean-fail): clean-fail-før-delta · **partial-deltas-så-drop (PRIMÆR
  accept-scenarie** — trigger for C11+D11) · HTTP-400-overflow-body (context-window). Assertér: ingen dubleret
  persisteret tekst, ingen anden samtidig pump.
- **Retry-prompt-identitet (4.1/4.7):** en retry SKAL sende byte-identiske messages som original (samme lean/fuld-
  beslutning, samme exchange-snapshot) — snapshot messages ÉN gang/runde, recompute ALDRIG lean-vs-fuld i retry-loopet.
- **Kill-switch (P1):** at slå retry FRA må ALDRIG slå terminal-frame (I2) eller nerve (I4) fra — de er ubetingede.
  Land watchdog→`note_round_failed`-wiring i Fase 1 (flag-off falder til den nerve-blinde watchdog-sti).
- **Minor:** fjerde give-up-sted `chat.py:991` (`empty_polls>150`) ind i H1/I2-revisionen · relay-GC/TTL for done-runs
  i `_RUNS` (in-proc dict, ingen eviction → memory-pressure på --workers 1) · idempotency-key som eksplicit
  forsvarligt ikke-mål (retries er sampling-only + history-keyed via S3).

### 11.3 Revideret rækkefølge (blokere foldet ind)
**Fase 1 bliver:** B11 (struktureret failure_kind) → C11+D11 (partial-discard + pump-fence, FØR hot-loop) →
4.1 rund-retry → A11 (decoder-hærdning i taksonomi) → E11 (tur-total-loft) → I1-resample → SLO-nerve-slice +
kill-switch-I2/I4-garanti. **Fase 0-harness's primære scenarie = partial-then-drop.** Først NÅR disse er inde +
verificeret mod harness, er designet failsafe-complete og på SDK-transport + codex-app-paritet.

### 11.4 Fase 0 leveret + forfining (29. jun)
Fase 0 bygget + verificeret (13 tests grønne, flag fail-closed OFF, hook streng prod-no-op):
`core/services/visible_followup.py` (flag `agentic_round_retry_enabled()` + injector + `_maybe_inject_fault`),
`tests/test_streaming_fault_injection.py`, `scripts/repro_streaming_fault.py`. visible_runs.py URØRT.

**Forfining af §2/H2 (kode-bekræftet via harness):** den lydløse runde-fejl er **raise-vs-yield-specifik**:
- En **RAISED** transient drop (mest realistisk socket-drop) fanges af `_pump_agentic`'s `except`
  (`visible_runs.py:2090`) → sætter `_a_failure` men fyrer **ALDRIG `note_round_failed`** → runde-fejlen er
  **centralt TAVS** (kun `followup_round` + `followup_loop_complete` fyrer). **Dette er den PRIMÆRE cut-klasse og
  den er usynlig på runde-fejl-niveau i dag.**
- En **YIELDED** `FollowupFailed` fyrer `note_round_failed`.
→ Fase 1/2 skal wire `note_round_retry`/`note_round_failed` præcis på den **raised-exception-sti** (`:2090`).
I2 holder dog selv på den tavse sti (terminal `done`/`interrupted` leveres altid) — det er kun runde-fejl-NERVEN der mangler.
