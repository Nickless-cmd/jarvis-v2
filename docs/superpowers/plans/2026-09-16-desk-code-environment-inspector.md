# Desk Code Environment Inspector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gør Desk Code-visningens Miljø til en handlingsklar workspace-oversigt med faktiske kilder samt klikbare agent- og tool-detaljer i ét fælles inspector-panel.

**Architecture:** Bevar samtalens foldede `ContentBlock[]` som autoritet og udled memoiseret `ToolEvidence`, `SourceEvidence` og `AgentReference` uden at kassere ID eller resultat. Generaliser det eksisterende artifact-panel til en typed inspector, og genbrug Agent Pool-runtime/API i en delt agent-inspector med composer. Miljø-panelet er fortsat en kompakt oversigt; alle tunge detaljer hentes eller rendres først ved klik.

**Tech Stack:** React 19, TypeScript 5.5, Vitest, Testing Library, Lucide React, Vite/Electron, eksisterende FastAPI `/mc/agents/*`-API.

**Spec:** `docs/superpowers/specs/2026-09-16-desk-code-environment-inspector-design.md`

## Global Constraints

- Workspace-headerens første række er `Ændringer +xx -xx`; tilføjelser er grønne og sletninger røde, men fortegn og tekst bærer også betydningen.
- Kilder bruger samme URL-regler som `lib/kilder.ts`; et rækkeklik åbner inspector, og kun `Åbn kilde` åbner URL'en eksternt.
- Der findes kun ét højre inspector-panel for artifacts, agenter, kilder og tools.
- En Agent Pool-composer må kun åbnes for et autoritativt `agent_id`; der må aldrig matches på tool-navn, måltekst eller senest oprettede agent.
- `explore`, `spawn_agent_task` og `quick_council_check` leverer top-level `agent_id`; `dispatch_code_mode_task` leverer `spawned[].agent_id`. `task`, council-sessioner og Claude-dispatch behandles som tools, medmindre deres konkrete resultat indeholder et Agent Pool-ID.
- Skjult chain-of-thought må ikke vises.
- Agent polling er lazy, stopper ved skjult panel/unmount og kører kun videre for aktive agentstatusser.
- Den 3.293 linjer lange `styles/app.css` må ikke udvides. Miljø-stil udtrækkes først efter Boy Scout-reglen, og al ny inspector-stil placeres i en fokuseret fil.
- Ingen nye frontendafhængigheder.
- Kør kun berørte Desk-tests, TypeScript/build og målrettet visuel kontrol; kør ikke hele repository-test-suiten.
- Alle commits oprettes med `scripts/commit_with_attribution.py`, og kun taskens filer stages.
- Alle testkommandoer køres fra `apps/jarvis-desk`; alle git- og commitkommandoer køres fra repository-roden `/media/projects/jarvis-v2`.

## File Map

**Create**

- `apps/jarvis-desk/src/styles/environment-inspector.css` - al Miljø- og inspector-stil.
- `apps/jarvis-desk/src/lib/environmentEvidence.ts` - rene typer og parsere for tools, kilder og agentreferencer.
- `apps/jarvis-desk/src/lib/environmentEvidence.test.ts` - parser-, provenance- og deduplikeringstests.
- `apps/jarvis-desk/src/lib/inspectorTargets.ts` - diskrimineret `InspectorTarget`-union.
- `apps/jarvis-desk/src/components/panel/InspectorPanel.tsx` - fælles panel-shell og target-router.
- `apps/jarvis-desk/src/components/panel/InspectorPanel.test.tsx` - routing, tilbage-navigation og artifact-regression.
- `apps/jarvis-desk/src/components/panel/SourceInspector.tsx` - kildeprovenance og eksplicit ekstern åbning.
- `apps/jarvis-desk/src/components/panel/ToolInspector.tsx` - struktureret tool-input/resultat.
- `apps/jarvis-desk/src/components/panel/EvidenceInspectors.test.tsx` - source/tool-adfærd.
- `apps/jarvis-desk/src/components/panel/AgentInspector.tsx` - agentdetalje, polling og composer.
- `apps/jarvis-desk/src/components/panel/AgentInspector.test.tsx` - lazy fetch, polling, send og fejltilstande.

**Modify**

- `apps/jarvis-desk/src/styles/app.css` - fjern kun den eksisterende sammenhængende `.env-*`-sektion.
- `apps/jarvis-desk/src/App.tsx` - importér ny CSS og render `InspectorPanel` i `ShellWithPanel`.
- `apps/jarvis-desk/src/lib/kilder.ts` - del URL-scanningen med provenance-parseren uden at ændre chatview-kontrakten.
- `apps/jarvis-desk/src/lib/panelReducer.ts` - gem typed target samt ét previous target.
- `apps/jarvis-desk/src/lib/panelReducer.test.ts` - reducerens target- og back-adfærd.
- `apps/jarvis-desk/src/contexts/PanelContext.tsx` - eksponér `target`, `openTarget`, `openArtifact` og `back` med kompatibel `open_`-alias.
- `apps/jarvis-desk/src/contexts/PanelContext.test.tsx` - context-kontrakten.
- `apps/jarvis-desk/src/components/panel/ArtifactPanel.tsx` - eksportér artifact-body, så fælles shell ikke nestes.
- `apps/jarvis-desk/src/components/panel/ArtifactPanel.test.tsx` - eksisterende artifact-adfærd gennem ny shell.
- `apps/jarvis-desk/src/lib/agentPoolApi.ts` - typed detail-kald til `/mc/agents/{agent_id}`.
- `apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.tsx` - genbrug delt agent-inspector i den eksisterende detaljeoverlay.
- `apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.test.tsx` - detail-genbrug uden eager fetch.
- `apps/jarvis-desk/src/components/code/EnvironmentPanel.tsx` - nyt workspace-layout og klikbare evidensrækker.
- `apps/jarvis-desk/src/components/code/EnvironmentPanel.test.tsx` - workspace, kilder og tools.
- `apps/jarvis-desk/src/components/code/EnvironmentPanel.agents.test.tsx` - autoritativ agentnavigation.
- `apps/jarvis-desk/src/lib/api.ts` - type de allerede returnerede git-felter `repo`, `host` og `link`.
- `apps/jarvis-desk/src/views/CodeView.tsx` - udled evidens fra historik/liveblokke og åbn inspector-targets.
- `apps/jarvis-desk/src/views/CodeView.test.tsx` - integration og tilbage til Miljø.

