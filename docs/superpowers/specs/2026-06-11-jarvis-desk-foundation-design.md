# jarvis-desk — App-shell + Rich-rendering foundation

**Status:** spec (afventer Bjørns review)
**Author:** Claude Opus 4.8 (med Bjørn)
**Created:** 2026-06-11
**Parent:** ny prod-grade desktop-app til Jarvis, taler `/chat/stream/v2`

## Formål

Etablér det arkitektoniske fundament for jarvis-desk som en **fuldt fungerende
desktop-app i Claude Desktop-klasse** — ikke et skelet der "kan udbygges", men
den rigtige base som Chat/Cowork/Code-modes bygges ovenpå.

Denne spec dækker **App-shell + Rich-rendering** (delsystem 1+2 af 5). De øvrige
delsystemer får egne spec→plan→byg cyklusser:

- Lag 1: Chat-mode færdiggørelse (visuelt design allerede locked 2026-06-10)
- Lag 2: Cowork-mode (kræver design)
- Lag 3: Code-mode (kræver design)

## Nordstjerne

jarvis-desk skal føles som en rigtig produktions-app — på niveau med Claude
Desktop. Det forenende princip gennem hele appen:

> **Delt mekanisme, mode bestemmer presentation-density.**

Tool-rendering, fejl/liveness-UX og det meste andet bygges ÉN gang som
density-aware komponenter. Hver mode konfigurerer hvor prominent tingene vises:
Chat-mode opfører sig som Claude.ai (roligt, samtale i fokus, tools diskrete);
Code-mode opfører sig som Claude Code (fuld agentic-timeline, diagnostik synlig).

## Locked beslutninger (fra brainstorm 2026-06-11)

| Emne | Valg |
|------|------|
| Scope | App-shell + Rich-rendering først; Chat/Cowork/Code egne specs |
| State-arkitektur | React Context + custom hooks, ingen ekstern state-lib |
| Multi-user | Per-install single-user, token i Electron-config |
| Rendering-libs | Shiki (code) + lazy mermaid/katex + react-markdown/remark-gfm |
| Tool-rendering | Density-aware komponenter (compact\|full), delt på tværs af modes |
| Fejl/liveness | Én delt state-maskine, density-konfigureret presentation per mode |
| Ombygning | Frisk genopbygning af shell'en (App.tsx → ~40 linjer) |
| Scope-afgrænsning | jarvis-desk = arbejds-app (Chat/Cowork/Code + Memory/Scheduling/Settings). Observability (Mind/Dashboard/Dispatches/Trading/Channels) → Mission Control |
| Rolle-skopering | Auth giver `role`; flader filtrerer *indhold* efter rolle, ikke kun synlighed |

## Scope-afgrænsning: arbejds-app, ikke observability

jarvis-desk er **relationen og arbejdet** med Jarvis — ikke et vindue ind i hans
maskineri. Det maskineri (affektiv tilstand, sub-agenter, trading, channels)
bor i Mission Control (web).

**Inde i jarvis-desk:**
- Mode-slider (arbejds-modes): **Chat**, **Cowork**, **Code**
- Sekundær nav (opslags-flader, i sidebar-fod ved bruger-avatar): **Memory**,
  **Scheduling**, **Settings**

**Ude (→ Mission Control):** Mind, Dashboard, Dispatches, Trading, Channels.

## Rolle-skopering (cross-cutting concern)

Auth/whoami giver `role: 'owner' | 'member' | 'guest'`. Rollen styrer ikke kun
*om* en flade vises, men *hvad* den viser:

- **Memory**: member ser kun den hukommelse Jarvis har *med ham* (relationen);
  owner ser Jarvis' fulde indre memory.
- **Scheduling**: member ser kun hvad Jarvis har planlagt *med ham*; owner ser alt.
- **Skrive-handlinger** (plan-approval, process-stop, staging-commit) gates til
  owner; member ser read-only.

Derfor eksponerer auth-laget `role` i context fra dag 1, og hver rolle-følsom
flade tager rollen som input.

### Serveren er grænsen — klienten er kun UX

**Kritisk:** klient-filtrering er ALDRIG den arkitektoniske grænse. En member
der manipulerer sin klient må ikke kunne nå owner-only memory/scheduling. Server
håndhæver; klienten filtrerer kun for at undgå at vise tomme/forbudte felter.

