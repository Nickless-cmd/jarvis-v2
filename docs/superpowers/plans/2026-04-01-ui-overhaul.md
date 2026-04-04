# UI Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overhaul the Jarvis V2 UI — split the monolithic JarvisTab into separate navbar tabs matching mock designs, add chat streaming visuals (chain-of-thought WorkingIndicator + streaming cursor), and elevate all MC tabs with the mock's visual language (monospace labels, large metric cards, progress bars, tables, sidebar panels).

**Architecture:** The existing `apps/ui/` React app stays as the single codebase. JarvisTab.jsx (4451 lines) gets decomposed into 5+ focused tab components. ChatTranscript gets a WorkingIndicator and streaming cursor. Backend SSE stream gets new event types (`working_step`, `tool_call`) to power the chain-of-thought display. The mock's design tokens (cool slate `#111214`, IBM Plex Mono) replace the current palette.

**Tech Stack:** React 18, vanilla CSS (global.css), Lucide icons, SSE streaming, FastAPI backend

**Reference files:**
- Mock ChatView: `ui-v2-old/ui-v2/ChatView.jsx`
- Mock MissionControl: `ui-v2-old/ui-v2/MissionControl.jsx`

---

## File Structure

### New files
- `apps/ui/src/components/mission-control/LivingMindTab.jsx` — Runtime subsystems (embodied, loop, idle consolidation, dream, affective, epistemic, subagent ecology, council runtime, adaptive planner, adaptive reasoning, guided learning, adaptive learning, cadence)
- `apps/ui/src/components/mission-control/DevelopmentTab.jsx` — Development focus, goals, critics, reflections, witness, temporal recurrence, open loops
- `apps/ui/src/components/mission-control/SelfReviewTab.jsx` — Self-review signals/records/runs/outcomes/cadence flow
- `apps/ui/src/components/mission-control/ContinuityTab.jsx` — World model, runtime awareness, integration carry-over, relation/promotion state
- `apps/ui/src/components/mission-control/CostTab.jsx` — Cost summary cards, provider cost table, budget controls (from mock)
- `apps/ui/src/components/mission-control/MemoryTab.jsx` — Memory table with search/filter, memory journal (from mock)
- `apps/ui/src/components/mission-control/SkillsTab.jsx` — Skills marketplace table with enable/disable (from mock)
- `apps/ui/src/components/mission-control/HardeningTab.jsx` — Presets, secrets/runtime status, doctor findings (from mock)
- `apps/ui/src/components/mission-control/LabTab.jsx` — Debug inspect, kernel queue, model benchmark (from mock)
- `apps/ui/src/components/chat/WorkingIndicator.jsx` — Chain-of-thought stepped progress display
- `apps/ui/src/components/shared/MetricCard.jsx` — Reusable large-number metric card component
- `apps/ui/src/components/shared/SectionTitle.jsx` — Monospace uppercase section label
- `apps/ui/src/components/shared/Chip.jsx` — Small status/tag chip

### Modified files
- `apps/ui/src/components/mission-control/MCTabBar.jsx` — Replace 4 primary tabs + "More" dropdown with 8-10 direct tabs
- `apps/ui/src/app/MissionControlPage.jsx` — Route to new tabs, remove jarvis sub-tab logic
- `apps/ui/src/app/useMissionControlPhaseA.js` — Add data sections for new tabs, update refresh config
- `apps/ui/src/lib/adapters.js` — Add backend calls for cost, memory, skills, hardening, lab; add SSE `working_step`/`tool_call` event handling
- `apps/ui/src/components/chat/ChatTranscript.jsx` — Add WorkingIndicator, streaming cursor
- `apps/ui/src/styles/global.css` — New design tokens, monospace font import, MetricCard styles, table styles, progress bar styles, WorkingIndicator animation, streaming cursor animation
- `apps/ui/src/lib/theme.js` — Update design tokens to match mock palette
- `apps/ui/src/app/useUnifiedShell.js` — Pass working steps from SSE to ChatTranscript
- `apps/api/jarvis_api/services/visible_runs.py` — Emit `working_step` and `tool_call` SSE events

### Deleted files
- `apps/ui/src/components/mission-control/JarvisTab.jsx` (4451 lines) — Replaced by LivingMindTab, DevelopmentTab, SelfReviewTab, ContinuityTab

---

## Task 1: Update Design Tokens & Typography

**Files:**
- Modify: `apps/ui/src/lib/theme.js`
- Modify: `apps/ui/src/styles/global.css:1-10` (root styles)

- [ ] **Step 1: Update theme.js tokens to match mock palette**

```js
export const theme = {
  bgBase:     '#111214',
  bgSurface:  '#16181c',
  bgRaised:   '#1c1f25',
  bgOverlay:  '#21252e',
  bgHover:    '#272b35',
  borderSoft: 'rgba(255,255,255,0.04)',
  borderMid:  'rgba(255,255,255,0.08)',
  borderStrong: 'rgba(255,255,255,0.13)',
  textStrong: '#e4e6ed',
  textMuted:  '#8b909e',
  textFaint:  '#4e5262',
  textGhost:  '#2d303d',
  accent:     '#3d8f7c',
  accentDim:  'rgba(61,143,124,0.10)',
  accentMid:  'rgba(61,143,124,0.18)',
  accentText: '#5ab8a0',
  accentGlow: 'rgba(61,143,124,0.25)',
  green:      '#4caf82',
  amber:      '#d4963a',
  red:        '#c05050',
  blue:       '#4a80c0',
  mono:       "'IBM Plex Mono', monospace",
  sans:       "'DM Sans', sans-serif",
}
```