---

### Task 1: Extract Environment Styling From Oversized Stylesheet

**Files:**
- Create: `apps/jarvis-desk/src/styles/environment-inspector.css`
- Modify: `apps/jarvis-desk/src/styles/app.css:2515-2635`
- Modify: `apps/jarvis-desk/src/App.tsx:36-37`
- Test: `apps/jarvis-desk/src/styles/tokens.test.ts`
- Test: `apps/jarvis-desk/src/components/code/EnvironmentPanel.test.tsx`

**Interfaces:**
- Consumes: eksisterende `.env-*`, `.git-add` og `.git-del` selectors.
- Produces: `environment-inspector.css`, importeret efter `app.css`, med identisk computed styling før funktionsændringer.

- [ ] **Step 1: Add a source-location regression test**

Tilføj i `tokens.test.ts` en test, der læser begge stylesheets og sikrer, at Miljø-reglerne kun ligger i den nye fil:

```ts
it('holder miljø- og inspector-stil ude af den store app.css', () => {
  const miljø = læs('environment-inspector.css')
  expect(app).not.toMatch(/\.env-panel\s*\{/)
  expect(miljø).toMatch(/\.env-panel\s*\{/)
  expect(miljø).toMatch(/\.git-add/)
  expect(miljø).toMatch(/\.git-del/)
})
```

- [ ] **Step 2: Run the focused test and verify failure**

Run from `apps/jarvis-desk`:

```bash
npm test -- src/styles/tokens.test.ts
```

Expected: FAIL because `environment-inspector.css` does not exist and `.env-panel` is still in `app.css`.

- [ ] **Step 3: Move the existing environment CSS without changing declarations**

Flyt den komplette sammenhængende `.env-*`-sektion og de miljøspecifikke `.git-add`/`.git-del`-regler til `environment-inspector.css`. Tilføj derefter importen umiddelbart efter den eksisterende import:

```ts
import './styles/app.css'
import './styles/environment-inspector.css'
```

Der må ikke tilføjes ny styling i dette trin; diffen skal være en ren extraction.

- [ ] **Step 4: Verify style and component regressions**

```bash
npm test -- src/styles/tokens.test.ts src/components/code/EnvironmentPanel.test.tsx
npm run build:renderer
```

Expected: alle tests PASS, og renderer-build fuldføres.

- [ ] **Step 5: Commit the extraction**

```bash
git add -- apps/jarvis-desk/src/styles/app.css apps/jarvis-desk/src/styles/environment-inspector.css apps/jarvis-desk/src/styles/tokens.test.ts apps/jarvis-desk/src/App.tsx
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'refactor(desk): extract environment panel styles' --path apps/jarvis-desk/src/styles/app.css --path apps/jarvis-desk/src/styles/environment-inspector.css --path apps/jarvis-desk/src/styles/tokens.test.ts --path apps/jarvis-desk/src/App.tsx
```

### Task 2: Preserve Tool, Source, and Agent Evidence

**Files:**
- Create: `apps/jarvis-desk/src/lib/environmentEvidence.ts`
- Create: `apps/jarvis-desk/src/lib/environmentEvidence.test.ts`
- Modify: `apps/jarvis-desk/src/lib/kilder.ts:1-65`
- Test: `apps/jarvis-desk/src/lib/kilder.test.ts`

**Interfaces:**
- Consumes: `ContentBlock` from `lib/sseProtocol.ts` and the existing URL filtering rules in `lib/kilder.ts`.
- Produces:

```ts
export interface ToolEvidence {
  id: string
  name: string
  input: Record<string, unknown>
  status: 'running' | 'done' | 'error'
  result?: string
}

export interface SourceEvidence extends Kilde {
  toolUseId?: string
  toolName?: string
  input?: Record<string, unknown>
  resultExcerpt?: string
  origin: 'tool_input' | 'tool_result' | 'assistant_text'
}

export interface AgentReference {
  agentId: string
  role?: string
  goal?: string
  status?: string
  dispatchToolUseId: string
}

export interface EnvironmentEvidence {
  tools: ToolEvidence[]
  sources: SourceEvidence[]
  agents: AgentReference[]
}

export function buildEnvironmentEvidence(blockGroups: readonly ContentBlock[][]): EnvironmentEvidence
export function mergeEnvironmentEvidence(...sets: readonly EnvironmentEvidence[]): EnvironmentEvidence
export function sourcesForTool(tool: ToolEvidence): SourceEvidence[]
```

- [ ] **Step 1: Write failing evidence tests**

