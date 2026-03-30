# Phase 17b: MC Tab Migration Map

## Why This Phase Exists

Previous parity attempt showed a critical failure:
- Old UI tabs were made visible in the UI
- But several had no real backend backing
- Jarvis tab was pushed away/diminished
- This created fake/empty-feeling tabs

The hard rule is now enforced:

> **No old-UI parity tab may become visible as an active tab until it has:**
> 1. A real data source
> 2. A real content role
> 3. Does not degrade an existing backend-backed domain

This design document creates a precise migration map from old UI tab structure to new backend domain structure, so tabs can be migrated one-by-one without losing functional UI.

## Parity Failure We Are Preventing

| Failure Mode | Consequence |
|-------------|-------------|
| Visible tabs without backend backing | Empty/fake UI, user confusion |
| Jarvis tab pushed away | Lost access to core Jarvis domains |
| Fake "More" dropdown with no content | Parity theater, not parity |
| Blind 1:1 copy of tab count | Empty sections, not functional UI |

## Strict Migration Rules

### Rule 1: Real Backend Backing Required
A tab may only be visible if there's a corresponding backend endpoint that returns meaningful data.

### Rule 2: Jarvis Protection
Jarvis tab (or its domains: Core, Identity, Continuity, Self-Review) must remain accessible. It cannot be replaced by old UI tabs until those domains are split out.

### Rule 3: Content Role Required
Each tab must have a clear content purpose - not just "show some data".

### Rule 4: Gradual Rollout
Tabs should be migrated in dependency order, not all at once.

## Tab Migration Matrix

| Old Tab/Domain | Old Role/Purpose | Closest New Backend Domain | Current Backing Status | Safe Current Destination | Migration Action | Visibility Rule |
|----------------|------------------|---------------------------|----------------------|-------------------------|------------------|----------------|
| **Overview** | Quick health summary, key metrics | `mc_overview` endpoint | ✅ FULLY BACKED | Keep as Primary Tab | None | Always visible |
| **Runs** | List of runtime executions | No direct endpoint | ❌ NO BACKING | Keep hidden or as future | Add backend + tab | NOT YET |
| **Approvals** | Pending contract/memory approvals | `mc_approvals` endpoint | ✅ FULLY BACKED (as Operations sub-feature) | Operations tab | Merge into Operations | Visible when approvals > 0 |
| **Sessions/Channels** | Active sessions and channels | No direct endpoint | ❌ NO BACKING | Keep hidden or as future | Add backend + tab | NOT YET |
| **Observability** | Event stream, logs, metrics | `mc_events` endpoint | ✅ FULLY BACKED | Keep as Primary Tab | None | Always visible |
| **Incident** | Incident management | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Cost** | Cost tracking and metrics | `mc_costs` endpoint | ✅ FULLY BACKED (in Observability) | Observability or separate tab | Make visible | Phase 17b.2 |
| **Agents** | Agent management/status | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Jarvis Core** | Current focus, loops, state | `mc_jarvis` endpoint | ✅ FULLY BACKED | Jarvis sub-tab | None | Always visible |
| **Jarvis Identity** | Self model, self-narrative | `mc_jarvis` sub-data | ✅ PARTIALLY BACKED | Jarvis sub-tab | Enhance content | Always visible |
| **Jarvis Continuity** | Relation continuity, memory | `mc_jarvis` sub-data | ✅ PARTIALLY BACKED | Jarvis sub-tab | Enhance content | Always visible |
| **Jarvis Self-Review** | Self-review runs/outcomes | No direct endpoint | ❌ NO BACKING | Jarvis sub-tab | Add backend | Phase 17b.3 |
| **Policy** | Policy management | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Skills** | Jarvis skills/capabilities | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Memory** | Memory/continuity deep-dive | `mc_jarvis` sub-data | ✅ PARTIALLY BACKED | Keep in Jarvis or future | Split from Jarvis | Phase 17b.4 |
| **Intelligence** | Intelligence signals | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Mind** | Mind/living mind signals | `mc_jarvis` sub-data | ✅ PARTIALLY BACKED | Keep in Jarvis | Split from Jarvis | Phase 17b.4 |
| **Council** | Council runs/deliberations | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Hardening** | Hardening signals | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Lab** | Experimental features | No direct endpoint | ❌ NO BACKING | Keep hidden | Never (deprecated) | NOT YET |
| **Debug** | Debug/traces | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Host** | Host/system status | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Workspace** | Workspace files/state | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |
| **Self** | Self model deep-dive | No direct endpoint | ❌ NO BACKING | Keep hidden | Add backend + tab | NOT YET |

