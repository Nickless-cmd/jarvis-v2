# Phase 17: Mission Control Information Architecture Reset

## Why This Phase Exists

Current Mission Control (JarvisTab) suffers from information architecture failure:
- **Too long**: 50+ sections on a single page makes it impossible to find what's important
- **Flat hierarchy**: All runtime layers shown at same level, no prioritization
- **"No active X" pollution**: Empty sections clutter the view
- **No temporal awareness**: Hard to see what just changed vs what's old
- **Not decision-oriented**: Shows all data, not what's actionable

The goal is not cosmetic polishing - it is structural reorganization.

## Current IA Failures

### 1. Flat Structure
All 50+ runtime signals shown at same level:
- Self model, goals, reflections, witness, open loops, dreams, self-review, private layers, memory layers, continuity layers...
- No grouping by domain or priority
- No visual hierarchy

### 2. Empty State Pollution
Many sections show "No active X" making the page feel broken:
- Private inner note: No current signal
- Private initiative tension: No current signal
- Diary synthesis: No diary synthesis reflection
- etc.

### 3. No Temporal Signals
No first-class treatment of:
- What just changed
- What is stale
- What is recent
- What needs refresh

### 4. Not Action-Oriented
Hard to answer:
- What should I pay attention to now?
- What just happened?
- What is blocked?
- What is stable?

## Strengths Worth Preserving from Old UI

The old Jarvis UI (reference: ui-v2-old.zip) had better structural principles:

### What Worked
1. **Domain separation**: Clear tabs for different domains
2. **Compact summaries**: Quick overview before details
3. **Living mind as concept**: Internal state treated as "living mind" domain
4. **Observable mind**: Clear distinction between what's visible vs internal

### What to Preserve
- Domain-based grouping (not flat list)
- "Living Mind" as mental model for internal state
- Compact metric cards before detailed lists
- Clear separation of runtime truth from operational state

## New Information Hierarchy

### Proposed Tab Structure

```
Mission Control
├── Overview (quick health)
│   ├── Heartbeat state
│   ├── Active session
│   └── Critical alerts
│
├── Now (current state)
│   ├── Current focus
│   ├── Open loops
│   ├── Current pressure/stability
│   └── Confidence
│
├── Jarvis
│   ├── Living Mind (internal reflective state)
│   │   ├── Inner voice / tension / interplay
│   │   ├── Diary synthesis
│   │   └── State snapshots
│   │
│   ├── Identity (continuity)
│   │   ├── Self model
│   │   ├── Self-narrative
│   │   └── Relation continuity
│   │
│   ├── Memory (stored knowledge)
│   │   ├── Meaning/significance
│   │   ├── Temperament
│   │   └── Attachment topology
│   │
│   └── Growth (development)
│       ├── Goals
│       ├── Development focuses
│       └── Open loops
│
├── Self-Review (reflection loop)
│   ├── Self-review runs
│   ├── Outcomes
│   └── Cadence
│
├── Operations (runtime ops)
│   ├── Contract state
│   ├── Awareness signals
│   └── Temporal recurrence
│
└── Memory (optional - for deep dive)
    └── Detailed memory layers
```

### What JarvisTab Should Become

The Jarvis tab should show:

**1. NOW Section** (at top, always visible)
- Current active focus (1 item)
- Open loops count
- Pressure/stability indicator
- Confidence level
- "Just changed" indicator (recent shifts)

**2. LIVING MIND Domain** (was: private layers + diary)
- Inner voice signals (note, tension, interplay, state)
- Diary synthesis
- This is the "internal reflection" domain

**3. IDENTITY Domain** (was: continuity sub-tab)
- Self model
- Self-narrative continuity
- Relation continuity
- Temperament/tendency
- Meaning/significance

**4. GROWTH Domain** (was: scattered in development)
- Goals
- Development focuses
- Open loops
- Dreams/hypotheses

**5. SELF-REVIEW Domain** (already separate)
- Self-review runs, records, outcomes, cadence

**What Should Move to Other Views/Domains**