- [ ] **Step 2: Add IBM Plex Mono font import and update root styles in global.css**

Add at top of `global.css`:
```css
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
```

Update `:root` / `body` styles:
```css
body { background: #111214; color: #e4e6ed; font-family: 'DM Sans', sans-serif; }
```

Add monospace utility class:
```css
.mono { font-family: 'IBM Plex Mono', monospace; }
```

- [ ] **Step 3: Update all hardcoded color values in global.css**

Search-replace the main background/text colors:
- `#0d1117` → `#111214`
- `#121923` → `#16181c`
- `#e7edf5` → `#e4e6ed`
- `#9aa7b8` → `#8b909e`
- `#49d2c3` → `#5ab8a0`
- `#28b1a3` → `#3d8f7c`

Update scrollbar styling:
```css
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #2d303d; border-radius: 2px; }
```

- [ ] **Step 4: Verify the app still renders**

Run: `cd apps/ui && npm run dev`
Open browser, confirm chat and MC pages render with updated colors.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/lib/theme.js apps/ui/src/styles/global.css
git commit -m "feat(ui): update design tokens to match mock palette — cool slate + IBM Plex Mono"
```

---

## Task 2: Create Shared UI Components (MetricCard, SectionTitle, Chip)

**Files:**
- Create: `apps/ui/src/components/shared/MetricCard.jsx`
- Create: `apps/ui/src/components/shared/SectionTitle.jsx`
- Create: `apps/ui/src/components/shared/Chip.jsx`
- Modify: `apps/ui/src/styles/global.css`

- [ ] **Step 1: Create MetricCard component**

```jsx
// apps/ui/src/components/shared/MetricCard.jsx
export function MetricCard({ label, value, sub, color, icon: Icon, alert }) {
  return (
    <div className={`metric-card ${alert ? 'metric-card-alert' : ''}`}>
      <div className="metric-card-header">
        <span className="metric-card-label mono">{label}</span>
        {Icon && <Icon size={12} />}
      </div>
      <div className="metric-card-value" style={color ? { color } : undefined}>
        {value}
      </div>
      {sub && <div className="metric-card-sub mono">{sub}</div>}
    </div>
  )
}
```

- [ ] **Step 2: Create SectionTitle component**

```jsx
// apps/ui/src/components/shared/SectionTitle.jsx
export function SectionTitle({ children }) {
  return (
    <div className="section-title mono">{children}</div>
  )
}
```

- [ ] **Step 3: Create Chip component**

```jsx
// apps/ui/src/components/shared/Chip.jsx
export function Chip({ children, color = '#4e5262', bg }) {
  const style = {
    background: bg || `${color}18`,
    border: `1px solid ${color}35`,
    color,
  }
  return <span className="chip mono" style={style}>{children}</span>
}
```

- [ ] **Step 4: Add CSS for shared components in global.css**

```css
/* ─── SHARED: MetricCard ─── */
.metric-card {
  padding: 14px 16px;
  background: #1c1f25;
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  flex: 1;
  min-width: 120px;
}
.metric-card-alert { border-color: rgba(212,150,58,0.25); }
.metric-card-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px; color: #4e5262;
}
.metric-card-label {
  font-size: 9px; letter-spacing: 0.1em; text-transform: uppercase;
}
.metric-card-value {
  font-size: 26px; font-weight: 300; color: #e4e6ed; letter-spacing: -0.02em;
}
.metric-card-sub { font-size: 9px; color: #4e5262; margin-top: 4px; }

/* ─── SHARED: SectionTitle ─── */
.section-title {
  font-size: 9px; color: #4e5262; letter-spacing: 0.12em;
  text-transform: uppercase; margin-bottom: 12px;
}

/* ─── SHARED: Chip ─── */
.chip {
  display: inline-flex; font-size: 9px; padding: 2px 7px;
  border-radius: 10px; letter-spacing: 0.06em; white-space: nowrap;
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/components/shared/MetricCard.jsx apps/ui/src/components/shared/SectionTitle.jsx apps/ui/src/components/shared/Chip.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): add shared MetricCard, SectionTitle, Chip components matching mock design"
```

---

## Task 3: Add Chat Streaming Cursor

**Files:**
- Modify: `apps/ui/src/components/chat/ChatTranscript.jsx`
- Modify: `apps/ui/src/styles/global.css`

- [ ] **Step 1: Add blinking cursor animation to global.css**

```css
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.streaming-cursor {
  display: inline-block; width: 2px; height: 14px;
  background: #5ab8a0; margin-left: 3px; vertical-align: middle;
  animation: blink 1s step-end infinite;
}
```

- [ ] **Step 2: Update ChatTranscript to show streaming cursor during pending messages with content**

Replace the message content rendering in `ChatTranscript.jsx` (lines 37-45):

```jsx
{message.content ? (
  <p>
    {message.content}
    {message.pending && <span className="streaming-cursor" />}
  </p>
) : null}
{message.pending && !message.content ? (
  <div className="thinking-indicator">
    <span className="thinking-dot" />
    <span className="thinking-dot" />
    <span className="thinking-dot" />
    <small>Jarvis is working…</small>
  </div>
) : null}
```

This means:
- When pending + no content yet → show thinking dots (existing behavior)
- When pending + content streaming in → show blinking cursor after text

- [ ] **Step 3: Verify in browser**

Open chat, send a message. During streaming:
- First: thinking dots appear
- Once first delta arrives: text appears with blinking cursor
- On done: cursor disappears

- [ ] **Step 4: Commit**

```bash
git add apps/ui/src/components/chat/ChatTranscript.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): add blinking streaming cursor to chat messages during generation"
```

---

## Task 4: Add Chain-of-Thought WorkingIndicator

**Files:**
- Create: `apps/ui/src/components/chat/WorkingIndicator.jsx`
- Modify: `apps/ui/src/components/chat/ChatTranscript.jsx`
- Modify: `apps/ui/src/app/useUnifiedShell.js`
- Modify: `apps/ui/src/lib/adapters.js`
- Modify: `apps/api/jarvis_api/services/visible_runs.py`
- Modify: `apps/ui/src/styles/global.css`

### Part A: Backend — emit working_step SSE events

- [ ] **Step 1: Add working_step SSE events to visible_runs.py**

In `_stream_visible_run()`, after the initial `run` event yield (line 292), add a `working_step` event before starting the model stream:

```python
yield _sse(
    "working_step",
    {
        "type": "working_step",
        "run_id": run.run_id,
        "action": "thinking",
        "detail": f"Preparing response via {run.provider}/{run.model}",
        "step": 0,
        "status": "running",
    },
)
```

After the model stream completes (before the `done` event), emit a completion step:

```python
yield _sse(
    "working_step",
    {
        "type": "working_step",
        "run_id": run.run_id,
        "action": "thinking",
        "detail": "Generation complete",
        "step": 0,
        "status": "done",
    },
)
```

- [ ] **Step 2: Handle working_step in SSE reader (adapters.js)**

In the `readSseStream` function in `adapters.js` (around line 1907), add a handler for the new event:

```js
if (eventName === 'working_step') handlers.onWorkingStep?.(payload)
```

- [ ] **Step 3: Commit backend + adapter changes**

```bash
git add apps/api/jarvis_api/services/visible_runs.py apps/ui/src/lib/adapters.js
git commit -m "feat: emit working_step SSE events during visible run streaming"
```

### Part B: Frontend — WorkingIndicator component

- [ ] **Step 4: Create WorkingIndicator component**

```jsx
// apps/ui/src/components/chat/WorkingIndicator.jsx
import { Loader2, CheckCircle2 } from 'lucide-react'

