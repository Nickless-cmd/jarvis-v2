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

## v2-stream Phase 2 — ✅ LØST 2026-06-12
- **Tool-leak:** Rod-årsag var IKKE ustrukturerede tool-events (capability-events
  bærer ingen tekst) — det var **modellen der selv ekkoede** rå tool-format i svaret.
  Fix: (A1) prompt-instruks mod ekko + (A2) `ToolEchoFilter` i translatoren der dropper
  `[<kendt_tool>]:`-linjer i streamen. Begge live på containeren.
- **Phase 2 tool_use-blokke:** `visible_runs_sse_v2.translate_to_v2` oversætter nu
  capability tool_result/capability → `tool_use` content-blocks (start + input_json_delta
  + stop) + system_event(tool_result) m. status. ToolCard renderer dem (var allerede wiret).
- **Preview-panel fil-detektion:** `detectArtifacts` binder nu fil-artifacts til FAKTISKE
  tool_use-kald (target_path/file_path/path) i stedet for tekst-regex → ingen ophobning
  af tilfældige prosa-stier.
  - Spec: docs/superpowers/specs/2026-06-12-v2-stream-phase2-toolblocks-design.md

## v2-stream — resterende (senere)
- thinking_delta-oversættelse (reasoning-blokke) i translatoren er stadig Phase 1.
- Mac + Windows builds af jarvis-desk.
- Ring-only systray (pulsing/dot — Jarvis' ønske).
