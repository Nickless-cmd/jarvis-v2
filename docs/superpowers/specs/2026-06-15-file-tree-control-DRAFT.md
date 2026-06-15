# File-tree-styring + preview/editor — DRAFT (Bjørns design)

**Dato:** 2026-06-15
**Status:** UDKAST — afventer plan (køres EFTER user-mgmt Fase C, API-key-revocation, og backlog F+H)
**Forfatter:** Bjørn (design) — fanget af Claude

Naturlig udvidelse af `open_ui_panel` / app-self-control-mønstret: Jarvis (og brugeren)
kan styre fil-træet og åbne filer i preview/editor — så en bruger der ikke kan finde en
fil bare kan få Jarvis til at highlighte den.

## Funktioner

| Funktion | Hvad den gør | Eksisterer? |
|----------|--------------|-------------|
| Åbn file tree | Vis filstruktur i højre panel | Delvist — code mode har allerede et file tree |
| Highlight filer | Markér specifikke filer i træet | ❌ Mangler |
| Luk file tree | Skjul panelet igen | ❌ Mangler |
| Klik → preview | Åbn fil i preview panel | Delvist — preview panel findes |
| Klik → editor/terminal | Åbn fil i lokal editor eller terminal | ❌ Mangler |

## Design — udvid `open_ui_panel`

```
open_ui_panel:
  - panel: "preview"                                  → åbn preview
  - panel: "file_tree"                                → åbn file tree
  - panel: "file_tree", highlight: ["src/auth/users.py"] → åbn + highlight
  - action: "close"                                   → luk panel

file_tree klik:
  - venstre klik → preview
  - højre klik   → "Åbn i editor" / "Åbn i terminal"
```

## Preview-rendering

Når en fil markeres (af Jarvis eller bruger) skal der være mulighed for at åbne den i et
**preview-panel ved siden af** ELLER i **editor**, med:
- **Kode-filer** → code view / syntax-highlight (som Jarvis' kodeblokke i chatview)
- **Almindelig tekst** → ren tekst-rendering

## Use-cases (Bjørn)

- Bruger: "hvor er auth-filen?" → Jarvis åbner file tree med highlight på `users.py`.
- Bruger har svært ved at finde en fil → Jarvis highlighter den i træet.
- Udvikler klikker på en fil → vælger preview eller editor.

## Åbne spørgsmål til plan-fasen

- "Editor" = den lokale OS-editor (via operator-bridge `xdg-open`?) eller en in-app editor?
- "Terminal" = den eksisterende code-mode terminal-rude (cd til filens mappe)?
- Highlight-protokol: backend `open_ui_panel(panel="file_tree", highlight=[...])` →
  desk file-tree-komponent scroller-til + markerer. Genbrug `app_action_request`/
  `ui_panel_store`-mønstret.
- Preview af kode vs. tekst: genbrug chatview'ets kode-renderer (samme highlight-lib).