export function WorkingIndicator({ steps }) {
  if (!steps || steps.length === 0) return null

  const doneSteps = steps.filter(s => s.status === 'done')
  const currentStep = steps.find(s => s.status === 'running')

  if (!currentStep && doneSteps.length === 0) return null

  return (
    <div className="working-indicator">
      <div className="working-indicator-spinner">
        <Loader2 size={13} />
      </div>
      <div className="working-indicator-steps">
        {doneSteps.map((step, i) => (
          <div key={i} className="working-step done">
            <CheckCircle2 size={9} />
            <span className="mono">{step.action}</span>
          </div>
        ))}
        {currentStep && (
          <>
            <div className="working-step current">
              <span className="mono">{currentStep.action}</span>
            </div>
            <div className="working-step-detail mono">{currentStep.detail}</div>
          </>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Add WorkingIndicator CSS to global.css**

```css
/* ─── CHAT: WorkingIndicator ─── */
@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.working-indicator {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 9px 14px;
  background: #1c1f25;
  border: 1px solid rgba(255,255,255,0.08);
  border-left: 2px solid #3d8f7c;
  border-radius: 10px;
  max-width: 380px;
  margin-left: 38px;
  animation: slideUp 0.2s ease both;
}
.working-indicator-spinner {
  margin-top: 1px; color: #5ab8a0;
  animation: spin 1s linear infinite;
}
.working-indicator-steps { flex: 1; }
.working-step {
  display: flex; align-items: center; gap: 5px; margin-bottom: 2px;
}
.working-step.done { color: #4e5262; }
.working-step.done svg { color: #4caf82; }
.working-step.done .mono { font-size: 9px; }
.working-step.current { color: #5ab8a0; }
.working-step.current .mono { font-size: 10px; }
.working-step-detail { font-size: 9px; color: #4e5262; margin-top: 2px; }
```

- [ ] **Step 6: Wire working steps through useUnifiedShell**

In `useUnifiedShell.js`, add state for working steps:

```js
const [workingSteps, setWorkingSteps] = useState([])
```

In `handleSend`, pass `onWorkingStep` to `backend.streamMessage`:

```js
const assistantMessage = await backend.streamMessage({
  sessionId,
  content,
  onWorkingStep: (step) => {
    setWorkingSteps((prev) => {
      if (step.status === 'done') {
        return prev.map((s) =>
          s.step === step.step ? { ...s, status: 'done' } : s
        )
      }
      return [...prev.filter((s) => s.step !== step.step), step]
    })
  },
  onDelta: (_delta, fullText) => {
    // existing delta handler unchanged
  },
})
```

Clear working steps when stream ends (in the `finally` block):
```js
setWorkingSteps([])
```

Return `workingSteps` from the hook.

- [ ] **Step 7: Add WorkingIndicator to ChatTranscript**

Update `ChatTranscript` to accept and display working steps:

```jsx
import { WorkingIndicator } from './WorkingIndicator'

export function ChatTranscript({ messages, workingSteps }) {
  // ... existing code ...

  // After the last message, before the scroll anchor:
  {workingSteps && workingSteps.length > 0 && (
    <WorkingIndicator steps={workingSteps} />
  )}
```

Update `ChatPage.jsx` to pass `workingSteps` prop from the shell hook.

- [ ] **Step 8: Verify end-to-end**

1. Start backend: `uvicorn apps.api.jarvis_api.app:app --reload`
2. Start frontend: `cd apps/ui && npm run dev`
3. Send a chat message
4. Confirm: WorkingIndicator appears with "thinking" step → text streams in with cursor → indicator disappears on done

- [ ] **Step 9: Commit**

```bash
git add apps/ui/src/components/chat/WorkingIndicator.jsx apps/ui/src/components/chat/ChatTranscript.jsx apps/ui/src/app/useUnifiedShell.js apps/ui/src/styles/global.css
git commit -m "feat(ui): add chain-of-thought WorkingIndicator to chat with stepped progress display"
```

---

## Task 5: Decompose JarvisTab — Extract LivingMindTab

**Files:**
- Create: `apps/ui/src/components/mission-control/LivingMindTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

This is the largest extraction. LivingMindTab takes the runtime subsystem rows from JarvisTab's Core sub-tab: embodied state, loop runtime, idle consolidation, dream articulation, prompt evolution, affective meta, epistemic runtime, subagent ecology, council runtime, adaptive planner, adaptive reasoning, guided learning, adaptive learning, cadence producers, heartbeat, metabolic state.

- [ ] **Step 1: Create LivingMindTab.jsx**

Extract these functions from JarvisTab.jsx into LivingMindTab.jsx:
- `StatusPill`, `humanizeToken`, `formatFreshness` (shared helpers — import from `meta.js`)
- `embodiedStateRow`, `embodiedBucketSummary`, `embodiedUsageSummary`
- `loopRuntimeRow`, `loopRuntimeItemRow`, `loopRuntimeCounts`, `loopRuntimeCountSummary`, `loopRuntimeUsageSummary`
- `idleConsolidationRow`, `idleConsolidationBoundarySummary`
- `dreamArticulationRow`, `dreamArticulationBoundarySummary`
- `promptEvolutionRow`, `promptEvolutionBoundarySummary`
- `affectiveMetaStateRow`, `affectiveMetaUsageSummary`, `affectiveMetaBoundarySummary`
- `epistemicRuntimeStateRow`, `epistemicRuntimeUsageSummary`, `epistemicRuntimeBoundarySummary`
- `subagentEcologyRow`, `subagentRoleRow`, `subagentEcologyUsageSummary`, `subagentEcologyBoundarySummary`, `subagentEcologyCountSummary`
- `councilRuntimeRow`, `councilRolePositionRow`, `councilRuntimeUsageSummary`, `councilRuntimeBoundarySummary`, `councilRuntimeRoleSummary`
- `adaptivePlannerRow`, `adaptivePlannerUsageSummary`, `adaptivePlannerBoundarySummary`
- `adaptiveReasoningRow`, `adaptiveReasoningUsageSummary`, `adaptiveReasoningBoundarySummary`
- `guidedLearningRow`, `guidedLearningUsageSummary`, `guidedLearningBoundarySummary`
- `adaptiveLearningRow`, `adaptiveLearningUsageSummary`, `adaptiveLearningBoundarySummary`
- `cadenceProducer`, `cadenceProducerLabel`, `cadenceProducerReason`
- `metabolicHeartbeatSummary`

The export signature:
```jsx
export function LivingMindTab({ data, onOpenItem, onHeartbeatTick, heartbeatBusy }) {
  // Extract relevant data from data prop (same destructuring as JarvisTab Core section)
  // Render with mock-inspired layout:
  //   1. Feature status grid (4x2) at top — embodied, loop, dream, affective, epistemic, subagent, consolidation, prompt evolution
  //   2. Detail sections below for items with data
  //   3. Heartbeat/cadence sidebar (200px right)
}
```

Use the mock `LivingMindTab` layout pattern:
- **Feature status grid** at top (each card shows: icon, label, status dot, last activity). With 13 subsystems, use a responsive grid (`repeat(auto-fill, minmax(160px, 1fr))`). Map Jarvis subsystems to this grid:
  - Embodied State → icon: Cpu, status from `embodiedState.state`
  - Loop Runtime → icon: Activity, status from `loopRuntimeSummary.currentStatus`
  - Idle Consolidation → icon: Moon, status from `idleConsolidationSummary.lastState`
  - Dream Articulation → icon: Sparkles, status from `dreamArticulationSummary.lastState`
  - Affective Meta → icon: Heart, status from `affectiveMetaState.state`
  - Epistemic Runtime → icon: Brain, status from `epistemicRuntimeState.wrongnessState`
  - Subagent Ecology → icon: Network, status from `subagentEcologySummary.lastActiveRoleStatus`
  - Prompt Evolution → icon: Wand2, status from `promptEvolutionSummary.lastState`
  - Council Runtime → icon: Users, status from `councilRuntime.councilState`
  - Adaptive Planner → icon: Map, status from `adaptivePlanner.plannerMode`
  - Adaptive Reasoning → icon: Lightbulb, status from `adaptiveReasoning.reasoningMode`
  - Guided Learning → icon: GraduationCap, status from `guidedLearning.learningMode`
  - Adaptive Learning → icon: TrendingUp, status from `adaptiveLearning.learningEngineMode`

- **Detail rows** below for expanded items (reusing existing row renderers)
- **Cadence sidebar** (200px) showing heartbeat ticks and cadence producer states

- [ ] **Step 2: Add feature-status-grid CSS to global.css**

```css
/* ─── MC: Feature Status Grid ─── */
.feature-status-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 8px;
  margin-bottom: 16px;
}
.feature-status-card {
  padding: 12px;
  background: #1c1f25;
  border: 1px solid rgba(255,255,255,0.04);
  border-left: 3px solid #2d303d;
  border-radius: 8px;
}
.feature-status-card.active { border-left-color: #3d8f7c; border-color: rgba(255,255,255,0.08); }
.feature-status-card-header {
  display: flex; align-items: center; gap: 6px; margin-bottom: 6px;
}
.feature-status-card-header svg { color: #4e5262; }
.feature-status-card.active .feature-status-card-header svg { color: #5ab8a0; }
.feature-status-card-label {
  font-size: 11px; font-weight: 500; color: #8b909e;
}
.feature-status-card.active .feature-status-card-label { color: #e4e6ed; }
.feature-status-card-meta { font-size: 9px; color: #4e5262; }
.feature-status-card-provider { font-size: 8px; color: #2d303d; margin-top: 2px; }
```

- [ ] **Step 3: Update MCTabBar — replace "Jarvis" tab with "Living Mind"**

In `MCTabBar.jsx`, change PRIMARY_TABS:
```jsx
import { Activity, Eye, Bot, Brain, MoreHorizontal } from 'lucide-react'

const PRIMARY_TABS = [
  { id: 'overview', label: 'Overview', icon: Activity },
  { id: 'operations', label: 'Operations', icon: Bot },
  { id: 'observability', label: 'Observability', icon: Eye },
  { id: 'living-mind', label: 'Living Mind', icon: Brain },
]
```

Remove JARVIS_SUB_TABS. Remove the sub-tabbar rendering. Remove `activeJarvisSubTab` / `onJarvisSubTabChange` props.

- [ ] **Step 4: Update MissionControlPage to route to LivingMindTab**

Replace the jarvis rendering block with:
```jsx
{activeTab === 'living-mind' ? (
  <LivingMindTab
    data={sections.jarvis}
    onOpenItem={openJarvisDetail}
    onHeartbeatTick={actOnHeartbeatTick}
    heartbeatBusy={isRefreshing}
  />
) : null}
```

Remove jarvis sub-tab state and props.

- [ ] **Step 5: Verify Living Mind tab renders**

Run dev server. Navigate to Mission Control → Living Mind tab. Verify the feature status grid renders and existing data appears.

- [ ] **Step 6: Commit**

```bash
git add apps/ui/src/components/mission-control/LivingMindTab.jsx apps/ui/src/components/mission-control/MCTabBar.jsx apps/ui/src/app/MissionControlPage.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): extract LivingMindTab from JarvisTab with feature-status grid layout"
```

---

## Task 6: Extract DevelopmentTab

**Files:**
- Create: `apps/ui/src/components/mission-control/DevelopmentTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Create DevelopmentTab.jsx**

Extract from JarvisTab's Identity sub-tab:
- `developmentSnapshotRow`, `goalDirectionRow`, `selfModelCalibrationRow`, `criticPressureRow`
- `developmentFocusRow`, `goalSignalRow`, `reflectiveCriticRow`, `selfModelSignalRow`
- `reflectionSignalRow`, `reflectionHistoryRow`
- `witnessSignalRow`, `temporalRecurrenceSignalRow`
- `openLoopSignalRow`, `openLoopClosureProposalRow`
- `internalOppositionSignalRow`
- `emergentSignalRow`
- `dreamHypothesisSignalRow`, `dreamAdoptionCandidateRow`, `dreamInfluenceProposalRow`
- `selfAuthoredPromptProposalRow`, `userMdUpdateProposalRow`
- `userUnderstandingSignalRow`, `selfhoodProposalRow`

Layout: Use mock's 2-column grid style with Card containers and SectionTitle headers. Group into sections:
1. **Development Snapshot** (top summary row)
2. **Focus & Goals** (2-col: development focuses | goal signals)
3. **Reflection & Critics** (2-col: reflection signals | reflective critics)
4. **Inner Signals** (witness, temporal, open loops, emergent)
5. **Proposals** (dream adoption, influence, self-authored, USER.md, selfhood)

```jsx
export function DevelopmentTab({ data, onOpenItem }) {
  // Destructure from data.development (same source as JarvisTab Identity sub-tab)
}
```

- [ ] **Step 2: Add "Development" to PRIMARY_TABS in MCTabBar**

```jsx
import { TrendingUp } from 'lucide-react'
// Add to PRIMARY_TABS array:
{ id: 'development', label: 'Development', icon: TrendingUp },
```

- [ ] **Step 3: Route in MissionControlPage**

```jsx
{activeTab === 'development' ? (
  <DevelopmentTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
) : null}
```

- [ ] **Step 4: Verify and commit**

```bash
git add apps/ui/src/components/mission-control/DevelopmentTab.jsx apps/ui/src/components/mission-control/MCTabBar.jsx apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(ui): extract DevelopmentTab — focus, goals, reflection, inner signals"
```

---

## Task 7: Extract SelfReviewTab

**Files:**
- Create: `apps/ui/src/components/mission-control/SelfReviewTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Create SelfReviewTab.jsx**

Extract from JarvisTab's Self-Review sub-tab:
- `selfReviewSignalRow`, `selfReviewRecordRow`, `selfReviewRunRow`, `selfReviewOutcomeRow`, `selfReviewCadenceSignalRow`
- `selfReviewFlowSummary`, `selfReviewStageLabel`

Layout — use the flow summary as a visual pipeline at the top:
```
[N need] → [N brief] → [N snapshot] → [N outcome] → [N cadence]
```

Then list rows grouped by stage below.

```jsx
export function SelfReviewTab({ data, onOpenItem }) {
  // data.development has selfReviewSignals, selfReviewRecords, selfReviewRuns, selfReviewOutcomes, selfReviewCadenceSignals
}
```

- [ ] **Step 2: Add CSS for flow summary pipeline**

```css
/* ─── MC: Self-Review Flow Pipeline ─── */
.mc-flow-summary {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 16px;
  background: #1c1f25;
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  margin-bottom: 16px;
}
.mc-flow-stage { font-size: 18px; font-weight: 300; color: #e4e6ed; }
.mc-flow-sep { color: #2d303d; font-size: 14px; }
.mc-flow-summary span { font-size: 11px; color: #8b909e; }
```

- [ ] **Step 3: Add "Self-Review" tab and route**

Add to MCTabBar:
```jsx
import { Shield } from 'lucide-react'
{ id: 'self-review', label: 'Self-Review', icon: Shield },
```

Route in MissionControlPage:
```jsx
{activeTab === 'self-review' ? (
  <SelfReviewTab data={sections.jarvis} onOpenItem={openJarvisDetail} />
) : null}
```

- [ ] **Step 4: Verify and commit**

```bash
git add apps/ui/src/components/mission-control/SelfReviewTab.jsx apps/ui/src/components/mission-control/MCTabBar.jsx apps/ui/src/app/MissionControlPage.jsx apps/ui/src/styles/global.css
git commit -m "feat(ui): extract SelfReviewTab with flow pipeline visualization"
```

---

## Task 8: Extract ContinuityTab

**Files:**
- Create: `apps/ui/src/components/mission-control/ContinuityTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

- [ ] **Step 1: Create ContinuityTab.jsx**

Extract from JarvisTab's Continuity sub-tab:
- `worldModelContextRow`, `worldModelSignalRow`
- `integrationCarryOverRow`
- `runtimeAwarenessSignalRow`, `runtimeAwarenessHistoryRow`
- Relation state, promotion signals from `data.continuity`

Layout:
1. **Summary row** — world model context + integration carry-over (2-col)
2. **World-Model Signals** — list with SectionTitle
3. **Runtime Awareness** — signals + history
4. **Relation & Promotion** — signals

```jsx
export function ContinuityTab({ data, onOpenItem }) {
  // data.continuity has worldModelSignals, runtimeAwarenessSignals, relationState, etc.
}
```

- [ ] **Step 2: Add "Continuity" tab and route**

Add to MCTabBar:
```jsx
import { Layers } from 'lucide-react'
{ id: 'continuity', label: 'Continuity', icon: Layers },
```

Route in MissionControlPage.

- [ ] **Step 3: Verify and commit**

```bash
git add apps/ui/src/components/mission-control/ContinuityTab.jsx apps/ui/src/components/mission-control/MCTabBar.jsx apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(ui): extract ContinuityTab — world model, runtime awareness, carry-over"
```

---

## Task 9: Delete JarvisTab.jsx

**Files:**
- Delete: `apps/ui/src/components/mission-control/JarvisTab.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx` (remove JarvisTab import)

- [ ] **Step 1: Remove JarvisTab import from MissionControlPage**

Delete the import line:
```jsx
import { JarvisTab } from '../components/mission-control/JarvisTab'
```

And the rendering block for `activeTab === 'jarvis'`.

- [ ] **Step 2: Delete JarvisTab.jsx**

```bash
rm apps/ui/src/components/mission-control/JarvisTab.jsx
```

- [ ] **Step 3: Verify no broken imports**

```bash
cd apps/ui && npx vite build 2>&1 | head -20
```

Expected: Build succeeds with no JarvisTab references.

- [ ] **Step 4: Commit**

```bash
git add -A apps/ui/src/components/mission-control/JarvisTab.jsx apps/ui/src/app/MissionControlPage.jsx
git commit -m "refactor(ui): remove monolithic JarvisTab.jsx — replaced by 4 focused tab components"
```

---

## Task 10: Add CostTab (from mock)

**Files:**
- Create: `apps/ui/src/components/mission-control/CostTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`
- Modify: `apps/ui/src/app/useMissionControlPhaseA.js`
- Modify: `apps/ui/src/lib/adapters.js`

- [ ] **Step 1: Add backend adapter for cost data**

In `adapters.js`, add to the `backend` object:

```js
async getCostSummary() {
  try {
    const data = await requestJson('/mc/cost/summary')
    return data
  } catch {
    return { cost_24h_usd: 0, tokens_24h: 0, unknown_pricing_24h: 0, providers: [] }
  }
},
```

- [ ] **Step 2: Add cost section to useMissionControlPhaseA**

Add `cost: null` to the initial data state. Add `'cost'` to `TAB_REFRESH_MS` with `30000`. Add a fetch function:

```js
async function fetchCost() {
  const data = await backend.getCostSummary()
  return { ...data, fetchedAt: new Date().toISOString() }
}
```

Wire it into the tab-switching logic alongside the other sections.

- [ ] **Step 3: Create CostTab.jsx (matching mock layout)**

```jsx
import { DollarSign, Hash, AlertCircle } from 'lucide-react'
import { MetricCard } from '../shared/MetricCard'
import { SectionTitle } from '../shared/SectionTitle'
import { Chip } from '../shared/Chip'

export function CostTab({ data }) {
  const cost = data || {}
  const providers = cost.providers || []

  return (
    <div className="mc-tab-page">
      {/* Summary cards */}
      <div className="mc-cost-cards">
        <MetricCard label="24h Cost (USD)" value={`$${Number(cost.cost_24h_usd || 0).toFixed(4)}`} icon={DollarSign} />
        <MetricCard label="24h Tokens" value={(cost.tokens_24h || 0).toLocaleString()} icon={Hash} />
        <MetricCard label="Unknown Pricing (24h)" value={cost.unknown_pricing_24h || 0} icon={AlertCircle} />
      </div>

      {/* Provider cost table */}
      <div className="support-card">
        <SectionTitle>Top Providers (24h)</SectionTitle>
        <table className="mc-table">
          <thead>
            <tr>
              {['Provider', 'Cost USD', 'Tokens', 'Calls'].map(h => (
                <th key={h} className="mono">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {providers.map(p => (
              <tr key={p.provider}>
                <td className="mono" style={{ color: '#5ab8a0' }}>{p.provider}</td>
                <td className="mono">{Number(p.cost_usd || 0).toFixed(4)}</td>
                <td className="mono">{p.tokens}</td>
                <td className="mono">{p.calls}</td>
              </tr>
            ))}
            {providers.length === 0 && (
              <tr><td colSpan={4} className="mc-table-empty mono">No cost data yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Add table CSS to global.css**

```css
/* ─── MC: Tables ─── */
.mc-table { width: 100%; border-collapse: collapse; }
.mc-table th {
  font-size: 9px; color: #4e5262; text-align: left;
  padding: 4px 8px; letter-spacing: 0.08em; text-transform: uppercase;
}
.mc-table td { padding: 7px 8px; font-size: 11px; color: #e4e6ed; }
.mc-table tr { transition: background 0.1s; }
.mc-table tbody tr:hover { background: #272b35; }
.mc-table-empty { color: #4e5262; font-style: italic; }

.mc-cost-cards { display: flex; gap: 10px; margin-bottom: 16px; }
```

- [ ] **Step 5: Add "Cost" tab to MCTabBar and route**

```jsx
import { DollarSign } from 'lucide-react'
{ id: 'cost', label: 'Cost', icon: DollarSign },
```

Route: `{activeTab === 'cost' ? <CostTab data={sections.cost} /> : null}`

- [ ] **Step 6: Verify and commit**

```bash
git add apps/ui/src/components/mission-control/CostTab.jsx apps/ui/src/components/mission-control/MCTabBar.jsx apps/ui/src/app/MissionControlPage.jsx apps/ui/src/app/useMissionControlPhaseA.js apps/ui/src/lib/adapters.js apps/ui/src/styles/global.css
git commit -m "feat(ui): add CostTab with metric cards and provider cost table"
```

---

## Task 11: Add MemoryTab, SkillsTab, HardeningTab, LabTab (stubs from mock)

**Files:**
- Create: `apps/ui/src/components/mission-control/MemoryTab.jsx`
- Create: `apps/ui/src/components/mission-control/SkillsTab.jsx`
- Create: `apps/ui/src/components/mission-control/HardeningTab.jsx`
- Create: `apps/ui/src/components/mission-control/LabTab.jsx`
- Modify: `apps/ui/src/components/mission-control/MCTabBar.jsx`
- Modify: `apps/ui/src/app/MissionControlPage.jsx`

These tabs are initially scaffolded with the mock's visual structure but use placeholder data since the backend endpoints don't exist yet. Each shows the correct layout and will be wired up when backends are ready.

- [ ] **Step 1: Create MemoryTab.jsx (scaffolded from mock)**

```jsx
import { Search, Filter } from 'lucide-react'
import { SectionTitle } from '../shared/SectionTitle'

export function MemoryTab() {
  return (
    <div className="mc-tab-page">
      <div className="mc-filter-bar">
        <div className="mc-search-input">
          <Search size={11} />
          <input placeholder="Search memory..." />
        </div>
      </div>
      <div className="support-card">
        <SectionTitle>Memory Items</SectionTitle>
        <div className="mc-empty-state">
          <strong>Backend endpoint not connected</strong>
          <p className="muted">Memory search will be available when /mc/memory is implemented.</p>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create SkillsTab.jsx, HardeningTab.jsx, LabTab.jsx (similar scaffolds)**

Each follows the mock layout with empty state placeholders. Use the mock's component structure (tables, cards, grids) but with "Not connected" empty states.

- [ ] **Step 3: Update MCTabBar — add all remaining tabs as primary**

Remove the MORE_TABS dropdown entirely. Make all tabs primary:

```jsx
const PRIMARY_TABS = [
  { id: 'overview',      label: 'Overview',      icon: Activity },
  { id: 'operations',    label: 'Operations',    icon: Bot },
  { id: 'observability', label: 'Observability',  icon: Eye },
  { id: 'cost',          label: 'Cost',           icon: DollarSign },
  { id: 'living-mind',   label: 'Living Mind',    icon: Brain },
  { id: 'development',   label: 'Development',    icon: TrendingUp },
  { id: 'continuity',    label: 'Continuity',     icon: Layers },
  { id: 'self-review',   label: 'Self-Review',    icon: Shield },
  { id: 'memory',        label: 'Memory',         icon: Database },
  { id: 'skills',        label: 'Skills',         icon: Package },
  { id: 'hardening',     label: 'Hardening',      icon: Lock },
  { id: 'lab',           label: 'Lab',            icon: FlaskConical },
]
```

Remove the `moreOpen` state and dropdown rendering. Remove `activeJarvisSubTab` and `onJarvisSubTabChange` props entirely.

- [ ] **Step 4: Route all new tabs in MissionControlPage**

```jsx
{activeTab === 'memory' ? <MemoryTab /> : null}
{activeTab === 'skills' ? <SkillsTab /> : null}
{activeTab === 'hardening' ? <HardeningTab /> : null}
{activeTab === 'lab' ? <LabTab /> : null}
```

- [ ] **Step 5: Verify all tabs render and commit**

```bash
git add apps/ui/src/components/mission-control/MemoryTab.jsx apps/ui/src/components/mission-control/SkillsTab.jsx apps/ui/src/components/mission-control/HardeningTab.jsx apps/ui/src/components/mission-control/LabTab.jsx apps/ui/src/components/mission-control/MCTabBar.jsx apps/ui/src/app/MissionControlPage.jsx
git commit -m "feat(ui): add Memory, Skills, Hardening, Lab tabs — scaffolded from mock designs"
```

---

## Task 12: Final Cleanup & Visual Polish

**Files:**
- Modify: `apps/ui/src/styles/global.css`
- Modify: `apps/ui/src/components/mission-control/OverviewTab.jsx`
- Modify: `apps/ui/src/components/mission-control/ObservabilityTab.jsx`

- [ ] **Step 1: Update OverviewTab to use MetricCard component**

Replace the `mc-stat` cards in OverviewTab with `<MetricCard>` components for consistent styling.

- [ ] **Step 2: Add progress bar utility CSS**

```css
/* ─── SHARED: Progress Bar ─── */
.progress-bar { height: 3px; background: #21252e; border-radius: 2px; }
.progress-bar-fill { height: 100%; border-radius: 2px; transition: width 0.8s ease; }
```

- [ ] **Step 3: Clean up unused CSS classes**

Remove CSS for:
- `.mc-sub-tabbar`, `.mc-sub-tab` (no more jarvis sub-tabs)
- `.mc-tab-more-wrapper`, `.mc-tab-more-dropdown`, `.mc-tab-more-item` (no more "More" dropdown)
- Any status-pill variants only used by JarvisTab

- [ ] **Step 4: Verify full app**

Run: `cd apps/ui && npx vite build`
Expected: Clean build with no warnings about missing components.

- [ ] **Step 5: Commit**

```bash
git add apps/ui/src/styles/global.css apps/ui/src/components/mission-control/OverviewTab.jsx apps/ui/src/components/mission-control/ObservabilityTab.jsx
git commit -m "refactor(ui): visual polish — MetricCard in OverviewTab, progress bars, clean up dead CSS"
```

---

## Summary

| Task | Description | Scope |
|------|-------------|-------|
| 1 | Design tokens & typography | Theme + CSS root |
| 2 | Shared components (MetricCard, SectionTitle, Chip) | 3 new files + CSS |
| 3 | Chat streaming cursor | ChatTranscript + CSS |
| 4 | Chain-of-thought WorkingIndicator | Backend SSE + new component + wiring |
| 5 | Extract LivingMindTab from JarvisTab | Largest extraction (13 subsystems incl. council, adaptive planner/reasoning/learning, guided learning) |
| 6 | Extract DevelopmentTab | Identity sub-tab content |
| 7 | Extract SelfReviewTab | Self-review pipeline |
| 8 | Extract ContinuityTab | World model + runtime awareness |
| 9 | Delete JarvisTab.jsx | Remove 4451-line monolith |
| 10 | Add CostTab (from mock) | New tab + backend adapter |
| 11 | Add Memory, Skills, Hardening, Lab tabs | Scaffolded from mock |
| 12 | Final cleanup & polish | OverviewTab upgrade, dead CSS removal |
