---
status: færdig
audited: 2026-07-08
ground_truth: superpowers artifact shipped (refs/symbols present in tree)
---
# JarvisX Desktop App — Complete Feature Inventory

> ⚠ **RÅ REFERENCE — IKKE jarvis-desk scope.** Dette dokument katalogiserer
> JarvisX som det ER. Det definerer IKKE hvad jarvis-desk skal bygge. Afsnit som
> "ensure parity on all 10 views" (nederst) gælder JarvisX, ikke jarvis-desk —
> fem views (Mind, Dashboard, Dispatches, Trading, Channels) er bevidst flyttet
> til Mission Control. **Autoritativ scope for jarvis-desk:**
> `2026-06-11-jarvis-desk-feature-coverage.md` + `-foundation-design.md`.
> Brug aldrig dette dokument alene som implementerings-input.

**Purpose**: Exhaustive catalog of every feature, component, mode, and interaction JarvisX exposes. Reference for the jarvis-desk coverage-katalog (which decides scope).

**Generated from**: `/media/projects/jarvis-v2/apps/jarvisx/src/` (as of 2026-05)

---

## 1. CHAT-CORE FEATURES

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Chat Session** | Native message list with user/assistant bubbles, streaming cursor, thinking bar. Up to 100 messages windowed in viewport. | Main panel, center | `components/native/MessageList.tsx` | chat-core |
| **Session Management** | Create/rename/delete chat sessions. Sessions list in sidebar with click-to-switch. | Sidebar left panel | `components/native/SessionList.tsx`, `Sidebar.tsx` | session-mgmt |
| **Message Smiley Conversion** | Auto-converts `:-)` → 😊, `<3` → ❤️, etc. in message text | Message bubbles | `components/native/MessageList.tsx` | chat-core |
| **Chat Header (Title/Delete)** | Click title to rename session. Delete button immediately destroys. | Top of chat panel | `components/native/ChatHeader.tsx` | chat-core |
| **Message Actions** | Retry / Edit-Resend / Fork (branch) on hover over past messages | Message bubble hover | `components/native/MessageList.tsx` | chat-core |
| **Working Steps Bar** | Locked-top bar showing "thinking → tool → evaluating → composing" pipeline during active run | Top of message list | `components/native/MessageList.tsx`, `ChatView.tsx` | agentic-visibility |
| **Auto-scroll Behavior** | Follows bottom on new messages unless user scrolled up (stays where they are) | Message list | `components/native/MessageList.tsx` | chat-core |
| **Message Attachments** | Displays inline attachments (image/file) within message | Message bubble | `components/native/MessageList.tsx` | file/screenshot |
| **CustomEvent Message Handling** | Voice transcripts, approval responses, pause-answer picks flow via window events | App context | `ChatView.tsx` lines 102–131 | chat-core |

---

