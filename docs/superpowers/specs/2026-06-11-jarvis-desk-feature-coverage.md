# jarvis-desk — Feature-coverage katalog

**Status:** levende reference (opdateres når modes designes)
**Created:** 2026-06-11
**Formål:** Sikre at jarvis-desk når feature-paritet med JarvisX uden at glemme
noget. Mapper hver bevaret feature → flade → spec → om fundamentet kan holde den.

Baseret på fuld inventering af JarvisX
(`docs/superpowers/specs/2026-06-11-jarvisx-feature-inventory.md`: 100+ features,
27 komponenter, 10 views).

> **Scope-autoritet:** DETTE katalog (+ foundation-spec'en) definerer hvad
> jarvis-desk er. Inventerings-dokumentet er en RÅ reference over JarvisX og dets
> "ensure parity på alle 10 views" gælder IKKE jarvis-desk — fem views er
> bevidst flyttet til Mission Control (se nedenfor). Brug aldrig inventeringen
> som implementerings-scope.

## Princip for hvad der er med

jarvis-desk = **arbejds-app** (relationen + det du laver med Jarvis).
Observability/maskineri → **Mission Control** (web).

- **Mode-slider** (arbejds-modes): Chat, Cowork, Code
- **Sekundær nav** (opslags-flader, rolle-skopet): Memory, Scheduling, Settings
- **Ude** → Mission Control: Mind, Dashboard, Dispatches, Trading, Channels

"Fundament holder?" = kan App-shell + Rich-rendering foundation-spec'en bære
featuren uden arkitektur-ændring. ✅ = ja (søm/mekanisme findes), ➕ = kræver
lille tilføjelse i den relevante mode-spec, men ingen foundation-ændring.

---

## CHAT-mode (→ Chat-spec, lag 1)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Native besked-liste, bobler, streaming-cursor | MessageList.tsx | ✅ MessageRow + StreamContext |
| Session mgmt (opret/omdøb/slet/skift) | SessionList.tsx | ✅ SessionContext |
| Besked-actions: retry / edit-resend / fork | MessageList.tsx | ✅ parent_id-søm i datamodel |
| Working-steps bar (thinking→tool→composing) | MessageList.tsx | ✅ density-aware liveness (compact) |
| Auto-scroll (følg bund medmindre scrollet op) | MessageList.tsx | ✅ glemt-ting #7 |
| Besked-attachments inline (billede/fil) | MessageList.tsx | ✅ ImageBlock + content-block |
| Smiley-konvertering `:-)`→😊 | MessageList.tsx | ➕ MarkdownRenderer plugin |
| Composer: tekst, @file, model-vælger, think | Composer.jsx | ✅ Composer (shell) |
| Slash-palette + 12 slash-kommandoer | SlashPalette.tsx | ➕ Chat-spec (mekanik findes) |
| Plan-mode toggle | ChatView.tsx | ➕ Chat-spec |
| Output-style vælger (concise/detailed/...) | OutputStylePill.tsx | ➕ Composer-pill |
| Voice STT (push-to-talk, da-DK) | VoiceButton.tsx | ➕ Chat-spec (Electron-bridge) |
| Skærmbillede-capture modal | ScreenCaptureModal.tsx | ➕ Chat-spec (desktopCapturer) |
| Cross-session søgning (Ctrl+K) | CrossSessionSearchModal.tsx | ➕ Chat-spec |
| Session-eksport (markdown) | ChatView.tsx | ➕ Chat-spec |
| Pinned results strip | PinnedStrip.tsx | ➕ Chat-spec (density-aware kort) |

## COWORK-mode (→ Cowork-spec, lag 2)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Staged edits strip (filer + ±linjer, commit/discard) | StagedEditsStrip.tsx | ✅ density-aware ToolCard-mønster |
| Diff review panel (fuld-skærm, syntax) | DiffReviewPanel.tsx | ✅ CodeBlock + rich-lib |
| Edit-kinds (edit_file vs write_file ikoner) | StagedEditsStrip.tsx | ➕ Cowork-spec |
| Commit-batch (alle stages i ét kald) | StagedEditsStrip.tsx | ➕ Cowork-spec |
| Pending plans strip (forslag, approve/dismiss) | PendingPlansStrip.tsx | ✅ ApprovalCard + rolle-gate |
| Todo panel (Jarvis' intentioner, read-only) | TodoPanel.tsx | ➕ Cowork-spec |

## CODE-mode (→ Code-spec, lag 3)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Fil-træ panel (collapsible, søgbart) | FileTreePanel.tsx | ➕ Code-spec |
| Fil-preview (syntax, 50+ sprog, markdown) | FilePreviewPane.tsx | ✅ CodeBlock + MarkdownRenderer |
| Project-anchor pill + recent + native picker | ProjectAnchor.tsx | ➕ Code-spec (Electron-bridge) |
| Terminal drawer (managed processes, ANSI, tabs) | TerminalDrawer.tsx | ➕ Code-spec |
| Process-kontrol (stop/remove, owner-only) | TerminalDrawer.tsx | ✅ rolle-gate |
| Task bar (test/build/typecheck) | TaskBar.tsx | ➕ Code-spec |
| Tool inventory modal (søgbar) | ToolInventoryModal.tsx | ➕ Code-spec |
| Fuld agentic-timeline (alle tool-kald udfoldet) | MessageList.tsx | ✅ density-aware ToolCard (full) |
| Status-linje diagnostik (elapsed/tokens/forb.) | StatusBar.tsx | ✅ liveness-maskine (full density) |

## MEMORY-flade (→ Memory-spec, sekundær nav, rolle-skopet)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Member: hukommelse Jarvis har *med brugeren* | MemoryView.tsx | ⚠ klient ✅; **server-kontrakt skal defineres** i Memory-spec |
| Owner: Jarvis' fulde indre memory | MemoryView.tsx | ⚠ `require_owner` server-side — ikke klient-filter |
| Browse + redigér workspace-filer | MemoryView.tsx | ➕ Memory-spec |

> ⚠ Rolle-grænsen håndhæves af **serveren**, ikke klienten (se foundation-spec
> "Serveren er grænsen"). Foundation leverer kun `role` i context; de præcise
> member-scoped vs owner-only endpoints + 403-adfærd defineres i Memory-spec.

## SCHEDULING-flade (→ Scheduling-spec, sekundær nav, rolle-skopet)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Member: hvad Jarvis har planlagt *med brugeren* | SchedulingView.tsx | ⚠ klient ✅; **server-kontrakt** i Scheduling-spec |
| Owner: alle planlagte tasks/wakeups | SchedulingView.tsx | ⚠ `require_owner` server-side |
| Time-to-fire countdown | SchedulingView.tsx | ➕ Scheduling-spec |

## SETTINGS-flade (→ delvist i denne foundation-spec)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Setup-screen (server-URL + token + whoami) | SetupScreen.tsx | ✅ i foundation |
| Forbindelse/mode-vælger, backend-ping | SettingsView.tsx | ✅ i foundation |
| Token-mgmt panel (validér/forny/udløb) | AuthPanel.tsx | ➕ Settings-spec |
| Rolle-system (owner/member/guest) | App.tsx | ✅ i foundation (auth.role) |
| Defaults: model, thinking, trust | — | ✅ i foundation |

## SYSTEM/SHELL (→ dels foundation, dels løbende)

| Feature | JarvisX-kilde | Fundament holder? |
|---------|--------------|-------------------|
| Status-bar: backend-health, latency, token-gauge | StatusBar.tsx | ✅ i foundation |
| Connection pill / presence pill | ConnectionPill.tsx | ➕ shell (presence = let) |
| Update banner (app-updater) | UpdateBanner.tsx | ➕ system-spec (Electron) |
| Git hot-reload banner | GitUpdateBanner.tsx | ➕ system-spec |
| Keyboard shortcuts (40+, layout-uafhængig) | lib/shortcuts.ts | ➕ shell (eget lag) |
| Shortcuts-overlay (F1) | KeyboardShortcutsOverlay.tsx | ➕ shell |
| Sidebar toggle, vindue-state-persistens | App.tsx | ✅ glemt-ting #6/#8 |
| localStorage UI-state | diverse | ✅ i foundation (settings/persistens) |
| Electron-bridge (config, picker, capture, ping) | preload | ✅ findes, udvides per behov |

---

## Eksplicit UDE af jarvis-desk (→ Mission Control)

| Flade | Hvorfor ude |
|-------|-------------|
| Mind View (affektiv tilstand, chronicle, dreams) | Observability — Jarvis' indre maskineri |
| Dashboard View (mood-cards, meta-state) | Observability |
| Claude Dispatches (parallelle Claude-jobs) | Observability/kontrol |
| Trading View (grid bot PnL) | Domæne-observability |
| Channels View (Discord/Telegram status) | Multi-channel observability |
| Mood pill i chat-header | Følger Mind ud (kan genovervejes hvis du vil have et roligt mood-glimt) |
| Agents Panel (live sub-agenter) | Observability → Mission Control |

### Chat-entrypoints til flyttede flader

Nogle observability-features havde et entrypoint inde i chat (slash-kommando/
panel). Når fladen flyttes til Mission Control, skal entrypointet håndteres
eksplicit — ikke efterlades dinglende:

| Entrypoint | JarvisX-kilde | Beslutning |
|------------|--------------|------------|
| `/agents` slash → AgentsPanel | ChatView.tsx, AgentsPanel.tsx | **Fjernes** fra jarvis-desk. Sub-agent-indsigt bor i Mission Control. (Evt. senere: deep-link der åbner MC i browser — egen beslutning, ikke nu.) |
| `/tools` slash → Tool Inventory | ToolInventoryModal.tsx | **Beholdes** men flyttes til Code-mode (Bjørn 2026-06-11). |
| Mood/presence pills i chat-header | MoodPill/PresencePill.tsx | **Fjernes** (følger Mind/Channels ud). Presence kan evt. genovervejes som roligt glimt. |

---

## Dækningskonklusion

- **Alt arbejds-relateret fra JarvisX har en plads** i en af de 6 flader; alt
  observability er bevidst flyttet til Mission Control MED dets chat-entrypoints
  eksplicit afklaret (fjernet eller deep-link), ikke efterladt dinglende.
- **Fundamentet (App-shell + Rich-rendering) kan bære alle ✅-rækker** uden
  ændring; ➕-rækker er normalt arbejde i den relevante mode-spec; ⚠-rækker
  kræver en server-kontrakt defineret i deres mode-spec før de er "dækket".
- **Ingen arbejds-feature falder mellem stolene** — hver er enten placeret
  (mode/flade), eksplicit flyttet til Mission Control (med entrypoint afklaret),
  eller markeret ⚠ som server-kontrakt-afhængig.
- De cross-cutting ting fundamentet SKAL levere (og gør): rolle i context,
  density-aware rich-komponenter, liveness-maskine, content-block-datamodel,
  parent_id-søm, Electron-bridge-stel, persistens.

## Brug

Når vi starter en mode-spec (fx Cowork), åbnes dette katalog, og hver ➕-række for
den mode bliver en feature der skal designes. Når en feature er bygget, markeres
den. Sådan kommer vi beviseligt hele vejen rundt.