Konkret kontrakt (detaljeres i Memory-spec og Scheduling-spec; foundation låser
princippet):

- **Token → rolle:** hvert request bærer bearer-token; server udleder `user_id`
  + `role` server-side. Klientens `role` er kun et spejl til UX.
- **Member-scoped reads:** memory/scheduling-endpoints returnerer som default KUN
  den anmodende brugers egen relations-data (workspace-isolation via det
  autentificerede user_id — ikke en klient-sendt parameter). En member kan ikke
  udvide scope ved at ændre query-params.
- **Owner-only data/felter:** Jarvis' fulde indre memory + alle brugeres
  scheduling eksponeres kun bag en `require_owner`-dependency (mønster findes
  allerede i backend, fx `routes/jarvisx.py` dispatches-endpoints). Non-owner →
  403, ikke filtreret 200.
- **Write-gates:** plan-approval, process-stop, staging-commit kræver
  `require_owner` server-side. Klientens skjul af knapper er kosmetik ovenpå.
- **Eksisterende endpoints at bygge på:** `/jarvisx/workspace/*`,
  `/jarvisx/scheduling/state` findes; Memory/Scheduling-specs definerer de
  præcise member-scoped vs owner-scoped varianter + felt-niveau redaktion.

Foundation-spec'en leverer kun klient-siden (role i context, role-prop til
placeholder-views). Server-kontrakten er et **eksplicit krav** til Memory- og
Scheduling-specs — den er ikke "dækket" før serveren håndhæver den.

## Hvad der genbruges (og hvad der SKAL ændres)

streamClient.ts og api.ts er solide fundamenter, men de er IKKE 1:1 uændrede —
Codex-review 2026-06-11 afslørede tre transport-realiteter der kræver ændringer.
Ærlig status:

- **`lib/streamClient.ts`** (502 linjer) — SSE-parsing, typed errors, backoff,
  size-caps **genbruges**. MEN tre ændringer kræves (se "Transport-realiteter"
  nedenfor): (1) skeln watchdog-abort fra user-abort, (2) eksponér aktivt
  `run_id` fra message_start, (3) cancel-hook der POST'er server-cancel. Plus:
  blind auto-reconnect-re-POST **deaktiveres for chat** (duplikerer user-message).
- **`lib/api.ts`** — REST-wrapper (timeout, auto-retry, typed errors)
  **genbruges**. MEN `ChatMessage.content` ændres `string` → `ContentBlock[]`, og
  `getSession()` får en `stringToBlocks()`-normalisering (se Datamodel).
- **Backend `/chat/stream/v2`** — Anthropic-style translator, deployed. MEN den
  har **intet `id:`-felt** på events og **appender user-message ved hver POST** —
  derfor kan klienten ikke "resume" et run; den kan kun bevare partial lokalt.

## Transport-realiteter (Codex-review 2026-06-11) — låst FØR implementering

Disse tre realiteter afgør hvad der faktisk kan bygges. Specs må ikke kode adfærd
transporten ikke understøtter.

### R1 — Ingen ægte resume; kun lokal partial-bevarelse

v2-events har intet `id:`-felt (`sse_v2_events.py:30`), og hver
`POST /chat/stream/v2` **appender user-beskeden + starter et nyt run**
(`chat_stream_v2.py:55`). Derfor:

- **Blind auto-reconnect (re-POST samme besked) er FORBUDT i chat** — det
  duplikerer user-message og laver et nyt run. streamClient's nuværende
  reconnect-loop deaktiveres/omgås for chat-lanen.
- Ved brudt stream: **bevar partial lokalt**, sæt `status='interrupted'`, og vis
  "forbindelse afbrudt — [genoptag]". "Genoptag" er en **ny tur** (ærligt: den
  re-sender ikke; den fortsætter samtalen), ikke et resume af det døde run.
- **Ægte resume** (re-attach til in-flight run uden re-append) kræver et nyt
  server-endpoint `GET /chat/runs/{run_id}/stream` + event-`id:` til offset. Det
  er en **navngiven fremtidig udvidelse**, ikke i denne foundation. streamClient's
  reconnect-stel er klar til den når endpointet findes.

### R2 — Hang-watchdog → synlig prompt, ikke auto-reconnect

