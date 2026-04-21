# Phase 17a: Mission Control Shell Parity Reset

## Why This Phase Exists

Current Jarvis UI (both Chat and Mission Control) feels:
- **Too flat**: No clear shell hierarchy
- **Dump-like**: Shows all runtime layers without structure
- **Not operator-like**: Lacks the "control console" feel of old MC
- **Disconnected from live data**: Not leveraging websockets/live events effectively
- **Heavy on polling**: Unnecessary background refresh

The goal is to recreate the old MC's shell and operator experience as closely as possible, but:
- On the new backend
- With real live data
- With new runtime truth
- Without old code debt
- And without heavy polling / heavy UI load

This is about shell parity, not pixel-perfect copy.

## What the Old UI Got Right Structurally

### Shell Structure
1. **Clear header bar**: Status, workspace, current session context
2. **Left sidebar**: Navigation, session list, quick actions
3. **Main content area**: Tabbed views with clear hierarchy
4. **Right panel**: Support/inspector panel that can collapse
5. **Bottom composer**: Fixed at bottom, always accessible

### Operational Feel
1. **Console aesthetic**: Dark, professional, data-dense but readable
2. **Status indicators**: Clear visual language for state
3. **Quick actions**: Buttons for common operations
4. **Live feedback**: Clear indication of what's happening now
5. **Tab-based navigation**: Clear separation of domains

### Layout Principles
1. **Fixed header**: Always visible status/controls
2. **Collapsible panels**: Can hide/show sidebars
3. **Responsive**: Works on different screen sizes
4. **Keyboard-friendly**: Common shortcuts

## Shell Parity Goals

### Primary Goals
- Recreate the "operator console" feel
- Make Jarvis feel like a living system, not a data dump
- Create clear visual hierarchy
- Make the UI feel "live" without heavy polling

### Not Goals (Do NOT)
- Blind pixel copy of old UI
- Replicate old bugs or bad patterns
- Make everything visible at once
- Heavy polling as default strategy

## Header Layout

### Current State
```
Mission Control
[Tab1 Overview] [Tab2 Operations] [Tab3 Observability] [Tab4 Jarvis > Core/Identity/Continuity/Self-Review]
[Refresh button] [Freshness indicator] [Last event indicator]
```

### Target Shell Parity
```
┌─────────────────────────────────────────────────────────────────┐
│ MISSION CONTROL          [Status: active] [WS: connected] [⟳] │
├─────────────────────────────────────────────────────────────────┤
│ [Overview] [Operations] [Observability] [Jarvis ▼]            │
├─────────────────────────────────────────────────────────────────┤
│ Content Area (varies by tab)                                  │
│                                                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Required Header Elements
1. **Title/brand**: "Mission Control" or context-aware
2. **Status indicators**: Heartbeat, websocket connection, last update
3. **Refresh control**: Manual refresh button
4. **Tab navigation**: As currently implemented

## Sidepanel Strategy

### Current State
- Chat: Left sidebar for sessions, right sidebar for support rail
- MC: Minimal sidebar, mostly full-width content

### Target Shell Parity
Keep two-panel layout for both views:

**Chat View:**
- Left: Session list / history (collapsible)
- Center: Chat transcript + composer
- Right: Support rail (context-aware, collapsible)

**MC View:**
- Left: Quick nav / filters (optional, collapsible)
- Center: Tab content (Overview, Operations, Observability, Jarvis)
- Right: Detail drawer (on demand)

## Content/View Strategy

### Tab Structure (Keep)
```
Overview     → Quick health summary
Operations   → Contract, heartbeat, runtime ops
Observability → Event stream, logs
Jarvis       → Core, Identity, Continuity, Self-Review
```

### Jarvis Sub-tabs (Enhance)
```
Core         → Current focus, loops, pressure, stability (NOW section!)
Identity     → Self model, self-narrative
Continuity   → Relation continuity, memory
Self-Review  → Review runs, outcomes
```

### Content Loading Strategy
| Data Type | Loading Strategy |
|-----------|-----------------|
| Current focus/loops | Fetch on tab switch, then websocket updates |
| Open loops | Fetch on tab switch |
| Historical events | Lazy load, paginated |
| Detail data | Fetch on demand when drawer opens |
| Heavy aggregates | Cache, refresh every 30s or on user action |

## ChatView/Composer Placement

### Current (Keep)
```
┌────────────────────────────────────────────────────┐
│ Chat Header (title, subtitle, actions)             │
├────────────────────────────────────────────────────┤
│                                                    │
│              Chat Transcript                       │
│                                                    │
│                                                    │
├────────────────────────────────────────────────────┤
│ Composer (fixed bottom)                            │
└────────────────────────────────────────────────────┘
         [Support Rail - optional right panel]
