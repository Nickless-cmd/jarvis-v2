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

## Hvad der allerede er bygget og genbruges 1:1

- **`lib/streamClient.ts`** (502 linjer) — prod-grade SSE-konsument: typed errors
  (network/auth/rate_limit/server/protocol/cancelled), reconnect med exponential
  backoff, ping-watchdog (70s), abort-support, size-caps. Bliver uændret.
- **`lib/api.ts`** — REST-wrapper med timeout, auto-retry, typed errors. Uændret.
- **Backend `/chat/stream/v2`** — Anthropic-style translator, deployed.
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

  views/                     ── én pr. mode, rene komponenter ──
    ChatView.tsx             (denne spec: skelet + Chat virker)
    CoworkView.tsx           placeholder — egen spec
    CodeView.tsx             placeholder — egen spec
    SettingsView.tsx         server, token, tema, model-default, trust-default
    SetupScreen.tsx          første-gangs: server-URL + token

  components/
    shell/
      Sidebar.tsx
      ModeSlider.tsx         Chat|Cowork|Code pille-segment
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
      ReconnectBanner.tsx    "genopretter..."
      ErrorBanner.tsx        typed StreamError → dansk besked
      HangPrompt.tsx         "svarer ikke — prøv igen / afbryd"

  lib/                       ── uændret, allerede solidt ──
    streamClient.ts
    api.ts
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
  isConfigured: boolean        // false → vis SetupScreen
  update(partial): Promise<void>   // skriver til Electron-config
}
```

Loader fra Electron-config ved opstart. Mangler apiBaseUrl/token →
`isConfigured=false` → App viser `SetupScreen` i stedet for shell.

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
  status: 'idle'|'working'|'reconnecting'|'hung'|'error'|'done'
  blocks: ContentBlock[]       // text/thinking/tool_use/image, indekseret
  elapsedMs: number
  lastEventAt: number
  reconnectAttempt: number
  error: StreamError | null
  needsAttention: boolean      // true når working/hung og vindue ude af fokus
  send(message, opts): void
  abort(): void                // POST cancel til server — se #3
  retry(): void                // fortsætter partial — se #2
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

## Liveness-state-maskinen (én kilde, density-agnostisk)

```
idle → working → done → idle
         │
         ├─ (forbindelse tabt) → reconnecting → working
         │     streamClient auto-reconnect; partial blocks BEVARES (#2)
         │
         ├─ (ingen event 90s) → hung
         │     → retry()  : fortsætter fra partial (genoptager, starter ikke forfra)
         │     → abort()  : POST cancel til server (#3) → idle
         │
         └─ (typed StreamError) → error → ErrorBanner (dansk userMessage())
```

`status ∈ {working, hung}` + vindue ude af fokus → `needsAttention=true` →
app-laget viser dock-badge + notifikation (#5). Særligt vigtigt ved
`approval_request` — Jarvis venter på dig.

Chat-mode læser maskinen som en rolig liveness-pille + diskret reconnect-banner.
Code-mode læser samme maskine som en fuld status-linje med elapsed/tokens/
forbindelse. **Samme `status`, to renderings.**

## De 8 "glemte" ting (folder ind i fundamentet)

Indsigter fra produktions-chat/agentic-apps. Alle med i denne spec.

### 🔴 Fundament

1. **Streaming-markdown der ikke flasher i stykker.** `MarkdownRenderer` buffrer
   ufærdige code-fences (` ``` ` uden lukning) og inline-marks (`**` uden anden
   `**`) til de lukker, så rendering ikke blinker mellem brækket/helt layout ved
   hver delta.
2. **Partial-besked overlever stream-død.** Blocks der allerede er streamet smides
   ALDRIG væk ved forbindelsestab. `retry()` genoptager fra partial.
3. **Rigtig STOP, ikke client-abort.** `abort()` POST'er cancel til serverens
   cancel-endpoint, så Jarvis holder op med at generere server-side (ikke bare
   lukker vores ende mens han brænder tokens).
4. **"Besked forsvinder"-race (dagens bug).** `reconcile()` bruger stream-blocks
   som sandhed indtil server bekræfter via efterfølgende session-load. Klienten
   blank-loader ALDRIG en session umiddelbart efter `done`.
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
            <Sidebar/> (ModeSlider, sessions, bruger-foot)
            <main>
              mode === 'chat'   → <ChatView/>
              mode === 'cowork' → <CoworkView/>   (placeholder)
              mode === 'code'   → <CodeView/>     (placeholder)
              mode === 'settings' → <SettingsView/>
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

## Test-strategi

- **Rich-komponenter:** render-tests med fixtures (markdown→output, ToolCard
  compact vs full, streaming-buffer med ufærdig fence, ImageBlock).
- **Reducer:** ren funktion `(state, v2event) → state` — unit-tests for hele
  event-sekvenser inkl. afbrudt-genoptag, hang, approval midt-i.
- **Hooks:** mock-providers (useStream med fake event-stream).
- **streamClient:** findes; tilføj tests for reconnect-grene hvis de mangler.
- **Stack:** Vitest (matcher Vite). Ingen E2E i denne spec — kommer når Chat-mode
  er fuld.

## Eksplicit IKKE i denne spec

- Cowork-mode + Code-mode indhold (placeholders kun) → egne specs
- Chat-mode interaktions-polish (branch/edit-UI, billede-vedhæft-flow) → Chat-spec
- Lys-tema (forberedt i tokens, ikke bygget)
- Virtualisering (constraint kun)
- E2E-tests

## Næste skridt

1. Bjørn reviewer denne spec
2. writing-plans → bite-sized implementerings-plan
3. Subagent-driven eksekvering med review mellem tasks
```