streamClient's ping-watchdog kalder i dag `abortController.abort()`
(`streamClient.ts:214`), hvilket klassificeres som `cancelled` (non-retryable) →
`onComplete`. Det er forkert for vores formål. Ændring: watchdog ved 90s emitter
en **`hung`-status** (ikke abort) → `HangPrompt` (genoptag/afbryd). Brugeren
beslutter — ingen tavs reconnect der kunne duplikere.

### R3 — Server-cancel kræver run_id + cancel-hook i streamClient

`startStream()` returnerer i dag kun en lokal abort-funktion
(`streamClient.ts:496`) uden run_id eller cancel-API. Ændring: streamClient
eksponerer aktivt `run_id` (fra `message_start.message.id`) og får en injiceret
`cancelRun(runId)` (bruger `api.ts`). `abort()` skelner nu mellem **netværks-
abort** (luk forbindelse) og **server-cancel** (POST `/chat/runs/{run_id}/cancel`
FØR lokal abort). Se "Server-cancel kontrakt".
- **Chat-mode visuelt design** — locked i
  `2026-06-10-jarvis-desk-chat-mode-design.md` (palette, layout, typografi,
  composer, asymmetriske bobler). Genbruges 1:1.

## Filstruktur

```
src/
  App.tsx                    ~40 linjer: wirer providers + aktiv view
  main.tsx                   Electron entry (uændret)

  contexts/                  ── delt state (React Context) ──
    SettingsContext.tsx      apiBaseUrl, token, tema, defaults; Electron-config
    SessionContext.tsx       session-liste, aktiv session, beskeder, CRUD
    StreamContext.tsx        aktiv stream-state, liveness-maskine, abort

  hooks/                     ── forbrugbar logik ──
    useSettings.ts
    useSessions.ts
    useStream.ts
    useTheme.ts              forberedt til lys/mørk senere

  views/                     ── én pr. flade, rene komponenter ──
    ChatView.tsx             mode-slider (denne spec: skelet + Chat virker)
    CoworkView.tsx           mode-slider — placeholder, egen spec
    CodeView.tsx             mode-slider — placeholder, egen spec
    MemoryView.tsx           sekundær nav — rolle-skopet, placeholder, egen spec
    SchedulingView.tsx       sekundær nav — rolle-skopet, placeholder, egen spec
    SettingsView.tsx         sekundær nav — server, token, tema, defaults
    SetupScreen.tsx          første-gangs: server-URL + token

  components/
    shell/
      Sidebar.tsx            app-navn, mode-slider, sessions, sekundær-nav, bruger-fod
      ModeSlider.tsx         Chat|Cowork|Code pille-segment (arbejds-modes)
      SecondaryNav.tsx       Memory|Scheduling|Settings ikoner (sidebar-fod)
      StatusBar.tsx          model · cache · cost · tid
      Composer.tsx           input + kontekst-menu + model/think-pills + send
    rich/                    ── density-aware rendering-bibliotek ──
      MarkdownRenderer.tsx   react-markdown + remark-gfm, custom renderers,
                             streaming-buffer
      CodeBlock.tsx          Shiki + kopiér-knap + sprog-label
      ToolCard.tsx           density: compact|full
      ApprovalCard.tsx       interaktiv approve/deny
      MermaidBlock.tsx       lazy-loaded
      MathBlock.tsx          lazy-loaded KaTeX
      Table.tsx              sheets-stil, sticky header
      ImageBlock.tsx         Jarvis' vision/ComfyUI-output + bruger-vedhæft
      MessageRow.tsx         bruger/Jarvis boble-layout (locked design)
    feedback/
      LivenessIndicator.tsx  "arbejder — 0:42" (density-aware)
      InterruptedBanner.tsx  "forbindelse afbrudt — [genoptag]" (R1, ny tur)
      ErrorBanner.tsx        typed StreamError → dansk besked
      HangPrompt.tsx         "svarer ikke — genoptag / afbryd" (R2)

  lib/                       ── genbruges med målrettede ændringer (R1-R3) ──
    streamClient.ts          + run_id-eksponering, cancel-hook, watchdog→hung
    api.ts                   + ChatMessage.content→ContentBlock[] + normalisering
    sseProtocol.ts           NY: rene v2 event-typer (udtrukket fra streamClient)

  styles/
    tokens.css               locked palette
    app.css                  layout
```

**Princip:** `contexts/` ejer state, `hooks/` eksponerer den, `views/` komponerer,
`components/rich/` er det density-aware bibliotek alle modes deler. Ingen view
kender en anden views internals — de taler kun via contexts.