```

### Target Parity
- Keep current layout - it already matches old shell well
- Focus on making chat feel "live" via websocket
- Add clearer status indicators in header

## Mapping: Old Shell → New Backend

| Old UI Element | New Backend | Loading |
|---------------|-------------|---------|
| Session list | `visible_sessions` API | On open + WS |
| Current session messages | Websocket stream | Live |
| Runtime state | `mc_jarvis` endpoint | On tab switch |
| Development focuses | `development_focuses` | On Jarvis tab |
| Open loops | `open_loop_signals` | On Jarvis tab |
| Private layers | Various private_* endpoints | On Jarvis tab |
| Contract state | `runtime_contract` | On Operations tab |
| Event stream | Websocket events | Live |

## Live Data Strategy with Minimal Calls

### Websocket-First (Real-time)
- Chat messages
- Heartbeat ticks
- Runtime events (if using event bus)
- Session state changes

### Fetch-on-Open (Cached)
- Tab content (Overview, Operations, Observability, Jarvis)
- Session list

### Fetch-on-Demand (Lazy)
- Detail drawer content
- Historical data
- Filtered lists

### Polling (Rare/Manual)
- Only for:
  - "Force refresh" button
  - Background sync every 60s when tab is idle
  - Not for real-time updates by default

### Polling Frequency Guidelines
| Component | Strategy | Frequency |
|-----------|----------|-----------|
| Chat messages | Websocket | N/A |
| Session list | Fetch on focus + WS | N/A |
| MC Overview | Fetch on tab switch | Manual refresh |
| MC Operations | Fetch on tab switch | Manual refresh |
| MC Observability | Fetch on tab switch + infinite scroll | Manual load more |
| MC Jarvis | Fetch on tab switch | Manual refresh |
| Detail drawer | Fetch when opened | N/A |

## Phased Implementation Order

### Phase 17a.1: Header Shell
- Add clear header with status indicators
- Make header consistent across Chat and MC
- Add websocket connection status indicator

### Phase 17a.2: Sidebar Parity
- Ensure collapsible sidebars work consistently
- Make session list more prominent in Chat
- Add quick-nav to MC if needed

### Phase 17a.3: Live Feel
- Implement websocket for chat messages
- Add "live" indicators throughout UI
- Reduce polling to minimum

### Phase 17a.4: Composer Position
- Verify composer is always fixed at bottom
- Ensure keyboard accessibility

### Phase 17a.5: Polish
- Add loading states
- Add error states
- Add empty states (not "No active X" everywhere)

## Non-Goals

- **NOT** pixel-perfect copy of old UI
- **NOT** making everything visible at once
- **NOT** heavy polling by default
- **NOT** replicating old bugs
- **NOT** changing backend models to fit UI
- **NOT** hardcoding personality in UI
- **NOT** making UI "pretty" before making it functional

## Acceptance Criteria

- [ ] Header shows clear status (heartbeat, connection, freshness)
- [ ] Tabs work consistently across Chat and MC
- [ ] Sidebar is collapsible and works in both views
- [ ] Composer is fixed at bottom in Chat
- [ ] Live indicators show when websocket is connected
- [ ] Polling is minimal (no continuous background polling)
- [ ] Tab content loads on switch, not eagerly
- [ ] Detail drawer loads on demand
- [ ] UI feels like "operator console", not data dump
- [ ] Empty states are handled gracefully (not "No active X" everywhere)