Test mindst disse konkrete cases:

```ts
it('bevarer tool-id, input, status og resultat', () => {
  const e = buildEnvironmentEvidence([[{
    type: 'tool_use', id: 't1', name: 'web_search', input: { query: 'wled' },
    status: 'done', result: '{"url":"https://kno.wled.ge"}',
  }]])
  expect(e.tools[0]).toEqual(expect.objectContaining({ id: 't1', name: 'web_search', status: 'done' }))
})

it('binder en URL til det tool-resultat der fandt den', () => {
  const e = buildEnvironmentEvidence([[{
    type: 'tool_use', id: 't1', name: 'web_search', input: { query: 'wled' },
    status: 'done', result: 'Læs https://kno.wled.ge/basics/getting-started/',
  }]])
  expect(e.sources[0]).toMatchObject({ toolUseId: 't1', toolName: 'web_search', origin: 'tool_result' })
})

it('udleder både top-level og spawned agent-id uden at gætte', () => {
  const e = buildEnvironmentEvidence([[
    { type: 'tool_use', id: 'a', name: 'explore', input: { query: 'find parser' }, status: 'done', result: '{"agent_id":"agent-a","status":"ok"}' },
    { type: 'tool_use', id: 'b', name: 'dispatch_code_mode_task', input: { task: 'review' }, status: 'done', result: '{"spawned":[{"role":"reviewer","agent_id":"agent-b"}]}' },
  ]])
  expect(e.agents.map((a) => a.agentId)).toEqual(['agent-a', 'agent-b'])
})

it('gør ikke jarvis-code task til Agent Pool-agent uden agent_id', () => {
  const e = buildEnvironmentEvidence([[{ type: 'tool_use', id: 't', name: 'task', input: { prompt: 'se efter' }, status: 'done', result: 'færdig' }]])
  expect(e.agents).toEqual([])
})
```

Tilføj også tests for URL i input, URL i assistant-tekst, interne URL'er,
ugyldig JSON, dublet tool-ID og dublet URL. Tilføj en merge-test, hvor
liveversionen af samme tool-ID erstatter historikkens status/resultat uden at
flytte rækkefølgen, samt en `sourcesForTool`-test der kun returnerer kilder fra
det givne kald.

- [ ] **Step 2: Run tests and verify the missing module failure**

```bash
npm test -- src/lib/environmentEvidence.test.ts src/lib/kilder.test.ts
```

Expected: FAIL because `environmentEvidence.ts` and provenance APIs do not exist.

- [ ] **Step 3: Expose shared URL scanning from `kilder.ts`**

Bevar `kilderFraBlokke` og `kilderPrDomaene` uændret udadtil. Eksportér en lille struktureret helper i stedet for at kopiere regexlogikken:

```ts
export function kilderFraTekst(tekst: string): Kilde[] {
  const ud = new Map<string, Kilde>()
  saml(tekst, ud)
  return [...ud.values()]
}
```

Lad `kilderFraBlokke` bruge samme helper internt, så chatview og Miljø fortsat filtrerer identisk.

- [ ] **Step 4: Implement deterministic evidence parsing**

Implementér `buildEnvironmentEvidence` som en ren funktion:

1. Fold tool-blokke i en `Map<string, ToolEvidence>`; senere forekomst med samme ID opdaterer den tidligere uden at ændre rækkefølgen.
2. Scan input før resultat og assistant-tekst til sidst.
3. Parse tool-resultat med `JSON.parse` alene. Ved parsefejl returneres ingen agentreference; brug aldrig regex til agent-ID.
4. Accepter top-level `agent_id` samt hvert validt element i `spawned[]`.
5. Brug inputfelterne `query`, `goal`, `task`, `prompt`, `description` og `question` som frivilligt mål, men aldrig som identitet.
6. Deduplikér agenter på `agentId` og kilder på fuld URL.
7. Begræns kun `resultExcerpt` til 4.000 tegn; behold hele resultatet i `ToolEvidence`.
8. Lad `mergeEnvironmentEvidence` bruge samme ID/URL-regler og lade den seneste
   version af samme tool vinde.
9. Lad `sourcesForTool` konstruere én `tool_use`-blok og genbruge samme parser;
   der må ikke opstå en anden URL-regex i inspector-koden.

- [ ] **Step 5: Verify parsers and legacy source behavior**

```bash
npm test -- src/lib/environmentEvidence.test.ts src/lib/kilder.test.ts
```

Expected: PASS, inklusive alle eksisterende chatview-kildetests.

- [ ] **Step 6: Commit the evidence model**

```bash
git add -- apps/jarvis-desk/src/lib/environmentEvidence.ts apps/jarvis-desk/src/lib/environmentEvidence.test.ts apps/jarvis-desk/src/lib/kilder.ts apps/jarvis-desk/src/lib/kilder.test.ts
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): preserve environment evidence' --path apps/jarvis-desk/src/lib/environmentEvidence.ts --path apps/jarvis-desk/src/lib/environmentEvidence.test.ts --path apps/jarvis-desk/src/lib/kilder.ts --path apps/jarvis-desk/src/lib/kilder.test.ts
```

### Task 3: Generalize the Right Panel to Typed Inspector Targets