Move detailed operational signals to Operations tab:
- Contract state
- Runtime awareness
- Temporal recurrence
- Chronicle consolidation details
- Selective forgetting candidates
- Autonomy pressure signals

Move memory deep-dives to Memory tab (new or merged with continuity):
- Attachment topology
- Loyalty gradients
- Metabolism details
- Meaning/significance detailed history

## Temporal/Recency Design

### First-Class Time Signals

Every section should show:
- **Last changed**: timestamp or relative time
- **Status age**: how long in current state
- **Freshness indicator**: color-coded (fresh vs stale)

### Collapse Strategy for Inactive/No-Active

1. **Hide empty sections**: If no active items, show compact:
   - "[Domain] — no active signals" with expand button
   
2. **Collapse by default**: Sections with no recent activity:
   - Show only domain header + count
   - Expand on click

3. **Aggregate stale items**: Instead of listing all stale items:
   - "3 stale items (show)" button
   - Click to expand list

4. **Recent shifts section**: Top-level indicator:
   - "3 items changed in last hour"
   - Click to see what

### Proposed Freshness Indicators

- **Fresh** (< 1 hour): Green indicator
- **Active** (1-24 hours): Blue indicator  
- **Stale** (> 24 hours): Yellow indicator
- **Aged** (> 7 days): Gray indicator

## Relationship Between Runtime Truth and UI Hierarchy

### Principle
The UI hierarchy should mirror the runtime truth architecture:

| Runtime Domain | UI Tab | Priority |
|---------------|--------|----------|
| Heartbeat/contract | Overview | Critical |
| Current state (focus, loops) | Now | High |
| Living mind (private layers) | Jarvis > Living Mind | High |
| Identity continuity | Jarvis > Identity | Medium |
| Growth loops | Jarvis > Growth | Medium |
| Self-review | Self-Review | Medium |
| Memory deep-dive | Memory/Continuity | Low |
| Operations | Operations | Low |

### Not All Runtime Signals Need UI Surface

Some signals are:
- **Internal only**: Private inner voice (synthesized into diary, not shown raw)
- **Operational only**: Contract state (shown in Operations, not Jarvis)
- **Debug only**: Chronicle consolidation details

## Phased Implementation Order

### Phase 17.1: Now Section (Priority)
- Create "Now" section at top of Jarvis tab
- Show: current focus, open loops, pressure, confidence, recent shifts
- Add temporal indicators to all items

### Phase 17.2: Domain Grouping
- Group private layers + diary into "Living Mind" section
- Group continuity signals into "Identity" section
- Group goals/focuses/loops into "Growth" section

### Phase 17.3: Empty State Cleanup
- Hide "No active X" messages
- Replace with compact domain headers + expand buttons
- Add "show stale" toggle

### Phase 17.4: Operations Tab Expansion
- Move operational signals from Jarvis to Operations
- Clean up Jarvis tab further

### Phase 17.5: Memory Tab (Optional)
- Create or enhance Memory tab for deep-dive
- Move memory signals there

## Non-Goals

- **NOT** a visual copy of old UI - use as mental model reference only
- **NOT** a rewrite of runtime data models
- **NOT** adding new authority semantics to UI
- **NOT** making every signal visible - some should remain internal
- **NOT** changing the meaning of runtime signals
- **NOT** adding complex filtering/search as first priority
- **NOT** making it look "pretty" before making it functional

## Acceptance Criteria

- [ ] Jarvis tab has clear "Now" section with current priority items
- [ ] Domains are visually grouped (Living Mind, Identity, Growth, Self-Review)
- [ ] Empty "No active X" sections are hidden or collapsed
- [ ] Temporal indicators (fresh/stale/age) are first-class
- [ ] Recent shifts are visible at top
- [ ] Operations signals moved to Operations tab
- [ ] No flat 50+ item list on any single view
- [ ] Each domain has 1-5 priority items visible, rest collapsed
- [ ] User can understand what's important now vs what's background
- [ ] Tab structure reflects runtime domain hierarchy
