# jarvis-desk — Stub- & TODO-log

Steder hvor foundation-buildet bevidst efterlod en stub eller delvis
implementation. Skal færdiggøres i de relevante mode-specs (Chat/Cowork/Code/
Memory/Scheduling) eller egne opgaver. Opdateres løbende.

## Composer
- ✅ **Attachment-vision LØST 2026-06-11:** v2-stream prepender nu samme
  `analyze_image`-direktiv som v1 (delt `apply_attachment_context` i
  `routes/attachments.py`). Jarvis kalder analyze_image(image_path=server_path) og
  ser billedet via vision-modellen. Deployet til containeren.
  - Resterende: billed-thumbnails i bruger-boblen bruger blob:-object-URL (kun i
    denne session); efter reload loades de fra serveren via `/attachments/{id}`.
    Verificér at getSession returnerer image-blocks for historiske beskeder.
- **Plugins** (`[+]`-menu): ren placeholder, lukker bare menuen. → senere.
- **Planlægningstilstand** (`[+]`-menu toggle): gemmer kun lokal state; backend
  plan-mode-flag findes ikke endnu. → Chat-spec / backend.

## Beskeder
- **Pin som kapitel** (`MessageActions.tsx`): lokal visuel markering (toggle).
  Kræver et kapitel/bookmark-koncept i backend for at være rigtigt brugbart.
  → senere.

## Sessioner
- **Session "..."-menu** (`Sidebar`): omdøb/slet kræver server-endpoints
  (kun createSession findes pt.). Eksport er klient-side. → afklar API.

## Performance
- **Virtualisering** af transcript: ikke implementeret. Store sessioner renderer
  alle beskeder på én gang (tungt ved load). memo + tool-filter afhjælper, men
  ægte fix er windowing. → constraint noteret i foundation-spec.

## Rolle-skopering (server-kontrakt)
- **Memory/Scheduling**: rolle-skopet INDHOLD (member vs owner) håndhæves ikke
  server-side endnu — kun klient-rolle eksponeret. → Memory-spec + Scheduling-spec.

## Proaktiv outreach
- jarvis-desk er request-scoped; Jarvis kan ikke nå brugeren proaktivt når appen
  er minimeret. → egen spec (Q1 i foundation-planen).

## v2-stream (observeret i live-test 2026-06-11 aften)
- **Tool-leak:** `visible_runs_sse_v2.py` er Phase 1 (kun text_delta + working_step).
  Tool-kald wrappes IKKE som `tool_use`-blokke → tool-output (fx `[read_file]: <fil>`)
  flyder gennem som tekst og leaker i boblen. jarvis-desk har `ToolCard` klar; v2
  mangler Phase 2-oversættelsen (tool_use blocks, thinking_delta, input_json_delta).
  → backend: implementér Phase 2 i visible_runs_sse_v2.
- **Preview-panel fil-detektion:** `detectArtifacts` fanger fil-stier — men også fra
  det leaket tool-tekst, så "Åbn xxx.md"-affordances hober sig op. Bliver renere når
  tool-blokke er strukturerede. Overvej desuden: kun seneste N fil-links, eller knyt
  panel-åbning til faktiske tool_use-blokke i stedet for tekst-regex.