**Files:**
- Create: `apps/jarvis-desk/src/lib/inspectorTargets.ts`
- Create: `apps/jarvis-desk/src/components/panel/InspectorPanel.tsx`
- Create: `apps/jarvis-desk/src/components/panel/InspectorPanel.test.tsx`
- Modify: `apps/jarvis-desk/src/lib/panelReducer.ts:1-40`
- Modify: `apps/jarvis-desk/src/lib/panelReducer.test.ts`
- Modify: `apps/jarvis-desk/src/contexts/PanelContext.tsx:1-36`
- Modify: `apps/jarvis-desk/src/contexts/PanelContext.test.tsx`
- Modify: `apps/jarvis-desk/src/components/panel/ArtifactPanel.tsx:1-76`
- Modify: `apps/jarvis-desk/src/components/panel/ArtifactPanel.test.tsx`
- Modify: `apps/jarvis-desk/src/App.tsx:171-194`

**Interfaces:**
- Consumes: `Artifact`, `ToolEvidence`, `SourceEvidence`, `AgentReference`.
- Produces:

```ts
export type InspectorTarget =
  | { type: 'artifact'; artifact: Artifact }
  | { type: 'agent'; agent: AgentReference; canMessage: boolean }
  | { type: 'source'; source: SourceEvidence; tool?: ToolEvidence }
  | { type: 'tool'; tool: ToolEvidence }

export interface PanelContextValue {
  open: boolean
  width: number
  target: InspectorTarget | null
  previousTarget: InspectorTarget | null
  canGoBack: boolean
  openTarget(target: InspectorTarget, rememberCurrent?: boolean): void
  openArtifact(artifact: Artifact): void
  open_(artifact: Artifact): void
  back(): void
  close(): void
  toggle(): void
  resize(width: number): void
}

export interface InspectorPanelProps {
  target: InspectorTarget | null
  config?: ApiConfig
  canGoBack: boolean
  onBack(): void
  onClose(): void
  onOpenTarget(target: InspectorTarget, rememberCurrent?: boolean): void
}
```

- [ ] **Step 1: Write failing reducer and context tests**

Tilføj tests der beviser:

```ts
it('åbner et typed tool-target og går tilbage til forrige target', () => {
  const tool = { type: 'tool', tool: { id: 't1', name: 'web', input: {}, status: 'done' } } as const
  const source = { type: 'source', source: { url: 'https://dr.dk', domaene: 'dr.dk', origin: 'tool_result' } } as const
  const opened = panelReducer(initialPanelState(420), { type: 'open-target', target: tool })
  const replaced = panelReducer(opened, { type: 'open-target', target: source, rememberCurrent: true })
  expect(panelReducer(replaced, { type: 'back' }).target).toEqual(tool)
})
```

Context-testen skal fortsat bevise, at `open_({kind:'markdown', ...})` åbner et artifact-target, så eksisterende call-sites er kompatible.

- [ ] **Step 2: Run tests and verify contract failures**

```bash
npm test -- src/lib/panelReducer.test.ts src/contexts/PanelContext.test.tsx src/components/panel/ArtifactPanel.test.tsx
```

Expected: FAIL because reducer/context only accepterer `artifact`.

- [ ] **Step 3: Implement target state and one-level history**

Skift reducer-state til:

```ts
export interface PanelState {
  open: boolean
  width: number
  target: InspectorTarget | null
  previousTarget: InspectorTarget | null
}
```

`open-target` gemmer kun nuværende target, når `rememberCurrent === true`. `back` bruger `previousTarget`; hvis den er `null`, lukker panelet. `close` nulstiller begge targets, men bevarer width. `toggle` må åbne et tomt panel uden at fabrikere et target.

- [ ] **Step 4: Add the common inspector shell without new target bodies**

`InspectorPanel` ejer header, ikon, titel, tilbage og luk. I denne task renderer
kun artifact-targetet et udtrukket `ArtifactInspectorBody`. De øvrige targettyper
renderer en fælles neutral tomtilstand, men kan endnu ikke åbnes fra nogen
produktflade. Task 4 og 5 erstatter disse cases, før Task 6 gør dem tilgængelige.

`ShellWithPanel` ændres til:

```tsx
panel={<InspectorPanel
  target={panel.target}
  canGoBack={panel.canGoBack}
  onBack={panel.back}
  onClose={panel.close}
  onOpenTarget={panel.openTarget}
  config={config}
/>}
```

- [ ] **Step 5: Verify artifact compatibility and panel navigation**

```bash
npm test -- src/lib/panelReducer.test.ts src/contexts/PanelContext.test.tsx src/components/panel/ArtifactPanel.test.tsx src/components/panel/InspectorPanel.test.tsx src/components/UiPanelWatcher.test.tsx src/components/rich/MessageRow.test.tsx
npm run build:renderer
```

Expected: PASS; artifact affordances og `open_ui_panel` virker fortsat.

- [ ] **Step 6: Commit typed panel infrastructure**

```bash
git add -- apps/jarvis-desk/src/lib/inspectorTargets.ts apps/jarvis-desk/src/lib/panelReducer.ts apps/jarvis-desk/src/lib/panelReducer.test.ts apps/jarvis-desk/src/contexts/PanelContext.tsx apps/jarvis-desk/src/contexts/PanelContext.test.tsx apps/jarvis-desk/src/components/panel/ArtifactPanel.tsx apps/jarvis-desk/src/components/panel/ArtifactPanel.test.tsx apps/jarvis-desk/src/components/panel/InspectorPanel.tsx apps/jarvis-desk/src/components/panel/InspectorPanel.test.tsx apps/jarvis-desk/src/App.tsx
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'refactor(desk): generalize preview panel targets' --path apps/jarvis-desk/src/lib/inspectorTargets.ts --path apps/jarvis-desk/src/lib/panelReducer.ts --path apps/jarvis-desk/src/lib/panelReducer.test.ts --path apps/jarvis-desk/src/contexts/PanelContext.tsx --path apps/jarvis-desk/src/contexts/PanelContext.test.tsx --path apps/jarvis-desk/src/components/panel/ArtifactPanel.tsx --path apps/jarvis-desk/src/components/panel/ArtifactPanel.test.tsx --path apps/jarvis-desk/src/components/panel/InspectorPanel.tsx --path apps/jarvis-desk/src/components/panel/InspectorPanel.test.tsx --path apps/jarvis-desk/src/App.tsx
```

