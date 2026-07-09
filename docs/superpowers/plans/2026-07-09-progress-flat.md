# Plan: Persisteret progress (FLAT v1)

**Dato:** 2026-07-09
**Spec:** [[2026-07-09-persisted-progress-tree-design]] (FLAT-delen — træet er OPFØLGNING)
**Branch:** `feat/leaked-cc-learnings`
**Substrate:** tur-akkumulatoren i det LIVE run-loop (`core/services/visible_runs.py`).

## Kerne-realitet (fra spec-self-review, verificeret live)
- `parent_tool_use_id` findes INTET sted → **kun FLAT** (`parent_tool_use_id` altid `null`).
- `working_step`-SSE bærer INGEN tool-id — kun `run_id/action/detail/step/status`.
- MEN: hvert `working_step` emittes lige før tool-exec, hvor `detail = _tool_label(name, args)`.
  `_tool_label` er **deterministisk** fra `(name, args)`. Tur-akkumulatoren gemmer allerede
  `id/name/input` pr. tool. → Vi kan **regenerere den præcise live-narration** ved build-tid
  fra de allerede-akkumulerede tool-calls. Ingen ny accumulator gennem SSE-stien, ingen ny
  SSE-event. Det er ærligt: samme funktion der producerede den live working_step.

## Repræsentations-valg: **(A) separate flade `progress`-content-blokke**

Overvejet mod (B) `progress_note`-felt på tool_use-blokken.

**Valgt A, fordi:**
- Matcher spec §5's data-model 1:1 (`{"type":"progress","tool_use_id",..,"parent_tool_use_id":null,"message","status"}`)
  → træet kan tilføjes senere UDEN format-brud (feltet er der allerede, bare `null`).
- Holder `tool_use`-blokken **urørt** (ingen shape-ændring på den mest kritiske blok-type →
  ingen regression-risiko i eksisterende ToolCard/foldToolResults/groupReadSearch).
- Giver et distinkt, foldbart "Forløb"-spor ("hvad Jarvis lavede") som EGEN visuel enhed —
  det er præcis v1-værdien: narrationen overlever reload, adskilt fra tool-kortene.
- `content_blocks_to_text` udelader det (samme regel som tool_use/tool_result) → server-læsere urørte.

(B) ville være marginalt færre blokke men ændrer tool_use-shapen og blander narration ind i
tool-kortet — mindre ærligt om at det er en SEPARAT ting, og sværere at fjerne rent via kill-switch.

## Æresærlig note om overlap (spec §6.1)
En `tool_use`-blok bærer allerede navn+status+input+result. En flad progress-blok tilføjer
primært den mellemliggende **working-narration** (`_tool_label`, fx "Analyserede billede: foto.png")
+ en settlet status pr. tool i **kald-rækkefølge som ét spor**. v1-værdien = forløbs-narrationen
overlever reload; den er tynd oven på tool-kortene, men den ER den ting der i dag er efemer.
Render defaults til FOLDET når sporet er langt, så overlappet ikke støjer.

## Data-model (per progress-blok)
```jsonc
{"type": "progress", "tool_use_id": "toolu_..", "parent_tool_use_id": null,
 "message": "Analyserede billede: foto.png", "status": "done|error"}
```
- Ét element pr. tool-kald i turen, i kald-rækkefølge.
- `status`: `error` hvis tool_result er error, ellers `done` (settlet snapshot — ingen `running`
  persisteres; ved run-slut er alt settlet).
- `message`: `_tool_label(name, input)` — samme som live working_step's `detail`.

## Opgaver (TDD, commit pr. unit)

1. **Plan-doc** (denne fil). Commit.

2. **Server-capture** i `_build_turn_blocks` (`core/services/visible_runs.py:268`):
   - Ny ren helper `_build_progress_blocks(tool_calls, tool_results)` → flad progress-liste
     via `_tool_label`. Kaldes fra `_build_turn_blocks`, blokke appended EFTER tool_use/tool_result.
   - Fail-open: try/except om progress-genereringen (aldrig bryd blok-bygningen).
   - Flag-gate: allerede centraliseret i `_persist_session_assistant_message` (persisterer kun
     content_json når `structured_content_v2_enabled()`). Ingen ekstra gate nødvendig — hvis flag
     OFF, persisteres HELE blok-arrayet ikke (inkl. progress). Verificeres i test.
   - `content_blocks_to_text` (`core/services/content_blocks.py`): allerede kun `type=="text"` →
     progress udelades gratis. Tilføj eksplicit test der beviser det.
   - **Tests** (`tests/test_content_blocks.py`, `tests/test_turn_accumulator_wiring.py`):
     - `content_blocks_to_text` ignorerer progress.
     - `_build_progress_blocks` producerer forventet flad progress fra en tool-call/result-sekvens
       (rækkefølge, message via label, status error/done, `parent_tool_use_id=null`).
     - `_build_turn_blocks` inkluderer progress efter tool-parrene.
     - Tom tur → ingen progress.

3. **Desk-render** (progress = content_json/render-only, wire/persist urørt):
   - `sseProtocol.ts`: tilføj `progress` til `ContentBlock`-union.
   - `foldToolResults.ts`: bevar `progress`-blokke (pass-through, ikke drop).
   - `groupReadSearch.ts`: passerer allerede ukendte typer uændret (else-gren) — verificér.
   - Ny komponent `ProgressTrail.tsx`: foldbart "Forløb"-spor m. status-ikoner; default foldet
     hvis > N elementer. `BlocksRenderer` samler sammenhængende progress-blokke til ét spor.
   - **Tests**: progress renders (pure-fn/component); tekst-only + tool-only beskeder uændrede;
     foldToolResults bevarer progress.

4. **Verify:** backend pytest-suite grøn; `compileall` rørte filer; desk `vitest` + `tsc --noEmit`.

## Blast-radius
Additivt oven på content_json. Samme flag, samme persist-sti, samme render-pipeline. Ingen ny
wire-kanal, ingen ny tabel, ingen server-læser-ændring. Reversibelt via `structured_content_v2`
kill-switch (progress forsvinder sammen med resten af content_json når OFF).