## Which Tabs Are Real Now vs Future

### Currently Fully Backed (Safe)
- Overview
- Observability  
- Operations (approvals)
- Jarvis (Core, Identity, Continuity sub-tabs)

### Can Be Made Visible Soon (Phase 17b.2)
- Cost (migrate from Observability)

### Future (Require Backend Work)
- Runs
- Sessions/Channels
- Incident
- Agents
- Policy
- Skills
- Memory (split from Jarvis)
- Mind (split from Jarvis)
- Intelligence
- Council
- Hardening
- Debug
- Host
- Workspace
- Self
- Self-Review (in Jarvis)

## Protection Rule for Jarvis Tab

Jarvis tab must remain as the primary way to access:
- Core (current focus, loops, state)
- Identity (self model, self-narrative)
- Continuity (relation continuity, memory)
- Self-Review (self-review runs/outcomes)

Until these domains are split into separate top-level tabs, Jarvis must stay visible and not be pushed aside by old UI tabs that lack backing.

## Mapping Old UI Domains to New Backend Truth

| Old UI Domain | New Runtime Truth Layer | Notes |
|---------------|----------------------|-------|
| Overview | `mc_overview` | Already mapped |
| Runs | (none yet) | Future: visible_runs tracking |
| Approvals | `mc_approvals` | Mapped to Operations |
| Sessions/Channels | (none yet) | Future |
| Observability | `mc_events`, `mc_costs` | Already mapped |
| Incident | (none yet) | Future |
| Cost | `mc_costs` | Can be split from Observability |
| Agents | (none yet) | Future |
| Jarvis Core | `mc_jarvis` > development focuses, open loops | Already mapped |
| Jarvis Identity | `mc_jarvis` > self_model, self_narrative | Already mapped |
| Jarvis Continuity | `mc_jarvis` > relation_continuity, metabolism | Already mapped |
| Jarvis Self-Review | (none yet) | Future |
| Policy | (none yet) | Future |
| Skills | (none yet) | Future |
| Memory | `mc_jarvis` sub-data | Can split from Jarvis |
| Mind | `mc_jarvis` sub-data | Can split from Jarvis |

## Phased Rollout Order

### Phase 17b.1: Current State (Already Achieved)
- Overview ✅
- Observability ✅
- Operations (approvals) ✅
- Jarvis with 4 sub-tabs ✅

### Phase 17b.2: Cost Tab (Next)
- Make Cost visible as separate tab
- Requires: `mc_costs` endpoint exists → Just add to tab bar

### Phase 17b.3: Jarvis Self-Review Enhancement
- Enhance Self-Review sub-tab in Jarvis
- Requires: Self-review backend data enhancement

### Phase 17b.4: Memory/Mind Split (Later)
- Split Memory from Jarvis (or keep in Continuity)
- Split Mind from Jarvis (or keep in Core)
- Requires: Backend domain clarification

### Phase 17b.5: Additional Tabs (Future)
- Runs - requires visible_runs backend
- Sessions/Channels - requires session tracking backend
- Incident - requires incident backend
- Agents - requires agent management backend

## Non-Goals

- **NOT** making all old UI tabs visible at once
- **NOT** creating fake/empty tabs for parity theater
- **NOT** replacing Jarvis with unbacked old UI tabs
- **NOT** broad backend rewrite to support all tabs
- **NOT** making tabs visible before they have content role
- **NOT** copying old UI tab count without data backing

## Acceptance Criteria

- [ ] Current backed tabs (Overview, Observability, Operations, Jarvis) remain functional
- [ ] Jarvis tab is protected and not pushed away
- [ ] Cost tab can be made visible in Phase 17b.2
- [ ] Migration matrix clearly shows which tabs need backend work
- [ ] No tab is visible without real data source
- [ ] Tab visibility rules are enforced in code
- [ ] Future tabs are documented in this plan
