# Tool-chips berigelse + pæne navne + luk-panel — jarvis-desk

**Dato:** 2026-06-15
**Status:** Design — afventer implementerings-plan
**Forfatter:** Claude Code (på Bjørns anmodning)

## Problem

To gener i jarvis-desk-transcripten:

1. **Tool-kald viser intet brugbart.** Et tool-kald renderes som en lille chip med
   skruenøgle + rå funktionsnavn (`internal_api`, `web_search`, `operator_read_file`).
   Folder man den ud, er der ofte intet at se. Bjørn: "jeg har ingen ide om hvad han
   laver i de kald og den viser heller ikke noget når man trykker på den."

   **Root cause (verificeret):** `_emit_tool_use` i
   [visible_runs_sse_v2.py](core/services/visible_runs_sse_v2.py) plukker kun et par
   hårdkodede arg-nøgler (`target_path`, `command_text`, `write_content`, `arguments`)
   og videresender **aldrig tool-resultatet**. Frontendens `ToolCard` er fuldt udstyret
   (foldbar, viser args/resultat/status) men får ingen data for de fleste tools.

2. **Rå funktionsnavne ser mærkelige ud.** `operator_*`, `internal_api`, `web_search`
   m.fl. står som kode. Claude Code/Desktop viser pæne labels, ikke funktionsnavne.

3. **Jarvis kan ikke lukke paneler.** `open_ui_panel` kan kun åbne; der er ingen vej
   til at lukke et panel han åbnede ([[project_jarvis_capability_roadmap]]).

## Mål

- Hvert tool-kald viser **uden klik** en pæn label + en kort opsummerings-/resultat-linje.
- Klik folder ud til pæne args + fuldt (trunkeret) resultat.
- Filredigeringer viser **`+32 −74`** (insertions/deletions) i enden af chip'en, som i
  Claude Code.
- **Komplet dækning:** hvert eneste tool får en pæn label (intet rå funktionsnavn).
- Jarvis kan **lukke** et panel igen.

## Tilgang (valgt: A — backend leverer data, frontend ejer udseendet)

Backend beriges til at sende **ren data** (`arguments` + `result_text`), uden
præsentation. Al label/ikon/opsummering bor i et frontend-register. Dette matcher
repoets ansvarsdeling (UI i UI; backend emitterer sandhed, ikke præsentation —
[[reference_bridge_not_orphaned]]-stil separation).

Fravalgt: **B) backend-deklareret display-metadata** (rører ~100 tool-definitioner,
kobler præsentation ind i backend) og **C) kun auto-labels** (Bjørn vil have komplet
håndlavet dækning).

## Beslutninger (afklaret med Bjørn)

- **Chip-indhold:** opsummering i hovedet (synlig uden klik) **+** rå args/resultat ved
  fuld udfoldning.
- **Dækning:** komplet — alle ~100 tools får håndlavet label + opsummering. Registret
  seedes fra backendens `TOOL_DEFINITIONS` så intet tool glemmes.
- **Diff-stat:** filredigeringer viser `+N −M` i chip-hovedet (grøn/rød).
- **Luk-panel:** `open_ui_panel` udvides med `action: 'open' | 'close'` (ikke et nyt tool).

## Arkitektur

```
Backend (visible_runs_sse_v2._emit_tool_use)
  tool_use start-event  → bærer nu HELE arguments-dict (trunkeret)
  tool_result-event     → bærer nu result_text (trunkeret ~4 KB)
        │  ren data, ingen labels/præsentation
        ▼
Frontend
  streamReducer → tool_use-blok får { name, input(args), result, status }
        ▼
  toolRegistry.ts (komplet, seedet fra backend-listen)
    name → { label, icon, summarize(args, result) → kort linje }
        ▼
  ToolCard
    sammenfoldet: ikon · label · summarize-linje · status · [ +N −M ]
    udfoldet:     pæne args + fuldt resultat (familie-renderere genbruges)
```

## Komponenter

### 1. Backend: data-berigelse i `_emit_tool_use`

**Fil:** [visible_runs_sse_v2.py](core/services/visible_runs_sse_v2.py) (`_emit_tool_use`,
~line 284) + emissions-stedet i [visible_runs.py](core/services/visible_runs.py).

- `tool_use`-start-event'et inkluderer **hele** `arguments`-dict'en (i dag kun 4 nøgler),
  trunkeret til en fornuftig størrelse (fx hver streng-værdi cappet, samlet payload cappet).
- Et `tool_result`-event (capability/system_event) bærer `result_text` (trunkeret ~4 KB)
  bundet til `tool_use_id`, så `ToolCard` kan vise resultatet.
- Trunkering sker server-side så store payloads ikke spildes over streamen (matcher det
  eksisterende `format_tool_result_for_model`-cap-mønster).
- Ingen labels/præsentation i backend.

### 2. Frontend: `toolRegistry.ts` (komplet dækning)

**Filer:** `apps/jarvis-desk/src/lib/toolRegistry.ts` (registret) +
`scripts/gen_tool_registry.py` (seed-generator).