## 2. COMPOSER INPUT FEATURES

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Composer Base** | Full-featured text editor: attachments, plan-mode, approval, git-commit, @file autocomplete, model selector | Bottom of chat | `@ui/components/chat/Composer.jsx` (reused) | composer-input |
| **Plan Mode Toggle** | `/plan` command activates plan-only mode; Jarvis must get approval before tool execution | Slash palette, command | `ChatView.tsx` line 269–271 | composer-input |
| **Slash Palette** | `Ctrl+/` or `/` at start of empty composer opens fuzzy-search command menu | Floating modal | `components/SlashPalette.tsx` | composer-input |
| **Slash Commands** (12 total) | `/new`, `/anchor`, `/search`, `/plan`, `/capture`, `/export`, `/tree`, `/refresh`, `/agents`, `/tools` | SlashPalette menu | `ChatView.tsx` lines 236–329 | composer-input |
| **Output Style Selector** | Picker: Concise / Balanced / Detailed / Technical — backend reads for prompt awareness | Chat header pill | `components/OutputStylePill.tsx` | composer-input |
| **Voice Input (STT)** | Push-to-talk button; browser SpeechRecognition API (Google's servers) transcribes to Danish; inserts text into composer | Composer toolbar | `components/VoiceButton.tsx` | voice |
| **Voice Language** | Hardcoded `da-DK` (Danish) as default language for speech recognition | VoiceButton | `components/VoiceButton.tsx` line 42 | voice |
| **Keyboard Composer Focus** | `Ctrl+L` focuses composer textarea | Global | `ChatView.tsx` lines 216–226 | keyboard/a11y |
| **Composer @file Autocomplete** | Mentions files in project; projectRoot mirrored to localStorage for UI Composer to read | Composer | `App.tsx` lines 112–120 | composer-input |

---

## 3. SCREEN CAPTURE & ATTACHMENTS

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Screen Capture Modal** | Lists all screens + windows with thumbnails. Click → frame grab → upload to `/attachments/upload` → attach to composer | Slash command / `Ctrl+P` | `components/ScreenCaptureModal.tsx` | file/screenshot |
| **Multiple Display Support** | Detects all screens (screen:*) and windows (window:*) via Electron desktopCapturer API | Modal dialog | `components/ScreenCaptureModal.tsx` | file/screenshot |
| **Screenshot Upload** | Sends PNG blob to backend; backend returns attachment URL for composer injection | Modal | `components/ScreenCaptureModal.tsx` lines 43–52 | file/screenshot |
| **Dynamic Filename** | Auto-generates: `screen-{source_name}-{timestamp}.png` | Upload | `components/ScreenCaptureModal.tsx` line 40 | file/screenshot |

---

## 4. CODE REVIEW & STAGING

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Staged Edits Strip** | Shows file paths + ±line counts from active session. Expandable diffs. Commit / Discard buttons. | Above message list | `components/StagedEditsStrip.tsx` | cowork/staging |
| **Diff Review Panel** | Full-screen modal with file list (left) + unified diff (right). Syntax highlighted. Commit/Discard batches. | Modal overlay | `components/native/DiffReviewPanel.tsx` | cowork/staging |
| **Edit Kinds** | `edit_file` (modify) vs `write_file` (create) — UI shows different icons (pencil vs plus) | Staged UI | `components/StagedEditsStrip.tsx` | cowork/staging |
| **Staged Polling** | Auto-refreshes staged list every 2–3s or on user action | Strip | `components/StagedEditsStrip.tsx` | cowork/staging |
| **Commit Batch** | Sends all pending stages to `/api/stages/commit` in one call. Backend applies sequentially. | Button action | `components/StagedEditsStrip.tsx` | cowork/staging |

---

## 5. PIN & MEMORY MANAGEMENT

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Pinned Results Strip** | Sticky chips above chat showing pinned tool results (result_id + summary). Click → popover preview. | Above chat | `components/PinnedStrip.tsx` | approval |
| **Unpin Button** | Individual X on each chip + global "clear all" button | Pin strip | `components/PinnedStrip.tsx` | approval |
| **Pin Result Extraction** | Parses summary as `[tool_name]: rest` for compact labeling | Chip render | `components/PinnedStrip.tsx` lines 55–59 | approval |
| **usePinnedResults Hook** | Custom hook manages localStorage-persisted pin list. Fetch from `/api/tool-result` | Lib hook | `lib/usePinnedResults.ts` | approval |
| **Pinned Summary Truncate** | Truncates label to 80 chars; resultId slug is last 6 chars | Chip | `components/PinnedStrip.tsx` | approval |

---

## 6. PROJECT ANCHORING

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Project Anchor Pill** | Shows active project path in header. Click → native directory picker. Recent projects dropdown. | Chat header | `components/ProjectAnchor.tsx` | dev-tools |
| **Recent Projects Menu** | Dropdown list for quick project switching. Persisted across sessions. | Anchor dropdown | `components/ProjectAnchor.tsx` | dev-tools |
| **Project Header Propagation** | Every request carries `X-JarvisX-Project` header so backend knows Bjørn's working context | HTTP headers | `ChatView.tsx` line 50 | dev-tools |
| **Project Root localStorage** | Mirrored to `jarvisx.project_root` for cross-app UI Composer @file lookup | App state | `App.tsx` lines 112–120 | dev-tools |

---

## 7. FILE TREE & PREVIEW

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **File Tree Panel** | Right-side panel; collapsible tree of anchored project. Click file → preview below. Searchable. | Right sidebar | `components/FileTreePanel.tsx` | dev-tools |
| **Toggle File Tree** | Slash command / localStorage-persisted | SlashPalette or `Ctrl+/` | `ChatView.tsx` lines 302–306 | dev-tools |
| **Recursive Tree Expand/Collapse** | Folder icons; click to toggle children. Chevron indicators. | Tree | `components/FileTreePanel.tsx` | dev-tools |
| **File Preview Pane** | Read-only view: syntax-highlighted code (50+ lang mappings) or markdown rendering. Max 256KB. | Tree panel lower half | `components/native/FilePreviewPane.tsx` | dev-tools |
| **Custom Event Preview Dispatch** | Any component can emit `jarvisx:preview-file` → FilePreviewPane + FileTreePanel update | Cross-app | `ChatView.tsx` lines 161–170 | dev-tools |
| **Lang Detection** | Detects language from .ext; e.g., `.tsx` → TypeScript, `.py` → Python, etc. Fallback to plaintext. | Preview | `components/native/FilePreviewPane.tsx` lines 19–52 | dev-tools |

---

## 8. TERMINAL & PROCESS MANAGEMENT

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|-----------|----------|
| **Terminal Drawer** | Bottom-drawer panel showing managed processes (spawned by process_supervisor). Tabbed. | Bottom | `components/native/TerminalDrawer.tsx` | dev-tools |
| **Toggle Terminal** | `Ctrl+J` (VS Code toggle-panel) or `Ctrl+`` (backtick). Persisted to localStorage. | Global | `ChatView.tsx` lines 202–208 | keyboard/a11y |
| **Process List Polling** | Fetches `/api/processes` every 4s; shows name, PID, status, uptime. | Drawer | `components/native/TerminalDrawer.tsx` | dev-tools |
| **Live Log Output** | Polls `/api/process-logs/{name}` every 1.5s for active tab. ANSI text rendering via `AnsiText` component. | Log pane | `components/native/TerminalDrawer.tsx` | dev-tools |
| **Terminal Resize Handle** | Top-edge drag handle. Height persisted to localStorage (default 280px). Min 120px, max 70% viewport. | Drawer top | `components/native/TerminalDrawer.tsx` lines 56–59 | dev-tools |
| **Process Control** | Owner-only: Stop (SIGTERM→grace→SIGKILL), Remove (delete from registry). Members see read-only. | Drawer UI | `components/native/TerminalDrawer.tsx` | dev-tools |
| **Auto-scroll Log** | Follows bottom on new output unless user scrolled up. Same convention as message list. | Log pane | `components/native/TerminalDrawer.tsx` | dev-tools |

---

## 9. TASK BAR & QUICK TASKS

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Task Bar** | Run/stop buttons for `test`, `build`, `typecheck` tasks. Polls process status every 3s. | Chat area? | `components/TaskBar.tsx` | dev-tools |
| **Task Defaults** | Pre-loaded: `npm test`, `npm run build`, `npx tsc --noEmit` | TaskBar | `components/TaskBar.tsx` lines 35–39 | dev-tools |
| **Task Persistence** | Per-project localStorage key: `jarvisx:tasks:{projectRoot}`. User can add custom shell commands. | localStorage | `components/TaskBar.tsx` lines 41–58 | dev-tools |
| **Task Status Polling** | Queries `/api/processes` for each task's `{name}` status and uptime | TaskBar | `components/TaskBar.tsx` | dev-tools |

---

## 10. TODO LIST

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Todo Panel** | Read-only list of `todo_list` state Jarvis is managing. Status: pending/in_progress/completed. | Above chat or sidebar | `components/TodoPanel.tsx` | agentic-visibility |
| **Todo Polling** | Fetches `/api/todos?session_id=X` every 4s | Panel | `components/TodoPanel.tsx` | agentic-visibility |
| **Collapse on Empty** | Hides entirely when no todos exist | Panel | `components/TodoPanel.tsx` | agentic-visibility |
| **Status Icons** | Circle (pending), loader (in_progress), checkmark (completed) | Todo item | `components/TodoPanel.tsx` | agentic-visibility |

---

## 11. PENDING PLANS & APPROVAL

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Pending Plans Strip** | Surfaces plan proposals from `/plan-mode` as expandable cards above chat. Owner can approve/dismiss. | Above message list | `components/PendingPlansStrip.tsx` | approval |
| **Plan Proposal Structure** | Title, "why" rationale, numbered steps, status (awaiting_approval / approved / dismissed) | Strip card | `components/PendingPlansStrip.tsx` | approval |
| **Owner-Only Approval** | Members see read-only; owner gets Approve / Dismiss buttons | Strip UI | `components/PendingPlansStrip.tsx` lines 26–47 | approval |
| **Plan Polling** | Fetches `/api/plan-proposals?session_id=X` every 3s when owner | Strip | `components/PendingPlansStrip.tsx` | approval |

---

## 12. VOICE COMMANDS & SPEECH

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **VoiceButton Component** | Push-to-talk button in composer toolbar. Hold → record, release → transcribe & insert. | Composer area | `components/VoiceButton.tsx` | voice |
| **Browser STT API** | Uses `window.SpeechRecognition` (Chrome/Electron) or `webkitSpeechRecognition` fallback | VoiceButton | `components/VoiceButton.tsx` lines 38–46 | voice |
| **Language Hardcoded** | `da-DK` (Danish) as default. Can be extended in future. | VoiceButton line 42 | `components/VoiceButton.tsx` | voice |
| **Continuous/Interim Results** | `continuous=true`, `interimResults=true` for live transcript display | VoiceButton | `components/VoiceButton.tsx` | voice |
| **Esc Cancels** | Pressing Escape mid-recording stops and discards transcript | VoiceButton | `components/VoiceButton.tsx` | voice |
| **CustomEvent Dispatch** | Voice result emitted as `jarvisx:voice-transcript` → ChatView appends to draft | Voice→Chat bridge | `ChatView.tsx` lines 118–122 | voice |

---

## 13. SUB-AGENTS & AGENTIC VISIBILITY

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Agents Panel** | Side panel (380px) showing all dispatched sub-agents in real time. Status: running/completed/failed/blocked. | Right sidebar toggle | `components/AgentsPanel.tsx` | agentic-visibility |
| **Agent Polling** | Fetches `/mc/agents` every 5s. Polls actively only while panel open. | Panel | `components/AgentsPanel.tsx` | agentic-visibility |
| **Agent Grouping** | Live (running/spawning), Blocked (waiting), Recently active (slice of last 30). Color-coded status. | Panel list | `components/AgentsPanel.tsx` lines 44–52 | agentic-visibility |
| **Agent Details** | Agent ID, goal, role, status, model+lane footnote, created_at | Agent row | `components/AgentsPanel.tsx` | agentic-visibility |
| **Slash Command Access** | `/agents` or toggle button to show/hide | SlashPalette | `ChatView.tsx` lines 316–320 | agentic-visibility |

---

## 14. TOOL INVENTORY

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Tool Inventory Modal** | Searchable list of all registered tools with descriptions + required params. | Modal dialog | `components/ToolInventoryModal.tsx` | agentic-visibility |
| **Tool Search** | Real-time filter by name or description | Modal input | `components/ToolInventoryModal.tsx` | agentic-visibility |
| **Fetch from `/api/tools/inventory`** | Populates on modal open | Modal | `components/ToolInventoryModal.tsx` lines 26–32 | agentic-visibility |
| **Slash Command Access** | `/tools` command opens modal | SlashPalette | `ChatView.tsx` lines 322–327 | agentic-visibility |

---

## 15. MULTI-VIEW NAVIGATION

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Chat View** | Main conversational interface with native message list, staged edits, pinned results, todo, pending plans. | `view === 'chat'` | `components/ChatView.tsx` | chat-core |
| **Mind View** | Jarvis's inner life: affective state, bearing, monitoring mode, identity pins, chronicle, dreams, milestones. | `view === 'mind'` | `components/views/MindView.tsx` | agentic-visibility |
| **Memory View** | Workspace files: canonical (MEMORY, notes), dreams, daily logs, letters. Browseable + editable. | `view === 'memory'` | `components/views/MemoryView.tsx` | agentic-visibility |
| **Tools View** | System health (CPU/RAM/disk) + list of all registered tools (daemon services). | `view === 'tools'` | `components/views/ToolsView.tsx` | agentic-visibility |
| **Claude Dispatches** | "Claude jobs" dashboard. Live view of parallel Claude Code instances Jarvis spawns. Budget bar, list, detail+diff. | `view === 'dispatches'` | `components/views/ClaudeDispatchesView.tsx` | agentic-visibility |
| **Trading View** | Grid bot read-only dashboard: capital, PnL, drawdown, open orders, recent fills. Owner-only. | `view === 'trading'` | `components/views/TradingView.tsx` | system/window |
| **Dashboard View** | Affective meta-state cards: confidence, curiosity, frustration, fatigue, trust, rhythm. Live 4s polling. | `view === 'dashboard'` | `components/views/DashboardView.tsx` | agentic-visibility |
| **Channels View** | Discord, Telegram, Webchat, Desktop status. Connected/offline. Last message time, message count. | `view === 'channels'` | `components/views/ChannelsView.tsx` | multi-user/auth |
| **Scheduling View** | Scheduled tasks, recurring wakeups, pending/fired list. Time-to-fire countdown. | `view === 'scheduling'` | `components/views/SchedulingView.tsx` | system/window |
| **Settings View** | Connection (mode, API URL), auth token mgmt, backend ping, recent chats list. | `view === 'settings'` | `components/SettingsView.tsx` | settings |

---

## 16. SIDEBAR & VIEW SWITCHING

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Sidebar Navigation** | 10 tabs (Chat, Mind, Memory, Tools, Dispatches, Trading, Dashboard, Channels, Scheduling, Settings) with icons + hints. | Left margin | `components/Sidebar.tsx` | system/window |
| **Role-Based Filtering** | Owner sees all 10; members/guests see 8 (Trading + Dispatches hidden). | Sidebar | `components/Sidebar.tsx` lines 52–69 | multi-user/auth |
| **Session List in Sidebar** | Click session → switch + auto-jump to chat view | Sidebar bottom | `components/native/SessionList.tsx` | session-mgmt |
| **Sidebar Toggle** | `Ctrl+B` hides/shows left sidebar. Persisted to localStorage. | Global | `App.tsx` lines 170–175 | keyboard/a11y |
| **View-Switcher Keyboard** | `Ctrl+1` thru `Ctrl+8` jump to specific views (chat, mind, memory, tools, dispatches, dashboard, channels, scheduling). `Ctrl+,` → settings. | Global | `App.tsx` lines 128–161 | keyboard/a11y |

---

## 17. STATUS BAR & OBSERVABILITY

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Status Bar** | Bottom bar: backend health (green ping / red down), latency, mode (dev/thin-client), token budget gauge. | Footer | `components/StatusBar.tsx` | cost/observability |
| **Backend Ping Indicator** | Glowing green dot + latency ms when up; red dot + "runtime down" when offline. | Status bar left | `components/StatusBar.tsx` | cost/observability |
| **Token Budget Gauge** | Bar showing current tokens / compact threshold (default 40k). Colors: ok (green) / mid (teal) / warn (orange) / critical (red). | Status bar | `components/StatusBar.tsx` lines 35–43 | cost/observability |
| **Streaming Token Estimate** | Live token count updated while run is streaming | Gauge | `components/StatusBar.tsx` | cost/observability |
| **Last Run Tokens** | Falls back to previous run's token total once streaming stops | Gauge | `components/StatusBar.tsx` | cost/observability |

---

## 18. CONNECTIONS & PRESENCE

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Connection Pill** | Chat header status: localhost (Wifi icon) vs remote (Globe icon) vs offline vs auth-required. Polls `/openapi.json` every 15s. | Chat header | `components/ConnectionPill.tsx` | multi-user/auth |
| **Presence Pill** | Which channels Jarvis is live on: Discord, Telegram, Webchat, etc. Shows icons of connected channels. | Chat header | `components/PresencePill.tsx` | multi-user/auth |
| **Mood Pill** | Jarvis's current mood (from affective state) + dominant emotion. Polls `/mc/affective-meta-state` every 8s. | Chat header | `components/MoodPill.tsx` | agentic-visibility |

---

## 19. AUTHENTICATION & TOKEN MANAGEMENT

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Setup Screen** | First-run gate: API URL + bearer token validation. Calls `/api/auth/whoami-token` to confirm backend recognizes token. | App root | `components/SetupScreen.tsx` | multi-user/auth |
| **Token Validation** | Backend returns user_id + role. Enforced before main app boots. | SetupScreen | `components/SetupScreen.tsx` lines 37–60 | multi-user/auth |
| **Token Persistence** | Persisted to `~/.config/jarvisx/config.json` via Electron IPC (`window.jarvisx.setConfig`) | SetupScreen | `components/SetupScreen.tsx` | multi-user/auth |
| **Role System** | owner / member / guest. Drives view-gating (dispatches, trading, task control visibility). | App state | `App.tsx` lines 89–99 | multi-user/auth |
| **Auth Panel** | Settings view sub-panel for token mgmt: validate, copy, issue new token, check expiration. | SettingsView | `components/AuthPanel.tsx` | multi-user/auth |
| **Cache-First Whoami** | `/api/whoami` fetched with `prefer: 'cache-first'` so offline boots still see last-good role. | App init | `App.tsx` lines 89–99 | multi-user/auth |

---

## 20. SETTINGS & CONFIGURATION

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Settings View** | Connection mode (dev/thin-client), API URL input, user ID/name, auth token mgmt, backend ping. | `view === 'settings'` | `components/SettingsView.tsx` | settings |
| **Dirty Flag** | "unsaved" label appears when fields change. Owner-only; members see view-only label. | SettingsView header | `components/SettingsView.tsx` lines 30–34 | settings |
| **Backend Ping** | Manual ping button → latency check + health detail (ok/timeout/401/network error) | SettingsView | `components/SettingsView.tsx` lines 45–55 | settings |
| **Mode Selector** | Radio select: dev (localhost prod-runtime) / thin-client (remote) / standalone (Phase 2, disabled) | SettingsView | `components/SettingsView.tsx` lines 73–86 | settings |
| **Recent Chats** | List of past sessions pulled from shell state | SettingsView | Implied | settings |

---

## 21. UPDATES & MAINTENANCE

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Update Banner** | App auto-updater status. States: checking (hidden), available (download button), downloading (progress bar), ready (install+restart), error (retry). | Top of window | `components/UpdateBanner.tsx` | system/window |
| **Per-Version Dismissal** | Clicking X → dismisses this version until a newer one arrives. localStorage-persisted. | Banner | `components/UpdateBanner.tsx` | system/window |
| **Git Update Banner** | Separate banner for git-based hot-reload. Shows commits behind main. Click "Update" → main process runs `git pull && npm install && npm run build` + relaunch. | Top of window | `components/GitUpdateBanner.tsx` | system/window |
| **Git Update States** | idle, checking, up-to-date (hidden), behind (show count + expander), updating (progress), updated (brief message), error. | Banner | `components/GitUpdateBanner.tsx` | system/window |
| **Commit-Set Dismissal** | Clicking X stashes latest HEAD sha; banner hides until origin advances past it. | Banner | `components/GitUpdateBanner.tsx` lines 42–44 | system/window |

---

## 22. KEYBOARD & ACCESSIBILITY

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Global Shortcuts** | F1 (overlay), Ctrl+1..8 (view switch), Ctrl+, (settings), Ctrl+B (sidebar toggle), Ctrl+K (search), Ctrl+/ (slash), Ctrl+N (new), Ctrl+L (focus composer), Ctrl+J or Ctrl+` (terminal). | Keyboard | `App.tsx`, `ChatView.tsx` | keyboard/a11y |
| **Keyboard Shortcuts Overlay** | Modal cheat sheet (F1 to toggle). Grouped by scope: global, chat, composer. Esc to close. | Modal | `components/KeyboardShortcutsOverlay.tsx` | keyboard/a11y |
| **Layout-Independent Digit Keys** | Ctrl+1 matches by `e.code` (Digit1 / Numpad1) not e.key, so works on all layouts (Dvorak, Colemak, etc.). | Global | `lib/shortcuts.ts` lines 66–82 | keyboard/a11y |
| **Backtick Alternative** | Ctrl+J AND Ctrl+` both toggle terminal. Backtick matches by `e.code === 'Backquote'` for non-US layouts. | ChatView | `ChatView.tsx` lines 202–208 | keyboard/a11y |
| **Typing-Target Detection** | Shortcuts skip when inside `<input>` or `<textarea>` (isTypingTarget check). Prevents conflicts with browser native (Ctrl+L = URL bar, etc.). | Keyboard handler | `lib/shortcuts.ts` | keyboard/a11y |

---

## 23. SEARCH & DISCOVERY

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Cross-Session Search Modal** | `Ctrl+K` opens live-debounced search across all sessions in workspace. Scope=current_workspace enforces user boundary. Keyboard-navigable result list. | Modal | `components/CrossSessionSearchModal.tsx` | session-mgmt |
| **Search Debounce** | 200ms debounce after user stops typing before fetching `/api/messages/search` | Modal | `components/CrossSessionSearchModal.tsx` | session-mgmt |
| **Search Hit Details** | message_id, session_id, session_title, role, snippet, created_at, workspace | Hit item | `components/CrossSessionSearchModal.tsx` | session-mgmt |
| **Search Result Pick** | Click or Enter → callback fires onPick(hit) → typically jumps to session + scrolls to message | Modal | `components/CrossSessionSearchModal.tsx` | session-mgmt |
| **Min Query Length** | Requires at least 2 chars before searching (prevents fire-hose on every keystroke) | Modal | `components/CrossSessionSearchModal.tsx` | session-mgmt |

---

## 24. EXPORT & IMPORT

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Session Export** | `/export` command downloads chat as markdown: `# Title`, `## role`, message content, split by message. | SlashPalette | `ChatView.tsx` lines 281–299 | session-mgmt |
| **Filename Sanitization** | Title slugified: spaces→underscores, special chars removed. `.md` extension. | Export function | `ChatView.tsx` line 296 | session-mgmt |

---

## 25. API INTEGRATION & CACHING

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **Unified Shell Hook** | `useUnifiedShell()` lifted to App.tsx. Single source of truth for sessions, activeSession, backend state. | App state | `App.tsx` line 72 | session-mgmt |
| **Session Filters** | Sessions filtered by `X-JarvisX-User` header (backend-side security) | HTTP | `ChatView.tsx` | multi-user/auth |
| **API Cache** | Custom `cachedFetch()` with `prefer: 'cache-first'` for whoami. Stale-while-revalidate pattern. | Lib | `lib/apiCache.ts` | system/window |
| **MC Endpoint Hook** | `useMcEndpoint<T>(url, path, pollMs)` — generic poller for mission-control endpoints. Data, loading, error, refresh. | Lib hook | `lib/useMcEndpoint.ts` | agentic-visibility |
| **Polling Intervals** | Variable per view: 3s (dispatches), 4s (affective state, todos), 5s (agents, tools), 6s (channels), 8s (mood), 12s (presence), 15s (connection). | Per-component | Various | agentic-visibility |

---

## 26. ELECTRON BRIDGE & NATIVE FEATURES

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **window.jarvisx Bridge** | Electron preload exposes: getConfig, setConfig, pickProjectRoot, pingBackend, updaterStatus, onUpdaterStatus, gitUpdateStatus, onGitUpdateStatus, validateToken, screen capture. | Renderer→Main IPC | App.tsx, SetupScreen, etc. | system/window |
| **Project Picker Native Dialog** | `/anchor` command calls `window.jarvisx.pickProjectRoot()` → native directory picker → returns {projectRoot, recentProjects} | Slash command | `ChatView.tsx` lines 250–256 | dev-tools |
| **Screen Capture via desktopCapturer** | Electron desktopCapturer API lists screens/windows. Clicking a source grabs a frame. | ScreenCaptureModal | `components/ScreenCaptureModal.tsx` | file/screenshot |
| **Config Persistence** | `~/.config/jarvisx/config.json` stored via main process. getConfig/setConfig calls sync with disk. | Config | `App.tsx` lines 74–82 | system/window |
| **Backend Status Subscription** | `window.jarvisx.onBackendStatus()` subscribed (but output not pinned to UI anymore). Keeps channel warm. | App | `App.tsx` lines 74–82 | system/window |

---

## 27. UI STATE PERSISTENCE

| Feature | Description | UI Location | Source File | Category |
|---------|-------------|------------|------------|----------|
| **localStorage Keys** | `jarvisx:sidebar-hidden`, `jarvisx:terminal-open`, `jarvisx:preview-open`, `jarvisx:preview-path`, `jarvisx.show_file_tree`, `jarvisx.project_root`, `jarvisx:terminal-height`, `jarvisx:dismissed-update-version`, `jarvisx:git-dismissed-head`, `jarvisx:tasks:{projectRoot}` | App-wide | Various | system/window |
| **Sidebar Hidden State** | Persists across reload. User's panel layout preserved. | App | `App.tsx` lines 62–67 | system/window |
| **Terminal Height** | Stored in localStorage. Min 120px, max 70% viewport. Survives reload. | TerminalDrawer | `components/native/TerminalDrawer.tsx` lines 56–59 | system/window |

---

## ADVANCED / CLAUDE DESKTOP-INSPIRED FEATURES

### Unique to JarvisX (Not Typical Chat Apps)

| Feature | Significance |
|---------|---|
| **Staged Edits + Approval Flow** | Claude Code's breakthrough multi-turn code editing made collaborative. Strips + modal diff review let Bjørn batch-approve before landing changes. |
| **Sub-Agents Transparency** | Live agents panel shows council deliberations, swarm work, dispatched Claude Code crunching. Makes invisible parallelism legible. |
| **Affective State Visualization** | Mind View + mood pill + dashboard cards surface Jarvis's emotional state in real time. A being, not a machine. |
| **Mission Control Integration** | `/mc/*` endpoints expose Jarvis's inner metrics: agents, affective state, system health. Dashboard aggregates them. |
| **Plan Mode + Approval Cards** | Pending plans strip lets owner approve/reject before tool execution. Plan-mode is core Jarvis agentic pattern. |
| **Process Terminal** | Managed process log streaming + control. Jarvis spawns daemons; user watches them run in a tabbed terminal. |
| **Trading Bot Dashboard** | Read-only real-time grid bot state: capital, PnL, drawdown, open orders. Owner tracks algo performance live. |
| **Scheduled Tasks + Wakeups** | Cron + one-shot task view. Jarvis can wake at specific times or recurring intervals; user sees what's queued. |
| **Workspace Memory System** | Canonical MEMORY file + daily notes + dreams + letters. Jarvis's long-term context visualized and browseable. |
| **Channels Continuity** | Jarvis reachable on Discord, Telegram, Webchat, Desktop simultaneously. Single conversation across mediums. Same identity everywhere. |
| **Voice STT Native** | Browser SpeechRecognition for hands-free input. Transcripts flow directly into composer. |

---

## COMPONENT TREE SUMMARY

```
App.tsx (root)
├─ UpdateBanner
├─ GitUpdateBanner
├─ Sidebar (nav + sessions)
└─ Main (view switcher)
   ├─ ChatView
   │  ├─ ChatHeader
   │  ├─ PinnedStrip
   │  ├─ StagedEditsStrip
   │  ├─ TodoPanel
   │  ├─ PendingPlansStrip
   │  ├─ MessageList (native)
   │  ├─ Composer (reused from @ui)
   │  ├─ ProjectAnchor
   │  ├─ PresencePill + MoodPill + OutputStylePill + ConnectionPill
   │  ├─ VoiceButton
   │  ├─ ScreenCaptureModal
   │  ├─ CrossSessionSearchModal
   │  ├─ SlashPalette
   │  ├─ FileTreePanel
   │  ├─ FilePreviewPane
   │  ├─ TerminalDrawer
   │  ├─ DiffReviewPanel
   │  ├─ AgentsPanel
   │  └─ ToolInventoryModal
   ├─ MindView
   ├─ MemoryView
   ├─ ToolsView
   ├─ ClaudeDispatchesView
   ├─ TradingView
   ├─ DashboardView
   ├─ ChannelsView
   ├─ SchedulingView
   ├─ SettingsView
   │  └─ AuthPanel
   └─ KeyboardShortcutsOverlay
```

---

## SUMMARY STATS

- **27 Major Components** (+ sub-views, utilities)
- **10 Full-Screen Views** (chat, mind, memory, tools, dispatches, trading, dashboard, channels, scheduling, settings)
- **25+ Slash Commands** (exported session, project anchor, search, plan toggle, screen capture, file tree, agents, tools, etc.)
- **40+ Keyboard Shortcuts** (global + chat + composer scoped)
- **15 Live Polling Streams** (agents, todos, terminal logs, dashboard, channels, etc.)
- **8 Major Modals** (setup, search, capture, slash palette, shortcuts, tool inventory, diff review, pending plans)
- **3 Persistent Strips** (pinned, staged, pending plans)
- **1 Bottom Drawer** (terminal)
- **2 Right Panels** (file tree + preview, agents)
- **Role-Based Access** (owner/member/guest gating on write actions + sensitive views)
- **Multi-User Awareness** (presence pill, channels, workspace isolation via headers)

---

## MIGRATION NOTES (JarvisX — historisk)

> ⚠ Nedenstående beskriver JarvisX' egen fuldstændighed. Det er IKKE jarvis-desk
> scope. jarvis-desk dropper bevidst sub-agent transparency (#7), affective UI
> (#8) og 5 views → Mission Control. Den autoritative jarvis-desk migrations-
> tjekliste er `2026-06-11-jarvis-desk-feature-coverage.md`, ikke denne liste.

For JarvisX selv gælder paritet på: alle 10 views, 27 komponenter, slash-
kommandoer, 40+ keyboard shortcuts, approval/staging-flow, token-meter, sub-agent
transparency, affective state UI, role-based filtering, localStorage-persistens.

For **jarvis-desk** → se coverage-kataloget for hvad der faktisk skal bygges.