## State-laget

Tre contexts, hver eksponeret via én hook. Views rører aldrig context direkte.

### SettingsContext → useSettings()

```ts
{
  settings: {
    apiBaseUrl: string
    authToken: string | null
    theme: 'dark'              // 'light' forberedt, ikke bygget
    defaultModel: string
    defaultThinking: 'think' | 'fast'
    trustDefault: 'ask' | 'trust'
  } | null
  auth: {
    userId: string
    displayName: string
    role: 'owner' | 'member' | 'guest'   // driver rolle-skopering
  } | null
  isConfigured: boolean        // false → vis SetupScreen
  update(partial): Promise<void>   // skriver til Electron-config
}
```

Loader fra Electron-config ved opstart. Mangler apiBaseUrl/token →
`isConfigured=false` → App viser `SetupScreen`. Ved boot kaldes whoami
(cache-first, så offline-boot stadig kender sidste-kendte rolle) → fylder `auth`.
`role` eksponeres så rolle-følsomme flader (Memory, Scheduling) og skrive-gates
kan filtrere.

### SessionContext → useSessions()

```ts
{
  sessions: ChatSession[]
  activeId: string | null
  messages: ChatMessage[]      // for aktiv session
  loading: boolean
  select(id): void
  create(title): Promise<void>
  refresh(): Promise<void>
  appendOptimistic(msg): void  // bruger-besked vises straks
  reconcile(assistantMsg): void // erstat stream-resultat når done — se #4
}
```

**Titler er server-ejede og mutable** (server auto-titler efter første besked).
Klienten fryser aldrig en titel; `refresh()` henter opdaterede titler. (Søm for
green-12.)

### StreamContext → useStream()

```ts
{
  status: 'idle'|'working'|'interrupted'|'hung'|'error'|'done'  // R1/R2: ingen 'reconnecting'
  blocks: ContentBlock[]       // text/thinking/tool_use/image, indekseret
  activeRunId: string | null   // fra message_start.message.id — bruges af abort() (R3)
  elapsedMs: number
  lastEventAt: number
  error: StreamError | null
  needsAttention: boolean      // true når working/hung/interrupted og vindue ude af fokus
  send(message, opts): void
  abort(): void                       // server-cancel (POST /chat/runs/{activeRunId}/cancel) + lokal — R3
  continueFromPartial(): void         // NY tur der fortsætter samtalen — IKKE resume af dødt run (R1)
}
```

### Hvorfor tre adskilte contexts

De har forskellige livscyklusser. Settings ændres sjældent (config). Sessions
ændres ved navigation. Stream ændres mange gange i sekundet under streaming. At
holde dem adskilt betyder at en stream-delta ikke re-rendrer sidebar, og et
session-skift ikke nulstiller settings. Hver kan testes isoleret med mock-provider.

### Grænsen aktiv-stream vs afsluttede-beskeder

`StreamContext` holder den *aktive* streams råtilstand (blocks + liveness). Når
en stream når `done`, flushes det færdige resultat ned i `SessionContext.messages`
via `reconcile()`, og StreamContext nulstilles til `idle`. Transcript =
afsluttede beskeder (SessionContext); kun den nederste igangværende besked læser
fra StreamContext. Det gør at en lang samtale ikke re-rendrer alt ved hver delta.

## Datamodel

```ts
interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system' | 'approval_request'
  content: ContentBlock[]      // ikke bare string — understøtter image/tool_use
  created_at: string
  parent_id: string | null     // branch-søm for green-9; null = lineær
}

type ContentBlock =
  | { type: 'text'; text: string }
  | { type: 'thinking'; thinking: string }
  | { type: 'tool_use'; id: string; name: string; input: Record<string, unknown>;
      status?: 'running'|'done'|'error'; result?: string }
  | { type: 'image'; src: string; alt?: string }
```

**`parent_id`** sidder i modellen fra dag 1 (branch-søm, green-9). Branch/edit-UI
hører til Chat-spec; datamodellen er klar nu, så ingen migration senere.

**`content` er ContentBlock[]**, ikke string — så billede-output (green-11) og
tool_use er førsteklasses content-typer fra start, matchende Anthropic-protokollen.

