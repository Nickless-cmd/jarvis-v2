# Codex CLI — streaming, fejlhåndtering & "et run der aldrig dør"

Date: 2026-09-02
Type: research-notat (åben kode, Apache-2.0)
Kilder:
- OpenAI Engineering: "Unrolling the Codex agent loop" (Michael Bolin, 2026-01-23) — openai.com/index/unrolling-the-codex-agent-loop
- ZenML LLMOps Database: "Building Production-Ready AI Agents: OpenAI Codex CLI Architecture and Agent Loop Design"
- NeuZhou: "Architecture teardown of Codex CLI" (549K linjer Rust, 88 crates) — github.com/NeuZhou/awesome-ai-anatomy/tree/main/codex-cli
- Selve repoet: github.com/openai/codex (Apache-2.0)

Formål: lære af OpenAIs produktionsmønstre — specifikt det Bjørn ville lære:
sikker/stabil streaming, fejlhåndtering, og hvordan et run overlever. Input til
V2 mobile companion + vores egen agent-harness. VI kopierer ikke deres app —
vi studerer åben kode og bygger vores egne stærkere versioner.

---

## 1. Den overordnede arkitektur: queue-pair, ikke direkte kald

Codex CLI er bygget som et **queue-pair system**, ikke som en funktionskæde:

```rust
pub struct Codex {
    tx_sub: Sender<Submission>,  // skub operationer ind
    rx_event: Receiver<Event>,   // få events ud
    ...
}
```

Alt — model-kald, tool-eksekvering, sandbox, approval-flows — kører inde i én
async loop. UIs (TUI, App Server, MCP Server) er bare *forskellige frontends*
der submitter til den samme kerne.