### Task 4: Implement Source and Tool Inspectors

**Files:**
- Create: `apps/jarvis-desk/src/components/panel/SourceInspector.tsx`
- Create: `apps/jarvis-desk/src/components/panel/ToolInspector.tsx`
- Create: `apps/jarvis-desk/src/components/panel/EvidenceInspectors.test.tsx`
- Modify: `apps/jarvis-desk/src/components/panel/InspectorPanel.tsx`
- Modify: `apps/jarvis-desk/src/styles/environment-inspector.css`

**Interfaces:**
- Consumes: source/tool targets from Task 3 and `lookupTool` from `lib/toolRegistry.ts`.
- Produces:

```ts
export function SourceInspector(props: {
  source: SourceEvidence
  tool?: ToolEvidence
  onOpenTool?: (tool: ToolEvidence) => void
}): JSX.Element

export function ToolInspector(props: {
  tool: ToolEvidence
  onOpenSource: (source: SourceEvidence) => void
}): JSX.Element
```

- [ ] **Step 1: Write failing interaction tests**

Test at minimum:

```ts
it('åbner ikke websiden før brugeren trykker Åbn kilde', async () => {
  const open = vi.spyOn(window, 'open').mockImplementation(() => null)
  render(<SourceInspector source={source} tool={tool} />)
  expect(open).not.toHaveBeenCalled()
  await userEvent.click(screen.getByRole('button', { name: 'Åbn kilde' }))
  expect(open).toHaveBeenCalledWith(source.url, '_blank', 'noopener,noreferrer')
})

it('viser tool-input som JSON og fejlresultatet som tekst', () => {
  render(<ToolInspector tool={{ id: 't1', name: 'web_search', input: { query: 'wled' }, status: 'error', result: 'timeout' }} onOpenSource={() => {}} />)
  expect(screen.getByText(/"query": "wled"/)).toBeInTheDocument()
  expect(screen.getByText('timeout')).toBeInTheDocument()
})
```

Test også source origin `assistant_text`, URL/domaene, query-visning og klik fra tool til relateret source.

- [ ] **Step 2: Run tests and verify missing components**

```bash
npm test -- src/components/panel/EvidenceInspectors.test.tsx src/components/panel/InspectorPanel.test.tsx
```

Expected: FAIL because inspector bodies do not exist.

- [ ] **Step 3: Implement bounded result rendering**

`ToolInspector` skal:

- vise registry-label og råt tool-navn;
- vise ID og tekststatus;
- bruge `JSON.stringify(input, null, 2)` i en eksisterende `CodeBlock` eller `<pre>`;
- forsøge `JSON.parse(result)` og pretty-printe object/array, ellers vise rå tekst;
- vise de kilder, `sourcesForTool(tool)` udleder fra netop dette tool;
- starte store output foldet efter 12.000 tegn med en eksplicit `Vis hele resultatet`-knap.

`SourceInspector` viser provenance og har en ikonknap med `ExternalLink`; selve URL-rækken må ikke navigere.

- [ ] **Step 4: Route both target types and add focused CSS**

Erstat Task 3's neutrale source/tool-cases i `InspectorPanel` med de rigtige
komponenter. Når `ToolInspector` åbner en kilde, kald
`onOpenTarget({type:'source', source, tool}, true)`, så Back går tilbage til
tool-resultatet.

Tilføj kun `.inspector-*`, `.source-inspector-*` og `.tool-inspector-*` regler i `environment-inspector.css`. Brug sektioner, ikke nested cards, og stabil header/button-dimension.

- [ ] **Step 5: Verify inspectors**

```bash
npm test -- src/components/panel/EvidenceInspectors.test.tsx src/components/panel/InspectorPanel.test.tsx src/lib/environmentEvidence.test.ts
npm run build:renderer
```

Expected: PASS; ingen midlertidig source/tool-tomtilstand er tilbage.

- [ ] **Step 6: Commit source and tool inspectors**

```bash
git add -- apps/jarvis-desk/src/components/panel/SourceInspector.tsx apps/jarvis-desk/src/components/panel/ToolInspector.tsx apps/jarvis-desk/src/components/panel/EvidenceInspectors.test.tsx apps/jarvis-desk/src/components/panel/InspectorPanel.tsx apps/jarvis-desk/src/styles/environment-inspector.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): inspect sources and tool results' --path apps/jarvis-desk/src/components/panel/SourceInspector.tsx --path apps/jarvis-desk/src/components/panel/ToolInspector.tsx --path apps/jarvis-desk/src/components/panel/EvidenceInspectors.test.tsx --path apps/jarvis-desk/src/components/panel/InspectorPanel.tsx --path apps/jarvis-desk/src/styles/environment-inspector.css
```

### Task 5: Extract and Reuse the Agent Inspector