**To kilder, samme model — normalisering:**
- **Streamede beskeder** kommer som native `ContentBlock[]` fra v2-protokollen.
- **Loadede beskeder** (fra `GET /chat/sessions/{id}`) returnerer serveren som
  `content: string` (markdown). Disse normaliseres ved load til ét tekst-block:
  `[{ type: 'text', text: serverContent }]`. `MarkdownRenderer` udleder så
  code/tabel/mermaid/math/billede fra selve markdown-strengen — så historiske
  beskeder rendres med fuld rich-formatering uden at serveren skal ændre format.
- Historiske tool-resultater er separate `role: 'tool'` rækker server-side; i
  Chat-mode filtreres de fra transcript (vises inline i density-laget senere).
  Denne spec normaliserer kun assistant/user-tekst; tool-row-merge hører til
  Chat-spec.

Dvs. `api.ts::ChatMessage.content` ændres fra `string` til `ContentBlock[]`, og
`getSession()` får en normaliserings-funktion `stringToBlocks(content)`.

## Data-flow

```
Composer.send(text)
  → SessionContext.appendOptimistic(userMsg)   // vises straks
  → StreamContext.send(text)
     → useStream: startStream() fra streamClient
     → v2-events → reducer → blocks[] + status
        message_start    → status='working', start elapsed-timer
        content_block_*   → opdatér blocks[index] (text/thinking/tool_use/image)
        system_event      → approval_request → ApprovalCard;
                            working_step → opdatér tool_use-block status
        ping / enhver event → nulstil hang-watchdog (90s)
        message_delta     → akkumulér usage (cost/cache til statusbar)
        message_stop      → status='done'
     → on done: SessionContext.reconcile(blocks → assistantMsg)
        StreamContext → 'idle'
```

Reduceren er en **ren funktion** `(state, v2event) → state` — al stream-logik
samlet ét sted, fuldt unit-testbar uden netværk.

### Reconcile-state-maskine (eksplicit — P2 Codex)

Hver besked har en `clientStatus` der styrer hvad reconcile gør. En assistant-
besked får et **temp client-id** under streaming; serverens persisterede
message-id matches via `(session_id, role, rækkefølge)` + indhold, ikke via et
delt id (serveren tildeler sit eget). Tilstande:

| clientStatus | Hvornår | Reconcile-adfærd |
|--------------|---------|------------------|
| `optimistic_user` | bruger-besked vist straks | erstattes når server-load bekræfter samme indhold; ellers bevares |
| `streaming_assistant` | mens stream kører (temp id) | StreamContext ejer; ikke i SessionContext endnu |
| `server_confirmed` | server-load matcher stream-resultat | brug server-id; stream-blocks beholdes som indhold |
| `server_missing_keep_stream` | `done`, men server-load mangler beskeden endnu (dagens race) | **behold stream-blocks**; re-poll/næste load reconcilerer; blank-load ALDRIG |
| `server_conflict` | server persisterede *andet* end stream viste (fx `"Generation cancelled."` ved cancel, `visible_runs.py:1024`, eller sanitized fallback) | **server vinder**; erstat stream-blocks med server-indhold (serveren er sandheden om hvad der blev gemt) |

Nøgle-distinktion: ved **normal done** er stream sandhed til server bekræfter
(beskytter mod race). Ved **cancel/sanitering** er server sandhed (den gemte
korrigerede tekst vinder). `server_conflict` er derfor ikke en fejl — det er
forventet ved cancel og fallback.

## Liveness-state-maskinen (én kilde, density-agnostisk)

```
idle → working → done → idle
         │
         ├─ (forbindelse tabt / stream slutter uden message_stop) → interrupted
         │     partial blocks BEVARES lokalt (R1). INGEN auto-reconnect-re-POST
         │     (ville duplikere user-message). Vis "afbrudt — [genoptag]".
         │     → genoptag() : NY tur (fortsætter samtalen), ikke resume af dødt run
         │     → abort()    : server-cancel + idle
         │
         ├─ (ingen event 90s) → hung           (R2: watchdog → synlig prompt)
         │     → genoptag() : ny tur
         │     → abort()    : POST /chat/runs/{run_id}/cancel (R3) → idle
         │
         └─ (typed StreamError) → error → ErrorBanner (dansk userMessage())
```

> R1/R2/R3 (se Transport-realiteter): `interrupted` og `hung` fører til en
> **synlig brugerbeslutning**, aldrig tavs reconnect. "Genoptag" er en ny tur —
> ægte server-resume er en navngiven fremtidig udvidelse.