**Hvorfor det betyder noget for os:**
- Cognition (kernen) er **afkoblet fra overfladen** (UI'en). Det er præcis vores
  R-krav "state bor på serveren, aldrig i klienten" — bekræftet af OpenAI selv.
- Backpressure: bounded channel (SUBMISSION_CHANNEL_CAPACITY = 512). Kernen kan
  ikke oversvømmes af frontends.
- Clean shutdown: drop senderen → receiver dræner → session lukker pænt.
- Flere overflader uden at duplikere logik: CLI, desktop-app, MCP, cloud-worker
  deler samme core. → Det er *deres* version af vores "Remote"-paritet.

---

## 2. Agent loop — turn-modellen

Klassisk think → act → observe, pakket ind:
1. Brugerinput → prompt (statisk indhold først, variabelt sidst).
2. Inference mod model (Responses API over SSE).
3. For hvert response item:
   - tekst → emit til UI (streaming)
   - tool_call → dispatch via ToolRouter → eksekver → append resultat → nyt kald
4. Ingen flere tool-kald → assistant message → turn er færdig.

**Terminologi:** en *thread* er hele samtalen; en *turn* er én bruger→agent-cyklus
(kan indeholde hundredvis af inference/tool-iterationer).

Vigtig pointe: agentens "output" er ofte ikke beskeden — det er kodeændringerne.
Assistant-message er bare termineringssignalet ("jeg tilføjede architecture.md").

---

## 3. Streaming — SSE + intern republisering

Responses API svarer med Server-Sent Events. Hver event's data er JSON med
type der starter med "response":

```
data: {"type":"response.reasoning_summary_text.delta","delta":"ah ", ...}
data: {"type":"response.output_text.delta","delta":"forty-", ...}
data: {"type":"response.output_item.added","item":{...}}
data: {"type":"response.output_item.done","item":{...}}   // reasoning, function_call
data: {"type":"response.completed","response":{...}}
```

Codex **konsumerer strømmen og republiserer events som interne objekter**:

- `response.output_text.delta` → UI-streaming
- `response.output_item.added/done` → transformeres til objekter der appendes
  til *næste* requests input (reasoning + function_call + function_call_output)

**Skarp adskillelse:** events til UI (deltas) vs. events til state-management
(items). Det er samme mønster vores streamReducer allerede bruger (idle →
working → interrupted → hung → error → done) — god validation.

**Prompt-format-kontrakt:** gammel prompt er *altid et eksakt præfiks* af den nye.
Det er bevidst — det er dét der muliggør prompt caching (se §5).

---

## 4. State: stateless requests + ZDR

Codex bruger **ikke** `previous_response_id` (selvom API'et understøtter det).
Årsag: fuldt stateless requests → Zero Data Retention compliance → hver request
bærer hele historikken. Resultatet er at JSON-mængden vokser *kvadratisk* over
samtalens levetid — men sampling dominerer prisen, så det er det rigtige offer.

**Lektie for os:** state i requesten (stateless server) frem for state på
serveren kræver at man tænker i replays og idempotens — præcis det vores
idempotente approve-and-execute (Task 3) gør. OpenAI valgte stateless for ZDR;
vi valgte state-på-server for overlevelsesevne. Begge er forsvarlige; forskellen
skal være et bevidst valg, ikke en tilfældighed.

---

## 5. Performance: prompt caching (linear, ikke kvadratisk)

Cache-hits kræver **eksakte præfiks-matches**. Statisk indhold (instruktioner,
eksempler) først; variabelt (bruger-specifikt) sidst. Også tools og billeder skal
være identiske mellem requests for at ramme cachen.

Det der *breaker* cachen:
- Ændring af tilgængelige tools midt i samtalen (fx MCP tools der ændrer sig)
- Skift af model
- Ændring af sandbox-config, approval-mode eller cwd

**Deres regel:** håndter midt-samtale-ændringer ved at *appende en ny message*
til input — aldrig ved at redigere en gammel. Bevar præfikset → bevar cachen.

---

## 6. Context management: auto-compaction

Når tokens overskrider `auto_compact_limit`, kalder Codex `/responses/compact`:

- Returnerer en liste af items der *erstatter* input — frigør context-vindue.
- Inkluderer en `type=compaction`-item med opaque `encrypted_content` der
  bevarer modellens latente forståelse (ikke bare tekst-resume).

Tidligere (manuelt /compact) gjorde de det med summarization-instruktioner;
nu er det et specialiseret endpoint. Claude Code har til sammenligning en
4-lags kaskade (SNIP → Microcompact → COLLAPSE → Autocompact) med kirurgisk
sletning; Codex' er simplere — "summarize everything" når det flyder over.

**Lektie for os:** vi har vores egen compaction (dream-konsolidering, chronicle).
Pointen er den samme: *noget* skal ske før context-vinduet rammer bunden, og
det skal være automatisk, ikke manuelt.

---

## 7. Fejlhåndtering & "et run der aldrig dør"

### 7.1 Guardian AI — auto-approval med second opinion (fail-closed)
Når et tool-kald kræver approval, kan en **anden model-instans** (gpt-5.4)
risiko-score handlingen:

```rust
const GUARDIAN_PREFERRED_MODEL: &str = "gpt-5.4";
const GUARDIAN_REVIEW_TIMEOUT: Duration = Duration::from_secs(90);
const GUARDIAN_APPROVAL_RISK_THRESHOLD: u8 = 80;
```

- Rekonstruerer kompakt transcript (token-loftet)
- Sender struktureret review-anmodning → GuardianAssessment (risk_level,
  risk_score 0-100, rationale, evidence)
- Auto-approve hvis risk_score < 80; deny ellers
- **Fails closed:** timeout, parse-fejl eller enhver exception = deny

Det er Constitutional AI anvendt på runtime tool-eksekvering. "Ask always" og
"ask never" er begge dårlige; en automatisk risikovurdering er mellemvejen.

### 7.2 Fire forsvarslag (defense in depth)
1. Approval policy (bruger-samtykke) — `Never | OnFailure | UnlessSafe | Always`
2. Guardian AI review (automatisk risikoscoring)
3. OS-sandbox (Seatbelt/Landlock+seccomp/RestrictedToken — 17K linjer, ingen Docker)
4. Network proxy (MITM, domæne-allowlist, audit-log)

### 7.3 Progressive sandbox escalation
Prøv strammeste sandbox først. Hvis denied → prøv løsere *uden* at spørge igen
(approval var cached):
1. Fuld sandbox (fs + netværk begrænset) → denied?
2. Fs-sandbox kun → fejler stadig?
3. Rapportér fejl til modellen → den finder en alternativ tilgang.

### 7.4 Hook-system til livscyklus-interception
Fem hooks (session_start, user_prompt_submit, pre_tool_use, post_tool_use, stop).
`pre_tool_use` kan approve/deny/modificere et tool-kald FØR eksekvering —
brugernes egen udvidelsesmekanisme til sikkerhedsmodellen.

### 7.5 Generelle resilience-mønstre (fra økosystemet)
- Retry med backoff + idempotency keys (forhindrer duplikat-aktioner ved retry)
- Circuit breakers (stop med at hamre på noget der er nede)
- Model fallbacks (prøv næste provider hvis én fejler)
- Graceful degradation (defineret svar på hver fejlklasse FØR den sker)
- Klassificér fejl: safe-to-retry vs. ikke

---

## 8. Det værd at stjæle (vores take-aways)

1. **Guardian-mønsteret** — en anden model risikoscorer handlinger; auto-approve
   under tærskel. ~200 linjer for en basis-version. → Kan vi bruge det i vores
   approval-system (capability vs tool-intent) for at reducere approval-fatigue?
2. **Queue-pair arkitektur** — afkobl agent-kerne fra frontends via typed channels.
   Det er præcis den struktur V2-appen bygger imod (mission-control som overflade
   på samme kerne).
3. **Progressive sandbox escalation** — prøv stramt, slap gradvist, spørg aldrig
   to gange.
4. **Append-don't-edit reglen** for midt-samtale-ændringer (bevar præfiks/cache).
5. **Two-phase memory extraction** (per-rollout → cross-rollout konsolidering) —
   undgår "summarize everything at once"-problemet. → beslægtet med vores
   chronicle/dream-struktur.
6. **Fail-closed som default** for alt der ikke kan nå at svare (timeout = deny).
7. **State-på-server** bekræftet af OpenAI selv: iOS-appen "reconnects to tasks
   more reliably when you return to the app" — state skal overleve klienten.

## 9. Hvad de gør anderledes end os (ærligt)

- De valgte **stateless + ZDR**; vi valgte **state-på-server for overlevelse**.
- De valgte **Rust + native sandbox** (17K linjer!); vi bygger i TS/RN med
  server-side isolation. Deres sandbox er produktet; vores er governance-laget.
- Guardian er en **anden model** der dømmer handlinger. Vi har approval-kort +
  Centralens governance-værn. Samme idé-familie, anden implementering.
- Claude Code vs Codex filosofi: Claude stoler på modellen og sandboxer løst;
  Codex verificerer alt og sandboxer stramt. Vi er (mest) Claude-skolen med
  Codex-inspireret approval-disciplin.