**Files:**
- Create: `apps/jarvis-desk/src/components/panel/AgentInspector.tsx`
- Create: `apps/jarvis-desk/src/components/panel/AgentInspector.test.tsx`
- Modify: `apps/jarvis-desk/src/lib/agentPoolApi.ts:1-140`
- Modify: `apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.tsx:90-380`
- Modify: `apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.test.tsx`
- Modify: `apps/jarvis-desk/src/components/panel/InspectorPanel.tsx`
- Modify: `apps/jarvis-desk/src/styles/environment-inspector.css`

**Interfaces:**
- Consumes: `GET /mc/agents/{agent_id}`, `sendTilAgent`, `agentHandling` and agent target from Task 3.
- Produces:

```ts
export interface AgentDetail {
  agent_id: string
  role?: string
  kind?: string
  goal?: string
  status?: string
  provider?: string
  model?: string
  tokens_burned?: number
  last_error?: string | null
  progress_label?: string
  created_at?: string
  completed_at?: string | null
  runs: AgentKoersel[]
  messages: AgentBesked[]
  tool_calls?: Array<Record<string, unknown>>
}

export function getAgentDetalje(config: ApiConfig, agentId: string): Promise<AgentDetail>

export function AgentInspector(props: {
  config: ApiConfig
  agent: AgentReference
  canMessage: boolean
}): JSX.Element
```

- [ ] **Step 1: Write failing API and component tests**

Mock `getAgentDetalje` og `sendTilAgent`. Dæk:

```ts
it('henter først detaljen når inspectoren mountes', async () => {
  render(<AgentInspector config={config} agent={agentRef} canMessage />)
  await waitFor(() => expect(api.getAgentDetalje).toHaveBeenCalledWith(config, 'agent-1'))
})

it('bevarer draft og viser fejl når send fejler', async () => {
  vi.spyOn(api, 'sendTilAgent').mockRejectedValue(new Error('nede'))
  render(<AgentInspector config={config} agent={agentRef} canMessage />)
  await userEvent.type(screen.getByLabelText('Besked til agenten'), 'se også testen')
  await userEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(await screen.findByText('nede')).toBeInTheDocument()
  expect(screen.getByLabelText('Besked til agenten')).toHaveValue('se også testen')
})
```

Dæk også: succes rydder draft og refetcher; `canMessage=false` skjuler composer; completed agent forklarer at tråden er afsluttet; fake timers viser 3 sekunders polling for `active|queued|starting|waiting`, men ikke for `completed|failed|cancelled|expired`.

- [ ] **Step 2: Run tests and verify failures**

```bash
npm test -- src/components/panel/AgentInspector.test.tsx src/components/cowork/agentpool/AgentPoolPanel.test.tsx
```

Expected: FAIL because detail API/component do not exist.

- [ ] **Step 3: Add the typed detail API and lifecycle-safe polling**

Implementér `getAgentDetalje` som ét `apiFetch` mod `/mc/agents/${encodeURIComponent(agentId)}`. I `AgentInspector`:

- hent straks ved mount/agent-ID-skift;
- behold seneste succesfulde data under refresh;
- poll hvert 3.000 ms kun ved aktiv status og `document.hidden === false`;
- ryd interval og ignorer sene promises efter unmount;
- brug summary fra `AgentReference` indtil første svar;
- vis fejl med `Prøv igen` uden at tømme kendte data.

- [ ] **Step 4: Implement the message composer and existing controls**

Send kun trimmet tekst. Sæt `sending=true`, kald `sendTilAgent`, refetch detail ved succes og ryd derefter draft. Ved fejl behold draftet. Genbrug de eksisterende labels `Stop`, `Marker pauset`, `Genoptag` og `Luk som udløbet`; vis kun handlinger når `canMessage` er sandt, og behold forklaringen om at suspend ikke stopper en tråd.

- [ ] **Step 5: Reuse the component in Agent Pool and InspectorPanel**

Fjern den lokale `AgentDetalje`-implementering fra `AgentPoolPanel.tsx`. Dens overlay må rendere den delte `AgentInspector` med `canMessage=true`. Det globale `InspectorPanel` renderer samme komponent for agent-targets og sender targetets `canMessage` videre.

Opdatér Agent Pool-testen til at forvente ét lazy `getAgentDetalje(config, 'agent-1')` frem for de to gamle detailkald. Liste-, summary- og work-kald forbliver uændrede.

- [ ] **Step 6: Verify agent behavior**

```bash
npm test -- src/components/panel/AgentInspector.test.tsx src/components/cowork/agentpool/AgentPoolPanel.test.tsx src/components/panel/InspectorPanel.test.tsx
npm run build:renderer
```

Expected: PASS; ingen agentdetail hentes før en agent åbnes.

- [ ] **Step 7: Commit shared agent inspection**

```bash
git add -- apps/jarvis-desk/src/lib/agentPoolApi.ts apps/jarvis-desk/src/components/panel/AgentInspector.tsx apps/jarvis-desk/src/components/panel/AgentInspector.test.tsx apps/jarvis-desk/src/components/panel/InspectorPanel.tsx apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.tsx apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.test.tsx apps/jarvis-desk/src/styles/environment-inspector.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): add shared agent inspector' --path apps/jarvis-desk/src/lib/agentPoolApi.ts --path apps/jarvis-desk/src/components/panel/AgentInspector.tsx --path apps/jarvis-desk/src/components/panel/AgentInspector.test.tsx --path apps/jarvis-desk/src/components/panel/InspectorPanel.tsx --path apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.tsx --path apps/jarvis-desk/src/components/cowork/agentpool/AgentPoolPanel.test.tsx --path apps/jarvis-desk/src/styles/environment-inspector.css
```

