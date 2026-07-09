# Persisteret progress-træ: tool/sub-agent-progress overlever reload

**Dato:** 2026-07-09
**Status:** Godkendt design (spec 3 af 4 fra leaked-Claude-Code-læringer)
**Ejer:** Bjørn / Claude
**Kilde:** Jarvis' analyse af leaked Claude Code (`ProgressMessage` med `toolUseID` + `parentToolUseID`)
**Afhænger af:** [[project_structured_content_blocks]] (udvider content_json-modellen)

---

## 1. Problem

`workingStep` ("Kalder analyze_image…") findes live i desk-stream-state men persisteres ikke. Ved reload er al progress-narration væk — man ser kun det færdige svar + tool-kort, ikke forløbet (særligt for nested sub-agent-orkestrering, hvor "hvad kørte under hvad" går tabt). Claude Code behandler progress som en førsteklasses persisteret besked (`ProgressMessage` med `toolUseID` + `parentToolUseID`), så hele forløbet kan genindlæses.

## 2. Mål

Persistér tool/sub-agent-progress som et **træ** i `content_json`, så det overlever reload — inkl. nested sub-agent-forløb via `parent_tool_use_id`.

## 3. Besluttede valg (brainstorm + self-review-rettelse)

**VIGTIG self-review-rettelse:** `parent_tool_use_id` findes INTET sted i koden i dag (0 hits),
og `working_step`-SSE-payload bærer INGEN tool-id (kun `action`/`detail`/`step`/`status`/`run_id`).
Det eneste eksisterende parent-link er `note_agent_spawn(..., parent=agent_id)` — men `parent`
er et **agent_id**, ikke et `tool_use_id`, og det ryger til central_trace, ikke ind i turen. Derfor:

- **v1 ship FLADT** progress pr. tool (ingen tree) — det er den byggbare, værdifulde kerne:
  progress overlever reload. `tool_use_id` hentes fra den EKSISTERENDE `tool_result`-sti (som bærer
  det), IKKE fra working_step.
- **Træet (parent_tool_use_id) er eksplicit OPFØLGNING** — kræver ny plumbing der linker en
  spawnet sub-agent tilbage til det spawnende `tool_use`. Den plumbing findes ikke; bygges separat.
- **Settlet snapshot, ikke deltas:** ét progress-element pr. tool (slut-status + sidste besked).
  content_json vokser pr. tool, ikke pr. token.
- **Genbrug:** samme flag (`structured_content_v2`), samme persist-sti (content_json), samme
  render-pipeline. Ingen ny wire-kanal, ingen ny tabel.

## 4. Ikke-mål (YAGNI)

- Ingen persistering af hver live-delta (kun settlet snapshot).
- Ingen ny DB-tabel eller wire-event-familie.
- Progress indgÅr IKKE i tekst-projektionen (ikke prosa) → server-læsere urørte.

## 5. Data-model

Ny blok-type i content_json (render + persist):
```jsonc
{"type": "progress", "tool_use_id": "toolu_..", "parent_tool_use_id": null,
 "message": "Analyserede billede", "status": "running|done|error"}
```
- **v1:** `parent_tool_use_id` er altid `null` (fladt) — feltet er med i skemaet så træet kan
  tilføjes uden format-brud senere.
- `content_blocks_to_text` udelader progress-blokke (samme regel som tool_use/tool_result).

## 6. Komponenter

### 6.1 Server — capture i tur-akkumulatoren (FLADT)
Udvid tur-akkumulatoren ([project_structured_content_blocks], `_build_turn_blocks` + `_accumulate_turn_blocks`) til også at fange progress:
- **Kilde:** `tool_use_id` + status + sidste working-besked hentes fra den EKSISTERENDE
  tool_result-sti (som allerede bærer `tool_use_id` + status), suppleret med seneste
  `working_step.detail` som besked-tekst (working_step bærer `run_id`/`action`/`detail`/`step`/
  `status`, IKKE tool-id — så det kan kun give besked-teksten, ikke id-linket).
- Ved run-slut: byg ét settlet progress-element pr. tool med slut-status + sidste besked;
  `parent_tool_use_id=null` (v1 fladt).
- Emit som progress-content-blok (flag-gated via `structured_content_v2`).
- Fail-open (try/except, aldrig bryd run — samme mønster som blok-akkumulatoren).

> **Bemærk overlap:** en `tool_use`-blok bærer allerede navn+status+result. En flad progress-blok
> tilføjer primært den mellemliggende working-besked ("Analyserede billede…"). Plan-fasen skal
> vurdere om v1-værdien retfærdiggør en separat blok, eller om working-beskeden hellere bør hænges
> på selve tool_use-blokken (et felt `progress_note`) — sidstnævnte er måske enklere. Afgøres i plan.

### 6.2 Persist
Progress-blokke indgår i `content_json`-array'et ved run-slut (allerede mekanismen — ingen ny persist-kode).

### 6.3 Klient — træ-render
- `apps/jarvis-desk/src/lib/`: en render-transform der bygger et træ fra progress-blokkenes `parent_tool_use_id` og indlejrer dem under deres forælder-tool.
- Komponent: indrykket, foldbart progress-træ m. status-ikoner (kører/færdig/fejl). Default foldet hvis stort.
- Overlever reload fordi det læses fra `content_json` (via `messageToBlocks`).

## 7. Test

- Progress-blok round-trip: server bygger settlet progress → content_json → klient rekonstruerer træ.
- Tekst-projektion udelader progress (unit på `content_blocks_to_text`).
- Træ-bygning (klient unit): flad liste m. parent-links → korrekt nested træ; manglende parent → rod-niveau; cyklus-guard.
- Fail-open: progress-capture-fejl bryder ikke run.
- Flag OFF → ingen progress-blokke persisteres (uændret adfærd).

## 8. Grounding-forbehold til plan-fasen
- **Emitter chat-runtimen `parent_tool_use_id` for nested sub-agenter i dag?** (council/swarm/agent-spawn). Verificér i Task 1. Hvis IKKE → degradér til fladt progress pr. tool (ingen tree) indtil spawn-relationen wires — spec'en holder, kun tree-delen venter.
- Præcis form af `working_step`-system_event-payload (tool_id/detail) som capture-kilde.
- Sub-agent-spawn-event-navn + hvor parent-relationen bæres.

## 9. Blast-radius

Additivt oven på content_json: samme flag, samme persist-sti, samme render-pipeline. Ingen ny wire-kanal, ingen ny tabel, ingen server-læser-ændring (tekst-projektion udelader progress). Reversibelt via kill-switch.