`status ∈ {working, hung, interrupted}` + vindue ude af fokus → `needsAttention=true` →
app-laget viser dock-badge + notifikation (#5). Særligt vigtigt ved
`approval_request` — Jarvis venter på dig.

Chat-mode læser maskinen som en rolig liveness-pille + diskret InterruptedBanner
ved afbrydelse. Code-mode læser samme maskine som en fuld status-linje med
elapsed/tokens/forbindelse. **Samme `status`, to renderings.**

## De 8 "glemte" ting (folder ind i fundamentet)

Indsigter fra produktions-chat/agentic-apps. Alle med i denne spec.

### 🔴 Fundament

1. **Streaming-markdown der ikke flasher i stykker.** `MarkdownRenderer` buffrer
   ufærdige code-fences (` ``` ` uden lukning) og inline-marks (`**` uden anden
   `**`) til de lukker, så rendering ikke blinker mellem brækket/helt layout ved
   hver delta.
2. **Partial-besked overlever stream-død (lokalt).** Blocks der allerede er
   streamet smides ALDRIG væk ved forbindelsestab; de markeres `interrupted` og
   vises med en "genoptag"-mulighed. **Ikke** ægte resume (R1) — "genoptag" er en
   ny tur. Ingen blind re-POST (duplikerer user-message).
3. **Rigtig STOP, ikke client-abort.** `abort()` POST'er `/chat/runs/{run_id}/
   cancel` (run_id fra message_start) FØR lokal abort, så Jarvis holder op med at
   generere server-side. Kræver streamClient-ændring R3.
4. **"Besked forsvinder"-race (dagens bug) — eksplicit reconcile-state-maskine.**
   Se "Reconcile-state-maskine" nedenfor. Klienten blank-loader ALDRIG umiddelbart
   efter `done`.
5. **Notifikation når vinduet ikke er i fokus.** `needsAttention` driver
   dock-badge + diskret OS-notifikation, særligt ved approval.

### 🟡 Praktisk (shell)

6. **Vindue-state + composer min-height.** Husk vindue-størrelse/position; fix
   composer min-height-bug; composer-tekst overlever fejlet send.
7. **Scroll-styring.** Auto-scroll kun nær bunden; "spring til bund"-knap når
   scrollet op; bevar scroll-position ved session-skift.
8. **Kopiér = rå markdown** (ikke renderet HTML); code-blocks kopierer uden
   linjenumre; thinking-blokke foldet sammen som default ("tænkte 3s", klik=åbn).

## Søm/constraints for udskudte features (green 9-12)

| # | Feature | Behandling i denne spec |
|---|---------|------------------------|
| 9 | Branch/edit-resend | **Søm:** `parent_id` i datamodel. UI → Chat-spec |
| 10 | Virtualisering | **Constraint:** transcript-container bager ingen "mål alt"-layout der blokerer windowing. Ingen kode nu |
| 11 | Billede-output | **Fuldt:** `ImageBlock` + `image` content-block fra dag 1 |
| 12 | Session-titel | **Fuldt:** titler server-ejede/mutable, `refresh()` håndterer |

## Rich-rendering biblioteket

`MarkdownRenderer` er indgangen — parser tekst og dispatcher til specialiserede
komponenter via custom react-markdown renderers:

| Input | Komponent | Note |
|-------|-----------|------|
| ` ```kode``` ` | CodeBlock | Shiki, kopiér-knap, sprog-label |
| ` ```mermaid``` ` | MermaidBlock | lazy-loaded |
| `$$math$$` | MathBlock | lazy-loaded KaTeX |
| `\| tabel \|` | Table | sheets-stil, sticky header |
| `![img]` / image-block | ImageBlock | vision/ComfyUI-output |

`ToolCard`, `ApprovalCard`, `LivenessIndicator` tager `density: 'compact'|'full'`.
**Hver rich-komponent er en ren funktion af (content, density)** — ingen egen
netværk/state, så de test-renderes isoleret med fixture-data.

### Library-strategi

- **Shiki** til code (samme engine som VS Code — vigtigt i Code-mode).
- **mermaid + katex lazy-loaded** første gang de bruges → normal chat render
  lyn-hurtigt, RAM spares når de ikke bruges.
- **react-markdown + remark-gfm** til markdown + tabeller (allerede installeret).

## App-shell flow

```
App.tsx
  <SettingsProvider>
    isConfigured === false → <SetupScreen />
    isConfigured === true  →
      <SessionProvider>
        <StreamProvider>
          <Shell>
            <Sidebar/> (ModeSlider, sessions, SecondaryNav, bruger-fod)
            <main>
              // mode-slider (arbejds-modes)
              surface === 'chat'       → <ChatView/>
              surface === 'cowork'     → <CoworkView/>     (placeholder)
              surface === 'code'       → <CodeView/>       (placeholder)
              // sekundær nav (opslags-flader, rolle-skopet)
              surface === 'memory'     → <MemoryView role={auth.role}/>  (placeholder)
              surface === 'scheduling' → <SchedulingView role={auth.role}/> (placeholder)
              surface === 'settings'   → <SettingsView/>
            </main>
            <StatusBar/>
          </Shell>
        </StreamProvider>
      </SessionProvider>
```

## Fejlhåndtering

- Alle netværks/stream-fejl er `StreamError` med typed `category` og dansk
  `userMessage()`. Vist via `ErrorBanner`.
- Server unåelig ved opstart → tydelig "kan ikke nå Jarvis — [prøv igen]", ikke
  brækket tom tilstand. Skelnes fra `isConfigured=false` (SetupScreen).
- Stream-hang (90s ingen event) → `HangPrompt` med fortsæt/afbryd.
- Send-fejl mister aldrig composer-tekst.

### Server-cancel kontrakt (rigtig STOP, ikke client-abort)

`abort()` må stoppe Jarvis **server-side**, ikke bare lukke vores ende. Kontrakt:

- **Endpoint:** `POST /chat/runs/{run_id}/cancel` (eksisterer i
  `apps/api/jarvis_api/routes/chat.py:226`).
- **run_id ejerskab:** klienten kender `run_id` fra `message_start`-eventets
  `message.id` (fx `visible-xxx`). `StreamContext` gemmer det aktive `run_id`
  fra message_start; `abort()` POST'er til netop det run.
- **Payload:** ingen body nødvendig; run_id i path.
- **Idempotens:** kald på et allerede-afsluttet/-cancelled run er no-op og
  returnerer `{status: "cancelled"}` eller 404 (run ukendt) — begge behandles af
  klienten som "stoppet". Gentagne kald er sikre.
- **Forventet server-event:** efter cancel afslutter den aktive stream med
  `message_delta(stop_reason="cancelled")` → `message_stop` (via v2-translator),
  så `useStream` rammer `done`/`idle` rent. Hvis streamen allerede er lukket,
  forlader klienten bare på POST-svaret.
- **Rækkefølge:** `abort()` POST'er cancel FØR den lokale `abortController.abort()`,
  så serveren får signalet selv hvis vi lukker forbindelsen umiddelbart efter.

## Test-strategi

- **Rich-komponenter:** render-tests med fixtures (markdown→output, ToolCard
  compact vs full, streaming-buffer med ufærdig fence, ImageBlock).
- **Reducer:** ren funktion `(state, v2event) → state` — unit-tests for hele
  event-sekvenser inkl. afbrudt-genoptag, hang, approval midt-i.
- **Hooks:** mock-providers (useStream med fake event-stream).
- **streamClient:** findes; tilføj tests for de nye R1-R3-grene (watchdog→hung,
  run_id-eksponering, cancel-hook, ingen blind re-POST).
- **Stack:** Vitest (matcher Vite). Ingen E2E i denne spec — kommer når Chat-mode
  er fuld.

## Eksplicit IKKE i denne spec

- Cowork/Code/Memory/Scheduling indhold (placeholders kun) → egne specs
- Chat-mode interaktions-polish (branch/edit-UI, billede-vedhæft-flow) → Chat-spec
- Observability-flader (Mind/Dashboard/Dispatches/Trading/Channels) → Mission Control, ikke jarvis-desk
- Lys-tema (forberedt i tokens, ikke bygget)
- Virtualisering (constraint kun)
- E2E-tests

Foundationen leverer dog: rolle i auth-context, SecondaryNav-stel, og
placeholder-views med `role`-prop — så de senere mode/flade-specs kan udfyldes
uden at røre fundamentet.

## Næste skridt

1. Bjørn reviewer denne spec
2. writing-plans → bite-sized implementerings-plan
3. Subagent-driven eksekvering med review mellem tasks