### Task 6: Rebuild the Environment Overview and Wire CodeView

**Files:**
- Modify: `apps/jarvis-desk/src/components/code/EnvironmentPanel.tsx:1-294`
- Modify: `apps/jarvis-desk/src/components/code/EnvironmentPanel.test.tsx`
- Modify: `apps/jarvis-desk/src/components/code/EnvironmentPanel.agents.test.tsx`
- Modify: `apps/jarvis-desk/src/lib/api.ts:500-506`
- Modify: `apps/jarvis-desk/src/views/CodeView.tsx:130-280,650-850`
- Modify: `apps/jarvis-desk/src/views/CodeView.test.tsx`
- Modify: `apps/jarvis-desk/src/styles/environment-inspector.css`

**Interfaces:**
- Consumes: `EnvironmentEvidence`, `InspectorTarget`, `PanelContext.openTarget`, existing `GitStatus` and existing git actions.
- Produces:

```ts
export interface EnvironmentPanelProps {
  // eksisterende workspace/run props bevares
  evidence: EnvironmentEvidence
  onInspectTool(tool: ToolEvidence): void
  onInspectSource(source: SourceEvidence, tool?: ToolEvidence): void
  onInspectAgent(agent: AgentReference): void
}

export interface GitStatus {
  branch: string
  dirty: number
  added: number
  removed: number
  is_git: boolean
  repo?: string
  host?: string
  link?: 'ok' | 'genforbinder' | 'nede'
}
```

- [ ] **Step 1: Replace old expectations with failing product tests**

Udvid først `GitStatus` med backendens eksisterende additive felter `repo`,
`host` og `link`. Workspace-testen skal kræve, at første indholdssektion er:

```ts
expect(screen.getByText('Ændringer')).toBeInTheDocument()
expect(screen.getByText('+12')).toHaveClass('git-add')
expect(screen.getByText('−4')).toHaveClass('git-del')
```

Tilføj clean-state `Ingen ændringer`. Kildetesten skal vise `kno.wled.ge`, ikke `Websøgning`, og et klik skal kalde `onInspectSource` uden at kalde `window.open`. Tool-testen skal kalde `onInspectTool` med hele resultatet.

Agenttesten skal bevise:

```ts
expect(screen.getByRole('button', { name: /find parser/ })).toBeEnabled()
await userEvent.click(screen.getByRole('button', { name: /find parser/ }))
expect(onInspectAgent).toHaveBeenCalledWith(expect.objectContaining({ agentId: 'agent-1' }))
```

Et `task`-tool uden ID må kun findes under Tools og må ikke optræde som agentknap.

- [ ] **Step 2: Run focused tests and verify old UI fails them**

```bash
npm test -- src/components/code/EnvironmentPanel.test.tsx src/components/code/EnvironmentPanel.agents.test.tsx src/views/CodeView.test.tsx
```

Expected: FAIL because panelet stadig modtager flade `tools` og viser generiske kilder.

- [ ] **Step 3: Derive historical and live evidence without per-token history parsing**

I `CodeView`:

```ts
const historicalEvidence = useMemo(
  () => buildEnvironmentEvidence(
    sessions.messages.filter((m) => m.role === 'assistant').map((m) => m.content),
  ),
  [sessions.messages],
)

const liveEvidence = useMemo(
  () => buildEnvironmentEvidence([
    stream.blocks,
    ...(bgActive ? [followState.blocks] : []),
  ]),
  [stream.blocks, followState.blocks, bgActive],
)
```

Flet med `mergeEnvironmentEvidence(historicalEvidence, liveEvidence)` fra Task 2.
Den deduplikerer på tool-ID, URL og agent-ID. Historikken genberegnes kun når
`sessions.messages` ændres; token-deltas parser kun de aktuelle liveblokke.

Stop med at gemme flade tool-lister som visningsautoritet i `session-stats`. Bevar token- og tool-totaler samt bagudkompatibel læsning af gamle records; ignorer det gamle `tools`-felt efter migrationen.

- [ ] **Step 4: Wire typed inspector actions**

```ts
const inspectTool = (tool: ToolEvidence) => panel.openTarget({ type: 'tool', tool })
const inspectSource = (source: SourceEvidence, tool?: ToolEvidence) =>
  panel.openTarget({ type: 'source', source, tool })
const inspectAgent = (agent: AgentReference) =>
  panel.openTarget({ type: 'agent', agent, canMessage: isOwner })
```

Miljø forbliver logisk åbent, mens `CodeView` skjuler det via den eksisterende `!panel.open`-betingelse. Når inspector lukkes/backes, kommer samme Miljø-state derfor tilbage automatisk.

- [ ] **Step 5: Rebuild the compact environment sections**

Fjern `SOURCE_RULES`, `AGENT_TOOLS` og index-baserede agentkeys. Render rækkefølgen Workspace, Aktivitet/kontekst, Agenter, Kilder, Seneste tools. Brug:

- `git.added` og `git.removed` i top-rækken, også når begge er nul;
- branch, root, `git.repo`, `git.host` og workstation/server under top-rækken,
  når felterne findes;
- stabile buttons med `ChevronRight` for agent/source/tool rows;
- højst 8 kilder og 8 seneste tools i oversigten, mens alle forbliver tilgængelige via data/inspector;
- agent-ID, tool-ID og URL som keys;
- eksisterende commit/PR-handlers og `RunHealth` uden funktionsændring.

