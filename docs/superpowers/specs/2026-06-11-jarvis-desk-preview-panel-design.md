# jarvis-desk: Preview-panel + Kontekst-ring — Design Spec

**Dato:** 2026-06-11
**Status:** Godkendt (v1-scope), udbygning deferred til "fuldt funktionel app"
**Relaterer til:** [foundation-design](2026-06-11-jarvis-desk-foundation-design.md), [chat-mode-design](2026-06-10-jarvis-desk-chat-mode-design.md)

## Formål

Et **preview/canvas-panel** der folder ud i højre side af den aktive view, så
indhold der er bedre at se "ved siden af" (specs, lange kode-blokke, dokumenter,
interne filer) kan åbnes uden at drukne i chat-strømmen — som Claude artifacts /
Codex preview. Plus en **kontekst-fill ring** der viser hvor fuldt Jarvis'
kontekst-vindue er (blå→gul→rød + compaction-signal).

Panelet er en **cross-mode primitiv**: samme mekanisme i Chat, Cowork og Code —
kun trigger-tæthed og default-bredde varierer pr. mode (samme princip som
tool-rendering: delt mekanisme, mode bestemmer densitet).

## Ikke-mål (v1)

- **Ingen auto-åbning** — store artifacts auto-åbner ikke; brugeren klikker en
  affordance. (Kan revurderes senere.)
- **Ingen Jarvis-konvention** endnu — Jarvis lærer ikke at sætte artifact-markører
  i v1. Klient-auto-detektion står alene. Konventionen lægges ovenpå senere.
- **Mermaid/HTML-preview** er specificeret men bygges sidst (sikkerhedsgates).
- **Kontekst-ringen** er specificeret men gated bag en backend-kontrakt
  (`context`-event i streamen) — klient-delen bygges når event'et findes.

## Arkitektur

### Del A — Preview-panel (klient-side, buildable nu)

**`PanelContext`** (ny React context, mode-agnostisk) holder:
```ts
interface PanelState {
  open: boolean
  width: number            // px, gemmes per-install i config
  artifact: Artifact | null
}
interface Artifact {
  kind: 'markdown' | 'code' | 'file'   // (v2: 'mermaid' | 'html')
  title: string
  language?: string        // for kode
  content?: string         // inline (markdown/kode)
  filePath?: string        // for 'file' — hentes via endpoint
}
```
Reducer-actions: `open(artifact)`, `close()`, `resize(width)`, `replace(artifact)`.
`open` på et nyt artifact mens panelet er åbent erstatter indholdet (ingen stak i v1).

**`ArtifactPanel`** lever i app-shellen til højre for den aktive view (fælles for
alle modes). Egen header: type-ikon + titel + kopiér + luk. Indhold renderes efter
`kind` via det eksisterende rich-bibliotek.

**Layout — trækbar split:** den aktive view (chat-kolonne) og `ArtifactPanel`
sidder i en horisontal split med et trækbart håndtag. Bredden clamps til
`[320px, 70% af vinduet]` og gemmes i config (`panelWidth`). Luk → chatten får
fuld bredde. Default-bredde pr. mode: Chat ~45%, Code ~55% (Code arbejder mere i
panelet). Under en min-vinduesbredde (~900px) falder panelet tilbage til overlay
(drawer) i stedet for split, så chatten ikke kvæles.

### Del B — Trigger (klient-auto-detektion)

Ren funktion `detectArtifacts(blocks: ContentBlock[]): ArtifactRef[]` kører over
Jarvis' **færdige** besked-blokke (ikke under streaming) og markerer panel-værdigt
indhold:

| Type | Regel |
|------|-------|
| Kode | `tool_use`/text-kodeblok ≥ 15 linjer → affordance |
| Markdown-dok | text-blok ≥ 40 linjer **og** ≥ 2 markdown-headers → affordance |
| Intern fil | regex matcher container-sti (`docs/…`, `workspace/…`, `core/…`, `apps/…`, abs. sti under whitelist-rødder) → klikbart link |

Affordance = en lille **"Åbn ↗"-knap** på blokken i `MessageRow` (synlig ved hover,
som besked-actions). Interne fil-referencer bliver klikbare links inline. Klik →
`panel.open(artifact)`. Detektion er ren og testbar isoleret.

### Del C — Indholds-renderere (genbrug)

- **markdown** → eksisterende `BlocksRenderer`/markdown-pipeline (Shiki, remark-gfm,
  sanitering) i fuld panel-højde.
