# Jarvis Unified UI

This zip is a **frontend-only unified shell** based on your two mock references:
- `ChatView.jsx` → chat-first hierarchy
- `MissionControl.jsx` → palette, panel treatment, operator feel

## What it is
A modular React/Vite frontend with:
- one shell
- one sidebar
- two rooms/routes in the same app:
  - Chat
  - Mission Control
- a clear backend adapter boundary in `src/lib/adapters.js`

## Structure
- `src/app/` → route-level pages
- `src/components/layout/` → shell + sidebar pieces
- `src/components/chat/` → transcript + composer
- `src/components/shared/` → main-agent panel + secondary support
- `src/lib/adapters.js` → the **only file Codex should wire to backend first**
- `src/mocks/mockData.js` → removable mock data source
- `src/styles/global.css` → shared theme/layout

## Integration rule for Codex later
Ask Codex to:
1. keep the component structure
2. replace `src/lib/adapters.js` with real backend fetch calls
3. preserve the shell/layout/theme
4. wire these backend truths first:
   - main agent selection
   - available configured targets
   - send message
   - mission control summary surfaces

## Why this is safer
Codex no longer has to guess the product structure.
It only has to connect a known shell to backend truth.