- **Generator** (`scripts/gen_tool_registry.py`): læser backendens `TOOL_DEFINITIONS`,
  udskriver en TS-skabelon med én entry pr. tool-navn (label = auto fra navn,
  `summarize` = generisk default). Kører som engangs-seed; herefter håndskrives label +
  `summarize` for alle. Genkøres for at fange nye tools (rapporterer manglende entries).
- **Register-form:**
  ```ts
  interface ToolMeta {
    label: string
    icon: LucideIcon
    summarize: (args: Record<string, unknown>, result?: string) => string
  }
  export const TOOL_REGISTRY: Record<string, ToolMeta>
  export function lookupTool(name: string): ToolMeta  // fallback for ukendt
  ```
- **Fallback** (ukendt tool): label = snake_case → Title Case; `summarize` = første
  meningsfulde arg-værdi. Sikrer at intet tool nogensinde står som rå funktionsnavn.

### 3. Frontend: `ToolCard`-rendering

**Filer:** `apps/jarvis-desk/src/components/rich/ToolCard.tsx` +
`apps/jarvis-desk/src/lib/diffStat.ts` (ny ren helper) + CSS i `styles/app.css`.

- **Sammenfoldet (synligt uden klik):** ikon · **label** (fra register) ·
  **summarize-linje** · status-badge · evt. **`+N −M`**.
- **Diff-stat:** `diffStat(args)` for `edit_file`/`write_file`/`operator_edit_file`/
  `operator_write_file` udregner insertions/deletions:
  - `edit_file`: linje-diff mellem `old_string` og `new_string`.
  - `write_file`: alle linjer = insertions (ny fil) eller diff mod kendt indhold hvis
    tilgængeligt; ellers rene insertions.
  - Vises som `+32 −74` (grøn/rød) i chip-hovedet. Ren funktion → unit-testbar.
- **Udfoldet:** pæne args (label'ede felter, ikke rå JSON for kendte tools) + fuldt
  trunkeret resultat. De eksisterende familie-renderere (bash-terminal, edit-diff,
  write-preview) genbruges uændret.

### 4. Luk-panel: `open_ui_panel` action

**Filer:** [ui_panel_tools.py](core/tools/ui_panel_tools.py) +
[ui_panel_store.py](core/services/ui_panel_store.py) +
`apps/jarvis-desk/src/components/UiPanelWatcher.tsx`.

- `open_ui_panel` får parameter `action: 'open' | 'close'` (default `'open'` —
  bagudkompatibelt). `panel` bliver valgfri ved `close` (lukker det åbne panel).
- Store'n bærer `action` på panel-requesten.
- `UiPanelWatcher` håndterer en `close`-request → `panel.close()` (i stedet for `open_`).
- Tool-beskrivelsen opdateres så Jarvis ved han kan lukke igen.

## Dataflow

1. Jarvis kalder et tool → backend eksekverer.
2. `_emit_tool_use` sender `tool_use`-start med fulde (trunkerede) args.
3. Efter eksekvering sendes `tool_result` med `result_text` (trunkeret).
4. Reducer sætter `{ name, input, result, status }` på blokken.
5. `ToolCard` slår `name` op i `toolRegistry` → label + ikon + `summarize`-linje;
   udregner evt. `+N −M`. Sammenfoldet visning vises straks.
6. Klik → udfold til args + resultat.

## Fejlhåndtering

- **Manglende args/result:** `ToolCard` falder tilbage til label + status (ingen
  opsummering); aldrig et crash.
- **Ukendt tool:** `lookupTool` fallback (Title Case + første arg).
- **Trunkering:** store resultater cappes server-side; UI viser "(trunkeret)".
- **Diff-stat ikke beregnelig** (mangler old/new): chip viser ingen `+N −M`, intet crash.
- **Luk uden åbent panel:** `panel.close()` er idempotent (no-op).
- **Bagudkompatibilitet:** `action` defaulter til `'open'`; gamle kald uændret.

## Testning

- **Backend:** `_emit_tool_use` inkluderer fulde args + `result_text`; trunkering capper;
  `open_ui_panel` accepterer `action='close'` og lægger en close-request.
- **Frontend:**
  - `diffStat`: `+N −M` for edit (old/new), write (rene insertions), tom ved manglende data.
  - `toolRegistry`: kendt tool → label + summarize; ukendt → fallback.
  - `ToolCard`: sammenfoldet viser label + summarize + diff-stat uden klik; udfold viser
    args+resultat.
  - `UiPanelWatcher`: close-request → `panel.close()` kaldes.

## Afgrænsning

- Ingen ny panel-type.
- Resultat trunkeres (ikke ubegrænset stream-spild).
- Følsomme felter vises som de er — det er ejers eget run i hans egen app; ingen ny
  eksponering på tværs af brugere (chip viser kun brugerens egne tool-kald).
- Ikke i scope: redigerbare/interaktive tool-kald, re-run-knap, kopiér-resultat (kan
  tilføjes senere).
