# v2-stream Phase 2 — tool_use-blokke + tool-leak fix

**Status:** spec
**Author:** Claude (med Bjørn)
**Created:** 2026-06-12
**Trigger:** Live-test af jarvis-desk viste (1) tool-leak — `[read_file]: <indhold>`
i boblen, og (2) preview-panel der hober tilfældige fil-stier op.

## Rod-årsag (verificeret)

- `start_visible_run` udsender `capability`-events for tool-kald, men de bærer
  **ingen tekst** (`{type, tool, status}`). Tool-resultat-teksten (`[read_file]: …`)
  ryger i `_resolved_result_texts` → fodres til **modellen**, streames/persisteres
  aldrig.
- Alle `delta`-events streamer udelukkende **modellens egne tokens**.
- **Tool-leaken er derfor modellen der selv ekkoer** det rå tool-format ind i sit
  svar (deepseek-flash er svag nok til at papegøje formatet).
- Preview-panel-ophobningen er en **følge**: `detectArtifacts` fanger fil-stier fra
  den leaket tekst.

## Løsning — to dele

### Del A — Tool-leak

**A1 Prompt-instruks (rod):** Høj-salient sektion i `prompt_contract` (tail-anchored,
nær tool-instruks): tool-resultater er kun til modellen; gengiv ALDRIG
`[værktøjsnavn]:`-blokke eller rå fil-dumps i svaret — referer med egne ord.

**A2 Stream-backstop (fordi prompt alene ikke holder på flash):** Bufret linje-filter
i v2-translatoren. Holder kun tilbage når en linje *starter* med `[`; samler til
newline; dropper linjen hvis den matcher `^\s*\[<kendt_toolnavn>\]:`. Regex bygges
fra de **faktisk registrerede toolnavne** (ikke vilkårlig `[x]:`). Flush ved stream-
slut. Minimal latency.

### Del B — Phase 2 tool_use-blokke

I `visible_runs_sse_v2.translate_to_v2`: `capability`-events oversættes til
strukturerede v2 content-blocks i stedet for `system_event`-wrap:

- `type == "tool_call"` (eller capability-plan med `tool_name` + `arguments`):
  luk åben text-block → `content_block_start(tool_use, id, name, input)` →
  `content_block_stop` → genåbn ny text-block (interleaved index++).
- `type == "tool_result"`: struktureret tool_result-blok (status ok/error) bundet
  til samme `tool_use_id`.
- `sse_v2_events.ContentBlockStart` understøtter allerede `block_type="tool_use"`
  med `tool_id`/`tool_name`/input — ingen protokol-ændring nødvendig.

Index-håndtering: hver tool-blok og hver genåbnet text-blok får stigende index, så
klienten kan rekonstruere interleaved rækkefølge.

## Klient (jarvis-desk)

- `streamReducer`: håndtér `tool_use`-block-start/stop → byg ToolCall-block i state.
- `MessageRow`/rich: render `tool_use`-blocks via eksisterende **ToolCard**.
- `detectArtifacts`: bind preview-panel-affordances til faktiske `tool_use`-blokke
  (fil-args) i stedet for tekst-regex → ophobning forsvinder.

## Tests

**Backend (pytest):**
- A2: bufret filter dropper `[read_file]: x`-linje, beholder normal tekst, beholder
  `[` der ikke er tool-echo (fx markdown-link `[tekst](url)`), flush ved slut.
- B: capability tool_call → tool_use block_start/stop med korrekt name/input/index;
  tool_result → result-blok; text-blok lukkes/genåbnes korrekt; interleaved indexes.

**Frontend (vitest):**
- streamReducer bygger tool_use-block fra v2-events; MessageRow renderer ToolCard;
  detectArtifacts kun fra tool_use fil-args.

## Rækkefølge
Backend (A1+A2+B) TDD → frontend TDD → samlet container-deploy + live-verifikation.

## Rollback
Per-del git revert. A2/B er additive i translatoren; A1 er en prompt-sektion.