- **code** → eksisterende `CodeBlock`, fuld højde + kopi.
- **file** → henter via nyt endpoint (Del E), vælger markdown- vs kode-rendering
  efter filendelse.

### Del D — Intern fil-endpoint (lille backend)

**`GET /chat/file?path=<rel-or-abs>`** → `{ path, content, language }`.
- **Path-jail:** kun stier under whitelist-rødder (`docs/`, `workspace/`,
  `core/`, `apps/`, `scripts/` + workspace-dir for brugeren). Afvis `..`,
  symlinks ud af jail, og alt udenfor — samme sikkerhedsmønster som
  `operator_read_file`/`dispatch_to_claude_code` path-jail.
- **Rolle-skopering:** member ser kun whitelisted dokument-stier; owner ser fuldt.
  Håndhæves server-side (jf. foundation rolle-kontrakt).
- Returnerer 403 udenfor jail, 404 hvis ikke-eksisterende.

### Del E — Kontekst-ring (backend-gated)

**Backend-kontrakt:** v2-streamen får et nyt event:
```
event: system_event
data: {"type":"system_event","kind":"context",
       "payload":{"used_tokens":N,"limit":M,"compacted":false}}
```
Udfyldt fra `estimate_messages_tokens(messages)` (used) +
`context_run_compact_threshold_tokens` (limit), og `compacted=true` i det event
hvor `_maybe_compact_agentic_messages` rent faktisk komprimerede. Sendes mindst
ved `message_start` og igen hvis compaction sker midt i et run.

**Klient:** lille SVG-ring i chat-headeren, til venstre for forbindelses-pillen.
- Fyld = `used_tokens / limit`.
- Farver: **blå** <60 %, **gul** 60–85 %, **rød** >85 %.
- **Compaction-pulse:** kort animation + skift når `compacted=true` modtages.
- Tooltip: `{used} / {limit} tokens`.
- `streamReducer` får et felt `context: { usedTokens, limit, compacted } | null`;
  ringen læser det. Hvis intet `context`-event er modtaget, vises ringen ikke.

## Data-flow

```
Jarvis-svar (færdige blocks)
   → detectArtifacts()  → affordances i MessageRow
   → klik               → PanelContext.open(artifact)
   → ArtifactPanel      → renderer (markdown/code) ELLER GET /chat/file → renderer

v2-stream system_event kind=context
   → streamReducer.context
   → ContextRing (header)  → farve/pulse
```

## Filstruktur (jarvis-desk)

- `src/contexts/PanelContext.tsx` — panel-state + reducer
- `src/hooks/usePanel.ts` — hook
- `src/components/panel/ArtifactPanel.tsx` — panel-shell + header
- `src/components/panel/SplitLayout.tsx` — trækbar split (+ overlay-fallback)
- `src/lib/detectArtifacts.ts` — ren detektions-funktion
- `src/lib/api.ts` — `getFile(config, path)` mod `GET /chat/file`
- `src/components/shell/ContextRing.tsx` — SVG-ring
- `src/lib/streamReducer.ts` — `context`-felt + `system_event kind=context`-case
- `src/components/rich/MessageRow.tsx` — "Åbn ↗"-affordance + fil-links
- Backend: `GET /chat/file` route + `context`-event i v2-stream-generator

## Test

Rene enheder, Vitest (samme mønster som foundationen):
- `detectArtifacts` — blok→artifact-klassificering (kode-tærskel, header-krav,
  fil-sti-regex, negative cases)
- panel-reducer — open/close/resize/replace + width-clamp
- fil-path-jail (server) — afvis `..`/udenfor-whitelist, accepter whitelisted
- `streamReducer` — `kind=context` → `context`-felt sat korrekt
- ring-farve-tærskler — token% → farve-bucket (grænseværdier 60/85)

## Rækkefølge / scope

**v1 (bygges nu):** Del A + B + C + D — panel-mekanisme, trækbar split,
auto-detektion, markdown/kode/internt-fil-link.

**Sidst i v1-spec (tungere):** mermaid/HTML-preview (lazy + sandboxed iframe +
sikkerhedsgates).

**Backend-gated, bygges når kontrakten findes:** Del E (kontekst-ring) — kræver
`context`-event i v2-streamen.

**Deferred til "fuldt funktionel app" (egen senere iteration):** Jarvis-konvention
(artifact-markører han selv sætter), artifact-historik/stak i panelet, panel i
Cowork-mode med interaktivt indhold.