- [ ] **Step 6: Verify CodeView integration**

```bash
npm test -- src/components/code/EnvironmentPanel.test.tsx src/components/code/EnvironmentPanel.agents.test.tsx src/views/CodeView.test.tsx src/lib/environmentEvidence.test.ts
npm run build:renderer
```

Expected: PASS; sourceklik navigerer aldrig eksternt direkte, og Back viser Miljø igen.

- [ ] **Step 7: Commit the environment workflow**

```bash
git add -- apps/jarvis-desk/src/components/code/EnvironmentPanel.tsx apps/jarvis-desk/src/components/code/EnvironmentPanel.test.tsx apps/jarvis-desk/src/components/code/EnvironmentPanel.agents.test.tsx apps/jarvis-desk/src/lib/api.ts apps/jarvis-desk/src/views/CodeView.tsx apps/jarvis-desk/src/views/CodeView.test.tsx apps/jarvis-desk/src/styles/environment-inspector.css
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'feat(desk): make code environment inspectable' --path apps/jarvis-desk/src/components/code/EnvironmentPanel.tsx --path apps/jarvis-desk/src/components/code/EnvironmentPanel.test.tsx --path apps/jarvis-desk/src/components/code/EnvironmentPanel.agents.test.tsx --path apps/jarvis-desk/src/lib/api.ts --path apps/jarvis-desk/src/views/CodeView.tsx --path apps/jarvis-desk/src/views/CodeView.test.tsx --path apps/jarvis-desk/src/styles/environment-inspector.css
```

### Task 7: Focused Regression and Visual Verification

**Files:**
- Modify only files with defects found by the checks below.
- Test: all focused files listed in Tasks 1-6.

**Interfaces:**
- Consumes: completed inspector workflow.
- Produces: verified renderer/build with no layout overlap or stale polling.

- [ ] **Step 1: Run the complete affected test set, not the repository suite**

```bash
cd apps/jarvis-desk
npm test -- \
  src/styles/tokens.test.ts \
  src/lib/kilder.test.ts \
  src/lib/environmentEvidence.test.ts \
  src/lib/panelReducer.test.ts \
  src/contexts/PanelContext.test.tsx \
  src/components/panel/ArtifactPanel.test.tsx \
  src/components/panel/InspectorPanel.test.tsx \
  src/components/panel/EvidenceInspectors.test.tsx \
  src/components/panel/AgentInspector.test.tsx \
  src/components/cowork/agentpool/AgentPoolPanel.test.tsx \
  src/components/code/EnvironmentPanel.test.tsx \
  src/components/code/EnvironmentPanel.agents.test.tsx \
  src/components/UiPanelWatcher.test.tsx \
  src/components/rich/MessageRow.test.tsx \
  src/views/CodeView.test.tsx
```

Expected: alle berørte tests PASS.

- [ ] **Step 2: Run static and production build checks**

```bash
npm run lint
npm run build
```

Expected: ESLint, renderer TypeScript/Vite og Electron TypeScript PASS.

- [ ] **Step 3: Start the renderer and inspect both target widths**

```bash
npm run dev -- --host 127.0.0.1
```

Åbn Code-visningen mod den lokale runtime og kontrollér ved cirka 1440x900 og 1180x800:

1. `Ændringer +xx −xx` er første workspace-række, med grøn plus og rød minus.
2. Lange paths, URL'er og agentmål overlapper ikke status eller chevrons.
3. Agentklik åbner inspector; composer bliver nederst og scrolles ikke væk af polling.
4. Kildeklik åbner provenance; først `Åbn kilde` navigerer eksternt.
5. Toolklik viser input og resultat; sourceklik derfra kan Back'e til tool.
6. Artifact-preview virker fortsat.
7. Back/luk viser Miljø igen med samme collapse- og git-state.
8. Smal bredde skjuler Miljø efter eksisterende regel og viser aldrig panel oven på composer/liveness.

- [ ] **Step 4: Check polling and render behavior in DevTools**

Med en aktiv agent åben: bekræft ét detailkald cirka hvert tredje sekund. Luk panelet og bekræft, at kald stopper. Start en tekststream og bekræft, at historisk evidens ikke genudledes for hvert token; kun den aktuelle livegruppe ændres.

- [ ] **Step 5: Fix only observed regressions and rerun their focused tests**

For hver observeret fejl: skriv eller stram først den nærmeste test, se den fejle, ret minimal kode, og kør den enkelte testfil igen. Undgå unrelated cleanup.

- [ ] **Step 6: Commit verification fixes if any files changed**

Hvis Step 5 gav kodeændringer, stage kun de konkrete filer. Byg derefter
wrapperens `--path`-argumenter direkte fra staged-listen:

```bash
mapfile -t paths < <(git diff --cached --name-only)
args=()
for path in "${paths[@]}"; do args+=(--path "$path"); done
python scripts/commit_with_attribution.py --repo . --actor codex --origin interactive --approved-by bjorn --message 'fix(desk): polish environment inspector' "${args[@]}"
```

Hvis ingen filer ændrede sig, oprettes ingen tom commit.

- [ ] **Step 7: Record final evidence**

Kør fra repository-roden:

```bash
git status --short
git log --oneline -7
```

Expected: ren worktree og de reviewbare commits fra Tasks 1-6, plus en eventuel målrettet polish-commit.
